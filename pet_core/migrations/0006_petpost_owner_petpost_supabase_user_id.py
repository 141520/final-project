from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pet_core', '0005_petpost_image_alter_petimage_table_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='petpost',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pet_posts',
                to=settings.AUTH_USER_MODEL,
                verbose_name='ผู้ประกาศ',
            ),
        ),
        migrations.AddField(
            model_name='petpost',
            name='supabase_user_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                null=True,
                verbose_name='Supabase UUID',
            ),
        ),
    ]
