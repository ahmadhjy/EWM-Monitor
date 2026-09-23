import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from content.models import Category, MenuItem, Page, SiteSettings


class Command(BaseCommand):
    help = "Populate the bundled Arabic-first site copy, pages, market guides, SEO fields, and navigation labels."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(settings.BASE_DIR / "data" / "arabic_content.json"),
            help="Path to the reviewed Arabic content bundle.",
        )

    def handle(self, *args, **options):
        source = Path(options["file"])
        if not source.exists():
            raise CommandError(f"Arabic content bundle not found: {source}")
        payload = json.loads(source.read_text(encoding="utf-8"))
        counts = {"settings": 0, "pages": 0, "categories": 0, "menus": 0}

        with transaction.atomic():
            settings_obj = SiteSettings.load()
            for field, value in payload.get("settings", {}).items():
                setattr(settings_obj, field, value)
            settings_obj.save()
            counts["settings"] = 1

            for slug, values in payload.get("pages", {}).items():
                updated = Page.objects.filter(slug=slug).update(**values)
                if not updated:
                    self.stderr.write(self.style.WARNING(f"Page not found: {slug}"))
                counts["pages"] += updated

            for slug, values in payload.get("categories", {}).items():
                updated = Category.objects.filter(slug=slug).update(**values)
                if not updated:
                    self.stderr.write(self.style.WARNING(f"Category not found: {slug}"))
                counts["categories"] += updated

            for english_label, arabic_label in payload.get("menus", {}).items():
                counts["menus"] += MenuItem.objects.filter(label=english_label).update(label_ar=arabic_label)

        self.stdout.write(
            self.style.SUCCESS(
                "Arabic content populated: "
                + ", ".join(f"{value} {key}" for key, value in counts.items())
                + "."
            )
        )
