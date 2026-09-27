from django.core.management.base import BaseCommand
from django.db import transaction
from content.models import Category, MenuItem


class Command(BaseCommand):
    help = "Apply the bilingual market navigation without replacing editorial content."

    @transaction.atomic
    def handle(self, *args, **options):
        news, _ = Category.objects.get_or_create(slug="latest-news-and-analysis", defaults={"name": "News & Analysis"})
        news.name, news.name_ar, news.is_visible = "News & Analysis", "الأخبار والتحليلات", True
        news.save(update_fields=["name", "name_ar", "is_visible"])
        groups = [
            ("News & Analysis", "الأخبار والتحليلات", "/latest-news-and-analysis/", [], []),
            ("Forex Forecast", "توقعات الفوركس", "", ["Currencies"], [("AUD/USD", "audusd"), ("EUR/USD", "eurusd"), ("GBP/USD", "gbpusd"), ("USD/CAD", "usdcad"), ("USD/JPY", "usdjpy")]),
            ("Commodities Forecast", "توقعات السلع", "", ["Commodities"], [("Crude Oil", "crude-oil", "النفط الخام"), ("Gold", "gold", "الذهب"), ("Silver", "silver", "الفضة")]),
            ("Crypto Forecast", "توقعات العملات الرقمية", "", ["Crypto", "Cryptocurrencies"], [("BTC/USD", "btcusd"), ("ETH/USD", "ethusd"), ("LTC/USD", "ltcusd")]),
            ("Indices Forecast", "توقعات المؤشرات", "", ["Stocks"], [("Dow Jones", "dow-jones", "داو جونز"), ("Nasdaq", "nasdaq", "ناسداك"), ("S&P 500", "sp-500", "S&P 500")]),
            ("Education", "تعليم التداول", "/education/", [], []),
            ("Brokers", "شركات التداول", "", [], []),
        ]
        roots = []
        for order, (label, arabic, url, aliases, children) in enumerate(groups):
            item = MenuItem.objects.filter(group="primary", parent=None, label__in=[label, *aliases]).first()
            if item is None:
                item = MenuItem(group="primary")
            item.label, item.label_ar, item.url = label, arabic, url
            item.order, item.is_active = order, True
            item.save()
            roots.append(item.pk)
            child_ids = []
            for position, child in enumerate(children):
                name, slug = child[:2]
                name_ar = child[2] if len(child) > 2 else name
                slug += "-forecast"
                Category.objects.get_or_create(slug=slug, defaults={
                    "name": f"{name} Forecast", "name_ar": f"توقعات {name_ar}",
                    "short_description": f"Elliott Wave analysis, market structure and the latest {name} forecasts.",
                    "short_description_ar": f"تحليل موجات إليوت وهيكل السوق وأحدث توقعات {name_ar}.",
                    "nav_group": "markets", "order": 20 + order * 10 + position,
                })
                entry, _ = MenuItem.objects.get_or_create(parent=item, url=f"/{slug}/", defaults={"label": name})
                entry.label, entry.label_ar = f"{name} Forecast", f"توقعات {name_ar}"
                entry.order, entry.is_active = position, True
                entry.save()
                child_ids.append(entry.pk)
            item.children.exclude(pk__in=child_ids).update(is_active=False)
        MenuItem.objects.filter(group="primary", parent=None).exclude(pk__in=roots).update(is_active=False)
        self.stdout.write(self.style.SUCCESS("Bilingual navigation updated; existing articles and archive URLs preserved."))
