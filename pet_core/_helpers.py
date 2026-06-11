"""
Internal helpers shared across views.

แยกออกมาจาก views.py เพื่อให้ views.py เน้นเฉพาะ HTTP handlers
helper เหล่านี้ไม่ถูก map เข้า urls.py
"""
from urllib.parse import urlparse as _urlparse

from django.core.cache import cache
from django.core.exceptions import ValidationError
from PIL import Image as PILImage

from .models import AuditLog

# ─────────────────────────────────────────────
# Shared constants
# ─────────────────────────────────────────────
MAX_IMAGES_PER_POST = 5
MAX_IMAGE_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}

ALLOWED_SOCIAL_DOMAINS = (
    'facebook.com', 'fb.com', 'fb.watch',
    'instagram.com', 'instagr.am',
    'twitter.com', 'x.com',
    'tiktok.com', 'vm.tiktok.com',
    'youtube.com', 'youtu.be',
    'line.me', 'lin.ee',
)


# ─────────────────────────────────────────────
# Request inspection
# ─────────────────────────────────────────────
def client_ip(request):
    """คืน IP จริงของ client.

    Render.com (และ proxy ทั่วไป) ต่อท้าย X-Forwarded-For ด้วย IP จริง
    การหยิบ entry แรกถูก spoof ได้ — ต้องหยิบ entry สุดท้าย
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR') or 'unknown'


def is_rate_limited(request, action, limit, window_seconds):
    """In-memory rate limiter (cache-backed). Skip non-POST."""
    if request.method != 'POST':
        return False
    key = f"rl:{action}:{getattr(request.user, 'id', None) or client_ip(request)}"
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, window_seconds)
    return False


# ─────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────
def validate_image_files(image_files):
    """ตรวจ size + MIME + magic bytes ของไฟล์รูป"""
    for uploaded_file in image_files[:MAX_IMAGES_PER_POST]:
        if getattr(uploaded_file, 'size', 0) > MAX_IMAGE_UPLOAD_BYTES:
            raise ValidationError('รูปภาพต้องมีขนาดไม่เกิน 8MB ต่อไฟล์')

        content_type = getattr(uploaded_file, 'content_type', '')
        if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ValidationError('รองรับเฉพาะไฟล์รูป JPG, PNG หรือ WebP')

        try:
            uploaded_file.seek(0)
            with PILImage.open(uploaded_file) as img:
                img.verify()
        except Exception as exc:
            raise ValidationError('ไฟล์ที่อัปโหลดไม่ใช่รูปภาพที่ถูกต้อง') from exc
        finally:
            try:
                uploaded_file.seek(0)
            except Exception:
                pass


def clean_social_link(url: str) -> str:
    """คืน url ถ้าอยู่ใน ALLOWED_SOCIAL_DOMAINS — ไม่ผ่านคืน ''"""
    if not url:
        return ''
    try:
        parsed = _urlparse(url if url.startswith(('http://', 'https://')) else f'https://{url}')
        host = parsed.netloc.lower().lstrip('www.')
        if any(host == d or host.endswith(f'.{d}') for d in ALLOWED_SOCIAL_DOMAINS):
            return url
    except Exception:
        pass
    return ''


# ─────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────
def audit(request, action, obj=None, metadata=None, logger=None):
    """บันทึก AuditLog แบบไม่ break view ถ้า log เขียนไม่สำเร็จ"""
    try:
        AuditLog.objects.create(
            user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            action=action,
            object_type=obj.__class__.__name__ if obj is not None else '',
            object_id=str(getattr(obj, 'pk', '') or ''),
            ip_address=client_ip(request),
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            metadata=metadata or {},
        )
    except Exception:
        if logger:
            logger.exception("Audit log write failed: action=%s", action)
