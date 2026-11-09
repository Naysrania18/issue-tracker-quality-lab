"""JSON schema for the agent's DRAFT output. Anything that does not match is rejected, not saved."""
from typing import Any

import jsonschema

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "kind", "title", "summary", "duplicates", "tests_run", "reproduction",
        "suggested_priority", "steps_to_reproduce", "expected", "actual", "confidence", "requires_human_review",
    ],
    "properties": {
        "kind": {"enum": ["bug_report", "verification_note", "duplicate_note"]},
        "title": {"type": "string", "minLength": 5, "maxLength": 200},
        "summary": {"type": "string", "minLength": 10, "maxLength": 2000},
        "duplicates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["issue_id", "score", "reason"],
                "properties": {
                    "issue_id": {"type": "integer", "minimum": 1},
                    "score": {"type": "number", "minimum": 0, "maximum": 1},
                    "reason": {"type": "string"},
                },
            },
        },
        "tests_run": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["keyword", "summary"],
                "properties": {"keyword": {"type": "string"}, "summary": {"type": "string"}},
            },
        },
        "reproduction": {
            "type": "object",
            "additionalProperties": False,
            "required": ["result", "notes"],
            "properties": {
                "result": {"enum": ["reproduced", "not_reproduced", "not_attempted"]},
                "notes": {"type": "string"},
            },
        },
        "suggested_priority": {"enum": ["P1", "P2", "P3", "P4"]},
        "steps_to_reproduce": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "expected": {"type": "string"},
        "actual": {"type": "string"},
        "confidence": {"enum": ["low", "medium", "high"]},
        "requires_human_review": {"const": True},
    },
}


def validate_draft(draft: dict[str, Any]) -> list[str]:
    """Return a list of human-readable problems (empty when the draft is valid)."""
    validator = jsonschema.Draft202012Validator(DRAFT_SCHEMA)
    return [f"{'/'.join(map(str, e.path)) or 'draft'}: {e.message}" for e in validator.iter_errors(draft)]
