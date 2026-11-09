"""Tests that expose the planted defects (see docs/planted-defects.md).

They are xfail(strict=True): the pipeline stays green while the bug exists, and the moment someone
fixes the bug the test XPASSes, strict mode turns that into a failure, and the marker can be removed.
"""
import pytest

from app.events import Event, EventType, NotificationConsumer
from tests.factories import new_issue, walk_to


@pytest.mark.xfail(strict=True, reason="BUG-001 docs/bugs/BUG-001.md: PATCH state skips workflow")
def test_bug001_patch_cannot_close_an_issue_without_verify(client, reporter, engineer):
    issue = new_issue(client, reporter)
    r = client.patch(f"/api/issues/{issue['id']}", json={"state": "Closed"}, headers=engineer)
    assert r.status_code == 422


@pytest.mark.xfail(strict=True, reason="BUG-002 docs/bugs/BUG-002.md: self duplicate accepted")
def test_bug002_issue_cannot_be_duplicate_of_itself(client, reporter, engineer):
    issue = new_issue(client, reporter)
    r = client.post(f"/api/issues/{issue['id']}/duplicate", json={"duplicate_of": issue["id"]}, headers=engineer)
    assert r.status_code == 422


@pytest.mark.xfail(strict=True, reason="BUG-003 docs/bugs/BUG-003.md: search is case-sensitive")
def test_bug003_search_ignores_case(client, reporter):
    new_issue(client, reporter, title="App will Crash on launch")
    assert len(client.get("/api/issues", params={"q": "crash"}, headers=reporter).json()) == 1


@pytest.mark.xfail(strict=True, reason="BUG-003 docs/bugs/BUG-003.md: priority filter uses <=")
def test_bug003_priority_filter_is_exact(client, reporter):
    new_issue(client, reporter, title="Urgent thing", priority="P1")
    new_issue(client, reporter, title="Less urgent thing", priority="P2")
    result = client.get("/api/issues", params={"priority": "P2"}, headers=reporter).json()
    assert [i["priority"] for i in result] == ["P2"]


@pytest.mark.xfail(strict=True, reason="BUG-004 docs/bugs/BUG-004.md: duplicate events notify twice")
def test_bug004_redelivered_event_notifies_once(db):
    consumer = NotificationConsumer(db)
    event = Event(EventType.ISSUE_CREATED, {"issue_id": 1, "title": "x"})
    consumer.handle(event)
    consumer.handle(event)  # same event_id delivered again
    assert db.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 1


@pytest.mark.xfail(strict=True, reason="BUG-005 docs/bugs/BUG-005.md: description not escaped")
def test_bug005_description_html_is_escaped(client, reporter):
    issue = new_issue(client, reporter, description="<script>alert(1)</script>")
    client.post("/login", data={"username": "rita", "password": "test-pass"})
    page = client.get(f"/issues/{issue['id']}").text
    assert "<script>alert(1)</script>" not in page


def test_sanity_normal_close_path_still_works(client, reporter, engineer, qa):
    """Control test: the legal route to Closed is fine, only the PATCH shortcut is broken."""
    issue = new_issue(client, reporter)
    walk_to(client, engineer, qa, issue["id"], "Closed")
