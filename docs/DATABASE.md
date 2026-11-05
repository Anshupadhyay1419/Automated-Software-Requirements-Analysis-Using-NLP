# Database schema

The database is one SQLite file, created automatically at `backend/data/app.db`. Tables are defined
in `backend/app/models.py`.

```mermaid
erDiagram
    PROJECTS ||--o{ DOCUMENTS : has
    PROJECTS ||--o{ REQUIREMENTS : has
    PROJECTS ||--o{ DUPLICATE_PAIRS : has
    PROJECTS ||--o{ QUALITY_ISSUES : has
    PROJECTS ||--o{ USER_STORIES : has
    DOCUMENTS ||--o{ REQUIREMENTS : "source of"
    REQUIREMENTS ||--o{ DUPLICATE_PAIRS : "compared in"
    REQUIREMENTS ||--o{ QUALITY_ISSUES : "has"
    REQUIREMENTS ||--o| USER_STORIES : "drafted as"

    PROJECTS {
        int id PK
        string name
        text description
        float similarity_threshold
        string analysis_status
        string analysis_step
        int analysis_progress
        text analysis_error
        json analysis_warnings
    }
    DOCUMENTS {
        int id PK
        int project_id FK
        string filename
        text text
    }
    REQUIREMENTS {
        int id PK
        int project_id FK
        int document_id FK
        text text
        text original_text
        string actor
        string origin
        string status
        bool edited
        text source_sentence
        int source_start
        int source_end
        string req_type
        string nfr_category
        bool type_overridden
        string predicted_type
        string predicted_category
        float confidence
    }
    DUPLICATE_PAIRS {
        int id PK
        int project_id FK
        int req_a_id FK
        int req_b_id FK
        float score
        text reason
        string status
    }
    QUALITY_ISSUES {
        int id PK
        int project_id FK
        int requirement_id FK
        int other_requirement_id FK
        string kind
        text evidence
        text message
        text question
        string origin
        string status
    }
    USER_STORIES {
        int id PK
        int project_id FK
        int requirement_id FK
        string role
        bool role_inferred
        text feature
        text benefit
        json acceptance_criteria
        string status
        bool edited
    }
    SETTINGS {
        string key PK
        text value
    }
```

## Why some columns exist

| Column | Why |
|---|---|
| `original_text` | Keeps the AI wording after a person edits `text` |
| `source_sentence`, `source_start`, `source_end` | Link each requirement to its exact place in the source |
| `predicted_type`, `predicted_category`, `confidence` | Keep the classifier's answer, even after a person changes it |
| `type_overridden` | Stops a re-run from replacing a person's classification |
| `origin` | Shows whether an item came from AI, a rule, the LLM or a person |
| `status` | Separates reviewed content from unreviewed AI suggestions |
| `evidence` | The words in the requirement that caused a quality issue |

## Deleting

Foreign keys use `ON DELETE CASCADE`. Deleting a project removes everything inside it, and deleting
a document removes the requirements extracted from it. This is tested in `backend/tests/test_api.py`.
