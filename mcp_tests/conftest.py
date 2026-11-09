"""Fixtures: a tracker API client (in-memory app) and a scripted fake LLM."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import connect
from app.main import create_app
from app.services import ComponentService, UserService

PASSWORD = "pw-test"


@pytest.fixture
def tracker(tmp_path):
    db_path = str(tmp_path / "t.db")
    app = create_app(db_path)
    conn = connect(db_path)
    users = UserService(conn)
    users.create("quinn", PASSWORD, "qa")
    components = ComponentService(conn)
    components.create("Mail")
    components.create("Sync", "Mail")
    conn.close()
    api = TestClient(app, base_url="http://testserver/api")
    token = api.post("/auth/login", json={"username": "quinn", "password": PASSWORD}).json()["token"]
    api.headers["Authorization"] = f"Bearer {token}"

    def create(title, description="", component="Mail > Sync", priority="P3"):
        r = api.post("/issues", json={"title": title, "description": description, "component": component,
                                      "priority": priority})
        assert r.status_code == 201
        return r.json()

    def issue_count():
        c = connect(db_path)
        try:
            return c.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
        finally:
            c.close()

    return SimpleNamespace(api=api, create=create, issue_count=issue_count, db_path=db_path)


class FakeLLM:
    """Plays back a list of assistant turns. Each turn is a list of content blocks."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.seen_tools: list[list[str]] = []
        self.messages_seen: list[list] = []

    def create(self, system, messages, tools):
        self.seen_tools.append([t["name"] for t in tools])
        self.messages_seen.append(list(messages))
        return self.turns.pop(0)


def tool_use(name, input_, id_="t1"):
    return {"type": "tool_use", "id": id_, "name": name, "input": input_}


def valid_draft(**overrides):
    draft = {
        "kind": "bug_report",
        "title": "Sync hangs on large mailbox",
        "summary": "Syncing a mailbox with many messages never completes.",
        "duplicates": [{"issue_id": 1, "score": 0.8, "reason": "Same symptom"}],
        "tests_run": [{"keyword": "sync", "summary": "3 passed"}],
        "reproduction": {"result": "not_attempted", "notes": "No automated test covers large mailboxes"},
        "suggested_priority": "P2",
        "steps_to_reproduce": ["Open a mailbox with 50000 messages", "Start sync"],
        "expected": "Sync completes",
        "actual": "Sync spinner never stops",
        "confidence": "medium",
        "requires_human_review": True,
    }
    draft.update(overrides)
    return draft
