from django.core.management.base import BaseCommand

from content.models import Article, TelegramAnnouncement
from content.telegram import configured, dispatch
from django.utils import timezone


class Command(BaseCommand):
    help = "Post newly published articles to the configured Telegram channel exactly once."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show eligible work without sending or changing records.")

    def handle(self, *args, **options):
        if options["dry_run"]:
            unseen = Article.objects.filter(status="published", published_at__lte=timezone.now(),
                                            telegram_announcement__isnull=True).count()
            ready = TelegramAnnouncement.objects.filter(status__in=("pending", "failed"),
                                                         next_attempt_at__lte=timezone.now()).count()
            self.stdout.write(f"Telegram configured: {'yes' if configured() else 'no'}; new: {unseen}; queued: {ready}; no messages sent.")
            return
        if not configured():
            self.stdout.write("Telegram not configured; no messages sent.")
            return
        outcomes = dispatch()
        self.stdout.write(f"Telegram dispatch: {', '.join(outcomes) if outcomes else 'nothing due'}.")
