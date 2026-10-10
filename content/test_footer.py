from importlib import import_module

from bs4 import BeautifulSoup
from django.apps import apps
from django.core.management import call_command
from django.test import TestCase
from django.utils import translation

from .models import Article, Category, MenuItem, SiteSettings


class FooterReleaseTests(TestCase):
    def setUp(self):
        call_command('configure_navigation', verbosity=0)

    def test_footer_uses_main_labels_without_tagline_or_email(self):
        settings = SiteSettings.load()
        settings.tagline = 'Footer tagline should not be rendered'
        settings.tagline_ar = 'عبارة يجب حذفها من التذييل'
        settings.contact_email = 'elliottwavemonitor@gmail.com'
        settings.save()
        for language, route in [('en','/en/'), ('ar','/')]:
            soup = BeautifulSoup(self.client.get(route).content, 'html.parser')
            footer = soup.select_one('.site-footer')
            with translation.override(language):
                expected = [item.display_label for item in MenuItem.objects.filter(group='primary',parent=None,is_active=True)]
            self.assertEqual([item.get_text(strip=True) for item in footer.select('.footer-menu-label')], expected)
            self.assertNotIn(settings.tagline, footer.get_text())
            self.assertNotIn(settings.tagline_ar, footer.get_text())
            self.assertNotIn(settings.contact_email, footer.get_text())
            self.assertFalse(footer.select('a[href^="mailto:"]'))
            self.assertEqual(footer.select_one('.brand__logo--footer')['width'], '240')
            self.assertTrue(footer.select('a[href$="privacy-policy/"]'))
            self.assertTrue(footer.select('a[href$="terms-conditions/"]'))
        self.assertContains(self.client.get('/en/contact-us/'), settings.contact_email)

    def test_unpublish_retains_articles_and_hides_archive(self):
        category = Category.objects.create(name='LTC/USD Forecast',name_ar='توقعات LTC/USD',slug='ltcusd-forecast',body='<p>Saved guide</p>')
        menu = MenuItem.objects.create(label='LTC/USD Forecast',url='/ltcusd-forecast/',parent=MenuItem.objects.get(label='Crypto Forecast',parent=None))
        article = Article.objects.create(title='Litecoin report', title_ar='تقرير لايتكوين', slug='litecoin-report',body='<p>Preserved analysis</p>',body_ar='<p>تحليل محفوظ</p>',status='published',category=category)
        module = import_module('content.migrations.0011_footer_and_archive_publication')
        module.unpublish_litecoin(apps, None)
        category.refresh_from_db()
        menu.refresh_from_db()
        self.assertFalse(category.is_published)
        self.assertFalse(menu.is_active)
        self.assertEqual(category.body, '<p>Saved guide</p>')
        article.refresh_from_db()
        self.assertEqual(article.status, 'published')
        for prefix in ('/','/en/'):
            self.assertEqual(self.client.get(prefix+'ltcusd-forecast/').status_code, 404)
            response = self.client.get(prefix+'litecoin-report/')
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'href="'+prefix+'ltcusd-forecast/"')
            self.assertNotContains(self.client.get(prefix), 'href="'+prefix+'ltcusd-forecast/"')
        self.assertNotContains(self.client.get('/sitemap.xml'), '/ltcusd-forecast/')
        self.assertContains(self.client.get('/sitemap.xml'), '/en/litecoin-report/')
        self.assertNotContains(self.client.get('/llms.txt'), '/ltcusd-forecast/')
        # Re-running the setup must not reintroduce the removed navigation item.
        call_command('configure_navigation',verbosity=0)
        menu.refresh_from_db()
        self.assertFalse(menu.is_active)

    def test_visibility_alone_still_preserves_legacy_archives(self):
        Category.objects.create(name='Legacy',slug='legacy-market',is_visible=False)
        self.assertEqual(self.client.get('/en/legacy-market/').status_code, 200)

    def test_unpublished_categories_are_hidden_even_with_active_menu(self):
        Category.objects.create(name='Draft',slug='draft-market',is_published=False)
        MenuItem.objects.create(label='Draft',url='/draft-market/',parent=MenuItem.objects.get(label='Crypto Forecast',parent=None))
        self.assertNotContains(self.client.get('/en/'), '/en/draft-market/')
