"""Regression suite health: where is the suite slow, stale or unlinked to any issue?"""
from dataclasses import dataclass
from statistics import mean

from qtools.flaky import build_histories
from qtools.junit import RunResult


@dataclass
class HealthReport:
    pass_rate_trend: list[tuple[str, float]]  # (run name, pass rate %)
    slowest: list[tuple[str, float]]  # (test id, average seconds)
    never_failed: list[str]  # candidates for review: do they still test anything useful?
    failing_without_issue: list[str]  # failing in the latest run but linked to no issue


def analyse(runs: list[RunResult], top_n: int = 5, min_runs_for_never_failed: int = 5) -> HealthReport:
    durations: dict[str, list[float]] = {}
    for run in runs:
        for case in run.executed:
            durations.setdefault(case.test_id, []).append(case.duration)
    slowest = sorted(((t, round(mean(d), 3)) for t, d in durations.items()), key=lambda p: -p[1])[:top_n]

    never_failed = sorted(
        h.test_id for h in build_histories(runs).values()
        if h.runs >= min_runs_for_never_failed and h.failures == 0
    )
    latest = runs[-1]
    unlinked = sorted(c.test_id for c in latest.cases if c.status == "failed" and not c.linked_issue)
    return HealthReport(
        pass_rate_trend=[(r.name, round(r.pass_rate * 100, 1)) for r in runs],
        slowest=slowest,
        never_failed=never_failed,
        failing_without_issue=unlinked,
    )


def to_markdown(report: HealthReport) -> str:
    lines = ["# Regression suite health", "", "## Pass rate by run", "| Run | Pass rate |", "|---|---|"]
    lines += [f"| {name} | {rate}% |" for name, rate in report.pass_rate_trend]
    lines += ["", "## Slowest tests (average seconds)", "| Test | Seconds |", "|---|---|"]
    lines += [f"| `{t}` | {s} |" for t, s in report.slowest]
    lines += ["", f"## Never failed ({len(report.never_failed)} tests)"]
    lines += [f"- `{t}`" for t in report.never_failed[:10]] or ["- none"]
    lines += ["", f"## Failing in the latest run with no linked issue ({len(report.failing_without_issue)})"]
    lines += [f"- `{t}`" for t in report.failing_without_issue] or ["- none"]
    return "\n".join(lines) + "\n"
