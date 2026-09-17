"""Real S7.6 Hume EVI tool integration acceptance — FAIL-not-SKIP.

Usage (from backend/):
    set HUME_API_KEY=...
    set HUME_SECRET_KEY=...
    set HUME_EVI_CONFIG_ID=...
    set SPEAKING_LIVE_CONVERSATION_PROVIDER=hume_evi
    python scripts/verify_speaking_s76_real_evi.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.language_speaking_audio_frontend.live_conversation_factory import build_live_conversation_provider  # noqa: E402
from app.services.language_speaking_coach.live_context import assemble_student_speaking_live_context  # noqa: E402
from app.services.language_speaking_coach.live_context_loader import opaque_student_reference  # noqa: E402
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH  # noqa: E402
from app.services.language_speaking_evaluation_runtime.evi_token import mint_evi_access_token  # noqa: E402
from app.services.language_speaking_evaluation_runtime.evi_tool_runtime import handle_evi_tool_call  # noqa: E402
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model  # noqa: E402

HUME_PROMPT_ADDITION = (
    "At the start of each new conversation, call get_student_speaking_context before your first reply "
    "so you can adapt naturally to this learner."
)


def _ok(label: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    line = f"  [{mark}] {label}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return passed


async def _run() -> list[bool]:
    results: list[bool] = []
    settings = get_settings()
    mode = (settings.SPEAKING_LIVE_CONVERSATION_PROVIDER or "").strip().lower()
    results.append(_ok("provider hume_evi", mode == "hume_evi", mode))
    results.append(_ok("HUME credentials present", bool(settings.HUME_API_KEY and settings.HUME_SECRET_KEY and settings.HUME_EVI_CONFIG_ID)))
    if mode != "hume_evi":
        return results

    try:
        token_payload = mint_evi_access_token()
    except Exception as exc:
        results.append(_ok("token mint", False, str(exc)))
        return results
    results.append(_ok("token mint", bool(token_payload.get("access_token"))))

    prov = build_live_conversation_provider("hume_evi")
    config_id = str(token_payload.get("config_id") or settings.HUME_EVI_CONFIG_ID)
    try:
        await prov.connect(
            config_id=config_id,
            access_token=str(token_payload.get("access_token") or ""),
            session_settings={
                "type": "session_settings",
                "audio": {"encoding": "linear16", "channels": 1, "sample_rate": 16000},
            },
        )
    except Exception as exc:
        results.append(_ok("real EVI connection", False, str(exc)))
        return results
    results.append(_ok("real EVI connection", True))

    # Nudge EVI to invoke the configured custom tool (may still depend on dashboard prompt).
    if hasattr(prov, "send_user_input"):
        await prov.send_user_input(
            text="Please call get_student_speaking_context now so you know my learner profile before we speak."
        )

    tool_call_event: dict | None = None
    assistant_after_tool = False
    deadline = asyncio.get_event_loop().time() + float(settings.SPEAKING_EVI_TIMEOUT_SECONDS or 60)
    sent_tool_response = False

    db = AsyncMock()

    async def _fake_load(db, *, student_id, language_id=1, speaking_goal="general_english"):
        return assemble_student_speaking_live_context(
            student_reference=opaque_student_reference(student_id=student_id),
            speaking_goal=speaking_goal,
            knowledge_model=empty_knowledge_model(student_id=student_id, language_id=language_id),
            skill_graph=SPEAKING_SKILL_GRAPH,
        )

    with patch(
        "app.services.language_speaking_coach.live_context_loader.load_student_speaking_live_context",
        side_effect=_fake_load,
    ):
        while asyncio.get_event_loop().time() < deadline:
            try:
                ev = await prov.receive_event()
            except Exception:
                break
            et = str(ev.get("type") or "")
            if et == "tool_call" and str(ev.get("name") or "") == "get_student_speaking_context":
                tool_call_event = ev
                handled = await handle_evi_tool_call(prov, db, ev, student_id=7501)
                sent_tool_response = handled.get("handled") is True
                results.append(_ok("real tool_call received", True))
                results.append(_ok("EduSpark tool executed", sent_tool_response))
                deadline = asyncio.get_event_loop().time() + float(settings.SPEAKING_EVI_TIMEOUT_SECONDS or 60)
                continue
            if tool_call_event and et in ("assistant_message", "audio_output", "assistant_end"):
                assistant_after_tool = True
                if et == "assistant_end":
                    break

    await prov.close()

    results.append(_ok("real tool_response sent", sent_tool_response))
    results.append(_ok("conversation continues after tool response", assistant_after_tool))

    if tool_call_event is None:
        results.append(_ok("REAL TOOL INTEGRATION ACCEPTED", False, "no tool_call observed"))
        print("\n--- Required Hume dashboard system-prompt addition (NOT applied automatically) ---")
        print(HUME_PROMPT_ADDITION)
    else:
        content_blob = json.dumps(tool_call_event)
        results.append(_ok("no mock provider in real path", "mock_evi" not in content_blob))
        results.append(_ok("REAL TOOL INTEGRATION ACCEPTED", sent_tool_response and assistant_after_tool))

    return results


def main() -> int:
    print("Speaking S7.6 Real Hume EVI Tool Integration Acceptance\n")
    results = asyncio.run(_run())
    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} checks passed")
    if passed == total:
        print("SPEAKING S7.6 REAL TOOL INTEGRATION ACCEPTANCE PASSED.")
        return 0
    print("SPEAKING S7.6 REAL TOOL INTEGRATION ACCEPTANCE FAILED.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
