#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly K6_DIR="${ROOT_DIR}/infra/k6"

fct_execute_this() {
    local target_base_url="${TARGET_BASE_URL:-http://host.docker.internal:8080}"
    printf '[step] run k6 smoke checks against %s\n' "${target_base_url}"

    MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker run --rm -i \
        -e TARGET_BASE_URL="${target_base_url}" \
        -e SMOKE_TARGET_RPS="${SMOKE_TARGET_RPS:-20}" \
        -e SMOKE_DURATION="${SMOKE_DURATION:-30s}" \
        -e SMOKE_PREALLOCATED_VUS="${SMOKE_PREALLOCATED_VUS:-20}" \
        -e SMOKE_MAX_VUS="${SMOKE_MAX_VUS:-80}" \
        -v "${K6_DIR}:/scripts:ro" \
        grafana/k6:0.57.0 run /scripts/smoke.js

    printf '[done] k6 smoke checks passed\n'
}

fct_main() {
    fct_execute_this "$@"
}

fct_main "$@"
