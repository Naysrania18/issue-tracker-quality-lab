-- A completed run must have recorded at least one result.
SELECT t.id AS run_id, t.status
FROM test_runs t
WHERE t.status <> 'running'
  AND NOT EXISTS (SELECT 1 FROM test_results r WHERE r.run_id = t.id);
