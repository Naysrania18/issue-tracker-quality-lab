-- Every test result must belong to an existing test run.
SELECT r.id AS result_id, r.run_id
FROM test_results r
LEFT JOIN test_runs t ON t.id = r.run_id
WHERE t.id IS NULL;
