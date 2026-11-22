from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.dependencies import Database, get_current_user
from app.models import Scheme
from app.schemas.schemes import EligibilityCriterion, EligibilityRequest, EligibilityResult

router = APIRouter(prefix="/eligibility", tags=["Eligibility checking"])


def criterion_matches(criterion: EligibilityCriterion, actual: str | int) -> bool:
    expected = criterion.value
    if criterion.operator == "in":
        if not isinstance(expected, list):
            return False
        return str(actual).casefold() in {str(value).casefold() for value in expected}
    if criterion.field in {"state", "occupation"} or criterion.operator == "eq":
        return str(actual).casefold() == str(expected).casefold()
    if isinstance(expected, list):
        return False
    try:
        actual_number = float(actual)
        expected_number = float(expected)
    except (TypeError, ValueError):
        return False
    return {
        "lt": actual_number < expected_number,
        "lte": actual_number <= expected_number,
        "gt": actual_number > expected_number,
        "gte": actual_number >= expected_number,
    }.get(criterion.operator, False)


@router.post("/check", response_model=list[EligibilityResult], dependencies=[Depends(get_current_user)])
def check_eligibility(payload: EligibilityRequest, db: Database) -> list[EligibilityResult]:
    schemes = db.scalars(select(Scheme).where(Scheme.is_active.is_(True)).order_by(Scheme.name)).all()
    if not schemes:
        return []
    supplied: dict[str, str | int] = {
        key: value
        for key, value in {
            "age": payload.age,
            "annual_income": payload.annual_income,
            "state": payload.state,
            "occupation": payload.occupation,
            "household_size": payload.household_size,
        }.items()
        if value is not None
    }
    results = []
    for scheme in schemes:
        criteria = [EligibilityCriterion.model_validate(item) for item in (scheme.eligibility_criteria or [])]
        matched: list[str] = []
        missing: list[str] = []
        failed: list[str] = []
        for criterion in criteria:
            actual = supplied.get(criterion.field)
            if actual is None:
                missing.append(criterion.label)
            elif criterion_matches(criterion, actual):
                matched.append(criterion.label)
            else:
                failed.append(criterion.label)
        assessment = (
            "does_not_match" if failed else
            "needs_more_information" if missing else
            "criteria_match"
        )
        results.append(
            EligibilityResult(
                scheme_id=scheme.id,
                scheme_name=scheme.name,
                assessment=assessment,
                matched_criteria=matched,
                missing_information=missing,
                disclaimer="This is a preliminary criteria match, not an official eligibility decision.",
            )
        )
    return results
