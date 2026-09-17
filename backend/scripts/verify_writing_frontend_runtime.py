"""Verify Writing frontend uses W6/W7 runtime — not legacy catalog flow."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def main() -> int:
    print("Writing Frontend Runtime Integration Verification\n")
    results: list[bool] = []

    writing_view = (SRC / "views/student/languages/StudentLanguageWritingView.vue").read_text(encoding="utf-8")
    practice = (SRC / "components/language/WritingPracticePanel.vue").read_text(encoding="utf-8")
    language_api = (SRC / "api/language.js").read_text(encoding="utf-8")
    router = (SRC / "router/index.js").read_text(encoding="utf-8")

    print("[Route]")
    results.append(_ok("route still /student/languages/writing", "languages/writing" in router and "StudentLanguageWritingView" in router))

    print("\n[Legacy removed from Writing page]")
    results.append(_ok("view does not import fetchWritingPrompts", "fetchWritingPrompts" not in writing_view))
    results.append(_ok("view does not import submitWritingPrompt", "submitWritingPrompt" not in writing_view))
    results.append(_ok("view does not import fetchWritingPrompt", "fetchWritingPrompt" not in writing_view))
    results.append(_ok("practice does not use legacy submit", "submitWritingPrompt" not in practice))
    results.append(_ok("practice does not use legacy list", "fetchWritingPrompts" not in practice))

    print("\n[W6/W7 API wired]")
    results.append(_ok("generateWritingLesson in language.js", "generateWritingLesson" in language_api))
    results.append(_ok("fetchWritingJourney in language.js", "fetchWritingJourney" in language_api))
    results.append(_ok("submitWritingDraft in language.js", "submitWritingDraft" in language_api))
    results.append(_ok("POST /writing/generate path", "/student/languages/writing/generate" in language_api))
    results.append(_ok("POST /writing/{id}/draft path", "/draft" in language_api and "contentItemId" in language_api))
    results.append(_ok("practice uses generate composable", "useWritingLesson" in practice))
    results.append(_ok("practice uses draft composable", "useWritingRevision" in practice))
    results.append(_ok("practice uses coach composable", "useWritingCoach" in practice))

    print("\n[UX structure]")
    results.append(_ok("journey + practice tabs", "writingJourney.tabs.journey" in writing_view and "WritingPracticePanel" in writing_view))
    results.append(_ok("mission card reused", "ListeningMissionCard" in practice))
    results.append(_ok("coach panel present", "WritingCoachPanel" in practice))
    results.append(_ok("evaluation panel present", "WritingEvaluationPanel" in practice))
    results.append(_ok("progress panel present", "WritingProgressPanel" in practice))

    print("\n[Composables exist]")
    for name in ("useWritingJourney", "useWritingLesson", "useWritingCoach", "useWritingRevision", "useWritingEvaluation"):
        results.append(_ok(f"{name}.js exists", (SRC / f"composables/{name}.js").is_file()))

    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} checks passed")
    if passed == total:
        print("WRITING FRONTEND RUNTIME INTEGRATED — browser QA ready.")
        return 0
    print("WRITING FRONTEND NOT READY — fix failures.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
