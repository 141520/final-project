from django.db import migrations, models


def seed_products_and_blog(apps, schema_editor):
    """ใส่สินค้า 12 ชิ้น + blog 3 อัน เริ่มต้นให้"""
    Product = apps.get_model('pet_core', 'Product')
    BlogPost = apps.get_model('pet_core', 'BlogPost')

    from datetime import date
    products = [
        ('ทรายแมวเต้าหู้ TOFUTOFU Premium', 'ปลอดภัย ไร้ฝุ่น',           299, 'hygiene'),
        ('Petcho โฟมอาบน้ำแห้ง',             'แชมพูแมว อ่อนโยน 400ml',     189, 'hygiene'),
        ('พรมดักทรายแมว',                    'ดักทรายจากเท้าแมว (-10%)',   159, 'hygiene'),
        ('TUBI ขนมขัดฟัน',                   'รูปกระดูกแปรงสีฟัน',          99, 'food'),
        ('Mili MiTag',                        'Bluetooth tracker 120ม',     590, 'gadget'),
        ('Digifounder Cat GPS Tracker',       'GPS ติดปลอกคอแมว',          1290, 'gadget'),
        ('ป้ายตามหาหมา แมว นก',              'ป้าย 100x100ซม',             250, 'other'),
        ('ROJECO เครื่องให้อาหารอัตโนมัติ',  'WiFi 4L',                   1490, 'gadget'),
        ('🐶 Salmon Oil 🐱',                   'น้ำมันปลาแซลมอน 100% Norway', 450, 'supplement'),
        ('PETBABYS Salmon Oil',               '250ML ลดขนร่วง',             390, 'supplement'),
        ('COUCOU VEV แมวเลีย',                'วิตามินไลซีน 14g',            39, 'supplement'),
        ('PARI Salmon Oil',                   'บำรุงสุขภาพ',                320, 'supplement'),
    ]

    for i, (name, desc, price, cat) in enumerate(products):
        Product.objects.create(
            name=name, description=desc, price=price, category=cat,
            amount_paid=50000, promotion_days=30, is_active=True,
            sort_order=i,
        )

    blogs = [
        ('10 Reasons to Help All Animals',  date(2024, 11, 22)),
        ('How to know your pet is hungry',  date(2024, 12, 2)),
        ('Best home for your pets',         date(2024, 11, 30)),
    ]
    for title, pub in blogs:
        BlogPost.objects.create(
            title=title, summary='', body='<p>บทความนี้ยังไม่มีเนื้อหา — แอดมินกรุณาแก้ไข</p>',
            published_at=pub, is_published=True,
        )


def unseed(apps, schema_editor):
    apps.get_model('pet_core', 'Product').objects.all().delete()
    apps.get_model('pet_core', 'BlogPost').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0006_petpost_owner_petpost_supabase_user_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='ชื่อสินค้า')),
                ('description', models.TextField(blank=True, verbose_name='รายละเอียด')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='ราคาขาย (บาท)')),
                ('category', models.CharField(
                    choices=[('food', 'อาหาร/ขนม'), ('toy', 'ของเล่น'),
                             ('hygiene', 'ของใช้/ความสะอาด'), ('gadget', 'อุปกรณ์/GPS/Tracker'),
                             ('supplement', 'อาหารเสริม/วิตามิน'), ('other', 'อื่นๆ')],
                    default='other', max_length=20, verbose_name='หมวดหมู่')),
                ('image', models.ImageField(blank=True, null=True, upload_to='products/', verbose_name='รูปสินค้า')),
                ('external_link', models.URLField(blank=True, max_length=500, verbose_name='ลิงก์ไปร้านค้า')),
                ('promoter_name', models.CharField(blank=True, max_length=200, verbose_name='ชื่อลูกค้า/ร้านค้า')),
                ('promoter_contact', models.CharField(blank=True, max_length=200, verbose_name='ช่องทางติดต่อ')),
                ('amount_paid', models.DecimalField(decimal_places=2, default=50000, max_digits=10,
                                                     verbose_name='ค่าโปรโมทที่จ่าย (บาท)')),
                ('promotion_days', models.PositiveIntegerField(default=30, verbose_name='จำนวนวันโปรโมท')),
                ('promotion_start', models.DateField(blank=True, null=True, verbose_name='วันที่เริ่มโปรโมท')),
                ('promotion_end', models.DateField(blank=True, null=True, verbose_name='วันที่สิ้นสุด')),
                ('is_active', models.BooleanField(default=True, verbose_name='แสดงบนเว็บ')),
                ('sort_order', models.IntegerField(default=0, verbose_name='ลำดับการแสดง (น้อยมาก่อน)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'สินค้าโปรโมท',
                'verbose_name_plural': 'สินค้าโปรโมท',
                'db_table': 'pet_core_product',
                'ordering': ['sort_order', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BlogPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=300, verbose_name='หัวข้อบทความ')),
                ('summary', models.CharField(blank=True, max_length=500, verbose_name='สรุปสั้น (แสดงใต้ title)')),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='blog/', verbose_name='รูปปก')),
                ('body', models.TextField(verbose_name='เนื้อหา (รองรับ HTML)')),
                ('author_name', models.CharField(blank=True, max_length=100, verbose_name='ผู้เขียน')),
                ('published_at', models.DateField(blank=True, null=True, verbose_name='วันที่เผยแพร่')),
                ('is_published', models.BooleanField(default=True, verbose_name='เผยแพร่บนเว็บ')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'บทความ/เคล็ดลับ',
                'verbose_name_plural': 'บทความ/เคล็ดลับ',
                'db_table': 'pet_core_blogpost',
                'ordering': ['-published_at', '-created_at'],
            },
        ),
        migrations.RunPython(seed_products_and_blog, reverse_code=unseed),
    ]
