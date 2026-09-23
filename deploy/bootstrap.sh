#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run as root"; exit 1; }
APP_DIR=/var/www/ewm
id ewm >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/ewm --shell /usr/sbin/nologin ewm
usermod -aG www-data ewm
install -d -o ewm -g www-data -m 0755 "$APP_DIR"
install -d -m 0755 /var/www/acme
if [[ ! -d "$APP_DIR/.git" ]]; then
    runuser -u ewm -- git clone https://github.com/ahmadhjy/EWM-Monitor.git "$APP_DIR"
fi
cd "$APP_DIR"
if [[ ! -f /etc/ewm.env ]]; then
    db_password="$(openssl rand -hex 32)"
    secret_key="$(openssl rand -hex 40)"
    runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "CREATE USER ewm WITH PASSWORD '$db_password';"
    runuser -u postgres -- createdb --owner ewm ewm
    umask 0027
    printf '%s\n' "DEBUG=False" "SECRET_KEY=$secret_key" "ALLOWED_HOSTS=165.227.156.218,127.0.0.1,localhost,elliottwavemonitor.com,www.elliottwavemonitor.com" "SITE_URL=https://165.227.156.218" "DATABASE_URL=postgresql://ewm:$db_password@127.0.0.1:5432/ewm" "SECURE_SSL_REDIRECT=True" "CSRF_TRUSTED_ORIGINS=https://165.227.156.218" "SITE_INDEXING_ENABLED=False" "TRUST_PROXY_CLIENT_IP=True" "TIME_ZONE=Asia/Beirut" "CONTACT_EMAIL_NOTIFICATIONS=False" > /etc/ewm.env
    chown root:ewm /etc/ewm.env
    chmod 0640 /etc/ewm.env
    unset db_password secret_key
fi
set -a
source /etc/ewm.env
set +a
runuser -u ewm -- python3 -m venv "$APP_DIR/.venv"
runuser -u ewm -- "$APP_DIR/.venv/bin/pip" install --disable-pip-version-check --upgrade pip
runuser -u ewm -- "$APP_DIR/.venv/bin/pip" install --disable-pip-version-check -r requirements.txt
install -d -o ewm -g www-data -m 0755 "$APP_DIR/media" "$APP_DIR/staticfiles"
runuser -u ewm -- "$APP_DIR/.venv/bin/python" manage.py migrate --noinput
if [[ ! -f /var/lib/ewm/content-imported ]]; then
    runuser -u ewm -- "$APP_DIR/.venv/bin/python" manage.py loaddata data/production_content.json
    touch /var/lib/ewm/content-imported
fi
runuser -u ewm -- "$APP_DIR/.venv/bin/python" manage.py collectstatic --noinput
runuser -u ewm -- "$APP_DIR/.venv/bin/python" manage.py check --deploy
if [[ ! -f /root/ewm-admin-access.txt ]]; then
    export DJANGO_SUPERUSER_USERNAME=ewmadmin
    export DJANGO_SUPERUSER_EMAIL=elliottwavemonitor@gmail.com
    export DJANGO_SUPERUSER_PASSWORD="$(openssl rand -base64 24)"
    runuser -u ewm -- "$APP_DIR/.venv/bin/python" manage.py createsuperuser --noinput
    umask 0077
    printf 'URL: https://165.227.156.218/admin/\nUsername: ewmadmin\nPassword: %s\n' "$DJANGO_SUPERUSER_PASSWORD" > /root/ewm-admin-access.txt
    unset DJANGO_SUPERUSER_PASSWORD
fi
install -m 0644 deploy/ewm.service /etc/systemd/system/
install -m 0750 deploy/update.sh /usr/local/sbin/ewm-deploy
install -m 0750 deploy/backup.sh /usr/local/sbin/ewm-backup
install -m 0644 deploy/ewm-backup.service deploy/ewm-backup.timer /etc/systemd/system/
install -m 0644 deploy/certbot-renew.service deploy/certbot-renew.timer /etc/systemd/system/
install -m 0644 deploy/nginx-proxy.conf /etc/nginx/snippets/ewm-proxy.conf
systemctl daemon-reload
systemctl enable --now ewm.service ewm-backup.timer certbot-renew.timer
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
systemctl enable --now fail2ban
echo "Application prepared. Install the IP certificate and Nginx configuration next."
