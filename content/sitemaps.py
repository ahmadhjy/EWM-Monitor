from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import Article, Category, Page


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    i18n = True
    alternates = True
    x_default = True

    def items(self):
        return Article.objects.filter(status="published", published_at__lte=timezone.now())

    def lastmod(self, obj):
        return obj.updated_at

    def get_languages_for_item(self, item):
        return ["ar", "en"] if item.has_arabic_translation else ["en"]


class CategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7
    i18n = True
    alternates = True
    x_default = True

    def items(self):
        return Category.objects.filter(is_visible=True)


class PageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5
    i18n = True
    alternates = True
    x_default = True

    def items(self):
        return Page.objects.filter(status="published", show_in_sitemap=True)

    def lastmod(self, obj):
        return obj.updated_at


class StaticSitemap(Sitemap):
    changefreq = "daily"
    priority = 1.0
    i18n = True
    alternates = True
    x_default = True

    def items(self):
        return ["home", "contact"]

    def location(self, item):
        return reverse(item)
