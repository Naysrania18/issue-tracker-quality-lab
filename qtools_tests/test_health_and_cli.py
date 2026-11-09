import json

from typer.testing import CliRunner

from qtools.cli import app
from qtools.health import analyse
from qtools.junit import load_runs
from qtools.sources import coverage_from_xml, issues_from_db, issues_from_file

P, F = "passed", "failed"
runner = CliRunner()


def test_health_report(make_runs):
    directory = make_runs(
        {"a::always_ok": [P] * 5, "a::slow": [P] * 5, "a::new_failure": [P, P, P, P, F]},
        times={"a::slow": 9.0},
        props={"a::new_failure": "BUG-007"},
    )
    report = analyse(load_runs(directory), top_n=1)
    assert report.slowest[0][0] == "a::slow"
    assert "a::always_ok" in report.never_failed
    assert report.pass_rate_trend[-1][1] == round(2 / 3 * 100, 1)
    assert report.failing_without_issue == []  # it has an issue property


def test_failing_test_without_issue_is_reported(make_runs):
    directory = make_runs({"a::x": [P, P, F]})
    assert analyse(load_runs(directory)).failing_without_issue == ["a::x"]


def test_issue_found_in_failure_message(tmp_path):
    (tmp_path / "run-001.xml").write_text(
        '<testsuite><testcase classname="a" name="x"><failure message="see BUG-042">x</failure></testcase></testsuite>'
    )
    assert load_runs(tmp_path)[0].cases[0].linked_issue == "BUG-042"


def test_cli_flaky_json(make_runs):
    directory = make_runs({"a::flaky": [P, F, P, F]})
    result = runner.invoke(app, ["flaky", str(directory), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["test_id"] == "a::flaky"


def test_cli_readiness_writes_reports_and_can_fail(make_runs, tmp_path):
    runs = make_runs({"a::t": [P, P, P]})
    issues = tmp_path / "issues.json"
    issues.write_text(json.dumps([{"id": 1, "title": "Bad", "priority": "P1", "state": "Build", "duplicate_of": None}]))
    out = tmp_path / "out"
    args = ["readiness", "--junit-dir", str(runs), "--issues-file", str(issues), "--coverage", "90", "--out-dir", str(out)]
    assert runner.invoke(app, args).exit_code == 0  # reports only
    assert (out / "readiness.md").exists() and (out / "readiness.html").exists()
    assert runner.invoke(app, [*args, "--fail-on-no-go"]).exit_code == 1


def test_cli_readiness_go_exit_zero(make_runs, tmp_path):
    runs = make_runs({"a::t": [P, P, P]})
    issues = tmp_path / "issues.json"
    issues.write_text("[]")
    args = ["readiness", "--junit-dir", str(runs), "--issues-file", str(issues), "--coverage", "90",
            "--out-dir", str(tmp_path / "o"), "--fail-on-no-go"]
    assert runner.invoke(app, args).exit_code == 0


def test_cli_requires_an_issue_source(make_runs, tmp_path):
    runs = make_runs({"a::t": [P, P, P]})
    result = runner.invoke(app, ["readiness", "--junit-dir", str(runs), "--out-dir", str(tmp_path)])
    assert result.exit_code != 0


def test_cli_duplicates_command():
    result = runner.invoke(app, ["duplicates", "pdf attachment crashes the app", "--issues-file", "data/labelled_duplicates.json"])
    assert result.exit_code == 0 and "#6" in result.stdout


def test_cli_duplicates_eval_prints_table():
    result = runner.invoke(app, ["duplicates-eval"])
    assert result.exit_code == 0 and "precision" in result.stdout


def test_cli_health(make_runs):
    result = runner.invoke(app, ["health", str(make_runs({"a::t": [P, P]}))])
    assert "Regression suite health" in result.stdout


def test_sources(tmp_path):
    xml = tmp_path / "coverage.xml"
    xml.write_text('<coverage line-rate="0.873"></coverage>')
    assert coverage_from_xml(str(xml)) == 87.3
    assert issues_from_file("data/release_candidate_issues.json")[0]["id"] == 101


def test_issues_from_db(tmp_path):
    from app.seed import seed

    db = str(tmp_path / "t.db")
    seed(db, issue_count=5)
    issues = issues_from_db(db)
    assert len(issues) == 5 and {"id", "title", "priority", "state", "component"} <= issues[0].keys()
