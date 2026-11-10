# Skills map

Where to find each skill in this repository. Every path exists; `tests/test_docs_links.py` checks it.

| Skill | Evidence (files) | What it shows |
|-------|------------------|---------------|
| **Python** | `app/services.py`, `qtools/flaky.py`, `qtools/duplicates.py`, `mcp_server/tools.py` | Typed, readable Python; dataclasses; small functions; mypy and ruff clean |
| **OOP** | `app/services.py` (`IssueService`, `TestService`, `ComponentService`), `ui_tests/pages/base_page.py` and subclasses, `java-api-tests/src/test/java/com/qualitylab/api/client/ApiClient.java` | One class per responsibility, inheritance for shared behaviour (page objects, `BaseApiTest`), composition for services |
| **Data structures and algorithms** | `qtools/flaky.py` (flip counting over sequences), `qtools/duplicates.py` (TF-IDF vectors, cosine similarity, pair combinations), `app/services.py` (`_component_subtree` breadth-first walk of a tree), `app/events.py` (`deque` queue), `app/workflow.py` (state graph as a dict of sets) | Choosing a structure for the job and explaining its cost |
| **Swift** | `swift-client/Sources/IssueTrackerClient/IssueTrackerClient.swift`, `Models.swift`, `APIError.swift` | `Codable`, async and await, enums with associated values, protocol-based networking |
| **XCTest** | `swift-client/Tests/IssueTrackerClientTests/ClientTests.swift`, `WorkflowTests.swift`, `MockTransport.swift` | Async tests, a mock transport, runs on Linux without UIKit |
| **Selenium** | `ui_tests/test_ui.py`, `ui_tests/conftest.py` | Journeys, explicit waits, screenshots on failure, markers |
| **Page Object Model** | `ui_tests/pages/` | UI details hidden behind page classes; race-free reload waits in `base_page.py` |
| **Java** | `java-api-tests/src/test/java/com/qualitylab/api/` | Java 17, builders, enums, records of intent through small classes |
| **Maven** | `java-api-tests/pom.xml` | Dependencies, surefire suite selection by property |
| **TestNG** | `java-api-tests/src/test/resources/testng.xml`, `java-api-tests/src/test/java/com/qualitylab/api/tests/WorkflowTest.java`, `java-api-tests/src/test/java/com/qualitylab/api/base/DataProviders.java` | Groups, data providers (25 workflow pairs), separate known-defect suite |
| **RestAssured** | `java-api-tests/src/test/java/com/qualitylab/api/client/ApiClient.java` | Request specs, JSON parsing |
| **Allure** | `java-api-tests/pom.xml`, `java-api-tests/src/test/java/com/qualitylab/api/client/ApiClient.java` (`AllureRestAssured` filter), `.github/workflows/ci.yml` (artifact upload) | Results with request and response attachments |
| **Jenkins** | `Jenkinsfile` | Declarative pipeline mirroring the Actions workflow |
| **CI/CD** | `.github/workflows/ci.yml`, `docs/ci-cd.md` | Five jobs, artifacts, quality gates |
| **MCP** | `mcp_server/server.py`, `mcp_server/tools.py`, `mcp_tests/test_server_protocol.py`, `docs/mcp-setup.md` | Tool design, safety limits, audit log, tested through a real MCP client |
| **Agentic workflows** | `agent/triage_agent.py`, `agent/schema.py`, `mcp_tests/test_agent.py` | Tool-using loop, schema-validated output, human review, no write access |
| **Test design** | `tests/test_workflow.py` (all 25 pairs, boundaries), `tests/test_search.py`, `qtools_tests/test_readiness.py` (boundary values) | Equivalence classes, boundaries, decision tables |
| **API testing** | `tests/test_issues_api.py`, `java-api-tests/src/test/java/com/qualitylab/api/tests/IssueTest.java` | Status codes, permissions, validation, error bodies |
| **SQL** | `sql/*.sql`, `tests/test_sql_integrity.py`, `docs/sql-queries.md` | Anti-joins, `NOT EXISTS`, integrity rules |
| **Exploratory testing** | `docs/exploratory/session-01-workflow-and-permissions.md`, `docs/exploratory/session-02-search-and-ui.md` | Charters, notes, heuristics, bugs raised |
| **Bug reporting** | `docs/bug-report-template.md`, `docs/bugs/BUG-001.md` to `BUG-006.md` | Reproducible, prioritised reports |
| **Triage** | `docs/planted-defects.md`, `qtools/duplicates.py`, `agent/triage_agent.py` | Priorities P1 to P4, duplicate detection |
| **Flaky test handling** | `qtools/flaky.py`, `qtools_tests/test_flaky.py`, `data/junit_runs/` | Scoring flakiness vs. regression |
| **Release readiness** | `qtools/readiness.py`, `qtools_tests/test_readiness.py`, `data/release_candidate_issues.json` | GO / NO-GO with reasons |
| **Spec review for testability** | `docs/testability-review.md` | Untestable statements, questions, acceptance criteria |
| **Test planning and strategy** | `docs/test-strategy.md`, `docs/test-plan.md` | Risks, levels, entry and exit criteria |
| **Root cause analysis** | `docs/root-cause-analysis.md` | 5 Whys, corrective and preventive actions |
| **Code review** | `docs/code-review-example.md` | Prioritised, actionable review comments |
| **Event-driven systems** | `app/events.py`, `tests/test_events.py` | Duplicate and out-of-order event tests |
