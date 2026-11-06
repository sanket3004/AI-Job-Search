# CareerPilot

Your AI companion from job discovery to application.

An installable **Agent Skill** for a personal job search: fresh profile, job discovery, fit assessments, tailored documents, recruiting contacts, browser applications and tracking. Version 0.8.0.

The AI agent you already use supplies the reasoning and tools. The canonical package is **`skills/careerpilot/`**. It includes `SKILL.md`, focused workflow references, a standard-library Python state helper and Codex display metadata. It has no model API dependency and includes no personal profile.

CareerPilot was previously named AI Job Toolkit. The skill command is now `careerpilot`; existing `job-search-workspace` folders and their `toolkit.sqlite3` database remain compatible. Open the same workspace to continue an existing search. The project folder and GitHub repository URL can retain their existing names.

## Install and use

Python 3.10+ is needed for saved state. From this repository, install into a project:

```powershell
python tools/install_skill.py --host codex --project "D:\path\to\your\workspace"
python tools/install_skill.py --host claude --project "D:\path\to\your\workspace"
```

For all local projects, use `--user` instead of `--project ...`. Use `--dry-run` to print the destination without writing. The installer is idempotent for identical files and refuses to overwrite a different existing skill. The full folder can also be copied into another agent's documented skill location.

- Codex: invoke **`$careerpilot`**.
- Claude Code: invoke **`/careerpilot`**.
- Local models: load the skill in a compatible agent runtime with file, Python and browser tools. A bare model endpoint does not supply those capabilities.

Examples:

> Use this skill to create a fresh profile and find suitable jobs.

> Import my resume and LinkedIn export, show me conflicting facts, and let me review the profile before saving it.

> Help me get my Indeed resume or profile export into the toolkit.

> Prepare applications for these three roles. Fill the forms, pause anything that needs my input, and leave Submit to me.

> Show my application progress and draft a message to a verified recruiting contact for this role.

## What works in this release

- Resume import (PDF, DOCX, TXT/MD), LinkedIn professional CSVs/ZIPs, and selected Indeed/account export files (PDF/DOCX/TXT/MD/CSV/JSON).
- Local source extraction, provenance, profile change previews, and confirmation before applying imported facts. Stale or altered-source previews are rejected.
- Portable workflow instructions with progressive references for each job-search stage.
- Fresh profile and durable job records, deduplication, fit assessments, notes, contacts and unsent outreach drafts.
- Document copies with hashes; review snapshots tied to the profile, answers and exact files.
- Per-job pause/resume, explicit queue selection, submission authorization records, and uncertain-result recovery.
- A private HTML review report and JSON state export.
- A charcoal dashboard with direct role/location search, posting-date filters, ranked results including low matches, timestamped search lists, and the same profile/documents/contacts/activity views.
- Installation, ZIP packaging, automated behavior tests and a local browser-form simulation.

The host AI performs web research, document authoring and browser actions through tools it already has. The dashboard can fetch supported public job feeds directly. The Python helpers **do not fill employer forms, send messages or submit applications**. Installing the skill does not add those tools or grant permissions. Browser workflows work only where the host tools and site access permit them; universal form support and unattended applications on LinkedIn/Indeed are not claimed. Live employer applications have not been submitted in release validation.

## Search from the dashboard

Enter a **job role**, **location**, and **posting-date range**. The default **LinkedIn + Indeed** mode saves a primary search request and opens a prompt to run with your connected AI/browser. Both portals are required. Only verified employer/ATS application routes enter the ranked list; LinkedIn Easy Apply and Indeed on-platform applications are excluded. Unknown routes remain excluded until verified. All eligible scores, including low matches, stay visible. Blocked source access is recorded honestly.

The explicitly selected **Supplementary public feeds** mode runs locally without an AI session or API key. It keeps all role candidates within the date range, but does not satisfy the required primary-source coverage or verify external-application eligibility.

Supplementary sources are [Remotive](https://remotive.com/remote-jobs/api), [Jobicy](https://github.com/Jobicy/remote-jobs-api), and [Arbeitnow](https://www.arbeitnow.com/blog/job-board-api), via their public JSON feeds. Remotive/Jobicy focus on remote jobs; Arbeitnow covers Europe, primarily Germany. This dashboard search does **not** scrape LinkedIn or Indeed. The host AI performs the required LinkedIn/Indeed search through permitted tools; no direct portal scraper is bundled.

Remotive is cached for six hours and its public jobs are delayed by 24 hours. Jobicy covers the last seven days. Jobicy and Arbeitnow are cached for one hour; each refresh stops after five pages and reports incomplete coverage when more pages exist. Source errors, invalid rows, date-filter exclusions and fetch timestamps are visible in each list. Repeating a search creates a new list but may use the same cached feed data. There is no claim of exhaustive regional coverage.

Automatic relevance is a transparent 0–100 comparison: title words up to 45, description words up to 15, and location text up to 40. It is not an AI fit assessment or a hiring probability. AI assessments remain separate. Geographic matching is textual; a broad remote restriction does not prove eligibility in a specific city.

Each row shows the source's posting date, or **Unknown**. Date-filtered searches exclude unknown dates unless the checkbox includes them; any-time searches include them. The window is measured backward from the search start. Source dates without a timezone are treated as UTC; the browser displays dates/times in its local timezone. **Search history** preserves a timestamped snapshot for every run, including per-source fetch times, so yesterday's list remains available when you search today. Searches run when requested; this release does not schedule a daily search automatically.

## Profile setup choices

Choose **Import resume**, **LinkedIn profile/export**, **Indeed profile/export**, or **Answer questions**. Combine sources if useful. The agent extracts professional facts, preserves existing confirmed answers, flags conflicts, and shows a proposed profile before applying it. Nothing is automatically copied from the original reference project's profile.

Account exports are local file imports, not account connections. Direct account reads require an already available permitted connector/browser and your authorization; there is no built-in LinkedIn/Indeed OAuth integration. LinkedIn archives default to professional-profile CSVs and skip messages/connections. Other archives require selecting the relevant files after inspection.

The core helper and DOCX/text/CSV/JSON imports use Python's standard library. PDF extraction optionally requires `pypdf` (`python -m pip install -r skills/careerpilot/scripts/requirements-pdf.txt`) or an existing host PDF tool. Scanned PDFs need OCR/visual review through the host; the importer does not include OCR. No extraction sends files to a service.

## User experience

### Open your dashboard

On Windows, double-click **`Open Dashboard.cmd`** in this repository. It opens the default `job-search-workspace` in your browser and creates an empty workspace if needed. Keep the terminal running; Ctrl+C stops the dashboard. To use another saved workspace, pass its path as the launcher's first argument or ask your AI to open that workspace's dashboard.

From any installed copy of the skill:

```powershell
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" dashboard --open
```

Initialize a new workspace with `init` first. The dashboard refreshes every five seconds while visible, uses a per-session local URL, and binds only to this computer. Use `--port 0` if the default port 8765 is occupied. No extra packages, hosting, or model API are required.

The dashboard defaults to required LinkedIn/Indeed search requests; optional supplementary feed searches run locally. Both use the canonical state helper. It also provides copyable requests for your AI chat. It does not run an AI agent, import profiles, grant permissions, or submit applications. Documents download only if they still match their registered content. Export data downloads state JSON; include workspace artifacts and imports separately for a full backup.

Ask in ordinary language. The skill offers a short task menu when useful and returns job tables, clear next actions and a read-only HTML report. All browser filling ends at review by default. Specific submission approval or a scoped automatic batch can be recorded when authorized, subject to the host's permission requirements. Contact outreach has separate authorization.

Candidate data goes in an explicit private workspace, outside the installed skill. The helper initializes a workspace ignore file; avoid placing data in source control. Workspace files are not encrypted by this package. Browser sessions and credentials remain managed by the host. A database backup must include the artifacts directory to preserve document bytes.

## Repository layout

```text
skills/careerpilot/    Canonical installable skill
tools/                   Installer and ZIP builder
tests/                   State/packaging tests and local browser fixture
legacy/dashboard/        Archived standalone prototype; separate data model
```

The archived dashboard is retained for reference and is not synchronized with the skill workspace. Use the new skill dashboard or generated report for current saved state.

## Validate and package

```powershell
python -m unittest discover -s tests -v
python tools/package_skill.py
```

The ZIP is written to `dist/careerpilot.zip`, containing only the canonical skill folder. It excludes runtime data, caches and the archived dashboard. A ZIP does not guarantee support by every chat interface; use that host's documented skill installation flow.

Workspace backups should include `imports/` to preserve evidence behind reviewed profile changes, along with the database and application artifacts.

Installation references: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code skills](https://code.claude.com/docs/en/skills).


## Accounts and phone assistance (0.6)

Open **Accounts & alerts** in the dashboard to save default signup details, approve exact career-site origins for login/signup, and securely save existing passwords. New signups can receive unique generated passwords. Windows DPAPI protects the private settings database; secrets are excluded from workspace exports. Non-Windows hosts currently need password-manager autofill/manual assistance.

Configure a Telegram bot in the same screen: create it with @BotFather, send /start to your bot, paste its token locally, select **Find my Telegram chat**, choose your account, enable alerts, save, and send a test. Do not paste secrets into AI chat. Normal low-volume bot alerts require no extra AI calls.

Every agent `pause` creates an **Assistance** request and attempts one phone alert, even if the dashboard is closed. Failed delivery can be retried. Resolve the blocker through your separately configured Chrome Remote Desktop, enter a note, and return the job to the queue. Keep the laptop awake and the application agent running; notifications do not start a background AI session.

Automatic credential filling requires host password-manager support or the optional Playwright bridge connected to an existing authorized local CDP browser. The bridge fills but never submits; the host handles approved login/signup clicks and observed confirmation. MFA, CAPTCHA, unsupported browsers, and host-required confirmations still need assistance. Account permissions do not authorize application submission.

See [full setup and browser compatibility](skills/careerpilot/references/accounts-and-assistance.md). The portable core is standard-library-only; the optional credential bridge requires `python -m pip install playwright` in the Python environment used by the host.


## Gmail application updates (0.7)

**Email updates** adds a read-only Gmail review workflow, application response statuses, supporting message excerpts and Gmail links, review/dismiss controls, optional automatic updates for confirmed matches and clear outcomes, and dated check history. It distinguishes application received, under review, assessment, interview, rejected, offer, withdrawn and unknown.

Connect Gmail through your AI host, enter the intended mailbox in the dashboard, and enable review of emails related to saved applications. Use **Check Gmail with AI** and paste the generated request into your host agent. The dashboard does not itself connect to Gmail or launch a background agent. No email passwords or OAuth tokens are stored locally for this feature, and it never sends or modifies mail.

The agent matches messages to exact saved applications, records minimal evidence, and imports through transactional state commands. Repeated message IDs are deduplicated; older, regressive, ambiguous and conflicting outcomes are held for review. An uncertain submission must be reconciled before applying an email outcome. “Approved for another round” is not treated as an employment offer.

See [Gmail review agent](skills/careerpilot/references/email-review.md). Scheduled checks require a separately configured host scheduler; no schedule is installed automatically. Gmail access remains inactive until the user configures and authorizes the account.


## Required portals and application filter (0.8)

LinkedIn and Indeed are now the primary required sources. Exclude Easy Apply, Indeed Apply / Apply with Indeed / Easily apply, and mixed listings that also offer an on-platform route. Import only recently verified external employer/ATS applications, preserving the original portal link, employer destination, posting date and verification evidence. Both portal outcomes must be recorded before a run can finish. A blocked portal yields partial/failed coverage, not a silent public-feed fallback.

Primary requests run through the host AI/browser after copying the dashboard prompt. The dashboard does not independently scrape these portals or start an agent. Historical saved jobs are retained and are not retroactively verified; recheck their routes before applying. See [primary portal workflow](skills/careerpilot/references/portal-search.md).
