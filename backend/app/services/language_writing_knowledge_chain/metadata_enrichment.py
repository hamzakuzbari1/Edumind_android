"""Derive W1.2 educational metadata fields for knowledge chain nodes."""

from __future__ import annotations

from dataclasses import replace

from app.services.language_writing.enums import ContextComplexity, ExpectedWritingOutput, WritingArc
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChainNode

_GRAMMAR_OUTCOMES: dict[str, str] = {
    "present_simple": "Use present simple correctly",
    "past_simple": "Use past simple correctly",
    "present_continuous": "Use present continuous correctly",
    "present_perfect": "Use present perfect correctly",
    "future_forms": "Use future forms correctly",
    "modal_verbs": "Use modal verbs appropriately",
    "imperatives": "Use imperatives clearly and politely",
    "questions": "Form clear questions",
    "comparatives": "Compare ideas using comparatives",
    "superlatives": "Use superlatives accurately",
    "passive_voice": "Use passive voice when appropriate",
    "conditionals": "Use conditional structures",
    "relative_clauses": "Use relative clauses",
    "linking_words": "Use linking words to connect ideas",
    "because": "Explain reasons with because/so",
    "cause_effect": "Show cause and effect clearly",
    "polite_requests": "Request politely",
    "sequencers": "Sequence ideas with first/then/next",
    "there_is_are": "Describe places with there is/are",
    "possessives": "Use possessives correctly",
    "adjectives": "Use adjectives to describe clearly",
    "conditional_first": "Explain if/then solutions",
}

_TASK_OUTCOMES: dict[str, str] = {
    "describe": "Describe the topic clearly",
    "explain_simple": "Explain a situation step by step",
    "explain": "Explain an idea clearly",
    "narrate": "Tell events in a clear order",
    "complaint": "Explain a problem clearly",
    "request": "Make a polite request",
    "thank": "Express thanks appropriately",
    "follow_up": "Follow up professionally",
    "opinion": "State and support an opinion",
    "compare": "Compare two options clearly",
    "recommend": "Give a clear recommendation",
    "review": "Write a balanced review",
    "report": "Report information objectively",
    "proposal": "Propose a solution clearly",
    "summary": "Summarize key points concisely",
    "application": "Write a focused application paragraph",
    "introduce": "Introduce yourself professionally",
    "invite": "Invite someone with clear details",
    "inquiry": "Ask for information politely",
    "guide": "Guide the reader through steps",
    "advise": "Give helpful advice",
    "persuade": "Persuade the reader respectfully",
    "propose": "Propose a practical solution",
    "argue": "Build a short written argument",
    "plan": "Outline a clear plan",
    "confirm": "Confirm details accurately",
    "announce": "Announce information clearly",
    "respond": "Respond thoughtfully to news",
    "list": "List information clearly",
    "state": "State a position clearly",
    "reflect": "Reflect on an experience",
}

_OUTPUT_OUTCOMES: dict[ExpectedWritingOutput, str] = {
    ExpectedWritingOutput.email: "Write a formal or semi-formal email",
    ExpectedWritingOutput.paragraph: "Write a coherent paragraph",
    ExpectedWritingOutput.essay: "Write a structured essay",
    ExpectedWritingOutput.report: "Write a short report",
    ExpectedWritingOutput.story: "Write a short narrative",
    ExpectedWritingOutput.dialogue: "Write a simple dialogue",
    ExpectedWritingOutput.review: "Write a review with reasons",
    ExpectedWritingOutput.summary: "Write a concise summary",
    ExpectedWritingOutput.article: "Write an informative article",
    ExpectedWritingOutput.message: "Write a clear short message",
}


def _grammar_label(key: str) -> str:
    return key.replace("_", " ") if key else ""


def derive_learning_outcomes(
    *,
    task_type: str,
    genre: str,
    grammar_primary: str,
    grammar_secondary: str,
    expected_output: ExpectedWritingOutput,
    learning_objectives: tuple[str, ...],
    explicit: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if explicit:
        return explicit
    outcomes: list[str] = []
    out_phrase = _OUTPUT_OUTCOMES.get(expected_output)
    if out_phrase:
        outcomes.append(out_phrase)
    task_out = _TASK_OUTCOMES.get(task_type)
    if task_out and task_out not in outcomes:
        outcomes.append(task_out)
    for g in (grammar_primary, grammar_secondary):
        phrase = _GRAMMAR_OUTCOMES.get(g)
        if phrase and phrase not in outcomes:
            outcomes.append(phrase)
    for obj in learning_objectives[:2]:
        if obj not in outcomes:
            outcomes.append(obj)
    return tuple(outcomes[:5])


def derive_common_mistakes(
    *,
    arc_stage: WritingArc,
    genre: str,
    grammar_primary: str,
    task_type: str,
    explicit: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if explicit:
        return explicit
    mistakes: list[str] = [
        f"grammar: Incorrect {_grammar_label(grammar_primary)} usage",
    ]
    if grammar_primary in ("past_simple", "present_perfect"):
        mistakes.append("grammar: Wrong verb tense or form")

    mistakes.append("vocabulary: Word choice too basic or imprecise for the topic")

    if arc_stage in (WritingArc.narrative_writing, WritingArc.opinion_writing, WritingArc.academic_writing):
        mistakes.append("organization: Ideas not grouped into clear paragraphs")
    if task_type in ("complaint", "request", "narrate"):
        mistakes.append("organization: Problem and request not clearly separated")

    if genre in ("formal_email", "business_email", "memo", "cover_letter") or arc_stage in (
        WritingArc.formal_writing,
        WritingArc.professional_writing,
    ):
        mistakes.append("tone: Register too casual for the audience")
    if task_type == "complaint":
        mistakes.append("tone: Language too aggressive or emotional")

    if "email" in genre:
        mistakes.append("formatting: Missing greeting or closing in email")
    if genre in ("essay", "academic_paragraph", "report", "proposal"):
        mistakes.append("formatting: Missing clear opening or closing section")

    return tuple(dict.fromkeys(mistakes))[:6]


_COMPLEXITY_DRIVERS: dict[int, str] = {
    1: "Foundational context — limited scenario with core vocabulary only",
    2: "Guided context — must connect ideas within a familiar situation",
    3: "Extended context — multi-step situation requiring clear organization",
    4: "Real-world stakes — the writing must work for a real audience",
    5: "High-stakes context — precision, tone, and completeness all matter",
}


def derive_difficulty_drivers(
    *,
    context_complexity: ContextComplexity,
    arc_stage: WritingArc,
    official_cefr_label: str,
    vocabulary_primary: tuple[str, ...],
    grammar_primary: str,
    task_type: str,
    expected_output: ExpectedWritingOutput,
    explicit: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if explicit:
        return explicit
    drivers: list[str] = []
    cx = int(context_complexity)

    drivers.append(_COMPLEXITY_DRIVERS.get(cx, f"Context complexity level {cx}"))

    if arc_stage == WritingArc.sentence_building:
        drivers.append("Sentence-level accuracy — each sentence must be clear on its own")
    elif arc_stage == WritingArc.paragraph_writing:
        drivers.append("Paragraph unity — sentences must support one main idea")

    if cx == 3:
        drivers.append("Problem-solving — must explain a situation and next steps")

    if arc_stage in (WritingArc.formal_writing, WritingArc.professional_writing):
        drivers.append("Formal language and professional register")
    if arc_stage == WritingArc.academic_writing:
        drivers.append("Argument structure and supported ideas")
    if arc_stage == WritingArc.opinion_writing:
        drivers.append("Multiple ideas with reasons and examples")

    if len(vocabulary_primary) >= 3:
        drivers.append("Topic-specific vocabulary to use accurately")
    elif vocabulary_primary:
        drivers.append("Choosing accurate words from a focused vocabulary set")

    if grammar_primary in ("past_simple", "present_perfect", "sequencers"):
        drivers.append("Complex timeline — events must be ordered clearly")
    if grammar_primary == "linking_words":
        drivers.append("Cohesion — linking words connect ideas")

    if expected_output in (ExpectedWritingOutput.essay, ExpectedWritingOutput.report):
        drivers.append("Longer response — more content to organize")
    if official_cefr_label in ("B2", "C1", "C2"):
        drivers.append(f"Higher {official_cefr_label} expectations for depth and accuracy")

    if task_type in ("complaint", "proposal", "argue"):
        drivers.append("Must balance clarity with persuasive or diplomatic tone")

    return tuple(dict.fromkeys(drivers))[:6]


def derive_prerequisite_skills(
    *,
    position: int,
    arc_stage: WritingArc,
    grammar_review: str,
    expected_output: ExpectedWritingOutput,
    previous_label: str | None,
    explicit: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if explicit:
        return explicit
    skills: list[str] = []

    if position == 1:
        if arc_stage == WritingArc.sentence_building:
            skills.append("Can write simple sentences about familiar topics")
        elif arc_stage == WritingArc.paragraph_writing:
            skills.append("Can write connected sentences")
        else:
            skills.append("Can write basic sentences in English")
        return tuple(skills)

    if previous_label:
        skills.append(f"Completed prior step: {previous_label}")
    if grammar_review:
        skills.append(f"Knows {_grammar_label(grammar_review)}")

    if arc_stage == WritingArc.paragraph_writing:
        skills.append("Can write a short paragraph")
    if arc_stage in (WritingArc.formal_writing, WritingArc.professional_writing):
        skills.append("Understands email or message structure")
        skills.append("Can write paragraphs with a clear purpose")
    if arc_stage == WritingArc.narrative_writing:
        skills.append("Can sequence events in writing")
    if arc_stage == WritingArc.opinion_writing:
        skills.append("Can state an opinion with at least one reason")
    if arc_stage == WritingArc.academic_writing:
        skills.append("Can organize ideas into paragraphs")
        skills.append("Knows basic connectors (because, however, therefore)")
    if expected_output == ExpectedWritingOutput.email:
        skills.append("Understands email opening and closing conventions")

    return tuple(dict.fromkeys(skills))[:6]


def enrich_node_pedagogy(
    node: WritingKnowledgeChainNode,
    *,
    previous_label: str | None = None,
    learning_outcomes: tuple[str, ...] = (),
    common_mistakes: tuple[str, ...] = (),
    difficulty_drivers: tuple[str, ...] = (),
    prerequisite_skills: tuple[str, ...] = (),
) -> WritingKnowledgeChainNode:
    """Return node with W1.2 pedagogy metadata populated."""
    output = node.expected_output
    return replace(
        node,
        learning_outcomes=derive_learning_outcomes(
            task_type=node.task_type,
            genre=node.genre,
            grammar_primary=node.grammar_focus_primary,
            grammar_secondary=node.grammar_focus_secondary,
            expected_output=output,
            learning_objectives=node.learning_objectives,
            explicit=learning_outcomes,
        ),
        common_mistakes=derive_common_mistakes(
            arc_stage=node.arc_stage,
            genre=node.genre,
            grammar_primary=node.grammar_focus_primary,
            task_type=node.task_type,
            explicit=common_mistakes,
        ),
        difficulty_drivers=derive_difficulty_drivers(
            context_complexity=node.context_complexity,
            arc_stage=node.arc_stage,
            official_cefr_label=node.official_cefr.value,
            vocabulary_primary=node.vocabulary_primary,
            grammar_primary=node.grammar_focus_primary,
            task_type=node.task_type,
            expected_output=output,
            explicit=difficulty_drivers,
        ),
        prerequisite_skills=derive_prerequisite_skills(
            position=node.position,
            arc_stage=node.arc_stage,
            grammar_review=node.grammar_focus_review,
            expected_output=output,
            previous_label=previous_label,
            explicit=prerequisite_skills,
        ),
    )
