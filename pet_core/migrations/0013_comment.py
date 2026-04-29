from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0012_pet_indexes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('author_name', models.CharField(blank=True, max_length=80, verbose_name='ชื่อผู้แสดงความเห็น')),
                ('text', models.TextField(verbose_name='ข้อความ')),
                ('reaction', models.CharField(blank=True, max_length=8, verbose_name='รีแอ็กชัน')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pet_post', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='comments', to='pet_core.petpost')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'pet_core_comment',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['pet_post', '-created_at'], name='comment_post_created_idx')],
            },
        ),
    ]
