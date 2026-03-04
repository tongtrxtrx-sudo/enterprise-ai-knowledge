#!/usr/bin/env bash
set -Eeuo pipefail

# SCRIPT INFO
# Name: go-live.sh
# Purpose: Run minimal production go-live steps.

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly COMPOSE_FILE="${ROOT_DIR}/infra/docker-compose.yml"
readonly ENV_FILE="${ROOT_DIR}/.env.production"
readonly HEALTH_URL="http://127.0.0.1:8080/health"

fct_usage() {
    printf '%s\n' "Usage:"
    printf '%s\n' "  scripts/go-live.sh [--no-build] [--init-admin]"
    printf '%s\n' ""
    printf '%s\n' "Options:"
    printf '%s\n' "  --no-build    Start services without rebuilding images"
    printf '%s\n' "  --init-admin  Bootstrap admin user (requires env vars below)"
    printf '%s\n' ""
    printf '%s\n' "Required env for --init-admin:"
    printf '%s\n' "  BOOTSTRAP_ADMIN_USERNAME"
    printf '%s\n' "  BOOTSTRAP_ADMIN_PASSWORD"
}

fct_require_command() {
    local cmd="${1}"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        printf '%s\n' "Error: command not found: ${cmd}" >&2
        exit 1
    fi
}

fct_check_env_file() {
    if [[ ! -f "${ENV_FILE}" ]]; then
        printf '%s\n' "Error: ${ENV_FILE} not found." >&2
        printf '%s\n' "Create it from .env.production.example first." >&2
        exit 1
    fi
}

fct_compose_up() {
    local with_build="${1}"
    if [[ "${with_build}" == "true" ]]; then
        docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build
    else
        docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d
    fi
}

fct_show_status() {
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps
}

fct_check_health() {
    printf '%s\n' "Checking health endpoint: ${HEALTH_URL}"
    curl -sS "${HEALTH_URL}"
    printf '\n'
}

fct_bootstrap_admin() {
    if [[ -z "${BOOTSTRAP_ADMIN_USERNAME:-}" || -z "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
        printf '%s\n' "Error: BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD are required with --init-admin." >&2
        exit 1
    fi

    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T backend \
        sh -lc "BOOTSTRAP_ADMIN_USERNAME='${BOOTSTRAP_ADMIN_USERNAME}' BOOTSTRAP_ADMIN_PASSWORD='${BOOTSTRAP_ADMIN_PASSWORD}' python /app/scripts/bootstrap_admin.py"
}

fct_main() {
    local with_build="true"
    local init_admin="false"

    while [[ $# -gt 0 ]]; do
        case "${1}" in
            --no-build)
                with_build="false"
                shift
                ;;
            --init-admin)
                init_admin="true"
                shift
                ;;
            -h|--help)
                fct_usage
                exit 0
                ;;
            *)
                printf '%s\n' "Error: unknown option: ${1}" >&2
                fct_usage
                exit 1
                ;;
        esac
    done

    fct_require_command docker
    fct_require_command curl
    fct_check_env_file

    fct_compose_up "${with_build}"
    fct_show_status
    fct_check_health

    if [[ "${init_admin}" == "true" ]]; then
        fct_bootstrap_admin
    fi

    printf '%s\n' "Go-live command sequence finished."
}

fct_main "$@"
