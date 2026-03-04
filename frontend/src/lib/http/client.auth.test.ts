import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpError, configureAuthRuntime, listVisibleFiles } from "./client";

function jsonResponse(body: unknown, status: number): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: {
            "Content-Type": "application/json",
        },
    });
}

describe("authenticated request lifecycle", () => {
    afterEach(() => {
        configureAuthRuntime(null);
        vi.restoreAllMocks();
    });

    it("recovers from 401 by refreshing token and retrying", async () => {
        const refreshAccessToken = vi.fn().mockResolvedValue("fresh-token");
        const onUnauthorized = vi.fn();
        configureAuthRuntime({
            getAccessToken: () => "stale-token",
            refreshAccessToken,
            onUnauthorized,
        });

        const fetchMock = vi
            .spyOn(globalThis, "fetch")
            .mockResolvedValueOnce(new Response("", { status: 401 }))
            .mockResolvedValueOnce(
                jsonResponse(
                    [
                        {
                            id: 1,
                            folder: "/knowledge",
                            filename: "guide.md",
                            owner_id: 1,
                            is_public: false,
                            parse_status: "normal",
                        },
                    ],
                    200,
                ),
            );

        const rows = await listVisibleFiles("stale-token");
        expect(rows).toHaveLength(1);
        expect(refreshAccessToken).toHaveBeenCalledTimes(1);
        expect(onUnauthorized).not.toHaveBeenCalled();
        expect(fetchMock).toHaveBeenCalledTimes(2);

        const retryRequest = fetchMock.mock.calls[1];
        expect(retryRequest).toBeDefined();
        const retryOptions = retryRequest?.[1] as RequestInit;
        const headers = new Headers(retryOptions.headers);
        expect(headers.get("Authorization")).toBe("Bearer fresh-token");
    });

    it("clears session when refresh cannot recover unauthorized request", async () => {
        const refreshAccessToken = vi.fn().mockResolvedValue(null);
        const onUnauthorized = vi.fn();
        configureAuthRuntime({
            getAccessToken: () => "expired-token",
            refreshAccessToken,
            onUnauthorized,
        });

        vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 401 }));

        await expect(listVisibleFiles("expired-token")).rejects.toMatchObject<HttpError>({
            status: 401,
            message: "Unauthorized",
        });
        expect(onUnauthorized).toHaveBeenCalledTimes(1);
    });
});
