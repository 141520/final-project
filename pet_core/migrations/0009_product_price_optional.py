from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0008_product_scraped_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(
                max_digits=10, decimal_places=2, null=True, blank=True,
                verbose_name='ราคาตั้ง (บาท) — ไม่บังคับ',
                help_text="ไม่ต้องใส่ก็ได้ถ้าจะใช้ 'Sync ราคา' จาก external_link แทน",
            ),
        ),
    ]
