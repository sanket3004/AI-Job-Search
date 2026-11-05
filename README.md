# AI Job Toolkit

An installable **Agent Skill** for a personal job search: fresh profile, job discovery, fit assessments, tailored documents, recruiting contacts, browser applications and tracking. Version 0.3.0.

The AI agent you already use supplies the reasoning and tools. The canonical package is **`skills/ai-job-toolkit/`**. It includes `SKILL.md`, focused workflow references, a standard-library Python state helper and Codex display metadata. It has no model API dependency and includes no personal profile.

## Install and use

Python 3.10+ is needed for saved state. From this repository, install into a project:

```powershell
python tools/install_skill.py --host codex --project "D:\path\to\your\workspace"
python tools/install_skill.py --host claude --project "D:\path\to\your\workspace"
```

For all local projects, use `--user` instead of `--project ...`. Use `--dry-run` to print the destination without writing. The installer is idempotent for identical files and refuses to overwrite a different existing skill. The full folder can also be copied into another agent's documented skill location.

- Codex: invoke **`$ai-job-toolkit`**.
- Claude Code: invoke **`/ai-job-toolkit`**.
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
- Installation, ZIP packaging, automated behavior tests and a local browser-form simulation.

The host AI performs web research, document authoring and browser actions through tools it already has. The Python helper **does not scrape sites, drive a browser, send messages or submit applications**. Installing the skill does not add those tools or grant permissions. Browser workflows work only where the host tools and site access permit them; universal form support and unattended applications on LinkedIn/Indeed are not claimed. Live employer applications have not been submitted in release validation.

## Profile setup choices

Choose **Import resume**, **LinkedIn profile/export**, **Indeed profile/export**, or **Answer questions**. Combine sources if useful. The agent extracts professional facts, preserves existing confirmed answers, flags conflicts, and shows a proposed profile before applying it. Nothing is automatically copied from the original reference project's profile.

Account exports are local file imports, not account connections. Direct account reads require an already available permitted connector/browser and your authorization; there is no built-in LinkedIn/Indeed OAuth integration. LinkedIn archives default to professional-profile CSVs and skip messages/connections. Other archives require selecting the relevant files after inspection.

The core helper and DOCX/text/CSV/JSON imports use Python's standard library. PDF extraction optionally requires `pypdf` (`python -m pip install -r skills/ai-job-toolkit/scripts/requirements-pdf.txt`) or an existing host PDF tool. Scanned PDFs need OCR/visual review through the host; the importer does not include OCR. No extraction sends files to a service.

## User experience

Ask in ordinary language. The skill offers a short task menu when useful and returns job tables, clear next actions and a read-only HTML report. All browser filling ends at review by default. Specific submission approval or a scoped automatic batch can be recorded when authorized, subject to the host's permission requirements. Contact outreach has separate authorization.

Candidate data goes in an explicit private workspace, outside the installed skill. The helper initializes a workspace ignore file; avoid placing data in source control. Workspace files are not encrypted by this package. Browser sessions and credentials remain managed by the host. A database backup must include the artifacts directory to preserve document bytes.

## Repository layout

```text
skills/ai-job-toolkit/    Canonical installable skill
tools/                   Installer and ZIP builder
tests/                   State/packaging tests and local browser fixture
legacy/dashboard/        Archived standalone prototype; separate data model
```

The old dashboard is retained for reference and is not synchronized with the skill workspace. Use the skill's generated report for the current application's saved state.

## Validate and package

```powershell
python -m unittest discover -s tests -v
python tools/package_skill.py
```

The ZIP is written to `dist/ai-job-toolkit.zip`, containing only the canonical skill folder. It excludes runtime data, caches and the archived dashboard. A ZIP does not guarantee support by every chat interface; use that host's documented skill installation flow.

Workspace backups should include `imports/` to preserve evidence behind reviewed profile changes, along with the database and application artifacts.

Installation references: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code skills](https://code.claude.com/docs/en/skills).
