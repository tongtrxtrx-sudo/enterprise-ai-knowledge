import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatPage } from "./ChatPage";
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

        await user.type(screen.getByLabelText("Question"), "What is in policy?");
        await user.click(screen.getByRole("button", { name: "Send" }));

        expect(await screen.findByTestId("stream-answer")).toHaveTextContent("Hello world");
        expect(await screen.findByText("upload #3, chunk #2")).toBeInTheDocument();
        expect(screen.getByTestId("stream-status")).toHaveTextContent("done");
    });
});

function renderPage() {
    return render(
        <SessionProvider initialSession={defaultSession}>
            <ChatPage />
        </SessionProvider>,
    );
}
