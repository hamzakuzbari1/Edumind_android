"""Types for the Listening Quality Layer (Phase 2.1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ListeningSituationKind(StrEnum):
    shopping = "shopping"
    airport = "airport"
    doctor = "doctor"
    school = "school"
    office = "office"
    meeting = "meeting"
    hotel = "hotel"
    phone_call = "phone_call"
    radio = "radio"
    podcast = "podcast"
    interview = "interview"
    lecture = "lecture"
    museum = "museum"
    travel = "travel"
    restaurant = "restaurant"
    customer_support = "customer_support"
    news = "news"
    public_announcement = "public_announcement"


class TranscriptFormatHint(StrEnum):
    monologue = "monologue"
    dialogue = "dialogue"
    interview = "interview"
    discussion = "discussion"
    panel = "panel"
    lecture = "lecture"
    news = "news"


class NarrativeArc(StrEnum):
    setup_development_resolution = "setup_development_resolution"
    problem_investigation_outcome = "problem_investigation_outcome"
    journey_with_complication = "journey_with_complication"
    compare_and_conclude = "compare_and_conclude"
    interview_exploration = "interview_exploration"
    announcement_and_action = "announcement_and_action"


class OpeningStyle(StrEnum):
    scene_setting = "scene_setting"
    direct_address = "direct_address"
    in_medias_res = "in_medias_res"
    question_hook = "question_hook"
    contextual_preview = "contextual_preview"


class EndingStyle(StrEnum):
    summary_sign_off = "summary_sign_off"
    call_to_action = "call_to_action"
    reflective_close = "reflective_close"
    next_steps = "next_steps"
    open_question = "open_question"


class PaceHint(StrEnum):
    slow_clear = "slow_clear"
    conversational = "conversational"
    brisk_informative = "brisk_informative"
    dynamic_multi_speaker = "dynamic_multi_speaker"


@dataclass(frozen=True, slots=True)
class ListeningQualitySpec:
    """One rotated quality directive bundle for a single generation call."""

    level: str
    situation: ListeningSituationKind
    situation_brief: str
    format_hint: TranscriptFormatHint
    speaker_count: int
    narrative_arc: NarrativeArc
    opening_style: OpeningStyle
    ending_style: EndingStyle
    pace: PaceHint
    avoid_topics: tuple[str, ...]
    listening_question_emphasis: tuple[str, ...]
