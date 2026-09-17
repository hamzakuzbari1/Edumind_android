"""Curriculum arc catalog (W1) — Layer 2 definitions."""

from __future__ import annotations

from app.services.language_writing.enums import OfficialWritingCEFR, WritingArc
from app.services.language_writing_curriculum.types import WritingArcStageDefinition

CATALOG_VERSION = "1.0.0"

WRITING_ARC_CATALOG: tuple[WritingArcStageDefinition, ...] = (
    WritingArcStageDefinition(
        arc_stage=WritingArc.sentence_building,
        label="Sentence Building",
        description="Write clear single sentences and short connected sentences about familiar topics.",
        allowed_task_types=("describe", "list", "complete_sentence", "short_message"),
        allowed_genres=("sentence_set", "caption", "short_note"),
        min_word_count=15,
        max_word_count=60,
        min_cefr=OfficialWritingCEFR.A1,
        organization_scaffold_level=1,
    ),
    WritingArcStageDefinition(
        arc_stage=WritingArc.paragraph_writing,
        label="Paragraph Writing",
        description="Organize ideas into a coherent paragraph with a beginning, middle, and end.",
        allowed_task_types=("describe", "narrate_short", "explain_simple", "email_short"),
        allowed_genres=("paragraph", "short_email", "diary_entry"),
        min_word_count=40,
        max_word_count=120,
        min_cefr=OfficialWritingCEFR.A1,
        organization_scaffold_level=2,
    ),
    WritingArcStageDefinition(
        arc_stage=WritingArc.narrative_writing,
        label="Narrative Writing",
        description="Tell a story or recount events in logical sequence with descriptive detail.",
        allowed_task_types=("narrate", "recount", "describe_sequence", "review_experience"),
        allowed_genres=("narrative", "story", "travelogue", "event_report"),
        min_word_count=60,
        max_word_count=180,
        min_cefr=OfficialWritingCEFR.A2,
        organization_scaffold_level=2,
    ),
    WritingArcStageDefinition(
        arc_stage=WritingArc.opinion_writing,
        label="Opinion Writing",
        description="State a viewpoint and support it with reasons and examples.",
        allowed_task_types=("opinion", "recommend", "compare_preferences", "respond"),
        allowed_genres=("opinion_paragraph", "review", "recommendation", "forum_post"),
        min_word_count=80,
        max_word_count=200,
        min_cefr=OfficialWritingCEFR.A2,
        organization_scaffold_level=2,
    ),
    WritingArcStageDefinition(
        arc_stage=WritingArc.formal_writing,
        label="Formal Writing",
        description="Write polite, structured messages for real-world situations requiring formality.",
        allowed_task_types=("complaint", "request", "apology", "inquiry", "application"),
        allowed_genres=("formal_email", "letter", "complaint", "request"),
        min_word_count=80,
        max_word_count=220,
        min_cefr=OfficialWritingCEFR.B1,
        organization_scaffold_level=3,
    ),
    WritingArcStageDefinition(
        arc_stage=WritingArc.professional_writing,
        label="Professional Writing",
        description="Produce workplace writing: reports, proposals, and professional correspondence.",
        allowed_task_types=("report", "proposal", "memo", "meeting_summary", "cover_letter"),
        allowed_genres=("business_email", "report", "memo", "proposal", "cover_letter"),
        min_word_count=100,
        max_word_count=280,
        min_cefr=OfficialWritingCEFR.B1,
        organization_scaffold_level=3,
    ),
    WritingArcStageDefinition(
        arc_stage=WritingArc.academic_writing,
        label="Academic Writing",
        description="Write structured academic texts: summaries, essays, and evidence-based arguments.",
        allowed_task_types=("summary", "essay", "compare", "argue", "analyze"),
        allowed_genres=("summary", "essay", "academic_paragraph", "literature_review"),
        min_word_count=120,
        max_word_count=350,
        min_cefr=OfficialWritingCEFR.B2,
        organization_scaffold_level=3,
    ),
)


def arc_by_stage(stage: WritingArc) -> WritingArcStageDefinition | None:
    for arc in WRITING_ARC_CATALOG:
        if arc.arc_stage == stage:
            return arc
    return None


def arc_stages_ordered() -> tuple[WritingArc, ...]:
    return tuple(a.arc_stage for a in WRITING_ARC_CATALOG)
