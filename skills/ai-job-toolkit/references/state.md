# State helper contract

Use the absolute path to the installed `scripts/toolkit.py` and to the user's workspace. Commands return JSON, exit nonzero on failure, and never send network requests or control a browser. Python 3.10+ is required. The private SQLite file is `toolkit.sqlite3`; no candidate data ships in the skill.

```text
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" init
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" status
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" show
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" show --job JOB_ID
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" next
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" run --input "WORKSPACE/request.json"
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" report
python "SKILL_DIR/scripts/toolkit.py" --workspace "WORKSPACE" export
```

Write mutation payloads with a file-writing tool as UTF-8 JSON; avoid interpolating profile text into shell commands. `--input -` accepts stdin. `show` includes private candidate data; retrieve only the job needed when possible. `export` saves state JSON, not a complete backup of document bytes. Back up the closed workspace database plus its artifacts to preserve everything.

Each request has `op`, plus the fields below. Job operations require the returned `job_id`; never invent it. Extra fields are not commands.

| op | Fields |
|---|---|
| `profile-save` | `profile`: complete object; replaces prior profile, increments revision |
| `job-add` | `title`, `company`, `url`, `description`, `source`; optional `location` |
| `evaluate` | `job_id`, `evaluation` with arrays `strengths`, `gaps`, `unknowns`, `evidence`; `recommendation`; optional `score` 0–100 plus `rationale` |
| `select` | `job_id`; Saved → Selected |
| `document-add` | `job_id`, `kind`: resume/cover_letter/other, absolute `path` to actual file |
| `start` | `job_id`; Selected/Preparing → Filling |
| `checkpoint` | `job_id`, `checkpoint` object described below |
| `pause` | `job_id`, `reason`, `next_action` |
| `resume` | `job_id`, `note` explaining resolution; → Preparing |
| `ready` | `job_id`; requires current-profile checkpoint, complete=true, no unresolved questions |
| `authorize` | `job_ids`: exact list of reviewed IDs, `user_instruction`: actual user authorization, `expires_at`: future ISO timestamp with timezone |
| `revoke` | `authorization_id` |
| `submit-begin` | `job_id`, `authorization_id`; consumes permission and records Submitting |
| `submitted` | `job_id`, `evidence`: actual observed confirmation/receipt |
| `uncertain` | `job_id`, `evidence`: why result is unknown |
| `resolve` | `job_id`, `result`: submitted/not_submitted, `evidence` from portal or user |
| `manual-submitted` | `job_id`, `evidence`: user's statement; labels result user-reported |
| `contact-add` | `job_id`, `contact`: see contact reference |
| `outreach-draft` | `job_id`, `recipient`, `channel`, `text`; saves draft only |
| `note` | `job_id`, `text` |
| `outcome` | `job_id`, `status`: Interview/Rejected/Offer/Withdrawn/Expired, `evidence` |

Example checkpoint shape (replace with actual observed facts):

```json
{
  "op": "checkpoint",
  "job_id": "ID_RETURNED_BY_HELPER",
  "checkpoint": {
    "page_url": "https://employer.example/apply/review",
    "step": "Final review",
    "answers": [{"field": "Full name", "value": "User-provided name", "source": "profile.name"}],
    "unresolved": [],
    "complete": true,
    "observation": "Observed all required fields complete, expected file attached, no validation errors. Submit remains unclicked."
  }
}
```

Do not use example observations as real evidence. `checkpoint` overwrites the previous current checkpoint, so provide the full known answer map across earlier pages. Registered document hashes and profile revision are included in review snapshots. Changed answers/documents invalidate earlier authorization; `profile-save` requires a new observed checkpoint. `authorize` records intent but does not prove it: the agent must use actual user instructions and honor the host's own approvals.

`next` returns the first Selected/Preparing job plus IDs left Filling/Submitting/Submission uncertain. Review in-flight IDs after an interruption. A Filling job can receive a new checkpoint or be paused. Submitting/uncertain jobs must be reconciled, never retried automatically. Paused jobs stay excluded until `resume`. The helper is serial per workspace transaction; do not run multiple browser workers against the same job.

The HTML report is a private read-only snapshot, with escaped content and no scripts. Its document links reference the workspace artifacts. Rebuild after changes. It cannot restore a browser session or perform submission.
