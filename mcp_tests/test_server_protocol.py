"""Talk to the server through a real MCP client (in-memory transport) to test the protocol layer."""
import asyncio

from mcp import Client

from mcp_server.server import build_server
from mcp_server.tools import TrackerTools

ALL_TOOLS = {
    "search_issues", "get_issue", "find_duplicates", "list_test_cases",
    "get_test_results", "run_tests", "create_issue", "add_comment",
}


def with_client(tracker, allow_write, action):
    async def go():
        server = build_server(TrackerTools(tracker.api, allow_write=allow_write))
        async with Client(server) as client:
            return await action(client)

    return asyncio.run(go())


def test_lists_all_eight_tools(tracker):
    async def action(client):
        return {t.name for t in (await client.list_tools()).tools}

    assert with_client(tracker, False, action) == ALL_TOOLS


def test_tools_have_input_schemas(tracker):
    async def action(client):
        return {t.name: t.input_schema for t in (await client.list_tools()).tools}

    schemas = with_client(tracker, False, action)
    assert "issue_id" in schemas["get_issue"]["properties"]


def test_read_tool_returns_structured_data(tracker):
    issue = tracker.create("Mailbox sync stuck")

    async def action(client):
        return await client.call_tool("get_issue", {"issue_id": issue["id"]})

    result = with_client(tracker, False, action)
    assert not result.is_error and result.structured_content["issue"]["title"] == "Mailbox sync stuck"


def test_write_tool_is_an_error_in_read_only_mode(tracker):
    async def action(client):
        return await client.call_tool("create_issue", {"title": "Should not exist", "component": "Mail"})

    result = with_client(tracker, False, action)
    assert result.is_error and "read-only" in result.content[0].text
    assert tracker.issue_count() == 0


def test_write_tool_works_with_flag(tracker):
    async def action(client):
        return await client.call_tool("create_issue", {"title": "Created via MCP", "component": "Mail"})

    result = with_client(tracker, True, action)
    assert not result.is_error and tracker.issue_count() == 1


def test_validation_error_message_reaches_the_client(tracker):
    async def action(client):
        return await client.call_tool("get_issue", {"issue_id": 0})

    result = with_client(tracker, False, action)
    assert result.is_error and "positive integer" in result.content[0].text
