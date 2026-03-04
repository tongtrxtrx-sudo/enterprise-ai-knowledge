import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatPage } from "./ChatPage";
import { I18nProvider } from "../../i18n";
import { SessionProvider, defaultSession } from "../../lib/state/sessionStore";

const { streamChatMock } = vi.hoisted(() => ({
    streamChatMock: vi.fn(),
}));

vi.mock("../../lib/http/client", async () => {
    const actual = await vi.importActual<typeof import("../../lib/http/client")>(
        "../../lib/http/client",
    );
    return {
        ...actual,
        streamChat: streamChatMock,
    };
});

describe("ChatPage", () => {
    it("streams SSE chunks and renders citations", async () => {
        streamChatMock.mockImplementation(async (_token, _payload, onEvent) => {
            onEvent({
                type: "chunk",
                delta: "Hello",
                citations: [{ upload_id: 3, chunk_index: 2 }],
                skill: "knowledge_qa",
                cache_hit: false,
            });
            onEvent({ type: "chunk", delta: " world", citations: [{ upload_id: 3, chunk_index: 2 }], skill: "knowledge_qa", cache_hit: false });
            onEvent({ type: "done" });
        });

        const user = userEvent.setup();
        renderPage();

        await user.type(screen.getByLabelText("问题"), "What is in policy?");
        await user.click(screen.getByRole("button", { name: "发送" }));

        expect(await screen.findByTestId("stream-answer")).toHaveTextContent("Hello world");
        expect(await screen.findByText("上传 #3，分块 #2")).toBeInTheDocument();
        expect(screen.getByTestId("stream-status")).toHaveTextContent("完成");
    });
});

function renderPage() {
    return render(
        <I18nProvider>
            <SessionProvider initialSession={defaultSession}>
                <ChatPage />
            </SessionProvider>
        </I18nProvider>,
    );
}
