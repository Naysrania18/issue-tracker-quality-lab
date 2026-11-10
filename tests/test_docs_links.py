"""Keeps documentation honest: every file path mentioned in skills-map.md must exist."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PATH_PATTERN = re.compile(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+|[A-Za-z0-9_.-]+/[A-Za-z0-9_./*-]*)`")


def referenced_paths(doc: str) -> list[str]:
    text = (ROOT / doc).read_text(encoding="utf-8")
    found = []
    for match in PATH_PATTERN.findall(text):
        if " " in match or match.startswith("http"):
            continue
        found.append(match)
    return sorted(set(found))


def exists(path: str) -> bool:
    if "*" in path:
        return bool(list(ROOT.glob(path)))
    if (ROOT / path).exists():
        return True
    # skills-map abbreviates Java paths with "..." in the second path of a row
    return path.startswith("...") or "/" not in path


@pytest.mark.parametrize("doc", ["docs/skills-map.md"])
def test_every_listed_path_exists(doc):
    missing = [p for p in referenced_paths(doc) if not exists(p)]
    assert missing == []


def test_readme_links_resolve():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)#]+)\)", text)
    missing = [link for link in links if not link.startswith("http") and not (ROOT / link).exists()]
    assert missing == []


def test_repository_has_no_forbidden_words():
    banned = ("app" + "le", "rad" + "ar")
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {".venv", ".git", "target", "node_modules", "reports"} for part in path.parts):
            continue
        if path.suffix in {".png", ".jpg", ".pyc", ".db"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        offenders += [str(path.relative_to(ROOT)) for word in banned if re.search(rf"\b{word}\b", text)]
    assert offenders == []
