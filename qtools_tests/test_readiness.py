import pytest

from qtools.flaky import FlakyFinding
from qtools.junit import CaseResult, RunResult
from qtools.readiness import Thresholds, assess, is_open, to_html, to_markdown


def issue(id_, priority="P3", state="Build", duplicate_of=None):
    return {"id": id_, "title": f"Issue {id_} <b>", "priority": priority, "state": state, "duplicate_of": duplicate_of}


def run_with(passed, failed):
    cases = [CaseResult(f"t{i}", "passed") for i in range(passed)] + [CaseResult(f"f{i}", "failed") for i in range(failed)]
    return RunResult("run", cases)


GOOD_RUN = run_with(99, 1)  # 99%


def test_clean_release_is_go():
    result = assess([issue(1, "P3")], GOOD_RUN, coverage=90, flaky=[])
    assert result.decision == "GO" and result.blockers == []


def test_any_open_p1_is_no_go():
    result = assess([issue(1, "P1")], GOOD_RUN, 90, [])
    assert result.decision == "NO-GO"
    assert "P1" in result.blockers[0]


def test_closed_and_duplicate_p1_do_not_block():
    issues = [issue(1, "P1", state="Closed"), issue(2, "P1", duplicate_of=1)]
    assert assess(issues, GOOD_RUN, 90, []).decision == "GO"


@pytest.mark.parametrize(("p2_count", "decision"), [(0, "GO"), (3, "GO"), (4, "NO-GO")])
def test_p2_limit(p2_count, decision):
    issues = [issue(i, "P2") for i in range(p2_count)]
    assert assess(issues, GOOD_RUN, 90, []).decision == decision


def test_some_p2_gives_warning_not_blocker():
    result = assess([issue(1, "P2")], GOOD_RUN, 90, [])
    assert result.warnings and not result.blockers


@pytest.mark.parametrize(("passed", "failed", "decision"), [(95, 5, "GO"), (94, 6, "NO-GO")])
def test_pass_rate_boundary(passed, failed, decision):
    assert assess([], run_with(passed, failed), 90, []).decision == decision


@pytest.mark.parametrize(("coverage", "decision"), [(80.0, "GO"), (79.9, "NO-GO")])
def test_coverage_boundary(coverage, decision):
    assert assess([], GOOD_RUN, coverage, []).decision == decision


def test_missing_results_block_release():
    assert assess([], None, 90, []).decision == "NO-GO"


def test_missing_coverage_only_warns():
    result = assess([], GOOD_RUN, None, [])
    assert result.decision == "GO" and "Coverage not provided" in result.warnings


def test_many_flaky_tests_warn():
    flaky = [FlakyFinding(f"t{i}", 10, 4, 5, 0.5) for i in range(4)]
    result = assess([], GOOD_RUN, 90, flaky, Thresholds(max_flaky=3))
    assert any("flaky" in w for w in result.warnings) and result.decision == "GO"


def test_is_open():
    assert is_open(issue(1)) and not is_open(issue(1, state="Closed")) and not is_open(issue(1, duplicate_of=5))


def test_markdown_lists_blockers_and_issues():
    text = to_markdown(assess([issue(7, "P1")], GOOD_RUN, 90, []))
    assert "NO-GO" in text and "| 7 | P1 |" in text


def test_html_escapes_issue_titles():
    page = to_html(assess([issue(7, "P1")], GOOD_RUN, 90, []))
    assert "&lt;b&gt;" in page and "<b>" not in page
