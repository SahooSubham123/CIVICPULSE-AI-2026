from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ServicePlanRequest(BaseModel):
    service_name: str = Field(min_length=3, max_length=180)
    jurisdiction: str = Field(min_length=2, max_length=120)


class ServicePlanResponse(BaseModel):
    task_id: str
    service_name: str
    status: str
    steps: list[str]
    requires_user_confirmation: bool = True
    warning: str
    created_at: datetime


class ServiceExecutionRequest(BaseModel):
    user_confirmed: bool


class ServiceExecutionResponse(BaseModel):
    task_id: str
    status: str
    message: str


class ServiceAssistanceRequest(BaseModel):
    service_request: str = Field(min_length=5, max_length=2_000)
    jurisdiction: str = Field(min_length=2, max_length=120)

    @field_validator("service_request")
    @classmethod
    def reject_credentials(cls, value: str) -> str:
        if re.search(
            r"\b(password|passcode|credential|one.time.(code|password)|otp|pin|cvv|security answer|secret)\b",
            value,
            re.I,
        ):
            raise ValueError("Do not enter government portal credentials or verification codes.")
        return value


class ServiceFormField(BaseModel):
    field_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    label: str = Field(min_length=2, max_length=120)
    help_text: str = Field(default="", max_length=400)
    field_type: Literal["text", "date", "number", "textarea"] = "text"
    required: bool = False

    @field_validator("field_id", "label", "help_text")
    @classmethod
    def reject_portal_credentials(cls, value: str) -> str:
        if re.search(
            r"\b(password|passcode|credential|otp|one.time.(code|password)|pin|cvv|security.(code|answer)|secret)\b",
            value,
            re.I,
        ):
            raise ValueError("Government portal credentials must not be collected.")
        return value


class ServiceAssistanceAssessment(BaseModel):
    service_name: str = Field(min_length=3, max_length=180)
    procedure: list[str] = Field(min_length=1, max_length=12)
    required_documents: list[str] = Field(default_factory=list, max_length=20)
    form_fields: list[ServiceFormField] = Field(default_factory=list, max_length=30)
    tracking_guidance: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def reject_credential_content(self) -> "ServiceAssistanceAssessment":
        generated_text = " ".join(
            [
                self.service_name,
                *self.procedure,
                *self.required_documents,
                *self.tracking_guidance,
                *(
                    text
                    for field in self.form_fields
                    for text in (field.field_id, field.label, field.help_text)
                ),
            ]
        )
        if re.search(
            r"\b(password|passcode|credential|one.time.(code|password)|otp|pin|cvv|security answer|secret)\b",
            generated_text,
            re.I,
        ):
            raise ValueError("Service guidance must not contain portal credentials or verification codes.")
        return self


class SupportedPortal(BaseModel):
    portal_id: str
    url: str


class ServiceAssistanceResponse(ServiceAssistanceAssessment):
    task_id: str
    supported_portals: list[SupportedPortal]
    privacy_notice: str = (
        "Application details are held only in this page's temporary form state and are not saved to the service plan. "
        "Never provide a government portal password, PIN, or one-time code."
    )
    safety_notice: str = (
        "Guidance and document lists are suggestions. Verify requirements on the official portal. "
        "Review every form field and legal declaration yourself; this assistant will not submit an application."
    )
    tracking_notice: str = (
        "Tracking guidance explains how to check progress yourself on the official portal. "
        "This assistant does not look up application status or request tracking credentials."
    )


class PortalInspectionRequest(BaseModel):
    path: str = Field(default="", max_length=2_000)


class PortalInspectionResponse(BaseModel):
    portal_id: str
    requested_url: str
    final_url: str
    title: str
    excerpt: str
    navigation_status: Literal["ok", "http_error", "page_error", "challenge"]
    http_status: int | None
    warnings: list[str]
