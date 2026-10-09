from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import TrafficDaily
from .search_console import PAGE_SIZE, page_number, search_report
from .geography import country_database_status
import pycountry


@admin.register(TrafficDaily)
class StatisticsAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            raise PermissionDenied
        try:
            days = int(request.GET.get("days", 28))
        except ValueError:
            days = 28
        if days not in (7, 28, 90):
            days = 28
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)
        rows = TrafficDaily.objects.filter(date__gte=start, date__lte=today)
        totals = rows.aggregate(views=Sum("views"))
        daily = dict(rows.values("date").annotate(total=Sum("views")).values_list("date", "total"))
        peak = max(daily.values(), default=1) or 1
        trend = [{"date": start + timedelta(days=n), "views": daily.get(start + timedelta(days=n), 0)} for n in range(days)]
        for point in trend:
            point["height"] = round(point["views"] / peak * 100, 2)
        def grouped(field):
            return list(rows.values(field).annotate(total=Sum("views")).order_by("-total", field)[:10])
        pages = grouped("path")
        for page in pages:
            page["url"] = settings.SITE_URL + page["path"]
        queries_page = page_number(request.GET.get("queries_page", 1))
        pages_page = page_number(request.GET.get("pages_page", 1))
        countries_page = page_number(request.GET.get("countries_page", 1))
        traffic_countries_page = page_number(request.GET.get("traffic_countries_page", 1))
        google = search_report(days, queries_page=queries_page, pages_page=pages_page, countries_page=countries_page)
        def pagination(kind, number, label):
            params = {"days": days, "queries_page": queries_page, "pages_page": pages_page, "countries_page": countries_page, "traffic_countries_page": traffic_countries_page}
            def link(target):
                return "?" + urlencode({**params, kind + "_page": target}) + "#google-" + kind
            count = len(google.get(kind, []))
            return {"number": number, "label": label,
                    "start": (number - 1) * PAGE_SIZE + 1 if count else 0,
                    "end": (number - 1) * PAGE_SIZE + count if count else 0,
                    "previous": link(number - 1) if number > 1 else None,
                    "first": link(1) if number > 1 else None,
                    "next": link(number + 1) if google.get(kind + "_has_next") else None}
        if google.get("totals"):
            google["totals"]["ctr_percent"] = google["totals"].get("ctr", 0) * 100
        def distribution(field):
            values = grouped(field)
            total = totals["views"] or 0
            for row in values:
                row["percent"] = round(row["total"] / total * 100, 1) if total else 0
            return values
        country_rows = list(rows.values("country").annotate(total=Sum("views")).order_by("-total", "country"))
        for row in country_rows:
            country = pycountry.countries.get(alpha_2=row["country"]) if row["country"] else None
            row["name"] = getattr(country, "name", "Unknown")
            row["percent"] = round(row["total"] / (totals["views"] or 1) * 100, 1)
        traffic_country_page = Paginator(country_rows, PAGE_SIZE).get_page(traffic_countries_page)
        traffic_countries_page = traffic_country_page.number
        traffic_pagination = pagination("traffic_countries", traffic_countries_page, "Website countries")
        traffic_pagination.update(start=traffic_country_page.start_index(), end=traffic_country_page.end_index())
        if traffic_country_page.has_next():
            params = {"days": days, "queries_page": queries_page, "pages_page": pages_page, "countries_page": countries_page, "traffic_countries_page": traffic_country_page.next_page_number()}
            traffic_pagination["next"] = "?" + urlencode(params) + "#google-traffic_countries"
        context = {
            **self.admin_site.each_context(request), "title": "Statistics", "opts": self.model._meta,
            "days": days, "start": start, "end": today, "ranges": (7, 28, 90),
            "views": totals["views"] or 0, "today_views": daily.get(today, 0),
            "page_count": rows.values("path").distinct().count(), "trend": trend,
            "top_pages": pages, "referrers": grouped("referrer"), "devices": distribution("device"),
            "languages": distribution("language"), "google": google,
            "queries_pagination": pagination("queries", queries_page, "Search queries"),
            "pages_pagination": pagination("pages", pages_page, "Google pages"),
            "countries_pagination": pagination("countries", countries_page, "Google countries"),
            "traffic_countries": traffic_country_page,
            "traffic_countries_pagination": traffic_pagination,
            "country_count": sum(1 for row in country_rows if row["country"]),
            "geography": country_database_status(),
            "tracking_enabled": settings.TRAFFIC_STATS_ENABLED and settings.SITE_INDEXING_ENABLED,
            "TIME_ZONE": settings.TIME_ZONE,
        }
        return TemplateResponse(request, "admin/content/statistics.html", context)
