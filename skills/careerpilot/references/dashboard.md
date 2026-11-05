# Local dashboard

The dashboard is an optional local discovery and review interface for the canonical workspace. It ships inside the skill and uses only Python's standard library. It is not the archived standalone app and does not require a hosted service or model API.

When the user asks to open a dashboard, resolve the workspace already in use. Initialize a fresh workspace only if needed; do not create a second workspace for an existing search. Start a retained local process:

```text
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" dashboard --open
```

`--open` opens the default browser. Alternatively omit it and open the exact printed URL through the host's supported browser. The server binds only to 127.0.0.1, defaults to port 8765, and issues a fresh URL token on each start. Use `--port 0` for an available port, or a specific port when needed. Keep the process running while the user uses the dashboard; Ctrl+C stops it. A stopped URL will no longer work. Do not expose it publicly or send its URL to external services.

On Windows, the repository's `Open Dashboard.cmd` launches the default `job-search-workspace` and browser. An optional first argument selects another workspace. It initializes an empty workspace if absent; it does not import candidate data.

Views:
- Overview: counts, recent jobs, decisions needing attention, and setup progress.
- Job pipeline: all role candidates with ordinal rank, explained relevance score, source link, posting date, date/score/status sorting and filters, and application details. Low scores are visible by default.
- Search history: a separate dated result snapshot for each search, with its role, location, date range, start/completion time, source fetch timestamps and coverage.
- Profile: confirmed facts, source provenance, and import change reviews.
- Documents: downloads of registered files, verified against their saved hashes.
- Contacts and drafts: sourced professional contacts and unsent messages.
- Activity: saved state changes and historical submission permissions.

Data refreshes every five seconds while the tab is visible. Connection failures clearly label the last snapshot as stale. A saved `Filling` status is not proof that an agent is currently running. Checkpoints do not restore website sessions. Submission permissions shown are historical records, not a fresh validity check.

The Search jobs form starts a background public-feed fetch and saves discovery results through the state helper. It never edits profiles, advances application states, authorizes submission, starts AI agents, or sends messages. "Continue with AI" and similar buttons show copyable requests for the user's agent chat. Help the user act on those requests using the existing skill workflows and authorization requirements. Downloaded JSON is a state export, not a complete backup of artifact files.

For a portable, static snapshot without a running server, keep using `report`. Its generated HTML is separate from the live dashboard.

## Direct search, dates and ranking

Enter role, location, and a posting window (any/24 hours/7 days/30 days) in the dashboard. The Search jobs button contacts public Remotive, Jobicy and Arbeitnow JSON feeds; no model/API key is used and no profile is transmitted. It records results in `searches`, including a separate listing snapshot for each run. URLs deduplicate canonical job records; rediscovery does not overwrite application states, documents, or reviewed facts. Search history lists every run by local date/time. A run interrupted by a server shutdown remains visible and is labeled interrupted; start a new run to retry.

Retain all role candidates in the chosen date window, including low-scoring or geographically mismatched jobs. The dashboard labels relevance as a heuristic: title-word overlap (45), description-word overlap (15), and location text (40). Do not call this an AI assessment or infer eligibility. AI `evaluation` records stay separate. Each historical list retains the scores and posting data collected for that run.

Posting timestamps come from the provider, never from retrieval time. Missing/unparseable dates are Unknown and excluded from a date-filtered search unless requested; dates without a timezone are interpreted as UTC. Fetch timestamps and cached status are shown separately. Each search has its own creation/completion timestamps, even when cached results are reused. The dashboard does not run daily on its own.

Source documentation and limits:
- [Remotive](https://github.com/remotive-com/remote-jobs-api): remote public feed, 24-hour publication delay, six-hour cache; retain Remotive attribution and canonical listing link.
- [Jobicy](https://github.com/Jobicy/remote-jobs-api): remote feed for the past seven days, sequential cursor pages, one-hour cache, at most five pages per refresh. Retain the canonical Jobicy URL.
- [Arbeitnow](https://www.arbeitnow.com/blog/job-board-api): Europe-focused feed, one-hour cache and at most five pages per refresh.

These are finite sources, not exhaustive LinkedIn/Indeed or city-wide scraping. Report partial pagination and source errors honestly. Feed failures are cached too, to avoid repeated requests. A published listing is not proof that an employer is still accepting applications; check the page before preparing it. Cache files live under `search-cache/` in the private workspace and may be omitted from backups. Back up the database to retain all historical result lists.


Version 0.6 adds Accounts & alerts and Assistance. See [setup and browser handoff](accounts-and-assistance.md). Additional same-origin POST routes save encrypted settings, discover Telegram private chats, send a test, retry a notification, or resume a paused job with a resolution note. They never submit applications. Secret settings are omitted from state exports.
