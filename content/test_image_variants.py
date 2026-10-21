from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from PIL import Image

from content.image_variants import featured_source_name, generate_featured_variants
from content.models import Article, Category


class FeaturedVariantTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.override = self.settings(MEDIA_ROOT=self.temp.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.category = Category.objects.create(name="News", slug="news")

    def upload(self):
        buffer = BytesIO()
        Image.new("RGB", (1200, 800), "navy").save(buffer, "PNG")
        return SimpleUploadedFile("news.png", buffer.getvalue(), content_type="image/png")

    def test_upload_generates_sizes_and_keeps_original(self):
        upload = self.upload()
        original = upload.read()
        upload.seek(0)
        article = Article.objects.create(title="News", slug="news", category=self.category, featured_image=upload)
        with article.featured_image.open("rb") as source:
            self.assertEqual(source.read(), original)
        self.assertTrue(article.card_image_url.endswith(".card-hq.webp"))
        self.assertTrue(article.article_mobile_image_url.endswith(".article-mobile.webp"))
        self.assertTrue(article.article_desktop_image_url.endswith(".article-desktop.webp"))
        for variant in ("article-mobile", "article-desktop"):
            name = article.featured_image.name.rsplit(".", 1)[0] + f".{variant}.webp"
            with default_storage.open(name, "rb") as source, Image.open(source) as image:
                self.assertFalse(image.info.get("lossless", False))
        for variant, size in [("mobile-hq", (480, 285)), ("card-hq", (960, 570))]:
            name = article.featured_image.name.rsplit(".", 1)[0] + f".{variant}.webp"
            with default_storage.open(name) as source, Image.open(source) as image:
                self.assertEqual(image.size, size)
        self.assertEqual(generate_featured_variants(article.featured_image.name), 0)

    def test_backfill_changes_no_editorial_fields(self):
        with patch("content.image_variants.generate_featured_variants"):
            article = Article.objects.create(title="News", slug="news", category=self.category, body="Original body", featured_image=self.upload())
        before = Article.objects.filter(pk=article.pk).values().get()
        call_command("generate_featured_variants", stdout=StringIO())
        self.assertEqual(before, Article.objects.filter(pk=article.pk).values().get())
        self.assertTrue(article.mobile_image_url.endswith(".mobile-hq.webp"))

    def test_missing_or_invalid_images_fail_safely(self):
        self.assertEqual(generate_featured_variants("missing.png"), 0)
        name = default_storage.save("invalid.png", SimpleUploadedFile("invalid.png", b"invalid"))
        with self.assertLogs("content.image_variants", level="ERROR"):
            self.assertEqual(generate_featured_variants(name), 0)

    def test_media_library_url_is_optimized(self):
        name = default_storage.save("library/news.png", self.upload())
        article = Article.objects.create(title="News", slug="news", category=self.category, featured_image_url="/media/" + name)
        self.assertTrue(article.card_image_url.endswith(".card-hq.webp"))
        self.assertEqual(featured_source_name(article), name)

    def test_external_urls_and_traversal_are_not_read(self):
        for url in ["https://other.example/media/image.png", "/media/../secret.png", "/media/%2e%2e/secret.png"]:
            article = Article(featured_image_url=url)
            self.assertEqual(featured_source_name(article), "")
