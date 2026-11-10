# Test strategy

Scope: the demo issue tracker (`app/`), the quality tools (`qtools/`), the MCP server and agent
(`mcp_server/`, `agent/`), and the clients (`java-api-tests/`, `swift-client/`).

## Goals

1. Catch regressions in workflow rules and permissions before release (these protect data trust).
2. Keep feedback fast: the whole Python suite runs in about a minute, smoke tests in about ten seconds.
3. Make quality visible: a readiness report turns test, coverage and issue data into GO / NO-GO.
4. Use AI help (duplicate finding, triage drafts) without giving it the power to change data.

## Test pyramid used here

| Level | Tool | Count (approx.) | What it covers | Where |
|-------|------|-----------------|----------------|-------|
| Unit | pytest | 48 (`qtools_tests/`) + 28 workflow cases | Workflow table, duplicate scoring, flaky scoring, readiness rules | `tests/test_workflow.py`, `qtools_tests/` |
| API / integration | pytest + FastAPI `TestClient` | about 80 | Endpoints, permissions, validation, events | `tests/` |
| Data integrity | pytest + SQL | 10 (of the 108 in `tests/`) | Rules that must hold across all data | `sql/`, `tests/test_sql_integrity.py` |
| Contract-style API suite | TestNG + RestAssured (Java) | 66 | Same API from another language and runner | `java-api-tests/` |
| Client unit | XCTest (Swift) | 21 | Decoding, request building, error mapping, client-side workflow check | `swift-client/Tests/` |
| UI end to end | Selenium + Page Objects | 13 | Real user journeys in Chrome | `ui_tests/` |
| MCP / agent | pytest, scripted fake LLM | 52 | Tool safety, protocol, agent loop, schema | `mcp_tests/` |
| Exploratory | Manual, chartered | 2 sessions | Finding what scripted tests do not | `docs/exploratory/` |

Rule of thumb: put each check at the lowest level that can see the problem. Workflow rules are tested as
pure functions (fast, exhaustive: all 25 state pairs). Selenium only checks that the pieces work together.

## Risk-based priorities

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Workflow bypass, issue closed unverified | Medium (two code paths) | High | Exhaustive transition tests, SQL check 01, strict xfail for BUG-001 |
| Wrong permissions (reporter can change state) | Low | High | Role matrix tests in Python and Java |
| Stored XSS in the web UI | Medium | High | UI test + xfail for BUG-005 |
| Search returns wrong issues | Medium | Medium | Search tests, planted bug tests |
| Notifications lost, duplicated or out of order | Medium | Low-Medium | Event tests |
| AI assistant changes data or runs arbitrary commands | Low | High | Read-only default, validation, audit log, no write tools for the agent |
| Flaky tests hide real failures | Medium | Medium | Flaky detector, suite health report |

## Test data

All data is fake. Python tests build their own data through the API (`tests/factories.py`), Java tests
create users with random suffixes, and `app/seed.py` uses `faker` with a fixed seed so runs are repeatable.
Every test uses its own database or unique names, so tests can run in any order.

## Known-defect handling

Tests for planted or found bugs state the **correct** behaviour and are marked `xfail(strict=True)`
(Python/Selenium) or live in a separate TestNG suite (Java). The pipeline stays green while the bug
exists, and when it is fixed the strict xfail fails loudly so the marker is removed.

## Entry and exit criteria for a release

- Entry: all smoke tests pass; no failing test without a linked, triaged issue.
- Exit (enforced by the CI gates in [ci-cd.md](ci-cd.md)): coverage at least 85%, pass rate at least 95%,
  no open P1, at most 3 open P2, flaky tests reviewed.

## Not covered (honest list)

Performance and load testing, accessibility, browsers other than Chrome, real concurrency (the demo uses
SQLite and one process), security testing beyond the XSS and permission checks, and Swift tests on iOS and macOS devices
(they run on Linux only, so no UIKit/AppKit code is exercised).
