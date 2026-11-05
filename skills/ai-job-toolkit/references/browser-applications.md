# Browser application agent

## Use the host's browser

Use the connected browser/computer tools the host actually provides. Read their APIs and permission requirements. The skill does not include a browser driver or assume a Playwright/CDP endpoint. If browser tools are missing, explain the specific missing capability, pause affected jobs, and continue document preparation. Do not install a browser extension or change host security settings implicitly.

Process selected job IDs or a user-authorized queue limit. Get `next` from the helper. A paused job is excluded until explicitly resumed. Each browser action must be grounded in the latest observed page, visible labels and validation messages, not guessed selectors or a stale form map.

## Per-job loop

1. `start` the selected job. Open its application URL; inspect the page and destination employer. When redirected, check the employer/role still match. Stop if the destination is unrelated or unsupported.
2. If login, MFA or CAPTCHA requires the user, record the current page, a clear blocker and next action; `pause` this job. Follow host rules for handoff. Continue another independent job when possible.
3. Inspect required fields, page steps, uploads, and the final submit control. Map each answer to an exact profile fact, user-approved reusable answer, or verified document. Do not guess missing eligibility, employment dates, compensation, legal attestations, demographic answers or consent choices.
4. Fill known fields and upload only the registered job-specific documents. Store a `checkpoint` after each page and validation pass: observed URL, step, answered fields with their source, unresolved required questions, and a short description of what was observed. Do not persist credentials or tokens from URLs; redact sensitive query parameters.
5. Reinspect after actions, dropdown changes and navigation. Correct supported validation errors. After at most two unsuccessful attempts on the same error, pause with the visible error and continue the queue. Checkpoints are saved instructions/evidence; a site may not preserve the actual form session. On resume, re-open and inspect before re-filling anything.
6. If a required answer is unknown, `pause` with the actual question. Do not classify the whole page as completed because text was typed into visible fields.
7. On the final review page, verify every required answer, uploaded file, employer/role and remaining validation message. Record `complete: true` only when the observed form is genuinely ready, then call `ready`. Generate the report and give the user a summary plus the live tab handoff when supported.

## Submission modes

**Prepare only:** leave final submission to the user. `ready` does not authorize a click. If the user later says they submitted manually, use `manual-submitted` with their statement as evidence, explicitly labeled as user-reported.

**Approve each:** after the user authorizes the exact reviewed application, record `authorize` for its ID and an expiry, then call `submit-begin` immediately before the browser submit action.

**Scoped automatic batch:** record the user's explicit scope, selected exact IDs, and expiry. For jobs not ready yet, prepare them first and record the matching approval after the review snapshot exists; do not ask again if the original instruction still covers those jobs and details. Expanding the job set or changing reviewed answers/documents requires authorization that covers the changed scope. A broad statement of desired product behavior is not permission to send real applications now.

The helper binds permissions to the exact job, current profile revision, checkpoint and document hashes. It consumes authorization at `submit-begin` so interruptions cannot replay a submit automatically. Host-required approvals still apply; the helper cannot relax them.

After the click, inspect confirmation. Record `submitted` with observed confirmation text and source URL or receipt. If no definite result is observable, call `uncertain`. Never repeat submission based on a timeout. On session recovery, jobs left in `Submitting` must be reconciled the same way. Use `resolve` with evidence to confirm submission or confirm non-submission; a new submit requires fresh authorization.

## Queue behavior and honest status

- Per-job failure: persist reason/checkpoint, continue to `next`.
- Shared browser outage: pause processing and explain the dependency; avoid opening every job into the same failure.
- User stop: save the current checkpoint and stop. Do not keep working in the background.
- Completion: list ready-for-review, paused, submitted and uncertain separately, with next actions.

The helper coordinates state; only actual browser observations establish form completion or submission. Never manufacture those observations for a demonstration. Use the repository's local test form for simulated evaluations and label them as such.
