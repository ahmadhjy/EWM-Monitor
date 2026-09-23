#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${EWM_APP_DIR:-/var/www/ewm}"
BACKUP_DIR="${EWM_BACKUP_DIR:-/var/backups/ewm}"
RETENTION_DAYS="${EWM_BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

umask 0077
install -d -m 0700 "${BACKUP_DIR}"

set -a
source /etc/ewm.env
set +a

pg_dump --format=custom --no-owner --no-acl --file "${BACKUP_DIR}/database-${STAMP}.dump" "${DATABASE_URL}"
tar --create --gzip --file "${BACKUP_DIR}/media-${STAMP}.tar.gz" --directory "${APP_DIR}" media
sha256sum "${BACKUP_DIR}/database-${STAMP}.dump" "${BACKUP_DIR}/media-${STAMP}.tar.gz" > "${BACKUP_DIR}/checksums-${STAMP}.sha256"

find "${BACKUP_DIR}" -type f -mtime "+${RETENTION_DAYS}" -delete
