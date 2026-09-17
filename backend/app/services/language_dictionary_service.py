"""Global English dictionary index — a huge, level-agnostic reference for every learner.

Backed by WordNet (~147k words) via nltk: free, offline, no AI, no quota. Provides word lookup
(definition + part of speech + examples + synonyms) and prefix suggestions for browsing/search.
The corpus lives in backend/nltk_data (downloaded once). If it's missing, the service degrades to
empty results rather than erroring.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# WordNet corpus shipped under backend/nltk_data
_NLTK_DATA = Path(__file__).resolve().parents[2] / "nltk_data"

_POS = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}

_wn = None
_available: bool | None = None


def _wordnet():
    """Lazily load WordNet (configuring the local data path). Returns the corpus or None."""
    global _wn, _available
    if _available is False:
        return None
    if _wn is not None:
        return _wn
    try:
        import nltk

        if str(_NLTK_DATA) not in nltk.data.path:
            nltk.data.path.insert(0, str(_NLTK_DATA))
        from nltk.corpus import wordnet as wn

        wn.ensure_loaded()
        _wn = wn
        _available = True
    except Exception as exc:  # pragma: no cover - corpus missing / nltk absent
        logger.warning("WordNet unavailable (%s); dictionary will return empty results", exc)
        _available = False
        return None
    return _wn


def _norm(word: str) -> str:
    return " ".join((word or "").strip().lower().replace("_", " ").split())


# Curated learner-friendly definitions for common FUNCTION/grammar words that WordNet either misses
# (because, although, their) or defines with the wrong/obscure sense (its -> "IT engineering",
# despite -> "contempt", while -> "a period of time"). Checked BEFORE WordNet so taps on these
# everyday words always show a sensible meaning.
FUNCTION_WORDS: dict[str, tuple[str, str]] = {
    # articles / determiners
    "the": ("determiner", "Used before a specific noun both speaker and listener know."),
    "a": ("determiner", "One, non-specific (a book = some book)."),
    "an": ("determiner", "One, non-specific; used before a vowel sound (an apple)."),
    "this": ("determiner", "The one here / close to the speaker."),
    "that": ("determiner", "The one there / further away, or already mentioned."),
    "these": ("determiner", "More than one thing here / close."),
    "those": ("determiner", "More than one thing there / further away."),
    "some": ("determiner", "An unspecified amount or number."),
    "any": ("determiner", "One or some, in questions and negatives."),
    "many": ("determiner", "A large number of (countable things)."),
    "much": ("determiner", "A large amount of (uncountable things)."),
    "few": ("determiner", "A small number of (countable things)."),
    "little": ("determiner", "A small amount of (uncountable things)."),
    "every": ("determiner", "All the members of a group, one by one."),
    "each": ("determiner", "Every one of two or more, considered separately."),
    "all": ("determiner", "The whole number or amount."),
    "both": ("determiner", "The two together."),
    "no": ("determiner", "Not any."),
    "none": ("pronoun", "Not any; not one."),
    "enough": ("determiner", "As much or as many as needed."),
    # possessives / pronouns
    "my": ("possessive", "Belonging to me."),
    "your": ("possessive", "Belonging to you."),
    "his": ("possessive", "Belonging to him."),
    "her": ("possessive", "Belonging to her."),
    "its": ("possessive", "Belonging to it."),
    "our": ("possessive", "Belonging to us."),
    "their": ("possessive", "Belonging to them."),
    "mine": ("pronoun", "The thing(s) belonging to me."),
    "yours": ("pronoun", "The thing(s) belonging to you."),
    "theirs": ("pronoun", "The thing(s) belonging to them."),
    "it": ("pronoun", "The thing or animal already mentioned."),
    "they": ("pronoun", "The people or things already mentioned."),
    "them": ("pronoun", "The people or things already mentioned (object)."),
    "we": ("pronoun", "The speaker and at least one other person."),
    "us": ("pronoun", "The speaker and others (object)."),
    # prepositions
    "of": ("preposition", "Showing belonging or connection (the leg of the table)."),
    "to": ("preposition", "Showing direction or a goal (go to school)."),
    "for": ("preposition", "Showing purpose or who benefits (a gift for you)."),
    "with": ("preposition", "Together; using something."),
    "without": ("preposition", "Not having something."),
    "from": ("preposition", "Showing the starting point or origin."),
    "by": ("preposition", "Near; or showing who did an action (made by her)."),
    "about": ("preposition", "On the subject of; concerning."),
    "into": ("preposition", "Moving to the inside of something."),
    "over": ("preposition", "Above, or across the top of."),
    "under": ("preposition", "Below something."),
    "between": ("preposition", "In the space separating two things."),
    "among": ("preposition", "In the middle of a group (three or more)."),
    "through": ("preposition", "From one side or end to the other."),
    "during": ("preposition", "Throughout a period of time."),
    "before": ("preposition", "Earlier than."),
    "after": ("preposition", "Later than."),
    "against": ("preposition", "Touching; or opposing."),
    "despite": ("preposition", "Even though something is true; in spite of."),
    "within": ("preposition", "Inside; not more than."),
    # conjunctions / connectors
    "and": ("conjunction", "Joins words or ideas that go together."),
    "or": ("conjunction", "Shows a choice between options."),
    "but": ("conjunction", "Introduces a contrast or exception."),
    "because": ("conjunction", "For the reason that; gives a cause."),
    "so": ("conjunction", "For that reason; with the result that."),
    "although": ("conjunction", "Even though; despite the fact that."),
    "though": ("conjunction", "Even though; however."),
    "while": ("conjunction", "During the time that; or whereas (contrast)."),
    "since": ("conjunction", "From a past time until now; or because."),
    "unless": ("conjunction", "Except if; if not."),
    "until": ("preposition", "Up to a certain time."),
    "if": ("conjunction", "On the condition that."),
    "when": ("conjunction", "At the time that."),
    "whether": ("conjunction", "Introduces a choice between possibilities."),
    "however": ("adverb", "Used to add a contrasting idea; but."),
    "therefore": ("adverb", "For that reason; as a result."),
    "moreover": ("adverb", "In addition; also."),
    "otherwise": ("adverb", "If not; in other ways."),
    "instead": ("adverb", "In place of something else."),
    "meanwhile": ("adverb", "At the same time."),
    "nevertheless": ("adverb", "In spite of that; even so."),
    "besides": ("adverb", "In addition; also."),
    # common adverbs
    "very": ("adverb", "To a high degree."),
    "too": ("adverb", "More than wanted; or also."),
    "also": ("adverb", "In addition; as well."),
    "just": ("adverb", "Exactly; or a very short time ago."),
    "only": ("adverb", "And no more; nothing else."),
    "even": ("adverb", "Used to stress something surprising."),
    "still": ("adverb", "Continuing up to now."),
    "already": ("adverb", "Before now or before an expected time."),
    "yet": ("adverb", "Up to now (in questions and negatives)."),
    "always": ("adverb", "Every time; all the time."),
    "never": ("adverb", "At no time; not ever."),
    "often": ("adverb", "Many times; frequently."),
    "usually": ("adverb", "Most of the time."),
    "perhaps": ("adverb", "Maybe; possibly."),
}


@lru_cache(maxsize=1)
def _all_words() -> list[str]:
    wn = _wordnet()
    if not wn:
        return []
    words = {name.replace("_", " ") for name in wn.all_lemma_names()}
    return sorted(words)


def lookup(word: str, *, max_entries: int = 6) -> list[dict]:
    """All sense entries for a word: [{part_of_speech, definition, examples, synonyms}]."""
    # Curated function/grammar words first — covers words WordNet misses or mis-senses.
    fw = FUNCTION_WORDS.get(_norm(word))
    if fw is not None:
        return [{"part_of_speech": fw[0], "definition": fw[1], "examples": [], "synonyms": []}]

    wn = _wordnet()
    if not wn:
        return []
    lemma = _norm(word).replace(" ", "_")
    synsets = wn.synsets(lemma)
    if not synsets:
        # Inflected form WordNet didn't resolve directly (plural/tense/comparative) -> reduce to its
        # base via morphology and look that up, so every form maps to a definition.
        bases: list[str] = []
        for pos in ("n", "v", "a", "r"):
            base = wn.morphy(lemma, pos)
            if base and base != lemma and base not in bases:
                bases.append(base)
        for base in bases:
            synsets = wn.synsets(base)
            if synsets:
                break
    entries: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for syn in synsets:
        pos = _POS.get(syn.pos(), syn.pos())
        definition = syn.definition() or ""
        key = (pos, definition)
        if key in seen:
            continue
        seen.add(key)
        synonyms = [l.name().replace("_", " ") for l in syn.lemmas() if _norm(l.name()) != _norm(word)]
        entries.append({
            "part_of_speech": pos,
            "definition": definition,
            "examples": list(syn.examples() or [])[:3],
            "synonyms": list(dict.fromkeys(synonyms))[:6],
        })
        if len(entries) >= max_entries:
            break
    return entries


def suggest(prefix: str, *, limit: int = 25) -> list[str]:
    """Words starting with the given prefix (for search/browse)."""
    p = _norm(prefix)
    if not p:
        return []
    out = [w for w in _all_words() if w.startswith(p)]
    return out[:limit]


def search(query: str, *, limit: int = 25) -> dict:
    """Combined: exact-word entries (if any) + prefix suggestions."""
    q = _norm(query)
    return {
        "query": q,
        "entries": lookup(q) if q else [],
        "suggestions": suggest(q, limit=limit),
        "total_words": len(_all_words()),
    }
