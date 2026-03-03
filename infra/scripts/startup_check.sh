#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly COMPOSE_FILE="${ROOT_DIR}/infra/docker-compose.yml"
readonly ENV_FILE="${ROOT_DIR}/.env.example"
readonly REQUIRED_SERVICES=("nginx" "frontend" "backend" "postgres" "redis" "minio" "onlyoffice")
readonly MAX_RETRIES="${MAX_RETRIES:-60}"
readonly SLEEP_SECONDS="${SLEEP_SECONDS:-5}"

fct_wait_for_healthy() {
    local service="$1"
    local attempt=1
    local status=""

    while (( attempt <= MAX_RETRIES )); do
        status="$(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps --format json "${service}" | python -c 'import json,sys; data=json.load(sys.stdin); rows=data if isinstance(data,list) else [data]; print(rows[0].get("Health","") if rows else "")')"
        if [[ "${status}" == "healthy" || "${status}" == "running" ]]; then
            printf '[ok] %s status: %s\n' "${service}" "${status}"
            return 0
        fi

        printf '[wait] %s status: %s (attempt %s/%s)\n' "${service}" "${status:-unknown}" "${attempt}" "${MAX_RETRIES}"
        sleep "${SLEEP_SECONDS}"
        ((attempt += 1))
    done

    printf '[fail] service did not become healthy: %s\n' "${service}" >&2
    return 1
}

fct_execute_this() {
    local service=""

    printf '[step] reset stack and named volumes\n'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" down -v --remove-orphans

    printf '[step] build images and start stack in detached mode\n'
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build

    printf '[step] verify service startup health\n'
    for service in "${REQUIRED_SERVICES[@]}"; do
        fct_wait_for_healthy "${service}"
    done

    printf '[done] all required services are healthy\n'
}

fct_main() {
    fct_execute_this "$@"
}

fct_main "$@"
