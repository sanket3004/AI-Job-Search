# Discovery and fit ranking

Use the user's target role, location/work arrangement, experience level and deal-breakers. Preserve the source URL, source name, retrieved date, complete available description, and external job identifier when present.

The [dashboard](dashboard.md) provides a built-in public-feed search with role/location fields, posting-date filters, saved timestamped result lists, and all relevance scores including low matches. Its word/location relevance score is separate from the AI fit assessment below. Review imported search results and source coverage before selecting jobs; do not overwrite saved historical search snapshots when adding an AI evaluation. Preserve source posting dates and distinguish missing dates from retrieval dates.

Prefer official employer career pages, supported job-feed APIs, and authorized connectors. LinkedIn and Indeed are supported as posting sources when retrieval is allowed; accept user-pasted descriptions and links as a fallback. Do not promise complete coverage, an official API you have not verified, or unrestricted scraping. Check current source access terms when implementing or activating a connector. An available third-party scraper is not evidence of platform permission.

Relevant platform references:
- https://www.linkedin.com/help/linkedin/answer/a1340567
- https://www.indeed.com/legal

Deduplicate before ranking. The helper removes common tracking parameters and fragments for URL identity, but different URLs may represent the same role. Compare employer, title, location and requisition number before adding another posting. Preserve the original URL for navigation. Expired/dead postings should be marked `Expired`; never silently replace their text with an unrelated opening.

For each role, assess required skills, experience, location/work arrangement, career relevance and user deal-breakers. Separate mandatory requirements from preferences. Distinguish unknown eligibility from a confirmed mismatch. Record strengths, gaps, unknowns, recommendation and evidence excerpts with `evaluate`. An optional 0–100 score must include its rationale; it is a comparison aid, not a hiring probability. Do not present simple keyword overlap as AI fit.

Return a compact shortlist with source links. Selecting a job for preparation is recorded with `select`; searching/ranking alone does not put jobs into the application queue. Selection can follow the user's explicit batch instructions without asking again.
