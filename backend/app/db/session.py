from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

connect_args: dict[str, object] = {}
engine_options: dict[str, object] = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    connect_args["connect_timeout"] = settings.database_connect_timeout_seconds
    connect_args["sslmode"] = settings.database_ssl_mode
    engine_options.update(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=1_800,
        connect_args=connect_args,
    )
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def assume_restricted_database_role(dbapi_connection: object, connection_record: object) -> None:
    del connection_record
    if engine.dialect.name == "postgresql":
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f'SET ROLE "{settings.database_rls_role}"')
            cursor.execute("SET search_path TO public, extensions")
        finally:
            cursor.close()


def _apply_rls_context(connection: Connection, context: dict[str, str]) -> None:
    connection.execute(
        text(
            "SELECT "
            "set_config('app.user_id', :user_id, true), "
            "set_config('app.is_admin', :is_admin, true), "
            "set_config('app.login_email', :login_email, true), "
            "set_config('app.tracking_reference', :tracking_reference, true)"
        ),
        {
            "user_id": context.get("user_id", ""),
            "is_admin": context.get("is_admin", "false"),
            "login_email": context.get("login_email", ""),
            "tracking_reference": context.get("tracking_reference", ""),
        },
    )


@event.listens_for(Session, "after_begin")
def apply_transaction_rls_context(
    session: Session,
    transaction: object,
    connection: Connection,
) -> None:
    del transaction
    if connection.dialect.name == "postgresql":
        _apply_rls_context(connection, session.info.get("rls_context", {}))


def set_rls_context(
    db: Session,
    *,
    user_id: str | None = None,
    is_admin: bool = False,
    login_email: str | None = None,
    tracking_reference: str | None = None,
) -> None:
    context = {
        "user_id": user_id or "",
        "is_admin": "true" if is_admin else "false",
        "login_email": login_email or "",
        "tracking_reference": tracking_reference or "",
    }
    db.info["rls_context"] = context
    if db.get_bind().dialect.name == "postgresql":
        _apply_rls_context(db.connection(), context)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
