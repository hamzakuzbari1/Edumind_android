"""Draft speaking-placement prompt content and seeding logic (Blueprint Phase A0+A1, MVP
activation).

MVP product decision: the drafted speaking_prompt items (originally 30; extended with cross-level
diversity top-ups, see SPEAKING_PROMPT_SEEDS) are used for MVP placement WITHOUT a completed
human-review pass. This module must never write or imply that a human review was performed --
every item it writes carries an explicit, machine-readable "mvp_approved_pending_full_review" /
human_reviewed=False marker (see MVP_REVIEW_STATUS below), and a full linguistic/content audit is
expected after MVP.

Kept importable/testable under app/services/ (rather than only in backend/scripts/, which is
excluded from the test Docker image via Dockerfile.test.dockerignore) so the seeding logic and
authored content can be covered by the automated test suite. backend/scripts/
seed_speaking_placement_prompts.py is a thin CLI wrapper around seed_speaking_prompts() and
activate_mvp_drafts() below.

Safety:
- Idempotent by stable_key: existing rows are updated (content only), missing rows are inserted.
- seed_speaking_prompts() NEVER touches is_verified/is_active on an update -- only a fresh
  insert sets them (now is_verified=True/is_active=True, reflecting the MVP-approved decision
  for this batch). So a routine re-run (fixing a typo, adding more items) can never silently
  change verification status either way.
- activate_mvp_drafts() is a separate, narrowly-scoped, explicit one-time action for rows that
  were already inserted before this MVP decision (i.e. still sitting in the exact
  never-touched-since-seeding state: source == "draft_seed" and is_verified is False). It is
  itself idempotent (a second run activates zero additional rows) and never touches a row a
  human/operator has since modified in any way (different source, or already verified either
  direction) -- so it cannot overwrite a later reviewer decision.
- Nothing here is wired into the live exam route by this module itself; skill="speaking_prompt"
  selection is wired in language_exam.py separately.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.catalog import Language
from app.models.language.enums import LanguageLevel
from app.models.language.question_bank import LanguagePlacementQuestionBankItem


MVP_REVIEW_STATUS = "mvp_approved_pending_full_review"

GRADE_BANDS = ("early_primary", "upper_primary", "middle_school", "secondary", "mixed_school")
ALL_GRADE_BANDS = list(GRADE_BANDS)
OLDER_GRADE_BANDS = ["middle_school", "secondary", "mixed_school"]

TASK_TYPES = (
    "self_intro",
    "simple_personal_information",
    "routine_description",
    "simple_preference",
    "past_narration",
    "opinion_justification",
    "compare_contrast",
    "hypothetical_reasoning",
    "abstract_discussion",
    "nuanced_argument",
)

DURATION_BY_LEVEL: dict[str, dict[str, int]] = {
    "A1": {"min": 10, "target": 20, "max": 45},
    "A2": {"min": 15, "target": 30, "max": 60},
    "B1": {"min": 20, "target": 40, "max": 75},
    "B2": {"min": 25, "target": 45, "max": 90},
    "C1": {"min": 30, "target": 55, "max": 100},
    "C2": {"min": 35, "target": 60, "max": 110},
}

COMPONENT_CODE_BY_TASK_TYPE: dict[str, str | None] = {
    "self_intro": "speaking.intro_personal",
    # Same A1 component as self_intro -- both are personal-information-disclosure tasks at the
    # same CEFR band, just a different prompt angle (see the taxonomy's existing precedent of
    # grouping conceptually-similar task types under one component, e.g. past_narration below).
    "simple_personal_information": "speaking.intro_personal",
    "routine_description": "speaking.describe_routine",
    "simple_preference": None,  # no existing learner-model component fits a bare preference+reason task yet
    "past_narration": "speaking.justify_opinion",  # existing event-mapping conflates B1 narration into this component
    "opinion_justification": "speaking.justify_opinion",
    "compare_contrast": None,  # no existing learner-model component for this task type yet
    "hypothetical_reasoning": "speaking.hypothetical",
    "abstract_discussion": "speaking.fluency_discourse",
    "nuanced_argument": "speaking.fluency_discourse",  # existing mapping reuses the C1 component for C2
}

REFERENCE_NOTES_BY_TASK_TYPE: dict[str, str] = {
    "self_intro": (
        "Reviewer check: prompt is simple and closed-scope, eliciting basic present-tense "
        "self-description (name, origin, likes). Confirm it asks for nothing beyond a first "
        "name / general origin. Suitable for all grade bands."
    ),
    "simple_personal_information": (
        "Reviewer check: prompt asks for one simple, closed-scope personal fact or preference "
        "(e.g. favorite color, family size) -- deliberately narrower than self_intro's full "
        "introduction framing, so the two task types read as genuinely different questions. "
        "Confirm it stays basic/present-tense. Suitable for all grade bands."
    ),
    "routine_description": (
        "Reviewer check: prompt elicits present-simple habitual description with sequencing "
        "vocabulary. Confirm the scenario stays neutral and age-appropriate; avoid "
        "workplace-specific routines for young learners."
    ),
    "simple_preference": (
        "Reviewer check: prompt asks the student to state a simple preference between two "
        "everyday options and give one brief reason, using present-tense/simple structures "
        "appropriate for A2 -- deliberately distinct from routine_description's daily-schedule "
        "framing. Confirm the topic is neutral and age-appropriate. Suitable for all grade bands."
    ),
    "past_narration": (
        "Reviewer check: prompt requires past-tense narration with some sequencing. Confirm the "
        "scenario does not assume experiences (e.g. international travel) that could "
        "disadvantage students from any particular background -- imaginative framing is fine."
    ),
    "opinion_justification": (
        "Reviewer check: prompt elicits a stated opinion plus at least one supporting reason. "
        "Confirm the topic is appropriate for the target grade band and not politically or "
        "culturally sensitive."
    ),
    "compare_contrast": (
        "Reviewer check: prompt requires comparing two clearly named options with reasoning. "
        "Confirm both options are genuinely comparable and age-appropriate."
    ),
    "hypothetical_reasoning": (
        "Reviewer check: prompt requires conditional/hypothetical language (if-clauses) plus "
        "reasoned justification. Confirm the hypothetical scenario is age-appropriate and not "
        "distressing."
    ),
    "abstract_discussion": (
        "Reviewer check: prompt requires discussing an abstract/societal issue with discourse "
        "markers and extended reasoning. Confirm the topic avoids partisan political framing "
        "and stays broadly discussable."
    ),
    "nuanced_argument": (
        "Reviewer check: prompt requires acknowledging multiple sides before reaching a "
        "position, at a genuinely C2 level of nuance. Confirm the topic has legitimate "
        "two-sided debate potential without being inflammatory."
    ),
}

_BOUNDARY_REVIEWER_SUFFIX = (
    " Boundary-confirmation item -- verify this cleanly sits at the {low}/{high} difficulty "
    "line: a {low}-level student should find it genuinely challenging, while a {high}-level "
    "student should handle it comfortably."
)


@dataclass(frozen=True)
class SpeakingPromptSeed:
    # Language-agnostic content identifier (e.g. "A1:self_intro:01"). The DB's stable_key column
    # has a GLOBAL unique constraint, not one scoped per language -- so the actual persisted
    # stable_key must incorporate the target language (see db_stable_key()) or seeding a second
    # language would collide with, or silently steal, the first language's rows.
    content_key: str
    level: LanguageLevel
    subskill: str  # task type -- must be a member of TASK_TYPES
    prompt_text: str
    situation: str
    grade_band: tuple[str, ...]
    boundary_low_level: LanguageLevel | None = None
    boundary_high_level: LanguageLevel | None = None

    @property
    def expected_response_seconds(self) -> dict[str, int]:
        return DURATION_BY_LEVEL[self.level.value]

    @property
    def component_code(self) -> str | None:
        return COMPONENT_CODE_BY_TASK_TYPE.get(self.subskill)

    @property
    def reference_notes(self) -> str:
        note = REFERENCE_NOTES_BY_TASK_TYPE[self.subskill]
        if self.boundary_low_level and self.boundary_high_level:
            note += _BOUNDARY_REVIEWER_SUFFIX.format(
                low=self.boundary_low_level.value, high=self.boundary_high_level.value
            )
        note += (
            " MVP note: this item is active for MVP placement without a completed human-review "
            "pass -- the checks above still need to be performed in the full post-MVP audit."
        )
        return note

    def body_json(self) -> dict:
        body: dict = {
            "grade_band": list(self.grade_band),
            "expected_response_seconds": self.expected_response_seconds,
            "reference_notes": self.reference_notes,
            # Explicit, machine-readable MVP status -- never claim a human review was done.
            "review_status": MVP_REVIEW_STATUS,
            "human_reviewed": False,
        }
        if self.component_code:
            body["component_code"] = self.component_code
        return body


def db_stable_key(language_code: str, content_key: str) -> str:
    """The actual value stored in the DB's globally-unique stable_key column -- namespaced by
    language so the same authored content_key can be seeded for more than one language without
    colliding (v1 only seeds "en", but the key scheme must not silently break if that changes)."""
    return f"speaking_prompt:{language_code}:{content_key}"


def _seed(
    *,
    key: str,
    level: str,
    subskill: str,
    situation: str,
    prompt_text: str,
    grade_band: tuple[str, ...] = tuple(ALL_GRADE_BANDS),
    boundary: tuple[str, str] | None = None,
) -> SpeakingPromptSeed:
    low, high = (LanguageLevel(boundary[0]), LanguageLevel(boundary[1])) if boundary else (None, None)
    return SpeakingPromptSeed(
        content_key=key,
        level=LanguageLevel(level),
        subskill=subskill,
        prompt_text=prompt_text,
        situation=situation,
        grade_band=grade_band,
        boundary_low_level=low,
        boundary_high_level=high,
    )


SPEAKING_PROMPT_SEEDS: list[SpeakingPromptSeed] = [
    # --- A1 : self_intro (universal, no age restriction) ---------------------------------
    _seed(
        key="A1:self_intro:01",
        level="A1",
        subskill="self_intro",
        situation="You are meeting a new classmate for the first time.",
        prompt_text=(
            "Hello! Please introduce yourself. Tell me your name, where you are from, and one "
            "thing you like."
        ),
    ),
    _seed(
        key="A1:self_intro:02",
        level="A1",
        subskill="self_intro",
        situation="You are recording a short video to introduce yourself to a new online class.",
        prompt_text="Introduce yourself for the class. Say your name, your age, and something you enjoy doing.",
    ),
    _seed(
        key="A1:self_intro:03",
        level="A1",
        subskill="self_intro",
        situation="You are meeting a host family for the first time during a homestay visit.",
        prompt_text="Introduce yourself to your host family. Tell them your name, where you are from, and your favorite food.",
    ),
    # --- A1 : simple_personal_information (universal, no age restriction) -----------------
    # Deliberately distinct from self_intro: one narrow personal-fact question rather than a
    # full introduction, so an A1-level session has more than one subskill to draw from.
    _seed(
        key="A1:simple_personal_information:01",
        level="A1",
        subskill="simple_personal_information",
        situation="A new friend wants to know a little about you.",
        prompt_text="What is your favorite color? Why do you like it?",
    ),
    _seed(
        key="A1:simple_personal_information:02",
        level="A1",
        subskill="simple_personal_information",
        situation="Someone is asking about your family.",
        prompt_text="Tell me about your family. How many people are in your family?",
    ),
    _seed(
        key="A1:simple_personal_information:03",
        level="A1",
        subskill="simple_personal_information",
        situation="A classmate is curious about the things you like.",
        prompt_text="What is your favorite animal? Why do you like it?",
    ),
    # --- A2 : routine_description (universal, no age restriction) -------------------------
    _seed(
        key="A2:routine_description:01",
        level="A2",
        subskill="routine_description",
        situation="A new friend wants to know about your daily life.",
        prompt_text="Tell me about your typical day. What do you usually do in the morning, afternoon, and evening?",
    ),
    _seed(
        key="A2:routine_description:02",
        level="A2",
        subskill="routine_description",
        situation="You are talking with a pen pal about your week.",
        prompt_text="Describe what you usually do on the weekend. What activities do you do, and who do you do them with?",
    ),
    _seed(
        key="A2:routine_description:03",
        level="A2",
        subskill="routine_description",
        situation="Someone is asking about your school or daily routine.",
        prompt_text="Describe your usual weekday routine. What time do you wake up, what do you do during the day, and what time do you go to bed?",
    ),
    # --- A2 : simple_preference (universal, no age restriction) ----------------------------
    # Deliberately distinct from routine_description: a stated preference plus one reason,
    # not a daily-schedule description, so an A2-level session has more than one subskill.
    _seed(
        key="A2:simple_preference:01",
        level="A2",
        subskill="simple_preference",
        situation="A friend is asking about the things you enjoy.",
        prompt_text="What is your favorite season of the year? Explain why you like it.",
    ),
    _seed(
        key="A2:simple_preference:02",
        level="A2",
        subskill="simple_preference",
        situation="Someone wants to know your food preferences.",
        prompt_text="Do you prefer eating at home or eating at a restaurant? Explain your preference.",
    ),
    _seed(
        key="A2:simple_preference:03",
        level="A2",
        subskill="simple_preference",
        situation="A classmate is asking about how you like to relax.",
        prompt_text="Do you prefer reading books or watching movies? Explain your preference.",
    ),
    # --- B1 : past_narration (universal, no age restriction) ------------------------------
    _seed(
        key="B1:past_narration:01",
        level="B1",
        subskill="past_narration",
        situation="A friend is asking about your last trip or vacation.",
        prompt_text="Tell me about a trip or vacation you took. Where did you go, what did you do, and how did you feel about it?",
    ),
    _seed(
        key="B1:past_narration:02",
        level="B1",
        subskill="past_narration",
        situation="You are telling a classmate about something memorable that happened to you.",
        prompt_text="Describe a memorable day from your past. What happened, and why was it memorable for you?",
    ),
    _seed(
        key="B1:past_narration:03",
        level="B1",
        subskill="past_narration",
        situation="A friend asks about how you learned a skill.",
        prompt_text="Talk about a time you learned something new. What did you learn, how did you learn it, and what was difficult about it?",
    ),
    # --- B1 : opinion_justification (universal, no age restriction) -----------------------
    _seed(
        key="B1:opinion_justification:01",
        level="B1",
        subskill="opinion_justification",
        situation="A friend is asking for your opinion about technology in class.",
        prompt_text="Do you think students should be allowed to use phones in class? Give your opinion and explain your reasons.",
    ),
    _seed(
        key="B1:opinion_justification:02",
        level="B1",
        subskill="opinion_justification",
        situation="Someone is asking what you think about the place where you live.",
        prompt_text="What do you like or dislike about the place where you live? Explain your opinion with reasons.",
    ),
    _seed(
        key="B1:opinion_justification:03",
        level="B1",
        subskill="opinion_justification",
        situation="A classmate asks for your opinion about free-time activities.",
        prompt_text="Do you think it's better to spend free time alone or with friends? Give your opinion and explain why.",
    ),
    # --- B2 : compare_contrast (older bands -- assumes some independence/judgment) --------
    _seed(
        key="B2:compare_contrast:01",
        level="B2",
        subskill="compare_contrast",
        situation="A friend is deciding between two places to live.",
        prompt_text="Compare living in a big city with living in a small town. What are the advantages and disadvantages of each?",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    _seed(
        key="B2:compare_contrast:02",
        level="B2",
        subskill="compare_contrast",
        situation="Someone is asking you to help them choose a way of studying.",
        prompt_text="Compare studying alone with studying in a group. Which do you think works better, and why?",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    _seed(
        key="B2:compare_contrast:03",
        level="B2",
        subskill="compare_contrast",
        situation="A friend is choosing between two ways of communicating.",
        prompt_text="Compare talking to someone in person with talking to them online. What are the benefits and drawbacks of each?",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    # --- B2 : hypothetical_reasoning (older bands -- avoids distressing hypotheticals) -----
    _seed(
        key="B2:hypothetical_reasoning:01",
        level="B2",
        subskill="hypothetical_reasoning",
        situation="A friend is asking what you would do in an unusual situation.",
        prompt_text="If you found a wallet full of money on the street, what would you do? Explain your reasoning.",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    _seed(
        key="B2:hypothetical_reasoning:02",
        level="B2",
        subskill="hypothetical_reasoning",
        situation="Someone is asking about a hypothetical change at your school or workplace.",
        prompt_text="If you could change one thing about your school or workplace, what would it be and why?",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    _seed(
        key="B2:hypothetical_reasoning:03",
        level="B2",
        subskill="hypothetical_reasoning",
        situation="A friend asks about an imagined opportunity.",
        prompt_text="If you had one extra hour every day, how would you use it? Explain your thinking.",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    # --- C1 : abstract_discussion (older bands) --------------------------------------------
    _seed(
        key="C1:abstract_discussion:01",
        level="C1",
        subskill="abstract_discussion",
        situation="You are having a thoughtful conversation about how technology affects society.",
        prompt_text="How do you think social media has changed the way people build relationships? Discuss both positive and negative effects.",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    _seed(
        key="C1:abstract_discussion:02",
        level="C1",
        subskill="abstract_discussion",
        situation="A discussion about education and society.",
        prompt_text="To what extent do you think formal education prepares people for real life? Discuss the strengths and limitations of traditional schooling.",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    _seed(
        key="C1:abstract_discussion:03",
        level="C1",
        subskill="abstract_discussion",
        situation="A conversation about environmental responsibility.",
        prompt_text="Discuss the balance between individual responsibility and government action in addressing environmental problems.",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    # --- C2 : nuanced_argument (older bands) ------------------------------------------------
    _seed(
        key="C2:nuanced_argument:01",
        level="C2",
        subskill="nuanced_argument",
        situation="You are debating a topic where reasonable people disagree.",
        prompt_text="Some people argue that artificial intelligence will ultimately benefit humanity, while others fear its risks outweigh its benefits. Present a nuanced argument that acknowledges both sides before stating your own position.",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    _seed(
        key="C2:nuanced_argument:02",
        level="C2",
        subskill="nuanced_argument",
        situation="A discussion requiring you to respond to a counter-argument.",
        prompt_text="Someone argues that a country's cultural traditions should never change, even as society evolves. Construct a counter-argument, addressing the strongest points of that view.",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    _seed(
        key="C2:nuanced_argument:03",
        level="C2",
        subskill="nuanced_argument",
        situation="A debate about competing values.",
        prompt_text="Discuss the tension between protecting individual privacy and ensuring public safety. Argue for a balanced position, acknowledging the merits of each side.",
        grade_band=tuple(OLDER_GRADE_BANDS),
    ),
    # --- Boundary items: B1/B2 (level tagged at the higher band, per common convention) ----
    _seed(
        key="boundary:B1_B2:01",
        level="B2",
        subskill="compare_contrast",
        situation="A discussion testing whether you can handle a more complex comparison.",
        prompt_text="Compare two approaches to solving a problem you've faced (for example, working alone vs. asking for help). Explain which approach is generally better and why.",
        grade_band=tuple(OLDER_GRADE_BANDS),
        boundary=("B1", "B2"),
    ),
    _seed(
        key="boundary:B1_B2:02",
        level="B2",
        subskill="hypothetical_reasoning",
        situation="A conversation testing hypothetical reasoning at a slightly higher level.",
        prompt_text="If your school or workplace introduced one new rule, what would you want it to be, and how would you convince others it's a good idea?",
        grade_band=tuple(OLDER_GRADE_BANDS),
        boundary=("B1", "B2"),
    ),
    # --- Boundary items: B2/C1 --------------------------------------------------------------
    _seed(
        key="boundary:B2_C1:01",
        level="C1",
        subskill="abstract_discussion",
        situation="A conversation testing whether you can discuss an issue more abstractly.",
        prompt_text="Discuss how the growth of remote work might reshape city life in the next decade. Consider both opportunities and challenges.",
        grade_band=tuple(OLDER_GRADE_BANDS),
        boundary=("B2", "C1"),
    ),
    _seed(
        key="boundary:B2_C1:02",
        level="C1",
        subskill="abstract_discussion",
        situation="A discussion testing more developed reasoning about a social issue.",
        prompt_text="Discuss whether access to information online has made people better informed or more easily misled. Support your view with reasoning.",
        grade_band=tuple(OLDER_GRADE_BANDS),
        boundary=("B2", "C1"),
    ),
    # --- Boundary items: C1/C2 --------------------------------------------------------------
    _seed(
        key="boundary:C1_C2:01",
        level="C2",
        subskill="nuanced_argument",
        situation="A debate testing whether you can construct a truly nuanced argument.",
        prompt_text="Some argue that competition drives innovation, while others argue that collaboration is a stronger driver of progress. Weigh both positions carefully and defend a nuanced conclusion.",
        grade_band=tuple(OLDER_GRADE_BANDS),
        boundary=("C1", "C2"),
    ),
    _seed(
        key="boundary:C1_C2:02",
        level="C2",
        subskill="nuanced_argument",
        situation="A discussion testing your ability to handle a sophisticated counter-argument.",
        prompt_text="A colleague claims that strict rules are always more effective than flexible guidelines. Construct a well-reasoned response that challenges this claim while acknowledging its valid points.",
        grade_band=tuple(OLDER_GRADE_BANDS),
        boundary=("C1", "C2"),
    ),
]


SPEAKING_PROMPT_SEEDS.extend(
    [
        # --- A1 top-up: more basic personal prompts ---------------------------------------
        _seed(
            key="A1:self_intro:04",
            level="A1",
            subskill="self_intro",
            situation="You are joining a new English group.",
            prompt_text="Say hello and introduce yourself. Tell the group your name, your country, and one hobby.",
        ),
        _seed(
            key="A1:self_intro:05",
            level="A1",
            subskill="self_intro",
            situation="Your teacher asks you to introduce yourself to the class.",
            prompt_text="Tell the class your name, your age, and one thing you do every day.",
        ),
        _seed(
            key="A1:self_intro:06",
            level="A1",
            subskill="self_intro",
            situation="You are making a short voice message for a new friend.",
            prompt_text="Introduce yourself. Say where you live and two things you like.",
        ),
        _seed(
            key="A1:simple_personal_information:04",
            level="A1",
            subskill="simple_personal_information",
            situation="A new classmate wants to know about your room.",
            prompt_text="Describe your room in simple words. What things are in your room?",
        ),
        _seed(
            key="A1:simple_personal_information:05",
            level="A1",
            subskill="simple_personal_information",
            situation="Someone asks about your day at school.",
            prompt_text="What subjects do you study? Say one subject you like and why.",
        ),
        _seed(
            key="A1:simple_personal_information:06",
            level="A1",
            subskill="simple_personal_information",
            situation="A friend asks about your home.",
            prompt_text="Tell me about your home. Is it big or small? What do you like there?",
        ),
        # --- A2 top-up: routine and simple preference -------------------------------------
        _seed(
            key="A2:routine_description:04",
            level="A2",
            subskill="routine_description",
            situation="A friend wants to understand your study habits.",
            prompt_text="Describe how you study English. When do you study, and what activities help you learn?",
        ),
        _seed(
            key="A2:routine_description:05",
            level="A2",
            subskill="routine_description",
            situation="Someone asks about a normal evening in your life.",
            prompt_text="Tell me about your usual evening. What do you do after school or after work?",
        ),
        _seed(
            key="A2:routine_description:06",
            level="A2",
            subskill="routine_description",
            situation="A classmate asks how you prepare for a busy day.",
            prompt_text="Describe your morning routine on a busy day. What do you do first, next, and last?",
        ),
        _seed(
            key="A2:simple_preference:04",
            level="A2",
            subskill="simple_preference",
            situation="A friend is asking about how you travel around your city.",
            prompt_text="Do you prefer walking, taking a bus, or going by car? Explain your choice.",
        ),
        _seed(
            key="A2:simple_preference:05",
            level="A2",
            subskill="simple_preference",
            situation="Someone asks about learning at home or in class.",
            prompt_text="Do you prefer studying at home or studying in a classroom? Say why.",
        ),
        _seed(
            key="A2:simple_preference:06",
            level="A2",
            subskill="simple_preference",
            situation="A friend asks about your free time.",
            prompt_text="Do you prefer quiet activities or active activities in your free time? Explain your preference.",
        ),
        # --- B1 top-up: narration and justified opinion -----------------------------------
        _seed(
            key="B1:past_narration:04",
            level="B1",
            subskill="past_narration",
            situation="A friend asks about a time you solved a problem.",
            prompt_text="Describe a problem you had and how you solved it. What happened, and what did you learn?",
        ),
        _seed(
            key="B1:past_narration:05",
            level="B1",
            subskill="past_narration",
            situation="Someone asks about an important change in your life.",
            prompt_text="Talk about a change you experienced. What changed, how did you feel, and why was it important?",
        ),
        _seed(
            key="B1:past_narration:06",
            level="B1",
            subskill="past_narration",
            situation="A classmate asks about a time you helped someone.",
            prompt_text="Tell me about a time you helped another person. What did you do, and how did it end?",
        ),
        _seed(
            key="B1:opinion_justification:04",
            level="B1",
            subskill="opinion_justification",
            situation="A class is discussing homework.",
            prompt_text="Do you think students should have homework every day? Give your opinion and reasons.",
        ),
        _seed(
            key="B1:opinion_justification:05",
            level="B1",
            subskill="opinion_justification",
            situation="A friend asks about learning languages.",
            prompt_text="What is the best way to improve English speaking? Explain your opinion with examples.",
        ),
        _seed(
            key="B1:opinion_justification:06",
            level="B1",
            subskill="opinion_justification",
            situation="Someone asks about how people should spend free time.",
            prompt_text="Is it better to plan your free time or decide at the last minute? Explain your view.",
        ),
        # --- B2 top-up: comparison and hypothetical reasoning -----------------------------
        _seed(
            key="B2:compare_contrast:04",
            level="B2",
            subskill="compare_contrast",
            situation="A friend is choosing between online and in-person learning.",
            prompt_text="Compare online classes with face-to-face classes. Which works better for different learners, and why?",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="B2:compare_contrast:05",
            level="B2",
            subskill="compare_contrast",
            situation="A group is discussing ways to manage time.",
            prompt_text="Compare making a strict schedule with keeping a flexible routine. What are the benefits and drawbacks of each?",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="B2:compare_contrast:06",
            level="B2",
            subskill="compare_contrast",
            situation="A discussion about different ways to learn from mistakes.",
            prompt_text="Compare learning from personal experience with learning from advice. Which approach is more effective, and why?",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="B2:hypothetical_reasoning:04",
            level="B2",
            subskill="hypothetical_reasoning",
            situation="A school committee asks for student suggestions.",
            prompt_text="If you could design one new school activity, what would it be? Explain how it would help students.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="B2:hypothetical_reasoning:05",
            level="B2",
            subskill="hypothetical_reasoning",
            situation="A friend asks about an important decision.",
            prompt_text="If you had to choose between a safe option and a challenging opportunity, how would you decide?",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="B2:hypothetical_reasoning:06",
            level="B2",
            subskill="hypothetical_reasoning",
            situation="Someone asks how you would improve your local area.",
            prompt_text="If you could improve one thing in your neighborhood, what would you change and why?",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        # --- C1 top-up: abstract discussion ------------------------------------------------
        _seed(
            key="C1:abstract_discussion:04",
            level="C1",
            subskill="abstract_discussion",
            situation="A seminar is discussing modern work and study habits.",
            prompt_text="Discuss whether constant connectivity has improved people's productivity or made concentration more difficult.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C1:abstract_discussion:05",
            level="C1",
            subskill="abstract_discussion",
            situation="A discussion about how people make choices.",
            prompt_text="To what extent do you think convenience shapes people's decisions more than quality or long-term value?",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C1:abstract_discussion:06",
            level="C1",
            subskill="abstract_discussion",
            situation="A thoughtful conversation about education.",
            prompt_text="Discuss whether schools should focus more on creativity or on measurable academic results.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C1:abstract_discussion:07",
            level="C1",
            subskill="abstract_discussion",
            situation="A group is discussing media and public opinion.",
            prompt_text="How does the way information is presented influence what people believe? Give a balanced discussion.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C1:abstract_discussion:08",
            level="C1",
            subskill="abstract_discussion",
            situation="A discussion about ambition and wellbeing.",
            prompt_text="Discuss whether ambition usually helps people live better lives or creates unnecessary pressure.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C1:abstract_discussion:09",
            level="C1",
            subskill="abstract_discussion",
            situation="A conversation about communities and change.",
            prompt_text="Discuss how communities can preserve identity while adapting to social and technological change.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        # --- C2 top-up: nuanced argument ---------------------------------------------------
        _seed(
            key="C2:nuanced_argument:04",
            level="C2",
            subskill="nuanced_argument",
            situation="A debate about fairness and achievement.",
            prompt_text="Some people argue that success is mainly the result of personal effort; others emphasize circumstances and opportunity. Evaluate both views and defend a nuanced position.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C2:nuanced_argument:05",
            level="C2",
            subskill="nuanced_argument",
            situation="A discussion about progress and tradition.",
            prompt_text="Assess the claim that societies should prioritize innovation even when it disrupts familiar ways of life.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C2:nuanced_argument:06",
            level="C2",
            subskill="nuanced_argument",
            situation="A debate about expert advice and public choice.",
            prompt_text="Evaluate whether important public decisions should rely primarily on expert judgment or broader public opinion.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C2:nuanced_argument:07",
            level="C2",
            subskill="nuanced_argument",
            situation="A discussion requiring careful qualification.",
            prompt_text="Critically discuss the idea that efficiency should be the main measure of a successful institution.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C2:nuanced_argument:08",
            level="C2",
            subskill="nuanced_argument",
            situation="A debate about education and independence.",
            prompt_text="Some argue that education should challenge students' beliefs, while others say it should give clear shared foundations. Weigh both positions and state your view.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
        _seed(
            key="C2:nuanced_argument:09",
            level="C2",
            subskill="nuanced_argument",
            situation="A discussion about technology and responsibility.",
            prompt_text="Evaluate the argument that technological creators should be held responsible for how people use their products.",
            grade_band=tuple(OLDER_GRADE_BANDS),
        ),
    ]
)


async def _table_exists(db: AsyncSession) -> bool:
    result = await db.execute(text("SELECT to_regclass('public.language_placement_question_bank_items')"))
    return result.scalar_one_or_none() is not None


async def _language_id(db: AsyncSession, code: str) -> int | None:
    return (
        await db.execute(select(Language.id).where(Language.code == code, Language.is_active.is_(True)).limit(1))
    ).scalar_one_or_none()


async def _existing_by_key(db: AsyncSession, keys: list[str]) -> dict[str, LanguagePlacementQuestionBankItem]:
    if not keys:
        return {}
    rows = (
        await db.execute(
            select(LanguagePlacementQuestionBankItem).where(LanguagePlacementQuestionBankItem.stable_key.in_(keys))
        )
    ).scalars().all()
    return {r.stable_key: r for r in rows if r.stable_key}


def _apply_content_fields(row: LanguagePlacementQuestionBankItem, seed: SpeakingPromptSeed, *, language_id: int) -> None:
    """Populate every field this module owns except is_verified/is_active, which are handled
    separately by the insert/update caller (is_verified must never be reset on a content-only
    re-run once a human reviewer has activated an item)."""
    row.language_id = language_id
    row.skill = "speaking_prompt"
    row.level = seed.level
    row.boundary_low_level = seed.boundary_low_level
    row.boundary_high_level = seed.boundary_high_level
    row.subskill = seed.subskill
    row.question_type = "speaking_prompt"
    row.prompt_text = seed.prompt_text
    row.situation = seed.situation
    row.body_json = seed.body_json()
    row.source = "draft_seed"


def summarize(seeds: list[SpeakingPromptSeed]) -> str:
    by_level: dict[str, int] = {}
    by_task_type: dict[str, int] = {}
    by_grade_band: dict[str, int] = {}
    boundary_pairs: dict[str, int] = {}
    for seed in seeds:
        by_level[seed.level.value] = by_level.get(seed.level.value, 0) + 1
        by_task_type[seed.subskill] = by_task_type.get(seed.subskill, 0) + 1
        for band in seed.grade_band:
            by_grade_band[band] = by_grade_band.get(band, 0) + 1
        if seed.boundary_low_level and seed.boundary_high_level:
            key = f"{seed.boundary_low_level.value}/{seed.boundary_high_level.value}"
            boundary_pairs[key] = boundary_pairs.get(key, 0) + 1

    lines = ["By CEFR level:"]
    lines += [f"  {level}: {count}" for level, count in sorted(by_level.items())]
    lines.append("By task type:")
    lines += [f"  {task_type}: {count}" for task_type, count in sorted(by_task_type.items())]
    lines.append("By grade band:")
    lines += [f"  {band}: {count}" for band, count in sorted(by_grade_band.items())]
    lines.append("Boundary pairs:")
    lines += [f"  {pair}: {count}" for pair, count in sorted(boundary_pairs.items())]
    lines.append("")
    lines.append(
        f"All items are MVP-approved for placement use ({MVP_REVIEW_STATUS}) but have NOT had a "
        "completed human review -- see each item's body_json.reference_notes/review_status. "
        "This module never performs, and never claims to perform, that review itself; a full "
        "linguistic/content audit is expected after MVP."
    )
    return "\n".join(lines)


async def seed_speaking_prompts(
    db: AsyncSession,
    *,
    language_id: int,
    language_code: str,
    apply: bool,
    seeds: list[SpeakingPromptSeed] | None = None,
) -> tuple[int, int]:
    """Core seeding logic, directly callable/testable.

    Idempotent by stable_key (namespaced with language_code via db_stable_key(), since the
    column's own unique constraint is global, not per-language): an existing row's content
    fields are updated but is_verified/is_active are deliberately left untouched, so a human
    reviewer's later decision on an item can never be silently reset by re-running this to fix a
    typo or add more items. A brand new row is inserted as an MVP-approved, active item
    (is_verified=True/is_active=True -- these items are used for MVP placement without a
    completed human review, per explicit product decision; see MVP_REVIEW_STATUS). Returns
    (inserts, updates); in dry-run mode (apply=False) nothing is written and the counts are
    computed, not applied.
    """
    seeds = SPEAKING_PROMPT_SEEDS if seeds is None else seeds
    keys = [db_stable_key(language_code, s.content_key) for s in seeds]
    existing = await _existing_by_key(db, keys)
    inserts = updates = 0
    if apply:
        for seed in seeds:
            key = db_stable_key(language_code, seed.content_key)
            row = existing.get(key)
            if row is None:
                row = LanguagePlacementQuestionBankItem(stable_key=key)
                _apply_content_fields(row, seed, language_id=language_id)
                row.is_verified = True
                row.is_active = True
                db.add(row)
                inserts += 1
            else:
                _apply_content_fields(row, seed, language_id=language_id)
                updates += 1
        await db.commit()
    else:
        inserts = sum(1 for key in keys if key not in existing)
        updates = len(seeds) - inserts
    return inserts, updates


async def activate_mvp_drafts(
    db: AsyncSession, *, language_code: str, seeds: list[SpeakingPromptSeed] | None = None
) -> int:
    """One-time MVP go-live action: elevate rows still sitting in the exact pristine,
    never-touched-since-seeding state (source == "draft_seed" and is_verified is False --
    i.e. inserted by an older version of seed_speaking_prompts(), before the MVP-approved
    decision made fresh inserts default to is_verified=True) to is_verified=True/is_active=True.

    Deliberately separate from seed_speaking_prompts()'s routine content-sync path, which never
    touches is_verified/is_active at all -- so a routine re-run (e.g. to add more items later)
    can never accidentally reactivate an item a human has since deliberately deactivated. This
    function itself only touches rows still exactly in that pristine draft state; anything a
    human/operator has since modified (a different source, or already is_verified=True/False by
    deliberate action after this ran once) is left untouched. Idempotent: a second run activates
    zero additional rows once the batch has been activated once. Returns the number activated.
    """
    seeds = SPEAKING_PROMPT_SEEDS if seeds is None else seeds
    keys = [db_stable_key(language_code, s.content_key) for s in seeds]
    existing = await _existing_by_key(db, keys)
    activated = 0
    for row in existing.values():
        if row.source == "draft_seed" and row.is_verified is False:
            row.is_verified = True
            row.is_active = True
            activated += 1
    if activated:
        await db.commit()
    return activated
