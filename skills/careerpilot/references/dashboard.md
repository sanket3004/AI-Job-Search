# Local dashboard

The dashboard is an optional, read-only view of the canonical workspace. It ships inside the skill and uses only Python's standard library. It is not the archived standalone app and does not require a hosted service or model API.

When the user asks to open a dashboard, resolve the workspace already in use. Initialize a fresh workspace only if needed; do not create a second workspace for an existing search. Start a retained local process:

```text
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" dashboard --open
```

`--open` opens the default browser. Alternatively omit it and open the exact printed URL through the host's supported browser. The server binds only to 127.0.0.1, defaults to port 8765, and issues a fresh URL token on each start. Use `--port 0` for an available port, or a specific port when needed. Keep the process running while the user uses the dashboard; Ctrl+C stops it. A stopped URL will no longer work. Do not expose it publicly or send its URL to external services.

On Windows, the repository's `Open Dashboard.cmd` launches the default `job-search-workspace` and browser. An optional first argument selects another workspace. It initializes an empty workspace if absent; it does not import candidate data.

Views:
- Overview: counts, recent jobs, decisions needing attention, and setup progress.
- Job pipeline: search, status filters, fit sorting, and application detail dialogs.
- Profile: confirmed facts, source provenance, and import change reviews.
- Documents: downloads of registered files, verified against their saved hashes.
- Contacts and drafts: sourced professional contacts and unsent messages.
- Activity: saved state changes and historical submission permissions.

Data refreshes every five seconds while the tab is visible. Connection failures clearly label the last snapshot as stale. A saved `Filling` status is not proof that an agent is currently running. Checkpoints do not restore website sessions. Submission permissions shown are historical records, not a fresh validity check.

The dashboard never edits profiles, changes jobs, authorizes submission, starts agents, or sends messages. "Continue with AI" and similar buttons show copyable requests for the user's agent chat. Help the user act on those requests using the existing skill workflows and authorization requirements. Downloaded JSON is a state export, not a complete backup of artifact files.

For a portable, static snapshot without a running server, keep using `report`. Its generated HTML is separate from the live dashboard.
