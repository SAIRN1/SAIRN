# SAIRNcash — Quarterly Tax Set-Aside + SEP IRA/Solo 401(k) Estimator

**Status:** Design drafted 2026-08-10, pending review. Not yet implemented.

The core value feature the pivot spec (`docs/superpowers/specs/2026-08-10-
sairncash-pivot-design.md`) described as "repurposing the calculator
panel." Confirmed decisions (asked directly, not assumed — all four
recommended options accepted): federal-only (state tax explicitly
disclosed as not included), real IRS safe-harbor basis (100%/110% of
prior-year tax), self-employment income only in v1 (no W-2 hybrid), all
4 standard filing statuses.

## 0. Prerequisite found during this design pass: Firebase sync isn't
   actually per-subscriber today

`sairncash.html:309` (`const msgsRef = ref(db, 'sairncash/messages');`)
uses one flat, global Firebase path for every subscriber's chat —
inherited from SAIRNtype, not caught during the foundation audit
because that pass verified the two specifically-flagged bugs
(`handleWaitlist`, `isSubscribed`), not every piece of ported code
independently. Harmless-ish for a generic chat log where the worst
case is another subscriber's small-talk bleeding through; **not
acceptable once real income, deduction, and tax-profile records ride
the same mechanism** — that would be one subscriber's real financial
data visible to every other subscriber's browser.

**Fix (Task 0 below, blocks everything else in this spec):** scope
every Firebase path by a stable per-subscriber identifier. The Stripe
`customerId` (not `subscriptionId` — survives a plan change or
resubscribe, `subscriptionId` doesn't) is already retrievable from
`api/sairncash/verify.js`'s Stripe response and not yet stored
client-side. Add it to `saveSub()`'s payload, then every Firebase ref
becomes `sairncash/customers/{customerId}/messages`,
`.../income`, `.../deductions`, `.../profile`, instead of the current
bare `sairncash/messages`.

## 1. Deterministic math — the actual formulas, none of it AI-guessed

All of the below is real arithmetic against IRS-published constants,
computed the same way every time for the same inputs, never phrased as
an AI estimate. Constants below are the real, verified tax year 2026
figures (web-searched during this design pass, sourced below — not
carried forward from stale training-data figures) and must be
re-verified against the current year's actual IRS Revenue Procedure
before this ships for a new tax year — hardcoded with a loud
`TAX_YEAR` constant and an in-UI "2026 rates" label so drift is visible
rather than silent (same discipline as every other dated/versioned
constant on this platform).

**Self-employment tax:**
- Net SE earnings = net profit (income − deductions) × 0.9235
- Social Security portion: 12.4% of the lesser of (net SE earnings) or
  the 2026 SS wage base, **$184,500** (up from $176,100 in 2025 —
  confirmed live, this figure moves every year, must not be hardcoded
  without a re-check)
- Medicare portion: 2.9% of ALL net SE earnings, no cap
- Additional Medicare: extra 0.9% on net SE earnings above the filing-
  status threshold — **$200,000 single/HoH, $250,000 MFJ, $125,000
  MFS** (these three are fixed by statute, not inflation-indexed —
  unlike the SS wage base and standard deduction, don't expect them to
  change year over year)
- Total SE tax = SS + Medicare + Additional Medicare
- Half of total SE tax is an above-the-line deduction for the federal
  income tax calculation below

**Federal income tax (all 4 filing statuses):**
- Taxable income = net SE earnings − (½ × SE tax) − standard deduction
  (per filing status) − any retirement contribution amount entered
- 2026 standard deduction (confirmed): **$16,100** single/MFS,
  **$24,150** HoH, **$32,200** MFJ
- Apply the real 2026 progressive bracket table (10/12/22/24/32/35/37%)
  for the selected filing status — a data table, not a formula, four
  separate tables. Only the top-bracket thresholds were confirmed
  during this design pass (single: 37% above $640,600; MFJ: 37% above
  $768,700) — **the full 7-bracket table for all 4 statuses must be
  transcribed exactly from IRS Rev. Proc. 2025-32 during
  implementation**, not approximated or reconstructed from partial
  search results.

**Quarterly safe-harbor set-aside (the real rule, not a simplification):**
- Required annual payment = the LESSER of:
  (a) 90% of this year's estimated total tax (SE tax + income tax,
      computed from income/deductions entered so far, annualized), or
  (b) 100% of last year's total tax liability (110% if last year's AGI
      was over $150k) — **requires one onboarding input: prior-year
      total tax liability**, per your confirmed answer
- Quarterly amount = required annual payment ÷ 4, adjusted for
  payments already made this year
- If insufficient data exists yet (e.g. first quarter, no prior-year
  figure entered) — say so plainly and show the best available partial
  estimate labeled as such, never silently substitute a guessed number

**SEP IRA / Solo 401(k) contribution estimate:**
- Self-employed effective contribution rate is NOT a flat 25% —
  circular math (25% of compensation, where compensation is itself
  reduced by the contribution) reduces to an effective ~20% of net SE
  earnings after the ½ SE-tax deduction. Present as: "approximately 20%
  of net SE earnings after the SE-tax deduction" with an explicit note
  this is a simplified estimate, not the exact IRS Publication 560
  worksheet, and to verify the exact figure with a tax professional or
  real plan administrator before contributing.
- SEP IRA cap (2026, confirmed): **$72,000** (up from $70,000 in 2025).
- Solo 401(k) (2026, confirmed): employee deferral **$24,500** (up from
  $23,500) + employer contribution (same ~20% estimate as SEP) —
  combined capped at **$72,000** for under-50. Catch-up contributions
  (age 50-59/64+: **$8,000**; SECURE 2.0 enhanced catch-up age 60-63:
  **$11,250**) are real but out of scope for this pass — v1 supports
  under-50 contributors only, age-based catch-up deferred.

## 2. Quarterly deadline tracking — fixed calendar, not computed

Standard IRS due dates: Apr 15 (Q1), Jun 15 (Q2), Sep 15 (Q3), Jan 15
next year (Q4) — a real date table for tax year 2026 specifically
(exact dates shift some years for weekends/holidays; do not assume the
15th always applies without checking the actual current-year IRS
calendar). UI shows a real "N days until Q_ payment due," computed from
`new Date()` against the real table entry, same honest-timestamp
discipline as `checkTrialGate()` elsewhere on this platform — never a
fabricated countdown.

## 3. Data model (Firebase, scoped per §0's fix)

- `sairncash/customers/{customerId}/profile` — `{filing_status,
  prior_year_tax_liability, tax_year, retirement_vehicle: 'sep'|
  'solo401k'|'none'}`. Entered once at onboarding, editable.
- `sairncash/customers/{customerId}/income` — list of `{id, amount,
  date, description, created_at}`.
- `sairncash/customers/{customerId}/deductions` — list of `{id,
  amount, date, category, description, created_at}`. `category` is
  AI-suggested (§4) but always user-editable before saving — the
  suggestion is never silently authoritative.
- `sairncash/customers/{customerId}/messages` — existing chat sync,
  re-scoped under §0's fix, not a new resource.

## 4. AI's role — constrained, explicitly

- **Explain a number Claude did not compute.** E.g. "why is my Q3
  set-aside $X" — the assistant is given the already-computed figure
  and formula inputs as context, and explains them in plain language.
  It must never independently recompute or restate a different number.
- **Suggest a deduction category from a free-text description** (e.g.
  "bought a laptop for client work" → suggested category "Equipment").
  A genuinely fuzzy, AI-appropriate task — but the suggestion only
  pre-fills an editable field; the user's own entered amount is used
  verbatim regardless, and the category is never silently accepted
  without the user seeing and being able to change it.
- **General questions** ("what counts as a deduction for a
  photographer") — general knowledge, not a substitute for the user's
  own actual figures.
- **Hard rule, same class as every other AI system prompt on this
  platform this session:** never provide an estimate as a substitute
  for a real number the deterministic engine would compute from actual
  entered data — if the data needed isn't there yet, say so and ask
  for it, don't guess.

## 5. Non-goals (this pass)

- No state tax (§ confirmed decision).
- No W-2 income interaction with SE tax (§ confirmed decision) —
  deferred to v2.
- No actual IRS e-filing or Form 1040-ES generation — SAIRNcash
  produces the estimate; the user (or their accountant/filing
  software) takes it from there, per the pivot spec's core positioning.
- No automatic bank/Plaid income import in this pass — manual entry
  only, matching the pivot spec's stated v1 scope (Bridge-based pull
  from existing SAIRN B2B apps is separate, later work).

## 6. Testing

- Pure math: hand-computed test cases against real IRS worksheets for
  each of the 4 filing statuses, at least one case per SE-tax bracket
  boundary (below/above the SS wage base, below/above the Additional
  Medicare threshold).
- Firebase scoping fix (§0): confirm two different `customerId`s never
  see each other's income/deduction/profile data — the actual
  regression test for the bug this spec found.
- AI category-suggestion: confirm the suggestion never overwrites a
  user-entered amount, and confirm the system prompt's anti-estimation
  rule holds when asked a question requiring data not yet entered.
- Standard structural checks (`checkblocks.py`, `div_balance_check.py`,
  `duplicate_global_check.py`) after every change; live-verify after
  push, per this platform's standing Push Protocol.
