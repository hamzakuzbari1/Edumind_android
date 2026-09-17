"""Backend vocabulary curriculum catalogs — real lexical items by theme and CEFR."""

from __future__ import annotations

from app.services.language_speaking_curriculum_engine.types import VocabularyTarget

# Theme keyed packs: list ordered by priority. CEFR filter applied at select time.


def _v(
    vid: str,
    *,
    lemma: str,
    surface: str,
    meaning: str,
    purpose: str,
    cefr: str,
    reuse: str,
    example: str,
    freq: int,
) -> VocabularyTarget:
    return VocabularyTarget(
        vocabulary_id=vid,
        lemma=lemma,
        surface=surface,
        meaning=meaning,
        communicative_purpose=purpose,
        cefr_suitability=cefr,
        expected_reuse=reuse,
        example_usage=example,
        required_lesson_frequency=freq,
    )


TRAVEL_GREETINGS_A1: tuple[VocabularyTarget, ...] = (
    _v(
        "lex_welcome",
        lemma="welcome",
        surface="Welcome!",
        meaning="A friendly word said when someone arrives.",
        purpose="Make a traveler feel accepted on arrival.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="Welcome! Nice to see you.",
        freq=2,
    ),
    _v(
        "lex_nice_to_meet_you",
        lemma="nice to meet you",
        surface="Nice to meet you",
        meaning="A polite phrase when you meet someone for the first time.",
        purpose="Start a first meeting politely.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="Nice to meet you. I'm Anna.",
        freq=2,
    ),
    _v(
        "lex_how_was_your_trip",
        lemma="how was your trip",
        surface="How was your trip?",
        meaning="A question about someone's journey.",
        purpose="Show interest after travel.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="Hi! How was your trip?",
        freq=2,
    ),
    _v(
        "lex_hello",
        lemma="hello",
        surface="Hello",
        meaning="A basic greeting.",
        purpose="Open any spoken exchange.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="Hello! Welcome!",
        freq=2,
    ),
    _v(
        "lex_thank_you",
        lemma="thank you",
        surface="Thank you",
        meaning="A polite response to help or kindness.",
        purpose="Respond politely after a greeting or help.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="Thank you. It's good to be here.",
        freq=2,
    ),
)

TRAVEL_GREETINGS_A2: tuple[VocabularyTarget, ...] = (
    _v(
        "lex_welcome_to",
        lemma="welcome to",
        surface="Welcome to",
        meaning="A greeting that names the place someone arrives in.",
        purpose="Welcome someone to a city or place.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="Welcome to Madrid!",
        freq=2,
    ),
    _v(
        "lex_how_was_your_flight",
        lemma="how was your flight",
        surface="How was your flight?",
        meaning="A question about air travel.",
        purpose="Care for a traveler after a flight.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="Hi! How was your flight?",
        freq=2,
    ),
    _v(
        "lex_nice_to_see_you",
        lemma="nice to see you",
        surface="Nice to see you",
        meaning="A warm greeting for someone you know or are happy to meet.",
        purpose="Show warmth when meeting again or arriving.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="Hello! Nice to see you!",
        freq=2,
    ),
    _v(
        "lex_good_to_be_here",
        lemma="good to be here",
        surface="good to be here",
        meaning="A reply showing relief or happiness after arriving.",
        purpose="Respond positively after arrival.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="Thanks — it's good to be here finally.",
        freq=2,
    ),
    _v(
        "lex_long_but_good",
        lemma="long but good",
        surface="long, but good",
        meaning="A simple way to describe a journey.",
        purpose="Give a short travel update.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="The flight was long, but good.",
        freq=2,
    ),
    _v(
        "lex_lets_grab_your_bags",
        lemma="grab your bags",
        surface="Let's grab your bags",
        meaning="A suggestion to collect luggage together.",
        purpose="Move from greeting into practical help.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="Great! Let's grab your bags.",
        freq=2,
    ),
)

SPEAKING_RATE_B2: tuple[VocabularyTarget, ...] = (
    _v(
        "lex_slow_down",
        lemma="slow down",
        surface="slow down",
        meaning="Speak or move less quickly.",
        purpose="Ask someone to reduce speaking speed.",
        cefr="B2",
        reuse="story+teaching+discussion+practice",
        example="Could you slow down a little?",
        freq=3,
    ),
    _v(
        "lex_speaking_pace",
        lemma="speaking pace",
        surface="speaking pace",
        meaning="How fast or slow someone talks.",
        purpose="Name the skill students control in speech.",
        cefr="B2",
        reuse="story+teaching+discussion+practice",
        example="A steady speaking pace helps listeners.",
        freq=3,
    ),
    _v(
        "lex_short_pauses",
        lemma="short pause",
        surface="short pauses",
        meaning="Brief stops between ideas while speaking.",
        purpose="Give listeners time to follow.",
        cefr="B2",
        reuse="story+teaching+discussion+practice",
        example="Use short pauses between key points.",
        freq=3,
    ),
    _v(
        "lex_rush_through",
        lemma="rush through",
        surface="rush through",
        meaning="Say something too quickly without care.",
        purpose="Describe the fluency problem to fix.",
        cefr="B2",
        reuse="story+teaching+discussion+practice",
        example="I rush through my sentences when nervous.",
        freq=2,
    ),
    _v(
        "lex_follow_you",
        lemma="follow",
        surface="follow you",
        meaning="Understand someone's spoken message as it progresses.",
        purpose="Link clear pace to listener success.",
        cefr="B2",
        reuse="story+teaching+discussion+practice",
        example="A steady pace helps listeners follow you.",
        freq=2,
    ),
    _v(
        "lex_presentation",
        lemma="presentation",
        surface="presentation",
        meaning="A talk given to an audience.",
        purpose="Transfer rate control to a real task.",
        cefr="B2",
        reuse="story+teaching+discussion+practice",
        example="I'll manage my pace in the next presentation.",
        freq=2,
    ),
    _v(
        "lex_clearly",
        lemma="clearly",
        surface="clearly",
        meaning="In a way that is easy to understand.",
        purpose="Describe the goal of controlled speech.",
        cefr="B2",
        reuse="story+teaching+discussion+practice",
        example="Speak clearly with short pauses.",
        freq=2,
    ),
)

EVERYDAY_A1: tuple[VocabularyTarget, ...] = (
    _v(
        "lex_please",
        lemma="please",
        surface="please",
        meaning="A polite word used when asking.",
        purpose="Make requests polite.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="Can I have water, please?",
        freq=2,
    ),
    _v(
        "lex_excuse_me",
        lemma="excuse me",
        surface="Excuse me",
        meaning="A polite way to get attention.",
        purpose="Start a short spoken request.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="Excuse me — where is the station?",
        freq=2,
    ),
    _v(
        "lex_i_need",
        lemma="i need",
        surface="I need",
        meaning="A simple way to say what you want.",
        purpose="Express a basic need.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="I need a ticket, please.",
        freq=2,
    ),
    _v(
        "lex_where_is",
        lemma="where is",
        surface="Where is",
        meaning="A question starter for location.",
        purpose="Ask for places.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="Where is the bus stop?",
        freq=2,
    ),
    _v(
        "lex_ok",
        lemma="ok",
        surface="OK",
        meaning="A short agreement or acceptance.",
        purpose="Confirm understanding in talk.",
        cefr="A1",
        reuse="story+teaching+discussion+practice",
        example="OK, thank you!",
        freq=2,
    ),
)

EVERYDAY_A2: tuple[VocabularyTarget, ...] = (
    _v(
        "lex_could_you",
        lemma="could you",
        surface="Could you",
        meaning="A polite request starter.",
        purpose="Ask for help politely.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="Could you help me, please?",
        freq=2,
    ),
    _v(
        "lex_of_course",
        lemma="of course",
        surface="Of course",
        meaning="A friendly yes.",
        purpose="Agree helpfully.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="Of course — this way.",
        freq=2,
    ),
    _v(
        "lex_im_looking_for",
        lemma="look for",
        surface="I'm looking for",
        meaning="Say what you want to find.",
        purpose="State a search goal.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="I'm looking for platform 3.",
        freq=2,
    ),
    _v(
        "lex_one_moment",
        lemma="one moment",
        surface="One moment",
        meaning="Ask someone to wait briefly.",
        purpose="Manage turn-taking politely.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="One moment, please.",
        freq=2,
    ),
    _v(
        "lex_that_helps",
        lemma="that helps",
        surface="That helps",
        meaning="Show that information was useful.",
        purpose="Close a help exchange warmly.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="Thanks — that helps a lot.",
        freq=2,
    ),
    _v(
        "lex_over_there",
        lemma="over there",
        surface="over there",
        meaning="Point to a nearby place.",
        purpose="Give simple directions.",
        cefr="A2",
        reuse="story+teaching+discussion+practice",
        example="The exit is over there.",
        freq=2,
    ),
)


def _cefr_rank(level: str) -> int:
    order = ("A1", "A2", "B1", "B2", "C1", "C2")
    key = (level or "A2").upper()[:2]
    try:
        return order.index(key)
    except ValueError:
        return 1


def _filter_by_cefr(items: tuple[VocabularyTarget, ...], cefr: str) -> list[VocabularyTarget]:
    rank = _cefr_rank(cefr)
    out = [i for i in items if _cefr_rank(i.cefr_suitability) <= rank]
    return out or list(items)


def theme_for_skill_ids(skill_ids: list[str], learning_focus: str) -> str:
    blob = " ".join([*(skill_ids or []), learning_focus or ""]).lower()
    if "travel_greeting" in blob or "greeting" in blob or "airport" in blob:
        return "travel_greetings"
    if "appropriate_rate" in blob or "speaking rate" in blob or "fluency" in blob or "pace" in blob:
        return "speaking_rate"
    if "polite" in blob or "request" in blob:
        return "everyday"
    return "everyday"


def select_vocabulary_targets(
    *,
    cefr: str,
    skill_ids: list[str],
    learning_focus: str,
    count: int,
) -> list[VocabularyTarget]:
    """Select real lexical curriculum items for this lesson."""
    theme = theme_for_skill_ids(skill_ids, learning_focus)
    level = (cefr or "A2").upper()
    if theme == "travel_greetings":
        pack = TRAVEL_GREETINGS_A1 if level == "A1" else TRAVEL_GREETINGS_A2
        if level in {"B1", "B2", "C1", "C2"}:
            # Higher CEFR still may practice greetings with A2+ density pack
            pack = TRAVEL_GREETINGS_A2
    elif theme == "speaking_rate":
        pack = SPEAKING_RATE_B2
    else:
        pack = EVERYDAY_A1 if level == "A1" else EVERYDAY_A2

    filtered = _filter_by_cefr(pack, level)
    if len(filtered) < count and theme == "speaking_rate":
        # Keep pack as-is for B2 fluency themes
        filtered = list(pack)
    return filtered[: max(1, count)]
