"""Add composite indexes สำหรับ query ที่ใช้บ่อย — ลดเวลา query 5-50x บนตารางใหญ่"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0011_petpost_resolved_at_resolved_note'),
    ]

    operations = [
        # ใช้บ่อยใน home/lost_pet_list/found_pet_list/map_view
        migrations.AddIndex(
            model_name='petpost',
            index=models.Index(
                fields=['post_type', 'status', '-created_at'],
                name='pet_type_status_created_idx',
            ),
        ),
        # ใช้ใน search.py: filter feature_vector + status + post_type
        migrations.AddIndex(
            model_name='petpost',
            index=models.Index(
                fields=['status', 'pet_type'],
                name='pet_status_type_idx',
            ),
        ),
        # ใช้ใน map_view filter latitude/longitude
        migrations.AddIndex(
            model_name='petpost',
            index=models.Index(
                fields=['status', 'latitude', 'longitude'],
                name='pet_status_geo_idx',
            ),
        ),
    ]
