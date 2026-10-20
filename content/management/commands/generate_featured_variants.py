from django.core.management.base import BaseCommand
from content.image_variants import featured_source_name, generate_featured_variants
from content.models import Article


class Command(BaseCommand):
    help = "Add missing featured-image display sizes without changing articles or original files."

    def handle(self, *args, **options):
        names = {featured_source_name(article) for article in Article.objects.only("featured_image", "featured_image_url").iterator()}
        count = sum(generate_featured_variants(name) for name in names)
        self.stdout.write(self.style.SUCCESS(f"Created {count} display images; articles and originals unchanged."))
