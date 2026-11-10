# Testability review of a feature spec (before coding)

The spec below is a short, made-up requirement for a feature that does not exist yet. The review shows how
I read a spec as a tester: find what cannot be tested, what is ambiguous, what is missing, and what the
system needs so that testing is cheap.

## The spec under review

> **FEAT-12: Suggest duplicates while filing an issue**
> While the reporter types a title, the system should quickly show up to 5 similar existing issues. If a very
> similar issue exists, the reporter is strongly encouraged not to file a new one. Suggestions should be
> relevant and the feature should not slow the form down. Engineers can turn the feature off per component.

## 1. Statements that cannot be tested as written

| Statement | Problem | Suggested wording |
|-----------|---------|-------------------|
| "quickly" | No number | "Suggestions appear within 500 ms for 95% of requests on a tracker with 10,000 issues" |
| "similar" / "very similar" | No definition, so no oracle | "Score >= 0.26 is similar, >= 0.6 is very similar" (values to be confirmed on labelled data) |
| "strongly encouraged" | Not observable | "A confirmation step lists the matches and requires one extra click to file anyway" |
| "relevant" | Subjective | "On the labelled set, precision >= 0.8 and recall >= 0.8" |
| "should not slow the form down" | No limit | "Typing is never blocked; the request is debounced by 300 ms and cancelled when the text changes" |

## 2. Ambiguities (questions to ask)

1. Which issues are searched: all, only the same component, or only open ones? Closed issues?
2. Are issues the user cannot see (permissions) excluded from suggestions? (Information leak risk.)
3. What happens with fewer than N characters of title? Minimum length for a search?
4. Is the title alone used, or title plus description? The spec says "title" but the algorithm gets better with both.
5. "Turn off per component": does it inherit from the parent component ("Mail" off means "Mail > Sync" off)?
6. Who is an "engineer" for this setting? The existing roles are reporter, engineer and QA.
7. Is a suggestion list a one-time answer or does it refresh as the title changes?
8. What if two users file the same issue at the same moment? Is there a server-side check as well?

## 3. Missing requirements

- **Failure behaviour:** what the form does when the suggestion service is down (must not block filing).
- **Empty state:** zero matches, or an empty tracker.
- **Audit:** are shown suggestions and the user's choice recorded? Needed to measure the feature's value.
- **Accessibility:** are the suggestions announced to screen readers?
- **Privacy:** titles of issues from restricted components must not appear.
- **Rollout:** feature flag, so it can be switched off globally without a deploy.

## 4. Testability needs (what to build in)

| Need | Why |
|------|-----|
| Scoring is a pure function with a documented threshold | Unit tests and threshold sweeps without a browser |
| Threshold and result limit are configuration, not constants | Tests can use extreme values |
| Stable element ids on the suggestion panel (`suggestion-list`, `suggestion-item`) | Selenium tests without brittle selectors |
| The response includes the score | Tests and users can see why something was suggested |
| Clock/debounce injectable or exposed | Tests do not need sleeps |
| Events: `SuggestionShown`, `SuggestionAccepted`, `IssueFiledAnyway` | Measure success; test through the existing event queue |
| Deterministic data seed for a labelled set | Repeatable quality measurement in CI |

## 5. Proposed acceptance criteria

1. Given a tracker with the labelled dataset, when a title from a known duplicate cluster is typed, then at
   least one member of the cluster is in the top 3 suggestions.
2. Given a title with fewer than 5 characters, then no request is sent.
3. Given a user without access to component X, then suggestions never include issues from X.
4. Given the suggestion service returns an error, then the issue can still be filed and no error blocks the form.
5. Given the feature is disabled for "Mail", then no suggestions appear for "Mail > Sync".
6. Given suggestions are shown, when the user files anyway, then an `IssueFiledAnyway` event is recorded.

## 6. Test ideas to start from
Boundary titles (4, 5, 6 characters), unicode and accents ("cafe" vs "café"), a title that is an exact
copy of an existing one, markup in titles (check escaping, remember BUG-005), a tracker with 1 issue and
one with 10,000, double submit, slow network, disabled parent component with enabled child.

## 7. Verdict
Not ready for development. Five statements are untestable and eight questions need answers. Most of this
can be fixed in one 30 minute conversation with the product owner. The core algorithm is already testable.
