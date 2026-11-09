"""Load the inputs the tools need: issues (SQLite or JSON file) and coverage."""
import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ISSUE_QUERY = """
SELECT i.id, i.title, i.description, i.priority, i.state, i.duplicate_of, c.name AS component
FROM issues i JOIN components c ON c.id = i.component_id
ORDER BY i.id
"""


def issues_from_db(db_path: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(ISSUE_QUERY)]
    finally:
        conn.close()


def issues_from_file(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["issues"] if isinstance(data, dict) else data


def coverage_from_xml(path: str) -> float:
    """Read total line coverage (percent) from a coverage.py / Cobertura XML report."""
    root = ET.parse(path).getroot()
    return round(float(root.get("line-rate", "0")) * 100, 1)
