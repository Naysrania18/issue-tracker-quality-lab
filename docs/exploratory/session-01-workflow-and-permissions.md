# Exploratory session 1: workflow and permissions

**Charter:** Explore the issue workflow and role permissions, using different entry points (the
transition endpoint, PATCH, the web form), to discover ways to reach a state the rules should forbid.

| | |
|---|---|
| Tester | Repo author |
| Build | demo tracker 1.0.0, fresh database, users rita (reporter), erin (engineer), quinn (qa) |
| Time box | 45 minutes |
| Tools | `TestClient` scripts, browser, SQL queries from `sql/` |

Note on honesty: the planted defects are known to the author, so this log shows the *technique* and the
evidence trail, not an unbiased discovery. BUG-006 and the single-token behaviour were not planted.

## Approach
Idea: every rule is enforced at one door, so look for the other doors. Doors found by reading the API list:
`/transition`, `PATCH /issues/{id}`, the web form, and the seed script.

## Notes (in order)

| # | Action | Result | Verdict |
|---|--------|--------|---------|
| 1 | Engineer moves a new issue straight to Closed via `/transition` | 422 "Cannot move from Analyze to Closed" | Rule works |
| 2 | Same request via `PATCH` with `{"state": "Closed"}` | **200, state is Closed** | **Bug, BUG-001** |
| 3 | Read history of that issue | `None -> Analyze`, `Analyze -> Closed`. No `Verify` row and the actor was an engineer, who is not allowed to close | Confirms the bypass also skips the role rule |
| 4 | Run `sql/01_closed_without_verify.sql` | Returns the issue | SQL check catches it |
| 5 | `PATCH` with `{"state": "Banana"}` | **200, state is "Banana"** | **Worse than #2**: not even a valid state. Added to BUG-001 |
| 6 | Reporter calls `/transition` | 403 | Works |
| 7 | Reporter opens the issue in the web UI | No workflow or duplicate forms | Works |
| 8 | Mark an issue as duplicate of itself | **200, "Duplicate of #1" on #1** | **Bug, BUG-002** |
| 9 | Log in a second time as the same user, reuse the first token | 401 | **Question**: is one session per user intended? See testability review |
| 10 | Create an issue via API with title `"     "` | **201** | **Bug, BUG-006** (found while probing boundaries) |

## Bugs raised
BUG-001 (P1), BUG-002 (P3), BUG-006 (P3).

## Questions for the product owner
- Should PATCH accept `state` at all, or should state only change through `/transition`?
- Should logging in on a second device end the first session?

## Next session ideas
Concurrent transitions on one issue (two engineers), reopening a Closed issue and then closing again
(does it need a second Verify?), very long comments.
