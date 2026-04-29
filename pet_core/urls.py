from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # ระบบค้นหา — route เดียว ใช้ query string ?pet_type=&post_type=
    path('search/', views.search_pet, name='search_pet'),
    path('search/lost/', views.search_pet, name='search_lost'),
    path('search/found/', views.search_pet, name='search_found'),

    # รายการประกาศ
    path('lost/', views.lost_pet_list, name='lost_pet_list'),
    path('found/', views.found_pet_list, name='found_pet_list'),

    # ลงประกาศใหม่ (ต้องล็อกอิน)
    path('report/lost/', views.report_lost, name='report_lost'),
    path('report/found/', views.report_found, name='report_found'),

    # รายละเอียด / แก้ไข / ลบ
    path('pet/<int:pet_id>/', views.pet_detail, name='pet_detail'),
    path('pet/<int:pet_id>/edit/', views.edit_post, name='edit_post'),
    path('pet/<int:pet_id>/resolved/', views.mark_as_resolved, name='mark_as_resolved'),
    path('pet/<int:pet_id>/delete/', views.delete_post, name='delete_post'),

    # แผนที่
    path('map/', views.map_view, name='map_view'),

    # สินค้า
    path('products/', views.product_list, name='product_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),

    # บทความ/เคล็ดลับ
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<int:post_id>/', views.blog_detail, name='blog_detail'),

    # 🆕 PRO features
    path('stories/', views.stories_view, name='stories'),
    path('feed/', views.feed_view, name='feed'),
    path('pet/<int:pet_id>/comment/', views.post_comment, name='post_comment'),
    path('pet/<int:pet_id>/og.png', views.og_image, name='pet_og_image'),

    # ส่วนของสมาชิก
    path('my_posts/', views.my_posts_view, name='my_posts'),
    path('login/', TemplateView.as_view(template_name='registration/login.html'), name='login'),
    path('signup/', TemplateView.as_view(template_name='registration/signup.html'), name='signup'),
    path('reset-password/', TemplateView.as_view(template_name='registration/reset_password.html'), name='reset_password'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]

handler404 = 'pet_core.views.custom_404'
handler500 = 'pet_core.views.custom_500'

# Django ยอมให้เข้าถึงไฟล์รูปภาพที่อัปโหลด (เฉพาะ DEBUG)
if settings.DEBUG and getattr(settings, 'MEDIA_ROOT', None):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
