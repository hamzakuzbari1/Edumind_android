"""Speaking Curriculum Engine V2 — educational intelligence before Claude authors.



RESPONSIBILITY: Enrich PackageConstraints with progression graph placement,

vocabulary, grammar targets, typed objectives, CEFR story complexity, density,

and lexical recycling. Never authors package content. Never writes CEFR/mastery/promotion.

"""



from app.services.language_speaking_curriculum_engine.case_taxonomy import (

    EducationalCaseCategory,

    case_archetype_for_cefr,

    select_case_category,

    select_educational_case_seed,

)

from app.services.language_speaking_curriculum_engine.engine import (

    enrich_speaking_constraints_payload,

)

from app.services.language_speaking_curriculum_engine.progression_catalog import (

    PROGRESSION_NODES,

    PROGRESSION_SPINE_IDS,

)

from app.services.language_speaking_curriculum_engine.progression_memory import (

    SPEAKING_PROGRESSION_KEY,

    ProgressionMasteryLedger,

    progression_ledger_from_payload,

    record_progression_exposure,

)

from app.services.language_speaking_curriculum_engine.progression_selector import (

    resolve_progression_decision,

    resolve_progression_from_payload,

    sample_progression_path,

)

from app.services.language_speaking_curriculum_engine.progression_types import (

    CaseVariant,

    MicroSkillNode,

    ProgressionDecision,

)

from app.services.language_speaking_curriculum_engine.story_complexity import (

    StoryComplexityPolicy,

    build_stakeholder_hints,

    story_complexity_policy_for_cefr,

)

from app.services.language_speaking_curriculum_engine.types import (

    CURRICULUM_ENGINE_VERSION,

    EducationalObjective,

    GrammarTarget,

    LessonAuthoringPolicy,

    LexicalRecyclingPolicy,

    ObjectiveKind,

    VocabularyTarget,

)



__all__ = [

    "CURRICULUM_ENGINE_VERSION",

    "CaseVariant",

    "EducationalCaseCategory",

    "EducationalObjective",

    "GrammarTarget",

    "LessonAuthoringPolicy",

    "LexicalRecyclingPolicy",

    "MicroSkillNode",

    "ObjectiveKind",

    "PROGRESSION_NODES",

    "PROGRESSION_SPINE_IDS",

    "ProgressionDecision",

    "ProgressionMasteryLedger",

    "SPEAKING_PROGRESSION_KEY",

    "StoryComplexityPolicy",

    "VocabularyTarget",

    "build_stakeholder_hints",

    "case_archetype_for_cefr",

    "enrich_speaking_constraints_payload",

    "progression_ledger_from_payload",

    "record_progression_exposure",

    "resolve_progression_decision",

    "resolve_progression_from_payload",

    "sample_progression_path",

    "select_case_category",

    "select_educational_case_seed",

    "story_complexity_policy_for_cefr",

]
