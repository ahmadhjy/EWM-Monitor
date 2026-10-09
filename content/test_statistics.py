from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.cache import cache
from django.db import DatabaseError
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from .models import TrafficDaily
from .search_console import search_report
from .traffic import TrafficMiddleware


@override_settings(TRAFFIC_STATS_ENABLED=True, SITE_INDEXING_ENABLED=True)
class TrafficTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def count(self, path='/en/?q=private', **headers):
        request = self.factory.get(path, HTTP_USER_AGENT='Mozilla/5.0 Chrome/140', **headers)
        request.user = AnonymousUser()
        request.resolver_match = SimpleNamespace(url_name='home')
        response = TrafficMiddleware(lambda r: HttpResponse('Page'))(request)
        self.assertEqual(response.status_code, 200)

    def test_aggregate_counts_without_identifiers_or_query_strings(self):
        self.count(HTTP_REFERER='https://google.com/search?q=private', REMOTE_ADDR='192.0.2.1')
        self.count(HTTP_REFERER='https://google.com/search?q=different')
        row = TrafficDaily.objects.get()
        self.assertEqual((row.views, row.path, row.language, row.referrer), (2, '/en/', 'en', 'google.com'))
        self.assertNotIn('private', str(row.__dict__))
        self.assertNotIn('192.0.2.1', str(row.__dict__))

    def test_privacy_and_background_requests_excluded(self):
        for headers in ({'HTTP_DNT': '1'}, {'HTTP_SEC_GPC': '1'}, {'HTTP_SEC_FETCH_DEST': 'empty'}):
            self.count(**headers)
        self.assertFalse(TrafficDaily.objects.exists())

    def test_bots_staff_non_public_and_non_html_excluded(self):
        for agent, staff, route, status, content_type, method in [
            ('Googlebot', False, 'home', 200, 'text/html', 'GET'),
            ('Mozilla', True, 'home', 200, 'text/html', 'GET'),
            ('Mozilla', False, 'login', 200, 'text/html', 'GET'),
            ('Mozilla', False, 'home', 404, 'text/html', 'GET'),
            ('Mozilla', False, 'home', 200, 'application/json', 'GET'),
            ('Mozilla', False, 'home', 200, 'text/html', 'POST'),
        ]:
            request = self.factory.generic(method, '/', HTTP_USER_AGENT=agent)
            request.user = SimpleNamespace(is_staff=staff)
            request.resolver_match = SimpleNamespace(url_name=route)
            TrafficMiddleware(lambda r: HttpResponse(status=status, content_type=content_type))(request)
        self.assertFalse(TrafficDaily.objects.exists())

    @override_settings(TRAFFIC_STATS_ENABLED=False)
    def test_disabled_does_not_collect(self):
        self.count()
        self.assertFalse(TrafficDaily.objects.exists())

    def test_retention_and_internal_referrer(self):
        TrafficDaily.objects.create(date=timezone.localdate()-timedelta(days=181), path='/old/', language='ar', device='Desktop')
        self.count('/', HTTP_REFERER='https://elliottwavemonitor.com/en/')
        row = TrafficDaily.objects.get()
        self.assertEqual(row.referrer, 'Internal navigation')
        self.assertEqual(row.language, 'ar')

    def test_database_failure_does_not_break_page(self):
        with patch('content.traffic.TrafficDaily.objects.filter', side_effect=DatabaseError('offline')):
            self.count()


@override_settings(SEARCH_CONSOLE_CREDENTIALS='')
class StatisticsAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('stats-editor', is_staff=True)

    def test_anonymous_redirect_and_staff_permission(self):
        url = '/admin/content/trafficdaily/'
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.user.user_permissions.add(Permission.objects.get(codename='view_trafficdaily'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Website statistics')
        self.assertContains(response, 'Not connected')
        self.assertContains(response, 'lang="en"')
        self.assertContains(response, 'dir="ltr"')
        self.assertEqual(self.client.get(url+'add/').status_code, 403)

    def test_totals_periods_and_escaping(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        TrafficDaily.objects.create(date=timezone.localdate(), path='/en/', language='en', device='Desktop', referrer='<script>alert(1)</script>', views=7)
        TrafficDaily.objects.create(date=timezone.localdate()-timedelta(days=10), path='/', language='ar', device='Mobile', views=3)
        response = self.client.get('/admin/content/trafficdaily/?days=7')
        self.assertEqual(response.context['views'], 7)
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        response = self.client.get('/admin/content/trafficdaily/?days=invalid')
        self.assertEqual(response.context['days'], 28)
        self.assertEqual(response.context['views'], 10)


class SearchConsoleTests(TestCase):
    def setUp(self):
        cache.clear()

    @override_settings(SEARCH_CONSOLE_CREDENTIALS='')
    @patch('content.search_console.requests.post')
    def test_disconnected_does_not_call_google(self, post):
        self.assertEqual(search_report(28)['status'], 'not_connected')
        post.assert_not_called()

    @override_settings(SEARCH_CONSOLE_CREDENTIALS='/private/service-account.json')
    @patch('content.search_console.Path')
    @patch('google.oauth2.service_account.Credentials.from_service_account_info')
    @patch('content.search_console.requests.post')
    def test_connected_report_cached_and_read_only(self, post, factory, path):
        path.return_value.stat.return_value.st_mtime_ns = 1
        path.return_value.read_text.return_value = '{"type":"service_account","token_uri":"https://oauth2.googleapis.com/token"}'
        factory.return_value.token = 'test-token'
        response = MagicMock()
        response.json.return_value = {'rows': [{'clicks': 2, 'impressions': 10, 'ctr': .2, 'position': 4}]}
        post.return_value = response
        report = search_report(28)
        self.assertEqual(report['status'], 'connected')
        self.assertEqual(report['totals']['clicks'], 2)
        self.assertEqual(report['end'], timezone.localdate(timezone=ZoneInfo('America/Los_Angeles'))-timedelta(days=3))
        self.assertEqual(post.call_count, 3)
        self.assertEqual(factory.call_args.kwargs['scopes'], ['https://www.googleapis.com/auth/webmasters.readonly'])
        self.assertEqual(post.call_args_list[0].kwargs['json']['dimensions'], [])
        self.assertEqual(search_report(28)['status'], 'connected')
        self.assertEqual(post.call_count, 3)

    @override_settings(SEARCH_CONSOLE_CREDENTIALS='/private/secret-key.json')
    @patch('content.search_console.Path', side_effect=ValueError('private-secret'))
    def test_failure_does_not_expose_secrets(self, path):
        report = search_report(28)
        self.assertEqual(report['status'], 'unavailable')
        self.assertNotIn('private-secret', str(report))
        self.assertNotIn('secret-key', str(report))
