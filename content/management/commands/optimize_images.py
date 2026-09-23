from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from PIL import Image, ImageFilter, ImageOps

from content.models import Article


class Command(BaseCommand):
    help = "Generate high-resolution WebP variants while preserving chart labels and market data."

    def handle(self, *args, **options):
        created = 0
        inline_created = 0
        articles_updated = 0
        for article in Article.objects.exclude(featured_image=""):
            with article.featured_image.open("rb") as source:
                image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
                lossless = PurePosixPath(article.featured_image.name).suffix.lower() == ".png"
                created += self.save_variant(article, image, "mobile-hq", (480, 285), 88, crop=True, lossless=lossless)
                created += self.save_variant(article, image, "compact-hq", (720, 720), 90, crop=False, lossless=lossless)
                created += self.save_variant(article, image, "card-hq", (960, 570), 90, crop=True, lossless=lossless)
                created += self.save_variant(article, image, "hero-hq", (1920, 1200), 94, crop=False, lossless=lossless)

        for article in Article.objects.all():
            soup = BeautifulSoup(article.body, "html.parser")
            changed = False
            for image_tag in soup.select("img[src]"):
                result = self.restore_inline_image(image_tag["src"])
                if not result:
                    continue
                was_created, url, width, height = result
                inline_created += was_created
                image_tag["src"] = url
                image_tag["width"] = str(width)
                image_tag["height"] = str(height)
                image_tag["loading"] = "lazy"
                image_tag["decoding"] = "async"
                image_tag.attrs.pop("srcset", None)
                image_tag.attrs.pop("sizes", None)
                changed = True
            if changed:
                article.body = str(soup)
                article.save(update_fields=["body", "updated_at"])
                articles_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {created} featured variants and {inline_created} restored inline images; "
                f"updated {articles_updated} articles."
            )
        )

    def save_variant(self, article, image, variant, size, quality, crop, lossless):
        path = PurePosixPath(article.featured_image.name)
        target = f"{path.with_suffix('')}.{variant}.webp"
        if default_storage.exists(target):
            return 0
        if crop:
            output_image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
        else:
            contained = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
            output_image = Image.new("RGB", size, (248, 250, 252))
            output_image.paste(contained, ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2))
        output_image = output_image.filter(ImageFilter.UnsharpMask(radius=1.25, percent=135, threshold=2))
        buffer = BytesIO()
        output_image.save(buffer, format="WEBP", quality=quality, method=6, lossless=lossless)
        default_storage.save(target, ContentFile(buffer.getvalue()))
        return 1

    def restore_inline_image(self, src):
        parsed = urlparse(src)
        media_path = parsed.path
        if not media_path.startswith(settings.MEDIA_URL):
            return None
        relative = unquote(media_path[len(settings.MEDIA_URL) :]).lstrip("/")
        if not relative or relative.endswith(".hd.webp") or not default_storage.exists(relative):
            return None
        path = PurePosixPath(relative)
        target = str(path.with_suffix(".hd.webp"))
        if default_storage.exists(target):
            with default_storage.open(target, "rb") as restored:
                with Image.open(restored) as existing:
                    return 0, default_storage.url(target), existing.width, existing.height

        with default_storage.open(relative, "rb") as source:
            image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
            scale = max(1.0, min(1600 / image.width, 2400 / image.height))
            size = (round(image.width * scale), round(image.height * scale))
            restored = image.resize(size, Image.Resampling.LANCZOS)
            restored = restored.filter(ImageFilter.UnsharpMask(radius=1.25, percent=140, threshold=2))
            buffer = BytesIO()
            restored.save(
                buffer,
                format="WEBP",
                quality=94,
                method=6,
                lossless=path.suffix.lower() == ".png",
            )
            default_storage.save(target, ContentFile(buffer.getvalue()))
        return 1, default_storage.url(target), restored.width, restored.height
