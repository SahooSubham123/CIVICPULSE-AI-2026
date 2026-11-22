from fastapi import APIRouter, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import CurrentUser, Database
from app.core.errors import APIError
from app.core.security import create_access_token, verify_password
from app.db.session import set_rls_context
from app.models import User, new_id
from app.schemas.users import TokenResponse, UserCreate, UserRead
from app.core.security import hash_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Database) -> User:
    email = str(payload.email).lower()
    set_rls_context(db, login_email=email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise APIError(409, "email_in_use", "An account with this email already exists.")
    user_id = new_id()
    set_rls_context(db, user_id=user_id)
    user = User(
        id=user_id,
        email=email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        preferred_language=payload.preferred_language,
        location=payload.location,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm, db: Database) -> TokenResponse:
    email = form.username.lower()
    set_rls_context(db, login_email=email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(form.password, user.password_hash):
        raise APIError(401, "invalid_credentials", "Email or password is incorrect.")
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
        user=user,
    )


@router.get("/me", response_model=UserRead)
def current_account(user: CurrentUser) -> User:
    return user
