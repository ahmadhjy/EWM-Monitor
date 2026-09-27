from datetime import timedelta
from bs4 import BeautifulSoup
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone, translation
from .models import Article, Category, SiteSettings
from .templatetags.content_extras import archive_content


class EditorialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.news = Category.objects.create(name="News & Analysis", name_ar="الأخبار والتحليلات", slug="latest-news-and-analysis")
        cls.market = Category.objects.create(name="Gold Forecast", name_ar="توقعات الذهب", slug="gold-forecast", body="<p>English guide</p>")
        cls.education = Category.objects.create(name="Education", slug="education", nav_group="education")
        cls.stamp = timezone.now() - timedelta(days=1)
        for index in range(7):
            Article.objects.create(title=f"Forecast {index}", title_ar=f"توقع {index}", slug=f"forecast-{index}", category=cls.market, status="published", published_at=cls.stamp, body=f'<h1 id="outlook">Outlook</h1><p>Complete body {index}</p><a href="#outlook">Jump</a>', body_ar=f"<p>تحليل كامل {index}</p>")
        cls.report = Article.objects.create(title="News lead", title_ar="خبر رئيسي", body="<p>News</p>", body_ar="<p>خبر</p>", slug="news-lead", category=cls.news, status="published")
        cls.lesson = Article.objects.create(title="Education lesson", body="<p>Lesson</p>", slug="lesson", category=cls.education, status="published")
        Article.objects.create(title="Future report", body="<p>Not yet</p>", slug="future-report", category=cls.news, status="published", published_at=timezone.now() + timedelta(days=1))

    def test_home_sections_use_only_their_categories(self):
        response = self.client.get("/en/")
        self.assertEqual(response.context["featured"], self.report)
        self.assertEqual(len(response.context["forecasts"]), 7)
        self.assertEqual(list(response.context["education_articles"]), [self.lesson])
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertNotIn("Forecast", soup.select_one(".news-gallery").get_text())
        self.assertNotIn("News lead", soup.select_one(".latest-forecasts").get_text())
        self.assertNotContains(response, "Future report")
        self.assertNotContains(self.client.get("/"), "Education lesson")
        self.assertNotContains(response, 'class="hero"')

    def test_archive_full_content_and_stable_pagination(self):
        seen = []
        for number in range(1, 5):
            response = self.client.get(f"/en/gold-forecast/?page={number}")
            self.assertEqual(response.status_code, 200)
            page_ids = [entry.pk for entry in response.context["articles"]]
            seen.extend(page_ids)
            soup = BeautifulSoup(response.content, "html.parser")
            self.assertEqual(len(soup.select("h1")), 1)
            self.assertEqual(len(soup.select("[data-archive-entry]")), len(page_ids))
            self.assertIn("Complete body", soup.select_one(".archive-entry__body").get_text())
            canonical = soup.select_one('link[rel="canonical"]')["href"]
            self.assertTrue(canonical.endswith(f"?page={number}" if number > 1 else "/en/gold-forecast/"))
            if number < 4:
                self.assertEqual(soup.select_one('[data-archive-next]')["href"], f"?page={number + 1}")
        self.assertEqual(len(seen), 7)
        self.assertEqual(len(set(seen)), 7)
        for invalid in ("0", "-1", "five", "999"):
            self.assertEqual(self.client.get(f"/en/gold-forecast/?page={invalid}").status_code, 404)

    def test_guide_languages_are_independent_and_optional(self):
        self.assertContains(self.client.get("/en/gold-forecast/"), 'id="market-guide"')
        self.assertNotContains(self.client.get("/gold-forecast/"), 'id="market-guide"')
        self.market.body_ar = "<p><br></p>"
        self.market.save()
        self.assertNotContains(self.client.get("/gold-forecast/"), 'id="market-guide"')
        self.market.body_ar = "<p>دليل السوق</p>"
        self.market.save()
        self.assertContains(self.client.get("/gold-forecast/"), 'id="market-guide"')
        self.assertNotContains(self.client.get("/gold-forecast/"), "English guide")

    def test_archive_namespaces_headings_and_inline_anchors(self):
        with translation.override("en"):
            html = archive_content('<h1 id="intro">Title</h1><a href="#intro">Jump</a><img src="/media/chart.png">', 42)
        self.assertIn('<h3 id="archive-42-intro">', html)
        self.assertIn('href="#archive-42-intro"', html)
        self.assertIn('loading="lazy"', html)

    def test_secondary_navigation_and_socials(self):
        settings = SiteSettings.load()
        settings.telegram_url = "https://t.me/testewm"
        settings.save()
        soup = BeautifulSoup(self.client.get("/en/").content, "html.parser")
        top = soup.select_one(".signal-bar")
        self.assertEqual(len(top.select(".market-watch a")), 5)
        self.assertIn("https://t.me/testewm", [a["href"] for a in top.select("a")])
        self.assertNotIn("Privacy", top.get_text())
        self.assertIn("Privacy policy", soup.select_one("footer").get_text())

    def test_imported_archive_canonical_uses_current_language_route(self):
        self.market.legacy_id = 999
        self.market.canonical_url = "https://elliottwavemonitor.com/category/gold-forecast/"
        self.market.save()
        response = self.client.get("/en/gold-forecast/")
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertTrue(soup.select_one('link[rel="canonical"]')["href"].endswith("/en/gold-forecast/"))

    def test_editor_guide_fields_and_admin_remain_english(self):
        user = get_user_model().objects.create_superuser(username="editor-test", password="test-password-only")
        self.client.force_login(user)
        response = self.client.get(f"/admin/content/category/{self.market.pk}/change/")
        self.assertEqual(response.status_code, 200)
        for label in ("English archive title", "Arabic archive title", "English market guide (optional)", "Arabic market guide (optional)"):
            self.assertContains(response, label)
        self.assertContains(response, 'lang="en"')
        self.assertNotContains(response, '<html lang="ar"')
