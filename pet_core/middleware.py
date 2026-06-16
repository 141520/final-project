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
import base64
import logging
import secrets
import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.utils.deprecation import MiddlewareMixin
from jwt import PyJWKClient

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add lightweight security headers without an extra dependency."""

    def process_request(self, request):
        request.csp_nonce = base64.b64encode(secrets.token_bytes(16)).decode('ascii')

    def process_response(self, request, response):
        nonce = getattr(request, 'csp_nonce', '')
        response.setdefault(
            'Content-Security-Policy',
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://unpkg.com; "
            f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://unpkg.com; "
            f"font-src 'self' https://fonts.gstatic.com data:; "
            f"img-src 'self' data: https:; "
            f"connect-src 'self' https:; "
            f"frame-ancestors 'self'; "
            f"base-uri 'self'; "
            f"form-action 'self';"
        )
        response.setdefault('Permissions-Policy', 'geolocation=(self), camera=(), microphone=()')
        return response


class SupabaseAuthMiddleware(MiddlewareMixin):
    """Sync Supabase JWT → Django User session"""

    def _extract_token(self, request):
        # 1. Authorization header
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Bearer '):
            return auth[7:].strip()
        # 2. Cookie (Supabase JS SDK เก็บไว้ที่คุกกี้นี้)
        return request.COOKIES.get('sb-access-token') or request.COOKIES.get('supabase-auth-token')

    def _decode_verified_token(self, token):
        """Verify Supabase access token and return trusted claims."""
        issuer = settings.SUPABASE_URL.rstrip('/') + '/auth/v1'

        try:
            jwks_client = PyJWKClient(issuer + '/.well-known/jwks.json')
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            alg = jwt.get_unverified_header(token).get('alg')
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg] if alg else ['RS256', 'ES256'],
                issuer=issuer,
                options={"verify_aud": False},
            )
        except Exception as jwks_error:
            logger.info("JWKS token verification failed, trying Auth server: %s", jwks_error)

        try:
            resp = requests.get(
                issuer + '/user',
                headers={
                    'apikey': settings.SUPABASE_ANON_KEY,
                    'Authorization': f'Bearer {token}',
                },
                timeout=4,
            )
            if resp.status_code != 200:
                logger.warning("Supabase token verification failed: HTTP %s", resp.status_code)
                return None
            user_data = resp.json()
            return {
                'sub': user_data.get('id'),
                'email': user_data.get('email') or '',
            }
        except Exception as auth_error:
            logger.warning("Supabase token verification request failed: %s", auth_error)
            return None

    def process_request(self, request):
        # ถ้า login อยู่แล้วผ่าน Django session ปกติ — ผ่าน
        if getattr(request, 'user', None) and request.user.is_authenticated:
            return None

        token = self._extract_token(request)
        if not token:
            return None

        payload = self._decode_verified_token(token)
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
