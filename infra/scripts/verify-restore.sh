#!/usr/bin/env bash
set -euo pipefail

infra_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${NUTRAMOVE_ENV_FILE:-$infra_dir/.env.prod}"
backup_file="${1:?Pass an existing .dump file}"
expected_user_id="${2:-}"
compose=(docker compose --env-file "$env_file" -f "$infra_dir/compose.prod.yaml")

[[ -f "$env_file" && -f "$backup_file" ]] || { echo "Env or backup file missing." >&2; exit 1; }
if [[ -n "$expected_user_id" && ! "$expected_user_id" =~ ^[0-9a-fA-F-]{36}$ ]]; then
  echo "Expected user id must be a UUID." >&2
  exit 1
fi
if [[ -f "$backup_file.sha256" ]]; then
  expected_hash="$(cut -d ' ' -f 1 < "$backup_file.sha256")"
  actual_hash="$(sha256sum "$backup_file" | cut -d ' ' -f 1)"
  [[ "$expected_hash" == "$actual_hash" ]] || { echo "Backup checksum mismatch." >&2; exit 1; }
fi

temporary_db="nutramove_restore_$(date -u +%Y%m%d%H%M%S)_$$"
cleanup() {
  "${compose[@]}" exec -T db sh -ec 'dropdb -U "$POSTGRES_USER" --if-exists "$1"' sh "$temporary_db" >/dev/null
}
trap cleanup EXIT

"${compose[@]}" exec -T db sh -ec 'createdb -U "$POSTGRES_USER" "$1"' sh "$temporary_db"
"${compose[@]}" exec -T db sh -ec 'exec pg_restore -U "$POSTGRES_USER" -d "$1" --no-owner --no-privileges --exit-on-error' sh "$temporary_db" < "$backup_file"

revision="$("${compose[@]}" exec -T db sh -ec 'psql -U "$POSTGRES_USER" -d "$1" -Atqc "SELECT version_num FROM alembic_version"' sh "$temporary_db" | tr -d '\r')"
users="$("${compose[@]}" exec -T db sh -ec 'psql -U "$POSTGRES_USER" -d "$1" -Atqc "SELECT count(*) FROM users"' sh "$temporary_db" | tr -d '\r')"
[[ -n "$revision" && "$users" =~ ^[0-9]+$ ]] || { echo "Restored schema validation failed." >&2; exit 1; }

if [[ -n "$expected_user_id" ]]; then
  found="$("${compose[@]}" exec -T db sh -ec 'psql -U "$POSTGRES_USER" -d "$1" -Atqc "SELECT EXISTS(SELECT 1 FROM users WHERE id = '\''$2'\'')"' sh "$temporary_db" "$expected_user_id" | tr -d '\r')"
  [[ "$found" == "t" ]] || { echo "Expected synthetic user was not restored." >&2; exit 1; }
fi

echo "Restore verified in temporary database: revision=$revision users=$users"
