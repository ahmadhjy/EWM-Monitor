import base64
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.core import mail
from django.urls import reverse

from .models import Article, Category, ContactMessage, MediaAsset, NewsletterSubscriber, Page, SiteSettings


class PublicSiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.category = Category.objects.create(
            name="Gold Forecast",
            name_ar="توقعات الذهب",
            slug="gold-forecast",
            body="<h2>What is gold forecasting?</h2><p>Evergreen market guide.</p>",
            body_ar="<h2>ما هي توقعات الذهب؟</h2><p>دليل دائم للسوق.</p>",
        )
        cls.article = Article.objects.create(
            title="Gold Elliott Wave Update",
            title_ar="تحليل الذهب بموجات إليوت",
            slug="gold-elliott-wave-update",
            excerpt="A concise market update.",
            excerpt_ar="تحديث موجز لتحليل سوق الذهب.",
            body="<p>Analysis body.</p>",
            body_ar="<p>نص تحليل الذهب.</p>",
            category=cls.category,
            status="published",
        )
        cls.education_category = Category.objects.create(
            name="Education",
            name_ar="التعليم",
            slug="education",
            nav_group="education",
        )
        cls.english_only_article = Article.objects.create(
            title="English Education Guide",
            slug="english-education-guide",
            body="<p>English education content.</p>",
            category=cls.education_category,
            status="published",
        )
        cls.page = Page.objects.create(
            title="Privacy Policy",
            title_ar="سياسة الخصوصية",
            slug="privacy-policy",
            body="<p>Policy</p>",
            body_ar="<p>السياسة</p>",
        )

    def test_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title_ar)
        self.assertContains(response, 'lang="ar" dir="rtl"')
        self.assertContains(response, 'hreflang="ar"')
        self.assertContains(response, 'hreflang="en"')
        self.assertContains(response, "🇬🇧")
        self.assertNotContains(response, self.english_only_article.title)

    def test_english_version_uses_prefixed_urls_and_ltr_layout(self):
        response = self.client.get("/en/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="en" dir="ltr"')
        self.assertContains(response, self.article.title)
        self.assertContains(response, self.english_only_article.title)
        self.assertContains(response, "🇸🇦")
        self.assertContains(response, "img/flag-sa.webp")

    def test_hero_keeps_animation_without_manual_controls(self):
        arabic = self.client.get("/")
        english = self.client.get("/en/")
        for response in (arabic, english):
            self.assertContains(response, 'class="chart-signal"')
            self.assertContains(response, "data-hero-motion")
            self.assertNotContains(response, "data-hero-motion-toggle")
            self.assertNotContains(response, "Pause animation")
            self.assertNotContains(response, "Resume animation")

    def test_article_detail(self):
        response = self.client.get(f"/{self.article.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "application/ld+json")
        self.assertContains(response, self.article.title_ar)
        self.assertContains(response, "نص تحليل الذهب.")

    def test_english_only_article_is_not_published_on_arabic_routes(self):
        self.assertEqual(self.client.get(f"/{self.english_only_article.slug}/").status_code, 404)
        english_response = self.client.get(f"/en/{self.english_only_article.slug}/")
        self.assertEqual(english_response.status_code, 200)
        self.assertContains(english_response, "English education content.")
        self.assertNotContains(english_response, '<link rel="alternate" hreflang="ar"')

    def test_category_detail(self):
        response = self.client.get(f"/{self.category.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title_ar)
        self.assertContains(response, "ما هي توقعات الذهب؟")

        english_response = self.client.get(f"/en/{self.category.slug}/")
        self.assertContains(english_response, "What is gold forecasting?")

    def test_high_resolution_variant_urls(self):
        from unittest.mock import patch
        self.article.featured_image.name = "articles/example.png"
        with patch("content.models.default_storage.exists", return_value=True):
            self.assertTrue(self.article.hero_image_url.endswith(".hero-hq.webp"))
            self.assertTrue(self.article.card_image_url.endswith(".card-hq.webp"))
        with patch("content.models.default_storage.exists", return_value=False):
            self.assertTrue(self.article.hero_image_url.endswith("example.png"))

    def test_page_detail(self):
        response = self.client.get(f"/{self.page.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سياسة الخصوصية")

        english_response = self.client.get(f"/en/{self.page.slug}/")
        self.assertContains(english_response, "Privacy Policy")

    def test_seo_endpoints(self):
        self.assertEqual(self.client.get("/robots.txt").status_code, 200)
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        self.assertEqual(self.client.get("/llms.txt").status_code, 200)

    def test_article_defaults_generate_excerpt_and_author(self):
        article = Article.objects.create(
            title="Automatic editorial defaults",
            slug="automatic-editorial-defaults",
            body="<p>One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen.</p>",
            body_ar="<p>واحد اثنان ثلاثة أربعة خمسة ستة سبعة ثمانية تسعة عشرة أحد عشر اثنا عشر ثلاثة عشر أربعة عشر خمسة عشر ستة عشر.</p>",
            category=self.category,
        )
        self.assertEqual(article.author_name, "EWM Team")
        self.assertEqual(
            article.excerpt,
            "One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen…",
        )
        self.assertTrue(article.excerpt_ar.endswith("…"))
        self.assertLessEqual(len(article.seo_description), 160)

    @override_settings(SITE_INDEXING_ENABLED=False)
    def test_ip_preview_is_consistently_noindex(self):
        response = self.client.get("/")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertContains(response, '<meta name="robots" content="noindex,nofollow')
        self.assertContains(self.client.get("/robots.txt"), "Disallow: /")

    def test_inline_links_follow_available_language_editions(self):
        from django.utils import translation
        from .templatetags.content_extras import localized_content
        html = '<a href="https://elliottwavemonitor.com/english-education-guide/">Guide</a>'
        with translation.override("en"):
            self.assertIn('href="/en/english-education-guide/"', localized_content(html))
        with translation.override("ar"):
            result = localized_content(html)
            self.assertIn('href="/en/english-education-guide/"', result)
            self.assertIn('hreflang="en"', result)

    def test_feeds_and_sitemap_do_not_advertise_missing_translations(self):
        from xml.etree import ElementTree
        self.assertNotContains(self.client.get("/feed/"), self.english_only_article.title)
        self.assertContains(self.client.get("/en/feed/"), self.english_only_article.title)
        tree = ElementTree.fromstring(self.client.get("/sitemap.xml").content)
        locations = [node.text for node in tree.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertEqual(len(locations), len(set(locations)))
        self.assertFalse(any(url.endswith("/english-education-guide/") and "/en/" not in url for url in locations))


class AdminMediaPickerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_directory = TemporaryDirectory()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_directory.name)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        cls.media_directory.cleanup()

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="editor",
            email="editor@example.com",
            password="test-password",
        )
        cls.asset = MediaAsset.objects.create(
            title="EUR USD chart",
            source_url="https://example.com/chart.png",
            alt_text="EUR USD Elliott Wave chart",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_admin_stays_english_and_exposes_translation_fields(self):
        self.client.cookies["django_language"] = "ar"
        response = self.client.get("/admin/content/article/add/", HTTP_ACCEPT_LANGUAGE="ar")
        self.assertContains(response, 'lang="en"')
        self.assertNotContains(response, '<html lang="ar"')
        self.assertContains(response, "Arabic translation")
        self.assertContains(response, 'name="title_ar"')
        self.assertContains(response, 'name="body_ar"')
        self.assertContains(response, "Newsletter subscribers")

    def test_picker_lists_and_searches_library(self):
        response = self.client.get(reverse("admin:content_mediaasset_picker"), {"q": "EUR"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["id"], self.asset.pk)

    def test_picker_uploads_image_with_alt_text(self):
        image = SimpleUploadedFile(
            "chart.gif",
            base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="),
            content_type="image/gif",
        )
        response = self.client.post(
            reverse("admin:content_mediaasset_picker_upload"),
            {"title": "Uploaded chart", "alt_text": "Wave count chart", "file": image},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["item"]["alt_text"], "Wave count chart")

    def test_picker_updates_alt_text(self):
        response = self.client.post(
            reverse("admin:content_mediaasset_picker_alt", args=[self.asset.pk]),
            {"alt_text": "Updated accessible description"},
        )
        self.assertEqual(response.status_code, 200)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.alt_text, "Updated accessible description")


class PublicFormSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        settings_obj = SiteSettings.load()
        settings_obj.contact_email = "elliottwavemonitor@gmail.com"
        settings_obj.save()

    def test_newsletter_saves_and_deduplicates_case_insensitively(self):
        first = self.client.post("/newsletter/subscribe/", {"email": "Reader@example.com", "next": "/"})
        second = self.client.post("/en/newsletter/subscribe/", {"email": "reader@EXAMPLE.COM", "next": "/en/"})
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)
        self.assertEqual(NewsletterSubscriber.objects.get().email, "reader@example.com")

    def test_newsletter_invalid_spam_and_external_redirects(self):
        self.client.post("/newsletter/subscribe/", {"email": "invalid"})
        self.client.post("/newsletter/subscribe/", {"email": "spam@example.com", "website": "spam"})
        self.assertFalse(NewsletterSubscriber.objects.exists())
        response = self.client.post("/newsletter/subscribe/", {"email": "reader@example.com", "next": "https://evil.example/"})
        self.assertEqual(response.url, "/")

    def test_forms_require_csrf(self):
        from django.test import Client
        protected_client = Client(enforce_csrf_checks=True)
        self.assertEqual(protected_client.post("/newsletter/subscribe/", {"email": "reader@example.com"}).status_code, 403)
        self.assertEqual(protected_client.post("/contact-us/", {}).status_code, 403)

    def test_contact_saved_without_email_delivery(self):
        response = self.client.post("/contact-us/", {"name": "Test Reader", "email": "reader@example.com", "subject": "A question", "message": "Hello from a reader."})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(CONTACT_EMAIL_NOTIFICATIONS=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_contact_optional_email_uses_configured_recipient(self):
        self.client.post("/en/contact-us/", {"name": "Reader", "email": "reader@example.com", "subject": "A question", "message": "Hello."})
        self.assertEqual(mail.outbox[0].to, ["elliottwavemonitor@gmail.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["reader@example.com"])
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_contact_honeypot_and_media_authentication(self):
        self.client.post("/contact-us/", {"name": "Bot", "email": "bot@example.com", "subject": "Spam", "message": "Spam", "website": "spam"})
        self.assertFalse(ContactMessage.objects.exists())
        response = self.client.get("/admin/content/mediaasset/picker/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)


class LegalPageImportTests(TestCase):
    def test_complete_bilingual_legal_pages_and_original_wording(self):
        from django.core.management import call_command
        from bs4 import BeautifulSoup
        call_command("populate_support_pages")
        privacy = Page.objects.get(slug="privacy-policy")
        terms = Page.objects.get(slug="terms-conditions")
        self.assertIn("March 15, 2022", privacy.body)
        self.assertIn("15 مارس 2022", privacy.body_ar)
        self.assertIn("providers will be liable in any way", terms.body)
        self.assertIn("سيتحملون المسؤولية", terms.body_ar)
        for item in (privacy, terms):
            english = BeautifulSoup(item.body, "html.parser")
            arabic = BeautifulSoup(item.body_ar, "html.parser")
            self.assertGreater(len(english.get_text().split()), 1500)
            self.assertGreater(len(arabic.get_text().split()), 1400)
            for tag in ("h2", "h3", "h4", "p", "li"):
                self.assertEqual(len(english.find_all(tag)), len(arabic.find_all(tag)))
            self.assertEqual(self.client.get(f"/{item.slug}/").status_code, 200)
            self.assertEqual(self.client.get(f"/en/{item.slug}/").status_code, 200)

    def test_import_does_not_overwrite_editor_changes_without_explicit_option(self):
        from django.core.management import call_command
        page = Page.objects.create(slug="privacy-policy", title="Privacy", body="<p>Editor changes.</p>")
        call_command("populate_support_pages")
        page.refresh_from_db()
        self.assertEqual(page.body, "<p>Editor changes.</p>")
        call_command("populate_support_pages", overwrite=True)
        page.refresh_from_db()
        self.assertIn("March 15, 2022", page.body)
