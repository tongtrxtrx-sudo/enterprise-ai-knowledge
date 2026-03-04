import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FileManagerPage } from "./FileManagerPage";
import { SessionProvider, defaultSession } from "../../lib/state/sessionStore";

function jsonResponse(payload: unknown, status = 200): Response {
    return new Response(JSON.stringify(payload), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

describe("FileManagerPage integration", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("loads files and versions from backend APIs", async () => {
        vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
            const url = String(input);
            if (url.endsWith("/api/permissions/files")) {
                return jsonResponse([
                    {
                        id: 42,
                        folder: "/knowledge",
                        filename: "guide.md",
                        owner_id: 1,
                        is_public: false,
                        parse_status: "normal",
                    },
                ]);
            }
            if (url.endsWith("/api/uploads/42/versions")) {
                return jsonResponse([
                    {
                        version_number: 2,
                        created_by: 1,
                        created_at: "2026-03-04T00:00:00Z",
                    },
                ]);
            }
            if (url.endsWith("/api/files/42/edit/start")) {
                return jsonResponse(
                    {
                        file_id: 42,
                        source_version: 2,
                        session_token: "token-1",
                        editor_config: { document: { url: "https://example.invalid" } },
                    },
                    200,
                );
            }
            if (url.endsWith("/api/files/42/edit/callback")) {
                return jsonResponse({ error: 0 });
            }
            return jsonResponse({ detail: "Not found" }, 404);
        });

        render(
            <SessionProvider initialSession={defaultSession}>
                <FileManagerPage />
            </SessionProvider>,
        );

        await waitFor(() => {
            expect(screen.getByText("guide.md - normal")).toBeInTheDocument();
        });

        await userEvent.click(screen.getByRole("button", { name: "Versions" }));
        expect(await screen.findByText("v2 by #1")).toBeInTheDocument();
    });

    it("shows file loading error when backend request fails", async () => {
        vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 500 }));

        render(
            <SessionProvider initialSession={defaultSession}>
                <FileManagerPage />
            </SessionProvider>,
        );

        expect(await screen.findByText("Failed to load files")).toBeInTheDocument();
    });
});
