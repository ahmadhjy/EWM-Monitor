import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from content.models import Article


class Command(BaseCommand):
    help = "Populate reviewed Arabic translations for market news and analysis articles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(settings.BASE_DIR / "data" / "arabic_articles.json"),
            help="Path to the reviewed Arabic article bundle.",
        )

    def handle(self, *args, **options):
        source = Path(options["file"])
        if not source.exists():
            raise CommandError(f"Arabic article bundle not found: {source}")
        payload = json.loads(source.read_text(encoding="utf-8"))
        updated_count = 0

        with transaction.atomic():
            for slug, values in payload.get("articles", {}).items():
                article = Article.objects.filter(slug=slug).first()
                if article is None:
                    self.stderr.write(self.style.WARNING(f"Article not found: {slug}"))
                    continue
                for field, value in values.items():
                    setattr(article, field, value)
                article.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Arabic market articles populated: {updated_count}."))
