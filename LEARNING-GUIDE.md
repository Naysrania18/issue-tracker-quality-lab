# Learning guide

A plain-English tour of every important file: what it does and **why it is built that way**. Use it to prepare
to talk about the project. Start with "The big picture", then read the sections in any order.

## The big picture

There is one small program to test (the *demo issue tracker*) and many things built around it to test it and
measure its quality. The tracker is a stand-in for any internal bug-tracking tool. It has planted bugs so the
tests and tools have something real to find.

The idea that connects everything: **one set of rules (the workflow), checked from many sides** (unit tests,
API tests in two languages, browser tests, SQL checks, a Swift client). When several independent checks agree,
you can trust the result; when one of them disagrees, you have found something.

---

## 1. The demo tracker (`app/`)

| File | What it does | Why it is designed this way |
|------|--------------|-----------------------------|
| `app/main.py` | Builds the web application. `create_app(db_path)` takes the database file as a parameter. Also turns domain errors (not found, conflict...) into HTTP status codes. | Because the database is a parameter, every test gets its own empty database: no shared state, tests can run in any order. |
| `app/database.py` | The SQL table definitions and a `connect()` helper. | Plain `sqlite3` instead of an ORM so the SQL is visible. That matters because I test data integrity with SQL. |
| `app/workflow.py` | The rules for moving an issue between states, as a dictionary of allowed moves, plus a role rule (only QA closes). | Pure functions with no database or web code can be tested exhaustively and fast (all 25 state pairs). |
| `app/services.py` | The business logic: `IssueService`, `ComponentService`, `TestService`, `UserService`. | The web pages and the JSON API both call these classes, so a rule lives in one place. Planted bugs 1 to 3 live here. |
| `app/events.py` | A tiny in-memory event queue and a consumer that writes notifications. | Shows event-driven design in a small space. Out-of-order events are handled with a per-issue sequence number. Duplicate events are not (planted bug 4). |
| `app/routes_api.py` | The JSON endpoints. | Thin: checks the user, calls a service, returns the result. |
| `app/routes_web.py` and `app/templates/` | The server-rendered pages. Every important element has a stable `id`. | Stable ids make Selenium tests reliable. The `safe` filter on the description in `issue_detail.html` is planted bug 5. |
| `app/deps.py` | Authentication and role checks as FastAPI dependencies. | Permissions are declared next to each endpoint, easy to review. |
| `app/seed.py` | Fills a database with fake data using `faker` and a fixed random seed. | Same seed means the same data on every run, so demos and tests are repeatable. |

**How a request flows:** HTTP request, route function, dependency checks token and role, service method does
the work and writes to SQLite, the service publishes an event, after the response the consumer turns the event
into a notification row.

## 2. Tests in Python (`tests/`)

| File | What it tests | Interview point |
|------|---------------|-----------------|
| `tests/conftest.py` | Fixtures: a fresh app and database per test, plus logged-in users for each role. | Fixtures = set-up code reused by many tests; function scope keeps tests isolated. |
| `tests/factories.py` | Helper functions that create issues, move them, build suites through the public API. | Tests read like stories and set-up code is not repeated. |
| `tests/test_workflow.py` | Rules as pure functions; `parametrize` runs one test for every state pair. | Parametrized tests give wide coverage with little code. |
| `tests/test_issues_api.py`, `test_search.py`, `test_test_management.py` | Endpoint behaviour: status codes, permissions, validation, search filters, test runs. | Check success and failure paths, and who is allowed. |
| `tests/test_events.py` | Events are published, consumed, out-of-order ones ignored. | Async-style behaviour tested without real async. |
| `tests/test_sql_integrity.py` and `sql/*.sql` | Queries return *bad* rows; healthy data returns none. Each query is also proven to catch a bug. | A check that has never failed might be broken. Testing the checker matters. |
| `tests/test_planted_defects.py` | Tests of the correct behaviour, marked `xfail(strict=True)`. | The suite stays green while a bug is known. When fixed, strict xfail fails, forcing cleanup. |
| `tests/test_found_defects.py` | The same idea for bugs *I found* (BUG-006). | Shows exploratory work turned into automation. |
| `tests/test_docs_links.py` | Every file mentioned in the docs exists; no banned words. | Documentation can rot like code. This makes rot fail the build. |

## 3. Quality tools (`qtools/`)

| File | What it does | How it works, simply |
|------|--------------|----------------------|
| `qtools/junit.py` | Reads JUnit XML (a format almost every test tool can write). | One parser means every suite (pytest, TestNG, Swift) can feed the tools. |
| `qtools/flaky.py` | Scores how flaky each test is. | Count how often a test flips between pass and fail, divide by the number of possible flips. Always failing is a bug, failing since run 7 is a regression: neither is "flaky". |
| `qtools/duplicates.py` | Finds issues that describe the same problem. | Turn text into TF-IDF vectors (rare words count more), measure the angle between vectors (cosine similarity), report pairs above a threshold. Character n-grams make "crash" match "crashes". `evaluate()` computes precision and recall against labelled pairs. |
| `qtools/readiness.py` | GO / NO-GO from open P1/P2, pass rate, coverage, flaky count. | Plain rules with explicit thresholds and reasons. Boundary values are tested (95% passes, 94% fails). |
| `qtools/health.py` | Slowest tests, tests that never fail, failures with no linked issue. | Shows where a suite is slow or stale. |
| `qtools/cli.py` | Command line using `typer`. | Thin wrapper; logic stays testable in the other files. |
| `data/labelled_duplicates.json` | 22 hand-written issues with known duplicate pairs. | The "answer key" for measuring the duplicate finder. Small, so results are optimistic. |

**Precision and recall in one line:** precision = of the duplicates I reported, how many were real;
recall = of the real duplicates, how many I found.

## 4. MCP server and agent (`mcp_server/`, `agent/`)

| File | What it does | Why |
|------|--------------|-----|
| `mcp_server/tools.py` | The logic of the eight tools, no MCP code. Validates input, checks the write flag, logs every call. | Separating logic from the protocol makes it unit-testable. |
| `mcp_server/server.py` | Registers the tools with the MCP SDK and runs over stdio. | Thin wiring. |
| `agent/triage_agent.py` | Loop: model asks for tools, we run them through MCP, results go back, until the model submits a draft. | The model never touches the database. It can only call the tools we offer, and write tools are removed from its list. |
| `agent/schema.py` | JSON schema the final draft must satisfy (`requires_human_review` must be true). | Do not trust model output: validate it. |
| `agent/llm.py` | One small interface plus a real Anthropic implementation. | Tests pass a scripted fake, so no API key or network is needed. |
| `mcp_tests/` | Tool tests, protocol tests through a real MCP client, agent tests. | Safety properties are tested explicitly: write refused by default, unsafe keywords rejected, agent cannot change the tracker. |

**Safety story for an interview:** read-only by default; writes need a flag; inputs validated; every call
logged; the agent has no write tools and its output is a draft for a human; tool results are treated as data,
not instructions; the API key comes only from the environment.

## 5. Selenium (`ui_tests/`)

| File | What it does | Why |
|------|--------------|-----|
| `ui_tests/pages/*.py` | One class per page (`LoginPage`, `IssuesPage`, ...) with methods like `create(...)` or `move_to(...)`. | Page Object Model: tests say *what* to do, pages know *how*. If a button's id changes, one file changes. |
| `ui_tests/pages/base_page.py` | Shared helpers: find, click, type, wait. | **Explicit waits only, no `sleep`**. `click_and_wait_for_reload` waits for the old page to go away; this fixed a real race that made CI fail. |
| `ui_tests/conftest.py` | Starts the real app on a free port in a thread, launches headless Chrome, saves a screenshot when a test fails. | Tests run against a real server like a user would. |
| `ui_tests/test_ui.py` | Smoke tests (login, logout), regression journeys (create, move through workflow, QA closes, search, duplicate, comment). | Markers let CI run the fast `smoke` set first as a gate. |

## 6. Java API tests (`java-api-tests/`)

| File | What it does |
|------|--------------|
| `pom.xml` | Maven build: TestNG, RestAssured, Allure. The `suite.file` property chooses which TestNG suite runs. |
| `client/ApiClient.java` | A logged-in user: wraps RestAssured calls and returns the raw response. |
| `client/IssueRequest.java` | Builder with sensible defaults, so a test sets only what it cares about. |
| `base/BaseApiTest.java` | Creates its own users and components, so the suite works against any fresh server. |
| `base/DataProviders.java` | Tables of inputs, e.g. all 25 workflow pairs, run as 25 tests. |
| `models/*.java` | `Issue` (JSON object), `Role` and `WorkflowState` enums. |
| `tests/*Test.java` | Auth, issues, workflow, search, test management. 66 tests. |
| `defects/KnownDefectsTest.java` | Correct-behaviour tests for planted bugs. Separate suite file, run on demand. |

OOP points: encapsulation (`ApiClient` hides RestAssured), inheritance (`BaseApiTest`), builder pattern,
enums with behaviour (`WorkflowState.canMoveTo`).

## 7. Swift (`swift-client/`)

| File | What it does |
|------|--------------|
| `Models.swift` | `Codable` types. The server uses `snake_case`; the decoder converts to Swift's `camelCase`. |
| `APIError.swift` | An enum of everything that can go wrong, mapped from HTTP status codes. |
| `Transport.swift` | A tiny protocol `HTTPTransport`; the real one uses `URLSession`. |
| `IssueTrackerClient.swift` | The client. Illegal workflow moves are rejected locally before any request. |
| `Tests/.../MockTransport.swift` | Fake transport: plays back canned answers and records requests. |
| `Tests/.../ClientTests.swift`, `WorkflowTests.swift` | XCTest: decoding, request building, error mapping, all 25 state pairs. |

Why a protocol for networking: tests replace it with a mock, so they are fast, need no server, and run on Linux.

## 8. CI/CD

| File | What it does |
|------|--------------|
| `.github/workflows/ci.yml` | Five jobs. A readiness job fails the build on NO-GO. Reports are uploaded as artifacts. |
| `Jenkinsfile` | The same pipeline for Jenkins. Not run on a real Jenkins server (see `KNOWN-ISSUES.md`). |
| `docs/ci-cd.md` | Describes jobs and quality gates. |

## 9. Documents (`docs/`)

Read these to talk about *process*, not just code: `test-strategy.md` (levels and risks), `test-plan.md`
(one feature in depth), `testability-review.md` (reviewing a spec before coding), `root-cause-analysis.md`
(5 Whys), `exploratory/` (charters and notes), `bugs/` (reports), `code-review-example.md`.

## 10. Things that went wrong and what they taught me (good interview stories)

- **Selenium flakiness in CI.** Two UI tests passed on my PC and failed on GitHub. Cause: the test read the old
  page right after a click. Fix: wait for the old page to go stale. Newer Chrome reports this with a different
  error message, so the wait handles both. Lesson: timing bugs show up on slower machines.
- **Missing `__init__.py`.** Tests passed locally with `python -m pytest` but failed in CI with plain `pytest`,
  because the first form adds the current folder to the import path. Lesson: CI is the cleanest environment.
- **Tiny labelled dataset.** The first duplicate finder (word tokens) scored F1 0.73; character n-grams reached
  1.0 on the same data. I report that as optimistic, not as proof.
- **Setup action vs. new OS image.** The Swift setup action did not support the newest Ubuntu image, so that job
  is pinned to 24.04.
