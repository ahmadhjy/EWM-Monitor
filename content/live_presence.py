"""Anonymous active-tab estimates with short retention and bounded queries."""
import hashlib
import hmac
import json
import logging
import re
from datetime import timedelta
from urllib.parse import urlsplit

import pycountry
from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .geography import request_country
from .models import LivePresence
from .traffic import BOT

logger = logging.getLogger(__name__)
SESSION_PATTERN = re.compile(r"^[0-9a-f]{32}$")
ACTIVE_WINDOW = timedelta(minutes=2)
RETENTION = timedelta(minutes=10)


def source_name(raw):
    try:
        hostname = (urlsplit(raw).hostname or "").lower().rstrip(".")
        if hostname in {urlsplit(settings.SITE_URL).hostname, "www.elliottwavemonitor.com"}:
            return "Internal navigation"
        if hostname and re.fullmatch(r"[a-z0-9.-]{1,253}", hostname):
            return hostname
    except ValueError:
        pass
    return "Direct / unknown"


@csrf_exempt
@require_POST
def presence_ping(request):
    if not settings.TRAFFIC_STATS_ENABLED or not settings.SITE_INDEXING_ENABLED:
        return HttpResponse(status=204)
    if (request.user.is_staff or BOT.search(request.META.get("HTTP_USER_AGENT", ""))
            or request.META.get("HTTP_DNT") == "1" or request.META.get("HTTP_SEC_GPC") == "1"):
        return HttpResponse(status=204)
    if (request.META.get("HTTP_SEC_FETCH_SITE") not in (None, "same-origin")
            or request.META.get("HTTP_ORIGIN", settings.SITE_URL).rstrip("/") != settings.SITE_URL.rstrip("/")):
        return HttpResponse(status=403)
    if len(request.body) > 1024:
        return HttpResponse(status=400)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)
    session = data.get("session", "") if isinstance(data, dict) else ""
    path = data.get("path", "") if isinstance(data, dict) else ""
    if (not isinstance(session, str) or not SESSION_PATTERN.fullmatch(session)
            or not isinstance(path, str) or not path.startswith("/")
            or path.startswith(("/admin/", "/static/", "/media/", "/_pulse/"))
            or len(path) > 300 or "?" in path or "#" in path):
        return HttpResponse(status=400)
    now = timezone.now()
    digest = hmac.new(settings.SECRET_KEY.encode(), session.encode(), hashlib.sha256).hexdigest()
    source = source_name(data.get("referrer", "") if isinstance(data.get("referrer", ""), str) else "")
    country = request_country(request)
    try:
        if not LivePresence.objects.filter(session_hash=digest).update(last_seen=now, path=path, country=country):
            try:
                with transaction.atomic():
                    LivePresence.objects.create(session_hash=digest, last_seen=now, path=path,
                                                country=country, referrer=source)
            except IntegrityError:
                LivePresence.objects.filter(session_hash=digest).update(last_seen=now, path=path, country=country)
        if cache.add("live-presence-cleanup", True, 60):
            LivePresence.objects.filter(last_seen__lt=now - RETENTION).delete()
    except DatabaseError:
        logger.warning("Could not update live presence")
    return HttpResponse(status=204)


def current_presence():
    # Polling the dashboard never causes a write. Five second cache bounds DB
    # reads if several editors leave the panel open at once.
    cached = cache.get("live-presence-report")
    if cached is not None:
        return cached
    active = LivePresence.objects.filter(last_seen__gte=timezone.now() - ACTIVE_WINDOW)
    def group(field):
        return list(active.values(field).annotate(total=Count("id")).order_by("-total", field)[:8])
    countries = group("country")
    for row in countries:
        obj = pycountry.countries.get(alpha_2=row["country"]) if row["country"] else None
        row["label"] = getattr(obj, "name", "Unknown")
    result = {"active": active.count(), "pages": [{"label": row["path"], "total": row["total"]} for row in group("path")],
              "countries": countries, "sources": [{"label": row["referrer"], "total": row["total"]} for row in group("referrer")],
              "as_of": timezone.now().isoformat()}
    cache.set("live-presence-report", result, 5)
    return result
