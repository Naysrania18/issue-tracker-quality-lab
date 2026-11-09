# Planted defects

The demo issue tracker contains five deliberate bugs. They exist so the test suite, the SQL
checks and the exploratory sessions have something realistic to find. Each one is marked in the
source with a `PLANTED-DEFECT-n` comment. Tests that expose them are `xfail(strict=True)`: the
main pipeline stays green, and if somebody fixes a bug the strict xfail turns red so the test can
be promoted to a normal test.

| ID | Where | Summary | Found by | Report |
|----|-------|---------|----------|--------|
| 1 | `app/services.py` `IssueService.update` | `PATCH /api/issues/{id}` accepts `state` and skips workflow validation, so an issue can be closed without passing Verify | API test, SQL check #1, exploratory session 1 | [BUG-001](bugs/BUG-001.md) |
| 2 | `app/services.py` `IssueService.mark_duplicate` | An issue can be marked a duplicate of itself | API test, SQL check #2 | [BUG-002](bugs/BUG-002.md) |
| 3 | `app/services.py` `IssueService.search` | Search is case-sensitive, and the priority filter uses `<=` so `P2` also returns `P1` | API test, exploratory session 2 | [BUG-003](bugs/BUG-003.md) |
| 4 | `app/events.py` `NotificationConsumer.handle` | A re-delivered event creates a second notification (no idempotency check) | Event test | [BUG-004](bugs/BUG-004.md) |
| 5 | `app/templates/issue_detail.html` | Issue description is rendered with `\|safe`, so HTML typed into it is not escaped (stored XSS) | Exploratory session 2, UI test | [BUG-005](bugs/BUG-005.md) |
