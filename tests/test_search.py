"""Search, filters and the component hierarchy."""
import pytest

from tests.factories import move, new_issue


@pytest.fixture
def sample_issues(client, reporter, engineer):
    ids = {
        "sync": new_issue(client, reporter, title="Sync fails on large mailbox", component="Mail > Sync", priority="P1"),
        "compose": new_issue(client, reporter, title="Compose window flickers", component="Mail > Compose", priority="P3"),
        "calendar": new_issue(client, reporter, title="Calendar shows wrong day", component="Calendar", priority="P3"),
    }
    move(client, engineer, ids["compose"]["id"], "Integrate")
    return ids


def titles(response):
    return sorted(i["title"] for i in response.json())


def test_text_search_matches_title(client, reporter, sample_issues):
    assert titles(client.get("/api/issues", params={"q": "flickers"}, headers=reporter)) == [
        "Compose window flickers"
    ]


def test_text_search_matches_description(client, reporter):
    new_issue(client, reporter, title="Plain title", description="contains the word zebra")
    assert len(client.get("/api/issues", params={"q": "zebra"}, headers=reporter).json()) == 1


def test_filter_by_state(client, reporter, sample_issues):
    r = client.get("/api/issues", params={"state": "Integrate"}, headers=reporter)
    assert titles(r) == ["Compose window flickers"]


def test_filter_by_priority_p1(client, reporter, sample_issues):
    r = client.get("/api/issues", params={"priority": "P1"}, headers=reporter)
    assert titles(r) == ["Sync fails on large mailbox"]


def test_parent_component_includes_children(client, reporter, sample_issues):
    r = client.get("/api/issues", params={"component": "Mail"}, headers=reporter)
    assert len(r.json()) == 2


def test_child_component_is_narrower(client, reporter, sample_issues):
    r = client.get("/api/issues", params={"component": "Mail > Sync"}, headers=reporter)
    assert titles(r) == ["Sync fails on large mailbox"]


def test_unknown_component_filter_is_404(client, reporter):
    assert client.get("/api/issues", params={"component": "Ghost"}, headers=reporter).status_code == 404


def test_combined_filters(client, reporter, sample_issues):
    r = client.get("/api/issues", params={"component": "Mail", "state": "Analyze"}, headers=reporter)
    assert titles(r) == ["Sync fails on large mailbox"]


def test_no_match_returns_empty_list(client, reporter, sample_issues):
    assert client.get("/api/issues", params={"q": "nothing-like-this"}, headers=reporter).json() == []
