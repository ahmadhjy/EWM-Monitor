"""Read-only, server-side Search Console reports. No credentials in the browser."""
from datetime import timedelta
from functools import partial
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def search_report(days):
    # Search Console dates use Pacific time, independently of the site timezone.
    end = timezone.localdate(timezone=ZoneInfo("America/Los_Angeles")) - timedelta(days=3)
    start = end - timedelta(days=days - 1)
    result = {"status": "not_connected", "start": start, "end": end, "property": settings.SEARCH_CONSOLE_PROPERTY}
    if not settings.SEARCH_CONSOLE_CREDENTIALS:
        return result
    try:
        credential_path = Path(settings.SEARCH_CONSOLE_CREDENTIALS)
        key = "search-console:" + hashlib.sha256(f"{settings.SEARCH_CONSOLE_PROPERTY}:{credential_path}:{credential_path.stat().st_mtime_ns}:{end}:{days}".encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return cached
        from google.oauth2.service_account import Credentials
        from google.auth.transport.requests import Request
        info = json.loads(credential_path.read_text())
        if info.get("type") != "service_account" or info.get("token_uri") != "https://oauth2.googleapis.com/token":
            raise ValueError("Unsupported credentials")
        credentials = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
        credentials.refresh(partial(Request(), timeout=10))
        url = "https://www.googleapis.com/webmasters/v3/sites/" + quote(settings.SEARCH_CONSOLE_PROPERTY, safe="") + "/searchAnalytics/query"
        def query(dimensions, limit):
            response = requests.post(url, headers={"Authorization": "Bearer " + credentials.token}, json={"startDate": str(start), "endDate": str(end), "dimensions": dimensions, "rowLimit": limit, "type": "web", "dataState": "final"}, timeout=(5, 12))
            response.raise_for_status()
            return response.json().get("rows", [])
        # Un-dimensioned query supplies property totals, not sums of top queries.
        totals = query([], 1)
        result.update(status="connected", totals=totals[0] if totals else None, queries=query(["query"], 10), pages=query(["page"], 10))
        cache.set(key, result, 1800)
        return result
    except Exception:
        # Never expose keys, tokens, raw Google error bodies or credential paths.
        result.update(status="unavailable", message="Google data is unavailable. Check property verification, service-account access and the enabled Search Console API.")
        if 'key' in locals():
            cache.set(key, result, 300)
        return result
