"""Generate fake JUnit XML for 10 runs so the tools can be demonstrated: python -m qtools.sample_data."""
import random
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

TESTS = {
    "tests.test_login::test_valid_login": ("stable", 0.2),
    "tests.test_login::test_wrong_password": ("stable", 0.2),
    "tests.test_search::test_search_by_title": ("stable", 0.4),
    "tests.test_search::test_search_is_case_insensitive": ("bug", 0.4),   # always fails: BUG-003
    "tests.test_sync::test_large_mailbox_sync": ("flaky", 2.8),           # timing dependent
    "tests.test_sync::test_sync_after_reconnect": ("flaky", 1.9),
    "tests.test_ui::test_attachment_preview": ("flaky_rare", 1.2),
    "tests.test_workflow::test_cannot_close_without_verify": ("regressed", 0.3),  # breaks from run 7
    "tests.test_calendar::test_invite_time_zone": ("stable", 0.6),
    "tests.test_calendar::test_recurring_invite": ("stable", 0.7),
    "tests.test_compose::test_dark_mode_text": ("failing_no_issue", 0.5),
    "tests.test_compose::test_send_message": ("stable", 0.5),
}


def outcome(kind: str, run: int, rng: random.Random) -> str:
    if kind == "stable":
        return "passed"
    if kind == "bug":
        return "failed"
    if kind == "flaky":
        return "failed" if rng.random() < 0.45 else "passed"
    if kind == "flaky_rare":
        return "failed" if rng.random() < 0.2 else "passed"
    if kind == "regressed":
        return "failed" if run >= 7 else "passed"
    return "failed" if run >= 9 else "passed"  # failing_no_issue starts failing in the last two runs


def build_xml(run: int, rng: random.Random) -> str:
    cases = []
    for test_id, (kind, base_time) in TESTS.items():
        classname, name = test_id.split("::")
        status = outcome(kind, run, rng)
        time = round(base_time * rng.uniform(0.8, 1.2), 3)
        body = ""
        if status == "failed":
            msg = "AssertionError: expected true"
            if kind == "bug":
                msg += " (BUG-003)"
            body = f"<failure message={quoteattr(msg)}>{msg}</failure>"
        cases.append(f'    <testcase classname="{classname}" name="{name}" time="{time}">{body}</testcase>')
    failures = sum("<failure" in c for c in cases)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuite name="demo" tests="{len(cases)}" failures="{failures}">\n' + "\n".join(cases) + "\n</testsuite>\n"
    )


def generate(out_dir: Path, runs: int = 10, seed: int = 11) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    for n in range(1, runs + 1):
        (out_dir / f"run-{n:03d}.xml").write_text(build_xml(n, rng), encoding="utf-8")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/junit_runs")
    generate(target)
    print(f"Wrote sample JUnit runs to {target}")
