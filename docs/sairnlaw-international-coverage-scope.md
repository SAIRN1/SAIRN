# SAIRNlaw international case-law coverage — final scope

**Recorded 2026-08-23. This corrects the 2026-08-20 commitment list.**

The original commitment named **BAILII (UK/Ireland), CanLII (Canada) and
AustLII (Australia)** as the sources to extend the citator against. That list
was written before any of the four sources had been checked against their own
terms. When they were checked — on 2026-08-21, before any code was written —
**two of the three refused this use outright.**

This file exists because the corrected scope kept being read as a placeholder.
It is not. **UK (England & Wales), Canada and the US via the sanctioned sources
is the finished answer**, and the two gaps are permanent unless a source's
terms change or a licence is negotiated.

## What is covered, and under what permission

| Jurisdiction | Source | Permission |
|---|---|---|
| United States | CourtListener | Existing citator integration |
| UK — England & Wales | **Find Case Law** (The National Archives) | Real public API, no auth. Open Justice Licence expressly permits commercial use and product incorporation |
| Canada | **CanLII official keyed API** | The sanctioned route. Requires `CANLII_API_KEY` |

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

Neither is a scope question — both need access nobody in a coding session has:

1. `sql/sairnlaw_wex_intl_schema.sql` — **unrun.** Wex definitions and Find
   Case Law both return an honest `NOT_PROVISIONED` until it is run in
   Supabase. This fails closed on purpose: without the ledger the published
   Wex crawl-delay cannot be honoured, so the lookup is refused rather than
   run unthrottled.
2. `CANLII_API_KEY` — **not set.** Free key from CanLII. Canada reports
   unavailable honestly rather than silently empty until then.
