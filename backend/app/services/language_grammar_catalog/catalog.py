"""Public Grammar Catalog API (G1) — read-only topic authority.



No progression, mastery, planner, runtime, or Claude logic lives here.

Curriculum definitions load from language-scoped YAML under backend/curriculum/.

"""



from __future__ import annotations



from functools import lru_cache



from app.services.language_grammar.enums import GrammarCEFRBand

from app.services.language_grammar.id_canon import normalize_grammar_id

from app.services.language_grammar_catalog.loader import (

    clear_curriculum_cache,

    get_cached_curriculum,

    load_grammar_curriculum,

)

from app.services.language_grammar_catalog.types import (

    GrammarCatalogSnapshot,

    GrammarTopic,

)

from app.services.language_grammar_catalog.validation import (

    CatalogValidationResult,

    validate_catalog,

    validate_curriculum_progression,

)



CATALOG_LANGUAGE_CODE = "en"





@lru_cache(maxsize=1)

def get_english_catalog() -> GrammarCatalogSnapshot:

    """Return the frozen English catalog snapshot (validated at load)."""

    snapshot = get_cached_curriculum("en")

    integrity = validate_catalog(snapshot)

    if not integrity.valid:

        codes = ", ".join(sorted({i.code for i in integrity.issues}))

        raise RuntimeError(f"English grammar catalog failed integrity validation: {codes}")

    curriculum = validate_curriculum_progression(snapshot)

    if not curriculum.valid:

        codes = ", ".join(sorted({i.code for i in curriculum.issues}))

        raise RuntimeError(f"English grammar catalog failed curriculum validation: {codes}")

    return snapshot





def get_default_catalog() -> GrammarCatalogSnapshot:

    """Default catalog for the platform (English)."""

    return get_english_catalog()





def list_topics(*, language_code: str = "en") -> tuple[GrammarTopic, ...]:

    if language_code != "en":

        raise ValueError(f"Unsupported grammar catalog language_code: {language_code}")

    return get_default_catalog().topics





def get_topic(grammar_id: str, *, language_code: str = "en") -> GrammarTopic | None:

    gid = normalize_grammar_id(grammar_id)

    return get_default_catalog().topic_by_id(gid) if language_code == "en" else None





def require_topic(grammar_id: str, *, language_code: str = "en") -> GrammarTopic:

    topic = get_topic(grammar_id, language_code=language_code)

    if topic is None:

        raise KeyError(f"Unknown grammar_id: {grammar_id}")

    return topic





def topics_for_cefr(band: GrammarCEFRBand, *, language_code: str = "en") -> tuple[GrammarTopic, ...]:

    catalog = get_default_catalog() if language_code == "en" else None

    if catalog is None:

        raise ValueError(f"Unsupported grammar catalog language_code: {language_code}")

    return catalog.topics_for_band(band)





def topics_up_to_cefr(band: GrammarCEFRBand, *, language_code: str = "en") -> tuple[GrammarTopic, ...]:

    catalog = get_default_catalog() if language_code == "en" else None

    if catalog is None:

        raise ValueError(f"Unsupported grammar catalog language_code: {language_code}")

    return catalog.topics_up_to_band(band)





def all_grammar_ids(*, language_code: str = "en") -> frozenset[str]:

    return get_default_catalog().topic_ids() if language_code == "en" else frozenset()





def validate_default_catalog() -> tuple[CatalogValidationResult, CatalogValidationResult]:

    """Run integrity + curriculum validation without raising (for verify scripts)."""

    clear_curriculum_cache()

    get_english_catalog.cache_clear()

    snapshot = load_grammar_curriculum("en")

    return validate_catalog(snapshot), validate_curriculum_progression(snapshot)





def reload_english_catalog() -> GrammarCatalogSnapshot:

    """Clear caches and reload English curriculum (tests / verify scripts)."""

    clear_curriculum_cache()

    get_english_catalog.cache_clear()

    return get_english_catalog()
