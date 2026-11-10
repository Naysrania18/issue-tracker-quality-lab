# Final report

**TASK COMPLETE**

## 1. Repository and CI status

Public repo: https://github.com/Naysrania18/issue-tracker-quality-lab

| CI job | Status |
|--------|--------|
| python-lint-and-tests (ruff, mypy, smoke gate, 85% coverage gate) | success |
| selenium-ui | success |
| java-api-tests (Maven, TestNG, RestAssured, Allure) | success |
| swift-xctest (Swift 6.0 on Ubuntu 24.04) | success |
| quality-report (release readiness gate) | success |

Local checks at the end: 203 Python tests pass and 8 are expected xfails (known bugs); 13 Selenium tests (12 pass, 1 xfail);
66 Java tests pass; 4 Java known-defect tests fail on purpose; ruff and mypy clean.

## 2. What was built

- A demo issue tracker (FastAPI, SQLite, Jinja UI) with a workflow, roles, test management and an event queue, with 5 planted bugs.
- Python tests (unit, API, events, SQL integrity), strict-xfail tests for known bugs, Selenium with Page Objects, a Java TestNG/RestAssured/Allure suite, and a Swift client with XCTest.
- `qtools`: flaky test detector, duplicate finder (TF-IDF, measured with precision and recall), release readiness (Markdown and HTML), suite health.
- An MCP server (8 tools, read-only by default, validation, audit log) and a triage agent that only drafts bug reports for human review.
- GitHub Actions (5 jobs, artifacts, quality gates), a Jenkinsfile, and documents: strategy, test plan, testability review, RCA, 2 exploratory sessions, 6 bug reports, code review example, skills map, README and a learning guide.
- One extra defect (BUG-006) found by exploratory testing, not planted.

## 3. Known issues

See [KNOWN-ISSUES.md](KNOWN-ISSUES.md). Main points: Jenkinsfile never run on a real Jenkins; no live LLM call or Claude Desktop check; the duplicate finder is tuned on a tiny dataset (its 1.0 score is optimistic); Swift runs on Linux only.

## 4. Ten files to study first

1. `app/workflow.py` (the rules everything checks)
2. `app/services.py` (business logic and three planted bugs)
3. `tests/test_workflow.py` (parametrized tests)
4. `tests/test_planted_defects.py` (strict xfail idea)
5. `tests/test_sql_integrity.py` with `sql/01_closed_without_verify.sql`
6. `qtools/duplicates.py` (TF-IDF, precision and recall)
7. `qtools/flaky.py` (flakiness score)
8. `mcp_server/tools.py` (safety design)
9. `ui_tests/pages/base_page.py` (explicit waits and the reload race)
10. `.github/workflows/ci.yml` (jobs and gates)

## 5. Interview questions

1. **Why parametrize the workflow tests?** One test function covers all 25 state pairs, so a rule change shows up as exactly which pair broke.
2. **What does `xfail(strict=True)` do and why use it?** It lets a known bug stay in the suite without failing CI; if the bug is fixed the test unexpectedly passes and strict mode fails the build, so the marker gets removed.
3. **How is a flaky test different from a regression?** Flaky tests flip between pass and fail on the same code; a regression fails consistently after a change. The score counts flips, so "pass pass fail fail" scores low.
4. **Explain precision and recall for the duplicate finder.** Precision: of the pairs reported, how many are real duplicates. Recall: of the real duplicates, how many were found. A lower threshold raises recall and lowers precision.
5. **Why is your 1.0 F1 not strong evidence?** Only 22 issues and 10 pairs, and the threshold was tuned on the same data. I would label more real data and tune on a separate split.
6. **Java OOP: where did you use inheritance, encapsulation and a builder?** `BaseApiTest` (inheritance, shared set-up), `ApiClient` (hides RestAssured), `IssueRequest` (builder with defaults).
7. **What does a TestNG data provider do?** It feeds a table of inputs to one test method; here 25 workflow pairs become 25 test runs.
8. **Why Page Object Model?** Tests describe user intent; page classes hold selectors and waits, so a UI change touches one file.
9. **Selenium tests failed on CI but passed locally. What was it?** A race: the test read the page right after clicking, before the reload. Fix: wait for the old element to go stale; newer Chrome reports that with a different error, which the wait also handles.
10. **Why mock the network in XCTest?** Tests become fast, deterministic and run on Linux without a server; the client talks to a small `HTTPTransport` protocol so the mock can replace `URLSession`.
11. **What is MCP and what are its tools here?** A protocol that lets an AI assistant call tools in a standard way. Mine exposes search, get issue, find duplicates, list test cases, get results, run tests, and two write tools.
12. **How did you make the MCP server safe?** Read-only by default, writes need a flag, validated inputs, `run_tests` only accepts a plain keyword, every call is audit-logged.
13. **How do you stop the agent from doing harm?** It is never offered write tools, its answer must pass a JSON schema with `requires_human_review: true`, it only writes a draft file, and tool output is treated as data not instructions.
14. **How do you test code that calls an LLM?** Put the model behind a small interface and use a scripted fake in tests, including bad drafts and forbidden tool calls; real calls are an optional manual check.
15. **What quality gates does CI enforce?** Zero failed smoke tests, 85% coverage, lint and types clean, and a readiness check that fails on NO-GO (open P1, too many P2, pass rate below 95%, coverage below 80%).

## 6. Resume entry (Projects)

**Issue Tracker Quality Lab** (Python, Java, Swift, Selenium, MCP, GitHub Actions) | github.com/Naysrania18/issue-tracker-quality-lab
Built a demo issue tracker with 5 planted bugs and a multi-language test stack (pytest, Selenium, TestNG/RestAssured/Allure, XCTest), plus CLI quality tools (flaky-test scoring, TF-IDF duplicate finder, GO/NO-GO release report) gated in CI; added a read-only-by-default MCP server and a human-reviewed AI triage agent.

## 7. 60-second spoken summary

"I built a small issue tracker on purpose with a few hidden bugs, and then built the quality tooling a QE team would want around it. There are tests at every level: Python unit and API tests, SQL checks that look for impossible data, Selenium browser tests with page objects, a Java suite with TestNG and RestAssured, and a Swift client tested with XCTest. On top of that I wrote command line tools: one scores flaky tests, one finds duplicate issues using TF-IDF and I measured it with precision and recall, and one decides go or no-go for a release. I also made an MCP server so an AI assistant can search issues and run tests, but it's read-only by default and logs everything, and a triage agent that only writes draft bug reports for a human to review. Everything runs in GitHub Actions with quality gates. The most useful lesson was a flaky Selenium test that passed locally and failed in CI. It was a timing race, and fixing it properly with waits is something I now check for in every UI test."
