from fastapi import APIRouter
from sqlalchemy import select

from app.core.dependencies import Database
from app.core.errors import APIError
from app.db.session import set_rls_context
from app.models import Grievance
from app.schemas.grievances import GrievancePublicRead

router = APIRouter(prefix="/tracking", tags=["Complaint tracking"])


@router.get("/{reference_number}", response_model=GrievancePublicRead)
def track_complaint(reference_number: str, db: Database) -> Grievance:
    set_rls_context(db, tracking_reference=reference_number.upper())
    grievance = db.scalar(
        select(Grievance).where(Grievance.reference_number == reference_number.upper())
    )
    if grievance is None:
        raise APIError(404, "tracking_not_found", "No complaint matches this reference number.")
    return grievance
