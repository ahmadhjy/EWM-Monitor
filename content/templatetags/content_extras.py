import math
import re

from django import template
from django.utils.html import strip_tags
from django.utils.translation import get_language
from django.utils.safestring import mark_safe
from django.conf import settings
from urllib.parse import urlsplit, urlunsplit
from bs4 import BeautifulSoup

from content.i18n import ui_text


register = template.Library()


@register.filter
def reading_time(value):
    words = len(re.findall(r"\w+", strip_tags(value or "")))
    return max(1, math.ceil(words / 220))


@register.filter
def absolute_media(url, site_url):
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{site_url.rstrip('/')}/{url.lstrip('/')}"


@register.simple_tag
def ui(value):
    return ui_text(value)


@register.filter
def localized_path(value):
    if not value or not value.startswith("/") or value.startswith(("/admin/", "/media/", "/static/")):
        return value
    language = (get_language() or "ar").split("-")[0]
    if language == "en" and not value.startswith("/en/"):
        return f"/en{value}"
    if language == "ar" and value.startswith("/en/"):
        return value[3:]
    return value


@register.filter
def localized_content(value):
    """Keep imported inline links on the appropriate language edition."""
    from content.models import Article
    from django.db import models
    soup = BeautifulSoup(value or "", "html.parser")
    language = (get_language() or "ar").split("-")[0]
    own_hosts = {"elliottwavemonitor.com", "www.elliottwavemonitor.com", urlsplit(settings.SITE_URL).hostname}
    english_only = set()
    if language == "ar":
        english_only = set(Article.objects.filter(models.Q(title_ar="") | models.Q(body_ar="")).values_list("slug", flat=True))
    for anchor in soup.select("a[href]"):
        url = urlsplit(anchor["href"])
        if (url.hostname and url.hostname not in own_hosts) or not url.path.startswith("/") or url.path.startswith(("/media/", "/static/", "/admin/")):
            continue
        target_path = localized_path(url.path)
        if language == "ar" and target_path.strip("/") in english_only:
            target_path = "/en" + target_path
            anchor["hreflang"] = "en"
        anchor["href"] = urlunsplit(("", "", target_path, url.query, url.fragment))
    for image in soup.select("img"):
        image["loading"] = "lazy"
        image["decoding"] = "async"
    return mark_safe(str(soup))
