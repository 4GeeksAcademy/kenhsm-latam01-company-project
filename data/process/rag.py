from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = REPO_ROOT / "docs" / "company-knowledge-base"
COLLECTION_NAME = "brasaland_knowledge"
COMPANY = "brasaland"
LANGUAGE = "es"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
EMBEDDING_MODEL = os.getenv(
    "FOURGEEKS_EMBEDDING_MODEL",
    "text-embedding-3-small",
)
GENERATION_MODEL = os.getenv(
    "FOURGEEKS_GENERATION_MODEL",
    "gpt-4o-mini",
)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _fallback_embedding(text: str, size: int = 1536) -> list[float]:
    normalized = _normalize_text(text)
    if not normalized:
        return [0.0] * size

    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    embedding: list[float] = []
    for index in range(size):
        start = (index * 2) % (len(digest) - 1)
        segment = digest[start:start + 2]
        if len(segment) < 2:
            segment = digest[:2]
        value = int.from_bytes(segment, byteorder="big") / 65535.0
        embedding.append((value * 2.0) - 1.0)
    return embedding


def get_openai_client() -> OpenAI | None:
    api_key = os.getenv("FOURGEEKS_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("FOURGEEKS_BASE_URL")
        or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)


def _source_document_name(path: Path) -> str:
    stem = path.stem.replace(".es", "")
    return stem.removeprefix("brasaland-")


def _chunk_text(text: str) -> list[str]:
    cleaned = _normalize_text(text)
    if not cleaned:
        return []

    words = cleaned.split()
    if len(words) <= 35:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + 35)
        chunk = " ".join(words[start:end])
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
        start = max(start + 25, end - 5)
    return chunks


def _document_chunks(path: Path) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8")
    source_document = _source_document_name(path)
    section = "Resumen general"
    paragraphs: list[tuple[str, str]] = []
    current_lines: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            if current_lines:
                paragraphs.append((section, " ".join(current_lines)))
                current_lines = []
            continue
        if line.startswith("#"):
            if current_lines:
                paragraphs.append((section, " ".join(current_lines)))
                current_lines = []
            section = line.lstrip("# ").strip() or section
            continue
        current_lines.append(line)

    if current_lines:
        paragraphs.append((section, " ".join(current_lines)))

    if not paragraphs:
        paragraphs = [("Resumen general", content)]

    chunks: list[dict[str, Any]] = []
    chunk_index = 0
    for section_name, paragraph in paragraphs:
        for sub_chunk in _chunk_text(paragraph):
            chunks.append(
                {
                    "company": COMPANY,
                    "source_document": source_document,
                    "section": section_name,
                    "language": LANGUAGE,
                    "chunk_index": chunk_index,
                    "text": sub_chunk,
                }
            )
            chunk_index += 1

    return chunks


def setup() -> list[dict[str, Any]]:
    """Build the knowledge base in Qdrant with a deterministic, idempotent collection reset."""
    docs = sorted(KNOWLEDGE_DIR.glob("*.md"))
    if not docs:
        raise FileNotFoundError(f"No se encontraron documentos fuente en {KNOWLEDGE_DIR}")

    chunks: list[dict[str, Any]] = []
    for doc_path in docs:
        chunks.extend(_document_chunks(doc_path))

    client = get_qdrant_client()
    try:
        client.get_collection(collection_name=COLLECTION_NAME)
    except Exception:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
    else:
        client.delete_collection(collection_name=COLLECTION_NAME)
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

    points: list[models.PointStruct] = []
    for chunk in chunks:
        vector = embed(chunk["text"])
        point_id = hashlib.sha1(
            f"{chunk['company']}|{chunk['source_document']}|{chunk['section']}|{chunk['chunk_index']}".encode("utf-8")
        ).hexdigest()
        payload = dict(chunk)
        points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    return chunks


def embed(text: str) -> list[float]:
    """Embed text using a dedicated embedding model; fallback is deterministic for tests and CI."""
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return [0.0] * 1536

    client = get_openai_client()
    if client is not None:
        try:
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=normalized_text)
            values = response.data[0].embedding
            return [float(value) for value in values]
        except Exception:
            return _fallback_embedding(normalized_text)
    return _fallback_embedding(normalized_text)


def retrieve(query: str, *, k: int = 5, min_score: float = 0.35) -> list[dict[str, Any]]:
    try:
        client = get_qdrant_client()
        vector = embed(query)
        matches = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=k,
            score_threshold=min_score,
            with_payload=True,
        )
    except Exception:
        return []

    results: list[dict[str, Any]] = []
    for raw_match in matches:
        if isinstance(raw_match, dict):
            payload_dict = raw_match.get("payload", {}) or {}
            score = float(raw_match.get("score", 0.0) or 0.0)
            point_id = raw_match.get("id", "")
        else:
            payload_dict = getattr(raw_match, "payload", {}) or {}
            score = float(getattr(raw_match, "score", 0.0) or 0.0)
            point_id = getattr(raw_match, "id", "")

        if not isinstance(payload_dict, dict):
            payload_dict = dict(payload_dict)

        if score < min_score:
            continue

        item = {
            "id": str(point_id),
            "score": score,
            "company": payload_dict.get("company", COMPANY),
            "source_document": payload_dict.get("source_document"),
            "section": payload_dict.get("section"),
            "language": payload_dict.get("language", LANGUAGE),
            "chunk_index": payload_dict.get("chunk_index", 0),
            "text": payload_dict.get("text", ""),
        }
        if item["text"]:
            results.append(item)
    return results


def generate_answer(question: str, context: Iterable[dict[str, Any]]) -> str:
    context_items = list(context)
    if not context_items:
        return (
            "No tengo información suficiente en la base de conocimiento de Brasaland para responder con precisión. "
            "Necesito más contexto sobre el tema solicitado antes de responder."
        )

    context_text = "\n\n".join(
        f"[{item.get('source_document', 'fuente')}] {item.get('text', '')}" for item in context_items
    )
    system_prompt = (
        "Eres un vendedor entrenado de Brasaland. Responde con la voz y audiencia de un gerente de local "
        "ofreciendo información precisa y clara, siempre basada exclusivamente en el contexto recuperado. "
        "Si el contexto no incluye una respuesta fiable, di que no hay información suficiente y no inventes."
    )

    client = get_openai_client()
    if client is None:
        return (
            "La base de conocimiento no ha devuelto información suficiente para responder esta pregunta con precisión. "
            "Revisa el contexto disponible o intenta otra consulta."
        )

    try:
        completion = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Pregunta del usuario: {question}\n\nContexto recuperado:\n{context_text}"},
            ],
            temperature=0.1,
        )
        answer = completion.choices[0].message.content.strip()
        return answer or "No pude generar una respuesta fiable con el contexto disponible."
    except Exception:
        return (
            "No tengo información suficiente en la base de conocimiento para responder con seguridad. "
            "El contexto recuperado no incluye una respuesta fiable."
        )


def query(question: str) -> str:
    try:
        context = retrieve(question, k=5, min_score=0.35)
    except Exception:
        context = []
    return generate_answer(question, context)
