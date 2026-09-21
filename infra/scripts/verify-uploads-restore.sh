#!/usr/bin/env bash
set -euo pipefail

infra_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${NUTRAMOVE_ENV_FILE:-$infra_dir/.env.prod}"
backup_file="${1:?Pass an existing private_uploads_*.tar.gz file}"
compose=(docker compose --env-file "$env_file" -f "$infra_dir/compose.prod.yaml")

[[ -f "$env_file" && -f "$backup_file" ]] || {
  echo "Production env or upload backup is missing." >&2
  exit 1
}
backup_file="$(realpath "$backup_file")"
docker_backup_file="$backup_file"
if command -v cygpath >/dev/null 2>&1; then
  docker_backup_file="$(cygpath -w "$backup_file")"
fi
if [[ -f "$backup_file.sha256" ]]; then
  expected_hash="$(cut -d ' ' -f 1 < "$backup_file.sha256")"
  actual_hash="$(sha256sum "$backup_file" | cut -d ' ' -f 1)"
  [[ "$expected_hash" == "$actual_hash" ]] || {
    echo "Upload backup checksum mismatch." >&2
    exit 1
  }
fi

backend_container="$("${compose[@]}" ps -q backend)"
[[ -n "$backend_container" ]] || {
  echo "A backend container is required to identify the approved image." >&2
  exit 1
}
backend_image="$(docker inspect --format '{{.Image}}' "$backend_container")"
[[ -n "$backend_image" ]] || exit 1

# The label allows cleanup to remove only the volume created by this invocation.
temporary_volume="nutramove-verify-uploads-$(date -u +%Y%m%d%H%M%S)-$$"
docker volume create --label "nutramove.verify_restore=$temporary_volume" "$temporary_volume" >/dev/null
cleanup() {
  status=$?
  trap - EXIT
  label="$(docker volume inspect --format '{{index .Labels "nutramove.verify_restore"}}' "$temporary_volume" 2>/dev/null || true)"
  if [[ "$label" == "$temporary_volume" ]]; then
    docker volume rm "$temporary_volume" >/dev/null || status=1
  fi
  exit "$status"
}
trap cleanup EXIT

# This container mounts only the new temporary volume and the read-only archive.
# It never mounts private_uploads_prod or accesses the network.
MSYS_NO_PATHCONV=1 docker run --rm --network none --read-only --user 0:0 \
  -v "$temporary_volume:/restore" \
  --mount "type=bind,source=$docker_backup_file,target=/backup.tar.gz,readonly" \
  "$backend_image" python -m app.cli.private_uploads_archive verify /backup.tar.gz /restore
