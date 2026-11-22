from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import decode_access_token
from app.db.session import get_db, set_rls_context
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
Database = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Database) -> User:
    user_id = decode_access_token(token)
    set_rls_context(db, user_id=user_id)
    user = db.get(User, user_id)
    if user is None:
        raise APIError(401, "user_not_found", "The account for this token no longer exists.")
    if user.role == "admin":
        set_rls_context(db, user_id=user.id, is_admin=True)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise APIError(403, "admin_required", "This operation requires an administrator account.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
