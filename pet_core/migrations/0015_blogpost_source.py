from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0014_productimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='source_name',
            field=models.CharField(
                blank=True, max_length=200,
                verbose_name='แหล่งที่มา (ชื่อ)',
                help_text='เช่น: สัตวแพทย์ ดร.สมชาย / เว็บไซต์ petmd.com',
            ),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='source_url',
            field=models.URLField(
                blank=True, max_length=500,
                verbose_name='ลิงก์แหล่งที่มา',
                help_text='URL ของเว็บไซต์ต้นฉบับ (ถ้ามี)',
            ),
        ),
    ]
