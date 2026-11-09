-- A result may only be recorded for a test case that belongs to the run's suite.
SELECT r.id AS result_id, r.run_id, r.case_id
FROM test_results r
JOIN test_runs t ON t.id = r.run_id
LEFT JOIN suite_cases sc ON sc.suite_id = t.suite_id AND sc.case_id = r.case_id
WHERE sc.case_id IS NULL;
