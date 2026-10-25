from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

import requests
from django.core.management import call_command
from django.core.management.base import CommandError
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
    def test_arabic_translation_still_uses_english_title_and_link(self, post):
        post.return_value = self.api_success()
        self.article(slug="arabic-report", status="published", title_ar="تحليل جديد", body_ar="<p>تحليل</p>")
        call_command("dispatch_telegram", stdout=StringIO())
        text = post.call_args.kwargs["json"]["text"]
        self.assertIn("New market report", text)
        self.assertNotIn("تحليل جديد", text)
        self.assertIn("https://elliottwavemonitor.com/en/arabic-report/", text)

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

    @patch("content.management.commands.check_telegram.requests.post")
    def test_read_only_connection_check(self, post):
        identity = Mock()
        identity.json.return_value = {"ok": True, "result": {"id": 123, "username": "ewm_bot"}}
        rights = Mock()
        rights.json.return_value = {"ok": True, "result": {"status": "administrator", "can_post_messages": True}}
        post.side_effect = [identity, rights]
        output = StringIO()
        call_command("check_telegram", stdout=output)
        self.assertIn("can post to @examplechannel", output.getvalue())
        self.assertEqual(post.call_count, 2)
        self.assertTrue(post.call_args.args[0].endswith("/getChatMember"))

    @patch("content.management.commands.check_telegram.requests.post")
    def test_connection_check_does_not_expose_token_on_error(self, post):
        post.side_effect = requests.Timeout("test-token")
        with self.assertRaisesMessage(CommandError, "Could not verify Telegram settings") as error:
            call_command("check_telegram", stdout=StringIO())
        self.assertNotIn("test-token", str(error.exception))
