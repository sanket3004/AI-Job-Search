# CareerPilot — skill package

## Product direction

An installable skill that the user adds to an AI agent, analogous to their Reverse Engineer Anything skill. The host supplies its chosen model and tools; the package supplies task instructions, persistent records and reusable helpers. A standalone dashboard is optional, not the product's foundation.

## Requirements

- Start with a fresh user profile. Never import the author's existing personalized profile.
- Support compatible Claude Code, Codex and local-model agent environments without embedding a model vendor.
- Search jobs from permitted sources, including LinkedIn/Indeed where supported, with pasted postings and employer-site alternatives.
- Evaluate fit against actual experience; draft tailored resumes and cover letters without invented claims.
- Find recruiting contacts through public professional sources, attach evidence, and include only published business emails. Prepare outreach drafts; sending requires separate authorization.
- Prioritize browser-assisted applications: fill observed fields, upload the correct documents, handle validation, pause blocked jobs and continue other selected jobs.
- Default to prepare-only. Support explicit per-application or scoped batch submission authorization, bound to reviewed content and subject to host permissions.
- Preserve checkpoints and exact document versions. Reconcile ambiguous submissions before retrying.
- Keep the interface simple through natural-language tasks, compact tables, meaningful next actions and a local review report.

## Release 0.2.0

Implemented: canonical SKILL.md, focused references, host-capability guidance, Python workspace helper, job queue state, evidence-linked assessments and contacts, document hashing, approval snapshot checks, local report, installer, ZIP builder and automated tests.

Browser actions are orchestrated by the host agent using its connected tools; the helper is not a browser driver. The fixture demonstrates the intended prepare/review boundary locally. No live employer submission or universal portal compatibility is claimed. The original standalone prototype is archived separately.

## Next development

1. Use the skill in a fresh host session with the user's chosen browser tools and a newly created profile.
2. Exercise a user-selected employer application through final review, saving real checkpoints and upload evidence.
3. Improve narrow portal-specific behavior based on observed failures; retain the generic host-browser workflow.
4. Add reusable document templates and permitted job-source adapters where they improve reliability.
5. Expand review/report usability and validated compatibility across host environments.

## Release 0.3.0 — profile import options

Adds resume import, LinkedIn professional-profile exports, selected Indeed account/profile exports, and guided manual setup. Local extraction supports PDF (optional pypdf), DOCX, TXT/MD, CSV and JSON, including selected ZIP/folder members. The host AI proposes a merged profile from source evidence; the helper records a before/after preview and applies it only after user confirmation, with checks against stale profiles and changed evidence. No old toolkit profile is imported automatically.

Direct LinkedIn/Indeed account reading remains dependent on the host's available tools and permitted access; this release does not add account OAuth or a private API. Scanned documents require a separate OCR/visual tool. The import feature does not depend on Firecrawl.

## Release 0.4.0 — local dashboard

Adds an optional dashboard inside the portable skill, using the canonical SQLite workspace in read-only mode. It includes overview counts, search/filter/sort for jobs, application details and blockers, profile/import reviews, document downloads, contacts/drafts and activity. The browser refreshes saved state every five seconds. Copyable requests connect the visual review back to the user's agent chat; the dashboard itself does not run the agent or mutate state. A Windows launcher opens the default workspace, with an optional custom workspace argument. The static HTML report remains available.

## Release 0.4.1 — CareerPilot

Renames the product and installable skill to CareerPilot (`careerpilot`), including the dashboard, report, invocation prompts, host installation destinations and ZIP. Existing workspace locations, database format and application state are preserved. The archived prototype remains historical reference material.

## Release 0.5.0 — search, dates and saved lists

Adds a dark charcoal dashboard and a working role/location search form using public Remotive, Jobicy and Arbeitnow feeds. Every role candidate inside the selected posting-date window is retained, including low relevance and location mismatches. Results display ordinal ranks, an explained 0–100 search relevance score, source links and posting dates. This deterministic search score stays separate from AI fit assessments.

Date windows support any time, 24 hours, 7 days and 30 days, with explicit handling of unknown dates. Each run stores its own timestamped listing snapshot and source fetch times; cached feed reuse is visible. Daily searches can produce new historical lists without replacing prior searches. No daily scheduling or application submission is introduced. A five-page collection limit and source errors are reported as partial coverage. Existing application records and approved documents are preserved on rediscovery.

## Runtime boundaries

Skill installation does not install browser tools or grant account access. Local models require a tool-enabled host. Site access restrictions still apply. Personal profiles, browser credentials and generated application documents stay outside the distributed package and source repository.


## Delivered in 0.6

Encrypted Windows signup/account settings, exact-origin login/signup permission controls, optional credential-fill bridge, Telegram private-chat setup/test, automatic assistance requests on pause, failed-delivery retry, and dashboard resolution back to the application queue. Cross-platform password-vault backends and a universally compatible browser credential bridge are not implemented. Live Telegram activation requires the user’s bot and recipient setup.
