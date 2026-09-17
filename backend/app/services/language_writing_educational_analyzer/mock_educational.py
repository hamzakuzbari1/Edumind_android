"""Teacher-grade heuristic educational analyzer (mock / offline mode).

Used when Claude is unavailable or WRITING_EDUCATIONAL_ANALYZER=mock. It analyses a
draft with linguistic heuristics so that offline QA still produces teacher-like
educational facts across every dimension. It NEVER produces pass/fail decisions.
"""

from __future__ import annotations

import re
from collections import Counter

from app.services.language_writing_educational_analyzer.types import (
    ANALYZER_FACTS_VERSION,
    ClaudeEducationalFacts,
    CoachGuidance,
    DimensionInsight,
    EducationalAnalysisContext,
    GrammarNote,
    VocabularyInsight,
)

_MODEL_NAME = "mock-educational-analyzer"

_STOPWORDS = frozenset(
    """
    a an the and or but so if then than that this these those of to in on at for with from by as is are am was were be been being
    it its it's i you he she we they me him her us them my your his our their do does did have has had not no yes can could will
    would should may might must about into over under again more most very just also too here there when where why how what who
    which whom while because although though into onto off out up down
    """.split()
)

_WEAK_WORDS = frozenset(
    {"good", "bad", "nice", "thing", "things", "stuff", "very", "really", "a lot", "lots", "big", "small", "get", "got"}
)

_CONNECTORS = (
    "because",
    "however",
    "therefore",
    "although",
    "moreover",
    "furthermore",
    "in addition",
    "for example",
    "for instance",
    "as a result",
    "on the other hand",
    "in conclusion",
    "firstly",
    "secondly",
    "finally",
    "whereas",
    "despite",
    "consequently",
)

_SUPPORT_MARKERS = ("because", "for example", "for instance", "such as", "this means", "which means", "in order to", "so that", "the reason")

_GOAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "business": ("meeting", "schedule", "regards", "colleague", "project", "deadline", "client", "report", "attached", "sincerely"),
    "travel": ("hotel", "flight", "trip", "book", "booking", "reservation", "refund", "airport", "luggage", "tour"),
    "ielts": ("opinion", "agree", "disagree", "however", "conclusion", "argument", "furthermore", "society", "government"),
    "academic": ("research", "evidence", "analysis", "study", "results", "hypothesis", "data", "conclusion", "therefore"),
    "creative_writing": ("suddenly", "silence", "whisper", "shadow", "bright", "cold", "heart", "dream", "remember", "felt"),
    "job_interview": ("experience", "skills", "role", "position", "team", "responsibility", "strength", "motivated"),
    "daily_communication": ("friend", "message", "invite", "weekend", "meet", "hi", "hey", "thanks", "sorry", "tomorrow"),
    "general_english": (),
}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def _content_words(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _detect_grammar(text: str) -> list[GrammarNote]:
    notes: list[GrammarNote] = []
    lower = f" {text.lower()} "

    def add(issue: str, rule: str, fix: str, example: str) -> None:
        if len(notes) >= 6:
            return
        notes.append(GrammarNote(issue=issue, rule=rule, fix=fix, example=example))

    if re.search(r"\b(name|friend|brother|sister|mother|father) are\b", lower) or " i are " in lower:
        add(
            "Subject–verb agreement error (a singular subject is used with 'are').",
            "A singular subject takes a singular verb ('is'/'am'), not 'are'.",
            "Match the verb to the subject: use 'is' for he/she/it and singular nouns, 'am' for I.",
            "\"My name are Hamza\" → \"My name is Hamza\".",
        )
    if re.search(r"\bi is\b", lower):
        add(
            "Wrong verb form with 'I'.",
            "The pronoun 'I' always takes 'am'.",
            "Use 'I am' instead of 'I is'.",
            "\"I is happy\" → \"I am happy\".",
        )
    if re.search(r"\b(he|she|it) (go|come|make|do|have|like|want|need|study)\b", lower):
        add(
            "Missing third-person '-s' on the present-simple verb.",
            "In the present simple, he/she/it verbs end in '-s'.",
            "Add '-s' to the verb after he/she/it.",
            "\"She go to school\" → \"She goes to school\".",
        )
    if re.search(r"\b(want|wants|need|needs|like|likes|try|tries|hope|hopes) (go|learn|eat|study|work|play|read|write|speak|see|buy|do|make)\b", lower):
        add(
            "Missing 'to' before the base verb (infinitive).",
            "Verbs like 'want', 'need', and 'like' are followed by 'to' + base verb.",
            "Insert 'to' before the second verb.",
            "\"I want learn English\" → \"I want to learn English\".",
        )
    if re.search(r"\b(he|she|it) don't\b", lower):
        add(
            "Wrong auxiliary with he/she/it.",
            "He/she/it uses 'doesn't', not 'don't'.",
            "Use 'doesn't' for third-person singular.",
            "\"He don't know\" → \"He doesn't know\".",
        )
    if re.search(r"\byesterday\b.*\b(go|eat|come|see|make|take)\b", lower):
        add(
            "Past-time marker used with a present-tense verb.",
            "Time words like 'yesterday' require the past simple.",
            "Change the verb to its past form.",
            "\"Yesterday I go\" → \"Yesterday I went\".",
        )
    doubles = re.findall(r"\b(\w+)\s+\1\b", lower)
    if doubles:
        add(
            f"Repeated word: '{doubles[0]}' appears twice in a row.",
            "Do not duplicate a word accidentally.",
            "Delete the duplicate word.",
            f"\"the {doubles[0]} {doubles[0]}\" → \"the {doubles[0]}\".",
        )
    # Missing sentence-final punctuation on a long run of words
    if len(text.split()) >= 20 and not re.search(r"[.!?]", text):
        add(
            "No sentence-ending punctuation in a long passage.",
            "Sentences must end with a full stop, question mark, or exclamation mark.",
            "Break the text into sentences and add full stops.",
            "\"I like biology it is fun\" → \"I like biology. It is fun.\"",
        )
    # Lowercase 'i' as a pronoun
    if re.search(r"(^|\s)i(\s|')", text) and not re.search(r"(^|\s)I(\s|')", text):
        add(
            "The pronoun 'i' is written in lowercase.",
            "The pronoun 'I' is always capitalised.",
            "Capitalise 'I' everywhere it appears.",
            "\"i think\" → \"I think\".",
        )
    return notes


def _topic_overlap(draft_words: list[str], context: EducationalAnalysisContext) -> float:
    seed = " ".join(
        [context.writing_prompt, context.narrative_why, " ".join(context.vocabulary_primary), " ".join(context.learning_outcomes)]
    )
    seed_words = set(_content_words(seed))
    if not seed_words:
        return 0.6  # no prompt signal — assume moderately on-topic
    draft_set = set(draft_words)
    hits = len(seed_words & draft_set)
    return min(1.0, hits / max(3, len(seed_words) * 0.4))


def _estimate_cefr(
    *, words: list[str], content: list[str], sentences: list[str], connectors: int, grammar_errors: int
) -> tuple[str, str]:
    total = max(1, len(words))
    diversity = len(set(content)) / max(1, len(content)) if content else 0.0
    avg_sentence = total / max(1, len(sentences))
    error_rate = grammar_errors / max(1, len(sentences))

    if total < 25 or error_rate >= 1.0:
        band = "A1"
    elif error_rate >= 0.5 or (avg_sentence < 8 and connectors == 0):
        band = "A2"
    elif connectors <= 1 and diversity < 0.55:
        band = "B1"
    elif connectors >= 2 and avg_sentence >= 12 and diversity >= 0.55:
        band = "B2"
    else:
        band = "B1"
    if connectors >= 4 and diversity >= 0.62 and avg_sentence >= 15 and error_rate < 0.15:
        band = "C1"

    reason = (
        f"Estimated {band}: average sentence length ~{avg_sentence:.0f} words, "
        f"{connectors} linking word(s), vocabulary diversity {diversity:.0%}, "
        f"{grammar_errors} grammar issue(s) noted."
    )
    return band, reason


def _vocabulary_insight(content: list[str], text: str, context: EducationalAnalysisContext) -> VocabularyInsight:
    counts = Counter(content)
    repeated = [w for w, c in counts.most_common(5) if c >= 3]
    lower = text.lower()
    weak = [w for w in _WEAK_WORDS if re.search(rf"\b{re.escape(w)}\b", lower)]
    topic_words = [w.lower() for w in context.vocabulary_primary]
    missing = [w for w in topic_words if w and w.lower() not in lower][:5]
    diversity = len(set(content)) / max(1, len(content)) if content else 0.0

    if diversity >= 0.6 and not repeated:
        score = 0.8
        range_comment = "Good lexical range with little repetition."
    elif repeated:
        score = 0.45
        range_comment = f"Some words are over-used ({', '.join(repeated[:3])}), which narrows the range."
    else:
        score = 0.6
        range_comment = "Everyday vocabulary with limited variety."
    if weak:
        score = min(score, 0.5)

    suggestions: list[str] = []
    if repeated:
        suggestions.append(f"Replace repeated words like '{repeated[0]}' with synonyms.")
    if weak:
        suggestions.append(f"Swap vague words ({', '.join(weak[:2])}) for precise ones.")
    if missing:
        suggestions.append(f"Try using topic words: {', '.join(missing[:3])}.")

    reason_bits = []
    if repeated:
        reason_bits.append("repetition reduces variety")
    if weak:
        reason_bits.append("some word choices are vague")
    if not reason_bits:
        reason_bits.append("word choice is mostly appropriate for the task")
    reason = "Vocabulary: " + ", ".join(reason_bits) + "."

    return VocabularyInsight(
        score=score,
        reason=reason,
        range_comment=range_comment,
        repeated_words=tuple(repeated),
        weak_choices=tuple(weak),
        missing_topic_words=tuple(missing),
        suggestions=tuple(suggestions),
    )


def _organization_insight(text: str, sentences: list[str], connectors: int) -> DimensionInsight:
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if len(sentences) <= 1:
        return DimensionInsight(0.3, "The draft is a single block with no sentence structure to guide the reader.")
    if len(paragraphs) >= 2 and connectors >= 2:
        return DimensionInsight(
            0.82, "Clear structure: separate paragraphs and linking words guide the reader through the ideas."
        )
    if connectors >= 2:
        return DimensionInsight(
            0.68, "Ideas are connected with linking words, but the text would read better split into paragraphs."
        )
    if len(sentences) >= 4:
        return DimensionInsight(
            0.5, "Sentences follow one another but transitions and paragraphing are missing, so the flow is flat."
        )
    return DimensionInsight(0.4, "The organization needs a clearer beginning, middle, and end.")


def _idea_development_insight(text: str, sentences: list[str]) -> DimensionInsight:
    lower = text.lower()
    supports = sum(1 for m in _SUPPORT_MARKERS if m in lower)
    if supports >= 2:
        return DimensionInsight(0.8, "Ideas are explained and backed with reasons or examples, not just listed.")
    if supports == 1:
        return DimensionInsight(0.6, "At least one idea is supported, but most points still need a reason or example.")
    if len(sentences) >= 3:
        return DimensionInsight(0.4, "Ideas are stated as facts without explanation or examples to support them.")
    return DimensionInsight(0.3, "Ideas are only listed briefly and are not developed.")


def _goal_alignment_insight(text: str, context: EducationalAnalysisContext) -> DimensionInsight:
    keywords = _GOAL_KEYWORDS.get(context.personal_goal, ())
    label = context.goal_label
    if not keywords:
        return DimensionInsight(0.7, f"Writing is reasonable for the {label} goal.")
    lower = text.lower()
    hits = sum(1 for k in keywords if k in lower)
    if hits >= 3:
        return DimensionInsight(0.85, f"Strong fit for {label}: uses register and vocabulary expected for this goal.")
    if hits >= 1:
        return DimensionInsight(0.6, f"Partly fits {label}, but more goal-specific language would strengthen it.")
    return DimensionInsight(0.4, f"The tone and vocabulary do not yet match the {label} goal.")


def _task_response_insight(overlap: float, context: EducationalAnalysisContext) -> tuple[DimensionInsight, DimensionInsight]:
    topic_hint = context.writing_prompt or context.narrative_why or "the assigned topic"
    topic_hint = topic_hint if len(topic_hint) <= 80 else topic_hint[:79] + "…"
    if overlap < 0.25:
        tr = DimensionInsight(0.2, f"The draft does not answer the prompt about {topic_hint}.")
        tu = DimensionInsight(0.2, "The writing drifts to unrelated content instead of the requested topic.")
    elif overlap < 0.55:
        tr = DimensionInsight(0.55, "The draft touches the prompt but only answers part of the task.")
        tu = DimensionInsight(0.6, "The student is mostly on topic but misses parts of what was asked.")
    else:
        tr = DimensionInsight(0.82, "The draft clearly addresses what the prompt asks for.")
        tu = DimensionInsight(0.85, "The writing stays on the requested topic throughout.")
    return tr, tu


_DIMENSION_LABELS = {
    "task_response": "Task response",
    "topic": "Topic",
    "coherence": "Coherence",
    "organization": "Organization",
    "idea_development": "Idea development",
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
}


_MOCK_WHY = {
    "task_response": "Answering the actual question matters more than anything else — the rest only counts once the task is addressed.",
    "topic": "Staying on the assigned topic is the priority; off-topic sentences dilute your message.",
    "idea_development": "Your points need support: explaining ideas is what moves your writing up a level.",
    "organization": "Clear structure is the priority so the reader can follow your ideas easily.",
    "grammar": "This grammar pattern is the priority because it repeats across the draft and affects clarity.",
    "vocabulary": "Widening word choice is the priority — repeated, vague words are holding the message back.",
    "coherence": "Linking your ideas is the priority so the draft reads as one connected argument.",
}

_MOCK_EXPLANATION = {
    "task_response": "Right now the draft talks around the prompt instead of answering it directly.",
    "topic": "Some sentences drift away from the topic you were asked to write about.",
    "idea_development": "You list ideas but don't yet show why they matter with an example.",
    "organization": "The ideas are there, but they need paragraphs and transitions to guide the reader.",
    "grammar": "The same grammar slip appears more than once, so fixing the pattern fixes several sentences at once.",
    "vocabulary": "A few words repeat often, which makes the writing feel narrower than your ideas.",
    "coherence": "The ideas are good but jump from one to the next without connecting words.",
}


def _build_mock_coach_guidance(
    *,
    weakest_key: str,
    weakest_label: str,
    learning_diagnosis: str,
    revision_priority: str,
    encouragement: str,
    grammar_notes: list[GrammarNote],
    vocabulary: VocabularyInsight,
) -> CoachGuidance:
    """One coherent coach plan built from the canonical weakest dimension.

    Never the 'first grammar error' unless grammar genuinely is the weakest
    dimension. Each field carries a distinct educational purpose.
    """
    before = ""
    after = ""
    if weakest_key == "grammar" and grammar_notes:
        note = grammar_notes[0]
        before = note.issue
        after = note.fix or note.example
        main_issue = note.rule or weakest_label
    elif weakest_key == "vocabulary" and vocabulary.repeated_words:
        word = vocabulary.repeated_words[0]
        before = f"You repeat '{word}' several times."
        alt = vocabulary.suggestions[0] if vocabulary.suggestions else "a stronger synonym"
        after = f"Replace some uses of '{word}' with {alt}."
        main_issue = weakest_label
    else:
        main_issue = weakest_label

    mission = revision_priority.split(":", 1)[-1].strip() if ":" in revision_priority else revision_priority

    return CoachGuidance(
        main_issue=main_issue,
        why_this_is_the_priority=_MOCK_WHY.get(weakest_key, learning_diagnosis),
        revision_mission=mission or "Revise the draft focusing on your main learning issue.",
        student_friendly_explanation=_MOCK_EXPLANATION.get(weakest_key, learning_diagnosis),
        before_example=before,
        after_example=after,
        encouragement=encouragement,
        available=True,
    )


def build_mock_educational_facts(draft_text: str, context: EducationalAnalysisContext) -> ClaudeEducationalFacts:
    """Deterministic teacher-like analysis from heuristics — never pass/fail."""
    text = draft_text.strip()
    words = re.findall(r"[a-zA-Z']+", text)
    content = _content_words(text)
    sentences = _sentences(text)
    connectors = sum(1 for c in _CONNECTORS if c in text.lower())
    grammar_notes = _detect_grammar(text)

    overlap = _topic_overlap(content, context)
    task_response, topic_understanding = _task_response_insight(overlap, context)

    grammar_score = max(0.15, 1.0 - 0.22 * len(grammar_notes))
    coherence = DimensionInsight(
        min(0.9, 0.4 + 0.12 * connectors + (0.2 if len(sentences) >= 3 else 0.0)),
        "Ideas connect with linking words and follow a logical order."
        if connectors >= 2
        else "Sentences are present but the links between ideas are weak.",
    )
    organization = _organization_insight(text, sentences, connectors)
    idea_development = _idea_development_insight(text, sentences)
    goal_alignment = _goal_alignment_insight(text, context)
    vocabulary = _vocabulary_insight(content, text, context)
    cefr_estimate, cefr_reason = _estimate_cefr(
        words=words, content=content, sentences=sentences, connectors=connectors, grammar_errors=len(grammar_notes)
    )

    # Learning diagnosis = biggest obstacle (lowest-scoring meaningful dimension).
    candidates = {
        "task_response": task_response.score,
        "topic": topic_understanding.score,
        "idea_development": idea_development.score,
        "organization": organization.score,
        "grammar": grammar_score,
        "vocabulary": vocabulary.score,
        "coherence": coherence.score,
    }
    weakest_key = min(candidates, key=candidates.get)
    weakest_label = _DIMENSION_LABELS.get(weakest_key, weakest_key.replace("_", " ").title())

    diagnosis_map = {
        "task_response": "The biggest obstacle is answering the actual question — the writing needs to respond to the prompt directly.",
        "topic": "The biggest obstacle is staying on topic — the draft moves away from what was asked.",
        "idea_development": "The biggest obstacle is developing ideas — points are listed but not explained or supported.",
        "organization": "The biggest obstacle is organization — the reader needs paragraphs and clearer transitions.",
        "grammar": "The biggest obstacle right now is grammar accuracy in core sentence patterns.",
        "vocabulary": "The biggest obstacle is vocabulary range — repeated and vague words limit the message.",
        "coherence": "The biggest obstacle is coherence — the ideas need to link together more clearly.",
    }
    learning_diagnosis = diagnosis_map[weakest_key]

    revision_map = {
        "task_response": "Next revision mission: rewrite so your first two sentences directly answer the prompt.",
        "topic": "Next revision mission: cut anything unrelated and keep every sentence on the assigned topic.",
        "idea_development": "Next revision mission: support every opinion with one real example.",
        "organization": "Next revision mission: split your writing into a clear beginning, middle, and end.",
        "grammar": f"Next revision mission: fix the '{grammar_notes[0].issue.lower()}' pattern throughout your draft."
        if grammar_notes
        else "Next revision mission: proofread each sentence for subject–verb agreement.",
        "vocabulary": "Next revision mission: replace your most repeated word with two different synonyms.",
        "coherence": "Next revision mission: add a linking word between each of your ideas.",
    }
    revision_priority = revision_map[weakest_key]

    strengths: list[str] = []
    if task_response.score >= 0.75:
        strengths.append("You answered the prompt directly.")
    if grammar_score >= 0.8:
        strengths.append("Your grammar is accurate and easy to read.")
    if connectors >= 2:
        strengths.append("You used linking words to connect your ideas.")
    if vocabulary.score >= 0.75:
        strengths.append("Your vocabulary choices are varied and appropriate.")
    if not strengths:
        strengths.append("You put real effort into responding to the task.")

    if task_response.score < 0.3:
        encouragement = (
            "You clearly have ideas to share — now aim them straight at the question and this draft will come alive."
        )
    elif grammar_notes and idea_development.score >= 0.6:
        encouragement = "Your ideas are genuinely good; tightening a few grammar patterns will let them shine."
    elif overlap >= 0.55 and grammar_score >= 0.8:
        encouragement = "This is a strong, on-topic draft — you write with control and clarity. Keep it up."
    else:
        encouragement = "You're making real progress. Focus on one improvement at a time and your writing will keep growing."

    progress_comparison = ""
    if context.revision_number > 1:
        if context.previous_cefr and cefr_estimate and cefr_estimate != context.previous_cefr:
            progress_comparison = (
                f"Compared with your previous draft, your language now reads closer to {cefr_estimate} "
                f"(was {context.previous_cefr}). "
            )
        if task_response.score > (context.previous_task_score or 0) + 0.1:
            progress_comparison += "You are answering the task more directly than before. "
        if not progress_comparison:
            progress_comparison = "This draft is on par with your previous one — push one dimension further to move ahead."
        progress_comparison = progress_comparison.strip()

    coach_guidance = _build_mock_coach_guidance(
        weakest_key=weakest_key,
        weakest_label=weakest_label,
        learning_diagnosis=learning_diagnosis,
        revision_priority=revision_priority,
        encouragement=encouragement,
        grammar_notes=grammar_notes,
        vocabulary=vocabulary,
    )

    return ClaudeEducationalFacts(
        task_response=task_response,
        topic_understanding=topic_understanding,
        coherence=coherence,
        organization=organization,
        idea_development=idea_development,
        goal_alignment=goal_alignment,
        vocabulary=vocabulary,
        grammar_notes=tuple(grammar_notes),
        cefr_estimate=cefr_estimate,
        cefr_reason=cefr_reason,
        progress_comparison=progress_comparison,
        learning_diagnosis=learning_diagnosis,
        revision_priority=revision_priority,
        encouragement=encouragement,
        strengths=tuple(strengths[:4]),
        coach_guidance=coach_guidance,
        major_learning_issue=weakest_label,
        available=True,
        analyzer_version=ANALYZER_FACTS_VERSION,
        model_name=_MODEL_NAME,
        source="mock",
    )
