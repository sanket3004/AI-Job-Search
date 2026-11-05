# AI Job Toolkit

A local job-search workspace. Foundation release 0.1. Requires Python 3.10 or later; no package installation needed.

## Start

Double-click **Start Toolkit.bat**, or run `python server.py` in this folder. Your browser opens at http://127.0.0.1:8765. Keep the server window open. Stop with Ctrl+C. If the port is in use, run `python server.py --port 8766`.

## Available now

- Responsive dashboard with profile, matches, application queue, tracker and settings.
- Editable candidate profile persisted in SQLite.
- Save job descriptions and URLs, with duplicate URL detection.
- Transparent keyword overlap ranking, search and status filtering.
- Manual application statuses, pause reasons, notes and activity history.
- CSV export of job records (not a full workspace backup).
- Saved provider preferences; prepare-only submission setting.

No example applications or personal data are preloaded. Add a profile and real job postings to begin. Existing profile files are not imported automatically.

## Not connected yet

AI provider execution, job scraping, resume import, document generation, browser form filling, automatic queue execution and submission are not implemented in this release. Statuses are manual records, including “Submitted” and “Ready for review”; changing them does not perform actions on job portals. Settings save preferences only. Keyword percentages count listed profile skills found in a posting and are not AI assessments or eligibility scores.

## Data and access

Saved data lives in `data/toolkit.db`. To back up the complete workspace, stop the server and copy this database. The server binds only to this computer; it is a single-user local app, with no account system. Files are not encrypted by the app. Do not expose this server to a network or commit the database to Git.

## Next milestones

1. Fresh structured profile and reusable application answers; no import of the existing personalized profile.
2. Browser form-filling agent on a supported employer application site, with one AI provider, review before submission, and clear pauses for missing answers.
3. Resumable application queue that continues other jobs when one is blocked.
4. Permitted job discovery integrations, AI ranking, and tailored resumes and cover letters.
5. Public recruiting-contact research with evidence, published work emails when available, and outreach drafts.
6. Explicit submission permissions, more providers and portal adapters.

## Checks

Run `python -m unittest discover -s tests -v` for API and persistence checks.
