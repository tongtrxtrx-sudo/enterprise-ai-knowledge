import { useMemo, useState } from "react";

import { useI18n } from "../../i18n";
import { streamChat, type Citation } from "../../lib/http/client";
import { useSession } from "../../lib/state/sessionStore";

export function ChatPage() {
    const { session } = useSession();
    const { t } = useI18n();
    const [query, setQuery] = useState("");
    const [answer, setAnswer] = useState("");
    const [citations, setCitations] = useState<Citation[]>([]);
    const [status, setStatus] = useState("idle");

    const canSend = useMemo(() => Boolean(session && query.trim().length > 0), [query, session]);
    const localizedStatus = t(`chat.status.${status}`);

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
                <h2>{t("chat.title")}</h2>
                <p className="muted">{t("chat.description")}</p>
                <label htmlFor="chat-query">{t("chat.question")}</label>
                <textarea
                    id="chat-query"
                    rows={4}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={t("chat.placeholder")}
                />
                <button type="button" onClick={() => void submitChat()} disabled={!canSend}>
                    {t("chat.send")}
                </button>
            </div>
            <div className="card">
                <h3>{t("chat.streamResult")}</h3>
                <p data-testid="stream-status">{t("chat.status", { status: localizedStatus })}</p>
                <pre data-testid="stream-answer">{answer || t("chat.empty")}</pre>
            </div>
            <div className="card">
                <h3>{t("chat.citations")}</h3>
                {citations.length === 0 ? (
                    <p className="muted">{t("chat.noCitations")}</p>
                ) : (
                    <ul>
                        {citations.map((item, index) => (
                            <li key={`${item.upload_id}-${item.chunk_index}-${index}`}>
                                {t("chat.citationItem", {
                                    uploadId: item.upload_id,
                                    chunkIndex: item.chunk_index,
                                })}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
