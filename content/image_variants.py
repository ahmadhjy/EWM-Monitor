"""Generate display images on editorial saves, never during public requests."""
import logging
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)
VARIANTS = {
    "mobile-hq": ((480, 285), True, 88),
    "card-hq": ((960, 570), True, 90),
    "compact-hq": ((720, 720), False, 92),
    "hero-hq": ((1920, 1200), False, 94),
}


def featured_source_name(article):
    if article.featured_image:
        return article.featured_image.name
    # Media-library selections may be stored as URLs. Only resolve our own
    # media storage; never fetch an arbitrary external URL from the server.
    parsed = urlsplit(article.featured_image_url or "")
    if parsed.netloc and parsed.netloc != urlsplit(settings.SITE_URL).netloc:
        return ""
    prefix = urlsplit(settings.MEDIA_URL).path
    path = unquote(parsed.path)
    if not path.startswith(prefix):
        return ""
    name = path[len(prefix):]
    if not name or ".." in PurePosixPath(name).parts or "\\" in name or name.startswith("/"):
        return ""
    return name


def generate_featured_variants(name):
    """Add missing derivatives only; keep originals and existing variants intact."""
    if not name:
        return 0
    path = PurePosixPath(name)
    pending = [(key, spec, f"{path.with_suffix('')}.{key}.webp")
               for key, spec in VARIANTS.items()
               if not default_storage.exists(f"{path.with_suffix('')}.{key}.webp")]
    if not pending or not default_storage.exists(name):
        return 0
    created = 0
    try:
        with default_storage.open(name, "rb") as source, Image.open(source) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            for key, (size, crop, quality), target in pending:
                if crop:
                    output = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
                else:
                    output = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
                buffer = BytesIO()
                # News thumbnails use high-quality compression. Full-size PNG
                # charts retain lossless encoding so labels remain readable.
                output.save(buffer, format="WEBP", quality=quality, method=4,
                            lossless=key == "hero-hq" and path.suffix.lower() == ".png")
                default_storage.save(target, ContentFile(buffer.getvalue()))
                created += 1
    except (OSError, ValueError, Image.DecompressionBombError):
        # A damaged image must not prevent the editor saving their article.
        logger.exception("Could not generate display images for %s", name)
    return created
