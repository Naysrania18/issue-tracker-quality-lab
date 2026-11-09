"""The actual tool logic, independent of MCP so it can be unit tested directly.

Safety rules:
  * Read-only by default. Write tools (create_issue, add_comment) raise unless allow_write=True.
  * Every input is validated before anything is sent to the tracker.
  * Every call (allowed, refused or failed) is appended to an audit log as one JSON line.
  * run_tests only ever runs this project's own pytest suite with a sanitised -k filter.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from mcp.server.mcpserver.exceptions import ToolError as McpToolError

from qtools.duplicates import DuplicateFinder

PRIORITIES = {"P1", "P2", "P3", "P4"}
KEYWORD_PATTERN = re.compile(r"^[A-Za-z0-9_ ]{1,60}$")
REPO_ROOT = Path(__file__).resolve().parent.parent

WRITE_TOOLS = {"create_issue", "add_comment"}


class ToolError(McpToolError, ValueError):
    """Raised for invalid input or refused actions. The message is safe to show to the model."""


class AuditLog:
    def __init__(self, path: Optional[Path]) -> None:
        self.path = path
        self.entries: list[dict[str, Any]] = []  # kept in memory too, handy for tests

    def record(self, tool: str, args: dict[str, Any], outcome: str) -> None:
        shortened = {k: (v[:80] + "..." if isinstance(v, str) and len(v) > 80 else v) for k, v in args.items()}
        entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tool": tool,
                 "args": shortened, "outcome": outcome}
        self.entries.append(entry)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ToolError(f"{name} must be a positive integer")
    return value


def _text(value: Any, name: str, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise ToolError(f"{name} must be a string")
    value = value.strip()
    if not min_len <= len(value) <= max_len:
        raise ToolError(f"{name} must be {min_len}-{max_len} characters")
    return value


def pytest_runner(keyword: str) -> dict[str, Any]:
    """Run the project's test suite, filtered by keyword, and summarise the outcome."""
    command = [sys.executable, "-m", "pytest", "tests", "-q", "--tb=no", "-p", "no:cacheprovider", "-k", keyword]
    done = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=180)
    summary = done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""
    status_words = r"passed|failed|errors?|skipped|xfailed|deselected"
    counts = {name: int(n) for n, name in re.findall(rf"(\d+) ({status_words})", summary)}
    failed = re.findall(r"^FAILED (\S+)", done.stdout, flags=re.MULTILINE)
    return {"keyword": keyword, "exit_code": done.returncode, "summary": summary, "counts": counts, "failed": failed}


class TrackerTools:
    def __init__(
        self,
        api: httpx.Client,
        allow_write: bool = False,
        audit: Optional[AuditLog] = None,
        test_runner: Callable[[str], dict[str, Any]] = pytest_runner,
    ) -> None:
        self.api = api
        self.allow_write = allow_write
        self.audit = audit or AuditLog(None)
        self.test_runner = test_runner

    # ---------- plumbing ----------
    def _call(self, tool: str, args: dict[str, Any], action: Callable[[], Any]) -> Any:
        if tool in WRITE_TOOLS and not self.allow_write:
            self.audit.record(tool, args, "refused: read-only mode")
            raise ToolError(f"'{tool}' is a write tool and the server is in read-only mode")
        try:
            result = action()
        except ToolError as exc:
            self.audit.record(tool, args, f"invalid: {exc}")
            raise
        except Exception as exc:
            self.audit.record(tool, args, f"error: {type(exc).__name__}")
            raise
        self.audit.record(tool, args, "ok")
        return result

    def _get(self, path: str, **params: Any) -> Any:
        response = self.api.get(path, params={k: v for k, v in params.items() if v})
        return self._unwrap(response)

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._unwrap(self.api.post(path, json=payload))

    @staticmethod
    def _unwrap(response: httpx.Response) -> Any:
        if response.status_code >= 400:
            detail = response.json().get("detail", response.text) if response.content else response.reason_phrase
            raise ToolError(f"Tracker returned {response.status_code}: {detail}")
        return response.json()

    # ---------- read tools ----------
    def search_issues(
        self, query: str = "", state: str = "", priority: str = "", component: str = ""
    ) -> dict[str, Any]:
        args = {"query": query, "state": state, "priority": priority, "component": component}

        def action() -> dict[str, Any]:
            if priority and priority not in PRIORITIES:
                raise ToolError("priority must be one of P1, P2, P3, P4")
            if query:
                _text(query, "query", 1, 200)
            issues = self._get("/issues", q=query, state=state, priority=priority, component=component)
            return {"count": len(issues), "items": issues[:25]}

        return self._call("search_issues", args, action)

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            number = _positive_int(issue_id, "issue_id")
            return {
                "issue": self._get(f"/issues/{number}"),
                "comments": self._get(f"/issues/{number}/comments"),
                "history": self._get(f"/issues/{number}/history"),
            }

        return self._call("get_issue", {"issue_id": issue_id}, action)

    def find_duplicates(self, text: str, top_n: int = 5) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            report = _text(text, "text", 5, 2000)
            limit = _positive_int(top_n, "top_n")
            issues = self._get("/issues")
            if not issues:
                return {"matches": []}
            matches = DuplicateFinder(issues).similar_to(report, min(limit, 10))
            return {"matches": [m.__dict__ for m in matches]}

        return self._call("find_duplicates", {"text": text, "top_n": top_n}, action)

    def list_test_cases(self, component: str = "") -> dict[str, Any]:
        def action() -> dict[str, Any]:
            cases = self._get("/test-cases", component=component)
            return {"count": len(cases), "items": cases[:50]}

        return self._call("list_test_cases", {"component": component}, action)

    def get_test_results(self, run_id: int = 0) -> dict[str, Any]:
        """Results of one test run, or a summary of all runs when run_id is 0."""
        def action() -> dict[str, Any]:
            if run_id:
                return {"run": self._get(f"/test-runs/{_positive_int(run_id, 'run_id')}")}
            runs = self._get("/test-runs")
            return {"runs": [{"id": r["id"], "suite_id": r["suite_id"], "status": r["status"],
                              "results": len(r["results"])} for r in runs]}

        return self._call("get_test_results", {"run_id": run_id}, action)

    def run_tests(self, keyword: str) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            if not isinstance(keyword, str) or not KEYWORD_PATTERN.match(keyword):
                raise ToolError("keyword must be 1-60 letters, digits, underscores or spaces")
            return self.test_runner(keyword)

        return self._call("run_tests", {"keyword": keyword}, action)

    # ---------- write tools (need allow_write) ----------
    def create_issue(self, title: str, component: str, description: str = "", priority: str = "P3") -> dict[str, Any]:
        args = {"title": title, "component": component, "description": description, "priority": priority}

        def action() -> dict[str, Any]:
            if priority not in PRIORITIES:
                raise ToolError("priority must be one of P1, P2, P3, P4")
            payload = {
                "title": _text(title, "title", 3, 200),
                "component": _text(component, "component", 1, 100),
                "description": _text(description, "description", 0, 5000),
                "priority": priority,
            }
            return self._post("/issues", payload)

        return self._call("create_issue", args, action)

    def add_comment(self, issue_id: int, body: str) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            number = _positive_int(issue_id, "issue_id")
            return self._post(f"/issues/{number}/comments", {"body": _text(body, "body", 1, 5000)})

        return self._call("add_comment", {"issue_id": issue_id, "body": body}, action)
