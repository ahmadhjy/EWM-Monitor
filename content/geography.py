"""Offline country lookup. Never persist addresses or call a geolocation API."""
from datetime import datetime, timezone as datetime_timezone
from functools import lru_cache
from ipaddress import ip_address
from pathlib import Path

import maxminddb
import pycountry
from django.conf import settings
from django.utils import timezone


@lru_cache(maxsize=1)
def _open_reader(path, modified):
    # Reader is thread-safe; a file replacement creates a fresh cached reader.
    return maxminddb.open_database(path)


def country_reader():
    if not settings.TRAFFIC_COUNTRY_DATABASE:
        return None
    try:
        path = Path(settings.TRAFFIC_COUNTRY_DATABASE)
        return _open_reader(str(path), path.stat().st_mtime_ns)
    except (OSError, ValueError, maxminddb.InvalidDatabaseError):
        return None


def request_country(request):
    address = request.META.get("REMOTE_ADDR", "")
    if settings.TRUST_PROXY_CLIENT_IP:
        # Only enable behind our nginx, which overwrites X-Real-IP. Do not trust
        # arbitrary CF-IPCountry/X-Forwarded-For headers sent by a visitor.
        address = request.META.get("HTTP_X_REAL_IP", address)
    try:
        ip = ip_address(address)
        if not ip.is_global:
            return ""
        reader = country_reader()
        if reader is None:
            return ""
        code = ((reader.get(str(ip)) or {}).get("country", {}).get("iso_code") or "").upper()
        return code if pycountry.countries.get(alpha_2=code) else ""
    except (OSError, ValueError, TypeError, AttributeError, maxminddb.InvalidDatabaseError):
        return ""


def country_database_status():
    reader = country_reader()
    if reader is None:
        return {"active": False}
    try:
        built = datetime.fromtimestamp(reader.metadata().build_epoch, datetime_timezone.utc)
        return {"active": True, "date": built.date(), "stale": (timezone.now() - built).days > 62}
    except (OSError, ValueError, maxminddb.InvalidDatabaseError):
        return {"active": False}
