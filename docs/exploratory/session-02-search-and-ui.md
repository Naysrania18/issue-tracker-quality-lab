# Exploratory session 2: search, filters and the web UI

**Charter:** Explore search and filtering, and how user-entered text is displayed in the web UI, to
discover wrong results and unsafe rendering.

| | |
|---|---|
| Tester | Repo author |
| Build | demo tracker 1.0.0, 3 issues: "App will Crash on launch" (P1), "Sync slow" (P2), one more P3 |
| Time box | 30 minutes |
| Heuristics | CRUD + boundaries, "data in = data out", SFDIPOT (Data, Interfaces), special characters |

Same honesty note as session 1: planted defects are known in advance.

## Notes

| # | Action | Result | Verdict |
|---|--------|--------|---------|
| 1 | Search `q=Crash` | 1 result | OK |
| 2 | Search `q=crash` (lower case) | **0 results** | **Bug, BUG-003a**: users type lower case |
| 3 | Filter `priority=P2` with a P1 and a P2 issue | **Returns P1 and P2** | **Bug, BUG-003b** |
| 4 | Filter `priority=P9` | **Returns every issue (3 of 3)** instead of 422 | Same root cause (string comparison `<=`). Added to BUG-003 |
| 5 | Search `q=%` | 0 results | OK: wildcard characters are treated as text |
| 6 | Search with empty `q=` | All issues | OK |
| 7 | Create issue with description `<img src=x onerror=alert(1)>`, open detail page | **Raw tag is present in the page HTML** | **Bug, BUG-005 (P1)** |
| 8 | Same text in the *title* | Shown as text, escaped | OK: only the description is unescaped. Narrows the cause to one template line |
| 9 | Title of 201 characters | 422 | OK |
| 10 | Title `"     "` and `"  ab  "` | 201 for both | **Bug, BUG-006**: no trimming |
| 11 | Create 2 + 3 issues, read notifications | 5 notifications | OK: one per creation |

## Bugs raised
BUG-003 (P2), BUG-005 (P1), BUG-006 (P3).

## What this session suggests for automation
- Case-insensitive search and exact priority filter belong in the regression suite (done: strict xfails).
- A UI test that types markup into the description and checks it is displayed as text (done:
  `ui_tests/test_ui.py::test_bug005_...`).
- Invalid filter values should be a validation error, not "everything". Needs a product decision.
