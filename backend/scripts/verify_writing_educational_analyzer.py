"""Verify the deep educational analyzer across the 15 required QA cases.

Runs the heuristic analyzer (offline/mock) so behavior is deterministic. Confirms
Claude-style educational facts for every dimension AND that no pass/fail leaks.
The Rule Engine still owns all decisions — this script never asserts progression.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("WRITING_EDUCATIONAL_ANALYZER", "mock")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing_educational_analyzer.mock_educational import (  # noqa: E402
    build_mock_educational_facts,
)
from app.services.language_writing_educational_analyzer.types import EducationalAnalysisContext  # noqa: E402


def _ctx(
    *,
    prompt: str,
    goal: str = "general_english",
    goal_label: str = "General English",
    vocabulary: tuple[str, ...] = (),
    outcomes: tuple[str, ...] = (),
    official_cefr: str = "B1",
    revision_number: int = 1,
    previous_cefr: str = "",
    previous_task_score: float = 0.0,
) -> EducationalAnalysisContext:
    return EducationalAnalysisContext(
        official_cefr=official_cefr,
        writing_prompt=prompt,
        chain_node_id="qa_node",
        genre="essay",
        task_type="paragraph",
        narrative_why=prompt,
        grammar_primary="present simple",
        vocabulary_primary=vocabulary,
        learning_outcomes=outcomes,
        success_criteria=(),
        rule_summary="Rule engine context only.",
        personal_goal=goal,
        goal_label=goal_label,
        revision_number=revision_number,
        previous_cefr=previous_cefr,
        previous_task_score=previous_task_score,
    )


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    tag = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {tag}{suffix}")
    return passed


def _no_passfail(facts) -> bool:
    """Assert the facts object exposes no pass/fail decision fields."""
    forbidden = ("passed", "ready", "completed", "eligible", "promotion", "stage")
    return not any(hasattr(facts, attr) for attr in forbidden)


def case_off_topic() -> list[bool]:
    print("[1] Completely off-topic answer")
    ctx = _ctx(prompt="Explain why Biology interests you.", vocabulary=("cells", "organism", "science"))
    f = build_mock_educational_facts("My name is Hamza. I live in Malaysia. I have two brothers.", ctx)
    return [
        _ok("task response low", f.task_response.score < 0.4, f"{f.task_response.score:.2f}"),
        _ok("topic understanding low", f.topic_understanding.score < 0.4),
        _ok("task reason explains why", "prompt" in f.task_response.reason.lower() or "topic" in f.task_response.reason.lower()),
        _ok("diagnosis not grammar", "grammar" not in f.learning_diagnosis.lower()),
    ]


def case_grammar_ok_wrong_task() -> list[bool]:
    print("[2] Excellent grammar but wrong task")
    ctx = _ctx(prompt="Describe your favourite hobby and why you enjoy it.", vocabulary=("hobby", "enjoy", "relax"))
    text = (
        "The weather in my city is usually warm and sunny. In the summer, the sky is clear and the days are long. "
        "Many people visit the park because the temperature is pleasant. The rain rarely falls during these months."
    )
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("grammar clean (no notes)", len(f.grammar_notes) == 0, f"{len(f.grammar_notes)} notes"),
        _ok("task response low despite grammar", f.task_response.score < 0.6, f"{f.task_response.score:.2f}"),
        _ok("has strengths anyway", len(f.strengths) >= 1),
    ]


def case_bad_grammar_right_idea() -> list[bool]:
    print("[3] Terrible grammar but correct idea")
    ctx = _ctx(prompt="Explain why you want to learn English.", vocabulary=("english", "learn", "job", "future"))
    text = "i want learn english because english help me get good job. english are important for my future and i is happy when i study english."
    f = build_mock_educational_facts(text, ctx)
    note = f.grammar_notes[0] if f.grammar_notes else None
    return [
        _ok("grammar notes found", len(f.grammar_notes) >= 1, f"{len(f.grammar_notes)} notes"),
        _ok("grammar note explains rule", bool(note and note.rule)),
        _ok("grammar note gives fix", bool(note and note.fix)),
        _ok("grammar note gives example", bool(note and note.example)),
        _ok("idea/topic acknowledged", f.task_response.score >= 0.5, f"task={f.task_response.score:.2f}"),
        _ok("diagnosis targets grammar", "grammar" in f.learning_diagnosis.lower()),
    ]


def case_excellent_b2() -> list[bool]:
    print("[4] Excellent B2 answer")
    ctx = _ctx(
        prompt="Discuss the advantages and disadvantages of remote work.",
        vocabulary=("remote", "productivity", "colleagues", "flexibility"),
    )
    text = (
        "Remote work offers clear advantages, however it also brings challenges. On the one hand, it gives employees "
        "flexibility because they can manage their own schedule. Moreover, many people report higher productivity when "
        "they avoid a long commute. On the other hand, working from home can feel isolating, and therefore some "
        "colleagues struggle to stay motivated. In conclusion, remote work is beneficial when companies provide clear "
        "structure and regular communication, although it does not suit every role."
    )
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("cefr B2 or higher", f.cefr_estimate in {"B2", "C1"}, f.cefr_estimate),
        _ok("cefr reason explains why", bool(f.cefr_reason)),
        _ok("coherence high", f.coherence.score >= 0.7, f"{f.coherence.score:.2f}"),
    ]


def case_weak_a2() -> list[bool]:
    print("[5] Weak A2 answer")
    ctx = _ctx(prompt="Write about your family.", vocabulary=("family", "mother", "father"))
    text = "I have family. My family is good. I like my family. My mother is nice. My father is nice."
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("cefr A1/A2", f.cefr_estimate in {"A1", "A2"}, f.cefr_estimate),
        _ok("cefr reason present", bool(f.cefr_reason)),
    ]


def case_repetitive_vocab() -> list[bool]:
    print("[6] Repetitive vocabulary")
    ctx = _ctx(prompt="Describe your city.", vocabulary=("city", "building", "street"))
    text = "My city is a good city. The city is big and the city is nice. I love my city because the city is my home city."
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("repetition detected", len(f.vocabulary.repeated_words) >= 1, str(f.vocabulary.repeated_words)),
        _ok("vocabulary suggestion given", len(f.vocabulary.suggestions) >= 1),
        _ok("vocabulary reason present", bool(f.vocabulary.reason)),
    ]


def case_strong_organization() -> list[bool]:
    print("[7] Strong organization")
    ctx = _ctx(prompt="Explain how to make a good first impression.")
    text = (
        "Making a good first impression matters for several reasons. Firstly, it builds trust quickly, because people "
        "judge others in seconds.\n\n"
        "Secondly, good body language helps. For example, a warm smile shows confidence. Moreover, clear speech makes "
        "you easier to understand.\n\n"
        "In conclusion, preparation and a positive attitude create a strong first impression."
    )
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("organization high", f.organization.score >= 0.7, f"{f.organization.score:.2f}"),
        _ok("organization reason present", bool(f.organization.reason)),
    ]


def case_poor_organization() -> list[bool]:
    print("[8] Poor organization")
    ctx = _ctx(prompt="Explain how to make a good first impression.")
    text = "first impression important smile good clothes nice talk clear be confident arrive early shake hands look eyes"
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("organization low", f.organization.score < 0.55, f"{f.organization.score:.2f}"),
        _ok("organization reason present", bool(f.organization.reason)),
    ]


def case_business_goal() -> list[bool]:
    print("[9] Business goal")
    ctx = _ctx(
        prompt="Write an email to schedule a meeting with a client.",
        goal="business",
        goal_label="Business",
        vocabulary=("meeting", "schedule", "client"),
    )
    text = (
        "Dear colleague, I would like to schedule a meeting with the client to discuss the project deadline. "
        "Please confirm your availability. Kind regards, Omar."
    )
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("goal alignment strong", f.goal_alignment.score >= 0.6, f"{f.goal_alignment.score:.2f}"),
        _ok("goal reason mentions Business", "business" in f.goal_alignment.reason.lower()),
    ]


def case_travel_goal() -> list[bool]:
    print("[10] Travel goal")
    ctx = _ctx(
        prompt="Write a message asking the hotel for a refund on your booking.",
        goal="travel",
        goal_label="Travel",
        vocabulary=("hotel", "booking", "refund"),
    )
    text = (
        "Hello, I booked a hotel room for my trip, but my flight was cancelled at the airport. "
        "Could I please have a refund for my booking? Thank you for your help."
    )
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("goal alignment reasonable", f.goal_alignment.score >= 0.6, f"{f.goal_alignment.score:.2f}"),
        _ok("goal reason mentions Travel", "travel" in f.goal_alignment.reason.lower()),
    ]


def case_ielts_opinion() -> list[bool]:
    print("[11] IELTS opinion essay")
    ctx = _ctx(
        prompt="Some people think students should study abroad. To what extent do you agree?",
        goal="ielts",
        goal_label="Ielts",
        vocabulary=("opinion", "society", "government"),
    )
    text = (
        "I strongly agree that studying abroad benefits students. Firstly, it improves language skills, because "
        "students practise every day. However, some argue it is expensive. In my opinion, the advantages outweigh the "
        "disadvantages. Furthermore, students gain independence. In conclusion, I agree that studying abroad is valuable."
    )
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("goal alignment strong (ielts)", f.goal_alignment.score >= 0.6, f"{f.goal_alignment.score:.2f}"),
        _ok("idea development supported", f.idea_development.score >= 0.6, f"{f.idea_development.score:.2f}"),
    ]


def case_academic_report() -> list[bool]:
    print("[12] Academic report")
    ctx = _ctx(
        prompt="Summarise the results of your research study on sleep and memory.",
        goal="academic",
        goal_label="Academic",
        vocabulary=("research", "results", "analysis"),
    )
    text = (
        "This study analysed the relationship between sleep and memory. The research collected data from forty "
        "participants. The results show that participants who slept longer performed better. Therefore, the analysis "
        "suggests that adequate sleep improves memory. Further research is needed to confirm these results."
    )
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("goal alignment academic", f.goal_alignment.score >= 0.6, f"{f.goal_alignment.score:.2f}"),
        _ok("goal reason mentions Academic", "academic" in f.goal_alignment.reason.lower()),
    ]


def case_creative_writing() -> list[bool]:
    print("[13] Creative writing")
    ctx = _ctx(
        prompt="Write the opening of a short story set on a cold winter night.",
        goal="creative_writing",
        goal_label="Creative Writing",
        vocabulary=("shadow", "silence", "cold"),
    )
    text = (
        "Suddenly, the cold wind broke the silence of the night. A shadow moved across the bright snow, and my heart "
        "began to race. I remembered the dream I had, and for a moment the whole street felt like a whisper from the past."
    )
    f = build_mock_educational_facts(text, ctx)
    return [
        _ok("goal alignment creative", f.goal_alignment.score >= 0.6, f"{f.goal_alignment.score:.2f}"),
        _ok("goal reason mentions Creative", "creative" in f.goal_alignment.reason.lower()),
    ]


def case_draft_comparison() -> list[bool]:
    print("[14] Compare first draft vs second draft")
    ctx1 = _ctx(prompt="Explain why you want to learn English.", vocabulary=("english", "learn", "job"))
    d1 = "i want learn english because english help me. english are good for job."
    f1 = build_mock_educational_facts(d1, ctx1)

    ctx2 = _ctx(
        prompt="Explain why you want to learn English.",
        vocabulary=("english", "learn", "job"),
        revision_number=2,
        previous_cefr=f1.cefr_estimate,
        previous_task_score=f1.task_response.score,
    )
    d2 = (
        "I want to learn English because it helps me find a better job. Moreover, English lets me travel and meet new "
        "people. For example, I can read books and watch films in English, which improves my skills every day."
    )
    f2 = build_mock_educational_facts(d2, ctx2)
    return [
        _ok("second draft has progress comparison", bool(f2.progress_comparison), f2.progress_comparison),
        _ok("first draft has no comparison", not f1.progress_comparison),
        _ok("second draft improves grammar", len(f2.grammar_notes) <= len(f1.grammar_notes)),
    ]


def case_every_judgment_has_why() -> list[bool]:
    print("[15] Every educational judgment explains WHY")
    ctx = _ctx(prompt="Describe your daily routine.", vocabulary=("morning", "work", "evening"))
    text = (
        "Every morning I wake up early and drink coffee. Then I go to work by bus because it is cheaper than driving. "
        "In the evening, I cook dinner and relax with my family before I sleep."
    )
    f = build_mock_educational_facts(text, ctx)
    reasons = {
        "task_response": f.task_response.reason,
        "topic_understanding": f.topic_understanding.reason,
        "coherence": f.coherence.reason,
        "organization": f.organization.reason,
        "idea_development": f.idea_development.reason,
        "goal_alignment": f.goal_alignment.reason,
        "vocabulary": f.vocabulary.reason,
    }
    results = [_ok(f"{k} has a reason", bool(v.strip())) for k, v in reasons.items()]
    results.append(_ok("cefr reason present", bool(f.cefr_reason)))
    results.append(_ok("learning diagnosis present", bool(f.learning_diagnosis)))
    results.append(_ok("exactly one revision priority", bool(f.revision_priority) and "\n" not in f.revision_priority))
    results.append(_ok("encouragement present + specific", bool(f.encouragement) and len(f.encouragement) > 20))
    results.append(_ok("no pass/fail fields on facts", _no_passfail(f)))
    return results


def main() -> int:
    print("Deep Educational Analyzer Verification (15 QA cases)\n")
    cases = [
        case_off_topic,
        case_grammar_ok_wrong_task,
        case_bad_grammar_right_idea,
        case_excellent_b2,
        case_weak_a2,
        case_repetitive_vocab,
        case_strong_organization,
        case_poor_organization,
        case_business_goal,
        case_travel_goal,
        case_ielts_opinion,
        case_academic_report,
        case_creative_writing,
        case_draft_comparison,
        case_every_judgment_has_why,
    ]
    all_results: list[bool] = []
    for case in cases:
        all_results.extend(case())
        print()
    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("EDUCATIONAL ANALYZER VERIFIED — teacher-like facts across all dimensions; no pass/fail leakage.")
        return 0
    print("EDUCATIONAL ANALYZER NOT READY — fix failures before continuing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
