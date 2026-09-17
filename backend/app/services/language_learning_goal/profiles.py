"""Learning goal profile definitions (Phase 3.1)."""

from __future__ import annotations

from app.services.language_learning_goal.types import LearningGoal, LearningGoalProfile

_PROFILES: dict[LearningGoal, LearningGoalProfile] = {
    LearningGoal.travel: LearningGoalProfile(
        goal=LearningGoal.travel,
        label="Travel",
        preferred_situations=frozenset(
            {
                "airport",
                "hotel",
                "restaurant",
                "travel",
                "public_announcement",
                "customer_support",
                "phone_call",
                "shopping",
            }
        ),
        preferred_narrative_formats=frozenset({"announcement", "dialogue", "monologue", "interview"}),
        preferred_format_hints=frozenset({"dialogue", "monologue", "news", "interview"}),
        preferred_objectives=(
            "directions",
            "announcements",
            "instructions",
            "detail",
            "purpose",
            "numbers",
            "dates",
        ),
        vocabulary_domains=("travel", "transport", "accommodation", "tourism", "immigration", "taxi"),
        preferred_pace=frozenset({"slow_clear", "conversational"}),
        preferred_narrative_styles=frozenset(
            {"journey_with_complication", "announcement_and_action", "setup_development_resolution"}
        ),
        preferred_categories=frozenset({"travel", "daily_life", "customer_service", "public_services"}),
        difficulty_progression="gradual",
        knowledge_chain_preference="travel_airport",
        style_directives=(
            "Use authentic travel-service interactions: check-in, hotel desks, transit, and practical requests abroad.",
            "Include clear directional language, service vocabulary, and real-world announcements where natural.",
            "Keep exchanges practical — booking, delays, directions, customs, and polite problem-solving.",
        ),
    ),
    LearningGoal.ielts: LearningGoalProfile(
        goal=LearningGoal.ielts,
        label="IELTS",
        preferred_situations=frozenset(
            {"lecture", "interview", "podcast", "news", "meeting", "school", "museum"}
        ),
        preferred_narrative_formats=frozenset({"lecture", "discussion", "monologue", "interview", "panel", "news"}),
        preferred_format_hints=frozenset({"lecture", "discussion", "interview", "monologue", "panel", "news"}),
        preferred_objectives=(
            "inference",
            "opinion",
            "main_idea",
            "detail",
            "fact_vs_opinion",
            "evidence",
            "conclusions",
            "comparisons",
        ),
        vocabulary_domains=("academic", "education", "society", "environment", "research", "note-taking"),
        preferred_pace=frozenset({"brisk_informative", "conversational"}),
        preferred_narrative_styles=frozenset(
            {"compare_and_conclude", "interview_exploration", "problem_investigation_outcome"}
        ),
        preferred_categories=frozenset({"education", "news", "culture", "environment", "business"}),
        difficulty_progression="exam_rigorous",
        knowledge_chain_preference="academic_progression",
        style_directives=(
            "Favor exam-style academic listening: extended talks with clear structure and supporting detail.",
            "Include opinion-based reasoning, inference-friendly cues, and note-taking density where natural.",
            "Use formal register and academic vocabulary without sounding artificial.",
        ),
    ),
    LearningGoal.toefl: LearningGoalProfile(
        goal=LearningGoal.toefl,
        label="TOEFL",
        preferred_situations=frozenset(
            {"lecture", "school", "interview", "podcast", "office", "museum", "meeting"}
        ),
        preferred_narrative_formats=frozenset({"lecture", "discussion", "interview", "monologue", "panel"}),
        preferred_format_hints=frozenset({"lecture", "discussion", "interview", "monologue"}),
        preferred_objectives=(
            "main_idea",
            "detail",
            "inference",
            "purpose",
            "examples",
            "cause_effect",
            "conclusions",
        ),
        vocabulary_domains=("campus", "academic", "university", "research", "lecture", "student life"),
        preferred_pace=frozenset({"brisk_informative", "conversational"}),
        preferred_narrative_styles=frozenset(
            {"setup_development_resolution", "compare_and_conclude", "problem_investigation_outcome"}
        ),
        preferred_categories=frozenset({"education", "culture", "technology", "business"}),
        difficulty_progression="exam_rigorous",
        knowledge_chain_preference="academic_progression",
        style_directives=(
            "Model campus and academic contexts: lectures, seminars, and student-faculty exchanges.",
            "Emphasize main-idea tracking, supporting examples, and cause-effect links in longer passages.",
            "Maintain natural North-American academic listening rhythm.",
        ),
    ),
    LearningGoal.business: LearningGoalProfile(
        goal=LearningGoal.business,
        label="Business",
        preferred_situations=frozenset(
            {"meeting", "office", "phone_call", "customer_support", "interview", "podcast", "news"}
        ),
        preferred_narrative_formats=frozenset({"dialogue", "interview", "discussion", "monologue", "lecture"}),
        preferred_format_hints=frozenset({"dialogue", "interview", "discussion", "monologue"}),
        preferred_objectives=(
            "purpose",
            "speaker_intention",
            "inference",
            "detail",
            "agreement",
            "disagreement",
            "problems_solutions",
        ),
        vocabulary_domains=("business", "finance", "negotiation", "workplace", "client", "presentation"),
        preferred_pace=frozenset({"conversational", "brisk_informative"}),
        preferred_narrative_styles=frozenset(
            {"problem_investigation_outcome", "compare_and_conclude", "interview_exploration"}
        ),
        preferred_categories=frozenset({"business", "technology", "customer_service", "news"}),
        difficulty_progression="balanced",
        knowledge_chain_preference="workplace_progression",
        style_directives=(
            "Use professional workplace contexts: meetings, presentations, calls, and client coordination.",
            "Include negotiation subtext, action points, and polite disagreement where natural.",
            "Favor concise business vocabulary and realistic office dynamics.",
        ),
    ),
    LearningGoal.job_interview: LearningGoalProfile(
        goal=LearningGoal.job_interview,
        label="Job Interview",
        preferred_situations=frozenset({"interview", "office", "meeting", "phone_call"}),
        preferred_narrative_formats=frozenset({"interview", "dialogue", "discussion", "monologue"}),
        preferred_format_hints=frozenset({"interview", "dialogue", "discussion"}),
        preferred_objectives=(
            "speaker_intention",
            "opinion",
            "detail",
            "inference",
            "purpose",
            "tone",
            "attitude",
        ),
        vocabulary_domains=("career", "professional", "workplace", "HR", "qualifications", "problem solving"),
        preferred_pace=frozenset({"conversational", "slow_clear"}),
        preferred_narrative_styles=frozenset(
            {"interview_exploration", "problem_investigation_outcome", "setup_development_resolution"}
        ),
        preferred_categories=frozenset({"business", "customer_service", "education"}),
        difficulty_progression="gradual_to_challenging",
        knowledge_chain_preference="workplace_progression",
        style_directives=(
            "Use realistic hiring and professional dialogue: HR screens, competency questions, and career narratives.",
            "Highlight speaker intention, professional tone, and structured answers without sounding scripted.",
            "Include problem-solving scenarios and workplace etiquette naturally.",
        ),
    ),
    LearningGoal.academic: LearningGoalProfile(
        goal=LearningGoal.academic,
        label="Academic",
        preferred_situations=frozenset({"lecture", "school", "museum", "interview", "podcast"}),
        preferred_narrative_formats=frozenset({"lecture", "monologue", "discussion", "interview", "panel"}),
        preferred_format_hints=frozenset({"lecture", "monologue", "discussion", "interview"}),
        preferred_objectives=(
            "main_idea",
            "inference",
            "evidence",
            "examples",
            "conclusions",
            "transitions",
        ),
        vocabulary_domains=("academic", "research", "science", "humanities", "study skills"),
        preferred_pace=frozenset({"brisk_informative", "conversational"}),
        preferred_narrative_styles=frozenset(
            {"setup_development_resolution", "compare_and_conclude", "problem_investigation_outcome"}
        ),
        preferred_categories=frozenset({"education", "culture", "science", "environment"}),
        difficulty_progression="balanced",
        knowledge_chain_preference="academic_progression",
        style_directives=(
            "Favor structured academic discourse with clear thesis, development, and implication.",
            "Use discipline-appropriate vocabulary and lecture-style coherence.",
        ),
    ),
    LearningGoal.daily_life: LearningGoalProfile(
        goal=LearningGoal.daily_life,
        label="Daily Life",
        preferred_situations=frozenset(
            {
                "shopping",
                "restaurant",
                "doctor",
                "phone_call",
                "travel",
                "hotel",
                "public_announcement",
            }
        ),
        preferred_narrative_formats=frozenset({"dialogue", "monologue", "announcement", "interview"}),
        preferred_format_hints=frozenset({"dialogue", "monologue", "interview"}),
        preferred_objectives=("detail", "instructions", "purpose", "main_idea", "numbers", "dates"),
        vocabulary_domains=("everyday", "health", "shopping", "home", "community", "services"),
        preferred_pace=frozenset({"slow_clear", "conversational"}),
        preferred_narrative_styles=frozenset(
            {"setup_development_resolution", "journey_with_complication", "announcement_and_action"}
        ),
        preferred_categories=frozenset({"daily_life", "health", "travel", "customer_service"}),
        difficulty_progression="gradual",
        knowledge_chain_preference="daily_life",
        style_directives=(
            "Use everyday practical situations: errands, appointments, services, and social coordination.",
            "Keep language accessible, natural, and immediately useful in daily routines.",
        ),
    ),
    LearningGoal.university: LearningGoalProfile(
        goal=LearningGoal.university,
        label="University",
        preferred_situations=frozenset({"lecture", "school", "interview", "podcast", "meeting", "museum"}),
        preferred_narrative_formats=frozenset({"lecture", "discussion", "interview", "panel", "podcast"}),
        preferred_format_hints=frozenset({"lecture", "discussion", "interview", "panel"}),
        preferred_objectives=(
            "main_idea",
            "detail",
            "inference",
            "examples",
            "opinion",
            "cause_effect",
        ),
        vocabulary_domains=("university", "campus", "academic", "seminar", "research", "student life"),
        preferred_pace=frozenset({"brisk_informative", "conversational"}),
        preferred_narrative_styles=frozenset(
            {"setup_development_resolution", "interview_exploration", "compare_and_conclude"}
        ),
        preferred_categories=frozenset({"education", "culture", "technology"}),
        difficulty_progression="balanced",
        knowledge_chain_preference="academic_progression",
        style_directives=(
            "Model university contexts: lectures, seminars, study groups, and campus services.",
            "Blend academic vocabulary with student-life authenticity.",
        ),
    ),
    LearningGoal.conversation: LearningGoalProfile(
        goal=LearningGoal.conversation,
        label="Conversation",
        preferred_situations=frozenset(
            {
                "restaurant",
                "shopping",
                "phone_call",
                "interview",
                "podcast",
                "travel",
                "museum",
                "customer_support",
            }
        ),
        preferred_narrative_formats=frozenset({"dialogue", "interview", "discussion", "podcast", "panel"}),
        preferred_format_hints=frozenset({"dialogue", "interview", "discussion", "panel"}),
        preferred_objectives=(
            "opinion",
            "agreement",
            "disagreement",
            "speaker_intention",
            "tone",
            "inference",
        ),
        vocabulary_domains=("social", "conversation", "opinions", "everyday", "culture"),
        preferred_pace=frozenset({"conversational", "dynamic_multi_speaker"}),
        preferred_narrative_styles=frozenset(
            {"interview_exploration", "compare_and_conclude", "setup_development_resolution"}
        ),
        preferred_categories=frozenset({"daily_life", "entertainment", "culture", "travel"}),
        difficulty_progression="balanced",
        knowledge_chain_preference="social_progression",
        style_directives=(
            "Prioritize multi-speaker, interactive exchanges with turn-taking and natural backchanneling.",
            "Include opinions, agreement/disagreement, and social nuance without forced small talk.",
        ),
    ),
    LearningGoal.general_english: LearningGoalProfile(
        goal=LearningGoal.general_english,
        label="General English",
        preferred_situations=frozenset(
            {
                "shopping",
                "restaurant",
                "travel",
                "office",
                "school",
                "news",
                "podcast",
                "interview",
            }
        ),
        preferred_narrative_formats=frozenset(
            {"dialogue", "monologue", "interview", "lecture", "news", "podcast", "announcement"}
        ),
        preferred_format_hints=frozenset({"dialogue", "monologue", "interview", "lecture", "news"}),
        preferred_objectives=("main_idea", "detail", "inference", "purpose", "opinion"),
        vocabulary_domains=("general", "everyday", "news", "culture", "work", "education"),
        preferred_pace=frozenset({"slow_clear", "conversational", "brisk_informative"}),
        preferred_narrative_styles=frozenset(
            {
                "setup_development_resolution",
                "journey_with_complication",
                "interview_exploration",
                "announcement_and_action",
            }
        ),
        preferred_categories=frozenset(
            {
                "daily_life",
                "travel",
                "business",
                "education",
                "news",
                "entertainment",
                "culture",
            }
        ),
        difficulty_progression="balanced",
        knowledge_chain_preference="general",
        style_directives=(
            "Maintain broad, balanced exposure across everyday, work, and cultural listening contexts.",
            "Keep transcripts varied, natural, and level-appropriate without over-specializing.",
        ),
    ),
}


def profile_for_goal(goal: LearningGoal) -> LearningGoalProfile:
    return _PROFILES.get(goal, _PROFILES[LearningGoal.general_english])


def all_profiles() -> dict[LearningGoal, LearningGoalProfile]:
    return dict(_PROFILES)
