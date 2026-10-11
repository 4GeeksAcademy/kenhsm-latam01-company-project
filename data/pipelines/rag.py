from __future__ import annotations

from data.process import rag as process_rag


def get_qdrant_client():
    return process_rag.get_qdrant_client()


def setup():
    return process_rag.setup()


def embed(text: str):
    return process_rag.embed(text)


def retrieve(query: str, *, k: int = 5, min_score: float = 0.35):
    try:
        client = get_qdrant_client()
        vector = embed(query)
        matches = client.search(
            collection_name="brasaland_knowledge",
            query_vector=vector,
            limit=k,
            score_threshold=min_score,
            with_payload=True,
        )
    except Exception:
        return []

    results = []
    for raw_match in matches:
        if isinstance(raw_match, dict):
            payload = raw_match.get("payload", {}) or {}
            score = float(raw_match.get("score", 0.0) or 0.0)
            point_id = raw_match.get("id", "")
        else:
            payload = getattr(raw_match, "payload", {}) or {}
            score = float(getattr(raw_match, "score", 0.0) or 0.0)
            point_id = getattr(raw_match, "id", "")
        if not isinstance(payload, dict):
            payload = dict(payload)
        if score < min_score:
            continue
        item = {
            "id": str(point_id),
            "score": score,
            "company": payload.get("company", "brasaland"),
            "source_document": payload.get("source_document"),
            "section": payload.get("section"),
            "language": payload.get("language", "es"),
            "chunk_index": payload.get("chunk_index", 0),
            "text": payload.get("text", ""),
        }
        if item["text"]:
            results.append(item)
    return results


def generate_answer(question: str, context):
    return process_rag.generate_answer(question, context)


def query(question: str) -> str:
    context = retrieve(question, k=5, min_score=0.35)
    return generate_answer(question, context)


__all__ = [
    "setup",
    "embed",
    "retrieve",
    "generate_answer",
    "query",
    "get_qdrant_client",
]
