"""Flaky test detector.

Idea: a flaky test flips between pass and fail across runs of the *same* code. We count the flips and
divide by the number of possible flips, giving a score between 0 (stable) and 1 (flips every run).

  pass pass pass pass  -> 0 flips, score 0.0   stable
  fail fail fail fail  -> 0 flips, score 0.0   consistently failing (a real bug, not flaky)
  pass pass fail fail  -> 1 flip,  score 0.33  a regression, not flakiness
  pass fail pass fail  -> 3 flips, score 1.0   very flaky
"""
from dataclasses import dataclass

from qtools.junit import RunResult


@dataclass
class TestHistory:
    __test__ = False  # not a pytest test class

    test_id: str
    outcomes: list[str]  # "passed"/"failed" per run, skipped runs removed

    @property
    def runs(self) -> int:
        return len(self.outcomes)

    @property
    def failures(self) -> int:
        return self.outcomes.count("failed")

    @property
    def flips(self) -> int:
        return sum(1 for a, b in zip(self.outcomes, self.outcomes[1:], strict=False) if a != b)

    @property
    def score(self) -> float:
        if self.runs < 2:
            return 0.0
        return self.flips / (self.runs - 1)

    @property
    def is_mixed(self) -> bool:
        return 0 < self.failures < self.runs


@dataclass
class FlakyFinding:
    test_id: str
    runs: int
    failures: int
    flips: int
    score: float


def build_histories(runs: list[RunResult]) -> dict[str, TestHistory]:
    histories: dict[str, TestHistory] = {}
    for run in runs:
        for case in run.executed:
            histories.setdefault(case.test_id, TestHistory(case.test_id, [])).outcomes.append(case.status)
    return histories


def find_flaky(runs: list[RunResult], min_runs: int = 3, threshold: float = 0.3) -> list[FlakyFinding]:
    """Return tests whose flip score is at or above `threshold`, most flaky first."""
    findings = [
        FlakyFinding(h.test_id, h.runs, h.failures, h.flips, round(h.score, 2))
        for h in build_histories(runs).values()
        if h.runs >= min_runs and h.is_mixed and h.score >= threshold
    ]
    return sorted(findings, key=lambda f: (-f.score, f.test_id))


def to_markdown(findings: list[FlakyFinding], total_runs: int) -> str:
    lines = [f"# Flaky test report ({total_runs} runs analysed)", ""]
    if not findings:
        return "\n".join(lines + ["No flaky tests found."])
    lines += ["| Test | Runs | Failures | Flips | Score |", "|---|---|---|---|---|"]
    lines += [f"| `{f.test_id}` | {f.runs} | {f.failures} | {f.flips} | {f.score} |" for f in findings]
    return "\n".join(lines)
