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

fct_require_backup_files() {
    local backup_dir="$1"
    local required=("postgres.dump" "redis.rdb")
    local file=""

    for file in "${required[@]}"; do
        if [[ ! -f "${backup_dir}/${file}" ]]; then
            printf 'missing backup file: %s\n' "${backup_dir}/${file}" >&2
            exit 1
        fi
    done

    if [[ ! -d "${backup_dir}/minio-data" ]]; then
        printf 'missing backup directory: %s\n' "${backup_dir}/minio-data" >&2
        exit 1
    fi
}

fct_restore_postgres() {
    local backup_dir="$1"
    printf '[restore] PostgreSQL schema and data\n'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T postgres sh -c \
        'psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T postgres sh -c \
        'pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner --no-privileges' \
        <"${backup_dir}/postgres.dump"
}

fct_restore_redis() {
    local backup_dir="$1"
    printf '[restore] Redis cache snapshot\n'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T redis redis-cli FLUSHALL
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" cp \
        "${backup_dir}/redis.rdb" redis:/data/dump.rdb
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" restart redis
}

fct_restore_minio() {
    local backup_dir="$1"
    printf '[restore] MinIO object data\n'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T minio sh -c 'rm -rf /data/*'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" cp \
        "${backup_dir}/minio-data/." minio:/data
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T minio sh -c \
        'if [ -d /data/minio-data ]; then cp -r /data/minio-data/. /data/ && rm -rf /data/minio-data; fi'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" restart minio
}

fct_execute_this() {
    local backup_name="${1:-}"
    local backup_dir=""

    if [[ -z "${backup_name}" ]]; then
        printf 'usage: %s <backup-name>\n' "$(basename "$0")" >&2
        exit 1
    fi

    backup_dir="${BACKUP_ROOT}/${backup_name}"
    if [[ ! -d "${backup_dir}" ]]; then
        printf 'backup directory does not exist: %s\n' "${backup_dir}" >&2
        exit 1
    fi

    fct_require_tools
    fct_require_backup_files "${backup_dir}"

    fct_restore_postgres "${backup_dir}"
    fct_restore_redis "${backup_dir}"
    fct_restore_minio "${backup_dir}"

    printf '[done] restore completed from %s\n' "${backup_dir}"
}

fct_main() {
    fct_execute_this "$@"
}

fct_main "$@"
