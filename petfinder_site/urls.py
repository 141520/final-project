from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

# Inline SVG favicon — เลี่ยง 404 ที่ browser ขออัตโนมัติ
FAVICON_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    b'<text y=".9em" font-size="90">\xf0\x9f\x90\xbe</text></svg>'
)
def favicon(_request):
    return HttpResponse(FAVICON_SVG, content_type='image/svg+xml')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', favicon),
    path('', include('pet_core.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)