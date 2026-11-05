"""API for Ollama status, model choice, classifier results and report export."""
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..config import OLLAMA_URL, SAVED_MODELS_DIR
from ..database import get_db
from ..documents.docx_export import render_docx
from ..documents.pdf_export import render_pdf
from ..documents.report import build_report
from ..models import Project, Setting
from ..nlp import llm
from ..nlp.classification import ModelNotTrained, classify
from ..schemas import ModelChoice, PredictRequest
from .helpers import get_or_404

router = APIRouter(prefix="/api")

RECOMMENDED_MODEL = "qwen3:4b-instruct-2507-q4_K_M"


@router.get("/system/status")
def system_status():
    """Reports the real state of Ollama, so the UI can show honest setup instructions."""
    status = {
        "ollama_url": OLLAMA_URL, "recommended_model": RECOMMENDED_MODEL, "selected_model": llm.selected_model,
        "ollama_running": False, "models": [], "active_model": None, "message": "",
        "classifier_trained": (SAVED_MODELS_DIR / "type_model.joblib").exists(),
    }
    try:
        status["models"] = llm.list_models()
        status["ollama_running"] = True
        status["active_model"] = llm.choose_model(status["models"])
        if status["active_model"] is None:
            status["message"] = f"No suitable model is installed. Run: ollama pull {llm.selected_model or RECOMMENDED_MODEL}"
    except llm.LLMUnavailable as error:
        status["message"] = str(error)
    return status


@router.put("/system/model")
def choose_model(data: ModelChoice, db: Session = Depends(get_db)):
    llm.selected_model = data.model
    db.merge(Setting(key="ollama_model", value=data.model))
    db.commit()
    return {"selected_model": data.model}


@router.get("/model/metrics")
def model_metrics():
    path = SAVED_MODELS_DIR / "metrics.json"
    if not path.exists():
        raise HTTPException(404, "No results yet. Run: python backend/training/evaluate.py")
    return json.loads(path.read_text())


@router.post("/model/predict")
def predict(data: PredictRequest):
    try:
        return classify([data.text])[0]
    except ModelNotTrained as error:
        raise HTTPException(503, str(error)) from error


@router.get("/projects/{project_id}/export/{file_format}")
def export_report(project_id: int, file_format: str, db: Session = Depends(get_db)):
    project = get_or_404(db, Project, project_id)
    report = build_report(db, project)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", project.name).strip("_") or "project"
    if file_format == "pdf":
        content, media_type = render_pdf(report), "application/pdf"
    elif file_format == "docx":
        content = render_docx(report)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(404, "Use pdf or docx.")
    headers = {"Content-Disposition": f'attachment; filename="{safe_name}_requirements.{file_format}"'}
    return Response(content, media_type=media_type, headers=headers)
