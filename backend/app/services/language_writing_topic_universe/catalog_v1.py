"""Writing Topic Universe catalog v1.2 (W1) — complete educational world."""

from __future__ import annotations

from app.services.language_writing.enums import (
    ContextComplexity,
    LexisCategory,
    OfficialWritingCEFR,
    WritingArc,
    WritingGoal,
    WritingTopicId,
)
from app.services.language_writing_knowledge_chain.builder import N, build_linear_chain
from app.services.language_writing_knowledge_chain.types import FutureBranchPoint, WritingKnowledgeChain
from app.services.language_writing_topic_universe.types import TopicComplexityBand, WritingTopicCatalog, WritingTopicNode, WritingUniverseCatalog

CATALOG_VERSION = "1.2.0"

_G = WritingGoal
_A = WritingArc
_C = ContextComplexity
_L = LexisCategory
_CE = OfficialWritingCEFR

# Shorthand goal tuples
_GE = (_G.general_english, _G.daily_communication)
_TR = (_G.travel, _G.general_english, _G.daily_communication)
_BU = (_G.business, _G.job_interview, _G.general_english)
_AC = (_G.academic, _G.ielts, _G.general_english)
_IL = (_G.ielts, _G.academic, _G.general_english)
_CR = (_G.creative_writing, _G.general_english)
_FA = (_G.general_english, _G.daily_communication)


def _topics() -> tuple[WritingTopicNode, ...]:
    specs = (
        (WritingTopicId.travel, "Travel", "Journeys, transport, hotels, and solving travel problems abroad.", (1, 5)),
        (WritingTopicId.education, "Education", "School, university, learning, and academic life.", (1, 4)),
        (WritingTopicId.business, "Business", "Workplace communication, meetings, and professional tasks.", (2, 5)),
        (WritingTopicId.technology, "Technology", "Devices, apps, reviews, and simple technical explanation.", (1, 4)),
        (WritingTopicId.health, "Health", "Wellbeing, symptoms, appointments, and healthy habits.", (1, 4)),
        (WritingTopicId.family, "Family", "Relationships, home life, celebrations, and personal stories.", (1, 3)),
        (WritingTopicId.work, "Work", "Jobs, applications, workplace routines, and career growth.", (2, 5)),
        (WritingTopicId.shopping, "Shopping", "Buying, comparing, returning items, and customer messages.", (1, 4)),
        (WritingTopicId.environment, "Environment", "Nature, pollution, sustainability, and community action.", (2, 5)),
        (WritingTopicId.science, "Science", "Experiments, explanations, and popular science writing.", (2, 5)),
        (WritingTopicId.entertainment, "Entertainment", "Films, music, events, reviews, and recommendations.", (1, 4)),
        (WritingTopicId.culture, "Culture", "Traditions, customs, comparisons, and cultural experiences.", (2, 4)),
        (WritingTopicId.history, "History", "Past events, figures, causes, and historical significance.", (2, 5)),
        (WritingTopicId.food, "Food", "Recipes, restaurants, cuisine, and food culture.", (1, 3)),
        (WritingTopicId.sports, "Sports", "Events, fitness, teams, and personal sports experiences.", (1, 4)),
        (WritingTopicId.daily_life, "Daily Life", "Routines, neighborhoods, habits, and everyday situations.", (1, 3)),
        (WritingTopicId.communication, "Communication", "Messages, announcements, and staying in touch.", (1, 4)),
        (WritingTopicId.services, "Services", "Banks, clinics, government, and customer service.", (2, 5)),
        (WritingTopicId.housing, "Housing", "Renting, repairs, landlords, and describing homes.", (2, 4)),
        (WritingTopicId.society, "Society", "Community issues, volunteering, and civic participation.", (2, 5)),
    )
    return tuple(
        WritingTopicNode(
            topic_id=tid,
            label=label,
            description=desc,
            chain_ids=(),  # populated in build_topic_catalog()
            default_complexity_range=cx,
            vocabulary_domains=(tid.value,),
        )
        for tid, label, desc, cx in specs
    )


def _complexity_bands() -> tuple[TopicComplexityBand, ...]:
    bands: list[TopicComplexityBand] = []
    for topic in _topics():
        lo, hi = topic.default_complexity_range
        for cefr, typical in (
            (_CE.A1, lo),
            (_CE.A2, min(lo + 1, hi)),
            (_CE.B1, min(lo + 2, hi)),
            (_CE.B2, min(lo + 3, hi)),
            (_CE.C1, hi),
        ):
            bands.append(
                TopicComplexityBand(
                    official_cefr=cefr,
                    topic_id=topic.topic_id,
                    min_complexity=_C(lo),
                    max_complexity=_C(hi),
                    typical_complexity=_C(typical),
                )
            )
    return tuple(bands)


def _chain_travel_airport() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="travel_airport_journey",
        topic_id=WritingTopicId.travel,
        label="Airport Journey",
        description="From arrival at the airport to resolving delays and sharing your travel experience.",
        primary_arc=_A.narrative_writing,
        node_specs=(
            N("airport_arrival", "At the Airport", "Learn to describe arriving at an airport and what you see.", cefr=_CE.A1, arc=_A.sentence_building, complexity=_C.familiar, goals=_TR, objectives=("Name airport places", "Use present simple"), grammar="present_simple", seeds=("airport", "gate", "flight"), task="describe", genre="short_note"),
            N("check_in", "Check-in Desk", "Practice explaining who you are and where you are going.", cefr=_CE.A1, arc=_A.paragraph_writing, complexity=_C.everyday, goals=_TR, objectives=("Give personal travel details", "Ask simple questions"), grammar="present_simple", grammar2="questions", seeds=("passport", "ticket", "destination"), task="describe", genre="dialogue_paragraph", carry="At the airport you arrived…"),
            N("security", "Security Check", "Describe a routine process step by step.", cefr=_CE.A2, arc=_A.paragraph_writing, complexity=_C.everyday, goals=_TR, objectives=("Sequence actions", "Use imperatives politely"), grammar="imperatives", grammar2="sequencers", seeds=("security", "belt", "luggage"), task="explain_simple", genre="paragraph"),
            N("delayed_flight", "Delayed Flight", "Explain a travel problem clearly and calmly.", cefr=_CE.A2, arc=_A.narrative_writing, complexity=_C.mild_problem, goals=_TR, objectives=("State a problem", "Give time and reason"), grammar="past_simple", grammar2="because", seeds=("delay", "boarding", "announcement"), task="narrate", genre="narrative", carry="After security…"),
            N("complaint_email", "Complaint Email", "Write a polite email to an airline about a delay.", cefr=_CE.B1, arc=_A.formal_writing, complexity=_C.real_world_stakes, goals=_TR, objectives=("Formal register", "State problem and request"), grammar="past_simple", grammar2="polite_requests", vocab_cats=(_L.core, _L.topic, _L.common_phrases), seeds=("refund", "apologize", "inconvenience"), task="complaint", genre="formal_email", carry="Your flight was delayed…", outcomes=("Write a formal email", "Explain a problem clearly", "Request politely", "Use past simple correctly"), mistakes=("tone: Language too aggressive or emotional", "organization: Problem and request not clearly separated", "formatting: Missing greeting or closing in email"), drivers=("Real-world stakes — the writing must work for a real audience", "Formal language and professional register", "Problem-solving — must explain a situation and next steps"), prerequisites=("Can sequence events in writing", "Knows past simple", "Understands email or message structure")),
            N("refund_request", "Refund Request", "Request compensation with clear facts and a specific ask.", cefr=_CE.B1, arc=_A.formal_writing, complexity=_C.real_world_stakes, goals=_TR, objectives=("Support a request with details", "Use formal closings"), grammar="present_perfect", grammar2="modal_verbs", seeds=("compensation", "booking reference", "resolve"), task="request", genre="formal_email"),
            N("travel_review", "Travel Review", "Share your overall trip experience and recommendation.", cefr=_CE.B2, arc=_A.opinion_writing, complexity=_C.multi_constraint, goals=_TR + (_G.ielts,), objectives=("Balance positives and negatives", "Give a recommendation"), grammar="past_simple", grammar2="linking_words", vocab_cats=(_L.core, _L.topic, _L.collocations), seeds=("overall", "recommend", "worth"), task="review", genre="review", review=("complaint_email",), future=("travel_hotel_stay",)),
        ),
        documented_future_branches=(
            FutureBranchPoint(
                anchor_node_id="check_in",
                branch_label="Trip purpose",
                option_a_chain_id="travel_business_trip",
                option_b_chain_id="travel_family_vacation",
                description=(
                    "Future extension: after check-in, students may follow a Business Trip path "
                    "or a Family Vacation path (not implemented — linear chain continues to security)."
                ),
            ),
        ),
    )


def _chain_travel_hotel() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="travel_hotel_stay",
        topic_id=WritingTopicId.travel,
        label="Hotel Stay",
        description="Handle hotel arrival, room issues, and polite follow-up messages.",
        primary_arc=_A.formal_writing,
        node_specs=(
            N("hotel_arrival", "Hotel Arrival", "Describe checking into a hotel and your first impressions.", cefr=_CE.A2, arc=_A.paragraph_writing, complexity=_C.everyday, goals=_TR, objectives=("Describe a place", "Express likes"), grammar="there_is_are", seeds=("reception", "room", "reservation"), task="describe", genre="paragraph"),
            N("room_issue", "Room Problem", "Explain a problem with your room clearly.", cefr=_CE.A2, arc=_A.narrative_writing, complexity=_C.mild_problem, goals=_TR, objectives=("Describe a defect", "Use polite tone"), grammar="present_continuous", grammar2="there_is_are", seeds=("noise", "broken", "maintenance"), task="complaint", genre="message"),
            N("service_request", "Service Request", "Request housekeeping or a room change professionally.", cefr=_CE.B1, arc=_A.formal_writing, complexity=_C.real_world_stakes, goals=_TR, objectives=("Make a formal request", "Offer alternatives"), grammar="modal_verbs", grammar2="polite_requests", seeds=("housekeeping", "available", "confirm"), task="request", genre="formal_email"),
            N("thank_you_note", "Thank You Note", "Write a short thank-you after good service.", cefr=_CE.B1, arc=_A.formal_writing, complexity=_C.everyday, goals=_TR, objectives=("Express gratitude", "Mention specific help"), grammar="past_simple", seeds=("appreciate", "helpful", "comfortable"), task="thank", genre="short_email"),
        ),
    )


def _chain_education_school() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="education_school_life",
        topic_id=WritingTopicId.education,
        label="School Life",
        description="From introducing yourself in class to communicating with teachers.",
        primary_arc=_A.paragraph_writing,
        node_specs=(
            N("class_intro", "Introduce Yourself", "Write a short introduction for a new class.", cefr=_CE.A1, arc=_A.sentence_building, complexity=_C.familiar, goals=_FA + (_G.academic,), objectives=("Give basic personal info",), grammar="present_simple", seeds=("classmate", "study", "country"), task="describe", genre="short_note"),
            N("describe_class", "Describe Your Class", "Describe your classroom, subjects, and classmates.", cefr=_CE.A1, arc=_A.paragraph_writing, complexity=_C.familiar, goals=_AC, objectives=("Use adjectives", "Simple present for routines"), grammar="present_simple", grammar2="adjectives", seeds=("subject", "teacher", "schedule"), task="describe", genre="paragraph"),
            N("homework_excuse", "Explain Missing Homework", "Politely explain why homework was late.", cefr=_CE.A2, arc=_A.narrative_writing, complexity=_C.mild_problem, goals=_AC, objectives=("Give a brief reason", "Apologize appropriately"), grammar="past_simple", grammar2="because", seeds=("deadline", "forgot", "sorry"), task="explain_simple", genre="email_short"),
            N("ask_teacher", "Ask Your Teacher", "Write a clear question about an assignment.", cefr=_CE.A2, arc=_A.formal_writing, complexity=_C.everyday, goals=_AC, objectives=("Ask focused questions", "Use polite forms"), grammar="questions", grammar2="modal_verbs", seeds=("assignment", "clarify", "submit"), task="inquiry", genre="formal_email"),
        ),
    )


def _chain_education_university() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="education_university_path",
        topic_id=WritingTopicId.education,
        label="University Path",
        description="Express academic interests and write application-style paragraphs.",
        primary_arc=_A.academic_writing,
        node_specs=(
            N("course_interest", "Course Interest", "Explain why a subject interests you.", cefr=_CE.B1, arc=_A.opinion_writing, complexity=_C.everyday, goals=_AC + (_G.ielts,), objectives=("State reasons", "Use linking words"), grammar="present_simple", grammar2="because", vocab_cats=(_L.academic, _L.core), seeds=("major", "interest", "career"), task="opinion", genre="paragraph"),
            N("application_paragraph", "Application Paragraph", "Write a focused paragraph about your background and goals.", cefr=_CE.B1, arc=_A.academic_writing, complexity=_C.mild_problem, goals=_AC, objectives=("Organize one clear paragraph", "Formal tone"), grammar="present_perfect", grammar2="future_plans", vocab_cats=(_L.academic, _L.collocations), seeds=("qualification", "motivated", "goal"), task="application", genre="academic_paragraph"),
            N("study_plan", "Study Plan", "Outline how you will prepare for university study.", cefr=_CE.B2, arc=_A.academic_writing, complexity=_C.real_world_stakes, goals=_AC + (_G.ielts,), objectives=("Sequence future actions", "Use formal vocabulary"), grammar="future_forms", grammar2="sequencers", vocab_cats=(_L.academic, _L.collocations), seeds=("schedule", "research", "deadline"), task="plan", genre="essay_outline"),
        ),
    )


def _chain_business_email() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="business_email_flow",
        topic_id=WritingTopicId.business,
        label="Business Email Flow",
        description="Professional email from introduction through follow-up and summary.",
        primary_arc=_A.professional_writing,
        node_specs=(
            N("intro_email", "Introduction Email", "Introduce yourself professionally to a new contact.", cefr=_CE.A2, arc=_A.paragraph_writing, complexity=_C.everyday, goals=_BU, objectives=("Professional greeting", "Clear purpose"), grammar="present_simple", vocab_cats=(_L.business, _L.common_phrases), seeds=("colleague", "pleased", "connect"), task="introduce", genre="business_email"),
            N("meeting_request", "Meeting Request", "Request a meeting with times and agenda.", cefr=_CE.B1, arc=_A.professional_writing, complexity=_C.mild_problem, goals=_BU, objectives=("Propose times", "State agenda"), grammar="modal_verbs", grammar2="polite_requests", vocab_cats=(_L.business, _L.collocations), seeds=("schedule", "agenda", "available"), task="request", genre="business_email"),
            N("follow_up", "Follow-up Email", "Follow up politely when you have not received a reply.", cefr=_CE.B1, arc=_A.professional_writing, complexity=_C.real_world_stakes, goals=_BU, objectives=("Reference prior message", "Maintain tone"), grammar="present_perfect", grammar2="past_simple", seeds=("follow up", "previous", "confirm"), task="follow_up", genre="business_email"),
            N("short_report", "Short Report", "Summarize a small project outcome for your team.", cefr=_CE.B2, arc=_A.professional_writing, complexity=_C.multi_constraint, goals=_BU, objectives=("Report structure", "Objective tone"), grammar="passive_voice", grammar2="past_simple", vocab_cats=(_L.business, _L.academic), seeds=("outcome", "recommend", "summary"), task="report", genre="report"),
        ),
    )


def _chain_business_proposal() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="business_proposal",
        topic_id=WritingTopicId.business,
        label="Business Proposal",
        description="Identify a problem and propose a structured business solution.",
        primary_arc=_A.professional_writing,
        node_specs=(
            N("problem_statement", "Problem Statement", "Describe a workplace problem objectively.", cefr=_CE.B1, arc=_A.formal_writing, complexity=_C.mild_problem, goals=_BU, objectives=("Neutral tone", "Clear facts"), grammar="present_simple", vocab_cats=(_L.business, _L.academic), seeds=("issue", "impact", "currently"), task="describe", genre="memo"),
            N("solution_proposal", "Solution Proposal", "Propose a solution with benefits.", cefr=_CE.B2, arc=_A.professional_writing, complexity=_C.real_world_stakes, goals=_BU, objectives=("Persuade professionally", "Use evidence"), grammar="modal_verbs", grammar2="conditionals", vocab_cats=(_L.business, _L.collocations), seeds=("proposal", "benefit", "implement"), task="proposal", genre="proposal"),
            N("executive_summary", "Executive Summary", "Write a concise summary for decision-makers.", cefr=_CE.C1, arc=_A.professional_writing, complexity=_C.multi_constraint, goals=_BU, objectives=("Concision", "Key points only"), grammar="passive_voice", grammar2="nominalization", vocab_cats=(_L.business, _L.academic), seeds=("overview", "conclusion", "stakeholder"), task="summary", genre="executive_summary"),
        ),
    )


def _chain_family_intro() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="family_introductions",
        topic_id=WritingTopicId.family,
        label="Family Introductions",
        description="Build from self-description to writing about family members and events.",
        primary_arc=_A.narrative_writing,
        node_specs=(
            N("myself", "About Me", "Write sentences about yourself for someone new.", cefr=_CE.A1, arc=_A.sentence_building, complexity=_C.familiar, goals=_FA, objectives=("Basic self-description",), grammar="present_simple", seeds=("name", "age", "live"), task="describe", genre="short_note"),
            N("parents", "My Parents", "Describe your parents and what they do.", cefr=_CE.A1, arc=_A.paragraph_writing, complexity=_C.familiar, goals=_FA, objectives=("Describe people", "Possessives"), grammar="present_simple", grammar2="possessives", seeds=("mother", "father", "work"), task="describe", genre="paragraph", carry="You wrote about yourself…"),
            N("siblings", "Brothers and Sisters", "Write about siblings and compare personalities.", cefr=_CE.A2, arc=_A.paragraph_writing, complexity=_C.everyday, goals=_FA, objectives=("Compare people", "Use and/but"), grammar="present_simple", grammar2="comparatives", seeds=("brother", "sister", "older"), task="describe", genre="paragraph"),
            N("family_event", "A Family Event", "Narrate a memorable family celebration.", cefr=_CE.A2, arc=_A.narrative_writing, complexity=_C.everyday, goals=_FA + (_G.creative_writing,), objectives=("Past narrative", "Sequence events"), grammar="past_simple", grammar2="sequencers", seeds=("celebration", "together", "remember"), task="narrate", genre="narrative"),
        ),
    )


def _chain_family_celebration() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="family_celebration",
        topic_id=WritingTopicId.family,
        label="Family Celebration",
        description="Invite, describe, and thank people around a family event.",
        primary_arc=_A.formal_writing,
        node_specs=(
            N("invitation", "Family Invitation", "Invite someone to a family gathering.", cefr=_CE.A2, arc=_A.paragraph_writing, complexity=_C.everyday, goals=_FA, objectives=("Give event details", "Warm tone"), grammar="future_forms", seeds=("invite", "Saturday", "celebrate"), task="invite", genre="message"),
            N("event_description", "Describe the Event", "Describe what happened at the celebration.", cefr=_CE.A2, arc=_A.narrative_writing, complexity=_C.everyday, goals=_FA, objectives=("Past narrative", "Sensory detail"), grammar="past_simple", seeds=("delicious", "music", "happy"), task="narrate", genre="narrative"),
            N("thank_you", "Thank You Message", "Thank guests or hosts after an event.", cefr=_CE.B1, arc=_A.formal_writing, complexity=_C.everyday, goals=_FA, objectives=("Express gratitude", "Mention specifics"), grammar="past_simple", grammar2="polite_closings", seeds=("grateful", "wonderful", "host"), task="thank", genre="short_email"),
        ),
    )


def _chain_work_job() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="work_job_search",
        topic_id=WritingTopicId.work,
        label="Job Search",
        description="From self-introduction to cover letter and interview follow-up.",
        primary_arc=_A.professional_writing,
        node_specs=(
            N("work_self_intro", "Professional Self-intro", "Introduce your skills and experience briefly.", cefr=_CE.A2, arc=_A.paragraph_writing, complexity=_C.everyday, goals=(_G.job_interview, _G.business), objectives=("Highlight skills", "Professional tone"), grammar="present_simple", vocab_cats=(_L.business, _L.core), seeds=("experience", "skill", "role"), task="introduce", genre="paragraph"),
            N("cover_letter", "Cover Letter", "Write a targeted cover letter paragraph.", cefr=_CE.B1, arc=_A.professional_writing, complexity=_C.real_world_stakes, goals=(_G.job_interview, _G.business), objectives=("Match job requirements", "Formal structure"), grammar="present_perfect", grammar2="modal_verbs", vocab_cats=(_L.business, _L.collocations), seeds=("qualified", "position", "apply"), task="application", genre="cover_letter"),
            N("interview_thanks", "Interview Thank-you", "Thank an employer after an interview.", cefr=_CE.B1, arc=_A.professional_writing, complexity=_C.mild_problem, goals=(_G.job_interview,), objectives=("Professional gratitude", "Reaffirm interest"), grammar="past_simple", seeds=("interview", "opportunity", "look forward"), task="thank", genre="business_email"),
        ),
    )


def _chain_work_workplace() -> WritingKnowledgeChain:
    return build_linear_chain(
        chain_id="work_workplace",
        topic_id=WritingTopicId.work,
        label="Workplace Routine",
        description="Describe daily work, report issues, and request time off.",
        primary_arc=_A.professional_writing,
        node_specs=(
            N("daily_tasks", "Daily Tasks", "Describe your typical workday.", cefr=_CE.A2, arc=_A.paragraph_writing, complexity=_C.everyday, goals=(_G.business, _G.general_english), objectives=("Routine present simple",), grammar="present_simple", vocab_cats=(_L.business, _L.core), seeds=("shift", "task", "team"), task="describe", genre="paragraph"),
            N("report_issue", "Report a Problem", "Report a workplace issue to a supervisor.", cefr=_CE.B1, arc=_A.formal_writing, complexity=_C.mild_problem, goals=(_G.business,), objectives=("Objective problem report",), grammar="past_simple", grammar2="passive_voice", seeds=("equipment", "safety", "report"), task="report", genre="memo"),
            N("time_off", "Request Time Off", "Request leave with dates and reason.", cefr=_CE.B1, arc=_A.professional_writing, complexity=_C.real_world_stakes, goals=(_G.business,), objectives=("Clear dates", "Polite request"), grammar="future_forms", grammar2="modal_verbs", seeds=("leave", "available", "cover"), task="request", genre="business_email"),
        ),
    )


def _compact_chain(
    topic: WritingTopicId,
    chain_id: str,
    label: str,
    description: str,
    primary_arc: WritingArc,
    steps: tuple[tuple[str, str, str, OfficialWritingCEFR, WritingArc, ContextComplexity, tuple[WritingGoal, ...], str, str], ...],
) -> WritingKnowledgeChain:
    """Compact 5-tuple steps: (id, label, why, cefr, arc, complexity, goals, grammar, task)."""
    specs = tuple(
        N(
            sid,
            slabel,
            why,
            cefr=cefr,
            arc=arc,
            complexity=cx,
            goals=goals,
            objectives=(f"Practice {slabel.lower()}",),
            grammar=grammar,
            seeds=(grammar.replace("_", " "), sid.replace("_", " ")),
            task=task,
            genre="paragraph" if arc != _A.sentence_building else "short_note",
        )
        for sid, slabel, why, cefr, arc, cx, goals, grammar, task in steps
    )
    return build_linear_chain(
        chain_id=chain_id,
        topic_id=topic,
        label=label,
        description=description,
        primary_arc=primary_arc,
        node_specs=specs,
    )


def _chain_technology() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.technology,
        "technology_product_review",
        "Product Review",
        "Describe a device, give pros and cons, and recommend.",
        _A.opinion_writing,
        (
            ("device_desc", "Describe a Device", "Describe a phone or laptop you use.", _CE.A2, _A.paragraph_writing, _C.familiar, _GE, "present_simple", "describe"),
            ("pros_cons", "Pros and Cons", "Compare advantages and disadvantages.", _CE.B1, _A.opinion_writing, _C.everyday, _GE, "comparatives", "compare"),
            ("recommend", "Recommendation", "Recommend the product to a friend.", _CE.B1, _A.opinion_writing, _C.mild_problem, _GE, "modal_verbs", "recommend"),
        ),
    )


def _chain_technology_howto() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.technology,
        "technology_how_to",
        "How-to Guide",
        "Write simple instructions and troubleshoot a common problem.",
        _A.paragraph_writing,
        (
            ("instructions", "Simple Instructions", "Explain how to use an app step by step.", _CE.A2, _A.paragraph_writing, _C.everyday, _GE, "imperatives", "explain_simple"),
            ("troubleshoot", "Troubleshooting", "Help someone fix a common tech problem.", _CE.B1, _A.formal_writing, _C.mild_problem, _GE, "conditional_first", "guide"),
        ),
    )


def _chain_health() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.health,
        "health_symptoms",
        "Health Visit",
        "Describe symptoms, explain a doctor visit, and note lifestyle advice.",
        _A.narrative_writing,
        (
            ("symptoms", "Describe Symptoms", "Explain how you feel using simple language.", _CE.A2, _A.paragraph_writing, _C.mild_problem, _GE, "present_simple", "describe"),
            ("doctor_visit", "Doctor Visit", "Recount what happened at the clinic.", _CE.A2, _A.narrative_writing, _C.everyday, _GE, "past_simple", "narrate"),
            ("lifestyle", "Healthy Habits", "Write advice for a healthier routine.", _CE.B1, _A.opinion_writing, _C.everyday, _GE, "imperatives", "advise"),
        ),
    )


def _chain_health_appt() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.health,
        "health_appointment",
        "Medical Appointment",
        "Book, reschedule, and thank a clinic.",
        _A.formal_writing,
        (
            ("book", "Book Appointment", "Request an appointment with reason.", _CE.A2, _A.formal_writing, _C.everyday, _GE, "modal_verbs", "request"),
            ("reschedule", "Reschedule", "Ask to change your appointment politely.", _CE.B1, _A.formal_writing, _C.mild_problem, _GE, "polite_requests", "request"),
            ("thank_clinic", "Thank the Clinic", "Thank staff after a good visit.", _CE.B1, _A.formal_writing, _C.everyday, _GE, "past_simple", "thank"),
        ),
    )


def _chain_shopping() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.shopping,
        "shopping_online",
        "Online Shopping",
        "Search, compare, purchase, and return items online.",
        _A.paragraph_writing,
        (
            ("search", "Find a Product", "Describe what you want to buy.", _CE.A2, _A.paragraph_writing, _C.familiar, _GE, "present_simple", "describe"),
            ("compare", "Compare Options", "Compare two products.", _CE.A2, _A.opinion_writing, _C.everyday, _GE, "comparatives", "compare"),
            ("return", "Return Request", "Write to return a defective item.", _CE.B1, _A.formal_writing, _C.mild_problem, _GE, "past_simple", "complaint"),
        ),
    )


def _chain_shopping_complaint() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.shopping,
        "shopping_complaint",
        "Shopping Complaint",
        "Complain about a product and seek resolution.",
        _A.formal_writing,
        (
            ("defective", "Defective Item", "Describe what is wrong with a purchase.", _CE.A2, _A.narrative_writing, _C.mild_problem, _GE, "past_simple", "describe"),
            ("complaint", "Write a Complaint", "State the problem and desired solution.", _CE.B1, _A.formal_writing, _C.real_world_stakes, _GE, "modal_verbs", "complaint"),
            ("resolution", "Resolution Follow-up", "Confirm whether the issue was resolved.", _CE.B1, _A.formal_writing, _C.everyday, _GE, "present_perfect", "follow_up"),
        ),
    )


def _chain_environment() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.environment,
        "environment_local",
        "Local Environment",
        "Describe your area and habits that help the planet.",
        _A.opinion_writing,
        (
            ("describe_park", "Describe a Green Place", "Describe a park or garden.", _CE.A2, _A.paragraph_writing, _C.familiar, _GE, "there_is_are", "describe"),
            ("recycling", "Recycling Habits", "Explain your recycling routine.", _CE.A2, _A.paragraph_writing, _C.everyday, _GE, "present_simple", "explain_simple"),
            ("pollution_opinion", "Pollution Opinion", "Give your view on local pollution.", _CE.B1, _A.opinion_writing, _C.mild_problem, _GE, "because", "opinion"),
        ),
    )


def _chain_environment_global() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.environment,
        "environment_global",
        "Global Environment",
        "Explain climate issues and propose action.",
        _A.academic_writing,
        (
            ("climate_facts", "Climate Facts", "Summarize basic climate facts.", _CE.B1, _A.paragraph_writing, _C.everyday, _AC, "present_simple", "summary"),
            ("problem_solution", "Problem and Solution", "Present an environmental problem and solution.", _CE.B2, _A.academic_writing, _C.real_world_stakes, _AC, "cause_effect", "essay"),
            ("call_to_action", "Call to Action", "Persuade readers to take action.", _CE.B2, _A.opinion_writing, _C.multi_constraint, _AC, "modal_verbs", "persuade"),
        ),
    )


def _chain_science() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.science,
        "science_experiment",
        "Simple Experiment",
        "Report a classroom experiment from hypothesis to results.",
        _A.academic_writing,
        (
            ("hypothesis", "Hypothesis", "State what you expect to happen.", _CE.B1, _A.paragraph_writing, _C.everyday, _AC, "future_forms", "state"),
            ("method", "Method", "Describe the steps you followed.", _CE.B1, _A.paragraph_writing, _C.everyday, _AC, "past_simple", "explain_simple"),
            ("results", "Results", "Report what happened and why it matters.", _CE.B2, _A.academic_writing, _C.mild_problem, _AC, "past_simple", "report"),
        ),
    )


def _chain_science_explainer() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.science,
        "science_explainer",
        "Science Explainer",
        "Explain a science concept for a general reader.",
        _A.academic_writing,
        (
            ("concept", "Simple Concept", "Explain one science idea clearly.", _CE.B1, _A.paragraph_writing, _C.everyday, _AC, "present_simple", "explain"),
            ("article", "Popular Article", "Write a short popular science paragraph.", _CE.B2, _A.academic_writing, _C.mild_problem, _AC, "passive_voice", "article"),
        ),
    )


def _chain_entertainment() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.entertainment,
        "entertainment_review",
        "Entertainment Review",
        "Summarize and review a film or show.",
        _A.opinion_writing,
        (
            ("summary", "Plot Summary", "Summarize a story without spoilers.", _CE.A2, _A.paragraph_writing, _C.familiar, _GE + (_G.creative_writing,), "past_simple", "summary"),
            ("review", "Write a Review", "Give your opinion with reasons.", _CE.B1, _A.opinion_writing, _C.everyday, _GE, "because", "review"),
            ("recommend", "Recommend to a Friend", "Recommend what to watch.", _CE.B1, _A.opinion_writing, _C.everyday, _GE, "comparatives", "recommend"),
        ),
    )


def _chain_entertainment_event() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.entertainment,
        "entertainment_event",
        "Live Event",
        "Invite someone and describe a live event.",
        _A.narrative_writing,
        (
            ("invite", "Event Invite", "Invite a friend to an event.", _CE.A2, _A.paragraph_writing, _C.everyday, _GE, "future_forms", "invite"),
            ("experience", "Event Experience", "Describe the atmosphere and highlights.", _CE.A2, _A.narrative_writing, _C.everyday, _CR, "past_simple", "narrate"),
        ),
    )


def _chain_culture() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.culture,
        "culture_tradition",
        "Traditions",
        "Describe a tradition and compare cultures.",
        _A.narrative_writing,
        (
            ("holiday", "Describe a Holiday", "Describe how a holiday is celebrated.", _CE.A2, _A.narrative_writing, _C.familiar, _GE, "present_simple", "describe"),
            ("compare", "Compare Cultures", "Compare two cultural customs.", _CE.B1, _A.opinion_writing, _C.mild_problem, _AC, "comparatives", "compare"),
        ),
    )


def _chain_culture_visit() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.culture,
        "culture_visit",
        "Cultural Visit",
        "Write about visiting a museum or festival.",
        _A.narrative_writing,
        (
            ("museum", "Museum Visit", "Describe what you saw and learned.", _CE.A2, _A.narrative_writing, _C.everyday, _GE, "past_simple", "narrate"),
            ("reflection", "Reflective Paragraph", "Explain what the visit meant to you.", _CE.B1, _A.opinion_writing, _C.mild_problem, _AC, "past_simple", "reflect"),
        ),
    )


def _chain_history() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.history,
        "history_biography",
        "Historical Figure",
        "Write about a person and an event they shaped.",
        _A.academic_writing,
        (
            ("figure", "Historical Figure", "Introduce an important person.", _CE.B1, _A.paragraph_writing, _C.everyday, _AC, "past_simple", "describe"),
            ("event", "Historical Event", "Narrate a key event.", _CE.B1, _A.narrative_writing, _C.mild_problem, _AC, "past_simple", "narrate"),
            ("significance", "Why It Matters", "Explain the event's significance.", _CE.B2, _A.academic_writing, _C.real_world_stakes, _AC, "cause_effect", "essay"),
        ),
    )


def _chain_history_essay() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.history,
        "history_argument",
        "Historical Argument",
        "Build a short cause-effect historical argument.",
        _A.academic_writing,
        (
            ("causes", "Causes", "Explain causes of a historical change.", _CE.B2, _A.academic_writing, _C.mild_problem, _AC, "cause_effect", "essay"),
            ("argument", "Historical Argument", "Argue why an event was important.", _CE.C1, _A.academic_writing, _C.multi_constraint, _IL, "passive_voice", "argue"),
        ),
    )


def _chain_food() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.food,
        "food_recipe",
        "Recipe Writing",
        "List ingredients and write cooking steps.",
        _A.paragraph_writing,
        (
            ("ingredients", "Ingredients List", "List ingredients for a simple dish.", _CE.A1, _A.sentence_building, _C.familiar, _GE, "there_is_are", "list"),
            ("steps", "Cooking Steps", "Write ordered instructions.", _CE.A2, _A.paragraph_writing, _C.everyday, _GE, "imperatives", "explain_simple"),
            ("dish_desc", "Describe the Dish", "Describe taste and appearance.", _CE.A2, _A.paragraph_writing, _C.familiar, _GE, "adjectives", "describe"),
        ),
    )


def _chain_food_review() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.food,
        "food_restaurant_review",
        "Restaurant Review",
        "Review a meal and recommend a restaurant.",
        _A.opinion_writing,
        (
            ("visit", "Restaurant Visit", "Describe your visit.", _CE.A2, _A.narrative_writing, _C.everyday, _GE, "past_simple", "narrate"),
            ("review", "Food Review", "Review the food and service.", _CE.B1, _A.opinion_writing, _C.everyday, _GE, "because", "review"),
            ("recommend", "Recommendation", "Recommend the restaurant.", _CE.B1, _A.opinion_writing, _C.mild_problem, _GE, "superlatives", "recommend"),
        ),
    )


def _chain_sports() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.sports,
        "sports_event",
        "Sports Event",
        "Report a match and share your opinion.",
        _A.narrative_writing,
        (
            ("match", "Match Description", "Describe a game you watched.", _CE.A2, _A.narrative_writing, _C.familiar, _GE, "past_simple", "narrate"),
            ("player", "Player Profile", "Write about a player you admire.", _CE.A2, _A.paragraph_writing, _C.everyday, _GE, "present_simple", "describe"),
            ("opinion", "Sports Opinion", "Argue who deserved to win.", _CE.B1, _A.opinion_writing, _C.mild_problem, _GE, "because", "opinion"),
        ),
    )


def _chain_sports_fitness() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.sports,
        "sports_fitness",
        "Fitness Goals",
        "Describe routines and set fitness goals.",
        _A.paragraph_writing,
        (
            ("routine", "Training Routine", "Describe your exercise routine.", _CE.A2, _A.paragraph_writing, _C.familiar, _GE, "present_simple", "describe"),
            ("goals", "Fitness Goals", "Write your goals for the next month.", _CE.B1, _A.opinion_writing, _C.everyday, _GE, "future_forms", "plan"),
        ),
    )


def _chain_daily_life() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.daily_life,
        "daily_routine",
        "Daily Routine",
        "Write about mornings, weekends, and changing habits.",
        _A.paragraph_writing,
        (
            ("morning", "Morning Routine", "Describe your morning.", _CE.A1, _A.sentence_building, _C.familiar, (_G.daily_communication, _G.general_english), "present_simple", "describe"),
            ("weekend", "Weekend Activities", "Describe what you do on weekends.", _CE.A2, _A.paragraph_writing, _C.familiar, (_G.daily_communication,), "present_simple", "describe"),
            ("habit_change", "Change a Habit", "Explain a habit you want to change.", _CE.A2, _A.opinion_writing, _C.everyday, (_G.daily_communication,), "future_forms", "plan"),
        ),
    )


def _chain_daily_neighborhood() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.daily_life,
        "daily_neighborhood",
        "My Neighborhood",
        "Describe your area and suggest a local improvement.",
        _A.opinion_writing,
        (
            ("area", "Describe the Area", "Describe where you live.", _CE.A2, _A.paragraph_writing, _C.familiar, (_G.daily_communication,), "there_is_are", "describe"),
            ("problem", "Local Problem", "Describe a problem in your neighborhood.", _CE.A2, _A.narrative_writing, _C.mild_problem, (_G.daily_communication,), "present_simple", "describe"),
            ("suggestion", "Suggest Improvement", "Propose a solution for the community.", _CE.B1, _A.opinion_writing, _C.mild_problem, (_G.daily_communication,), "modal_verbs", "propose"),
        ),
    )


def _chain_communication() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.communication,
        "communication_messages",
        "Everyday Messages",
        "Write informal and semi-formal messages.",
        _A.formal_writing,
        (
            ("text_friend", "Message a Friend", "Write a casual message to a friend.", _CE.A1, _A.sentence_building, _C.familiar, (_G.daily_communication,), "present_continuous", "message"),
            ("formal_message", "Formal Message", "Write a polite message to a neighbor.", _CE.A2, _A.formal_writing, _C.everyday, (_G.daily_communication,), "polite_requests", "message"),
            ("announcement", "Group Announcement", "Inform a group about a change.", _CE.B1, _A.formal_writing, _C.mild_problem, (_G.daily_communication, _G.business), "future_forms", "announce"),
        ),
    )


def _chain_communication_social() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.communication,
        "communication_online",
        "Online Communication",
        "Introduce yourself online and respond to news.",
        _A.paragraph_writing,
        (
            ("online_intro", "Online Introduction", "Introduce yourself in an online group.", _CE.A2, _A.paragraph_writing, _C.everyday, (_G.daily_communication,), "present_simple", "introduce"),
            ("respond_news", "Respond to News", "Share your reaction to a news item.", _CE.B1, _A.opinion_writing, _C.mild_problem, (_G.daily_communication, _G.general_english), "past_simple", "respond"),
        ),
    )


def _chain_services() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.services,
        "services_bank",
        "Bank Services",
        "Handle basic banking messages.",
        _A.formal_writing,
        (
            ("open_account", "Open an Account", "Ask about opening a bank account.", _CE.B1, _A.formal_writing, _C.mild_problem, _GE, "modal_verbs", "inquiry"),
            ("bank_problem", "Report a Problem", "Report an issue with your account.", _CE.B1, _A.formal_writing, _C.real_world_stakes, _GE, "past_simple", "complaint"),
            ("resolution", "Resolution Message", "Confirm a banking issue was fixed.", _CE.B2, _A.formal_writing, _C.mild_problem, _GE, "present_perfect", "confirm"),
        ),
    )


def _chain_services_gov() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.services,
        "services_government",
        "Government Services",
        "Book appointments and request documents.",
        _A.formal_writing,
        (
            ("appointment", "Book Appointment", "Request a government appointment.", _CE.B1, _A.formal_writing, _C.mild_problem, _GE, "polite_requests", "request"),
            ("document", "Document Request", "Request a document or certificate.", _CE.B1, _A.formal_writing, _C.real_world_stakes, _GE, "modal_verbs", "request"),
            ("follow_up", "Follow-up", "Follow up on your application.", _CE.B2, _A.formal_writing, _C.real_world_stakes, _GE, "present_perfect", "follow_up"),
        ),
    )


def _chain_housing() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.housing,
        "housing_search",
        "Finding Housing",
        "Describe housing needs and contact a landlord.",
        _A.formal_writing,
        (
            ("room_desc", "Describe a Room", "Describe your ideal room or flat.", _CE.A2, _A.paragraph_writing, _C.familiar, _GE, "there_is_are", "describe"),
            ("rental_inquiry", "Rental Inquiry", "Ask about a rental listing.", _CE.B1, _A.formal_writing, _C.mild_problem, _GE, "questions", "inquiry"),
            ("landlord_msg", "Message to Landlord", "Write about a tenancy question.", _CE.B1, _A.formal_writing, _C.real_world_stakes, _GE, "polite_requests", "email"),
        ),
    )


def _chain_housing_maintenance() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.housing,
        "housing_maintenance",
        "Home Maintenance",
        "Report repairs and ask about your lease.",
        _A.formal_writing,
        (
            ("report_repair", "Report a Repair", "Explain a repair needed at home.", _CE.B1, _A.formal_writing, _C.mild_problem, _GE, "present_continuous", "complaint"),
            ("follow_up_repair", "Repair Follow-up", "Follow up on an unresolved repair.", _CE.B1, _A.formal_writing, _C.real_world_stakes, _GE, "past_simple", "follow_up"),
            ("lease_question", "Lease Question", "Ask a question about your contract.", _CE.B2, _A.formal_writing, _C.real_world_stakes, _GE, "modal_verbs", "inquiry"),
        ),
    )


def _chain_society() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.society,
        "society_community",
        "Community Life",
        "Write about community events and volunteering.",
        _A.opinion_writing,
        (
            ("event", "Community Event", "Describe a local event.", _CE.A2, _A.narrative_writing, _C.everyday, _GE, "past_simple", "narrate"),
            ("volunteer", "Volunteer Appeal", "Encourage others to volunteer.", _CE.B1, _A.opinion_writing, _C.mild_problem, _GE, "imperatives", "persuade"),
        ),
    )


def _chain_society_issue() -> WritingKnowledgeChain:
    return _compact_chain(
        WritingTopicId.society,
        "society_issue",
        "Social Issue",
        "Describe a community problem and propose change.",
        _A.academic_writing,
        (
            ("describe_issue", "Describe the Issue", "Explain a social problem clearly.", _CE.B1, _A.paragraph_writing, _C.mild_problem, _AC, "present_simple", "describe"),
            ("opinion", "Your View", "Give your opinion with reasons.", _CE.B1, _A.opinion_writing, _C.mild_problem, _AC, "because", "opinion"),
            ("proposal", "Proposed Solution", "Propose a practical community solution.", _CE.B2, _A.academic_writing, _C.real_world_stakes, _AC, "modal_verbs", "propose"),
        ),
    )


def _all_chains() -> tuple[WritingKnowledgeChain, ...]:
    builders = (
        _chain_travel_airport,
        _chain_travel_hotel,
        _chain_education_school,
        _chain_education_university,
        _chain_business_email,
        _chain_business_proposal,
        _chain_family_intro,
        _chain_family_celebration,
        _chain_work_job,
        _chain_work_workplace,
        _chain_technology,
        _chain_technology_howto,
        _chain_health,
        _chain_health_appt,
        _chain_shopping,
        _chain_shopping_complaint,
        _chain_environment,
        _chain_environment_global,
        _chain_science,
        _chain_science_explainer,
        _chain_entertainment,
        _chain_entertainment_event,
        _chain_culture,
        _chain_culture_visit,
        _chain_history,
        _chain_history_essay,
        _chain_food,
        _chain_food_review,
        _chain_sports,
        _chain_sports_fitness,
        _chain_daily_life,
        _chain_daily_neighborhood,
        _chain_communication,
        _chain_communication_social,
        _chain_services,
        _chain_services_gov,
        _chain_housing,
        _chain_housing_maintenance,
        _chain_society,
        _chain_society_issue,
    )
    return tuple(b() for b in builders)


def build_topic_catalog() -> WritingTopicCatalog:
    topics = _topics()
    # Attach chain ids from built chains
    chains = _all_chains()
    chain_ids_by_topic: dict[WritingTopicId, list[str]] = {}
    for c in chains:
        chain_ids_by_topic.setdefault(c.topic_id, []).append(c.chain_id)
    topics = tuple(
        WritingTopicNode(
            topic_id=t.topic_id,
            label=t.label,
            description=t.description,
            chain_ids=tuple(chain_ids_by_topic.get(t.topic_id, t.chain_ids)),
            default_complexity_range=t.default_complexity_range,
            vocabulary_domains=t.vocabulary_domains,
        )
        for t in topics
    )
    return WritingTopicCatalog(
        catalog_version=CATALOG_VERSION,
        topics=topics,
        complexity_bands=_complexity_bands(),
    )


def build_universe_catalog() -> WritingUniverseCatalog:
    return WritingUniverseCatalog(
        catalog_version=CATALOG_VERSION,
        topics=build_topic_catalog().topics,
        chains=_all_chains(),
    )
