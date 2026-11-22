from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client(monkeypatch):
    Base.metadata.create_all(test_engine)

    @asynccontextmanager
    async def no_app_startup(_app):
        del _app
        yield

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(app.router, "lifespan_context", no_app_startup)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def citizen(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "citizen@example.test",
            "full_name": "Test Citizen",
            "password": "test-password-123",
        },
    )
    assert response.status_code == 201
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "citizen@example.test", "password": "test-password-123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    db = TestSession()
    user = User(
        email="admin@example.test",
        full_name="Test Admin",
        password_hash=hash_password("test-admin-password"),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.close()
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.test", "password": "test-admin-password"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
