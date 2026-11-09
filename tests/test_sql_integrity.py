"""Run the data-integrity queries from sql/ against a database that has been used through the API.

Each query returns the *bad* rows, so a healthy database gives an empty list.
"""
from pathlib import Path

import pytest

from tests.factories import new_issue, new_suite_with_case, walk_to

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

pytestmark = pytest.mark.sql


def run_check(conn, filename):
    return conn.execute((SQL_DIR / filename).read_text()).fetchall()


@pytest.fixture
def busy_database(client, reporter, engineer, qa, db):
    """Create realistic data using only legal API calls."""
    first = new_issue(client, reporter)
    second = new_issue(client, reporter, title="Another problem")
    walk_to(client, engineer, qa, first["id"], "Closed")
    client.post(f"/api/issues/{second['id']}/duplicate", json={"duplicate_of": first["id"]}, headers=engineer)
    suite_id, case_id = new_suite_with_case(client, qa)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    client.post(
        f"/api/test-runs/{run['id']}/results",
        json={"case_id": case_id, "status": "failed", "issue_id": second["id"]},
        headers=qa,
    )
    client.post(f"/api/test-runs/{run['id']}/complete", headers=qa)
    return db


@pytest.mark.parametrize(
    "query_file",
    [
        "01_closed_without_verify.sql",
        "02_self_duplicate.sql",
        "03_orphan_test_results.sql",
        "04_result_case_not_in_suite.sql",
        "05_completed_run_without_results.sql",
    ],
)
def test_healthy_database_has_no_violations(busy_database, query_file):
    assert run_check(busy_database, query_file) == []


# The tests below prove the queries really detect the problems they are meant to catch.

def test_query1_detects_issue_closed_via_patch_shortcut(client, reporter, engineer, db):
    issue = new_issue(client, reporter)
    client.patch(f"/api/issues/{issue['id']}", json={"state": "Closed"}, headers=engineer)  # BUG-001
    rows = run_check(db, "01_closed_without_verify.sql")
    assert [r["id"] for r in rows] == [issue["id"]]


def test_query2_detects_self_duplicate(client, reporter, engineer, db):
    issue = new_issue(client, reporter)
    client.post(f"/api/issues/{issue['id']}/duplicate", json={"duplicate_of": issue["id"]}, headers=engineer)  # BUG-002
    assert [r["id"] for r in run_check(db, "02_self_duplicate.sql")] == [issue["id"]]


def test_query3_detects_orphan_result(db):
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute("INSERT INTO test_results (run_id, case_id, status) VALUES (999, 1, 'passed')")
    assert len(run_check(db, "03_orphan_test_results.sql")) == 1


def test_query4_detects_result_outside_suite(client, qa, db):
    suite_id, _ = new_suite_with_case(client, qa)
    _, other_case = new_suite_with_case(client, qa, "Calendar")
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    db.execute("INSERT INTO test_results (run_id, case_id, status) VALUES (?,?, 'passed')", (run["id"], other_case))
    assert len(run_check(db, "04_result_case_not_in_suite.sql")) == 1


def test_query5_detects_completed_run_without_results(client, qa, db):
    suite_id, _ = new_suite_with_case(client, qa)
    run = client.post("/api/test-runs", json={"suite_id": suite_id}, headers=qa).json()
    client.post(f"/api/test-runs/{run['id']}/complete", headers=qa)
    assert [r["run_id"] for r in run_check(db, "05_completed_run_without_results.sql")] == [run["id"]]
