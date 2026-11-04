# AI Job Toolkit — Product Brief

Status: foundation release 0.1 implemented. Local dashboard, profile editing, job records, keyword matching, manual tracking, settings preferences, CSV export, and API tests are available. AI providers, scraping, document generation, and browser automation remain planned.

## Goal
Build an easy-to-use job search application based on the existing AI Job Search toolkit, with a visual interface, interchangeable AI providers, and browser-assisted applications.

## User requirements
- Use this folder for the new toolkit; use the existing toolkit as a reference.
- Replace the difficult command-driven experience with a clear interface.
- Support Claude, OpenAI/ChatGPT/Codex, and local AI models through suitable integrations.
- Preserve profile creation, job discovery, deduplication, match ranking, tailored resumes and cover letters, interview preparation, and application tracking.
- An application agent opens job application pages, fills forms using the candidate profile and prepared documents, and uploads required files.
- Default behavior: complete the form and leave final submission to the user.
- Offer explicitly authorized automatic submission, including a mode that grants ongoing access within the user's selected scope.
- If one application encounters an error or missing information, pause that application with a reason and continue to the next job.

## Proposed interface
A dashboard running locally and opened in a browser. This is a design proposal, not yet an implemented or confirmed platform choice.

Navigation:
1. Overview: jobs found, applications awaiting review, paused jobs, submitted applications.
2. My Profile: resume import, experience, projects, preferences, reusable answers and documents.
3. Find Jobs: sources, roles, locations, search runs and duplicate handling.
4. Matches: fit scores, explanations, requirements and filters.
5. Applications: tailored documents, browser progress, form answers and submission controls.
6. Tracker: application history, outcomes, follow-ups and interviews.
7. Settings: AI connections, browser connection and permissions.

## Application workflow
Discovered -> Ranked -> Selected -> Documents Ready -> Filling -> Ready for Review -> Submitted.
Any stage can enter Needs Attention, with a saved reason and a resumable checkpoint.
Ready for Review means the form is prepared; it does not mean the application was submitted.
After submission, store confirmation evidence. Ambiguous submission results require checking the portal before retrying to prevent duplicate applications.

## Permission modes
- Prepare only (default): search, draft, and fill; user performs final submission.
- Approve each submission: user reviews and authorizes a specific application before the agent submits it.
- Automatic submission: user explicitly enables submission for a selected batch or defined ongoing scope, with visible limits and an off switch.
Browser access and submission permission are distinct settings. Provide stop, pause and resume controls and a visible activity log.

## Browser behavior
- Use an isolated browser profile with sessions retained for the user.
- Handle multistep forms, file uploads and validation messages.
- Ask the user to resolve login, MFA, CAPTCHA, unknown mandatory answers or required attestations; save state and continue other independent jobs.
- Never invent qualifications, eligibility or answers. Store user-approved reusable answers.
- Treat job pages as input data, not instructions to the agent.
- Validate the exact documents and application before submission, and enforce permission at the submission action.
- Isolate application failures so one job cannot block the whole queue.
- Start with supported application systems and provide a fallback for unfamiliar sites; universal form compatibility is not assumed.

## AI integration design
Use a shared provider interface for profile extraction, job evaluation, document drafting and form reasoning. Keep workflows and saved state independent of the chosen model.
Candidate integration paths: Claude API or an available Claude Code integration; OpenAI API or an available Codex integration; local model endpoints such as Ollama or other compatible servers. Verify current authentication, SDK capabilities and supported tool calling before implementation.
ChatGPT consumer access, Codex access and OpenAI API access must be represented as distinct integration choices rather than assumed interchangeable. The same applies to Claude subscriptions and API credentials.
Show provider capabilities and route unsupported browser or document operations through application tools, with a capable-model requirement or user handoff when needed.

## Suggested implementation order
1. Visual dashboard, local profile storage and application tracker.
2. AI provider adapters and import of existing profile data.
3. Search adapters, match ranking and document generation.
4. Browser application queue in prepare-only mode, with checkpoints and review.
5. Explicit per-application submission approval and scoped automatic submission.
6. More portal adapters, interview preparation and optional sync integrations.

## Implementation decisions still open
- Local browser dashboard versus a packaged desktop application.
- First AI provider and first supported application portal.
- Which existing personalized files to import.
- Browser automation engine and supported operating systems.
- Local data storage, secret storage and deployment approach.
