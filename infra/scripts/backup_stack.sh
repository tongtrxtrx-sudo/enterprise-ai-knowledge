#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly COMPOSE_FILE="${ROOT_DIR}/infra/docker-compose.yml"
readonly ENV_FILE="${ROOT_DIR}/.env.example"
readonly BACKUP_ROOT="${ROOT_DIR}/infra/backups"

fct_require_tools() {
    command -v docker >/dev/null 2>&1 || {
        printf 'docker command is required\n' >&2
        exit 1
    }
}

fct_backup_postgres() {
    local backup_dir="$1"
    printf '[backup] PostgreSQL schema and data\n'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T postgres sh -c \
        'pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc' >"${backup_dir}/postgres.dump"
}

fct_backup_redis() {
    local backup_dir="$1"
    printf '[backup] Redis cache snapshot\n'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T redis sh -c \
        'redis-cli --rdb /data/dump.rdb >/tmp/redis-rdb.log && cat /tmp/redis-rdb.log'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" cp \
        redis:/data/dump.rdb "${backup_dir}/redis.rdb"
}

fct_backup_minio() {
    local backup_dir="$1"
    printf '[backup] MinIO object store data\n'
    mkdir -p "${backup_dir}/minio-data"
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" cp \
        minio:/data/. "${backup_dir}/minio-data"
}

fct_write_manifest() {
    local backup_dir="$1"
    {
        printf 'created_at=%s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        printf 'postgres_dump=postgres.dump\n'
        printf 'redis_snapshot=redis.rdb\n'
        printf 'minio_archive=minio-data/\n'
    } >"${backup_dir}/manifest.env"
}

fct_execute_this() {
    local backup_name="${1:-manual-$(date -u +"%Y%m%dT%H%M%SZ")}"
    local backup_dir="${BACKUP_ROOT}/${backup_name}"

    fct_require_tools
    mkdir -p "${backup_dir}"

    fct_backup_postgres "${backup_dir}"
    fct_backup_redis "${backup_dir}"
    fct_backup_minio "${backup_dir}"
    fct_write_manifest "${backup_dir}"

    printf '[done] backup stored at %s\n' "${backup_dir}"
}

fct_main() {
    fct_execute_this "$@"
}

fct_main "$@"
