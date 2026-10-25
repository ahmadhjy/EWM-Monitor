"""Read-only Telegram bot and channel permission verification."""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Verify the configured Telegram bot can post to the channel without sending a message."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
            raise CommandError("Telegram bot token or channel ID is not configured.")
        base = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
        try:
            identity = requests.post(base + "/getMe", timeout=(3, 10)).json()
            if identity.get("ok") is not True:
                raise ValueError("Invalid bot identity")
            bot = identity["result"]
            member = requests.post(base + "/getChatMember", json={
                "chat_id": settings.TELEGRAM_CHANNEL_ID, "user_id": bot["id"],
            }, timeout=(3, 10)).json()
            if member.get("ok") is not True:
                raise ValueError("Bot is not accessible in the channel")
            rights = member["result"]
        except (requests.RequestException, ValueError, KeyError, TypeError):
            # Never expose the token-bearing request URL in an exception or log.
            raise CommandError("Could not verify Telegram settings. Check the bot token, channel ID, and admin membership.") from None
        if rights.get("status") not in ("administrator", "creator") or not rights.get("can_post_messages"):
            raise CommandError("Bot is in the channel but lacks Post Messages permission.")
        self.stdout.write(self.style.SUCCESS(
            f"Bot @{bot.get('username', 'unknown')} can post to {settings.TELEGRAM_CHANNEL_ID}. No message was sent."
        ))
