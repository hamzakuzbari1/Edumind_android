# Listening MVP 60-Item Bank Expansion — Draft Batch

Status: **offline content draft only**. No database rows inserted, no audio generated, no runtime
code touched. All `draft_id` values are authoring-time identifiers only, not database IDs.

This file contains 42 new draft Listening items to expand the reachable bank from 18 to 60 items
(39 MCQ + 21 Gap Fill), per the approved Listening coverage audit. See **Coverage Summary**,
**Final Bank Projection**, **Self-Audit Findings**, and **Known Non-Goals** at the end of the file.

---

## A1 (8 new items: 4 MCQ + 4 Gap Fill)

### ITEM LST-A1-01
- draft_id: LST-A1-01
- cefr_level: A1
- question_type: mcq
- listening_skill: explicit_detail
- secondary_skill: main_idea
- audio_context: classroom
- discourse_type: dialogue
- speakers: 2 (teacher, new student)
- transcript: "Hello! I'm Ms. Carter. What's your name?" "My name is Tomas." "Nice to meet you, Tomas. Where are you from?" "I'm from Madrid." "How old are you?" "I'm eleven." "Welcome to our class, Tomas. You can sit next to Anna."
- transcript_word_count: 40
- target_duration_seconds: 18
- situation: A teacher welcomes a new student on his first day of class.
- prompt_or_question: How old is Tomas?
- options: ["Ten", "Eleven", "Twelve", "Thirteen"]
- correct_index: 1
- correct_answer: Eleven
- rationale: Tomas directly states his age ("I'm eleven"), a single explicit fact.
- distractor_rationale: "Ten" and "Twelve" are plausible nearby ages a young listener might mishear; "Thirteen" is a common age distractor for this age group. None are hinted at anywhere in the transcript.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Very short two-turn exchange; only one clear fact (age) is tested.
- estimated_cefr_justification: Present simple, short sentences, one fact per line, common classroom vocabulary — matches A1.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Hello! I'm Ms. Carter. What's your name? My name is Tomas. Nice to meet you, Tomas. Where are you from? I'm from Madrid. How old are you? I'm eleven. Welcome to our class, Tomas. You can sit next to Anna.",
  "situation": "A teacher welcomes a new student on his first day of class.",
  "question": "How old is Tomas?",
  "options": ["Ten", "Eleven", "Twelve", "Thirteen"],
  "correct_index": 1,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": "main_idea",
  "audio_context": "classroom",
  "discourse_type": "dialogue",
  "rationale": "Tomas directly states his age, a single explicit fact.",
  "distractor_rationale": "Ten/Twelve/Thirteen are plausible nearby ages, none supported by the transcript."
}
```

### ITEM LST-A1-02
- draft_id: LST-A1-02
- cefr_level: A1
- question_type: mcq
- listening_skill: number_time_price
- secondary_skill: relationship_between_speakers
- audio_context: shopping
- discourse_type: dialogue
- speakers: 2 (customer, shopkeeper)
- transcript: "Hello! Can I have three apples and one banana, please?" "Sure. The apples are two dollars, and the banana is fifty cents." "Okay, here you are." "Thank you! Have a nice day." "You too, bye!"
- transcript_word_count: 35
- target_duration_seconds: 16
- situation: A customer buys fruit at a small shop.
- prompt_or_question: How much do the apples cost?
- options: ["One dollar", "Two dollars", "Three dollars", "Four dollars"]
- correct_index: 1
- correct_answer: Two dollars
- rationale: The shopkeeper states the price directly ("That's two dollars").
- distractor_rationale: "Three dollars" reuses the number of apples to test careful listening; "One dollar" and "Four dollars" are simple nearby-price distractors with no support in the audio.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Classic service-interaction template; price stated once, clearly.
- estimated_cefr_justification: High-frequency shopping vocabulary, present simple/short imperative, one number to track.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Hello! Can I have three apples and one banana, please? Sure. The apples are two dollars, and the banana is fifty cents. Okay, here you are. Thank you! Have a nice day. You too, bye!",
  "situation": "A customer buys fruit at a small shop.",
  "question": "How much do the apples cost?",
  "options": ["One dollar", "Two dollars", "Three dollars", "Four dollars"],
  "correct_index": 1,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": "relationship_between_speakers",
  "audio_context": "shopping",
  "discourse_type": "dialogue",
  "rationale": "The shopkeeper states the price directly.",
  "distractor_rationale": "Three dollars reuses the item count as a trap; the others are simple nearby prices."
}
```

### ITEM LST-A1-03
- draft_id: LST-A1-03
- cefr_level: A1
- question_type: mcq
- listening_skill: place_name
- secondary_skill: main_idea
- audio_context: public announcement
- discourse_type: monologue
- speakers: 1 (bus announcer)
- transcript: "Good morning, everyone, and welcome aboard. This bus goes to Green Park. The next stop is Green Park, in about five minutes. Please have your ticket ready. Thank you for riding with us today."
- transcript_word_count: 34
- target_duration_seconds: 16
- situation: An announcement on a public bus.
- prompt_or_question: Where does the bus go?
- options: ["Green Park", "Central Station", "River Road", "Market Square"]
- correct_index: 0
- correct_answer: Green Park
- rationale: The destination is repeated twice in the announcement.
- distractor_rationale: The other three are common, plausible place names of similar length and register; none are mentioned in the audio.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Simple public-announcement register; repetition of the key fact supports A1 listeners.
- estimated_cefr_justification: Short present-simple sentences, single repeated fact, common transport vocabulary.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Good morning, everyone, and welcome aboard. This bus goes to Green Park. The next stop is Green Park, in about five minutes. Please have your ticket ready. Thank you for riding with us today.",
  "situation": "An announcement on a public bus.",
  "question": "Where does the bus go?",
  "options": ["Green Park", "Central Station", "River Road", "Market Square"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "place_name",
  "secondary_skill": "main_idea",
  "audio_context": "public_announcement",
  "discourse_type": "monologue",
  "rationale": "The destination is repeated twice.",
  "distractor_rationale": "Other place names are plausible but unmentioned."
}
```

### ITEM LST-A1-04
- draft_id: LST-A1-04
- cefr_level: A1
- question_type: mcq
- listening_skill: reason_cause
- secondary_skill: speaker_purpose
- audio_context: informal planning
- discourse_type: dialogue
- speakers: 2 (mother, son)
- transcript: "Let's go to the park today." "Why, Mom?" "Because it's sunny and warm, and your sister wants to ride her new bike." "Okay, let's go! Can we bring the dog too?" "Yes, of course we can."
- transcript_word_count: 36
- target_duration_seconds: 17
- situation: A parent suggests a weekend activity to her child.
- prompt_or_question: Why does Mom want to go to the park?
- options: ["Because it is sunny", "Because it is a holiday", "Because her friend is there", "Because the park is new"]
- correct_index: 0
- correct_answer: Because it is sunny
- rationale: Mom gives the reason directly: "Because it's sunny and warm."
- distractor_rationale: The other options are ordinary reasons one might expect for a park trip, but none are stated in the dialogue.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Minimal exchange; reason given in a single short clause.
- estimated_cefr_justification: Very short turns, one simple reason clause with "because", high-frequency vocabulary.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Let's go to the park today. Why, Mom? Because it's sunny and warm, and your sister wants to ride her new bike. Okay, let's go! Can we bring the dog too? Yes, of course we can.",
  "situation": "A parent suggests a weekend activity to her child.",
  "question": "Why does Mom want to go to the park?",
  "options": ["Because it is sunny", "Because it is a holiday", "Because her friend is there", "Because the park is new"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "reason_cause",
  "secondary_skill": "speaker_purpose",
  "audio_context": "informal_planning",
  "discourse_type": "dialogue",
  "rationale": "Mom gives the reason directly.",
  "distractor_rationale": "Plausible alternative reasons, none supported by the audio."
}
```

### ITEM LST-A1-05
- draft_id: LST-A1-05
- cefr_level: A1
- question_type: gap_fill
- listening_skill: explicit_detail
- secondary_skill: main_idea
- audio_context: everyday conversation
- discourse_type: monologue
- speakers: 1 (child introducing herself)
- transcript: "Hi! My name is Lucy. I am nine years old. I live in Bristol with my mom and dad. I like cats and I have one cat. Her name is Milo. I also have a little brother."
- transcript_word_count: 37
- target_duration_seconds: 17
- situation: A child gives a short self-introduction.
- prompt_or_question: What is the girl's name?
- accepted_answers: ["Lucy"]
- max_words: 1
- case_sensitive: false
- word_bank: ["Lucy", "Milo", "Bristol", "nine"]
- correct_answer: Lucy
- rationale: The speaker states her own name in the first sentence.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Word bank includes a plausible distractor (the cat's name) to test that the listener distinguishes the speaker from other named entities.
- estimated_cefr_justification: Simple present tense, one fact per sentence, common personal-information vocabulary.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Hi! My name is Lucy. I am nine years old. I live in Bristol with my mom and dad. I like cats and I have one cat. Her name is Milo. I also have a little brother.",
  "situation": "A child gives a short self-introduction.",
  "prompt": "What is the girl's name?",
  "accepted_answers": ["Lucy"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": ["Lucy", "Milo", "Bristol", "nine"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": "main_idea",
  "audio_context": "everyday_conversation",
  "discourse_type": "monologue",
  "rationale": "The speaker states her own name in the first sentence."
}
```

### ITEM LST-A1-06
- draft_id: LST-A1-06
- cefr_level: A1
- question_type: gap_fill
- listening_skill: number_time_price
- secondary_skill: (none)
- audio_context: everyday conversation
- discourse_type: dialogue
- speakers: 2 (friends)
- transcript: "What time is it, Sam?" "It's four o'clock." "Great, the film starts at five, so we have an hour." "Perfect, let's walk there and get some popcorn first." "Good idea, I'm hungry too."
- transcript_word_count: 33
- target_duration_seconds: 15
- situation: Two friends check the time before going to the cinema.
- prompt_or_question: What time is it now?
- accepted_answers: ["four", "4", "4:00"]
- max_words: 1
- case_sensitive: false
- word_bank: ["four", "five", "six"]
- correct_answer: four
- rationale: Sam answers the direct question about the current time. "4pm" is not accepted, since the transcript only says "four o'clock" and never states am/pm.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Word bank includes the film start time (five o'clock) as a plausible but incorrect near-neighbor.
- estimated_cefr_justification: Very short exchange, one clock time to identify, everyday vocabulary.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "What time is it, Sam? It's four o'clock. Great, the film starts at five, so we have an hour. Perfect, let's walk there and get some popcorn first. Good idea, I'm hungry too.",
  "situation": "Two friends check the time before going to the cinema.",
  "prompt": "What time is it now?",
  "accepted_answers": ["four", "4", "4:00"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": ["four", "five", "six"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": null,
  "audio_context": "everyday_conversation",
  "discourse_type": "dialogue",
  "rationale": "Sam answers the direct question about the current time; am/pm is never stated in the transcript, so it is not required or accepted."
}
```

### ITEM LST-A1-07
- draft_id: LST-A1-07
- cefr_level: A1
- question_type: gap_fill
- listening_skill: following_instructions
- secondary_skill: sequence
- audio_context: classroom
- discourse_type: dialogue
- speakers: 2 (teacher, class)
- transcript: "Okay class, first open your books. Now find page five. Good. Look at the picture on page five. Can everyone see it? Great, now let's read the first sentence together."
- transcript_word_count: 30
- target_duration_seconds: 14
- situation: A teacher gives a simple classroom instruction.
- prompt_or_question: Which page should the students find?
- accepted_answers: ["five", "5"]
- max_words: 1
- case_sensitive: false
- word_bank: ["five", "six", "ten"]
- correct_answer: five
- rationale: The teacher names the page number twice in sequence ("first... now find page five").
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Sequence markers ("first", "now") support the secondary sequence tag without requiring a separate question about order.
- estimated_cefr_justification: Simple imperative instructions, one number to extract, classroom vocabulary.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Okay class, first open your books. Now find page five. Good. Look at the picture on page five. Can everyone see it? Great, now let's read the first sentence together.",
  "situation": "A teacher gives a simple classroom instruction.",
  "prompt": "Which page should the students find?",
  "accepted_answers": ["five", "5"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": ["five", "six", "ten"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "following_instructions",
  "secondary_skill": "sequence",
  "audio_context": "classroom",
  "discourse_type": "dialogue",
  "rationale": "The teacher names the page number as the instruction's target."
}
```

### ITEM LST-A1-08
- draft_id: LST-A1-08
- cefr_level: A1
- question_type: gap_fill
- listening_skill: place_name
- secondary_skill: main_idea
- audio_context: informal planning
- discourse_type: monologue
- speakers: 1 (father, leaving a short voice note)
- transcript: "Hi kids, it's Dad. We are going to the zoo this afternoon, and Mom is coming too. Please put on your shoes and don't forget your hats. See you soon! Love you both."
- transcript_word_count: 33
- target_duration_seconds: 15
- situation: A parent leaves a short voice message about the family's plan.
- prompt_or_question: Where is the family going?
- accepted_answers: ["zoo"]
- max_words: 1
- case_sensitive: false
- word_bank: ["zoo", "park", "school"]
- correct_answer: zoo
- rationale: The destination is stated in a single clear sentence.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Word bank offers two other common family-outing destinations as gentle distractors.
- estimated_cefr_justification: Short present-continuous plan statement, one place name, everyday family vocabulary.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Hi kids, it's Dad. We are going to the zoo this afternoon, and Mom is coming too. Please put on your shoes and don't forget your hats. See you soon! Love you both.",
  "situation": "A parent leaves a short voice message about the family's plan.",
  "prompt": "Where is the family going?",
  "accepted_answers": ["zoo"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": ["zoo", "park", "school"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "place_name",
  "secondary_skill": "main_idea",
  "audio_context": "informal_planning",
  "discourse_type": "monologue",
  "rationale": "The destination is stated in a single clear sentence."
}
```

---

## A2 (8 new items: 4 MCQ + 4 Gap Fill)

### ITEM LST-A2-01
- draft_id: LST-A2-01
- cefr_level: A2
- question_type: mcq
- listening_skill: speaker_purpose
- secondary_skill: number_time_price
- audio_context: appointments
- discourse_type: dialogue
- speakers: 2 (receptionist, caller)
- transcript: "Good morning, Riverside Dental Clinic, how can I help you?" "Hi, I'd like to make an appointment, please. My tooth has been hurting since yesterday." "I'm sorry to hear that. Let me check the calendar. Can you come tomorrow at three o'clock?" "Yes, that's fine for me. Should I bring anything with me?" "Just your insurance card, if you have one. We'll see you tomorrow." "Great, thank you very much."
- transcript_word_count: 70
- target_duration_seconds: 32
- situation: A patient calls a dental clinic to arrange a visit.
- prompt_or_question: Why is the caller phoning the clinic?
- options: ["To make an appointment", "To cancel an appointment", "To ask about opening hours", "To complain about a bill"]
- correct_index: 0
- correct_answer: To make an appointment
- rationale: The caller states her purpose directly: "I'd like to make an appointment."
- distractor_rationale: The other purposes are common reasons to call a clinic and use similarly short, parallel phrasing, but none match what is actually said.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Purpose is stated early and clearly, appropriate for A2 rather than requiring inference.
- estimated_cefr_justification: Everyday service phone-call register, short turns, common appointment vocabulary.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Good morning, Riverside Dental Clinic, how can I help you? Hi, I'd like to make an appointment, please. My tooth has been hurting since yesterday. I'm sorry to hear that. Let me check the calendar. Can you come tomorrow at three o'clock? Yes, that's fine for me. Should I bring anything with me? Just your insurance card, if you have one. We'll see you tomorrow. Great, thank you very much.",
  "situation": "A patient calls a dental clinic to arrange a visit.",
  "question": "Why is the caller phoning the clinic?",
  "options": ["To make an appointment", "To cancel an appointment", "To ask about opening hours", "To complain about a bill"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "speaker_purpose",
  "secondary_skill": "number_time_price",
  "audio_context": "appointments",
  "discourse_type": "dialogue",
  "rationale": "The caller states her purpose directly.",
  "distractor_rationale": "Plausible, parallel alternative reasons to call a clinic; none are supported by the audio."
}
```

### ITEM LST-A2-02
- draft_id: LST-A2-02
- cefr_level: A2
- question_type: mcq
- listening_skill: place_name
- secondary_skill: sequence
- audio_context: transport
- discourse_type: dialogue
- speakers: 2 (tourist, local resident)
- transcript: "Excuse me, how do I get to the train station? I don't know this area very well." "No problem. Go straight for two blocks, then turn left at the traffic lights. The station is next to the bank, just past the small bakery." "Is it far from here?" "Not really, it's about a ten-minute walk." "Thanks a lot, that's really helpful!" "You're welcome. Have a safe trip."
- transcript_word_count: 67
- target_duration_seconds: 31
- situation: A tourist asks a local resident for directions.
- prompt_or_question: Where is the train station located?
- options: ["Next to the bank", "Next to the hotel", "Across from the park", "Behind the market"]
- correct_index: 0
- correct_answer: Next to the bank
- rationale: The resident states the station's location relative to a known landmark.
- distractor_rationale: Other landmarks are common in direction-giving language and similar in length, but none appear in the transcript.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Two-step direction sequence ("straight... then turn left") supports the secondary sequence tag.
- estimated_cefr_justification: Simple imperative direction-giving, one landmark to track, common transport vocabulary.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Excuse me, how do I get to the train station? I don't know this area very well. No problem. Go straight for two blocks, then turn left at the traffic lights. The station is next to the bank, just past the small bakery. Is it far from here? Not really, it's about a ten-minute walk. Thanks a lot, that's really helpful! You're welcome. Have a safe trip.",
  "situation": "A tourist asks a local resident for directions.",
  "question": "Where is the train station located?",
  "options": ["Next to the bank", "Next to the hotel", "Across from the park", "Behind the market"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "place_name",
  "secondary_skill": "sequence",
  "audio_context": "transport",
  "discourse_type": "dialogue",
  "rationale": "The resident states the station's location relative to a known landmark.",
  "distractor_rationale": "Other common landmarks are plausible but unsupported by the audio."
}
```

### ITEM LST-A2-03
- draft_id: LST-A2-03
- cefr_level: A2
- question_type: mcq
- listening_skill: reason_cause
- secondary_skill: relationship_between_speakers
- audio_context: shopping
- discourse_type: dialogue
- speakers: 2 (customer, shop assistant)
- transcript: "Hi, I'd like to return this shirt, please." "Sure, no problem. What seems to be the issue with it?" "It's too small for me, I think I ordered the wrong size." "That happens a lot, don't worry. Would you like a bigger size instead, or would you prefer a full refund?" "I think I'll try a bigger size, please, if you have one in stock." "Let me check... yes, we do. Here you go."
- transcript_word_count: 74
- target_duration_seconds: 34
- situation: A customer returns a piece of clothing at a shop.
- prompt_or_question: Why does the customer want to return the shirt?
- options: ["It is too small", "It is the wrong colour", "It has a hole in it", "It was too expensive"]
- correct_index: 0
- correct_answer: It is too small
- rationale: The customer states the reason directly: "It's too small for me."
- distractor_rationale: Other common return reasons are equally plausible in a shop context but are not mentioned in this exchange.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Customer/assistant register supports the secondary relationship_between_speakers tag.
- estimated_cefr_justification: Everyday service dialogue, one clear reason clause, common shopping vocabulary.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Hi, I'd like to return this shirt, please. Sure, no problem. What seems to be the issue with it? It's too small for me, I think I ordered the wrong size. That happens a lot, don't worry. Would you like a bigger size instead, or would you prefer a full refund? I think I'll try a bigger size, please, if you have one in stock. Let me check... yes, we do. Here you go.",
  "situation": "A customer returns a piece of clothing at a shop.",
  "question": "Why does the customer want to return the shirt?",
  "options": ["It is too small", "It is the wrong colour", "It has a hole in it", "It was too expensive"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "reason_cause",
  "secondary_skill": "relationship_between_speakers",
  "audio_context": "shopping",
  "discourse_type": "dialogue",
  "rationale": "The customer states the reason directly.",
  "distractor_rationale": "Other common return reasons are plausible but unsupported."
}
```

### ITEM LST-A2-04
- draft_id: LST-A2-04
- cefr_level: A2
- question_type: mcq
- listening_skill: reason_cause
- secondary_skill: main_idea
- audio_context: public announcement
- discourse_type: monologue
- speakers: 1 (station announcer)
- transcript: "Attention, passengers. The 10:15 train to Oakville is delayed this morning because of a signal problem near the station. We are sorry for the delay and any inconvenience this may cause. The train will now leave from platform two at 10:40. Please listen carefully for further announcements, and thank you for your patience this morning."
- transcript_word_count: 55
- target_duration_seconds: 25
- situation: A train station announcement about a delay.
- prompt_or_question: Why is the train delayed?
- options: ["A signal problem", "Bad weather", "A staff shortage", "A late driver"]
- correct_index: 0
- correct_answer: A signal problem
- rationale: The announcer states the cause directly: "because of a signal problem."
- distractor_rationale: Other options are common, plausible causes of train delays but are not mentioned in this announcement.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Announcement register with one clear cause and one time change.
- estimated_cefr_justification: Simple passive/cause structure ("delayed because of"), one number pair to track, common transport vocabulary.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Attention, passengers. The 10:15 train to Oakville is delayed this morning because of a signal problem near the station. We are sorry for the delay and any inconvenience this may cause. The train will now leave from platform two at 10:40. Please listen carefully for further announcements, and thank you for your patience this morning.",
  "situation": "A train station announcement about a delay.",
  "question": "Why is the train delayed?",
  "options": ["A signal problem", "Bad weather", "A staff shortage", "A late driver"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "reason_cause",
  "secondary_skill": "main_idea",
  "audio_context": "public_announcement",
  "discourse_type": "monologue",
  "rationale": "The announcer states the cause directly.",
  "distractor_rationale": "Other common delay causes are plausible but unsupported by the audio."
}
```

### ITEM LST-A2-05
- draft_id: LST-A2-05
- cefr_level: A2
- question_type: gap_fill
- listening_skill: number_time_price
- secondary_skill: speaker_purpose
- audio_context: appointments
- discourse_type: dialogue
- speakers: 2 (customer, restaurant host)
- transcript: "Hello, I'd like to book a table for Saturday evening, please." "Of course, I can help with that. How many people will be joining you?" "Four people, at seven o'clock, if that's possible." "Let me check... yes, that works well. Could I have a name for the booking?" "Yes, it's under Roberts." "Perfect, a table for four at seven, under Roberts. See you then."
- transcript_word_count: 64
- target_duration_seconds: 30
- situation: A customer books a table at a restaurant by phone.
- prompt_or_question: How many people is the table for?
- accepted_answers: ["four", "4", "four people", "4 people"]
- max_words: 2
- case_sensitive: false
- word_bank: ["two people", "four people", "six people"]
- correct_answer: four people
- rationale: The customer states the number of guests directly.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Word bank uses simple neighbouring guest-count distractors only; a prior draft borrowed "seven" from the booking time as a distractor, which risked confusing careless listeners between two different quantities rather than testing listening precision, and was replaced during cleanup.
- estimated_cefr_justification: Everyday booking dialogue, one number to extract among two candidate numbers, common vocabulary.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Hello, I'd like to book a table for Saturday evening, please. Of course, I can help with that. How many people will be joining you? Four people, at seven o'clock, if that's possible. Let me check... yes, that works well. Could I have a name for the booking? Yes, it's under Roberts. Perfect, a table for four at seven, under Roberts. See you then.",
  "situation": "A customer books a table at a restaurant by phone.",
  "prompt": "How many people is the table for?",
  "accepted_answers": ["four", "4", "four people", "4 people"],
  "max_words": 2,
  "case_sensitive": false,
  "word_bank": ["two people", "four people", "six people"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": "speaker_purpose",
  "audio_context": "appointments",
  "discourse_type": "dialogue",
  "rationale": "The customer states the number of guests directly."
}
```

### ITEM LST-A2-06
- draft_id: LST-A2-06
- cefr_level: A2
- question_type: gap_fill
- listening_skill: number_time_price
- secondary_skill: (none)
- audio_context: shopping
- discourse_type: dialogue
- speakers: 2 (customer, market seller)
- transcript: "How much are the strawberries today?" "They're three pounds fifty for a box, and they're really fresh this morning." "Okay, I'll take two boxes then, please." "That's seven pounds altogether. Would you like a bag for those?" "Yes, please, that would be great." "Here you are, thank you very much. Enjoy the strawberries! Have a lovely day."
- transcript_word_count: 57
- target_duration_seconds: 26
- situation: A customer buys fruit at an outdoor market.
- prompt_or_question: How many pounds is the total price for two boxes of strawberries?
- accepted_answers: ["seven", "7"]
- max_words: 1
- case_sensitive: false
- word_bank: ["3.50", "7", "2"]
- correct_answer: seven
- rationale: The seller states the final total after the customer orders two boxes; the prompt already supplies "pounds", so only the number is required.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Requires tracking the unit price and quantity to recognise the stated total; the total itself is explicitly said aloud, so no arithmetic inference is required of the listener. The word bank uses bare numbers (unit price, total, quantity) since "pounds" is already stated in the prompt.
- estimated_cefr_justification: Two related numbers in a short exchange, common market vocabulary, simple present tense.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "How much are the strawberries today? They're three pounds fifty for a box, and they're really fresh this morning. Okay, I'll take two boxes then, please. That's seven pounds altogether. Would you like a bag for those? Yes, please, that would be great. Here you are, thank you very much. Enjoy the strawberries! Have a lovely day.",
  "situation": "A customer buys fruit at an outdoor market.",
  "prompt": "How many pounds is the total price for two boxes of strawberries?",
  "accepted_answers": ["seven", "7"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": ["3.50", "7", "2"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": null,
  "audio_context": "shopping",
  "discourse_type": "dialogue",
  "rationale": "The seller states the final total aloud; the prompt already supplies the currency unit."
}
```

### ITEM LST-A2-07
- draft_id: LST-A2-07
- cefr_level: A2
- question_type: gap_fill
- listening_skill: explicit_detail
- secondary_skill: main_idea
- audio_context: school discussion
- discourse_type: monologue
- speakers: 1 (school office announcer)
- transcript: "Good morning, students. Don't forget the school trip to the science museum is this Friday. Please bring your permission form and a packed lunch with you. The bus leaves at nine, so make sure you arrive at school a little earlier than usual. We will return by four in the afternoon. Please wear comfortable shoes for walking."
- transcript_word_count: 57
- target_duration_seconds: 26
- situation: A school announces details of an upcoming trip.
- prompt_or_question: Where is the school trip going?
- accepted_answers: ["science museum", "museum"]
- max_words: 2
- case_sensitive: false
- word_bank: ["science museum", "art gallery", "zoo"]
- correct_answer: science museum
- rationale: The destination is stated once, clearly, near the start of the announcement.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Word bank offers two other plausible school-trip destinations.
- estimated_cefr_justification: School-announcement register, one clear destination fact plus supporting detail, common vocabulary.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Good morning, students. Don't forget the school trip to the science museum is this Friday. Please bring your permission form and a packed lunch with you. The bus leaves at nine, so make sure you arrive at school a little earlier than usual. We will return by four in the afternoon. Please wear comfortable shoes for walking.",
  "situation": "A school announces details of an upcoming trip.",
  "prompt": "Where is the school trip going?",
  "accepted_answers": ["science museum", "museum"],
  "max_words": 2,
  "case_sensitive": false,
  "word_bank": ["science museum", "art gallery", "zoo"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": "main_idea",
  "audio_context": "school_discussion",
  "discourse_type": "monologue",
  "rationale": "The destination is stated once, clearly, near the start."
}
```

### ITEM LST-A2-08
- draft_id: LST-A2-08
- cefr_level: A2
- question_type: gap_fill
- listening_skill: following_instructions
- secondary_skill: understanding_explanation
- audio_context: work discussion
- discourse_type: dialogue
- speakers: 2 (office colleagues)
- transcript: "Can you help me with something before lunch?" "Sure, what do you need?" "Please send the invoice to Mr. Patel by email, and copy in the finance team as well." "No problem, I'll do that right now. Should I mention the payment deadline in the email?" "Yes please, that would be really helpful, and let me know once it's sent."
- transcript_word_count: 60
- target_duration_seconds: 28
- situation: One colleague asks another to complete a simple work task.
- prompt_or_question: What does the colleague need to send by email?
- accepted_answers: ["invoice", "the invoice"]
- max_words: 2
- case_sensitive: false
- word_bank: ["invoice", "report", "form"]
- correct_answer: invoice
- rationale: The specific item to send is stated directly in the instruction.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Word bank includes two other plausible office documents.
- estimated_cefr_justification: Short workplace request, one clear task item, common office vocabulary.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Can you help me with something before lunch? Sure, what do you need? Please send the invoice to Mr. Patel by email, and copy in the finance team as well. No problem, I'll do that right now. Should I mention the payment deadline in the email? Yes please, that would be really helpful, and let me know once it's sent.",
  "situation": "One colleague asks another to complete a simple work task.",
  "prompt": "What does the colleague need to send by email?",
  "accepted_answers": ["invoice", "the invoice"],
  "max_words": 2,
  "case_sensitive": false,
  "word_bank": ["invoice", "report", "form"],
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "following_instructions",
  "secondary_skill": "understanding_explanation",
  "audio_context": "work_discussion",
  "discourse_type": "dialogue",
  "rationale": "The specific item to send is stated directly."
}
```

---

## B1 (8 new items: 4 MCQ + 4 Gap Fill)

### ITEM LST-B1-01
- draft_id: LST-B1-01
- cefr_level: B1
- question_type: mcq
- listening_skill: reason_cause
- secondary_skill: speaker_purpose
- audio_context: work discussion
- discourse_type: dialogue
- speakers: 2 (colleagues)
- transcript: "Hi Dana, I need to move our meeting from Tuesday to Thursday, if that's possible." "Oh, is something wrong?" "Not really — I have a client visiting on Tuesday afternoon, and I don't want to rush our discussion by squeezing it in beforehand. I'd rather we both have proper time to go through the figures together." "That makes sense. Is Thursday morning or afternoon better for you?" "Afternoon would be ideal, around two o'clock if that works." "That's fine, two o'clock on Thursday works well for me too. I'll update the calendar invite now."
- transcript_word_count: 94
- target_duration_seconds: 43
- situation: A colleague calls to reschedule a work meeting.
- prompt_or_question: Why does the speaker want to move the meeting?
- options: ["A client is visiting on Tuesday", "He is going on holiday", "The meeting room is unavailable", "He forgot about the meeting"]
- correct_index: 0
- correct_answer: A client is visiting on Tuesday
- rationale: The speaker explains the reason clearly: a client visit that would rush the discussion.
- distractor_rationale: The other options are ordinary scheduling reasons of similar plausibility and length, but none are mentioned.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Reason requires connecting two clauses ("client visiting" + "don't want to rush"), appropriate step up from A2's single-clause reasons.
- estimated_cefr_justification: Two linked ideas, moderate discourse length, everyday workplace register.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Hi Dana, I need to move our meeting from Tuesday to Thursday, if that's possible. Oh, is something wrong? Not really — I have a client visiting on Tuesday afternoon, and I don't want to rush our discussion by squeezing it in beforehand. I'd rather we both have proper time to go through the figures together. That makes sense. Is Thursday morning or afternoon better for you? Afternoon would be ideal, around two o'clock if that works. That's fine, two o'clock on Thursday works well for me too. I'll update the calendar invite now.",
  "situation": "A colleague calls to reschedule a work meeting.",
  "question": "Why does the speaker want to move the meeting?",
  "options": ["A client is visiting on Tuesday", "He is going on holiday", "The meeting room is unavailable", "He forgot about the meeting"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "reason_cause",
  "secondary_skill": "speaker_purpose",
  "audio_context": "work_discussion",
  "discourse_type": "dialogue",
  "rationale": "The speaker explains the reschedule reason clearly.",
  "distractor_rationale": "Ordinary scheduling reasons, none supported by the audio."
}
```

### ITEM LST-B1-02
- draft_id: LST-B1-02
- cefr_level: B1
- question_type: mcq
- listening_skill: relationship_between_speakers
- secondary_skill: speaker_attitude
- audio_context: everyday conversation
- discourse_type: dialogue
- speakers: 2 (friends)
- transcript: "My laptop crashed again this morning, right before my deadline, of all things." "Oh no, not again! Didn't you just get it fixed last month?" "Yeah, I did, and they told me it was completely sorted. I'm honestly getting tired of dealing with it, especially with how much is riding on this project right now." "That sounds so frustrating. Do you want to borrow mine this week? I'm mostly working from notes anyway, so I don't need it much." "Would you? That would really help, thank you so much. I'll bring it back the moment mine's fixed properly."
- transcript_word_count: 98
- target_duration_seconds: 45
- situation: Two close friends talk about a recurring technical problem.
- prompt_or_question: What is the relationship between the two speakers?
- options: ["Close, long-time friends", "Shop assistant and customer", "Teacher and student", "Strangers on a bus"]
- correct_index: 0
- correct_answer: Close, long-time friends
- rationale: The casual tone, shared history ("last month"), and offer to lend a personal item all indicate a close, informal relationship.
- distractor_rationale: The other relationships would use more formal or transactional language, which does not match this exchange.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Relationship must be inferred from tone and offer of help, not stated directly.
- estimated_cefr_justification: Requires connecting register and context clues rather than an explicit label; moderate discourse length.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "My laptop crashed again this morning, right before my deadline, of all things. Oh no, not again! Didn't you just get it fixed last month? Yeah, I did, and they told me it was completely sorted. I'm honestly getting tired of dealing with it, especially with how much is riding on this project right now. That sounds so frustrating. Do you want to borrow mine this week? I'm mostly working from notes anyway, so I don't need it much. Would you? That would really help, thank you so much. I'll bring it back the moment mine's fixed properly.",
  "situation": "Two close friends talk about a recurring technical problem.",
  "question": "What is the relationship between the two speakers?",
  "options": ["Close, long-time friends", "Shop assistant and customer", "Teacher and student", "Strangers on a bus"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "relationship_between_speakers",
  "secondary_skill": "speaker_attitude",
  "audio_context": "everyday_conversation",
  "discourse_type": "dialogue",
  "rationale": "Casual tone and offer to lend a personal item indicate close friends.",
  "distractor_rationale": "Other relationships would use more formal/transactional language, absent here."
}
```

### ITEM LST-B1-03
- draft_id: LST-B1-03
- cefr_level: B1
- question_type: mcq
- listening_skill: speaker_attitude
- secondary_skill: relationship_between_speakers
- audio_context: school discussion
- discourse_type: dialogue
- speakers: 2 (two students)
- transcript: "So for the group project, I think we should do our presentation on recycling, since it's something everyone can relate to." "Hmm, I'm not sure. We did something similar last term, and I don't want the teacher to think we're just repeating ourselves." "That's true, but I still think it's a strong topic if we find new examples, maybe something about local recycling schemes instead of the general facts we used before." "Okay, I suppose it could work if we make it different this time and focus more on our own town." "Exactly, that's what I was thinking too."
- transcript_word_count: 99
- target_duration_seconds: 46
- situation: Two students discuss an idea for a group school project.
- prompt_or_question: How does the second student feel about the recycling topic at first?
- options: ["Hesitant about it", "Extremely enthusiastic", "Firmly against it", "Indifferent to the whole project"]
- correct_index: 0
- correct_answer: Hesitant about it
- rationale: The second student says "I'm not sure" and raises a mild concern, showing hesitation rather than outright rejection or enthusiasm.
- distractor_rationale: "Extremely enthusiastic" and "firmly against it" both overstate the mild, hedged reaction shown; "indifferent" ignores that the student engages with the topic directly.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Attitude is hedged ("I'm not sure", "I suppose") rather than absolute, matching the audit's guidance to avoid extreme-wording distractors.
- estimated_cefr_justification: Requires tracking one speaker's attitude shift across the exchange; moderate discourse length and mild hedging language.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "So for the group project, I think we should do our presentation on recycling, since it's something everyone can relate to. Hmm, I'm not sure. We did something similar last term, and I don't want the teacher to think we're just repeating ourselves. That's true, but I still think it's a strong topic if we find new examples, maybe something about local recycling schemes instead of the general facts we used before. Okay, I suppose it could work if we make it different this time and focus more on our own town. Exactly, that's what I was thinking too.",
  "situation": "Two students discuss an idea for a group school project.",
  "question": "How does the second student feel about the recycling topic at first?",
  "options": ["Hesitant about it", "Extremely enthusiastic", "Firmly against it", "Indifferent to the whole project"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "speaker_attitude",
  "secondary_skill": "relationship_between_speakers",
  "audio_context": "school_discussion",
  "discourse_type": "dialogue",
  "rationale": "The student's hedged language shows hesitation, not outright rejection or enthusiasm.",
  "distractor_rationale": "Other options overstate or ignore the mild, hedged reaction shown."
}
```

### ITEM LST-B1-04
- draft_id: LST-B1-04
- cefr_level: B1
- question_type: mcq
- listening_skill: sequence
- secondary_skill: (none)
- audio_context: everyday conversation
- discourse_type: monologue
- speakers: 1 (person recounting a trip)
- transcript: "Last weekend I visited my cousin in Leeds, since I hadn't seen her in almost a year. First, I took the train, which took about two hours and was surprisingly comfortable. When I arrived, we had lunch together at a small cafe near the station, and caught up on everything that had happened recently. After that, we walked around the city centre and visited an old market, where I bought a few small gifts for my family. In the evening, we watched a film at her flat and ordered pizza, before I took the last train home feeling really glad I'd made the trip."
- transcript_word_count: 104
- target_duration_seconds: 48
- situation: A person describes a recent weekend trip to a friend.
- prompt_or_question: What did the speaker do immediately after having lunch?
- options: ["Walked around the city centre", "Took the train home", "Watched a film", "Visited a museum"]
- correct_index: 0
- correct_answer: Walked around the city centre
- rationale: The sequence marker "after that" directly follows the lunch description and precedes the city-centre walk.
- distractor_rationale: The other events did happen but at different points in the sequence, testing whether the listener tracks order rather than just content.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Four sequential events with explicit connectors ("first", "after that", "in the evening") support a clean sequence test.
- estimated_cefr_justification: Past simple narrative with multiple linked events, moderate transcript length, common everyday vocabulary.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Last weekend I visited my cousin in Leeds, since I hadn't seen her in almost a year. First, I took the train, which took about two hours and was surprisingly comfortable. When I arrived, we had lunch together at a small cafe near the station, and caught up on everything that had happened recently. After that, we walked around the city centre and visited an old market, where I bought a few small gifts for my family. In the evening, we watched a film at her flat and ordered pizza, before I took the last train home feeling really glad I'd made the trip.",
  "situation": "A person describes a recent weekend trip to a friend.",
  "question": "What did the speaker do immediately after having lunch?",
  "options": ["Walked around the city centre", "Took the train home", "Watched a film", "Visited a museum"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "sequence",
  "secondary_skill": null,
  "audio_context": "everyday_conversation",
  "discourse_type": "monologue",
  "rationale": "The sequence marker directly follows the lunch description.",
  "distractor_rationale": "Other events occurred but at different points in the sequence."
}
```

### ITEM LST-B1-05
- draft_id: LST-B1-05
- cefr_level: B1
- question_type: gap_fill
- listening_skill: following_instructions
- secondary_skill: sequence
- audio_context: shopping
- discourse_type: dialogue
- speakers: 2 (shop worker, new self-checkout user)
- transcript: "Excuse me, sorry to bother you, but how does this machine actually work? I've never used a self-checkout before." "No problem at all, it's easy once you get the hang of it. First, scan the barcode on each item, one at a time, and wait for the beep. Then place it straight into the bag area on your left. If it doesn't recognise something, just wait, the screen will tell you to try again or call for help. When you've scanned everything, press the green button on the screen to pay by card." "That's really helpful, thank you so much for explaining it all."
- transcript_word_count: 104
- target_duration_seconds: 48
- situation: A shop worker explains how to use a self-checkout machine.
- prompt_or_question: What should the customer press to pay?
- accepted_answers: ["green button", "the green button"]
- max_words: 3
- case_sensitive: false
- word_bank: null
- correct_answer: green button
- rationale: The final instruction states exactly which button to press to complete payment.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: No word bank at B1 per level guidance; the answer is a short, concrete, easily spelled phrase.
- estimated_cefr_justification: Multi-step instruction sequence with connectors ("first", "then", "when"), moderate transcript length.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Excuse me, sorry to bother you, but how does this machine actually work? I've never used a self-checkout before. No problem at all, it's easy once you get the hang of it. First, scan the barcode on each item, one at a time, and wait for the beep. Then place it straight into the bag area on your left. If it doesn't recognise something, just wait, the screen will tell you to try again or call for help. When you've scanned everything, press the green button on the screen to pay by card. That's really helpful, thank you so much for explaining it all.",
  "situation": "A shop worker explains how to use a self-checkout machine.",
  "prompt": "What should the customer press to pay?",
  "accepted_answers": ["green button", "the green button"],
  "max_words": 3,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "following_instructions",
  "secondary_skill": "sequence",
  "audio_context": "shopping",
  "discourse_type": "dialogue",
  "rationale": "The final instruction states exactly which button to press."
}
```

### ITEM LST-B1-06
- draft_id: LST-B1-06
- cefr_level: B1
- question_type: gap_fill
- listening_skill: number_time_price
- secondary_skill: reason_cause
- audio_context: work discussion
- discourse_type: dialogue
- speakers: 2 (colleagues handing over a task)
- transcript: "Before you leave, can you send me your notes on the Hamilton project? I want to look through them before tomorrow's call." "Sure, I'll send them over in a few minutes. Just so you know, the client needs the final report by next Wednesday now, not Friday as we originally planned, because their board meeting moved earlier than expected." "Oh, that changes things a bit. Okay, thanks for the heads up, I'll update my calendar and let the rest of the team know as well." "Good idea, it'll probably affect a few other deadlines too."
- transcript_word_count: 95
- target_duration_seconds: 44
- situation: One colleague hands over task details to another before leaving.
- prompt_or_question: By which day does the client now need the final report?
- accepted_answers: ["Wednesday", "next Wednesday"]
- max_words: 2
- case_sensitive: false
- word_bank: null
- correct_answer: Wednesday
- rationale: The speaker corrects the deadline explicitly, contrasting it with the previously expected day.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: "Not Friday" is included as a natural contrastive distractor within the transcript itself, testing careful listening rather than surface pattern-matching.
- estimated_cefr_justification: Requires distinguishing a corrected detail from a superseded one; moderate discourse length, workplace register.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Before you leave, can you send me your notes on the Hamilton project? I want to look through them before tomorrow's call. Sure, I'll send them over in a few minutes. Just so you know, the client needs the final report by next Wednesday now, not Friday as we originally planned, because their board meeting moved earlier than expected. Oh, that changes things a bit. Okay, thanks for the heads up, I'll update my calendar and let the rest of the team know as well. Good idea, it'll probably affect a few other deadlines too.",
  "situation": "One colleague hands over task details to another before leaving.",
  "prompt": "By which day does the client now need the final report?",
  "accepted_answers": ["Wednesday", "next Wednesday"],
  "max_words": 2,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": "reason_cause",
  "audio_context": "work_discussion",
  "discourse_type": "dialogue",
  "rationale": "The speaker corrects the deadline explicitly."
}
```

### ITEM LST-B1-07
- draft_id: LST-B1-07
- cefr_level: B1
- question_type: gap_fill
- listening_skill: explicit_detail
- secondary_skill: sequence
- audio_context: everyday conversation
- discourse_type: monologue
- speakers: 1 (person describing daily routine)
- transcript: "On a normal weekday, I wake up at half past six and go for a short run around the neighbourhood before it gets too busy outside. Then I have a quick breakfast, usually just toast and coffee, and leave for work at around eight fifteen. The commute takes about forty minutes if the traffic isn't too bad. I usually arrive at the office by nine, just before the morning meeting starts, which gives me a few minutes to check my emails and plan out the rest of the day before things get busy."
- transcript_word_count: 93
- target_duration_seconds: 43
- situation: A person describes their typical weekday morning routine.
- prompt_or_question: What time does the speaker usually arrive at the office?
- accepted_answers: ["nine", "9", "nine o'clock", "9 o'clock"]
- max_words: 2
- case_sensitive: false
- word_bank: null
- correct_answer: nine
- rationale: The arrival time is stated directly, distinct from the earlier wake-up and departure times. The transcript never states am/pm, so "am" variants are not required or accepted.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Three time markers appear in sequence; the item targets only the final one to test careful tracking rather than the first number heard.
- estimated_cefr_justification: Multiple sequential time references in a short personal narrative, moderate transcript length.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "On a normal weekday, I wake up at half past six and go for a short run around the neighbourhood before it gets too busy outside. Then I have a quick breakfast, usually just toast and coffee, and leave for work at around eight fifteen. The commute takes about forty minutes if the traffic isn't too bad. I usually arrive at the office by nine, just before the morning meeting starts, which gives me a few minutes to check my emails and plan out the rest of the day before things get busy.",
  "situation": "A person describes their typical weekday morning routine.",
  "prompt": "What time does the speaker usually arrive at the office?",
  "accepted_answers": ["nine", "9", "nine o'clock", "9 o'clock"],
  "max_words": 2,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": "sequence",
  "audio_context": "everyday_conversation",
  "discourse_type": "monologue",
  "rationale": "The arrival time is stated directly, distinct from earlier times mentioned; am/pm is never stated, so it is not required."
}
```

### ITEM LST-B1-08
- draft_id: LST-B1-08
- cefr_level: B1
- question_type: gap_fill
- listening_skill: explicit_detail
- secondary_skill: number_time_price
- audio_context: housing or community issue
- discourse_type: dialogue
- speakers: 2 (prospective tenant, landlord)
- transcript: "Hi, I'm calling about the flat you advertised near the university, the one-bedroom on the second floor." "Yes, that's right, it's available from the first of next month. Rent is six hundred pounds a month, including water, though gas and electricity are separate." "That sounds reasonable. Is it furnished, or would I need to bring my own furniture?" "It comes with a bed and a wardrobe, but the rest is unfurnished." "That sounds good. Can I come and see it this weekend?" "Sure, Saturday afternoon works well, shall we say two o'clock?"
- transcript_word_count: 92
- target_duration_seconds: 42
- situation: A prospective tenant enquires about renting a flat.
- prompt_or_question: How many pounds is the monthly rent?
- accepted_answers: ["600", "six hundred"]
- max_words: 2
- case_sensitive: false
- word_bank: null
- correct_answer: 600
- rationale: The landlord states the rent amount clearly and directly; the prompt already supplies "pounds", so only the number is required.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Includes an included utility detail ("including water") as background information not required for the answer, testing selective listening.
- estimated_cefr_justification: Everyday housing-enquiry register, one clear number among several details, moderate transcript length.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Hi, I'm calling about the flat you advertised near the university, the one-bedroom on the second floor. Yes, that's right, it's available from the first of next month. Rent is six hundred pounds a month, including water, though gas and electricity are separate. That sounds reasonable. Is it furnished, or would I need to bring my own furniture? It comes with a bed and a wardrobe, but the rest is unfurnished. That sounds good. Can I come and see it this weekend? Sure, Saturday afternoon works well, shall we say two o'clock?",
  "situation": "A prospective tenant enquires about renting a flat.",
  "prompt": "How many pounds is the monthly rent?",
  "accepted_answers": ["600", "six hundred"],
  "max_words": 2,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": "number_time_price",
  "audio_context": "housing_or_community_issue",
  "discourse_type": "dialogue",
  "rationale": "The landlord states the rent amount clearly and directly; the prompt already supplies the currency unit."
}
```

---

## B2 (6 new items: 3 MCQ + 3 Gap Fill)

### ITEM LST-B2-01
- draft_id: LST-B2-01
- cefr_level: B2
- question_type: mcq
- listening_skill: speaker_attitude
- secondary_skill: reason_cause
- audio_context: civic or media discussion
- discourse_type: discussion
- speakers: 2 (radio host, community caller)
- transcript: "We're talking today about the new parking charges in the town centre. Maria, you called in — what do you think?" "Well, I understand the council needs the income, and I know the roads do need repairing, but I think it's going to hurt small shop owners. My sister runs a bakery, and she's already noticed fewer people stopping by since the charges started, especially in the mornings when people used to pop in quickly on their way to work." "What would you have liked the council to do differently?" "Honestly, just talk to us first. A short trial period would have shown them a lot, and at least local businesses would have felt consulted rather than presented with a decision that was already made."
- transcript_word_count: 125
- target_duration_seconds: 58
- situation: A caller shares her view on new town-centre parking charges during a radio phone-in.
- prompt_or_question: What is the caller's overall attitude toward the new parking charges?
- options: ["Cautiously critical of how they were introduced", "Firmly opposed to any parking charges", "Fully supportive of the council's decision", "Indifferent, with no real opinion"]
- correct_index: 0
- correct_answer: Cautiously critical of how they were introduced
- rationale: The caller explicitly says she "understands" the need for income and the need for road repairs, but still raises a specific concern about consultation and impact on businesses like her sister's — a hedged, partial criticism rather than blanket opposition or support.
- distractor_rationale: "Firmly opposed" overstates her hedged language; "fully supportive" ignores her stated concern; "indifferent" contradicts her clear, detailed engagement with the topic.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Attitude is deliberately nuanced and hedged ("not against it entirely", "just concerned") rather than extreme, per audit guidance.
- estimated_cefr_justification: Requires synthesising attitude across multiple turns with hedged language and a follow-up confirmation question; moderate-length discourse.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "We're talking today about the new parking charges in the town centre. Maria, you called in — what do you think? Well, I understand the council needs the income, and I know the roads do need repairing, but I think it's going to hurt small shop owners. My sister runs a bakery, and she's already noticed fewer people stopping by since the charges started, especially in the mornings when people used to pop in quickly on their way to work. What would you have liked the council to do differently? Honestly, just talk to us first. A short trial period would have shown them a lot, and at least local businesses would have felt consulted rather than presented with a decision that was already made.",
  "situation": "A caller shares her view on new town-centre parking charges during a radio phone-in.",
  "question": "What is the caller's overall attitude toward the new parking charges?",
  "options": ["Cautiously critical of how they were introduced", "Firmly opposed to any parking charges", "Fully supportive of the council's decision", "Indifferent, with no real opinion"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "speaker_attitude",
  "secondary_skill": "reason_cause",
  "audio_context": "civic_or_media_discussion",
  "discourse_type": "discussion",
  "rationale": "The caller's hedged language shows partial, not blanket, criticism.",
  "distractor_rationale": "The other options overstate, invert, or ignore her nuanced position."
}
```

### ITEM LST-B2-02
- draft_id: LST-B2-02
- cefr_level: B2
- question_type: mcq
- listening_skill: reason_cause
- secondary_skill: inference
- audio_context: work discussion
- discourse_type: dialogue
- speakers: 2 (project manager, team member)
- transcript: "I wanted to give you a heads-up before the wider team meeting that the Kowalski launch is being pushed back two weeks." "Oh — is that because of the supplier issue we discussed last week?" "Partly. That's the main factor, since they still haven't confirmed the delivery date for the new materials, but we also want more time to test the packaging after the feedback from the pilot group, which raised a couple of small concerns." "That makes sense, better to get it right than rush it. Should I let the marketing team know so they can adjust the campaign schedule?" "Yes, please, before end of day if you can, so they have time to plan around it, and mention that we're aiming to confirm the exact date by Friday at the latest."
- transcript_word_count: 133
- target_duration_seconds: 61
- situation: A project manager explains a schedule change to a team member.
- prompt_or_question: What does the manager give as the main reason for the delay?
- options: ["A problem with the supplier", "A shortage of marketing staff", "Negative feedback about the product itself", "A change in company leadership"]
- correct_index: 0
- correct_answer: A problem with the supplier
- rationale: The manager confirms the supplier issue is "the main factor," while packaging testing is mentioned as an additional, secondary reason.
- distractor_rationale: "Negative feedback about the product" plausibly echoes the mention of "feedback from the pilot group," but the transcript specifies this feedback concerns packaging testing time, not negative product feedback; the other two options are unsupported.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Two reasons are given (supplier issue, packaging testing); the question targets the one explicitly marked as primary, testing careful weighting rather than surface recall.
- estimated_cefr_justification: Requires distinguishing a primary cause from a secondary contributing factor across natural, unscripted-sounding workplace dialogue.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "I wanted to give you a heads-up before the wider team meeting that the Kowalski launch is being pushed back two weeks. Oh — is that because of the supplier issue we discussed last week? Partly. That's the main factor, since they still haven't confirmed the delivery date for the new materials, but we also want more time to test the packaging after the feedback from the pilot group, which raised a couple of small concerns. That makes sense, better to get it right than rush it. Should I let the marketing team know so they can adjust the campaign schedule? Yes, please, before end of day if you can, so they have time to plan around it, and mention that we're aiming to confirm the exact date by Friday at the latest.",
  "situation": "A project manager explains a schedule change to a team member.",
  "question": "What does the manager give as the main reason for the delay?",
  "options": ["A problem with the supplier", "A shortage of marketing staff", "Negative feedback about the product itself", "A change in company leadership"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "reason_cause",
  "secondary_skill": "inference",
  "audio_context": "work_discussion",
  "discourse_type": "dialogue",
  "rationale": "The manager explicitly confirms the supplier issue as the main factor.",
  "distractor_rationale": "One distractor plausibly echoes a mentioned detail (pilot feedback) but misattributes its content; the others are unsupported."
}
```

### ITEM LST-B2-03
- draft_id: LST-B2-03
- cefr_level: B2
- question_type: mcq
- listening_skill: inference
- secondary_skill: implied_meaning
- audio_context: interview
- discourse_type: dialogue
- speakers: 2 (interviewer, small-business owner)
- transcript: "So you started this candle business two years ago, just as a small hobby in your spare room — how has that grown since then?" "It has, quite a bit actually, more than I ever expected when I started. I still have my full-time job, and I don't see myself giving that up lightly, but the orders have picked up so much over the last few months that I've started thinking seriously about what comes next for it, especially once the busier season starts." "Are you planning to leave your job, then, to focus on the business full-time?" "Let's just say I've started looking into what it would actually take, financially and otherwise, before I make any real decision either way."
- transcript_word_count: 121
- target_duration_seconds: 56
- situation: An interviewer talks with someone about a small side business.
- prompt_or_question: What does the business owner imply about her future plans?
- options: ["She may consider running the business full-time", "She has already resigned from her job", "She plans to close the business soon", "She has no interest in expanding further"]
- correct_index: 0
- correct_answer: She may consider running the business full-time
- rationale: Her non-committal reply ("let's just say I've started looking into what it would take") implies serious consideration without confirming a decision, and follows a direct question about leaving her job.
- distractor_rationale: "Already resigned" overstates her carefully hedged answer; "close the business" and "no interest in expanding" both contradict the described growth and her stated interest in "what comes next."
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: The correct answer is deliberately hedged rather than absolute, avoiding the audit's flagged "hedged correct vs absolute wrong" pattern by making two of the three distractors also somewhat plausible-sounding rather than obviously extreme.
- estimated_cefr_justification: Requires inference from an evasive, indirect answer rather than an explicit statement; natural interview register.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "So you started this candle business two years ago, just as a small hobby in your spare room — how has that grown since then? It has, quite a bit actually, more than I ever expected when I started. I still have my full-time job, and I don't see myself giving that up lightly, but the orders have picked up so much over the last few months that I've started thinking seriously about what comes next for it, especially once the busier season starts. Are you planning to leave your job, then, to focus on the business full-time? Let's just say I've started looking into what it would actually take, financially and otherwise, before I make any real decision either way.",
  "situation": "An interviewer talks with someone about a small side business.",
  "question": "What does the business owner imply about her future plans?",
  "options": ["She may consider running the business full-time", "She has already resigned from her job", "She plans to close the business soon", "She has no interest in expanding further"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "inference",
  "secondary_skill": "implied_meaning",
  "audio_context": "interview",
  "discourse_type": "dialogue",
  "rationale": "Her hedged, non-committal reply implies serious consideration without confirming a decision.",
  "distractor_rationale": "Other options overstate or contradict her carefully hedged answer and the described growth."
}
```

### ITEM LST-B2-04
- draft_id: LST-B2-04
- cefr_level: B2
- question_type: gap_fill
- listening_skill: number_time_price
- secondary_skill: (none)
- audio_context: work discussion
- discourse_type: dialogue
- speakers: 2 (colleagues discussing a budget)
- transcript: "Have you seen the updated budget for the office renovation? It came through this morning." "Yes, I noticed it went up quite a bit, from eighteen thousand to twenty-two thousand." "Right, mostly because of the flooring costs, apparently the original quote didn't include the underlay. We need to get sign-off from finance before we can proceed with ordering anything, and every week we delay pushes the whole schedule back further." "That's a fair point. Could you also mention we might want a small contingency built in, in case there are other surprises like this one?" "Good idea, I'll add that to the agenda as well, so it doesn't come up again halfway through the project, and we can present it as one clear request rather than several small ones."
- transcript_word_count: 129
- target_duration_seconds: 60
- situation: Two colleagues discuss a revised project budget.
- prompt_or_question: What is the new total budget for the renovation?
- accepted_answers: ["twenty-two thousand", "22,000", "22000"]
- max_words: 2
- case_sensitive: false
- word_bank: null
- correct_answer: twenty-two thousand
- rationale: The updated figure is stated directly, distinguished from the earlier, superseded figure. No currency is stated in the transcript, so none is required in the answer.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Two figures are mentioned (old and new); the item targets only the updated one, testing tracking of a correction rather than first-number recall.
- estimated_cefr_justification: Requires distinguishing a superseded figure from a current one within a natural workplace exchange.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Have you seen the updated budget for the office renovation? It came through this morning. Yes, I noticed it went up quite a bit, from eighteen thousand to twenty-two thousand. Right, mostly because of the flooring costs, apparently the original quote didn't include the underlay. We need to get sign-off from finance before we can proceed with ordering anything, and every week we delay pushes the whole schedule back further. That's a fair point. Could you also mention we might want a small contingency built in, in case there are other surprises like this one? Good idea, I'll add that to the agenda as well, so it doesn't come up again halfway through the project, and we can present it as one clear request rather than several small ones.",
  "situation": "Two colleagues discuss a revised project budget.",
  "prompt": "What is the new total budget for the renovation?",
  "accepted_answers": ["twenty-two thousand", "22,000", "22000"],
  "max_words": 2,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": null,
  "audio_context": "work_discussion",
  "discourse_type": "dialogue",
  "rationale": "The updated figure is stated directly, distinguished from the superseded one; no currency is stated, so none is required."
}
```

### ITEM LST-B2-05
- draft_id: LST-B2-05
- cefr_level: B2
- question_type: gap_fill
- listening_skill: explicit_detail
- secondary_skill: (none)
- audio_context: civic or media discussion
- discourse_type: monologue
- speakers: 1 (local radio announcer)
- transcript: "In local news this morning, the city council has confirmed that the new community library on Elm Street will finally open to the public on the fourteenth of March. The project, which was delayed twice by funding issues over the past two years, will include a dedicated children's reading room, several study spaces, and a small cafe run by a local charity. Councillors say the opening will be marked with a small community event that morning, and residents are being encouraged to attend, with free activities planned for younger visitors throughout the day. A full programme of events will be published on the council's website closer to the date, and volunteers are still being sought to help run some of the opening-day activities."
- transcript_word_count: 123
- target_duration_seconds: 57
- situation: A local radio announcer reports a community news item.
- prompt_or_question: On what date will the new library open?
- accepted_answers: ["14th of March", "March 14th", "March 14", "14 March", "the 14th"]
- max_words: 3
- case_sensitive: false
- word_bank: null
- correct_answer: 14th of March
- rationale: The opening date is stated explicitly as a specific fact within the news report.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Word bank omitted per B2 guidance; multiple date-format variants are explicitly authored to avoid penalising reasonable phrasing differences.
- estimated_cefr_justification: Radio-news register with moderate information density; one clearly extractable date among several supporting details.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "In local news this morning, the city council has confirmed that the new community library on Elm Street will finally open to the public on the fourteenth of March. The project, which was delayed twice by funding issues over the past two years, will include a dedicated children's reading room, several study spaces, and a small cafe run by a local charity. Councillors say the opening will be marked with a small community event that morning, and residents are being encouraged to attend, with free activities planned for younger visitors throughout the day. A full programme of events will be published on the council's website closer to the date, and volunteers are still being sought to help run some of the opening-day activities.",
  "situation": "A local radio announcer reports a community news item.",
  "prompt": "On what date will the new library open?",
  "accepted_answers": ["14th of March", "March 14th", "March 14", "14 March", "the 14th"],
  "max_words": 3,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": null,
  "audio_context": "civic_or_media_discussion",
  "discourse_type": "monologue",
  "rationale": "The opening date is stated explicitly as a specific fact."
}
```

### ITEM LST-B2-06
- draft_id: LST-B2-06
- cefr_level: B2
- question_type: gap_fill
- listening_skill: following_instructions
- secondary_skill: understanding_explanation
- audio_context: work discussion
- discourse_type: dialogue
- speakers: 2 (office manager, new employee)
- transcript: "One more thing before you start — for any expense claim over fifty pounds, you'll need to attach a scanned receipt and get approval from your line manager before submitting it through the portal. That approval step usually takes a day or two, so try to submit things early if you can, especially near the end of the month when things get busier for the finance team." "Got it. And for anything under fifty?" "Just the receipt is fine, no approval needed, the system will process it automatically within a few days." "That's really clear, thanks for walking me through it, it sounds simpler than I expected, and I'll make sure to keep my receipts organised from now on so nothing gets lost before the deadline."
- transcript_word_count: 126
- target_duration_seconds: 58
- situation: An office manager explains the expense claims process to a new employee.
- prompt_or_question: What must be attached to any expense claim over fifty pounds?
- accepted_answers: ["scanned receipt", "a scanned receipt", "receipt"]
- max_words: 3
- case_sensitive: false
- word_bank: null
- correct_answer: scanned receipt
- rationale: The requirement is stated directly as part of the explained procedure.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: A threshold-based rule (over/under fifty pounds) requires the listener to track which branch of the instruction applies to the question asked.
- estimated_cefr_justification: Conditional-style procedural explanation with a numeric threshold; moderate discourse length, workplace register.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "One more thing before you start — for any expense claim over fifty pounds, you'll need to attach a scanned receipt and get approval from your line manager before submitting it through the portal. That approval step usually takes a day or two, so try to submit things early if you can, especially near the end of the month when things get busier for the finance team. Got it. And for anything under fifty? Just the receipt is fine, no approval needed, the system will process it automatically within a few days. That's really clear, thanks for walking me through it, it sounds simpler than I expected, and I'll make sure to keep my receipts organised from now on so nothing gets lost before the deadline.",
  "situation": "An office manager explains the expense claims process to a new employee.",
  "prompt": "What must be attached to any expense claim over fifty pounds?",
  "accepted_answers": ["scanned receipt", "a scanned receipt", "receipt"],
  "max_words": 3,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "following_instructions",
  "secondary_skill": "understanding_explanation",
  "audio_context": "work_discussion",
  "discourse_type": "dialogue",
  "rationale": "The requirement is stated directly as part of the explained procedure."
}
```

---

## C1 (6 new items: 3 MCQ + 3 Gap Fill)

### ITEM LST-C1-01
- draft_id: LST-C1-01
- cefr_level: C1
- question_type: mcq
- listening_skill: following_argument
- secondary_skill: reason_cause
- audio_context: civic or media discussion
- discourse_type: discussion
- speakers: 2 (podcast host, urban planner)
- transcript: "There's a lot of talk about remote work reshaping our cities. Do you buy that?" "To some extent, yes, but I think the story is more complicated than 'everyone left the office, so city centres are dying.' What we're actually seeing is a redistribution rather than a collapse. Some neighbourhoods that were purely commercial are struggling, sure, but residential areas nearby are seeing more daytime footfall than they ever had, because people are working from cafes and local spaces instead of commuting downtown. So the challenge for planners isn't reversing remote work, it's rethinking which areas need investment now." "So you'd say the problem is more about mismatched infrastructure than shrinking demand overall?" "Exactly — that's a much better way to put it." "Does that mean the investment priorities most cities have now are essentially outdated?" "In a lot of cases, yes. Transport budgets, for instance, are often still built around the old nine-to-five commuting pattern, when the actual demand has shifted to a much more spread-out schedule throughout the day."
- transcript_word_count: 171
- target_duration_seconds: 79
- situation: A podcast host discusses the effects of remote work on cities with an urban planner.
- prompt_or_question: What is the planner's main argument about remote work's effect on cities?
- options: ["Demand has shifted location rather than disappeared", "City centres are finished for good", "Remote work has had no real effect on any neighbourhood", "Only commercial districts have been affected at all"]
- correct_index: 0
- correct_answer: Demand has shifted location rather than disappeared
- rationale: The planner explicitly frames this as "redistribution rather than a collapse," and the host's paraphrase ("mismatched infrastructure than shrinking demand") is confirmed as accurate.
- distractor_rationale: "Permanently and completely finished" and "no real effect... at all" both use extreme wording the speaker explicitly rejects; "only commercial districts" ignores the residential-footfall point.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: The argument is built across several sentences with a qualifying clause ("more complicated than..."), requiring the listener to follow a chain of reasoning rather than spot one key phrase.
- estimated_cefr_justification: Extended discourse with subordinate clauses, a rhetorical contrast structure, and a paraphrase-confirmation exchange typical of C1 argument-following tasks.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "There's a lot of talk about remote work reshaping our cities. Do you buy that? To some extent, yes, but I think the story is more complicated than 'everyone left the office, so city centres are dying.' What we're actually seeing is a redistribution rather than a collapse. Some neighbourhoods that were purely commercial are struggling, sure, but residential areas nearby are seeing more daytime footfall than they ever had, because people are working from cafes and local spaces instead of commuting downtown. So the challenge for planners isn't reversing remote work, it's rethinking which areas need investment now. So you'd say the problem is more about mismatched infrastructure than shrinking demand overall? Exactly — that's a much better way to put it. Does that mean the investment priorities most cities have now are essentially outdated? In a lot of cases, yes. Transport budgets, for instance, are often still built around the old nine-to-five commuting pattern, when the actual demand has shifted to a much more spread-out schedule throughout the day.",
  "situation": "A podcast host discusses the effects of remote work on cities with an urban planner.",
  "question": "What is the planner's main argument about remote work's effect on cities?",
  "options": ["Demand has shifted location rather than disappeared", "City centres are finished for good", "Remote work has had no real effect on any neighbourhood", "Only commercial districts have been affected at all"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "following_argument",
  "secondary_skill": "reason_cause",
  "audio_context": "civic_or_media_discussion",
  "discourse_type": "discussion",
  "rationale": "The planner frames the change as redistribution rather than collapse, confirmed by the host's paraphrase.",
  "distractor_rationale": "Extreme-wording options are explicitly rejected by the speaker; one ignores the residential-footfall point."
}
```

### ITEM LST-C1-02
- draft_id: LST-C1-02
- cefr_level: C1
- question_type: mcq
- listening_skill: implied_meaning
- secondary_skill: speaker_attitude
- audio_context: educational explanation
- discourse_type: discussion
- speakers: 2 (education journalist, headteacher)
- transcript: "As education correspondent, I've been speaking to headteachers across the region about this. There's been a lot of debate about reducing exam-based assessment in favour of coursework. As a headteacher, where do you stand?" "I think coursework has real value, particularly for showing sustained effort. That said, I'd be cautious about any change that isn't backed by proper moderation, because we've seen, historically, how inconsistent grading between schools can undermine trust in the whole system. I'm not against reform — far from it — but I'd want to see the safeguards in place before we move too quickly." "So it sounds like the timeline concerns you more than the idea itself." "That's a fair way of putting it, yes. Do you think other headteachers share that view? Many do, in my experience, though there's always a vocal minority who feel any delay is really just resistance to change dressed up as caution. I don't think that's a fair characterisation in most cases, but I understand why it gets made."
- transcript_word_count: 169
- target_duration_seconds: 78
- situation: An education journalist interviews a headteacher about assessment reform.
- prompt_or_question: What does the headteacher imply about her position on the reform?
- options: ["She supports the idea but worries about how quickly it is introduced", "She is firmly opposed to any coursework-based assessment", "She believes moderation problems make reform impossible", "She has no real opinion on the proposed changes"]
- correct_index: 0
- correct_answer: She supports the idea but worries about how quickly it is introduced
- rationale: She states she is "not against reform — far from it" while raising a specific concern about safeguards and pacing, and confirms the interviewer's paraphrase about timeline concern.
- distractor_rationale: "Firmly opposed" contradicts her explicit statement; "impossible" overstates a caution about moderation into an absolute claim; "no real opinion" ignores her clearly stated, detailed position.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Implied stance requires combining an explicit disclaimer ("not against reform") with a hedged caveat, rather than a single quotable line.
- estimated_cefr_justification: Layered discourse with concession structures ("that said", "far from it") typical of nuanced C1 opinion-tracking tasks.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "As education correspondent, I've been speaking to headteachers across the region about this. There's been a lot of debate about reducing exam-based assessment in favour of coursework. As a headteacher, where do you stand? I think coursework has real value, particularly for showing sustained effort. That said, I'd be cautious about any change that isn't backed by proper moderation, because we've seen, historically, how inconsistent grading between schools can undermine trust in the whole system. I'm not against reform — far from it — but I'd want to see the safeguards in place before we move too quickly. So it sounds like the timeline concerns you more than the idea itself. That's a fair way of putting it, yes. Do you think other headteachers share that view? Many do, in my experience, though there's always a vocal minority who feel any delay is really just resistance to change dressed up as caution. I don't think that's a fair characterisation in most cases, but I understand why it gets made.",
  "situation": "An education journalist interviews a headteacher about assessment reform.",
  "question": "What does the headteacher imply about her position on the reform?",
  "options": ["She supports the idea but worries about how quickly it is introduced", "She is firmly opposed to any coursework-based assessment", "She believes moderation problems make reform impossible", "She has no real opinion on the proposed changes"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "implied_meaning",
  "secondary_skill": "speaker_attitude",
  "audio_context": "educational_explanation",
  "discourse_type": "discussion",
  "rationale": "She explicitly is not against reform but flags a pacing/safeguard concern, confirmed by the interviewer's paraphrase.",
  "distractor_rationale": "Other options contradict, overstate, or ignore her clearly stated nuanced position."
}
```

### ITEM LST-C1-03
- draft_id: LST-C1-03
- cefr_level: C1
- question_type: mcq
- listening_skill: relationship_between_speakers
- secondary_skill: speaker_attitude
- audio_context: work discussion
- discourse_type: dialogue
- speakers: 2 (two colleagues on a project team)
- transcript: "I looked over the draft you sent, and I have to say, I think we need to rework the client-facing summary before it goes out." "Really? I thought it captured the main points fine." "It does cover them, but the tone reads a bit informal for this particular client — they've been quite traditional in previous correspondence. I'd suggest we tighten the language a little." "Fair enough, I can see that. I'll take another pass at it this afternoon." "Great, and let me know if you want a second opinion before you send it. Actually, that would be helpful, thank you. I sometimes find it hard to judge tone in written work, especially with clients I haven't met in person. That's completely understandable, it's one of the trickier parts of this job. I'll take a look this afternoon and send you a few suggestions, nothing major, just some phrasing adjustments. It's a good reminder that even small stylistic choices can affect how a message lands with a client we don't see face to face very often."
- transcript_word_count: 176
- target_duration_seconds: 81
- situation: Two colleagues review a client-facing document before sending it.
- prompt_or_question: What best describes the relationship and dynamic between the two speakers?
- options: ["Peers offering constructive, respectful feedback to one another", "A manager formally reprimanding a junior employee", "Two strangers meeting for the first time", "Competitors trying to undermine each other's work"]
- correct_index: 0
- correct_answer: Peers offering constructive, respectful feedback to one another
- rationale: The tone is collaborative throughout ("I can see that", "let me know if you want a second opinion"), with disagreement expressed diplomatically rather than as a directive from a clear authority figure.
- distractor_rationale: "Formally reprimanding" mismatches the mutual, hedged tone; "strangers" contradicts the familiarity with each other's work; "competitors... undermine" contradicts the offer of further help.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: No job titles are stated; the relationship must be inferred purely from register, hedging, and the collaborative closing offer.
- estimated_cefr_justification: Subtle interpersonal dynamic conveyed through diplomatic hedging and professional register rather than explicit labels.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "I looked over the draft you sent, and I have to say, I think we need to rework the client-facing summary before it goes out. Really? I thought it captured the main points fine. It does cover them, but the tone reads a bit informal for this particular client — they've been quite traditional in previous correspondence. I'd suggest we tighten the language a little. Fair enough, I can see that. I'll take another pass at it this afternoon. Great, and let me know if you want a second opinion before you send it. Actually, that would be helpful, thank you. I sometimes find it hard to judge tone in written work, especially with clients I haven't met in person. That's completely understandable, it's one of the trickier parts of this job. I'll take a look this afternoon and send you a few suggestions, nothing major, just some phrasing adjustments. It's a good reminder that even small stylistic choices can affect how a message lands with a client we don't see face to face very often.",
  "situation": "Two colleagues review a client-facing document before sending it.",
  "question": "What best describes the relationship and dynamic between the two speakers?",
  "options": ["Peers offering constructive, respectful feedback to one another", "A manager formally reprimanding a junior employee", "Two strangers meeting for the first time", "Competitors trying to undermine each other's work"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "relationship_between_speakers",
  "secondary_skill": "speaker_attitude",
  "audio_context": "work_discussion",
  "discourse_type": "dialogue",
  "rationale": "Collaborative, hedged tone and an offer of further help indicate respectful peer feedback.",
  "distractor_rationale": "Other options mismatch the mutual, non-hierarchical, collaborative register."
}
```

### ITEM LST-C1-04
- draft_id: LST-C1-04
- cefr_level: C1
- question_type: gap_fill
- listening_skill: understanding_explanation
- secondary_skill: (none)
- audio_context: academic-style explanation
- discourse_type: monologue
- speakers: 1 (guest lecturer)
- transcript: "Before we look at the case study, it's worth explaining briefly how the certification process works. A product first goes through internal testing by the manufacturer. Once that's complete, an independent inspector reviews the results and, if satisfied, issues a provisional certificate. Only after a follow-up inspection, usually conducted around six months later, is the certificate made permanent. This two-stage approach exists because a single inspection, however thorough, can't capture how a product performs once it's actually being manufactured at scale and used in real conditions over time. The provisional period allows regulators to catch issues that only emerge after a product has been in circulation for a while, which is precisely the kind of problem a one-off test would likely miss entirely. It's a more cautious system than some manufacturers would prefer, since it delays full approval, but it has significantly reduced the number of products recalled after release compared with the previous single-inspection model. Understanding this distinction matters for what we'll discuss next."
- transcript_word_count: 165
- target_duration_seconds: 76
- situation: A guest lecturer explains a certification process before discussing a case study.
- prompt_or_question: Roughly how many months after the provisional certificate is the follow-up inspection usually conducted?
- accepted_answers: ["six", "6"]
- max_words: 1
- case_sensitive: false
- word_bank: null
- correct_answer: six
- rationale: The timeframe for the follow-up inspection is stated as a specific, extractable fact within the explanation; the prompt already supplies "months", so only the number is required.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: The explanation describes a multi-step process, but the question isolates one concrete, factual detail rather than requiring synthesis of the whole procedure — appropriate for Gap Fill even at C1.
- estimated_cefr_justification: Formal explanatory register with sequential technical steps, though the tested detail itself remains simple and explicit.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Before we look at the case study, it's worth explaining briefly how the certification process works. A product first goes through internal testing by the manufacturer. Once that's complete, an independent inspector reviews the results and, if satisfied, issues a provisional certificate. Only after a follow-up inspection, usually conducted around six months later, is the certificate made permanent. This two-stage approach exists because a single inspection, however thorough, can't capture how a product performs once it's actually being manufactured at scale and used in real conditions over time. The provisional period allows regulators to catch issues that only emerge after a product has been in circulation for a while, which is precisely the kind of problem a one-off test would likely miss entirely. It's a more cautious system than some manufacturers would prefer, since it delays full approval, but it has significantly reduced the number of products recalled after release compared with the previous single-inspection model. Understanding this distinction matters for what we'll discuss next.",
  "situation": "A guest lecturer explains a certification process before discussing a case study.",
  "prompt": "Roughly how many months after the provisional certificate is the follow-up inspection usually conducted?",
  "accepted_answers": ["six", "6"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "understanding_explanation",
  "secondary_skill": null,
  "audio_context": "academic_style_explanation",
  "discourse_type": "monologue",
  "rationale": "The follow-up timeframe is stated as a specific, extractable fact; the prompt already supplies the time unit."
}
```

### ITEM LST-C1-05
- draft_id: LST-C1-05
- cefr_level: C1
- question_type: gap_fill
- listening_skill: explicit_detail
- secondary_skill: (none)
- audio_context: civic or media discussion
- discourse_type: discussion
- speakers: 2 (journalist, city official)
- transcript: "The council has faced criticism over the cycling lane expansion. Can you tell us how much has actually been spent so far?" "As of this quarter, the total spend stands at four hundred and thirty thousand pounds, out of an approved budget of six hundred thousand. The remaining work, mainly signage and junction adjustments, is expected to be completed by the autumn." "And has ridership increased as a result?" "Early figures are encouraging, though we'll have a fuller picture once the full network is finished." "When is that expected to be complete?" "The final phase, connecting the two remaining neighbourhoods, is scheduled for next spring, assuming there are no further delays with land agreements. Once that's done, we'll be able to properly compare ridership before and after across the whole route, rather than relying on the partial data we have now, which only covers about two-thirds of the planned network at the moment, so any comparison right now would understate the eventual impact."
- transcript_word_count: 163
- target_duration_seconds: 75
- situation: A journalist questions a city official about a public infrastructure project's spending.
- prompt_or_question: How many pounds have been spent on the project so far, according to the official?
- accepted_answers: ["430,000", "430000"]
- max_words: 1
- case_sensitive: false
- word_bank: null
- correct_answer: 430,000
- rationale: The official states the current spend explicitly, distinct from the total approved budget mentioned immediately after; the prompt already supplies "pounds", so only the number is required.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Two monetary figures appear close together (spend vs. total budget); the item targets only the first, testing precise tracking under moderate information density.
- estimated_cefr_justification: Two closely-placed numerical figures within a formal civic-accountability register, requiring precise discrimination.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "The council has faced criticism over the cycling lane expansion. Can you tell us how much has actually been spent so far? As of this quarter, the total spend stands at four hundred and thirty thousand pounds, out of an approved budget of six hundred thousand. The remaining work, mainly signage and junction adjustments, is expected to be completed by the autumn. And has ridership increased as a result? Early figures are encouraging, though we'll have a fuller picture once the full network is finished. When is that expected to be complete? The final phase, connecting the two remaining neighbourhoods, is scheduled for next spring, assuming there are no further delays with land agreements. Once that's done, we'll be able to properly compare ridership before and after across the whole route, rather than relying on the partial data we have now, which only covers about two-thirds of the planned network at the moment, so any comparison right now would understate the eventual impact.",
  "situation": "A journalist questions a city official about a public infrastructure project's spending.",
  "prompt": "How many pounds have been spent on the project so far, according to the official?",
  "accepted_answers": ["430,000", "430000"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "explicit_detail",
  "secondary_skill": null,
  "audio_context": "civic_or_media_discussion",
  "discourse_type": "discussion",
  "rationale": "The current spend figure is stated explicitly, distinct from the total budget; the prompt already supplies the currency unit."
}
```

### ITEM LST-C1-06
- draft_id: LST-C1-06
- cefr_level: C1
- question_type: gap_fill
- listening_skill: reason_cause
- secondary_skill: (none)
- audio_context: work discussion
- discourse_type: monologue
- speakers: 1 (department head giving a brief update)
- transcript: "A quick update before we close the meeting: the rollout of the new booking system has been paused for two weeks. This isn't due to the software itself, which has tested well, but because our support team is currently short-staffed after two recent departures, and we don't want to launch without adequate cover for user queries. We'll confirm the new launch date once recruitment is finalised. In the meantime, the current system will remain in place, so there's no disruption to daily operations, and customers won't notice any change on their end. I know some of you have already blocked out time for the transition, so I'd ask you to hold off on rescheduling anything until we have a confirmed date, which I expect to share within the next week or so, once we've confirmed the final start dates with the two candidates we're hoping to bring on board, both of whom have already accepted our offer verbally and are just finalising their notice periods."
- transcript_word_count: 165
- target_duration_seconds: 76
- situation: A department head gives a brief status update at the end of a meeting.
- prompt_or_question: What is the actual reason given for pausing the system rollout?
- accepted_answers: ["short-staffed support team", "staff shortage", "short staffing", "understaffed support team"]
- max_words: 3
- case_sensitive: false
- word_bank: null
- correct_answer: short-staffed support team
- rationale: The speaker explicitly rules out the software as the cause and names staffing levels as the actual reason.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: The transcript explicitly rules out one plausible cause (software) before stating the real one, testing whether the listener tracks the correction rather than the first-mentioned topic.
- estimated_cefr_justification: Contrastive cause structure ("isn't due to X... but because Y") typical of C1-level reasoning; the extractable answer itself remains a short factual phrase.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "A quick update before we close the meeting: the rollout of the new booking system has been paused for two weeks. This isn't due to the software itself, which has tested well, but because our support team is currently short-staffed after two recent departures, and we don't want to launch without adequate cover for user queries. We'll confirm the new launch date once recruitment is finalised. In the meantime, the current system will remain in place, so there's no disruption to daily operations, and customers won't notice any change on their end. I know some of you have already blocked out time for the transition, so I'd ask you to hold off on rescheduling anything until we have a confirmed date, which I expect to share within the next week or so, once we've confirmed the final start dates with the two candidates we're hoping to bring on board, both of whom have already accepted our offer verbally and are just finalising their notice periods.",
  "situation": "A department head gives a brief status update at the end of a meeting.",
  "prompt": "What is the actual reason given for pausing the system rollout?",
  "accepted_answers": ["short-staffed support team", "staff shortage", "short staffing", "understaffed support team"],
  "max_words": 3,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "reason_cause",
  "secondary_skill": null,
  "audio_context": "work_discussion",
  "discourse_type": "monologue",
  "rationale": "The speaker rules out the software and names staffing as the actual cause."
}
```

---

## C2 (6 new items: 3 MCQ + 3 Gap Fill)

### ITEM LST-C2-01
- draft_id: LST-C2-01
- cefr_level: C2
- question_type: mcq
- listening_skill: following_argument
- secondary_skill: reason_cause
- audio_context: civic or media discussion
- discourse_type: discussion
- speakers: 2 (podcast host, technology ethicist)
- transcript: "There's a persistent idea that social media platforms end up addictive almost by accident, as a side effect of trying to keep people engaged. Does that framing hold up, in your view?" "Not really, and I think it lets the industry off too lightly. What we're actually looking at is a set of deliberate design choices, refined over years of testing, optimised specifically to maximise time on screen rather than to serve any goal the user actually stated. Infinite scroll, unpredictable reward timing, notification badges — these aren't accidental byproducts. They're closer to the mechanics you'd find in a slot machine, built by teams who understood precisely what they were doing. That's not to say every individual designer set out with bad intentions, but the systems themselves were shaped by an incentive structure — advertising revenue tied to attention — that rewards exactly this kind of design regardless of anyone's personal ethics." "But surely individual designers still bear some responsibility for choices they personally made?" "To some degree, sure, but focusing there misses the bigger lever. Change how a platform makes its money, and the design incentives shift with it, regardless of who's sitting at the keyboard. That's what actually moves the needle, far more than any individual designer's conscience." "Is there any realistic path to changing that model, or are we stuck with it?" "There are experiments — subscription-based platforms without ads, for instance — but none has matched the scale of the advertising giants yet. Regulation could accelerate that shift, particularly rules that limit how granular the targeting can be, since that's really what makes the current model so lucrative and so relentless in its pursuit of attention."
- transcript_word_count: 280
- target_duration_seconds: 129
- situation: A podcast host and a technology ethicist discuss whether addictive app design is intentional.
- prompt_or_question: What is the ethicist's central argument about why social media apps are addictive?
- options: ["Deliberate design choices, driven by the advertising business model, are responsible", "Individual designers intentionally set out to harm users personally", "Addictiveness is a random accident with no identifiable cause", "The technology itself makes engagement-focused design unavoidable"]
- correct_index: 0
- correct_answer: Deliberate design choices, driven by the advertising business model, are responsible
- rationale: The ethicist explicitly rejects the "accident" framing and traces the design choices back to the advertising-revenue incentive structure; when challenged that individual designers bear responsibility, she concedes only a minor point before reasserting that the business model is the real lever.
- distractor_rationale: "Individual designers... intentionally... harm users personally" is explicitly rejected by the speaker (and only a small, hedged concession is made, not full responsibility); "random accident" is the exact framing the ethicist argues against; "technology... unavoidable" ignores the speaker's point that changing the business model changes the incentives.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Restructured during content cleanup to replace a paraphrase-then-confirmation exchange with a challenge-and-rebuttal exchange, so the listener must track a concession-and-return-to-thesis move rather than a simple restatement. The argument still depends on the listener following a chain of reasoning (rejecting one framing, proposing an alternative, tying it to incentives, defending it under challenge) rather than a single stated conclusion.
- estimated_cefr_justification: Long, dense turns with subordinate clauses, rhetorical structure ("that's not to say... but"), a direct challenge-and-rebuttal exchange, and abstract argumentation about systems and incentives — appropriate for C2.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "There's a persistent idea that social media platforms end up addictive almost by accident, as a side effect of trying to keep people engaged. Does that framing hold up, in your view? Not really, and I think it lets the industry off too lightly. What we're actually looking at is a set of deliberate design choices, refined over years of testing, optimised specifically to maximise time on screen rather than to serve any goal the user actually stated. Infinite scroll, unpredictable reward timing, notification badges — these aren't accidental byproducts. They're closer to the mechanics you'd find in a slot machine, built by teams who understood precisely what they were doing. That's not to say every individual designer set out with bad intentions, but the systems themselves were shaped by an incentive structure — advertising revenue tied to attention — that rewards exactly this kind of design regardless of anyone's personal ethics. But surely individual designers still bear some responsibility for choices they personally made? To some degree, sure, but focusing there misses the bigger lever. Change how a platform makes its money, and the design incentives shift with it, regardless of who's sitting at the keyboard. That's what actually moves the needle, far more than any individual designer's conscience. Is there any realistic path to changing that model, or are we stuck with it? There are experiments — subscription-based platforms without ads, for instance — but none has matched the scale of the advertising giants yet. Regulation could accelerate that shift, particularly rules that limit how granular the targeting can be, since that's really what makes the current model so lucrative and so relentless in its pursuit of attention.",
  "situation": "A podcast host and a technology ethicist discuss whether addictive app design is intentional.",
  "question": "What is the ethicist's central argument about why social media apps are addictive?",
  "options": ["Deliberate design choices, driven by the advertising business model, are responsible", "Individual designers intentionally set out to harm users personally", "Addictiveness is a random accident with no identifiable cause", "The technology itself makes engagement-focused design unavoidable"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "following_argument",
  "secondary_skill": "reason_cause",
  "audio_context": "civic_or_media_discussion",
  "discourse_type": "discussion",
  "rationale": "The ethicist rejects the accident framing and ties the design to the advertising incentive structure, conceding only a minor point under challenge before reasserting her thesis.",
  "distractor_rationale": "Other options are explicitly rejected, restate the rejected framing, or ignore the incentive-based argument."
}
```

### ITEM LST-C2-02
- draft_id: LST-C2-02
- cefr_level: C2
- question_type: mcq
- listening_skill: implied_meaning
- secondary_skill: speaker_attitude
- audio_context: interview
- discourse_type: dialogue
- speakers: 2 (interviewer, nutrition scientist)
- transcript: "Your recent research got a lot of media attention for questioning some very popular dietary advice. How do you feel about how it was reported?" "Mixed feelings, honestly. The underlying study was fairly narrow — it looked at one specific population over a relatively short period, and the effect size, while statistically significant, was modest. What ended up in the headlines was a much bolder claim than anything we actually demonstrated. I understand why that happens; nuance doesn't travel as well as a punchy headline. But I do worry that people will now either overcorrect based on a claim we never made, or dismiss the finding entirely once a more cautious follow-up study inevitably tempers it. Neither reaction would reflect what the data actually shows." "So if you could rewrite the headline yourself, what would it say?" "Something considerably less exciting, I'm afraid — probably starting with 'preliminary evidence suggests', which is exactly the phrase that never survives into print. Do you think the scientific community bears any responsibility for how these stories get simplified? To some extent, yes. We could be clearer in our own summaries, and some press releases from universities are, frankly, guilty of overselling their own research to attract coverage. But the incentive structures on both sides, ours and the media's, tend to reward the bolder claim, so I don't think this is a problem either side can fix alone."
- transcript_word_count: 234
- target_duration_seconds: 108
- situation: A nutrition scientist is interviewed about media coverage of her recent study.
- prompt_or_question: What does the scientist imply about the media coverage of her research?
- options: ["It overstated findings that were actually modest and preliminary", "It was a fair and accurate summary of her conclusions", "It failed to mention the study at all", "It focused on a different, unrelated piece of research"]
- correct_index: 0
- correct_answer: It overstated findings that were actually modest and preliminary
- rationale: She describes the study as "fairly narrow" with a "modest" effect, contrasted with "a much bolder claim than anything we actually demonstrated," and jokes that an accurate headline would need to start with "preliminary evidence suggests."
- distractor_rationale: "Completely accurate" directly contradicts her stated concern; "failed to mention... at all" and "unrelated research" are not consistent with a scientist actively discussing coverage of her own study.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: The implication is built through understatement and a closing ironic remark rather than a direct complaint, testing whether the listener can read tone alongside content.
- estimated_cefr_justification: Nuanced self-reflective commentary, hedged evaluative language, and closing irony — discourse features typical of C2 implied-meaning tasks.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "Your recent research got a lot of media attention for questioning some very popular dietary advice. How do you feel about how it was reported? Mixed feelings, honestly. The underlying study was fairly narrow — it looked at one specific population over a relatively short period, and the effect size, while statistically significant, was modest. What ended up in the headlines was a much bolder claim than anything we actually demonstrated. I understand why that happens; nuance doesn't travel as well as a punchy headline. But I do worry that people will now either overcorrect based on a claim we never made, or dismiss the finding entirely once a more cautious follow-up study inevitably tempers it. Neither reaction would reflect what the data actually shows. So if you could rewrite the headline yourself, what would it say? Something considerably less exciting, I'm afraid — probably starting with 'preliminary evidence suggests', which is exactly the phrase that never survives into print. Do you think the scientific community bears any responsibility for how these stories get simplified? To some extent, yes. We could be clearer in our own summaries, and some press releases from universities are, frankly, guilty of overselling their own research to attract coverage. But the incentive structures on both sides, ours and the media's, tend to reward the bolder claim, so I don't think this is a problem either side can fix alone.",
  "situation": "A nutrition scientist is interviewed about media coverage of her recent study.",
  "question": "What does the scientist imply about the media coverage of her research?",
  "options": ["It overstated findings that were actually modest and preliminary", "It was a fair and accurate summary of her conclusions", "It failed to mention the study at all", "It focused on a different, unrelated piece of research"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "implied_meaning",
  "secondary_skill": "speaker_attitude",
  "audio_context": "interview",
  "discourse_type": "dialogue",
  "rationale": "She contrasts the modest, preliminary findings with the bolder headline claim, closing with ironic understatement.",
  "distractor_rationale": "Other options contradict her stated concern or are inconsistent with the interview's premise."
}
```

### ITEM LST-C2-03
- draft_id: LST-C2-03
- cefr_level: C2
- question_type: mcq
- listening_skill: inference
- secondary_skill: relationship_between_speakers
- audio_context: civic or media discussion
- discourse_type: discussion
- speakers: 2 (two media commentators)
- transcript: "I have to push back on your reading of the polling data. You're treating a five-point swing as if it's decisive, but the margin of error on that survey is close to four points either way." "Sure, but it's the third consecutive poll showing movement in the same direction, and that consistency is what makes me less willing to dismiss it as noise." "That's fair, and I'll admit a single poll wouldn't move me much either. I suppose my real objection is to how confidently the movement is being described in some of the coverage, as though the outcome were already settled." "On that, we actually agree completely — 'settled' is far too strong a word for anything this close, whatever the trend line suggests." "Good, then we've found some common ground after all, even if we got there by disagreeing about almost everything else first. Should we do this again next week, same disagreements included? Absolutely, though I suspect the data will have moved on by then, and we'll have an entirely new set of numbers to argue about. That's half the fun of this job, honestly. It keeps the audience guessing whether we're actually going to agree on anything, which I suspect is part of why people keep tuning in each week, disagreements and all. There are worse reputations to have than being reliably, respectfully argumentative on air."
- transcript_word_count: 230
- target_duration_seconds: 106
- situation: Two commentators debate how confidently to interpret recent polling data.
- prompt_or_question: What can be inferred about the two speakers' overall relationship in this exchange?
- options: ["Professional rivals in disagreement who ultimately find a shared point of agreement", "Two people who agree with each other from beginning to end", "Speakers who remain in disagreement from start to finish", "An interviewer questioning a reluctant, uncooperative guest"]
- correct_index: 0
- correct_answer: Professional rivals in disagreement who ultimately find a shared point of agreement
- rationale: The exchange opens with direct pushback and methodological disagreement, but the closing turns ("we actually agree completely", "found some common ground") show a genuine, if partial, resolution.
- distractor_rationale: "Agree from beginning to end" ignores the initial sustained disagreement; "never resolve any part" contradicts the explicit closing agreement; "reluctant, uncooperative guest" mischaracterises a debate between equals as an interview.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Requires tracking a shift in stance across the whole exchange rather than reading any single turn in isolation.
- estimated_cefr_justification: Dense argumentative register with statistical reasoning, concession structures, and an ironic closing line — features typical of C2 discourse.
- body_json_candidate:
```json
{
  "question_type": "mcq",
  "transcript": "I have to push back on your reading of the polling data. You're treating a five-point swing as if it's decisive, but the margin of error on that survey is close to four points either way. Sure, but it's the third consecutive poll showing movement in the same direction, and that consistency is what makes me less willing to dismiss it as noise. That's fair, and I'll admit a single poll wouldn't move me much either. I suppose my real objection is to how confidently the movement is being described in some of the coverage, as though the outcome were already settled. On that, we actually agree completely — 'settled' is far too strong a word for anything this close, whatever the trend line suggests. Good, then we've found some common ground after all, even if we got there by disagreeing about almost everything else first. Should we do this again next week, same disagreements included? Absolutely, though I suspect the data will have moved on by then, and we'll have an entirely new set of numbers to argue about. That's half the fun of this job, honestly. It keeps the audience guessing whether we're actually going to agree on anything, which I suspect is part of why people keep tuning in each week, disagreements and all. There are worse reputations to have than being reliably, respectfully argumentative on air.",
  "situation": "Two commentators debate how confidently to interpret recent polling data.",
  "question": "What can be inferred about the two speakers' overall relationship in this exchange?",
  "options": ["Professional rivals in disagreement who ultimately find a shared point of agreement", "Two people who agree with each other from beginning to end", "Speakers who remain in disagreement from start to finish", "An interviewer questioning a reluctant, uncooperative guest"],
  "correct_index": 0,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "inference",
  "secondary_skill": "relationship_between_speakers",
  "audio_context": "civic_or_media_discussion",
  "discourse_type": "discussion",
  "rationale": "The exchange moves from direct disagreement to an explicit, if partial, resolution.",
  "distractor_rationale": "Other options ignore either the initial disagreement or the closing agreement, or mischaracterise the format."
}
```

### ITEM LST-C2-04
- draft_id: LST-C2-04
- cefr_level: C2
- question_type: gap_fill
- listening_skill: number_time_price
- secondary_skill: (none)
- audio_context: academic-style explanation
- discourse_type: monologue
- speakers: 1 (guest expert on a panel broadcast)
- transcript: "One figure from the report that's worth pausing on: across the cities studied, the average commute time fell by only three minutes despite a reported thirty percent increase in remote-working arrangements. That gap is telling. It suggests that reduced commuting frequency hasn't translated into meaningfully shorter individual journeys for those who still travel, likely because reduced overall road use has been absorbed by other drivers rather than benefiting the commuters who remain. In other words, fewer people are commuting, but the ones who still do aren't necessarily experiencing a faster trip, which complicates any simple narrative about remote work easing congestion. There's a second figure worth mentioning alongside it: public transport usage in the same cities fell by closer to twelve percent, a much steeper drop than the change in car commute times would suggest. That imbalance matters, because it hints that some of the people who stopped commuting by train or bus didn't necessarily start working remotely full-time; some may simply have shifted to driving instead, for journeys they still make occasionally. If that's right, the environmental benefits some commentators have assumed alongside remote work's rise may be considerably smaller than the headline figures imply, and any policy built on that assumption deserves a closer look before it's acted on more broadly. None of this means remote work hasn't changed anything, clearly it has, but the second-order effects on transport and emissions appear to be far messier and less linear than the early, optimistic commentary suggested when these arrangements first became widespread."
- transcript_word_count: 253
- target_duration_seconds: 117
- situation: An expert discusses a surprising statistic from a transport research report.
- prompt_or_question: According to the report, by how many minutes did the average commute time fall?
- accepted_answers: ["three", "3"]
- max_words: 1
- case_sensitive: false
- word_bank: null
- correct_answer: three
- rationale: The specific figure is stated explicitly at the start of the commentary, before the more abstract discussion of why the number is small; the prompt already supplies "minutes", so only the number is required.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: The surrounding commentary is abstract and interpretive, but the tested fact itself is a single, clearly stated figure — keeping the Gap Fill answer extractable rather than requiring the listener to reason about causation.
- estimated_cefr_justification: Dense, interpretive expert commentary with abstract reasoning about causation, though the specific numeric detail tested remains explicit and extractable.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "One figure from the report that's worth pausing on: across the cities studied, the average commute time fell by only three minutes despite a reported thirty percent increase in remote-working arrangements. That gap is telling. It suggests that reduced commuting frequency hasn't translated into meaningfully shorter individual journeys for those who still travel, likely because reduced overall road use has been absorbed by other drivers rather than benefiting the commuters who remain. In other words, fewer people are commuting, but the ones who still do aren't necessarily experiencing a faster trip, which complicates any simple narrative about remote work easing congestion. There's a second figure worth mentioning alongside it: public transport usage in the same cities fell by closer to twelve percent, a much steeper drop than the change in car commute times would suggest. That imbalance matters, because it hints that some of the people who stopped commuting by train or bus didn't necessarily start working remotely full-time; some may simply have shifted to driving instead, for journeys they still make occasionally. If that's right, the environmental benefits some commentators have assumed alongside remote work's rise may be considerably smaller than the headline figures imply, and any policy built on that assumption deserves a closer look before it's acted on more broadly. None of this means remote work hasn't changed anything, clearly it has, but the second-order effects on transport and emissions appear to be far messier and less linear than the early, optimistic commentary suggested when these arrangements first became widespread.",
  "situation": "An expert discusses a surprising statistic from a transport research report.",
  "prompt": "According to the report, by how many minutes did the average commute time fall?",
  "accepted_answers": ["three", "3"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "number_time_price",
  "secondary_skill": null,
  "audio_context": "academic_style_explanation",
  "discourse_type": "monologue",
  "rationale": "The specific figure is stated explicitly before the interpretive discussion begins; the prompt already supplies the time unit."
}
```

### ITEM LST-C2-05
- draft_id: LST-C2-05
- cefr_level: C2
- question_type: gap_fill
- listening_skill: place_name
- secondary_skill: (none)
- audio_context: civic or media discussion
- discourse_type: discussion
- speakers: 2 (journalist, policy analyst)
- transcript: "Your organisation has been cited as the source behind this new congestion-pricing proposal. Can you clarify which city first piloted the model you're now recommending nationally?" "Happy to. The framework draws heavily on what was first trialled in Stockholm, back in the mid-2000s, and later refined in a handful of other cities, though Stockholm remains the closest comparison for the scale we're proposing here. What made that case particularly useful for us wasn't just the reduction in traffic, which was substantial, but the fact that public support actually increased after implementation, once residents could see the results directly, having initially opposed the scheme before it began." "So the political lesson is as important as the traffic data itself?" "Arguably more so. Getting the technical design right matters, but if you can't survive the initial period of public resistance, the policy never gets the chance to prove itself. Is there a risk that this particular scheme fails for exactly that reason, regardless of how well it's designed technically? It's a real risk, yes, and it's precisely why we've recommended a phased rollout rather than an overnight citywide launch, starting with the districts where support is already strongest, before expanding to the more sceptical areas once there's visible evidence to point to. It's slower than some politicians would like, admittedly, but a scheme that collapses under early opposition helps no one, and a cautious, evidence-led rollout gives residents in the more hesitant districts something concrete to evaluate rather than a promise to take on faith."
- transcript_word_count: 253
- target_duration_seconds: 117
- situation: A policy analyst is interviewed about the origins of a proposed congestion-pricing scheme.
- prompt_or_question: Which city does the analyst identify as the original pilot for the pricing model?
- accepted_answers: ["Stockholm"]
- max_words: 1
- case_sensitive: false
- word_bank: null
- correct_answer: Stockholm
- rationale: The analyst names the city explicitly and returns to it again later in the answer as the key comparison case.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: The city name is repeated, supporting confident extraction despite the surrounding discussion being dense and interpretive.
- estimated_cefr_justification: Dense policy-discussion register with embedded clauses and a secondary discussion of public opinion, though the tested place name remains explicit and repeated.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Your organisation has been cited as the source behind this new congestion-pricing proposal. Can you clarify which city first piloted the model you're now recommending nationally? Happy to. The framework draws heavily on what was first trialled in Stockholm, back in the mid-2000s, and later refined in a handful of other cities, though Stockholm remains the closest comparison for the scale we're proposing here. What made that case particularly useful for us wasn't just the reduction in traffic, which was substantial, but the fact that public support actually increased after implementation, once residents could see the results directly, having initially opposed the scheme before it began. So the political lesson is as important as the traffic data itself? Arguably more so. Getting the technical design right matters, but if you can't survive the initial period of public resistance, the policy never gets the chance to prove itself. Is there a risk that this particular scheme fails for exactly that reason, regardless of how well it's designed technically? It's a real risk, yes, and it's precisely why we've recommended a phased rollout rather than an overnight citywide launch, starting with the districts where support is already strongest, before expanding to the more sceptical areas once there's visible evidence to point to. It's slower than some politicians would like, admittedly, but a scheme that collapses under early opposition helps no one, and a cautious, evidence-led rollout gives residents in the more hesitant districts something concrete to evaluate rather than a promise to take on faith.",
  "situation": "A policy analyst is interviewed about the origins of a proposed congestion-pricing scheme.",
  "prompt": "Which city does the analyst identify as the original pilot for the pricing model?",
  "accepted_answers": ["Stockholm"],
  "max_words": 1,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "place_name",
  "secondary_skill": null,
  "audio_context": "civic_or_media_discussion",
  "discourse_type": "discussion",
  "rationale": "The city name is stated explicitly and repeated as the key comparison case."
}
```

### ITEM LST-C2-06
- draft_id: LST-C2-06
- cefr_level: C2
- question_type: gap_fill
- listening_skill: sequence
- secondary_skill: (none)
- audio_context: academic-style explanation
- discourse_type: monologue
- speakers: 1 (researcher presenting findings)
- transcript: "Let me walk through how the study actually unfolded, since the order matters for interpreting the result. We began with a broad survey of nearly two thousand participants, simply to identify candidates for the more detailed phase. From that group, around two hundred were selected for structured interviews, based on specific criteria related to their reported habits. Only after those interviews were complete did we move to the final and most resource-intensive stage: an eight-week observational study with a much smaller group of thirty participants, which is where the headline finding — the one everyone's been discussing — actually emerged. It's worth stressing that the observational stage came last, not first, because the earlier phases were what allowed us to identify exactly who was worth observing that closely in the first place. Some colleagues have asked why we didn't simply observe a larger group from the outset, rather than narrowing it down in stages. The honest answer is cost and practicality; close observation of this kind is expensive and time-consuming to conduct well, so narrowing the pool first, using cheaper methods, let us direct our limited resources toward the participants most likely to yield a meaningful result. It's a trade-off, certainly, and a valid methodological criticism, but given the constraints we were working under, I still think it was the right one, and it's something we'll address more directly in the paper's limitations section."
- transcript_word_count: 234
- target_duration_seconds: 108
- situation: A researcher explains the sequence of stages in a completed study.
- prompt_or_question: Which stage of the study came last, according to the researcher?
- accepted_answers: ["observational study", "the observational study", "observational stage", "observation"]
- max_words: 3
- case_sensitive: false
- word_bank: null
- correct_answer: observational study
- rationale: The researcher explicitly states that "the observational stage came last, not first," directly answering the sequencing question.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- audio_generation_status: not_generated
- authoring_notes: Three sequential stages are described (survey, interviews, observation); the item targets only the final one, requiring the listener to track the full order rather than the most memorable detail (the headline finding).
- estimated_cefr_justification: Extended, multi-stage explanatory narrative with metadiscourse ("let me walk through", "it's worth stressing") typical of C2 explanation-following tasks.
- body_json_candidate:
```json
{
  "question_type": "gap_fill",
  "transcript": "Let me walk through how the study actually unfolded, since the order matters for interpreting the result. We began with a broad survey of nearly two thousand participants, simply to identify candidates for the more detailed phase. From that group, around two hundred were selected for structured interviews, based on specific criteria related to their reported habits. Only after those interviews were complete did we move to the final and most resource-intensive stage: an eight-week observational study with a much smaller group of thirty participants, which is where the headline finding — the one everyone's been discussing — actually emerged. It's worth stressing that the observational stage came last, not first, because the earlier phases were what allowed us to identify exactly who was worth observing that closely in the first place. Some colleagues have asked why we didn't simply observe a larger group from the outset, rather than narrowing it down in stages. The honest answer is cost and practicality; close observation of this kind is expensive and time-consuming to conduct well, so narrowing the pool first, using cheaper methods, let us direct our limited resources toward the participants most likely to yield a meaningful result. It's a trade-off, certainly, and a valid methodological criticism, but given the constraints we were working under, I still think it was the right one, and it's something we'll address more directly in the paper's limitations section.",
  "situation": "A researcher explains the sequence of stages in a completed study.",
  "prompt": "Which stage of the study came last, according to the researcher?",
  "accepted_answers": ["observational study", "the observational study", "observational stage", "observation"],
  "max_words": 3,
  "case_sensitive": false,
  "word_bank": null,
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "audio_generation_status": "not_generated",
  "listening_skill": "sequence",
  "secondary_skill": null,
  "audio_context": "academic_style_explanation",
  "discourse_type": "monologue",
  "rationale": "The researcher explicitly states which stage came last."
}
```

---

## Coverage Summary

*Re-verified after the content-cleanup pass documented in the Cleanup Change Log below. None of the cleanup edits changed any item's `cefr_level`, `question_type`, `listening_skill`, `secondary_skill`, `audio_context`, or `discourse_type` — only transcript wording, prompts, options, accepted-answer sets, `max_words`, `word_bank`, rationale text, and `correct_answer` fields were touched — so every count in this section is unchanged from before cleanup and has been re-confirmed against the current file.*

**Count by CEFR level** (8 new items each for A1/A2/B1; 6 new items each for B2/C1/C2 = 42 total):

| Level | New items | MCQ | Gap Fill |
|---|---|---|---|
| A1 | 8 | 4 | 4 |
| A2 | 8 | 4 | 4 |
| B1 | 8 | 4 | 4 |
| B2 | 6 | 3 | 3 |
| C1 | 6 | 3 | 3 |
| C2 | 6 | 3 | 3 |
| **Total** | **42** | **21** | **21** |

This matches the required distribution exactly:
- A1: 4 MCQ + 4 Gap Fill ✓
- A2: 4 MCQ + 4 Gap Fill ✓
- B1: 4 MCQ + 4 Gap Fill ✓
- B2: 3 MCQ + 3 Gap Fill ✓
- C1: 3 MCQ + 3 Gap Fill ✓
- C2: 3 MCQ + 3 Gap Fill ✓

**Count by question_type**: `mcq` = 21, `gap_fill` = 21.

**Count by dialogue/monologue/discussion** (per level, against the required minimum dialogues-or-discussions):

| Level | Dialogue | Monologue | Discussion | Dialogue+Discussion | Required min | Met? |
|---|---|---|---|---|---|---|
| A1 | 5 | 3 | 0 | 5 | 4 | ✓ |
| A2 | 6 | 2 | 0 | 6 | 5 | ✓ |
| B1 | 6 | 2 | 0 | 6 | 5 | ✓ |
| B2 | 4 | 1 | 1 | 5 | 4 | ✓ |
| C1 | 1 | 2 | 3 | 4 | 3 | ✓ |
| C2 | 1 | 2 | 3 | 4 | 3 | ✓ |

No monologue is ever labelled dialogue or discussion; the table above reflects each item's literal, honest `discourse_type` value.

**Count by listening_skill (primary)**:

| Skill | Primary count |
|---|---|
| explicit_detail | 7 |
| number_time_price | 7 |
| reason_cause | 6 |
| place_name | 4 |
| following_instructions | 4 |
| relationship_between_speakers | 2 |
| speaker_attitude | 2 |
| sequence | 2 |
| inference | 2 |
| following_argument | 2 |
| implied_meaning | 2 |
| speaker_purpose | 1 |
| understanding_explanation | 1 |
| **Total** | **42** |

**Combined coverage (primary + secondary)**, against the required minimums:

| Skill | Primary | Secondary | Combined | Required ≥ | Met? |
|---|---|---|---|---|---|
| main_idea | 0 | 6 | 6 | 5 | ✓ |
| explicit_detail | 7 | 0 | 7 | 6 | ✓ |
| number_time_price | 7 | 2 | 9 | 5 | ✓ |
| place_name | 4 | 0 | 4 | 4 | ✓ |
| sequence | 2 | 4 | 6 | 4 | ✓ |
| reason_cause | 6 | 4 | 10 | 5 | ✓ |
| speaker_purpose | 1 | 3 | 4 | 3 | ✓ |
| speaker_attitude | 2 | 4 | 6 | 3 | ✓ |
| inference | 2 | 1 | 3 | 3 | ✓ |
| relationship_between_speakers | 2 | 4 | 6 | 3 | ✓ |
| following_instructions | 4 | 0 | 4 | 3 | ✓ |
| understanding_explanation | 1 | 2 | 3 | 2 | ✓ |
| following_argument | 2 | 0 | 2 | 2 | ✓ |
| implied_meaning | 2 | 1 | 3 | 2 | ✓ |

`main_idea` is used only as a secondary skill in this batch (never primary) — a deliberate choice, since gist alone was judged too coarse to serve as the sole tested skill for any single item in a batch already asked to sharpen subskill precision, but it remains genuinely present as a secondary dimension on 6 items. No item uses the generic value `comprehension`.

**Count by audio_context** (14 distinct contexts used across 42 items): work discussion (8), civic or media discussion (7), everyday conversation (5), shopping (4), academic-style explanation (3), classroom (2), public announcement (2), informal planning (2), appointments (2), school discussion (2), interview (2), transport (1), housing or community issue (1), educational explanation (1). Every context category named in the task brief is represented at least once. A1/A2 are not limited to introductions/family (only 2 of 16 A1/A2 items touch that theme); B2–C2 are not all institutional (informal interview and personal-narrative registers appear at B2 and C1).

**A1/A2 word-bank presence**: all 8 A1 Gap Fill items and all 8 A2 Gap Fill items include a populated `word_bank` (16/16 = 100%, as required — word banks are mandatory at these two levels). All B1–C2 Gap Fill items use `word_bank: null` (13/13), per the "no word bank unless necessary" guidance for B1 and above; none of the 13 needed one.

---

## Final Bank Projection

| | MCQ | Gap Fill | Total |
|---|---|---|---|
| Existing reachable items | 18 | 0 | 18 |
| New draft items (this file) | 21 | 21 | 42 |
| **Projected total** | **39** | **21** | **60** |

**Projected total per CEFR level** (existing + new, once these drafts are reviewed, authored into real bank rows, and audio-backfilled):

| Level | Existing | New | Projected total |
|---|---|---|---|
| A1 | 2 | 8 | 10 |
| A2 | 2 | 8 | 10 |
| B1 | 2 | 8 | 10 |
| B2 | 4 | 6 | 10 |
| C1 | 4 | 6 | 10 |
| C2 | 4 | 6 | 10 |
| **Total** | **18** | **42** | **60** |

This projection reflects a future state only. No row in this projection exists in the database yet; every "new" figure above corresponds to a draft item in this file, not an inserted record.

---

## Self-Audit Findings

Strict, item-by-item review, updated after this content-cleanup pass. Status values used: **MVP ready**, **needs minor edit**, **needs human review**, **potential risk**. This pass fixed every unit-in-answer violation, the word_bank/max_words mismatches, one remaining design-level risk (LST-A2-05), and restructured two of the four paraphrase-confirmation items; see the Cleanup Change Log for the full list of edits and reasons.

**Cross-cutting finding, partially resolved this pass:** four B2/C1/C2 items previously shared a rhetorical device — a host paraphrases the other speaker's position, who then confirms it ("So you're saying...?" / "Exactly."). **LST-B2-01 and LST-C2-01 were rewritten this pass** to use a different interaction pattern (a genuinely new follow-up question, and a challenge-and-rebuttal exchange, respectively) instead of a paraphrase-confirm. **LST-C1-01 and LST-C1-02 still use the original paraphrase-confirmation device** and were intentionally left unchanged this pass (the task required rewriting at least two of the four, not all four, to keep this cleanup scoped) — flagged below for a future pass if a reviewer wants full diversity across all four.

| draft_id | Status | Note (only where not simply "MVP ready") |
|---|---|---|
| LST-A1-01 | MVP ready | |
| LST-A1-02 | MVP ready | |
| LST-A1-03 | MVP ready | |
| LST-A1-04 | MVP ready | |
| LST-A1-05 | MVP ready | |
| LST-A1-06 | needs minor edit | This pass removed "4pm" from `accepted_answers`/`word_bank`: the transcript only ever says "four o'clock" and never states am/pm, so accepting "4pm" would have required the student to supply information not actually in the audio. A human reviewer should confirm the simplified answer set still reads naturally. |
| LST-A1-07 | MVP ready | Max_words/word_bank compliance issue from the prior audit was already fixed in an earlier pass; re-verified clean this pass, no further change needed. |
| LST-A1-08 | MVP ready | Same prior-pass fix as LST-A1-07; re-verified clean this pass. |
| LST-A2-01 | MVP ready | |
| LST-A2-02 | MVP ready | |
| LST-A2-03 | MVP ready | |
| LST-A2-04 | MVP ready | |
| LST-A2-05 | needs minor edit | The word_bank distractor "seven people" (borrowed from the booking *time*, seven o'clock, not a real person-count) was replaced with "six people" this pass, removing a formatting-driven confusion risk flagged in the prior audit. |
| LST-A2-06 | needs minor edit | Unit-handling fix this pass: the prompt now states "in pounds" and `accepted_answers`/`word_bank` were reduced to bare numbers ("seven"/"7" and "3.50"/"7"/"2"), removing the previously-required spelled-out "pounds" and the "three pounds fifty" word_bank entry that exceeded `max_words`. |
| LST-A2-07 | MVP ready | Max_words compliance issue from the prior audit was already fixed in an earlier pass; re-verified clean this pass. |
| LST-A2-08 | MVP ready | |
| LST-B1-01 | MVP ready | |
| LST-B1-02 | MVP ready | Option-length fix from the prior audit re-verified clean this pass; no further change needed. |
| LST-B1-03 | needs minor edit | Speaker-count fix from the prior audit re-verified; this pass additionally corrected a leftover `estimated_cefr_justification` phrase ("across three turns") that no longer matched the corrected 2-speaker structure. |
| LST-B1-04 | MVP ready | |
| LST-B1-05 | MVP ready | |
| LST-B1-06 | MVP ready | |
| LST-B1-07 | needs minor edit | Unit-handling fix this pass: removed "9am"/"9 am" from `accepted_answers`, since the transcript never states am/pm — only "nine"/"9"/"nine o'clock"/"9 o'clock" remain, all directly supported by the audio. |
| LST-B1-08 | needs minor edit | Unit-handling fix this pass, resolving the prior audit's currency-variant risk: the prompt now states "in pounds" and `accepted_answers` were reduced to ["600", "six hundred"], dropping the "£600" symbol form entirely rather than relying on an implied conversion. |
| LST-B2-01 | needs minor edit | Rewritten this pass to remove the paraphrase-confirmation device (see cross-cutting finding above); the host now asks a genuinely new follow-up question instead of restating the caller's position. A human reviewer should confirm the new exchange still tests speaker_attitude as cleanly as the original. |
| LST-B2-02 | MVP ready | |
| LST-B2-03 | MVP ready | |
| LST-B2-04 | needs minor edit | Unit-handling fix this pass: the transcript never actually states a currency for the budget figures, so the invented "£22,000" form was removed from `accepted_answers`, leaving only the figure itself ("twenty-two thousand"/"22,000"/"22000"). |
| LST-B2-05 | MVP ready | Max_words compliance issue from the prior audit was already fixed in an earlier pass; re-verified clean this pass. |
| LST-B2-06 | MVP ready | |
| LST-C1-01 | needs minor edit | Still uses the paraphrase-confirmation device (see cross-cutting finding above) — intentionally left unchanged this pass since two of the four flagged items were already rewritten; also one of the longer/denser C1 items and worth a fluency read-aloud check before audio generation. |
| LST-C1-02 | needs minor edit | Still uses the paraphrase-confirmation device (see cross-cutting finding above) — intentionally left unchanged this pass. |
| LST-C1-03 | MVP ready | |
| LST-C1-04 | potential risk | Unit-handling fix applied this pass (prompt now states "months", answer reduced to bare "six"/"6"), but the underlying risk flagged in the prior audit is unchanged: the gap-fill target sits inside a formally worded, multi-step explanation, and a candidate who loses the thread of the certification process could plausibly mishear which numeric detail is being asked about even though the fact itself is simple. Recommend a human listening pass to confirm the number is acoustically well-separated from surrounding detail. |
| LST-C1-05 | needs minor edit | Unit-handling fix this pass, resolving the prior audit's currency risk: the prompt now states "in pounds" and `accepted_answers` were reduced to ["430,000", "430000"], dropping the "£430,000" symbol form. |
| LST-C1-06 | MVP ready | |
| LST-C2-01 | needs minor edit | Rewritten this pass to remove the paraphrase-confirmation device (see cross-cutting finding above); the host now challenges the ethicist directly ("But surely individual designers still bear some responsibility...?") and the ethicist concedes a minor point before reasserting her thesis, rather than the host simply paraphrasing and the ethicist confirming. Transcript grew slightly (265→280 words, still within the C2 220–300 range) — a human reviewer should confirm the new exchange still tests following_argument as cleanly as the original and that the target duration is realistic against real TTS output. |
| LST-C2-02 | MVP ready | |
| LST-C2-03 | MVP ready | |
| LST-C2-04 | potential risk | Unit-handling fix applied this pass (prompt now states "minutes", answer reduced to bare "three"/"3"), but the underlying risk flagged in the prior audit is unchanged: the extractable answer is stated early, but surrounded by dense, abstract causal reasoning about induced demand, and a strong listener could still second-guess whether "three" or "thirty" (percent, an unrelated figure in the same sentence) is the number being asked about. Recommend a human check that the question wording disambiguates this clearly enough. |
| LST-C2-05 | potential risk | Unchanged this pass. "Stockholm" is stated in the very first two sentences of the analyst's answer (before the passage becomes dense), which already substantially mitigates the risk noted in the prior audit; recommend only a light human listening check, not a rewrite. |
| LST-C2-06 | MVP ready | |

Summary: **27 items MVP ready**, **12 items needing minor edit** (all fixed in place this pass or a prior pass, listed above with what changed and why; 2 of the 4 paraphrase-confirmation items — LST-C1-01, LST-C1-02 — remain flagged and unchanged by design, since only 2 of 4 were required to be rewritten), **3 items flagged as potential risk** (LST-C1-04 and LST-C2-04 had their unit-*format* risk resolved this pass but retain an underlying density/disambiguation risk needing a human listening pass; LST-C2-05 is unchanged and re-confirmed as adequately mitigated by repetition. Two previously-flagged potential-risk items — LST-A2-05 and LST-B1-08 — were fully resolved this pass and moved to "needs minor edit" above since their fixes are already applied, not just recommended). No item is marked as requiring full human review beyond what a normal MVP content pass would already involve, and none of the 42 items is claimed to be already verified.

---

## Cleanup Change Log

This section lists every item changed during this content-cleanup pass. It does not repeat the four items already fixed in an earlier authoring pass and merely re-verified clean this time (LST-A1-07, LST-A1-08, LST-A2-07, LST-B1-02, LST-B2-05) — those required no further edits.

| draft_id | Field(s) changed | Reason |
|---|---|---|
| LST-A1-06 | `accepted_answers`, `word_bank` note, `rationale` (bullet + body_json_candidate) | Removed "4pm" from accepted answers — the transcript only ever says "four o'clock" and never states am/pm, so requiring/accepting "4pm" would have made the student supply information not actually in the audio, and "pm" is an explicitly disallowed unit token to require typing. |
| LST-A2-05 | `word_bank`, `authoring_notes` (bullet + body_json_candidate) | Replaced the word_bank distractor "seven people" (borrowed from the booking *time*, not a real person-count) with "six people", removing a cross-field formatting confusion flagged as a potential risk in the prior audit. |
| LST-A2-06 | `prompt_or_question`, `accepted_answers`, `max_words`, `word_bank`, `correct_answer`, `rationale`, `authoring_notes` (bullet + body_json_candidate) | Unit-handling fix: prompt now states "in pounds"; accepted answers reduced to bare numbers ("seven"/"7"); word_bank reduced to bare numbers ("3.50"/"7"/"2"), removing the "three pounds fifty" entry that exceeded the 2-word cap and the spelled-out "pounds" the student previously had to type. |
| LST-B1-03 | `estimated_cefr_justification` | Corrected a leftover phrase ("across three turns") that no longer matched the item's corrected 2-speaker structure from the prior authoring pass. |
| LST-B1-07 | `accepted_answers`, `rationale` (bullet + body_json_candidate) | Removed "9am"/"9 am" from accepted answers — the transcript never states am/pm, so "am" (a disallowed unit token) should not be required or accepted. |
| LST-B1-08 | `prompt_or_question`, `accepted_answers`, `max_words`, `correct_answer`, `rationale` (bullet + body_json_candidate) | Unit-handling fix: prompt now states "in pounds"; accepted answers reduced to ["600", "six hundred"], dropping the "£600" symbol form and the spelled-out "pounds" the student previously had to type. Resolves the currency-variant risk flagged in the prior audit. |
| LST-B2-01 | `transcript`, `transcript_word_count`, `target_duration_seconds`, `rationale`, `distractor_rationale`, `authoring_notes` (bullet + body_json_candidate) | Restructured to remove the paraphrase-then-confirmation device: the host now asks a genuinely new follow-up question ("What would you have liked the council to do differently?") instead of restating the caller's position for her to confirm. Also fixed a stale distractor_rationale reference to "Completely opposed" (the option itself had already been changed to "Firmly opposed" in an earlier pass, but the rationale text still referenced the old wording). |
| LST-B2-04 | `accepted_answers`, `max_words`, `rationale` (bullet + body_json_candidate) | Unit-handling fix: removed the invented "£22,000" currency form — the transcript never actually states a currency for the budget figures, so no currency symbol should have been required or accepted in the first place. |
| LST-C1-04 | `prompt_or_question`, `accepted_answers`, `max_words`, `correct_answer`, `rationale` (bullet + body_json_candidate) | Unit-handling fix: prompt now states "months"; accepted answers reduced to bare numbers ("six"/"6"), removing the spelled-out "months" the student previously had to type. |
| LST-C1-05 | `prompt_or_question`, `accepted_answers`, `max_words`, `correct_answer`, `rationale` (bullet + body_json_candidate) | Unit-handling fix: prompt now states "in pounds"; accepted answers reduced to ["430,000", "430000"], dropping the "£430,000" symbol form and the spelled-out "pounds". |
| LST-C2-01 | `transcript`, `transcript_word_count`, `target_duration_seconds`, `rationale`, `distractor_rationale`, `authoring_notes`, `estimated_cefr_justification` (bullet + body_json_candidate) | Restructured to remove the paraphrase-then-confirmation device: the host now directly challenges the ethicist ("But surely individual designers still bear some responsibility...?"), and the ethicist concedes a minor point before reasserting her thesis, rather than the host simply paraphrasing and the ethicist agreeing. |
| LST-C2-04 | `prompt_or_question`, `accepted_answers`, `max_words`, `correct_answer`, `rationale` (bullet + body_json_candidate) | Unit-handling fix: prompt now states "minutes"; accepted answers reduced to bare numbers ("three"/"3"), removing the spelled-out "minutes" the student previously had to type. |

**Not changed, and why:** LST-C1-01 and LST-C1-02 still use the paraphrase-confirmation rhetorical device. The task required rewriting *at least two* of the four flagged items (LST-B2-01, LST-C1-01, LST-C1-02, LST-C2-01); LST-B2-01 and LST-C2-01 were rewritten, satisfying that minimum while keeping this cleanup pass scoped rather than rewriting all four. LST-C2-05 was reviewed for its flagged density risk but left unchanged, since "Stockholm" already appears twice in the first two sentences of the answer (before the passage becomes dense), which was judged an adequate existing mitigation rather than a defect requiring a rewrite.

**Phase 1 dry-run validation fix (separate, later pass):** the Phase 1 seed-service dry-run validator (`language_listening_bank_seed_service.py`) flagged three `body_json_candidate.audio_context` mismatches against the visible `audio_context` field:

| draft_id | Field changed | Reason |
|---|---|---|
| LST-A2-03 | `audio_context` (bullet only) | Visible field said "shopping or service interaction" while `body_json_candidate.audio_context` already said "shopping"; changed the visible field to "shopping" to match, rather than the reverse, since "shopping" is the shorter canonical tag already used consistently elsewhere in this file (e.g. LST-A1-02). |
| LST-A2-06 | `audio_context` (bullet only) | Same mismatch and fix as LST-A2-03. |
| LST-B1-05 | `audio_context` (bullet only) | Same mismatch and fix as LST-A2-03. |

No other field was touched on these three items — transcript, prompt/question, options, accepted_answers, max_words, question_type, and CEFR level are all unchanged. The Coverage Summary's audio_context tally above was updated accordingly (14 distinct contexts, "shopping" now at 4, "shopping or service interaction" no longer exists as a separate tag).

---

## Known Non-Goals

This file is a content draft only. It does **not**:

- insert any row into `LanguagePlacementQuestionBankItem` or any other database table;
- generate, regenerate, or backfill any audio file;
- modify any backend runtime code (`app/api/`, `app/services/`, schemas, or the Gap Fill scoring contract implemented in `057d673`);
- modify any frontend file or frontend behavior;
- modify the current 18 reachable MCQ rows or the six excluded scaffold rows;
- modify any transcript, cached WAV file, or audio-caching/cached-file-validation logic;
- modify Speaking or Legacy Placement in any way;
- change the adaptive staircase, minimum evidence floor, boundary-confirmation logic, final CEFR calculation, or confidence calculation;
- stage or commit any file.

The only file created or modified by this task is `backend/content_drafts/listening_mvp_60_item_bank_expansion_draft.md`. This confirmation applies both to the original authoring pass and to the subsequent content-cleanup pass documented in the Cleanup Change Log above — no other file was touched by either pass.
