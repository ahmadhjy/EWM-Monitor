# DigitalOcean deployment runbook

This project is designed for a small Ubuntu Droplet with Nginx, Gunicorn, Python 3.12+, PostgreSQL, and Certbot. The repository also includes a tested update command, daily PostgreSQL/media backups, and GitHub checks for every change.

## Current public-IP preview

- Preview: https://165.227.156.218/ (Arabic), https://165.227.156.218/en/ (English).
- Admin: https://165.227.156.218/admin/ (always English/LTR).
- The IP has a trusted Let's Encrypt short-lived certificate. Certbot is installed at /opt/certbot/bin/certbot; certbot-renew.timer checks twice daily. Its renewal dry run passed.
- Nginx uses nginx-ip.conf plus nginx-proxy.conf. HTTP redirects to HTTPS. The production environment has DEBUG=False, PostgreSQL, secure cookies and SITE_INDEXING_ENABLED=False.
- IP staging is deliberately noindex with robots disallow. Do not enable indexing, change the domain, or replace canonical URLs until the owner approves the domain launch.
- The production admin password is generated separately, stored outside Git in /root/ewm-admin-access.txt, and supplied privately to the owner. Rotate it on handover.
- Contact messages and subscriber addresses are stored in the admin. CONTACT_EMAIL_NOTIFICATIONS=False; SMTP and outbound campaigns are not configured.
- Daily server-local backups retain 14 days. Arrange an off-server backup destination before relying on them for disaster recovery.

The steps below also document a fresh rebuild. Do not re-import the public fixture during routine updates because editors may have changed content.

## 1. Prepare the server

Install Python, PostgreSQL, Nginx, Git, Certbot, and the Nginx Certbot integration. Create a dedicated unprivileged `ewm` service user and place the project at `/var/www/ewm`.

Create a virtual environment and install `requirements.txt`. Create a PostgreSQL database and user with a long generated password.

## 2. Production environment

Create `/etc/ewm.env`, readable only by the `ewm` user and root:

```dotenv
DEBUG=False
SECRET_KEY=generate-a-long-random-value
ALLOWED_HOSTS=elliottwavemonitor.com,www.elliottwavemonitor.com
SITE_URL=https://elliottwavemonitor.com
DATABASE_URL=postgresql://ewm:replace-password@127.0.0.1:5432/ewm
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://elliottwavemonitor.com,https://www.elliottwavemonitor.com
TIME_ZONE=Asia/Beirut
```

Never reuse the local `.env` or local admin password.

## 3. Initialize the release

Activate the production virtual environment, then run:

```bash
python manage.py check --deploy
python manage.py migrate
python manage.py loaddata data/production_content.json
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

The production fixture contains only public/editorial data. It intentionally excludes users, contact messages, and newsletter subscribers. Copy the verified local `media/` directory separately, then create a new production administrator password. Do not run the WordPress import again unless a deliberate content refresh is intended.

## 4. Services

Copy `deploy/ewm.service` to `/etc/systemd/system/ewm.service`, adjust user/group paths if needed, reload systemd, and enable the service.

Copy `deploy/nginx.conf` to `/etc/nginx/sites-available/elliottwavemonitor.com`, enable it, verify the Nginx configuration, and reload Nginx.

Install the maintenance commands:

```bash
sudo install -m 0750 deploy/update.sh /usr/local/sbin/ewm-deploy
sudo install -m 0750 deploy/backup.sh /usr/local/sbin/ewm-backup
sudo install -m 0644 deploy/ewm-backup.service /etc/systemd/system/
sudo install -m 0644 deploy/ewm-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ewm-backup.timer
```

For the later domain launch, obtain the domain certificate only after the owner approves DNS cutover and its A/AAAA records resolve correctly. Keep the IP certificate and staging configuration until then. Configure the domain certificate using the installed Certbot, update SITE_URL/ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS, preserve HTTPS and rate limits, and only then enable indexing and remove the staging X-Robots-Tag.

```bash
sudo /opt/certbot/bin/certbot certonly --webroot -w /var/www/acme -d elliottwavemonitor.com -d www.elliottwavemonitor.com
```

## 5. Pre-DNS launch checklist

- Crawl the old and new URL inventories and compare status codes, titles, canonicals, index directives, headings, and image responses.
- Confirm the 20 migrated article slugs and 12 market/education archive slugs remain unchanged.
- Add explicit redirects for any URL intentionally changed.
- Test article creation, image upload, scheduled publishing, search, contact form, newsletter capture, sitemap, feed, `robots.txt`, and `llms.txt`.
- Configure transactional email before relying on contact notifications; messages are always retained in the admin.
- Set analytics/consent configuration only after legal approval. Third-party scripts can affect performance.
- Run Lighthouse from an external location after Nginx, TLS, and DNS/CDN are active.
- Create automated daily PostgreSQL and media backups and test a restore.
- Keep the old Bluehost site available but unmodified until DNS propagation and the final crawl are complete.

## 6. Operations

After reviewed changes are pushed to `main`, update production with:

```bash
sudo ewm-deploy
```

That command creates a backup, fast-forwards the repository, installs pinned dependencies, applies migrations, rebuilds static assets, restarts the service, and refuses to report success until the health endpoint responds. Inspect backup scheduling with `systemctl list-timers ewm-backup.timer`.

Content imports are intentionally not part of ewm-deploy. The full legal source can be restored explicitly with populate_support_pages --overwrite after a backup; routine releases preserve admin edits and collected messages/subscribers.

To verify the latest backup without touching production data, run `sudo bash deploy/verify-backup.sh` from the checkout. It checks archive hashes, reads the media archive, restores PostgreSQL into a uniquely named disposable database, verifies table counts and removes only that temporary database. This restore test passed on the live Droplet.
