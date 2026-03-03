from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def _permission_clause(alias: str, principals: list[str]) -> tuple[str, dict[str, str]]:
    if not principals:
        return "1 = 0", {}

    clauses: list[str] = []
    params: dict[str, str] = {}
    for idx, principal in enumerate(principals):
        key = f"perm_{idx}"
        clauses.append(f"instr({alias}.read_allow, :{key}) > 0")
        params[key] = f"|{principal}|"
    return "(" + " OR ".join(clauses) + ")", params


def hybrid_rrf_search(
    session: Session,
    *,
    query_text: str,
    query_vector: list[float],
    principals: list[str],
    limit: int = 5,
    rrf_k: int = 60,
) -> list[dict[str, object]]:
    """Search chunks with BM25-like lexical rank + vector rank using SQL RRF."""
    if limit <= 0:
        return []
    if not query_vector:
        raise ValueError("query_vector must not be empty")

    permission_sql, permission_params = _permission_clause("c", principals)
    sql = f"""
    WITH bm25_candidates AS (
        SELECT
            c.id AS chunk_id,
            ROW_NUMBER() OVER (
                ORDER BY
                    (
                        LENGTH(LOWER(c.content_tsv)) -
                        LENGTH(REPLACE(LOWER(c.content_tsv), :query_token, ''))
                    ) DESC,
                    c.id ASC
            ) AS rank_pos
        FROM doc_chunks c
        WHERE {permission_sql}
          AND INSTR(LOWER(c.content_tsv), :query_token) > 0
        LIMIT :candidate_limit
    ),
    vector_candidates AS (
        SELECT
            c.id AS chunk_id,
            ROW_NUMBER() OVER (
                ORDER BY
                    ABS(COALESCE(JSON_EXTRACT(c.content_vector, '$[0]'), 1000000000.0) - :qv0) ASC,
                    c.id ASC
            ) AS rank_pos
        FROM doc_chunks c
        WHERE {permission_sql}
          AND c.vector_ready = 1
          AND c.content_vector IS NOT NULL
        LIMIT :candidate_limit
    ),
    merged AS (
        SELECT chunk_id, (1.0 / (:rrf_k + rank_pos)) AS score FROM bm25_candidates
        UNION ALL
        SELECT chunk_id, (1.0 / (:rrf_k + rank_pos)) AS score FROM vector_candidates
    )
    SELECT
        c.id,
        c.upload_id,
        c.chunk_index,
        c.content,
        SUM(merged.score) AS rrf_score
    FROM merged
    JOIN doc_chunks c ON c.id = merged.chunk_id
    GROUP BY c.id, c.upload_id, c.chunk_index, c.content
    ORDER BY rrf_score DESC, c.id ASC
    LIMIT :limit_value
    """

    params: dict[str, object] = {
        "query_token": query_text.lower().strip(),
        "qv0": float(query_vector[0]),
        "rrf_k": rrf_k,
        "candidate_limit": max(limit * 5, 20),
        "limit_value": limit,
    }
    params.update(permission_params)

    rows = session.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]
