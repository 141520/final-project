from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
import os

from pet_core.sitemaps import SITEMAPS

# ───── Inline SVG favicon ─────
FAVICON_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    b'<text y=".9em" font-size="90">\xf0\x9f\x90\xbe</text></svg>'
)
def favicon(_request):
    return HttpResponse(FAVICON_SVG, content_type='image/svg+xml')


# ───── robots.txt ─────
@require_GET
def robots_txt(_request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /logout/",
        "Disallow: /pet/*/edit/",
        "Disallow: /pet/*/delete/",
        "Allow: /",
        "",
        "Sitemap: /sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


# ───── PWA Service Worker (must be at root scope) ─────
@require_GET
@cache_control(no_cache=True, max_age=0)
def service_worker(_request):
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    try:
        with open(sw_path, 'rb') as f:
            content = f.read()
    except FileNotFoundError:
        content = b'// sw missing'
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


# ───── PWA manifest (root-served for compatibility) ─────
@require_GET
def manifest(_request):
    mf_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.webmanifest')
    try:
        with open(mf_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='application/manifest+json')
    except FileNotFoundError:
        return HttpResponse('{}', content_type='application/manifest+json')


from pet_core.views import admin_stats_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/stats/', admin_stats_api, name='admin_stats_api'),
    path('favicon.ico', favicon),
    path('robots.txt', robots_txt),
    path('sw.js', service_worker),
    path('manifest.webmanifest', manifest),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('pet_core.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
