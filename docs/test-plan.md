# Test plan: duplicate issue detection

Feature under test: finding existing issues that describe the same problem as a new report.
Implemented in `qtools/duplicates.py`, exposed through the CLI (`qtools duplicates`), the MCP tool
`find_duplicates`, and used by the triage agent.

## 1. Objectives
- Users and the agent get relevant candidates, with few false alarms.
- The feature never changes data: it only suggests.
- Behaviour is predictable on edge cases (empty tracker, very short text, very long text).

## 2. How it works (what testers need to know)
Title and description are turned into character n-gram TF-IDF vectors. Cosine similarity ranks existing
issues. A candidate is reported when its score is at least the threshold (default 0.26).

## 3. Scope

| In scope | Out of scope |
|----------|--------------|
| Ranking quality (precision, recall) on labelled data | Automatic merging of duplicates |
| Threshold behaviour, top-N limit | Languages other than English |
| Input validation in the MCP tool | UI for showing suggestions (not built) |
| Behaviour with 0, 1 and many issues | Performance beyond a few thousand issues |

## 4. Risks and test approach

| Risk | Approach |
|------|----------|
| Too many false positives annoy users | Precision measured on labelled data; unrelated-text test returns no matches |
| Misses duplicates with different wording | Recall measured; word-form test ("synchronising" vs "sync") |
| Threshold tuned on too little data | Documented limitation; test asserts a floor (>= 0.8), not perfection; threshold sweep command shows sensitivity |
| Closed issues or issues already marked duplicate are suggested | Decision needed; see open questions |
| Hostile input (very long text, markup) | Length limits (5 to 2000 characters) tested in `mcp_tests/test_tools.py` |

## 5. Test cases

| ID | Case | Expected | Automated in |
|----|------|----------|--------------|
| DUP-1 | New report about a PDF crash, tracker has 3 PDF-crash issues | One of them ranked first | `qtools_tests/test_duplicates.py` |
| DUP-2 | Unrelated text | No matches | same |
| DUP-3 | Different word form | Still matches | same |
| DUP-4 | Labelled dataset at default threshold | Precision and recall >= 0.8 | same |
| DUP-5 | Error counting in the evaluator (TP/FP/FN) | Counts are exact | same |
| DUP-6 | `top_n` limits the result count | Exactly N when N qualify | same |
| DUP-7 | Empty issue list | Clear error in the library, empty list in the MCP tool | `qtools_tests`, `mcp_tests/test_tools.py` |
| DUP-8 | Text shorter than 5 or longer than 2000 characters | Validation error, nothing sent | `mcp_tests/test_tools.py` |
| DUP-9 | Results sorted by score, scores between 0 and 1 | Yes | `qtools_tests/test_duplicates.py` |
| DUP-10 | Agent receives duplicates and can cite them in its draft | Draft validates and keeps issue ids | `mcp_tests/test_agent.py` |
| DUP-11 | Exploratory: paste real-looking multi-paragraph reports with stack traces | Reasonable ranking, no crash | Manual |

## 6. Measured quality (from `python -m qtools duplicates-eval`)

| Threshold | Precision | Recall | F1 |
|-----------|-----------|--------|----|
| 0.22 | 0.71 | 1.00 | 0.83 |
| 0.24 | 0.77 | 1.00 | 0.87 |
| **0.26** | **1.00** | **1.00** | **1.00** |
| 0.28 | 1.00 | 0.90 | 0.95 |
| 0.30 | 1.00 | 0.80 | 0.89 |

Reading this honestly: 22 issues and 10 duplicate pairs is a very small set and the threshold was chosen on
it, so 1.00 is optimistic. The sharp drop either side of 0.26 shows the result is sensitive. Before relying on
it, collect a larger labelled set from real triage decisions and choose the threshold on a separate split.

## 7. Environment and data
Python 3.10+, scikit-learn. No network. Data in `data/labelled_duplicates.json` (hand-written, fake).

## 8. Entry and exit criteria
- Entry: labelled dataset reviewed by a second person.
- Exit: DUP-1 to DUP-10 pass in CI; precision and recall >= 0.8 at the default threshold; open questions answered.

## 9. Open questions for the product owner
1. Should Closed issues be suggested? (Probably yes: a closed duplicate tells the user it is fixed.)
2. Should issues already marked as duplicates be excluded from candidates?
3. What is worse here, a missed duplicate or a false suggestion? That decides the threshold.
