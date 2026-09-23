import json
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from content.models import Category


SOURCE_HOSTS = {"elliottwavemonitor.com", "www.elliottwavemonitor.com"}


class Command(BaseCommand):
    help = "Import the bundled evergreen currency guides captured from the former WordPress pages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(settings.BASE_DIR / "data" / "currency_sections.json"),
            help="Path to the sanitized currency-page content snapshot.",
        )

    def handle(self, *args, **options):
        source = Path(options["file"])
        if not source.exists():
            raise CommandError(f"Currency content snapshot not found: {source}")
        rows = json.loads(source.read_text(encoding="utf-8"))
        updated = 0
        with transaction.atomic():
            for row in rows:
                category = Category.objects.filter(slug=row["slug"]).first()
                if not category:
                    self.stderr.write(self.style.WARNING(f"Category not found: {row['slug']}"))
                    continue
                soup = BeautifulSoup(row["html"], "html.parser")
                for link in soup.select("a[href]"):
                    parsed = urlparse(link["href"])
                    if parsed.hostname in SOURCE_HOSTS:
                        link["href"] = parsed.path or "/"
                category.body = str(soup)
                category.save(update_fields=["body"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Imported evergreen guides for {updated} currency pages."))
