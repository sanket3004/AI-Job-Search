# Profile and application documents

## Fresh profile

Build a new profile from information the current user supplies. Offer resume import, LinkedIn/Indeed profile or export import, and guided questions; use [profile import](profile-import.md) for extraction and reviewed merges. Do not search unrelated folders or import an old toolkit profile. Collect in small groups and save progress. The profile JSON supports:

```json
{
  "name": "Candidate name",
  "email": "user-provided address",
  "location": "user-provided location",
  "target_roles": ["Data Analyst"],
  "preferences": {"locations": [], "work_arrangements": [], "deal_breakers": []},
  "skills": ["Python", "SQL"],
  "experience": [],
  "education": [],
  "projects": [],
  "answers": [
    {"question": "Notice period", "answer": "Two weeks", "source": "User confirmed in this chat"}
  ]
}
```

Omit unknown facts. Store relevant applicant answers only when volunteered/confirmed. Do not put passwords, authentication tokens, government ID numbers, or payment information in the profile. If a form asks for such information, hand it to the user rather than persist it. Ask the user about required personal eligibility questions instead of deriving answers.

`profile-save` replaces the profile and increments its revision for direct manual updates. Imported facts use `profile-preview` followed by `profile-apply` after user review. Read the current profile before either path so unrelated facts are preserved. Existing form approvals become stale; re-review affected ready applications.

## Tailor documents

1. Read the selected posting and the current profile. Extract essential requirements and compare them with sourced experience.
2. Create a resume using only supported skills, titles, dates and achievements. Rearrange emphasis for the role without changing facts. Keep genuine gaps visible.
3. Write a specific cover letter if requested or required. Connect the user's experience to the role; do not fabricate enthusiasm, company knowledge, or contacts.
4. Use the user's requested format or an available document skill/renderer. Favor a readable single-column resume and literal contact text. Page count should fit the candidate and posting, not an arbitrary universal limit.
5. Check rendered output when producing PDF/DOCX. Check extracted PDF text, contact details, reading order, and supported job keywords. Do not call a Markdown draft an ATS-verified PDF. If rendering is unavailable, deliver the draft with that limitation and keep application preparation pending if a final file is required.
6. Register actual files with `document-add`: resume, cover_letter, or other. The helper copies each file into the workspace and records a SHA-256 digest. Each changed file invalidates earlier approval snapshots. Preserve the final exact version used for an application.

Use available document tools without requiring a particular vendor. A second review may be useful when the host supports it and delegation is authorized; it is not a mandatory extra model call.
