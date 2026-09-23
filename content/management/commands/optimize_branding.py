from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image


class Command(BaseCommand):
    help = "Build a compact 4x-density flag icon from the untouched owner-supplied artwork."

    def handle(self, *args, **options):
        directory = settings.BASE_DIR / "static" / "img"
        source = directory / "flag-sa.png"
        destination = directory / "flag-sa.webp"
        with Image.open(source) as image:
            if image.width * 2 != image.height * 3:
                raise ValueError("The supplied Saudi flag must retain its 3:2 proportions.")
            icon = image.convert("RGB").resize((108, 72), Image.Resampling.LANCZOS)
            icon.save(destination, format="WEBP", lossless=True, method=6)
        self.stdout.write(self.style.SUCCESS(f"Flag icon: {destination.stat().st_size} bytes; original artwork preserved."))
