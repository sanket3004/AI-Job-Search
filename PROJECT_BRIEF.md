# AI Job Toolkit — skill package

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

## Boundaries

Skill installation does not install browser tools or grant account access. Local models require a tool-enabled host. Site access restrictions still apply. Personal profiles, browser credentials and generated application documents stay outside the distributed package and source repository.
