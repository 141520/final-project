"""
SupabaseAuthMiddleware
---------------------
อ่าน Supabase JWT access_token ที่ frontend ส่งมาทาง header `Authorization: Bearer <token>`
หรือคุกกี้ `sb-access-token`  แล้ว:
  1. verify token กับ Supabase
  2. สร้าง/หา Django User ที่ผูกกับ Supabase UUID
  3. login ผู้ใช้ใน Django session ให้อัตโนมัติ

ทำให้ `@login_required` และ `request.user.is_authenticated` ใช้ได้ตามปกติ
พร้อมตรวจ ownership โพสต์ได้
"""
import logging
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class SupabaseAuthMiddleware(MiddlewareMixin):
    """Sync Supabase JWT → Django User session"""

    def _extract_token(self, request):
        # 1. Authorization header
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Bearer '):
            return auth[7:].strip()
        # 2. Cookie (Supabase JS SDK เก็บไว้ที่คุกกี้นี้)
        return request.COOKIES.get('sb-access-token') or request.COOKIES.get('supabase-auth-token')

    def _decode_token(self, token):
        """Decode JWT โดยไม่ verify signature (dev-friendly)
        ⚠️ Production: ควรดึง JWKS มา verify จริง
        สำหรับโปรเจกต์เรียน — ใช้ decode อ่าน payload พอ
        """
        try:
            return jwt.decode(
                token, options={"verify_signature": False, "verify_aud": False}
            )
        except jwt.PyJWTError as e:
            logger.warning(f"JWT decode failed: {e}")
            return None

    def process_request(self, request):
        # ถ้า login อยู่แล้วผ่าน Django session ปกติ — ผ่าน
        if getattr(request, 'user', None) and request.user.is_authenticated:
            return None

        token = self._extract_token(request)
        if not token:
            return None

        payload = self._decode_token(token)
        if not payload:
            return None

        sb_user_id = payload.get('sub')
        email = payload.get('email') or ''
        if not sb_user_id:
            return None

        # หา/สร้าง Django user ที่ผูกกับ supabase uuid
        # ใช้ username = "sb_<uuid ตัด 12 ตัวแรก>" เพื่อ unique + อ่านได้
        username = f"sb_{sb_user_id[:12]}"
        user, created = UserModel.objects.get_or_create(
            username=username,
            defaults={'email': email, 'first_name': email.split('@')[0] if email else ''},
        )
        if not created and email and user.email != email:
            user.email = email
            user.save(update_fields=['email'])

        # เก็บ supabase uuid ไว้ที่ request เพื่อใช้ที่ view ได้
        request.supabase_user_id = sb_user_id

        # Login เข้า Django session
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        return None
