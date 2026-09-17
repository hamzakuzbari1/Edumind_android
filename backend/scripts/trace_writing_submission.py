"""End-to-end trace for ONE writing draft submission — evidence only."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DRAFT = """My name are Hamza.
I like.
Because good.
Teacher."""

TRACE: list[dict[str, Any]] = []
CLAUDE_CALLS: list[dict[str, Any]] = []


def log(step: int, name: str, **fields: Any) -> None:
    entry = {"step": step, "event": name, "ts": datetime.now(timezone.utc).isoformat(), **fields}
    TRACE.append(entry)
    print(f"\n--- STEP {step}: {name} ---")
    for k, v in fields.items():
        print(f"  {k}: {json.dumps(v, default=str) if isinstance(v, (dict, list)) else v}")


async def run_pipeline_trace() -> tuple[Any, dict]:
    from app.core.config import get_settings
    from app.services import claude_service
    from app.services.language_writing.enums import OfficialWritingCEFR, WritingGoal
    from app.services.language_writing_curriculum.goal_profiles import profile_for_goal
    from app.services.language_writing_curriculum.selector import select_writing_curriculum_node
    from app.services.language_writing_lesson_planner.planner_contract import assemble_blueprint
    from app.services.language_writing_lesson_planner.types import LessonPlannerInput
    from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY, WRITING_CURRICULUM_KEY
    from app.services.language_writing_evaluation_runtime.pipeline import process_writing_draft_turn
    from app.services.language_writing_explainability.student_evaluation_display import build_student_evaluation_display
    from app.services.language_writing_coach.revision_plan import revision_plan_to_feedback

    settings = get_settings()
    log(
        0,
        "ENVIRONMENT",
        WRITING_MODEL_PROVIDER=os.environ.get("WRITING_MODEL_PROVIDER", settings.WRITING_MODEL_PROVIDER),
        CLAUDE_MODEL=settings.CLAUDE_MODEL,
        ANTHROPIC_API_KEY_set=bool(os.environ.get("ANTHROPIC_API_KEY") or getattr(settings, "ANTHROPIC_API_KEY", "")),
    )

    sel = select_writing_curriculum_node(
        goal=WritingGoal.travel,
        official_cefr=OfficialWritingCEFR.B1,
        completed_node_ids=frozenset(),
    )
    bp = assemble_blueprint(
        LessonPlannerInput(
            official_cefr=OfficialWritingCEFR.B1,
            goal_profile=profile_for_goal(WritingGoal.travel),
            selected_node=sel.node,
            blueprint_id="trace:submission",
        )
    ).blueprint
    body_json = {
        WRITING_BLUEPRINT_KEY: bp.to_dict(),
        WRITING_CURRICULUM_KEY: {
            "official_cefr": "B1",
            "chain_id": sel.chain_id,
            "chain_node_id": sel.node.node_id,
            "personal_goal": "travel",
        },
    }
    log(1, "INPUT", draft_text=DRAFT, word_count=len(DRAFT.split()), blueprint_node=sel.node.node_id)

    original = claude_service.generate_claude_json

    async def spy(*args, **kwargs):
        CLAUDE_CALLS.append(
            {
                "function": "claude_service.generate_claude_json",
                "model": kwargs.get("model"),
                "system_preview": str(kwargs.get("system") or "")[:300],
                "user_preview": str(kwargs.get("user") or "")[:300],
            }
        )
        out = await original(*args, **kwargs)
        CLAUDE_CALLS[-1]["response_preview"] = str(out)[:500]
        return out

    with patch.object(claude_service, "generate_claude_json", spy):
        result, updated_body = await process_writing_draft_turn(
            student_id=1,
            content_item_id=99999,
            draft_text=DRAFT,
            body_json=body_json,
            force_complete=False,
        )

    log(
        2,
        "CLAUDE_DURING_DRAFT_EVALUATION",
        was_claude_called=len(CLAUDE_CALLS) > 0,
        call_count=len(CLAUDE_CALLS),
        calls=CLAUDE_CALLS or "NONE",
        why_not_called_if_zero="Hybrid engine calls claude_service.generate_claude_json when WRITING_EDUCATIONAL_ANALYZER=claude and API key is set; mock/off skip the API",
    )

    ev = result.evaluation
    log(
        3,
        "EVALUATION_OBJECT",
        class_name="WritingEvaluationEngineResult",
        engine_version=ev.engine_version,
        grammar_passed=ev.grammar.passed,
        grammar_score=ev.grammar.score,
        grammar_errors=list(ev.grammar.errors),
        weak_skills=list(ev.weak_skills),
        explanation_improvements=list(ev.explanation.improvements),
        explanation_priority=ev.explanation.priority_issue,
        revision_readiness_ready=ev.revision_readiness.ready,
        claude_analysis_available=ev.claude_analysis is not None and ev.claude_analysis.available,
        claude_major_issue=ev.claude_analysis.major_learning_issue if ev.claude_analysis else None,
        blockers=list(ev.revision_readiness.blockers),
        completion_eligible=ev.completion.eligible,
        lesson_completed_flag=result.completed,
    )

    display = build_student_evaluation_display(ev)
    fb = revision_plan_to_feedback(result.revision_plan)
    log(
        4,
        "BROWSER_PAYLOAD_SOURCES",
        evaluation_display_improvements=list(display.improvements),
        evaluation_display_ready_to_complete=display.ready_to_complete,
        feedback_dict=fb.to_student_dict() if hasattr(fb, "to_student_dict") else str(fb),
        revision_plan_main_issue=result.revision_plan.main_issue,
        narrative_summary=result.narrative.coach_summary,
    )

    persisted = updated_body.get("writing_evaluation_facts") or {}
    log(5, "PERSISTED_EVALUATION", engine_version=persisted.get("engine_version"), ready=persisted.get("revision_readiness"))
    return result, updated_body


async def http_trace() -> None:
    try:
        import httpx
    except ImportError:
        log(10, "HTTP_SKIPPED", reason="httpx not installed")
        return

    base = os.environ.get("WRITING_QA_API", "http://127.0.0.1:8000")
    email = os.environ.get("WRITING_QA_EMAIL", "qa.listening.student-g@eduspark-test.dev")
    password = "TestOnly123!"

    async with httpx.AsyncClient(base_url=base, timeout=90.0) as client:
        login = await client.post("/api/auth/login", json={"email": email, "password": password})
        if login.status_code != 200:
            log(10, "HTTP_LOGIN_FAILED", status=login.status_code, body=login.text[:300])
            return
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        gen = await client.post("/api/student/languages/writing/generate", headers=headers, json={"goal": "travel"})
        gen_body = gen.json() if gen.status_code == 200 else {"error": gen.text}
        log(
            10,
            "HTTP_GENERATE_LESSON",
            status=gen.status_code,
            content_item_id=gen_body.get("content_item_id") if isinstance(gen_body, dict) else None,
            note="Claude only invoked here if server WRITING_MODEL_PROVIDER=claude AND key configured",
        )
        if gen.status_code != 200:
            return

        cid = gen_body["content_item_id"]
        draft = await client.post(
            f"/api/student/languages/writing/{cid}/draft",
            headers=headers,
            json={"draft_text": DRAFT, "complete_if_ready": False},
        )
        d = draft.json() if draft.status_code == 200 else {"error": draft.text}
        log(
            11,
            "HTTP_DRAFT_SUBMIT_LIVE_SERVER",
            status=draft.status_code,
            ready_to_complete=d.get("ready_to_complete"),
            completed=d.get("completed"),
            evaluation_display=d.get("evaluation_display"),
            feedback=d.get("feedback"),
            revision_plan=d.get("revision_plan"),
            completion=d.get("completion"),
        )


async def main() -> int:
    print("=" * 72)
    print("TRACE DRAFT:", repr(DRAFT))
    print("=" * 72)
    await run_pipeline_trace()
    await http_trace()
    out = Path(__file__).resolve().parent / "trace_writing_submission_output.json"
    out.write_text(json.dumps({"draft": DRAFT, "trace": TRACE, "claude_calls": CLAUDE_CALLS}, indent=2, default=str), encoding="utf-8")
    print(f"\nJSON trace: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
