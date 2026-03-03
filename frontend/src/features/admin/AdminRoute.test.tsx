import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createAppRoutes } from "../../app/router";
import { defaultSession } from "../../lib/state/sessionStore";
import { renderWithRouter } from "../../test/utils";

vi.mock("../../lib/http/client", async () => {
    const actual = await vi.importActual<typeof import("../../lib/http/client")>(
        "../../lib/http/client",
    );
    return {
        ...actual,
        listAdminUsers: vi.fn().mockResolvedValue([]),
        listDepartments: vi.fn().mockResolvedValue([]),
        listFolderPermissions: vi.fn().mockResolvedValue([]),
        listAuditStates: vi.fn().mockResolvedValue([]),
    };
});

describe("admin route guard", () => {
    it("redirects non-admin user to forbidden page", async () => {
        const nonAdmin = {
            ...defaultSession,
            permissions: {
                ...defaultSession.permissions,
                canAccessAdmin: false,
            },
            user: {
                ...defaultSession.user,
                role: "user" as const,
            },
        };

        renderWithRouter(createAppRoutes(), {
            initialPath: "/admin",
            session: nonAdmin,
        });

        expect(await screen.findByText("Forbidden")).toBeInTheDocument();
    });

    it("allows admin user to open admin state pages", async () => {
        renderWithRouter(createAppRoutes(), {
            initialPath: "/admin",
            session: defaultSession,
        });

        expect(await screen.findByText("Admin Console")).toBeInTheDocument();
        expect(screen.getByText("Users")).toBeInTheDocument();
        expect(screen.getByText("Permissions")).toBeInTheDocument();
        expect(screen.getByText("Audit")).toBeInTheDocument();
    });
});
