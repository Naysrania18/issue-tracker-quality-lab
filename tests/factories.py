"""Small helpers that build test data through the public API."""
from typing import Any


def new_issue(client, headers, **overrides: Any) -> dict:
    payload = {
        "title": "Calendar invite shows wrong time",
        "description": "Invite time is off by one hour",
        "component": "Mail > Sync",
        "priority": "P3",
    }
    payload.update(overrides)
    response = client.post("/api/issues", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def move(client, headers, issue_id: int, target: str):
    return client.post(f"/api/issues/{issue_id}/transition", json={"target": target}, headers=headers)


def walk_to(client, engineer, qa, issue_id: int, target: str) -> None:
    """Move an issue through the legal path until it reaches `target`."""
    path = ["Integrate", "Build", "Verify", "Closed"]
    for state in path[: path.index(target) + 1]:
        actor = qa if state == "Closed" else engineer
        response = move(client, actor, issue_id, state)
        assert response.status_code == 200, response.text


def new_suite_with_case(client, qa, component="Mail > Sync") -> tuple[int, int]:
    case = client.post(
        "/api/test-cases", json={"title": "Sync completes", "component": component}, headers=qa
    ).json()
    suite = client.post(
        "/api/suites", json={"name": f"Suite {case['id']}", "case_ids": [case["id"]]}, headers=qa
    ).json()
    return suite["id"], case["id"]
