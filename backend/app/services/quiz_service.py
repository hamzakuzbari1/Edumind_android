"""Generate lesson-grounded MCQ questions with hints."""

import asyncio
import json
import logging
import random
import re
import time

from app.core.config import get_settings
from app.services.ai_service import generate_ollama_text

logger = logging.getLogger(__name__)
settings = get_settings()

QUIZ_FOCUS_HINTS = (
    "المصطلحات الأساسية الواردة في الدرس",
    "العلاقات بين السبب والنتيجة",
    "خطوات العملية أو تسلسل الفكرة",
    "الأمثلة والأسماء العلمية المذكورة",
    "الفروق بين المفاهيم القريبة",
)

GENERIC_QUIZ_PHRASES = (
    "الفكرة الرئيسية",
    "فهم المفاهيم الأساسية",
    "حفظ دون فهم",
    "تجاهل الأمثلة",
    "الخروج عن موضوع الدرس",
    "تطبيق عملي للدرس",
    "حل مثال مشابه",
    "كيف تتأكد",
    "شرح الفكرة بكلماتك",
    "تخطي التمارين",
    "الإجابة عشوائياً",
)

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
    "أي",
    "اي",
    "كل",
    "درس",
    "الدرس",
    "المادة",
    "حسب",
    "يتم",
    "تم",
}

WEAK_ANSWER_PHRASES = {
    "عنوان",
    "العنوان",
    "هذه الصبغة",
    "هذا الدرس",
    "نفس الوقت",
    "في نفس الوقت",
    "عندما",
    "وهو غذاء النبات",
}


def _call_claude_text(prompt: str, timeout: int = 20, max_attempts: int = 2) -> str:
    """Call Claude for plain text generation, with retry and per-call timeout."""
    from app.services.claude_service import generate_claude_text_sync, is_claude_configured

    if not is_claude_configured():
        return ""

    for attempt in range(1, max_attempts + 1):
        try:
            return generate_claude_text_sync(prompt, timeout=float(timeout), max_tokens=1800)
        except Exception as exc:
            if attempt == max_attempts:
                logger.warning("Claude text generation failed after %s attempts: %s", attempt, exc)
                return ""
            logger.info("Claude text generation attempt %s failed, retrying: %s", attempt, exc)
            time.sleep(attempt * 2)
    return ""


async def generate_quiz_questions(
    lesson_text: str,
    subject: str,
    grade: str,
    count: int | None = None,
    avoid_questions: list[str] | None = None,
    focus_hint: str | None = None,
) -> list[dict]:
    count = count or settings.QUIZ_COUNT
    avoid_questions = [q.strip() for q in (avoid_questions or []) if q.strip()]
    focus_hint = focus_hint or random.choice(QUIZ_FOCUS_HINTS)
    sample = lesson_text[:8000]

    if is_lesson_text_too_short(sample):
        logger.info("Skipping quiz generation because extracted lesson text is too short")
        return []

    avoid_block = ""
    if avoid_questions:
        previous = "\n".join(f"- {q[:180]}" for q in avoid_questions[:12])
        avoid_block = f"""
Previous quiz questions to avoid:
{previous}
"""

    if settings.LLM_PROVIDER.lower() == "ollama":
        try:
            prompt = f"""Create exactly {count} Arabic multiple-choice questions from the lesson text only.

Strict rules:
- Use only clear facts directly stated in the lesson text.
- Do not create generic study questions such as "main idea", "how do you know you understood", or "practical application".
- The correct answer must be a term or fact that appears in the lesson text.
- Each question has exactly 4 options, one answer that matches one option exactly, and one correct_index from 0 to 3.
- Keep questions specific to the lesson.
- Make the questions varied. Do not repeat the same fact with different wording.
- Use this variation focus: {focus_hint}.
- If previous quiz questions are listed, do not repeat or rephrase them.
- The hint must be Arabic only. Do not use English phrases such as "The text states".
- Return valid JSON only, as one object with this shape:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer":"...","correct_index":0,"hint":"..."}}]}}

Subject: {subject}
Grade: {grade}
{avoid_block}

Lesson:
{sample}
"""
            text = await generate_ollama_text(
                prompt,
                temperature=0.45 if avoid_questions else 0.2,
                max_tokens=1800,
                json_mode=True,
            )
            items = _extract_quiz_items(text)
            questions = _normalize_quiz(items, count, sample, avoid_questions)
            questions = _supplement_quiz_from_text(questions, count, sample, avoid_questions)
            if questions:
                return questions
            logger.warning("Ollama quiz generation returned no lesson-grounded questions")
        except Exception as exc:
            logger.warning("Ollama quiz generation failed: %s", exc)

    from app.services.claude_service import is_claude_configured

    if is_claude_configured():
        try:
            prompt = f"""من محتوى الدرس التالي فقط، أنشئ بالضبط {count} أسئلة اختيار من متعدد بالعربية.
كل سؤال يجب أن يعتمد على معلومة واضحة موجودة نصاً في الدرس.
ممنوع إنشاء أسئلة عامة مثل الفكرة الرئيسية أو كيف أتأكد أنني فهمت.
نوّع الأسئلة وركّز هذه المرة على: {focus_hint}.
إذا وجدت أسئلة سابقة في القائمة التالية فلا تكررها ولا تعيد صياغتها:
{chr(10).join(f"- {q[:180]}" for q in avoid_questions[:12]) if avoid_questions else "لا توجد أسئلة سابقة."}
كل سؤال 4 خيارات وإجابة صحيحة واحدة في حقل answer وتلميح عند الخطأ.
يجب أن يكون التلميح بالعربية فقط، ممنوع استخدام عبارات إنكليزية مثل The text states.
المادة: {subject}، الصف: {grade}.

أعد JSON فقط بهذا الشكل:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer":"...","correct_index":0,"hint":"..."}}]}}

المحتوى:
{sample}
"""
            text = await asyncio.to_thread(_call_claude_text, prompt)
            items = _extract_quiz_items(text)
            questions = _normalize_quiz(items, count, sample, avoid_questions)
            questions = _supplement_quiz_from_text(questions, count, sample, avoid_questions)
            if questions:
                return questions
            logger.warning("Claude quiz generation returned no lesson-grounded questions")
        except Exception as exc:
            logger.warning("Quiz generation failed: %s", exc)

    fallback_questions = _supplement_quiz_from_text([], count, sample, avoid_questions)
    if fallback_questions:
        return fallback_questions

    logger.info("Skipping quiz because no reliable lesson-grounded questions were generated")
    return []


async def generate_remedial_questions(
    lesson_text: str,
    subject: str,
    grade: str,
    mistakes: list[dict],
    per_mistake: int = 2,
) -> list[dict]:
    sample = lesson_text[:8000]
    if is_lesson_text_too_short(sample) or not mistakes:
        return []

    out: list[dict] = []
    for mistake in mistakes[:3]:
        target_count = max(1, per_mistake)
        avoid_questions = [mistake.get("question", ""), *[q["question"] for q in out]]
        generated: list[dict] = []

        if settings.LLM_PROVIDER.lower() == "ollama":
            try:
                prompt = f"""Create exactly {target_count} short Arabic remedial multiple-choice questions from the lesson text only.

The student missed this question:
{mistake.get("question", "")}

Student answer:
{mistake.get("selected", "")}

Correct answer:
{mistake.get("correct", "")}

Strict rules:
- Questions must train the same concept as the missed question, but do not repeat the original wording.
- Use only facts directly stated in the lesson text.
- Each question has exactly 4 options, one answer that matches one option exactly, and one correct_index from 0 to 3.
- Keep the language clear and simple Arabic.
- The hint must be Arabic only. Do not use English phrases such as "The text states".
- Return valid JSON only, as one object with this shape:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer":"...","correct_index":0,"hint":"..."}}]}}

Subject: {subject}
Grade: {grade}

Lesson:
{sample}
"""
                text = await generate_ollama_text(
                    prompt,
                    temperature=0.35,
                    max_tokens=900,
                    json_mode=True,
                )
                items = _extract_quiz_items(text)
                generated = _normalize_quiz(items, target_count, sample, avoid_questions)
            except Exception as exc:
                logger.warning("Ollama remedial quiz generation failed: %s", exc)

        from app.services.claude_service import is_claude_configured

        if not generated and is_claude_configured():
            try:
                prompt = f"""من محتوى الدرس التالي فقط، أنشئ بالضبط {target_count} سؤال/أسئلة اختيار من متعدد قصيرة بالعربية لعلاج خطأ الطالب.

السؤال الذي أخطأ فيه الطالب:
{mistake.get("question", "")}

إجابة الطالب:
{mistake.get("selected", "")}

الإجابة الصحيحة:
{mistake.get("correct", "")}

قواعد صارمة:
- يجب أن تدرّب الأسئلة الجديدة على نفس المفهوم الذي أخطأ فيه الطالب، دون تكرار صياغة السؤال الأصلي.
- استخدم فقط معلومات واردة نصاً في الدرس.
- كل سؤال 4 خيارات، إجابة صحيحة واحدة في حقل answer، وحقل correct_index من 0 إلى 3.
- استخدم لغة عربية واضحة وبسيطة.
- يجب أن يكون التلميح بالعربية فقط، ممنوع استخدام عبارات إنكليزية مثل The text states.
- أعد JSON فقط بهذا الشكل:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer":"...","correct_index":0,"hint":"..."}}]}}

المادة: {subject}، الصف: {grade}.

المحتوى:
{sample}
"""
                text = await asyncio.to_thread(_call_claude_text, prompt)
                items = _extract_quiz_items(text)
                generated = _normalize_quiz(items, target_count, sample, avoid_questions)
            except Exception as exc:
                logger.warning("Gemini remedial quiz generation failed: %s", exc)

        generated = _supplement_remedial_from_text(
            generated,
            target_count,
            sample,
            mistake,
            avoid_questions,
        )
        out.extend(generated[:target_count])

    return out


def is_lesson_text_too_short(text: str) -> bool:
    clean = re.sub(r"\[[^\]]+\]", " ", text)
    words = [w for w in re.findall(r"[\w\u0600-\u06FF]+", clean) if len(w) > 1]
    return len(clean.strip()) < 120 or len(words) < 12


def _extract_quiz_items(text: str) -> list:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    candidates = [cleaned]
    object_match = re.search(r"\{[\s\S]*\}", cleaned)
    if object_match:
        candidates.append(object_match.group())
    array_match = re.search(r"\[[\s\S]*\]", cleaned)
    if array_match:
        candidates.append(array_match.group())

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if isinstance(data, dict):
            items = data.get("questions") or data.get("quiz") or data.get("items")
            return items if isinstance(items, list) else []
        if isinstance(data, list):
            return data
    return []


def _content_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[\w\u0600-\u06FF]+", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in ARABIC_STOPWORDS}


def _is_generic_quiz_item(question: str, options: list[str]) -> bool:
    combined = " ".join([question, *options])
    return any(phrase in combined for phrase in GENERIC_QUIZ_PHRASES)


def _is_supported_by_lesson(value: str, lesson_text: str, lesson_tokens: set[str]) -> bool:
    clean_value = value.strip().lower()
    if not clean_value:
        return False
    if clean_value in lesson_text.lower():
        return True
    tokens = _content_tokens(clean_value)
    if not tokens:
        return False
    hits = sum(1 for token in tokens if token in lesson_tokens)
    return hits >= max(1, min(2, len(tokens)))


def _is_repeated_question(question: str, avoid_questions: list[str]) -> bool:
    question_tokens = _content_tokens(question)
    if not question_tokens:
        return False
    for old_question in avoid_questions:
        old_tokens = _content_tokens(old_question)
        if not old_tokens:
            continue
        overlap = len(question_tokens & old_tokens)
        similarity = overlap / max(len(question_tokens), len(old_tokens))
        if similarity >= 0.62:
            return True
    return False


def _option_index_from_text(options: list[str], text: str) -> int | None:
    normalized_text = text.strip().lower()
    if not normalized_text:
        return None
    for idx, option in enumerate(options):
        normalized_option = option.strip().lower()
        if normalized_option == normalized_text:
            return idx
    for idx, option in enumerate(options):
        normalized_option = option.strip().lower()
        if normalized_option and normalized_option in normalized_text:
            return idx
    return None


def _shuffle_options(options: list[str], correct_index: int) -> tuple[list[str], int]:
    indexed_options = list(enumerate(options))
    random.shuffle(indexed_options)
    shuffled = [option for _, option in indexed_options]
    new_correct_index = next(
        idx for idx, (original_idx, _) in enumerate(indexed_options) if original_idx == correct_index
    )
    return shuffled, new_correct_index


def _clean_lesson_text(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_answer_phrase(value: str) -> str:
    value = re.sub(r"[\"“”«»]", "", value)
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\s+", " ", value).strip(" .،:؛-")
    if value.startswith("غاز "):
        value = value[4:].strip()
    if value.startswith("صبغة "):
        value = value[5:].strip()
    return value


def _normalized_phrase(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _add_candidate(candidates: list[str], seen: set[str], value: str) -> None:
    value = _clean_answer_phrase(value)
    tokens = _content_tokens(value)
    if not value or len(value) < 3 or len(value) > 48 or not tokens:
        return
    normalized = _normalized_phrase(value)
    if normalized in WEAK_ANSWER_PHRASES:
        return
    if normalized.startswith(("هذه ", "هذا ", "عندما ", "في ")):
        return
    if normalized.endswith((" فقط", " بنفسها")):
        return
    if normalized in seen:
        return
    seen.add(normalized)
    candidates.append(value)


def _candidate_answer_phrases(text: str) -> list[str]:
    clean = _clean_lesson_text(text)
    candidates: list[str] = []
    seen: set[str] = set()

    patterns = (
        r"تدعى\s+([^،.؟]+)",
        r"تُسمى\s+([^،.؟]+)",
        r"تسمى\s+([^،.؟]+)",
        r"تحتوي\s+على\s+([^،.؟]+)",
        r"تكوين\s+([^،.؟]+)",
        r"(?:و)?يُ?طلق\s+(?:غاز\s+)?([^،.؟]+?)\s+ك",
        r"(?:و)?يمتص\s+(?:النبات\s+)?(?:غاز\s+)?([^،.؟]+?)\s+من\s+(?:الهواء|الأرض|الألرض)",
        r"يقوم\s+([^،.؟]+?)\s+ب",
        r"يسقط\s+([^،.؟]+?)\s+على",
        r"يحول\s+([^،.؟]+?)\s+و",
    )
    for pattern in patterns:
        for match in re.findall(pattern, clean):
            _add_candidate(candidates, seen, match)

    for term in (
        "الماء",
        "الأوكسجين",
        "الأكسجين",
        "أوكسجين",
        "الغلوكوز",
        "الطاقة الشمسية",
        "ضوء الشمس",
    ):
        if term in clean:
            _add_candidate(candidates, seen, term)

    for pattern in (r"[\"“”«]([^\"“”«»]{3,48})[\"“”»]", r"\(([\u0600-\u06FF][^)]{2,42})\)"):
        for match in re.findall(pattern, clean):
            _add_candidate(candidates, seen, match)

    return candidates


def _lesson_sentences(text: str) -> list[str]:
    clean = _clean_lesson_text(text)
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.؟!])\s+", clean)
        if len(sentence.strip()) > 25
    ]


def _sentence_for_answer(answer: str, sentences: list[str]) -> str | None:
    normalized_answer = _normalized_phrase(answer)
    for sentence in sentences:
        if normalized_answer in _normalized_phrase(sentence):
            return sentence
    return None


def _cloze_snippet(sentence: str, answer: str) -> str | None:
    match = re.search(re.escape(answer), sentence, flags=re.IGNORECASE)
    if not match:
        return None
    start = max(match.start() - 70, 0)
    end = min(match.end() + 70, len(sentence))
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(sentence) else ""
    snippet = f"{prefix}{sentence[start:match.start()]}____{sentence[match.end():end]}{suffix}"
    return re.sub(r"\s+", " ", snippet).strip()


def _fallback_options(answer: str, candidates: list[str]) -> list[str] | None:
    answer_key = _normalized_phrase(answer)
    pool = [
        candidate
        for candidate in candidates
        if _normalized_phrase(candidate) != answer_key
        and answer_key not in _normalized_phrase(candidate)
        and _normalized_phrase(candidate) not in answer_key
    ]
    unique_pool: list[str] = []
    seen: set[str] = set()
    for candidate in pool:
        key = _normalized_phrase(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_pool.append(candidate)
    if len(unique_pool) < 3:
        return None
    return [answer, *random.sample(unique_pool, 3)]


def _supplement_quiz_from_text(
    existing: list[dict],
    count: int,
    lesson_text: str,
    avoid_questions: list[str] | None = None,
) -> list[dict]:
    if len(existing) >= count:
        return existing[:count]

    out = list(existing)
    avoid_questions = avoid_questions or []
    generated_questions = [q["question"] for q in out]
    used_answers = {
        _normalized_phrase(q["options"][q["correct_index"]])
        for q in out
        if q.get("options") and 0 <= q.get("correct_index", -1) < len(q["options"])
    }
    candidates = _candidate_answer_phrases(lesson_text)
    random.shuffle(candidates)
    sentences = _lesson_sentences(lesson_text)

    for answer in candidates:
        if len(out) >= count:
            break
        answer_key = _normalized_phrase(answer)
        if answer_key in used_answers:
            continue
        sentence = _sentence_for_answer(answer, sentences)
        if not sentence:
            continue
        snippet = _cloze_snippet(sentence, answer)
        if not snippet:
            continue
        question = f"حسب نص الدرس، ما الكلمة أو العبارة التي تكمل الجملة: «{snippet}»؟"
        if _is_repeated_question(question, avoid_questions + generated_questions):
            continue
        options = _fallback_options(answer, candidates)
        if not options:
            continue
        options, correct_index = _shuffle_options(options, 0)
        out.append(
            {
                "question": question,
                "options": options,
                "correct_index": correct_index,
                "hint": f"ارجعي إلى الجملة في الدرس: {sentence[:160]}",
            }
        )
        generated_questions.append(question)
        used_answers.add(answer_key)

    return out[:count]


def _sentence_with_token_overlap(answer: str, sentences: list[str]) -> str | None:
    answer_tokens = _content_tokens(answer)
    if not answer_tokens:
        return None
    best_sentence = None
    best_hits = 0
    for sentence in sentences:
        hits = len(answer_tokens & _content_tokens(sentence))
        if hits > best_hits:
            best_hits = hits
            best_sentence = sentence
    return best_sentence if best_hits else None


def _supplement_remedial_from_text(
    existing: list[dict],
    count: int,
    lesson_text: str,
    mistake: dict,
    avoid_questions: list[str] | None = None,
) -> list[dict]:
    if len(existing) >= count:
        return existing[:count]

    out = list(existing)
    avoid_questions = avoid_questions or []
    answer = _clean_answer_phrase(str(mistake.get("correct") or ""))
    if not answer:
        return out

    candidates = _candidate_answer_phrases(lesson_text)
    seen_candidates = {_normalized_phrase(candidate) for candidate in candidates}
    if _normalized_phrase(answer) not in seen_candidates:
        candidates.insert(0, answer)

    sentences = _lesson_sentences(lesson_text)
    sentence = _sentence_for_answer(answer, sentences) or _sentence_with_token_overlap(answer, sentences)
    if not sentence:
        return out

    options = _fallback_options(answer, candidates)
    if not options:
        return out

    variants: list[tuple[str, str]] = []
    snippet = _cloze_snippet(sentence, answer)
    if snippet:
        variants.append(
            (
                f"حتى نعالج الخطأ، ما العبارة التي تكمل الجملة من الدرس: «{snippet}»؟",
                f"ارجعي إلى الجملة في الدرس: {sentence[:160]}",
            )
        )
    variants.append(
        (
            f"أي خيار يثبت الفكرة الصحيحة للسؤال الذي أخطأتِ فيه: «{str(mistake.get('question') or '')[:90]}»؟",
            f"الفكرة المطلوبة مرتبطة بـ: {answer}",
        )
    )

    for question, hint in variants:
        if len(out) >= count:
            break
        if _is_repeated_question(question, avoid_questions + [q["question"] for q in out]):
            continue
        shuffled_options, correct_index = _shuffle_options(options, 0)
        out.append(
            {
                "question": question,
                "options": shuffled_options,
                "correct_index": correct_index,
                "hint": hint,
            }
        )

    return out[:count]


def _normalize_hint(hint: object) -> str:
    text = str(hint or "").strip()
    if not text:
        return "راجعي الجملة المرتبطة بالسؤال في نص الدرس."

    replacements = (
        (r"(?i)\bthe text states\b\s*:?", "النص يذكر:"),
        (r"(?i)\bthe lesson states\b\s*:?", "الدرس يذكر:"),
        (r"(?i)\baccording to the text\b\s*:?", "حسب نص الدرس:"),
        (r"(?i)\bthe correct answer is\b\s*:?", "الجواب الصحيح هو:"),
        (r"(?i)\bcorrect answer\b\s*:?", "الجواب الصحيح:"),
        (r"(?i)\bstudent answer\b\s*:?", "جوابك:"),
        (r"(?i)\bremember\b\s*:?", "تذكري:"),
        (r"(?i)\bhint\b\s*:?", "تلميح:"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("النص يذكر: '", "النص يذكر: ")
    text = text.replace('النص يذكر: "', "النص يذكر: ")
    text = text.rstrip("'\"")
    if re.search(r"[A-Za-z]{3,}", text):
        text = re.sub(
            r"(?i)\b(the|text|states|lesson|according|correct|answer|student|hint|remember|says|to)\b",
            "",
            text,
        )
        text = re.sub(r"\s+", " ", text).strip(" :،")
    return text or "راجعي الجملة المرتبطة بالسؤال في نص الدرس."


def _normalize_quiz(
    items: list,
    count: int,
    lesson_text: str,
    avoid_questions: list[str] | None = None,
) -> list[dict]:
    out = []
    lesson_tokens = _content_tokens(lesson_text)
    avoid_questions = avoid_questions or []
    for item in items:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        options = [str(option).strip() for option in item.get("options", []) if str(option).strip()]
        try:
            correct_index = int(item.get("correct_index", 0))
        except Exception:
            correct_index = 0
        answer_index = _option_index_from_text(options, str(item.get("answer") or ""))
        if answer_index is not None:
            correct_index = answer_index
        else:
            hint_index = _option_index_from_text(options, str(item.get("hint") or ""))
            if hint_index is not None:
                correct_index = hint_index
        if not question or len(options) != 4 or not 0 <= correct_index <= 3:
            continue
        if len(set(options)) != 4:
            continue
        if _is_generic_quiz_item(question, options):
            continue
        if _is_repeated_question(question, avoid_questions):
            continue
        if not _is_supported_by_lesson(options[correct_index], lesson_text, lesson_tokens):
            continue
        options, correct_index = _shuffle_options(options, correct_index)
        out.append(
            {
                "question": question,
                "options": options,
                "correct_index": correct_index,
                "hint": _normalize_hint(item.get("hint", "راجع الشرح في المحادثة")),
            }
        )
        if len(out) >= count:
            break
    return out
