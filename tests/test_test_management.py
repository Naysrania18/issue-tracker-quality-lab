"""Test cases, suites, runs and results."""
import pytest

from tests.factories import new_issue, new_suite_with_case


def test_only_qa_can_create_cases(client, engineer):
    r = client.post("/api/test-cases", json={"title": "Some case", "component": "Mail"}, headers=engineer)
    assert r.status_code == 403


def test_list_cases_filtered_by_component(client, qa):
    new_suite_with_case(client, qa, "Mail > Sync")
    new_suite_with_case(client, qa, "Calendar")
    mail = client.get("/api/test-cases", params={"component": "Mail"}, headers=qa).json()
    assert len(mail) == 1


def test_suite_with_unknown_case_is_404(client, qa):
    r = client.post("/api/suites", json={"name": "Broken", "case_ids": [999]}, headers=qa)
    assert r.status_code == 404


def test_duplicate_suite_name_conflicts(client, qa):
    client.post("/api/suites", json={"name": "Smoke"}, headers=qa)
    assert client.post("/api/suites", json={"name": "Smoke"}, headers=qa).status_code == 409


def test_run_lifecycle_passed(client, qa):
    suite_id, case_id = new_suite_with_case(client, qa)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    assert run["status"] == "running"
    client.post(f"/api/test-runs/{run['id']}/results", json={"case_id": case_id, "status": "passed"}, headers=qa)
    done = client.post(f"/api/test-runs/{run['id']}/complete", headers=qa).json()
    assert done["status"] == "passed" and done["completed_at"]


def test_one_failure_fails_the_run(client, reporter, qa):
    suite_id, case_id = new_suite_with_case(client, qa)
    issue = new_issue(client, reporter)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    client.post(
        f"/api/test-runs/{run['id']}/results",
        json={"case_id": case_id, "status": "failed", "issue_id": issue["id"]},
        headers=qa,
    )
    assert client.post(f"/api/test-runs/{run['id']}/complete", headers=qa).json()["status"] == "failed"


@pytest.mark.parametrize("statuses,expected", [(["passed", "skipped"], "passed"), (["skipped"], "passed")])
def test_skipped_results_do_not_fail_a_run(client, qa, statuses, expected):
    suite_id, case_id = new_suite_with_case(client, qa)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    for status in statuses:
        client.post(f"/api/test-runs/{run['id']}/results", json={"case_id": case_id, "status": status}, headers=qa)
    assert client.post(f"/api/test-runs/{run['id']}/complete", headers=qa).json()["status"] == expected


def test_cannot_add_result_after_completion(client, qa):
    suite_id, case_id = new_suite_with_case(client, qa)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    client.post(f"/api/test-runs/{run['id']}/complete", headers=qa)
    r = client.post(f"/api/test-runs/{run['id']}/results", json={"case_id": case_id, "status": "passed"}, headers=qa)
    assert r.status_code == 409


def test_result_for_case_outside_suite_rejected(client, qa):
    suite_id, _ = new_suite_with_case(client, qa)
    _, other_case = new_suite_with_case(client, qa, "Calendar")
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    r = client.post(f"/api/test-runs/{run['id']}/results", json={"case_id": other_case, "status": "passed"}, headers=qa)
    assert r.status_code == 404


def test_result_linked_to_missing_issue_rejected(client, qa):
    suite_id, case_id = new_suite_with_case(client, qa)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    r = client.post(
        f"/api/test-runs/{run['id']}/results",
        json={"case_id": case_id, "status": "failed", "issue_id": 999},
        headers=qa,
    )
    assert r.status_code == 404


def test_negative_duration_rejected(client, qa):
    suite_id, case_id = new_suite_with_case(client, qa)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    r = client.post(
        f"/api/test-runs/{run['id']}/results",
        json={"case_id": case_id, "status": "passed", "duration_ms": -5},
        headers=qa,
    )
    assert r.status_code == 422
