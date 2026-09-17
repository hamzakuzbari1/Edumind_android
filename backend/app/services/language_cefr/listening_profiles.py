"""Listening CEFR profile definitions — single registry (Phase 1.1 blueprint)."""

from __future__ import annotations

from app.models.language.enums import LanguageLevel
from app.services.language_cefr.types import CefrListeningProfile, ListeningQuestionType

# ---------------------------------------------------------------------------
# A1 — Breakthrough
# ---------------------------------------------------------------------------
_A1 = CefrListeningProfile(
    level=LanguageLevel.A1,
    transcript_min_words=30,
    transcript_max_words=65,
    ideal_word_count=45,
    sentence_min_words=4,
    sentence_max_words=8,
    allowed_grammar=(
        "present simple",
        "be + adjective/noun",
        "simple WH and yes/no questions",
        "simple negatives",
        "basic imperatives",
    ),
    forbidden_grammar=(
        "past perfect",
        "conditionals",
        "passive voice",
        "relative clauses",
        "reported speech",
        "subjunctive",
        "present perfect",
        "past simple",
    ),
    vocabulary_band=(
        "Top 500–800 high-frequency words only; no academic lexis, idioms, "
        "phrasal verbs, or rare vocabulary; heavy repetition acceptable."
    ),
    topic_complexity=(
        "Suitable: self-introduction, family, daily routine, food, weather, "
        "classroom, simple purchases. "
        "Unsuitable: politics, abstract ethics, academic lectures, job interviews, news analysis."
    ),
    listening_objectives=(
        "Understand very short, simple messages when speech is slow and clear.",
        "Catch explicit facts: name, age, nationality, simple prices and times.",
        "Follow basic classroom instructions and familiar words in announcements.",
    ),
    allowed_question_types=(
        ListeningQuestionType.detail,
        ListeningQuestionType.main_idea,
        ListeningQuestionType.matching,
        ListeningQuestionType.sequence,
        ListeningQuestionType.sentence_completion,
        ListeningQuestionType.purpose,
    ),
    forbidden_question_types=(
        ListeningQuestionType.inference,
        ListeningQuestionType.speaker_intention,
        ListeningQuestionType.opinion,
        ListeningQuestionType.tone,
        ListeningQuestionType.bias,
        ListeningQuestionType.prediction,
        ListeningQuestionType.true_false_notgiven,
    ),
    distractor_complexity=(
        "Low: wrong answers use clearly different content; no near-synonym traps; "
        "one distractor may be absurd or obvious."
    ),
    inference_level="none",
    cognitive_load=(
        "Memory: recall one fact. Inference, reasoning, prediction, and implicit "
        "meaning: none."
    ),
    recommended_speaking_speed="100–120 wpm (slow, clearly articulated; pauses between sentences)",
    recommended_accent=(
        "Standard neutral English (clear en-US or en-GB); single speaker preferred; "
        "no regional accents or fast connected speech."
    ),
    learning_goal=(
        "After ~20 lessons: understand slow, clear self-introductions; catch explicit "
        "facts without transcript; answer simple detail questions; build confidence "
        "with short listening clips."
    ),
)

# ---------------------------------------------------------------------------
# A2 — Waystage
# ---------------------------------------------------------------------------
_A2 = CefrListeningProfile(
    level=LanguageLevel.A2,
    transcript_min_words=55,
    transcript_max_words=110,
    ideal_word_count=70,
    sentence_min_words=6,
    sentence_max_words=12,
    allowed_grammar=(
        "all A1 structures",
        "past simple (regular and common irregular)",
        "going to future",
        "present continuous",
        "can/can't and basic must",
        "simple conjunctions (and, but, because)",
        "present perfect (limited, familiar contexts only)",
    ),
    forbidden_grammar=(
        "third conditional",
        "complex passive chains",
        "embedded relative clauses",
    ),
    vocabulary_band=(
        "Top 1,500–2,000 words; very limited academic nouns (school subjects); "
        "rare transparent idioms; common transparent phrasal verbs; low–moderate "
        "lexical richness."
    ),
    topic_complexity=(
        "Suitable: shopping, hobbies, travel plans, weekend activities, basic health, "
        "simple workplace instructions, describing family or photos. "
        "Unsuitable: legal contracts, philosophical debate, multi-stakeholder policy, satirical comedy."
    ),
    listening_objectives=(
        "Understand short, simple messages on familiar matters (routine, shopping, local area).",
        "Follow simple directions, short phone messages, and basic weather forecasts.",
        "Understand descriptions of daily routine.",
    ),
    allowed_question_types=(
        ListeningQuestionType.detail,
        ListeningQuestionType.main_idea,
        ListeningQuestionType.inference,
        ListeningQuestionType.speaker_intention,
        ListeningQuestionType.purpose,
        ListeningQuestionType.prediction,
        ListeningQuestionType.matching,
        ListeningQuestionType.sequence,
        ListeningQuestionType.true_false_notgiven,
        ListeningQuestionType.sentence_completion,
    ),
    forbidden_question_types=(
        ListeningQuestionType.opinion,
        ListeningQuestionType.tone,
        ListeningQuestionType.bias,
    ),
    distractor_complexity=(
        "Low–medium: same topic domain; one distractor may swap a number or time; "
        "avoid subtle paraphrase traps."
    ),
    inference_level="one-step simple",
    cognitive_load=(
        "Memory: two related facts. Inference: one-step. Reasoning: simple cause–effect. "
        "Prediction: simple next step. Implicit meaning: minimal."
    ),
    recommended_speaking_speed="120–140 wpm (natural but clear; some linking acceptable)",
    recommended_accent=(
        "Neutral primary plus one mild regional variant optional; simple two-speaker dialogues."
    ),
    learning_goal=(
        "Follow short conversations on familiar topics; distinguish main point from one "
        "supporting detail; handle simple inference and T/F/NG; tolerate slightly faster speech."
    ),
)

# ---------------------------------------------------------------------------
# B1 — Threshold
# ---------------------------------------------------------------------------
_B1 = CefrListeningProfile(
    level=LanguageLevel.B1,
    transcript_min_words=90,
    transcript_max_words=170,
    ideal_word_count=110,
    sentence_min_words=10,
    sentence_max_words=16,
    allowed_grammar=(
        "all A2 structures",
        "present perfect vs past simple contrast",
        "first conditional",
        "defining relative clauses",
        "passive (common forms)",
        "modal verbs (might, should, could)",
        "second conditional (limited)",
        "reported speech (simple)",
    ),
    forbidden_grammar=(
        "dense academic syntax",
        "literary inversion",
    ),
    vocabulary_band=(
        "2,500–3,500 words; AWL Tier 1–2 in simple contexts; common idioms; "
        "extended phrasal verbs; occasional rare words; moderate lexical richness."
    ),
    topic_complexity=(
        "Suitable: travel problems, job experiences, general environmental issues, "
        "education choices, technology use, accessible cultural differences. "
        "Unsuitable: specialized medical research, legal fine print, dense economic forecasting, irony-heavy satire."
    ),
    listening_objectives=(
        "Understand main points of clear standard speech on familiar matters (work, school, leisure, travel).",
        "Follow radio announcements, simple interviews, and explanations of a process.",
        "Express and understand opinions on familiar topics.",
    ),
    allowed_question_types=(
        ListeningQuestionType.detail,
        ListeningQuestionType.main_idea,
        ListeningQuestionType.inference,
        ListeningQuestionType.speaker_intention,
        ListeningQuestionType.opinion,
        ListeningQuestionType.tone,
        ListeningQuestionType.purpose,
        ListeningQuestionType.prediction,
        ListeningQuestionType.matching,
        ListeningQuestionType.sequence,
        ListeningQuestionType.true_false_notgiven,
        ListeningQuestionType.sentence_completion,
    ),
    forbidden_question_types=(
        ListeningQuestionType.bias,
    ),
    distractor_complexity=(
        "Medium: paraphrase distractors in the same semantic field; one distractor "
        "may be partially true (Not Given required for T/F/NG)."
    ),
    inference_level="one-to-two steps",
    cognitive_load=(
        "Memory: hold two to three facts across a short passage. Inference: one to two steps. "
        "Reasoning: compare two stated reasons. Prediction: plausible next event. "
        "Implicit meaning: basic (e.g. sigh → frustration)."
    ),
    recommended_speaking_speed="140–160 wpm (natural connected speech; moderate redundancy)",
    recommended_accent=(
        "Up to two accents per lesson (e.g. British + American); multi-speaker dialogues (2–3 speakers); "
        "mild connected speech (gonna, wanna) sparingly."
    ),
    learning_goal=(
        "Follow extended monologue on familiar topics; answer inference and opinion questions; "
        "use T/F/NG reliably; cope with natural pace and mild accent variation."
    ),
)

# ---------------------------------------------------------------------------
# B2 — Vantage
# ---------------------------------------------------------------------------
_B2 = CefrListeningProfile(
    level=LanguageLevel.B2,
    transcript_min_words=150,
    transcript_max_words=280,
    ideal_word_count=170,
    sentence_min_words=12,
    sentence_max_words=20,
    allowed_grammar=(
        "all B1 structures",
        "second conditional",
        "mixed conditionals (simple)",
        "passive across tenses",
        "complex sentences with multiple subordinate clauses",
        "participle clauses (limited)",
        "reported speech (full common forms)",
    ),
    forbidden_grammar=(
        "dense C1 rhetorical inversion as default",
    ),
    vocabulary_band=(
        "4,000–5,000+ words; AWL Tier 1–3; frequent idioms including less transparent; "
        "full common phrasal verbs plus figurative uses; occasional domain-specific terms; high lexical richness."
    ),
    topic_complexity=(
        "Suitable: social media impact, urban planning, workplace ethics, migration stories, "
        "climate policy for general audience, accessible arts/culture criticism. "
        "Unsuitable: PhD-level technical lectures, highly specialized legal testimony, unexplained jargon fields, rapid cultural-only comedy."
    ),
    listening_objectives=(
        "Understand extended speech and lectures; follow complex lines of argument on familiar and abstract topics.",
        "Follow radio documentaries, debates with contrasting viewpoints, professional meetings, and news with background context.",
    ),
    allowed_question_types=tuple(ListeningQuestionType),
    forbidden_question_types=(),
    distractor_complexity=(
        "Medium–high: near-paraphrase and plausible partial truths; distractors may reuse "
        "transcript keywords with wrong collocation."
    ),
    inference_level="multi-step",
    cognitive_load=(
        "Memory: integrate information across the full passage. Inference: multi-step. "
        "Reasoning: evaluate competing claims. Prediction: based on argument structure. "
        "Implicit meaning: speaker attitude and hedging (I suppose, arguably)."
    ),
    recommended_speaking_speed="160–180 wpm (natural lecture/dialogue pace; overlapping speech acceptable)",
    recommended_accent=(
        "Multiple accents (British, American, Australian, mild international); "
        "2–4 speakers in discussion; connected speech and reductions common."
    ),
    learning_goal=(
        "Follow extended arguments and identify speaker stance; distinguish fact, opinion, and implication; "
        "handle academic-ish vocabulary; perform at IELTS Band 5.5–6.5 listening equivalence."
    ),
)

# ---------------------------------------------------------------------------
# C1 — Effective Operational Proficiency
# ---------------------------------------------------------------------------
_C1 = CefrListeningProfile(
    level=LanguageLevel.C1,
    transcript_min_words=200,
    transcript_max_words=350,
    ideal_word_count=230,
    sentence_min_words=15,
    sentence_max_words=25,
    allowed_grammar=(
        "all B2 structures",
        "third conditional",
        "mixed conditionals (full)",
        "inversion for emphasis",
        "cleft sentences",
        "complex nominalization",
        "subjunctive (formal)",
        "dense subordination in academic/professional register",
    ),
    forbidden_grammar=(),
    vocabulary_band=(
        "6,000–8,000+ words; full AWL and discipline-neutral academic lexis; advanced contextual idioms; "
        "low-frequency figurative phrasal verbs; domain terms (jurisdiction, paradigm, mitigate); very high lexical richness."
    ),
    topic_complexity=(
        "Suitable: AI ethics, globalization, education reform, professional development, leadership, "
        "media literacy, cognitive bias. "
        "Unsuitable: undifferentiated PhD seminars without scaffolding, raw technical specs without context."
    ),
    listening_objectives=(
        "Understand long, complex speech even when not clearly structured.",
        "Recognize implicit attitudes and unstated assumptions in academic lectures, professional podcasts, and policy discussions.",
    ),
    allowed_question_types=tuple(ListeningQuestionType),
    forbidden_question_types=(),
    distractor_complexity=(
        "High: sophisticated paraphrase; distractors reflect plausible misreadings of nuance; "
        "Not Given essential for unstated claims."
    ),
    inference_level="deep",
    cognitive_load=(
        "Memory: synthesize across long, non-linear speech. Inference: deep, requires world and linguistic knowledge. "
        "Reasoning: evaluate argument strength. Prediction: anticipate rhetorical moves. "
        "Implicit meaning: central (what is the speaker not saying?)."
    ),
    recommended_speaking_speed=(
        "170–190 wpm (native-like lecture and panel pace; overlaps, false starts, self-correction acceptable)"
    ),
    recommended_accent=(
        "Full accent diversity including non-native high-proficiency speakers; "
        "multi-party discussions (3–5 speakers); idiolect and register shifts within one passage."
    ),
    learning_goal=(
        "Comprehend implicit meaning and speaker positioning; critically evaluate claims and bias; "
        "handle academic/professional register at speed; IELTS Band 7–8 listening equivalence."
    ),
)

# ---------------------------------------------------------------------------
# C2 — Mastery
# ---------------------------------------------------------------------------
_C2 = CefrListeningProfile(
    level=LanguageLevel.C2,
    transcript_min_words=280,
    transcript_max_words=450,
    ideal_word_count=280,
    sentence_min_words=18,
    sentence_max_words=28,
    allowed_grammar=(
        "full native-like grammatical range including all C1 structures",
        "literary and rhetorical devices (anaphora, tricolon, ironic understatement)",
        "ellipsis and advanced discourse cohesion",
        "register switching mid-passage for effect",
    ),
    forbidden_grammar=(
        "written-essay syntax pasted as unnatural spoken English",
    ),
    vocabulary_band=(
        "8,000–10,000+ words; specialist and cross-disciplinary academic lexis; "
        "full idiom range including culture-bound (with context clues); all phrasal-verb registers; "
        "frequent precise connotative vocabulary; near-native synonym discrimination."
    ),
    topic_complexity=(
        "Suitable: geopolitics, epistemology, professional ethics, scientific discourse for educated lay audience, "
        "literary/cultural analysis. "
        "Unsuitable: content with zero context for any listener, deliberately obscurantist jargon, audio requiring visual supplements."
    ),
    listening_objectives=(
        "Understand virtually everything heard, including idiomatic, implicit, and culturally loaded speech.",
        "Track rapid shifts in topic and register in expert panels, sophisticated documentaries, negotiations, and satire."
    ),
    allowed_question_types=tuple(ListeningQuestionType),
    forbidden_question_types=(),
    distractor_complexity=(
        "Very high: near-equivalent paraphrases; requires precise comprehension of scope and modality (may vs will, some vs most)."
    ),
    inference_level="multi-layer",
    cognitive_load=(
        "Memory: integrate long, digressive speech. Inference: multi-layer and pragmatic/cultural. "
        "Reasoning: evaluate competing sophisticated arguments. Prediction: anticipate rhetorical and logical turns. "
        "Implicit meaning: primary assessment target."
    ),
    recommended_speaking_speed=(
        "180–200+ wpm (native lecture, debate, and broadcast pace; natural disfluency, overlap, and repair)"
    ),
    recommended_accent=(
        "Full international range including regional variants (Scottish, Indian English, Australian, etc.); "
        "multiple speakers with distinct voices and agendas; authentic broadcast and academic patterns."
    ),
    learning_goal=(
        "Near-native comprehension of extended implicit idiomatic speech; detect bias, irony, and rhetorical strategy; "
        "IELTS Band 8.5–9 / CPE listening equivalence; ready for university and professional English environments."
    ),
)

LISTENING_CEFR_PROFILES: dict[LanguageLevel, CefrListeningProfile] = {
    LanguageLevel.A1: _A1,
    LanguageLevel.A2: _A2,
    LanguageLevel.B1: _B1,
    LanguageLevel.B2: _B2,
    LanguageLevel.C1: _C1,
    LanguageLevel.C2: _C2,
}
