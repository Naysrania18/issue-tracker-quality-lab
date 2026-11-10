# Root cause analysis: BUG-001 (an issue can be closed without Verify)

Subject: [BUG-001](bugs/BUG-001.md), the highest-impact planted defect in the demo tracker. The analysis uses
the real code and tests in this repository. The "timeline" is reasoned from the code, not from real history,
because the defect was planted for practice.

## Problem statement
`PATCH /api/issues/{id}` with `{"state": "Closed"}` closes an issue from any state, for any engineer, with no
Verify step. `/transition` for the same change correctly returns 422.

## Impact
- Rule broken: "an issue is closed only after Verify, and only QA closes".
- Reports built on closed counts (release readiness) overstate quality.
- Also accepts nonsense states such as `Banana`.
- Detectable only by looking at history or running SQL check 01; nothing fails visibly for the user.

## Detection
Found by exploratory session 1 (second door to the same rule), then pinned by a strict xfail test and
`sql/01_closed_without_verify.sql`. Not caught earlier because the test suite exercised workflow rules only
through `/transition`.

## 5 Whys

1. **Why could an engineer close an unverified issue?**
   Because PATCH wrote the new state straight to the database.

2. **Why did PATCH write the state directly?**
   Because `IssueService.update` treats `state` like any other editable field (title, priority) and has its own
   `UPDATE` statement, separate from `IssueService.transition`.

3. **Why does `update` handle state at all?**
   Because the request model `IssueUpdate` includes `state`. It was added so a client could send "all editable
   fields in one call", and nobody asked whether state belonged in the same group as title and priority.

4. **Why was that not questioned in design or review?**
   There was no rule saying "state changes go through one function", and the workflow rules live in a separate
   module (`workflow.py`) that `update` has no reason to import. The review looked at each endpoint on its own.

5. **Why did tests not catch it?**
   Tests were written per rule ("illegal transitions return 422") and every one used the `/transition` door.
   Nothing asserted the invariant itself ("no issue is ever Closed without a Verify row") across all doors.

**Root cause:** the invariant was enforced at a single entry point instead of at the place where state is
stored, and the test suite verified the entry point, not the invariant.

## Corrective actions (fix this bug)

| Action | Owner | Done when |
|--------|-------|-----------|
| Remove `state` from `IssueUpdate`, or call `transition()` for it | Developer | `test_bug001...` XPASSes, remove xfail |
| Reject unknown state names with 422 | Developer | New test for `Banana` |
| Find existing bad data with `sql/01_closed_without_verify.sql` and decide per issue | Triage | Query returns no rows |

## Preventive actions (stop the whole class of bug)

| Action | Why it helps |
|--------|--------------|
| Make `IssueService.set_state()` the only code that writes `issues.state`; give it the workflow check | One door, rule cannot be bypassed |
| Add a database trigger or constraint check as a last line of defence | Protects against scripts and future code paths |
| Run the SQL integrity checks after the API test run in CI, not only in one test file | Catches invariant violations from any test |
| Property-style test: apply random sequences of API calls across all endpoints, then run all SQL checks | Finds bypasses nobody thought of |
| Review checklist item: "for each rule, list every door that can change this data" | Brings the lesson into code review |

## What went well
The history table recorded the bad move with the actor, which made the investigation fast.
The SQL check found the damage without needing to know how it happened.

## Lessons
Test the invariant, not just the happy entry point. When two endpoints can change the same field, treat that
as a risk during design.
