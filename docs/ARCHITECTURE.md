# Architecture

## System architecture

```mermaid
flowchart LR
    User([Reviewer]) --> UI["React frontend<br/>Vite, Tailwind, Recharts"]
    UI -->|"/api requests"| API["FastAPI<br/>routes/"]
    API --> Pipeline["pipeline.py<br/>runs the steps in the background"]
    API --> DB[("SQLite<br/>SQLAlchemy")]
    API --> Docs["documents/<br/>read files, export reports"]
    Pipeline --> DB
    Pipeline --> NLP["nlp/<br/>one file per step"]
    NLP --> Ollama["Ollama<br/>local Qwen model"]
    NLP --> Sk["scikit-learn<br/>saved classifier"]
    NLP --> ST["sentence-transformers<br/>all-MiniLM-L6-v2"]
    NLP --> Spacy["spaCy<br/>en_core_web_sm"]
```

Everything runs on one computer. The frontend starts an analysis and then asks for progress every
2 seconds, so the page stays usable while the model works.

## NLP pipeline

```mermaid
flowchart TD
    Input["Pasted text, TXT, PDF or DOCX"] --> Clean["Read and clean the text"]
    Clean --> Split["spaCy: split into sentences<br/>and keep their positions"]
    Split --> LLM1["Local LLM: extract atomic<br/>requirements as JSON"]
    LLM1 --> Check{"Passes checks against<br/>the source sentence?"}
    Check -->|"No, first try"| Retry["Ask again and<br/>explain the problem"]
    Retry --> LLM1
    Check -->|"No, second try"| Warn["Save nothing and<br/>show a warning"]
    Check -->|Yes| Save["Save with a link<br/>to the source"]
    Save --> Classify["TF-IDF and Logistic Regression:<br/>type and category"]
    Classify --> Dup["Embeddings and cosine similarity:<br/>potential duplicates"]
    Dup --> Quality["Rules and local LLM:<br/>quality issues and contradictions"]
    Quality --> Stories["Local LLM and checks:<br/>draft user stories"]
    Stories --> Review["Human review:<br/>edit, accept, reject"]
    Warn --> Review
    Review --> Export["PDF and DOCX report"]
```

## Classifier training

```mermaid
flowchart LR
    Data["PROMISE_exp<br/>968 unique rows"] --> Split["Fixed 80/20 split"]
    Split -->|"774 rows"| Train
    Extra["Hand-written examples<br/>100 rows"] --> Train["train.py"]
    Train --> Saved["Vectorizer and two models"]
    Split -->|"194 rows, never trained on"| Eval["evaluate.py"]
    Saved --> Eval
    Eval --> Metrics["metrics.json"]
    Metrics --> Page["Classifier results page"]
```

## Design decisions

| Decision | Reason |
|---|---|
| NLP files do not touch the database | Each step can be read and tested alone |
| Plain functions instead of classes | Easier to read and explain |
| Rule-based checks after the LLM | The LLM can make things up, so its answers need checking |
| No fallback when the LLM fails | A failure must be visible, so results are never faked |
| Embeddings run on the CPU | The GPU has only 4 GB, and Ollama needs it |
| Tailwind 3 rather than 4 | Version 3 is pure JavaScript, which avoids extra native binaries that Windows Smart App Control might block |
| Bind the frontend and API to this computer | There is no login, so it should not be exposed on a network |
