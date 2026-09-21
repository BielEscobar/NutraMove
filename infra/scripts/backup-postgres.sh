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
db_target="$backup_root/daily/nutramove-$stamp.dump"
uploads_target="$backup_root/daily/private_uploads_$stamp.tar.gz"
[[ ! -e "$db_target" && ! -e "$uploads_target" ]] || {
  echo "A backup for this timestamp already exists." >&2
  exit 1
}
db_tmp="$(mktemp "$backup_root/daily/.nutramove-XXXXXXXX.dump")"
uploads_tmp="$(mktemp "$backup_root/daily/.private_uploads-XXXXXXXX.tar.gz")"
backend_stopped=false
complete=false
cleanup() {
  status=$?
  trap - EXIT
  rm -f -- "$db_tmp" "$uploads_tmp"
  if [[ "$complete" != true ]]; then
    rm -f -- "$db_target" "$db_target.sha256" "$uploads_target" "$uploads_target.sha256"
  fi
  if [[ "$backend_stopped" == true ]]; then
    if ! "${compose[@]}" up -d --wait backend >/dev/null; then
      echo "Backend restart failed; investigate immediately." >&2
      status=1
    fi
  fi
  exit "$status"
}
trap cleanup EXIT

backend_container="$("${compose[@]}" ps -q backend)"
[[ -n "$backend_container" && "$(docker inspect --format '{{.State.Running}}' "$backend_container")" == true ]] || {
  echo "A running backend is required to identify the private uploads volume." >&2
  exit 1
}
backend_image="$(docker inspect --format '{{.Image}}' "$backend_container")"
uploads_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/app/private_uploads"}}{{.Name}}{{end}}{{end}}' "$backend_container")"
[[ -n "$backend_image" && -n "$uploads_volume" ]] || {
  echo "Backend image or private uploads volume was not found." >&2
  exit 1
}

# Quiesce writes so the database dump and private files represent one backup window.
backend_stopped=true
"${compose[@]}" stop -t 60 backend >/dev/null
"${compose[@]}" exec -T db sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges' > "$db_tmp"
[[ -s "$db_tmp" ]]
"${compose[@]}" exec -T db pg_restore --list < "$db_tmp" > /dev/null
MSYS_NO_PATHCONV=1 docker run --rm --network none --read-only -v "$uploads_volume:/source:ro" "$backend_image" \
  python -m app.cli.private_uploads_archive create /source > "$uploads_tmp"
[[ -s "$uploads_tmp" ]]
tar -tzf "$uploads_tmp" > /dev/null

mv -- "$db_tmp" "$db_target"
mv -- "$uploads_tmp" "$uploads_target"
sha256sum "$db_target" > "$db_target.sha256"
sha256sum "$uploads_target" > "$uploads_target.sha256"
"${compose[@]}" up -d --wait backend >/dev/null
backend_stopped=false
complete=true

if [[ "$(date -u +%u)" == "7" ]]; then
  for target in "$db_target" "$uploads_target"; do
    cp -- "$target" "$backup_root/weekly/$(basename "$target")"
    cp -- "$target.sha256" "$backup_root/weekly/$(basename "$target.sha256")"
  done
fi

# Provisional technical retention only; the controller must approve legal retention.
find "$backup_root/daily" -maxdepth 1 -type f -name 'nutramove-*.dump*' -mtime +6 -delete
find "$backup_root/weekly" -maxdepth 1 -type f -name 'nutramove-*.dump*' -mtime +27 -delete
find "$backup_root/daily" -maxdepth 1 -type f -name 'private_uploads_*.tar.gz*' -mtime +6 -delete
find "$backup_root/weekly" -maxdepth 1 -type f -name 'private_uploads_*.tar.gz*' -mtime +27 -delete
echo "Backup pair created: $db_target and $uploads_target"
