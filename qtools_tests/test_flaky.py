import pytest

from qtools.flaky import TestHistory, find_flaky, to_markdown
from qtools.junit import load_runs

P, F, S = "passed", "failed", "skipped"


@pytest.mark.parametrize(
    ("outcomes", "flips", "score"),
    [
        ([P, P, P, P], 0, 0.0),  # stable
        ([F, F, F, F], 0, 0.0),  # always failing
        ([P, P, F, F], 1, 1 / 3),  # regression
        ([P, F, P, F], 3, 1.0),  # very flaky
        ([P], 0, 0.0),  # too short
    ],
)
def test_history_score(outcomes, flips, score):
    history = TestHistory("t", outcomes)
    assert history.flips == flips
    assert history.score == pytest.approx(score)


def test_finds_only_the_flaky_test(make_runs):
    directory = make_runs(
        {
            "a::stable": [P, P, P, P, P],
            "a::broken": [F, F, F, F, F],
            "a::flaky": [P, F, P, F, P],
            "a::regressed": [P, P, P, F, F],
        }
    )
    findings = find_flaky(load_runs(directory))
    assert [f.test_id for f in findings] == ["a::flaky"]
    assert findings[0].score == 1.0 and findings[0].failures == 2


def test_most_flaky_listed_first(make_runs):
    directory = make_runs({"a::mild": [P, P, F, P, P, P], "a::bad": [P, F, P, F, P, F]})
    assert [f.test_id for f in find_flaky(load_runs(directory))] == ["a::bad", "a::mild"]


def test_skipped_runs_are_ignored(make_runs):
    directory = make_runs({"a::t": [P, S, S, F, P]})
    finding = find_flaky(load_runs(directory), min_runs=3, threshold=0.0)[0]
    assert finding.runs == 3


def test_min_runs_filters_short_histories(make_runs):
    directory = make_runs({"a::t": [P, F]})
    assert find_flaky(load_runs(directory), min_runs=3) == []


def test_markdown_for_empty_result():
    assert "No flaky tests" in to_markdown([], total_runs=5)


def test_missing_directory_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_runs(tmp_path)
