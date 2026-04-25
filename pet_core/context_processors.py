"""Context processors — inject ค่าจาก settings ลง template ทุกหน้า"""
from django.conf import settings


def supabase_settings(request):
    """ส่ง Supabase URL + anon key ลง template
    ใช้ใน base.html แทนการ hardcode"""
    return {
        'SUPABASE_URL': settings.SUPABASE_URL,
        'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
    }
