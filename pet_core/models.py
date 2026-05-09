from django.db import models
from django.conf import settings
from pgvector.django import VectorField

# 1. คลาส PetPost
class PetPost(models.Model):
    POST_TYPE_CHOICES = (
        ('lost', 'หาย'), 
        ('found', 'พบ')
    )
    
    STATUS_CHOICES = (
        ('active', 'กำลังตามหา/กำลังหาเจ้าของ'),
        ('resolved', 'เจอแล้ว/ส่งคืนแล้ว'),
    )

    GENDER_CHOICES = (
        ('M', 'ตัวผู้'),
        ('F', 'ตัวเมีย'),
        ('U', 'ไม่ระบุ/ไม่แน่ใจ'),
    )
    
    # --- เจ้าของโพสต์ (ผู้ประกาศ) ---
    # null=True, blank=True เพื่อให้ migrate ได้ไม่ต้องลบข้อมูลเก่า
    # โพสต์เก่าที่ไม่มีเจ้าของจะแก้ไขไม่ได้จนกว่าจะ assign
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pet_posts',
        verbose_name="ผู้ประกาศ"
    )
    # Supabase Auth user id (UUID) — เผื่อกรณี Django User ยังไม่ถูกสร้าง
    supabase_user_id = models.CharField(
        max_length=64, null=True, blank=True, db_index=True,
        verbose_name="Supabase UUID"
    )

    # --- ข้อมูลสถานะ ---
    post_type = models.CharField(max_length=10, choices=POST_TYPE_CHOICES, default='lost', verbose_name="ประเภทประกาศ")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name="สถานะ")
    
    # --- ข้อมูลทั่วไป ---
    name = models.CharField(max_length=100, verbose_name="ชื่อสัตว์เลี้ยง/ลักษณะเด่น")
    pet_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="ประเภทสัตว์ (เช่น สุนัข, แมว)")
    breed = models.CharField(max_length=100, null=True, blank=True, verbose_name="สายพันธุ์")
    age = models.CharField(max_length=50, null=True, blank=True, verbose_name="อายุ")
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True, verbose_name="เพศ")
    color = models.CharField(max_length=100, null=True, blank=True, verbose_name="สี")
    microchip = models.CharField(max_length=100, null=True, blank=True, verbose_name="หมายเลขไมโครชิป")
    description = models.TextField(verbose_name="รายละเอียดเพิ่มเติม", null=True, blank=True)
    
    # 🌟 รูปภาพหลัก (บันทึกลง Supabase)
    image = models.ImageField(upload_to='pets/', null=True, blank=True, verbose_name="รูปภาพหลัก")
    
    # --- ข้อมูลติดต่อ ---
    contact_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="ชื่อผู้ติดต่อ")
    contact_email = models.EmailField(null=True, blank=True, verbose_name="อีเมลผู้ติดต่อ")
    contact_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="เบอร์โทรศัพท์")
    social_link = models.URLField(max_length=500, null=True, blank=True, verbose_name="ลิงก์โซเชียลมีเดีย")
    
    # --- สถานที่และแผนที่ ---
    location_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="สถานที่ (ชื่อเรียก)")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="ละติจูด")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="ลองจิจูด")
    situation = models.TextField(null=True, blank=True, verbose_name="สถานการณ์ตอนที่หาย/พบ")
    reward = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="รางวัล (บาท)",
        help_text="ระบุจำนวนเงินรางวัลถ้ามี (ไม่บังคับ)"
    )
    
    # --- วันที่และเวลา ---
    lost_date = models.DateField(null=True, blank=True, verbose_name="วันที่หาย")
    lost_time = models.TimeField(null=True, blank=True, verbose_name="เวลาที่หาย")
    found_date = models.DateField(null=True, blank=True, verbose_name="วันที่พบ")
    found_time = models.TimeField(null=True, blank=True, verbose_name="เวลาที่พบ")
    
    # --- การปิดประกาศ (เจอน้อง / ส่งคืนเจ้าของ) ---
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="วันที่ปิดประกาศ")
    resolved_note = models.TextField(
        blank=True, verbose_name="ข้อความเมื่อปิดประกาศ",
        help_text="เช่น เรื่องราวการกลับมา / ขอบคุณคนที่ช่วย"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pet_core_petpost'
        ordering = ['-created_at'] 
        verbose_name = "ประกาศสัตว์เลี้ยง"
        verbose_name_plural = "ประกาศสัตว์เลี้ยงทั้งหมด"

    def __str__(self):
        return f"[{self.get_post_type_display()}] {self.name} - สถานะ: {self.get_status_display()}"

    def thumb_url(self, width=400, quality=72):
        """คืน URL รูป — ใช้ Supabase public object endpoint (ฟรี).
        หมายเหตุ: Image Transform (resize/WebP at edge) ต้อง Supabase Pro plan
        ถ้าอนาคต upgrade ค่อยเปลี่ยน path เป็น /storage/v1/render/image/public/
        """
        return self.supabase_image_url

    @property
    def supabase_image_url(self):
        if self.image:
            image_path = str(self.image)
            if image_path.startswith('http'):
                return image_path
            
            # ลบคำว่า media/ หรือ /media/ ออก
            if image_path.startswith('/media/'):
                image_path = image_path[7:]
            elif image_path.startswith('media/'):
                image_path = image_path[6:]
                
            from django.conf import settings
            base_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.AWS_STORAGE_BUCKET_NAME}/"
            return f"{base_url}{image_path}"
        
        # ถ้ารูปไม่มี ให้แสดงรูป Placeholder
        return "https://placehold.co/264x264?text=No+Image"


# 2. คลาส PetImage
class PetImage(models.Model):
    pet_post = models.ForeignKey(PetPost, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='pet_images/')
    feature_vector = VectorField(dimensions=2048, null=True, blank=True)

    class Meta:
        db_table = 'pet_core_petimage'

    # 👇👇👇 ส่วนที่เพิ่มเข้ามาใหม่สำหรับ PetImage 👇👇👇
    @property
    def supabase_image_url(self):
        if self.image:
            image_path = str(self.image)
            if image_path.startswith('http'):
                return image_path
                
            if image_path.startswith('/media/'):
                image_path = image_path[7:]
            elif image_path.startswith('media/'):
                image_path = image_path[6:]
                
            from django.conf import settings
            base_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.AWS_STORAGE_BUCKET_NAME}/"
            return f"{base_url}{image_path}"
        return ""

    # NOTE: feature_vector ถูก set โดย views._attach_images_to_post() ตอน upload
    # ไม่ต้อง override save() เพื่อ download รูปจาก Supabase กลับมาประมวลผล (ช้ามาก)


# =========================================================
# 3. Product — สินค้าโปรโมท (admin จัดการ)
# =========================================================
class Product(models.Model):
    """สินค้าที่ลูกค้าจ่ายค่าโปรโมท (default 50,000 บ / 30 วัน)"""
    CATEGORY_CHOICES = (
        ('food',    'อาหาร/ขนม'),
        ('toy',     'ของเล่น'),
        ('hygiene', 'ของใช้/ความสะอาด'),
        ('gadget',  'อุปกรณ์/GPS/Tracker'),
        ('supplement', 'อาหารเสริม/วิตามิน'),
        ('other',   'อื่นๆ'),
    )

    # ข้อมูลสินค้า
    name = models.CharField(max_length=200, verbose_name="ชื่อสินค้า")
    description = models.TextField(blank=True, verbose_name="รายละเอียด")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="ราคาตั้ง (บาท) — ไม่บังคับ",
        help_text="ไม่ต้องใส่ก็ได้ถ้าจะใช้ 'Sync ราคา' จาก external_link แทน"
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', verbose_name="หมวดหมู่")
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="รูปสินค้า")
    external_link = models.URLField(
        max_length=500, blank=True,
        verbose_name="ลิงก์ไปร้านค้า",
        help_text=(
            "วางลิงก์สินค้าจาก Shopee / Lazada / Facebook ฯลฯ<br>"
            "✅ <b>ใส่ได้เลยทุกแบบ</b> — ระบบจะตัด tracking token (sp_atk, utm_* ฯลฯ) ออกให้อัตโนมัติ<br>"
            "ตัวอย่าง Shopee: <code>https://shopee.co.th/product-name-i.123456.789</code>"
        )
    )
    # ราคาที่ดึงจากหน้าร้านอัตโนมัติ (optional)
    scraped_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="ราคาจากหน้าร้าน (sync อัตโนมัติ)",
        help_text="ราคานี้จะถูก sync จาก external_link เมื่อกดปุ่ม 'Sync ราคา' — ถ้ามีจะโชว์แทน price"
    )
    last_scraped_at = models.DateTimeField(null=True, blank=True, verbose_name="sync ราคาล่าสุด")

    # ข้อมูลผู้ลงโปรโมท
    promoter_name = models.CharField(max_length=200, blank=True, verbose_name="ชื่อลูกค้า/ร้านค้า")
    promoter_contact = models.CharField(max_length=200, blank=True, verbose_name="ช่องทางติดต่อ")
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=50000,
        verbose_name="ค่าโปรโมทที่จ่าย (บาท)"
    )

    # ระยะเวลาโปรโมท
    promotion_days = models.PositiveIntegerField(default=30, verbose_name="จำนวนวันโปรโมท")
    promotion_start = models.DateField(null=True, blank=True, verbose_name="วันที่เริ่มโปรโมท")
    promotion_end = models.DateField(null=True, blank=True, verbose_name="วันที่สิ้นสุด")

    # สถานะ
    is_active = models.BooleanField(default=True, verbose_name="แสดงบนเว็บ")
    sort_order = models.IntegerField(default=0, verbose_name="ลำดับการแสดง (น้อยมาก่อน)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pet_core_product'
        ordering = ['sort_order', '-created_at']
        verbose_name = "สินค้าโปรโมท"
        verbose_name_plural = "สินค้าโปรโมท"

    def __str__(self):
        return f"{self.name} (฿{self.price})"

    def clean(self):
        """แปลง Shopee URL เป็น canonical format ก่อนบันทึก
        เช่น shopee.co.th/สินค้า-i.123456.789 → shopee.co.th/product/123456/789
        """
        import re
        url = (self.external_link or '').strip()
        if url and any(d in url for d in ('shopee.co.th', 'shopee.com', 'shp.ee')):
            # รูปแบบ i.{shop_id}.{item_id} ที่ Shopee ใช้ทั่วไป
            match = re.search(r'[iI]\.(\d{6,})\.(\d{6,})', url)
            if match:
                self.external_link = (
                    f'https://shopee.co.th/product/{match.group(1)}/{match.group(2)}'
                )

    def save(self, *args, **kwargs):
        # คำนวณ promotion_end อัตโนมัติ
        from datetime import timedelta, date
        if self.promotion_start and self.promotion_days and not self.promotion_end:
            self.promotion_end = self.promotion_start + timedelta(days=self.promotion_days)
        super().save(*args, **kwargs)

    @property
    def is_promotion_active(self):
        """เช็คว่ายังอยู่ในช่วงโปรโมทอยู่ไหม"""
        from datetime import date
        today = date.today()
        if not (self.promotion_start and self.promotion_end):
            return self.is_active
        return self.is_active and self.promotion_start <= today <= self.promotion_end

    @property
    def days_remaining(self):
        from datetime import date
        if not self.promotion_end:
            return None
        return max((self.promotion_end - date.today()).days, 0)

    @property
    def display_price(self):
        """ถ้ามี scraped_price ให้ใช้ก่อน (ราคาจริงจากหน้าร้าน) — ไม่มีก็ใช้ราคา manual"""
        return self.scraped_price if self.scraped_price else self.price

    @property
    def display_image_url(self):
        if self.image:
            path = str(self.image)
            if path.startswith('http'):
                return path
            from django.conf import settings
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.AWS_STORAGE_BUCKET_NAME}/{path}"
        return "https://placehold.co/300x300?text=No+Image"

    @property
    def all_image_urls(self):
        """รวมรูปทั้งหมด: main image (ถ้ามี) + extra images — สำหรับ swipeable gallery
        ถ้า table pet_core_productimage ยังไม่ถูก migrate จะ fallback ได้ปลอดภัย
        """
        urls = []
        if self.image:
            urls.append(self.display_image_url)
        try:
            for ex in self.extra_images.all().order_by('sort_order', 'id'):
                url = ex.image_url
                if url and url not in urls:
                    urls.append(url)
        except Exception:
            pass  # table ยังไม่ถูก migrate / DB error — แสดงแค่ main image ไปก่อน
        return urls or ["https://placehold.co/600x600?text=No+Image"]


# =========================================================
# 3b. ProductImage — รูปเสริมของสินค้า (admin อัปโหลดได้สูงสุด 9 รูปนอกจาก main)
# =========================================================
class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name='extra_images', on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='products/', verbose_name="รูปสินค้า")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ลำดับ (น้อย→มาก่อน)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pet_core_productimage'
        ordering = ['sort_order', 'id']
        verbose_name = "รูปสินค้า (เสริม)"
        verbose_name_plural = "รูปสินค้า (เสริม)"

    def __str__(self):
        return f"Image #{self.id} of {self.product_id}"

    @property
    def image_url(self):
        if self.image:
            path = str(self.image)
            if path.startswith('http'):
                return path
            from django.conf import settings
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.AWS_STORAGE_BUCKET_NAME}/{path}"
        return ""


# =========================================================
# 4. BlogPost — บทความ/เคล็ดลับ (admin เขียน)
# =========================================================
class BlogPost(models.Model):
    title = models.CharField(max_length=300, verbose_name="หัวข้อบทความ")
    summary = models.CharField(max_length=500, blank=True, verbose_name="สรุปสั้น (แสดงใต้ title)")
    cover_image = models.ImageField(upload_to='blog/', null=True, blank=True, verbose_name="รูปปก")
    body = models.TextField(verbose_name="เนื้อหา (รองรับ HTML)")

    author_name = models.CharField(max_length=100, blank=True, verbose_name="ผู้เขียน")
    published_at = models.DateField(null=True, blank=True, verbose_name="วันที่เผยแพร่")
    is_published = models.BooleanField(default=True, verbose_name="เผยแพร่บนเว็บ")

    # แหล่งที่มา / อ้างอิง
    source_name = models.CharField(
        max_length=200, blank=True,
        verbose_name="แหล่งที่มา (ชื่อ)",
        help_text="เช่น: สัตวแพทย์ ดร.สมชาย / เว็บไซต์ petmd.com / วารสารสัตวแพทย์ไทย"
    )
    source_url = models.URLField(
        max_length=500, blank=True,
        verbose_name="ลิงก์แหล่งที่มา",
        help_text="URL ของเว็บไซต์ต้นฉบับ (ถ้ามี)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pet_core_blogpost'
        ordering = ['-published_at', '-created_at']
        verbose_name = "บทความ/เคล็ดลับ"
        verbose_name_plural = "บทความ/เคล็ดลับ"

    def __str__(self):
        return self.title

    @property
    def display_cover_url(self):
        if self.cover_image:
            path = str(self.cover_image)
            if path.startswith('http'):
                return path
            from django.conf import settings
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.AWS_STORAGE_BUCKET_NAME}/{path}"
        return "https://placehold.co/400x260?text=No+Image"


# =========================================================
# 5. Comment — ความเห็นใต้โพสต์ pet (Reaction + Comment)
# =========================================================
class Comment(models.Model):
    pet_post = models.ForeignKey(
        'PetPost', related_name='comments', on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='comments'
    )
    author_name = models.CharField(max_length=80, blank=True, verbose_name="ชื่อผู้แสดงความเห็น")
    text = models.TextField(verbose_name="ข้อความ")
    reaction = models.CharField(max_length=8, blank=True, verbose_name="รีแอ็กชัน")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pet_core_comment'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['pet_post', '-created_at'])]

    def __str__(self):
        return f"Comment by {self.author_name or self.user_id} on post {self.pet_post_id}"

    @property
    def display_name(self):
        if self.user:
            return self.user.first_name or self.user.username or self.author_name or 'ผู้ใช้'
        return self.author_name or 'ผู้ใช้'

    @property
    def initial(self):
        n = self.display_name
        return n[0].upper() if n else '?'


