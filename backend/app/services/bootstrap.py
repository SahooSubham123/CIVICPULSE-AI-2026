from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError
from app.core.security import hash_password
from app.db.session import set_rls_context
from app.models import User, new_id


def ensure_bootstrap_admin(db: Session) -> None:
    email = settings.bootstrap_admin_email
    password = settings.bootstrap_admin_password
    if bool(email) != bool(password):
        raise APIError(
            500,
            "bootstrap_admin_invalid",
            "Set both BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD, or leave both empty.",
        )
    if not email or not password:
        return
    if db.scalar(select(User.id).where(User.email == email.lower())):
        return
    admin_id = new_id()
    set_rls_context(db, user_id=admin_id, is_admin=True)
    admin = User(
        id=admin_id,
        email=email.lower(),
        full_name="CIVICPULSE Administrator",
        password_hash=hash_password(password.get_secret_value()),
        role="admin",
    )
    db.add(admin)
    db.commit()
