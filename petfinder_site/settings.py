import os
from pathlib import Path
from dotenv import load_dotenv

# 1. ตั้งค่า Path พื้นฐาน (ต้องอยู่บนสุด)
BASE_DIR = Path(__file__).resolve().parent.parent

# โหลด .env
load_dotenv(BASE_DIR / '.env')

# ---- Helper ----
def env(key, default=None, required=False):
    val = os.environ.get(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val

def env_bool(key, default=False):
    val = os.environ.get(key, '').lower()
    if val in ('1', 'true', 'yes', 'on'):
        return True
    if val in ('0', 'false', 'no', 'off'):
        return False
    return default

# ---- Security ----
SECRET_KEY = env('DJANGO_SECRET_KEY', required=True)
DEBUG = env_bool('DJANGO_DEBUG', default=False)
ALLOWED_HOSTS = [h.strip() for h in env('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# 2. ลงทะเบียนแอป
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',  # 🟢 SEO: /sitemap.xml

    # Library เสริม
    'storages',  # 🟢 ใช้สำหรับเชื่อมต่อ Supabase Storage

    # แอปของคุณ
    'pet_core',
    'pgvector',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'pet_core.middleware.SecurityHeadersMiddleware',
    # 🟢 WhiteNoise — serve static files ใน production (Render)
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # 🟢 GZip HTML responses (~70% smaller HTML payload)
    'django.middleware.gzip.GZipMiddleware',
    # 🟢 ConditionalGetMiddleware — ส่ง 304 Not Modified เมื่อ ETag/Last-Modified ตรง
    'django.middleware.http.ConditionalGetMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 🟢 Sync Supabase JWT → Django User (วางหลัง AuthenticationMiddleware)
    'pet_core.middleware.SupabaseAuthMiddleware',
]

# ─────────────────────────────────────────
# Cache framework — local memory (free, no Redis needed)
# ─────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pf-default',
        'TIMEOUT': 60,
        'OPTIONS': {'MAX_ENTRIES': 1000},
    }
}

ROOT_URLCONF = 'petfinder_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # 🟢 inject SUPABASE_URL / SUPABASE_ANON_KEY ลงทุก template
                'pet_core.context_processors.supabase_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'petfinder_site.wsgi.application'

# 3. ตั้งค่า Database เชื่อมกับ Supabase
# Production (Render): ใช้ DATABASE_URL string ตัวเดียว
# Local dev: ใช้ DB_NAME/USER/PASSWORD/HOST/PORT แยก
import dj_database_url
DATABASE_URL = env('DATABASE_URL', '')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', 'postgres'),
            'USER': env('DB_USER', required=True),
            'PASSWORD': env('DB_PASSWORD', required=True),
            'HOST': env('DB_HOST', required=True),
            'PORT': env('DB_PORT', '6543'),
        }
    }

# 4. ตั้งค่ารหัสผ่านและภาษา
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'th'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 5. ตั้งค่าไฟล์ Static (CSS, JS)
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')   # collectstatic target
# WhiteNoise compressed + cached static files (production)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# CSRF trusted origins สำหรับ Render
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ======================
# 🛡️ Security headers (production-grade)
# ======================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'SAMEORIGIN'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

if not DEBUG:
    # HTTPS-only (เปิดเฉพาะ production)
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# WhiteNoise: cache static อย่างหนักหน่วง (immutable hash filename)
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year

# Auth
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# =========================================================
# 6. 🟢 ตั้งค่าดึงรูปภาพจาก Supabase Cloud Storage (S3-compatible)
# =========================================================
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', required=True)
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', required=True)
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', 'pet-images')
AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', required=True)
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_FILE_OVERWRITE = True       # ป้องกัน HeadObject 400 จาก Supabase
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False        # ใช้ public URL ไม่มี signed query string
AWS_S3_ADDRESSING_STYLE = 'path'   # path-style สำหรับ Supabase S3-compatible

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        # WhiteNoise: gzip + brotli + manifest (cache-busting via hash)
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# 🟢 Supabase public URLs (ใช้ใน template + frontend)
SUPABASE_URL = env('SUPABASE_URL', required=True)
SUPABASE_ANON_KEY = env('SUPABASE_ANON_KEY', required=True)

# URL สำหรับแสดงรูปสาธารณะ
MEDIA_URL = f'{SUPABASE_URL}/storage/v1/object/public/{AWS_STORAGE_BUCKET_NAME}/'
