from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.chat_service import ChatService
from app.db import get_db_session
from app.deps import get_current_user
from app.indexing.embedding import embed_texts
from app.indexing.retrieval import hybrid_rrf_search
from app.permissions.service import get_retrieval_principals
from app.schemas.chat import ChatStreamRequest


router = APIRouter(prefix="/chat", tags=["chat"])
_chat_service = ChatService()


def _yield_text_chunks(text: str, *, chunk_size: int = 24):
    for idx in range(0, len(text), chunk_size):
        yield text[idx : idx + chunk_size]


def _build_context(
    session: Session, *, query: str, folder: str | None, principals: list[str]
) -> list[dict[str, object]]:
    vector = embed_texts([query])[0]
    rows = hybrid_rrf_search(
        session,
        query_text=query,
        query_vector=vector,
        principals=principals,
        limit=3,
    )

    context = []
    for row in rows:
        if folder and isinstance(row.get("folder"), str) and row["folder"] != folder:
            continue
        context.append(
            {
                "content": str(row.get("content", "")),
                "metadata": {
                    "upload_id": int(row.get("upload_id", 0)),
                    "chunk_index": int(row.get("chunk_index", 0)),
                    "score": float(row.get("rrf_score", 0.0)),
                },
            }
        )

    if not context:
        context.append(
            {
                "content": "No indexed context available.",
                "metadata": {"upload_id": 0, "chunk_index": 0, "source": "system"},
            }
        )
    return context


@router.post("/stream")
async def stream_chat(
    payload: ChatStreamRequest,
    session: Session = Depends(get_db_session),
    user=Depends(get_current_user),
) -> StreamingResponse:
    principals = get_retrieval_principals(user)
    context_chunks = _build_context(
        session, query=payload.query, folder=payload.folder, principals=principals
    )
    answer = await _chat_service.answer(
        query=payload.query,
        context_chunks=context_chunks,
        public_query=payload.public_query,
    )

    async def event_stream():
        citations = answer["citations"]
        for text_part in _yield_text_chunks(answer["text"]):
            data = {
                "type": "chunk",
                "delta": text_part,
                "citations": citations,
                "skill": answer["skill"],
                "cache_hit": answer["cache_hit"],
            }
            yield f"data: {json.dumps(data)}\n\n"
        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")
