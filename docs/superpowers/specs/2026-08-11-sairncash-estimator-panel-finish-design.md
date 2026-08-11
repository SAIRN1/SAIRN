# SAIRNcash — Estimator Panel Finish (Task 3 completion) Design

**Status:** Implemented, reviewed, and live 2026-08-11. Commits
`aa75c03`..`73a190f`. Two real plan-mandated bugs caught during task
review and fixed: `saveProfile()` was passing `undefined` (not `null`)
into a real Firebase `set()` call for an absent optional field, which
the SDK rejects; `renderEstimator()`'s currency writes were missing the
file's own `(Number(x)||0)` guard. Both fixed and re-reviewed clean.
Local checks, structural checks, and a timezone-safe re-run of the
quarterly-deadline date logic all pass. Live byte-verified (after
accounting for a harmless local-CRLF-vs-deployed-LF difference — content
MD5-identical). **Not yet live-tested end-to-end**: the plan's Task 4
Steps 3-7 (real Stripe-subscribed account regression — profile
save/sync, live recompute, two-device isolation) are blocked on Stripe
not being configured in this Vercel project at all yet (confirmed live:
`api/sairncash/checkout.js` returns `"Stripe not configured"`) —
expected, per the user, Stripe setup is planned for next week, not this
session. See `SAIRN-PLATFORM-SESSION3-HANDOFF.md` for full detail.

Completes Task 3 of the already-approved
`docs/superpowers/specs/2026-08-10-sairncash-tax-retirement-estimator-design.md`
and its implementation plan
(`docs/superpowers/plans/2026-08-10-sairncash-tax-retirement-estimator.md`).
That spec is treated as still valid and is not re-litigated here — Tasks
0 (Firebase per-customer scoping), 1 (the deterministic tax-math engine:
`TAX_YEAR_2026`, `calcSeTax`, `calcAdditionalMedicare`, `bracketTax`,
`calcTotalTax`, `calcQuarterlySetAside`, `calcRetirementEstimate`), 2
(income/deduction entry + AI category suggestion), and 4 (the
constrained "explain, never recompute" AI system prompt) are all
confirmed already implemented and live in production — checked directly
against both the committed source and the deployed app, not assumed
from commit messages. Only Task 3 (the estimator panel UI) was left
incomplete when this was last touched; an uncommitted diff on disk is a
correct, partial start on it (the profile input form and results-display
skeleton), sitting unfinished across several sessions.

**Confirmed, not assumed, before writing this:** no existing tax-bracket
or personal-income-tax logic exists anywhere else on the platform to
reuse — `sairnbiz.html` has payroll-tax code, but it computes a flat-rate
W-2 employer-withholding estimate (22%/3.99%, explicitly caveated as an
approximation in its own code comment), not the real progressive
personal-bracket math this feature needs. No reuse applies; SAIRNcash's
own `bracketTax()` (already committed) is the only real implementation
of this on the platform.

## 0. Design questions, resolved

**Keep the existing approved spec as-is — this is a finish-line pass,
not a redesign.** Every decision in the 2026-08-10 spec (federal-only
scope, real IRS safe-harbor basis, self-employment-only v1, all 4 filing
statuses, the SEP/Solo 401(k) ~20% effective-rate approximation, AI's
constrained explain-only role) is already implemented and live — checked
directly, not assumed. Re-opening any of it here would re-litigate
settled, working code for no reason connected to what's actually
missing.

**Profile persistence — mirrors the existing income/deduction Firebase
pattern exactly, confirmed by reading the real code, not invented.**
`initFirebase()` (`sairncash.html:395-443`) already exposes
`window._fbProfileRef` (line 438) specifically for this — set up in an
earlier session, never consumed. `initFinanceSync()`
(`sairncash.html:724-736`) already establishes the real-time-listener
pattern this profile sync mirrors: `window._fbOnValueRaw(ref, snap =>
{...})`. Firebase's `set` (`window._fbSetRaw`, already used for presence
writes) is the correct primitive for `saveProfile()` — a profile is one
object at a fixed path, not a list of pushed entries the way income and
deductions are (that distinction is already real in this file, not
new).

**Recompute trigger — live, via the same reactive listeners already
proven in this file, not a new polling/manual mechanism.** Firebase's
`onValue` listeners are inherently live; income/deduction changes
already trigger `renderFinancePanel()` this way today. The estimator
gets the identical treatment: a new `renderEstimator()` call added
alongside every existing `renderFinancePanel()` call site, plus a new
listener on `window._fbProfileRef`, plus a call on switching to the
estimator view. No new polling, no manual refresh control — this file
already has the mechanism this feature needs.

**Quarterly deadlines — verified live against IRS.gov for tax year 2026
specifically, not carried forward from the parent spec's own citation.**
Confirmed: Apr 15, 2026 (Q1), Jun 15, 2026 (Q2), Sep 15, 2026 (Q3), Jan
15, 2027 (Q4) — each checked individually against weekend/holiday
shifts, none apply this year. The parent spec's own testing section
flagged this exact re-check as required before implementation, per IRS
Pub. 509's year-to-year variability; done here, not skipped.

**Partial-estimate disclosure — shown in two places, both already
present as empty scaffolding in the uncommitted HTML.** The parent
spec's hard requirement ("an honest... note when [`hasFullBasis`] is
false, never silently presented as final") is served by: (1) the
existing `#profileMissingNote` element near the prior-year-tax input
itself, and (2) `#resQuarterlyLabel`'s text swapping to disclose
partial-estimate status directly next to the dollar figure it
qualifies — not relying on the user having scrolled past the input
section to see the caveat that governs the number they're looking at.
Both elements already exist in the uncommitted markup; this makes their
intended dual role explicit rather than leaving one of them unused.

## 1. Architecture

- **`profileCache`** — new module-level object (parallel to
  `incomeCache`/`deductionCache`), holds the currently-synced profile:
  `{filing_status, prior_year_tax_liability, prior_year_agi_over_150k,
  retirement_vehicle}`.
- **`initProfileSync()`** — new function, called from the same place
  `initFinanceSync()` is called (once a real subscription is confirmed).
  Subscribes via `window._fbOnValueRaw(window._fbProfileRef, snap => {
  profileCache = snap.val() || {}; populateProfileForm(); renderEstimator();
  })`.
- **`populateProfileForm()`** — new function, sets the 4 form fields
  (`profFilingStatus`, `profPriorYearTax`, `profAgiOver150k`,
  `profRetirementVehicle`) from `profileCache`, called after every
  profile sync so a second device's saved profile shows up here too.
- **`saveProfile()`** — new function, reads the 4 form fields, calls
  `window._fbSetRaw(window._fbProfileRef, {filing_status, prior_year_tax_liability,
  prior_year_agi_over_150k, retirement_vehicle})`. The listener above
  picks up the change and re-populates/re-renders — `saveProfile()`
  itself does not need to touch `profileCache` or call the render
  functions directly, the same one-way-data-flow pattern
  `addIncomeEntry()`/`addDeductionEntry()` already use (they write, the
  listener re-renders).
- **`QUARTERLY_DEADLINES_2026`** — new small constant, the 4 verified
  dates from §0, each with its quarter label. Re-verify for any other
  tax year before reuse, same discipline as `TAX_YEAR_2026`.
- **`renderEstimator()`** — new function. Reads `profileCache` +
  `ytdNetProfit()` (already exists), calls `calcQuarterlySetAside()` and
  `calcRetirementEstimate()` (already exist, unchanged), and populates:
  - `resYtdNet` — `ytdNetProfit()`, formatted as currency.
  - `resEstAnnual` — `calcQuarterlySetAside()`'s `estAnnual`.
  - `resQuarterly` — `calcQuarterlySetAside()`'s `quarterlyAmount`.
  - `resQuarterlyLabel` — "Recommended quarterly set-aside" if
    `hasFullBasis`, else a partial-estimate disclosure (exact copy in
    §4).
  - `resDeadline` — the next unpassed date in `QUARTERLY_DEADLINES_2026`
    compared against `new Date()`, formatted as "Mon D, YYYY (N days)".
  - `resRetirement` — `calcRetirementEstimate()`'s `estimate`, using
    `profileCache.retirement_vehicle`.
  - `profileMissingNote`'s `display` toggled based on `hasFullBasis`.
  Called from: both existing Firebase listener callbacks in
  `initFinanceSync()` (alongside their existing `renderFinancePanel()`
  call), the new profile listener, and `switchView('estimator')`.

## 2. Data model

No new Firebase paths — `sairncash/customers/{customerId}/profile`
already exists as a target (`window._fbProfileRef`, set up in Task 0),
simply unused until now. Shape: `{filing_status: 'single'|'mfj'|'mfs'|
'hoh', prior_year_tax_liability: number|undefined,
prior_year_agi_over_150k: boolean, retirement_vehicle: 'sep'|'solo401k'|
'none'}`. `prior_year_tax_liability` genuinely optional — its absence is
exactly what drives `hasFullBasis: false` in `calcQuarterlySetAside()`,
already handled correctly by that existing function.

## 3. Error handling

- **`saveProfile()` called before Firebase is ready** (matches
  `addIncomeEntry()`'s existing guard exactly): if `window._fbProfileRef`
  or `window._fbSetRaw` isn't set yet, show `showToast('Sync not ready
  yet -- try again in a moment')` and return without attempting the
  write — never a silent no-op.
- **`renderEstimator()` called before any profile has ever been
  saved:** `profileCache` is `{}` (Firebase's `snap.val()` returns
  `null`/`undefined` for a path with no data, guarded to `{}`).
  `calcQuarterlySetAside()`/`calcRetirementEstimate()` already handle
  missing/undefined inputs safely (verified by reading their existing
  code: `priorYearTaxLiability` falsy → `hasFullBasis: false`,
  `retirement_vehicle` undefined → falls through to the `{estimate: 0,
  cap: 0}` branch) — no new guard needed in `renderEstimator()` itself
  beyond what these functions already do.
- **`renderEstimator()` called with zero income entries yet:**
  `ytdNetProfit()` already returns `0` cleanly (empty-array `.reduce()`
  with an initial value) — the estimate correctly shows `$0.00`
  everywhere rather than throwing, no new handling needed.

## 4. Exact label/disclosure text

- `resQuarterlyLabel`, when `hasFullBasis` is `true`: "Recommended
  quarterly set-aside" (already the HTML's static default text — no
  change needed for this case).
- `resQuarterlyLabel`, when `hasFullBasis` is `false`: "Partial estimate
  (90% of this year only) -- add prior-year tax above for the full
  figure".
- `profileMissingNote` (already exists verbatim in the uncommitted
  HTML, unchanged): "No prior-year tax figure entered yet -- the
  set-aside below is a partial estimate (90% of this year's projected
  tax only), not the full IRS safe-harbor calculation. Add it above for
  a more accurate number."

## 5. Non-goals (explicit scope cuts, this pass)

- No changes to Tasks 0/1/2/4's already-implemented, already-live code
  — this pass only adds the missing UI-wiring layer on top.
- No new Firebase paths, no new sync mechanism — reuses
  `window._fbProfileRef` and the existing listener pattern exactly.
- No manual "Refresh"/"Calculate" control — live recompute via existing
  listeners only (§0).
- No age-based catch-up contribution logic (already deferred in the
  parent spec, unchanged here).
- No re-verification of `TAX_YEAR_2026`'s bracket/threshold constants —
  those were already verified 2026-08-10 against real sources per the
  code's own citation comment; this pass only adds the quarterly-date
  table, verified fresh in §0.

## 6. Testing

- `renderEstimator()`'s date-selection logic: hand-computed cases — a
  date just before each of the 4 deadlines selects that deadline as
  "next," a date just after the last deadline of a lookback year would
  need next year's Q1 (out of scope to build a rollover table this pass
  since `QUARTERLY_DEADLINES_2026` is tax-year-2026-specific by design,
  but confirm the function fails safely — e.g. shows the last known
  deadline or an honest "N/A" — rather than throwing, if ever called
  after Jan 15, 2027).
- `saveProfile()` → listener → `populateProfileForm()` round-trip:
  confirm a saved profile reappears correctly formatted in the form
  after a simulated re-sync (matches the parent spec's own two-device
  isolation test methodology, applied to profile specifically).
- `hasFullBasis` disclosure: confirm both `profileMissingNote` and
  `resQuarterlyLabel` correctly show/hide and swap text together, never
  independently out of sync with each other.
- Full live regression: enter a real filing status + prior-year tax
  liability + retirement vehicle, confirm `resQuarterly`/`resRetirement`
  match a hand-computed cross-check using the already-verified
  `calcQuarterlySetAside()`/`calcRetirementEstimate()` functions (these
  functions themselves were already tested per the parent plan's Task 1
  — this test is specifically for the new UI-wiring layer, not a
  re-test of the math).
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`,
  `duplicate_global_check.py`) after every change; Push Protocol
  before/after push, per this platform's standing discipline.
