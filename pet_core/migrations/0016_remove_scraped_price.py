from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0015_blogpost_source'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='scraped_price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='last_scraped_at',
        ),
    ]
