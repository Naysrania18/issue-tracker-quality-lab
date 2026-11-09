import asyncio
import json

import pytest

from agent.llm import AnthropicLLM
from agent.schema import validate_draft
from agent.triage_agent import AgentError, TriageAgent
from mcp_server.tools import AuditLog, TrackerTools
from mcp_tests.conftest import FakeLLM, tool_use, valid_draft

REPORT = {"title": "Sync hangs on large mailbox", "description": "Spinner never stops"}


def run_agent(tracker, turns, tmp_path, allow_write=False):
    llm = FakeLLM(turns)
    tools = TrackerTools(tracker.api, allow_write=allow_write, audit=AuditLog(None),
                         test_runner=lambda k: {"keyword": k, "summary": "3 passed", "exit_code": 0})
    agent = TriageAgent(llm, tools, tmp_path / "review")
    return llm, agent, lambda: asyncio.run(agent.run(REPORT))


def test_full_flow_saves_a_validated_draft(tracker, tmp_path):
    tracker.create("Mailbox sync stuck", "Sync never finishes")
    turns = [
        [tool_use("find_duplicates", {"text": "Sync hangs on large mailbox"}, "a")],
        [tool_use("run_tests", {"keyword": "sync"}, "b")],
        [tool_use("submit_draft", valid_draft(), "c")],
    ]
    llm, _, run = run_agent(tracker, turns, tmp_path)
    path = run()
    saved = json.loads(path.with_suffix(".json").read_text())
    assert validate_draft(saved) == [] and saved["requires_human_review"] is True
    assert "DRAFT" in path.read_text()
    # tool results were fed back to the model
    last_user = llm.messages_seen[-1][-1]["content"][0]
    assert last_user["type"] == "tool_result" and "3 passed" in last_user["content"]


def test_write_tools_are_never_offered_to_the_model(tracker, tmp_path):
    llm, _, run = run_agent(tracker, [[tool_use("submit_draft", valid_draft())]], tmp_path, allow_write=True)
    run()
    offered = set(llm.seen_tools[0])
    assert "create_issue" not in offered and "add_comment" not in offered
    assert {"find_duplicates", "run_tests", "submit_draft"} <= offered


def test_model_cannot_call_write_tool_anyway(tracker, tmp_path):
    turns = [
        [tool_use("create_issue", {"title": "Sneaky issue", "component": "Mail"}, "x")],
        [tool_use("submit_draft", valid_draft(), "y")],
    ]
    llm, _, run = run_agent(tracker, turns, tmp_path, allow_write=True)
    run()
    assert tracker.issue_count() == 0
    refusal = llm.messages_seen[1][-1]["content"][0]
    assert refusal["is_error"] and "not available" in refusal["content"]


def test_invalid_draft_is_rejected_then_fixed(tracker, tmp_path):
    bad = valid_draft(suggested_priority="P9")
    turns = [[tool_use("submit_draft", bad, "a")], [tool_use("submit_draft", valid_draft(), "b")]]
    llm, _, run = run_agent(tracker, turns, tmp_path)
    run()
    feedback = llm.messages_seen[1][-1]["content"][0]
    assert feedback["is_error"] and "suggested_priority" in feedback["content"]


def test_agent_never_changes_the_tracker(tracker, tmp_path):
    tracker.create("Existing issue one")
    before = tracker.api.get("/issues").json()
    _, _, run = run_agent(tracker, [[tool_use("submit_draft", valid_draft())]], tmp_path)
    run()
    assert tracker.api.get("/issues").json() == before


def test_tool_errors_are_passed_back_not_raised(tracker, tmp_path):
    turns = [[tool_use("get_issue", {"issue_id": 999}, "a")], [tool_use("submit_draft", valid_draft(), "b")]]
    llm, _, run = run_agent(tracker, turns, tmp_path)
    run()
    assert llm.messages_seen[1][-1]["content"][0]["is_error"] is True


def test_model_without_tool_call_fails(tracker, tmp_path):
    _, _, run = run_agent(tracker, [[{"type": "text", "text": "I think it's a bug."}]], tmp_path)
    with pytest.raises(AgentError, match="without submitting"):
        run()


def test_gives_up_after_max_steps(tracker, tmp_path):
    turns = [[tool_use("search_issues", {}, str(i))] for i in range(8)]
    _, _, run = run_agent(tracker, turns, tmp_path)
    with pytest.raises(AgentError, match="No valid draft"):
        run()


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"requires_human_review": False}, "requires_human_review"),
        ({"kind": "closed_issue"}, "kind"),
        ({"steps_to_reproduce": []}, "steps_to_reproduce"),
        ({"extra": 1}, "extra"),
    ],
)
def test_schema_rejects_bad_drafts(change, fragment):
    problems = validate_draft(valid_draft(**change))
    assert problems and any(fragment in p for p in problems)


def test_missing_api_key_gives_clear_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicLLM()
