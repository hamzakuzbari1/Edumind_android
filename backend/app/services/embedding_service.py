"""BGE-M3 embeddings and FAISS vector indexes for lesson chunks."""

import asyncio
import logging
from pathlib import Path

from app.core.config import get_settings
from app.services.model_cache import configure_model_cache

logger = logging.getLogger(__name__)
settings = get_settings()

_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is not None:
        return _embedder

    configure_model_cache()

    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
    _embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedder


def _index_path(lesson_id: int) -> Path:
    base = Path(settings.VECTOR_INDEX_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"lesson_{lesson_id}.faiss"


def _embed_texts_sync(texts: list[str]):
    import numpy as np

    model = _get_embedder()
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return np.asarray(embeddings, dtype="float32")


async def embed_text(text: str) -> list[float]:
    """Return a single BGE-M3 embedding, or [] when unavailable."""
    if not (settings.ENABLE_FAISS or settings.ENABLE_EMBEDDINGS):
        return []
    try:
        vectors = await asyncio.to_thread(_embed_texts_sync, [text])
        return vectors[0].tolist()
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return []


async def build_lesson_faiss_index(lesson_id: int, chunks: list[str]) -> bool:
    """Build and persist a FAISS cosine-search index for a lesson."""
    if not settings.ENABLE_FAISS or not chunks:
        return False
    try:
        await asyncio.to_thread(_build_lesson_faiss_index_sync, lesson_id, chunks)
        return True
    except Exception as exc:
        logger.warning("FAISS index build failed, keyword RAG will be used: %s", exc)
        return False


def _build_lesson_faiss_index_sync(lesson_id: int, chunks: list[str]) -> None:
    import faiss

    embeddings = _embed_texts_sync(chunks)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    faiss.write_index(index, str(_index_path(lesson_id)))
    logger.info("FAISS index built for lesson %s with %s vectors", lesson_id, index.ntotal)


async def search_lesson_faiss_index(
    lesson_id: int,
    query: str,
    top_k: int,
    chunk_count: int,
) -> list[int]:
    """Return chunk indices ranked by semantic similarity."""
    if not settings.ENABLE_FAISS:
        return []
    try:
        return await asyncio.to_thread(
            _search_lesson_faiss_index_sync,
            lesson_id,
            query,
            top_k,
            chunk_count,
        )
    except Exception as exc:
        logger.warning("FAISS search failed, keyword RAG will be used: %s", exc)
        return []


def _search_lesson_faiss_index_sync(
    lesson_id: int,
    query: str,
    top_k: int,
    chunk_count: int,
) -> list[int]:
    import faiss
    import numpy as np

    path = _index_path(lesson_id)
    if not path.exists():
        return []

    index = faiss.read_index(str(path))
    if index.ntotal <= 0:
        return []

    query_emb = _embed_texts_sync([query])
    _, indices = index.search(query_emb, min(top_k, index.ntotal))
    out: list[int] = []
    for raw in np.asarray(indices[0]).tolist():
        idx = int(raw)
        if 0 <= idx < chunk_count:
            out.append(idx)
    return out
