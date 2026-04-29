"""
สร้าง superuser อัตโนมัติจาก env vars (idempotent — ไม่ซ้ำถ้ามีอยู่แล้ว)
ใช้ใน build.sh:
    python manage.py ensure_superuser

Required env vars:
    DJANGO_SUPERUSER_USERNAME
    DJANGO_SUPERUSER_PASSWORD
    DJANGO_SUPERUSER_EMAIL (optional)

ถ้า env ไม่ครบ จะข้าม (ไม่ raise error → build ไม่พัง)
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Ensure a superuser exists from env vars (idempotent)"

    def handle(self, *args, **opts):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                '[ensure_superuser] DJANGO_SUPERUSER_USERNAME/PASSWORD ไม่ได้ตั้ง — ข้าม'
            ))
            return

        u, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_staff': True, 'is_superuser': True},
        )

        # Always update password + flags (กันกรณี user มีแต่ flag ผิด)
        u.is_staff = True
        u.is_superuser = True
        if email and not u.email:
            u.email = email
        u.set_password(password)
        u.save()

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'[ensure_superuser] ✅ สร้าง superuser "{username}" สำเร็จ'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'[ensure_superuser] ✅ อัปเดตรหัสผ่าน superuser "{username}"'
            ))
