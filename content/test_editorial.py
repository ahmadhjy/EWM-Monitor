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

    def test_news_gallery_has_twenty_stories_and_standard_pagination(self):
        for index in range(22):
            Article.objects.create(title=f"News {index}", title_ar=f"خبر {index}", slug=f"news-{index}", body="<p>News article body</p>", body_ar="<p>نص الخبر</p>", category=self.news, status="published", published_at=self.stamp)
        for prefix in ("/", "/en/"):
            response = self.client.get(prefix + "latest-news-and-analysis/")
            soup = BeautifulSoup(response.content, "html.parser")
            self.assertEqual(len(soup.select(".news-lead")), 1)
            self.assertEqual(len(soup.select(".news-small")), 19)
            self.assertEqual(len(soup.select(".latest-forecasts")), 1)
            self.assertEqual(len(soup.select("h1")), 1)
            self.assertEqual(soup.select_one('.news-pagination [rel="next"]')["href"], "?page=2")
            self.assertNotContains(response, "data-archive-feed")
            self.assertNotContains(response, "js/archive.js")
            self.assertNotContains(response, "News article body")
            second = self.client.get(prefix + "latest-news-and-analysis/?page=2")
            second_soup = BeautifulSoup(second.content, "html.parser")
            self.assertEqual(len(second_soup.select(".news-lead, .news-small")), 3)
            self.assertTrue(second_soup.select_one('link[rel="canonical"]')["href"].endswith("?page=2"))
            first_ids = {article.pk for article in response.context["articles"]}
            second_ids = {article.pk for article in second.context["articles"]}
            self.assertFalse(first_ids & second_ids)
            self.assertEqual(self.client.get(prefix + "latest-news-and-analysis/?page=3").status_code, 404)
        self.assertEqual(len(self.client.get("/en/gold-forecast/").context["articles"]), 2)
        self.assertContains(self.client.get("/en/gold-forecast/"), "data-archive-feed")

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

    def test_shared_sidebar_subscription_removal_and_forecast_sections(self):
        for route in ('/', '/en/', '/en/gold-forecast/', '/en/news-lead/', '/en/education/', '/en/latest-news-and-analysis/', '/en/search/?q=gold', '/en/contact-us/'):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, route)
            soup = BeautifulSoup(response.content, 'html.parser')
            self.assertEqual(len(soup.select('aside.site-sidebar')), 1, route)
            self.assertFalse(soup.select('.newsletter-form, .newsletter-section, [data-guide-jump], .news-kicker'))
            self.assertTrue(soup.select('.forecast-meta time'))
        self.assertContains(self.client.get('/en/gold-forecast/'), 'class="archive-entry"')

    def test_uploaded_logo_is_used_and_updates_without_code_changes(self):
        settings = SiteSettings.load()
        for filename in ('branding/client-logo.png', 'branding/revised-logo.png', 'branding/lOGO-SVG.gif'):
            settings.logo.name = filename
            settings.save()
            soup = BeautifulSoup(self.client.get('/en/').content, 'html.parser')
            for selector in ('.brand__logo--header', '.brand__logo--footer'):
                self.assertTrue(soup.select_one(selector)['src'].endswith(filename))
                self.assertIn('brand-logo-frame', soup.select_one(selector).parent.get('class'))

    def test_word_language_menu_and_mobile_menu_contents(self):
        soup = BeautifulSoup(self.client.get('/en/').content, 'html.parser')
        self.assertEqual([link.get('hreflang') for link in soup.select('.language-menu nav a')], ['ar', 'en'])
        self.assertFalse(soup.select('.language-menu img'))
        nav = soup.select_one('[data-navigation]')
        self.assertIn('mobile-menu-search', nav.find(recursive=False).get('class'))
        self.assertTrue(nav.select('.mobile-menu-socials'))
        self.assertIn('Trending:', soup.select_one('.market-watch').get_text())

    def test_footer_logo_is_independent_and_preserves_fallback(self):
        settings = SiteSettings.load()
        settings.logo.name = 'branding/client-logo.png'
        for filename in ('branding/footer/white-logo.png', 'branding/footer/revised-logo.webp'):
            settings.footer_logo.name = filename
            settings.save()
            for route in ('/', '/en/'):
                soup = BeautifulSoup(self.client.get(route).content, 'html.parser')
                self.assertTrue(soup.select_one('.brand__logo--header')['src'].endswith('branding/client-logo.png'))
                self.assertTrue(soup.select_one('.brand__logo--footer')['src'].endswith(filename))
                frame = soup.select_one('.brand-logo-frame--footer')
                self.assertIn('has-custom-logo', frame['class'])
                self.assertNotIn('is-uploaded', frame['class'])
        settings.footer_logo = ''
        settings.save()
        soup = BeautifulSoup(self.client.get('/en/').content, 'html.parser')
        self.assertTrue(soup.select_one('.brand__logo--footer')['src'].endswith('branding/client-logo.png'))
        settings.logo = ''
        settings.save()
        soup = BeautifulSoup(self.client.get('/en/').content, 'html.parser')
        self.assertTrue(soup.select_one('.brand__logo--footer')['src'].endswith('img/ewm-original.svg'))

    def test_footer_logo_field_is_available_in_english_admin(self):
        user = get_user_model().objects.create_superuser(username='footer-editor', password='test-password-only')
        self.client.force_login(user)
        settings = SiteSettings.load()
        response = self.client.get(f'/admin/content/sitesettings/{settings.pk}/change/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="footer_logo"')
        self.assertContains(response, 'Footer logo')
        self.assertContains(response, 'lang="en"')

    def test_home_education_limit_and_standard_education_archive(self):
        for index in range(23):
            Article.objects.create(title=f'Lesson {index}', slug=f'lesson-{index}', category=self.education, status='published', body='<p>Complete lesson content</p>')
        home = self.client.get('/en/')
        self.assertEqual(len(home.context['education_articles']), 3)
        soup = BeautifulSoup(home.content, 'html.parser')
        self.assertEqual(len(soup.select('.home-education .article-card')), 3)
        response = self.client.get('/en/education/')
        self.assertEqual(len(response.context['articles']), 20)
        self.assertNotContains(response, 'data-archive-feed')
        self.assertNotContains(response, 'js/archive.js')
        self.assertNotContains(response, 'archive-entry__body')
        self.assertEqual(len(self.client.get('/en/education/?page=2').context['articles']), 4)
