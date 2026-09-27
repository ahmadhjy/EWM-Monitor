from django.core.management import call_command
from django.test import TestCase
from .models import Article, Category, MenuItem


class NavigationTests(TestCase):
    def setUp(self):
        call_command("configure_navigation", verbosity=0)

    def test_exact_order_and_children(self):
        roots = MenuItem.objects.filter(parent=None, is_active=True, group="primary")
        self.assertEqual(list(roots.values_list("label", flat=True)), ["News & Analysis", "Forex Forecast", "Commodities Forecast", "Crypto Forecast", "Indices Forecast", "Education", "Brokers"])
        self.assertEqual([r.children.filter(is_active=True).count() for r in roots], [0, 5, 3, 3, 3, 0, 0])
        self.assertEqual(roots.get(label="Brokers").url, "")
        self.assertNotContains(self.client.get("/en/"), '>Home</a>\n        ')
        self.assertContains(self.client.get("/en/"), 'class="submenu-toggle nav-parent"', count=4)

    def test_idempotent_and_preserves_editor_content(self):
        category = Category.objects.get(slug="btcusd-forecast")
        category.body = "<p>Editor content</p>"
        category.save()
        before = (Category.objects.count(), MenuItem.objects.count())
        call_command("configure_navigation", verbosity=0)
        self.assertEqual(before, (Category.objects.count(), MenuItem.objects.count()))
        category.refresh_from_db()
        self.assertEqual(category.body, "<p>Editor content</p>")

    def test_news_language_isolation_and_archives(self):
        category = Category.objects.get(slug="latest-news-and-analysis")
        Article.objects.create(title="English-only report", slug="english-report", body="<p>Report</p>", category=category, status="published")
        self.assertContains(self.client.get("/en/latest-news-and-analysis/"), "English-only report")
        self.assertNotContains(self.client.get("/latest-news-and-analysis/"), "English-only report")
        for slug in ["btcusd", "ethusd", "ltcusd", "dow-jones", "nasdaq", "sp-500"]:
            for prefix in ["/", "/en/"]:
                self.assertEqual(self.client.get(f"{prefix}{slug}-forecast/").status_code, 200)
