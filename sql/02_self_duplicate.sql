-- An issue can never be a duplicate of itself.
SELECT id, title
FROM issues
WHERE duplicate_of = id;
