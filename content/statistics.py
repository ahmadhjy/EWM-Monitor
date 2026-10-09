from datetime import timedelta

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.template.response import TemplateResponse
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import TrafficDaily
from .search_console import search_report


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
        google = search_report(days)
        if google.get("totals"):
            google["totals"]["ctr_percent"] = google["totals"].get("ctr", 0) * 100
        context = {
            **self.admin_site.each_context(request), "title": "Statistics", "opts": self.model._meta,
            "days": days, "start": start, "end": today, "ranges": (7, 28, 90),
            "views": totals["views"] or 0, "today_views": daily.get(today, 0),
            "page_count": rows.values("path").distinct().count(), "trend": trend,
            "top_pages": pages, "referrers": grouped("referrer"), "devices": grouped("device"),
            "languages": grouped("language"), "google": google,
            "tracking_enabled": settings.TRAFFIC_STATS_ENABLED and settings.SITE_INDEXING_ENABLED,
            "TIME_ZONE": settings.TIME_ZONE,
        }
        return TemplateResponse(request, "admin/content/statistics.html", context)
