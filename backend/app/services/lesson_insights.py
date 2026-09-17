"""Small extractive lesson insights for the student lesson page."""

from __future__ import annotations

import re
from collections import Counter

ARABIC_STOPWORDS = {
    "هذا",
    "هذه",
    "ذلك",
    "الذي",
    "التي",
    "على",
    "إلى",
    "الى",
    "عن",
    "من",
    "في",
    "هو",
    "هي",
    "ما",
    "ماذا",
    "كيف",
    "هل",
    "كل",
    "ثم",
    "كما",
    "مع",
    "بين",
    "أو",
    "او",
    "أن",
    "ان",
    "إن",
    "الى",
    "لكن",
    "حيث",
    "داخل",
    "خلال",
    "عملية",
    "يقوم",
    "تقوم",
    "يتم",
    "تبدأ",
    "تعطي",
    "تحتوي",
    "يوجد",
    "توجد",
    "يسمى",
    "تسمى",
    "يدعى",
    "تدعى",
    "بامتصاص",
    "امتصاص",
    "يدعى",
    "تدعى",
    "يكون",
    "تكون",
}


def build_lesson_insights(text: str, max_bullets: int = 5, max_keywords: int = 5) -> dict:
    clean = _clean_text(text)
    return {
        "summary": _summary_bullets(clean, max_bullets),
        "keywords": _keywords(clean, max_keywords),
    }


def _clean_text(text: str) -> str:
    text = re.sub(r"\[صفحة\s+\d+\]", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[\w\u0600-\u06FF]+", text.lower())
    return [t for t in raw if len(t) > 2 and t not in ARABIC_STOPWORDS and not t.isdigit()]


def _summary_bullets(text: str, max_bullets: int) -> list[str]:
    sentences = [
        s.strip(" ،،:-")
        for s in re.split(r"(?<=[.!؟])\s+|[؛;]\s*", text)
        if s.strip()
    ]
    bullets: list[str] = []
    seen = set()
    for sentence in sentences:
        if len(sentence) < 35 or len(sentence.split()) < 6:
            continue
        if sentence.startswith(("عنوان", "درس", "صفحة")):
            continue
        compact = sentence[:190].strip()
        key = " ".join(_tokens(compact)[:8])
        if not key or key in seen:
            continue
        seen.add(key)
        bullets.append(compact)
        if len(bullets) >= max_bullets:
            break
    if bullets:
        return bullets

    fallback = text[:220].strip()
    return [fallback] if fallback else []


def _keywords(text: str, max_keywords: int) -> list[str]:
    tokens = _tokens(text)
    if not tokens:
        return []

    selected = _known_phrases(text, max_keywords)
    phrases: Counter[str] = Counter()
    sentences = re.split(r"(?<=[.!؟])\s+|[؛;]\s*", text)
    for sentence in sentences:
        sentence_tokens = _tokens(sentence)
        for size in (3, 2):
            for idx in range(0, len(sentence_tokens) - size + 1):
                phrase_tokens = sentence_tokens[idx : idx + size]
                phrase = " ".join(phrase_tokens)
                if len(phrase) < 8:
                    continue
                phrases[phrase] += 1

    for phrase, _ in phrases.most_common(max_keywords * 2):
        if _overlaps(phrase, selected):
            continue
        selected.append(phrase)
        if len(selected) >= max_keywords:
            break

    if len(selected) < max_keywords:
        for token, _ in Counter(tokens).most_common(max_keywords * 3):
            if any(token in phrase.split() for phrase in selected):
                continue
            selected.append(token)
            if len(selected) >= max_keywords:
                break

    return selected[:max_keywords]


def _known_phrases(text: str, max_keywords: int) -> list[str]:
    common_patterns = (
        "التركيب الضوئي",
        "البالستيدات الخضراء",
        "ثاني أوكسيد الكربون",
        "ثاني أكسيد الكربون",
        "ضوء الشمس",
        "طاقة الشمس",
        "الطاقة الشمسية",
        "سكر الغلوكوز",
        "الغلوكوز",
        "اليخضور",
        "الكلوروفيل",
        "الأوكسجين",
        "أوكسجين",
        "الماء",
    )
    found: list[str] = []
    for phrase in common_patterns:
        if phrase in text and not _overlaps(phrase, found):
            found.append(phrase)
        if len(found) >= max_keywords:
            break
    return found


def _overlaps(candidate: str, selected: list[str]) -> bool:
    candidate_tokens = set(candidate.split())
    for phrase in selected:
        tokens = set(phrase.split())
        if candidate_tokens & tokens:
            return True
    return False
