"""Catalog of real-life listening situations and quality guidance (Phase 2.1)."""

from __future__ import annotations

from app.services.language_listening_quality.types import (
    ListeningSituationKind,
    NarrativeArc,
    OpeningStyle,
    PaceHint,
    TranscriptFormatHint,
)

OVERUSED_TOPIC_HINTS: tuple[str, ...] = (
    "daily routine",
    "my family",
    "introducing yourself",
    "what i like",
    "my school day",
    "my hobbies list",
)

GENERIC_AI_PHRASES: tuple[str, ...] = (
    "my name is",
    "i am from",
    "i like to",
    "i go to school",
    "every day i wake up",
    "my favourite",
    "let me tell you about myself",
    "today i will talk about",
)

SITUATION_BRIEFS: dict[ListeningSituationKind, str] = {
    ListeningSituationKind.shopping: (
        "A realistic shopping interaction — comparing prices, asking for sizes, returns, or advice from staff."
    ),
    ListeningSituationKind.airport: (
        "Airport context — check-in, security instructions, gate changes, or baggage issues."
    ),
    ListeningSituationKind.doctor: (
        "Medical visit — symptoms, advice, follow-up instructions, or clinic reception guidance."
    ),
    ListeningSituationKind.school: (
        "School or university context — briefing, project update, or counselor advice (not a self-introduction drill)."
    ),
    ListeningSituationKind.office: (
        "Workplace moment — task handover, deadline discussion, or colleague coordination."
    ),
    ListeningSituationKind.meeting: (
        "Meeting excerpt — agenda item, decision, disagreement, or action points."
    ),
    ListeningSituationKind.hotel: (
        "Hotel stay — booking problem, room request, local recommendations, or checkout."
    ),
    ListeningSituationKind.phone_call: (
        "Phone call — appointment booking, message taking, or resolving a practical issue."
    ),
    ListeningSituationKind.radio: (
        "Radio segment — listener question, traffic/weather update, or short feature story."
    ),
    ListeningSituationKind.podcast: (
        "Podcast excerpt — host sets context, guest develops an idea, natural sign-off."
    ),
    ListeningSituationKind.interview: (
        "Interview — host questions, follow-ups, and nuanced answers with personality."
    ),
    ListeningSituationKind.lecture: (
        "Short lecture or seminar clip — concept introduction, example, and implication."
    ),
    ListeningSituationKind.museum: (
        "Museum or gallery — guided explanation, exhibit context, or visitor question."
    ),
    ListeningSituationKind.travel: (
        "Travel situation — directions, tour commentary, transport delay, or local customs."
    ),
    ListeningSituationKind.restaurant: (
        "Restaurant — ordering, dietary needs, complaint handled politely, or chef recommendation."
    ),
    ListeningSituationKind.customer_support: (
        "Customer support call — identify issue, troubleshoot, confirm resolution."
    ),
    ListeningSituationKind.news: (
        "News bulletin style — lead story, supporting detail, brief sign-off."
    ),
    ListeningSituationKind.public_announcement: (
        "Public announcement — station, campus, or event information with clear purpose."
    ),
}

SITUATIONS_BY_LEVEL: dict[str, tuple[ListeningSituationKind, ...]] = {
    "A1": (
        ListeningSituationKind.shopping,
        ListeningSituationKind.restaurant,
        ListeningSituationKind.airport,
        ListeningSituationKind.hotel,
        ListeningSituationKind.public_announcement,
        ListeningSituationKind.phone_call,
        ListeningSituationKind.travel,
        ListeningSituationKind.school,
    ),
    "A2": (
        ListeningSituationKind.shopping,
        ListeningSituationKind.doctor,
        ListeningSituationKind.restaurant,
        ListeningSituationKind.airport,
        ListeningSituationKind.hotel,
        ListeningSituationKind.phone_call,
        ListeningSituationKind.travel,
        ListeningSituationKind.museum,
        ListeningSituationKind.public_announcement,
        ListeningSituationKind.radio,
    ),
    "B1": (
        ListeningSituationKind.office,
        ListeningSituationKind.meeting,
        ListeningSituationKind.interview,
        ListeningSituationKind.podcast,
        ListeningSituationKind.travel,
        ListeningSituationKind.museum,
        ListeningSituationKind.customer_support,
        ListeningSituationKind.news,
        ListeningSituationKind.lecture,
        ListeningSituationKind.restaurant,
    ),
    "B2": (
        ListeningSituationKind.interview,
        ListeningSituationKind.podcast,
        ListeningSituationKind.lecture,
        ListeningSituationKind.meeting,
        ListeningSituationKind.news,
        ListeningSituationKind.office,
        ListeningSituationKind.museum,
        ListeningSituationKind.customer_support,
        ListeningSituationKind.travel,
        ListeningSituationKind.radio,
    ),
    "C1": (
        ListeningSituationKind.interview,
        ListeningSituationKind.podcast,
        ListeningSituationKind.lecture,
        ListeningSituationKind.meeting,
        ListeningSituationKind.news,
        ListeningSituationKind.office,
        ListeningSituationKind.museum,
        ListeningSituationKind.customer_support,
        ListeningSituationKind.travel,
        ListeningSituationKind.radio,
    ),
    "C2": (
        ListeningSituationKind.interview,
        ListeningSituationKind.podcast,
        ListeningSituationKind.lecture,
        ListeningSituationKind.meeting,
        ListeningSituationKind.news,
        ListeningSituationKind.office,
        ListeningSituationKind.museum,
        ListeningSituationKind.customer_support,
        ListeningSituationKind.travel,
        ListeningSituationKind.radio,
    ),
}

FORMAT_BY_SITUATION: dict[ListeningSituationKind, tuple[TranscriptFormatHint, ...]] = {
    ListeningSituationKind.shopping: (TranscriptFormatHint.dialogue, TranscriptFormatHint.monologue),
    ListeningSituationKind.airport: (
        TranscriptFormatHint.monologue,
        TranscriptFormatHint.dialogue,
        TranscriptFormatHint.news,
    ),
    ListeningSituationKind.doctor: (TranscriptFormatHint.dialogue, TranscriptFormatHint.interview),
    ListeningSituationKind.school: (TranscriptFormatHint.lecture, TranscriptFormatHint.dialogue),
    ListeningSituationKind.office: (TranscriptFormatHint.dialogue, TranscriptFormatHint.discussion),
    ListeningSituationKind.meeting: (TranscriptFormatHint.discussion, TranscriptFormatHint.dialogue),
    ListeningSituationKind.hotel: (TranscriptFormatHint.dialogue, TranscriptFormatHint.interview),
    ListeningSituationKind.phone_call: (TranscriptFormatHint.dialogue, TranscriptFormatHint.monologue),
    ListeningSituationKind.radio: (TranscriptFormatHint.monologue, TranscriptFormatHint.interview),
    ListeningSituationKind.podcast: (TranscriptFormatHint.interview, TranscriptFormatHint.panel),
    ListeningSituationKind.interview: (TranscriptFormatHint.interview, TranscriptFormatHint.panel),
    ListeningSituationKind.lecture: (TranscriptFormatHint.lecture, TranscriptFormatHint.monologue),
    ListeningSituationKind.museum: (TranscriptFormatHint.monologue, TranscriptFormatHint.dialogue),
    ListeningSituationKind.travel: (TranscriptFormatHint.monologue, TranscriptFormatHint.dialogue),
    ListeningSituationKind.restaurant: (TranscriptFormatHint.dialogue,),
    ListeningSituationKind.customer_support: (TranscriptFormatHint.dialogue, TranscriptFormatHint.interview),
    ListeningSituationKind.news: (TranscriptFormatHint.news, TranscriptFormatHint.monologue),
    ListeningSituationKind.public_announcement: (TranscriptFormatHint.monologue, TranscriptFormatHint.news),
}

NARRATIVE_ARCS: tuple[NarrativeArc, ...] = tuple(NarrativeArc)
OPENING_STYLES: tuple[OpeningStyle, ...] = tuple(OpeningStyle)
PACE_HINTS: tuple[PaceHint, ...] = tuple(PaceHint)

SPEAKER_COUNT_BY_FORMAT: dict[TranscriptFormatHint, tuple[int, ...]] = {
    TranscriptFormatHint.monologue: (1,),
    TranscriptFormatHint.dialogue: (2,),
    TranscriptFormatHint.interview: (2, 3),
    TranscriptFormatHint.discussion: (3, 4),
    TranscriptFormatHint.panel: (3, 4, 5),
    TranscriptFormatHint.lecture: (1, 2),
    TranscriptFormatHint.news: (1, 2),
}

LISTENING_QUESTION_EMPHASIS_BY_LEVEL: dict[str, tuple[str, ...]] = {
    "A1": ("detail", "sequence", "purpose"),
    "A2": ("detail", "sequence", "main_idea", "purpose"),
    "B1": ("detail", "inference", "speaker_intention", "sequence"),
    "B2": ("inference", "speaker_intention", "purpose", "tone", "detail"),
    "C1": ("inference", "speaker_intention", "tone", "bias", "purpose", "sequence"),
    "C2": ("inference", "bias", "tone", "speaker_intention", "purpose", "prediction"),
}
