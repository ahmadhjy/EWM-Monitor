#!/usr/bin/env bash
set -Eeuo pipefail

# Restore into a disposable database only, never into the production database.
[[ "${EUID}" -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
BACKUP_DIR=/var/backups/ewm
CHECKSUM_FILE="$(find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'checksums-*.sha256' -printf '%f\n' | sort | tail -1)"
[[ "${CHECKSUM_FILE}" =~ ^checksums-([0-9]{8}T[0-9]{6}Z)\.sha256$ ]] || { echo "No valid backup manifest found." >&2; exit 1; }
STAMP="${BASH_REMATCH[1]}"
sha256sum --check "${BACKUP_DIR}/${CHECKSUM_FILE}"
tar --list --gzip --file "${BACKUP_DIR}/media-${STAMP}.tar.gz" >/dev/null

CHECK_DB="ewm_restorecheck_$(date +%s)_$$"
runuser -u postgres -- createdb --template=template0 "${CHECK_DB}"
trap 'runuser -u postgres -- dropdb --if-exists "${CHECK_DB}"' EXIT
cat "${BACKUP_DIR}/database-${STAMP}.dump" | runuser -u postgres -- pg_restore --exit-on-error --no-owner --no-privileges --dbname="${CHECK_DB}"
runuser -u postgres -- psql --no-psqlrc --set ON_ERROR_STOP=on --dbname="${CHECK_DB}" --command="SELECT 'articles' AS collection, count(*) FROM content_article UNION ALL SELECT 'pages', count(*) FROM content_page UNION ALL SELECT 'media', count(*) FROM content_mediaasset;"
echo "Backup checksums, media archive and isolated PostgreSQL restore verified."
