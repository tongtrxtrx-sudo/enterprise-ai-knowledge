import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpError } from "../http/client";
import { SessionProvider, useSession } from "./sessionStore";

const {
    loginWithPasswordMock,
    fetchSessionProfileMock,
    refreshAccessTokenMock,
    logoutCurrentSessionMock,
} = vi.hoisted(() => ({
    loginWithPasswordMock: vi.fn(),
    fetchSessionProfileMock: vi.fn(),
    refreshAccessTokenMock: vi.fn(),
    logoutCurrentSessionMock: vi.fn(),
}));

vi.mock("../http/client", async () => {
    const actual = await vi.importActual<typeof import("../http/client")>("../http/client");
    return {
        ...actual,
        loginWithPassword: loginWithPasswordMock,
        fetchSessionProfile: fetchSessionProfileMock,
        refreshAccessToken: refreshAccessTokenMock,
        logoutCurrentSession: logoutCurrentSessionMock,
    };
});

describe("SessionProvider authentication lifecycle", () => {
    beforeEach(() => {
        localStorage.clear();
        vi.clearAllMocks();
    });

    it("logs in with backend auth and persists access token", async () => {
        loginWithPasswordMock.mockResolvedValue({
            access_token: "access-1",
            refresh_token: "refresh-1",
            token_type: "bearer",
        });
        fetchSessionProfileMock.mockResolvedValue({
            user: {
                id: 1,
                username: "alice",
                role: "user",
                department: "knowledge",
            },
            permissions: {
                can_upload: true,
                can_view_versions: true,
                can_edit_file: true,
                can_access_admin: false,
            },
        });

        renderProvider();
        const user = userEvent.setup();
        await user.click(screen.getByRole("button", { name: "login" }));

        expect(await screen.findByTestId("username")).toHaveTextContent("alice");
        expect(localStorage.getItem("kb_access_token")).toBe("access-1");
    });

    it("recovers expired token by refresh during bootstrap", async () => {
        localStorage.setItem("kb_access_token", "expired-token");
        fetchSessionProfileMock
            .mockRejectedValueOnce(new HttpError("Unauthorized", 401))
            .mockResolvedValueOnce({
                user: {
                    id: 2,
                    username: "root",
                    role: "admin",
                    department: "knowledge",
                },
                permissions: {
                    can_upload: true,
                    can_view_versions: true,
                    can_edit_file: true,
                    can_access_admin: true,
                },
            });
        refreshAccessTokenMock.mockResolvedValue({
            access_token: "fresh-token",
            refresh_token: "refresh-2",
            token_type: "bearer",
        });

        renderProvider();

        await waitFor(() => {
            expect(screen.getByTestId("username")).toHaveTextContent("root");
        });
        expect(refreshAccessTokenMock).toHaveBeenCalledTimes(1);
        expect(localStorage.getItem("kb_access_token")).toBe("fresh-token");
    });
});

function SessionProbe() {
    const { session, login } = useSession();

    return (
        <div>
            <button
                type="button"
                onClick={() => {
                    void login("alice", "password123");
                }}
            >
                login
            </button>
            <p data-testid="username">{session?.user.username ?? "anonymous"}</p>
        </div>
    );
}

function renderProvider() {
    return render(
        <SessionProvider initialSession={null}>
            <SessionProbe />
        </SessionProvider>,
    );
}
