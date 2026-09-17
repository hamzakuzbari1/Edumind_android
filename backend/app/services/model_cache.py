"""Shared on-disk model cache locations for local and Docker AI models."""

from __future__ import annotations

import os
from pathlib import Path

from app.core.config import get_settings


def configure_model_cache() -> Path:
    """Keep HuggingFace/SentenceTransformer downloads under the uploads volume."""
    settings = get_settings()
    base_dir = Path(settings.UPLOAD_DIR) / "model-cache"
    hf_home = base_dir / "huggingface"
    sentence_home = base_dir / "sentence-transformers"

    hf_home.mkdir(parents=True, exist_ok=True)
    sentence_home.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_home / "hub"))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(sentence_home))
    return base_dir
