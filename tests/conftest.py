"""Shared fixtures: a throw-away app + database per test, and logged-in users for each role."""
import pytest
from fastapi.testclient import TestClient

from app.database import connect
from app.main import create_app
from app.services import ComponentService, UserService

PASSWORD = "test-pass"


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def app(db_path):
    application = create_app(db_path)
    conn = connect(db_path)
    users = UserService(conn)
    for name, role in [("rita", "reporter"), ("erin", "engineer"), ("quinn", "qa")]:
        users.create(name, PASSWORD, role)
    components = ComponentService(conn)
    components.create("Mail")
    components.create("Sync", "Mail")
    components.create("Compose", "Mail")
    components.create("Calendar")
    conn.close()
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def _login(client, username):
    token = client.post("/api/auth/login", json={"username": username, "password": PASSWORD}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reporter(client):
    return _login(client, "rita")


@pytest.fixture
def engineer(client):
    return _login(client, "erin")


@pytest.fixture
def qa(client):
    return _login(client, "quinn")


@pytest.fixture
def db(app, db_path):
    conn = connect(db_path)
    yield conn
    conn.close()
