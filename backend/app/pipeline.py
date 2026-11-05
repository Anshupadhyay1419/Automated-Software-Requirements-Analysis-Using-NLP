"""Runs the NLP steps in order and saves results to the database.

The files in nlp/ know nothing about the database, and this file contains no NLP logic.

Re-running is safe: anything a person has reviewed or edited is kept.
"""
from .database import SessionLocal
from .models import Document, DuplicatePair, Project, QualityIssue, Requirement, UserStory
from .nlp import quality
from .nlp.classification import ModelNotTrained, classify
from .nlp.duplicates import review_reason, similar_pairs, similarity_matrix
from .nlp.extraction import ExtractionFailed, extract_requirements
from .nlp.llm import LLMBadOutput, LLMUnavailable
from .nlp.preprocess import split_into_sentences
from .nlp.user_stories import generate_story

STEPS = ["extract", "classify", "duplicates", "quality", "stories"]
STEP_LABELS = {
    "extract": "Extracting requirements",
    "classify": "Classifying requirements",
    "duplicates": "Finding potential duplicates",
    "quality": "Checking requirement quality",
    "stories": "Drafting user stories",
}
LLM_PAIR_MIN_SCORE = 0.5  # pairs this similar are worth asking the LLM about
RULE_PAIR_MIN_SCORE = 0.6  # pairs this similar are checked by the contradiction rule
MAX_LLM_PAIRS = 20  # limits the extra waiting time on large projects


def active_requirements(db, project_id):
    """Every requirement except the rejected ones."""
    return (db.query(Requirement)
            .filter(Requirement.project_id == project_id, Requirement.status != "rejected")
            .order_by(Requirement.id).all())


# ----- Step 1: extraction -----

def extract_step(db, project, warnings, report):
    documents = db.query(Document).filter(Document.project_id == project.id).all()
    jobs = [(doc, split_into_sentences(doc.text)) for doc in documents]
    total = sum(len(sentences) for _, sentences in jobs) or 1
    done = 0
    for doc, sentences in jobs:
        for index, sentence in enumerate(sentences):
            context = sentences[index - 1]["text"] if index else ""
            try:
                items = extract_requirements(sentence["text"], context)
                save_extracted(db, project, doc, sentence, items)
            except ExtractionFailed as error:
                warnings.append({
                    "step": "extract",
                    "message": f"Not extracted, please review by hand. {error}",
                    "source": sentence["text"],
                })
            done += 1
            report(done / total)


def save_extracted(db, project, doc, sentence, items):
    """Update one sentence's requirements. Unchanged rows stay, so their reviews stay too."""
    existing = db.query(Requirement).filter(
        Requirement.document_id == doc.id, Requirement.source_start == sentence["start"]
    ).all()
    by_text = {row.original_text.strip().lower(): row for row in existing}
    new_texts = {item.text.strip().lower() for item in items}

    for key, row in by_text.items():
        untouched = row.status == "pending" and not row.edited
        if key not in new_texts and untouched:
            db.delete(row)

    for item in items:
        if item.text.strip().lower() not in by_text:
            db.add(Requirement(
                project_id=project.id, text=item.text, original_text=item.text, actor=item.actor,
                document_id=doc.id, source_sentence=sentence["text"],
                source_start=sentence["start"], source_end=sentence["end"],
            ))
    db.commit()


# ----- Step 2: classification -----

def classify_step(db, project, warnings, report):
    requirements = active_requirements(db, project.id)
    for row, result in zip(requirements, classify([row.text for row in requirements])):
        row.predicted_type = result["type"]
        row.predicted_category = result["category"]
        row.confidence = result["confidence"]
        if not row.type_overridden:  # never replace a person's decision
            row.req_type = result["type"]
            row.nfr_category = result["category"]
    db.commit()


# ----- Step 3: duplicate detection -----

def duplicates_step(db, project, warnings, report):
    requirements = active_requirements(db, project.id)
    texts = [row.text for row in requirements]
    found = {}
    for i, j, score in similar_pairs(texts, project.similarity_threshold):
        found[(requirements[i].id, requirements[j].id)] = (score, review_reason(texts[i], texts[j], score))

    # Reviewed pairs stay as they are. Pending pairs are refreshed.
    for pair in db.query(DuplicatePair).filter(DuplicatePair.project_id == project.id).all():
        key = (pair.req_a_id, pair.req_b_id)
        if pair.status != "pending":
            found.pop(key, None)
        elif key in found:
            pair.score, pair.reason = found.pop(key)
        else:
            db.delete(pair)
    for (a_id, b_id), (score, reason) in found.items():
        db.add(DuplicatePair(project_id=project.id, req_a_id=a_id, req_b_id=b_id, score=score, reason=reason))
    db.commit()


# ----- Step 4: quality analysis -----

def quality_step(db, project, warnings, report):
    requirements = active_requirements(db, project.id)
    db.query(QualityIssue).filter(
        QualityIssue.project_id == project.id, QualityIssue.status == "pending"
    ).delete()
    db.commit()
    reviewed = {
        (issue.requirement_id, issue.kind, issue.evidence.lower())
        for issue in db.query(QualityIssue).filter(QualityIssue.project_id == project.id)
    }

    def add_issue(row, found, origin, other_id=None):
        key = (row.id, found["kind"], found["evidence"].lower())
        if key not in reviewed:
            reviewed.add(key)
            db.add(QualityIssue(project_id=project.id, requirement_id=row.id,
                                other_requirement_id=other_id, origin=origin, **found))

    llm_working = True
    for index, row in enumerate(requirements):
        rule_issues = quality.check_rules(row.text, row.nfr_category)
        for found in rule_issues:
            add_issue(row, found, "rule")
        if llm_working:
            try:
                rule_kinds = {found["kind"] for found in rule_issues}
                for found in quality.llm_review(row.text):
                    if found["kind"] not in rule_kinds:  # avoid repeating what a rule found
                        add_issue(row, found, "llm")
            except LLMUnavailable as error:
                llm_working = False
                warnings.append({"step": "quality", "message": f"LLM review stopped, so the remaining results come from rules only. {error}", "source": ""})
            except LLMBadOutput as error:
                warnings.append({"step": "quality", "message": f"LLM review was skipped for this requirement. {error}", "source": row.text})
        db.commit()
        report((index + 1) / len(requirements) * 0.7)

    if len(requirements) >= 2:
        check_contradictions(requirements, add_issue, llm_working, warnings)
    db.commit()


def check_contradictions(requirements, add_issue, llm_working, warnings):
    """Rules handle very similar pairs. The LLM checks the next most similar pairs."""
    scores = similarity_matrix([row.text for row in requirements])
    pairs = sorted(
        ((float(scores[i][j]), i, j) for i in range(len(requirements)) for j in range(i + 1, len(requirements))
         if scores[i][j] >= LLM_PAIR_MIN_SCORE),
        reverse=True,
    )
    llm_calls = 0
    for score, i, j in pairs:
        a, b = requirements[i], requirements[j]
        reason = quality.rule_contradiction(a.text, b.text) if score >= RULE_PAIR_MIN_SCORE else None
        origin = "rule"
        if reason is None and llm_working and llm_calls < MAX_LLM_PAIRS:
            llm_calls += 1
            origin = "llm"
            try:
                reason = quality.llm_contradiction(a.text, b.text)
            except LLMUnavailable as error:
                llm_working = False
                warnings.append({"step": "quality", "message": f"The LLM contradiction check stopped early. {error}", "source": ""})
            except LLMBadOutput as error:  # one bad reply should not stop the other pairs
                warnings.append({"step": "quality", "message": f"This pair was not checked by the LLM. {error}", "source": f"{a.text} / {b.text}"})
        if reason:
            add_issue(a, {
                "kind": "potential_contradiction", "evidence": b.text, "message": reason,
                "question": "Which of these two requirements is correct, or when does each apply?",
            }, origin, other_id=b.id)


# ----- Step 5: user stories -----

def stories_step(db, project, warnings, report):
    have_story = {story.requirement_id for story in db.query(UserStory).filter(UserStory.project_id == project.id)}
    todo = [row for row in active_requirements(db, project.id)
            if row.req_type == "functional" and row.id not in have_story]
    for index, row in enumerate(todo):
        try:
            db.add(UserStory(project_id=project.id, requirement_id=row.id, **generate_story(row.text)))
            db.commit()
        except ExtractionFailed as error:
            warnings.append({"step": "stories", "message": f"No story was drafted. {error}", "source": row.text})
        report((index + 1) / len(todo))


STEP_FUNCTIONS = {
    "extract": extract_step,
    "classify": classify_step,
    "duplicates": duplicates_step,
    "quality": quality_step,
    "stories": stories_step,
}


def run_analysis(project_id: int, steps: list[str]):
    """Runs in the background. The frontend reads progress from the project row."""
    db = SessionLocal()
    project = db.get(Project, project_id)
    # Keep warnings from steps that are not being re-run.
    warnings = [item for item in (project.analysis_warnings or []) if item["step"] not in steps]
    try:
        for number, step in enumerate(steps):
            def report(fraction, number=number, step=step):
                project.analysis_step = STEP_LABELS[step]
                project.analysis_progress = int((number + fraction) / len(steps) * 100)
                db.commit()

            report(0)
            STEP_FUNCTIONS[step](db, project, warnings, report)
        project.analysis_status = "done"
        project.analysis_error = ""
        project.analysis_progress = 100
    except (LLMUnavailable, ModelNotTrained) as error:
        db.rollback()
        project.analysis_status = "failed"
        project.analysis_error = str(error)
    except Exception as error:  # for example, Windows blocking a library from loading
        db.rollback()
        project.analysis_status = "failed"
        project.analysis_error = f"Analysis stopped unexpectedly: {error}. Earlier results were kept. Please try again."
    finally:
        project.analysis_warnings = warnings
        db.commit()
        db.close()


def recheck_after_edit(db, requirement):
    """After a text edit, refresh this requirement's rule issues and remove its pending story.
    The LLM is not called, so saving an edit stays instant. Re-run analysis for a full check."""
    db.query(QualityIssue).filter(
        QualityIssue.requirement_id == requirement.id, QualityIssue.status == "pending"
    ).delete()
    db.query(UserStory).filter(
        UserStory.requirement_id == requirement.id, UserStory.status == "pending"
    ).delete()
    for found in quality.check_rules(requirement.text, requirement.nfr_category):
        db.add(QualityIssue(project_id=requirement.project_id, requirement_id=requirement.id, origin="rule", **found))
