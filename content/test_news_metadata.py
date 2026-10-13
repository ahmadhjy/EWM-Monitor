from importlib import import_module
from types import SimpleNamespace

from bs4 import BeautifulSoup
from django.apps import apps
from django.db import connection
from django.test import TestCase

from content.models import Category


class NewsMetadataTests(TestCase):
    def apply_update(self):
        import_module("content.migrations.0013_news_archive_description").fill_news_description(
            apps, SimpleNamespace(connection=connection),
        )

    def test_news_description_differs_from_home_and_preserves_arabic(self):
        news = Category.objects.create(slug="latest-news-and-analysis", name="News & Analysis", meta_description_ar="Arabic editorial description")
        self.apply_update()
        self.apply_update()
        news.refresh_from_db()
        self.assertEqual(news.meta_description_ar, "Arabic editorial description")
        home = BeautifulSoup(self.client.get("/en/").content, "html.parser")
        archive = BeautifulSoup(self.client.get("/en/latest-news-and-analysis/").content, "html.parser")
        self.assertEqual(archive.select_one('meta[name="description"]')["content"], news.meta_description)
        self.assertNotEqual(home.select_one('meta[name="description"]')["content"], news.meta_description)
        self.assertTrue(news.meta_description)

    def test_existing_editor_description_is_not_overwritten(self):
        news = Category.objects.create(slug="latest-news-and-analysis", name="News", meta_description="Custom editorial description")
        self.apply_update()
        news.refresh_from_db()
        self.assertEqual(news.meta_description, "Custom editorial description")

    def test_existing_short_description_is_not_overwritten(self):
        news = Category.objects.create(slug="latest-news-and-analysis", name="News", short_description="Custom archive summary")
        self.apply_update()
        news.refresh_from_db()
        self.assertEqual(news.meta_description, "")
        self.assertEqual(news.short_description, "Custom archive summary")
