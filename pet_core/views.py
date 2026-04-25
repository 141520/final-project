from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from .models import PetPost, PetImage, Product, BlogPost
from datetime import date
from django.core.files.base import ContentFile
from .utils import extract_feature_vector, classify_pet_type, compress_image
from pgvector.django import CosineDistance
from collections import defaultdict
import logging
import os
import json
import uuid

# จำกัดจำนวนรูปต่อโพสต์
MAX_IMAGES_PER_POST = 5

logger = logging.getLogger(__name__)

# ---- หน้าหลัก ----
def home(request):
    recent_lost_pets = PetPost.objects.filter(post_type='lost', status='active').order_by('-created_at')[:4]
    if not recent_lost_pets.exists():
        recent_lost_pets = PetPost.objects.filter(post_type='lost').order_by('-created_at')[:4]

    recent_found_pets = PetPost.objects.filter(post_type='found', status='active').order_by('-created_at')[:4]
    if not recent_found_pets.exists():
        recent_found_pets = PetPost.objects.filter(post_type='found').order_by('-created_at')[:4]

    from django.contrib.auth import get_user_model
    User = get_user_model()
    stats = {
        'total_posts': PetPost.objects.count(),
        'total_users': User.objects.count(),
        'active_posts': PetPost.objects.filter(status='active').count(),
        'resolved_posts': PetPost.objects.filter(status='resolved').count(),
    }

    return render(request, 'pet_core/home.html', {
        'recent_lost_pets': recent_lost_pets,
        'recent_found_pets': recent_found_pets,
        **stats,
    })


# ---- แผนที่ ----
def map_view(request):
    posts = PetPost.objects.filter(
        latitude__isnull=False, longitude__isnull=False
    ).exclude(latitude=0, longitude=0).order_by('-created_at')

    posts_json = []
    for p in posts:
        posts_json.append({
            'id': p.id,
            'name': p.name or 'ไม่ระบุชื่อ',
            'post_type': p.post_type,
            'status': p.status,
            'pet_type': p.pet_type or '',
            'location_name': p.location_name or '',
            'reward': float(p.reward) if (p.reward and p.post_type == 'lost') else None,
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'image_url': p.supabase_image_url if p.image else '',
            'detail_url': f'/pet/{p.id}/',
            'created_at': p.created_at.strftime('%d/%m/%Y'),
        })

    total_lost = PetPost.objects.filter(post_type='lost', status='active').count()
    total_found = PetPost.objects.filter(post_type='found', status='active').count()

    return render(request, 'pet_core/map.html', {
        'posts_json': json.dumps(posts_json, ensure_ascii=False),
        'total_lost': total_lost,
        'total_found': total_found,
        'total_map': len(posts_json),
    })

# ---- รายการประกาศสัตว์หาย ----
def lost_pet_list(request):
    from django.db.models import Q
    q = request.GET.get('q', '').strip()
    posts = PetPost.objects.filter(post_type='lost').order_by('-created_at')
    if q:
        posts = posts.filter(
            Q(name__icontains=q) | Q(breed__icontains=q) |
            Q(location_name__icontains=q) | Q(color__icontains=q) |
            Q(description__icontains=q) | Q(pet_type__icontains=q)
        )
    return render(request, 'pet_core/lost_pet_list.html', {'posts': posts, 'q': q})

# ---- รายการประกาศสัตว์ที่พบ ----
def found_pet_list(request):
    from django.db.models import Q
    q = request.GET.get('q', '').strip()
    posts = PetPost.objects.filter(post_type='found').order_by('-created_at')
    if q:
        posts = posts.filter(
            Q(name__icontains=q) | Q(breed__icontains=q) |
            Q(location_name__icontains=q) | Q(color__icontains=q) |
            Q(description__icontains=q) | Q(pet_type__icontains=q)
        )
    return render(request, 'pet_core/found_pet_list.html', {'posts': posts, 'q': q})


# ---- helper: ประมวลผลรูปที่อัปโหลด (compress + AI vector) ----
def _process_uploaded_image(uploaded_file):
    """
    รับ Django UploadedFile → คืน (ContentFile_compressed, feature_vector_or_None, pet_type_guess_or_None)
    - ลดขนาดรูป (long edge 1600px, JPEG q82)
    - สกัด feature vector + จำแนกประเภทสัตว์ในขั้นตอนเดียว (ลด I/O)
    """
    try:
        compressed = compress_image(uploaded_file, max_dim=1600, quality=82)
        compressed_bytes = compressed.getvalue()
    except Exception as e:
        logger.warning(f"compress_image failed, fallback to original: {e}")
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        compressed_bytes = uploaded_file.read()

    # AI: feature vector + classification จาก bytes ที่ compress แล้ว (เร็วกว่ารูปต้นฉบับ)
    vector = None
    pet_type = None
    try:
        vector = extract_feature_vector(compressed_bytes)
    except Exception as e:
        logger.warning(f"feature extract failed: {e}")
    try:
        cls = classify_pet_type(compressed_bytes)
        pet_type = cls.get('pet_type')
    except Exception as e:
        logger.warning(f"classify failed: {e}")

    # ตั้งชื่อไฟล์ใหม่ unique เพื่อป้องกันชนกัน
    fname = f"{uuid.uuid4().hex}.jpg"
    return ContentFile(compressed_bytes, name=fname), vector, pet_type


def _attach_images_to_post(post, image_files):
    """
    บันทึกหลายรูป (สูงสุด MAX_IMAGES_PER_POST) ให้กับ PetPost
    - รูปแรก = main image
    - รูปทั้งหมด → PetImage พร้อม feature_vector
    - ถ้า post.pet_type ว่าง จะ auto-fill จาก AI prediction
    Returns: ai_pet_types list (ผลทำนายของแต่ละรูป)
    """
    ai_predictions = []
    saved = 0
    for i, f in enumerate(image_files[:MAX_IMAGES_PER_POST]):
        cfile, vec, pet_guess = _process_uploaded_image(f)
        ai_predictions.append(pet_guess)

        if i == 0:
            post.image = cfile
            post.save(update_fields=['image'])

        # PetImage with vector — บันทึก vector ตรง (ไม่พึ่ง model.save() เพื่อหลีกเลี่ยง round-trip)
        pi = PetImage(pet_post=post, image=cfile)
        pi.save()
        if vec is not None:
            pi.feature_vector = vec
            try:
                PetImage.objects.filter(pk=pi.pk).update(feature_vector=vec)
            except Exception as e:
                logger.warning(f"save vector failed: {e}")
        saved += 1

    # Auto-fill pet_type ถ้าผู้ใช้ไม่ได้ระบุ
    if not post.pet_type:
        # โหวตจาก predictions: pet_type ที่ปรากฏมากที่สุด
        valid = [p for p in ai_predictions if p]
        if valid:
            from collections import Counter
            top = Counter(valid).most_common(1)[0][0]
            post.pet_type = top
            post.save(update_fields=['pet_type'])
    return ai_predictions


# ---- helper: สร้างโพสต์จาก form ----
def _build_post_from_form(request, post_type):
    time_field = 'lost_time' if post_type == 'lost' else 'found_time'
    date_field = 'lost_date' if post_type == 'lost' else 'found_date'

    import re
    time_period = request.POST.get(f'{post_type}_time_period') or ''
    exact_time = request.POST.get(f'{post_type}_time_exact') or ''

    # map ป้ายกำกับช่วงเวลา → ชั่วโมงตัวแทน (เพื่อเก็บใน TimeField)
    PERIOD_MAP = {
        'ช่วงเช้า': '09:00', 'morning': '09:00', 'Morning': '09:00',
        'ช่วงบ่าย': '15:00', 'afternoon': '15:00', 'Afternoon': '15:00',
        'ช่วงเย็น': '18:00', 'evening': '18:00', 'Evening': '18:00',
        'ช่วงกลางคืน': '21:00', 'กลางคืน': '21:00', 'night': '21:00', 'Night': '21:00',
    }

    final_time = None
    if time_period == 'Exact' and exact_time:
        final_time = exact_time
    elif time_period:
        # ถ้าเป็น HH:MM อยู่แล้ว ใช้เลย
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_period.strip()):
            final_time = time_period.strip()
        else:
            # หา keyword ช่วงเวลาใน label
            for key, hhmm in PERIOD_MAP.items():
                if key in time_period:
                    final_time = hhmm
                    break
            # ถ้าไม่เข้า pattern ใดเลย เก็บเป็น None (กัน DB error)

    p_type = request.POST.get('pet_type', '').strip()
    if p_type == 'Other':
        p_type = request.POST.get('pet_type_other', '').strip()

    final_age = f"{request.POST.get('age_num', '').strip()} {request.POST.get('age_unit', '').strip()}".strip()

    data = dict(
        post_type=post_type,
        status='active',
        owner=request.user if request.user.is_authenticated else None,
        supabase_user_id=getattr(request, 'supabase_user_id', None),
        name=request.POST.get('pet_name', request.POST.get('name', 'ไม่ระบุชื่อ')).strip(),
        pet_type=p_type,
        breed=request.POST.get('breed', '').strip(),
        age=final_age,
        gender=request.POST.get('gender', '').strip(),
        color=request.POST.get('color', '').strip(),
        microchip=request.POST.get('microchip', '').strip(),
        description=request.POST.get('description', '').strip(),
        contact_name=request.POST.get('contact_name', '').strip(),
        contact_email=request.POST.get('contact_email', '').strip(),
        contact_phone=request.POST.get('contact_phone', '').strip(),
        location_name=request.POST.get('location_name', '').strip(),
        latitude=request.POST.get('latitude') or 0,
        longitude=request.POST.get('longitude') or 0,
        situation=request.POST.get('situation', '').strip(),
        social_link=request.POST.get('social_link', '').strip(),
        # reward เฉพาะประกาศ "หาย" (เจ้าของให้รางวัลคนช่วยตามหา)
        reward=(request.POST.get('reward') or None) if post_type == 'lost' else None,
    )
    data[date_field] = request.POST.get(date_field) or None
    data[time_field] = final_time
    return PetPost.objects.create(**data)


# ---- ลงประกาศสัตว์หาย (ต้องล็อกอิน) ----
@login_required
def report_lost(request):
    if request.method == 'POST':
        try:
            post = _build_post_from_form(request, 'lost')
            images = request.FILES.getlist('images') or request.FILES.getlist('image')
            if images:
                _attach_images_to_post(post, images)
            messages.success(request, '✅ ลงประกาศสัตว์หายสำเร็จแล้ว! AI ช่วยจำแนกประเภทสัตว์ให้แล้ว')
            return redirect('pet_detail', pet_id=post.id)
        except Exception as e:
            logger.exception("Error saving lost post")
            messages.error(request, f'เกิดข้อผิดพลาด: {e}')
    return render(request, 'pet_core/create_find_post.html', {
        'max_images': MAX_IMAGES_PER_POST,
    })


# ---- ลงประกาศสัตว์ที่พบ (ต้องล็อกอิน) ----
@login_required
def report_found(request):
    if request.method == 'POST':
        try:
            post = _build_post_from_form(request, 'found')
            images = request.FILES.getlist('images') or request.FILES.getlist('image')
            if images:
                _attach_images_to_post(post, images)
            messages.success(request, '✅ ลงประกาศสัตว์ที่พบสำเร็จแล้ว! AI ช่วยจำแนกประเภทสัตว์ให้แล้ว')
            return redirect('pet_detail', pet_id=post.id)
        except Exception as e:
            logger.exception("Error saving found post")
            messages.error(request, f'เกิดข้อผิดพลาด: {e}')
    return render(request, 'pet_core/create_found_post.html', {
        'max_images': MAX_IMAGES_PER_POST,
    })


# ---- ค้นหาด้วย AI (+ filter ประเภทสัตว์) ----
def search_pet(request):
    """
    AI Image Search:
      1) อัปโหลดรูป → classify_pet_type ตรวจจับประเภทอัตโนมัติ
      2) ดึง feature vector → เทียบกับทุก PetImage ใน DB (cosine distance)
      3) Group ผลลัพธ์ตาม PetPost (1 โพสต์ = 1 การ์ด, ใช้ image ที่ match สูงสุด)
      4) เรียงตาม similarity จากสูง → ต่ำ
    """
    results = []          # list ของ dict: {'post', 'best_image', 'similarity_pct', 'matched_count'}
    searched = False
    ai_detection = None   # ผลทำนายจากรูปที่ผู้ใช้อัปโหลด
    selected_pet_type = request.GET.get('pet_type') or request.POST.get('pet_type', '')
    selected_post_type = request.GET.get('post_type') or request.POST.get('post_type', '')
    auto_detected = False

    # รองรับ URL เก่า /search/lost/ /search/found/
    if not selected_post_type:
        path = request.path.rstrip('/')
        if path.endswith('/lost'):
            selected_post_type = 'lost'
        elif path.endswith('/found'):
            selected_post_type = 'found'

    if request.method == 'POST' and 'search_image' in request.FILES:
        searched = True
        search_img = request.FILES['search_image']

        # อ่านครั้งเดียวเป็น bytes — ส่งให้ AI ทั้ง classify + extract vector
        try:
            search_img.seek(0)
            img_bytes = search_img.read()
        except Exception:
            img_bytes = search_img.read()

        try:
            # 🤖 AI Classify (ตรวจประเภทสัตว์)
            ai_detection = classify_pet_type(img_bytes)
            # ถ้าผู้ใช้ไม่ได้เลือกประเภท + AI confident พอ (>30%) → ใช้ AI suggest
            if not selected_pet_type and ai_detection.get('pet_type') \
                    and ai_detection.get('confidence', 0) > 0.30:
                selected_pet_type = ai_detection['pet_type']
                auto_detected = True

            # 🧠 Feature vector
            query_vector = extract_feature_vector(img_bytes)

            if query_vector is not None:
                qs = PetImage.objects.filter(
                    feature_vector__isnull=False
                ).select_related('pet_post')

                if selected_pet_type:
                    qs = qs.filter(pet_post__pet_type__iexact=selected_pet_type)
                if selected_post_type in ('lost', 'found'):
                    qs = qs.filter(pet_post__post_type=selected_post_type)

                # threshold 0.75 — ผ่อนเพื่อจับผลที่อาจจะใช่
                similar = qs.annotate(
                    distance=CosineDistance('feature_vector', query_vector)
                ).filter(distance__lt=0.75).order_by('distance')[:50]

                # Group ตาม pet_post — เก็บ image ที่ similarity สูงสุดของโพสต์นั้น
                best_per_post = {}
                count_per_post = defaultdict(int)
                for img_obj in similar:
                    pid = img_obj.pet_post_id
                    count_per_post[pid] += 1
                    if pid not in best_per_post or img_obj.distance < best_per_post[pid].distance:
                        best_per_post[pid] = img_obj

                # เรียงโดย distance น้อยสุดก่อน (similarity สูง)
                ranked = sorted(best_per_post.values(), key=lambda x: x.distance)[:12]
                for img_obj in ranked:
                    similarity = round((1 - img_obj.distance) * 100, 1)
                    results.append({
                        'post': img_obj.pet_post,
                        'image': img_obj,
                        'similarity_pct': similarity,
                        'matched_count': count_per_post[img_obj.pet_post_id],
                    })

        except Exception:
            logger.exception("AI search failed")

    return render(request, 'pet_core/search.html', {
        'results': results,
        'searched': searched,
        'ai_detection': ai_detection,
        'auto_detected': auto_detected,
        'selected_pet_type': selected_pet_type,
        'selected_post_type': selected_post_type,
    })


# ---- รายละเอียดโพสต์ ----
def pet_detail(request, pet_id):
    pet = get_object_or_404(PetPost, id=pet_id)
    images = list(pet.images.all().order_by('id'))  # ทั้งหมดของโพสต์นี้
    # ถ้าไม่มี PetImage แต่มี main image → ใช้ main image เป็นรูปเดียว
    image_urls = [img.supabase_image_url for img in images if img.supabase_image_url]
    if not image_urls and pet.image:
        image_urls = [pet.supabase_image_url]

    is_owner = (
        request.user.is_authenticated
        and pet.owner_id
        and pet.owner_id == request.user.id
    )
    return render(request, 'pet_core/pet_detail.html', {
        'pet': pet,
        'is_owner': is_owner,
        'image_urls': image_urls,
        'image_count': len(image_urls),
    })


# ---- แก้ไขโพสต์ (เฉพาะเจ้าของ) ----
@login_required
def edit_post(request, pet_id):
    pet = get_object_or_404(PetPost, id=pet_id)
    if pet.owner_id != request.user.id:
        return HttpResponseForbidden("❌ คุณไม่ใช่เจ้าของประกาศนี้")

    if request.method == 'POST':
        # อัปเดตฟิลด์ข้อความ
        for field in ['name', 'pet_type', 'breed', 'age', 'gender', 'color',
                      'microchip', 'description', 'contact_name', 'contact_email',
                      'contact_phone', 'social_link', 'location_name', 'situation',
                      'status']:
            val = request.POST.get(field)
            if val is not None:
                setattr(pet, field, val.strip())

        if request.POST.get('latitude'):
            pet.latitude = request.POST.get('latitude')
        if request.POST.get('longitude'):
            pet.longitude = request.POST.get('longitude')

        # 🟢 รางวัล — เฉพาะประกาศ "หาย" เท่านั้น (found post จะถูกล้างเป็น None)
        if pet.post_type == 'lost':
            reward_val = request.POST.get('reward', '').strip()
            pet.reward = reward_val if reward_val else None
        else:
            pet.reward = None

        # 🟢 วันที่/เวลา หาย-พบ
        if pet.post_type == 'lost':
            pet.lost_date = request.POST.get('lost_date') or None
            pet.lost_time = request.POST.get('lost_time') or None
        else:
            pet.found_date = request.POST.get('found_date') or None
            pet.found_time = request.POST.get('found_time') or None

        pet.save()

        # 🟢 เพิ่มรูปใหม่ (ถ้ามี) — เก็บได้สูงสุด MAX_IMAGES_PER_POST รูป
        new_images = request.FILES.getlist('images') or (
            [request.FILES['image']] if 'image' in request.FILES else []
        )
        if new_images:
            existing_count = pet.images.count()
            slots_left = MAX_IMAGES_PER_POST - existing_count
            if slots_left > 0:
                _attach_images_to_post(pet, new_images[:slots_left])
            else:
                messages.info(request, f'มีรูปครบ {MAX_IMAGES_PER_POST} แล้ว — กรุณาลบรูปเก่าก่อน')

        # 🟢 ลบรูปย่อยที่ผู้ใช้เลือก
        delete_ids = request.POST.getlist('delete_image_ids')
        if delete_ids:
            pet.images.filter(id__in=delete_ids).delete()

        messages.success(request, '✅ แก้ไขประกาศเรียบร้อยแล้ว')
        return redirect('pet_detail', pet_id=pet.id)

    return render(request, 'pet_core/edit_post.html', {
        'pet': pet,
        'pet_images': pet.images.all().order_by('id'),
        'max_images': MAX_IMAGES_PER_POST,
    })


# ---- ลบโพสต์ (เฉพาะเจ้าของ) ----
@login_required
def delete_post(request, pet_id):
    pet = get_object_or_404(PetPost, id=pet_id)
    if pet.owner_id != request.user.id:
        return HttpResponseForbidden("❌ คุณไม่ใช่เจ้าของประกาศนี้")
    if request.method == 'POST':
        pet.delete()
        messages.success(request, '🗑️ ลบประกาศแล้ว')
        return redirect('my_posts')
    return render(request, 'pet_core/confirm_delete.html', {'pet': pet})


# ---- สินค้าและบทความ (admin จัดการผ่าน /admin/) ----
def product_list(request):
    """แสดงสินค้าที่ is_active + อยู่ในช่วงโปรโมท (หรือยังไม่ตั้งช่วง)"""
    today = date.today()
    qs = Product.objects.filter(is_active=True)
    # เอาเฉพาะที่ยังอยู่ในช่วงโปรโมท (หรือ admin ยังไม่กำหนดช่วง)
    products = []
    for p in qs:
        if not p.promotion_start or not p.promotion_end:
            products.append(p)
        elif p.promotion_start <= today <= p.promotion_end:
            products.append(p)

    # filter หมวดหมู่
    category = request.GET.get('category', '').strip()
    if category:
        products = [p for p in products if p.category == category]

    blog_posts = BlogPost.objects.filter(is_published=True)[:3]

    return render(request, 'pet_core/product_list.html', {
        'products': products,
        'blog_posts': blog_posts,
        'category_choices': Product.CATEGORY_CHOICES,
        'selected_category': category,
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    return render(request, 'pet_core/product_detail.html', {'product': product})


# ---- บทความ ----
def blog_list(request):
    posts = BlogPost.objects.filter(is_published=True)
    return render(request, 'pet_core/blog_list.html', {'posts': posts})


def blog_detail(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id, is_published=True)
    related = BlogPost.objects.filter(is_published=True).exclude(id=post.id)[:3]
    return render(request, 'pet_core/blog_detail.html', {'post': post, 'related': related})


# ---- ระบบ Auth ของ FoundPet ----

def login_view(request):
    return render(request, 'registration/login.html')


@require_POST
def logout_view(request):
    """Django session logout (Supabase signOut ทำที่ client)"""
    django_logout(request)
    response = redirect('home')
    response.delete_cookie('sb-access-token', path='/')
    return response


def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)


@login_required
def profile_view(request):
    # นับโพสต์ของตัวเอง
    my_posts = PetPost.objects.filter(owner=request.user)
    ctx = {
        'total_posts': my_posts.count(),
        'lost_count': my_posts.filter(post_type='lost').count(),
        'found_count': my_posts.filter(post_type='found').count(),
        'active_count': my_posts.filter(status='active').count(),
    }
    return render(request, 'profile.html', ctx)


@login_required
def my_posts_view(request):
    posts = PetPost.objects.filter(owner=request.user).order_by('-created_at')
    filter_type = request.GET.get('type', '')
    if filter_type in ('lost', 'found'):
        posts = posts.filter(post_type=filter_type)
    return render(request, 'my_posts.html', {
        'posts': posts,
        'total': posts.count(),
        'filter_type': filter_type,
    })


def create_post(request):
    return redirect('report_lost')
