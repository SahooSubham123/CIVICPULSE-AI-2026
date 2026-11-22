from datetime import datetime

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class ClaimCheckRequest(BaseModel):
    claim: str = Field(min_length=8, max_length=8_000)
    context: str | None = Field(default=None, max_length=4_000)
    context_url: AnyHttpUrl | None = None
    source_urls: list[AnyHttpUrl] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def reject_duplicate_sources(self) -> "ClaimCheckRequest":
        urls = [str(url) for url in self.source_urls]
        if self.context_url:
            urls.append(str(self.context_url))
        if len(urls) != len(set(urls)):
            raise ValueError("Source URLs must be unique.")
        return self


class MediaAnalysisRequest(BaseModel):
    media_url: AnyHttpUrl
    context: str | None = Field(default=None, max_length=4_000)


class VerificationEvidence(BaseModel):
    kind: Literal[
        "trusted_source_excerpt",
        "transcript_excerpt",
        "visual_observation",
        "video_frame_observation",
    ]
    description: str = Field(min_length=1, max_length=2_000)
    source_url: AnyHttpUrl | None = None
    timestamp_seconds: float | None = Field(default=None, ge=0)


class VerificationRead(BaseModel):
    id: str
    subject_type: str
    provider: str
    assessment: str
    confidence: float | None
    analysis: str
    sources: list[str]
    evidence: list[VerificationEvidence] = Field(default_factory=list)
    transcript: str | None = None
    limitations: list[str] = Field(default_factory=list)
    confidence_note: str = (
        "AI confidence is an uncalibrated model estimate, not a probability or a measure of truth."
    )
    created_at: datetime
    disclaimer: str


class FrameObservation(BaseModel):
    frame_index: int = Field(ge=0)
    description: str = Field(min_length=1, max_length=1_000)


class AIAnalysis(BaseModel):
    assessment: str = Field(pattern="^(supported|contradicted|inconclusive|needs_human_review|possible_manipulation_indicators)$")
    confidence: float | None = Field(default=None, ge=0, le=1)
    analysis: str = Field(min_length=1, max_length=12_000)
    sources: list[str] = Field(default_factory=list, max_length=20)
    observations: list[str] = Field(default_factory=list, max_length=20)
    frame_observations: list[FrameObservation] = Field(default_factory=list, max_length=12)
