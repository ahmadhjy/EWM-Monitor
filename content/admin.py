from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.forms import Textarea
from django.http import JsonResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from tinymce.models import HTMLField
from tinymce.widgets import AdminTinyMCE
from unfold.admin import ModelAdmin, TabularInline

from .forms import MediaAssetUploadForm
from .models import (
    Article,
    Category,
    ContactMessage,
    MediaAsset,
    MenuItem,
    NewsletterSubscriber,
    Page,
    Redirect,
    SiteSettings,
)


SEO_FIELDSET = (
    "Search & social preview",
    {
        "classes": ["collapse"],
        "fields": (
            "meta_title",
            "meta_description",
            "focus_keyword",
            "canonical_url",
            "robots",
            "social_title",
            "social_description",
            "social_image",
        ),
        "description": "These fields replace the familiar Yoast controls. Blank fields use sensible content defaults.",
    },
)

RICH_TEXT_OVERRIDES = {
    HTMLField: {"widget": AdminTinyMCE(attrs={"rows": 30})},
}


class BilingualAdminMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if isinstance(db_field, HTMLField) and db_field.name.endswith("_ar"):
            kwargs["widget"] = AdminTinyMCE(
                attrs={"rows": 30, "dir": "rtl", "lang": "ar"},
                mce_attrs={
                    "directionality": "rtl",
                    "content_style": "body { font-family: Tahoma, Arial, sans-serif; font-size: 17px; line-height: 1.9; direction: rtl; text-align: right; max-width: 820px; margin: 24px auto; } img { max-width: 100%; height: auto; }",
                },
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for name, field in form.base_fields.items():
            if name.endswith("_ar"):
                field.widget.attrs.update({"dir": "rtl", "lang": "ar"})
        return form


ARABIC_SEO_FIELDSET = (
    "Arabic search & social preview",
    {
        "classes": ["collapse"],
        "fields": ("meta_title_ar", "meta_description_ar", "focus_keyword_ar", "social_title_ar", "social_description_ar"),
        "description": "Arabic SEO fields for the main-language website. Blank fields use the Arabic page title and summary.",
    },
)


def admin_environment(request):
    return ["Local preview", "info"]


@admin.register(Article)
class ArticleAdmin(BilingualAdminMixin, ModelAdmin):
    formfield_overrides = RICH_TEXT_OVERRIDES
    list_display = ("title", "arabic_translation", "category", "status_badge", "published_at", "is_featured", "is_trending")
    list_filter = ("status", "category", "is_featured", "is_trending", "published_at")
    search_fields = ("title", "title_ar", "excerpt", "excerpt_ar", "body", "body_ar", "focus_keyword", "focus_keyword_ar")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("legacy_id", "source_url", "created_at", "updated_at", "image_preview")
    autocomplete_fields = ("category", "additional_categories")
    date_hierarchy = "published_at"
    save_on_top = True
    list_per_page = 30
    fieldsets = (
        ("English article", {"fields": ("title", "slug", "excerpt", "body")}),
        ("Arabic translation", {"fields": ("title_ar", "excerpt_ar", "body_ar"), "description": "Enter the Arabic title and full Arabic content here, then Save. Both are required for this article to appear on the Arabic website. Leave them blank to keep an article English-only. The shared slug, image and publishing controls apply to both editions."}),
        ("Publishing", {"fields": ("category", "additional_categories", "author_name", "status", "published_at", "is_featured", "is_trending")}),
        ("Featured image", {"fields": ("featured_image", "featured_image_url", "featured_image_alt_ar", "featured_image_alt", "image_preview")}),
        ARABIC_SEO_FIELDSET,
        SEO_FIELDSET,
        ("Migration record", {"classes": ["collapse"], "fields": ("legacy_id", "source_url", "created_at", "updated_at")}),
    )

    @admin.display(boolean=True, description="Arabic edition")
    def arabic_translation(self, obj):
        return obj.has_arabic_translation

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        color = {"published": "#15966a", "scheduled": "#b87700", "draft": "#64748b"}.get(obj.status, "#64748b")
        return format_html('<span style="color:{};font-weight:700">{}</span>', color, obj.get_status_display())

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if not obj.image_url:
            return "No image selected"
        return format_html('<img src="{}" alt="" style="max-width:360px;max-height:220px;border-radius:12px" />', obj.image_url)

    def save_model(self, request, obj, form, change):
        if obj.status == "published" and not obj.published_at:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Page)
class PageAdmin(BilingualAdminMixin, ModelAdmin):
    formfield_overrides = RICH_TEXT_OVERRIDES
    list_display = ("title", "slug", "status", "show_in_sitemap", "updated_at")
    list_filter = ("status", "show_in_sitemap")
    search_fields = ("title", "body", "meta_title", "meta_description")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("legacy_id", "updated_at")
    save_on_top = True
    fieldsets = (
        ("Arabic page — main language", {"fields": ("title_ar", "eyebrow_ar", "excerpt_ar", "body_ar")}),
        ("English page", {"classes": ["collapse"], "fields": ("title", "slug", "eyebrow", "excerpt", "body", "featured_image")}),
        ("Publishing", {"fields": ("status", "show_in_sitemap")}),
        ARABIC_SEO_FIELDSET,
        SEO_FIELDSET,
        ("Migration record", {"classes": ["collapse"], "fields": ("legacy_id", "updated_at")}),
    )


@admin.register(Category)
class CategoryAdmin(BilingualAdminMixin, ModelAdmin):
    formfield_overrides = RICH_TEXT_OVERRIDES
    list_display = ("name", "nav_group", "order", "is_visible", "article_count")
    list_editable = ("order", "is_visible")
    list_filter = ("nav_group", "is_visible")
    search_fields = ("name", "short_description", "body")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("legacy_id",)
    fieldsets = (
        ("Arabic category — main language", {"fields": ("name_ar", "short_description_ar", "body_ar")}),
        ("English category", {"classes": ["collapse"], "fields": ("name", "slug", "short_description", "body", "featured_image")}),
        ("Navigation & visibility", {"fields": ("nav_group", "order", "is_visible")}),
        ARABIC_SEO_FIELDSET,
        SEO_FIELDSET,
        ("Migration record", {"classes": ["collapse"], "fields": ("legacy_id",)}),
    )

    @admin.display(description="Articles")
    def article_count(self, obj):
        return obj.articles.count()


@admin.register(SiteSettings)
class SiteSettingsAdmin(BilingualAdminMixin, ModelAdmin):
    fieldsets = (
        ("Arabic brand — main language", {"fields": ("site_name_ar", "tagline_ar", "hero_title_ar", "hero_text_ar")}),
        ("English brand", {"classes": ["collapse"], "fields": ("site_name", "tagline", "hero_title", "hero_text")}),
        ("Brand images", {"fields": ("logo", "default_social_image")}),
        ("Contact & social", {"fields": ("contact_email", "telegram_url", "instagram_url", "facebook_url", "youtube_url", "x_url", "linkedin_url")}),
        ("Arabic footer", {"fields": ("footer_disclaimer_ar",)}),
        ("English footer", {"classes": ["collapse"], "fields": ("footer_disclaimer",)}),
        ("Search verification & analytics", {"classes": ["collapse"], "fields": ("google_site_verification", "google_analytics_id")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ChildMenuInline(TabularInline):
    model = MenuItem
    fk_name = "parent"
    extra = 0


@admin.register(MenuItem)
class MenuItemAdmin(ModelAdmin):
    list_display = ("label_ar", "label", "group", "parent", "url", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("group", "is_active")
    search_fields = ("label", "url")
    inlines = (ChildMenuInline,)


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ("thumbnail", "title", "alt_text", "uploaded_at")
    search_fields = ("title", "alt_text", "caption", "credit")
    readonly_fields = ("legacy_id", "thumbnail_large", "uploaded_at")

    def get_urls(self):
        custom_urls = [
            path("picker/", self.admin_site.admin_view(self.picker_view), name="content_mediaasset_picker"),
            path("picker/upload/", self.admin_site.admin_view(self.picker_upload), name="content_mediaasset_picker_upload"),
            path(
                "picker/<int:asset_id>/alt/",
                self.admin_site.admin_view(self.picker_update_alt),
                name="content_mediaasset_picker_alt",
            ),
        ]
        return custom_urls + super().get_urls()

    @staticmethod
    def asset_payload(asset):
        return {
            "id": asset.pk,
            "title": asset.title,
            "url": asset.image_url,
            "alt_text": asset.alt_text,
            "caption": asset.caption,
            "credit": asset.credit,
            "uploaded_at": asset.uploaded_at.isoformat(),
        }

    def picker_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        queryset = self.get_queryset(request).filter(Q(file__gt="") | Q(source_url__gt=""))
        query = request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(alt_text__icontains=query)
                | Q(caption__icontains=query)
                | Q(credit__icontains=query)
            )
        paginator = Paginator(queryset, 36)
        page = paginator.get_page(request.GET.get("page", 1))
        return JsonResponse(
            {
                "items": [self.asset_payload(asset) for asset in page.object_list],
                "page": page.number,
                "has_more": page.has_next(),
                "total": paginator.count,
            }
        )

    def picker_upload(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method != "POST":
            return JsonResponse({"error": "POST required."}, status=405)
        form = MediaAssetUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
        asset = form.save()
        return JsonResponse({"item": self.asset_payload(asset)}, status=201)

    def picker_update_alt(self, request, asset_id):
        asset = self.get_object(request, str(asset_id))
        if asset is None:
            return JsonResponse({"error": "Image not found."}, status=404)
        if not self.has_change_permission(request, asset):
            raise PermissionDenied
        if request.method != "POST":
            return JsonResponse({"error": "POST required."}, status=405)
        asset.alt_text = request.POST.get("alt_text", "").strip()[:220]
        asset.save(update_fields=["alt_text"])
        return JsonResponse({"item": self.asset_payload(asset)})

    @admin.display(description="Image")
    def thumbnail(self, obj):
        if not obj.image_url:
            return "—"
        return format_html('<img src="{}" alt="" style="width:72px;height:52px;object-fit:cover;border-radius:8px" />', obj.image_url)

    @admin.display(description="Preview")
    def thumbnail_large(self, obj):
        if not obj.image_url:
            return ""
        return format_html('<img src="{}" alt="" style="max-width:520px;max-height:360px;border-radius:12px" />', obj.image_url)


@admin.register(Redirect)
class RedirectAdmin(ModelAdmin):
    list_display = ("old_path", "new_path", "permanent", "hits")
    list_filter = ("permanent",)
    search_fields = ("old_path", "new_path")
    readonly_fields = ("hits",)


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ("subject", "name", "email", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "created_at")
    formfield_overrides = {models.TextField: {"widget": Textarea(attrs={"rows": 12})}}


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("email",)
    list_filter = ("is_active", "created_at")
