# CI/CD

The same pipeline exists twice: `.github/workflows/ci.yml` (GitHub Actions, `ubuntu-latest`) and
`Jenkinsfile` (any Jenkins agent with Python, JDK 17, Maven and Chrome; Swift is optional).

## Jobs

| Job | What it does | Artifacts |
|-----|--------------|-----------|
| `python-lint-and-tests` | ruff, mypy, smoke tests, full pytest run with coverage | `python-reports` (JUnit XML, coverage XML/HTML) |
| `selenium-ui` | Headless Chrome tests, smoke first, then the full journey suite | `selenium-reports` (JUnit, failure screenshots) |
| `java-api-tests` | Starts the Python tracker, runs Maven + TestNG + RestAssured | `java-allure-results` (Allure results, surefire reports) |
| `swift-xctest` | Installs Swift, builds the package and runs XCTest on Linux | `swift-reports` (xUnit XML) |
| `quality-report` | Runs `qtools readiness` and the other tools | `quality-reports` (Markdown + HTML) |

## Quality gates

| Gate | Where | Fails the build when |
|------|-------|----------------------|
| Zero failed smoke tests | `pytest -m smoke`, `pytest ui_tests -m smoke` | any smoke test fails |
| Coverage threshold | `--cov-fail-under=85` | total line coverage of `app`, `qtools`, `mcp_server`, `agent` is below 85% |
| No open P1 | `qtools readiness --fail-on-no-go` | the readiness decision is NO-GO (open P1, more than 3 open P2, pass rate below 95%, coverage below 80%) |
| Lint and types | ruff, mypy | any finding |

The readiness gate reads `data/release_candidate_issues.json`, a fake snapshot of a release candidate
with no open P1. The `quality-report` job also produces a **demo NO-GO** report from a seeded database
so you can see what a failing decision looks like (it does not fail the build).

## Viewing results

- Allure: download `java-allure-results`, then `allure serve allure-results` (Allure CLI needed).
- Python coverage: open `htmlcov/index.html` from `python-reports`.
- Readiness: open `readiness/readiness.html` from `quality-reports`.

## Why the known-defect tests do not break CI

Python: `xfail(strict=True)`. Java: separate suite `testng-known-defects.xml`, not part of `mvn test`.
Both are run on demand to prove the bugs are still reproducible.
