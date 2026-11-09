# Connecting the MCP server

The MCP server (`mcp_server/`) lets an AI assistant search issues, find duplicates, look at test
results and run the project's tests. It talks to the demo tracker over its HTTP API, so the tracker
must be running.

## 1. Start the tracker and get a token

```
# Windows PowerShell                          # Linux / macOS
.venv\Scripts\python -m app.seed              .venv/bin/python -m app.seed
.venv\Scripts\python -m uvicorn app.main:app  .venv/bin/python -m uvicorn app.main:app
```

In another terminal, log in as the seeded QA user and copy the token:

```
curl -s -X POST http://127.0.0.1:8000/api/auth/login -H "Content-Type: application/json" ^
     -d "{\"username\":\"quinn\",\"password\":\"demo-pass\"}"
```

## 2. Claude Code

```
claude mcp add issue-tracker -e TRACKER_TOKEN=<token> -- <repo>\.venv\Scripts\python.exe -m mcp_server
```

Run it from the repository root so `run_tests` finds the test folder. Add `--allow-write` after
`-m mcp_server` only if you want `create_issue` and `add_comment` to work.

## 3. Claude Desktop

Edit `claude_desktop_config.json` (Settings, Developer, Edit Config):

```json
{
  "mcpServers": {
    "issue-tracker": {
      "command": "C:\\path\\to\\issue-tracker-quality-lab\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\path\\to\\issue-tracker-quality-lab",
      "env": { "TRACKER_TOKEN": "<token>", "TRACKER_URL": "http://127.0.0.1:8000/api" }
    }
  }
}
```

Restart Claude Desktop. The eight tools appear in the tools menu.

## Tools

| Tool | Kind | What it does |
|------|------|--------------|
| `search_issues` | read | Text, state, priority and component filters |
| `get_issue` | read | One issue with comments and history |
| `find_duplicates` | read | TF-IDF similarity against existing issues |
| `list_test_cases` | read | Test cases, optionally for one component |
| `get_test_results` | read | One run with results, or all runs |
| `run_tests` | read* | Runs this project's pytest suite filtered by a keyword |
| `create_issue` | **write** | Needs `--allow-write` |
| `add_comment` | **write** | Needs `--allow-write` |

\* `run_tests` does not change tracker data. It runs a fixed command and the keyword may only
contain letters, digits, underscores and spaces, so nothing can be injected into the command line.

## Safety design

- **Read-only by default.** Write tools return an error until the server is started with `--allow-write`.
- **Validation.** Ids must be positive integers, priorities must be P1 to P4, text has length limits.
- **Audit log.** Every call, allowed or refused, is appended as one JSON line to `reports/mcp-audit.log`
  (override with `MCP_AUDIT_LOG`). Long arguments are shortened in the log.
- **Least privilege token.** Use a reporter or engineer account for assistants that should not manage tests.

## The triage agent

`python -m agent.triage_agent --title "Sync hangs" --description "..."` runs a small agent loop
(Anthropic API) that uses the read-only MCP tools to check duplicates and related tests, then
submits a draft. The draft is checked against a JSON schema and written to `review/` for a human.
The agent is never given the write tools and never changes the tracker.

Set `ANTHROPIC_API_KEY` in your environment (see `.env.example`). The tests use a scripted fake model,
so CI needs no key.
