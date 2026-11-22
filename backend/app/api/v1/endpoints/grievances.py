import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select

from app.core.config import settings
from app.core.dependencies import CurrentUser, Database, require_admin
from app.core.errors import APIError
from app.models import Grievance, utc_now
from app.schemas.common import PaginatedResponse
from app.schemas.grievances import GrievanceCreate, GrievanceRead, GrievanceUpdate
from app.services.grievance_triage import assess_grievance

router = APIRouter(prefix="/grievances", tags=["Grievance reporting"])
logger = logging.getLogger(__name__)
SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _read_image(file: UploadFile, content: bytes) -> None:
    if file.content_type not in SUPPORTED_IMAGE_TYPES:
        raise APIError(415, "unsupported_media_type", "Upload a JPEG, PNG, or WebP image.")
    if not content:
        raise APIError(400, "empty_media", "The uploaded image is empty.")
    if len(content) > settings.max_media_size_bytes:
        raise APIError(413, "media_too_large", "The uploaded image exceeds the configured size limit.")
    valid_signature = (
        (file.content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff"))
        or (file.content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
        or (
            file.content_type == "image/webp"
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        )
    )
    if not valid_signature:
        raise APIError(415, "invalid_media", "The image bytes do not match the declared image type.")


async def _create_grievance(
    payload: GrievanceCreate,
    user: CurrentUser,
    db: Database,
    image: bytes | None = None,
    content_type: str | None = None,
    filename: str | None = None,
) -> Grievance:
    fields = payload.model_dump()
    grievance = Grievance(
        **fields,
        user_id=user.id,
        evidence_image=image,
        evidence_content_type=content_type,
        evidence_filename=filename[:255] if filename else None,
        priority="medium",
        review_status="pending",
        ai_triage_status="unavailable",
        status="received",
    )
    try:
        triage, _ = await assess_grievance(
            payload.title,
            payload.description,
            payload.category,
        )
    except APIError as exc:
        logger.warning("AI grievance triage unavailable (%s)", exc.code)
        grievance.ai_rationale = "AI triage unavailable; human review is required."
    else:
        grievance.ai_suggested_category = triage.category
        grievance.ai_suggested_priority = triage.priority
        grievance.ai_confidence = triage.confidence
        grievance.ai_rationale = triage.rationale
        grievance.ai_triage_status = "completed"
    db.add(grievance)
    db.commit()
    db.refresh(grievance)
    return grievance


@router.post("", response_model=GrievanceRead, status_code=status.HTTP_201_CREATED)
async def create_grievance(
    payload: GrievanceCreate,
    user: CurrentUser,
    db: Database,
) -> Grievance:
    return await _create_grievance(payload, user, db)


@router.post("/submit", response_model=GrievanceRead, status_code=status.HTTP_201_CREATED)
async def submit_grievance(
    user: CurrentUser,
    db: Database,
    category: str = Form(min_length=2, max_length=80),
    title: str = Form(min_length=5, max_length=180),
    description: str = Form(min_length=10, max_length=10_000),
    location: str = Form(min_length=3, max_length=240),
    latitude: float | None = Form(default=None, ge=-90, le=90),
    longitude: float | None = Form(default=None, ge=-180, le=180),
    file: UploadFile | None = File(default=None),
) -> Grievance:
    image = None
    content_type = None
    filename = None
    if file is not None:
        image = await file.read(settings.max_media_size_bytes + 1)
        _read_image(file, image)
        content_type = file.content_type
        filename = file.filename
    if (latitude is None) != (longitude is None):
        raise APIError(422, "validation_error", "Latitude and longitude must be supplied together.")
    payload = GrievanceCreate(
        category=category,
        title=title,
        description=description,
        location=location,
        latitude=latitude,
        longitude=longitude,
    )
    return await _create_grievance(payload, user, db, image, content_type, filename)


@router.get("", response_model=PaginatedResponse[GrievanceRead])
def list_grievances(
    db: Database,
    user: CurrentUser,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    statement = select(Grievance).where(Grievance.user_id == user.id)
    items = db.scalars(statement.order_by(Grievance.created_at.desc()).limit(limit).offset(offset)).all()
    total = db.scalar(select(func.count()).select_from(Grievance).where(Grievance.user_id == user.id)) or 0
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{grievance_id}/evidence")
def get_grievance_evidence(grievance_id: str, user: CurrentUser, db: Database) -> Response:
    grievance = db.get(Grievance, grievance_id)
    if grievance is None or (user.role != "admin" and grievance.user_id != user.id):
        raise APIError(404, "grievance_not_found", "The requested grievance was not found.")
    if grievance.evidence_image is None or grievance.evidence_content_type is None:
        raise APIError(404, "evidence_not_found", "No image evidence is attached to this grievance.")
    return Response(
        content=grievance.evidence_image,
        media_type=grievance.evidence_content_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/{grievance_id}", response_model=GrievanceRead)
def get_grievance(grievance_id: str, user: CurrentUser, db: Database) -> Grievance:
    grievance = db.get(Grievance, grievance_id)
    if grievance is None or (user.role != "admin" and grievance.user_id != user.id):
        raise APIError(404, "grievance_not_found", "The requested grievance was not found.")
    return grievance


@router.patch(
    "/{grievance_id}",
    response_model=GrievanceRead,
    dependencies=[Depends(require_admin)],
)
def update_grievance(
    grievance_id: str,
    payload: GrievanceUpdate,
    user: CurrentUser,
    db: Database,
) -> Grievance:
    grievance = db.get(Grievance, grievance_id)
    if grievance is None:
        raise APIError(404, "grievance_not_found", "The requested grievance was not found.")
    changes = payload.model_dump(exclude_unset=True)
    review_status = changes.pop("review_status", None)
    if review_status is None and {"category", "priority", "status"}.intersection(changes):
        review_status = "reviewed"
    for field, value in changes.items():
        setattr(grievance, field, value)
    if review_status is not None:
        grievance.review_status = review_status
        grievance.reviewed_by_id = user.id if review_status == "reviewed" else None
        grievance.reviewed_at = utc_now() if review_status == "reviewed" else None
    db.commit()
    db.refresh(grievance)
    return grievance
