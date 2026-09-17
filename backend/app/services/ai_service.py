"""Gemma/Ollama tutoring with PDF-scoped RAG context."""

import asyncio
import logging
import re

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ANSWER_BUDGETS = {
    "short": {
        "words": 80,
        "tokens": 300,
        "chars": 900,
        "shape": "إجابة مختصرة وكاملة: ابدأ بالجواب المباشر ثم أضف تفصيلاً داعماً مختصراً.",
    },
    "normal": {
        "words": 300,
        "tokens": 900,
        "chars": 3500,
        "shape": (
            "ابدأ بجواب مباشر، ثم شرح واضح. استخدم فقرات قصيرة أو قائمة مرقّمة "
            "عند الحاجة. غطِّ النقاط ذات الصلة من سياق الدرس."
        ),
    },
    "detailed": {
        "words": 700,
        "tokens": 2000,
        "chars": 7000,
        "shape": (
            "شرح منظّم: جواب افتتاحي ثم تفاصيل بفقرات قصيرة و/أو قوائم مرقّمة "
            "و/أو نقاط. استخدم الميزانية كاملة عندما يدعمها سياق الدرس."
        ),
    },
}

VALID_PERSONALITY_MODES = frozenset(
    {
        "friendly_teacher",
        "strict_teacher",
        "coach",
        "mentor",
        "exam_prep",
        "kid_friendly",
    }
)

# Tone instructions for the model (Arabic). Keys are API-stable; UI shows Arabic labels.
PERSONALITY_MODES = {
    "friendly_teacher": (
        "معلم ودود — نبرة دافئة ومشجّعة. استخدم تشجيعاً مختصراً عندما يفهم الطالب الفكرة. "
        "ابقَ ملتزماً بحقائق الدرس فقط."
    ),
    "strict_teacher": (
        "معلم صارم — نبرة مباشرة ومركّزة على الدقة. قلّل المجاملات والحشو. "
        "اشرح بوضوح دون إضافة معلومات من خارج الدرس."
    ),
    "coach": (
        "مدرب تحفيزي — نبرة محفّزة. قسّم الفكرة إلى خطوات يسهل على الطالب متابعتها. "
        "شجّع على التقدّم باستخدام حقائق الدرس فقط."
    ),
    "mentor": (
        "مرشد — نبرة هادئة وعميقة. اربط الأفكار بفهم أوسع عندما يسمح سياق الدرس بذلك. "
        "لا تضف حقائق جديدة."
    ),
    "exam_prep": (
        "تحضير امتحانات — ركّز على المفاهيم المهمّة في الدرس، واذكر أخطاء شائعة مرتبطة "
        "بنفس المفاهيم إذا وردت في سياق الدرس. لا تخترع أسئلة أو حقائق."
    ),
    "kid_friendly": (
        "مبسّط للأطفال — مفردات بسيطة جداً، جمل قصيرة، شرح خطوة بخطوة، أمثلة ودودة وسهلة. "
        "مناسب لطلاب أصغر سنّاً. لا تستخدم مصطلحات معقدة إلا إذا وردت في الدرس."
    ),
}


def _personality_instructions(personality_mode: str | None) -> str:
    mode = (personality_mode or "friendly_teacher").strip()
    if mode not in VALID_PERSONALITY_MODES:
        mode = "friendly_teacher"
    return PERSONALITY_MODES[mode]


VALID_TEACHER_TEACHING_STYLES = frozenset(
    {
        "step_by_step",
        "concept_first",
        "exam_focused",
        "practical_examples",
        "discussion_based",
    }
)

TEACHER_TEACHING_STYLE = {
    "step_by_step": (
        "اشرح خطوة بخطوة بترقيم واضح. لا تتخطّ خطوة قبل أن تكون السابقة مفهومة "
        "من سياق الدرس."
    ),
    "concept_first": (
        "ابدأ بالفكرة الأساسية والمفهوم العام، ثم انتقل إلى التفاصيل والأمثلة "
        "من سياق الدرس."
    ),
    "exam_focused": (
        "ركّز على ما يُحتمل أن يُسأل عنه في الامتحان: تعريفات، قواعد، ونقاط مهمة "
        "من الدرس فقط."
    ),
    "practical_examples": (
        "اربط الشرح بأمثلة تطبيقية قصيرة مستمدة من سياق الدرس. لا تخترع أمثلة "
        "خارجية."
    ),
    "discussion_based": (
        "قدّم الشرح بأسلوب حواري: اربط الأفكار ببعضها واشرح لماذا كل جزء مهم "
        "وفق الدرس."
    ),
}

VALID_TEACHER_TONES = frozenset({"friendly", "strict", "balanced"})

TEACHER_TONE = {
    "friendly": "نبرة ودودة وداعمة. استخدم تشجيعاً مختصراً عندما يناسب الشرح.",
    "strict": "نبرة مباشرة وصارمة على الدقة. قلّل المجاملات والحشو.",
    "balanced": "نبرة متوازنة: واضحة ومحترمة دون مبالغة في الحماس أو الجفاف.",
}

VALID_TEACHER_QUESTION_STYLES = frozenset({"asks_questions", "explains_only", "mixed"})

TEACHER_QUESTION_STYLE = {
    "asks_questions": (
        "يمكنك إنهاء الشرح بسؤال تأملي قصير واحد يساعد الطالب على التفكير "
        "في مفهوم من الدرس — دون أسئلة متعددة أو عبارات فارغة."
    ),
    "explains_only": "قدّم الشرح فقط دون أسئلة متابعة في نهاية الإجابة.",
    "mixed": (
        "غالباً اشرح مباشرة. أحياناً أضف سؤالاً قصيراً واحداً عندما يساعد "
        "على الفهم — لا تكرّر أسئلة في كل إجابة."
    ),
}

VALID_TEACHER_MOTIVATION_LEVELS = frozenset({"low", "medium", "high"})

TEACHER_MOTIVATION = {
    "low": "تحفيز منخفض: اكتفِ بالشرح الواضح دون عبارات تحفيزية إضافية.",
    "medium": "تحفيز متوسط: تشجيع مختصر وطبيعي عندما يناسب السياق.",
    "high": "تحفيز مرتفع: شجّع الطالب بعبارات قصيرة ومحفّزة مع بقاء الشرح مركزاً على الدرس.",
}


def _teacher_instruction(value: str | None, valid: frozenset, mapping: dict, default: str) -> str:
    key = (value or default).strip()
    if key not in valid:
        key = default
    return mapping[key]


def _teacher_question_rule(question_style: str | None) -> str:
    style = (question_style or "mixed").strip()
    if style == "asks_questions":
        return (
            "- يمكنك إنهاء الإجابة بسؤال تأملي واحد قصير مرتبط بمفهوم من الدرس."
        )
    if style == "mixed":
        return (
            "- يمكنك أحياناً إضافة سؤال تأملي واحد قصير — لا تكرّر أسئلة في كل إجابة."
        )
    return (
        "- لا تضف أسئلة متابعة أو عبارات مثل \"شو رأيك؟\"، \"تمام؟\"، \"فهمت؟\" في نهاية الإجابة."
    )


EGYPTIAN_TO_SYRIAN = (
    ("بتاعه", "تبعه"),
    ("بتاعها", "تبعها"),
    ("بتاعهم", "تبعهم"),
    ("بتاعي", "تبعي"),
    ("بتاعك", "تبعك"),
    ("بتاعنا", "تبعنا"),
    ("بتاع", "تبع"),
    ("بتاعة", "تبع"),
    ("بتوع", "تبع"),
    ("عشان", "حتى"),
    ("علشان", "حتى"),
    ("إيه", "شو"),
    ("ايه", "شو"),
    ("كده", "هيك"),
    ("دلوقتي", "هلأ"),
    ("ازاي", "كيف"),
    ("ليه", "ليش"),
    ("عايز", "بدك"),
    ("عايزة", "بدك"),
    ("عاوز", "بدك"),
    ("عاوزة", "بدك"),
    ("حاجة", "شي"),
    ("حاجات", "أشياء"),
    ("كويس", "منيح"),
    ("برضه", "كمان"),
    ("برده", "كمان"),
    ("أوي", "كتير"),
    ("اوي", "كتير"),
    ("خالص", "تماماً"),
    ("معلش", "ولا يهمك"),
    ("بص", "شوف"),
    ("بصي", "شوفي"),
    ("مياه", "ماء"),
    ("مية", "مي"),
    ("النهارده", "اليوم"),
    ("امتى", "إيمتى"),
    ("فين", "وين"),
    ("مفيش", "ما في"),
    ("وده", "وهذا"),
    ("ودي", "وهذه"),
    ("فده", "فهذا"),
    ("فدي", "فهذه"),
    ("دول", "هدول"),
    ("ده", "هذا"),
    ("دي", "هذه"),
    ("زي", "مثل"),
)

CASUAL_OPENING_PATTERNS = (
    r"^\s*شباب[،,\s]+",
    r"^\s*شبا[،,\s]+",
    r"^\s*شوا[،,\s]+",
    r"^\s*يا\s+حلوين[،,\s]+",
    r"^\s*يا\s+حلو[،,\s]+",
    r"^\s*هلا\s+يا\s+حلو[،,\s]+",
)

CASUAL_TRAILING_PATTERNS = (
    r"\s*شو\s+رأيك[؟?]?\s*$",
    r"\s*فهمت[؟?]?\s*$",
    r"\s*واضح[؟?]?\s*$",
    r"\s*تمام[؟?]?\s*$",
)

OUT_OF_SCOPE_REPLY = (
    "عذرا، هذا السؤال خارج محتوى الدرس المرفوع. "
    "راجع ملف PDF أو اسألني عن جزء موجود بالدرس."
)

SHORT_CONTEXT_REPLY = (
    "النص المستخرج من ملف الدرس قصير جداً، لذلك ما بقدر أشرح بتفصيل بدون ما اخترع معلومات. "
    "الموجود عندي من الدرس هو:\n\n{context}\n\n"
    "إذا بدك شرح أدق، ارفع PDF أوضح أو يحتوي نصاً أكثر."
)

AI_UNAVAILABLE_REPLY = (
    "ما قدرت أحضّر إجابة دقيقة هلأ لأن المساعد الذكي تأخر بالرد. "
    "جرب اسأل مرة ثانية بعد شوي."
)


_SHORT_CONTEXT_PREFIX = SHORT_CONTEXT_REPLY.split("{context}")[0]


def is_real_reply(reply: str) -> bool:
    """Return False for fallback replies that should not get interactive visuals."""
    if reply in (OUT_OF_SCOPE_REPLY, AI_UNAVAILABLE_REPLY):
        return False
    if reply.startswith(_SHORT_CONTEXT_PREFIX):
        return False
    return True


def _is_context_too_short(context: str) -> bool:
    words = [w for w in context.split() if len(w.strip()) > 1]
    return len(context.strip()) < 120 or len(words) < 12


def _format_lesson_reply(text: str) -> str:
    """Normalize lesson-chat layout for readability without changing facts."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            if out and out[-1] != "":
                out.append("")
            i += 1
            continue

        if re.match(r"^[-*•]\s+", stripped):
            if out and out[-1] != "":
                out.append("")
            n = 1
            while i < len(lines):
                item = lines[i].strip()
                if not item:
                    break
                match = re.match(r"^[-*•]\s+(.*)", item)
                if not match:
                    break
                out.append(f"{n}. {match.group(1).strip()}")
                n += 1
                i += 1
            continue

        out.append(lines[i].rstrip())
        i += 1

    formatted = "\n".join(out)
    formatted = re.sub(r"([^\n])\n(## )", r"\1\n\n\2", formatted)
    formatted = re.sub(r"\n{3,}", "\n\n", formatted)
    return formatted.strip()


def _compact_reply(text: str, max_chars: int) -> str:
    cleaned = _format_lesson_reply(text)
    if len(cleaned) <= max_chars:
        return cleaned

    paragraph_cut = cleaned.rfind("\n\n", 0, max_chars)
    min_cut = min(280, max_chars // 3)
    if paragraph_cut >= min_cut:
        return cleaned[:paragraph_cut].strip() + "..."

    sentence_marks = (".", "؟", "!", "؟", "\n")
    cut = max(cleaned.rfind(mark, 0, max_chars) for mark in sentence_marks)
    if cut < min_cut:
        cut = cleaned.rfind(" ", 0, max_chars)
    if cut < min_cut:
        cut = max_chars

    return cleaned[:cut].strip().rstrip("،,:;") + "..."


def _normalize_dialect(text: str) -> str:
    normalized = text
    for pattern in CASUAL_OPENING_PATTERNS:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    for pattern in CASUAL_TRAILING_PATTERNS:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    for source, target in EGYPTIAN_TO_SYRIAN:
        normalized = re.sub(rf"(?<!\w){re.escape(source)}(?!\w)", target, normalized)
    return normalized


def _finalize_reply(text: str, max_chars: int) -> str:
    return _normalize_dialect(_compact_reply(text, max_chars))


def _answer_budget(question: str, preferred_explanation_style: str | None = None) -> dict:
    """Resolve answer budget. Profile preference applies when the student chose it in settings."""
    q = question.strip().lower()

    explicit_short_keywords = (
        "اختصر",
        "باختصار",
        "مختصر",
        "جواب قصير",
        "بكلمة",
        "كلمتين",
        "نعم او لا",
        "نعم أو لا",
        "صح او خطأ",
        "صح أو خطأ",
    )
    definition_keywords = (
        "ما هو",
        "ما هي",
        "عرف",
        "تعريف",
    )
    detailed_keywords = (
        "بالتفصيل",
        "فصل",
        "اشرح بالتفصيل",
        "شرح كامل",
        "خطوة بخطوة",
        "مع مثال",
        "أمثلة",
        "امثلة",
        "قارن",
        "حل",
        "برهن",
        "علل",
    )
    normal_keywords = (
        "اشرح",
        "وضح",
        "فسر",
        "ليش",
        "لماذا",
        "كيف",
        "ما فهمت",
        "بدي افهم",
    )

    if any(keyword in q for keyword in explicit_short_keywords):
        return ANSWER_BUDGETS["short"]
    if any(keyword in q for keyword in detailed_keywords):
        return ANSWER_BUDGETS["detailed"]
    if any(keyword in q for keyword in normal_keywords):
        return ANSWER_BUDGETS["normal"]
    if preferred_explanation_style in ANSWER_BUDGETS:
        return ANSWER_BUDGETS[preferred_explanation_style]
    if any(keyword in q for keyword in definition_keywords):
        return ANSWER_BUDGETS["normal"]
    if len(q.split()) <= 5:
        return ANSWER_BUDGETS["short"]
    return ANSWER_BUDGETS["normal"]


async def generate_ollama_text(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    json_mode: bool = False,
) -> str:
    """Generate text through Ollama's local HTTP API."""
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": model or settings.OLLAMA_MODEL,
        "messages": [],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens
    if json_mode:
        payload["format"] = "json"
    if system:
        payload["messages"].append({"role": "system", "content": system})
    payload["messages"].append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return (data.get("message", {}).get("content") or "").strip()


async def generate_tutor_reply(
    question: str,
    context_chunks: list[str],
    persona_prompt: str,
    subject: str,
    grade: str,
    difficulty: str = "medium",
    *,
    student_age: int | None = None,
    academic_interests: list[str] | None = None,
    personal_hobbies: list[str] | None = None,
    learning_style: str | None = None,
    future_goal: str | None = None,
    preferred_explanation_style: str | None = None,
    personality_mode: str | None = None,
    teacher_teaching_style: str | None = None,
    teacher_tone: str | None = None,
    teacher_question_style: str | None = None,
    teacher_motivation_level: str | None = None,
    teacher_display_name: str | None = None,
    teacher_bio: str | None = None,
    teacher_signature_phrase: str | None = None,
    learning_memory_summary: str | None = None,
    weak_topics: list[str] | None = None,
    strong_topics: list[str] | None = None,
    repeated_mistakes: list[str] | None = None,
    recent_lessons: list[str] | None = None,
) -> str:
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
    budget = _answer_budget(question, preferred_explanation_style=preferred_explanation_style)

    if not context.strip():
        return OUT_OF_SCOPE_REPLY

    if _is_context_too_short(context):
        return SHORT_CONTEXT_REPLY.format(context=context.strip()[:500])

    personality_block = _personality_instructions(personality_mode)
    teaching_style_block = _teacher_instruction(
        teacher_teaching_style, VALID_TEACHER_TEACHING_STYLES, TEACHER_TEACHING_STYLE, "step_by_step"
    )
    tone_block = _teacher_instruction(
        teacher_tone, VALID_TEACHER_TONES, TEACHER_TONE, "balanced"
    )
    question_style_block = _teacher_instruction(
        teacher_question_style, VALID_TEACHER_QUESTION_STYLES, TEACHER_QUESTION_STYLE, "mixed"
    )
    motivation_block = _teacher_instruction(
        teacher_motivation_level, VALID_TEACHER_MOTIVATION_LEVELS, TEACHER_MOTIVATION, "medium"
    )
    question_rule = _teacher_question_rule(teacher_question_style)
    teacher_name = (teacher_display_name or "").strip() or "المعلّم"
    teacher_bio_text = (teacher_bio or "").strip() or "غير محددة"
    signature_text = (teacher_signature_phrase or "").strip()
    interests_text = "، ".join(academic_interests or []) if academic_interests else "غير محددة"
    hobbies_text = "، ".join(personal_hobbies or []) if personal_hobbies else "غير محددة"
    weak_text = "، ".join(weak_topics or []) if weak_topics else "لا يوجد"
    strong_text = "، ".join(strong_topics or []) if strong_topics else "لا يوجد"
    mistakes_text = "؛ ".join(repeated_mistakes or []) if repeated_mistakes else "لا يوجد"
    recent_lessons_text = "، ".join(recent_lessons or []) if recent_lessons else "لا يوجد"
    memory_summary_text = (learning_memory_summary or "").strip() or "لا توجد ذاكرة تعليمية محفوظة بعد."

    system = f"""{persona_prompt}

Strict rules:
- Answer in neutral classroom Arabic with a light Syrian touch. Keep it professional and easy for Syrian students.
- Prefer words like: شو، ليش، كيف، هيك، هلأ، حتى، مشان، منيح.
- Never use Egyptian dialect words such as: عشان، علشان، بتاع، إيه، كده، دلوقتي، ازاي، عايز، برضه، أوي، خالص.
- Use only information from the lesson context.
- Every sentence must be supported by the lesson context. If a sentence is not supported, do not write it.
- Personalization, teacher style, learning memory, and personality change tone, vocabulary, and structure only. They must not add new factual claims beyond the lesson context.
- Learning memory is historical signal only — never invent past quiz results, mistakes, or lessons not listed below.
{question_rule}
- If a word in the lesson context is corrupted by OCR/PDF extraction, do not guess that word; use only the clear surrounding facts.
- Do not say the student's question is unclear when it contains understandable lesson terms.
- Adapt the answer length to the student's question.
- Current answer budget: at most {budget["words"]} Arabic words.
- Current answer shape: {budget["shape"]}
- Use lesson terms exactly as they appear in the context when possible.
- Do not add analogies, nicknames, or outside examples unless they only illustrate concepts already present in the lesson context without adding new facts.
- If the teacher persona conflicts with these dialect rules, follow these dialect rules.
- Avoid casual openings such as: شباب، شبا، شوا، يا حلو، يا حلوين.
- Start directly with the answer; do not repeat the student's question or write a long introduction.
- If the student asks for a short answer, keep it very short.
- If the student asks for details, explain clearly but do not turn it into a full article.
- Do not invent examples, equations, facts, or quiz-style answers that are not explicitly in the context.
- Be very careful with negation: never flip a fact's meaning. Words like "تنعدم", "ينعدم", "معدوم", "غير موجود", "لا يوجد", "نادر" already express absence by themselves — do NOT add "ما" or "لا" before them, because that reverses the meaning into the opposite of the lesson context.

Formatting (readability — do not change lesson facts):
- ابدأ مباشرة بالجواب على سؤال الطالب دون مقدمة طويلة.
- استخدم قوائم مرقّمة (1. 2. 3.) للخطوات والتسلسل.
- استخدم نقاط (- ) للخصائص والأنواع والأمثلة.
- اكتب فقرات قصيرة (2–4 أسطر كحد أقصى). تجنّب جدار نص واحد.
- استخدم **كلمة** للمصطلحات المهمة باقتضاب.
- عند الحاجة يمكنك استخدام عناوين فرعية بصيغة "## عنوان" مع سطر فارغ قبلها.
- Whenever you write a mathematical equation, formula, or symbolic expression (e.g. variables, Greek letters, fractions, derivatives), wrap it in single dollar signs like $...$ for inline math or double dollar signs like $$...$$ for a standalone equation. Do not write raw equations without these delimiters.
- If the lesson context is short or unclear, say that clearly and summarize only what is available.
- If the answer is not in the lesson context, say that the question is outside the lesson.
- Subject: {subject}. Grade: {grade}. Student level: {difficulty}.

Priority order when signals conflict:
1. Lesson context (highest — never violate lesson facts)
2. Teacher teaching profile (structure, pacing, interaction style)
3. Student learning memory (emphasis, pacing, revisiting weak areas — facts still from lesson only)
4. Student personalization (grade, age, learning style, interests)
5. Student personality mode (tone overlay)
6. Personal hobbies and future goal (examples and connections only)

Teacher identity:
- Display name: {teacher_name}
- Bio: {teacher_bio_text}
- Signature phrase (use naturally and sparingly, at most once when appropriate): {signature_text or "غير محددة"}

Teacher teaching profile:
- Teaching style ({teacher_teaching_style or "step_by_step"}): {teaching_style_block}
- Tone ({teacher_tone or "balanced"}): {tone_block}
- Question style ({teacher_question_style or "mixed"}): {question_style_block}
- Motivation level ({teacher_motivation_level or "medium"}): {motivation_block}

Student learning memory (adapt emphasis only — do not invent history):
- Summary: {memory_summary_text}
- Weak topics: {weak_text}
- Strong topics: {strong_text}
- Repeated mistakes / misconceptions: {mistakes_text}
- Recently studied lessons: {recent_lessons_text}
- If the current lesson topic matches a weak topic, explain more carefully with shorter steps and recap key terms from the lesson.
- If the current lesson topic matches a strong topic, you may use a slightly faster pace while staying complete.
- If repeated mistakes are listed and relate to the current question, address the likely misconception explicitly using lesson facts only.

Student profile:
- Grade level: {grade}
- Age: {student_age if student_age is not None else "غير محددة"}
- Learning level: {difficulty}
- Learning style: {learning_style if learning_style else "theoretical"}
- Personality mode: {personality_mode if personality_mode else "friendly_teacher"}
- Future goal: {future_goal if future_goal else "undecided"}
- Preferred explanation style: {preferred_explanation_style if preferred_explanation_style else "normal"}
- Academic interests: {interests_text}
- Personal hobbies: {hobbies_text}

Personalization instructions (grounded in lesson context only; never invent facts):
- Grade vocabulary: lower grades (الصف 1–4) = very simple words; middle (5–9) = clear school vocabulary; secondary (10–12) = more academic terms. Grade always overrides personality complexity.
- Age: if provided, use it as an additional signal for vocabulary and pacing (younger = simpler, older = more academic).
- Learning style: visual = more descriptive explanation; practical = real-life framing; theoretical = concept-focused; step_by_step = numbered breakdowns.
- Personality tone ({personality_mode or "friendly_teacher"}): {personality_block}
- Academic interests: prefer examples and emphasis aligned with the student's academic interests when the lesson context supports it.
- Personal hobbies: when the lesson context supports the underlying concept, use the student's hobbies for short illustrative analogies or examples (e.g. "مثل…"). When hobbies are listed, include at least one brief hobby-based illustration when appropriate — without adding hobby-specific facts not in the lesson.
- Future goal: when appropriate, connect explanations to the student's future goal without adding new facts.
- Preferred explanation style: when the student chose short/normal/detailed in profile settings, follow that length budget even if the question is brief.
"""

    user_prompt = f"""Lesson context:
{context[:12000]}

Student question:
{question}

Answer in neutral Arabic with a light Syrian touch in at most {budget["words"]} words. Do not use Egyptian dialect.
Use short paragraphs, numbered lists for steps, bullet points (- ) for properties/types/examples, and **bold** for key terms.
"""

    if settings.LLM_PROVIDER.lower() == "ollama":
        try:
            reply = await generate_ollama_text(
                user_prompt,
                system=system,
                max_tokens=budget["tokens"],
            )
            if reply:
                return _finalize_reply(reply, budget["chars"])
        except Exception as exc:
            logger.warning("Ollama chat failed: %s", exc)

    from app.services.claude_service import generate_claude_text, is_claude_configured

    if is_claude_configured():
        try:
            reply = await generate_claude_text(
                user_prompt,
                system=system,
                temperature=0.2,
                max_tokens=budget["tokens"] + 8192,
                timeout=60.0,
            )
            if reply:
                return _finalize_reply(reply, budget["chars"])
            logger.warning("Claude chat returned empty reply")
        except Exception as exc:
            logger.warning("Claude chat failed: %s", exc)

    return AI_UNAVAILABLE_REPLY


async def generate_llm_json(
    prompt: str,
    *,
    system: str = "",
    temperature: float = 0.4,
    max_output_tokens: int = 1024,
    model_name: str | None = None,
) -> str:
    """Structured JSON via Claude — shared helper for modules that need JSON output."""
    from app.services.claude_service import generate_claude_json

    return await generate_claude_json(
        prompt,
        system=system,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        model_name=model_name,
    )


# Backward-compatible alias — implementation now uses Claude.
generate_gemini_json = generate_llm_json


async def generate_planner_interpretation(message: str) -> dict | None:
    """Optional LLM layer for planner chat — returns structured JSON or None."""
    import json

    system = """أنت مساعد تخطيط دراسي. استخرج من رسالة الطالب أحداثاً وجدولاً بصيغة JSON فقط:
{"life_events":[{"title":"","event_type":"private_lesson|exam|sport|family|school|other","day_of_week":0-6,"start_time":"HH:MM","duration_minutes":60,"subject":""}],"profile_updates":{"preferred_period":"morning|evening|night"},"weak_subjects":["رياضيات"]}
لا تكتب أي نص خارج JSON."""

    prompt = f"رسالة الطالب:\n{message}"

    raw = None
    if settings.LLM_PROVIDER.lower() == "ollama":
        try:
            raw = await generate_ollama_text(prompt, system=system, max_tokens=300)
        except Exception:
            pass
    if not raw:
        from app.services.claude_service import generate_claude_text, is_claude_configured

        if is_claude_configured():
            try:
                raw = await generate_claude_text(prompt, system=system, max_tokens=300, timeout=60.0)
            except Exception:
                pass

    if not raw:
        return None
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        return None
    return None
