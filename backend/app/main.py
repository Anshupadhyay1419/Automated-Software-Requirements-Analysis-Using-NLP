"""Starts the API. Run from the project root:

    python -m uvicorn app.main:app --app-dir backend --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import update

from .database import SessionLocal, create_tables
from .models import Project, Setting
from .nlp import llm
from .routes import projects, review, system


def prepare_database():
    create_tables()
    db = SessionLocal()
    try:
        # A restart stops any running analysis, so do not show it as running forever.
        db.execute(update(Project).where(Project.analysis_status == "running").values(
            analysis_status="failed",
            analysis_error="The server restarted during this analysis. Earlier results were kept. Please run it again.",
        ))
        db.commit()
        # A model chosen on the Settings page overrides the .env value.
        saved = db.get(Setting, "ollama_model")
        if saved is not None:
            llm.selected_model = saved.value
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app):
    prepare_database()
    yield


app = FastAPI(title="Automated Software Requirements Analysis", lifespan=lifespan)
app.include_router(projects.router)
app.include_router(review.router)
app.include_router(system.router)


@app.exception_handler(Exception)
async def unexpected_error(_request, error):
    """Return a readable message instead of a bare 500 error."""
    return JSONResponse(status_code=500, content={"detail": f"Unexpected server error: {error}"})
