"""Read JUnit XML files (the format pytest, TestNG, Maven Surefire and XCTest converters all produce)."""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

ISSUE_PATTERN = re.compile(r"\bBUG-\d+\b")


@dataclass
class CaseResult:
    test_id: str  # "classname::name"
    status: str  # passed | failed | skipped
    duration: float = 0.0
    message: str = ""
    linked_issue: str = ""  # e.g. BUG-001, taken from a property, the name or the failure text


@dataclass
class RunResult:
    name: str  # file name, e.g. run-003.xml
    cases: list[CaseResult] = field(default_factory=list)

    @property
    def executed(self) -> list[CaseResult]:
        return [c for c in self.cases if c.status != "skipped"]

    @property
    def pass_rate(self) -> float:
        executed = self.executed
        if not executed:
            return 1.0
        return sum(1 for c in executed if c.status == "passed") / len(executed)


def _find_issue(case: ET.Element, text: str) -> str:
    for prop in case.iter("property"):
        if prop.get("name") == "issue":
            return prop.get("value", "")
    match = ISSUE_PATTERN.search(text)
    return match.group(0) if match else ""


def parse_file(path: Path) -> RunResult:
    root = ET.parse(path).getroot()
    run = RunResult(name=path.name)
    for case in root.iter("testcase"):
        classname = case.get("classname", "")
        name = case.get("name", "")
        test_id = f"{classname}::{name}" if classname else name
        status, message = "passed", ""
        for tag, mapped in (("failure", "failed"), ("error", "failed"), ("skipped", "skipped")):
            child = case.find(tag)
            if child is not None:
                status = mapped
                message = child.get("message", "") or (child.text or "")
                break
        run.cases.append(
            CaseResult(
                test_id=test_id,
                status=status,
                duration=float(case.get("time", "0") or 0),
                message=message.strip(),
                linked_issue=_find_issue(case, f"{name} {message}"),
            )
        )
    return run


def load_runs(directory: Path) -> list[RunResult]:
    """Load every *.xml in a folder. Files are ordered by name, so name them run-001.xml, run-002.xml ..."""
    files = sorted(Path(directory).glob("*.xml"))
    if not files:
        raise FileNotFoundError(f"No JUnit XML files found in {directory}")
    return [parse_file(f) for f in files]
