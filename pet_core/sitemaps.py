"""Sitemaps สำหรับ SEO — ให้ Google index ได้ครบ"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import PetPost, BlogPost, Product


class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home', 'lost_pet_list', 'found_pet_list', 'map_view',
                'search_pet', 'product_list', 'blog_list']

    def location(self, item):
        return reverse(item)


class PetPostSitemap(Sitemap):
    priority = 0.9
    changefreq = 'daily'
    limit = 5000

    def items(self):
        return PetPost.objects.filter(status='active').only('id', 'updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/pet/{obj.id}/'


class BlogSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        return BlogPost.objects.filter(is_published=True).only('id', 'updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/blog/{obj.id}/'


class ProductSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return Product.objects.filter(is_active=True).only('id', 'updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/product/{obj.id}/'


SITEMAPS = {
    'static': StaticSitemap,
    'pets': PetPostSitemap,
    'blog': BlogSitemap,
    'products': ProductSitemap,
}
