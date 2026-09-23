#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${EWM_APP_DIR:-/var/www/ewm}"
APP_USER="${EWM_APP_USER:-ewm}"
BRANCH="${EWM_BRANCH:-main}"
exec 9>/run/lock/ewm-deploy.lock
flock -n 9 || { echo "Another EWM deployment is running." >&2; exit 1; }

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this command as root." >&2
    exit 1
fi

set -a
source /etc/ewm.env
set +a

if [[ -x /usr/local/sbin/ewm-backup ]]; then
    /usr/local/sbin/ewm-backup
fi

sudo -u "${APP_USER}" git -C "${APP_DIR}" fetch --prune origin
sudo -u "${APP_USER}" git -C "${APP_DIR}" checkout "${BRANCH}"
sudo -u "${APP_USER}" git -C "${APP_DIR}" pull --ff-only origin "${BRANCH}"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --disable-pip-version-check --requirement "${APP_DIR}/requirements.txt"
runuser -u "${APP_USER}" -- "${APP_DIR}/.venv/bin/python" "${APP_DIR}/manage.py" check --deploy
runuser -u "${APP_USER}" -- "${APP_DIR}/.venv/bin/python" "${APP_DIR}/manage.py" migrate --noinput
runuser -u "${APP_USER}" -- "${APP_DIR}/.venv/bin/python" "${APP_DIR}/manage.py" collectstatic --noinput

systemctl restart ewm.service
systemctl reload nginx.service

for attempt in {1..15}; do
    if curl --fail --silent --show-error --unix-socket /run/ewm/gunicorn.sock --header "Host: 165.227.156.218" --header "X-Forwarded-Proto: https" http://localhost/health/ >/dev/null; then
        echo "EWM deployment is healthy."
        exit 0
    fi
    sleep 1
done

journalctl --unit ewm.service --lines 60 --no-pager >&2
exit 1
