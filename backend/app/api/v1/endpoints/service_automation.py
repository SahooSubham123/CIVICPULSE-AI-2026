from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, Database
from app.core.errors import APIError
from app.models import ServiceTask
from app.schemas.common import PaginatedResponse
from app.schemas.services import (
    PortalInspectionRequest,
    PortalInspectionResponse,
    ServiceAssistanceRequest,
    ServiceAssistanceResponse,
    ServiceExecutionRequest,
    ServiceExecutionResponse,
    ServicePlanRequest,
    ServicePlanResponse,
    SupportedPortal,
)
from app.services.government_portals import inspect_portal, list_supported_portals
from app.services.government_service_assistant import assess_service_request

router = APIRouter(prefix="/services/automation", tags=["Government service automation"])
USER_WARNING = (
    "This plan is guidance only. It does not submit forms or access government accounts. "
    "Review every field and legal declaration yourself."
)


@router.post("/plans", response_model=ServicePlanResponse, status_code=201)
def create_service_plan(payload: ServicePlanRequest, user: CurrentUser, db: Database) -> ServicePlanResponse:
    steps = [
        f"Confirm the official {payload.service_name} service portal for {payload.jurisdiction}.",
        "Review the current eligibility criteria and required documents with the responsible department.",
        "Complete the official application yourself and review every field before submission.",
    ]
    task = ServiceTask(
        user_id=user.id,
        service_name=payload.service_name,
        steps=steps,
        status="planned",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return ServicePlanResponse(
        task_id=task.id,
        service_name=task.service_name,
        status=task.status,
        steps=steps,
        created_at=task.created_at,
        warning=USER_WARNING,
    )


@router.post("/assist", response_model=ServiceAssistanceResponse, status_code=201)
async def assist_with_service(
    payload: ServiceAssistanceRequest,
    user: CurrentUser,
    db: Database,
) -> ServiceAssistanceResponse:
    assessment = await assess_service_request(payload.service_request, payload.jurisdiction)
    task = ServiceTask(
        user_id=user.id,
        service_name=assessment.service_name,
        steps=assessment.procedure,
        status="planned",
        user_confirmed=False,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return ServiceAssistanceResponse(
        **assessment.model_dump(),
        task_id=task.id,
        supported_portals=list_supported_portals(),
    )


@router.get("/plans", response_model=PaginatedResponse[ServicePlanResponse])
def list_service_plans(
    user: CurrentUser,
    db: Database,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    statement = select(ServiceTask).where(ServiceTask.user_id == user.id)
    tasks = db.scalars(statement.order_by(ServiceTask.created_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count()).select_from(ServiceTask).where(ServiceTask.user_id == user.id)) or 0
    items = [
        ServicePlanResponse(
            task_id=task.id,
            service_name=task.service_name,
            status=task.status,
            steps=task.steps,
            created_at=task.created_at,
            warning=USER_WARNING,
        )
        for task in tasks
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/portals", response_model=list[SupportedPortal])
def supported_portals(user: CurrentUser) -> list[SupportedPortal]:
    del user
    return list_supported_portals()


@router.post("/portals/{portal_id}/inspect", response_model=PortalInspectionResponse)
async def inspect_supported_portal(
    portal_id: str,
    payload: PortalInspectionRequest,
    user: CurrentUser,
) -> PortalInspectionResponse:
    del user
    return await inspect_portal(portal_id, payload.path)


@router.post("/{task_id}/execute", response_model=ServiceExecutionResponse)
def execute_service_task(
    task_id: str,
    payload: ServiceExecutionRequest,
    user: CurrentUser,
    db: Database,
) -> ServiceExecutionResponse:
    task = db.scalar(
        select(ServiceTask).where(ServiceTask.id == task_id, ServiceTask.user_id == user.id)
    )
    if task is None:
        raise APIError(404, "service_task_not_found", "The requested service plan was not found.")
    if not payload.user_confirmed:
        raise APIError(400, "confirmation_required", "Explicit user confirmation is required.")
    raise APIError(
        503,
        "service_execution_unavailable",
        "Application submission is disabled. Review every field and legal declaration, then submit directly on the official portal yourself.",
    )
