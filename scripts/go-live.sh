#!/usr/bin/env bash
set -Eeuo pipefail

# 脚本说明：一键执行上线 + 冒烟验证
# 用法示例：
#   BOOTSTRAP_ADMIN_USERNAME=admin BOOTSTRAP_ADMIN_PASSWORD='Strong#Pass1' bash scripts/go-live.sh --init-admin --smoke

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly COMPOSE_FILE="${ROOT_DIR}/infra/docker-compose.yml"
readonly ENV_FILE="${ROOT_DIR}/.env.production"
readonly HEALTH_URL="http://127.0.0.1:8080/health"
readonly LOGIN_URL="http://127.0.0.1:8080/api/auth/login"
readonly ADMIN_USERS_URL="http://127.0.0.1:8080/api/admin/users"
readonly ADMIN_DEPTS_URL="http://127.0.0.1:8080/api/admin/departments"
readonly ADMIN_AUDIT_URL="http://127.0.0.1:8080/api/admin/audit-states"
readonly UPLOAD_URL="http://127.0.0.1:8080/api/uploads"
readonly CHAT_URL="http://127.0.0.1:8080/api/chat/stream"

fct_usage() {
    printf '%s\n' "Usage:"
    printf '%s\n' "  scripts/go-live.sh [--no-build] [--init-admin] [--smoke] [--no-smoke]"
    printf '%s\n' ""
    printf '%s\n' "Options:"
    printf '%s\n' "  --no-build    Start services without rebuilding images"
    printf '%s\n' "  --init-admin  Bootstrap admin user (requires env vars below)"
    printf '%s\n' "  --smoke       Run authenticated smoke checks (default)"
    printf '%s\n' "  --no-smoke    Skip smoke checks"
    printf '%s\n' ""
    printf '%s\n' "Required env for --init-admin and --smoke login:"
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

fct_require_admin_env() {
    if [[ -z "${BOOTSTRAP_ADMIN_USERNAME:-}" || -z "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
        printf '%s\n' "Error: BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD are required." >&2
        exit 1
    fi
}

fct_bootstrap_admin() {
    fct_require_admin_env

    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T backend \
        sh -lc "BOOTSTRAP_ADMIN_USERNAME='${BOOTSTRAP_ADMIN_USERNAME}' BOOTSTRAP_ADMIN_PASSWORD='${BOOTSTRAP_ADMIN_PASSWORD}' python /app/scripts/bootstrap_admin.py"
}

fct_smoke_login_and_token() {
    # 登录并提取 access token，供后续接口验证使用
    local login_payload
    login_payload="{\"username\":\"${BOOTSTRAP_ADMIN_USERNAME}\",\"password\":\"${BOOTSTRAP_ADMIN_PASSWORD}\"}"

    local login_resp
    login_resp="$(curl -sS -c /tmp/kb_cookies.txt -H "Content-Type: application/json" -d "${login_payload}" "${LOGIN_URL}")"

    ACCESS_TOKEN="$(python -c "import json,sys; print(json.loads(sys.argv[1])['access_token'])" "${login_resp}")"
    if [[ -z "${ACCESS_TOKEN}" ]]; then
        printf '%s\n' "Error: failed to obtain access token from login response." >&2
        exit 1
    fi
}

fct_smoke_admin_apis() {
    # 核心管理接口检查：用户、部门、审计
    curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" "${ADMIN_USERS_URL}" >/dev/null
    curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" "${ADMIN_DEPTS_URL}" >/dev/null
    curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" "${ADMIN_AUDIT_URL}" >/dev/null
}

fct_smoke_upload_and_versions_and_edit() {
    # 上传 -> 版本查询 -> 编辑启动链路
    local tmp_file
    local smoke_name
    local upload_resp
    local upload_id

    tmp_file="$(mktemp)"
    smoke_name="smoke-$(date +%s).txt"
    printf '%s\n' "go-live smoke content" >"${tmp_file}"

    upload_resp="$(curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -F "folder=knowledge" \
        -F "filename=${smoke_name}" \
        -F "file=@${tmp_file}" \
        "${UPLOAD_URL}")"
    rm -f "${tmp_file}"

    upload_id="$(python -c "import json,sys; print(json.loads(sys.argv[1])['upload_id'])" "${upload_resp}")"
    if [[ -z "${upload_id}" ]]; then
        printf '%s\n' "Error: upload_id missing in upload response." >&2
        exit 1
    fi

    curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" "${UPLOAD_URL}/${upload_id}/versions" >/dev/null
    curl -sS -X POST -H "Authorization: Bearer ${ACCESS_TOKEN}" "http://127.0.0.1:8080/api/files/${upload_id}/edit/start" >/dev/null
}

fct_smoke_chat_sse() {
    # 对话流式接口检查：必须能收到 done 事件
    local sse_resp
    sse_resp="$(curl -sS -N -H "Authorization: Bearer ${ACCESS_TOKEN}" -H "Content-Type: application/json" -d '{"query":"smoke test","public_query":false}' "${CHAT_URL}")"
    if ! printf '%s\n' "${sse_resp}" | grep -E '"type"[[:space:]]*:[[:space:]]*"done"' >/dev/null; then
        printf '%s\n' "Error: chat SSE did not return done event." >&2
        exit 1
    fi
}

fct_run_smoke() {
    fct_require_admin_env
    printf '%s\n' "Running smoke checks..."
    fct_smoke_login_and_token
    fct_smoke_admin_apis
    fct_smoke_upload_and_versions_and_edit
    fct_smoke_chat_sse
    printf '%s\n' "Smoke checks passed."
}

fct_main() {
    local with_build="true"
    local init_admin="false"
    local run_smoke="true"

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
            --smoke)
                run_smoke="true"
                shift
                ;;
            --no-smoke)
                run_smoke="false"
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

    if [[ "${run_smoke}" == "true" ]]; then
        fct_run_smoke
    fi

    printf '%s\n' "Go-live command sequence finished."
}

fct_main "$@"
