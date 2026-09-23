import html
import re
from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import get_language
from tinymce.models import HTMLField


BLOCK_END_TAGS = re.compile(r"</(?:p|div|h[1-6]|li|blockquote|figcaption|td|th)\s*>", re.IGNORECASE)


def content_text(value):
    """Return readable plain text from editor HTML without joining block elements."""
    spaced_html = BLOCK_END_TAGS.sub(" ", value or "")
    return " ".join(html.unescape(strip_tags(spaced_html)).split())


def word_excerpt(value, limit=15):
    words = content_text(value).split()
    if not words:
        return ""
    excerpt = " ".join(words[:limit])
    return f"{excerpt}…" if len(words) > limit else excerpt


def character_excerpt(value, limit=160):
    text = content_text(value)
    if len(text) <= limit:
        return text
    shortened = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return f"{shortened}…"


def localized_value(instance, field_name):
    if (get_language() or "ar").split("-")[0] == "ar":
        arabic_value = getattr(instance, f"{field_name}_ar", "")
        if arabic_value:
            return arabic_value
    return getattr(instance, field_name, "")


class SEOFields(models.Model):
    ROBOTS_CHOICES = [
        ("index,follow", "Index and follow"),
        ("noindex,follow", "Do not index; follow links"),
        ("noindex,nofollow", "Do not index or follow"),
    ]

    meta_title = models.CharField(
        max_length=70,
        blank=True,
        help_text="Aim for 50–60 characters. Falls back to the page title.",
    )
    meta_description = models.CharField(
        max_length=320,
        blank=True,
        help_text="Aim for 140–160 characters. Falls back to the excerpt.",
    )
    focus_keyword = models.CharField(max_length=120, blank=True)
    canonical_url = models.URLField(blank=True, help_text="Leave blank to use this page's public URL.")
    robots = models.CharField(max_length=24, choices=ROBOTS_CHOICES, default="index,follow")
    social_title = models.CharField(max_length=100, blank=True)
    social_description = models.CharField(max_length=240, blank=True)
    social_image = models.ImageField(upload_to="social/%Y/%m/", blank=True)

    class Meta:
        abstract = True

    @property
    def localized_seo_title(self):
        if localized_value(self, "meta_title"):
            return localized_value(self, "meta_title")
        for field_name in ("title", "name"):
            value = localized_value(self, field_name)
            if value:
                return value
        return getattr(self, "seo_title", "")

    @property
    def localized_seo_description(self):
        description = localized_value(self, "meta_description")
        if description:
            return description
        for field_name in ("excerpt", "short_description"):
            value = localized_value(self, field_name)
            if value:
                return character_excerpt(value, 160)
        return getattr(self, "seo_description", "")

    @property
    def localized_social_title(self):
        return localized_value(self, "social_title") or self.localized_seo_title

    @property
    def localized_social_description(self):
        return localized_value(self, "social_description") or self.localized_seo_description


class ArabicSEOFields(models.Model):
    meta_title_ar = models.CharField("Arabic SEO title", max_length=70, blank=True)
    meta_description_ar = models.CharField("Arabic meta description", max_length=320, blank=True)
    focus_keyword_ar = models.CharField("Arabic focus keyword", max_length=120, blank=True)
    social_title_ar = models.CharField("Arabic social title", max_length=100, blank=True)
    social_description_ar = models.CharField("Arabic social description", max_length=240, blank=True)

    class Meta:
        abstract = True


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100, default="Elliott Wave Monitor")
    tagline = models.CharField(
        max_length=180,
        default="Independent Elliott Wave forecasts, market structure and trading education.",
    )
    hero_title = models.CharField(max_length=180, default="See the market structure before the move")
    hero_text = models.TextField(
        default="Actionable Elliott Wave analysis across forex, commodities, crypto and global indices."
    )
    site_name_ar = models.CharField("Arabic site name", max_length=100, blank=True)
    tagline_ar = models.CharField("Arabic tagline", max_length=180, blank=True)
    hero_title_ar = models.CharField("Arabic hero title", max_length=180, blank=True)
    hero_text_ar = models.TextField("Arabic hero text", blank=True)
    logo = models.ImageField(upload_to="branding/", blank=True)
    default_social_image = models.ImageField(upload_to="branding/", blank=True)
    contact_email = models.EmailField(blank=True)
    telegram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    x_url = models.URLField("X / Twitter URL", blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    footer_disclaimer = models.TextField(blank=True)
    footer_disclaimer_ar = models.TextField("Arabic footer disclaimer", blank=True)
    google_site_verification = models.CharField(max_length=160, blank=True)
    google_analytics_id = models.CharField(max_length=32, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Elliott Wave Monitor settings"

    @property
    def display_site_name(self):
        return localized_value(self, "site_name")

    @property
    def display_tagline(self):
        return localized_value(self, "tagline")

    @property
    def display_hero_title(self):
        return localized_value(self, "hero_title")

    @property
    def display_hero_text(self):
        return localized_value(self, "hero_text")

    @property
    def display_footer_disclaimer(self):
        return localized_value(self, "footer_disclaimer")


class Category(SEOFields, ArabicSEOFields):
    GROUP_CHOICES = [
        ("currencies", "Currencies Forecast"),
        ("commodities", "Commodities Forecast"),
        ("markets", "Other Markets"),
        ("education", "Education"),
    ]

    name = models.CharField(max_length=120)
    name_ar = models.CharField("Arabic name", max_length=120, blank=True)
    slug = models.SlugField(max_length=140, unique=True)
    short_description = models.TextField(blank=True)
    short_description_ar = models.TextField("Arabic short description", blank=True)
    body = HTMLField(blank=True, help_text="Evergreen introduction shown below the latest analysis.")
    body_ar = HTMLField("Arabic evergreen guide", blank=True, help_text="Arabic guide shown on the main-language page.")
    nav_group = models.CharField(max_length=24, choices=GROUP_CHOICES, default="markets")
    order = models.PositiveSmallIntegerField(default=0)
    featured_image = models.ImageField(upload_to="categories/%Y/%m/", blank=True)
    legacy_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("content_detail", kwargs={"slug": self.slug})

    @property
    def display_name(self):
        return localized_value(self, "name")

    @property
    def display_short_description(self):
        return localized_value(self, "short_description")

    @property
    def display_body(self):
        return localized_value(self, "body")

    @property
    def seo_title(self):
        return self.meta_title or self.name


class Article(SEOFields, ArabicSEOFields):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("scheduled", "Scheduled"),
    ]

    title = models.CharField(max_length=220)
    title_ar = models.CharField("Arabic title", max_length=220, blank=True)
    slug = models.SlugField(max_length=240, unique=True)
    excerpt = models.TextField(
        blank=True,
        help_text="Used on cards and below the title. Leave blank to generate the first 15 words automatically.",
    )
    excerpt_ar = models.TextField(
        "Arabic excerpt",
        blank=True,
        help_text="Leave blank to generate the first 15 Arabic words when an Arabic body is present.",
    )
    body = HTMLField()
    body_ar = HTMLField("Arabic body", blank=True)
    category = models.ForeignKey(Category, related_name="articles", on_delete=models.PROTECT)
    additional_categories = models.ManyToManyField(Category, blank=True, related_name="additional_articles")
    author_name = models.CharField(max_length=100, default="EWM Team")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft", db_index=True)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    featured_image = models.ImageField(upload_to="articles/%Y/%m/", blank=True)
    featured_image_url = models.URLField(blank=True, max_length=500)
    featured_image_alt = models.CharField(max_length=220, blank=True)
    featured_image_alt_ar = models.CharField("Arabic image alt text", max_length=220, blank=True)
    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    legacy_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    source_url = models.URLField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["category", "status", "-published_at"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("content_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        populated_fields = []
        if not (self.excerpt or "").strip():
            self.excerpt = word_excerpt(self.body, 15)
            populated_fields.append("excerpt")
        if not (self.author_name or "").strip():
            self.author_name = "EWM Team"
            populated_fields.append("author_name")
        if (self.body_ar or "").strip() and not (self.excerpt_ar or "").strip():
            self.excerpt_ar = word_excerpt(self.body_ar, 15)
            populated_fields.append("excerpt_ar")
        if kwargs.get("update_fields") is not None and populated_fields:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | set(populated_fields)
        return super().save(*args, **kwargs)

    @property
    def image_url(self):
        return self.featured_image.url if self.featured_image else self.featured_image_url

    def _variant_url(self, variant):
        if not self.featured_image:
            return self.featured_image_url
        path = PurePosixPath(self.featured_image.name)
        name = f"{path.with_suffix('')}.{variant}.webp"
        if not default_storage.exists(name):
            return self.featured_image.url
        return f"{settings.MEDIA_URL.rstrip('/')}/{str(name).lstrip('/')}"

    @property
    def card_image_url(self):
        return self._variant_url("card-hq")

    @property
    def hero_image_url(self):
        return self._variant_url("hero-hq")

    @property
    def mobile_image_url(self):
        return self._variant_url("mobile-hq")

    @property
    def compact_image_url(self):
        return self._variant_url("compact-hq")

    @property
    def seo_title(self):
        return self.meta_title or self.title

    @property
    def seo_description(self):
        return self.meta_description or character_excerpt(self.body, 160) or self.excerpt[:160]

    @property
    def has_arabic_translation(self):
        return bool((self.title_ar or "").strip() and (self.body_ar or "").strip())

    @property
    def display_title(self):
        return localized_value(self, "title")

    @property
    def display_excerpt(self):
        return localized_value(self, "excerpt")

    @property
    def display_body(self):
        return localized_value(self, "body")

    @property
    def display_featured_image_alt(self):
        return localized_value(self, "featured_image_alt")


class Page(SEOFields, ArabicSEOFields):
    title = models.CharField(max_length=180)
    title_ar = models.CharField("Arabic title", max_length=180, blank=True)
    slug = models.SlugField(max_length=200, unique=True)
    eyebrow = models.CharField(max_length=80, blank=True)
    eyebrow_ar = models.CharField("Arabic eyebrow", max_length=80, blank=True)
    excerpt = models.TextField(blank=True)
    excerpt_ar = models.TextField("Arabic excerpt", blank=True)
    body = HTMLField()
    body_ar = HTMLField("Arabic body", blank=True)
    featured_image = models.ImageField(upload_to="pages/%Y/%m/", blank=True)
    status = models.CharField(
        max_length=16,
        choices=[("draft", "Draft"), ("published", "Published")],
        default="published",
        db_index=True,
    )
    show_in_sitemap = models.BooleanField(default=True)
    legacy_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("content_detail", kwargs={"slug": self.slug})

    @property
    def display_title(self):
        return localized_value(self, "title")

    @property
    def display_eyebrow(self):
        return localized_value(self, "eyebrow")

    @property
    def display_excerpt(self):
        return localized_value(self, "excerpt")

    @property
    def display_body(self):
        return localized_value(self, "body")

    @property
    def seo_title(self):
        return self.meta_title or self.title


class MediaAsset(models.Model):
    title = models.CharField(max_length=180)
    file = models.ImageField(upload_to="library/%Y/%m/", blank=True)
    source_url = models.URLField(blank=True, max_length=500)
    alt_text = models.CharField(max_length=220, blank=True)
    caption = models.TextField(blank=True)
    credit = models.CharField(max_length=180, blank=True)
    legacy_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title

    @property
    def image_url(self):
        return self.file.url if self.file else self.source_url


class MenuItem(models.Model):
    label = models.CharField(max_length=80)
    label_ar = models.CharField("Arabic label", max_length=80, blank=True)
    url = models.CharField(max_length=300, help_text="Use a local path such as /education/ or a full URL.")
    group = models.CharField(
        max_length=24,
        choices=[("primary", "Primary navigation"), ("footer", "Footer navigation")],
        default="primary",
    )
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(default=0)
    open_in_new_tab = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group", "order", "label"]

    def __str__(self):
        return self.label

    @property
    def display_label(self):
        return localized_value(self, "label")


class Redirect(models.Model):
    old_path = models.CharField(max_length=500, unique=True, help_text="Must start with /.")
    new_path = models.CharField(max_length=500)
    permanent = models.BooleanField(default=True)
    hits = models.PositiveIntegerField(default=0, editable=False)

    def __str__(self):
        return f"{self.old_path} → {self.new_path}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
