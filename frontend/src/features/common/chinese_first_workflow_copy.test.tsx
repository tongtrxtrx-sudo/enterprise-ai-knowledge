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
        listVisibleFiles: vi.fn().mockResolvedValue([]),
        listFileVersions: vi.fn().mockResolvedValue([]),
        uploadFile: vi.fn(),
        startEditSession: vi.fn(),
        submitEditSaveCallback: vi.fn(),
        listAdminUsers: vi.fn().mockResolvedValue([]),
        listDepartments: vi.fn().mockResolvedValue([]),
        listFolderPermissions: vi.fn().mockResolvedValue([]),
        listAuditStates: vi.fn().mockResolvedValue([]),
    };
});

describe("Chinese-first workflow copy", () => {
    it("renders Chinese copy in chat and files workflows by default", async () => {
        localStorage.removeItem("kb.locale");

        renderWithRouter(createAppRoutes(), {
            initialPath: "/chat",
            session: defaultSession,
        });

        expect(await screen.findByRole("heading", { name: "智能问答" })).toBeInTheDocument();
        expect(screen.getByLabelText("问题")).toBeInTheDocument();

        renderWithRouter(createAppRoutes(), {
            initialPath: "/files",
            session: defaultSession,
        });

        expect(await screen.findByRole("heading", { name: "文件管理" })).toBeInTheDocument();
        expect(screen.getByText("上传状态：空闲")).toBeInTheDocument();
    });

    it("renders Chinese copy for admin and forbidden screens", async () => {
        localStorage.removeItem("kb.locale");

        renderWithRouter(createAppRoutes(), {
            initialPath: "/admin",
            session: defaultSession,
        });
        expect(await screen.findByRole("heading", { name: "管理控制台" })).toBeInTheDocument();

        renderWithRouter(createAppRoutes(), {
            initialPath: "/forbidden",
            session: null,
        });

        expect(await screen.findByRole("heading", { name: "无权限访问" })).toBeInTheDocument();
    });
});
