"""Load language-scoped grammar curriculum YAML into GrammarCatalogSnapshot."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.services.language_grammar.enums import GrammarCEFRBand
from app.services.language_grammar.id_canon import assert_canonical_grammar_id
from app.services.language_grammar_catalog.builder import derive_future_edges, topic
from app.services.language_grammar_catalog.schema import (
    ENGLISH_CEFR_QUOTAS,
    EXPECTED_TOPIC_COUNT,
    CurriculumIndexDocument,
    CurriculumTopicDocument,
    parse_index_document,
    parse_topic_document,
)
from app.services.language_grammar_catalog.types import (
    GRAMMAR_CATALOG_SCHEMA_VERSION,
    GrammarCatalogSnapshot,
    GrammarTopic,
)

# backend/ (parent of app/)
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CURRICULUM_ROOT = _BACKEND_ROOT / "curriculum"

LANGUAGE_DIR_ALIASES: dict[str, str] = {
    "en": "english",
    "english": "english",
}


def curriculum_root() -> Path:
    override = (os.environ.get("LANG_GRAMMAR_CURRICULUM_ROOT") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _DEFAULT_CURRICULUM_ROOT


def language_curriculum_dir(language_code: str = "en") -> Path:
    key = (language_code or "en").strip().lower()
    folder = LANGUAGE_DIR_ALIASES.get(key)
    if folder is None:
        raise ValueError(f"Unsupported grammar curriculum language_code: {language_code}")
    return curriculum_root() / folder / "grammar"


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _topic_from_document(doc: CurriculumTopicDocument) -> GrammarTopic:
    return topic(
        doc.grammar_id,
        display_name=doc.title,
        cefr_band=GrammarCEFRBand(doc.cefr_level),
        introduction_order=doc.order,
        prerequisite_ids=doc.prerequisites,
        learning_objectives=doc.learning_objectives,
        demonstration_patterns=doc.grammar_targets,
        example_sentences=doc.examples,
        common_errors=doc.common_mistakes,
        best_reinforcement_skills=doc.reinforcement_skills,
        recommended_contexts=doc.recommended_contexts,
        minimum_context_diversity=doc.minimum_context_diversity,
        evidence_requirements=doc.evidence,
        mastery_threshold=doc.mastery_threshold,
        review_priority=doc.review_priority,
        review_half_life_days=doc.review_half_life_days,
        focus_note=doc.focus_note or doc.teaching_notes,
        display_code=doc.display_code,
        estimated_duration_minutes=doc.estimated_duration_minutes,
        difficulty=doc.difficulty,
        teaching_notes=doc.teaching_notes,
    )


def _validate_unlock_targets(
    docs: tuple[CurriculumTopicDocument, ...],
    topics: tuple[GrammarTopic, ...],
) -> None:
    by_id = {t.grammar_id: t for t in topics}
    for doc in docs:
        if not doc.unlock_targets:
            continue
        futures = set(by_id[doc.grammar_id].future_topic_ids)
        unknown = [u for u in doc.unlock_targets if u not in futures]
        if unknown:
            raise ValueError(
                f"{doc.grammar_id}: unlock_targets not in derived future edges: {unknown}"
            )


def _validate_quotas(topics: tuple[GrammarTopic, ...], index: CurriculumIndexDocument) -> None:
    expected = index.cefr_quotas or ENGLISH_CEFR_QUOTAS
    counts: dict[str, int] = {band: 0 for band in expected}
    for topic_row in topics:
        band = topic_row.cefr_band.value
        if band not in counts:
            raise ValueError(f"Unexpected CEFR band in curriculum: {band}")
        counts[band] += 1
    if len(topics) != EXPECTED_TOPIC_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_TOPIC_COUNT} grammar topics, found {len(topics)}"
        )
    for band, want in expected.items():
        got = counts.get(band, 0)
        if got != int(want):
            raise ValueError(f"CEFR quota mismatch for {band}: expected {want}, got {got}")


def load_grammar_curriculum(language_code: str = "en") -> GrammarCatalogSnapshot:
    """Discover, parse, validate, and emit a GrammarCatalogSnapshot for a language pack."""
    root = language_curriculum_dir(language_code)
    index_path = root / "_index.yaml"
    if not index_path.is_file():
        raise FileNotFoundError(f"Missing grammar curriculum index: {index_path}")

    index = parse_index_document(_load_yaml(index_path) or {})
    requested = (language_code or "en").strip().lower()
    index_lang = index.language_code.strip().lower()
    if LANGUAGE_DIR_ALIASES.get(requested) != LANGUAGE_DIR_ALIASES.get(index_lang, index_lang):
        if not (
            LANGUAGE_DIR_ALIASES.get(requested) == "english"
            and index_lang in {"en", "english"}
        ):
            raise ValueError(
                f"Index language_code {index.language_code!r} does not match request {language_code!r}"
            )

    docs: list[CurriculumTopicDocument] = []
    seen_files: set[str] = set()
    for grammar_id in index.ordered_grammar_ids:
        gid = assert_canonical_grammar_id(grammar_id)
        path = root / f"{gid}.yaml"
        if not path.is_file():
            raise FileNotFoundError(f"Missing curriculum topic file: {path}")
        seen_files.add(path.name)
        doc = parse_topic_document(_load_yaml(path) or {})
        if doc.grammar_id != gid:
            raise ValueError(
                f"Topic file {path.name} grammar_id {doc.grammar_id!r} != index entry {gid!r}"
            )
        docs.append(doc)

    # Extra topic YAML files (not listed in index) are forbidden.
    for path in sorted(root.glob("gram_*.yaml")):
        if path.name not in seen_files:
            raise ValueError(f"Orphan curriculum topic file not listed in _index.yaml: {path.name}")

    display_codes = [d.display_code for d in docs]
    if len(display_codes) != len(set(display_codes)):
        raise ValueError("display_code values must be unique across the curriculum")

    expected_codes = {f"G{i:03d}" for i in range(1, len(docs) + 1)}
    if set(display_codes) != expected_codes:
        missing = sorted(expected_codes - set(display_codes))
        extra = sorted(set(display_codes) - expected_codes)
        raise ValueError(
            f"display_code set must be G001–G{len(docs):03d}; missing={missing} extra={extra}"
        )

    # display_code order follows introduction order (G001 = first by order)
    ordered_by_intro = sorted(docs, key=lambda d: (d.order, d.grammar_id))
    for idx, doc in enumerate(ordered_by_intro, start=1):
        want = f"G{idx:03d}"
        if doc.display_code != want:
            raise ValueError(
                f"{doc.grammar_id}: display_code {doc.display_code!r} != expected {want} "
                f"for introduction_order rank {idx}"
            )

    raw_topics = tuple(_topic_from_document(d) for d in docs)
    topics = derive_future_edges(
        tuple(sorted(raw_topics, key=lambda t: (t.introduction_order, t.grammar_id)))
    )
    _validate_unlock_targets(tuple(docs), topics)
    _validate_quotas(topics, index)

    return GrammarCatalogSnapshot(
        version=index.version,
        schema_version=index.schema_version or GRAMMAR_CATALOG_SCHEMA_VERSION,
        language_code="en" if index.language_code in {"en", "english"} else index.language_code,
        topics=topics,
    )


@lru_cache(maxsize=4)
def get_cached_curriculum(language_code: str = "en") -> GrammarCatalogSnapshot:
    return load_grammar_curriculum(language_code)


def clear_curriculum_cache() -> None:
    get_cached_curriculum.cache_clear()
