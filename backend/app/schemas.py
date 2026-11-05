"""Pydantic models that check the data sent to the API."""
from typing import Literal

from pydantic import BaseModel, Field

ReqType = Literal["functional", "non_functional"]
Category = Literal["performance", "security", "usability", "reliability", "maintainability", "other"]
ReviewStatus = Literal["pending", "accepted", "rejected"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    similarity_threshold: float | None = Field(default=None, ge=0.3, le=1.0)


class TextDocument(BaseModel):
    text: str = Field(min_length=1)
    filename: str = "Pasted text"


class AnalyzeRequest(BaseModel):
    steps: list[Literal["extract", "classify", "duplicates", "quality", "stories"]] | None = None


class RequirementCreate(BaseModel):
    text: str = Field(min_length=3)
    req_type: ReqType | None = None
    nfr_category: Category | None = None


class RequirementUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=3)
    req_type: ReqType | None = None
    nfr_category: Category | None = None
    status: ReviewStatus | None = None


class DuplicateUpdate(BaseModel):
    status: Literal["pending", "confirmed", "dismissed"]


class ManualDuplicate(BaseModel):
    req_a_id: int
    req_b_id: int


class IssueUpdate(BaseModel):
    status: Literal["pending", "accepted", "dismissed"]


class StoryUpdate(BaseModel):
    role: str | None = Field(default=None, min_length=1)
    feature: str | None = Field(default=None, min_length=1)
    benefit: str | None = Field(default=None, min_length=1)
    acceptance_criteria: list[str] | None = None
    status: ReviewStatus | None = None


class ModelChoice(BaseModel):
    model: str = ""


class PredictRequest(BaseModel):
    text: str = Field(min_length=1)
