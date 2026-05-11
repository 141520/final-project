from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import PetPost, PetImage, Product, ProductImage, BlogPost, Comment, AuditLog


# ==========================================================
# Customize Admin Site — หัว-ท้าย + ลบ Group (ไม่ได้ใช้)
# ==========================================================
admin.site.site_header = "🐾 TarmRoy Admin"
admin.site.site_title = "TarmRoy Admin"
admin.site.index_title = "ยินดีต้อนรับสู่ระบบจัดการ TarmRoy"

# ลบ Group ออก — เว็บนี้ไม่ได้ใช้ระบบกลุ่มผู้ใช้
admin.site.unregister(Group)

# ==========================================================
# ปรับ User Admin ให้เรียบง่ายขึ้น (แสดงแค่ที่จำเป็น)
# ==========================================================
admin.site.unregister(User)

@admin.register(User)
class SimpleUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    list_per_page = 25
    # ซ่อน fieldsets ที่ซับซ้อน
    fieldsets = (
        ('🔐 ข้อมูลเข้าสู่ระบบ', {'fields': ('username', 'password')}),
        ('👤 ข้อมูลส่วนตัว', {'fields': ('first_name', 'last_name', 'email')}),
        ('🔑 สิทธิ์การใช้งาน', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
            'description': (
                '⚠️ <b>is_staff</b> = เข้า Admin ได้ · '
                '<b>is_superuser</b> = มีสิทธิ์ทุกอย่าง (ระวัง!)'
            ),
        }),
        ('📅 วันที่', {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )


# ==========================================================
# PetImage (inline — แสดงในหน้า PetPost)
# ==========================================================
class PetImageInline(admin.TabularInline):
    model = PetImage
    extra = 0
    fields = ('thumbnail', 'image', 'has_vector')
    readonly_fields = ('thumbnail', 'has_vector')

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:80px;border-radius:6px;"/>',
                obj.supabase_image_url,
            )
        return "—"
    thumbnail.short_description = "รูป"

    def has_vector(self, obj):
        return "✅" if obj.feature_vector is not None else "❌ ยังไม่ได้สกัด"
    has_vector.short_description = "AI Vector"


# ==========================================================
# PetPost
# ==========================================================
@admin.register(PetPost)
class PetPostAdmin(admin.ModelAdmin):
    list_display = (
        'thumb', 'name', 'post_type_badge', 'pet_type', 'status_badge',
        'owner', 'location_name', 'created_at',
    )
    list_filter = ('post_type', 'status', 'pet_type', 'gender', 'created_at')
    search_fields = ('name', 'breed', 'description', 'contact_name',
                     'contact_phone', 'contact_email', 'location_name')
    list_per_page = 20
    list_select_related = ('owner',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('owner',)
    readonly_fields = ('created_at', 'updated_at', 'main_image_preview')
    inlines = [PetImageInline]

    fieldsets = (
        ('📌 สถานะและเจ้าของ', {
            'fields': ('post_type', 'status', 'owner', 'supabase_user_id',
                       'created_at', 'updated_at')
        }),
        ('🐶 ข้อมูลสัตว์เลี้ยง', {
            'fields': ('name', 'pet_type', 'breed', 'age', 'gender', 'color',
                       'microchip', 'description', 'main_image_preview', 'image')
        }),
        ('📞 ข้อมูลติดต่อ', {
            'fields': ('contact_name', 'contact_email', 'contact_phone', 'social_link')
        }),
        ('📍 สถานที่และเวลา', {
            'fields': ('location_name', 'latitude', 'longitude', 'situation',
                       'lost_date', 'lost_time', 'found_date', 'found_time')
        }),
    )

    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:6px;"/>',
                obj.supabase_image_url,
            )
        return "—"
    thumb.short_description = "รูป"

    def post_type_badge(self, obj):
        colors = {'lost': '#E74C3C', 'found': '#27AE60'}
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:10px;font-size:12px;">{}</span>',
            colors.get(obj.post_type, '#888'), obj.get_post_type_display(),
        )
    post_type_badge.short_description = "ประเภท"

    def status_badge(self, obj):
        colors = {'active': '#F39C12', 'resolved': '#2ECC71'}
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:10px;font-size:12px;">{}</span>',
            colors.get(obj.status, '#888'), obj.get_status_display(),
        )
    status_badge.short_description = "สถานะ"

    def main_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:300px;border-radius:8px;"/>',
                obj.supabase_image_url,
            )
        return "ยังไม่มีรูป"
    main_image_preview.short_description = "ตัวอย่างรูปหลัก"


# ==========================================================
# PetImage (standalone — สำหรับดู AI vectors)
# ==========================================================
@admin.register(PetImage)
class PetImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'thumb', 'pet_post', 'has_vector')
    list_filter = ('pet_post__post_type', 'pet_post__pet_type')
    search_fields = ('pet_post__name',)
    autocomplete_fields = ('pet_post',)
    list_select_related = ('pet_post',)

    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:60px;height:60px;object-fit:cover;border-radius:6px;"/>',
                obj.supabase_image_url,
            )
        return "—"
    thumb.short_description = "รูป"

    def has_vector(self, obj):
        return "✅" if obj.feature_vector is not None else "❌"
    has_vector.short_description = "AI vector"


# ==========================================================
# ProductImage (inline — รูปเสริม สูงสุด 9 รูป รวม main = 10)
# ==========================================================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    max_num = 9   # 9 + main image (1) = 10 รูปสูงสุด
    fields = ('thumbnail', 'image', 'sort_order')
    readonly_fields = ('thumbnail',)

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:80px;object-fit:cover;border-radius:6px;"/>',
                obj.image_url,
            )
        return "—"
    thumbnail.short_description = "ตัวอย่าง"


# ==========================================================
# Product — สินค้าโปรโมท
# ==========================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = (
        'thumb', 'name', 'category', 'price_display',
        'promotion_status', 'image_count', 'is_active', 'sort_order',
    )
    list_editable = ('is_active', 'sort_order')
    list_filter = ('is_active', 'category', 'promotion_start', 'promotion_end')
    search_fields = ('name', 'description')
    list_per_page = 30
    ordering = ('sort_order', '-created_at')
    readonly_fields = ('created_at', 'updated_at', 'image_preview',
                       'promotion_status_detail', 'days_remaining_display')

    def image_count(self, obj):
        n = (1 if obj.image else 0) + obj.extra_images.count()
        color = '#2ECC71' if n >= 1 else '#bbb'
        return format_html('<span style="color:{};font-weight:700;">{} / 10</span>', color, n)
    image_count.short_description = "จำนวนรูป"

    fieldsets = (
        ('🛒 ข้อมูลสินค้า', {
            'fields': ('name', 'description', 'category', 'price',
                       'image_preview', 'image', 'external_link'),
            'description': (
                '💡 <b>external_link</b> = ลิงก์ไปร้านค้า (Shopee/Lazada/เว็บร้าน) — '
                'ผู้ใช้กดปุ่ม "ดูสินค้า" จะไปที่ลิงก์นี้<br>'
                '💡 วาง Shopee URL ได้เลย ระบบแปลงเป็น canonical URL ให้อัตโนมัติ'
            ),
        }),
        ('⏰ ระยะเวลาโปรโมท', {
            'description': 'กำหนด "วันที่เริ่ม" + "จำนวนวัน" แล้วระบบจะคำนวณวันสิ้นสุดให้',
            'fields': ('promotion_start', 'promotion_days', 'promotion_end',
                       'promotion_status_detail', 'days_remaining_display')
        }),
        ('🌐 การแสดงผลบนเว็บ', {
            'fields': ('is_active', 'sort_order')
        }),
        ('🕐 Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def thumb(self, obj):
        url = obj.display_image_url
        return format_html(
            '<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:6px;"/>',
            url,
        )
    thumb.short_description = "รูป"

    def image_preview(self, obj):
        url = obj.display_image_url
        return format_html('<img src="{}" style="max-width:300px;border-radius:8px;"/>', url)
    image_preview.short_description = "ตัวอย่างรูป"

    def price_display(self, obj):
        if obj.price is None:
            return format_html('<span style="color:#bbb;">—</span>')
        return f"฿{obj.price:,.0f}"
    price_display.short_description = "ราคาตั้ง"

    def promotion_status(self, obj):
        if not obj.promotion_start:
            return format_html('<span style="color:#888;">ยังไม่เริ่ม</span>')
        if obj.is_promotion_active:
            days = obj.days_remaining
            return format_html(
                '<span style="background:#2ECC71;color:#fff;padding:3px 10px;border-radius:10px;">'
                'กำลังโปรโมท ({} วันเหลือ)</span>', days)
        return format_html(
            '<span style="background:#95A5A6;color:#fff;padding:3px 10px;border-radius:10px;">หมดอายุ</span>')
    promotion_status.short_description = "สถานะ"

    def promotion_status_detail(self, obj):
        if not obj.pk:
            return "บันทึกสินค้าก่อนเพื่อดูสถานะ"
        if not obj.promotion_start:
            return "⚪ ยังไม่ได้ตั้งวันเริ่มโปรโมท"
        if obj.is_promotion_active:
            return format_html(
                '🟢 <b>กำลังโปรโมท</b> — เหลือ {} วัน<br>'
                '(เริ่ม {} → สิ้นสุด {})',
                obj.days_remaining, obj.promotion_start, obj.promotion_end)
        return format_html(
            '🔴 <b>หมดอายุ</b> (สิ้นสุดเมื่อ {})<br>'
            'ถ้าต้องการโปรโมทต่อ: เปลี่ยน "วันที่เริ่ม" ใหม่ + ล้าง "วันที่สิ้นสุด"',
            obj.promotion_end)
    promotion_status_detail.short_description = "สถานะโปรโมท"

    def days_remaining_display(self, obj):
        if obj.days_remaining is None:
            return "—"
        return f"{obj.days_remaining} วัน"
    days_remaining_display.short_description = "วันที่เหลือ"

    actions = ['mark_active', 'mark_inactive']

    @admin.action(description="✅ เปิดแสดงบนเว็บ")
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"เปิดแสดง {updated} รายการ")

    @admin.action(description="🚫 ซ่อนจากเว็บ")
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"ซ่อน {updated} รายการ")


# ==========================================================
# BlogPost — บทความ/เคล็ดลับ
# ==========================================================
@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('thumb', 'title', 'author_name', 'published_at',
                    'is_published', 'created_at')
    list_editable = ('is_published',)
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'summary', 'body', 'author_name')
    date_hierarchy = 'published_at'
    readonly_fields = ('created_at', 'updated_at', 'cover_preview')

    fieldsets = (
        ('📝 เนื้อหา', {
            'fields': ('title', 'summary', 'cover_preview', 'cover_image', 'body')
        }),
        ('👤 ผู้เขียนและการเผยแพร่', {
            'fields': ('author_name', 'published_at', 'is_published')
        }),
        ('📚 แหล่งที่มา / อ้างอิง', {
            'fields': ('source_name', 'source_url'),
            'description': (
                '💡 ระบุแหล่งที่มาของบทความ (ถ้ามี) เพื่อความน่าเชื่อถือ<br>'
                '<b>source_name</b> = ชื่อแหล่งที่มา เช่น "สัตวแพทย์หญิง ดร.นภา" หรือ "petmd.com"<br>'
                '<b>source_url</b> = ลิงก์เว็บต้นฉบับ (ถ้าอ้างอิงจากเว็บอื่น)'
            ),
        }),
        ('🕐 Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def thumb(self, obj):
        return format_html(
            '<img src="{}" style="width:80px;height:50px;object-fit:cover;border-radius:4px;"/>',
            obj.display_cover_url,
        )
    thumb.short_description = "ปก"

    def cover_preview(self, obj):
        return format_html(
            '<img src="{}" style="max-width:400px;border-radius:8px;"/>',
            obj.display_cover_url,
        )
    cover_preview.short_description = "ตัวอย่างรูปปก"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'pet_post', 'display_name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'author_name', 'pet_post__name')
    list_select_related = ('pet_post', 'user')
    readonly_fields = ('created_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'user', 'object_type', 'object_id', 'ip_address')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'object_type', 'object_id', 'ip_address')
    list_select_related = ('user',)
    readonly_fields = ('created_at', 'user', 'action', 'object_type', 'object_id', 'ip_address', 'user_agent', 'metadata')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
