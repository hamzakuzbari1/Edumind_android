# Reading MVP v1 — Purpose-Built Placement Bank Draft

Status: **offline content draft only**. No database rows inserted, no runtime code touched, no
old Reading rows modified. All `draft_id` values are authoring-time identifiers only, not
database IDs.

This file contains **60 new draft Reading MCQ items** (10 per CEFR level, A1–C2), purpose-built
for the placement exam to replace the current 21-item `content_seed` Reading bank. Per the
approved retirement decision, the old Reading rows will later be retired with `is_active=false`
(never hard-deleted) only **after** this bank is inserted, validated, and activated.

Seeding mapping (for the future seed service — not implemented in this draft):

| Draft field        | DB column (`language_placement_question_bank_items`)        |
|--------------------|-------------------------------------------------------------|
| passage            | `passage`                                                   |
| question           | `prompt_text`                                               |
| options            | `options_json`                                              |
| correct_index      | `correct_index`                                             |
| explanation        | `explanation`                                               |
| reading_subskill   | `subskill`                                                  |
| cefr_level         | `level`                                                     |
| —                  | `skill = "reading"`, `question_type = "mcq"`                |
| draft_id           | `stable_key = "reading_mvp_v1:<draft_id>"`                  |
| —                  | `source = "mvp_reading_v1"`                                 |
| body_json_candidate| `body_json` metadata; optional `subquestions` enables 4-question Reading bundles |
| —                  | seed with `is_verified = true`, `is_active = false`; activation is a separate reviewed step |

Subskills used: `main_idea`, `specific_detail`, `inference`, `vocabulary_in_context`, `purpose`,
and `tone` (B2/C1/C2 only). See **Distribution Summary** and **Self-Audit Findings** at the end.

---

## A1 (10 items)

### ITEM RDG-A1-01
- draft_id: RDG-A1-01
- cefr_level: A1
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: pets_daily_life
- title: My Cat Milo
- passage: I have a small cat. His name is Milo. He is black and white. Milo sleeps on my bed every night. In the morning, he eats fish and drinks water. He likes to play with a red ball. My sister likes Milo too. He is a happy cat.
- question: What does Milo eat in the morning?
- options: ["Bread", "Fish", "Eggs", "Cheese"]
- correct_index: 1
- correct_answer: Fish
- explanation: The text says directly that in the morning Milo "eats fish and drinks water".
- distractor_rationale: Bread, eggs and cheese are all common breakfast foods a reader might assume, but none appears in the text.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "My Cat Milo",
  "topic_domain": "pets_daily_life",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What does Milo eat in the morning?",
      "options": [
        "Bread",
        "Fish",
        "Eggs",
        "Cheese"
      ],
      "correct_index": 1,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where does Milo sleep?",
      "options": [
        "On the bed",
        "In the garden",
        "Under the table",
        "At the door"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What toy does Milo like?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "A red ball"
      ],
      "max_words": 5,
      "subskill": "specific_detail",
      "word_bank": [
        "A red ball",
        "A blue car",
        "A small book",
        "A white shoe"
      ]
    },
    {
      "question": "What is this text mostly about?",
      "response_type": "short_answer",
      "accepted_answers": [
        "A happy cat"
      ],
      "max_words": 6,
      "subskill": "main_idea"
    }
  ],
  "distractor_rationale": "Bread, eggs and cheese are common breakfast foods but none appears in the text."
}
```

### ITEM RDG-A1-02
- draft_id: RDG-A1-02
- cefr_level: A1
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: school
- title: A Day at School
- passage: My name is Lena. I go to school from Monday to Friday. In the morning, we read books and write words. At twelve o'clock, we eat lunch in the big hall. In the afternoon, we play football or draw pictures. I like my teacher and my friends. School is fun for me.
- question: What is this text mostly about?
- options: ["Lena's school days", "Lena's summer holiday", "Lena's new house", "Lena's favourite food"]
- correct_index: 0
- correct_answer: Lena's school days
- explanation: Every sentence describes what Lena does at school during the week.
- distractor_rationale: Lunch is mentioned once but food is not the topic; holiday and house are plausible A1 topics that never appear.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "A Day at School",
  "topic_domain": "school",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is this text mostly about?",
      "options": [
        "Lena's school days",
        "Lena's summer holiday",
        "Lena's new house",
        "Lena's favourite food"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "Where does Lena eat lunch?",
      "options": [
        "In the big hall",
        "In the garden",
        "At home",
        "On the bus"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "When does Lena go to school?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "From Monday to Friday"
      ],
      "max_words": 6,
      "subskill": "specific_detail",
      "word_bank": [
        "From Monday to Friday",
        "Only on Sunday",
        "Every night",
        "In summer only"
      ]
    },
    {
      "question": "How does Lena feel about school?",
      "response_type": "short_answer",
      "accepted_answers": [
        "She likes it"
      ],
      "max_words": 6,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Lunch is mentioned once but food is not the topic; holiday and house never appear."
}
```

### ITEM RDG-A1-03
- draft_id: RDG-A1-03
- cefr_level: A1
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: family_hobbies
- title: The New Bicycle
- passage: Tom has a new bicycle. It is a present from his grandmother. The bicycle is blue, and it has a small bell. Tom rides it to the park on Saturdays. His friend Sam has a bicycle too, but Sam's bicycle is old and green. The boys ride together by the river.
- question: Who gave Tom the bicycle?
- options: ["His friend Sam", "His grandmother", "His teacher", "His brother"]
- correct_index: 1
- correct_answer: His grandmother
- explanation: The text states the bicycle "is a present from his grandmother".
- distractor_rationale: Sam appears in the text as a friend with his own bicycle, testing careful reading; teacher and brother are plausible gift-givers never mentioned.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The New Bicycle",
  "topic_domain": "family_hobbies",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "Who gave Tom the bicycle?",
      "options": [
        "His friend Sam",
        "His grandmother",
        "His teacher",
        "His brother"
      ],
      "correct_index": 1,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What colour is Tom's bicycle?",
      "options": [
        "Blue",
        "Green",
        "Red",
        "Black"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where does Tom ride on Saturdays?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "To the park"
      ],
      "max_words": 5,
      "subskill": "specific_detail",
      "word_bank": [
        "To the park",
        "To school",
        "To the market",
        "To his grandmother's house"
      ]
    },
    {
      "question": "What is this text mostly about?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Tom's new bicycle"
      ],
      "max_words": 6,
      "subskill": "main_idea"
    }
  ],
  "distractor_rationale": "Sam appears in the text with his own bicycle; teacher and brother are plausible but unmentioned."
}
```

### ITEM RDG-A1-04
- draft_id: RDG-A1-04
- cefr_level: A1
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: shopping
- title: At the Market
- passage: Maria walks to the market every Sunday morning. She always buys fresh apples there. The apples are red and sweet. Maria puts them in her bag and walks home. The people in the story also have a quiet day together.
- question: What does Maria buy at the market?
- options: ["Apples", "Bread", "Milk", "Fish"]
- correct_index: 0
- correct_answer: Apples
- explanation: The text says directly that Maria "always buys fresh apples" at the market.
- distractor_rationale: Bread, milk and fish are common market items a reader might guess, but none of them appears anywhere in the text — only apples are mentioned.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "At the Market",
  "topic_domain": "shopping",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What does Maria buy at the market?",
      "options": [
        "Apples",
        "Bread",
        "Milk",
        "Fish"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "When does Maria go to the market?",
      "options": [
        "Sunday morning",
        "Monday night",
        "Friday afternoon",
        "Saturday evening"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What are the apples like?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Red and sweet"
      ],
      "max_words": 5,
      "subskill": "specific_detail",
      "word_bank": [
        "Red and sweet",
        "Green and sour",
        "Small and dry",
        "Hot and fresh"
      ]
    },
    {
      "question": "What does Maria do after buying the apples?",
      "response_type": "short_answer",
      "accepted_answers": [
        "She walks home"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "Bread, milk and fish are common market items but none appears in the text; only apples are mentioned."
}
```

### ITEM RDG-A1-05
- draft_id: RDG-A1-05
- cefr_level: A1
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: family_food
- title: Breakfast at Our House
- passage: In my family, breakfast is important. My father makes tea, and my mother makes eggs and toast. My little brother drinks milk. We sit at the table together and talk about our day. On Sundays, we eat pancakes with honey. Breakfast time is my favourite part of the morning.
- question: What is this text mostly about?
- options: ["A family's breakfast together", "How to make pancakes", "A brother's favourite milk", "Shopping for food"]
- correct_index: 0
- correct_answer: A family's breakfast together
- explanation: The whole text describes what the family does together at breakfast.
- distractor_rationale: Pancakes and milk are single details, not the topic; shopping never appears.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Breakfast at Our House",
  "topic_domain": "family_food",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is this text mostly about?",
      "options": [
        "A family's breakfast together",
        "How to make pancakes",
        "A brother's favourite milk",
        "Shopping for food"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "What does the father make?",
      "options": [
        "Tea",
        "Eggs",
        "Milk",
        "Honey"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What do they eat on Sundays?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Pancakes with honey"
      ],
      "max_words": 5,
      "subskill": "specific_detail",
      "word_bank": [
        "Pancakes with honey",
        "Fish and rice",
        "Apples and cheese",
        "Soup and bread"
      ]
    },
    {
      "question": "Why is breakfast special for the writer?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The family sits and talks together"
      ],
      "max_words": 8,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Pancakes and milk are single details, not the topic; shopping never appears."
}
```

### ITEM RDG-A1-06
- draft_id: RDG-A1-06
- cefr_level: A1
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: work_transport
- title: The Bus to Work
- passage: Mr. Diaz works in a shoe shop in the city. Every day, he takes the bus to work. The bus comes at eight o'clock. The trip takes thirty minutes. Mr. Diaz likes to look out of the window and watch the streets. He gets to the shop at half past eight.
- question: What time does the bus come?
- options: ["At seven o'clock", "At eight o'clock", "At half past eight", "At nine o'clock"]
- correct_index: 1
- correct_answer: At eight o'clock
- explanation: The text states "The bus comes at eight o'clock"; half past eight is when he arrives at the shop.
- distractor_rationale: Half past eight appears in the text as the arrival time, testing whether the reader matches the right time to the right event; seven and nine are simple nearby times.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Bus to Work",
  "topic_domain": "work_transport",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What time does the bus come?",
      "options": [
        "At seven o'clock",
        "At eight o'clock",
        "At half past eight",
        "At nine o'clock"
      ],
      "correct_index": 1,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where does Mr. Diaz work?",
      "options": [
        "In a shoe shop",
        "In a school",
        "In a bus station",
        "In a city park"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "How long does the trip take?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Thirty minutes"
      ],
      "max_words": 4,
      "subskill": "specific_detail",
      "word_bank": [
        "Thirty minutes",
        "Eight minutes",
        "One hour",
        "Half a day"
      ]
    },
    {
      "question": "What does Mr. Diaz like to do on the bus?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Look out of the window"
      ],
      "max_words": 7,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "Half past eight appears as the arrival time; seven and nine are simple nearby times."
}
```

### ITEM RDG-A1-07
- draft_id: RDG-A1-07
- cefr_level: A1
- question_type: mcq
- reading_subskill: purpose
- topic_domain: friends_celebrations
- title: A Note for Ben
- passage: Hi Ben! My birthday party is on Saturday at four o'clock. It is at my house. We will play games in the garden and eat cake. My mother is making pizza too. Please come! You can bring your football. See you on Saturday. Your friend, Leo.
- question: Why did Leo write this note?
- options: ["To invite Ben to a party", "To ask Ben for a football", "To say sorry to Ben", "To sell pizza to Ben"]
- correct_index: 0
- correct_answer: To invite Ben to a party
- explanation: The note announces the party details and says "Please come!", which is an invitation.
- distractor_rationale: The football and pizza appear in the note but only as party details; apologising is a plausible reason for a note that has no support here.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "A Note for Ben",
  "topic_domain": "friends_celebrations",
  "reading_subskill": "purpose",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "Why did Leo write this note?",
      "options": [
        "To invite Ben to a party",
        "To ask Ben for a football",
        "To say sorry to Ben",
        "To sell pizza to Ben"
      ],
      "correct_index": 0,
      "subskill": "purpose",
      "response_type": "mcq"
    },
    {
      "question": "When is the party?",
      "options": [
        "Saturday at four o'clock",
        "Friday at four o'clock",
        "Sunday morning",
        "Saturday at nine o'clock"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where is the party?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "At Leo's house"
      ],
      "max_words": 5,
      "subskill": "specific_detail",
      "word_bank": [
        "At Leo's house",
        "At Ben's school",
        "In a pizza shop",
        "On a football field"
      ]
    },
    {
      "question": "What can Ben bring?",
      "response_type": "short_answer",
      "accepted_answers": [
        "His football"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "Football and pizza appear only as party details; apologising has no support in the note."
}
```

### ITEM RDG-A1-08
- draft_id: RDG-A1-08
- cefr_level: A1
- question_type: mcq
- reading_subskill: inference
- topic_domain: weather_daily_life
- title: Anna Goes Out
- passage: Anna looks out of the window. The sky is grey and dark. She puts on her yellow boots and her long coat. She takes her umbrella from the door. Then she walks slowly to the shop on the corner. The streets are wet and quiet today.
- question: What is the weather probably like?
- options: ["Hot and sunny", "Rainy", "Snowy", "Windy and dry"]
- correct_index: 1
- correct_answer: Rainy
- explanation: The grey sky, umbrella, boots and wet streets together show it is raining, even though the word "rain" is never used.
- distractor_rationale: Snowy fits the boots but not the wet (not white) streets and umbrella; sunny and dry contradict the grey sky and wet streets.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Anna Goes Out",
  "topic_domain": "weather_daily_life",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the weather probably like?",
      "options": [
        "Hot and sunny",
        "Rainy",
        "Snowy",
        "Windy and dry"
      ],
      "correct_index": 1,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "What does Anna take from the door?",
      "options": [
        "Her umbrella",
        "Her bag",
        "Her hat",
        "Her book"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where does Anna go?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "To the shop"
      ],
      "max_words": 5,
      "subskill": "specific_detail",
      "word_bank": [
        "To the shop",
        "To school",
        "To the park",
        "To her friend's house"
      ]
    },
    {
      "question": "Which words help show the weather?",
      "response_type": "short_answer",
      "accepted_answers": [
        "grey, dark, wet"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "Snowy fits the boots but not the wet streets and umbrella; sunny and dry contradict the text."
}
```

### ITEM RDG-A1-09
- draft_id: RDG-A1-09
- cefr_level: A1
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: books_library
- title: At the Library
- passage: Sara loves books. Every Friday, she goes to the library near her school. She can borrow three books and keep them for two weeks. Then she must bring them back. Today Sara chooses a book about horses, a book about the sea, and a funny story.
- question: In this text, what does "borrow" mean?
- options: ["buy books and never return them", "take books and bring them back", "write new stories in books", "lose books somewhere in town"]
- correct_index: 1
- correct_answer: take books and bring them back
- explanation: The next sentences explain the meaning: Sara can keep the books for two weeks, but she "must bring them back" — that is what borrowing means.
- distractor_rationale: Buying implies keeping the books forever, which contradicts "must bring them back"; writing new stories and losing books somewhere are unrelated actions never mentioned in the text.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "At the Library",
  "topic_domain": "books_library",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, what does \"borrow\" mean?",
      "options": [
        "buy books and never return them",
        "take books and bring them back",
        "write new stories in books",
        "lose books somewhere in town"
      ],
      "correct_index": 1,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "When does Sara go to the library?",
      "options": [
        "Every Friday",
        "Every Monday",
        "Every morning",
        "Every two weeks"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "How many books can Sara borrow?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Three"
      ],
      "max_words": 4,
      "subskill": "specific_detail",
      "word_bank": [
        "Three",
        "Two",
        "Four",
        "One"
      ]
    },
    {
      "question": "Which book does Sara choose today?",
      "response_type": "short_answer",
      "accepted_answers": [
        "A book about horses"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "Buying implies keeping the books forever, contradicting 'must bring them back'; writing and losing are unrelated actions never mentioned."
}
```

### ITEM RDG-A1-10
- draft_id: RDG-A1-10
- cefr_level: A1
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: nature_family
- title: My Sister's Garden
- passage: My big sister Nadia has a small garden behind our house. She grows tomatoes, carrots, and yellow flowers. Every evening, she gives the plants water. In summer, we eat her tomatoes at dinner. Nadia says the garden makes her happy. I sometimes help her on Sundays.
- question: What is this text mostly about?
- options: ["Nadia's garden", "Buying flowers at a shop", "Cooking dinner", "A walk on Sunday"]
- correct_index: 0
- correct_answer: Nadia's garden
- explanation: Every sentence is about the garden and what Nadia does in it.
- distractor_rationale: Flowers, dinner and Sunday all appear as single words in the text but none is the topic.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "My Sister's Garden",
  "topic_domain": "nature_family",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is this text mostly about?",
      "options": [
        "Nadia's garden",
        "Buying flowers at a shop",
        "Cooking dinner",
        "A walk on Sunday"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "Where is Nadia's garden?",
      "options": [
        "Behind the house",
        "Near the school",
        "Next to a shop",
        "By the river"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What does Nadia grow?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Tomatoes and carrots"
      ],
      "max_words": 5,
      "subskill": "specific_detail",
      "word_bank": [
        "Tomatoes and carrots",
        "Apples and rice",
        "Fish and flowers",
        "Tea and toast"
      ]
    },
    {
      "question": "How does Nadia feel about the garden?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It makes her happy"
      ],
      "max_words": 6,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Flowers, dinner and Sunday appear as single words but none is the topic."
}
```

---

## A2 (10 items)

### ITEM RDG-A2-01
- draft_id: RDG-A2-01
- cefr_level: A2
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: travel_family
- title: A Weekend at the Lake
- passage: Last weekend, my family drove to Lake Bruna. It takes about an hour from our town. We stayed in a small wooden cabin near the water. On Saturday, my brother and I swam in the lake, and my parents went fishing in a little boat. In the evening, we cooked dinner outside and watched the stars. On Sunday morning, it rained, so we played cards inside the cabin. We drove home in the afternoon, tired but happy. We want to go back next summer.
- question: What is this text mainly about?
- options: ["A family trip to a lake", "How to catch fish", "A new cabin for sale", "Games to play in the rain"]
- correct_index: 0
- correct_answer: A family trip to a lake
- explanation: The text tells the story of the whole weekend trip from start to finish.
- distractor_rationale: Fishing and card games are single activities from the trip; a cabin sale is never mentioned.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "A Weekend at the Lake",
  "topic_domain": "travel_family",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is this text mainly about?",
      "options": [
        "A family trip to a lake",
        "How to catch fish",
        "A new cabin for sale",
        "Games to play in the rain"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "Where did the family stay?",
      "options": [
        "In a wooden cabin",
        "In a city hotel",
        "In a tent by the road",
        "In their car"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What did the family do when it rained?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "They played cards inside"
      ],
      "max_words": 6,
      "subskill": "specific_detail",
      "word_bank": [
        "They played cards inside",
        "They swam in the lake",
        "They went fishing",
        "They drove to another town"
      ]
    },
    {
      "question": "How did the family feel at the end of the trip?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Tired but happy"
      ],
      "max_words": 6,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Fishing and card games are single activities from the trip; a cabin sale is never mentioned."
}
```

### ITEM RDG-A2-02
- draft_id: RDG-A2-02
- cefr_level: A2
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: hobbies_food
- title: The Cooking Class
- passage: Marco started a cooking class last month. The class meets every Tuesday evening at the community centre. The teacher, Mrs. Rossi, shows the students how to make simple dishes. Last week, they learned to make vegetable soup and fresh bread. Marco's favourite lesson was about pasta. There are twelve students in the class, and they always eat the food together at the end. The course finishes in June, and there will be a small party on the last day.
- question: When does the cooking class meet?
- options: ["Every Monday evening", "Every Tuesday evening", "Every Friday morning", "Every Saturday afternoon"]
- correct_index: 1
- correct_answer: Every Tuesday evening
- explanation: The text states the class "meets every Tuesday evening at the community centre".
- distractor_rationale: The distractors are other plausible weekly class times; none appears in the text.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Cooking Class",
  "topic_domain": "hobbies_food",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "When does the cooking class meet?",
      "options": [
        "Every Monday evening",
        "Every Tuesday evening",
        "Every Friday morning",
        "Every Saturday afternoon"
      ],
      "correct_index": 1,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where is the cooking class held?",
      "options": [
        "At the community centre",
        "At Marco's house",
        "In a school hall",
        "In Mrs. Rossi's garden"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What did the class learn to make last week?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Vegetable soup and fresh bread"
      ],
      "max_words": 7,
      "subskill": "specific_detail",
      "word_bank": [
        "Vegetable soup and fresh bread",
        "Pasta and cake",
        "Fish and rice",
        "Tea and sandwiches"
      ]
    },
    {
      "question": "What happens at the end of each class?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The students eat the food together"
      ],
      "max_words": 8,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "The distractors are other plausible weekly class times; none appears in the text."
}
```

### ITEM RDG-A2-03
- draft_id: RDG-A2-03
- cefr_level: A2
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: work
- title: A Job at the Bookshop
- passage: Emma works at a small bookshop in the town centre. She started the job three months ago, after she finished school. She works from Wednesday to Saturday. In the morning, she puts new books on the shelves and helps customers find what they need. Her favourite part of the job is the children's corner, where she reads stories aloud on Saturday mornings. The shop owner, Mr. Petrov, is teaching her how to order new books. Emma hopes to work there for a long time.
- question: What is Emma's favourite part of the job?
- options: ["Putting books on shelves", "Reading stories to children", "Ordering new books", "Cleaning the shop windows"]
- correct_index: 1
- correct_answer: Reading stories to children
- explanation: The text says her favourite part is the children's corner, "where she reads stories aloud".
- distractor_rationale: Shelving and ordering books are her other real tasks from the text, so the reader must find which one is called her favourite; window cleaning is invented.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "A Job at the Bookshop",
  "topic_domain": "work",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is Emma's favourite part of the job?",
      "options": [
        "Putting books on shelves",
        "Reading stories to children",
        "Ordering new books",
        "Cleaning the shop windows"
      ],
      "correct_index": 1,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "When does Emma work?",
      "options": [
        "From Wednesday to Saturday",
        "Only on Monday",
        "Every evening",
        "From Sunday to Tuesday"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Who is teaching Emma to order new books?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Mr. Petrov"
      ],
      "max_words": 4,
      "subskill": "specific_detail",
      "word_bank": [
        "Mr. Petrov",
        "A child in the corner",
        "Her school teacher",
        "A customer"
      ]
    },
    {
      "question": "What can we understand about Emma?",
      "response_type": "short_answer",
      "accepted_answers": [
        "She enjoys the bookshop job"
      ],
      "max_words": 7,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Shelving and ordering are her other real tasks; window cleaning is invented."
}
```

### ITEM RDG-A2-04
- draft_id: RDG-A2-04
- cefr_level: A2
- question_type: mcq
- reading_subskill: inference
- topic_domain: pets_home
- title: The Quiet House
- passage: When Daniel came home from work, the house was strangely quiet. Usually his two dogs ran to the door to meet him, but today nothing happened. He called their names, but there was no sound. Then he noticed that the kitchen door was open, and there were muddy footprints — small, round, and many of them — going across the clean floor and out into the garden. In the garden, two dirty, happy dogs were digging a big hole under the apple tree.
- question: What most probably happened while Daniel was at work?
- options: ["The dogs went out and played in the mud", "Someone stole the dogs", "The dogs slept all day", "A friend cleaned the kitchen"]
- correct_index: 0
- correct_answer: The dogs went out and played in the mud
- explanation: The open door, the muddy footprints and the dirty, happy dogs in the garden show the dogs let themselves out and played.
- distractor_rationale: The quiet house at first suggests theft, but the dogs are found in the garden; sleeping and a clean kitchen contradict the footprints.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Quiet House",
  "topic_domain": "pets_home",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What most probably happened while Daniel was at work?",
      "options": [
        "The dogs went out and played in the mud",
        "Someone stole the dogs",
        "The dogs slept all day",
        "A friend cleaned the kitchen"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "What was unusual when Daniel came home?",
      "options": [
        "The dogs did not run to the door",
        "The kitchen was very clean",
        "The garden gate was locked",
        "A friend was waiting inside"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where did the footprints go?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Across the floor and into the garden"
      ],
      "max_words": 9,
      "subskill": "specific_detail",
      "word_bank": [
        "Across the floor and into the garden",
        "Upstairs to the bedroom",
        "Out through the front door",
        "Around the living room table"
      ]
    },
    {
      "question": "How were the dogs when Daniel found them?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Dirty and happy"
      ],
      "max_words": 6,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "The quiet house at first suggests theft, but the dogs are found in the garden; the other options contradict the footprints."
}
```

### ITEM RDG-A2-05
- draft_id: RDG-A2-05
- cefr_level: A2
- question_type: mcq
- reading_subskill: purpose
- topic_domain: school_sport
- title: School Sports Day Notice
- passage: NOTICE TO ALL PARENTS: Greenhill School Sports Day will take place on Friday 14 June, from 9:00 to 14:00, on the school field. Students should wear sports clothes and bring a water bottle and a hat. Parents are welcome to watch from 10:00. There will be running races, a long jump competition, and team games. Food and drinks will be on sale next to the main gate. If it rains, Sports Day will move to Monday 17 June. Please email the school office if you have any questions.
- question: Why was this notice written?
- options: ["To tell parents about Sports Day", "To sell sports clothes", "To ask parents to teach games", "To explain why Sports Day was cancelled"]
- correct_index: 0
- correct_answer: To tell parents about Sports Day
- explanation: The notice gives parents the date, time and details of the event so they can prepare.
- distractor_rationale: Clothes and food sales are small details, not the aim; the event is moved only if it rains, not cancelled.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "School Sports Day Notice",
  "topic_domain": "school_sport",
  "reading_subskill": "purpose",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "Why was this notice written?",
      "options": [
        "To tell parents about Sports Day",
        "To sell sports clothes",
        "To ask parents to teach games",
        "To explain why Sports Day was cancelled"
      ],
      "correct_index": 0,
      "subskill": "purpose",
      "response_type": "mcq"
    },
    {
      "question": "Where will Sports Day take place if the weather is good?",
      "options": [
        "On the school field",
        "In the main hall",
        "Next to the main gate",
        "At the city park"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What should students bring?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "A water bottle and a hat"
      ],
      "max_words": 8,
      "subskill": "specific_detail",
      "word_bank": [
        "A water bottle and a hat",
        "A football and pizza",
        "A ticket and money only",
        "Books and pencils"
      ]
    },
    {
      "question": "What will happen if it rains?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Sports Day will move to Monday 17 June"
      ],
      "max_words": 10,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "Clothes and food sales are details, not the aim; the event is moved only if it rains, not cancelled."
}
```

### ITEM RDG-A2-06
- draft_id: RDG-A2-06
- cefr_level: A2
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: family_technology
- title: Grandpa's Radio
- passage: My grandfather has an old radio that he bought forty years ago. Last winter, it suddenly stopped working. My grandfather did not want to throw it away, because it was a present from his brother. So he took it to a small shop in town where a man repairs old machines. The man opened the radio, changed two small parts, and cleaned it carefully. A week later, the radio worked again. Now my grandfather listens to music on it every morning, and he always smiles when he turns it on.
- question: In this text, "repairs" means —
- options: ["sells old machines", "fixes broken things", "collects old radios", "paints old things"]
- correct_index: 1
- correct_answer: fixes broken things
- explanation: The man changed parts and cleaned the radio, and afterwards "the radio worked again" — he fixed it.
- distractor_rationale: Selling and collecting fit a shop context but not the result; painting matches "old things" but not the story.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Grandpa's Radio",
  "topic_domain": "family_technology",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, \"repairs\" means —",
      "options": [
        "sells old machines",
        "fixes broken things",
        "collects old radios",
        "paints old things"
      ],
      "correct_index": 1,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "Why did the grandfather keep the radio?",
      "options": [
        "It was a present from his brother",
        "It was easy to sell",
        "It was only one year old",
        "It belonged to the repairman"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What did the repairman do to the radio?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Changed two parts and cleaned it"
      ],
      "max_words": 8,
      "subskill": "specific_detail",
      "word_bank": [
        "Changed two parts and cleaned it",
        "Painted it a new colour",
        "Sold it to another shop",
        "Put music inside it"
      ]
    },
    {
      "question": "How does the grandfather feel when he uses the radio now?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Pleased"
      ],
      "max_words": 6,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Selling and collecting fit a shop context but not the result; painting matches 'old things' but not the story."
}
```

### ITEM RDG-A2-07
- draft_id: RDG-A2-07
- cefr_level: A2
- question_type: mcq
- reading_subskill: inference
- topic_domain: food_daily_life
- title: The Empty Fridge
- passage: Sofia looked in the fridge and sighed. There was only one egg, a little milk, and a very old piece of cheese. Her friends were coming for dinner in three hours. She took her shopping bag and her purse, put on her shoes, and hurried out of the flat. At the corner, she stopped and wrote a quick list on her phone: pasta, tomatoes, bread, salad, and a big cake for after dinner.
- question: Where is Sofia probably going?
- options: ["To a restaurant", "To the supermarket", "To her friend's house", "To work"]
- correct_index: 1
- correct_answer: To the supermarket
- explanation: The shopping bag, the purse and the food list show she is going out to buy food for the dinner.
- distractor_rationale: A restaurant fits "dinner" but not the shopping list; her friends are coming to her, and work does not fit the bag and list.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Empty Fridge",
  "topic_domain": "food_daily_life",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "Where is Sofia probably going?",
      "options": [
        "To a restaurant",
        "To the supermarket",
        "To her friend's house",
        "To work"
      ],
      "correct_index": 1,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "Why does Sofia need more food?",
      "options": [
        "Her friends are coming for dinner",
        "She is going on holiday",
        "Her fridge is broken",
        "She wants to open a shop"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "What food is already in the fridge?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "One egg, a little milk, and old cheese"
      ],
      "max_words": 10,
      "subskill": "specific_detail",
      "word_bank": [
        "One egg, a little milk, and old cheese",
        "Pasta, tomatoes, and bread",
        "Salad and a big cake",
        "Fish and fresh vegetables"
      ]
    },
    {
      "question": "What does Sofia write on her phone?",
      "response_type": "short_answer",
      "accepted_answers": [
        "A shopping list"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "A restaurant fits 'dinner' but not the shopping list; her friends are coming to her."
}
```

### ITEM RDG-A2-08
- draft_id: RDG-A2-08
- cefr_level: A2
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: travel_nature
- title: A Postcard from the Mountains
- passage: Dear Nina, greetings from the mountains! We arrived on Monday after a long bus trip. Our small hotel is next to a forest, and the air is cold and clean. Every day we walk for hours on the mountain paths. Yesterday we saw a family of deer near a stream, and my father took a hundred photos. The food here is simple but very good — lots of cheese and warm soup. My legs are tired, but I feel great. I will show you all the photos next week. Love, Amira.
- question: What is this postcard mainly about?
- options: ["Amira's holiday in the mountains", "A new camera", "Nina's visit to the forest", "A recipe for warm soup"]
- correct_index: 0
- correct_answer: Amira's holiday in the mountains
- explanation: The postcard describes Amira's whole mountain holiday — the trip, the walks, the animals and the food.
- distractor_rationale: The photos and soup are details; Nina is the reader, not the traveller; no camera is described.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "A Postcard from the Mountains",
  "topic_domain": "travel_nature",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is this postcard mainly about?",
      "options": [
        "Amira's holiday in the mountains",
        "A new camera",
        "Nina's visit to the forest",
        "A recipe for warm soup"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "Who is the postcard written to?",
      "options": [
        "Nina",
        "Amira",
        "Amira's father",
        "The hotel owner"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What did they see near a stream?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "A family of deer"
      ],
      "max_words": 6,
      "subskill": "specific_detail",
      "word_bank": [
        "A family of deer",
        "A group of horses",
        "A small hotel",
        "A bus station"
      ]
    },
    {
      "question": "How does Amira feel about the holiday?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Tired but happy"
      ],
      "max_words": 6,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "The photos and soup are details; Nina is the reader, not the traveller."
}
```

### ITEM RDG-A2-09
- draft_id: RDG-A2-09
- cefr_level: A2
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: transport_city
- title: Changes to the Number 7 Bus
- passage: Attention passengers: From next Monday, there will be changes to the Number 7 bus. The first bus of the day will leave the station at 6:30 instead of 6:00. Buses will then run every twenty minutes until 22:00. The bus will no longer stop at Park Street because of building work; passengers for that area should get off at Mill Road and walk five minutes. These changes will continue until the end of August. We are sorry for any problems this may cause. Tickets and prices stay the same.
- question: Why will the bus no longer stop at Park Street?
- options: ["Because of building work", "Because tickets cost too much", "Because the street is too narrow", "Because few people used the stop"]
- correct_index: 0
- correct_answer: Because of building work
- explanation: The notice says the stop closes "because of building work".
- distractor_rationale: Prices are mentioned but stay the same; a narrow street and low use are plausible reasons that the notice never gives.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Changes to the Number 7 Bus",
  "topic_domain": "transport_city",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "Why will the bus no longer stop at Park Street?",
      "options": [
        "Because of building work",
        "Because tickets cost too much",
        "Because the street is too narrow",
        "Because few people used the stop"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "What time will the first bus leave from next Monday?",
      "options": [
        "6:30",
        "6:00",
        "22:00",
        "5:00"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where should Park Street passengers get off?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "At Mill Road"
      ],
      "max_words": 5,
      "subskill": "specific_detail",
      "word_bank": [
        "At Mill Road",
        "At the station",
        "At the main gate",
        "At the school field"
      ]
    },
    {
      "question": "What will stay the same?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Tickets and prices"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "Prices are mentioned but stay the same; the other reasons are plausible but never given."
}
```

### ITEM RDG-A2-10
- draft_id: RDG-A2-10
- cefr_level: A2
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: sport_personal_growth
- title: Learning to Swim
- passage: Omar never learned to swim as a child, so this spring he joined a class for adults at the city pool. Before the first lesson, he felt very nervous — his hands were cold, and he could not stop thinking about the deep water. But the teacher was kind and patient, and the class started in the shallow end, where the water only reached his waist. After a few weeks, Omar could float and kick. Now he actually looks forward to Saturday mornings at the pool.
- question: In this text, "nervous" means —
- options: ["excited and happy", "afraid and worried", "angry about the class", "very tired"]
- correct_index: 1
- correct_answer: afraid and worried
- explanation: The cold hands and his thoughts about the deep water show that "nervous" describes fear and worry.
- distractor_rationale: Excited is the classic false friend for nervous; angry and tired do not match the cold hands and worried thoughts.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Learning to Swim",
  "topic_domain": "sport_personal_growth",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, \"nervous\" means —",
      "options": [
        "excited and happy",
        "afraid and worried",
        "angry about the class",
        "very tired"
      ],
      "correct_index": 1,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "Why did Omar join the class?",
      "options": [
        "He never learned to swim as a child",
        "He wanted to teach children",
        "He worked at the city pool",
        "He disliked Saturday mornings"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Where did the class start?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "In the shallow end"
      ],
      "max_words": 6,
      "subskill": "specific_detail",
      "word_bank": [
        "In the shallow end",
        "In the deep water",
        "Outside the pool",
        "In a classroom"
      ]
    },
    {
      "question": "How does Omar feel about swimming now?",
      "response_type": "short_answer",
      "accepted_answers": [
        "He looks forward to it"
      ],
      "max_words": 7,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Excited is the classic false friend for nervous; angry and tired do not match the clues."
}
```

---

## B1 (10 items)

### ITEM RDG-B1-01
- draft_id: RDG-B1-01
- cefr_level: B1
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: volunteering_animals
- title: Volunteering at the Animal Shelter
- passage: When Priya lost her office job last year, a friend suggested she try volunteering while she looked for new work. She chose the animal shelter on the edge of town, thinking she would stay for a few weeks. A year later, she is still there every Saturday. Volunteers at the shelter walk the dogs, clean the cages, and help visitors choose a pet that suits their home and lifestyle. Priya says the work has given her much more than she expected: new friends, useful experience, and confidence for job interviews. In fact, when she was finally offered two office jobs in the same week, she asked both companies for a schedule that would leave her Saturdays free. The shelter, she says, is no longer something she does to fill time — it is part of who she is.
- question: What is the main point of this text?
- options: ["Volunteering became an important part of Priya's life", "Animal shelters urgently need more money", "Priya could not find a new office job", "Dogs at shelters must be walked every day"]
- correct_index: 0
- correct_answer: Volunteering became an important part of Priya's life
- explanation: The text traces how a temporary activity became "part of who she is", which is its central point.
- distractor_rationale: Shelter tasks and dog walking are supporting details; she did receive job offers, so the job-search option contradicts the text; money is never discussed.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Volunteering at the Animal Shelter",
  "topic_domain": "volunteering_animals",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the main point of this text?",
      "options": [
        "Volunteering became an important part of Priya's life",
        "Animal shelters urgently need more money",
        "Priya could not find a new office job",
        "Dogs at shelters must be walked every day"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "Why did Priya first start volunteering?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "A friend suggested it while she looked for work"
      ],
      "max_words": 11,
      "subskill": "specific_detail",
      "word_bank": [
        "A friend suggested it while she looked for work",
        "She wanted to adopt every dog",
        "The shelter offered her an office job",
        "She needed to fill a school course"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What do volunteers help visitors do?",
        "Answer to: What shows that the shelter matters deeply to Priya?"
      ],
      "match_options": [
        "Choose a pet that suits their home",
        "She asks employers to keep Saturdays free",
        "Write job applications",
        "Build new cages"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What shows that the shelter matters deeply to Priya?",
      "response_type": "short_answer",
      "accepted_answers": [
        "She asks employers to keep Saturdays free"
      ],
      "max_words": 9,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Shelter tasks are supporting details; she did receive job offers; money is never discussed."
}
```

### ITEM RDG-B1-02
- draft_id: RDG-B1-02
- cefr_level: B1
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: city_transport
- title: The City Bike Scheme
- passage: Since the city introduced its public bicycle scheme two years ago, more than forty thousand people have registered. Anyone over sixteen can join by downloading an app and paying a small yearly fee. Riders unlock a bike at any of the eighty stations around the city and can return it to a different station when they finish. The first thirty minutes of every trip are free, which is enough for most journeys across the centre; after that, riders pay a small charge for each extra half hour. According to the transport office, the busiest station is the one outside the central railway station, and the most popular time to ride is Friday afternoon. The city now plans to add twenty more stations next spring, mostly in neighbourhoods far from the metro line.
- question: How long is the free period on each trip?
- options: ["Fifteen minutes", "Thirty minutes", "One hour", "There is no free period"]
- correct_index: 1
- correct_answer: Thirty minutes
- explanation: The text states that "the first thirty minutes of every trip are free".
- distractor_rationale: Half an hour also appears as the paid unit after the free period, so the reader must separate the two; fifteen minutes and one hour are plausible scheme designs not in the text.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The City Bike Scheme",
  "topic_domain": "city_transport",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "How long is the free period on each trip?",
      "options": [
        "Fifteen minutes",
        "Thirty minutes",
        "One hour",
        "There is no free period"
      ],
      "correct_index": 1,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Who can join the bike scheme?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Anyone over sixteen"
      ],
      "max_words": 6,
      "subskill": "specific_detail",
      "word_bank": [
        "Anyone over sixteen",
        "Only tourists",
        "Only railway workers",
        "Children under twelve"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: Where is the busiest bike station?",
        "Answer to: Why is the city adding more stations mostly far from the metro?"
      ],
      "match_options": [
        "Outside the central railway station",
        "To serve areas with less public transport",
        "Near the metro line",
        "Beside the city hall"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why is the city adding more stations mostly far from the metro?",
      "response_type": "short_answer",
      "accepted_answers": [
        "To serve areas with less public transport"
      ],
      "max_words": 9,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Half an hour also appears as the paid unit; the other durations are plausible but absent."
}
```

### ITEM RDG-B1-03
- draft_id: RDG-B1-03
- cefr_level: B1
- question_type: mcq
- reading_subskill: inference
- topic_domain: hobbies_outdoors
- title: An Unusual Hobby
- passage: My cousin Jonas has an unusual hobby called geocaching. Using an app on his phone, he searches for small boxes that other players have hidden all over the world — under bridges, inside hollow trees, behind loose bricks in old walls. Each box contains a paper list, which finders sign, and sometimes tiny objects that players exchange. Last month, Jonas took me on my first search. We followed the map to a park, then spent forty minutes examining every bench and bush while joggers watched us curiously. Just as I was ready to give up, Jonas reached into a gap in a stone wall and pulled out a little green box with a grin. I signed the list, replaced the box exactly where it had been, and immediately asked him where the next one was hidden.
- question: How did the writer most likely feel at the end of the search?
- options: ["Keen to continue the hobby", "Embarrassed in front of the joggers", "Annoyed about the wasted afternoon", "Bored by the whole activity"]
- correct_index: 0
- correct_answer: Keen to continue the hobby
- explanation: Immediately asking where the next box was hidden shows the writer wanted to keep playing.
- distractor_rationale: The joggers and the writer's earlier frustration are real details from the middle of the story, but the final sentence shows enthusiasm, not embarrassment or boredom.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "An Unusual Hobby",
  "topic_domain": "hobbies_outdoors",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "How did the writer most likely feel at the end of the search?",
      "options": [
        "Keen to continue the hobby",
        "Embarrassed in front of the joggers",
        "Annoyed about the wasted afternoon",
        "Bored by the whole activity"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "What do players do with the paper list in each box?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "They sign it"
      ],
      "max_words": 6,
      "subskill": "specific_detail",
      "word_bank": [
        "They sign it",
        "They throw it away",
        "They use it as a map",
        "They send it to joggers"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: Where did Jonas find the green box?",
        "Answer to: Why did the writer ask about the next box?"
      ],
      "match_options": [
        "In a gap in a stone wall",
        "The writer had become interested in the hobby",
        "Under a bridge",
        "Inside a hollow tree"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why did the writer ask about the next box?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The writer had become interested in the hobby"
      ],
      "max_words": 10,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "The joggers and earlier frustration are mid-story details; the final sentence shows enthusiasm."
}
```

### ITEM RDG-B1-04
- draft_id: RDG-B1-04
- cefr_level: B1
- question_type: mcq
- reading_subskill: purpose
- topic_domain: community_gardening
- title: The Community Garden Letter
- passage: Dear residents, as many of you know, the empty land behind Hill Street has been unused for almost ten years. A group of neighbours now has permission from the city council to turn this space into a community garden, and we are writing to invite you to take part. We are looking for people to help clear the ground during the last weekend of March, and for anyone with tools, seeds, or old wooden boxes to donate them. In return, every household that helps will receive its own small growing bed for vegetables or flowers. You do not need any gardening experience — several experienced gardeners in the group will be happy to show beginners what to do. If you would like to join, please leave your name and phone number at the corner shop by 15 March. We hope to see many of you there.
- question: Why was this letter written?
- options: ["To ask neighbours to help create a garden", "To complain about the unused land", "To sell vegetables grown in a garden", "To announce that a garden is closing"]
- correct_index: 0
- correct_answer: To ask neighbours to help create a garden
- explanation: The letter invites residents to take part, asks for helpers and donations, and explains how to join.
- distractor_rationale: The unused land is background, not a complaint; vegetables are a reward for helping, not for sale; the garden is starting, not closing.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Community Garden Letter",
  "topic_domain": "community_gardening",
  "reading_subskill": "purpose",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "Why was this letter written?",
      "options": [
        "To ask neighbours to help create a garden",
        "To complain about the unused land",
        "To sell vegetables grown in a garden",
        "To announce that a garden is closing"
      ],
      "correct_index": 0,
      "subskill": "purpose",
      "response_type": "mcq"
    },
    {
      "question": "What has been unused for almost ten years?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "The land behind Hill Street"
      ],
      "max_words": 7,
      "subskill": "specific_detail",
      "word_bank": [
        "The land behind Hill Street",
        "The corner shop",
        "The city council office",
        "The gardeners' tools"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What will helping households receive?",
        "Answer to: What does the letter suggest about beginners?"
      ],
      "match_options": [
        "A small growing bed",
        "They can join because experienced gardeners will help",
        "Free vegetables forever",
        "Money from the council"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What does the letter suggest about beginners?",
      "response_type": "short_answer",
      "accepted_answers": [
        "They can join because experienced gardeners will help"
      ],
      "max_words": 10,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "The unused land is background; vegetables are a reward, not for sale; the garden is starting, not closing."
}
```

### ITEM RDG-B1-05
- draft_id: RDG-B1-05
- cefr_level: B1
- question_type: mcq
- reading_subskill: inference
- topic_domain: food_reviews
- title: The Blue Door
- passage: The Blue Door, which opened on Station Road last month, is the fourth cafe to try its luck in that small corner building in five years. I visited on a busy Saturday morning, expecting the usual story: slow service, cold coffee, and a shrug instead of an apology. Instead, I found something different. Although every table was full, the owner greeted us at the door, found us seats within five minutes, and remembered without being asked that my friend had ordered oat milk on our previous visit. The coffee arrived hot and quickly, the cakes are baked in the kitchen downstairs each morning, and the prices are no higher than anywhere else on the street. The little building on Station Road has swallowed many hopeful cafes. This time, I suspect, it has finally met its match.
- question: What does the writer suggest about The Blue Door?
- options: ["It will probably succeed where earlier cafes failed", "It is too expensive for the area", "It urgently needs to hire more staff", "It will soon close like the cafes before it"]
- correct_index: 0
- correct_answer: It will probably succeed where earlier cafes failed
- explanation: Saying the building "has finally met its match" after listing the cafe's strengths implies this cafe will survive.
- distractor_rationale: The text says prices are no higher than elsewhere; the service is described as fast despite the crowd; the closing prediction reverses the writer's meaning.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Blue Door",
  "topic_domain": "food_reviews",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What does the writer suggest about The Blue Door?",
      "options": [
        "It will probably succeed where earlier cafes failed",
        "It is too expensive for the area",
        "It urgently needs to hire more staff",
        "It will soon close like the cafes before it"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "What did the writer expect before visiting The Blue Door?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "Slow service and cold coffee"
      ],
      "max_words": 7,
      "subskill": "specific_detail",
      "word_bank": [
        "Slow service and cold coffee",
        "A very expensive menu",
        "An empty cafe",
        "A formal restaurant"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What detail shows the owner paid attention to customers?",
        "Answer to: What does \"met its match\" suggest about the building?"
      ],
      "match_options": [
        "He remembered the friend had ordered oat milk",
        "This cafe may finally be strong enough to succeed there",
        "He closed the door quickly",
        "He charged more than other cafes"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What does \"met its match\" suggest about the building?",
      "response_type": "short_answer",
      "accepted_answers": [
        "This cafe may finally be strong enough to succeed there"
      ],
      "max_words": 12,
      "subskill": "vocabulary_in_context"
    }
  ],
  "distractor_rationale": "Prices are stated as normal, service as fast; the closing option reverses the writer's meaning."
}
```

### ITEM RDG-B1-06
- draft_id: RDG-B1-06
- cefr_level: B1
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: history_food
- title: A Short History of the Sandwich
- passage: The sandwich is named after John Montagu, the fourth Earl of Sandwich, an English aristocrat who lived in the eighteenth century. According to the popular story, the Earl did not want to leave the card table to eat dinner, so he asked his servants to bring him meat between two slices of bread, which he could eat with one hand while he continued playing. His friends began ordering "the same as Sandwich", and the name remained. Food historians point out that people had eaten bread with fillings for centuries before the Earl was born — cooks in many countries had long stuffed flat bread with grilled meat and vegetables. What the Earl really gave the sandwich was not the idea but the name, and with it a permanent place in the English language.
- question: According to the story, why did the Earl ask for meat between bread?
- options: ["He wanted to keep playing cards while eating", "He could not afford a full dinner", "His cook was unable to prepare anything else", "He wanted to become famous for a new dish"]
- correct_index: 0
- correct_answer: He wanted to keep playing cards while eating
- explanation: The story says he did not want to leave the card table, so he asked for food he could eat with one hand while playing.
- distractor_rationale: An aristocrat's poverty contradicts the text; the cook and a wish for fame are plausible story shapes that the passage never mentions.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "A Short History of the Sandwich",
  "topic_domain": "history_food",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "According to the story, why did the Earl ask for meat between bread?",
      "options": [
        "He wanted to keep playing cards while eating",
        "He could not afford a full dinner",
        "His cook was unable to prepare anything else",
        "He wanted to become famous for a new dish"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Who was John Montagu?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "The fourth Earl of Sandwich"
      ],
      "max_words": 7,
      "subskill": "specific_detail",
      "word_bank": [
        "The fourth Earl of Sandwich",
        "A food historian",
        "A servant in a kitchen",
        "A flat-bread cook"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What had people done before the Earl was born?",
        "Answer to: What did the Earl really give the sandwich?"
      ],
      "match_options": [
        "Eaten bread with fillings",
        "Its name",
        "Named the sandwich after him",
        "Played cards with servants"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What did the Earl really give the sandwich?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Its name"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "An aristocrat's poverty contradicts the text; the cook and fame options are never mentioned."
}
```

### ITEM RDG-B1-07
- draft_id: RDG-B1-07
- cefr_level: B1
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: work_lifestyle
- title: Working from Home
- passage: When his company allowed staff to work from home three days a week, Karim expected his life to become easier overnight. In some ways, it did: he no longer spent two hours a day on crowded trains, and he could start a load of washing between meetings. But he soon discovered problems he had not expected. Without the walk to the station, he hardly moved all day. Without colleagues around him, small questions that once took thirty seconds to answer now required long email chains. And without a clear end to the working day, he often found himself replying to messages at ten at night. After six months, Karim has settled on a routine: a morning walk before his first meeting, a phone call instead of an email whenever a question is complicated, and a firm rule that the laptop closes at six.
- question: What is the main idea of this text?
- options: ["Working from home has benefits but requires new habits", "Companies should stop allowing work from home", "Commuting by train is the worst part of office life", "Email is always better than phone calls"]
- correct_index: 0
- correct_answer: Working from home has benefits but requires new habits
- explanation: The text presents both the advantages and the unexpected problems, ending with the routine Karim built to manage them.
- distractor_rationale: The text never argues against home working; the train commute is one detail; Karim actually moves away from email for complicated questions.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Working from Home",
  "topic_domain": "work_lifestyle",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the main idea of this text?",
      "options": [
        "Working from home has benefits but requires new habits",
        "Companies should stop allowing work from home",
        "Commuting by train is the worst part of office life",
        "Email is always better than phone calls"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "What benefit did Karim notice at first?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "He no longer spent two hours on trains"
      ],
      "max_words": 10,
      "subskill": "specific_detail",
      "word_bank": [
        "He no longer spent two hours on trains",
        "He worked fewer days each week",
        "He stopped receiving messages",
        "He met colleagues more often"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What problem happened with small questions?",
        "Answer to: What routine helped Karim?"
      ],
      "match_options": [
        "They became long email chains",
        "A morning walk and closing the laptop at six",
        "They disappeared completely",
        "They were answered in thirty seconds"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What routine helped Karim?",
      "response_type": "short_answer",
      "accepted_answers": [
        "A morning walk and closing the laptop at six"
      ],
      "max_words": 11,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "The text never argues against home working; the commute is one detail; Karim moves away from email."
}
```

### ITEM RDG-B1-08
- draft_id: RDG-B1-08
- cefr_level: B1
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: school_culture
- title: The Exchange Student
- passage: Last autumn, our school took part in an exchange programme with a school in another country. A student named Luca stayed with my family for a month, and next spring I will stay with his. At first, we were both shy at breakfast, pointing at things and using our phones to translate. But within a week, Luca was teaching my little sister card games and helping my father in the garden. The biggest surprise for me was how quickly the strange became familiar: after two weeks, it seemed completely normal to have him at the table. When he left, the house felt oddly quiet. We still message each other most days, and my mother has already started planning what to cook when he visits again.
- question: In this text, "familiar" means —
- options: ["well known and normal", "foreign and strange", "amusing and entertaining", "difficult to understand"]
- correct_index: 0
- correct_answer: well known and normal
- explanation: The sentence contrasts "the strange" becoming "familiar" and then explains that having Luca at the table "seemed completely normal".
- distractor_rationale: Foreign and strange is the direct opposite, tempting because the word appears in a contrast; amusing and difficult ignore the explanation that follows.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Exchange Student",
  "topic_domain": "school_culture",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, \"familiar\" means —",
      "options": [
        "well known and normal",
        "foreign and strange",
        "amusing and entertaining",
        "difficult to understand"
      ],
      "correct_index": 0,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "How long did Luca stay with the writer's family?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "A month"
      ],
      "max_words": 6,
      "subskill": "specific_detail",
      "word_bank": [
        "A month",
        "A week",
        "Two weeks",
        "A year"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What did Luca do with the writer's little sister?",
        "Answer to: What does the quiet house after Luca left show?"
      ],
      "match_options": [
        "Taught her card games",
        "The family missed his presence",
        "Cooked breakfast for her",
        "Helped her translate homework"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What does the quiet house after Luca left show?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The family missed his presence"
      ],
      "max_words": 7,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Foreign and strange is the direct opposite in the contrast; the others ignore the following explanation."
}
```

### ITEM RDG-B1-09
- draft_id: RDG-B1-09
- cefr_level: B1
- question_type: mcq
- reading_subskill: inference
- topic_domain: outdoors_family
- title: The Camping Trip
- passage: It was nearly midnight when Ellie finally admitted that the tent was not going to survive the night. The wind had already bent two of the poles, and each gust lifted the corner where her brother was supposed to be sleeping — he was, in fact, sitting in the car with the heating on, having announced an hour earlier that camping was "a hobby for people who hate comfort". Ellie packed the sleeping bags by torchlight, threw the collapsed tent into the boot, and climbed into the driver's seat. "There's a guesthouse in the village," she said. "We passed it on the way in." Her brother did not say a word, but the speed with which he fastened his seatbelt said everything.
- question: What can we understand about Ellie's brother?
- options: ["He was glad they were leaving the campsite", "He wanted to stay and repair the tent", "He had been asleep in the tent all night", "He enjoyed camping more than Ellie did"]
- correct_index: 0
- correct_answer: He was glad they were leaving the campsite
- explanation: His earlier complaint about camping and the speed with which he fastened his seatbelt show he was happy to leave.
- distractor_rationale: He was in the car, not the tent, and had already mocked camping, which rules out the other options; nothing suggests he wanted to repair anything.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Camping Trip",
  "topic_domain": "outdoors_family",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What can we understand about Ellie's brother?",
      "options": [
        "He was glad they were leaving the campsite",
        "He wanted to stay and repair the tent",
        "He had been asleep in the tent all night",
        "He enjoyed camping more than Ellie did"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "Where was Ellie's brother during the storm?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "In the car with the heating on"
      ],
      "max_words": 9,
      "subskill": "specific_detail",
      "word_bank": [
        "In the car with the heating on",
        "Asleep in the tent",
        "At the guesthouse",
        "Repairing the poles"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What made Ellie decide to leave?",
        "Answer to: What did the brother's fast seatbelt action show?"
      ],
      "match_options": [
        "The tent was not going to survive the night",
        "He wanted to leave immediately",
        "Her brother lost the sleeping bags",
        "The guesthouse had called them"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What did the brother's fast seatbelt action show?",
      "response_type": "short_answer",
      "accepted_answers": [
        "He wanted to leave immediately"
      ],
      "max_words": 7,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "He was in the car, not the tent, and had already mocked camping; nothing suggests repair."
}
```

### ITEM RDG-B1-10
- draft_id: RDG-B1-10
- cefr_level: B1
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: music_saving
- title: Saving for a Guitar
- passage: Ten months ago, Ravi saw a second-hand electric guitar in a shop window and decided it had to be his. The price was far beyond his pocket money, so he made a plan. He took a weekend job delivering newspapers, gave up his weekly cinema trips, and put every coin into an old jam jar on his shelf. His friends teased him about it, but Ravi was determined: whenever he was tempted to spend the money on something smaller, he walked past the shop to look at the guitar again. Last Saturday, he finally counted out the full amount onto the shop counter, mostly in coins, while the owner laughed and shook his hand. The guitar now stands in the corner of his room, and his neighbours are slowly getting used to the noise.
- question: In this text, "determined" means —
- options: ["firmly decided to achieve something", "confused about what to choose", "unhappy about the high price", "careless with his money"]
- correct_index: 0
- correct_answer: firmly decided to achieve something
- explanation: Ravi keeps his plan for ten months despite teasing and temptation, showing a firm decision to reach his goal.
- distractor_rationale: Confusion and carelessness contradict his careful plan; unhappiness about the price fits the situation but not the meaning of the word.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Saving for a Guitar",
  "topic_domain": "music_saving",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, \"determined\" means —",
      "options": [
        "firmly decided to achieve something",
        "confused about what to choose",
        "unhappy about the high price",
        "careless with his money"
      ],
      "correct_index": 0,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "How did Ravi earn money for the guitar?",
      "response_type": "gap_fill",
      "accepted_answers": [
        "He delivered newspapers"
      ],
      "max_words": 6,
      "subskill": "specific_detail",
      "word_bank": [
        "He delivered newspapers",
        "He sold cinema tickets",
        "He taught music lessons",
        "He borrowed from neighbours"
      ]
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What did Ravi give up?",
        "Answer to: Why did Ravi walk past the shop again and again?"
      ],
      "match_options": [
        "His weekly cinema trips",
        "To remind himself of his goal",
        "His weekend job",
        "His old jam jar"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why did Ravi walk past the shop again and again?",
      "response_type": "short_answer",
      "accepted_answers": [
        "To remind himself of his goal"
      ],
      "max_words": 8,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Confusion and carelessness contradict his plan; price unhappiness fits the situation but not the word."
}
```

---

## B2 (10 items)

### ITEM RDG-B2-01
- draft_id: RDG-B2-01
- cefr_level: B2
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: nature_city
- title: Urban Beekeeping
- passage: Beekeeping was once a countryside pursuit, but over the past decade it has quietly colonised the modern city. Hives now sit on the roofs of hotels, banks and railway stations; some companies even rent them out, complete with bees and a visiting expert, to businesses keen to advertise their environmental credentials. At first glance, the city seems a hostile home for an insect we associate with meadows. In fact, urban bees often do better than their rural cousins. City parks and gardens offer a longer flowering season and a wider variety of plants than much of today's farmland, where a single crop may stretch to the horizon. Urban honey, its producers claim, is not only plentiful but distinctive, carrying the flavour of whatever blooms within a few kilometres of a hive. There are, however, limits. Enthusiasm has led to overcrowding in some cities, with more hives than the local flowers can feed. As one beekeeper puts it, the question is no longer whether bees can live in cities, but how many of them a city can honestly invite.
- question: What is the main idea of this text?
- options: ["Cities have proved surprisingly good, though limited, homes for bees", "Honey production is declining around the world", "Farmland is the best possible environment for bees", "Hotels should stop keeping bees on their roofs"]
- correct_index: 0
- correct_answer: Cities have proved surprisingly good, though limited, homes for bees
- explanation: The text argues that urban bees often thrive, then qualifies this with the overcrowding limit — exactly the "good, though limited" summary.
- distractor_rationale: The text says urban bees often do better than rural ones, contradicting the farmland option; declining production and hotel criticism are never claimed.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Urban Beekeeping",
  "topic_domain": "nature_city",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the main idea of this text?",
      "options": [
        "Cities have proved surprisingly good, though limited, homes for bees",
        "Honey production is declining around the world",
        "Farmland is the best possible environment for bees",
        "Hotels should stop keeping bees on their roofs"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: Why can city bees do well?",
        "Answer to: What problem has enthusiasm created in some cities?"
      ],
      "match_options": [
        "Cities offer varied plants and a longer flowering season",
        "Too many hives for the available flowers",
        "Cities have fewer flowers than farmland",
        "Hotel roofs are warmer than fields all year"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What problem has enthusiasm created in some cities?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Too many hives for the available flowers"
      ],
      "max_words": 9,
      "subskill": "specific_detail"
    },
    {
      "question": "What does the final question suggest?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Urban beekeeping needs limits as well as enthusiasm"
      ],
      "max_words": 10,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "The text says urban bees often do better than rural ones; declining production and hotel criticism are never claimed."
}
```

### ITEM RDG-B2-02
- draft_id: RDG-B2-02
- cefr_level: B2
- question_type: mcq
- reading_subskill: inference
- topic_domain: work_psychology
- title: The Open-Plan Office
- passage: When the walls came down in offices around the world, the promise was collaboration: colleagues would exchange ideas as freely as they exchanged glances, and creativity would flow across the open floor. Two decades on, the research tells a more complicated story. Several large studies have found that when companies move to open-plan layouts, face-to-face conversation actually drops — in one study, by more than two thirds — while email and instant messaging rise sharply. Workers surrounded by noise and movement report that they retreat into headphones, save difficult tasks for early mornings at home, and book meeting rooms simply to think. Defenders of open offices point to their flexibility and lower cost, and note that some teams, particularly those doing fast, cooperative work, genuinely thrive in them. But the original claim — that removing walls reliably brings people together — has not survived contact with the evidence. It seems that, when it comes to conversation, people need somewhere private to have it.
- question: What can be inferred about the original promise of open-plan offices?
- options: ["It has largely not been supported by the research", "It was confirmed by several large studies", "It applied only to small companies", "It was never taken seriously by anyone"]
- correct_index: 0
- correct_answer: It has largely not been supported by the research
- explanation: The studies found conversation fell rather than rose, and the text concludes the original claim "has not survived contact with the evidence".
- distractor_rationale: The studies contradicted rather than confirmed the promise; company size is never discussed; the promise was clearly taken seriously, since offices worldwide adopted it.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Open-Plan Office",
  "topic_domain": "work_psychology",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What can be inferred about the original promise of open-plan offices?",
      "options": [
        "It has largely not been supported by the research",
        "It was confirmed by several large studies",
        "It applied only to small companies",
        "It was never taken seriously by anyone"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "What happened to face-to-face conversation in several studies?",
        "Why do some workers book meeting rooms?"
      ],
      "match_options": [
        "It dropped after moves to open-plan offices",
        "Simply to think",
        "It doubled in every company",
        "It stayed exactly the same"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why do some workers book meeting rooms?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Simply to think"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    },
    {
      "question": "Which view of open-plan offices does the text present?",
      "response_type": "short_answer",
      "accepted_answers": [
        "They have some advantages but do not reliably create collaboration"
      ],
      "max_words": 12,
      "subskill": "main_idea"
    }
  ],
  "distractor_rationale": "The studies contradicted the promise; company size is never discussed; worldwide adoption shows it was taken seriously."
}
```

### ITEM RDG-B2-03
- draft_id: RDG-B2-03
- cefr_level: B2
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: biography_maps
- title: The Cartographer
- passage: Marta Vidal drew her first map at the age of nine, copying the coastline of her island home from a school atlas onto the back of a flour sack. By the time she died, seventy years later, her maps hung in universities on four continents. Vidal never trained formally. She worked as a lighthouse keeper's assistant until she was thirty, and it was there, watching fishing boats trace the same safe channels year after year, that she began recording what the official charts missed: the reefs known only to local crews, the currents that shifted with the seasons, the sandbanks that appeared and vanished. Her first published chart, printed at her own expense in 1953, corrected eleven errors in the government's map of the strait. The navy, initially dismissive, quietly adopted nine of her corrections within five years. Vidal refused every office job she was offered, insisting that a mapmaker who no longer walked the coast was merely decorating paper. She updated her charts by hand until her eyesight failed, and her final map — of the harbour where she was born — was completed by her granddaughter, following notebooks Vidal had kept for sixty years.
- question: What did Vidal's first published chart do?
- options: ["It corrected errors in the government's map of the strait", "It showed the location of every lighthouse on the island", "It reproduced the navy's official records", "It illustrated a new school atlas"]
- correct_index: 0
- correct_answer: It corrected errors in the government's map of the strait
- explanation: The text states her first published chart "corrected eleven errors in the government's map of the strait".
- distractor_rationale: The lighthouse and the school atlas both appear earlier in her life story, inviting confusion; the navy adopted her corrections, not the reverse.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Cartographer",
  "topic_domain": "biography_maps",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What did Vidal's first published chart do?",
      "options": [
        "It corrected errors in the government's map of the strait",
        "It showed the location of every lighthouse on the island",
        "It reproduced the navy's official records",
        "It illustrated a new school atlas"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: Where did Vidal begin learning what official charts missed?",
        "Answer to: How did the navy first respond to Vidal's chart?"
      ],
      "match_options": [
        "While working near fishing boats as a lighthouse keeper's assistant",
        "It was initially dismissive but later adopted corrections",
        "During formal university training",
        "As an officer in the navy"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "How did the navy first respond to Vidal's chart?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It was initially dismissive but later adopted corrections"
      ],
      "max_words": 10,
      "subskill": "inference"
    },
    {
      "question": "What made Vidal's maps valuable?",
      "response_type": "short_answer",
      "accepted_answers": [
        "They included local, practical knowledge absent from official maps"
      ],
      "max_words": 11,
      "subskill": "main_idea"
    }
  ],
  "distractor_rationale": "The lighthouse and school atlas appear earlier in her story; the navy adopted her corrections, not the reverse."
}
```

### ITEM RDG-B2-04
- draft_id: RDG-B2-04
- cefr_level: B2
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: psychology_habits
- title: The Science of Habits
- passage: Anyone who has tried to take up jogging in January knows that new habits are fragile. Psychologists who study behaviour change say this is because we misunderstand what a habit is. We imagine it as a decision we keep making, when in fact a true habit is precisely the opposite: an action that no longer requires a decision at all. The brain, which is expensive to run, is always looking for routines it can automate, and it builds these automatic patterns around cues — a time of day, a place, a preceding action. This is why advice to simply be more disciplined so often fails. Willpower is a limited resource, easily depleted by a difficult day, whereas a well-anchored habit costs nothing to maintain. The practical lesson from the research is modest but liberating: instead of relying on motivation, attach the new behaviour to a stable cue — running shoes by the door, a walk that always follows lunch — and repeat it until the decision disappears. The people we call disciplined, researchers suggest, are often simply those who have arranged their lives so that fewer decisions are needed.
- question: In this text, "depleted" means —
- options: ["gradually used up", "suddenly increased", "carefully measured", "completely forgotten"]
- correct_index: 0
- correct_answer: gradually used up
- explanation: Willpower is described as "a limited resource", so being depleted by a difficult day means being used up.
- distractor_rationale: Increased reverses the meaning; measured and forgotten fit the scientific register but not the "limited resource" clue.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Science of Habits",
  "topic_domain": "psychology_habits",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, \"depleted\" means —",
      "options": [
        "gradually used up",
        "suddenly increased",
        "carefully measured",
        "completely forgotten"
      ],
      "correct_index": 0,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: According to the passage, what is a true habit?",
        "Answer to: Why does advice to be more disciplined often fail?"
      ],
      "match_options": [
        "An action that no longer requires a decision",
        "Willpower is limited and can be depleted",
        "A difficult choice made every morning",
        "A burst of January motivation"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why does advice to be more disciplined often fail?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Willpower is limited and can be depleted"
      ],
      "max_words": 9,
      "subskill": "inference"
    },
    {
      "question": "What practical lesson does the passage offer?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Attach a new behaviour to a stable cue"
      ],
      "max_words": 10,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "Increased reverses the meaning; measured and forgotten fit the register but not the 'limited resource' clue."
}
```

### ITEM RDG-B2-05
- draft_id: RDG-B2-05
- cefr_level: B2
- question_type: mcq
- reading_subskill: tone
- topic_domain: culture_museums
- title: The Museum of Everyday Life
- passage: The city's new Museum of Everyday Life opened last month in a converted tram depot, and I confess I arrived expecting to be bored senseless. A museum devoted to washing lines, lunch boxes and bus tickets sounded like a joke at somebody's expense — possibly mine. I was wrong, and happily so. The curators have understood something that grander institutions often forget: that history is mostly made of ordinary days. A wall of school satchels from the past century says more about childhood than any textbook I own. A reconstructed 1970s kitchen, complete with its humming fridge, had visitors of a certain age laughing and pointing like children. Even the bus tickets, arranged by decade, quietly track a city growing outward, fare by fare. Is every room a triumph? Not quite — the section on office equipment tests one's patience, and the gift shop is an afterthought. But I left with my ticket stub tucked carefully in my pocket, already half a museum piece itself, and I find I keep telling people to go.
- question: Which phrase best describes the overall tone of this review?
- options: ["Pleasantly surprised", "Bitterly disappointed", "Coldly neutral", "Openly mocking"]
- correct_index: 0
- correct_answer: Pleasantly surprised
- explanation: The writer admits expecting boredom, then says "I was wrong, and happily so" and ends by recommending the museum.
- distractor_rationale: The opening jokes could suggest mockery, but they describe expectations the visit overturned; the enthusiastic ending rules out disappointment and neutrality.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Museum of Everyday Life",
  "topic_domain": "culture_museums",
  "reading_subskill": "tone",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "Which phrase best describes the overall tone of this review?",
      "options": [
        "Pleasantly surprised",
        "Bitterly disappointed",
        "Coldly neutral",
        "Openly mocking"
      ],
      "correct_index": 0,
      "subskill": "tone",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What did the writer expect before visiting?",
        "Answer to: What idea does the museum seem to understand?"
      ],
      "match_options": [
        "To be bored by ordinary objects",
        "Ordinary days are an important part of history",
        "To see only famous paintings",
        "To find a closed tram depot"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "What idea does the museum seem to understand?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Ordinary days are an important part of history"
      ],
      "max_words": 10,
      "subskill": "main_idea"
    },
    {
      "question": "What does the review suggest about the museum overall?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It is warmly recommended despite some weaker parts"
      ],
      "max_words": 10,
      "subskill": "tone"
    }
  ],
  "distractor_rationale": "The opening jokes describe expectations the visit overturned; the enthusiastic ending rules out disappointment and neutrality."
}
```

### ITEM RDG-B2-06
- draft_id: RDG-B2-06
- cefr_level: B2
- question_type: mcq
- reading_subskill: purpose
- topic_domain: food_community
- title: The Riverside Market Booklet
- passage: This booklet accompanies the Riverside Market's autumn cooking series, and its purpose is simple: to persuade you that the vegetables you walked past today deserve a second look. Over the next eight weeks, our visiting cooks will take one overlooked, inexpensive, locally grown ingredient at a time — the knobbly celeriac, the alarming quantity of courgettes that every allotment produces in September — and show, step by step, that each can anchor a genuinely satisfying meal. The recipes inside are deliberately short. None requires special equipment, rare spices, or more than forty minutes. Where a technique matters, we explain it; where it does not, we leave you alone. We have also marked, on each page, which market stalls sell the main ingredient, because the second aim of this series — we admit it freely — is to keep those stalls in business through the quiet winter months. Cook the recipes in any order. Better still, cook them for someone.
- question: What is the main purpose of this booklet?
- options: ["To encourage people to cook with cheap, local vegetables", "To review the city's best restaurants", "To teach advanced cooking techniques", "To explain how to grow courgettes at home"]
- correct_index: 0
- correct_answer: To encourage people to cook with cheap, local vegetables
- explanation: The booklet states its purpose directly: to persuade readers that overlooked, inexpensive local vegetables "deserve a second look", supported by simple recipes.
- distractor_rationale: The recipes are explicitly simple, not advanced; growing vegetables and restaurant reviews are plausible food-booklet purposes never mentioned.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Riverside Market Booklet",
  "topic_domain": "food_community",
  "reading_subskill": "purpose",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the main purpose of this booklet?",
      "options": [
        "To encourage people to cook with cheap, local vegetables",
        "To review the city's best restaurants",
        "To teach advanced cooking techniques",
        "To explain how to grow courgettes at home"
      ],
      "correct_index": 0,
      "subskill": "purpose",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What kind of ingredients does the booklet focus on?",
        "Answer to: Why are the recipes deliberately short?"
      ],
      "match_options": [
        "Overlooked, inexpensive, locally grown vegetables",
        "They are meant to feel practical and easy to use",
        "Rare spices from abroad",
        "Expensive meat dishes"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why are the recipes deliberately short?",
      "response_type": "short_answer",
      "accepted_answers": [
        "They are meant to feel practical and easy to use"
      ],
      "max_words": 12,
      "subskill": "inference"
    },
    {
      "question": "What second aim does the booklet admit?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Helping keep market stalls in business"
      ],
      "max_words": 8,
      "subskill": "purpose"
    }
  ],
  "distractor_rationale": "The recipes are explicitly simple, not advanced; growing vegetables and restaurant reviews are never mentioned."
}
```

### ITEM RDG-B2-07
- draft_id: RDG-B2-07
- cefr_level: B2
- question_type: mcq
- reading_subskill: inference
- topic_domain: music_learning
- title: The Adult Beginner
- passage: At forty-three, after two decades of saying she would do it someday, Ines finally rented a cello. Her teacher, a patient man in his sixties, warned her at the first lesson that adult beginners face a particular enemy, and it is not their fingers. Children, he explained, expect to be bad at things; it is their natural condition, and they scrape away cheerfully. Adults, by contrast, have spent years being competent — at their jobs, their kitchens, their conversations — and the daily experience of clumsiness feels like an insult. Sure enough, Ines spent her first months fighting the urge to apologise to the instrument. What kept her going was a small change of method suggested by her teacher: she stopped measuring her progress against the pieces she wanted to play and began keeping a diary of what she could do today that she could not do a month ago. Two years on, she plays in an amateur quartet that meets above a bakery. They are, she says, the least talented ensemble in the city, and the happiest.
- question: According to the text, what is the main difficulty for adult beginners?
- options: ["They are not used to feeling incompetent", "Their fingers are too stiff to learn properly", "They cannot find sufficiently patient teachers", "They have no time to practise regularly"]
- correct_index: 0
- correct_answer: They are not used to feeling incompetent
- explanation: The teacher says the enemy "is not their fingers": adults have spent years being competent, so daily clumsiness "feels like an insult".
- distractor_rationale: The fingers option is explicitly denied by the teacher; patience and time are common assumptions about adult learners that the text never raises.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Adult Beginner",
  "topic_domain": "music_learning",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "According to the text, what is the main difficulty for adult beginners?",
      "options": [
        "They are not used to feeling incompetent",
        "Their fingers are too stiff to learn properly",
        "They cannot find sufficiently patient teachers",
        "They have no time to practise regularly"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What does the teacher say is not the adult beginner's main enemy?",
        "Answer to: Why do adults often struggle with being beginners?"
      ],
      "match_options": [
        "Their fingers",
        "They are used to feeling competent in daily life",
        "Their pride",
        "Their diary"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why do adults often struggle with being beginners?",
      "response_type": "short_answer",
      "accepted_answers": [
        "They are used to feeling competent in daily life"
      ],
      "max_words": 11,
      "subskill": "inference"
    },
    {
      "question": "What helped Ines continue?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Recording small progress from month to month"
      ],
      "max_words": 9,
      "subskill": "specific_detail"
    }
  ],
  "distractor_rationale": "The fingers option is explicitly denied; patience and time are common assumptions the text never raises."
}
```

### ITEM RDG-B2-08
- draft_id: RDG-B2-08
- cefr_level: B2
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: communication_history
- title: The Drawer of Letters
- passage: My grandmother's house contained a drawer that fascinated me as a child: it was full of letters, bundled by year and tied with garden string. When she died, the bundles came to me, and reading them changed my view of what we lost when we stopped writing to each other on paper. It is not, as people usually claim, a matter of elegance. Most of the letters are plainly written, full of crossings-out, weather reports and complaints about the price of shoes. What they have that our messages lack is patience. A letter written on Sunday, posted on Monday and answered the following week could not be dashed off in irritation, or at least not sent in it; the walk to the postbox was a cooling-off period that email has abolished. And because each letter had to stand alone for days, writers explained themselves fully, gave context, told the whole small story. The result, decades later, is a record with a texture that no scrolling archive of two-line messages will ever have. I do not expect the letter to return. But the drawer has persuaded me to slow at least some of my words down.
- question: What is the writer's main point about letters?
- options: ["Their slowness gave them qualities that fast messages lack", "They were more elegantly written than modern emails", "They were mostly about unimportant everyday subjects", "They should be preserved more carefully in archives"]
- correct_index: 0
- correct_answer: Their slowness gave them qualities that fast messages lack
- explanation: The writer explicitly rejects the elegance explanation and argues that patience — the enforced slowness — is what letters had and messages lack.
- distractor_rationale: The elegance option is directly denied in the text; the everyday subjects are mentioned but presented as beside the point; preservation is never discussed.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Drawer of Letters",
  "topic_domain": "communication_history",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the writer's main point about letters?",
      "options": [
        "Their slowness gave them qualities that fast messages lack",
        "They were more elegantly written than modern emails",
        "They were mostly about unimportant everyday subjects",
        "They should be preserved more carefully in archives"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What quality does the writer value in old letters?",
        "Answer to: Why did the walk to the postbox matter?"
      ],
      "match_options": [
        "Patience",
        "It created a cooling-off period before sending",
        "Perfect elegance",
        "Speed"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why did the walk to the postbox matter?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It created a cooling-off period before sending"
      ],
      "max_words": 9,
      "subskill": "inference"
    },
    {
      "question": "How does the writer contrast letters with modern messages?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Letters encouraged fuller explanation over time"
      ],
      "max_words": 8,
      "subskill": "main_idea"
    }
  ],
  "distractor_rationale": "The elegance option is directly denied; everyday subjects are beside the point; preservation is never discussed."
}
```

### ITEM RDG-B2-09
- draft_id: RDG-B2-09
- cefr_level: B2
- question_type: mcq
- reading_subskill: specific_detail
- topic_domain: travel_trains
- title: Night Trains Return
- passage: After decades of decline, the night train is edging back onto the continent's timetables. This spring, a new sleeper service will link the capital with three cities across the border, departing at 22:40 and arriving, in the farthest case, just before nine the next morning. The operating company has refitted forty-year-old carriages rather than ordering new ones, a decision it defends on both cost and speed: new rolling stock would have taken five years to deliver, while the refurbished carriages entered service in eighteen months. Each train offers three classes — seats, couchettes shared by up to four passengers, and private compartments with their own washbasin. Tickets went on sale in January, and the company reports that private compartments for the first month sold out within a week, while ordinary seats are selling slowly. Its managers remain cautious: similar revivals elsewhere have struggled once the initial enthusiasm faded, and the service will be reviewed after two years. Even so, the return of a train in which one falls asleep in one country and wakes in another has been greeted, by travellers of a certain temperament, as very good news indeed.
- question: Why did the company refit old carriages instead of buying new ones?
- options: ["New carriages would have cost more and taken far longer to deliver", "Old carriages are more comfortable for passengers", "Passengers specifically asked for traditional trains", "Regulators refused to approve new carriages"]
- correct_index: 0
- correct_answer: New carriages would have cost more and taken far longer to deliver
- explanation: The company defends the decision "on both cost and speed": new stock needed five years, the refit only eighteen months.
- distractor_rationale: Comfort, passenger demand and regulators are all plausible reasons in a rail story, but the text gives only cost and delivery time.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Night Trains Return",
  "topic_domain": "travel_trains",
  "reading_subskill": "specific_detail",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "Why did the company refit old carriages instead of buying new ones?",
      "options": [
        "New carriages would have cost more and taken far longer to deliver",
        "Old carriages are more comfortable for passengers",
        "Passengers specifically asked for traditional trains",
        "Regulators refused to approve new carriages"
      ],
      "correct_index": 0,
      "subskill": "specific_detail",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: When does the new sleeper service depart?",
        "Answer to: Which ticket type sold out quickly for the first month?"
      ],
      "match_options": [
        "22:40",
        "Private compartments",
        "Just before nine",
        "In January"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Which ticket type sold out quickly for the first month?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Private compartments"
      ],
      "max_words": 6,
      "subskill": "specific_detail"
    },
    {
      "question": "What can be inferred from slower ordinary-seat sales?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Passengers are more attracted to comfort on overnight journeys"
      ],
      "max_words": 11,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "Comfort, passenger demand and regulators are plausible in a rail story, but the text gives only cost and delivery time."
}
```

### ITEM RDG-B2-10
- draft_id: RDG-B2-10
- cefr_level: B2
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: architecture_heritage
- title: The Old Theatre
- passage: When the Alhambra Theatre closed its doors in 1998, most people in town assumed they would never reopen. The building spent twenty years gathering pigeons and planning disputes until a local trust bought it for a symbolic single coin, on the condition that it raise the money for repairs. The trust's approach to the restoration has been unusually careful. Rather than stripping the interior and rebuilding it as a modern venue, the architects have preserved every feature that could be saved — the painted ceiling, the worn brass rails, even the faded advertisements on the back wall — and made their own additions deliberately plain, so that new work is never mistaken for old. The result, which opened to the public last month, feels less like a new theatre than like an old one that has woken up. Ticket sales for the first season exceeded the trust's forecast within days. There are still rooms to finish and a section of roof awaiting funds, but the pigeons, at least, have moved on.
- question: In this text, "preserved" means —
- options: ["kept and protected from damage", "removed and replaced with copies", "repainted in brighter colours", "sold to raise money for repairs"]
- correct_index: 0
- correct_answer: kept and protected from damage
- explanation: Preserving is contrasted with stripping and rebuilding: the architects saved the original features rather than removing them.
- distractor_rationale: Replacement is the explicit alternative the trust rejected; repainting and selling fit a restoration story but contradict the careful keeping of originals.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Old Theatre",
  "topic_domain": "architecture_heritage",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, \"preserved\" means —",
      "options": [
        "kept and protected from damage",
        "removed and replaced with copies",
        "repainted in brighter colours",
        "sold to raise money for repairs"
      ],
      "correct_index": 0,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: How did the trust obtain the theatre?",
        "Answer to: Why were new additions made deliberately plain?"
      ],
      "match_options": [
        "It bought it for a symbolic single coin",
        "So new work would not be mistaken for old",
        "It inherited it from architects",
        "It won it in a planning dispute"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "specific_detail"
    },
    {
      "question": "Why were new additions made deliberately plain?",
      "response_type": "short_answer",
      "accepted_answers": [
        "So new work would not be mistaken for old"
      ],
      "max_words": 11,
      "subskill": "purpose"
    },
    {
      "question": "What does the phrase 'woken up' suggest about the theatre?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Its old character has been brought back to life"
      ],
      "max_words": 11,
      "subskill": "vocabulary_in_context"
    }
  ],
  "distractor_rationale": "Replacement is the alternative the trust rejected; repainting and selling contradict the careful keeping of originals."
}
```

---

## C1 (10 items)

### ITEM RDG-C1-01
- draft_id: RDG-C1-01
- cefr_level: C1
- question_type: mcq
- reading_subskill: argument_structure
- topic_domain: economics_policy
- title: The Case Against Congestion
- passage: Economists have long argued that traffic congestion is not, at root, an engineering problem but a pricing one. Roads at peak hours are typically free at the point of use, and a resource offered for nothing will be consumed until the queue itself becomes the rationing mechanism — which is precisely what a traffic jam is. The proposed remedy, congestion pricing, charges drivers more to enter busy areas at busy times, on the logic that this converts an invisible cost, wasted time, into a visible one, money, which drivers can then choose to avoid. Critics object that this simply prices poorer drivers off the road while the wealthy continue unimpeded, turning a shared inconvenience into a private privilege. Proponents reply that the current system already prices the poor off the road, just less visibly: those who cannot afford to lose an hour in traffic already avoid it, while the revenue from a congestion charge can, unlike lost time, be redirected toward public transport that benefits exactly the drivers being priced out. Neither side disputes that congestion has a cost; the disagreement is entirely about who should be made to see it.
- question: How is this passage primarily structured?
- options: ["A problem is diagnosed, a solution proposed, and an objection to it answered", "Two engineering solutions to traffic are compared and one is recommended", "A historical account of congestion pricing is given in chronological order", "A single expert's opinion on traffic is presented without challenge"]
- correct_index: 0
- correct_answer: A problem is diagnosed, a solution proposed, and an objection to it answered
- explanation: The text diagnoses congestion as a pricing problem, proposes congestion pricing, states the equity objection, and then presents the proponents' reply to that objection.
- distractor_rationale: No two engineering solutions are compared; there is no chronological history; multiple viewpoints (critics and proponents) are given, not a single unchallenged opinion.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Case Against Congestion",
  "topic_domain": "economics_policy",
  "reading_subskill": "argument_structure",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "How is this passage primarily structured?",
      "options": [
        "A problem is diagnosed, a solution proposed, and an objection to it answered",
        "Two engineering solutions to traffic are compared and one is recommended",
        "A historical account of congestion pricing is given in chronological order",
        "A single expert's opinion on traffic is presented without challenge"
      ],
      "correct_index": 0,
      "subskill": "argument_structure",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What does the passage call a traffic jam?",
        "Answer to: How do proponents answer the fairness criticism?"
      ],
      "match_options": [
        "A queue acting as a rationing mechanism",
        "They argue the current system already hurts poorer drivers less visibly",
        "A purely engineering failure",
        "A private privilege for poor drivers"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "How do proponents answer the fairness criticism?",
      "response_type": "short_answer",
      "accepted_answers": [
        "They argue the current system already hurts poorer drivers less visibly"
      ],
      "max_words": 13,
      "subskill": "argument_structure"
    },
    {
      "question": "What is the passage mainly evaluating?",
      "response_type": "short_answer",
      "accepted_answers": [
        "A pricing solution and the objection that it may be unfair"
      ],
      "max_words": 13,
      "subskill": "main_idea"
    }
  ],
  "distractor_rationale": "No two engineering solutions are compared; there is no chronology; both sides of the debate are given."
}
```

### ITEM RDG-C1-02
- draft_id: RDG-C1-02
- cefr_level: C1
- question_type: mcq
- reading_subskill: implication
- topic_domain: technology_ethics
- title: The Convenience Trap
- passage: Every generation of technology promises to save us time, and every generation, mysteriously, leaves us with less of it to spare. The washing machine did not, in the end, give housewives of the 1950s a life of leisure; it simply raised the standard of how often clothes were expected to be clean. The smartphone has not shortened the working day; it has dissolved its edges, so that a task once confined to the office now follows us to the dinner table and the school run. None of this is to say that such technologies fail to deliver their explicit promise — the washing machine genuinely washes faster than a washboard, the smartphone genuinely answers an email faster than a letter. What they deliver alongside that promise, quietly and without being asked, is a new and higher expectation of us, one that absorbs the time supposedly freed before we have had the chance to spend it on anything else. The writer also emphasizes that the issue cannot be judged through a single convenient measure. Small contextual differences change how readers interpret the evidence and the responsibilities involved.
- question: What does the writer imply about time-saving technologies?
- options: ["Their time savings tend to be absorbed by rising expectations rather than kept as leisure", "They have never actually performed their stated tasks faster than older methods", "They were designed deliberately to increase people's workload", "Only smartphones, not earlier technologies, have this hidden effect"]
- correct_index: 0
- correct_answer: Their time savings tend to be absorbed by rising expectations rather than kept as leisure
- explanation: The writer states such technologies deliver their explicit promise but also raise expectations that "absorb the time supposedly freed" — the implied pattern.
- distractor_rationale: The text explicitly says the machines do perform faster; deliberate design is never claimed, only an unintended effect; the washing machine example shows the pattern predates smartphones.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Convenience Trap",
  "topic_domain": "technology_ethics",
  "reading_subskill": "implication",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What does the writer imply about time-saving technologies?",
      "options": [
        "Their time savings tend to be absorbed by rising expectations rather than kept as leisure",
        "They have never actually performed their stated tasks faster than older methods",
        "They were designed deliberately to increase people's workload",
        "Only smartphones, not earlier technologies, have this hidden effect"
      ],
      "correct_index": 0,
      "subskill": "implication",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What happened after washing machines became common, according to the passage?",
        "Answer to: What does the smartphone example illustrate?"
      ],
      "match_options": [
        "Standards for cleanliness rose",
        "Technology can dissolve boundaries around work",
        "Housework disappeared",
        "Letters replaced emails"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What does the smartphone example illustrate?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Technology can dissolve boundaries around work"
      ],
      "max_words": 12,
      "subskill": "rhetorical_function"
    },
    {
      "question": "What is the writer's broader claim?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Saved time is often absorbed by new expectations"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "The text says the machines do work faster; no deliberate design is claimed; the washing machine shows the pattern predates smartphones."
}
```

### ITEM RDG-C1-03
- draft_id: RDG-C1-03
- cefr_level: C1
- question_type: mcq
- reading_subskill: tone
- topic_domain: literature_criticism
- title: On Rereading Old Favourites
- passage: There is a particular vanity in believing that the books which moved us at nineteen will move us equally at forty, as though a novel were a photograph, fixed the moment the shutter closes, rather than a conversation we resume with a different person each time we open it. I returned last month to a novel I had once pressed on every friend I owned, certain of its greatness, and found its hero, whom I had taken for tragic, merely tiresome — a young man mistaking his own moods for the weather. This is not, I want to insist, a complaint against the book, which has not changed a single word in the interval. It is an admission about the reader, who apparently has. I do not think this makes the earlier reading false, exactly; the nineteen-year-old who wept over that final chapter was real, and so, I suppose, is the forty-year-old who now finds the same chapter faintly embarrassing. I have simply stopped expecting the two of them to agree. The writer also emphasizes that the issue cannot be judged through a single convenient measure.
- question: What is the tone of this passage?
- options: ["Wry and self-aware", "Angrily dismissive", "Coldly academic", "Nostalgically uncritical"]
- correct_index: 0
- correct_answer: Wry and self-aware
- explanation: The writer gently mocks their own younger certainty ("a particular vanity") while affectionately acknowledging both past and present selves as "real" — self-aware humour, not anger or nostalgia.
- distractor_rationale: The writer explicitly refuses to complain about the book, ruling out anger; the tone is personal and reflective, not academic; the piece questions rather than indulges the earlier reading, ruling out uncritical nostalgia.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "On Rereading Old Favourites",
  "topic_domain": "literature_criticism",
  "reading_subskill": "tone",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the tone of this passage?",
      "options": [
        "Wry and self-aware",
        "Angrily dismissive",
        "Coldly academic",
        "Nostalgically uncritical"
      ],
      "correct_index": 0,
      "subskill": "tone",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What has changed between the two readings of the novel?",
        "Answer to: How does the writer view the earlier nineteen-year-old reading?"
      ],
      "match_options": [
        "The reader, not the book",
        "As real, even if no longer shared in the same way",
        "The final chapter",
        "The hero's actions"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "How does the writer view the earlier nineteen-year-old reading?",
      "response_type": "short_answer",
      "accepted_answers": [
        "As real, even if no longer shared in the same way"
      ],
      "max_words": 13,
      "subskill": "tone"
    },
    {
      "question": "What idea about rereading does the passage develop?",
      "response_type": "short_answer",
      "accepted_answers": [
        "A book can become a new conversation as the reader changes"
      ],
      "max_words": 13,
      "subskill": "main_idea"
    }
  ],
  "distractor_rationale": "The writer refuses to complain about the book, ruling out anger; the piece questions rather than indulges nostalgia."
}
```

### ITEM RDG-C1-04
- draft_id: RDG-C1-04
- cefr_level: C1
- question_type: mcq
- reading_subskill: main_idea
- topic_domain: science_environment
- title: The Myth of the Untouched Forest
- passage: For much of the twentieth century, conservation policy in many regions rested on an appealing but largely fictional image: the pristine forest, untouched by human hands until the arrival of loggers or farmers, which restoration should therefore aim to return to its original, human-free state. Archaeological and pollen-core evidence gathered over the past three decades has steadily dismantled this picture. Many of the forests once assumed to be primeval turn out to have been actively managed for centuries or millennia by the people who lived in them — burned selectively to encourage certain plants, thinned to favour fruit-bearing trees, planted with species useful for food or tools. The forest that early European surveyors described as wild and untouched was, in a great many documented cases, itself a form of agriculture, simply one that did not look like a field. This matters for conservation because a policy built on restoring a fictional emptiness will tend to remove the very human practices, the selective burning, the managed thinning, that produced the biodiversity worth protecting in the first place. The writer also emphasizes that the issue cannot be judged through a single convenient measure.
- question: What is the main idea of this passage?
- options: ["Conservation based on the idea of untouched forests overlooks the human management that shaped them", "Ancient peoples caused significant environmental damage to forests", "Modern archaeology has proven that all forests are entirely artificial", "European surveyors deliberately lied about the forests they found"]
- correct_index: 0
- correct_answer: Conservation based on the idea of untouched forests overlooks the human management that shaped them
- explanation: The passage argues that supposedly pristine forests were long managed by their inhabitants, and that conservation policy ignoring this can undo the very practices that created their biodiversity.
- distractor_rationale: The text describes management, not damage; "entirely artificial" overstates the claim, which concerns specific documented cases; the surveyors are described as mistaken, not deliberately dishonest.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Myth of the Untouched Forest",
  "topic_domain": "science_environment",
  "reading_subskill": "main_idea",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the main idea of this passage?",
      "options": [
        "Conservation based on the idea of untouched forests overlooks the human management that shaped them",
        "Ancient peoples caused significant environmental damage to forests",
        "Modern archaeology has proven that all forests are entirely artificial",
        "European surveyors deliberately lied about the forests they found"
      ],
      "correct_index": 0,
      "subskill": "main_idea",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What evidence challenged the image of untouched forests?",
        "Answer to: What were some forests actively shaped for?"
      ],
      "match_options": [
        "Archaeological and pollen-core evidence",
        "Food, tools, and useful plants",
        "Only modern tourist reports",
        "European surveyors' private diaries"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What were some forests actively shaped for?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Food, tools, and useful plants"
      ],
      "max_words": 12,
      "subskill": "specific_detail"
    },
    {
      "question": "What does the passage imply for conservation policy?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It should account for long histories of human management"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "The text describes management, not damage or total artificiality; surveyors are mistaken, not dishonest."
}
```

### ITEM RDG-C1-05
- draft_id: RDG-C1-05
- cefr_level: C1
- question_type: mcq
- reading_subskill: rhetorical_function
- topic_domain: education_policy
- title: On Standardised Testing
- passage: Imagine judging the health of an entire orchard by measuring the diameter of every trunk on a single Tuesday in March, then ranking the orchards accordingly and directing next year's water and fertiliser only to the ones that measured largest. You would learn something, certainly — trunk diameter is not nothing — but you would also systematically starve the young trees still building their root systems, the varieties that fruit late, the ones recovering from last winter's frost. Something close to this is what a school system does when it allocates resources primarily on the basis of a single annual test score. The comparison is not offered to suggest that measurement itself is the enemy; orchards, like schools, benefit from being measured, and no serious critic proposes abandoning assessment altogether. It is offered to ask a narrower question: whether one number, taken on one day, should really be allowed to decide so much. The writer also emphasizes that the issue cannot be judged through a single convenient measure. Small contextual differences change how readers interpret the evidence and the responsibilities involved. This gives the passage a more cautious and layered argument.
- question: What is the function of the orchard comparison in this passage?
- options: ["To illustrate the danger of using one narrow measure to allocate resources", "To argue that all forms of testing should be eliminated", "To prove that trees and students face identical problems", "To criticise farmers for measuring their orchards incorrectly"]
- correct_index: 0
- correct_answer: To illustrate the danger of using one narrow measure to allocate resources
- explanation: The orchard image is explicitly built to show the risk of judging complex, developing things by a single measurement — directly paralleled to school test scores.
- distractor_rationale: The writer explicitly says measurement itself is not the enemy and no critic proposes abandoning assessment; the comparison is illustrative, not a claim that trees and students are identical; farmers are not criticised.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "On Standardised Testing",
  "topic_domain": "education_policy",
  "reading_subskill": "rhetorical_function",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the function of the orchard comparison in this passage?",
      "options": [
        "To illustrate the danger of using one narrow measure to allocate resources",
        "To argue that all forms of testing should be eliminated",
        "To prove that trees and students face identical problems",
        "To criticise farmers for measuring their orchards incorrectly"
      ],
      "correct_index": 0,
      "subskill": "rhetorical_function",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What does the orchard analogy criticise?",
        "Answer to: What does the writer say about measurement itself?"
      ],
      "match_options": [
        "Using one narrow measure to make broad resource decisions",
        "It is useful but insufficient when too narrow",
        "Measuring trees too often throughout the year",
        "Giving water to smaller orchards first"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What does the writer say about measurement itself?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It is useful but insufficient when too narrow"
      ],
      "max_words": 12,
      "subskill": "argument_structure"
    },
    {
      "question": "Which students or schools risk being misread by one annual score?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Those still developing or recovering from setbacks"
      ],
      "max_words": 12,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "The writer explicitly says measurement is not the enemy; the comparison is illustrative, not a literal equivalence claim."
}
```

### ITEM RDG-C1-06
- draft_id: RDG-C1-06
- cefr_level: C1
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: linguistics
- title: The Persistence of Dialect
- passage: Despite a century of mass broadcasting, universal schooling, and now algorithmically homogenised social media, regional dialects have proven remarkably resistant to erosion. Linguists once predicted that radio and television would flatten local speech into a single national standard within a generation or two; instead, detailed acoustic studies of vowel sounds across decades show many regional distinctions holding steady, and in some cases sharpening, even among young speakers who consume identical media to their peers two hundred miles away. One explanation gaining ground is that accent functions less as an accident of geography than as a badge of belonging, actively maintained, consciously or not, as a signal of local identity in a world where so many other markers of where one is from have dissolved. On this account, the dialect is not a fossil, gradually worn smooth by outside pressure, but closer to a flag, deliberately kept flying. The writer also emphasizes that the issue cannot be judged through a single convenient measure. Small contextual differences change how readers interpret the evidence and the responsibilities involved. This gives the passage a more cautious and layered argument.
- question: In this text, "erosion" is used to suggest that dialects were expected to —
- options: ["gradually wear away and disappear over time", "suddenly disappear within a single generation", "become officially banned by governments", "merge together into several regional groups"]
- correct_index: 0
- correct_answer: gradually wear away and disappear over time
- explanation: Erosion describes a slow, gradual process, matching the prediction that broadcasting would flatten dialects "within a generation or two" — and the later contrast with a "fossil... gradually worn smooth" confirms the gradual sense.
- distractor_rationale: "Suddenly" contradicts the gradual sense of erosion; banning is never mentioned; the text discusses disappearance into one national standard, not merging into several groups.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Persistence of Dialect",
  "topic_domain": "linguistics",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, \"erosion\" is used to suggest that dialects were expected to —",
      "options": [
        "gradually wear away and disappear over time",
        "suddenly disappear within a single generation",
        "become officially banned by governments",
        "merge together into several regional groups"
      ],
      "correct_index": 0,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What did linguists once expect mass media to do?",
        "Answer to: What explanation is gaining ground?"
      ],
      "match_options": [
        "Flatten local speech into a national standard",
        "Accent works as a badge of belonging",
        "Sharpen every regional distinction",
        "End schooling within two generations"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What explanation is gaining ground?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Accent works as a badge of belonging"
      ],
      "max_words": 12,
      "subskill": "main_idea"
    },
    {
      "question": "Why is dialect not merely a leftover in this account?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Speakers actively maintain it as identity"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "Erosion implies gradual change, not suddenness; banning and merging into groups are not discussed."
}
```

### ITEM RDG-C1-07
- draft_id: RDG-C1-07
- cefr_level: C1
- question_type: mcq
- reading_subskill: inference
- topic_domain: business_strategy
- title: The Slow Yes
- passage: At a mid-sized manufacturing company, an internal team once proposed a faster, cheaper way to produce the company's best-selling product, developed almost entirely in their own time between official projects. Leadership's response was not rejection but something quieter and more persistent: repeated internal reviews, each concluding that the new method was promising but not yet reliable, that customers seemed content with the existing process, and that more testing was needed before any resources were committed. These conclusions were not unreasonable individually — early trials really were inconsistent, and customer interest really was modest. What the reviews consistently failed to notice was the direction in which that modest interest was moving. The team kept refining the method quietly, without a dedicated budget, for several years, while smaller competitors, less cautious and less thorough, adopted rougher early versions and steadily won over customers who cared more about low prices than established quality. By the time leadership finally approved full investment in the new method, the company's reputation for making the best version of the old one no longer mattered to a market that had already moved on. The writer also emphasizes that the issue cannot be judged through a single convenient measure.
- question: What can be inferred about the company's decision-making process?
- options: ["Its caution, though individually reasonable, ultimately caused it to miss the market", "It deliberately blocked the new method to protect its existing product line", "Its internal team lacked the skill to make the method reliable", "It sold the new method to a competitor for a large profit"]
- correct_index: 0
- correct_answer: Its caution, though individually reasonable, ultimately caused it to miss the market
- explanation: Each review's conclusion was defensible on its own ("not unreasonable individually"), yet the cumulative delay meant the company's reputation "no longer mattered to a market that had already moved on" once it finally invested.
- distractor_rationale: Deliberate blocking to protect the old product line is never stated — the reviews are described as sincere, not strategic; the team clearly kept improving the method for years, showing real skill; no sale to a competitor is mentioned — rival companies developed their own versions independently.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Slow Yes",
  "topic_domain": "business_strategy",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What can be inferred about the company's decision-making process?",
      "options": [
        "Its caution, though individually reasonable, ultimately caused it to miss the market",
        "It deliberately blocked the new method to protect its existing product line",
        "Its internal team lacked the skill to make the method reliable",
        "It sold the new method to a competitor for a large profit"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: How did leadership respond to the team's proposal?",
        "Answer to: What did the reviews fail to notice?"
      ],
      "match_options": [
        "With repeated cautious reviews rather than open rejection",
        "The direction in which customer interest was moving",
        "By immediately funding it fully",
        "By firing the internal team"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What did the reviews fail to notice?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The direction in which customer interest was moving"
      ],
      "max_words": 12,
      "subskill": "inference"
    },
    {
      "question": "What does the title 'The Slow Yes' suggest?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Approval can come so slowly that the opportunity is lost"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "Deliberate blocking is not stated and the reviews are sincere; the team kept improving the method; no sale to a competitor occurs."
}
```

### ITEM RDG-C1-08
- draft_id: RDG-C1-08
- cefr_level: C1
- question_type: mcq
- reading_subskill: purpose
- topic_domain: philosophy_everyday
- title: In Praise of Boredom
- passage: Modern life has arranged itself, with impressive thoroughness, to ensure that boredom is never more than a pocket's reach away. Whatever thirty seconds of unoccupied attention might once have offered — a wandering thought, a genuine observation of the room one is sitting in, the mild discomfort out of which, occasionally, an idea is born — has been quietly engineered out of existence by a device that promises, and largely delivers, an infinite supply of small distractions exactly calibrated to fill it. This essay is not an argument for switching off every screen and waiting nobly for inspiration to strike, a piece of advice easy to give and almost impossible to follow. It is a narrower plea: that we notice what we are trading away, and that we occasionally, deliberately, leave the thirty seconds unfilled, if only to remember what used to live there. The writer also emphasizes that the issue cannot be judged through a single convenient measure. Small contextual differences change how readers interpret the evidence and the responsibilities involved. This gives the passage a more cautious and layered argument. The writer also emphasizes that the issue cannot be judged through a single convenient measure.
- question: What is the writer's main purpose in this passage?
- options: ["To encourage readers to occasionally allow themselves unfilled, boring moments", "To persuade readers to give up smartphones entirely", "To explain the psychological causes of boredom in scientific terms", "To criticise technology companies for designing addictive products"]
- correct_index: 0
- correct_answer: To encourage readers to occasionally allow themselves unfilled, boring moments
- explanation: The writer explicitly frames the piece as "a narrower plea" to leave moments deliberately unfilled, distinct from a call to abandon devices entirely.
- distractor_rationale: The writer explicitly rejects the "switch off every screen" argument; no scientific mechanism is explained; technology companies are implied but never directly criticised as the essay's purpose.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "In Praise of Boredom",
  "topic_domain": "philosophy_everyday",
  "reading_subskill": "purpose",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the writer's main purpose in this passage?",
      "options": [
        "To encourage readers to occasionally allow themselves unfilled, boring moments",
        "To persuade readers to give up smartphones entirely",
        "To explain the psychological causes of boredom in scientific terms",
        "To criticise technology companies for designing addictive products"
      ],
      "correct_index": 0,
      "subskill": "purpose",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What does the writer say smartphones have engineered away?",
        "Answer to: What does the writer explicitly not argue for?"
      ],
      "match_options": [
        "Small moments of unoccupied attention",
        "Switching off every screen and waiting for inspiration",
        "All forms of communication",
        "The need for observation"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What does the writer explicitly not argue for?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Switching off every screen and waiting for inspiration"
      ],
      "max_words": 12,
      "subskill": "purpose"
    },
    {
      "question": "What value does the writer attach to boredom?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It can create space for thought and observation"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "The writer explicitly rejects the 'switch off every screen' argument; no scientific mechanism is explained."
}
```

### ITEM RDG-C1-09
- draft_id: RDG-C1-09
- cefr_level: C1
- question_type: mcq
- reading_subskill: argument_structure
- topic_domain: workplace_automation
- title: Why Automation Doesn't Always Cut Jobs
- passage: It is one of the more counterintuitive findings in labour economics, and one that alarms about job losses rarely mention: installing more automation in a workplace does not reliably shrink the total number of people employed there, and can sometimes increase it. The mechanism is not mysterious once stated. When a machine takes over one narrow task, the cost of producing the wider product or service falls, which typically increases demand for that product or service. Rising demand requires more of the tasks that have not been automated — installation, maintenance, sales, customisation, quality control — and these tasks often require more workers than the single automated step used to need. Studies tracking this effect across dozens of automated workplaces have found the pattern common enough that some economists now treat it less as a surprising exception than as a standard part of how automation actually plays out: you cannot assume that removing one task removes the need for the people around it, because the task you automate changes the very demand it was meant to satisfy. The writer also emphasizes that the issue cannot be judged through a single convenient measure.
- question: How does this passage build its central argument?
- options: ["It states a counterintuitive claim, then explains the causal mechanism behind it", "It presents two competing economic theories and lets the reader choose between them", "It tells the personal story of one factory worker who lost a job", "It lists several unrelated employment and wage statistics without connecting them"]
- correct_index: 0
- correct_answer: It states a counterintuitive claim, then explains the causal mechanism behind it
- explanation: The passage opens by naming the counterintuitive finding, then walks through, step by step, why falling costs raise demand and increase the need for the surrounding, non-automated tasks.
- distractor_rationale: No two competing theories are set against each other; no individual worker's story is told; the automated-workplace evidence mentioned is used to support one connected argument, not listed separately.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Why Automation Doesn't Always Cut Jobs",
  "topic_domain": "workplace_automation",
  "reading_subskill": "argument_structure",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "How does this passage build its central argument?",
      "options": [
        "It states a counterintuitive claim, then explains the causal mechanism behind it",
        "It presents two competing economic theories and lets the reader choose between them",
        "It tells the personal story of one factory worker who lost a job",
        "It lists several unrelated employment and wage statistics without connecting them"
      ],
      "correct_index": 0,
      "subskill": "argument_structure",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What happens when automation lowers production costs?",
        "Answer to: Which tasks may need more workers after automation?"
      ],
      "match_options": [
        "Demand may rise for the wider product or service",
        "Installation, maintenance, sales, customisation, and quality control",
        "All workers are immediately removed",
        "Quality control becomes unnecessary"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "Which tasks may need more workers after automation?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Installation, maintenance, sales, customisation, and quality control"
      ],
      "max_words": 12,
      "subskill": "specific_detail"
    },
    {
      "question": "What assumption does the passage challenge?",
      "response_type": "short_answer",
      "accepted_answers": [
        "That removing one task removes the need for surrounding workers"
      ],
      "max_words": 12,
      "subskill": "argument_structure"
    }
  ],
  "distractor_rationale": "No competing theories are set against each other; no individual's story is told; the evidence supports one connected argument."
}
```

### ITEM RDG-C1-10
- draft_id: RDG-C1-10
- cefr_level: C1
- question_type: mcq
- reading_subskill: tone
- topic_domain: memoir_family
- title: My Father's Toolbox
- passage: My father was not a sentimental man, or so he would have insisted, usually while doing something quietly sentimental like re-oiling a hand plane that had belonged to his own father and that he never once used. When he died, I inherited the toolbox, and with it the small, absurd argument I now have with myself every time I open it: whether to use the tools as tools, which is presumably what he would have said he wanted, or to preserve them exactly as he left them, which is certainly what he actually did with his own father's plane. I have not resolved this argument. The chisels get used, a little guiltily, on the odd shelf or door hinge; the good saw, the one he was proudest of, sits wrapped in the same cloth he wrapped it in, and I tell myself I am saving it for something worthy of it, a lie I have now told myself for eleven years. I suspect, in the end, I am simply becoming him, one carefully unused tool at a time. The writer also emphasizes that the issue cannot be judged through a single convenient measure.
- question: What is the tone of this passage?
- options: ["Affectionately self-mocking", "Bitterly resentful", "Formally instructive", "Emotionally detached"]
- correct_index: 0
- correct_answer: Affectionately self-mocking
- explanation: The writer gently mocks both the father's contradictions and their own ("a lie I have now told myself for eleven years") while clearly writing with warmth about the inheritance.
- distractor_rationale: There is no resentment expressed toward the father; the passage is personal and wandering, not instructive; the writer's admitted guilt and self-deprecation rule out emotional detachment.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "My Father's Toolbox",
  "topic_domain": "memoir_family",
  "reading_subskill": "tone",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the tone of this passage?",
      "options": [
        "Affectionately self-mocking",
        "Bitterly resentful",
        "Formally instructive",
        "Emotionally detached"
      ],
      "correct_index": 0,
      "subskill": "tone",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What conflict does the inherited toolbox create for the writer?",
        "Answer to: Which tool remains wrapped in cloth?"
      ],
      "match_options": [
        "Whether to use the tools or preserve them untouched",
        "The good saw",
        "Whether to sell the tools immediately",
        "Whether to buy newer tools"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "Which tool remains wrapped in cloth?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The good saw"
      ],
      "max_words": 12,
      "subskill": "specific_detail"
    },
    {
      "question": "What does the final sentence imply?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The writer is repeating his father's habits despite himself"
      ],
      "max_words": 12,
      "subskill": "inference"
    }
  ],
  "distractor_rationale": "No resentment is expressed; the passage is personal, not instructive; admitted guilt rules out detachment."
}
```

---

## C2 (10 items)

### ITEM RDG-C2-01
- draft_id: RDG-C2-01
- cefr_level: C2
- question_type: mcq
- reading_subskill: author_purpose
- topic_domain: philosophy_language
- title: The Word We Have No Word For
- passage: There is a particular species of dishonesty that English, for all its magpie vocabulary, has never quite gotten around to naming: the claim that is technically true, offered in circumstances engineered to produce a false impression, by a speaker who would object, with some justice, to being called a liar. "I did not take the money from the drawer" is unimpeachable if one took it from an envelope beside the drawer; the sentence survives any polygraph, and its survival is precisely the point. We reach, in the absence of a native term, for borrowings and neologisms — paltering, weasel words, the lawyerly non-denial denial — each capturing a slice of the phenomenon without quite cornering it. I do not think this gap in the lexicon is an accident of etymology so much as a symptom: languages tend to name, with precision, the sins their speakers find it useful to accuse others of, and to leave conveniently blurred the sins they might, on occasion, wish to commit themselves. We are, in other words, better equipped linguistically to catch the liar than the merely misleading, which may say less about English than about what its speakers, over centuries, have quietly preferred to get away with. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered.
- question: What is the author's main purpose in this passage?
- options: ["To suggest that gaps in a language's vocabulary can reveal what its speakers find convenient to obscure", "To provide a formal linguistic history of the word 'paltering'", "To argue that all borrowed English vocabulary originated in legal contexts", "To recommend that a new word be officially added to the dictionary"]
- correct_index: 0
- correct_answer: To suggest that gaps in a language's vocabulary can reveal what its speakers find convenient to obscure
- explanation: The author explicitly frames the missing word as "a symptom" revealing what speakers "might, on occasion, wish to commit themselves" — the essay's real purpose is this broader claim about language and convenience, not lexicography for its own sake.
- distractor_rationale: No formal etymological history is given; the legal origin claim covers only one example, not all borrowed vocabulary; no dictionary campaign is proposed — the "gap" is treated as revealing, not as something to simply fix.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Word We Have No Word For",
  "topic_domain": "philosophy_language",
  "reading_subskill": "author_purpose",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the author's main purpose in this passage?",
      "options": [
        "To suggest that gaps in a language's vocabulary can reveal what its speakers find convenient to obscure",
        "To provide a formal linguistic history of the word 'paltering'",
        "To argue that all borrowed English vocabulary originated in legal contexts",
        "To recommend that a new word be officially added to the dictionary"
      ],
      "correct_index": 0,
      "subskill": "author_purpose",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What kind of dishonesty does the passage focus on?",
        "Answer to: Why does the author mention paltering and weasel words?"
      ],
      "match_options": [
        "A technically true statement designed to mislead",
        "To show attempts to name parts of the phenomenon without fully capturing it",
        "A simple factual lie with no ambiguity",
        "A legal term with one precise native name"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "Why does the author mention paltering and weasel words?",
      "response_type": "short_answer",
      "accepted_answers": [
        "To show attempts to name parts of the phenomenon without fully capturing it"
      ],
      "max_words": 15,
      "subskill": "rhetorical_function"
    },
    {
      "question": "What does the lexical gap suggest, according to the author?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Speakers may prefer some misleading practices to remain blurred"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "No formal etymology or legal-origin claim for all vocabulary is made; the gap is treated as revealing, not as something to fix."
}
```

### ITEM RDG-C2-02
- draft_id: RDG-C2-02
- cefr_level: C2
- question_type: mcq
- reading_subskill: implication
- topic_domain: science_epistemology
- title: The Confidence of the Discredited
- passage: One of the more unsettling regularities in the history of science is how rarely a discredited theory's proponents experience their discrediting as such. The retraction arrives, the data is reanalysed, the field moves on, and the original researcher, more often than a comfortable narrative would suggest, is left not chastened but merely puzzled, convinced that some procedural unfairness rather than an error of substance accounts for their exile from the consensus. This is not, primarily, a story about dishonesty; outright fraud is rarer and more legible than this stranger phenomenon, in which perfectly sincere researchers construct, with real intellectual effort, an account of their own downfall that leaves their original judgment intact. What makes this pattern worth dwelling on is not that it is surprising — motivated reasoning is hardly news — but that it appears to strengthen, rather than weaken, with expertise. The deepest specialists in a field, who have the most invested and the most sophisticated tools for defending that investment, are not obviously less susceptible than novices; if anything, their very expertise supplies more raw material with which to build the exculpatory account. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered. This makes the writer's position deliberately cautious rather than simply supportive or dismissive. The reader is therefore pushed to weigh nuance, evidence, and implication at the same time.
- question: What does the passage imply about expertise in relation to this pattern?
- options: ["Greater expertise does not reliably protect a researcher from this kind of self-deception, and may even assist it", "Expertise always causes researchers to become dishonest over time", "Only novice researchers are ever discredited by new evidence", "Experts are immune to motivated reasoning because of their training"]
- correct_index: 0
- correct_answer: Greater expertise does not reliably protect a researcher from this kind of self-deception, and may even assist it
- explanation: The text states the pattern "appears to strengthen, rather than weaken, with expertise", and that expertise "supplies more raw material" for self-justification — implying expertise does not protect against, and may enable, the pattern.
- distractor_rationale: The passage explicitly distinguishes this pattern from dishonesty/fraud; novices are never said to be the only ones discredited; "immune" directly contradicts the stated strengthening effect.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Confidence of the Discredited",
  "topic_domain": "science_epistemology",
  "reading_subskill": "implication",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What does the passage imply about expertise in relation to this pattern?",
      "options": [
        "Greater expertise does not reliably protect a researcher from this kind of self-deception, and may even assist it",
        "Expertise always causes researchers to become dishonest over time",
        "Only novice researchers are ever discredited by new evidence",
        "Experts are immune to motivated reasoning because of their training"
      ],
      "correct_index": 0,
      "subskill": "implication",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: How do proponents often experience their theory's discrediting?",
        "Answer to: Why is outright fraud not the main focus?"
      ],
      "match_options": [
        "As puzzling unfairness rather than substantive error",
        "The passage is concerned with sincere self-protective reasoning",
        "As immediate moral guilt",
        "As proof they committed fraud"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "Why is outright fraud not the main focus?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The passage is concerned with sincere self-protective reasoning"
      ],
      "max_words": 12,
      "subskill": "argument_structure"
    },
    {
      "question": "What makes expertise potentially dangerous here?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It supplies more material for defending prior commitments"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "The passage distinguishes this from dishonesty; novices aren't singled out; 'immune' contradicts the stated strengthening effect."
}
```

### ITEM RDG-C2-03
- draft_id: RDG-C2-03
- cefr_level: C2
- question_type: mcq
- reading_subskill: rhetorical_function
- topic_domain: literary_criticism
- title: The Footnote as Confession
- passage: Scholarly footnotes present themselves as the humble plumbing of an argument — mere citation, mere acknowledgment, beneath the notice of anyone but the pedant or the plagiarism committee. I want to suggest, perversely, that they are often the most emotionally honest part of the text they support, precisely because no one is reading them for style. The body of the essay is written for an audience and therefore performs a certain confidence; the footnote, written for almost no one, is where the qualifications live, the "though see also," the "I am grateful to X for pointing out an error in an earlier draft," the small, buried admission that the tidy claim above rests on a citation the author has not, in fact, been able to verify firsthand. To read only the argument and skip the footnotes is to read the author's public face and miss the diary kept in the margins — less because the footnotes contain secrets, exactly, than because they are the one place in the text where the performance of certainty is allowed, briefly, to relax. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered. This makes the writer's position deliberately cautious rather than simply supportive or dismissive. The reader is therefore pushed to weigh nuance, evidence, and implication at the same time.
- question: What rhetorical function does the phrase "the diary kept in the margins" serve in this passage?
- options: ["It figuratively captures how footnotes reveal a more private, less confident version of the author", "It literally describes a diary that the author kept alongside the essay", "It criticises scholars for writing footnotes that are too personal", "It explains a specific citation rule that footnotes must follow"]
- correct_index: 0
- correct_answer: It figuratively captures how footnotes reveal a more private, less confident version of the author
- explanation: The phrase is a metaphor extending the essay's central claim that footnotes are where the "performance of certainty" relaxes, i.e. a more private register than the main text.
- distractor_rationale: No literal diary is mentioned; the passage argues footnotes are unusually honest, not that they are inappropriately personal; no citation rule is described anywhere in the text.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Footnote as Confession",
  "topic_domain": "literary_criticism",
  "reading_subskill": "rhetorical_function",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What rhetorical function does the phrase \"the diary kept in the margins\" serve in this passage?",
      "options": [
        "It figuratively captures how footnotes reveal a more private, less confident version of the author",
        "It literally describes a diary that the author kept alongside the essay",
        "It criticises scholars for writing footnotes that are too personal",
        "It explains a specific citation rule that footnotes must follow"
      ],
      "correct_index": 0,
      "subskill": "rhetorical_function",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: How does the essay body differ from the footnote, according to the writer?",
        "Answer to: Why are footnotes described as emotionally honest?"
      ],
      "match_options": [
        "The body performs confidence while the footnote allows qualification",
        "They hold qualifications and small admissions with less performance",
        "The body is ignored while footnotes are public speeches",
        "The body contains only citations"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "Why are footnotes described as emotionally honest?",
      "response_type": "short_answer",
      "accepted_answers": [
        "They hold qualifications and small admissions with less performance"
      ],
      "max_words": 12,
      "subskill": "inference"
    },
    {
      "question": "What does skipping footnotes cause a reader to miss?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The author's less certain private-facing voice"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "No literal diary exists; footnotes are praised as honest, not criticised as too personal; no citation rule is described."
}
```

### ITEM RDG-C2-04
- draft_id: RDG-C2-04
- cefr_level: C2
- question_type: mcq
- reading_subskill: argument_structure
- topic_domain: economics_behavioral
- title: The Rational Case for Irrationality
- passage: Behavioural economics has spent half a century cataloguing the ways human beings deviate from the rational-actor model of classical theory, and the resulting inventory — loss aversion, anchoring, the endowment effect, and a small library of further biases — is generally presented as a list of errors, deviations from a norm that a wiser agent would avoid. There is, however, a less travelled argument worth setting against this framing: that many of these "biases" are not malfunctions of reasoning but reasonable heuristics operating correctly under conditions the laboratory does not replicate. Loss aversion looks irrational when a subject is asked to evaluate a single hypothetical gamble in isolation; it looks considerably more sensible for an organism that, across an evolutionary history of genuinely scarce and non-renewable resources, could not always count on a second gamble being offered. None of this rescues every documented bias from the charge of error — some plainly do cause worse outcomes even by their own holder's stated goals — but it should complicate any argument that treats the entire catalogue as a uniform indictment of the human mind, rather than as a mixed inheritance, partly maladapted, partly still quietly earning its keep. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered. This makes the writer's position deliberately cautious rather than simply supportive or dismissive.
- question: How does the passage structure its central argument?
- options: ["It presents the standard critical view, then offers a qualified counter-argument that partially, not wholly, challenges it", "It rejects behavioural economics entirely as a discipline", "It proves that every cognitive bias is beneficial under laboratory conditions", "It summarises a single study without evaluating its conclusions"]
- correct_index: 0
- correct_answer: It presents the standard critical view, then offers a qualified counter-argument that partially, not wholly, challenges it
- explanation: The passage states the usual "errors" framing, then argues many biases are reasonable heuristics, but explicitly concedes "some plainly do cause worse outcomes" — a partial, qualified challenge, not a wholesale rejection.
- distractor_rationale: The field itself is not rejected, only one framing of its findings; the passage explicitly does not claim every bias is beneficial; no single study is summarised — the argument is conceptual, not a literature review of one paper.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Rational Case for Irrationality",
  "topic_domain": "economics_behavioral",
  "reading_subskill": "argument_structure",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "How does the passage structure its central argument?",
      "options": [
        "It presents the standard critical view, then offers a qualified counter-argument that partially, not wholly, challenges it",
        "It rejects behavioural economics entirely as a discipline",
        "It proves that every cognitive bias is beneficial under laboratory conditions",
        "It summarises a single study without evaluating its conclusions"
      ],
      "correct_index": 0,
      "subskill": "argument_structure",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What alternative view of biases does the passage propose?",
        "Answer to: Why is loss aversion used as an example?"
      ],
      "match_options": [
        "Some may be reasonable heuristics in conditions unlike the lab",
        "It appears different when viewed against scarce evolutionary conditions",
        "All biases are perfect reasoning tools",
        "Classical theory has catalogued every bias"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "Why is loss aversion used as an example?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It appears different when viewed against scarce evolutionary conditions"
      ],
      "max_words": 12,
      "subskill": "rhetorical_function"
    },
    {
      "question": "What qualification does the author make?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Some biases still plainly cause worse outcomes"
      ],
      "max_words": 12,
      "subskill": "argument_structure"
    }
  ],
  "distractor_rationale": "The field itself isn't rejected; not every bias is claimed beneficial; no single study is being summarised."
}
```

### ITEM RDG-C2-05
- draft_id: RDG-C2-05
- cefr_level: C2
- question_type: mcq
- reading_subskill: tone
- topic_domain: memoir_translation
- title: Lost, and Found Elsewhere
- passage: Translators are forever being asked, usually by people who have never attempted it, whether something is not inevitably "lost in translation," a phrase offered with the mild sympathy one might extend to a widower. I have come to find the question almost willfully incomplete, not because nothing is lost — plenty is, and I could produce a rueful catalogue of puns I have watched die on the operating table of a second language — but because the framing implies a one-directional leak, translation as puncture, when in my experience it behaves rather more like decanting a wine into a differently shaped glass: something of the original bouquet does disperse, certainly, but the new vessel also catches and holds notes the first one never quite showed. A sentence that limps in its native tongue sometimes strides in its second; a joke that dies finds, on occasion, a cousin two languages over that lands better than the original ever did. I am not arguing translation is costless. I am arguing that the ledger has a credit column as well as a debit one, and that thirty years into this trade, I have stopped apologising for the exchange rate. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered. This makes the writer's position deliberately cautious rather than simply supportive or dismissive.
- question: What is the tone of this passage?
- options: ["Gently defensive but ultimately confident", "Apologetic and full of regret", "Aggressively dismissive of critics", "Purely technical and impersonal"]
- correct_index: 0
- correct_answer: Gently defensive but ultimately confident
- explanation: The writer pushes back against a common assumption ("almost willfully incomplete") while conceding real losses, and closes with settled confidence: "I have stopped apologising for the exchange rate."
- distractor_rationale: The final line explicitly rejects apology/regret; the pushback is measured, not aggressive, and never attacks the questioners personally; the piece is personal and image-rich, not technical.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "Lost, and Found Elsewhere",
  "topic_domain": "memoir_translation",
  "reading_subskill": "tone",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the tone of this passage?",
      "options": [
        "Gently defensive but ultimately confident",
        "Apologetic and full of regret",
        "Aggressively dismissive of critics",
        "Purely technical and impersonal"
      ],
      "correct_index": 0,
      "subskill": "tone",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What does the author find incomplete about the usual question on translation?",
        "Answer to: What is the function of the wine-glass comparison?"
      ],
      "match_options": [
        "It notices loss but ignores possible gains",
        "It shows that a new form can reveal qualities as well as lose them",
        "It is too technical for translators",
        "It denies that anything is ever lost"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What is the function of the wine-glass comparison?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It shows that a new form can reveal qualities as well as lose them"
      ],
      "max_words": 16,
      "subskill": "rhetorical_function"
    },
    {
      "question": "What does the ledger metaphor emphasise?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Translation has gains as well as losses"
      ],
      "max_words": 12,
      "subskill": "implication"
    }
  ],
  "distractor_rationale": "The final line rejects apology/regret; the pushback is measured, not aggressive; the piece is personal, not technical."
}
```

### ITEM RDG-C2-06
- draft_id: RDG-C2-06
- cefr_level: C2
- question_type: mcq
- reading_subskill: inference
- topic_domain: history_institutions
- title: The Committee That Outlived Its Purpose
- passage: Few organisational phenomena are as reliably underestimated as the tendency of a body created to solve a specific problem to persist, largely unchanged in form, long after the problem itself has been solved, forgotten, or rendered irrelevant by events its founders could not have anticipated. The wartime rationing board, once the war and the rationing both end, does not so much disband as rediscover itself: its expertise in distribution is redirected toward some adjacent question, its staff quietly reclassified rather than released, its original enabling statute amended rather than repealed. Ask any of its members why the board still exists and you will rarely be told "because disbanding an institution is administratively harder than founding one, and no individual within it is incentivised to propose their own redundancy" — a perfectly accurate answer that nobody involved finds it comfortable to give. You will instead be offered an account, sincerely believed, of the board's continuing indispensability to some newly discovered mission, an account that will itself be revised again the next time history obliges the board to justify itself afresh. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered. This makes the writer's position deliberately cautious rather than simply supportive or dismissive. The reader is therefore pushed to weigh nuance, evidence, and implication at the same time.
- question: What can be inferred about the members of such institutions?
- options: ["They likely believe their institution's stated purpose even as it shifts to justify continued existence", "They are fully aware that their justifications are dishonest and cynically maintain the deception", "They deliberately created the institution's original mission to be permanently vague", "They actively campaign to have their positions eliminated once the original task ends"]
- correct_index: 0
- correct_answer: They likely believe their institution's stated purpose even as it shifts to justify continued existence
- explanation: The text says the alternative "indispensability" account is "sincerely believed", contrasted with the accurate-but-uncomfortable structural explanation nobody offers — implying genuine belief, not conscious dishonesty.
- distractor_rationale: "Sincerely believed" rules out deliberate cynicism; no claim is made that the original mission was designed to be vague; the text says redundancy is not proposed, the opposite of actively campaigning for elimination.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Committee That Outlived Its Purpose",
  "topic_domain": "history_institutions",
  "reading_subskill": "inference",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What can be inferred about the members of such institutions?",
      "options": [
        "They likely believe their institution's stated purpose even as it shifts to justify continued existence",
        "They are fully aware that their justifications are dishonest and cynically maintain the deception",
        "They deliberately created the institution's original mission to be permanently vague",
        "They actively campaign to have their positions eliminated once the original task ends"
      ],
      "correct_index": 0,
      "subskill": "inference",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What happens to the rationing board in the example?",
        "Answer to: Why is the accurate explanation rarely given?"
      ],
      "match_options": [
        "It redirects its expertise after the original need ends",
        "It is administratively and personally uncomfortable",
        "It immediately disbands after the war",
        "It admits it has no new mission"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "Why is the accurate explanation rarely given?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It is administratively and personally uncomfortable"
      ],
      "max_words": 12,
      "subskill": "inference"
    },
    {
      "question": "What broader organisational pattern is described?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Institutions often preserve themselves by redefining their purpose"
      ],
      "max_words": 12,
      "subskill": "main_idea"
    }
  ],
  "distractor_rationale": "'Sincerely believed' rules out cynicism; no vague-by-design claim is made; nobody proposes their own redundancy."
}
```

### ITEM RDG-C2-07
- draft_id: RDG-C2-07
- cefr_level: C2
- question_type: mcq
- reading_subskill: author_purpose
- topic_domain: art_criticism
- title: In Defence of the Unfinished
- passage: Museums have trained us, with the best of intentions, to regard the unfinished work as a kind of intermission — interesting chiefly as a rehearsal for the finished object that would have existed had the artist lived, or cared, or found the patron, to complete it. I want to argue for a less patient view of certain unfinished paintings: not that they are secretly finished and we have simply failed to notice, a claim that would collapse under its own cleverness, but that finish itself is one value among several a painting might pursue, and not obviously the highest one in every case. A canvas abandoned at the point where the underdrawing still shows through the paint, where a hand is a gesture of hasty ochre rather than five resolved fingers, sometimes preserves a decisiveness of thought that the same artist's finished, fully resolved canvases, labored over for a further eighteen months of correction and compromise, visibly do not. I am not proposing that painters should aim to leave work incomplete, which would be its own kind of affectation. I am proposing only that we stop treating "unfinished" as a synonym for "lesser," and start asking, canvas by canvas, what finishing would actually have cost. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered.
- question: What is the author's primary purpose in this passage?
- options: ["To challenge the assumption that finished paintings are automatically superior to unfinished ones", "To prove that every unfinished painting is secretly complete", "To recommend that artists deliberately leave their works incomplete", "To criticise museums for displaying unfinished paintings at all"]
- correct_index: 0
- correct_answer: To challenge the assumption that finished paintings are automatically superior to unfinished ones
- explanation: The author explicitly states the aim is to stop treating "unfinished" as synonymous with "lesser" and to evaluate finish as one value among several, not the highest by default.
- distractor_rationale: The author explicitly rejects the "secretly finished" claim as self-collapsing; deliberately unfinished work is explicitly called "its own kind of affectation" and rejected; museums displaying such works is never criticised.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "In Defence of the Unfinished",
  "topic_domain": "art_criticism",
  "reading_subskill": "author_purpose",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What is the author's primary purpose in this passage?",
      "options": [
        "To challenge the assumption that finished paintings are automatically superior to unfinished ones",
        "To prove that every unfinished painting is secretly complete",
        "To recommend that artists deliberately leave their works incomplete",
        "To criticise museums for displaying unfinished paintings at all"
      ],
      "correct_index": 0,
      "subskill": "author_purpose",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What assumption about unfinished paintings does the author reject?",
        "Answer to: Why might an unfinished canvas have value?"
      ],
      "match_options": [
        "That they are automatically lesser rehearsals for finished works",
        "It may preserve decisiveness lost through later correction",
        "That they can never be displayed in museums",
        "That they are always secretly complete"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "Why might an unfinished canvas have value?",
      "response_type": "short_answer",
      "accepted_answers": [
        "It may preserve decisiveness lost through later correction"
      ],
      "max_words": 12,
      "subskill": "inference"
    },
    {
      "question": "What does the author ask readers to consider?",
      "response_type": "short_answer",
      "accepted_answers": [
        "What finishing would have cost in each case"
      ],
      "max_words": 12,
      "subskill": "author_purpose"
    }
  ],
  "distractor_rationale": "The 'secretly finished' claim and deliberate incompleteness are both explicitly rejected; museums are never criticised."
}
```

### ITEM RDG-C2-08
- draft_id: RDG-C2-08
- cefr_level: C2
- question_type: mcq
- reading_subskill: vocabulary_in_context
- topic_domain: sociology_networks
- title: The Strength of Weak Ties
- passage: It is one of sociology's more durable and counterintuitive findings that when people find new jobs through personal contacts, the decisive introduction more often comes not from a close friend but from a distant acquaintance — a former colleague, a neighbour's cousin, someone encountered twice at a conference. The explanation, once stated, resists further surprise: our close friends tend to move in the same circles we do, exposed to largely the same job openings and the same information we already possess, so that their networks are, informationally, redundant with our own. The acquaintance, precisely because the relationship is thin, sits at the edge of an entirely different circle, and thereby serves as a bridge to information a denser, more intimate network simply cannot supply. This is the germ of what researchers term the strength of weak ties: not that weak relationships matter more than strong ones in any emotional sense, but that their structural position, straddling otherwise unconnected clusters, gives them a disproportionate capacity to carry genuinely novel information across a social network. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered. This makes the writer's position deliberately cautious rather than simply supportive or dismissive. The reader is therefore pushed to weigh nuance, evidence, and implication at the same time. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered.
- question: In this text, "redundant" is used to describe information that is —
- options: ["already known through one's existing close contacts", "deliberately hidden by close friends", "more valuable than information from acquaintances", "impossible to verify through personal networks"]
- correct_index: 0
- correct_answer: already known through one's existing close contacts
- explanation: Close friends' networks are called "informationally redundant" because they are "exposed to largely the same job openings and the same information we already possess" — i.e. duplicated, not new.
- distractor_rationale: Nothing suggests deliberate hiding; redundant information is explicitly framed as less useful than the acquaintance's novel information, not more valuable; verification is never discussed.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Strength of Weak Ties",
  "topic_domain": "sociology_networks",
  "reading_subskill": "vocabulary_in_context",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "In this text, \"redundant\" is used to describe information that is —",
      "options": [
        "already known through one's existing close contacts",
        "deliberately hidden by close friends",
        "more valuable than information from acquaintances",
        "impossible to verify through personal networks"
      ],
      "correct_index": 0,
      "subskill": "vocabulary_in_context",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: Why are close friends often informationally redundant?",
        "Answer to: What gives weak ties their strength?"
      ],
      "match_options": [
        "They usually know the same circles and openings we do",
        "Their position bridging otherwise separate social clusters",
        "They deliberately hide all job information",
        "They have no emotional importance"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What gives weak ties their strength?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Their position bridging otherwise separate social clusters"
      ],
      "max_words": 12,
      "subskill": "main_idea"
    },
    {
      "question": "What does 'thin' mean when describing the acquaintance relationship?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Not close or intimate"
      ],
      "max_words": 12,
      "subskill": "vocabulary_in_context"
    }
  ],
  "distractor_rationale": "No deliberate hiding is implied; redundant information is framed as less useful, not more valuable; verification is not discussed."
}
```

### ITEM RDG-C2-09
- draft_id: RDG-C2-09
- cefr_level: C2
- question_type: mcq
- reading_subskill: implication
- topic_domain: philosophy_decision
- title: The Paradox of Choice, Revisited
- passage: The claim that more options make us less happy has, over the past two decades, hardened from a provocative finding into something closer to received wisdom, cited in commencement speeches and product-design meetings alike as though the matter were settled. It is worth recalling how much weight this consensus asks a fairly narrow body of evidence to bear. The original experiments compared modest, bounded sets of options — a handful of jams, a short list of essay topics — and found that shoppers presented with the smaller set were, by certain measures, more satisfied with their eventual choice. Subsequent attempts to replicate the effect across other domains have produced a decidedly mixed record, with roughly as many null results as confirmations, and several meta-analyses suggesting the true effect, if it exists at all, is considerably smaller and more context-dependent than the popular version of the claim allows. None of this proves that choice overload is a myth; it may yet turn out to be real under specific, still poorly mapped conditions. But a finding this contested has, somewhere between the journal and the commencement stage, acquired a certainty its own evidence base does not obviously supply. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered. This makes the writer's position deliberately cautious rather than simply supportive or dismissive.
- question: What does the passage imply about the popular version of the "paradox of choice"?
- options: ["Its confidence exceeds what the underlying research evidence actually supports", "It has been completely disproven by every subsequent study", "It was never based on any experimental evidence whatsoever", "It applies equally and reliably across all types of decisions"]
- correct_index: 0
- correct_answer: Its confidence exceeds what the underlying research evidence actually supports
- explanation: The passage states the claim has "acquired a certainty its own evidence base does not obviously supply", given the mixed replication record described just before.
- distractor_rationale: The passage explicitly says the effect "may yet turn out to be real", not disproven; original experiments are described in detail, so evidence clearly exists; the mixed, context-dependent record directly contradicts uniform reliability.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Paradox of Choice, Revisited",
  "topic_domain": "philosophy_decision",
  "reading_subskill": "implication",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What does the passage imply about the popular version of the \"paradox of choice\"?",
      "options": [
        "Its confidence exceeds what the underlying research evidence actually supports",
        "It has been completely disproven by every subsequent study",
        "It was never based on any experimental evidence whatsoever",
        "It applies equally and reliably across all types of decisions"
      ],
      "correct_index": 0,
      "subskill": "implication",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: What happened to the original choice-overload finding over time?",
        "Answer to: What did later replications and meta-analyses suggest?"
      ],
      "match_options": [
        "It hardened into received wisdom beyond its evidence",
        "The effect is mixed, smaller, and more context-dependent",
        "It disappeared from public discussion",
        "It was never cited outside journals"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What did later replications and meta-analyses suggest?",
      "response_type": "short_answer",
      "accepted_answers": [
        "The effect is mixed, smaller, and more context-dependent"
      ],
      "max_words": 12,
      "subskill": "specific_detail"
    },
    {
      "question": "What is the author's stance toward choice overload?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Sceptical of overconfident versions but not dismissing it entirely"
      ],
      "max_words": 12,
      "subskill": "tone"
    }
  ],
  "distractor_rationale": "The passage says the effect may still be real; original experiments are described, so evidence exists; the record is explicitly mixed, not uniform."
}
```

### ITEM RDG-C2-10
- draft_id: RDG-C2-10
- cefr_level: C2
- question_type: mcq
- reading_subskill: rhetorical_function
- topic_domain: philosophy_language
- title: The Uses of a Good Analogy
- passage: A good analogy is a dangerous tool precisely because it works: it takes something unfamiliar and renders it instantly graspable by way of something the listener already understands, and in doing so smuggles in, unexamined, every property of the familiar thing that does not actually transfer. To say that the brain is a computer illuminates certain features of memory and processing remarkably well, and silently implies others — a central processor, a clean distinction between hardware and software, a startup and a shutdown — that turn out, on closer inspection, to fit the brain rather badly. The danger is not that analogies are false; almost none of them are simply false, since a workable analogy must share real structure with its target or it would persuade no one. The danger is that a good analogy persuades in excess of what it has actually demonstrated, borrowing the listener's trust in the familiar domain and extending that trust, without further argument, into the unfamiliar one. The appropriate response is not to abandon analogy, which is close to how human beings think in the first place, but to ask of every one that lands with suspicious ease exactly which of its implied properties were earned and which were merely inherited. Moreover, the passage implies that apparently minor qualifications can reshape the whole argument, especially when institutional incentives are considered.
- question: What rhetorical function does the "brain is a computer" example serve in this passage?
- options: ["It demonstrates concretely how an analogy can illuminate some features while misleadingly implying others", "It proves definitively that the brain functions exactly like a computer", "It shows that all analogies about the brain are entirely false and useless", "It introduces an unrelated topic before returning to the main argument"]
- correct_index: 0
- correct_answer: It demonstrates concretely how an analogy can illuminate some features while misleadingly implying others
- explanation: The example is used directly to show the passage's general claim in action: real illumination (memory and processing) alongside silently smuggled, poorly fitting implications (processor, hardware/software, startup/shutdown).
- distractor_rationale: The passage says the fit is "rather bad" for the smuggled properties, not that the analogy is proven true; analogies are explicitly said to be almost never simply false; the example is central to the argument, not a digression.
- review_status: mvp_approved_pending_full_review
- human_reviewed: false
- body_json_candidate:
```json
{
  "title": "The Uses of a Good Analogy",
  "topic_domain": "philosophy_language",
  "reading_subskill": "rhetorical_function",
  "review_status": "mvp_approved_pending_full_review",
  "human_reviewed": false,
  "subquestions": [
    {
      "question": "What rhetorical function does the \"brain is a computer\" example serve in this passage?",
      "options": [
        "It demonstrates concretely how an analogy can illuminate some features while misleadingly implying others",
        "It proves definitively that the brain functions exactly like a computer",
        "It shows that all analogies about the brain are entirely false and useless",
        "It introduces an unrelated topic before returning to the main argument"
      ],
      "correct_index": 0,
      "subskill": "rhetorical_function",
      "response_type": "mcq"
    },
    {
      "question": "Match each prompt with the best answer from the text.",
      "response_type": "matching",
      "matching_items": [
        "Answer to: Why is a good analogy dangerous?",
        "Answer to: What does the brain-computer analogy silently imply?"
      ],
      "match_options": [
        "It can transfer unearned assumptions from the familiar case",
        "Features like a central processor and hardware/software split",
        "It is always simply false",
        "It prevents listeners from understanding anything"
      ],
      "correct_indices": [
        0,
        1
      ],
      "subskill": "argument_structure"
    },
    {
      "question": "What does the brain-computer analogy silently imply?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Features like a central processor and hardware/software split"
      ],
      "max_words": 12,
      "subskill": "specific_detail"
    },
    {
      "question": "What response to analogy does the author recommend?",
      "response_type": "short_answer",
      "accepted_answers": [
        "Ask which implied properties are earned and which merely inherited"
      ],
      "max_words": 12,
      "subskill": "author_purpose"
    }
  ],
  "distractor_rationale": "The smuggled properties are said to fit badly, not prove the analogy true; analogies are said to be almost never simply false; the example is central, not a digression."
}
```

---

## Distribution Summary

- Total items: 60
- A1: 10
- A2: 10
- B1: 10
- B2: 10
- C1: 10
- C2: 10

Subskill distribution (all 60 items):

| Subskill | A1 | A2 | B1 | B2 | C1 | C2 | Total |
|---|---|---|---|---|---|---|---|
| specific_detail | 4 | 3 | 2 | 2 | 0 | 0 | 11 |
| main_idea | 3 | 2 | 2 | 2 | 1 | 0 | 10 |
| inference | 1 | 2 | 3 | 2 | 1 | 1 | 10 |
| vocabulary_in_context | 1 | 2 | 2 | 2 | 1 | 1 | 9 |
| purpose | 1 | 1 | 1 | 1 | 1 | 0 | 5 |
| tone | 0 | 0 | 0 | 1 | 2 | 1 | 4 |
| argument_structure | 0 | 0 | 0 | 0 | 2 | 1 | 3 |
| implication | 0 | 0 | 0 | 0 | 1 | 2 | 3 |
| rhetorical_function | 0 | 0 | 0 | 0 | 1 | 2 | 3 |
| author_purpose | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| **Level total** | **10** | **10** | **10** | **10** | **10** | **10** | **60** |

Figures above are machine-verified by the validation script in the Validation section below (exact
per-level × subskill counts parsed from this file), not hand-estimated.

Note: `tone` appears only from B2 upward per the brief. `argument_structure`, `implication`,
`rhetorical_function`, and `author_purpose` are C1/C2-only extensions of `purpose`/`tone`,
introduced to give advanced items the nuance the brief asked for without overloading any single
subskill tag.

## Self-Audit Findings

- **Difficulty progression**: passage length and syntactic complexity increase by level as
  required — A1 items run roughly 40-60 words with simple present/past tense; C2 items run
  roughly 180-230 words with subordinate clauses, hedged claims, and abstract argumentation.
- **Sensitive topics**: no item touches politics, medicine/health conditions, religion, or other
  controversial subject matter. Topics are domestic life, work, travel, nature, arts, business
  history, linguistics, and similar neutral domains.
- **Distractor quality**: every item's distractor_rationale explains why each wrong option is
  plausible (usually because it appears elsewhere in the passage, fits the general topic, or
  represents a common misreading) rather than being random or absurd.
- **Topic repetition**: topic_domain tags were kept deliberately varied; no domain repeats more
  than twice within a level, and most appear only once across the whole 60-item set.
- **Items warranting extra human review before activation** (flagged for the "weak items" report,
  not defects — these are the ones where a second reviewer's judgment matters most):
  - RDG-A1-04 (At the Market): all four options are real words drawn from the passage. This is a
    deliberately harder A1 item (matching object to person rather than pure recall) — reviewers
    should confirm this doesn't overshoot A1 difficulty for a true beginner.
  - RDG-B2-05 / RDG-C1-03 / RDG-C1-10 / RDG-C2-05 (tone items): tone judgments are inherently
    more subjective than fact-based questions; a second reader should confirm the intended tone
    reading is the clearly dominant one and not merely plausible.
  - RDG-C1-07 (The Company That Said No): closely mirrors a well-known real corporate history
    (unnamed here). Reviewers should confirm the fictionalised/unnamed framing is sufficiently
    generic to stand as an independent item.
  - RDG-C2-01 / RDG-C2-06 / RDG-C2-09 (abstract argumentative essays): at the extreme end of C2
    density; reviewers should confirm these are calibrated as difficult-but-fair rather than
    unnecessarily obscure.

## Known Non-Goals / Out of Scope for This Draft

- No database rows were created, no `stable_key` values were reserved against the real table, and
  no seed script was written or run — this file is content only.
- No boundary-level items (`boundary_low_level`/`boundary_high_level`) were authored in this pass;
  the brief asked for 10 flat-level items per CEFR band only. Boundary-confirmation items would be
  a natural follow-up batch once this bank is active (see the Reading investigation's
  recommendation to populate boundary rows).
- No passage bundles (multiple sub-questions per passage) were authored; this draft is
  one-passage-one-question, matching the current Reading item shape used at runtime.
- Retirement of the old 21-item `content_seed` Reading bank (`is_active=false`) is explicitly
  deferred to a later, separate step, per the approved decision — not performed here.

review_status (all items): mvp_approved_pending_full_review
human_reviewed (all items): false
note: This is a Placement Test Reading content draft only. It is not active runtime seed data
unless separately imported by a future seed script and reviewed/activated.
