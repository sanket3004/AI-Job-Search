# Release 0.2.0 validation

Completed on November 4, 2026:

- Skill creator's `quick_validate.py`: valid frontmatter and skill naming.
- 12 Python behavior tests passed: fresh profile/restart persistence; URL deduplication; independent paused jobs; incomplete/stale form checks; prepare-only state; scoped, one-use submission authorization; changed documents and answers; revocation and expiry; transaction rollback and confirmation evidence; contact email evidence; HTML escaping; installer collisions and ZIP contents.
- JavaScript/browser check on `tests/fixtures/application.html`: entered synthetic name `Test Candidate`, synthetic address `candidate@example.invalid`, and `Remote`; advanced to review; observed the expected answers and “Submission has not occurred”; left the final submission button unclicked.
- No employer website was filled or submitted during validation. No personal profile was imported. The optional file-upload field was not exercised by the browser check.

The browser check validates a small local form through the host's connected browser. It does not prove arbitrary portal compatibility, selector reliability across websites, or model-independent execution. The 12 tests exercise state behavior, not the judgment of every host/model. The helper has no browser/network execution engine.

PyYAML was used only in a temporary validation folder for the bundled skill validator. The distributed scripts use Python's standard library.

## Release 0.3.0 import validation

November 5, 2026: all 24 tests passed (12 existing state/packaging tests plus 12 import tests), with no skips. The new synthetic tests cover text/DOCX/PDF extraction, empty PDF handling, LinkedIn default file filtering, explicit Indeed archive selection, unsafe ZIP paths, CSV/JSON preservation, preview-before-apply, repeat apply rejection, stale profile preservation, altered evidence rejection, workspace boundaries and the extraction CLI. Skill validation also passed. PDF extraction uses optional pypdf; the base state helper remains standard-library only.

No real resume, account export, browser account session or original personalized profile was imported during these tests. The tested archive structures are synthetic; unknown real export layouts use inspection and explicit file selection. Account login and direct account access are not implemented by the extraction script.

## Release 0.4.0 dashboard validation

November 5, 2026: 31 Python tests passed (24 existing tests plus 7 dashboard tests). Dashboard checks cover fresh read-only reads from the canonical database, updates saved by another helper, token/Host/Origin restrictions, a static-asset allowlist and CSP, rejected mutation methods, verified document downloads and changed-file rejection, JSON export, and missing/unavailable databases. The HTTP tests required local loopback access outside the restricted sandbox. JavaScript syntax was checked with `node --check`.

Browser verification used only an isolated synthetic workspace and an empty workspace: overview counts, search combined with a status filter, paused-job details and checkpoint answers, copyable chat requests, profile details, documents, contacts/drafts, activity, automatic refresh after a saved note, and fresh-profile onboarding. No browser errors or warnings were reported on the final inspected page. The desktop layout was visually inspected; a screenshot is retained in ignored local work files. No real employer, account, profile, outreach message, or application was accessed or submitted.

The dashboard is a read-only local viewer, not a browser driver or background AI runner. Hosted access and mobile-device browser behavior were not validated. The server has no write API; agent actions still use the existing state helper and host permissions.

## Release 0.4.1 CareerPilot validation

November 5, 2026: all 31 existing tests passed after renaming the skill folder, host installer destinations, packaging and test imports to `careerpilot`. Skill frontmatter validation and JavaScript syntax checks passed. The package contains 18 files under `careerpilot/`. Workspace paths, database filename/schema, saved records and submission controls are unchanged; no candidate data was imported or migrated.

## Release 0.5.0 search validation

November 5, 2026: 44 tests passed, including all existing workflows plus public-feed normalization, date formats and exact window boundaries, unknown-date inclusion, preservation of low-scoring results, immutable per-search snapshots, deduplication without changing application state, pagination, partial-source failure, cache reuse, concurrent-request rejection, constrained source endpoints, same-origin search POST handling and rejected application mutations. Automated tests use synthetic sources only. JavaScript syntax validation passed.

An isolated live browser check searched `Data Analyst / Remote` through the dashboard. A seven-day run saved 128 postings, including 79 low-relevance results. A subsequent 24-hour run saved 65 postings using the same cached feeds. Both independently dated lists remained available in Search history. The UI correctly reported partial coverage at the five-page caps for Jobicy and Arbeitnow; Remotive returned ten feed rows, with no role candidates for this query. Posting dates, source fetch times, low-score filtering, newest-first sorting, score explanations, and historical-list reopening were verified in the browser. These counts describe this validation run, not expected future search volume or exhaustive coverage.

The dark desktop interface was visually inspected. No console errors/warnings were reported in the inspected browser view. The live check imported no personal profile and submitted no employer application or outreach. Test data and screenshots remain in ignored local work files.


## Release 0.6.0 validation — November 5, 2026

- 51 Python tests passed, including real Windows DPAPI round trips and ciphertext checks, secret omission from exports/API responses, exact-origin rejection, unique signup passwords and revocation, notification failure/retry/deduplication, mocked browser destination checks, cross-origin POST protection, and assistance resume validation.
- A Windows loopback connection interruption affected one test on an intermediate run; the complete rerun passed.
- JavaScript syntax and skill quick validation passed.
- In an isolated local browser workspace, saved synthetic signup defaults and observed the saved confirmation; created a synthetic paused job, observed its failed-delivery status with Telegram unconfigured, and resolved it through the dashboard back to the queue.
- Telegram network delivery was mocked in automated tests. No real bot token/recipient is configured and no live phone notification was sent.
- Credential bridge behavior was tested with a simulated page. No real employer login/signup or application submission was performed. Live Playwright/CDP compatibility requires a connected authorized browser and optional dependency.
- The user’s existing profile, application data and permissions were not imported or changed by validation.


## Release 0.7.0 validation — November 5, 2026

- 59 Python tests passed, including seven Gmail tracking behavior tests and a dashboard route protection check. Covered default review, opt-in automatic updates, message deduplication, changed/revoked permissions, account mismatch, stale/regressive messages, conflicting final outcomes, unknown classifications, scope/evidence validation and check completion.
- JavaScript syntax and skill frontmatter validation passed.
- Browser smoke test used an isolated synthetic workspace: opened Email updates, reviewed a demo interview invitation, applied it with a review note, and observed Submitted → Interview, pending → applied, and the review count decrease to zero.
- No live Gmail profile, messages or attachments were accessed; no mail was sent or modified. End-to-end mailbox retrieval awaits the user's configured account and connected host Gmail tools.
- No recurring task was created. The dashboard's Check Gmail with AI action generates a host-agent prompt and does not independently run an agent.
