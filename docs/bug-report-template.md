# Bug report template

Use this layout for every defect. A good report lets someone who has never seen the problem
reproduce it in under two minutes and decide how urgent it is without asking questions.

```
Title:        <component>: <what is wrong> (<condition that triggers it>)
ID:           BUG-nnn
Component:    <Component > Sub-component>
Priority:     P1-P4  (P1 = show stopper, P2 = major, P3 = normal, P4 = minor)
Found by:     <test / session / person>, <date>
Build/env:    <version, environment, browser if relevant>

Summary
  One or two sentences. What happens and why it matters.

Steps to reproduce
  1. ...
  2. ...

Expected result
Actual result

Evidence
  Request/response, log lines, screenshot, failing test name.

Impact
  Who is affected, how badly, is there a workaround.

Suspected cause (optional)
  File and line, or the rule that seems to be missing.

Suggested regression test
  The automated check that should guard this after the fix.
```

## Priority guide

| Priority | Meaning | Example |
|----------|---------|---------|
| P1 | Blocks release; data loss, security hole, core flow broken | Stored XSS, workflow bypass that corrupts records |
| P2 | Major feature wrong, workaround is painful | Wrong search results |
| P3 | Normal defect, workaround exists | Wrong ordering, missing validation on a rare path |
| P4 | Cosmetic or very rare | Typo, spacing |
