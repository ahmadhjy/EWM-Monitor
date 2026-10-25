"""At-most-once-oriented Telegram delivery for newly public articles."""
import time
from datetime import timedelta

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone, translation

from .models import Article, TelegramAnnouncement


def configured():
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHANNEL_ID)


def queue_new_publications(now=None):
    """Find public articles, leaving the migration-marked archive untouched."""
    now = now or timezone.now()
    eligible = Article.objects.filter(status="published", published_at__lte=now,
                                      telegram_announcement__isnull=True)
    count = 0
    for article_id in eligible.values_list("pk", flat=True).iterator():
        _, created = TelegramAnnouncement.objects.get_or_create(article_id=article_id)
        count += created
    return count


def message_for(article):
    with translation.override("en"):
        url = settings.SITE_URL + article.get_absolute_url()
    return f"{article.title.strip()}\n\n{url}"


def send_announcement(announcement_id):
    """Claim before sending. Ambiguous outcomes require review, never blind retry."""
    now = timezone.now()
    with transaction.atomic():
        item = TelegramAnnouncement.objects.select_for_update().select_related("article").get(pk=announcement_id)
        if item.status not in ("pending", "failed") or item.next_attempt_at > now:
            return "skipped"
        if item.article.status != "published" or item.article.published_at > now:
            return "skipped"
        item.status = "sending"
        item.attempts += 1
        item.last_error = ""
        item.save(update_fields=["status", "attempts", "last_error"])

    # The token only appears in the HTTPS request URL, never in stored errors.
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": settings.TELEGRAM_CHANNEL_ID, "text": message_for(item.article)},
            timeout=(3, 10),
        )
    except requests.RequestException:
        TelegramAnnouncement.objects.filter(pk=item.pk, status="sending").update(
            status="uncertain", last_error="Network outcome unknown. Check the channel before retrying."
        )
        return "uncertain"

    try:
        data = response.json()
    except ValueError:
        data = None
    result = data.get("result") if isinstance(data, dict) else None
    if response.ok and isinstance(data, dict) and data.get("ok") is True and isinstance(result, dict):
        TelegramAnnouncement.objects.filter(pk=item.pk, status="sending").update(
            status="sent", sent_at=timezone.now(), message_id=result.get("message_id"), last_error=""
        )
        return "sent"

    if response.status_code >= 500 or data is None or (isinstance(data, dict) and data.get("ok") is True):
        TelegramAnnouncement.objects.filter(pk=item.pk, status="sending").update(
            status="uncertain", last_error="Telegram outcome unknown. Check the channel before retrying."
        )
        return "uncertain"

    delay = min(6 * 3600, 300 * (2 ** min(item.attempts - 1, 6)))
    retry_after = (data.get("parameters") or {}).get("retry_after") if isinstance(data, dict) else None
    if isinstance(retry_after, int) and 0 < retry_after <= 86400:
        delay = max(delay, retry_after)
    reason = data.get("description", "Telegram rejected the request") if isinstance(data, dict) else "Telegram rejected the request"
    reason = str(reason).replace(settings.TELEGRAM_BOT_TOKEN, "[redacted]")
    TelegramAnnouncement.objects.filter(pk=item.pk, status="sending").update(
        status="failed", next_attempt_at=timezone.now() + timedelta(seconds=delay),
        last_error=reason[:300],
    )
    return "failed"


def dispatch(limit=5):
    queue_new_publications()
    ids = list(TelegramAnnouncement.objects.filter(
        status__in=("pending", "failed"), next_attempt_at__lte=timezone.now(),
    ).order_by("created_at", "pk").values_list("pk", flat=True)[:limit])
    outcomes = []
    for index, announcement_id in enumerate(ids):
        if index:
            time.sleep(1.1)  # Stay below Telegram's per-chat rate guidance.
        outcomes.append(send_announcement(announcement_id))
    return outcomes
