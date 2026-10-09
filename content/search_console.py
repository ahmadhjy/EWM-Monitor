"""Read-only, server-side Search Console reports. No credentials in the browser."""
from datetime import timedelta
from functools import partial
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
import pycountry
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


PAGE_SIZE = 10


def page_number(value):
    try:
        number = int(value)
        return number if 1 <= number <= 1000000 else 1
    except (TypeError, ValueError):
        return 1


def search_report(days, queries_page=1, pages_page=1, countries_page=1):
    queries_page, pages_page = page_number(queries_page), page_number(pages_page)
    countries_page = page_number(countries_page)
    # Search Console dates use Pacific time, independently of the site timezone.
    end = timezone.localdate(timezone=ZoneInfo("America/Los_Angeles")) - timedelta(days=3)
    start = end - timedelta(days=days - 1)
    result = {"status": "not_connected", "start": start, "end": end, "property": settings.SEARCH_CONSOLE_PROPERTY}
    if not settings.SEARCH_CONSOLE_CREDENTIALS:
        return result
    try:
        credential_path = Path(settings.SEARCH_CONSOLE_CREDENTIALS)
        key = "search-console:v3:" + hashlib.sha256(f"{settings.SEARCH_CONSOLE_PROPERTY}:{credential_path}:{credential_path.stat().st_mtime_ns}:{end}:{days}:{queries_page}:{pages_page}:{countries_page}".encode()).hexdigest()
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
        def query(dimensions, limit, offset=0):
            response = requests.post(url, headers={"Authorization": "Bearer " + credentials.token}, json={"startDate": str(start), "endDate": str(end), "dimensions": dimensions, "rowLimit": limit, "startRow": offset, "type": "web", "dataState": "final"}, timeout=(5, 12))
            response.raise_for_status()
            return response.json().get("rows", [])
        # Un-dimensioned query supplies property totals, not sums of top queries.
        totals = query([], 1)
        # One extra row detects a next page without guessing a total Google
        # does not provide. The next request overlaps only that lookahead row.
        queries = query(["query"], PAGE_SIZE + 1, (queries_page - 1) * PAGE_SIZE)
        pages = query(["page"], PAGE_SIZE + 1, (pages_page - 1) * PAGE_SIZE)
        countries = query(["country"], PAGE_SIZE + 1, (countries_page - 1) * PAGE_SIZE)
        for row in countries[:PAGE_SIZE]:
            code = (row.get("keys") or [""])[0].upper()
            country = pycountry.countries.get(alpha_3=code)
            row["country_name"] = getattr(country, "name", code or "Unknown")
            row["ctr_percent"] = row.get("ctr", 0) * 100
        result.update(status="connected", totals=totals[0] if totals else None,
                      queries=queries[:PAGE_SIZE], pages=pages[:PAGE_SIZE], countries=countries[:PAGE_SIZE],
                      queries_has_next=len(queries) > PAGE_SIZE,
                      pages_has_next=len(pages) > PAGE_SIZE,
                      countries_has_next=len(countries) > PAGE_SIZE)
        cache.set(key, result, 1800)
        return result
    except Exception:
        # Never expose keys, tokens, raw Google error bodies or credential paths.
        result.update(status="unavailable", message="Google data is unavailable. Check property verification, service-account access and the enabled Search Console API.")
        if 'key' in locals():
            cache.set(key, result, 300)
        return result
