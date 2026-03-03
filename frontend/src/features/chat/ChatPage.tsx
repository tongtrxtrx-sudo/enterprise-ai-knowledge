import { useMemo, useState } from "react";

import { streamChat, type Citation } from "../../lib/http/client";
import { useSession } from "../../lib/state/sessionStore";

export function ChatPage() {
    const { session } = useSession();
    const [query, setQuery] = useState("");
    const [answer, setAnswer] = useState("");
    const [citations, setCitations] = useState<Citation[]>([]);
    const [status, setStatus] = useState("idle");

    const canSend = useMemo(() => Boolean(session && query.trim().length > 0), [query, session]);

    async function submitChat() {
        if (!session || !query.trim()) {
            return;
        }
        setAnswer("");
        setCitations([]);
        setStatus("streaming");
        try {
            await streamChat(
                session.accessToken,
                {
                    query,
                    public_query: false,
                },
                (event) => {
                    if (event.type === "chunk") {
                        setAnswer((prev) => prev + event.delta);
                        setCitations(event.citations);
                        return;
                    }
                    setStatus("done");
                },
            );
        } catch {
            setStatus("error");
        }
    }

    return (
        <div>
            <div className="card">
                <h2>Chat</h2>
                <p className="muted">SSE streaming with citation rendering.</p>
                <label htmlFor="chat-query">Question</label>
                <textarea
                    id="chat-query"
                    rows={4}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Ask something from indexed documents"
                />
                <button type="button" onClick={() => void submitChat()} disabled={!canSend}>
                    Send
                </button>
            </div>
            <div className="card">
                <h3>Stream Result</h3>
                <p data-testid="stream-status">Status: {status}</p>
                <pre data-testid="stream-answer">{answer || "(empty)"}</pre>
            </div>
            <div className="card">
                <h3>Citations</h3>
                {citations.length === 0 ? (
                    <p className="muted">No citations yet</p>
                ) : (
                    <ul>
                        {citations.map((item, index) => (
                            <li key={`${item.upload_id}-${item.chunk_index}-${index}`}>
                                upload #{item.upload_id}, chunk #{item.chunk_index}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
