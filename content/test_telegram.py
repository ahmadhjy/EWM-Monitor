from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

import requests
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Article, Category, TelegramAnnouncement


@override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHANNEL_ID="@examplechannel",
                   SITE_URL="https://elliottwavemonitor.com")
class TelegramDispatchTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="News", slug="news")

    def article(self, slug="new-report", **kwargs):
        return Article.objects.create(title="New market report", slug=slug,
                                      body="<p>Analysis</p>", category=self.category, **kwargs)

    def api_success(self):
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {"ok": True, "result": {"message_id": 42}}
        return response

    @patch("content.telegram.requests.post")
    def test_one_first_publish_never_reposts_after_edits(self, post):
        post.return_value = self.api_success()
        article = self.article(status="draft")
        call_command("dispatch_telegram", stdout=StringIO())
        post.assert_not_called()
        article.status = "published"
        article.save(update_fields=["status"])
        call_command("dispatch_telegram", stdout=StringIO())
        self.assertEqual(TelegramAnnouncement.objects.get(article=article).status, "sent")
        self.assertEqual(TelegramAnnouncement.objects.get(article=article).message_id, 42)
        self.assertIn("https://elliottwavemonitor.com/en/new-report/", post.call_args.kwargs["json"]["text"])
        self.assertEqual(post.call_args.kwargs["json"]["chat_id"], "@examplechannel")
        article.title = "Updated headline"
        article.save(update_fields=["title"])
        call_command("dispatch_telegram", stdout=StringIO())
        self.assertEqual(post.call_count, 1)

    @patch("content.telegram.requests.post")
    def test_arabic_translation_uses_arabic_link(self, post):
        post.return_value = self.api_success()
        self.article(slug="arabic-report", status="published", title_ar="تحليل جديد", body_ar="<p>تحليل</p>")
        call_command("dispatch_telegram", stdout=StringIO())
        text = post.call_args.kwargs["json"]["text"]
        self.assertIn("تحليل جديد", text)
        self.assertIn("https://elliottwavemonitor.com/arabic-report/", text)
        self.assertNotIn("/en/", text)

    @patch("content.telegram.requests.post")
    def test_future_and_historical_articles_are_not_sent(self, post):
        post.return_value = self.api_success()
        future = self.article(slug="future", status="published", published_at=timezone.now() + timedelta(days=1))
        old = self.article(slug="historical", status="published")
        TelegramAnnouncement.objects.create(article=old, status="historical")
        call_command("dispatch_telegram", stdout=StringIO())
        post.assert_not_called()
        future.published_at = timezone.now() - timedelta(seconds=1)
        future.save(update_fields=["published_at"])
        call_command("dispatch_telegram", stdout=StringIO())
        self.assertEqual(post.call_count, 1)

    @patch("content.telegram.requests.post", side_effect=requests.Timeout("private URL with test-token"))
    def test_ambiguous_timeout_is_not_retried(self, post):
        article = self.article(status="published")
        call_command("dispatch_telegram", stdout=StringIO())
        record = TelegramAnnouncement.objects.get(article=article)
        self.assertEqual(record.status, "uncertain")
        self.assertNotIn("test-token", record.last_error)
        call_command("dispatch_telegram", stdout=StringIO())
        self.assertEqual(post.call_count, 1)

    @patch("content.telegram.requests.post")
    def test_explicit_failure_backoff_and_dry_run(self, post):
        response = Mock(ok=False, status_code=403)
        response.json.return_value = {"ok": False, "description": "not an admin"}
        post.return_value = response
        article = self.article(status="published")
        call_command("dispatch_telegram", "--dry-run", stdout=StringIO())
        post.assert_not_called()
        self.assertFalse(TelegramAnnouncement.objects.filter(article=article).exists())
        call_command("dispatch_telegram", stdout=StringIO())
        record = TelegramAnnouncement.objects.get(article=article)
        self.assertEqual(record.status, "failed")
        self.assertGreater(record.next_attempt_at, timezone.now())
        call_command("dispatch_telegram", stdout=StringIO())
        self.assertEqual(post.call_count, 1)

    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHANNEL_ID="")
    @patch("content.telegram.requests.post")
    def test_missing_configuration_is_inert(self, post):
        article = self.article(status="published")
        call_command("dispatch_telegram", stdout=StringIO())
        self.assertFalse(TelegramAnnouncement.objects.filter(article=article).exists())
        post.assert_not_called()
