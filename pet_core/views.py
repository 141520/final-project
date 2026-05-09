from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from .models import PetPost, PetImage, Product, BlogPost, Comment
from datetime import date
from django.core.files.base import ContentFile
from .utils import extract_feature_vector, classify_pet_type, compress_image, analyze_image
from pgvector.django import CosineDistance
from django.core.cache import cache
from django.db.models import Count, Q
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
    """Home — แคช 60 วิ (ผ่าน DB-level cache, render ใหม่ทุกครั้งเพื่อให้ nav แสดง user ปัจจุบัน)"""
    cached = cache.get('home_data_v2')
    if cached is None:
        # 1 query for stats (4 counts → 1 aggregate)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        agg = PetPost.objects.aggregate(
            total_posts=Count('id'),
            active_posts=Count('id', filter=Q(status='active')),
            resolved_posts=Count('id', filter=Q(status='resolved')),
        )
        recent_lost = list(
            PetPost.objects.filter(post_type='lost', status='active')
            .only('id', 'name', 'pet_type', 'breed', 'location_name', 'image', 'created_at', 'reward')
            .order_by('-created_at')[:4]
        )
        recent_found = list(
            PetPost.objects.filter(post_type='found', status='active')
            .only('id', 'name', 'pet_type', 'breed', 'location_name', 'image', 'created_at')
            .order_by('-created_at')[:4]
        )
        cached = {
            'recent_lost_pets': recent_lost,
            'recent_found_pets': recent_found,
            'total_posts': agg['total_posts'],
            'total_users': User.objects.count(),
            'active_posts': agg['active_posts'],
            'resolved_posts': agg['resolved_posts'],
        }
        cache.set('home_data_v2', cached, 60)

    return render(request, 'pet_core/home.html', cached)


# ---- แผนที่ ----
def map_view(request):
    cached = cache.get('map_data_v1')
    if cached is None:
        from django.conf import settings as _s
        base_url = f"{_s.SUPABASE_URL}/storage/v1/object/public/{_s.AWS_STORAGE_BUCKET_NAME}/"

        # values() — skip model object creation, ~5x faster than .all() loop
        rows = PetPost.objects.filter(
            latitude__isnull=False, longitude__isnull=False, status='active'
        ).exclude(latitude=0, longitude=0).order_by('-created_at').values(
            'id', 'name', 'post_type', 'status', 'pet_type', 'location_name',
            'reward', 'latitude', 'longitude', 'image', 'created_at'
        )[:500]

        posts_json = []
        for r in rows:
            img = str(r['image']) if r['image'] else ''
            if img and not img.startswith('http'):
                img = base_url + img.lstrip('/').removeprefix('media/')
            posts_json.append({
                'id': r['id'],
                'name': r['name'] or 'ไม่ระบุชื่อ',
                'post_type': r['post_type'],
                'status': r['status'],
                'pet_type': r['pet_type'] or '',
                'location_name': r['location_name'] or '',
                'reward': float(r['reward']) if (r['reward'] and r['post_type'] == 'lost') else None,
                'lat': float(r['latitude']),
                'lng': float(r['longitude']),
                'image_url': img,
                'detail_url': f"/pet/{r['id']}/",
                'created_at': r['created_at'].strftime('%d/%m/%Y'),
            })

        agg = PetPost.objects.filter(status='active').aggregate(
            total_lost=Count('id', filter=Q(post_type='lost')),
            total_found=Count('id', filter=Q(post_type='found')),
        )
        cached = {
            'posts_json': posts_json,
            'total_lost': agg['total_lost'],
            'total_found': agg['total_found'],
        }
        cache.set('map_data_v1', cached, 90)

    posts_json = cached['posts_json']
    total_lost = cached['total_lost']
    total_found = cached['total_found']

    return render(request, 'pet_core/map.html', {
        'posts_json': json.dumps(posts_json, ensure_ascii=False),
        'total_lost': total_lost,
        'total_found': total_found,
        'total_map': len(posts_json),
    })

_LIST_FIELDS = ('id', 'name', 'pet_type', 'breed', 'color', 'location_name',
                'image', 'created_at', 'reward', 'post_type', 'status')


def _list_posts(post_type: str, q: str):
    """Helper: คืน QuerySet เบาๆ (.only() ดึงเฉพาะ fields ที่ template ใช้)"""
    qs = (PetPost.objects
          .filter(post_type=post_type, status='active')
          .only(*_LIST_FIELDS)
          .order_by('-created_at'))
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(breed__icontains=q) |
            Q(location_name__icontains=q) | Q(color__icontains=q) |
            Q(description__icontains=q) | Q(pet_type__icontains=q)
        )
    return qs


# ---- รายการประกาศสัตว์หาย ----
def lost_pet_list(request):
    q = request.GET.get('q', '').strip()
    if not q:
        # Cache เฉพาะ list ที่ไม่มี search query (60s)
        posts = cache.get('list_lost_v1')
        if posts is None:
            posts = list(_list_posts('lost', q)[:120])
            cache.set('list_lost_v1', posts, 60)
    else:
        posts = _list_posts('lost', q)[:120]
    return render(request, 'pet_core/lost_pet_list.html', {'posts': posts, 'q': q})


# ---- รายการประกาศสัตว์ที่พบ ----
def found_pet_list(request):
    q = request.GET.get('q', '').strip()
    if not q:
        posts = cache.get('list_found_v1')
        if posts is None:
            posts = list(_list_posts('found', q)[:120])
            cache.set('list_found_v1', posts, 60)
    else:
        posts = _list_posts('found', q)[:120]
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

    # AI: รวม feature extract + classify ในรอบเดียว (TTA + L2 normalized)
    # → DB ได้ vector คุณภาพสูง + auto-detect pet_type พร้อมกัน
    vector = None
    pet_type = None
    try:
        analysis = analyze_image(compressed_bytes)
        vector = analysis.get('feature_vector')
        pet_type = analysis.get('pet_type')
    except Exception as e:
        logger.warning(f"AI analyze failed: {e}")

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
            # 🤖 Single-pass: TTA + classify + feature extract ในรอบเดียว (~2x เร็วกว่าเดิม)
            analysis = analyze_image(img_bytes)
            ai_detection = {
                'pet_type': analysis.get('pet_type'),
                'confidence': analysis.get('confidence', 0.0),
                'top_labels': analysis.get('top_labels', []),
            }
            query_vector = analysis.get('feature_vector')
            ai_pet_type = ai_detection.get('pet_type')
            ai_conf = ai_detection.get('confidence', 0)

            # AI suggest แสดงเป็นข้อความ — แต่ไม่ filter เข้ม (เป็น soft boost ตอน scoring)
            # __any__ = ผู้ใช้เลือก "อื่นๆ/ทั้งหมด" → ไม่ filter ประเภทเลย
            any_type = (selected_pet_type == '__any__')
            user_picked_type = bool(selected_pet_type) and not any_type
            if not selected_pet_type and ai_pet_type and ai_conf > 0.30:
                selected_pet_type = ai_pet_type  # โชว์ที่ UI เฉยๆ
                auto_detected = True

            if query_vector is not None:
                qs = PetImage.objects.filter(
                    feature_vector__isnull=False,
                    pet_post__status='active',  # ❗ ไม่ค้นเจอโพสต์ที่ปิดแล้ว
                ).select_related('pet_post')

                # Hard filter เฉพาะตอนผู้ใช้เลือกประเภทแบบเฉพาะเจาะจง
                # ('อื่นๆ/ทั้งหมด' หรือ auto-detect → ไม่ filter, ให้ AI หาทุกประเภท)
                if user_picked_type:
                    qs = qs.filter(pet_post__pet_type__iexact=selected_pet_type)
                if selected_post_type in ('lost', 'found'):
                    qs = qs.filter(pet_post__post_type=selected_post_type)

                # ดึงทั้งหมดมาเทียบ (ไม่มี threshold) → re-rank → ตัดเหลือ 24
                # ผ่อนสุดทางเพื่อให้แสดงผลเยอะที่สุด — เรียงลำดับโดย similarity ดี-แย่
                similar = qs.annotate(
                    distance=CosineDistance('feature_vector', query_vector)
                ).order_by('distance')[:200]

                # Group ตาม post — เก็บ best image + นับจำนวน match
                best_per_post = {}
                count_per_post = defaultdict(int)
                sum_dist_per_post = defaultdict(float)
                for img_obj in similar:
                    pid = img_obj.pet_post_id
                    count_per_post[pid] += 1
                    sum_dist_per_post[pid] += img_obj.distance
                    if pid not in best_per_post or img_obj.distance < best_per_post[pid].distance:
                        best_per_post[pid] = img_obj

                # 🎯 Smart re-ranking score (ค่ายิ่งสูง = match ดี)
                # องค์ประกอบ:
                #  - base similarity (1 - distance) ของรูปที่ดีที่สุด → 0..1
                #  - multi-image bonus: ถ้ามีหลายรูปของโพสต์เดียว match ด้วย → bonus 0..0.15
                #  - pet_type match bonus: ถ้า AI ทำนายตรงกับโพสต์ → bonus 0.05
                scored = []
                for pid, img_obj in best_per_post.items():
                    base_sim = max(0.0, 1.0 - float(img_obj.distance))
                    n_match = count_per_post[pid]
                    # log-scale bonus: 1 รูป=0, 2 รูป=+0.07, 3=+0.10, 5=+0.13
                    multi_bonus = min(0.15, 0.07 * (n_match - 1) ** 0.7) if n_match > 1 else 0.0
                    # pet_type bonus
                    type_bonus = 0.0
                    if ai_pet_type and img_obj.pet_post.pet_type \
                            and img_obj.pet_post.pet_type.lower() == ai_pet_type.lower():
                        type_bonus = 0.05

                    final_score = base_sim + multi_bonus + type_bonus
                    scored.append((final_score, base_sim, n_match, img_obj))

                # เรียงตาม final_score มาก→น้อย
                scored.sort(key=lambda x: -x[0])
                top = scored[:24]

                for final_score, base_sim, n_match, img_obj in top:
                    # แสดง similarity ที่เห็นในการ์ดเป็น base_sim (ไม่ใช่ score รวม)
                    # เพื่อไม่ให้ผู้ใช้เข้าใจผิดว่า >100%
                    results.append({
                        'post': img_obj.pet_post,
                        'image': img_obj,
                        'similarity_pct': round(base_sim * 100, 1),
                        'matched_count': n_match,
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
    comments = list(pet.comments.select_related('user').all()[:50])

    return render(request, 'pet_core/pet_detail.html', {
        'pet': pet,
        'is_owner': is_owner,
        'image_urls': image_urls,
        'image_count': len(image_urls),
        'comments': comments,
        'comments_count': len(comments),
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


# ---- ปิดประกาศ: เจอน้องแล้ว / ส่งคืนเจ้าของแล้ว (เฉพาะเจ้าของ) ----
@login_required
@require_POST
def mark_as_resolved(request, pet_id):
    pet = get_object_or_404(PetPost, id=pet_id)
    if pet.owner_id != request.user.id:
        return HttpResponseForbidden("❌ คุณไม่ใช่เจ้าของประกาศนี้")

    if pet.status == 'resolved':
        messages.info(request, 'ประกาศนี้ถูกปิดไปแล้ว')
        return redirect('pet_detail', pet_id=pet.id)

    from django.utils import timezone
    pet.status = 'resolved'
    pet.resolved_at = timezone.now()
    pet.resolved_note = (request.POST.get('resolved_note') or '').strip()[:1000]
    pet.save(update_fields=['status', 'resolved_at', 'resolved_note', 'updated_at'])

    # ลบ feature_vector เพื่อไม่ให้โผล่ใน image search อีก (โพสต์ยังคงอยู่)
    pet.images.update(feature_vector=None)

    if pet.post_type == 'lost':
        messages.success(request, '🎉 ยินดีด้วย! ปิดประกาศเรียบร้อย — น้องกลับบ้านปลอดภัยแล้ว')
    else:
        messages.success(request, '🎉 ส่งคืนน้องเรียบร้อย — ขอบคุณที่ช่วยเหลือน้อง!')
    return redirect('pet_detail', pet_id=pet.id)


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
    try:
        image_urls = product.all_image_urls
    except Exception:
        image_urls = [product.display_image_url] if product.image else ["https://placehold.co/600x600?text=No+Image"]
    return render(request, 'pet_core/product_detail.html', {
        'product': product,
        'image_urls': image_urls,
    })


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


# =========================================================
# 🆕 PRO FEATURES: Comments, Stories, Leaderboard, OG image
# =========================================================

# ---- POST: comment / reaction บนโพสต์ ----
@require_POST
def post_comment(request, pet_id):
    pet = get_object_or_404(PetPost, id=pet_id)
    text = (request.POST.get('text') or '').strip()[:1000]
    reaction = (request.POST.get('reaction') or '').strip()[:8]

    if not text and not reaction:
        return JsonResponse({'ok': False, 'error': 'empty'}, status=400)

    user = request.user if request.user.is_authenticated else None
    author = (request.POST.get('author_name') or '').strip()[:80]
    if user and not author:
        author = user.first_name or user.username or ''

    c = Comment.objects.create(
        pet_post=pet, user=user,
        author_name=author, text=text or '👍', reaction=reaction,
    )
    if request.headers.get('x-requested-with') == 'fetch':
        return JsonResponse({
            'ok': True,
            'comment': {
                'id': c.id,
                'name': c.display_name,
                'initial': c.initial,
                'text': c.text,
                'reaction': c.reaction,
                'when': 'เมื่อสักครู่',
            },
        })
    return redirect(f'/pet/{pet.id}/#comments')


# ---- Dynamic OG image for sharing (Pillow generated) ----
@require_GET
def og_image(request, pet_id):
    """Generate 1200x630 PNG with pet name/photo/branding for social sharing."""
    from django.http import HttpResponse
    from PIL import Image as PImage, ImageDraw, ImageFont
    import io as _io
    import urllib.request

    pet = get_object_or_404(PetPost, id=pet_id)
    W, H = 1200, 630

    # Background
    img = PImage.new('RGB', (W, H), (252, 238, 213))
    draw = ImageDraw.Draw(img)

    # Decorative blob
    for r, c in [(420, (117, 110, 245, 100)), (320, (215, 92, 167, 90))]:
        blob = PImage.new('RGBA', (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(blob)
        bd.ellipse((W - r * 2, -r // 2, W + r // 2, r), fill=c)
        img.paste(blob, (0, 0), blob)

    # Try to load pet image from Supabase
    if pet.image:
        try:
            url = pet.thumb_url(width=520, quality=80)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                pet_img = PImage.open(_io.BytesIO(resp.read())).convert('RGB')
            pet_img.thumbnail((460, 460))
            # circular mask
            mask = PImage.new('L', pet_img.size, 0)
            ImageDraw.Draw(mask).ellipse((0, 0, *pet_img.size), fill=255)
            img.paste(pet_img, (60, (H - pet_img.height) // 2), mask)
        except Exception:
            pass

    # Text — use default font (no font file required)
    try:
        font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        font_mid = ImageFont.truetype("DejaVuSans.ttf", 32)
        font_sm  = ImageFont.truetype("DejaVuSans.ttf", 26)
    except Exception:
        font_big = ImageFont.load_default()
        font_mid = ImageFont.load_default()
        font_sm  = ImageFont.load_default()

    badge = '🔍 ตามหา' if pet.post_type == 'lost' else '🐾 พบเจอ'
    draw.rectangle((560, 100, 760, 150), fill=(2, 31, 116))
    draw.text((576, 108), badge, fill='white', font=font_mid)

    name = (pet.name or 'ไม่ระบุชื่อ')[:30]
    draw.text((560, 180), name, fill=(2, 31, 116), font=font_big)

    info_lines = []
    if pet.pet_type: info_lines.append(f"ประเภท: {pet.pet_type}")
    if pet.breed: info_lines.append(f"พันธุ์: {pet.breed[:30]}")
    if pet.location_name: info_lines.append(f"สถานที่: {pet.location_name[:35]}")
    y = 280
    for line in info_lines[:3]:
        draw.text((560, y), line, fill=(50, 50, 70), font=font_mid)
        y += 50

    draw.text((560, H - 80), 'TarmRoy · ตามหาสัตว์เลี้ยงหาย 🐾',
              fill=(2, 31, 116), font=font_sm)

    out = _io.BytesIO()
    img.save(out, format='PNG', optimize=True)
    out.seek(0)
    response = HttpResponse(out.read(), content_type='image/png')
    response['Cache-Control'] = 'public, max-age=86400'
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
