from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.schemas.common import ORMModel


class GrievanceCreate(BaseModel):
    category: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=10, max_length=10_000)
    location: str = Field(min_length=3, max_length=240)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "GrievanceCreate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be supplied together.")
        return self


class GrievanceUpdate(BaseModel):
    status: Literal["received", "in_progress", "resolved", "rejected"] | None = None
    category: str | None = Field(default=None, min_length=2, max_length=80)
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    department: str | None = Field(default=None, max_length=180)
    resolution_note: str | None = Field(default=None, max_length=5_000)
    review_status: Literal["pending", "reviewed"] | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "GrievanceUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one grievance field must be provided.")
        for field in ("status", "category", "priority", "review_status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        if self.review_status == "pending" and {"status", "category", "priority"}.intersection(self.model_fields_set):
            raise ValueError("Decision updates cannot be left pending human review.")
        return self


class GrievanceRead(ORMModel):
    id: str
    reference_number: str
    user_id: str
    category: str
    title: str
    description: str
    location: str
    latitude: float | None
    longitude: float | None
    evidence_content_type: str | None
    ai_suggested_category: str | None
    ai_suggested_priority: str | None
    ai_confidence: float | None
    ai_rationale: str | None
    ai_triage_status: str
    priority: str
    review_status: str
    reviewed_by_id: str | None
    reviewed_at: datetime | None
    status: str
    department: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def has_evidence(self) -> bool:
        return self.evidence_content_type is not None


class GrievancePublicRead(BaseModel):
    reference_number: str
    category: str
    title: str
    location: str
    status: str
    department: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime
