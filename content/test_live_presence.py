import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .live_presence import current_presence
from .models import LivePresence


@override_settings(TRAFFIC_STATS_ENABLED=True, SITE_INDEXING_ENABLED=True,
                   SITE_URL="https://elliottwavemonitor.com")
class LivePresenceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.payload = {"session": "a" * 32, "path": "/en/news/",
                        "referrer": "https://google.com/search?q=ewm"}

    def ping(self, **headers):
        with patch("content.live_presence.request_country", return_value="US"):
            return self.client.post(reverse("presence_ping"), json.dumps(self.payload),
                                    content_type="application/json", HTTP_USER_AGENT="Mozilla/5.0",
                                    **headers)

    def test_one_active_tab_updates_without_retaining_token_or_ip(self):
        self.assertEqual(self.ping().status_code, 204)
        self.payload["path"] = "/en/gold-forecast/"
        self.assertEqual(self.ping().status_code, 204)
        self.assertEqual(LivePresence.objects.count(), 1)
        record = LivePresence.objects.get()
        self.assertNotEqual(record.session_hash, self.payload["session"])
        self.assertEqual(record.path, self.payload["path"])
        self.assertEqual(record.country, "US")
        self.assertEqual(record.referrer, "google.com")
        report = current_presence()
        self.assertEqual(report["active"], 1)
        self.assertEqual(report["pages"][0]["label"], "/en/gold-forecast/")
        self.assertEqual(report["countries"][0]["label"], "United States")

    def test_expiry_and_opt_out(self):
        self.ping()
        LivePresence.objects.update(last_seen=timezone.now() - timedelta(minutes=3))
        self.assertEqual(current_presence()["active"], 0)
        self.assertEqual(self.ping(HTTP_DNT="1").status_code, 204)
        self.assertEqual(current_presence()["active"], 0)

    def test_invalid_and_cross_site_requests(self):
        self.payload["session"] = "not-a-token"
        self.assertEqual(self.ping().status_code, 400)
        self.payload["session"] = "a" * 32
        self.assertEqual(self.ping(HTTP_ORIGIN="https://other.example").status_code, 403)
        self.assertFalse(LivePresence.objects.exists())

    def test_admin_endpoint_requires_staff_view_permission(self):
        url = reverse("admin:content_trafficdaily_live")
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create_user(username="staff", password="test-password", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 403)
