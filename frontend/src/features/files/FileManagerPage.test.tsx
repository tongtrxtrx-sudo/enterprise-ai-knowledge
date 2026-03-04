import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FileManagerPage } from "./FileManagerPage";
import { I18nProvider } from "../../i18n";
import { SessionProvider, defaultSession } from "../../lib/state/sessionStore";

const { listVisibleFilesMock } = vi.hoisted(() => ({
    listVisibleFilesMock: vi.fn(),
}));

vi.mock("../../lib/http/client", async () => {
    const actual = await vi.importActual<typeof import("../../lib/http/client")>(
        "../../lib/http/client",
    );
    return {
        ...actual,
        listVisibleFiles: listVisibleFilesMock,
        listFileVersions: vi.fn().mockResolvedValue([]),
        uploadFile: vi.fn(),
        startEditSession: vi.fn(),
        submitEditSaveCallback: vi.fn(),
    };
});

describe("FileManagerPage", () => {
    it("disables upload and version actions by permissions", async () => {
        listVisibleFilesMock.mockResolvedValue([
            {
                id: 9,
                folder: "/knowledge",
                filename: "guide.md",
                owner_id: 1,
                is_public: false,
                parse_status: "normal",
            },
        ]);

        const restrictedSession = {
            ...defaultSession,
            permissions: {
                canUpload: false,
                canViewVersions: false,
                canEditFile: false,
                canAccessAdmin: false,
            },
            user: {
                ...defaultSession.user,
                role: "user" as const,
            },
        };

        render(
            <I18nProvider>
                <SessionProvider initialSession={restrictedSession}>
                    <FileManagerPage />
                </SessionProvider>
            </I18nProvider>,
        );

        await waitFor(() => {
            expect(screen.getByText("guide.md - 正常")).toBeInTheDocument();
        });

        expect(screen.getByLabelText("上传文件")).toBeDisabled();
        expect(screen.getByRole("button", { name: "版本" })).toBeDisabled();
        expect(screen.getByRole("button", { name: "编辑" })).toBeDisabled();
    });
});
