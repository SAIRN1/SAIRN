# SAIRNlaw international case-law coverage — final scope

**Recorded 2026-08-23. This corrects the 2026-08-20 commitment list.**

The original commitment named **BAILII (UK/Ireland), CanLII (Canada) and
AustLII (Australia)** as the sources to extend the citator against. That list
was written before any of the four sources had been checked against their own
terms. When they were checked — on 2026-08-21, before any code was written —
**two of the three refused this use outright.**

This file exists because the corrected scope kept being read as a placeholder.
It is not. **The US and UK (England & Wales) via the sanctioned sources is the
finished answer**, and the gaps are permanent unless a source's terms change or
a licence is negotiated.

> **CANADA REMOVED — 2026-08-23, later the same day.** An earlier version of
> this table listed Canada via CanLII's keyed API as covered. It was built and
> it was correct, but `CANLII_API_KEY` was never configured, so the code was
> dormant for its entire life while the in-app coverage panel advertised Canada
> as supported — a false claim on the one screen whose whole job is honest
> disclosure, found by a Guardian pass. Canada is now **out of scope by
> decision**, not blocked pending a key. The client, both API actions
> (`canlii_browse`, `canlii_citator`) and all helpers have been deleted. Do not
> re-add Canada to this table without a new decision, and if it ever comes back,
> rebuild against CanLII's terms as they stand then rather than restoring the
> old code from git history.

## What is covered, and under what permission

| Jurisdiction | Source | Permission |
|---|---|---|
| United States | CourtListener | Existing citator integration |
| UK — England & Wales | **Find Case Law** (The National Archives) | Real public API, no auth. Open Justice Licence expressly permits commercial use and product incorporation |

**One constraint carried into the design rather than noted and ignored:** the
Open Justice Licence permits commercial use but does **not** cover
*"computational analysis"* — bulk programmatic searching to extract or enrich.
So the Find Case Law client is **on-demand lookup only and never sweeps the
corpus.** That is a design constraint, not a limitation to be engineered away.

## What is not covered, and why it is final

| Jurisdiction | Blocked by |
|---|---|
| **Australia** | AustLII's usage policy prohibits *"spidering, scraping, crawling, mirroring, page framing, API access, bulk querying, automated agents"* and blocks automated access for AI-related uses **across its entire collection**. Even its educational-permission carve-out is stated as excluding AI uses. |
| **Scotland, Northern Ireland, Ireland** | BAILII prohibits bulk downloading and scraping in its standard user agreement and restricts crawlers. Its stated concern is AI software built to predict case outcomes — **it names this product category.** Find Case Law covers England & Wales only. |

**Neither is a bot-detection problem.** That distinction is the whole point: a
technical block invites better tooling, a written prohibition does not. Routing
around a stated prohibition with better scraping tooling makes the violation
deliberate rather than incidental, which is worse, not better.

A Bright Data connector was considered and was the wrong tool for this reason,
independent of whether it was available.

## The fact that sharpened it

**CanLII sued an AI legal-research platform — Caseway AI, November 2024 — over
systematic scraping.** Live enforcement against exactly this product category,
and confirmation that CanLII's keyed API is the sanctioned route while scraping
is not. This is not a theoretical terms-of-service concern.

## Why this is not "pending"

The distinction the deadline engine's own gate settled applies here. There are
three kinds of "not covered" and only one of them is work:

- **Not yet verified** — someone needs to read the rule. Real work.
- **Awaiting a capability** — a named, scoped build would close it. Real work.
- **Excluded by the source's own terms** — **no engineering closes it.** Only a
  licence, or a change in the source's terms, would.

Australia and Ireland/Scotland are the third kind. Describing them as "not
covered yet" implies a roadmap item and is the same failure mode the deadline
engine's Phase 8 gate caught: **a permanent limit described in temporary
language.**

## Where this is enforced in the product

- `api/legal-reference.js` — the `coverage` action returns each jurisdiction
  with its own reason, plus a top-level note stating this is final scope.
- `sairnlaw.html` — `refRenderCoverage()` now renders that top-level note.
  **It previously fetched and discarded it**, so a user saw "Not covered" with
  a per-row reason but never the sentence explaining the exclusion is
  permanent. Fixed 2026-08-23 as part of this correction.
- `api/_lib/intl-caselaw.js` — the `COVERAGE` table is the single source; the
  app renders it live rather than restating it.

## If Australia or Ireland is genuinely needed

The real options are a licensing conversation with AustLII or BAILII, or a
different source whose terms permit the use. Not a technical workaround. A
research pass on permitted alternatives is a reasonable thing to scope; adding
the prohibited sources is not.

## Standing blockers on what IS built

One remains. It is not a scope question — it needs access nobody in a coding
session has:

1. `sql/sairnlaw_wex_intl_schema.sql` — Wex definitions and Find Case Law both
   return an honest `NOT_PROVISIONED` until it is run in Supabase. This fails
   closed on purpose: without the ledger the published Wex crawl-delay cannot
   be honoured, so the lookup is refused rather than run unthrottled.
   *(Session 6's handoff records this as since run and both working — re-verify
   live before trusting either statement.)*

2. ~~`CANLII_API_KEY` — not set.~~ **No longer a blocker: Canada is out of
   scope and the code is deleted (see above).** One leftover: that migration
   also created a `public.canlii_rate_limit_log` table, which now has nothing
   writing to it. Dropping it is a destructive change to a shared database and
   is deliberately NOT done here — flagged for whoever owns the Supabase
   schema. The migration file itself is left as written; it is a record of what
   was run, not a live description of scope.
