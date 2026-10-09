#!/usr/bin/env bash
# Run after approved DNS cutover, a database/media backup and certificate issuance.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
exec 9>/run/lock/ewm-deploy.lock
flock -n 9 || { echo 'Another deployment is running.' >&2; exit 1; }
APP_DIR=/var/www/ewm
DOMAIN=elliottwavemonitor.com
test -s "/etc/letsencrypt/live/$DOMAIN/privkey.pem"
openssl x509 -checkend 86400 -noout -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
for key in SITE_URL SITE_INDEXING_ENABLED CSRF_TRUSTED_ORIGINS; do
    grep -q "^$key=" /etc/ewm.env || { echo "Missing environment key: $key" >&2; exit 1; }
done
backup_dir=$(mktemp -d /root/ewm-domain-launch.XXXXXX)
chmod 700 "$backup_dir"
cp -a /etc/ewm.env "$backup_dir/ewm.env"
cp -a /etc/nginx/sites-available/ewm "$backup_dir/nginx-ewm"
rollback() {
    trap - ERR
    cp -a "$backup_dir/ewm.env" /etc/ewm.env
    cp -a "$backup_dir/nginx-ewm" /etc/nginx/sites-available/ewm
    systemctl restart ewm.service
    nginx -t && systemctl reload nginx.service
    echo "Launch failed; previous app and Nginx settings restored from $backup_dir" >&2
    exit 1
}
trap rollback ERR
install -m 0644 "$APP_DIR/deploy/cloudflare-realip.conf" /etc/nginx/snippets/ewm-cloudflare-realip.conf
install -m 0644 "$APP_DIR/deploy/nginx-domain.conf" /etc/nginx/sites-available/ewm
sed -i \
    -e 's|^SITE_URL=.*|SITE_URL=https://elliottwavemonitor.com|' \
    -e 's|^SITE_INDEXING_ENABLED=.*|SITE_INDEXING_ENABLED=True|' \
    -e 's|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://elliottwavemonitor.com,https://www.elliottwavemonitor.com,https://165.227.156.218|' \
    /etc/ewm.env
set -a
source /etc/ewm.env
set +a
runuser -u ewm -- "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" check --deploy
nginx -t
systemctl restart ewm.service
systemctl reload nginx.service
healthy=false
for attempt in {1..15}; do
    if curl --fail --silent --show-error --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/health/" >/dev/null; then
        healthy=true
        break
    fi
    sleep 1
done
[[ "$healthy" == true ]]
curl --fail --silent --show-error --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/robots.txt" | grep -q "Sitemap: https://$DOMAIN/sitemap.xml"
trap - ERR
echo "Domain HTTPS and indexing enabled. Rollback files retained in $backup_dir"
