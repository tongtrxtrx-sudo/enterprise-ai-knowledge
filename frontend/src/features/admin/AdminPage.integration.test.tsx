import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminPage } from "./AdminPage";
import { SessionProvider, defaultSession } from "../../lib/state/sessionStore";

function jsonResponse(payload: unknown, status = 200): Response {
    return new Response(JSON.stringify(payload), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

describe("AdminPage integration", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("renders admin users, departments, permissions and audits from backend endpoints", async () => {
        vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
            const url = String(input);
            if (url.endsWith("/api/admin/users")) {
                return jsonResponse([
                    { id: 1, username: "admin", role: "admin", department: "knowledge", status: "active" },
                ]);
            }
            if (url.endsWith("/api/admin/departments")) {
                return jsonResponse([
                    { name: "knowledge", manager_user_id: 1, member_count: 3 },
                ]);
            }
            if (url.endsWith("/api/admin/folder-permissions")) {
                return jsonResponse([
                    { id: 8, folder: "/knowledge", grantee_user_id: 2, can_edit: true },
                ]);
            }
            if (url.endsWith("/api/admin/audit-states")) {
                return jsonResponse([
                    {
                        id: 21,
                        actor_user_id: 1,
                        action: "folder_permission_updated",
                        target_type: "folder_permission",
                        target_id: 8,
                        created_at: "2026-03-04T00:00:00Z",
                    },
                ]);
            }
            return jsonResponse({ detail: "Not found" }, 404);
        });

        render(
            <SessionProvider initialSession={defaultSession}>
                <AdminPage />
            </SessionProvider>,
        );

        await waitFor(() => {
            expect(screen.getByText("folder_permission_updated")).toBeInTheDocument();
        });
        expect(screen.getAllByText("knowledge").length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText("/knowledge")).toBeInTheDocument();
        expect(screen.getByText("active")).toBeInTheDocument();
    });

    it("shows error state when admin endpoint fails", async () => {
        vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 500 }));

        render(
            <SessionProvider initialSession={defaultSession}>
                <AdminPage />
            </SessionProvider>,
        );

        expect(await screen.findByText("Failed to load admin state")).toBeInTheDocument();
    });
});
