from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.dependencies import Database, require_admin
from app.core.errors import APIError
from app.models import Document, Grievance, Scheme, ServiceTask, User, Verification
from app.schemas.admin import AdminOverview
from app.schemas.common import PaginatedResponse
from app.schemas.grievances import GrievanceRead

router = APIRouter(prefix="/admin", tags=["Admin dashboard"])


@router.get("/overview", response_model=AdminOverview, dependencies=[Depends(require_admin)])
def overview(db: Database) -> AdminOverview:
    def count(model: type, *criteria: object) -> int:
        statement = select(func.count()).select_from(model)
        if criteria:
            statement = statement.where(*criteria)
        return db.scalar(statement) or 0

    return AdminOverview(
        total_users=count(User),
        total_schemes=count(Scheme, Scheme.is_active.is_(True)),
        total_documents=count(Document, Document.is_published.is_(True)),
        total_grievances=count(Grievance),
        open_grievances=count(Grievance, Grievance.status.in_(["received", "in_progress"])),
        resolved_grievances=count(Grievance, Grievance.status == "resolved"),
        pending_review_grievances=count(Grievance, Grievance.review_status == "pending"),
        pending_service_tasks=count(ServiceTask, ServiceTask.status == "planned"),
        verification_count=count(Verification),
    )


@router.get(
    "/grievances",
    response_model=PaginatedResponse[GrievanceRead],
    dependencies=[Depends(require_admin)],
)
def admin_grievances(
    db: Database,
    status_filter: str | None = None,
    review_status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    statement = select(Grievance)
    count_statement = select(func.count()).select_from(Grievance)
    if status_filter:
        if status_filter not in {"received", "in_progress", "resolved", "rejected"}:
            raise APIError(422, "invalid_status", "The requested grievance status is not supported.")
        statement = statement.where(Grievance.status == status_filter)
        count_statement = count_statement.where(Grievance.status == status_filter)
    if review_status:
        if review_status not in {"pending", "reviewed"}:
            raise APIError(422, "invalid_review_status", "The requested review status is not supported.")
        statement = statement.where(Grievance.review_status == review_status)
        count_statement = count_statement.where(Grievance.review_status == review_status)
    if priority:
        if priority not in {"low", "medium", "high", "urgent"}:
            raise APIError(422, "invalid_priority", "The requested grievance priority is not supported.")
        statement = statement.where(Grievance.priority == priority)
        count_statement = count_statement.where(Grievance.priority == priority)
    items = db.scalars(statement.order_by(Grievance.created_at.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": db.scalar(count_statement) or 0, "limit": limit, "offset": offset}
