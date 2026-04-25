from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0009_product_price_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='petpost',
            name='reward',
            field=models.DecimalField(
                max_digits=10, decimal_places=2, null=True, blank=True,
                verbose_name='รางวัล (บาท)',
                help_text='ระบุจำนวนเงินรางวัลถ้ามี (ไม่บังคับ)',
            ),
        ),
    ]
