"""Private local artifact handling for offline grammar authoring."""

from __future__ import annotations

import json
import os
import uuid
from html import escape
from pathlib import Path
from typing import Any

DEFAULT_PRIVATE_ARTIFACT_DIR = (
    Path(__file__).resolve().parents[3]
    / "uploads"
    / "private"
    / "grammar_canonical_authoring"
)


def write_raw_authoring_artifact(
    *,
    revision_id: str,
    raw_response_text: str | None,
    success: bool,
    base_dir: Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Write raw provider output to a private local file and return only a reference."""

    if raw_response_text is None:
        return None
    root = base_dir or DEFAULT_PRIVATE_ARTIFACT_DIR
    kind = "success" if success else "failed"
    target_dir = root / "raw" / kind
    target_dir.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    safe_revision_id = "".join(ch for ch in str(revision_id) if ch.isalnum() or ch == "-")[:80]
    final_path = target_dir / f"{safe_revision_id}-{run_id}.json"
    tmp_path = final_path.with_suffix(".tmp")
    payload = {
        "revision_id": str(revision_id),
        "success": bool(success),
        "metadata": dict(metadata or {}),
        "raw_response_text": raw_response_text,
    }
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp_path, final_path)
    try:
        return str(final_path.relative_to(root))
    except ValueError:
        return str(final_path)


def write_student_safe_review_artifact(
    *,
    revision_id: str,
    inspection: dict[str, Any],
    base_dir: Path | None = None,
) -> str:
    root = base_dir or DEFAULT_PRIVATE_ARTIFACT_DIR
    target_dir = root / "reviews"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_revision_id = "".join(ch for ch in str(revision_id) if ch.isalnum() or ch == "-")[:80]
    final_path = target_dir / f"{safe_revision_id}-student-safe.json"
    tmp_path = final_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(inspection, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp_path, final_path)
    return str(final_path)


def write_student_safe_review_html_artifact(
    *,
    revision_id: str,
    inspection: dict[str, Any],
    base_dir: Path | None = None,
) -> str:
    root = base_dir or DEFAULT_PRIVATE_ARTIFACT_DIR
    target_dir = root / "reviews"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_revision_id = "".join(ch for ch in str(revision_id) if ch.isalnum() or ch == "-")[:80]
    final_path = target_dir / f"{safe_revision_id}-student-safe.html"
    tmp_path = final_path.with_suffix(".tmp")
    tmp_path.write_text(_review_html(inspection), encoding="utf-8")
    os.replace(tmp_path, final_path)
    return str(final_path)


_PRIVATE_REVIEW_KEYS = {
    "server_teaching_metadata",
    "expected_answer",
    "sample_answer",
    "success_criteria",
    "misconception",
    "feedback_reasoning",
    "hint",
    "similar_retry_prompt",
    "validation_metadata",
    "diagnostics",
    "validation_summary",
    "private_diagnostics",
    "raw_response_text",
    "raw_artifact_ref",
}

_HTML_HIDDEN_KEYS = _PRIVATE_REVIEW_KEYS | {"id"}

_SECTION_LABELS = {
    "understand": "\u0627\u0641\u0647\u0645 \u0627\u0644\u0641\u0643\u0631\u0629",
    "see_how_it_works": "\u0634\u0648\u0641 \u0643\u064a\u0641 \u062a\u0639\u0645\u0644",
    "rules_and_mistakes": "\u0627\u0644\u0642\u0627\u0639\u062f\u0629 \u0648\u0627\u0644\u0623\u062e\u0637\u0627\u0621",
    "guided_practice": "\u062a\u062f\u0631\u0628 \u062e\u0637\u0648\u0629 \u0628\u062e\u0637\u0648\u0629",
    "use_it_yourself": "\u0627\u0633\u062a\u062e\u062f\u0645\u0647\u0627 \u0628\u0646\u0641\u0633\u0643",
}

_TARGET_FORM_DISPLAY = {
    "affirmative_am": "am",
    "affirmative_is": "is",
    "affirmative_are": "are",
    "negative_am_not": "am not",
    "negative_is_not": "is not / isn't",
    "negative_are_not": "are not / aren't",
    "question_am": "Am I ...?",
    "question_is": "Is he/she/it ...?",
    "question_are": "Are you/we/they ...?",
    "short_answer_am": "Yes, I am. / No, I'm not.",
    "short_answer_is": "Yes, she is. / No, she isn't.",
    "short_answer_are": "Yes, they are. / No, they aren't.",
}


def _review_html(inspection: dict[str, Any]) -> str:
    identity = inspection.get("canonical_identity") or {}
    revision = inspection.get("revision") or {}
    sections = inspection.get("learner_sections") or {}
    display_name = str(identity.get("display_name") or "").strip()
    if not display_name:
        display_name = _display_name_from_grammar_id(str(identity.get("grammar_id") or ""))
    title = f"{display_name} {identity.get('cefr_level', '')} review".strip()
    body = [
        "<!doctype html>",
        '<html lang="ar" dir="rtl">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title>",
        "<style>",
        "body{font-family:Arial,'Noto Naskh Arabic',sans-serif;margin:32px;line-height:1.75;background:#f7f7f5;color:#202124}",
        "main{max-width:980px;margin:auto;background:white;padding:28px;border:1px solid #ddd}",
        "h1{font-size:28px;margin:0 0 8px} h2{font-size:22px;margin-top:28px;border-top:1px solid #e5e5e5;padding-top:20px}",
        ".meta{direction:ltr;text-align:left;color:#5f6368;font-size:13px;margin-bottom:20px}",
        ".block{margin:10px 0;padding:10px 12px;background:#fafafa;border-right:4px solid #2f6f73}",
        ".key{font-weight:700;color:#17484d}.item{margin:8px 0}.en{direction:ltr;display:inline-block}",
        "ul{margin:6px 0 10px}.warning{color:#8a4b00}",
        "</style>",
        "</head>",
        "<body><main>",
        f"<h1>{escape(display_name or 'Canonical grammar lesson')}</h1>",
        "<div class=\"meta\">",
        f"CEFR: {escape(str(identity.get('cefr_level') or ''))} | locale: {escape(str(identity.get('locale') or ''))} | ",
        f"revision: {escape(str(revision.get('revision_number') or ''))} | status: {escape(str(revision.get('status') or ''))} | ",
        f"hash: {escape(str(revision.get('content_hash') or ''))}",
        "</div>",
    ]
    for key in ("understand", "see_how_it_works", "rules_and_mistakes", "guided_practice", "use_it_yourself"):
        body.append(f"<h2>{_SECTION_LABELS[key]}</h2>")
        body.append(_render_value(sections.get(key)))
    body.append("</main></body></html>")
    return "\n".join(body)


def _render_value(value: Any, *, key_name: str = "") -> str:
    if isinstance(value, dict):
        parts = []
        for key, child in value.items():
            if key in _HTML_HIDDEN_KEYS:
                continue
            parts.append("<div class=\"block\">")
            parts.append(f"<div class=\"key\">{escape(str(key))}</div>")
            parts.append(_render_value(child, key_name=str(key)))
            parts.append("</div>")
        return "\n".join(parts)
    if isinstance(value, list):
        items = [f"<li>{_render_value(item, key_name=key_name)}</li>" for item in value if not _is_private_item(item)]
        return "<ul>" + "\n".join(items) + "</ul>"
    if value is None:
        return ""
    text = escape(_student_display_text(key_name, value))
    if _looks_english(text):
        return f'<span class="en">{text}</span>'
    return f'<div class="item">{text}</div>'


def _is_private_item(value: Any) -> bool:
    return isinstance(value, dict) and any(key in _PRIVATE_REVIEW_KEYS for key in value)


def _looks_english(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    ascii_letters = [ch for ch in letters if ord(ch) < 128]
    return len(ascii_letters) >= max(4, len(letters) // 2)


def _student_display_text(key_name: str, value: Any) -> str:
    raw = str(value)
    if key_name == "target_form":
        return _TARGET_FORM_DISPLAY.get(raw.strip(), raw)
    return raw


def _display_name_from_grammar_id(grammar_id: str) -> str:
    if not grammar_id:
        return "Canonical grammar lesson"
    return grammar_id.replace("gram_", "").replace("_", " ").title()
