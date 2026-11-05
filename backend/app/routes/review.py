"""API for human review: requirements, duplicates, quality issues and user stories."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..documents.readers import clean_text
from ..models import DuplicatePair, Project, QualityIssue, Requirement, UserStory
from ..nlp.duplicates import similarity_matrix
from ..nlp.user_stories import story_sentence
from ..pipeline import recheck_after_edit
from ..schemas import (DuplicateUpdate, IssueUpdate, ManualDuplicate, RequirementCreate,
                       RequirementUpdate, StoryUpdate)
from .helpers import get_or_404, to_dict

router = APIRouter(prefix="/api")


def requirement_texts(db, project_id) -> dict:
    """Maps requirement id to its row, for showing text next to issues and duplicates."""
    return {row.id: row for row in db.query(Requirement).filter(Requirement.project_id == project_id)}


def is_rejected(requirements, requirement_id):
    row = requirements.get(requirement_id)
    return row is None or row.status == "rejected"


# ----- Requirements -----

@router.get("/projects/{project_id}/requirements")
def list_requirements(project_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Project, project_id)
    rows = db.query(Requirement).filter(Requirement.project_id == project_id).order_by(Requirement.id)
    return [to_dict(row) for row in rows]


@router.post("/projects/{project_id}/requirements", status_code=201)
def add_requirement(project_id: int, data: RequirementCreate, db: Session = Depends(get_db)):
    """A person adds a requirement. It has no AI prediction and counts as accepted."""
    get_or_404(db, Project, project_id)
    row = Requirement(
        project_id=project_id, text=clean_text(data.text), origin="human", status="accepted",
        req_type=data.req_type, nfr_category=data.nfr_category, type_overridden=data.req_type is not None,
    )
    db.add(row)
    db.commit()
    return to_dict(row)


@router.patch("/requirements/{requirement_id}")
def update_requirement(requirement_id: int, data: RequirementUpdate, db: Session = Depends(get_db)):
    row = get_or_404(db, Requirement, requirement_id)
    changes = data.model_dump(exclude_unset=True)

    if changes.get("text") and clean_text(changes["text"]) != row.text:
        row.text = clean_text(changes["text"])
        row.edited = True
        recheck_after_edit(db, row)

    if "req_type" in changes or "nfr_category" in changes:
        row.type_overridden = True
        row.req_type = changes.get("req_type", row.req_type)
        row.nfr_category = changes.get("nfr_category", row.nfr_category)
        if row.req_type == "functional":
            row.nfr_category = None

    if changes.get("status"):
        row.status = changes["status"]
    db.commit()
    return to_dict(row)


# ----- Duplicates -----

@router.get("/projects/{project_id}/duplicates")
def list_duplicates(project_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Project, project_id)
    requirements = requirement_texts(db, project_id)
    pairs = (db.query(DuplicatePair).filter(DuplicatePair.project_id == project_id)
             .order_by(DuplicatePair.score.desc()))
    return [
        {**to_dict(pair), "text_a": requirements[pair.req_a_id].text, "text_b": requirements[pair.req_b_id].text}
        for pair in pairs
        if not is_rejected(requirements, pair.req_a_id) and not is_rejected(requirements, pair.req_b_id)
    ]


@router.post("/projects/{project_id}/duplicates", status_code=201)
def mark_duplicate(project_id: int, data: ManualDuplicate, db: Session = Depends(get_db)):
    """A person marks two requirements as duplicates. Neither is merged or deleted."""
    if data.req_a_id == data.req_b_id:
        raise HTTPException(422, "Choose two different requirements.")
    a = get_or_404(db, Requirement, data.req_a_id)
    b = get_or_404(db, Requirement, data.req_b_id)
    if a.project_id != project_id or b.project_id != project_id:
        raise HTTPException(422, "Both requirements must belong to this project.")
    first, second = sorted([a.id, b.id])
    pair = db.query(DuplicatePair).filter_by(req_a_id=first, req_b_id=second).first()
    if pair:
        pair.status = "confirmed"
    else:
        score = round(float(similarity_matrix([a.text, b.text])[0][1]), 3)
        pair = DuplicatePair(project_id=project_id, req_a_id=first, req_b_id=second, score=score,
                             reason="Marked by a reviewer.", status="confirmed")
        db.add(pair)
    db.commit()
    return to_dict(pair)


@router.patch("/duplicates/{pair_id}")
def update_duplicate(pair_id: int, data: DuplicateUpdate, db: Session = Depends(get_db)):
    pair = get_or_404(db, DuplicatePair, pair_id)
    pair.status = data.status
    db.commit()
    return to_dict(pair)


# ----- Quality issues -----

@router.get("/projects/{project_id}/issues")
def list_issues(project_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Project, project_id)
    requirements = requirement_texts(db, project_id)
    issues = db.query(QualityIssue).filter(QualityIssue.project_id == project_id).order_by(QualityIssue.id)
    return [
        {**to_dict(issue), "requirement_text": requirements[issue.requirement_id].text,
         "other_requirement_text": requirements[issue.other_requirement_id].text if issue.other_requirement_id else None}
        for issue in issues if not is_rejected(requirements, issue.requirement_id)
    ]


@router.patch("/issues/{issue_id}")
def update_issue(issue_id: int, data: IssueUpdate, db: Session = Depends(get_db)):
    issue = get_or_404(db, QualityIssue, issue_id)
    issue.status = data.status
    db.commit()
    return to_dict(issue)


# ----- User stories -----

@router.get("/projects/{project_id}/stories")
def list_stories(project_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Project, project_id)
    requirements = requirement_texts(db, project_id)
    stories = db.query(UserStory).filter(UserStory.project_id == project_id).order_by(UserStory.id)
    return [
        {**to_dict(story), "requirement_text": requirements[story.requirement_id].text,
         "sentence": story_sentence(story.role, story.feature, story.benefit)}
        for story in stories if not is_rejected(requirements, story.requirement_id)
    ]


@router.patch("/stories/{story_id}")
def update_story(story_id: int, data: StoryUpdate, db: Session = Depends(get_db)):
    story = get_or_404(db, UserStory, story_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("role", "feature", "benefit", "acceptance_criteria"):
        if changes.get(field) is not None and changes[field] != getattr(story, field):
            setattr(story, field, changes[field])
            story.edited = True
            if field == "role":
                story.role_inferred = False  # a person has now confirmed the role
    if changes.get("status"):
        story.status = changes["status"]
    db.commit()
    return to_dict(story)
