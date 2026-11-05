"""Database tables. See docs/DATABASE.md for the diagram.

Review status values:
  requirement / story : pending, accepted, rejected
  duplicate pair      : pending, confirmed, dismissed
  quality issue       : pending, accepted, dismissed
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from .database import Base
from .config import SIMILARITY_THRESHOLD


def now():
    return datetime.now(timezone.utc)


def project_fk():
    return Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    similarity_threshold = Column(Float, default=SIMILARITY_THRESHOLD)
    # Progress of the analysis, read by the frontend while it waits.
    analysis_status = Column(String(20), default="idle")  # idle, running, done, failed
    analysis_step = Column(String(100), default="")
    analysis_progress = Column(Integer, default=0)
    analysis_error = Column(Text, default="")
    analysis_warnings = Column(JSON, default=list)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Document(Base):
    """Original source text, stored exactly as received."""
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    project_id = project_fk()
    filename = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now)


class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(Integer, primary_key=True)
    project_id = project_fk()
    text = Column(Text, nullable=False)
    actor = Column(String(200), default="")
    origin = Column(String(20), default="ai")  # ai or human
    status = Column(String(20), default="pending")
    edited = Column(Boolean, default=False)
    original_text = Column(Text, default="")  # the AI wording, kept after edits

    # Link back to the source. Empty for requirements added by hand.
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    source_sentence = Column(Text, default="")
    source_start = Column(Integer, nullable=True)
    source_end = Column(Integer, nullable=True)

    # Current classification, which a reviewer may change.
    req_type = Column(String(20), nullable=True)  # functional or non_functional
    nfr_category = Column(String(30), nullable=True)
    type_overridden = Column(Boolean, default=False)
    # What the classifier originally said, kept for comparison.
    predicted_type = Column(String(20), nullable=True)
    predicted_category = Column(String(30), nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=now)


class DuplicatePair(Base):
    __tablename__ = "duplicate_pairs"
    id = Column(Integer, primary_key=True)
    project_id = project_fk()
    req_a_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    req_b_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    reason = Column(Text, default="")
    status = Column(String(20), default="pending")


class QualityIssue(Base):
    __tablename__ = "quality_issues"
    id = Column(Integer, primary_key=True)
    project_id = project_fk()
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    # Only used for contradictions, which involve two requirements.
    other_requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=True)
    kind = Column(String(40), nullable=False)
    evidence = Column(Text, default="")  # the words in the requirement that caused this issue
    message = Column(Text, nullable=False)
    question = Column(Text, default="")  # inferred question, never stated by the client
    origin = Column(String(10), default="rule")  # rule or llm
    status = Column(String(20), default="pending")


class UserStory(Base):
    __tablename__ = "user_stories"
    id = Column(Integer, primary_key=True)
    project_id = project_fk()
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, unique=True)
    role = Column(String(200), nullable=False)
    role_inferred = Column(Boolean, default=False)  # True if the source did not name this role
    feature = Column(Text, nullable=False)
    benefit = Column(Text, nullable=False)
    acceptance_criteria = Column(JSON, default=list)
    status = Column(String(20), default="pending")
    edited = Column(Boolean, default=False)


class Setting(Base):
    """Small key/value table. Currently it stores the chosen Ollama model."""
    __tablename__ = "settings"
    key = Column(String(50), primary_key=True)
    value = Column(Text, default="")
