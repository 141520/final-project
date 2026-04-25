from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0007_product_blogpost'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='scraped_price',
            field=models.DecimalField(
                max_digits=10, decimal_places=2, null=True, blank=True,
                verbose_name='ราคาจากหน้าร้าน (sync อัตโนมัติ)',
                help_text="ราคานี้จะถูก sync จาก external_link เมื่อกดปุ่ม 'Sync ราคา' — ถ้ามีจะโชว์แทน price",
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='last_scraped_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='sync ราคาล่าสุด'),
        ),
        migrations.AlterField(
            model_name='product',
            name='external_link',
            field=models.URLField(
                max_length=500, blank=True,
                verbose_name='ลิงก์ไปร้านค้า',
                help_text="วางลิงก์สินค้าจาก Shopee / Lazada / Facebook ฯลฯ ผู้ใช้จะกด 'ดูสินค้า' แล้วไปที่ลิงก์นี้",
            ),
        ),
    ]
