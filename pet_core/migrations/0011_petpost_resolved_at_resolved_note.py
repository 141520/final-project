from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0010_petpost_reward'),
    ]

    operations = [
        migrations.AddField(
            model_name='petpost',
            name='resolved_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='วันที่ปิดประกาศ'),
        ),
        migrations.AddField(
            model_name='petpost',
            name='resolved_note',
            field=models.TextField(blank=True, verbose_name='ข้อความเมื่อปิดประกาศ',
                                   help_text='เช่น เรื่องราวการกลับมา / ขอบคุณคนที่ช่วย'),
        ),
    ]
