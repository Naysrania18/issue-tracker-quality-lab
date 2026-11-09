import json
import subprocess

import pytest

from mcp_server import tools as tools_module
from mcp_server.tools import AuditLog, ToolError, TrackerTools


def make_tools(tracker, allow_write=False, runner=None, log_path=None):
    kwargs = {"test_runner": runner} if runner else {}
    return TrackerTools(tracker.api, allow_write=allow_write, audit=AuditLog(log_path), **kwargs)


class TestReadTools:
    def test_search_issues(self, tracker):
        tracker.create("Sync hangs on large mailbox")
        tracker.create("Calendar color wrong", component="Mail")
        result = make_tools(tracker).search_issues(query="Sync")
        assert result["count"] == 1 and result["items"][0]["title"].startswith("Sync")

    def test_get_issue_includes_comments_and_history(self, tracker):
        issue = tracker.create("Something broken here")
        tracker.api.post(f"/issues/{issue['id']}/comments", json={"body": "seen twice"})
        result = make_tools(tracker).get_issue(issue["id"])
        assert result["issue"]["id"] == issue["id"]
        assert result["comments"][0]["body"] == "seen twice"
        assert result["history"][0]["field"] == "created"

    def test_get_missing_issue_gives_clear_error(self, tracker):
        with pytest.raises(ToolError, match="404"):
            make_tools(tracker).get_issue(999)

    def test_find_duplicates(self, tracker):
        original = tracker.create("App crashes when opening PDF attachment", "Opening a PDF closes the app")
        tracker.create("Calendar widget colour is wrong", "Birthdays are blue")
        result = make_tools(tracker).find_duplicates("Opening a PDF attachment crashes the app")
        assert result["matches"][0]["issue_id"] == original["id"]

    def test_find_duplicates_on_empty_tracker(self, tracker):
        assert make_tools(tracker).find_duplicates("anything at all here") == {"matches": []}

    def test_list_test_cases_and_results(self, tracker):
        case = tracker.api.post("/test-cases", json={"title": "Sync completes", "component": "Mail > Sync"}).json()
        suite = tracker.api.post("/suites", json={"name": "Smoke", "case_ids": [case["id"]]}).json()
        run = tracker.api.post("/test-runs", json={"suite_id": suite["id"]}).json()
        tracker.api.post(f"/test-runs/{run['id']}/results", json={"case_id": case["id"], "status": "passed"})
        tools = make_tools(tracker)
        assert tools.list_test_cases("Mail")["count"] == 1
        assert tools.get_test_results(run["id"])["run"]["results"][0]["status"] == "passed"
        assert tools.get_test_results()["runs"][0]["results"] == 1


class TestValidation:
    @pytest.mark.parametrize("bad_id", [0, -1, "1", None, True, 1.5])
    def test_issue_id_must_be_positive_int(self, tracker, bad_id):
        with pytest.raises(ToolError, match="positive integer"):
            make_tools(tracker).get_issue(bad_id)

    def test_bad_priority_filter(self, tracker):
        with pytest.raises(ToolError, match="priority"):
            make_tools(tracker).search_issues(priority="P9")

    @pytest.mark.parametrize("text", ["", "abc", "x" * 2001])
    def test_duplicate_text_length(self, tracker, text):
        with pytest.raises(ToolError):
            make_tools(tracker).find_duplicates(text)

    @pytest.mark.parametrize("keyword", ["", "a; rm -rf /", "$(whoami)", "a" * 61, "x --collect-only", "a|b", "../x"])
    def test_run_tests_rejects_unsafe_keywords(self, tracker, keyword):
        called = []
        tools = make_tools(tracker, runner=lambda k: called.append(k))
        with pytest.raises(ToolError, match="keyword"):
            tools.run_tests(keyword)
        assert called == []

    def test_run_tests_uses_runner_for_safe_keyword(self, tracker):
        tools = make_tools(tracker, runner=lambda k: {"keyword": k, "exit_code": 0})
        assert tools.run_tests("sync or workflow")["exit_code"] == 0


class TestWriteSafety:
    def test_writes_refused_by_default(self, tracker):
        tools = make_tools(tracker)
        with pytest.raises(ToolError, match="read-only"):
            tools.create_issue("A new issue", "Mail")
        with pytest.raises(ToolError, match="read-only"):
            tools.add_comment(1, "hello")
        assert tracker.issue_count() == 0

    def test_writes_work_when_enabled(self, tracker):
        tools = make_tools(tracker, allow_write=True)
        issue = tools.create_issue("A new issue", "Mail > Sync", "details", "P2")
        assert issue["priority"] == "P2"
        tools.add_comment(issue["id"], "first comment")
        assert tools.get_issue(issue["id"])["comments"][0]["body"] == "first comment"

    @pytest.mark.parametrize(
        "kwargs",
        [{"title": "ab", "component": "Mail"}, {"title": "Valid", "component": "Mail", "priority": "P7"},
         {"title": "Valid", "component": ""}],
    )
    def test_create_validates_input(self, tracker, kwargs):
        with pytest.raises(ToolError):
            make_tools(tracker, allow_write=True).create_issue(**kwargs)
        assert tracker.issue_count() == 0

    def test_comment_body_validated(self, tracker):
        with pytest.raises(ToolError):
            make_tools(tracker, allow_write=True).add_comment(1, "   ")


class TestAudit:
    def test_every_outcome_is_logged(self, tracker, tmp_path):
        log = tmp_path / "audit" / "log.jsonl"
        tools = make_tools(tracker, log_path=log)
        tools.search_issues()
        with pytest.raises(ToolError):
            tools.get_issue(0)
        with pytest.raises(ToolError):
            tools.create_issue("Nope nope", "Mail")
        outcomes = [e["outcome"].split(":")[0] for e in tools.audit.entries]
        assert outcomes == ["ok", "invalid", "refused"]
        lines = [json.loads(line) for line in log.read_text().splitlines()]
        assert [line["tool"] for line in lines] == ["search_issues", "get_issue", "create_issue"]

    def test_long_arguments_are_shortened(self, tracker):
        audit = AuditLog(None)
        audit.record("x", {"text": "a" * 500}, "ok")
        assert len(audit.entries[0]["args"]["text"]) < 100


def test_pytest_runner_parses_summary(monkeypatch):
    fake = subprocess.CompletedProcess(
        args=[], returncode=1,
        stdout="FAILED tests/test_a.py::test_x - assert\n2 failed, 5 passed, 1 xfailed in 1.2s\n", stderr="",
    )
    monkeypatch.setattr(tools_module.subprocess, "run", lambda *a, **k: fake)
    result = tools_module.pytest_runner("sync")
    assert result["counts"] == {"failed": 2, "passed": 5, "xfailed": 1}
    assert result["failed"] == ["tests/test_a.py::test_x"] and result["exit_code"] == 1
