"""MCP wiring: exposes TrackerTools as MCP tools over stdio.

Run:  python -m mcp_server            (read-only)
      python -m mcp_server --allow-write
Environment: TRACKER_URL (default http://127.0.0.1:8000/api), TRACKER_TOKEN (required),
             MCP_AUDIT_LOG (default reports/mcp-audit.log)
"""
import argparse
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from mcp_server.tools import AuditLog, TrackerTools


def build_server(tools: TrackerTools) -> MCPServer:
    server = MCPServer("issue-tracker-quality-lab")

    @server.tool()
    def search_issues(query: str = "", state: str = "", priority: str = "", component: str = "") -> dict[str, Any]:
        """Search issues by text, state (Analyze/Integrate/Build/Verify/Closed), priority (P1-P4) or component path."""
        return tools.search_issues(query, state, priority, component)

    @server.tool()
    def get_issue(issue_id: int) -> dict[str, Any]:
        """Get one issue with its comments and history."""
        return tools.get_issue(issue_id)

    @server.tool()
    def find_duplicates(text: str, top_n: int = 5) -> dict[str, Any]:
        """Find existing issues similar to a bug description. Returns issue ids with similarity scores."""
        return tools.find_duplicates(text, top_n)

    @server.tool()
    def list_test_cases(component: str = "") -> dict[str, Any]:
        """List test cases, optionally for one component (and its children)."""
        return tools.list_test_cases(component)

    @server.tool()
    def get_test_results(run_id: int = 0) -> dict[str, Any]:
        """Get one test run with its results, or a summary of all runs when run_id is 0."""
        return tools.get_test_results(run_id)

    @server.tool()
    def run_tests(keyword: str) -> dict[str, Any]:
        """Run this project's automated tests whose names match the keyword (letters, digits, spaces)."""
        return tools.run_tests(keyword)

    @server.tool()
    def create_issue(title: str, component: str, description: str = "", priority: str = "P3") -> dict[str, Any]:
        """WRITE: create an issue. Only works when the server was started with --allow-write."""
        return tools.create_issue(title, component, description, priority)

    @server.tool()
    def add_comment(issue_id: int, body: str) -> dict[str, Any]:
        """WRITE: add a comment to an issue. Only works when the server was started with --allow-write."""
        return tools.add_comment(issue_id, body)

    return server


def tools_from_environment(allow_write: bool) -> TrackerTools:
    token = os.environ.get("TRACKER_TOKEN")
    if not token:
        raise SystemExit("Set TRACKER_TOKEN (get one from POST /api/auth/login)")
    api = httpx.Client(
        base_url=os.environ.get("TRACKER_URL", "http://127.0.0.1:8000/api"),
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    audit = AuditLog(Path(os.environ.get("MCP_AUDIT_LOG", "reports/mcp-audit.log")))
    return TrackerTools(api, allow_write=allow_write, audit=audit)


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP server for the demo issue tracker")
    parser.add_argument("--allow-write", action="store_true", help="enable create_issue and add_comment")
    args = parser.parse_args()
    build_server(tools_from_environment(args.allow_write)).run("stdio")


if __name__ == "__main__":
    main()
