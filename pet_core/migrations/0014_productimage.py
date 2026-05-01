from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0013_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('image', models.ImageField(upload_to='products/', verbose_name='รูปสินค้า')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='ลำดับ (น้อย→มาก่อน)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='extra_images', to='pet_core.product')),
            ],
            options={
                'db_table': 'pet_core_productimage',
                'ordering': ['sort_order', 'id'],
                'verbose_name': 'รูปสินค้า (เสริม)',
                'verbose_name_plural': 'รูปสินค้า (เสริม)',
            },
        ),
    ]
