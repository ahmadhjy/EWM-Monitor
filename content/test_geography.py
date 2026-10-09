from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

import maxminddb
import requests
from django.core.management import call_command, CommandError
from django.test import RequestFactory, SimpleTestCase, override_settings

from .geography import country_database_status, request_country


class GeographyTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUST_PROXY_CLIENT_IP=False)
    @patch('content.geography.country_reader')
    def test_direct_address_and_spoofed_headers(self, reader):
        reader.return_value.get.return_value = {'country': {'iso_code': 'LB'}}
        request = self.factory.get('/', REMOTE_ADDR='8.8.8.8', HTTP_X_REAL_IP='1.1.1.1', HTTP_CF_IPCOUNTRY='US')
        self.assertEqual(request_country(request), 'LB')
        reader.return_value.get.assert_called_once_with('8.8.8.8')

    @override_settings(TRUST_PROXY_CLIENT_IP=True)
    @patch('content.geography.country_reader')
    def test_trusted_nginx_address_and_ipv6(self, reader):
        reader.return_value.get.return_value = {'country': {'iso_code': 'SA'}}
        request = self.factory.get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP='2606:4700:4700::1111')
        self.assertEqual(request_country(request), 'SA')
        reader.return_value.get.assert_called_once_with('2606:4700:4700::1111')

    @override_settings(TRUST_PROXY_CLIENT_IP=False)
    @patch('content.geography.country_reader')
    def test_private_invalid_and_missing_addresses_are_unknown(self, reader):
        for address in ('127.0.0.1', '192.168.0.1', '::1', '', 'not-an-ip'):
            self.assertEqual(request_country(self.factory.get('/', REMOTE_ADDR=address)), '')
        reader.assert_not_called()

    @override_settings(TRUST_PROXY_CLIENT_IP=False)
    @patch('content.geography.country_reader')
    def test_missing_corrupt_and_unknown_database_fail_open(self, reader):
        request = self.factory.get('/', REMOTE_ADDR='8.8.8.8')
        reader.return_value = None
        self.assertEqual(request_country(request), '')
        reader.return_value = MagicMock()
        reader.return_value.get.side_effect = maxminddb.InvalidDatabaseError('Corrupt')
        self.assertEqual(request_country(request), '')
        reader.return_value.get.side_effect = None
        for record in (None, {}, {'country': {'iso_code': 'XX'}}):
            reader.return_value.get.return_value = record
            self.assertEqual(request_country(request), '')

    @override_settings(TRAFFIC_COUNTRY_DATABASE='')
    def test_unconfigured_database_state(self):
        self.assertEqual(country_database_status(), {'active': False})

    @patch('content.management.commands.update_country_database.requests.get', side_effect=requests.ConnectionError('offline'))
    def test_download_failure_preserves_existing_database(self, download):
        with TemporaryDirectory() as directory:
            database = Path(directory) / 'country.mmdb'
            database.write_bytes(b'previous-database')
            with override_settings(TRAFFIC_COUNTRY_DATABASE=str(database)):
                with self.assertRaisesMessage(CommandError, 'existing database was preserved'):
                    call_command('update_country_database')
            self.assertEqual(database.read_bytes(), b'previous-database')
