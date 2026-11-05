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
