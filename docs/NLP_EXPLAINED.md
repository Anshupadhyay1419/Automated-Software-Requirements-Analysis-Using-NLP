# How the system works, in plain language

Use this to understand the code and explain it to anyone. Each NLP step is one short file in
`backend/app/nlp/`.

## The whole idea in one minute

Clients write requirements in messy sentences. The system does five things:

1. **Extract:** split messy sentences into small, single-idea requirements.
2. **Classify:** label each one functional (what the system does) or non-functional (how well it
   does it).
3. **Find duplicates:** show pairs that seem to mean the same thing.
4. **Check quality:** point out vague wording and possible contradictions.
5. **Draft user stories:** write "As a..., I want..., so that..." drafts.

A person then reviews everything and exports a report.

**The main design idea:** an LLM is powerful but can make things up. So the LLM never has the last
word. Simple code checks its answers, and a person approves the results.

## Step 1: `preprocess.py` (spaCy helpers)

**What:** splits text into sentences and gives simple language facts.

**How:** spaCy understands English grammar. We use it to find:

| Function | Input | Output |
|---|---|---|
| `split_into_sentences` | "Users log in. Admins export." | Two sentences, with their positions in the text |
| `content_words` | "Users placed orders" | `{user, place, order}` (base forms, without common words) |
| `has_negation` | "must not delete" | `True` |
| `numbers_in` | "within 2 seconds" | `{"2"}` |
| `subject_of` | "The website should be fast" | "the website" |

**Why positions?** So clicking a requirement can highlight its exact original sentence.

## Step 2: `llm.py` (talking to the local model)

**What:** sends a prompt to Qwen through Ollama and returns a checked answer.

**How:** three settings make the answers dependable:

- `format`: forces the reply to follow our JSON shape.
- `temperature: 0`: makes the model choose its most likely answer each time.
- `num_predict`: limits the reply length.

Pydantic then checks the JSON. If Ollama is off or the reply is invalid, the code **raises an
error**. It never makes up an answer, so the user always sees a failure.

## Step 3: `extraction.py` (requirement extraction)

**What:** "Users should register and log in." becomes "Users can register." and "Users can log in."

**How:**

1. Send the sentence and the previous sentence to the LLM. The previous sentence lets it work out
   what "they" means.
2. Check the answer with `find_problems`.
3. If a check fails, ask again and say what was wrong.
4. If it fails twice, save nothing and show a warning.

**The checks in `find_problems`:**

| Check | What it catches |
|---|---|
| New words | The LLM adds a feature that the client never mentioned |
| Missing words | The LLM drops part of the sentence, such as "at any time" |
| Numbers | "2 seconds" is lost, or a new number appears |
| Negation | "must not delete" becomes "must delete" |
| Conditions | "if payment fails" is lost |
| Empty answer | A sentence with "must" or "shall" returned nothing |

**Example to show someone:** the input "Guests can browse products but must not place orders."
gives two requirements, and the "not" stays in the right one.

## Step 4: `classification.py` (TF-IDF and Logistic Regression)

**What:** labels each requirement. No LLM is used here.

**TF-IDF** turns text into numbers. A word gets a high score if it is common in this sentence but
rare across all sentences. "encrypted" says more than "the". We also use word pairs, such as
"response time".

**Logistic Regression** learns a weight for each word. Words like "encrypted" and "seconds" push
towards non-functional. The weights are added up and converted into a probability, which is the
confidence shown in the app.

There are **two models**: the first decides functional or non-functional, and the second picks the
category for non-functional requirements.

**Training data:**

- PROMISE_exp: 969 real requirements from 47 projects. 80% is for training and 20% for testing.
- 100 extra hand-written examples, for training only. PROMISE is formal ("The system shall..."),
  while the LLM writes short sentences ("Users can log in.").

**Files:** `training/dataset.py` makes the split, `train.py` trains, and `evaluate.py` measures.

**If asked why accuracy is only 74.9% on unseen projects:** this is the honest test. Every project
uses different words, and TF-IDF only knows words it has seen. It cannot understand that "sign in"
and "log in" mean the same thing.

## Step 5: `duplicates.py` (sentence embeddings)

**What:** finds pairs with similar meaning, even when the words differ.

**How:**

1. A small neural network (`all-MiniLM-L6-v2`) turns each sentence into 384 numbers, called an
   embedding. Sentences with similar meaning get similar numbers.
2. **Cosine similarity** measures how close two embeddings are. 1.0 means the same meaning, and
   values near 0 mean unrelated.
3. Pairs at or above the threshold (default 0.60) are shown to a person.

**Why not merge them automatically?** "Users can log in" and "Users can log out" score 0.80 but
are different features. The system also warns when only one sentence is negated or the numbers
differ.

**TF-IDF or embeddings?** TF-IDF compares words, so it would miss "sign in" and "log in".
Embeddings compare meaning.

## Step 6: `quality.py` (quality analysis)

**What:** finds vague or incomplete requirements. It has two parts.

**Rules** are predictable and easy to explain:

| Rule | Example | Result |
|---|---|---|
| Vague words | "very fast" | "What response-time target should the website meet?" |
| Unclear actor | "It should look modern." | "What does 'It' refer to?" |
| Passive voice | "Reports are generated" | "Who or what should perform this action?" |
| Unspecified behaviour | "handle returns, etc." | "What exactly should be included?" |
| Missing number | Reliability goal with no target | "What measurable target...?" |
| Contradiction | "2 seconds" and "5 seconds" for the same subject | "Which is correct?" |

**The LLM** can notice things that rules miss, such as "track their deliveries" not saying what is
shown. Its answers are filtered: the quoted evidence must really appear in the requirement.

Each result shows whether it came from a rule or the LLM. **Questions are inferred by the tool,
and the client did not state them.** This cannot find every problem.

## Step 7: `user_stories.py` (user stories)

**What:** drafts "As a customer, I want to place an order, so that I can purchase products."

**How:** the LLM writes a draft, then checks remove unsafe content. An acceptance criterion is
dropped if it adds a new number, adds a new "not", or is mostly new words. If the role was not in
the requirement, the story is marked "Role inferred".

The benefit is always a suggestion, because clients rarely state it. Stories stay labelled as
drafts until a person accepts them.

## Step 8: `pipeline.py` (connecting the steps)

**What:** runs the steps in order and saves the results.

The `nlp/` files know nothing about the database, and `pipeline.py` has no NLP logic. This makes
each part easy to test and explain.

**Running it twice is safe:** anything a person accepted, rejected or edited is kept.

**Failures are honest:**

| Situation | What happens |
|---|---|
| Ollama is off during extraction | The analysis stops with a clear error, and earlier results stay |
| One sentence fails the checks | It becomes a warning, and the rest continue |
| The LLM stops during quality checks | Rule results stay, and a warning explains what is missing |

## Other components

| Component | Location | Job |
|---|---|---|
| API | `backend/app/routes/` | The URLs that the website calls |
| Database | `models.py`, `database.py` | Stores everything in one SQLite file |
| Request checks | `schemas.py` | Pydantic rejects invalid data |
| File reading | `documents/readers.py` | Gets text from TXT, PDF and DOCX |
| Reports | `documents/report.py` | Collects the content once, for both report formats |
| PDF and Word | `pdf_export.py`, `docx_export.py` | Draw the report in each format |
| Frontend | `frontend/src/` | React pages, one for each sidebar item |
| Tests | `backend/tests/` | Check each part automatically |

## Questions you may be asked

**Why use an LLM and also a classifier?** The brief asks for a classic ML classifier, and it is
fast, cheap and measurable. The LLM handles splitting sentences, which needs real language
understanding.

**Why run it locally?** Client requirements can be confidential. It also needs no API keys or fees.

**How do you stop the LLM from making things up?** With JSON output, temperature 0, a clear prompt,
rule-based checks against the source, a retry, and human review. This reduces the risk but does not
remove it.

**What is macro F1?** F1 combines precision and recall. Macro means calculating it for each class
and averaging, so a small class counts as much as a large one.

**What is a held-out test set?** Data the model never sees during training. Testing on training data
would give a falsely high score.

**Why two accuracy numbers?** With a random split (85.6%), sentences from one project can be in both
training and test data. Testing on entirely unseen projects (74.9%) is harder and more realistic.

**What would you improve next?** More real training data in everyday language, a transformer
classifier, labelled data to measure extraction quality properly, and a larger set of pairs for
choosing the duplicate threshold.
