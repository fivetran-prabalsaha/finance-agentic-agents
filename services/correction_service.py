"""
CorrectionService — Phase C Feedback Loop

Stores user corrections as pgvector embeddings and retrieves semantically
similar past corrections to inject as few-shot context into future queries.

Flow:
  1. User clicks ❌ Wrong → types correction text
  2. _save_feedback() calls CorrectionService.store_correction() in a background thread
  3. store_correction() embeds the original query text using MiniLM (384-dim)
     and writes the row into correction_embeddings
  4. On every future query, process_with_claude() calls find_similar_corrections()
     which does a cosine ANN search and returns the top-k most relevant corrections
  5. Corrections are injected into dynamic_context as few-shot examples
"""

import logging
import os
from typing import List, Dict, Any, Optional

import numpy as np
from sqlalchemy import text as sqla_text

logger = logging.getLogger(__name__)

# Similarity threshold — only inject corrections with cosine similarity >= this value
_MIN_SIMILARITY = float(os.getenv("CORRECTION_MIN_SIMILARITY", "0.70"))
# How many corrections to surface per query
_TOP_K = int(os.getenv("CORRECTION_TOP_K", "3"))


def _get_embedding_service():
    """Lazy-load EmbeddingService (HuggingFace MiniLM, 384-dim, free/local)."""
    from services.embedding_service import create_embedding_service
    return create_embedding_service(provider="huggingface")


def store_correction(
    run_id: str,
    user_email: str,
    query_preview: str,
    correction: str,
    tool_called: Optional[str] = None,
) -> None:
    """
    Embed the original user query and persist into correction_embeddings.

    Called from _save_feedback() in a background thread — must not raise.

    Args:
        run_id:        LangSmith trace ID (links to answer_feedback row)
        user_email:    User who provided the correction
        query_preview: First 300 chars of the original user question
        correction:    Full correction text from the modal
        tool_called:   MCP tool that produced the wrong answer
    """
    try:
        from models.database_config import DatabaseConfig

        # 1. Generate embedding for the query text (MiniLM, 384-dim, local)
        svc = _get_embedding_service()
        vec: np.ndarray = svc.embed_text(query_preview[:300])
        vec_list = vec.tolist()

        # 2. Write to Postgres
        session = DatabaseConfig().get_session()
        try:
            session.execute(
                sqla_text("""
                    INSERT INTO correction_embeddings
                        (run_id, user_email, query_preview, correction, tool_called, embedding)
                    VALUES
                        (:run_id, :user_email, :query_preview, :correction,
                         :tool_called, CAST(:embedding AS vector))
                """),
                {
                    "run_id":        run_id or None,
                    "user_email":    user_email,
                    "query_preview": query_preview[:300],
                    "correction":    correction[:2000],
                    "tool_called":   tool_called or None,
                    "embedding":     str(vec_list),
                },
            )
            session.commit()
            logger.info(
                f"CorrectionService: stored embedding for run={run_id} user={user_email}"
            )
        except Exception as e:
            session.rollback()
            logger.warning(f"CorrectionService: DB write failed: {e}")
        finally:
            session.close()

    except Exception as e:
        logger.warning(f"CorrectionService.store_correction failed: {e}")


def find_similar_corrections(
    query: str,
    top_k: int = _TOP_K,
    min_similarity: float = _MIN_SIMILARITY,
) -> List[Dict[str, Any]]:
    """
    Search correction_embeddings for stored corrections that are semantically
    similar to the current user query.

    Returns a list of dicts with keys:
        query_preview, correction, tool_called, similarity, used_count

    Returns [] on any error so callers never see an exception.
    """
    if not query or not query.strip():
        return []

    try:
        from models.database_config import DatabaseConfig

        svc = _get_embedding_service()
        vec: np.ndarray = svc.embed_text(query[:300])
        vec_list = vec.tolist()

        session = DatabaseConfig().get_session()
        try:
            rows = session.execute(
                sqla_text("""
                    SELECT
                        id,
                        query_preview,
                        correction,
                        tool_called,
                        used_count,
                        1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
                    FROM correction_embeddings
                    WHERE 1 - (embedding <=> CAST(:qvec AS vector)) >= :min_sim
                    ORDER BY embedding <=> CAST(:qvec AS vector)
                    LIMIT :top_k
                """),
                {
                    "qvec":    str(vec_list),
                    "min_sim": min_similarity,
                    "top_k":   top_k,
                },
            ).fetchall()

            results = [dict(r._mapping) for r in rows]

            # Bump used_count for matched rows (fire-and-forget, ignore errors)
            if results:
                ids = [str(r["id"]) for r in results]
                try:
                    session.execute(
                        sqla_text(
                            "UPDATE correction_embeddings "
                            "SET used_count = used_count + 1, last_used_at = NOW() "
                            "WHERE id = ANY(CAST(:ids AS uuid[]))"
                        ),
                        {"ids": "{" + ",".join(ids) + "}"},
                    )
                    session.commit()
                except Exception:
                    session.rollback()

            logger.info(
                f"CorrectionService: found {len(results)} corrections "
                f"(threshold={min_similarity})"
            )
            return results

        finally:
            session.close()

    except Exception as e:
        logger.warning(f"CorrectionService.find_similar_corrections failed: {e}")
        return []


def format_corrections_for_context(corrections: List[Dict[str, Any]]) -> str:
    """
    Format a list of corrections into a few-shot block for injection into
    dynamic_context inside the system message.

    Example output:
        === Past Correction Examples (from compliance officer feedback) ===
        [1] When asked: "show me all high violations in Finance"
            The agent gave a wrong answer. The correct answer is:
            "Finance has 28 open violations — 3 CRITICAL (AP Entry + AP Approval conflicts
             requiring immediate remediation), 8 HIGH, 12 MEDIUM, 5 LOW."

        [2] When asked: "can Austin Chen get the Controller role?"
            ...
    """
    if not corrections:
        return ""

    lines = ["=== Past Correction Examples (compliance officer feedback) ==="]
    for i, c in enumerate(corrections, 1):
        qp = (c.get("query_preview") or "").strip()
        corr = (c.get("correction") or "").strip()
        if not qp or not corr:
            continue
        lines.append(f'[{i}] When asked: "{qp}"')
        lines.append(f'    The correct answer is: "{corr}"')
    lines.append(
        "Use these examples to calibrate your answer. "
        "If the current query is similar, ensure your response aligns with the corrections above."
    )
    return "\n".join(lines)
