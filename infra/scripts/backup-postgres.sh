#!/usr/bin/env bash
set -euo pipefail

infra_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${NUTRAMOVE_ENV_FILE:-$infra_dir/.env.prod}"
backup_root="${NUTRAMOVE_BACKUP_DIR:-/srv/nutramove/backups}"
compose=(docker compose --env-file "$env_file" -f "$infra_dir/compose.prod.yaml")

if [[ ! -f "$env_file" || "$backup_root" != /* ]]; then
  echo "Production env file and an absolute backup directory are required." >&2
  exit 1
fi

umask 077
mkdir -p "$backup_root/daily" "$backup_root/weekly"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="$backup_root/daily/nutramove-$stamp.dump"
tmp="$(mktemp "$backup_root/daily/.nutramove-XXXXXXXX.dump")"
trap 'rm -f -- "$tmp"' EXIT

"${compose[@]}" exec -T db sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges' > "$tmp"
[[ -s "$tmp" ]]
"${compose[@]}" exec -T db pg_restore --list < "$tmp" > /dev/null
mv -- "$tmp" "$target"
trap - EXIT
sha256sum "$target" > "$target.sha256"

if [[ "$(date -u +%u)" == "7" ]]; then
  cp -- "$target" "$backup_root/weekly/$(basename "$target")"
  cp -- "$target.sha256" "$backup_root/weekly/$(basename "$target.sha256")"
fi

# Provisional technical retention only; the controller must approve legal retention.
find "$backup_root/daily" -maxdepth 1 -type f -name 'nutramove-*.dump*' -mtime +6 -delete
find "$backup_root/weekly" -maxdepth 1 -type f -name 'nutramove-*.dump*' -mtime +27 -delete
echo "Backup created: $target"
