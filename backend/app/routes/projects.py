"""API for projects, source documents and starting an analysis."""
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import update
from sqlalchemy.orm import Session

from ..config import MAX_UPLOAD_BYTES, SAMPLES_DIR
from ..database import get_db
from ..documents.readers import UnsupportedDocument, clean_text, read_document
from ..models import Document, DuplicatePair, Project, QualityIssue, Requirement, UserStory
from ..pipeline import STEPS, run_analysis
from ..schemas import AnalyzeRequest, ProjectCreate, ProjectUpdate, TextDocument
from .helpers import get_or_404, to_dict

router = APIRouter(prefix="/api")


def project_stats(db: Session, project_id: int) -> dict:
    """The numbers shown on the dashboard. Rejected requirements are not counted as active."""
    requirements = db.query(Requirement).filter(Requirement.project_id == project_id).all()
    active = {row.id: row for row in requirements if row.status != "rejected"}
    both_active = lambda pair: pair.req_a_id in active and pair.req_b_id in active
    pairs = [pair for pair in db.query(DuplicatePair).filter(DuplicatePair.project_id == project_id)
             if both_active(pair) and pair.status != "dismissed"]
    issues = [issue for issue in db.query(QualityIssue).filter(QualityIssue.project_id == project_id)
              if issue.requirement_id in active and issue.status != "dismissed"]
    stories = [story for story in db.query(UserStory).filter(UserStory.project_id == project_id)
               if story.requirement_id in active and story.status != "rejected"]

    def count_by(values):
        counts = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return counts

    return {
        "total": len(active),
        "functional": sum(row.req_type == "functional" for row in active.values()),
        "non_functional": sum(row.req_type == "non_functional" for row in active.values()),
        "duplicates": len(pairs),
        "warnings": len(issues),
        "reviewed": sum(row.status != "pending" for row in requirements),
        "all_requirements": len(requirements),
        "accepted": sum(row.status == "accepted" for row in requirements),
        "rejected": sum(row.status == "rejected" for row in requirements),
        "stories": len(stories),
        "stories_accepted": sum(story.status == "accepted" for story in stories),
        "categories": count_by(row.nfr_category for row in active.values()
                               if row.req_type == "non_functional" and row.nfr_category),
        "issue_kinds": count_by(issue.kind for issue in issues),
    }


def project_summary(db, project):
    return {**to_dict(project), "stats": project_stats(db, project.id)}


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    return [project_summary(db, project) for project in projects]


@router.post("/projects", status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=data.name.strip(), description=data.description)
    db.add(project)
    db.commit()
    return project_summary(db, project)


@router.post("/projects/sample", status_code=201)
def create_sample_project(db: Session = Depends(get_db)):
    text = (SAMPLES_DIR / "sample_requirements.txt").read_text(encoding="utf-8")
    project = Project(name="ShopEasy Online Store (sample)",
                      description="Built-in example with duplicates, vague statements and contradictions.")
    db.add(project)
    db.flush()
    db.add(Document(project_id=project.id, filename="sample_requirements.txt", text=clean_text(text)))
    db.commit()
    return project_summary(db, project)


@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    return project_summary(db, get_or_404(db, Project, project_id))


@router.patch("/projects/{project_id}")
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    project = get_or_404(db, Project, project_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(project, field, value)
    db.commit()
    return project_summary(db, project)


def refuse_while_running(project):
    if project.analysis_status == "running":
        raise HTTPException(409, "An analysis is running for this project. Please wait for it to finish.")


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = get_or_404(db, Project, project_id)
    refuse_while_running(project)
    db.delete(project)
    db.commit()


# ----- Source documents -----

@router.get("/projects/{project_id}/documents")
def list_documents(project_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Project, project_id)
    documents = db.query(Document).filter(Document.project_id == project_id).order_by(Document.id)
    return [to_dict(document) for document in documents]


@router.post("/projects/{project_id}/documents/text", status_code=201)
def add_text(project_id: int, data: TextDocument, db: Session = Depends(get_db)):
    get_or_404(db, Project, project_id)
    text = clean_text(data.text)
    if not text:
        raise HTTPException(422, "The text is empty.")
    document = Document(project_id=project_id, filename=data.filename, text=text)
    db.add(document)
    db.commit()
    return to_dict(document)


@router.post("/projects/{project_id}/documents/upload", status_code=201)
async def upload_document(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    get_or_404(db, Project, project_id)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The file is larger than the 10 MB limit.")
    try:
        text = read_document(file.filename or "", content)
    except UnsupportedDocument as error:
        raise HTTPException(422, str(error)) from error
    document = Document(project_id=project_id, filename=file.filename, text=text)
    db.add(document)
    db.commit()
    return to_dict(document)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = get_or_404(db, Document, document_id)
    refuse_while_running(get_or_404(db, Project, document.project_id))
    db.delete(document)
    db.commit()


# ----- Analysis -----

@router.post("/projects/{project_id}/analyze", status_code=202)
def start_analysis(project_id: int, data: AnalyzeRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    project = get_or_404(db, Project, project_id)
    has_documents = db.query(Document).filter(Document.project_id == project_id).count() > 0
    has_requirements = db.query(Requirement).filter(Requirement.project_id == project_id).count() > 0
    if not has_documents and not has_requirements:
        raise HTTPException(422, "Add some requirement text before starting the analysis.")

    # Only one analysis per project. This update succeeds only if none is running.
    claimed = db.execute(
        update(Project)
        .where(Project.id == project_id, Project.analysis_status != "running")
        .values(analysis_status="running", analysis_progress=0, analysis_step="Starting", analysis_error="")
    ).rowcount
    db.commit()
    if not claimed:
        refuse_while_running(project)
        raise HTTPException(409, "An analysis is already running.")

    background.add_task(run_analysis, project_id, data.steps or STEPS)
    db.refresh(project)
    return to_dict(project)
