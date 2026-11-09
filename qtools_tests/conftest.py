"""Helpers that build JUnit XML runs for qtools tests."""
from pathlib import Path

import pytest


def write_run(directory: Path, number: int, results: dict[str, str], times: dict[str, float] | None = None, props=None):
    """results maps 'class::name' -> passed|failed|skipped."""
    times = times or {}
    props = props or {}
    cases = []
    for test_id, status in results.items():
        classname, name = test_id.split("::")
        inner = ""
        if status == "failed":
            inner = '<failure message="boom">boom</failure>'
        elif status == "skipped":
            inner = "<skipped/>"
        if test_id in props:
            inner += f'<properties><property name="issue" value="{props[test_id]}"/></properties>'
        cases.append(
            f'<testcase classname="{classname}" name="{name}" time="{times.get(test_id, 0.1)}">{inner}</testcase>'
        )
    xml = f'<testsuite name="s">{"".join(cases)}</testsuite>'
    (directory / f"run-{number:03d}.xml").write_text(xml, encoding="utf-8")


@pytest.fixture
def make_runs(tmp_path):
    """make_runs({'a::t': ['passed','failed',...]}) writes one file per position."""

    def _make(histories: dict[str, list[str]], **kwargs):
        length = len(next(iter(histories.values())))
        for n in range(length):
            write_run(tmp_path, n + 1, {t: h[n] for t, h in histories.items()}, **kwargs)
        return tmp_path

    return _make
