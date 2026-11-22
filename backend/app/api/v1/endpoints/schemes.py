from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select

from app.core.dependencies import Database, require_admin
from app.core.errors import APIError
from app.models import Scheme
from app.schemas.common import PaginatedResponse
from app.schemas.schemes import SchemeCreate, SchemeRead

router = APIRouter(prefix="/schemes", tags=["Government schemes"])


@router.get("", response_model=PaginatedResponse[SchemeRead])
def list_schemes(
    db: Database,
    query: str | None = None,
    state: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit, offset = min(max(limit, 1), 100), max(offset, 0)
    statement = select(Scheme).where(Scheme.is_active.is_(True))
    count_statement = select(func.count()).select_from(Scheme).where(Scheme.is_active.is_(True))
    if query:
        statement = statement.where(Scheme.name.ilike(f"%{query}%"))
        count_statement = count_statement.where(Scheme.name.ilike(f"%{query}%"))
    if state:
        statement = statement.where((Scheme.state == state) | Scheme.state.is_(None))
        count_statement = count_statement.where((Scheme.state == state) | Scheme.state.is_(None))
    items = db.scalars(statement.order_by(Scheme.name).limit(limit).offset(offset)).all()
    total = db.scalar(count_statement) or 0
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{scheme_id}", response_model=SchemeRead)
def get_scheme(scheme_id: str, db: Database) -> Scheme:
    scheme = db.get(Scheme, scheme_id)
    if scheme is None or not scheme.is_active:
        raise APIError(404, "scheme_not_found", "The requested scheme was not found.")
    return scheme


@router.post(
    "",
    response_model=SchemeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_scheme(payload: SchemeCreate, db: Database) -> Scheme:
    scheme = Scheme(**payload.model_dump(mode="json"))
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return scheme


@router.delete(
    "/{scheme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def archive_scheme(scheme_id: str, db: Database) -> None:
    scheme = db.get(Scheme, scheme_id)
    if scheme is None:
        raise APIError(404, "scheme_not_found", "The requested scheme was not found.")
    scheme.is_active = False
    db.commit()
