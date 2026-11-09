"""API tests for issues, auth, comments, history and duplicates."""
import pytest

from tests.factories import move, new_issue, walk_to


@pytest.mark.smoke
def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


class TestAuth:
    def test_login_returns_token(self, client):
        r = client.post("/api/auth/login", json={"username": "rita", "password": "test-pass"})
        assert r.status_code == 200 and r.json()["token"]

    def test_wrong_password_rejected(self, client):
        r = client.post("/api/auth/login", json={"username": "rita", "password": "nope"})
        assert r.status_code == 403

    def test_endpoints_need_a_token(self, client):
        assert client.get("/api/issues").status_code == 401

    def test_bad_token_rejected(self, client):
        assert client.get("/api/issues", headers={"Authorization": "Bearer junk"}).status_code == 401

    def test_duplicate_username_conflicts(self, client):
        r = client.post("/api/users", json={"username": "rita", "password": "abcd", "role": "qa"})
        assert r.status_code == 409


class TestCreateIssue:
    @pytest.mark.smoke
    def test_create_returns_full_record(self, client, reporter):
        issue = new_issue(client, reporter, priority="P1")
        assert issue["state"] == "Analyze"
        assert issue["priority"] == "P1"
        assert issue["component"] == "Mail > Sync"
        assert issue["reporter"] == "rita"

    @pytest.mark.parametrize(
        "payload",
        [
            {"title": "ab", "component": "Mail"},  # title too short
            {"title": "Valid title", "component": "Mail", "priority": "P9"},  # bad priority
            {"component": "Mail"},  # missing title
        ],
    )
    def test_invalid_payload_is_422(self, client, reporter, payload):
        assert client.post("/api/issues", json=payload, headers=reporter).status_code == 422

    def test_unknown_component_is_404(self, client, reporter):
        r = client.post("/api/issues", json={"title": "Valid title", "component": "Nope"}, headers=reporter)
        assert r.status_code == 404

    def test_history_records_creation(self, client, reporter):
        issue = new_issue(client, reporter)
        history = client.get(f"/api/issues/{issue['id']}/history", headers=reporter).json()
        assert history[0]["field"] == "created"

    def test_get_missing_issue_is_404(self, client, reporter):
        assert client.get("/api/issues/999", headers=reporter).status_code == 404


class TestWorkflowViaApi:
    def test_full_happy_path(self, client, reporter, engineer, qa):
        issue = new_issue(client, reporter)
        walk_to(client, engineer, qa, issue["id"], "Closed")
        assert client.get(f"/api/issues/{issue['id']}", headers=reporter).json()["state"] == "Closed"

    def test_cannot_skip_to_closed(self, client, reporter, qa):
        issue = new_issue(client, reporter)
        r = move(client, qa, issue["id"], "Closed")
        assert r.status_code == 422

    def test_engineer_cannot_close(self, client, reporter, engineer, qa):
        issue = new_issue(client, reporter)
        walk_to(client, engineer, qa, issue["id"], "Verify")
        assert move(client, engineer, issue["id"], "Closed").status_code == 422

    def test_reporter_cannot_change_state(self, client, reporter):
        issue = new_issue(client, reporter)
        assert move(client, reporter, issue["id"], "Integrate").status_code == 403

    def test_unknown_state_rejected(self, client, reporter, engineer):
        issue = new_issue(client, reporter)
        assert move(client, engineer, issue["id"], "Teleport").status_code == 422

    def test_state_changes_are_logged(self, client, reporter, engineer):
        issue = new_issue(client, reporter)
        move(client, engineer, issue["id"], "Integrate")
        history = client.get(f"/api/issues/{issue['id']}/history", headers=reporter).json()
        assert history[-1]["old_value"] == "Analyze" and history[-1]["new_value"] == "Integrate"

    def test_reopen_after_close(self, client, reporter, engineer, qa):
        issue = new_issue(client, reporter)
        walk_to(client, engineer, qa, issue["id"], "Closed")
        assert move(client, engineer, issue["id"], "Analyze").status_code == 200


class TestUpdateAndPermissions:
    def test_reporter_cannot_patch(self, client, reporter):
        issue = new_issue(client, reporter)
        r = client.patch(f"/api/issues/{issue['id']}", json={"priority": "P1"}, headers=reporter)
        assert r.status_code == 403

    def test_engineer_can_change_priority_and_assignee(self, client, reporter, engineer):
        issue = new_issue(client, reporter)
        r = client.patch(
            f"/api/issues/{issue['id']}", json={"priority": "P1", "assignee": "erin"}, headers=engineer
        )
        assert r.json()["priority"] == "P1" and r.json()["assignee"] == "erin"

    def test_patch_unknown_assignee_is_404(self, client, reporter, engineer):
        issue = new_issue(client, reporter)
        r = client.patch(f"/api/issues/{issue['id']}", json={"assignee": "ghost"}, headers=engineer)
        assert r.status_code == 404


class TestComments:
    def test_add_and_list(self, client, reporter):
        issue = new_issue(client, reporter)
        client.post(f"/api/issues/{issue['id']}/comments", json={"body": "Seen on build 12"}, headers=reporter)
        comments = client.get(f"/api/issues/{issue['id']}/comments", headers=reporter).json()
        assert [c["body"] for c in comments] == ["Seen on build 12"]

    def test_empty_comment_rejected(self, client, reporter):
        issue = new_issue(client, reporter)
        r = client.post(f"/api/issues/{issue['id']}/comments", json={"body": ""}, headers=reporter)
        assert r.status_code == 422


class TestDuplicates:
    def test_mark_duplicate(self, client, reporter, engineer):
        original = new_issue(client, reporter)
        dupe = new_issue(client, reporter, title="Same problem again")
        r = client.post(
            f"/api/issues/{dupe['id']}/duplicate", json={"duplicate_of": original["id"]}, headers=engineer
        )
        assert r.json()["duplicate_of"] == original["id"]

    def test_duplicate_of_missing_issue_is_404(self, client, reporter, engineer):
        issue = new_issue(client, reporter)
        r = client.post(f"/api/issues/{issue['id']}/duplicate", json={"duplicate_of": 999}, headers=engineer)
        assert r.status_code == 404

    def test_reporter_cannot_mark_duplicate(self, client, reporter):
        a, b = new_issue(client, reporter), new_issue(client, reporter, title="Another one")
        r = client.post(f"/api/issues/{b['id']}/duplicate", json={"duplicate_of": a["id"]}, headers=reporter)
        assert r.status_code == 403
