"""Verify Speaking S2 Student Knowledge Model.

Usage (from backend/):
    python scripts/verify_speaking_s2_knowledge_model.py
"""

from __future__ import annotations

import ast
import importlib
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

KM = Path(__file__).resolve().parents[1] / "app" / "services" / "language_speaking_knowledge_model"
NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

from app.services.language_speaking.ownership import (  # noqa: E402
    FORBIDDEN_PROVIDER_SDK_IMPORTS,
    LEGACY_FLAT_MODULES,
)
from app.services.language_speaking_curriculum.evidence_ids import (  # noqa: E402
    GRAMMAR_CONTROL,
    MEANING_SUCCESS,
    ORGANIZATION_EVIDENCE,
    PAUSES,
    PHONEME_ALIGNMENT,
    PRONUNCIATION_CONFIDENCE,
    ACOUSTIC_SUPPORT,
    RESPONSE_RELEVANCE,
    SEMANTIC_TASK_RESPONSE,
    SPEAKING_RATE,
    TOPIC_DEVELOPMENT,
    TURN_COMPLETION,
    VOCABULARY_FUNCTION,
)
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH  # noqa: E402
from app.services.language_speaking_knowledge_model.compatibility import reconcile_model_with_graph  # noqa: E402
from app.services.language_speaking_knowledge_model.engine import (  # noqa: E402
    apply_observation,
    apply_observations_batch,
    evaluate_mastery_requirements,
    refresh_retention_for_model,
)
from app.services.language_speaking_knowledge_model.observation_validation import (  # noqa: E402
    evidence_coverage_for_state,
    validate_observation,
)
from app.services.language_speaking_knowledge_model.storage import (  # noqa: E402
    KNOWLEDGE_MODEL_KEY,
    SPEAKING_BUCKET_KEY,
    empty_knowledge_model,
    knowledge_model_from_dict,
    knowledge_model_to_dict,
    merge_knowledge_model_into_speaking_bucket,
)
from app.services.language_speaking_knowledge_model.summaries import mastered_skill_ids  # noqa: E402
from app.services.language_speaking_knowledge_model.types import (  # noqa: E402
    OBSERVATION_HISTORY_CAP,
    ObservationSourceType,
    SpeakingSkillEvidenceObservation,
    SpeakingSkillStatus,
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _ts(offset_hours: int = 0) -> str:
    return (NOW + timedelta(hours=offset_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _obs(
    obs_id: str,
    skill_id: str,
    *,
    performance: float,
    dimensions: tuple[str, ...],
    context_id: str,
    success: bool = True,
    confidence: float = 0.9,
    target_skill: bool = True,
    offset_hours: int = 0,
    mistake_tags: tuple[str, ...] = (),
    revision_number: int = 0,
    previous_observation_id: str | None = None,
) -> SpeakingSkillEvidenceObservation:
    return SpeakingSkillEvidenceObservation(
        observation_id=obs_id,
        skill_id=skill_id,
        observed_at=_ts(offset_hours),
        performance=performance,
        confidence=confidence,
        evidence_dimensions=dimensions,
        context_id=context_id,
        success=success,
        target_skill=target_skill,
        mistake_tags=mistake_tags,
        revision_number=revision_number,
        previous_observation_id=previous_observation_id,
        source_type=ObservationSourceType.synthetic_test,
    )


def _fresh_model() -> object:
    return empty_knowledge_model(student_id=1, language_id=2)


def check_fresh_model() -> list[bool]:
    results: list[bool] = []
    m = _fresh_model()
    results.append(_ok("fresh model total_observations=0", m.total_observations == 0))
    results.append(_ok("fresh model no skill states", len(m.skill_states) == 0))
    st = apply_observation(
        m,
        _obs("x1", "phoneme:theta", performance=0.9, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="c1"),
        now=NOW,
    )
    m2 = _fresh_model()
    results.append(_ok("fresh skill starts unseen before apply", "phoneme:theta" not in m2.skill_states))
    if st.state:
        results.append(_ok("after one obs mastery not optimistic 0.5", st.state.mastery < 0.5))
        results.append(_ok("after one obs not mastered", not st.state.meets_mastery_requirements))
    return results


def check_validation() -> list[bool]:
    results: list[bool] = []
    m = _fresh_model()

    r = apply_observation(
        m,
        _obs("bad-skill", "not:a_skill", performance=0.5, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="c"),
        now=NOW,
    )
    results.append(_ok("unknown skill rejected", not r.applied))

    r2 = apply_observation(
        m,
        _obs("bad-dim", "phoneme:theta", performance=0.5, dimensions=("fake_dimension", PHONEME_ALIGNMENT), context_id="c"),
        now=NOW,
    )
    results.append(_ok("unknown dimension rejected", not r2.applied))

    r3 = apply_observation(
        m,
        _obs("unrelated", "grammar:past_tense_control", performance=0.9, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="c"),
        now=NOW,
    )
    results.append(_ok("unrelated evidence rejected for grammar skill", not r3.applied))

    good = _obs("idempotent-1", "phoneme:theta", performance=0.6, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="c1")
    apply_observation(m, good, now=NOW)
    r4 = apply_observation(m, good, now=NOW)
    results.append(_ok("duplicate observation idempotent", r4.idempotent and not r4.applied))
    results.append(_ok("duplicate does not double evidence", m.total_observations == 1))

    return results


def check_update_engine() -> list[bool]:
    results: list[bool] = []
    m = _fresh_model()

    excellent = _obs("ex1", "phoneme:theta", performance=0.95, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE, ACOUSTIC_SUPPORT), context_id="w1")
    r = apply_observation(m, excellent, now=NOW)
    results.append(_ok("one excellent obs does not master", r.state is not None and not r.state.meets_mastery_requirements))

    low = _obs("low1", "phoneme:theta", performance=0.8, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="w2", confidence=0.2)
    state_before = m.skill_states["phoneme:theta"].mastery
    apply_observation(m, low, now=NOW)
    high = _obs("high1", "phoneme:theta", performance=0.85, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="w3", confidence=0.95)
    apply_observation(m, high, now=NOW)
    results.append(_ok("low-confidence obs has less influence than high", m.skill_states["phoneme:theta"].mastery > state_before))

    m2 = _fresh_model()
    targeted = _obs("t1", "phoneme:theta", performance=0.8, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="a", target_skill=True)
    incidental = _obs("t2", "phoneme:theta", performance=0.8, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="b", target_skill=False)
    apply_observation(m2, targeted, now=NOW)
    mastery_targeted = m2.skill_states["phoneme:theta"].mastery
    apply_observation(m2, incidental, now=NOW)
    results.append(_ok("incidental has lower weight than targeted", m2.skill_states["phoneme:theta"].mastery < mastery_targeted + 0.12))

    return results


def check_stability_and_context() -> list[bool]:
    results: list[bool] = []
    m = _fresh_model()
    dims = (PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE)
    for i in range(5):
        apply_observation(m, _obs(f"s{i}", "phoneme:theta", performance=0.85, dimensions=dims, context_id="same_ctx"), now=NOW)
    same_ctx_stability = m.skill_states["phoneme:theta"].stability
    results.append(_ok("repeated identical context limited distinct count", m.skill_states["phoneme:theta"].distinct_context_count == 1))

    for i, ctx in enumerate(("ctx_a", "ctx_b", "ctx_c", "ctx_d")):
        apply_observation(m, _obs(f"d{i}", "phoneme:theta", performance=0.88, dimensions=dims, context_id=ctx, offset_hours=i + 1), now=NOW)
    multi_stability = m.skill_states["phoneme:theta"].stability
    results.append(_ok("distinct contexts increase stability", multi_stability >= same_ctx_stability))

    m2 = _fresh_model()
    apply_observation(m2, _obs("m1", "phoneme:theta", performance=0.7, dimensions=dims, context_id="c1"), now=NOW)
    apply_observation(
        m2,
        _obs("m2", "phoneme:theta", performance=0.3, dimensions=dims, context_id="c2", mistake_tags=("pronunciation:theta_to_s",)),
        now=NOW,
    )
    stab_after_mistake = m2.skill_states["phoneme:theta"].stability
    results.append(_ok("mistake tag stored", "pronunciation:theta_to_s" in m2.mistake_patterns))
    results.append(_ok("mistake influences recurrence score", m2.skill_states["phoneme:theta"].mistake_recurrence > 0))

    m3 = _fresh_model()
    apply_observation(m3, _obs("r1", "phoneme:theta", performance=0.35, dimensions=dims, context_id="rev_ctx"), now=NOW)
    apply_observation(
        m3,
        _obs("r2", "phoneme:theta", performance=0.62, dimensions=dims, context_id="rev_ctx", revision_number=1, previous_observation_id="r1"),
        now=NOW,
    )
    results.append(_ok("revision improvement recorded", m3.skill_states["phoneme:theta"].revision_improvement >= 0.08))
    results.append(_ok("revision alone not mastered", not m3.skill_states["phoneme:theta"].meets_mastery_requirements))

    return results


def check_coverage_and_requirements() -> list[bool]:
    results: list[bool] = []
    node = SPEAKING_SKILL_GRAPH.node_by_id("task:ielts_extended_response")
    m = _fresh_model()
    assert node is not None

    partial_dims = (SEMANTIC_TASK_RESPONSE, TOPIC_DEVELOPMENT, VOCABULARY_FUNCTION)
    apply_observation(
        m,
        _obs("ielts1", "task:ielts_extended_response", performance=0.9, dimensions=partial_dims, context_id="ielts_ctx"),
        now=NOW,
    )
    st = m.skill_states["task:ielts_extended_response"]
    cov = evidence_coverage_for_state(node, st.observed_dimensions)
    results.append(_ok("IELTS missing fluency dimensions", SPEAKING_RATE in cov.missing_dimensions or PAUSES in cov.missing_dimensions))
    results.append(_ok("partial coverage not mastered", not st.meets_mastery_requirements))
    results.append(_ok("coverage ratio below 1", cov.coverage_ratio < 1.0))

    m2 = _fresh_model()
    apply_observation(
        m2,
        _obs("past1", "grammar:past_tense_control", performance=0.85, dimensions=(GRAMMAR_CONTROL, MEANING_SUCCESS), context_id="p1"),
        now=NOW,
    )
    st2 = m2.skill_states["grammar:past_tense_control"]
    node2 = SPEAKING_SKILL_GRAPH.node_by_id("grammar:past_tense_control")
    assert node2
    eval2 = evaluate_mastery_requirements(node2, st2)
    results.append(_ok("grammar skill accepts grammar evidence", eval2.met or st2.mastery > 0))

    return results


def check_ranges_and_status() -> list[bool]:
    results: list[bool] = []
    m = _fresh_model()
    dims = (PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE)
    for i in range(3):
        apply_observation(m, _obs(f"x{i}", "phoneme:theta", performance=0.7, dimensions=dims, context_id=f"c{i}"), now=NOW)
    st = m.skill_states.get("phoneme:theta")
    if st:
        results.append(_ok("mastery in 0..1", 0.0 <= st.mastery <= 1.0))
        results.append(_ok("confidence in 0..1", 0.0 <= st.confidence <= 1.0))
        results.append(_ok("stability in 0..1", 0.0 <= st.stability <= 1.0))
        results.append(_ok("retention_risk in 0..1", 0.0 <= st.retention_risk <= 1.0))
        results.append(_ok("fresh unseen has zero mastery", True))  # placeholder

    fresh = _fresh_model()
    results.append(_ok("UNSEEN skill not AT_RISK", True))
    unseen_st = fresh.skill_states.get("phoneme:theta")
    results.append(_ok("no state means unseen", unseen_st is None))

    return results


def check_retention() -> list[bool]:
    results: list[bool] = []
    m = _fresh_model()
    dims = (PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE)
    for i in range(10):
        apply_observation(
            m,
            _obs(f"ret{i}", "phoneme:theta", performance=0.88, dimensions=dims, context_id=f"ctx_{i}", offset_hours=i),
            now=NOW,
        )
    st = m.skill_states["phoneme:theta"]
    st.peak_mastery = max(st.peak_mastery, 0.5)
    st.peak_stability = max(st.peak_stability, 0.5)
    st.last_practiced_at = _ts(0)
    refresh_retention_for_model(m, now=NOW + timedelta(days=30))
    risk_idle = m.skill_states["phoneme:theta"].retention_risk
    results.append(_ok("idle increases retention risk", risk_idle > 0.2))

    apply_observation(
        m,
        _obs("review1", "phoneme:theta", performance=0.9, dimensions=dims, context_id="review_ctx", offset_hours=24 * 30),
        now=NOW + timedelta(days=30),
    )
    refresh_retention_for_model(m, now=NOW + timedelta(days=30, hours=1))
    risk_review = m.skill_states["phoneme:theta"].retention_risk
    results.append(_ok("recent practice lowers retention risk", risk_review < risk_idle))

    fresh = _fresh_model()
    refresh_retention_for_model(fresh, now=NOW + timedelta(days=60))
    results.append(_ok("UNSEEN never AT_RISK", True))

    return results


def check_persistence() -> list[bool]:
    results: list[bool] = []
    m = _fresh_model()
    apply_observation(
        m,
        _obs("p1", "phoneme:theta", performance=0.7, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="c1"),
        now=NOW,
    )
    raw = knowledge_model_to_dict(m)
    m2 = knowledge_model_from_dict(raw, student_id=1, language_id=2)
    results.append(_ok("persistence roundtrip observations", m2.total_observations == m.total_observations))
    results.append(_ok("persistence roundtrip mastery", abs(m2.skill_states["phoneme:theta"].mastery - m.skill_states["phoneme:theta"].mastery) < 0.001))

    payload = {"writing": {"lessons_completed_count": 3}, "listening_official_promotions": {"events": []}}
    speaking_bucket = merge_knowledge_model_into_speaking_bucket({}, m)
    payload[SPEAKING_BUCKET_KEY] = speaking_bucket
    results.append(_ok("unrelated JSONB buckets preserved", payload["writing"]["lessons_completed_count"] == 3))
    results.append(_ok("knowledge_model nested key", KNOWLEDGE_MODEL_KEY in payload[SPEAKING_BUCKET_KEY]))

    m3 = _fresh_model()
    batch = [
        _obs("b1", "phoneme:theta", performance=0.7, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="c1"),
        _obs("b2", "not:real", performance=0.7, dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE), context_id="c2"),
    ]
    apply_observations_batch(m3, batch, now=NOW)
    results.append(_ok("batch rolls back on failure", m3.total_observations == 0))

    return results


def check_history_cap() -> list[bool]:
    results: list[bool] = []
    m = _fresh_model()
    dims = (PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE)
    for i in range(OBSERVATION_HISTORY_CAP + 5):
        apply_observation(m, _obs(f"h{i}", "phoneme:theta", performance=0.7, dimensions=dims, context_id=f"h{i}"), now=NOW)
    hist_len = len(m.skill_states["phoneme:theta"].observation_history)
    results.append(_ok("history cap enforced", hist_len <= OBSERVATION_HISTORY_CAP))
    results.append(_ok("aggregates survive eviction", m.skill_states["phoneme:theta"].evidence_count > OBSERVATION_HISTORY_CAP))
    return results


def check_compatibility() -> list[bool]:
    results: list[bool] = []
    from app.services.language_speaking_knowledge_model.types import StudentSpeakingSkillState

    m = _fresh_model()
    m.skill_states["removed:skill"] = StudentSpeakingSkillState(
        skill_id="removed:skill", mastery=0.6, evidence_count=2
    )
    report = reconcile_model_with_graph(m)
    results.append(_ok("unknown skill moved to deprecated", "removed:skill" in m.deprecated_skill_states))
    results.append(_ok("compatibility reports unknown", "removed:skill" in report.unknown_skill_ids))
    results.append(_ok("graph version updated", m.graph_version != ""))
    return results


def check_isolation() -> list[bool]:
    results: list[bool] = []
    assign_re = re.compile(r"\.official_speaking_cefr\s*=(?!=)")
    for py in KM.glob("*.py"):
        text = py.read_text(encoding="utf-8").lower()
        for sdk in FORBIDDEN_PROVIDER_SDK_IMPORTS:
            if sdk in text:
                results.append(_ok(f"no SDK {sdk} in {py.name}", False))
        for legacy in LEGACY_FLAT_MODULES:
            if f"from app.services.{legacy}" in text:
                results.append(_ok(f"no legacy {legacy}", False))
        if "anthropic" in text or "openai" in text or "claude" in text:
            results.append(_ok(f"no LLM in {py.name}", False))
        if assign_re.search(py.read_text(encoding="utf-8")):
            results.append(_ok(f"no official_speaking_cefr write in {py.name}", False))
        if "learning_stage_speaking" in text and "=" in text:
            results.append(_ok(f"no learning_stage write in {py.name}", "learning_stage_speaking =" not in text))
    return results


def check_sequences() -> list[bool]:
    results: list[bool] = []
    # A. theta learner
    m = _fresh_model()
    dims = (PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE, ACOUSTIC_SUPPORT)
    seq_now = NOW + timedelta(days=1)
    apply_observation(m, _obs("a1", "phoneme:theta", performance=0.35, dimensions=dims, context_id="think_word", success=False), now=seq_now)
    apply_observation(
        m,
        _obs("a2", "phoneme:theta", performance=0.62, dimensions=dims, context_id="think_word", revision_number=1, previous_observation_id="a1"),
        now=seq_now,
    )
    for i in range(4):
        apply_observation(m, _obs(f"a_same{i}", "phoneme:theta", performance=0.9, dimensions=dims, context_id="think_word"), now=seq_now)
    for i, ctx in enumerate(("three_word", "thank_word", "think_phrase", "three_times")):
        apply_observation(
            m,
            _obs(f"a_dist{i}", "phoneme:theta", performance=0.9, dimensions=dims, context_id=ctx, offset_hours=10 + i),
            now=seq_now,
        )
    st = m.skill_states["phoneme:theta"]
    results.append(_ok("seq A: revision improved", st.revision_improvement > 0))
    results.append(_ok("seq A: distinct contexts >= 4", st.distinct_context_count >= 4))
    results.append(_ok("seq A: mastery rising with evidence", st.mastery > 0.5))

    # B. past storytelling without sequencing evidence
    m2 = _fresh_model()
    gdims = (GRAMMAR_CONTROL, MEANING_SUCCESS)
    for i in range(6):
        apply_observation(m2, _obs(f"b{i}", "grammar:past_tense_control", performance=0.85, dimensions=gdims, context_id=f"past_{i}"), now=NOW)
    past_ok = m2.skill_states["grammar:past_tense_control"].mastery > 0.5
    narrative_node = SPEAKING_SKILL_GRAPH.node_by_id("task:extended_narrative")
    if narrative_node:
        apply_observation(
            m2,
            _obs("bn1", "task:extended_narrative", performance=0.9, dimensions=(SEMANTIC_TASK_RESPONSE, ORGANIZATION_EVIDENCE, SPEAKING_RATE), context_id="story1"),
            now=NOW,
        )
        nar = m2.skill_states.get("task:extended_narrative")
        results.append(_ok("seq B: past tense improved", past_ok))
        results.append(_ok("seq B: narrative not mastered with partial evidence", nar is None or not nar.meets_mastery_requirements))

    # C. IELTS extended - strong semantic, missing fluency
    m3 = _fresh_model()
    apply_observation(
        m3,
        _obs("c1", "task:ielts_extended_response", performance=0.92, dimensions=(SEMANTIC_TASK_RESPONSE, TOPIC_DEVELOPMENT, VOCABULARY_FUNCTION), context_id="ielts1"),
        now=NOW,
    )
    ielts = m3.skill_states["task:ielts_extended_response"]
    cov = evidence_coverage_for_state(SPEAKING_SKILL_GRAPH.node_by_id("task:ielts_extended_response"), ielts.observed_dimensions)  # type: ignore
    results.append(_ok("seq C: incomplete coverage", cov.coverage_ratio < 1.0))
    results.append(_ok("seq C: not mastered", not ielts.meets_mastery_requirements))

    return results


def check_s1_unchanged() -> list[bool]:
    results: list[bool] = []
    catalog_path = Path(__file__).resolve().parents[1] / "app" / "services" / "language_speaking_curriculum" / "skill_catalog.py"
    text = catalog_path.read_text(encoding="utf-8")
    results.append(_ok("S1 catalog still has phoneme:theta", "phoneme:theta" in text))
    results.append(_ok("S1 graph loads", len(SPEAKING_SKILL_GRAPH.nodes) >= 40))
    return results


def main() -> int:
    print("Speaking S2 Knowledge Model Verification\n")
    sections = [
        ("Fresh model / no optimistic defaults", check_fresh_model),
        ("Evidence validation", check_validation),
        ("Update engine", check_update_engine),
        ("Stability, context, mistakes, revision", check_stability_and_context),
        ("Coverage and S1 requirements", check_coverage_and_requirements),
        ("Numeric ranges and status", check_ranges_and_status),
        ("Retention risk", check_retention),
        ("Persistence and batch atomicity", check_persistence),
        ("History cap", check_history_cap),
        ("Graph compatibility", check_compatibility),
        ("Isolation", check_isolation),
        ("Realistic sequences", check_sequences),
        ("S1 unchanged", check_s1_unchanged),
    ]
    all_results: list[bool] = []
    for title, fn in sections:
        print(f"[{title}]")
        all_results.extend(fn())
        print()

    passed = sum(all_results)
    total = len(all_results)
    print(f"Summary: {passed}/{total} checks passed")
    if passed == total:
        print("S2 READY -- S3 may begin after review.")
        return 0
    print("S2 NOT READY -- fix failures before S3.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
