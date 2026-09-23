from django.conf import settings
from django.utils.translation import get_language

from .models import MenuItem, SiteSettings


def site_context(request):
    site_settings = SiteSettings.load()
    icons = {
        "telegram": '<path d="m3 11 18-7-4 17-6-5-4 3 1-6 10-7-9 9z"/>',
        "instagram": '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>',
        "facebook": '<path d="M14 22v-9h3l1-4h-4V7c0-1 .5-2 2-2h2V1h-3c-4 0-6 2-6 6v2H6v4h3v9"/>',
        "youtube": '<rect x="2" y="5" width="20" height="14" rx="4"/><path d="m10 9 6 3-6 3z"/>',
        "x": '<path d="m4 3 16 18M20 3 4 21M4 3h5l11 18h-5z"/>',
        "linkedin": '<rect x="3" y="8" width="4" height="13"/><path d="M11 21V8h4v2c4-4 7-1 7 3v8h-4v-8c0-2-3-2-3 0v8"/><circle cx="5" cy="3.5" r="2"/>',
    }
    social_links = [
        {"name": label, "url": getattr(site_settings, f"{field}_url"), "icon": icons[field]}
        for field, label in [("telegram", "Telegram"), ("instagram", "Instagram"), ("facebook", "Facebook"), ("youtube", "YouTube"), ("x", "X / Twitter"), ("linkedin", "LinkedIn")]
        if getattr(site_settings, f"{field}_url")
    ]
    primary = MenuItem.objects.filter(group="primary", is_active=True, parent__isnull=True).prefetch_related("children")
    footer = MenuItem.objects.filter(group="footer", is_active=True, parent__isnull=True)
    language_code = (get_language() or settings.LANGUAGE_CODE).split("-")[0]
    return {
        "site_settings": site_settings,
        "social_links": social_links,
        "site_url": settings.SITE_URL,
        "primary_menu": primary,
        "footer_menu": footer,
        "language_code": language_code,
        "is_rtl": language_code == "ar",
        "text_direction": "rtl" if language_code == "ar" else "ltr",
    }
