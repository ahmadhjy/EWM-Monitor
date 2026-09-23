import html
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from content.models import Article, Category, MediaAsset, MenuItem, Page, SiteSettings


SOURCE_HOSTS = {"elliottwavemonitor.com", "www.elliottwavemonitor.com"}


class Command(BaseCommand):
    help = "Import the bundled public WordPress snapshot into the local editorial database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(settings.BASE_DIR / "data" / "wordpress_export.json"),
            help="Path to the normalized WordPress snapshot.",
        )
        parser.add_argument(
            "--download-media",
            action="store_true",
            help="Copy remote featured and inline images into local media storage.",
        )

    def handle(self, *args, **options):
        source = Path(options["file"])
        if not source.exists():
            raise CommandError(f"Snapshot not found: {source}")
        data = json.loads(source.read_text(encoding="utf-8"))
        currency_sections_path = settings.BASE_DIR / "data" / "currency_sections.json"
        self.currency_sections = {}
        if currency_sections_path.exists():
            self.currency_sections = {
                row["slug"]: row["html"]
                for row in json.loads(currency_sections_path.read_text(encoding="utf-8"))
            }
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 EWM migration"})
        self.download_media = options["download_media"]

        with transaction.atomic():
            self.import_settings()
            categories = self.import_categories(data.get("categories", []))
            self.import_pages(data.get("pages", []))
            self.import_articles(data.get("posts", []), categories)
            self.import_media_library(data.get("media", []))
            self.import_menu()

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {Article.objects.count()} articles, {Page.objects.count()} pages, "
                f"{Category.objects.count()} categories and {MediaAsset.objects.count()} media records."
            )
        )

    def import_settings(self):
        settings_obj = SiteSettings.load()
        settings_obj.site_name = "Elliott Wave Monitor"
        settings_obj.tagline = "Independent Elliott Wave forecasts, market structure and trading education."
        settings_obj.hero_title = "See the market structure before the move"
        settings_obj.hero_text = (
            "Actionable Elliott Wave analysis across forex, commodities, crypto and global indices—"
            "built around scenarios, structure and disciplined risk awareness."
        )
        settings_obj.google_site_verification = "6rG3GPe-n67xk43QJrBNV2XKt10nZFGAb8m7Yb5DVHc"
        original_logo = "library/2026/09/lOGO-SVG.png"
        if default_storage.exists(original_logo):
            settings_obj.default_social_image.name = original_logo
        settings_obj.footer_disclaimer = (
            "The content on this website is provided for research, education and to assist traders in making "
            "independent decisions. It does not constitute investment advice. Opinions, analysis and market data "
            "may change without notice and may not be real-time or accurate. Trading financial instruments on "
            "margin carries a high level of risk and may not be suitable for all investors. Consider your objectives, "
            "experience and risk appetite, use appropriate risk controls, and seek professional advice when needed."
        )
        settings_obj.save()

    def seo_values(self, item):
        return {
            "meta_title": html.unescape(item.get("meta_title", ""))[:70],
            "meta_description": html.unescape(item.get("meta_description", ""))[:320],
            "canonical_url": item.get("canonical_url", ""),
            "robots": item.get("robots", "index,follow"),
            "social_title": html.unescape(item.get("social_title", ""))[:100],
            "social_description": html.unescape(item.get("social_description", ""))[:240],
        }

    def import_categories(self, rows):
        categories = {}
        for row in rows:
            body_source = self.currency_sections.get(row["slug"], row.get("body", ""))
            body = self.prepare_html(body_source, f"category-{row['slug']}")
            values = {
                "name": html.unescape(row["name"]),
                "slug": row["slug"],
                "short_description": html.unescape(row.get("short_description", "")),
                "body": body,
                "nav_group": row.get("nav_group", "markets"),
                "order": row.get("order", 0),
                "legacy_id": row.get("legacy_id"),
                "is_visible": row.get("is_visible", True),
                **self.seo_values(row),
            }
            obj, _ = Category.objects.update_or_create(slug=row["slug"], defaults=values)
            categories[row.get("legacy_id")] = obj
        return categories

    def import_pages(self, rows):
        for row in rows:
            values = {
                "title": html.unescape(row["title"]),
                "excerpt": html.unescape(row.get("excerpt", "")),
                "body": self.prepare_html(row.get("body", ""), f"page-{row['slug']}"),
                "status": row.get("status", "published"),
                "legacy_id": row.get("legacy_id"),
                **self.seo_values(row),
            }
            Page.objects.update_or_create(slug=row["slug"], defaults=values)

    def import_articles(self, rows, categories):
        for row in rows:
            linked = [categories[legacy_id] for legacy_id in row.get("category_ids", []) if legacy_id in categories]
            if not linked:
                self.stderr.write(self.style.WARNING(f"Skipping {row['slug']}: no matching category"))
                continue
            values = {
                "title": html.unescape(row["title"]),
                "excerpt": html.unescape(row.get("excerpt", "")),
                "body": self.prepare_html(row.get("body", ""), f"article-{row['slug']}"),
                "category": linked[0],
                "author_name": row.get("author_name") or "EWM Team",
                "status": row.get("status", "published"),
                "published_at": parse_datetime(row["published_at"]),
                "featured_image_url": row.get("featured_image_url", ""),
                "featured_image_alt": html.unescape(row.get("featured_image_alt", ""))[:220],
                "is_featured": row.get("is_featured", False),
                "is_trending": row.get("is_trending", False),
                "legacy_id": row.get("legacy_id"),
                "source_url": row.get("source_url", ""),
                **self.seo_values(row),
            }
            article, _ = Article.objects.update_or_create(slug=row["slug"], defaults=values)
            article.additional_categories.set(linked[1:])
            if self.download_media and row.get("featured_image_url") and not article.featured_image:
                result = self.download(row["featured_image_url"], f"articles/{article.published_at:%Y/%m}")
                if result:
                    filename, content = result
                    article.featured_image.save(filename, content, save=True)

    def import_media_library(self, rows):
        for row in rows:
            values = {
                "title": html.unescape(row.get("title") or "Imported image")[:180],
                "source_url": row.get("source_url", ""),
                "alt_text": html.unescape(row.get("alt_text", ""))[:220],
                "caption": html.unescape(row.get("caption", "")),
            }
            asset, _ = MediaAsset.objects.update_or_create(legacy_id=row["legacy_id"], defaults=values)
            if self.download_media and row.get("source_url") and not asset.file:
                result = self.download(row["source_url"], "library/imported")
                if result:
                    filename, content = result
                    asset.file.save(filename, content, save=True)

    def prepare_html(self, source, folder):
        if not source:
            return ""
        soup = BeautifulSoup(source, "html.parser")
        for unwanted in soup.select("script, style, noscript"):
            unwanted.decompose()
        for link in soup.select("a[href]"):
            parsed = urlparse(link.get("href", ""))
            if parsed.hostname in SOURCE_HOSTS:
                link["href"] = parsed.path or "/"
        for image in soup.select("img[src]"):
            image["loading"] = "lazy"
            image["decoding"] = "async"
            if not image.get("alt"):
                image["alt"] = "Elliott Wave analysis chart"
            if self.download_media:
                result = self.download(image["src"], f"inline/{folder}")
                if result:
                    filename, content = result
                    storage_name = default_storage.save(f"inline/{folder}/{filename}", content)
                    image["src"] = default_storage.url(storage_name)
                    image.attrs.pop("srcset", None)
                    image.attrs.pop("sizes", None)
        return str(soup)

    def download(self, url, folder):
        if not url or url.startswith("data:"):
            return None
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 403 and "elliottwavemonitor.com/wp-content/" in url:
                parsed = urlparse(url)
                proxy = f"https://i0.wp.com/elliottwavemonitor.com{parsed.path}?ssl=1"
                response = self.session.get(proxy, timeout=30)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0]
            if content_type and not content_type.startswith("image/"):
                return None
            filename = Path(unquote(urlparse(url).path)).name or "image"
            if "." not in filename:
                filename += mimetypes.guess_extension(content_type) or ".jpg"
            filename = re.sub(r"[^A-Za-z0-9._-]+", "-", filename)[:180]
            return filename, ContentFile(response.content)
        except requests.RequestException as exc:
            self.stderr.write(self.style.WARNING(f"Could not download {url}: {exc}"))
            return None

    def import_menu(self):
        MenuItem.objects.all().delete()
        currencies = MenuItem.objects.create(label="Currencies", url="/eurusd-forecast/", order=10)
        for order, (label, url) in enumerate(
            [
                ("AUD/USD Forecast", "/audusd-forecast/"),
                ("EUR/USD Forecast", "/eurusd-forecast/"),
                ("GBP/USD Forecast", "/gbpusd-forecast/"),
                ("USD/CAD Forecast", "/usdcad-forecast/"),
                ("USD/CHF Forecast", "/usdchf-forecast/"),
                ("USD/JPY Forecast", "/usdjpy-forecast/"),
            ],
            start=1,
        ):
            MenuItem.objects.create(label=label, url=url, parent=currencies, order=order)
        commodities = MenuItem.objects.create(label="Commodities", url="/gold-forecast/", order=20)
        for order, (label, url) in enumerate(
            [("Crude Oil Forecast", "/crude-oil-forecast/"), ("Gold Forecast", "/gold-forecast/"), ("Silver Forecast", "/silver-forecast/")],
            start=1,
        ):
            MenuItem.objects.create(label=label, url=url, parent=commodities, order=order)
        MenuItem.objects.create(label="Crypto", url="/cryptocurriencies-forecast/", order=30)
        MenuItem.objects.create(label="Stocks", url="/stocks-forecast/", order=40)
        MenuItem.objects.create(label="Education", url="/education/", order=50)
