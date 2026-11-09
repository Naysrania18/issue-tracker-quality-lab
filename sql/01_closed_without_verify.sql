-- Every Closed issue must have passed through Verify.
-- Returns the offending issues; an empty result means the data is healthy.
SELECT i.id, i.title
FROM issues i
WHERE i.state = 'Closed'
  AND NOT EXISTS (
      SELECT 1 FROM history h
      WHERE h.issue_id = i.id AND h.field = 'state' AND h.new_value = 'Verify'
  );
