# Discovery and fit ranking

Use the user's target role, location/work arrangement, experience level and deal-breakers. Preserve the source URL, source name, retrieved date, complete available description, and external job identifier when present.

## Required primary sources and application type

**Search LinkedIn and Indeed for every primary discovery run.** Follow [primary portal searches](portal-search.md) to create a dated list, record source outcomes, and import verified external-application postings. The user's filter excludes LinkedIn Easy Apply and Indeed Apply / Easily apply / Apply with Indeed. A listing offering on-platform application is excluded even if an external link also exists. Unknown application routes remain excluded until inspected.

Use allowed host browser/retrieval tools, authorized source connectors, or user-provided posting evidence. If a portal needs login, CAPTCHA or unavailable access, mark that source blocked/partial. Do not replace it silently with employer sites or public feeds, and do not claim complete coverage. Do not invent an official API or use cookie extraction, CAPTCHA bypasses or unapproved scraping services. Current tool/platform access rules still apply.

The dashboard defaults to a **LinkedIn + Indeed** request with role, location and posting-date filters. It saves the request and supplies a host-agent prompt; it does not scrape those portals directly. The existing Remotive/Jobicy/Arbeitnow fetcher is an explicitly selected supplementary search, with separate unverified results. It does not fulfill required primary coverage. Never describe a public-feed-only list as a LinkedIn/Indeed search.

Rank every qualifying external posting, including low matches, and retain source posting dates. Source verification and application-route filtering are independent of fit score. A search's automatic word/location score remains separate from the AI fit assessment below. Do not overwrite historical list snapshots when adding AI evaluations.

Deduplicate before ranking. The helper removes common tracking parameters and fragments for URL identity, but different URLs may represent the same role. Compare employer, title, location and requisition number before adding another posting. Preserve the original URL for navigation. Expired/dead postings should be marked `Expired`; never silently replace their text with an unrelated opening.

For each role, assess required skills, experience, location/work arrangement, career relevance and user deal-breakers. Separate mandatory requirements from preferences. Distinguish unknown eligibility from a confirmed mismatch. Record strengths, gaps, unknowns, recommendation and evidence excerpts with `evaluate`. An optional 0–100 score must include its rationale; it is a comparison aid, not a hiring probability. Do not present simple keyword overlap as AI fit.

Return a compact shortlist with source links. Selecting a job for preparation is recorded with `select`; searching/ranking alone does not put jobs into the application queue. Selection can follow the user's explicit batch instructions without asking again.
