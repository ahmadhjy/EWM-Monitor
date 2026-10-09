"""Install the monthly DB-IP Lite country database, never sending visitor IPs."""
import gzip
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import maxminddb
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Download the current DB-IP Lite country database (CC BY 4.0; dashboard attribution included)."

    def handle(self, *args, **options):
        if not settings.TRAFFIC_COUNTRY_DATABASE:
            raise CommandError("Configure TRAFFIC_COUNTRY_DATABASE first.")
        destination = Path(settings.TRAFFIC_COUNTRY_DATABASE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        month = timezone.now().strftime("%Y-%m")
        url = f"https://download.db-ip.com/free/dbip-country-lite-{month}.mmdb.gz"
        try:
            with TemporaryDirectory(prefix="ewm-geo-", dir=destination.parent) as directory:
                archive = Path(directory) / "country.mmdb.gz"
                database = Path(directory) / "country.mmdb"
                with requests.get(url, stream=True, timeout=(10, 45)) as response:
                    response.raise_for_status()
                    size = 0
                    with archive.open("wb") as output:
                        for chunk in response.iter_content(65536):
                            size += len(chunk)
                            if size > 32 * 1024 * 1024:
                                raise ValueError("Download exceeds expected size.")
                            output.write(chunk)
                with gzip.open(archive, "rb") as source, database.open("wb") as output:
                    size = 0
                    while chunk := source.read(65536):
                        size += len(chunk)
                        if size > 64 * 1024 * 1024:
                            raise ValueError("Database exceeds expected size.")
                        output.write(chunk)
                with maxminddb.open_database(database) as reader:
                    if "country" not in reader.metadata().database_type.lower():
                        raise ValueError("Not a country database.")
                    if not (reader.get("8.8.8.8") or {}).get("country", {}).get("iso_code"):
                        raise ValueError("Database validation failed.")
                database.chmod(0o644)
                os.replace(database, destination)
        except (OSError, ValueError, requests.RequestException, maxminddb.InvalidDatabaseError) as error:
            raise CommandError("Country database update failed; existing database was preserved.") from error
        self.stdout.write(self.style.SUCCESS(f"Installed DB-IP Lite country database for {month}."))
