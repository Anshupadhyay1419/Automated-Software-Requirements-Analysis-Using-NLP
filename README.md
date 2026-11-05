# Automated Software Requirements Analysis Using NLP

A local web application, called **ReqLens** in the interface. It turns informal client text into
structured software requirements, finds quality problems, drafts user stories, and exports a
report. A person reviews everything, and nothing is sent to the cloud.

**Input:** "Users should register, log in, search products, and place orders."

**Output:** four separate requirements, each classified, linked to the source sentence, checked
for quality, and with a draft user story.

## What it does

| Feature | How it works |
|---|---|
| Sentence splitting | spaCy |
| Requirement extraction | Local Qwen model through Ollama, with checks on every answer |
| Functional / non-functional classification | TF-IDF and Logistic Regression (no LLM) |
| Duplicate detection | sentence-transformers and cosine similarity |
| Quality analysis | Fixed rules and the local LLM |
| User stories | Local LLM, with checks that remove invented details |
| Human review | Edit, reclassify, accept, reject, mark duplicates |
| Export | PDF (ReportLab) and DOCX (python-docx) |

## Setup

You need Python 3.10, Node.js and [Ollama](https://ollama.com). These commands are for PowerShell.

```powershell
cd D:\bennett\nlp\Project

# Python packages (skip any you already have)
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Local LLM
ollama pull qwen3:4b-instruct-2507-q4_K_M

# Frontend packages
cd frontend
npm install
cd ..
```

The trained classifier is already in `backend/saved_models/`. To train and measure it again:

```powershell
python backend/training/train.py
python backend/training/evaluate.py
```

The first analysis downloads the small embedding model (`all-MiniLM-L6-v2`), so it needs internet
once. After that, everything runs offline.

## Run the application

Open two terminals. Ollama must also be running.

```powershell
# Terminal 1: backend
cd D:\bennett\nlp\Project
python -m uvicorn app.main:app --app-dir backend --port 8000
```

```powershell
# Terminal 2: frontend
cd D:\bennett\nlp\Project\frontend
npm run dev
```

Open **http://localhost:5173**, select **Sample project**, then **Run analysis**. The sample takes
about 4 minutes on an RTX 3050 with 4 GB of memory. The first request is slower because the model
has to load.

## Run the tests

```powershell
cd D:\bennett\nlp\Project
python -m pytest                       # regular tests (no Ollama needed)
python -m pytest -m llm -o addopts=""  # tests with the real Ollama model
```

## Measured results

### Classifier

Measured by `backend/training/evaluate.py` and saved in `backend/saved_models/metrics.json`.

| Test | Rows | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Type: PROMISE_exp held-out 20% | 194 | 85.6% | 85.9% | 85.1% | 85.3% |
| Type: unseen projects, 5-fold | 968 | 74.9% | 77.5% | 73.4% | 73.4% |
| Type: hand-written app-style test | 55 | 100% | 100% | 100% | 100% |
| Category: PROMISE_exp held-out 20% | 105 | 82.9% | 76.3% | 76.4% | 76.1% |

Precision, recall and F1 are macro averages.

How to read these numbers:

- **Quote the unseen-projects result as the realistic score (74.9%).** A new client's wording is
  new to the model. The 85.6% result is higher partly because sentences from the same project can
  appear in both training and test data.
- **Do not present the 100% as an achievement.** The same author wrote that test set and the
  matching training examples, in the same style. It only shows that the model handles this style.
- Adding the app-style examples lowered PROMISE accuracy slightly (87.1% to 85.6%), but stopped
  sentences like "Users can register." from being mislabelled. On the app-style test, accuracy
  went from 87.3% to 100%, with the caveat above.

### Duplicate threshold

Chosen from 20 hand-labelled pairs: 10 real duplicates and 10 similar but different pairs.

| Threshold | Duplicates caught | False alarms |
|---:|---:|---:|
| 0.50 | 10/10 | 9/10 |
| **0.60 (default)** | **10/10** | **5/10** |
| 0.70 | 6/10 | 5/10 |
| 0.85 | 4/10 | 0/10 |

Cosine similarity alone cannot separate these cleanly: "log in" and "log out" score 0.80, while
"sign in" and "log in" with different actors score 0.64. This is why a person decides every pair.
The list is small, so treat 0.60 as a starting point. You can change it on the Duplicates page.

## Known limitations

- **The classifier makes visible mistakes.** On the sample, "The website should be very fast." is
  labelled usability, not performance, and "Reports are generated every week." is labelled
  security. Classifications are editable for this reason.
- **The LLM can still make mistakes that the checks miss.** For example, an acceptance criterion
  can add a detail using mostly the requirement's own words. All drafts need human review.
- **Quality analysis is not complete.** It cannot find every missing requirement or contradiction.
- **Sentences can be refused.** If an answer fails the checks twice, nothing is saved and the
  sentence appears as a warning, so it can be added by hand.
- **A hung Ollama call occurred once in testing.** It blocked later calls until
  `ollama stop <model>` was run. The cause was not confirmed and it did not recur. A reply length
  limit was added, and the app now reports a timeout with this command instead of waiting forever.
- **PDF export uses a Latin font,** so scripts such as Hindi will not display correctly in PDF.
  Scanned PDFs cannot be read, because there is no OCR.
- **Editing a requirement refreshes only its rule-based issues.** Run the analysis again to refresh
  its duplicates and LLM checks.
- **This is a single-user local tool.** It has no login, by design. Do not expose it to a network.

## Troubleshooting

| Problem | Fix |
|---|---|
| `DLL load failed ... Application Control policy` | Windows Smart App Control blocked a library. This happened once with spaCy and passed when retried. Run the command or the analysis again. |
| "Cannot reach Ollama" | Start Ollama with `ollama serve`, or open the Ollama app. |
| "Ollama did not reply within 180 seconds" | Run `ollama stop qwen3:4b-instruct-2507-q4_K_M`, then run the analysis again. |
| "Classifier not found" | Run `python backend/training/train.py`. |
| The analysis is very slow | Close other programs that use the GPU. Part of the model runs on the CPU if GPU memory is full. |

## Project layout

```text
backend/
  app/
    nlp/            one short file for each NLP step (start here)
    documents/      read TXT, PDF, DOCX and export reports
    routes/         the API
    pipeline.py     runs the NLP steps and saves the results
    models.py       database tables
  training/         dataset, train.py, evaluate.py
  saved_models/     trained model and measured results
  tests/
frontend/           React interface
samples/            sample input as TXT, PDF and DOCX
docs/               explanations and diagrams
```

## Documentation

- [docs/NLP_EXPLAINED.md](docs/NLP_EXPLAINED.md): every component in plain language
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): architecture and NLP pipeline diagrams
- [docs/DATABASE.md](docs/DATABASE.md): database schema
- [backend/training/data/README.md](backend/training/data/README.md): dataset sources and limits
