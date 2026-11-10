# Code review example

A sample pull request review, written the way I would review a teammate's change. The PR is hypothetical
(a fix for BUG-002) but the files and code it touches are real, so the comments can be checked against the repo.

## Pull request

**Title:** Reject self-duplicates and cycles when marking an issue as duplicate (BUG-002)

**Description from the author:** Adds a check that `duplicate_of` differs from the issue id. Removes the
xfail on the test.

### Diff (abridged)

```diff
 # app/services.py
 def mark_duplicate(self, issue_id: int, duplicate_of: int, actor: sqlite3.Row) -> dict[str, Any]:
     row = self._row(issue_id)
     self._row(duplicate_of)  # 404 when the original does not exist
-    # PLANTED-DEFECT-2: missing check `issue_id == duplicate_of`.
+    if issue_id == duplicate_of:
+        raise Conflict("An issue cannot be a duplicate of itself")
     self.conn.execute(
```

```diff
 # tests/test_planted_defects.py
-@pytest.mark.xfail(strict=True, reason="BUG-002 docs/bugs/BUG-002.md: self duplicate accepted")
 def test_bug002_issue_cannot_be_duplicate_of_itself(client, reporter, engineer):
```

## Review comments

**Summary:** Good, small fix and the right test is un-xfailed. Two things to change before merging, three
smaller suggestions. Request changes.

### Must fix

1. **`app/services.py`, new `raise Conflict(...)`: wrong error type**
   The test expects 422, and `Conflict` maps to 409. A self-reference is invalid input, not a clash with
   existing state. Use the same error as other validation failures (the workflow uses `InvalidTransition`,
   which the handler maps to 422), or add a small `ValidationFailed` exception. As written, the un-xfailed test
   will fail in CI, so I assume this was not run locally. Please run `pytest tests/test_planted_defects.py`.

2. **Cycles are still possible.**
   A is a duplicate of B, then B is a duplicate of A. Both lines pass the new check, and SQL check 02 does not
   see it either, because it only compares an id with itself. The BUG-002 report calls this out under
   "Suggested fix". Either handle it here (follow the `duplicate_of` chain from the target and reject if it
   reaches `issue_id`) or open a follow-up and link it in the description. I prefer fixing it here; the loop is
   five lines.

### Should fix

3. **Test coverage:** the PR removes a marker but adds no new test. Please add the cycle case (A to B, then
   B to A, expect 422) and a case for duplicating an already closed issue so the behaviour is written down.

4. **Remove the stale marker comment.** `docs/planted-defects.md` still lists BUG-002 as open. Update the
   table or the next reader will think the bug still exists.

### Nit / question

5. **Nit:** the message could include the id: `f"Issue {issue_id} cannot be a duplicate of itself"`.
   Helps people reading logs.

6. **Question:** the web form (`routes_web.duplicate`) catches `DOMAIN_ERRORS`. Is the new exception in that
   tuple? If not, the UI would show a 500 page instead of the error banner. A Selenium test for the web path
   would answer this: `test_mark_duplicate` has the pattern.

### What I checked
Read the diff and surrounding function, searched for other callers of `mark_duplicate`
(`routes_api.py`, `routes_web.py`), and ran the SQL checks mentally against the new behaviour.

## Principles I follow when reviewing
- Review the behaviour first, style second (the linter covers style).
- Say why, and offer a concrete alternative.
- Separate "must fix" from "nice to have", so the author knows what blocks the merge.
- Check that tests would fail without the change.
