"""Phase 9 — Curriculum knowledge base (text-based retrieval, no pgvector required).

A curated CEFR grammar reference with simple keyword retrieval. `ENABLE_PGVECTOR=false` by default, so
this grounds generation/feedback WITHOUT embeddings: `get_prompt_grounding()` returns a [REFERENCE]
block injected before a prompt so the AI teaches from a real reference instead of improvising.
Swap the scorer for pgvector similarity later without changing callers.
"""

from __future__ import annotations

import re

# Curated, CEFR-graded grammar reference. Each entry: stable id, topic, level, keywords, concise text.
KB: list[dict] = [
    {"id": "present_simple", "topic": "Present Simple", "cefr_level": "A1",
     "keywords": ["present", "simple", "habit", "routine", "always", "every day", "facts", "third person", "s"],
     "text": "Present Simple: habits, routines and facts. Add -s/-es for he/she/it (she works). Negatives/questions use do/does (She does not work; Does she work?)."},
    {"id": "present_continuous", "topic": "Present Continuous", "cefr_level": "A2",
     "keywords": ["present", "continuous", "progressive", "now", "ing", "am is are", "happening"],
     "text": "Present Continuous: actions happening now or around now. Form: am/is/are + verb-ing (I am working; They are eating). Not used with stative verbs (know, like)."},
    {"id": "past_simple", "topic": "Past Simple", "cefr_level": "A2",
     "keywords": ["past", "simple", "yesterday", "ago", "regular", "irregular", "ed", "finished"],
     "text": "Past Simple: finished actions at a definite past time. Regular: verb+ed (worked). Many irregulars (go->went, have->had). Negatives/questions use did (I did not go; Did you go?)."},
    {"id": "articles", "topic": "Articles", "cefr_level": "A2",
     "keywords": ["article", "a", "an", "the", "vowel", "definite", "indefinite", "a or an"],
     "text": "Articles: a/an = one, non-specific (a book; an apple — 'an' before a vowel SOUND). the = specific/known. No article for general plurals/uncountables (Cats are nice; Water is wet)."},
    {"id": "comparatives", "topic": "Comparatives and Superlatives", "cefr_level": "A2",
     "keywords": ["comparative", "superlative", "than", "er", "est", "more", "most", "bigger"],
     "text": "Comparatives/Superlatives: short adjectives +er/-est (big->bigger->the biggest); long adjectives more/most (more useful, the most useful). Irregulars: good->better->best, bad->worse->worst."},
    {"id": "present_perfect", "topic": "Present Perfect", "cefr_level": "B1",
     "keywords": ["present", "perfect", "have", "has", "ever", "never", "yet", "already", "just", "since", "for", "experience"],
     "text": "Present Perfect: have/has + past participle. Past action with present relevance, or experience/unfinished time (I have seen it; She has lived here for years). Use since (point) / for (duration). Not with a finished past time (NOT 'I have seen it yesterday')."},
    {"id": "past_continuous", "topic": "Past Continuous", "cefr_level": "B1",
     "keywords": ["past", "continuous", "was", "were", "ing", "while", "interrupted", "background"],
     "text": "Past Continuous: was/were + verb-ing for an action in progress in the past, often interrupted by a Past Simple action (I was reading when she called)."},
    {"id": "first_conditional", "topic": "First Conditional", "cefr_level": "B1",
     "keywords": ["conditional", "first", "if", "will", "real", "future", "possible"],
     "text": "First Conditional (real future): If + present simple, ... will + base verb (If it rains, we will stay home). For likely future situations."},
    {"id": "second_conditional", "topic": "Second Conditional", "cefr_level": "B2",
     "keywords": ["conditional", "second", "if", "would", "unreal", "hypothetical", "imaginary", "were"],
     "text": "Second Conditional (unreal/hypothetical present): If + past simple, ... would + base verb (If I had time, I would travel). Use 'were' for all persons (If I were you)."},
    {"id": "passive", "topic": "Passive Voice", "cefr_level": "B2",
     "keywords": ["passive", "voice", "be", "past participle", "by", "agent", "object"],
     "text": "Passive: be + past participle, when the action matters more than the doer (The bridge was built in 1990). Add 'by' for the agent only if needed."},
    {"id": "relative_clauses", "topic": "Relative Clauses", "cefr_level": "B2",
     "keywords": ["relative", "clause", "who", "which", "that", "whose", "where", "defining", "non-defining"],
     "text": "Relative clauses add information: who (people), which (things), that (people/things, defining), whose (possession), where (places). Non-defining clauses take commas (My brother, who lives in Berlin, ...)."},
    {"id": "reported_speech", "topic": "Reported Speech", "cefr_level": "B2",
     "keywords": ["reported", "indirect", "speech", "said", "told", "backshift", "tense"],
     "text": "Reported speech backshifts tenses one step (present->past): 'I am tired' -> She said she was tired. Pronouns and time words also shift (now->then, today->that day)."},
    {"id": "modals_deduction", "topic": "Modals of Deduction", "cefr_level": "B2",
     "keywords": ["modal", "deduction", "must", "might", "could", "can't", "certainty", "probability"],
     "text": "Modals of deduction (present): must (sure it's true), might/could (possible), can't (sure it's false). 'She must be tired; He can't be at home.'"},
    {"id": "third_conditional", "topic": "Third Conditional", "cefr_level": "C1",
     "keywords": ["conditional", "third", "if", "had", "would have", "past", "regret", "unreal past"],
     "text": "Third Conditional (unreal past): If + past perfect, ... would have + past participle (If I had known, I would have helped). For regrets/hypotheticals about the past."},
    {"id": "prepositions_time", "topic": "Prepositions of Time", "cefr_level": "A1",
     "keywords": ["preposition", "time", "in", "on", "at", "month", "day", "clock"],
     "text": "Prepositions of time: at + clock time (at 7), on + day/date (on Monday), in + month/year/part of day (in May, in the morning)."},
    {"id": "prepositions_place", "topic": "Prepositions of Place", "cefr_level": "A1",
     "keywords": ["preposition", "place", "in", "on", "at", "under", "next to", "between"],
     "text": "Prepositions of place: in (enclosed: in the room), on (surface: on the table), at (point: at the door); also under, next to, between, behind, in front of."},
    {"id": "future_going_to", "topic": "Future: going to", "cefr_level": "A2",
     "keywords": ["future", "going to", "plan", "intention", "prediction", "evidence"],
     "text": "going to: plans/intentions decided before now (I'm going to study tonight) and predictions from evidence (Look at those clouds - it's going to rain). Form: am/is/are going to + base verb."},
    {"id": "future_will", "topic": "Future: will", "cefr_level": "A2",
     "keywords": ["future", "will", "decision", "promise", "offer", "prediction"],
     "text": "will + base verb: instant decisions (I'll get it), promises/offers (I'll help you) and general predictions (It will be cold). Negative: won't."},
    {"id": "quantifiers", "topic": "Quantifiers", "cefr_level": "A2",
     "keywords": ["quantifier", "some", "any", "much", "many", "a lot", "few", "little", "countable", "uncountable"],
     "text": "Quantifiers: some (+ affirmative), any (questions/negatives); many/few + countable, much/little + uncountable; a lot of for both (a lot of books / a lot of water)."},
    {"id": "question_formation", "topic": "Question Formation", "cefr_level": "A2",
     "keywords": ["question", "wh", "do", "does", "did", "auxiliary", "word order", "inversion"],
     "text": "Questions: auxiliary + subject + verb. Yes/No: Do you like it? Did she go? Wh-: What do you want? Where did they go? Subject questions need no auxiliary (Who called?)."},
    {"id": "used_to", "topic": "used to", "cefr_level": "B1",
     "keywords": ["used to", "past habit", "past state", "no longer"],
     "text": "used to + base verb: past habits/states that are no longer true (I used to play tennis; She used to live here). Questions/negatives: did/didn't use to."},
    {"id": "gerunds_infinitives", "topic": "Gerunds and Infinitives", "cefr_level": "B1",
     "keywords": ["gerund", "infinitive", "ing", "to", "verb patterns", "enjoy", "want", "decide"],
     "text": "Verb patterns: some verbs take -ing (enjoy/finish/avoid + doing), others take to + base (want/decide/hope to do). After prepositions, always use -ing (good at swimming)."},
    {"id": "phrasal_verbs", "topic": "Phrasal Verbs", "cefr_level": "B1",
     "keywords": ["phrasal", "verb", "particle", "separable", "look up", "give up", "put off"],
     "text": "Phrasal verbs = verb + particle with a new meaning (give up = quit, put off = postpone). Many separable verbs take an object between parts (turn it off); others are inseparable (look after them)."},
    {"id": "too_enough", "topic": "too / enough", "cefr_level": "B1",
     "keywords": ["too", "enough", "degree", "adjective", "not enough", "too much"],
     "text": "too + adjective = more than wanted (too hot); enough after adjective/before noun = the right amount (warm enough; enough time). too much/many + noun."},
    {"id": "wish", "topic": "wish / if only", "cefr_level": "B2",
     "keywords": ["wish", "if only", "regret", "past", "subjunctive", "would"],
     "text": "wish + past simple = regret about the present (I wish I had more time); wish + past perfect = regret about the past (I wish I had studied); wish + would = annoyance about others' behaviour."},
    {"id": "so_such", "topic": "so / such", "cefr_level": "B2",
     "keywords": ["so", "such", "emphasis", "result", "that"],
     "text": "so + adjective/adverb (so tired), such + (a/an) + (adjective) noun (such a long day). Both add emphasis, often with a result clause: so tired that I slept."},
    {"id": "requests_politeness", "topic": "Polite Requests", "cefr_level": "A2",
     "keywords": ["request", "polite", "could", "would", "can", "may", "please", "pragmatics"],
     "text": "Polite requests: Could/Can you ...?, Would you mind + -ing?, May I ...? Softeners: please, possibly. Direct imperatives sound rude in requests (prefer 'Could you open the window?')."},
]

_LEVEL_ORDER = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
_GROUNDING_MAX = 3


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z']+", (text or "").lower()) if len(t) > 1}


def _score(entry: dict, query_tokens: set[str], cefr_level: str | None) -> float:
    """Keyword/topic overlap, with a soft preference for entries at or below the learner's level."""
    kw = set()
    for k in entry.get("keywords", []):
        kw |= _tokens(k)
    kw |= _tokens(entry.get("topic", ""))
    overlap = len(query_tokens & kw)
    if overlap == 0:
        return 0.0
    score = float(overlap)
    if cefr_level and cefr_level in _LEVEL_ORDER:
        diff = _LEVEL_ORDER.get(entry.get("cefr_level", "A1"), 1) - _LEVEL_ORDER[cefr_level]
        if diff <= 0:
            score += 0.5  # at or below the learner's level — appropriate
        else:
            score -= 0.5 * diff  # above level — gently de-prioritise
    return score


def search(query: str, *, cefr_level: str | None = None, top_k: int = 5) -> list[dict]:
    """Rank KB entries by keyword overlap (+ level fit). Returns the top_k matching entries."""
    qt = _tokens(query)
    if not qt:
        return []
    scored = [(e, _score(e, qt, cefr_level)) for e in KB]
    scored = [(e, s) for e, s in scored if s > 0]
    scored.sort(key=lambda es: es[1], reverse=True)
    return [e for e, _ in scored[:top_k]]


def get_grammar_reference(topic: str, *, level: str | None = None) -> str:
    """Best single reference text for a topic ("" if no match)."""
    hits = search(topic, cefr_level=level, top_k=1)
    return hits[0]["text"] if hits else ""


def get_prompt_grounding(lesson_topic: str, *, level: str | None = None) -> str:
    """A [REFERENCE] block (top matches) to inject BEFORE a prompt. "" when nothing matches."""
    hits = search(lesson_topic, cefr_level=level, top_k=_GROUNDING_MAX)
    if not hits:
        return ""
    body = "\n".join(f"- {h['topic']} ({h['cefr_level']}): {h['text']}" for h in hits)
    return (
        "[REFERENCE — teach accurately from these CEFR grammar facts; do not contradict them]\n"
        + body
        + "\n[/REFERENCE]"
    )
