"""Command line entry point:  python -m qtools <command> --help"""
import json
from pathlib import Path
from typing import Optional

import typer

from qtools import duplicates, flaky, health, readiness
from qtools.junit import load_runs
from qtools.sources import coverage_from_xml, issues_from_db, issues_from_file

app = typer.Typer(help="Quality tools for the demo issue tracker.", no_args_is_help=True)


def _load_issues(db: Optional[str], issues_file: Optional[str]) -> list:
    if db:
        return issues_from_db(db)
    if issues_file:
        return issues_from_file(issues_file)
    raise typer.BadParameter("Give --db or --issues-file")


@app.command("flaky")
def flaky_command(
    runs_dir: Path = typer.Argument(..., help="Folder of JUnit XML files, one per run"),
    min_runs: int = typer.Option(3, help="Ignore tests seen in fewer runs"),
    threshold: float = typer.Option(0.3, help="Minimum flip score to report"),
    as_json: bool = typer.Option(False, "--json", help="Print JSON instead of Markdown"),
):
    """Score tests by how often they flip between pass and fail."""
    runs = load_runs(runs_dir)
    findings = flaky.find_flaky(runs, min_runs, threshold)
    if as_json:
        typer.echo(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        typer.echo(flaky.to_markdown(findings, len(runs)))


@app.command("duplicates")
def duplicates_command(
    text: str = typer.Argument(..., help="Title and description of the new report"),
    db: Optional[str] = typer.Option(None, help="SQLite database of the tracker"),
    issues_file: Optional[str] = typer.Option(None, help="JSON file with existing issues"),
    threshold: float = typer.Option(0.26),
    top: int = typer.Option(5),
):
    """Find existing issues similar to a new report."""
    finder = duplicates.DuplicateFinder(_load_issues(db, issues_file), threshold)
    matches = finder.similar_to(text, top)
    if not matches:
        typer.echo("No likely duplicates.")
    for m in matches:
        typer.echo(f"#{m.issue_id}  score {m.score}  {m.title}")


@app.command("duplicates-eval")
def duplicates_eval(
    dataset: Path = typer.Option(Path("data/labelled_duplicates.json"), help="Labelled dataset"),
):
    """Measure precision and recall of the duplicate finder on a labelled dataset."""
    data = json.loads(dataset.read_text(encoding="utf-8"))
    typer.echo("threshold  precision  recall    f1")
    for e in duplicates.sweep(data["issues"], data["duplicate_pairs"], [0.2, 0.22, 0.24, 0.26, 0.28, 0.3]):
        typer.echo(f"{e.threshold:<10} {e.precision:<10} {e.recall:<9} {e.f1}")


@app.command("readiness")
def readiness_command(
    junit_dir: Path = typer.Option(..., help="Folder of JUnit XML files (latest file = latest run)"),
    db: Optional[str] = typer.Option(None),
    issues_file: Optional[str] = typer.Option(None),
    coverage_xml: Optional[Path] = typer.Option(None, help="coverage.xml from pytest-cov"),
    coverage: Optional[float] = typer.Option(None, help="Coverage percent, if no XML"),
    out_dir: Path = typer.Option(Path("reports"), help="Where to write readiness.md and readiness.html"),
    fail_on_no_go: bool = typer.Option(False, help="Exit with code 1 when the decision is NO-GO"),
):
    """Decide GO / NO-GO for a release and write Markdown + HTML reports."""
    runs = load_runs(junit_dir)
    cov = coverage_from_xml(str(coverage_xml)) if coverage_xml else coverage
    result = readiness.assess(_load_issues(db, issues_file), runs[-1], cov, flaky.find_flaky(runs))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "readiness.md").write_text(readiness.to_markdown(result), encoding="utf-8")
    (out_dir / "readiness.html").write_text(readiness.to_html(result), encoding="utf-8")
    typer.echo(readiness.to_markdown(result))
    if fail_on_no_go and result.decision == "NO-GO":
        raise typer.Exit(code=1)


@app.command("health")
def health_command(runs_dir: Path = typer.Argument(..., help="Folder of JUnit XML files")):
    """Regression suite health: trend, slow tests, tests that never fail, failures with no issue."""
    typer.echo(health.to_markdown(health.analyse(load_runs(runs_dir))))


if __name__ == "__main__":
    app()
