"""Interest / profession / culture overlays — never change curriculum category."""

from __future__ import annotations

from typing import Any

# Soft experience packs keyed by hobby/interest. Educational quality first.
INTEREST_PACKS: dict[str, dict[str, Any]] = {
    "football": {
        "labels": ("football", "soccer", "sports"),
        "setting": "football club offices",
        "title": "A Deal Between Football Clubs",
        "world": (
            "Two football clubs are negotiating a contract transfer deadline. "
            "Managers, a captain, and the club board must speak carefully before "
            "the agreement collapses."
        ),
        "roles": ("club manager", "team captain", "club board member"),
        "names": ("Kareem", "Yara", "Hassan", "Nina", "Omar"),
        "emotional": "competitive urgency under public pressure",
        "discussion": "Would this decision also work inside a football team?",
    },
    "medicine": {
        "labels": ("medicine", "medical", "doctor", "hospital", "clinic", "healthcare"),
        "setting": "hospital planning room",
        "title": "Hospital Resources Under Pressure",
        "world": (
            "A hospital team must negotiate limited resources and patient priorities. "
            "A resident, a nurse lead, and an administrator decide what to say next."
        ),
        "roles": ("resident doctor", "nurse lead", "hospital administrator"),
        "names": ("Rami", "Dr. Ellis", "Noor", "Samira", "Jonas"),
        "emotional": "careful empathy under time pressure",
        "discussion": "How would this decision feel if a patient's family were waiting?",
    },
    "business": {
        "labels": ("business", "entrepreneur", "company", "startup", "supplier", "owner"),
        "setting": "supplier negotiation room",
        "title": "Supplier Contract Decision",
        "world": (
            "A business owner negotiates a supplier contract while cash flow and "
            "delivery deadlines create conflicting pressure on the agreement."
        ),
        "roles": ("business owner", "supplier lead", "operations manager"),
        "names": ("Maya", "Jordan", "Hana", "Diego", "Lee"),
        "emotional": "pragmatic tension and accountability",
        "discussion": "Would you accept the same trade-off in your own business?",
    },
    "music": {
        "labels": ("music", "band", "concert", "guitar", "piano"),
        "setting": "studio production meeting",
        "title": "Studio Schedule Conflict",
        "world": (
            "A music studio faces a schedule conflict before a live show. "
            "The producer, lead artist, and venue contact must agree who speaks next."
        ),
        "roles": ("producer", "lead artist", "venue contact"),
        "names": ("Lina", "Omar", "Sara", "Kim", "Theo"),
        "emotional": "creative pride mixed with practical stress",
        "discussion": "How would this choice play out in a music band?",
    },
    "programming": {
        "labels": ("programming", "coding", "software", "developer", "tech", "technology"),
        "setting": "product engineering standup",
        "title": "Release Decision on a Tight Deadline",
        "world": (
            "A software team must negotiate a release decision with incomplete features. "
            "An engineer, a product lead, and a client contact feel the trade-off."
        ),
        "roles": ("engineer", "product lead", "client contact"),
        "names": ("Sam", "Aya", "Chris", "Noor", "Ibrahim"),
        "emotional": "quiet tension about quality vs speed",
        "discussion": "Would this decision work inside a programming team?",
    },
    "travel": {
        "labels": ("travel", "tourism", "trip", "flight", "hotel"),
        "setting": "hotel front desk",
        "title": "Hotel Booking Under Pressure",
        "world": (
            "At a busy hotel desk, a traveler and staff negotiate a booking problem "
            "while another guest and a supervisor wait for a clear decision."
        ),
        "roles": ("traveler", "desk agent", "hotel supervisor"),
        "names": ("Anna", "Diego", "Kim", "Noor", "Lee"),
        "emotional": "polite frustration under time pressure",
        "discussion": "How would you handle this on a real trip?",
    },
    "photography": {
        "labels": ("photography", "camera", "photo"),
        "setting": "gallery opening prep room",
        "title": "Exhibition Deadline Tension",
        "world": (
            "A photographer, a curator, and a sponsor negotiate which exhibit photos "
            "can still change before an opening night."
        ),
        "roles": ("photographer", "curator", "sponsor"),
        "names": ("Mira", "Jonas", "Sara", "Omar", "Hana"),
        "emotional": "artistic pride vs practical constraints",
        "discussion": "Would this choice feel fair to a photography team?",
    },
    "cooking": {
        "labels": ("cooking", "food", "chef", "kitchen", "restaurant"),
        "setting": "restaurant kitchen office",
        "title": "Kitchen Service Decision",
        "world": (
            "A kitchen team must decide how to handle a supplier delay before dinner "
            "service. A chef, a waiter lead, and an owner all need clarity."
        ),
        "roles": ("head chef", "waiter lead", "restaurant owner"),
        "names": ("Yara", "Hassan", "Maya", "Lee", "Omar"),
        "emotional": "fast service stress with pride in quality",
        "discussion": "How would this decision work during a busy restaurant service?",
    },
    "education": {
        "labels": ("education", "teaching", "school", "university", "student", "teacher"),
        "setting": "university advising office",
        "title": "Course Deadline Dilemma",
        "world": (
            "A university student, an advisor, and a department head negotiate an "
            "extension request that affects fairness for the whole class."
        ),
        "roles": ("student", "advisor", "department head"),
        "names": ("Sara", "Mr. Hayes", "Lina", "Omar", "Noor"),
        "emotional": "responsibility mixed with anxiety",
        "discussion": "Would this decision feel fair on a university campus?",
    },
}

PROFESSION_PACKS: dict[str, dict[str, Any]] = {
    "medical_student": INTEREST_PACKS["medicine"],
    "doctor": INTEREST_PACKS["medicine"],
    "nurse": INTEREST_PACKS["medicine"],
    "business_owner": INTEREST_PACKS["business"],
    "entrepreneur": INTEREST_PACKS["business"],
    "developer": INTEREST_PACKS["programming"],
    "engineer": INTEREST_PACKS["programming"],
    "teacher": INTEREST_PACKS["education"],
    "student": INTEREST_PACKS["education"],
    "traveler": INTEREST_PACKS["travel"],
}

# Alternate settings used when memory blocks a previously used place.
SETTING_ALTERNATES: dict[str, tuple[str, ...]] = {
    "airport": ("hotel front desk", "train station help desk", "conference registration desk"),
    "airport arrivals": ("hotel check-in", "travel insurance counter", "taxi stand conflict"),
    "workplace": ("client meeting room", "remote video call", "project standup corner"),
    "family": ("shared kitchen", "living room planning talk", "extended family visit"),
    "hospital": ("clinic consultation room", "pharmacy counter", "ward planning office"),
    "medical": ("clinic consultation room", "pharmacy counter", "ward planning office"),
}

NAME_CULTURE_POOLS: dict[str, tuple[str, ...]] = {
    "arabic_levant": ("Lina", "Omar", "Noor", "Rami", "Hana", "Yara", "Kareem", "Sara"),
    "international": ("Sam", "Lee", "Maya", "Jordan", "Anna", "Diego", "Kim", "Chris"),
    "default": ("Sam", "Lee", "Maya", "Jordan", "Noor", "Omar", "Hana", "Sara"),
}


def _blob(*parts: str) -> str:
    return " ".join(p for p in parts if p).lower()


def age_band(age: int | None) -> str:
    if age is None:
        return "adult"
    if age < 18:
        return "teen"
    if age < 25:
        return "young_adult"
    if age < 40:
        return "adult"
    if age < 60:
        return "mid_career"
    return "senior"


def match_interest_pack(
    *,
    interests: tuple[str, ...] | list[str],
    hobbies: tuple[str, ...] | list[str],
    favorite_topics: tuple[str, ...] | list[str],
    avoided_topics: tuple[str, ...] | list[str] = (),
    used_theme_keys: tuple[str, ...] | list[str] = (),
) -> tuple[str, dict[str, Any] | None]:
    """Pick an interest pack when educationally appropriate; never force hobbies."""
    blob = _blob(*(interests or ()), *(hobbies or ()), *(favorite_topics or ()))
    avoided = {_blob(a) for a in (avoided_topics or ())}
    used = set(used_theme_keys or ())
    ranked: list[tuple[str, dict[str, Any]]] = []
    for key, pack in INTEREST_PACKS.items():
        if key in used:
            continue
        labels = pack.get("labels") or ()
        if any(_blob(lab) in avoided for lab in labels):
            continue
        if any(lab in blob for lab in labels):
            ranked.append((key, pack))
    if not ranked:
        return "", None
    return ranked[0][0], ranked[0][1]


def match_profession_pack(
    *,
    occupation: str,
    future_goal: str,
    used_theme_keys: tuple[str, ...] | list[str] = (),
) -> tuple[str, dict[str, Any] | None]:
    blob = _blob(occupation, future_goal)
    used = set(used_theme_keys or ())
    for key, pack in PROFESSION_PACKS.items():
        if key in used:
            continue
        token = key.replace("_", " ")
        if token in blob or any(part in blob for part in key.split("_") if len(part) > 3):
            return key, pack
    # soft goal keywords
    soft = (
        ("medical", "medicine"),
        ("business", "business"),
        ("coding", "programming"),
        ("program", "programming"),
        ("teach", "education"),
        ("university", "education"),
        ("travel", "travel"),
        ("football", "football"),
        ("sport", "football"),
    )
    for needle, pack_key in soft:
        if needle in blob and pack_key not in used:
            return pack_key, INTEREST_PACKS[pack_key]
    return "", None


def culture_name_pool(culture_hint: str, locale: str = "en") -> tuple[str, ...]:
    hint = (culture_hint or "").lower()
    if any(k in hint for k in ("arab", "syria", "levant", "gulf", "egypt")):
        return NAME_CULTURE_POOLS["arabic_levant"]
    if locale.lower().startswith("ar"):
        return NAME_CULTURE_POOLS["arabic_levant"]
    if hint:
        return NAME_CULTURE_POOLS["international"]
    return NAME_CULTURE_POOLS["default"]


def alternate_setting(current: str, used_settings: tuple[str, ...] | list[str]) -> str:
    """Avoid repeating identical settings from case memory."""
    cur = (current or "").strip().lower()
    used_l = {s.lower() for s in (used_settings or ())}
    if cur and cur not in used_l and not any(cur in u or u in cur for u in used_l):
        return current
    for key, alts in SETTING_ALTERNATES.items():
        if key in cur or cur in key:
            for alt in alts:
                if alt.lower() not in used_l:
                    return alt
    # Generic diversifiers when memory already saw the current setting
    generics = (
        "community center meeting room",
        "quiet cafe corner",
        "shared office hallway",
        "online video call",
        "neighborhood library desk",
    )
    for g in generics:
        if g not in used_l:
            return g
    return current or "everyday place"


def learning_style_dialogue(learning_style: str, explanation_style: str) -> tuple[str, str]:
    ls = (learning_style or "").lower()
    es = (explanation_style or "").lower()
    dialogue = "natural spoken turns with clear decisions"
    framing = "practical and human"
    if "visual" in ls:
        dialogue = "concrete, scene-based spoken details the listener can picture"
        framing = "vivid but still educational"
    elif "practical" in ls or "hands" in ls:
        dialogue = "action-first speech with concrete next steps"
        framing = "pragmatic and decision-focused"
    elif "theoretical" in ls:
        dialogue = "reasoned spoken explanations with cause and effect"
        framing = "thoughtful and structured"
    if "simple" in es or "short" in es:
        dialogue = f"{dialogue}; keep sentences clear and short"
    elif "detailed" in es or "deep" in es:
        dialogue = f"{dialogue}; allow careful nuance without leaving the case"
    return dialogue, framing
