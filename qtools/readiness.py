"""Release readiness report: combines open issues, test pass rate, coverage and flakiness into GO / NO-GO."""
import html
from dataclasses import dataclass, field
from typing import Any, Optional

from qtools.flaky import FlakyFinding
from qtools.junit import RunResult


@dataclass
class Thresholds:
    max_open_p1: int = 0
    max_open_p2: int = 3
    min_pass_rate: float = 0.95
    min_coverage: float = 80.0
    max_flaky: int = 3


@dataclass
class Readiness:
    decision: str  # "GO" or "NO-GO"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    open_blockers: list[dict[str, Any]] = field(default_factory=list)


def is_open(issue: dict[str, Any]) -> bool:
    """Open = not Closed and not a duplicate of another issue."""
    return issue["state"] != "Closed" and not issue.get("duplicate_of")


def assess(
    issues: list[dict[str, Any]],
    latest_run: Optional[RunResult],
    coverage: Optional[float],
    flaky: list[FlakyFinding],
    thresholds: Optional[Thresholds] = None,
) -> Readiness:
    t = thresholds or Thresholds()
    open_issues = [i for i in issues if is_open(i)]
    p1 = [i for i in open_issues if i["priority"] == "P1"]
    p2 = [i for i in open_issues if i["priority"] == "P2"]
    pass_rate = latest_run.pass_rate if latest_run else None

    result = Readiness(decision="GO")
    result.metrics = {
        "open_issues": len(open_issues),
        "open_p1": len(p1),
        "open_p2": len(p2),
        "pass_rate": None if pass_rate is None else round(pass_rate * 100, 1),
        "coverage": coverage,
        "flaky_tests": len(flaky),
    }
    result.open_blockers = [{"id": i["id"], "title": i["title"], "priority": i["priority"]} for i in p1 + p2]

    if len(p1) > t.max_open_p1:
        result.blockers.append(f"{len(p1)} open P1 issue(s): ship-stoppers must be fixed first")
    if len(p2) > t.max_open_p2:
        result.blockers.append(f"{len(p2)} open P2 issues (limit {t.max_open_p2})")
    elif p2:
        result.warnings.append(f"{len(p2)} open P2 issue(s) accepted within the limit of {t.max_open_p2}")
    if pass_rate is None:
        result.blockers.append("No test results available")
    elif pass_rate < t.min_pass_rate:
        result.blockers.append(f"Pass rate {pass_rate:.1%} is below the {t.min_pass_rate:.0%} requirement")
    if coverage is None:
        result.warnings.append("Coverage not provided")
    elif coverage < t.min_coverage:
        result.blockers.append(f"Coverage {coverage}% is below the {t.min_coverage:.0f}% requirement")
    if len(flaky) > t.max_flaky:
        result.warnings.append(f"{len(flaky)} flaky tests (limit {t.max_flaky}): results may be unreliable")

    result.decision = "NO-GO" if result.blockers else "GO"
    return result


def to_markdown(r: Readiness) -> str:
    m = r.metrics
    lines = [f"# Release readiness: {r.decision}", ""]
    if r.blockers:
        lines += ["## Blockers", *[f"- {b}" for b in r.blockers], ""]
    if r.warnings:
        lines += ["## Warnings", *[f"- {w}" for w in r.warnings], ""]
    lines += [
        "## Metrics",
        "| Metric | Value |", "|---|---|",
        f"| Open issues | {m['open_issues']} |",
        f"| Open P1 | {m['open_p1']} |",
        f"| Open P2 | {m['open_p2']} |",
        f"| Latest pass rate | {m['pass_rate']}% |" if m["pass_rate"] is not None else "| Latest pass rate | n/a |",
        f"| Coverage | {m['coverage']}% |" if m["coverage"] is not None else "| Coverage | n/a |",
        f"| Flaky tests | {m['flaky_tests']} |",
    ]
    if r.open_blockers:
        lines += ["", "## Open P1/P2 issues", "| ID | Priority | Title |", "|---|---|---|"]
        lines += [f"| {i['id']} | {i['priority']} | {i['title']} |" for i in r.open_blockers]
    return "\n".join(lines) + "\n"


def to_html(r: Readiness) -> str:
    colour = "#1a7f37" if r.decision == "GO" else "#b42318"

    def items(values: list[str]) -> str:
        return "".join(f"<li>{html.escape(v)}</li>" for v in values) or "<li>none</li>"

    rows = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>" for k, v in r.metrics.items()
    )
    issues = "".join(
        f"<tr><td>{i['id']}</td><td>{i['priority']}</td><td>{html.escape(i['title'])}</td></tr>"
        for i in r.open_blockers
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Release readiness</title>"
        "<style>body{font-family:system-ui;max-width:760px;margin:2em auto}"
        "td,th{border-bottom:1px solid #ddd;padding:4px 8px;text-align:left}</style></head><body>"
        f"<h1>Release readiness: <span style='color:{colour}'>{r.decision}</span></h1>"
        f"<h2>Blockers</h2><ul>{items(r.blockers)}</ul>"
        f"<h2>Warnings</h2><ul>{items(r.warnings)}</ul>"
        f"<h2>Metrics</h2><table>{rows}</table>"
        f"<h2>Open P1/P2 issues</h2><table><tr><th>ID</th><th>Priority</th><th>Title</th></tr>{issues}</table>"
        "</body></html>"
    )
