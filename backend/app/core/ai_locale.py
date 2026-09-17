"""EduSpark Syria — locale defaults for AI-generated content."""

AI_OUTPUT_LANGUAGE = "Arabic"
AI_LOCALE_TAG = "ar-SY"

# English-learning module: output stays in English; audience is Syrian students.
ENGLISH_MODULE_LANGUAGE_RULE = (
    "LANGUAGE: Write all output entirely in English. "
    "Use clear, classroom-appropriate English suitable for Syrian secondary-school students. "
    "Do not respond in Arabic unless quoting lesson text verbatim."
)

# Backward-compatible alias (language module imports).
GEMINI_LANGUAGE_RULE = ENGLISH_MODULE_LANGUAGE_RULE

# ——— Lesson tutor user-facing fallbacks (Arabic) ———

OUT_OF_SCOPE_REPLY = (
    "عذراً، هذا السؤال خارج محتوى الدرس المرفوع. "
    "راجع ملف PDF أو اسأل عن شيء وارد في هذا الدرس."
)

SHORT_CONTEXT_REPLY = (
    "نص الدرس المستخرج قصير جداً ولا يكفي لشرح تفصيلي دون تخمين. "
    "هذا ما هو متوفر من الدرس:\n\n{context}\n\n"
    "لشرح أوضح، ارفع ملف PDF يحتوي نصاً أوضح."
)

AI_UNAVAILABLE_REPLY = (
    "تعذر تجهيز إجابة موثوقة الآن لأن المساعد الذكي لم يستجب في الوقت المناسب. "
    "حاول مرة أخرى بعد قليل."
)

# ——— Default teacher persona (Arabic) ———

DEFAULT_PERSONA = """أنت معلم سوري ودود يشرح للطلاب باللهجة السورية المبسطة.
استخدم أمثلة من الحياة اليومية، اشرح خطوة بخطوة، وشجّع الطالب.
أجب فقط من محتوى الدرس المرفوع. إذا السؤال خارج المحتوى قل ذلك بلطف."""

# ——— Quiz prompt language block (Arabic lesson quizzes) ———

QUIZ_LANGUAGE_RULES = """- اكتب كل سؤال وخيار وإجابة وتلميح بالعربية فقط.
- استخدم فقط معلومات واردة نصاً في محتوى الدرس."""

REMEDIAL_LANGUAGE_RULES = """- اكتب كل سؤال وخيار وإجابة وتلميح بالعربية فقط.
- استخدم لغة عربية واضحة وبسيطة."""

# ——— Voice transcription prompts (Arabic STT fallbacks) ———

STT_TRANSCRIBE_AUDIO_PROMPT = (
    "انسخ هذا التسجيل الصوتي بالعربية. أعد النص فقط بدون تعليقات."
)

STT_TRANSCRIBE_VIDEO_PROMPT = (
    "انسخ كل الكلام المنطوق في هذا الفيديو التعليمي بالعربية. "
    "أعد النص الكامل فقط دون أي تعليقات أو تنسيق إضافي."
)

# Backward-compatible aliases (STT fallbacks).
GEMINI_TRANSCRIBE_AUDIO_PROMPT = STT_TRANSCRIBE_AUDIO_PROMPT
GEMINI_TRANSCRIBE_VIDEO_PROMPT = STT_TRANSCRIBE_VIDEO_PROMPT

# ——— Answer-budget keyword triggers (Arabic) ———

EXPLICIT_SHORT_KEYWORDS = (
    "باختصار",
    "بشكل مختصر",
    "إجابة قصيرة",
    "كلمة واحدة",
    "نعم أو لا",
    "صح أو خطأ",
    "عرّف",
    "تعريف",
)

DEFINITION_KEYWORDS = (
    "ما هو",
    "ما هي",
    "عرّف",
    "تعريف",
    "معنى",
)

DETAILED_KEYWORDS = (
    "بالتفصيل",
    "اشرح بالتفصيل",
    "خطوة بخطوة",
    "بمثال",
    "أمثلة",
    "قارن",
    "حل",
    "برهن",
    "لماذا",
    "كيف",
)

NORMAL_KEYWORDS = (
    "اشرح",
    "وضّح",
    "وضح",
    "لماذا",
    "كيف",
    "ساعدني أفهم",
    "ما فهمت",
)

# ——— Arabic stopwords for quiz/insights tokenization ———

ENGLISH_STOPWORDS = {
    "في",
    "من",
    "إلى",
    "على",
    "عن",
    "مع",
    "هذا",
    "هذه",
    "ذلك",
    "تلك",
    "التي",
    "الذي",
    "ما",
    "هل",
    "أن",
    "إن",
    "كان",
    "كانت",
    "يكون",
    "هو",
    "هي",
    "هم",
    "نحن",
    "أنا",
    "أنت",
    "درس",
    "نص",
    "حسب",
    "وفق",
}


def with_language_rule(system: str) -> str:
    """Append the English-module output rule to a system prompt."""
    system = (system or "").strip()
    if not system:
        return ENGLISH_MODULE_LANGUAGE_RULE
    if ENGLISH_MODULE_LANGUAGE_RULE in system:
        return system
    return f"{system}\n\n{ENGLISH_MODULE_LANGUAGE_RULE}"
