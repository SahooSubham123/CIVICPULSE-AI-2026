from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.dependencies import AdminUser, CurrentUser, Database, require_admin
from app.core.errors import APIError
from app.models import User
from app.schemas.common import PaginatedResponse
from app.schemas.users import UserRead, UserRoleUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["User management"])


@router.get("/me", response_model=UserRead)
def get_profile(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserRead)
def update_profile(payload: UserUpdate, user: CurrentUser, db: Database) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.get(
    "",
    response_model=PaginatedResponse[UserRead],
    dependencies=[Depends(require_admin)],
)
def list_users(db: Database, limit: int = 50, offset: int = 0) -> dict:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    total = db.scalar(select(func.count()).select_from(User)) or 0
    items = db.scalars(select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.patch("/{user_id}/role", response_model=UserRead)
def update_user_role(user_id: str, payload: UserRoleUpdate, admin: AdminUser, db: Database) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise APIError(404, "user_not_found", "The requested account was not found.")
    if user.id == admin.id and payload.role != "admin":
        raise APIError(409, "cannot_demote_self", "Administrators cannot remove their own administrator role.")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user
