"""Curriculum Progression Graph catalog — ordered speaking journey A1→C1."""

from __future__ import annotations

from app.services.language_speaking_curriculum_engine.progression_types import (
    CaseVariant,
    MicroSkillNode,
)


def _cv(
    case_id: str,
    title: str,
    scenario: str,
    world: str,
    characters: tuple[str, ...],
    category: str,
    theme: str = "",
    emotion: str = "",
) -> CaseVariant:
    return CaseVariant(
        case_id=case_id,
        title_hint=title,
        scenario_type=scenario,
        story_world=world,
        character_hints=characters,
        case_category=category,
        theme_key=theme or case_id,
        emotional_theme=emotion,
    )


def _node(
    *,
    node_id: str,
    label: str,
    cluster_id: str,
    cluster_label: str,
    domain_id: str,
    domain_label: str,
    parent_id: str | None,
    children_ids: tuple[str, ...],
    prerequisite_ids: tuple[str, ...],
    recommended_next_ids: tuple[str, ...],
    difficulty: int,
    cefr_min: str,
    cefr_max: str,
    enter: float,
    advance: float,
    micro_skills: tuple[str, ...],
    cases: tuple[CaseVariant, ...],
    grammar: tuple[str, ...] = (),
    vocab_themes: tuple[str, ...] = (),
    linked: tuple[str, ...] = (),
) -> MicroSkillNode:
    return MicroSkillNode(
        node_id=node_id,
        label=label,
        cluster_id=cluster_id,
        cluster_label=cluster_label,
        domain_id=domain_id,
        domain_label=domain_label,
        parent_id=parent_id,
        children_ids=children_ids,
        prerequisite_ids=prerequisite_ids,
        recommended_next_ids=recommended_next_ids,
        difficulty=difficulty,
        cefr_min=cefr_min,
        cefr_max=cefr_max,
        estimated_mastery_enter=enter,
        estimated_mastery_advance=advance,
        micro_skills=micro_skills,
        case_variants=cases,
        required_grammar_hints=grammar,
        required_vocabulary_themes=vocab_themes,
        linked_skill_ids=linked,
    )


# Ordered default spine (path_index 0..n-1) — natural A1→C1 journey
PROGRESSION_SPINE_IDS: tuple[str, ...] = (
    # A1 — Daily Communication
    "micro:greetings",
    "micro:introductions",
    "micro:small_talk",
    "micro:meeting_new_people",
    # A2 — Travel / Shopping
    "micro:airport_arrival",
    "micro:hotel_checkin",
    "micro:travel_problems",
    "micro:shopping_requests",
    # B1 — University / Work / Health / Family
    "micro:university_planning",
    "micro:workplace_requests",
    "micro:healthcare_visit",
    "micro:family_discussion",
    # B2 — Immigration / Business / Negotiation / Conflict
    "micro:immigration",
    "micro:business_travel",
    "micro:negotiation",
    "micro:conflict_resolution",
    # C1 — Leadership / Ethics / Public / Academic / Law
    "micro:leadership_decisions",
    "micro:ethics_dilemmas",
    "micro:public_speaking",
    "micro:academic_speaking",
    "micro:law_and_society",
)


def build_progression_nodes() -> dict[str, MicroSkillNode]:
    """Build the Curriculum Progression Graph (id → node)."""
    nodes: dict[str, MicroSkillNode] = {}

    def add(n: MicroSkillNode) -> None:
        nodes[n.node_id] = n

    # --- A1 Daily Communication ---
    add(
        _node(
            node_id="micro:greetings",
            label="Greeting politely",
            cluster_id="cluster:daily_communication",
            cluster_label="Daily Communication",
            domain_id="domain:greetings",
            domain_label="Greetings",
            parent_id=None,
            children_ids=("micro:introductions",),
            prerequisite_ids=(),
            recommended_next_ids=("micro:introductions",),
            difficulty=1,
            cefr_min="A1",
            cefr_max="A2",
            enter=0.0,
            advance=0.45,
            micro_skills=("Greeting politely", "Saying hello and goodbye"),
            grammar=("present_simple",),
            vocab_themes=("greetings",),
            linked=("phrase:travel_greetings",),
            cases=(
                _cv(
                    "case:greetings:cafe",
                    "Hello at the Cafe",
                    "cafe",
                    "A busy cafe counter where a customer greets a barista before ordering.",
                    ("Sam", "Lee"),
                    "daily_life",
                    "everyday",
                    "friendly politeness",
                ),
                _cv(
                    "case:greetings:neighbor",
                    "Meeting a Neighbor",
                    "neighborhood",
                    "A hallway greeting between neighbors who see each other for the first time this week.",
                    ("Noor", "Omar"),
                    "daily_life",
                    "everyday",
                    "warm first contact",
                ),
                _cv(
                    "case:greetings:classroom",
                    "First Day Hello",
                    "classroom",
                    "A classroom door where a new student greets a classmate before the lesson starts.",
                    ("Sara", "Maya"),
                    "school",
                    "everyday",
                    "nervous friendliness",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:introductions",
            label="Introducing yourself",
            cluster_id="cluster:daily_communication",
            cluster_label="Daily Communication",
            domain_id="domain:introductions",
            domain_label="Introductions",
            parent_id="micro:greetings",
            children_ids=("micro:small_talk",),
            prerequisite_ids=("micro:greetings",),
            recommended_next_ids=("micro:small_talk",),
            difficulty=1,
            cefr_min="A1",
            cefr_max="A2",
            enter=0.35,
            advance=0.45,
            micro_skills=("Introducing yourself", "Exchanging names"),
            grammar=("present_simple", "be_verb"),
            vocab_themes=("introductions",),
            cases=(
                _cv(
                    "case:intro:class",
                    "New Classmate Introduction",
                    "classroom",
                    "Two students introduce themselves on the first day and exchange simple facts.",
                    ("Lina", "Jordan"),
                    "school",
                    emotion="hopeful curiosity",
                ),
                _cv(
                    "case:intro:work",
                    "New Team Member",
                    "workplace",
                    "A new hire introduces themselves to a teammate before a short meeting.",
                    ("Maya", "Kim"),
                    "career",
                    emotion="professional warmth",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:small_talk",
            label="Making small talk",
            cluster_id="cluster:daily_communication",
            cluster_label="Daily Communication",
            domain_id="domain:small_talk",
            domain_label="Small Talk",
            parent_id="micro:introductions",
            children_ids=("micro:meeting_new_people",),
            prerequisite_ids=("micro:introductions",),
            recommended_next_ids=("micro:meeting_new_people",),
            difficulty=2,
            cefr_min="A1",
            cefr_max="A2",
            enter=0.35,
            advance=0.45,
            micro_skills=("Making small talk", "Asking simple questions"),
            grammar=("present_simple", "wh_questions"),
            cases=(
                _cv(
                    "case:smalltalk:bus",
                    "Short Talk on the Bus",
                    "public_transport",
                    "Two passengers make light conversation about the delay and the weather.",
                    ("Anna", "Diego"),
                    "daily_life",
                    emotion="light curiosity",
                ),
                _cv(
                    "case:smalltalk:queue",
                    "Waiting in a Queue",
                    "shop_queue",
                    "People waiting in a shop queue chat briefly about time and plans.",
                    ("Hana", "Lee"),
                    "daily_life",
                    emotion="polite patience",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:meeting_new_people",
            label="Meeting new people",
            cluster_id="cluster:daily_communication",
            cluster_label="Daily Communication",
            domain_id="domain:meeting_people",
            domain_label="Meeting New People",
            parent_id="micro:small_talk",
            children_ids=("micro:airport_arrival",),
            prerequisite_ids=("micro:small_talk",),
            recommended_next_ids=("micro:airport_arrival",),
            difficulty=2,
            cefr_min="A1",
            cefr_max="A2",
            enter=0.35,
            advance=0.5,
            micro_skills=("Meeting new people", "Keeping a first conversation going"),
            cases=(
                _cv(
                    "case:meet:party",
                    "First Conversation at a Gathering",
                    "social_gathering",
                    "A guest meets someone new and must keep a short conversation natural.",
                    ("Sara", "Omar"),
                    "relationships",
                    emotion="social warmth",
                ),
                _cv(
                    "case:meet:club",
                    "New Club Member",
                    "community_club",
                    "A new club member meets another member and finds a shared topic.",
                    ("Noor", "Chris"),
                    "relationships",
                    emotion="welcoming uncertainty",
                ),
            ),
        )
    )

    # --- A2 Travel ---
    add(
        _node(
            node_id="micro:airport_arrival",
            label="Airport arrival communication",
            cluster_id="cluster:travel",
            cluster_label="Travel",
            domain_id="domain:airport",
            domain_label="Airport Arrival",
            parent_id="micro:meeting_new_people",
            children_ids=("micro:hotel_checkin",),
            prerequisite_ids=("micro:meeting_new_people",),
            recommended_next_ids=("micro:hotel_checkin",),
            difficulty=2,
            cefr_min="A2",
            cefr_max="B1",
            enter=0.35,
            advance=0.5,
            micro_skills=("Greeting travelers", "Clarifying arrival problems"),
            linked=("phrase:travel_greetings",),
            cases=(
                _cv(
                    "case:airport:late",
                    "Late at Arrivals",
                    "airport",
                    "An international airport arrivals hall where a late arrival creates tension "
                    "between a traveler and the person waiting to meet them.",
                    ("Anna", "Diego"),
                    "travel",
                    "travel_greetings",
                    "awkward urgency",
                ),
                _cv(
                    "case:airport:business",
                    "Business Traveler Arrival",
                    "airport",
                    "A business traveler lands late for a meeting and must greet a company host clearly.",
                    ("Maya", "Mr. Hayes"),
                    "travel",
                    "travel_greetings",
                    "professional stress",
                ),
                _cv(
                    "case:airport:family",
                    "Family Vacation Arrival",
                    "airport",
                    "A family arrives after a long flight and must coordinate who meets them and when.",
                    ("Lina", "Omar", "Sara"),
                    "travel",
                    "travel_greetings",
                    "tired relief",
                ),
                _cv(
                    "case:airport:luggage",
                    "Lost Luggage Desk",
                    "airport",
                    "A traveler reports missing luggage and must describe the bag and trip clearly.",
                    ("Noor", "agent Kim"),
                    "travel",
                    "travel_emergency",
                    "frustrated politeness",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:hotel_checkin",
            label="Hotel check-in requests",
            cluster_id="cluster:travel",
            cluster_label="Travel",
            domain_id="domain:hotel",
            domain_label="Hotel Check-in",
            parent_id="micro:airport_arrival",
            children_ids=("micro:travel_problems",),
            prerequisite_ids=("micro:airport_arrival",),
            recommended_next_ids=("micro:travel_problems",),
            difficulty=2,
            cefr_min="A2",
            cefr_max="B1",
            enter=0.4,
            advance=0.5,
            micro_skills=("Making polite requests", "Confirming booking details"),
            cases=(
                _cv(
                    "case:hotel:booking",
                    "Hotel Booking Under Pressure",
                    "hotel",
                    "At a busy hotel desk, a traveler and staff negotiate a booking problem "
                    "while another guest waits.",
                    ("Anna", "Diego", "Kim"),
                    "travel",
                    "travel",
                    "polite frustration",
                ),
                _cv(
                    "case:hotel:room",
                    "Wrong Room Type",
                    "hotel",
                    "A guest discovers the room type is wrong and must request a fair change.",
                    ("Hana", "desk agent"),
                    "customer_service",
                    emotion="firm politeness",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:travel_problems",
            label="Handling travel problems",
            cluster_id="cluster:travel",
            cluster_label="Travel",
            domain_id="domain:travel_problems",
            domain_label="Travel Problems",
            parent_id="micro:hotel_checkin",
            children_ids=("micro:shopping_requests",),
            prerequisite_ids=("micro:hotel_checkin",),
            recommended_next_ids=("micro:shopping_requests",),
            difficulty=3,
            cefr_min="A2",
            cefr_max="B1",
            enter=0.4,
            advance=0.5,
            micro_skills=("Explaining a problem", "Requesting practical help"),
            linked=("task:travel_emergency",),
            cases=(
                _cv(
                    "case:travel:missed",
                    "Missed Connection",
                    "travel_emergency",
                    "A transit desk where a missed connection creates cost, time pressure, and "
                    "frustration with staff.",
                    ("Noor", "agent Kim"),
                    "travel",
                    "travel_emergency",
                    "urgent need",
                ),
                _cv(
                    "case:travel:delay",
                    "Delayed Bus Explanation",
                    "bus_station",
                    "A traveler must explain a delay to a waiting friend and re-plan the next step.",
                    ("Sam", "Lee"),
                    "travel",
                    emotion="apology under pressure",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:shopping_requests",
            label="Shopping and service requests",
            cluster_id="cluster:shopping",
            cluster_label="Shopping",
            domain_id="domain:shopping",
            domain_label="Shopping",
            parent_id="micro:travel_problems",
            children_ids=("micro:university_planning",),
            prerequisite_ids=("micro:travel_problems",),
            recommended_next_ids=("micro:university_planning",),
            difficulty=2,
            cefr_min="A2",
            cefr_max="B1",
            enter=0.4,
            advance=0.5,
            micro_skills=("Asking for help in a shop", "Handling a complaint politely"),
            cases=(
                _cv(
                    "case:shop:size",
                    "Wrong Size Exchange",
                    "clothing_store",
                    "A customer needs to exchange an item and must explain the problem clearly.",
                    ("Yara", "shop assistant"),
                    "customer_service",
                    emotion="polite insistence",
                ),
                _cv(
                    "case:shop:return",
                    "Return Without Receipt",
                    "electronics_store",
                    "A customer wants a return without a receipt and must negotiate a fair option.",
                    ("Rami", "store lead"),
                    "customer_service",
                    emotion="fairness tension",
                ),
            ),
        )
    )

    # --- B1 ---
    add(
        _node(
            node_id="micro:university_planning",
            label="University planning decisions",
            cluster_id="cluster:university",
            cluster_label="University",
            domain_id="domain:university",
            domain_label="University",
            parent_id="micro:shopping_requests",
            children_ids=("micro:workplace_requests",),
            prerequisite_ids=("micro:shopping_requests",),
            recommended_next_ids=("micro:workplace_requests",),
            difficulty=3,
            cefr_min="B1",
            cefr_max="B2",
            enter=0.4,
            advance=0.55,
            micro_skills=("Explaining plans", "Asking for advice", "Making decisions"),
            cases=(
                _cv(
                    "case:uni:deadline",
                    "Course Deadline Dilemma",
                    "university",
                    "A student, an advisor, and a department head negotiate an extension that "
                    "affects fairness for the class.",
                    ("Sara", "Mr. Hayes", "Lina"),
                    "university",
                    "education",
                    "responsibility anxiety",
                ),
                _cv(
                    "case:uni:group",
                    "Group Project Roles",
                    "campus",
                    "Group members disagree about roles before a presentation and must decide clearly.",
                    ("Omar", "Maya", "Jordan"),
                    "university",
                    emotion="shared responsibility",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:workplace_requests",
            label="Workplace requests and clarity",
            cluster_id="cluster:career",
            cluster_label="Career",
            domain_id="domain:workplace",
            domain_label="Workplace",
            parent_id="micro:university_planning",
            children_ids=("micro:healthcare_visit",),
            prerequisite_ids=("micro:university_planning",),
            recommended_next_ids=("micro:healthcare_visit",),
            difficulty=3,
            cefr_min="B1",
            cefr_max="B2",
            enter=0.4,
            advance=0.55,
            micro_skills=("Making clear requests", "Clarifying misunderstandings"),
            linked=("fluency:speaking_rate",),
            cases=(
                _cv(
                    "case:work:meeting",
                    "Too Fast in the Meeting",
                    "workplace",
                    "A team meeting where one coworker rushes explanations and the other cannot "
                    "follow the next step.",
                    ("Maya", "Jordan"),
                    "business",
                    "speaking_rate",
                    "frustration under pressure",
                ),
                _cv(
                    "case:work:deadline",
                    "Deadline Clarification",
                    "office",
                    "A junior employee must clarify a vague deadline with a manager before work starts.",
                    ("Sam", "Lee"),
                    "career",
                    emotion="professional caution",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:healthcare_visit",
            label="Healthcare conversations",
            cluster_id="cluster:healthcare",
            cluster_label="Healthcare",
            domain_id="domain:healthcare",
            domain_label="Healthcare",
            parent_id="micro:workplace_requests",
            children_ids=("micro:family_discussion",),
            prerequisite_ids=("micro:workplace_requests",),
            recommended_next_ids=("micro:family_discussion",),
            difficulty=3,
            cefr_min="B1",
            cefr_max="B2",
            enter=0.4,
            advance=0.55,
            micro_skills=("Describing symptoms", "Confirming next steps"),
            cases=(
                _cv(
                    "case:health:clinic",
                    "What the Doctor Needs to Know",
                    "medical",
                    "A clinic consultation where a patient must describe symptoms accurately "
                    "and understand next steps.",
                    ("Rami", "Dr. Ellis"),
                    "healthcare",
                    "medical_visit",
                    "careful empathy",
                ),
                _cv(
                    "case:health:pharmacy",
                    "Pharmacy Clarification",
                    "pharmacy",
                    "A patient clarifies medicine instructions with a pharmacist after a rushed visit.",
                    ("Noor", "pharmacist"),
                    "healthcare",
                    emotion="anxious clarity",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:family_discussion",
            label="Family discussions and opinions",
            cluster_id="cluster:family",
            cluster_label="Family",
            domain_id="domain:family",
            domain_label="Family",
            parent_id="micro:healthcare_visit",
            children_ids=("micro:immigration",),
            prerequisite_ids=("micro:healthcare_visit",),
            recommended_next_ids=("micro:immigration",),
            difficulty=3,
            cefr_min="B1",
            cefr_max="B2",
            enter=0.45,
            advance=0.55,
            micro_skills=("Expressing opinions", "Disagreeing respectfully"),
            cases=(
                _cv(
                    "case:family:kitchen",
                    "A Hard Family Talk",
                    "family",
                    "A family kitchen where relatives disagree about a sensitive plan that "
                    "affects everyone in the house.",
                    ("Lina", "Omar"),
                    "family",
                    "family_conflict",
                    "love and tension",
                ),
                _cv(
                    "case:family:visit",
                    "Family Visit Plans",
                    "living_room",
                    "Relatives negotiate visit timing and responsibilities without hurting anyone.",
                    ("Hana", "Kareem", "Sara"),
                    "family",
                    emotion="mixed loyalties",
                ),
            ),
        )
    )

    # --- B2 ---
    add(
        _node(
            node_id="micro:immigration",
            label="Immigration conversations",
            cluster_id="cluster:immigration",
            cluster_label="Travel",
            domain_id="domain:immigration",
            domain_label="Immigration",
            parent_id="micro:family_discussion",
            children_ids=("micro:business_travel",),
            prerequisite_ids=("micro:family_discussion",),
            recommended_next_ids=("micro:business_travel",),
            difficulty=4,
            cefr_min="B2",
            cefr_max="C1",
            enter=0.45,
            advance=0.6,
            micro_skills=("Explaining documents", "Persuading politely", "Handling stress"),
            cases=(
                _cv(
                    "case:immig:visa",
                    "Visa Documents Under Review",
                    "immigration_office",
                    "An applicant must explain missing paperwork while an officer follows strict rules.",
                    ("Noor", "officer Lee", "translator"),
                    "immigration",
                    "immigration",
                    "high stakes calm",
                ),
                _cv(
                    "case:immig:interview",
                    "Residency Interview",
                    "immigration_interview",
                    "A residency interview where clear answers and honesty compete with nerves.",
                    ("Rami", "officer Hayes"),
                    "immigration",
                    emotion="controlled anxiety",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:business_travel",
            label="Business travel coordination",
            cluster_id="cluster:business",
            cluster_label="Business",
            domain_id="domain:business_travel",
            domain_label="Business Travel",
            parent_id="micro:immigration",
            children_ids=("micro:negotiation",),
            prerequisite_ids=("micro:immigration",),
            recommended_next_ids=("micro:negotiation",),
            difficulty=4,
            cefr_min="B2",
            cefr_max="C1",
            enter=0.5,
            advance=0.6,
            micro_skills=("Coordinating plans", "Giving updates", "Making decisions"),
            cases=(
                _cv(
                    "case:biztravel:meeting",
                    "Client Meeting Delay",
                    "business_hotel",
                    "A delayed flight forces a business traveler to renegotiate a client meeting.",
                    ("Maya", "client Jordan", "assistant"),
                    "business",
                    emotion="professional urgency",
                ),
                _cv(
                    "case:biztravel:conference",
                    "Conference Slot Conflict",
                    "conference",
                    "Two colleagues must decide who presents when a conference slot changes suddenly.",
                    ("Sam", "Lee", "host"),
                    "business",
                    emotion="shared accountability",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:negotiation",
            label="Negotiation and agreement",
            cluster_id="cluster:negotiation",
            cluster_label="Negotiation",
            domain_id="domain:negotiation",
            domain_label="Negotiation",
            parent_id="micro:business_travel",
            children_ids=("micro:conflict_resolution",),
            prerequisite_ids=("micro:business_travel",),
            recommended_next_ids=("micro:conflict_resolution",),
            difficulty=4,
            cefr_min="B2",
            cefr_max="C1",
            enter=0.5,
            advance=0.6,
            micro_skills=("Negotiating", "Agreeing", "Finding trade-offs"),
            grammar=("conditionals",),
            cases=(
                _cv(
                    "case:nego:supplier",
                    "Supplier Contract Decision",
                    "supplier_meeting",
                    "A business owner negotiates a supplier contract while cash flow and deadlines "
                    "create conflicting pressure.",
                    ("Maya", "Jordan", "Hana"),
                    "business",
                    "business",
                    "pragmatic tension",
                ),
                _cv(
                    "case:nego:football",
                    "A Deal Between Football Clubs",
                    "football_club",
                    "Two football clubs negotiate a transfer deadline with managers and a captain present.",
                    ("Kareem", "Yara", "Hassan"),
                    "negotiation",
                    "football",
                    "competitive urgency",
                ),
                _cv(
                    "case:nego:hospital",
                    "Hospital Resource Negotiation",
                    "hospital",
                    "A hospital team negotiates limited resources and patient priorities under time pressure.",
                    ("Rami", "Dr. Ellis", "Noor"),
                    "healthcare",
                    "medicine",
                    "careful pressure",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:conflict_resolution",
            label="Conflict resolution",
            cluster_id="cluster:conflict_resolution",
            cluster_label="Conflict Resolution",
            domain_id="domain:conflict",
            domain_label="Conflict Resolution",
            parent_id="micro:negotiation",
            children_ids=("micro:leadership_decisions",),
            prerequisite_ids=("micro:negotiation",),
            recommended_next_ids=("micro:leadership_decisions",),
            difficulty=4,
            cefr_min="B2",
            cefr_max="C1",
            enter=0.5,
            advance=0.6,
            micro_skills=("Resolving conflict", "Apologizing", "Rebuilding trust"),
            cases=(
                _cv(
                    "case:conflict:team",
                    "Team Blame Argument",
                    "workplace",
                    "Two coworkers argue after a failed delivery and must decide how to repair trust.",
                    ("Maya", "Jordan", "manager"),
                    "conflict_resolution",
                    "workplace_conflict",
                    "hidden frustration",
                ),
                _cv(
                    "case:conflict:neighbors",
                    "Neighbor Noise Dispute",
                    "apartment",
                    "Neighbors dispute late noise and need a fair spoken agreement tonight.",
                    ("Lina", "Omar"),
                    "conflict_resolution",
                    emotion="boundary tension",
                ),
            ),
        )
    )

    # --- C1 ---
    add(
        _node(
            node_id="micro:leadership_decisions",
            label="Leadership decisions",
            cluster_id="cluster:leadership",
            cluster_label="Leadership",
            domain_id="domain:leadership",
            domain_label="Leadership",
            parent_id="micro:conflict_resolution",
            children_ids=("micro:ethics_dilemmas",),
            prerequisite_ids=("micro:conflict_resolution",),
            recommended_next_ids=("micro:ethics_dilemmas",),
            difficulty=5,
            cefr_min="C1",
            cefr_max="C2",
            enter=0.55,
            advance=0.65,
            micro_skills=("Leading a discussion", "Making difficult decisions", "Persuading"),
            cases=(
                _cv(
                    "case:lead:layoff",
                    "Restructuring Announcement",
                    "boardroom",
                    "A leader must announce a restructuring choice with competing stakeholder interests.",
                    ("Director Sam", "HR Lee", "team lead Maya"),
                    "leadership",
                    emotion="long-term responsibility",
                ),
                _cv(
                    "case:lead:crisis",
                    "Crisis Call with Partners",
                    "executive_call",
                    "Partners disagree on crisis spending and need a spoken decision with consequences.",
                    ("CEO Noor", "partner Omar", "advisor"),
                    "leadership",
                    emotion="high-stakes ambiguity",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:ethics_dilemmas",
            label="Ethical dilemmas",
            cluster_id="cluster:ethics",
            cluster_label="Ethics",
            domain_id="domain:ethics",
            domain_label="Ethics",
            parent_id="micro:leadership_decisions",
            children_ids=("micro:public_speaking",),
            prerequisite_ids=("micro:leadership_decisions",),
            recommended_next_ids=("micro:public_speaking",),
            difficulty=5,
            cefr_min="C1",
            cefr_max="C2",
            enter=0.55,
            advance=0.65,
            micro_skills=("Discussing ethics", "Defending a position", "Weighing trade-offs"),
            cases=(
                _cv(
                    "case:ethics:honesty",
                    "Integrity at Work",
                    "workplace",
                    "An employee discovers a reporting error that benefits the company and must decide "
                    "what to say.",
                    ("Sara", "manager Hayes", "colleague"),
                    "ethics",
                    "ethical_dilemma",
                    "moral pressure",
                ),
                _cv(
                    "case:ethics:university",
                    "Academic Honesty Case",
                    "university",
                    "A student faces pressure to share exam answers and must discuss the ethical choice.",
                    ("Omar", "classmate", "professor"),
                    "ethics",
                    emotion="peer pressure",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:public_speaking",
            label="Public communication",
            cluster_id="cluster:public_speaking",
            cluster_label="Public Speaking",
            domain_id="domain:public",
            domain_label="Public Communication",
            parent_id="micro:ethics_dilemmas",
            children_ids=("micro:academic_speaking",),
            prerequisite_ids=("micro:ethics_dilemmas",),
            recommended_next_ids=("micro:academic_speaking",),
            difficulty=5,
            cefr_min="C1",
            cefr_max="C2",
            enter=0.55,
            advance=0.65,
            micro_skills=("Giving presentations", "Handling questions", "Persuading an audience"),
            cases=(
                _cv(
                    "case:public:town",
                    "Town Hall Response",
                    "town_hall",
                    "A speaker answers community questions about a contested public plan.",
                    ("Mayor Lina", "resident Omar", "journalist"),
                    "public_communication",
                    emotion="public scrutiny",
                ),
                _cv(
                    "case:public:company",
                    "Company All-Hands Q&A",
                    "all_hands",
                    "A director defends a strategy change while staff raise counterarguments.",
                    ("Director Kim", "engineer Maya", "HR"),
                    "public_communication",
                    emotion="transparent tension",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:academic_speaking",
            label="Academic speaking",
            cluster_id="cluster:academic_speaking",
            cluster_label="Academic Speaking",
            domain_id="domain:academic",
            domain_label="Academic Speaking",
            parent_id="micro:public_speaking",
            children_ids=("micro:law_and_society",),
            prerequisite_ids=("micro:public_speaking",),
            recommended_next_ids=("micro:law_and_society",),
            difficulty=5,
            cefr_min="C1",
            cefr_max="C2",
            enter=0.55,
            advance=0.65,
            micro_skills=("Defending an argument", "Using evidence", "Counterarguments"),
            cases=(
                _cv(
                    "case:academic:seminar",
                    "Seminar Counterargument",
                    "university_seminar",
                    "A graduate seminar where a student must defend a claim and answer a counterargument.",
                    ("Sara", "professor", "peer"),
                    "university",
                    emotion="intellectual pressure",
                ),
                _cv(
                    "case:academic:panel",
                    "Research Panel Challenge",
                    "conference_panel",
                    "A researcher answers a tough methodological challenge before a panel.",
                    ("Dr. Noor", "panelist", "chair"),
                    "university",
                    emotion="precise defense",
                ),
            ),
        )
    )
    add(
        _node(
            node_id="micro:law_and_society",
            label="Law and society discussions",
            cluster_id="cluster:law",
            cluster_label="Law",
            domain_id="domain:law_society",
            domain_label="Law & Society",
            parent_id="micro:academic_speaking",
            children_ids=(),
            prerequisite_ids=("micro:academic_speaking",),
            recommended_next_ids=(),
            difficulty=5,
            cefr_min="C1",
            cefr_max="C2",
            enter=0.55,
            advance=0.7,
            micro_skills=("Analyzing policy", "Discussing societal consequences", "No single correct answer"),
            cases=(
                _cv(
                    "case:law:policy",
                    "Policy Trade-off Hearing",
                    "policy_hearing",
                    "Stakeholders debate a public policy with legal, social, and financial consequences.",
                    ("advocate", "council member", "resident", "analyst"),
                    "law",
                    emotion="systemic stakes",
                ),
                _cv(
                    "case:law:contract",
                    "Contract Ambiguity Dispute",
                    "legal_meeting",
                    "Two parties dispute a contract clause with long-term effects and no neat answer.",
                    ("counsel A", "counsel B", "client"),
                    "law",
                    emotion="strategic ambiguity",
                ),
            ),
        )
    )

    return nodes


PROGRESSION_NODES: dict[str, MicroSkillNode] = build_progression_nodes()


def spine_nodes_for_cefr(cefr: str) -> list[MicroSkillNode]:
    """Return spine nodes whose CEFR band intersects the learner level."""
    level = (cefr or "A2").upper()
    if level.startswith("C"):
        level = "C1"
    order = ("A1", "A2", "B1", "B2", "C1")
    try:
        idx = order.index(level if level in order else "A2")
    except ValueError:
        idx = 1
    allowed = set(order[: idx + 1])
    # Also include nodes whose cefr_min matches current level specifically
    out: list[MicroSkillNode] = []
    for nid in PROGRESSION_SPINE_IDS:
        node = PROGRESSION_NODES[nid]
        if node.cefr_min in allowed or node.cefr_min == level:
            # Prefer nodes intended for this band or earlier unfinished path
            out.append(node)
    # Restrict to nodes that are primarily for current CEFR: cefr_min <= level
    primary: list[MicroSkillNode] = []
    for node in out:
        try:
            if order.index(node.cefr_min) <= idx:
                primary.append(node)
        except ValueError:
            primary.append(node)
    return primary


def path_index(node_id: str) -> int:
    try:
        return PROGRESSION_SPINE_IDS.index(node_id)
    except ValueError:
        return -1
