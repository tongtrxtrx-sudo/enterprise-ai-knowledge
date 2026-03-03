import http from "k6/http";
import { check, sleep } from "k6";

const targetBaseUrl = __ENV.TARGET_BASE_URL || "http://127.0.0.1:8080";

export const options = {
    scenarios: {
        smoke_traffic: {
            executor: "constant-arrival-rate",
            rate: Number(__ENV.SMOKE_TARGET_RPS || 20),
            timeUnit: "1s",
            duration: __ENV.SMOKE_DURATION || "30s",
            preAllocatedVUs: Number(__ENV.SMOKE_PREALLOCATED_VUS || 20),
            maxVUs: Number(__ENV.SMOKE_MAX_VUS || 80),
        },
    },
    thresholds: {
        http_req_failed: ["rate<0.01"],
        http_req_duration: ["p(95)<500"],
        checks: ["rate>0.99"],
    },
};

export default function () {
    const response = http.get(`${targetBaseUrl}/health`, {
        tags: { endpoint: "health" },
    });

    check(response, {
        "health returns 200": (r) => r.status === 200,
        "health includes service_name": (r) => r.json("service_name") !== undefined,
        "health includes version": (r) => r.json("version") !== undefined,
    });

    sleep(0.1);
}
