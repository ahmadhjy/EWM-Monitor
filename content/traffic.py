"""Aggregate page views, without visitor identifiers, cookies or tracking JS."""
import logging
import re
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import TrafficDaily
from .geography import request_country

BOT = re.compile(r"bot|spider|crawl|slurp|headless|lighthouse|python|curl|wget|monitor|preview|facebookexternalhit", re.I)
logger = logging.getLogger(__name__)


class TrafficMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not settings.TRAFFIC_STATS_ENABLED or not settings.SITE_INDEXING_ENABLED:
            return response
        match = request.resolver_match
        agent = request.META.get("HTTP_USER_AGENT", "")
        if (
            request.method != "GET" or response.status_code != 200
            or "text/html" not in response.get("Content-Type", "")
            or not match or match.url_name not in {"home", "content_detail", "search", "contact"}
            or request.user.is_staff or not agent or BOT.search(agent)
            or request.META.get("HTTP_DNT") == "1" or request.META.get("HTTP_SEC_GPC") == "1"
            or request.META.get("HTTP_SEC_FETCH_DEST", "document") != "document"
        ):
            return response
        today = timezone.localdate()
        referrer = "Direct / unknown"
        try:
            hostname = (urlsplit(request.META.get("HTTP_REFERER", "")).hostname or "").lower().rstrip(".")
            own_hosts = {urlsplit(settings.SITE_URL).hostname, "www.elliottwavemonitor.com", "elliottwavemonitor.com", "165.227.156.218"}
            if hostname in own_hosts:
                referrer = "Internal navigation"
            elif hostname and re.fullmatch(r"[a-z0-9.-]{1,253}", hostname):
                referrer = hostname
        except ValueError:
            pass
        device = "Tablet" if re.search(r"ipad|tablet", agent, re.I) else "Mobile" if re.search(r"mobile|android|iphone", agent, re.I) else "Desktop"
        bucket = dict(date=today, path=request.path[:300], language="en" if request.path.startswith("/en/") else "ar", device=device, referrer=referrer, country=request_country(request))
        try:
            if not TrafficDaily.objects.filter(**bucket).update(views=F("views") + 1):
                try:
                    with transaction.atomic():
                        TrafficDaily.objects.create(**bucket)
                except IntegrityError:
                    TrafficDaily.objects.filter(**bucket).update(views=F("views") + 1)
            if cache.add(f"traffic-retention:{today}", True, 86400):
                TrafficDaily.objects.filter(date__lt=today - timedelta(days=settings.TRAFFIC_STATS_RETENTION_DAYS)).delete()
        except DatabaseError:
            # Analytics must never prevent someone reading the public website.
            logger.warning("Could not update aggregate traffic statistics")
        return response
