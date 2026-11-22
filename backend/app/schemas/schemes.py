from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator

from app.schemas.common import Timestamped


class EligibilityCriterion(BaseModel):
    field: Literal["age", "annual_income", "state", "occupation", "household_size"]
    operator: Literal["eq", "lt", "lte", "gt", "gte", "in"] = "eq"
    value: str | int | list[str] | list[int]
    label: str = Field(min_length=2, max_length=180)

    @model_validator(mode="after")
    def validate_field_operator(self) -> "EligibilityCriterion":
        numeric_field = self.field in {"age", "annual_income", "household_size"}
        if not numeric_field and self.operator not in {"eq", "in"}:
            raise ValueError("Text eligibility fields support only eq or in operators")
        values = self.value if isinstance(self.value, list) else [self.value]
        if numeric_field and any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise ValueError("Numeric eligibility fields require integer values")
        if not numeric_field and any(not isinstance(value, str) for value in values):
            raise ValueError("Text eligibility fields require string values")
        if self.operator == "in" and not isinstance(self.value, list):
            raise ValueError("The in operator requires a list of values")
        if self.operator != "in" and isinstance(self.value, list):
            raise ValueError("Only the in operator accepts a list of values")
        return self


class SchemeCreate(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    department: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=10, max_length=10_000)
    benefit: str = Field(min_length=2, max_length=240)
    eligibility_criteria: list[EligibilityCriterion] = Field(default_factory=list, max_length=30)
    application_url: AnyHttpUrl | None = None
    state: str | None = Field(default=None, max_length=100)


class SchemeRead(Timestamped):
    id: str
    name: str
    department: str
    description: str
    benefit: str
    eligibility_criteria: list[EligibilityCriterion]
    application_url: str | None
    state: str | None
    is_active: bool


class EligibilityRequest(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    annual_income: int | None = Field(default=None, ge=0, le=1_000_000_000)
    state: str | None = Field(default=None, max_length=100)
    occupation: str | None = Field(default=None, max_length=120)
    household_size: int | None = Field(default=None, ge=1, le=30)


class EligibilityResult(BaseModel):
    scheme_id: str
    scheme_name: str
    assessment: str
    matched_criteria: list[str]
    missing_information: list[str]
    disclaimer: str
