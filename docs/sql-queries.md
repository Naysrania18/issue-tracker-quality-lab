# SQL integrity checks

The queries in `sql/` look for data that should never exist. Each one returns the *bad* rows, so an
empty result means healthy data. `tests/test_sql_integrity.py` runs them in two ways:

1. against a database filled using only legal API calls, expecting no rows;
2. against a database where a defect is deliberately triggered, expecting the query to catch it.

Why bother when API tests exist? API tests check what one request returns. These checks look at
the whole database after any mix of requests, scripts and migrations, and they can be pointed at
a real environment as a post-deploy check.

| File | Rule | Catches |
|------|------|---------|
| `01_closed_without_verify.sql` | A Closed issue must have a history row moving it to Verify | BUG-001 |
| `02_self_duplicate.sql` | `duplicate_of` must not equal the issue's own id | BUG-002 |
| `03_orphan_test_results.sql` | Every `test_results.run_id` exists in `test_runs` (`LEFT JOIN ... WHERE t.id IS NULL`) | Deleted runs, disabled foreign keys |
| `04_result_case_not_in_suite.sql` | A result's test case belongs to the run's suite (`LEFT JOIN suite_cases`) | Results recorded against the wrong case |
| `05_completed_run_without_results.sql` | A finished run has at least one result (`NOT EXISTS`) | Runs completed with nothing executed |

## Techniques used

- `NOT EXISTS` subquery: "no matching history row" (query 1, 5).
- `LEFT JOIN ... WHERE right.id IS NULL`: the anti-join pattern for orphans (query 3, 4).
- Self comparison on one row (query 2).

## Running by hand

```
sqlite3 tracker.db < sql/01_closed_without_verify.sql
```
