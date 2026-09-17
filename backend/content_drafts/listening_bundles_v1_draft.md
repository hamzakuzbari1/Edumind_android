# Listening Bundles v1 — Content Draft (Phase 6)

Content-authoring draft only. Not yet inserted into any database table. No audio has been
generated for any item below. This draft is the input to a future, dedicated bundle seed service
(Phase 6C, not yet implemented) — it deliberately does not reuse the old single-question
`listening_mvp_60_item_bank_expansion_draft.md` batch or its `stable_key`/`source` values.

## Coverage Summary

- Total bundles: 30
- Per level (A1, A2, B1, B2, C1, C2): 5 bundles each (3 MCQ + 2 Gap Fill)
- MCQ bundles: 18 (54 subquestions → 54 answer points)
- Gap Fill bundles: 12 (36 blanks → 36 answer points)
- Total answer points: 90
- No word bank in this batch (note/summary completion is free-text under a word limit)

## Cleanup Change Log

- Rebalanced `correct_index` position within a bundle for 6 MCQ bundles that originally had all 3
  subquestions share the same correct-answer letter (a position-bias test-design flaw):
  `LSTB-B1-MCQ-02`, `LSTB-B2-MCQ-02`, `LSTB-B2-MCQ-03`, `LSTB-C1-MCQ-01`, `LSTB-C2-MCQ-02`,
  `LSTB-C2-MCQ-03`. Content/meaning unchanged — only option order and `correct_index` adjusted so
  the correct answer is not always in the same position.
- Fixed `max_words` for `LSTB-C2-GF-02` blank 1 (was 3, needed 4 to fit "five in the morning").
- Narrowed accepted-answer variants for `LSTB-C2-GF-02` blank 3 (phone number) to single-token
  forms only (`"555-0198"`, `"5550198"`), removing the space-separated `"555 0198"` variant that
  would have been 2 words against a `max_words: 1` constraint.

---

### ITEM LSTB-A1-MCQ-01
- draft_id: LSTB-A1-MCQ-01
- level: A1
- question_type: mcq
- title: At the Bakery
- situation: A customer buying bread and a cake at a small bakery.
- audio_transcript: "Good morning! Welcome to Sunny Bakery. Can I help you? Yes, I would like two loaves of bread, please. Anything else? Yes, one chocolate cake too. That's nice. Is it for a birthday? Yes, it's my daughter's birthday today. Happy birthday to her! That will be eight dollars in total. Here you are. Thank you very much. Have a wonderful day!"
- listening_skill_tags: [situation, explicit_detail, reason_cause]
- estimated_audio_duration_seconds: 32

```json
{
  "audio_transcript": "Good morning! Welcome to Sunny Bakery. Can I help you? Yes, I would like two loaves of bread, please. Anything else? Yes, one chocolate cake too. That's nice. Is it for a birthday? Yes, it's my daughter's birthday today. Happy birthday to her! That will be eight dollars in total. Here you are. Thank you very much. Have a wonderful day!",
  "subquestions": [
    {
      "question": "Where does this conversation happen?",
      "options": ["At a bakery", "At a school", "At a hospital", "At a train station"],
      "correct_index": 0,
      "explanation": "The speakers mention Sunny Bakery and buying bread and cake."
    },
    {
      "question": "How many loaves of bread does the customer buy?",
      "options": ["One", "Two", "Three", "Four"],
      "correct_index": 1,
      "explanation": "The customer says \"two loaves of bread, please.\""
    },
    {
      "question": "Why is the customer buying a cake?",
      "options": ["It is a wedding", "It is a birthday", "It is a holiday", "It is a graduation"],
      "correct_index": 1,
      "explanation": "The customer says it is \"my daughter's birthday today.\""
    }
  ]
}
```

---

### ITEM LSTB-A1-MCQ-02
- draft_id: LSTB-A1-MCQ-02
- level: A1
- question_type: mcq
- title: Morning Bus Stop
- situation: Two students talking at a bus stop about their school day.
- audio_transcript: "Hi Sara! Good morning, Tom. Are you going to school now? Yes, the bus comes at eight o'clock. Is your first class Math? No, my first class is English. I like English very much. Me too! What time do you finish today? I finish at three o'clock. That's early! Yes, I have no class after lunch on Mondays. Oh look, the bus is here! Let's go!"
- listening_skill_tags: [situation, explicit_detail, sequence]
- estimated_audio_duration_seconds: 33

```json
{
  "audio_transcript": "Hi Sara! Good morning, Tom. Are you going to school now? Yes, the bus comes at eight o'clock. Is your first class Math? No, my first class is English. I like English very much. Me too! What time do you finish today? I finish at three o'clock. That's early! Yes, I have no class after lunch on Mondays. Oh look, the bus is here! Let's go!",
  "subquestions": [
    {
      "question": "Where are Tom and Sara?",
      "options": ["At a bus stop", "At home", "In a classroom", "At a shop"],
      "correct_index": 0,
      "explanation": "They are waiting for the bus that comes at eight o'clock."
    },
    {
      "question": "What is Tom's first class today?",
      "options": ["Math", "Science", "English", "Art"],
      "correct_index": 2,
      "explanation": "Tom says \"my first class is English.\""
    },
    {
      "question": "What does Tom say about Mondays?",
      "options": ["He has extra homework", "He has no class after lunch", "He goes to Math class", "He arrives late"],
      "correct_index": 1,
      "explanation": "Tom says \"I have no class after lunch on Mondays.\""
    }
  ]
}
```

---

### ITEM LSTB-A1-MCQ-03
- draft_id: LSTB-A1-MCQ-03
- level: A1
- question_type: mcq
- title: Weekend Phone Call
- situation: A phone call between a mother and her son about weekend plans.
- audio_transcript: "Hello Mom! Hi Ben, how are you? I am fine. What are you doing this weekend? On Saturday, I am going to the park with my friends. That sounds fun! What about Sunday? On Sunday, I am staying home and doing my homework. Good idea. Do you need anything from the shop? Yes, can you buy some apples, please? Of course. I will buy them this afternoon. Thank you, Mom! You're welcome, Ben. See you soon!"
- listening_skill_tags: [main_idea, explicit_detail, explicit_detail]
- estimated_audio_duration_seconds: 35

```json
{
  "audio_transcript": "Hello Mom! Hi Ben, how are you? I am fine. What are you doing this weekend? On Saturday, I am going to the park with my friends. That sounds fun! What about Sunday? On Sunday, I am staying home and doing my homework. Good idea. Do you need anything from the shop? Yes, can you buy some apples, please? Of course. I will buy them this afternoon. Thank you, Mom! You're welcome, Ben. See you soon!",
  "subquestions": [
    {
      "question": "What is this phone call mainly about?",
      "options": ["Ben's weekend plans", "Ben's school test", "A birthday party", "A trip to another city"],
      "correct_index": 0,
      "explanation": "Ben describes his plans for Saturday and Sunday."
    },
    {
      "question": "What will Ben do on Sunday?",
      "options": ["Go to the park", "Visit his grandmother", "Do his homework", "Go shopping"],
      "correct_index": 2,
      "explanation": "Ben says \"On Sunday, I am staying home and doing my homework.\""
    },
    {
      "question": "What does Ben ask his mother to buy?",
      "options": ["Bread", "Apples", "Milk", "A birthday cake"],
      "correct_index": 1,
      "explanation": "Ben asks \"can you buy some apples, please?\""
    }
  ]
}
```

---

### ITEM LSTB-A1-GF-01
- draft_id: LSTB-A1-GF-01
- level: A1
- question_type: gap_fill
- title: Café Order Note
- situation: A customer ordering at a small café; the clerk notes the order.
- audio_transcript: "Hello, welcome to Green Café. What would you like today? I would like one cup of tea and one sandwich, please. Sure. That's three dollars for the tea and two dollars for the sandwich. So, five dollars in total. Would you like to sit inside or outside? Outside, please, table number four. Great, I will bring your order to table four in a few minutes."
- listening_skill_tags: [number_time_price, explicit_detail]
- estimated_audio_duration_seconds: 28

```json
{
  "audio_transcript": "Hello, welcome to Green Café. What would you like today? I would like one cup of tea and one sandwich, please. Sure. That's three dollars for the tea and two dollars for the sandwich. So, five dollars in total. Would you like to sit inside or outside? Outside, please, table number four. Great, I will bring your order to table four in a few minutes.",
  "note_template": "Order: tea and {{1}}. Total price: {{2}} dollars. Table number: {{3}}.",
  "blanks": [
    {"accepted_answers": ["sandwich"], "max_words": 1, "case_sensitive": false},
    {"accepted_answers": ["five", "5"], "max_words": 1, "case_sensitive": false},
    {"accepted_answers": ["four", "4"], "max_words": 1, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-A1-GF-02
- draft_id: LSTB-A1-GF-02
- level: A1
- question_type: gap_fill
- title: School Timetable Note
- situation: A teacher tells students about tomorrow's schedule.
- audio_transcript: "Good afternoon, class. Tomorrow, our first class is Science at nine o'clock. After that, we have Art at ten thirty. Please remember to bring your art book. At twelve o'clock, we will have lunch in the big hall. Do not forget your lunch box! After lunch, we have a short break, and then Music class at one thirty. Please arrive on time. Have a nice evening, everyone!"
- listening_skill_tags: [number_time_price, following_instructions]
- estimated_audio_duration_seconds: 31

```json
{
  "audio_transcript": "Good afternoon, class. Tomorrow, our first class is Science at nine o'clock. After that, we have Art at ten thirty. Please remember to bring your art book. At twelve o'clock, we will have lunch in the big hall. Do not forget your lunch box! After lunch, we have a short break, and then Music class at one thirty. Please arrive on time. Have a nice evening, everyone!",
  "note_template": "Tomorrow: Science at {{1}}, Art at ten thirty, lunch at twelve, Music at {{2}}. Remember to bring your {{3}}.",
  "blanks": [
    {"accepted_answers": ["nine o'clock", "nine", "9 o'clock", "9am", "9 am"], "max_words": 2, "case_sensitive": false},
    {"accepted_answers": ["one thirty", "1:30", "1.30"], "max_words": 2, "case_sensitive": false},
    {"accepted_answers": ["art book"], "max_words": 2, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-A2-MCQ-01
- draft_id: LSTB-A2-MCQ-01
- level: A2
- question_type: mcq
- title: Doctor's Appointment
- situation: A patient calling a clinic to make an appointment.
- audio_transcript: "Good morning, Riverside Clinic, how can I help you? Hello, I would like to make an appointment with Doctor Lee, please. Of course. Is this your first visit? No, I visited last year. I understand. We have an opening on Thursday at eleven o'clock, or Friday at two thirty. Thursday at eleven is better for me. Great, may I have your name, please? My name is Omar Hassan. Thank you, Mr. Hassan. Please arrive fifteen minutes early to complete a short form. Alright, thank you very much. You're welcome. See you on Thursday!"
- listening_skill_tags: [main_idea, explicit_detail, following_instructions]
- estimated_audio_duration_seconds: 41

```json
{
  "audio_transcript": "Good morning, Riverside Clinic, how can I help you? Hello, I would like to make an appointment with Doctor Lee, please. Of course. Is this your first visit? No, I visited last year. I understand. We have an opening on Thursday at eleven o'clock, or Friday at two thirty. Thursday at eleven is better for me. Great, may I have your name, please? My name is Omar Hassan. Thank you, Mr. Hassan. Please arrive fifteen minutes early to complete a short form. Alright, thank you very much. You're welcome. See you on Thursday!",
  "subquestions": [
    {
      "question": "Why is Omar calling the clinic?",
      "options": ["To cancel an appointment", "To make an appointment", "To ask about opening hours", "To complain about a bill"],
      "correct_index": 1,
      "explanation": "Omar says \"I would like to make an appointment with Doctor Lee.\""
    },
    {
      "question": "Which day and time does Omar choose?",
      "options": ["Thursday at eleven", "Friday at two thirty", "Thursday at two thirty", "Friday at eleven"],
      "correct_index": 0,
      "explanation": "Omar says \"Thursday at eleven is better for me.\""
    },
    {
      "question": "What does the receptionist ask Omar to do?",
      "options": ["Bring a friend", "Pay in advance", "Arrive fifteen minutes early", "Call again tomorrow"],
      "correct_index": 2,
      "explanation": "The receptionist says \"Please arrive fifteen minutes early to complete a short form.\""
    }
  ]
}
```

---

### ITEM LSTB-A2-MCQ-02
- draft_id: LSTB-A2-MCQ-02
- level: A2
- question_type: mcq
- title: Hotel Booking
- situation: A traveler calling a hotel to book a room.
- audio_transcript: "Hello, Blue Sky Hotel, how may I assist you? Hi, I would like to book a room for two nights, please. Certainly. Would you like a single room or a double room? A double room, please, for me and my husband. Alright. We have a double room available from Friday to Sunday. The price is sixty dollars per night. That works well for us. Would you like breakfast included? That is an extra ten dollars per day. Yes, please include breakfast. Perfect. Can I have your name to confirm the booking? Yes, it's Layla Ahmadi. Thank you, Mrs. Ahmadi. We look forward to welcoming you on Friday."
- listening_skill_tags: [main_idea, explicit_detail, explicit_detail]
- estimated_audio_duration_seconds: 44

```json
{
  "audio_transcript": "Hello, Blue Sky Hotel, how may I assist you? Hi, I would like to book a room for two nights, please. Certainly. Would you like a single room or a double room? A double room, please, for me and my husband. Alright. We have a double room available from Friday to Sunday. The price is sixty dollars per night. That works well for us. Would you like breakfast included? That is an extra ten dollars per day. Yes, please include breakfast. Perfect. Can I have your name to confirm the booking? Yes, it's Layla Ahmadi. Thank you, Mrs. Ahmadi. We look forward to welcoming you on Friday.",
  "subquestions": [
    {
      "question": "What is the purpose of this call?",
      "options": ["To cancel a hotel booking", "To book a hotel room", "To ask for directions", "To complain about noise"],
      "correct_index": 1,
      "explanation": "The caller says \"I would like to book a room for two nights.\""
    },
    {
      "question": "How many nights does Layla book?",
      "options": ["One", "Two", "Three", "Four"],
      "correct_index": 1,
      "explanation": "She books \"a room for two nights.\""
    },
    {
      "question": "What extra service does Layla add to her booking?",
      "options": ["Airport pickup", "Late check-out", "Breakfast", "A city tour"],
      "correct_index": 2,
      "explanation": "She says \"Yes, please include breakfast.\""
    }
  ]
}
```

---

### ITEM LSTB-A2-MCQ-03
- draft_id: LSTB-A2-MCQ-03
- level: A2
- question_type: mcq
- title: First Day at Work
- situation: A manager explaining the schedule to a new employee.
- audio_transcript: "Welcome to the team, Nadia! I'm happy to be here. Let me explain your schedule. You will start work at nine o'clock every morning. Lunch break is from twelve thirty to one thirty. On Wednesdays, we have a short team meeting at nine fifteen, so please arrive a little earlier that day. You will finish work at five o'clock, except on Fridays, when we finish at four. Do you have any questions? Yes, where is the meeting room? It's next to the kitchen, on the second floor. Thank you! You're welcome. I hope you enjoy working here."
- listening_skill_tags: [main_idea, explicit_detail, reason_cause]
- estimated_audio_duration_seconds: 44

```json
{
  "audio_transcript": "Welcome to the team, Nadia! I'm happy to be here. Let me explain your schedule. You will start work at nine o'clock every morning. Lunch break is from twelve thirty to one thirty. On Wednesdays, we have a short team meeting at nine fifteen, so please arrive a little earlier that day. You will finish work at five o'clock, except on Fridays, when we finish at four. Do you have any questions? Yes, where is the meeting room? It's next to the kitchen, on the second floor. Thank you! You're welcome. I hope you enjoy working here.",
  "subquestions": [
    {
      "question": "What is the manager mainly doing?",
      "options": ["Explaining Nadia's schedule", "Interviewing Nadia for the job", "Giving Nadia a tour of the building", "Discussing Nadia's salary"],
      "correct_index": 0,
      "explanation": "The manager says \"Let me explain your schedule.\""
    },
    {
      "question": "What time does the team meeting start on Wednesdays?",
      "options": ["Nine o'clock", "Nine fifteen", "Twelve thirty", "Five o'clock"],
      "correct_index": 1,
      "explanation": "The manager says \"a short team meeting at nine fifteen.\""
    },
    {
      "question": "Why should Nadia arrive earlier on Wednesdays?",
      "options": ["Because of a team meeting", "Because of a fire drill", "Because the office opens later", "Because of a client visit"],
      "correct_index": 0,
      "explanation": "The manager links the earlier arrival directly to the Wednesday meeting."
    }
  ]
}
```

---

### ITEM LSTB-A2-GF-01
- draft_id: LSTB-A2-GF-01
- level: A2
- question_type: gap_fill
- title: Train Ticket Note
- situation: A ticket officer at a train station describing a journey.
- audio_transcript: "Good afternoon. I would like a ticket to Riverside, please. Certainly. The next train leaves at four fifteen from platform six. How much is the ticket? A one-way ticket is twelve dollars. I would like a return ticket, please. That will be twenty dollars. Which platform did you say? Platform six. Thank you. The train takes about forty minutes to reach Riverside. Please be at the platform ten minutes before departure. Thank you very much. Have a safe trip!"
- listening_skill_tags: [number_time_price]
- estimated_audio_duration_seconds: 39

```json
{
  "audio_transcript": "Good afternoon. I would like a ticket to Riverside, please. Certainly. The next train leaves at four fifteen from platform six. How much is the ticket? A one-way ticket is twelve dollars. I would like a return ticket, please. That will be twenty dollars. Which platform did you say? Platform six. Thank you. The train takes about forty minutes to reach Riverside. Please be at the platform ten minutes before departure. Thank you very much. Have a safe trip!",
  "note_template": "Train to Riverside leaves at {{1}} from platform six. Return ticket price: {{2}} dollars. Journey time: about {{3}} minutes.",
  "blanks": [
    {"accepted_answers": ["four fifteen", "4:15", "4.15"], "max_words": 2, "case_sensitive": false},
    {"accepted_answers": ["twenty", "20"], "max_words": 1, "case_sensitive": false},
    {"accepted_answers": ["forty", "40"], "max_words": 1, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-A2-GF-02
- draft_id: LSTB-A2-GF-02
- level: A2
- question_type: gap_fill
- title: Restaurant Reservation Note
- situation: A customer booking a table at a restaurant by phone.
- audio_transcript: "Good evening, Olive Garden Restaurant. Hello, I would like to book a table for four people, please. Of course. What time would you like to come? Around seven thirty this evening, please. Let me check... Yes, we have a table at seven thirty. Could I also request a table near the window? Yes, that's possible. May I have your name, please? It's Karim Nabil. Thank you, Mr. Nabil. We look forward to seeing you and your group at seven thirty tonight."
- listening_skill_tags: [number_time_price, place_name]
- estimated_audio_duration_seconds: 39

```json
{
  "audio_transcript": "Good evening, Olive Garden Restaurant. Hello, I would like to book a table for four people, please. Of course. What time would you like to come? Around seven thirty this evening, please. Let me check... Yes, we have a table at seven thirty. Could I also request a table near the window? Yes, that's possible. May I have your name, please? It's Karim Nabil. Thank you, Mr. Nabil. We look forward to seeing you and your group at seven thirty tonight.",
  "note_template": "Reservation for {{1}} people at seven thirty. Table location requested: near the {{2}}. Name: {{3}}.",
  "blanks": [
    {"accepted_answers": ["four", "4"], "max_words": 1, "case_sensitive": false},
    {"accepted_answers": ["window"], "max_words": 1, "case_sensitive": false},
    {"accepted_answers": ["Karim Nabil", "karim nabil"], "max_words": 2, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-B1-MCQ-01
- draft_id: LSTB-B1-MCQ-01
- level: B1
- question_type: mcq
- title: Meeting Reschedule
- situation: Two colleagues discussing a scheduling conflict for a meeting.
- audio_transcript: "Hi Diane, do you have a minute? Sure, what's up? The client meeting on Thursday at ten now clashes with the budget review. Oh no, I forgot about the budget review. What should we do? I think we should move the client meeting to Thursday afternoon instead, maybe two o'clock. That could work, but I need to check if the client is available then. I already emailed them, and they agreed to two o'clock. That's great news. Should we still keep the budget review at ten? Yes, let's keep that as it is, since most of the finance team already confirmed. Alright, I'll update the calendar and send a new invitation to everyone. Thanks for handling this so quickly."
- listening_skill_tags: [main_idea, explicit_detail, reason_cause]
- estimated_audio_duration_seconds: 57

```json
{
  "audio_transcript": "Hi Diane, do you have a minute? Sure, what's up? The client meeting on Thursday at ten now clashes with the budget review. Oh no, I forgot about the budget review. What should we do? I think we should move the client meeting to Thursday afternoon instead, maybe two o'clock. That could work, but I need to check if the client is available then. I already emailed them, and they agreed to two o'clock. That's great news. Should we still keep the budget review at ten? Yes, let's keep that as it is, since most of the finance team already confirmed. Alright, I'll update the calendar and send a new invitation to everyone. Thanks for handling this so quickly.",
  "subquestions": [
    {
      "question": "What is the main purpose of this conversation?",
      "options": ["To resolve a scheduling conflict", "To cancel the client meeting", "To discuss the budget numbers", "To complain about the calendar system"],
      "correct_index": 0,
      "explanation": "The two colleagues work out how to fix the clash between two meetings."
    },
    {
      "question": "What new time is suggested for the client meeting?",
      "options": ["Nine o'clock", "Two o'clock", "Ten o'clock", "Four o'clock"],
      "correct_index": 1,
      "explanation": "The speaker suggests moving it to \"Thursday afternoon instead, maybe two o'clock.\""
    },
    {
      "question": "Why does the speaker decide to keep the budget review at ten?",
      "options": ["Because the room is only free then", "Because most of the finance team already confirmed", "Because the client prefers it", "Because it was already printed on the calendar"],
      "correct_index": 1,
      "explanation": "The speaker says to keep it \"since most of the finance team already confirmed.\""
    }
  ]
}
```

---

### ITEM LSTB-B1-MCQ-02
- draft_id: LSTB-B1-MCQ-02
- level: B1
- question_type: mcq
- title: Change of Plans
- situation: Two friends discussing a cancelled beach trip; one seems disappointed.
- audio_transcript: "Hey Maya, are you still coming to the beach this weekend? Actually, I don't think I can come anymore. Oh, why not? Something came up with my family, so I need to stay home. That's too bad, I know how much you were looking forward to it. Yeah... I was really looking forward to it, but it can't be helped. Do you want us to go another weekend instead? That would be nice, actually. Maybe next month, when things are calmer for you? Sounds good. I'll let you know as soon as I'm free again. Okay, no worries, take your time. Thanks for understanding, Maya."
- listening_skill_tags: [main_idea, reason_cause, speaker_attitude]
- estimated_audio_duration_seconds: 57

```json
{
  "audio_transcript": "Hey Maya, are you still coming to the beach this weekend? Actually, I don't think I can come anymore. Oh, why not? Something came up with my family, so I need to stay home. That's too bad, I know how much you were looking forward to it. Yeah... I was really looking forward to it, but it can't be helped. Do you want us to go another weekend instead? That would be nice, actually. Maybe next month, when things are calmer for you? Sounds good. I'll let you know as soon as I'm free again. Okay, no worries, take your time. Thanks for understanding, Maya.",
  "subquestions": [
    {
      "question": "What are the two friends mainly talking about?",
      "options": ["A cancelled beach trip", "Planning a birthday party", "Choosing a restaurant", "Buying plane tickets"],
      "correct_index": 0,
      "explanation": "The speaker says they \"don't think I can come\" to the beach anymore."
    },
    {
      "question": "Why can the speaker not go to the beach?",
      "options": ["The weather is bad", "Something came up with the family", "The car broke down", "They have too much homework"],
      "correct_index": 1,
      "explanation": "The speaker says \"Something came up with my family, so I need to stay home.\""
    },
    {
      "question": "How does the speaker likely feel about missing the trip?",
      "options": ["Relieved", "Angry", "Disappointed", "Indifferent"],
      "correct_index": 2,
      "explanation": "The speaker says \"I was really looking forward to it\", showing disappointment."
    }
  ]
}
```

---

### ITEM LSTB-B1-MCQ-03
- draft_id: LSTB-B1-MCQ-03
- level: B1
- question_type: mcq
- title: School Orientation Talk
- situation: A school coordinator explaining a new attendance policy to students.
- audio_transcript: "Good morning, everyone. Before we begin, I want to explain a new attendance policy starting this term. From now on, students must arrive at least five minutes before class starts. This is because late arrivals were disturbing lessons, and teachers found it difficult to continue. If a student arrives more than ten minutes late, they must go to the office first to get a late slip. We understand that sometimes things happen, like traffic or family issues, so if you have a good reason, please tell your teacher directly. Also, remember that three late arrivals in one week will result in a meeting with your parents. We hope this policy will help everyone focus better in class. Thank you for listening."
- listening_skill_tags: [main_idea, following_instructions, reason_cause]
- estimated_audio_duration_seconds: 57

```json
{
  "audio_transcript": "Good morning, everyone. Before we begin, I want to explain a new attendance policy starting this term. From now on, students must arrive at least five minutes before class starts. This is because late arrivals were disturbing lessons, and teachers found it difficult to continue. If a student arrives more than ten minutes late, they must go to the office first to get a late slip. We understand that sometimes things happen, like traffic or family issues, so if you have a good reason, please tell your teacher directly. Also, remember that three late arrivals in one week will result in a meeting with your parents. We hope this policy will help everyone focus better in class. Thank you for listening.",
  "subquestions": [
    {
      "question": "What is this talk mainly about?",
      "options": ["A new grading system", "A new attendance policy", "A change in school holidays", "A new exam schedule"],
      "correct_index": 1,
      "explanation": "The speaker says \"I want to explain a new attendance policy.\""
    },
    {
      "question": "What must a student do if they arrive more than ten minutes late?",
      "options": ["Go home", "Get a late slip from the office", "Call their parents", "Wait outside the classroom"],
      "correct_index": 1,
      "explanation": "The speaker says they \"must go to the office first to get a late slip.\""
    },
    {
      "question": "Why was this new policy introduced?",
      "options": ["Late arrivals were disturbing lessons", "The school day became shorter", "Too many students were absent", "Parents requested stricter rules"],
      "correct_index": 0,
      "explanation": "The speaker explains \"late arrivals were disturbing lessons.\""
    }
  ]
}
```

---

### ITEM LSTB-B1-GF-01
- draft_id: LSTB-B1-GF-01
- level: B1
- question_type: gap_fill
- title: Apartment Rental Note
- situation: A rental agent describing an apartment to a prospective tenant.
- audio_transcript: "This apartment has two bedrooms and one bathroom, and it's on the third floor. The monthly rent is four hundred and fifty dollars, which includes water but not electricity. If you're interested, we would need a deposit of one month's rent before you move in. The earliest move-in date available is the first of next month. There is also a small balcony with a nice view of the park. Parking is available for an extra twenty dollars per month, if you need it. Please let me know within a week if you would like to proceed, since we have another interested tenant as well."
- listening_skill_tags: [number_time_price]
- estimated_audio_duration_seconds: 52

```json
{
  "audio_transcript": "This apartment has two bedrooms and one bathroom, and it's on the third floor. The monthly rent is four hundred and fifty dollars, which includes water but not electricity. If you're interested, we would need a deposit of one month's rent before you move in. The earliest move-in date available is the first of next month. There is also a small balcony with a nice view of the park. Parking is available for an extra twenty dollars per month, if you need it. Please let me know within a week if you would like to proceed, since we have another interested tenant as well.",
  "note_template": "Monthly rent: {{1}} dollars (includes water). Deposit required: one month's rent. Earliest move-in date: {{2}}. Optional parking: {{3}} dollars extra per month.",
  "blanks": [
    {"accepted_answers": ["four hundred and fifty", "450"], "max_words": 4, "case_sensitive": false},
    {"accepted_answers": ["the first of next month", "first of next month", "the first"], "max_words": 5, "case_sensitive": false},
    {"accepted_answers": ["twenty", "20"], "max_words": 1, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-B1-GF-02
- draft_id: LSTB-B1-GF-02
- level: B1
- question_type: gap_fill
- title: Conference Registration Note
- situation: An event organizer describing registration details for a conference by phone.
- audio_transcript: "Thank you for calling about the Business Innovation Conference. The event will take place on the fifteenth of March at the Central Convention Hall. Early registration costs eighty dollars, but after the first of March, the price increases to one hundred dollars. Registration includes lunch and all conference materials. If you would like to attend the evening dinner as well, that is an extra thirty dollars. Please register online before the deadline to guarantee your seat, since the hall only holds two hundred people. You will receive a confirmation email with your ticket within twenty-four hours of registering."
- listening_skill_tags: [number_time_price]
- estimated_audio_duration_seconds: 52

```json
{
  "audio_transcript": "Thank you for calling about the Business Innovation Conference. The event will take place on the fifteenth of March at the Central Convention Hall. Early registration costs eighty dollars, but after the first of March, the price increases to one hundred dollars. Registration includes lunch and all conference materials. If you would like to attend the evening dinner as well, that is an extra thirty dollars. Please register online before the deadline to guarantee your seat, since the hall only holds two hundred people. You will receive a confirmation email with your ticket within twenty-four hours of registering.",
  "note_template": "Conference date: the fifteenth of March. Early registration price: {{1}} dollars. Evening dinner: extra {{2}} dollars. Confirmation email arrives within {{3}} hours.",
  "blanks": [
    {"accepted_answers": ["eighty", "80"], "max_words": 1, "case_sensitive": false},
    {"accepted_answers": ["thirty", "30"], "max_words": 1, "case_sensitive": false},
    {"accepted_answers": ["twenty-four", "24", "twenty four"], "max_words": 2, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-B2-MCQ-01
- draft_id: LSTB-B2-MCQ-01
- level: B2
- question_type: mcq
- title: Project Delay Discussion
- situation: Two colleagues discussing a delayed project and how to handle it.
- audio_transcript: "Have you seen the latest update on the Hamilton project? Yes, and it's not good news. We're now about three weeks behind schedule. I know, the supplier issue really set us back. Do you think we can still meet the client's deadline? Honestly, I doubt it, unless we cut back on some of the testing phase. That seems risky though, especially given the client's strict quality requirements. You're right. Maybe we should be upfront with the client and propose a revised timeline instead. That might actually work better than rushing and delivering something with problems. I'll draft an email explaining the delay and suggesting two extra weeks. I think that's the more responsible approach, even if it's not what they want to hear. Agreed. I'd rather have an honest conversation now than a bigger problem later."
- listening_skill_tags: [main_idea, explicit_detail, speaker_purpose]
- estimated_audio_duration_seconds: 65

```json
{
  "audio_transcript": "Have you seen the latest update on the Hamilton project? Yes, and it's not good news. We're now about three weeks behind schedule. I know, the supplier issue really set us back. Do you think we can still meet the client's deadline? Honestly, I doubt it, unless we cut back on some of the testing phase. That seems risky though, especially given the client's strict quality requirements. You're right. Maybe we should be upfront with the client and propose a revised timeline instead. That might actually work better than rushing and delivering something with problems. I'll draft an email explaining the delay and suggesting two extra weeks. I think that's the more responsible approach, even if it's not what they want to hear. Agreed. I'd rather have an honest conversation now than a bigger problem later.",
  "subquestions": [
    {
      "question": "What are the speakers mainly deciding?",
      "options": ["Whether to hire more staff", "How to handle a project delay", "Which supplier to switch to", "How to test a new product"],
      "correct_index": 1,
      "explanation": "They discuss the delay and how to communicate it to the client."
    },
    {
      "question": "How far behind schedule is the project?",
      "options": ["One week", "Two weeks", "Three weeks", "Four weeks"],
      "correct_index": 2,
      "explanation": "The speaker says \"We're now about three weeks behind schedule.\""
    },
    {
      "question": "What does the second speaker imply about rushing the project?",
      "options": ["It would save money", "It could result in quality problems", "It would please the client", "It is the safest option"],
      "correct_index": 1,
      "explanation": "They prefer proposing a revised timeline \"rather than rushing and delivering something with problems.\""
    }
  ]
}
```

---

### ITEM LSTB-B2-MCQ-02
- draft_id: LSTB-B2-MCQ-02
- level: B2
- question_type: mcq
- title: Study Skills Talk
- situation: A university tutor giving advice on exam preparation strategies.
- audio_transcript: "Today I want to talk about effective ways to prepare for exams, especially when you have limited time. Many students think that reading through notes repeatedly is the best method, but research actually shows that active recall, testing yourself without looking at the material, is far more effective. Another useful technique is spaced repetition, where you review information at increasing intervals rather than cramming everything the night before. I also recommend teaching the material to someone else, even if that person is just a friend or family member, because explaining a concept out loud often reveals gaps in your own understanding. Finally, don't underestimate the value of sleep. Students who sleep well before an exam consistently perform better than those who stay up all night reviewing. Try combining these methods rather than relying on just one."
- listening_skill_tags: [main_idea, explicit_detail, speaker_purpose]
- estimated_audio_duration_seconds: 67

```json
{
  "audio_transcript": "Today I want to talk about effective ways to prepare for exams, especially when you have limited time. Many students think that reading through notes repeatedly is the best method, but research actually shows that active recall, testing yourself without looking at the material, is far more effective. Another useful technique is spaced repetition, where you review information at increasing intervals rather than cramming everything the night before. I also recommend teaching the material to someone else, even if that person is just a friend or family member, because explaining a concept out loud often reveals gaps in your own understanding. Finally, don't underestimate the value of sleep. Students who sleep well before an exam consistently perform better than those who stay up all night reviewing. Try combining these methods rather than relying on just one.",
  "subquestions": [
    {
      "question": "What is the main purpose of this talk?",
      "options": ["To recommend effective exam preparation techniques", "To criticize students' study habits", "To explain how exams are graded", "To discuss university admission requirements"],
      "correct_index": 0,
      "explanation": "The speaker introduces \"effective ways to prepare for exams.\""
    },
    {
      "question": "According to the speaker, what is more effective than repeatedly reading notes?",
      "options": ["Watching videos", "Active recall", "Highlighting text", "Group study only"],
      "correct_index": 1,
      "explanation": "The speaker says \"active recall... is far more effective.\""
    },
    {
      "question": "Why does the speaker mention teaching the material to someone else?",
      "options": ["To help others get better grades", "To reduce study time significantly", "To reveal gaps in one's own understanding", "To avoid taking the exam"],
      "correct_index": 2,
      "explanation": "The speaker says explaining a concept aloud \"often reveals gaps in your own understanding.\""
    }
  ]
}
```

---

### ITEM LSTB-B2-MCQ-03
- draft_id: LSTB-B2-MCQ-03
- level: B2
- question_type: mcq
- title: Customer Service Complaint
- situation: A customer service call resolving a complaint about a late delivery.
- audio_transcript: "Thank you for calling customer support, how can I help? I ordered a package two weeks ago, and it still hasn't arrived. I'm sorry to hear that. Let me look into it right away... I see here that there was a delay at the shipping center due to a technical issue. I understand, but this is quite frustrating since I needed it for an event last weekend. I completely understand your frustration, and I apologize for the inconvenience. As compensation, I'd like to offer you a full refund on the shipping cost, plus a fifteen percent discount on your next order. That sounds fair, thank you. Also, I've arranged for your package to be delivered by tomorrow with priority shipping, at no extra charge. That's very helpful, I appreciate you resolving this quickly. We value your business and apologize again for the delay."
- listening_skill_tags: [main_idea, explicit_detail, implied_meaning]
- estimated_audio_duration_seconds: 65

```json
{
  "audio_transcript": "Thank you for calling customer support, how can I help? I ordered a package two weeks ago, and it still hasn't arrived. I'm sorry to hear that. Let me look into it right away... I see here that there was a delay at the shipping center due to a technical issue. I understand, but this is quite frustrating since I needed it for an event last weekend. I completely understand your frustration, and I apologize for the inconvenience. As compensation, I'd like to offer you a full refund on the shipping cost, plus a fifteen percent discount on your next order. That sounds fair, thank you. Also, I've arranged for your package to be delivered by tomorrow with priority shipping, at no extra charge. That's very helpful, I appreciate you resolving this quickly. We value your business and apologize again for the delay.",
  "subquestions": [
    {
      "question": "What is the customer's main complaint?",
      "options": ["The package arrived late", "The product was damaged", "The wrong item was sent", "The price was too high"],
      "correct_index": 0,
      "explanation": "The customer says the package \"still hasn't arrived\" two weeks after ordering."
    },
    {
      "question": "What compensation does the representative offer first?",
      "options": ["A replacement product", "A full refund on shipping cost", "A free gift", "A store credit"],
      "correct_index": 1,
      "explanation": "The representative offers \"a full refund on the shipping cost.\""
    },
    {
      "question": "What can be inferred about the outcome of this call?",
      "options": ["The customer remains dissatisfied", "The customer cancels the order", "The issue is resolved to the customer's satisfaction", "The representative refuses to help"],
      "correct_index": 2,
      "explanation": "The customer says \"that's very helpful, I appreciate you resolving this quickly.\""
    }
  ]
}
```

---

### ITEM LSTB-B2-GF-01
- draft_id: LSTB-B2-GF-01
- level: B2
- question_type: gap_fill
- title: Technical Support Ticket Note
- situation: A technical support agent describing next steps to a customer whose laptop is broken.
- audio_transcript: "Thank you for describing the issue with your laptop. Based on what you've told me, it sounds like a hardware problem with the battery. I've created a support ticket for you, and the reference number is A2 dash 7 7 4. Our technician will call you within two business days to schedule a repair appointment. In the meantime, please back up any important files, since the repair may require replacing some internal components. If the issue is covered under warranty, there will be no charge; otherwise, the estimated repair cost is thirty-five dollars. You can check the ticket status anytime using the reference number I gave you. Do you have any other questions? No, that's all, thank you."
- listening_skill_tags: [explicit_detail, number_time_price]
- estimated_audio_duration_seconds: 57

```json
{
  "audio_transcript": "Thank you for describing the issue with your laptop. Based on what you've told me, it sounds like a hardware problem with the battery. I've created a support ticket for you, and the reference number is A2 dash 7 7 4. Our technician will call you within two business days to schedule a repair appointment. In the meantime, please back up any important files, since the repair may require replacing some internal components. If the issue is covered under warranty, there will be no charge; otherwise, the estimated repair cost is thirty-five dollars. You can check the ticket status anytime using the reference number I gave you. Do you have any other questions? No, that's all, thank you.",
  "note_template": "Support ticket reference number: {{1}}. Technician will call within two business days. Estimated repair cost if not covered by warranty: {{2}} dollars. Customer advised to back up {{3}}.",
  "blanks": [
    {"accepted_answers": ["A2-774", "A2 774", "a2-774"], "max_words": 2, "case_sensitive": false},
    {"accepted_answers": ["thirty-five", "35", "thirty five"], "max_words": 2, "case_sensitive": false},
    {"accepted_answers": ["files", "important files"], "max_words": 2, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-B2-GF-02
- draft_id: LSTB-B2-GF-02
- level: B2
- question_type: gap_fill
- title: Event Logistics Note
- situation: An event coordinator briefing a colleague about venue logistics.
- audio_transcript: "Let me give you the details for Saturday's charity event. The venue is the Lakeside Hall, and it holds a maximum capacity of three hundred guests. We need to confirm final numbers with the caterer by Wednesday, since they need at least three days' notice to prepare. The hall itself is booked from four in the afternoon until eleven at night, giving us enough time to set up and clean afterward. Please remember that the deadline for submitting the guest list to security is Thursday at noon, so they can prepare the entry passes in time. If we miss that deadline, guests may face delays getting inside. Let me know if you have any questions about the schedule."
- listening_skill_tags: [number_time_price, following_instructions]
- estimated_audio_duration_seconds: 57

```json
{
  "audio_transcript": "Let me give you the details for Saturday's charity event. The venue is the Lakeside Hall, and it holds a maximum capacity of three hundred guests. We need to confirm final numbers with the caterer by Wednesday, since they need at least three days' notice to prepare. The hall itself is booked from four in the afternoon until eleven at night, giving us enough time to set up and clean afterward. Please remember that the deadline for submitting the guest list to security is Thursday at noon, so they can prepare the entry passes in time. If we miss that deadline, guests may face delays getting inside. Let me know if you have any questions about the schedule.",
  "note_template": "Venue capacity: {{1}} guests. Caterer confirmation deadline: Wednesday. Guest list deadline for security: {{2}} at noon. Hall booked until {{3}} at night.",
  "blanks": [
    {"accepted_answers": ["three hundred", "300"], "max_words": 2, "case_sensitive": false},
    {"accepted_answers": ["Thursday", "thursday"], "max_words": 1, "case_sensitive": false},
    {"accepted_answers": ["eleven", "11"], "max_words": 1, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-C1-MCQ-01
- draft_id: LSTB-C1-MCQ-01
- level: C1
- question_type: mcq
- title: Panel Discussion on Remote Work
- situation: A panel discussion between two professionals debating remote-work policy.
- audio_transcript: "Host: Tonight we're discussing whether companies should mandate a full return to the office. Maria, you've argued strongly in favor of flexible arrangements. Maria: That's right. The data consistently shows that employees who have some autonomy over where they work report higher satisfaction and, in many cases, comparable or even improved productivity. Forcing a rigid return ignores years of evidence we've gathered since the pandemic. Host: David, you disagree? David: I do, to an extent. I'm not arguing against flexibility altogether, but I think we've overcorrected. Spontaneous collaboration, mentorship, and the kind of informal knowledge-sharing that happens in hallways simply doesn't translate well to video calls. Maria: I'd push back on that. Well-structured hybrid models can preserve those benefits while still respecting employees' need for balance. David: Perhaps, but well-structured is doing a lot of work in that sentence. In practice, many hybrid policies end up satisfying no one, neither the collaboration advocates nor the flexibility advocates. Host: So it sounds like the real disagreement isn't flexibility versus none, but how well any given policy is actually designed and implemented."
- listening_skill_tags: [main_idea, explicit_detail, speaker_attitude]
- estimated_audio_duration_seconds: 80

```json
{
  "audio_transcript": "Host: Tonight we're discussing whether companies should mandate a full return to the office. Maria, you've argued strongly in favor of flexible arrangements. Maria: That's right. The data consistently shows that employees who have some autonomy over where they work report higher satisfaction and, in many cases, comparable or even improved productivity. Forcing a rigid return ignores years of evidence we've gathered since the pandemic. Host: David, you disagree? David: I do, to an extent. I'm not arguing against flexibility altogether, but I think we've overcorrected. Spontaneous collaboration, mentorship, and the kind of informal knowledge-sharing that happens in hallways simply doesn't translate well to video calls. Maria: I'd push back on that. Well-structured hybrid models can preserve those benefits while still respecting employees' need for balance. David: Perhaps, but well-structured is doing a lot of work in that sentence. In practice, many hybrid policies end up satisfying no one, neither the collaboration advocates nor the flexibility advocates. Host: So it sounds like the real disagreement isn't flexibility versus none, but how well any given policy is actually designed and implemented.",
  "subquestions": [
    {
      "question": "What is the main focus of this panel discussion?",
      "options": ["Whether companies should require a full return to the office", "Whether to increase employee salaries", "How to hire new remote employees", "How to measure employee productivity"],
      "correct_index": 0,
      "explanation": "The host introduces the topic as \"whether companies should mandate a full return to the office.\""
    },
    {
      "question": "According to Maria, what does the data show about employees with flexible arrangements?",
      "options": ["Lower productivity", "Higher satisfaction and comparable or improved productivity", "Higher rates of resignation", "No measurable difference at all"],
      "correct_index": 1,
      "explanation": "Maria says such employees \"report higher satisfaction and... comparable or even improved productivity.\""
    },
    {
      "question": "What is David's overall position in the discussion?",
      "options": ["He believes remote work should be banned entirely", "He fully agrees with Maria's position", "He accepts some flexibility but is concerned about lost collaboration", "He believes hybrid models always work well"],
      "correct_index": 2,
      "explanation": "David says \"I'm not arguing against flexibility altogether, but I think we've overcorrected\" regarding collaboration."
    }
  ]
}
```

---

### ITEM LSTB-C1-MCQ-02
- draft_id: LSTB-C1-MCQ-02
- level: C1
- question_type: mcq
- title: Business Strategy Meeting
- situation: An executive presenting a strategic pivot to stakeholders and explaining the reasoning.
- audio_transcript: "Thank you all for joining. I want to walk you through why we're proposing a shift in our market strategy. Over the past two years, our core product line has plateaued, largely because the market has become saturated with competitors offering nearly identical features at lower prices. Rather than continuing to compete purely on price, which would erode our margins further, we believe our strength lies in specialized customer support and customization, areas where larger competitors typically struggle to match us. This means reallocating a portion of our marketing budget away from broad advertising and toward account-based strategies targeting mid-sized clients who value that personalized service. I want to be clear that this isn't a retreat from growth; it's a recalibration of where we believe sustainable growth actually comes from, given the current competitive landscape. I recognize this represents a meaningful change in direction, and I welcome your questions and concerns before we finalize the plan next quarter."
- listening_skill_tags: [main_idea, explicit_detail, speaker_purpose]
- estimated_audio_duration_seconds: 80

```json
{
  "audio_transcript": "Thank you all for joining. I want to walk you through why we're proposing a shift in our market strategy. Over the past two years, our core product line has plateaued, largely because the market has become saturated with competitors offering nearly identical features at lower prices. Rather than continuing to compete purely on price, which would erode our margins further, we believe our strength lies in specialized customer support and customization, areas where larger competitors typically struggle to match us. This means reallocating a portion of our marketing budget away from broad advertising and toward account-based strategies targeting mid-sized clients who value that personalized service. I want to be clear that this isn't a retreat from growth; it's a recalibration of where we believe sustainable growth actually comes from, given the current competitive landscape. I recognize this represents a meaningful change in direction, and I welcome your questions and concerns before we finalize the plan next quarter.",
  "subquestions": [
    {
      "question": "What is the executive's main purpose in this talk?",
      "options": ["To propose a shift in market strategy", "To announce layoffs", "To report quarterly profits", "To introduce a new product line"],
      "correct_index": 0,
      "explanation": "The executive explains \"why we're proposing a shift in our market strategy.\""
    },
    {
      "question": "Where does the executive want to reallocate marketing budget toward?",
      "options": ["Broad advertising", "Account-based strategies targeting mid-sized clients", "International expansion", "A new product launch"],
      "correct_index": 1,
      "explanation": "The executive proposes moving budget \"toward account-based strategies targeting mid-sized clients.\""
    },
    {
      "question": "Why does the executive emphasize that this 'isn't a retreat from growth'?",
      "options": ["To reassure stakeholders that the change reflects strategic recalibration, not decline", "To announce that the company is closing certain divisions", "To justify a decrease in the marketing budget overall", "To explain a temporary pause in all business activity"],
      "correct_index": 0,
      "explanation": "The executive frames the change as \"a recalibration of where we believe sustainable growth actually comes from,\" not a decline."
    }
  ]
}
```

---

### ITEM LSTB-C1-MCQ-03
- draft_id: LSTB-C1-MCQ-03
- level: C1
- question_type: mcq
- title: Academic Interview on Urban Planning
- situation: An interviewer questioning an urban planning expert about contrasting views on city design.
- audio_transcript: "Interviewer: Many cities are now debating whether to prioritize car infrastructure or public transit expansion. What's your view? Expert: I think the framing itself is part of the problem. It's often presented as a binary choice, but the most successful cities I've studied treat it as a question of sequencing and integration rather than pure prioritization. Interviewer: Could you elaborate? Expert: Certainly. Cities that expanded transit without first addressing land use around stations often saw disappointing ridership, because people still needed a car for the last mile. Conversely, cities that invested heavily in highways alone tend to face worsening congestion within a decade, since new roads generate their own demand. Interviewer: So which comes first, ideally? Expert: Ideally, zoning reform that allows denser development near planned transit corridors happens in parallel with the transit investment itself. Without that alignment, you get the worst of both worlds, expensive infrastructure that doesn't fully solve the underlying mobility problem. Interviewer: A more nuanced picture than the debate usually allows. Expert: Exactly, and that nuance is often lost in public discourse."
- listening_skill_tags: [main_idea, explicit_detail, speaker_attitude]
- estimated_audio_duration_seconds: 80

```json
{
  "audio_transcript": "Interviewer: Many cities are now debating whether to prioritize car infrastructure or public transit expansion. What's your view? Expert: I think the framing itself is part of the problem. It's often presented as a binary choice, but the most successful cities I've studied treat it as a question of sequencing and integration rather than pure prioritization. Interviewer: Could you elaborate? Expert: Certainly. Cities that expanded transit without first addressing land use around stations often saw disappointing ridership, because people still needed a car for the last mile. Conversely, cities that invested heavily in highways alone tend to face worsening congestion within a decade, since new roads generate their own demand. Interviewer: So which comes first, ideally? Expert: Ideally, zoning reform that allows denser development near planned transit corridors happens in parallel with the transit investment itself. Without that alignment, you get the worst of both worlds, expensive infrastructure that doesn't fully solve the underlying mobility problem. Interviewer: A more nuanced picture than the debate usually allows. Expert: Exactly, and that nuance is often lost in public discourse.",
  "subquestions": [
    {
      "question": "What is the expert's main argument?",
      "options": ["Cities should only invest in highways", "The car-versus-transit debate is too simplistic; integration and sequencing matter more", "Public transit never works in any city", "Zoning reform is unnecessary for transit success"],
      "correct_index": 1,
      "explanation": "The expert says the successful cities treat it \"as a question of sequencing and integration rather than pure prioritization.\""
    },
    {
      "question": "According to the expert, what happens when cities invest heavily in highways alone?",
      "options": ["Congestion worsens within a decade", "Ridership increases significantly", "Property values decrease", "Transit use disappears completely"],
      "correct_index": 0,
      "explanation": "The expert says such cities \"tend to face worsening congestion within a decade.\""
    },
    {
      "question": "What does the expert suggest is the ideal approach?",
      "options": ["Prioritizing highways before any transit investment", "Zoning reform for dense development happening in parallel with transit investment", "Avoiding all new infrastructure investment", "Letting each city decide independently with no coordination"],
      "correct_index": 1,
      "explanation": "The expert says zoning reform \"happens in parallel with the transit investment itself.\""
    }
  ]
}
```

---

### ITEM LSTB-C1-GF-01
- draft_id: LSTB-C1-GF-01
- level: C1
- question_type: gap_fill
- title: Research Grant Summary Note
- situation: A university administrator briefing a researcher on grant details.
- audio_transcript: "Congratulations on your successful grant application. The funding body has approved a total award of ninety-five thousand dollars over two years. The first installment, sixty percent of the total, will be released once you submit the signed agreement, which is due by the thirtieth of April. The remaining funds will be released after your first progress report, which must be submitted twelve months into the project. Please note that the grant requires you to publish at least one peer-reviewed article by the end of the funding period, and to present preliminary findings at the annual research symposium. If you anticipate any delays, you must notify the funding body at least one month in advance, or the remaining funds may be withheld. Please also keep all receipts for equipment purchases, as they may be audited at any point during the grant period."
- listening_skill_tags: [number_time_price]
- estimated_audio_duration_seconds: 65

```json
{
  "audio_transcript": "Congratulations on your successful grant application. The funding body has approved a total award of ninety-five thousand dollars over two years. The first installment, sixty percent of the total, will be released once you submit the signed agreement, which is due by the thirtieth of April. The remaining funds will be released after your first progress report, which must be submitted twelve months into the project. Please note that the grant requires you to publish at least one peer-reviewed article by the end of the funding period, and to present preliminary findings at the annual research symposium. If you anticipate any delays, you must notify the funding body at least one month in advance, or the remaining funds may be withheld. Please also keep all receipts for equipment purchases, as they may be audited at any point during the grant period.",
  "note_template": "Total grant amount: {{1}} dollars over two years. Signed agreement deadline: {{2}}. Progress report required after {{3}} months.",
  "blanks": [
    {"accepted_answers": ["ninety-five thousand", "95000", "95,000", "ninety five thousand"], "max_words": 3, "case_sensitive": false},
    {"accepted_answers": ["the thirtieth of April", "thirtieth of April", "April 30", "30 April"], "max_words": 4, "case_sensitive": false},
    {"accepted_answers": ["twelve", "12"], "max_words": 1, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-C1-GF-02
- draft_id: LSTB-C1-GF-02
- level: C1
- question_type: gap_fill
- title: Corporate Product Launch Briefing Note
- situation: A product manager briefing the marketing team on launch logistics.
- audio_transcript: "Let's go over the key details for the product launch. The launch date has been confirmed for the twelfth of September, which gives the marketing team about six weeks to prepare campaign materials. Our target market for this initial phase is the Southeast Asian region, particularly urban areas with high smartphone penetration. The total marketing budget allocated for this launch is two hundred and forty thousand dollars, split roughly evenly between digital advertising and regional influencer partnerships. We're also planning a soft launch event in Singapore one week before the official date, limited to about fifty invited press and industry guests. Please make sure all localized content is finalized and translated by the end of August, since our translation partner needs at least two weeks to complete quality review before the launch date."
- listening_skill_tags: [number_time_price, place_name]
- estimated_audio_duration_seconds: 65

```json
{
  "audio_transcript": "Let's go over the key details for the product launch. The launch date has been confirmed for the twelfth of September, which gives the marketing team about six weeks to prepare campaign materials. Our target market for this initial phase is the Southeast Asian region, particularly urban areas with high smartphone penetration. The total marketing budget allocated for this launch is two hundred and forty thousand dollars, split roughly evenly between digital advertising and regional influencer partnerships. We're also planning a soft launch event in Singapore one week before the official date, limited to about fifty invited press and industry guests. Please make sure all localized content is finalized and translated by the end of August, since our translation partner needs at least two weeks to complete quality review before the launch date.",
  "note_template": "Launch date: the twelfth of September. Target market: {{1}}. Total marketing budget: {{2}} dollars. Localized content deadline: end of {{3}}.",
  "blanks": [
    {"accepted_answers": ["Southeast Asia", "Southeast Asian region", "southeast asia"], "max_words": 3, "case_sensitive": false},
    {"accepted_answers": ["two hundred and forty thousand", "240000", "240,000", "two hundred forty thousand"], "max_words": 5, "case_sensitive": false},
    {"accepted_answers": ["August", "august"], "max_words": 1, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-C2-MCQ-01
- draft_id: LSTB-C2-MCQ-01
- level: C2
- question_type: mcq
- title: Academic Lecture Excerpt — Cognitive Bias in Decision-Making
- situation: A university lecture excerpt on cognitive biases in economic decision-making.
- audio_transcript: "Today I want to examine why traditional economic models, which assume individuals act as rational, self-interested agents, often fail to predict real-world behavior with any precision. Behavioral economics has identified numerous systematic deviations from this idealized rationality, and I want to focus on one in particular: loss aversion. Kahneman and Tversky's foundational work demonstrated that individuals experience the pain of a loss roughly twice as intensely as the pleasure of an equivalent gain. This asymmetry has profound implications well beyond individual psychology; it shapes market behavior, retirement savings patterns, and even policy design. Consider, for instance, why framing a policy as preventing a loss, rather than securing an equivalent gain, tends to generate substantially higher public support, even when the underlying outcomes are mathematically identical. Critics of behavioral economics sometimes argue that these findings, while robust in laboratory settings, don't scale reliably to complex, real-world markets where multiple biases interact unpredictably. That's a fair methodological concern, but it doesn't undermine the core insight: rationality, as classical economics defines it, is an idealization rather than an empirical description of how people actually behave."
- listening_skill_tags: [main_idea, explicit_detail, following_argument]
- estimated_audio_duration_seconds: 87

```json
{
  "audio_transcript": "Today I want to examine why traditional economic models, which assume individuals act as rational, self-interested agents, often fail to predict real-world behavior with any precision. Behavioral economics has identified numerous systematic deviations from this idealized rationality, and I want to focus on one in particular: loss aversion. Kahneman and Tversky's foundational work demonstrated that individuals experience the pain of a loss roughly twice as intensely as the pleasure of an equivalent gain. This asymmetry has profound implications well beyond individual psychology; it shapes market behavior, retirement savings patterns, and even policy design. Consider, for instance, why framing a policy as preventing a loss, rather than securing an equivalent gain, tends to generate substantially higher public support, even when the underlying outcomes are mathematically identical. Critics of behavioral economics sometimes argue that these findings, while robust in laboratory settings, don't scale reliably to complex, real-world markets where multiple biases interact unpredictably. That's a fair methodological concern, but it doesn't undermine the core insight: rationality, as classical economics defines it, is an idealization rather than an empirical description of how people actually behave.",
  "subquestions": [
    {
      "question": "What is the main purpose of this lecture excerpt?",
      "options": ["To explain loss aversion as evidence against purely rational economic models", "To argue that classical economics is entirely correct", "To describe how to design retirement savings plans", "To criticize Kahneman and Tversky's research methods"],
      "correct_index": 0,
      "explanation": "The lecturer uses loss aversion to challenge the idealized-rationality assumption of classical economics."
    },
    {
      "question": "According to the lecture, how intensely do people experience loss compared to an equivalent gain?",
      "options": ["Equally intensely", "About half as intensely", "About twice as intensely", "Three times as intensely"],
      "correct_index": 2,
      "explanation": "The lecturer says people \"experience the pain of a loss roughly twice as intensely.\""
    },
    {
      "question": "Why does the speaker mention the critics' methodological concern near the end?",
      "options": ["To fully accept that behavioral economics is flawed", "To dismiss all criticism of behavioral economics as invalid", "To acknowledge a valid limitation while still defending the core argument", "To suggest that classical economics should be abandoned entirely"],
      "correct_index": 2,
      "explanation": "The speaker calls it \"a fair methodological concern, but it doesn't undermine the core insight.\""
    }
  ]
}
```

---

### ITEM LSTB-C2-MCQ-02
- draft_id: LSTB-C2-MCQ-02
- level: C2
- question_type: mcq
- title: Public Policy Briefing — Water Infrastructure
- situation: A public briefing on a proposed regional water infrastructure investment plan.
- audio_transcript: "Good evening. Tonight's briefing concerns the proposed regional water infrastructure investment plan. Our current system, much of it built over fifty years ago, loses an estimated eighteen percent of treated water through aging pipe networks before it ever reaches consumers. The proposed plan allocates funding to replace roughly a third of the highest-risk pipe segments over the next decade, prioritized based on failure likelihood rather than simple age. Some residents have raised concerns about the associated rate increase, which would amount to roughly four dollars per household monthly during the investment period. It's worth noting, however, that deferring this investment doesn't eliminate the cost; it merely shifts it forward, typically at a higher price given inflation and the increasing frequency of emergency repairs on failing infrastructure. Independent engineering assessments commissioned by the oversight board concluded that without intervention, unplanned service disruptions are likely to increase substantially within the next five to seven years. The board will vote on the plan next month, following a final round of public comment sessions scheduled for the coming three weeks."
- listening_skill_tags: [main_idea, explicit_detail, following_argument]
- estimated_audio_duration_seconds: 89

```json
{
  "audio_transcript": "Good evening. Tonight's briefing concerns the proposed regional water infrastructure investment plan. Our current system, much of it built over fifty years ago, loses an estimated eighteen percent of treated water through aging pipe networks before it ever reaches consumers. The proposed plan allocates funding to replace roughly a third of the highest-risk pipe segments over the next decade, prioritized based on failure likelihood rather than simple age. Some residents have raised concerns about the associated rate increase, which would amount to roughly four dollars per household monthly during the investment period. It's worth noting, however, that deferring this investment doesn't eliminate the cost; it merely shifts it forward, typically at a higher price given inflation and the increasing frequency of emergency repairs on failing infrastructure. Independent engineering assessments commissioned by the oversight board concluded that without intervention, unplanned service disruptions are likely to increase substantially within the next five to seven years. The board will vote on the plan next month, following a final round of public comment sessions scheduled for the coming three weeks.",
  "subquestions": [
    {
      "question": "What is this briefing mainly about?",
      "options": ["A proposed water infrastructure investment plan", "A new public transit system", "A change in local tax policy", "A new residential housing development"],
      "correct_index": 0,
      "explanation": "The speaker says \"Tonight's briefing concerns the proposed regional water infrastructure investment plan.\""
    },
    {
      "question": "What percentage of treated water is currently lost through aging pipes?",
      "options": ["Eight percent", "Eighteen percent", "Twenty-eight percent", "Thirty-eight percent"],
      "correct_index": 1,
      "explanation": "The speaker says the system \"loses an estimated eighteen percent of treated water.\""
    },
    {
      "question": "Why does the speaker mention that deferring the investment 'shifts the cost forward'?",
      "options": ["To suggest that delaying the plan avoids any real cost", "To recommend cancelling the infrastructure plan entirely", "To argue that postponing investment ultimately leads to higher costs later", "To announce that costs will decrease over time regardless of action"],
      "correct_index": 2,
      "explanation": "The speaker explains deferral is \"typically at a higher price given inflation and... emergency repairs.\""
    }
  ]
}
```

---

### ITEM LSTB-C2-MCQ-03
- draft_id: LSTB-C2-MCQ-03
- level: C2
- question_type: mcq
- title: Expert Panel — Artificial Intelligence Regulation
- situation: Two experts debating the pace and approach of AI regulation.
- audio_transcript: "Host: Dr. Chen, you've argued for a more cautious, slower regulatory approach to artificial intelligence. Chen: That's right. My concern is that regulation drafted hastily, in response to public anxiety rather than technical understanding, risks entrenching rules that either stifle beneficial innovation or, paradoxically, fail to address the actual risks we should be worried about. Host: Dr. Osei, you've been more vocal about the need for immediate action. Osei: I understand that concern, but I'd argue the greater risk lies in inaction. Waiting for perfect regulatory clarity, particularly given how quickly capabilities are advancing, means we could be addressing yesterday's problems once legislation finally passes. Chen: I don't disagree that capabilities are advancing quickly, but rushing tends to produce brittle frameworks that require constant amendment, which itself creates uncertainty for developers and the public alike. Osei: Perhaps, but a flawed framework we can iterate on seems preferable to a regulatory vacuum in a domain with genuinely significant societal stakes. Host: So the disagreement seems less about whether regulation is needed, and more about the acceptable cost of getting the timing wrong in either direction."
- listening_skill_tags: [main_idea, explicit_detail, speaker_attitude]
- estimated_audio_duration_seconds: 89

```json
{
  "audio_transcript": "Host: Dr. Chen, you've argued for a more cautious, slower regulatory approach to artificial intelligence. Chen: That's right. My concern is that regulation drafted hastily, in response to public anxiety rather than technical understanding, risks entrenching rules that either stifle beneficial innovation or, paradoxically, fail to address the actual risks we should be worried about. Host: Dr. Osei, you've been more vocal about the need for immediate action. Osei: I understand that concern, but I'd argue the greater risk lies in inaction. Waiting for perfect regulatory clarity, particularly given how quickly capabilities are advancing, means we could be addressing yesterday's problems once legislation finally passes. Chen: I don't disagree that capabilities are advancing quickly, but rushing tends to produce brittle frameworks that require constant amendment, which itself creates uncertainty for developers and the public alike. Osei: Perhaps, but a flawed framework we can iterate on seems preferable to a regulatory vacuum in a domain with genuinely significant societal stakes. Host: So the disagreement seems less about whether regulation is needed, and more about the acceptable cost of getting the timing wrong in either direction.",
  "subquestions": [
    {
      "question": "What is the central disagreement between Dr. Chen and Dr. Osei?",
      "options": ["The appropriate speed and timing of AI regulation", "Whether AI should be regulated at all", "Which country should regulate AI first", "Whether AI companies should be banned"],
      "correct_index": 0,
      "explanation": "The host summarizes it as a disagreement over \"the acceptable cost of getting the timing wrong.\""
    },
    {
      "question": "According to Dr. Chen, what risk does hasty regulation create?",
      "options": ["It always increases innovation", "It could stifle beneficial innovation or fail to address real risks", "It guarantees permanent legal clarity", "It has no effect on developers"],
      "correct_index": 1,
      "explanation": "Chen warns hasty rules \"risk... stifle beneficial innovation or... fail to address the actual risks.\""
    },
    {
      "question": "What does the host's closing remark suggest about the debate?",
      "options": ["The experts fully agree on every point", "Dr. Osei believes no regulation is necessary", "The real disagreement is about the cost of mistimed regulation, not whether regulation is needed", "Dr. Chen believes regulation should never happen"],
      "correct_index": 2,
      "explanation": "The host says the disagreement is \"less about whether regulation is needed, and more about... timing.\""
    }
  ]
}
```

---

### ITEM LSTB-C2-GF-01
- draft_id: LSTB-C2-GF-01
- level: C2
- question_type: gap_fill
- title: Academic Conference Logistics Note
- situation: A conference organizer briefing delegates on submission and registration logistics.
- audio_transcript: "Welcome to this year's International Symposium on Applied Linguistics. I'd like to outline a few key logistical details before we begin. Full paper submissions for next year's symposium must be received no later than the fifteenth of January, through the online submission portal only; email submissions will not be accepted under any circumstances. The submission fee is one hundred and twenty dollars for standard registrations, though this is waived for presenters affiliated with our partner institutions. Please note that abstracts exceeding the three-hundred-word limit will be automatically rejected by the portal's validation system, so please review your submissions carefully before the deadline. Successful applicants will be notified by the twentieth of February, allowing sufficient time to arrange travel before the symposium itself, which takes place in early May. Any requests for extensions must be submitted in writing at least two weeks before the original deadline; requests submitted after that point will not be considered under any circumstances."
- listening_skill_tags: [number_time_price]
- estimated_audio_duration_seconds: 74

```json
{
  "audio_transcript": "Welcome to this year's International Symposium on Applied Linguistics. I'd like to outline a few key logistical details before we begin. Full paper submissions for next year's symposium must be received no later than the fifteenth of January, through the online submission portal only; email submissions will not be accepted under any circumstances. The submission fee is one hundred and twenty dollars for standard registrations, though this is waived for presenters affiliated with our partner institutions. Please note that abstracts exceeding the three-hundred-word limit will be automatically rejected by the portal's validation system, so please review your submissions carefully before the deadline. Successful applicants will be notified by the twentieth of February, allowing sufficient time to arrange travel before the symposium itself, which takes place in early May. Any requests for extensions must be submitted in writing at least two weeks before the original deadline; requests submitted after that point will not be considered under any circumstances.",
  "note_template": "Submission deadline: the fifteenth of January. Submission fee: {{1}} dollars. Abstract word limit: {{2}} words. Notification date: {{3}}.",
  "blanks": [
    {"accepted_answers": ["one hundred and twenty", "120", "one hundred twenty"], "max_words": 4, "case_sensitive": false},
    {"accepted_answers": ["three hundred", "300"], "max_words": 2, "case_sensitive": false},
    {"accepted_answers": ["the twentieth of February", "twentieth of February", "February 20", "20 February"], "max_words": 4, "case_sensitive": false}
  ]
}
```

---

### ITEM LSTB-C2-GF-02
- draft_id: LSTB-C2-GF-02
- level: C2
- question_type: gap_fill
- title: Public Information Broadcast Note — Road Closure
- situation: A public transportation authority announcement about a road closure.
- audio_transcript: "This is an important public information announcement from the City Transportation Authority. Due to scheduled bridge maintenance, the Eastbound Riverside Bridge will be completely closed to all vehicle traffic starting Monday at eleven at night, and is expected to remain closed until the following Friday at five in the morning. During this period, all eastbound traffic should use the alternative route via Millbrook Avenue, which has been temporarily widened to accommodate the additional volume. Public bus routes normally crossing the bridge will be rerouted accordingly, and updated schedules are available on the authority's website. Residents requiring emergency access during the closure should contact the dedicated hotline at 555-0198, which will remain staffed twenty-four hours a day throughout the closure period. We apologize for any inconvenience and appreciate the public's patience while this essential maintenance work is completed."
- listening_skill_tags: [number_time_price, place_name]
- estimated_audio_duration_seconds: 74

```json
{
  "audio_transcript": "This is an important public information announcement from the City Transportation Authority. Due to scheduled bridge maintenance, the Eastbound Riverside Bridge will be completely closed to all vehicle traffic starting Monday at eleven at night, and is expected to remain closed until the following Friday at five in the morning. During this period, all eastbound traffic should use the alternative route via Millbrook Avenue, which has been temporarily widened to accommodate the additional volume. Public bus routes normally crossing the bridge will be rerouted accordingly, and updated schedules are available on the authority's website. Residents requiring emergency access during the closure should contact the dedicated hotline at 555-0198, which will remain staffed twenty-four hours a day throughout the closure period. We apologize for any inconvenience and appreciate the public's patience while this essential maintenance work is completed.",
  "note_template": "Bridge closes Monday at eleven at night until Friday at {{1}}. Alternative route: {{2}}. Emergency hotline number: {{3}}.",
  "blanks": [
    {"accepted_answers": ["five in the morning", "5am", "five am", "5 am"], "max_words": 4, "case_sensitive": false},
    {"accepted_answers": ["Millbrook Avenue", "millbrook avenue"], "max_words": 2, "case_sensitive": false},
    {"accepted_answers": ["555-0198", "5550198"], "max_words": 1, "case_sensitive": false}
  ]
}
```
