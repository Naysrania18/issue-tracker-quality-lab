# Known issues and limitations

Honest list of what is not done, not verified, or not perfect.

## Not verified in a real environment
- **Jenkinsfile** has never run on a Jenkins server (no Jenkins available). It mirrors the GitHub Actions jobs,
  which do run. Expect small agent-setup differences (Python venv, Chrome, Maven paths).
- **Swift tests run on Linux only** (Swift 6.0 compiler in Swift 5 language mode). Nothing in the project
  touches UIKit or AppKit, so behaviour on iOS and macOS devices is not covered.
- **Real LLM calls are untested.** `agent/llm.py::AnthropicLLM` was never called with a live key; all agent tests
  use a scripted fake model. The model id comes from `AGENT_MODEL` (default `claude-sonnet-5-5`).
- The **MCP server was tested through an in-memory MCP client**, not yet from Claude Desktop or Claude Code.

## Design limitations
- **Duplicate finder** was tuned on 22 hand-written issues; the F1 of 1.0 at threshold 0.26 is optimistic and
  the score drops quickly either side (see `docs/test-plan.md`). It also suggests closed issues and issues
  already marked as duplicates (open question in the test plan).
- **One token per user:** logging in again signs out the earlier session (documented by a test; raised as a
  question in `docs/testability-review.md`).
- **Demo tracker** uses SQLite and a single process. No concurrency control, so concurrent-edit bugs are not covered.
- `run_tests` in the MCP server runs the repository's own pytest suite; it needs to be started from the repo root.
- The `quality-report` CI gate reads a fixed fake snapshot (`data/release_candidate_issues.json`), not live
  tracker data. A NO-GO example is produced from a seeded database for illustration.
- Allure results are produced and uploaded, but the HTML report is not generated in CI (needs the Allure CLI).

## Defects that remain open on purpose
`BUG-001` to `BUG-005` are planted; `BUG-006` was found by exploratory testing and left open. See `docs/planted-defects.md`.
