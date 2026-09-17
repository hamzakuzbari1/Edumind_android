"""Retrieve relevant lesson chunks (keyword search; optional vectors when enabled)."""

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.lesson import ContentChunk
from app.services.embedding_service import search_lesson_faiss_index

logger = logging.getLogger(__name__)

VIDEO_SOURCE_TERMS = (
    "video",
    "فيديو",
    "الفيديو",
    "بالفيديو",
    "فديو",
    "الفديو",
    "بالفديو",
    "فيدو",
    "المقطع",
    "بالمقطع",
    "التسجيل",
    "الأستاذ",
    "الاستاذ",
    "حكاها",
    "قالها",
)

PDF_SOURCE_TERMS = (
    "pdf",
    "ملف",
    "الملف",
    "بالملف",
    "صفحة",
    "الصفحة",
    "بي دي اف",
)


_AR_DIACRITICS = re.compile(r"[\u064B-\u0652\u0670\u0640]")


def _normalize_ar(text: str) -> str:
    """Normalize Arabic alef/yeh variants and strip tashkeel/tatweel.

    OCR'd PDFs often render letters like "\u0627" and "\u0623"/"\u0625"/"\u0622" inconsistently
    (and sometimes duplicate an initial alef), which breaks plain substring
    matching between a question and the lesson text. Normalizing both sides
    avoids that.
    """
    text = _AR_DIACRITICS.sub("", text)
    text = re.sub(r"[\u0625\u0623\u0622\u0627]", "\u0627", text)
    text = text.replace("\u0649", "\u064A").replace("\u0629", "\u0647")
    # Common OCR transposition: "\u0627\u0644" + word-starting-with-alef often comes
    # out as "\u0627\u0627\u0644..." instead of "\u0627\u0644\u0627...". Un-scramble it so terms like
    # "\u0627\u0644\u0627\u0633\u062A\u0633\u0642\u0627\u0621" match their OCR'd form "\u0627\u0627\u0644\u0633\u062A\u0633\u0642\u0627\u0621".
    text = text.replace("\u0627\u0627\u0644", "\u0627\u0644\u0627")
    return text


def _tokenize(text: str) -> set[str]:
    # Arabic letters only (excludes punctuation like "\u061F" and combining marks).
    tokens = re.findall(r"[\w\u0621-\u064A]+", _normalize_ar(text).lower())
    return {t for t in tokens if len(t) > 1}


def _keyword_score(query: str, content: str) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    c_norm = _normalize_ar(content).lower()
    hits = sum(1 for t in q_tokens if t in c_norm)
    return hits / len(q_tokens)


def _source_intent(query: str) -> str | None:
    normalized = (query or "").lower()
    if any(term in normalized for term in VIDEO_SOURCE_TERMS):
        return "video"
    if any(term in normalized for term in PDF_SOURCE_TERMS):
        return "pdf"
    return None


def _chunk_source(chunk: ContentChunk) -> str | None:
    if not chunk.metadata_json:
        return None
    try:
        metadata = json.loads(chunk.metadata_json)
    except Exception:
        return None
    if isinstance(metadata, dict):
        source = metadata.get("source")
        return str(source) if source else None
    return None


async def retrieve_chunks(
    db: AsyncSession,
    lesson_id: int,
    query: str,
    top_k: int = 5,
) -> list[str]:
    chunks = await retrieve_chunk_records(db, lesson_id, query, top_k)
    return [chunk.content for chunk in chunks]


async def retrieve_chunk_records(
    db: AsyncSession,
    lesson_id: int,
    query: str,
    top_k: int = 5,
) -> list[ContentChunk]:
    settings = get_settings()
    top_k = top_k or settings.RAG_TOP_K

    result = await db.execute(
        select(ContentChunk)
        .where(ContentChunk.lesson_id == lesson_id)
        .order_by(ContentChunk.chunk_index)
    )
    chunks = result.scalars().all()
    if not chunks:
        return []

    source_intent = _source_intent(query)
    if source_intent:
        source_chunks = [chunk for chunk in chunks if _chunk_source(chunk) == source_intent]
        if source_chunks:
            return _rank_chunks_by_keyword(query, source_chunks, top_k)

    indices = await search_lesson_faiss_index(lesson_id, query, top_k, len(chunks))
    if indices:
        logger.info("Using FAISS retrieval for lesson %s", lesson_id)
        selected = list(indices)
        # Hybrid fallback: semantic search can miss chunks that contain a
        # literal, distinctive match for the question (e.g. a specific
        # term/definition split across OCR'd chunks). Pull in any chunk
        # with a strong keyword overlap that FAISS didn't surface.
        keyword_scored = sorted(
            ((i, _keyword_score(query, ch.content)) for i, ch in enumerate(chunks)),
            key=lambda x: x[1],
            reverse=True,
        )
        for i, score in keyword_scored[:2]:
            if score >= 0.5 and i not in selected:
                selected.append(i)
        return [chunks[i] for i in selected]

    # Vector search path only when pgvector + embeddings are enabled (future)
    if settings.ENABLE_PGVECTOR and settings.ENABLE_EMBEDDINGS:
        try:
            return await _retrieve_chunks_vector(db, lesson_id, query, chunks, top_k)
        except Exception as exc:
            logger.warning("Vector retrieval failed, using keywords: %s", exc)

    return _rank_chunks_by_keyword(query, chunks, top_k)


def _rank_chunks_by_keyword(query: str, chunks: list[ContentChunk], top_k: int) -> list[ContentChunk]:
    scored = [(_keyword_score(query, ch.content), ch) for ch in chunks]
    scored.sort(key=lambda x: x[0], reverse=True)
    if scored[0][0] > 0:
        top = [chunk for _, chunk in scored[:top_k]]
        # A near-perfect keyword match often has its answer continue into
        # the next chunk (content split mid-topic by chunking). Pull that
        # chunk in too if it isn't already included.
        if scored[0][0] >= 0.75:
            best = scored[0][1]
            next_index = best.chunk_index + 1
            if not any(c.chunk_index == next_index for c in top):
                next_chunk = next((c for c in chunks if c.chunk_index == next_index), None)
                if next_chunk:
                    top.append(next_chunk)
        return top

    return chunks[:top_k]


async def _retrieve_chunks_vector(
    db: AsyncSession,
    lesson_id: int,
    query: str,
    chunks: list[ContentChunk],
    top_k: int,
) -> list[str]:
    """Placeholder for when pgvector is re-enabled."""
    del db, lesson_id, query, chunks, top_k
    return []


async def get_lesson_context_text(db: AsyncSession, lesson_id: int, max_chars: int = 12000) -> str:
    result = await db.execute(
        select(ContentChunk)
        .where(ContentChunk.lesson_id == lesson_id)
        .order_by(ContentChunk.chunk_index)
    )
    parts = [c.content for c in result.scalars().all()]
    text = "\n\n".join(parts)
    return text[:max_chars]
