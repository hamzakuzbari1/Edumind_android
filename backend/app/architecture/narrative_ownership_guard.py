"""Narrative Ownership Guard — static analysis for listening backend (Phase 2.1.1).

Detects student-facing educational copy outside the Learning Narrative Builder.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Canonical owner: all modules under this path may emit student educational copy.
NARRATIVE_OWNER_PREFIX = "app/services/language_learning_narrative/"

# LLM / generation-internal modules — not student UI copy.
INTERNAL_GENERATION_GLOBS = (
    "**/prompt.py",
    "**/profiles.py",
)

# Deprecated modules that must not grow; all prose findings must be in debt manifest.
DEPRECATED_GENERATOR_SUFFIXES: tuple[str, ...] = (
    "teacher_summary.py",
    "learning_path.py",
    "student_summary.py",
)

# Known educational phrase probes (not exhaustive — combined with structural heuristics).
EDUCATIONAL_PHRASE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bGreat work\b", re.I),
    re.compile(r"\bGood effort\b", re.I),
    re.compile(r"\bYou improved\b", re.I),
    re.compile(r"\bYou are improving\b", re.I),
    re.compile(r"\bToday's (Mission|practice|situation)\b", re.I),
    re.compile(r"\bPractice more\b", re.I),
    re.compile(r"\bAlmost there\b", re.I),
    re.compile(r"\bCongratulations\b", re.I),
    re.compile(r"\bKeep pract", re.I),
    re.compile(r"\bwhy this lesson\b", re.I),
    re.compile(r"\bToday's practice targets\b", re.I),
    re.compile(r"\bProgress toward\b", re.I),
    re.compile(r"\bContinue with your next\b", re.I),
    re.compile(r"\bEvery attempt builds\b", re.I),
    re.compile(r"\bStrong session\b", re.I),
)

TEACHER_PROSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bRecent confidence gains\b", re.I),
    re.compile(r"\bNo positive confidence trends\b", re.I),
    re.compile(r"\bNo high-confidence objectives\b", re.I),
    re.compile(r"\bNo under-confident objectives\b", re.I),
    re.compile(r"\bNo confidence state\b", re.I),
    re.compile(r"\bNo format signal\b", re.I),
    re.compile(r"\bNo situation signal\b", re.I),
    re.compile(r"\bIntroduce .+ in an upcoming lesson\b", re.I),
    re.compile(r"\bSchedule a review lesson\b", re.I),
    re.compile(r"\bContinue practising\b", re.I),
    re.compile(r"\bPrioritise lessons\b", re.I),
    re.compile(r"\bMaintain .+ with periodic review\b", re.I),
)

DEFAULT_DEBT_MANIFEST_REL = "architecture/listening_narrative_debt_manifest.json"

SECOND_PERSON_EDUCATIONAL = re.compile(
    r"\b(you|your)\b.*\b("
    r"practice|practise|improve|learn|listen|lesson|mission|ready|scored|"
    r"congratulations|almost|work on|will practice|have mastered"
    r")\b",
    re.I,
)

MISSION_OPENERS = re.compile(
    r"^(This lesson|Today you|After this lesson|Continue with|Curriculum selected)",
    re.I,
)

DIAGNOSTIC_MARKERS = re.compile(
    r"\b(intent=|curriculum=|blended=|goal=|challenge_score|recommendation score)\b",
    re.I,
)

# Listening backend scan roots (relative to backend/).
LISTENING_SCAN_ROOTS: tuple[str, ...] = (
    "app/services/language_learning_facts",
    "app/services/language_learning_goal",
    "app/services/language_learning_stage",
    "app/services/language_learning_narrative",
    "app/services/language_listening_explainability",
    "app/services/language_listening_challenge",
    "app/services/language_listening_confidence",
    "app/services/language_listening_curriculum",
    "app/services/language_listening_intelligence",
    "app/services/language_listening_progression",
    "app/services/language_listening_quality",
    "app/services/language_listening_lesson_context.py",
    "app/services/language_listening_service.py",
    "app/services/language_listening_prefill_task.py",
)


@dataclass(frozen=True, slots=True)
class CopyFinding:
    rel_path: str
    line: int
    snippet: str
    reason: str
    fingerprint: str


@dataclass
class GuardResult:
    allowed_owner_prefix: str
    scanned_files: int
    findings: list[CopyFinding] = field(default_factory=list)
    debt_findings: list[CopyFinding] = field(default_factory=list)
    new_violations: list[CopyFinding] = field(default_factory=list)
    debt_manifest_drift: list[str] = field(default_factory=list)
    narrative_owner_files: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.new_violations and not self.debt_manifest_drift


def _normalize_path(path: Path, backend_root: Path) -> str:
    rel = path.relative_to(backend_root).as_posix()
    return rel


def _is_narrative_owner(rel_path: str) -> bool:
    return rel_path.startswith(NARRATIVE_OWNER_PREFIX) or rel_path.replace("\\", "/").startswith(
        NARRATIVE_OWNER_PREFIX
    )


def _is_internal_generation(rel_path: str) -> bool:
    name = Path(rel_path).name
    return name in {"prompt.py", "profiles.py"}


def _is_deprecated_generator(rel_path: str) -> bool:
    return any(rel_path.endswith(suffix) for suffix in DEPRECATED_GENERATOR_SUFFIXES)


def _is_prose_candidate(text: str) -> bool:
    stripped = text.strip()
    words = stripped.split()
    return len(words) >= 4 and len(stripped) >= 28 and not stripped.startswith("Phase ")


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


def is_educational_student_copy(text: str) -> tuple[bool, str]:
    """Return (is_copy, reason)."""
    stripped = text.strip()
    if len(stripped) < 12:
        return False, ""
    if stripped.startswith(("http://", "https://", "SELECT ", "INSERT ", "UPDATE ")):
        return False, ""
    if DIAGNOSTIC_MARKERS.search(stripped):
        return False, ""
    # Engine reason codes
    if stripped in {"no_candidates_fallback", "balanced_coverage"}:
        return False, ""
    if re.fullmatch(r"[a-z0-9_=.:\s\-]+", stripped) and "=" in stripped and " " not in stripped.split("=")[0]:
        return False, ""

    for pattern in EDUCATIONAL_PHRASE_PATTERNS:
        if pattern.search(stripped):
            return True, f"phrase:{pattern.pattern}"

    if SECOND_PERSON_EDUCATIONAL.search(stripped):
        return True, "second_person_educational"

    if MISSION_OPENERS.search(stripped):
        return True, "mission_opener"

    # Imperative coaching without second person
    if re.search(r"\b(Practise|Practice|Prioritise|Schedule a review|Introduce .+ in an upcoming lesson)\b", stripped):
        return True, "imperative_coaching"

    for pattern in TEACHER_PROSE_PATTERNS:
        if pattern.search(stripped):
            return True, f"teacher_prose:{pattern.pattern}"

    if re.search(r"\bprogress toward\b", stripped, re.I):
        return True, "progress_phrase"

    return False, ""


class _StringLiteralVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.literals: list[tuple[int, str]] = []

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            self.literals.append((node.lineno, node.value))

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
        if parts:
            self.literals.append((node.lineno, "".join(parts)))


def _docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                lines.add(node.body[0].lineno)
    return lines


def extract_string_literals(source: str) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    skip_lines = _docstring_lines(tree)
    visitor = _StringLiteralVisitor()
    visitor.visit(tree)
    return [(line, text) for line, text in visitor.literals if line not in skip_lines]


def collect_listening_python_files(backend_root: Path) -> list[Path]:
    files: set[Path] = set()
    for root_spec in LISTENING_SCAN_ROOTS:
        path = backend_root / root_spec
        if path.is_file() and path.suffix == ".py":
            files.add(path.resolve())
        elif path.is_dir():
            for py in path.rglob("*.py"):
                if py.is_file():
                    files.add(py.resolve())
    return sorted(files)


def scan_listening_backend(backend_root: Path, *, debt_manifest: dict[str, list[str]] | None = None) -> GuardResult:
    debt_manifest = debt_manifest or {}
    result = GuardResult(
        allowed_owner_prefix=NARRATIVE_OWNER_PREFIX,
        scanned_files=0,
    )

    for path in collect_listening_python_files(backend_root):
        rel = _normalize_path(path, backend_root)
        result.scanned_files += 1

        if _is_narrative_owner(rel):
            result.narrative_owner_files.append(rel)
            continue
        if _is_internal_generation(rel):
            continue

        is_deprecated = _is_deprecated_generator(rel)

        source = path.read_text(encoding="utf-8")
        for line_no, literal in extract_string_literals(source):
            is_copy, reason = is_educational_student_copy(literal)
            if not is_copy:
                if is_deprecated and _is_prose_candidate(literal) and not DIAGNOSTIC_MARKERS.search(literal):
                    if re.search(
                        r"\b(you|your|practice|practise|lesson|review|confidence|mission|improve|listening journey)\b",
                        literal,
                        re.I,
                    ):
                        is_copy, reason = True, "deprecated_generator_prose"
                    else:
                        continue
                else:
                    continue
            finding = CopyFinding(
                rel_path=rel,
                line=line_no,
                snippet=literal[:120].replace("\n", " "),
                reason=reason,
                fingerprint=_fingerprint(literal),
            )
            result.findings.append(finding)

            if rel in debt_manifest:
                result.debt_findings.append(finding)
            else:
                result.new_violations.append(finding)

    # Verify debt manifest fingerprints have not drifted or shrunk/grown
    debt_by_file: dict[str, set[str]] = {}
    for f in result.debt_findings:
        debt_by_file.setdefault(f.rel_path, set()).add(f.fingerprint)

    for rel, expected_fps in debt_manifest.items():
        expected = set(expected_fps)
        actual = debt_by_file.get(rel, set())
        if actual != expected:
            result.debt_manifest_drift.append(
                f"{rel}: expected {len(expected)} fingerprints, found {len(actual)} "
                f"(missing={sorted(expected - actual)}, extra={sorted(actual - expected)})"
            )

    # Debt files must not contain violations outside manifest
    for rel, fps in debt_by_file.items():
        if rel not in debt_manifest:
            continue
        extra = fps - set(debt_manifest[rel])
        if extra:
            result.debt_manifest_drift.append(f"{rel}: undeclared new fingerprints {sorted(extra)}")

    return result


def build_debt_manifest(result: GuardResult) -> dict[str, list[str]]:
    by_file: dict[str, set[str]] = {}
    for finding in result.findings:
        if _is_narrative_owner(finding.rel_path):
            continue
        if _is_internal_generation(finding.rel_path):
            continue
        by_file.setdefault(finding.rel_path, set()).add(finding.fingerprint)
    return {rel: sorted(fps) for rel, fps in sorted(by_file.items())}


def load_debt_manifest(backend_root: Path) -> dict[str, list[str]]:
    manifest_path = backend_root / DEFAULT_DEBT_MANIFEST_REL
    if not manifest_path.is_file():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {str(k): list(v) for k, v in data.get("files", {}).items()}


def findings_to_dict(findings: list[CopyFinding]) -> list[dict[str, object]]:
    return [
        {
            "file": f.rel_path,
            "line": f.line,
            "reason": f.reason,
            "fingerprint": f.fingerprint,
            "snippet": f.snippet,
        }
        for f in findings
    ]
