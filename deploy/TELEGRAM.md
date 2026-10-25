# Telegram article announcements

The server checks for newly public articles once per minute. Saving an article
does not wait for Telegram. Each article has one delivery record in the English
admin under **Editorial content → Telegram announcements**; later edits or
unpublish/republish cycles do not repost it. Articles that were already
published when migration `0015` ran are marked historical and never sent.
Drafts, articles with a future publication time, and scheduled-status articles
are not sent until their status is Published and the time has arrived.

The message always uses the English title and English `/en/` article URL,
even when the article also has an Arabic translation. Telegram generates the link preview
from the public article URL. No article content is copied to Telegram.

## One-time owner and server setup

1. Create a bot in Telegram using [@BotFather](https://t.me/BotFather).
   Keep its HTTP API token secret; never put it in Git, an admin text field,
   or a chat message.
2. Add the bot as an **administrator** of the desired channel with **Post
   Messages** permission. For a public channel, use its `@username` as the
   channel ID. For a private channel, use its numeric chat ID (normally
   beginning `-100`).
3. On the Droplet, as root, edit `/etc/ewm.env` and add
   `TELEGRAM_BOT_TOKEN=...` and `TELEGRAM_CHANNEL_ID=@yourchannel` (or the
   numeric ID). Keep file permissions restricted to root and the `ewm` user.
4. Install `deploy/ewm-telegram.service` and `deploy/ewm-telegram.timer` into
   `/etc/systemd/system/`, run `systemctl daemon-reload`, then
   `systemctl enable --now ewm-telegram.timer`. The timer should not be
   enabled until the bot and destination are confirmed.
5. Run `python manage.py dispatch_telegram --dry-run` as `ewm` with the
   production environment loaded. It prints counts and never sends. Then
   publish one new test article, trigger `systemctl start ewm-telegram.service`,
   and check the channel and delivery record.

Transient explicit Telegram errors retry with backoff. Network timeouts,
malformed responses, and server errors are labelled **Outcome uncertain** and
are not retried automatically: verify the channel first to avoid duplicates.
Only a superuser can explicitly queue an uncertain record again in the admin.
The service sends at most five posts per run and spaces them at least 1.1
seconds apart to respect per-channel rate guidance. Inspect failures with
`journalctl -u ewm-telegram.service` and the admin delivery record. Do not
print or log the bot token.
