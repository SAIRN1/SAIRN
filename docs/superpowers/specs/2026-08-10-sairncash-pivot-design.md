# SAIRNcash — Pivot from SAIRNtype: AI Financial Co-Pilot for Freelancers

**Status:** Foundation implemented and live-verified 2026-08-10
(`docs/superpowers/plans/2026-08-10-sairncash-pivot-foundation.md`).
`sairncash.html` live at `sairn.vercel.app/sairncash`. Both audit-found
bugs fixed and confirmed live: `isSubscribed()` uses the real Stripe
`expiresAt` with per-load server re-verification (forged-`localStorage`
bypass tested live, correctly rejected); `handleWaitlist()` persists for
real (honest `NOT_PROVISIONED` confirmed live pending the DB migration).
**Not yet functional end-to-end** — `STRIPE_SECRET_KEY`/`STRIPE_PRICE_ID`
and `SAIRNCASH_FIREBASE_*` are not yet set in this Vercel project
(confirmed live: checkout returns a clean 500 "Stripe not configured",
firebase-config returns `null`, both honest degradations, not crashes);
`sql/sairncash_waitlist_schema.sql` has not been run. Tax/retirement
estimator, Bridge integration, and the trial-notice/no-filing UI
copy from §3 below remain unimplemented, per the foundation plan's
explicit scope cut.

Pivots SAIRNtype (generic AI-chat-response keyboard/wrapper, confirmed
oversaturated per prior market research) into SAIRNcash: a year-round AI
financial co-pilot for freelancers/self-employed users — quarterly tax
set-aside tracking, deduction categorization, SEP IRA/Solo 401(k)
retirement optimization. **Explicitly not a tax-filing product.**

## 0. SAIRNtype's real current state (verified 2026-08-10, not assumed)

**Not in version control.** Zero references anywhere in the `SAIRN1/SAIRN`
git history (`git log --all --grep`, `git log --diff-filter=A` both
empty). The project lives only as ~15 loose folders/zips in
`~/Downloads` (`SAIRNtype_PRO`, `SAIRNtype_PRO (1)`, `SAIRNtype_PWA`,
`SAIRNtype_SUBSCRIPTION`, `SAIRNtype_SYNCED`, `SAIRNtype_iOS`,
`SAIRNtype_Desktop_Cell2`, plus a consolidated single file,
`SAIRNtype_UNIVERSE.html`, dated May 18 — the most recent artifact,
~3 months stale as of today). No single folder contains a complete,
deployable app — the front end (`SAIRNtype_UNIVERSE.html`) and the only
folder with all 5 referenced API routes (`SAIRNtype_PRO (1)/
sairntype_stripe/api/{checkout,verify,claude,costs,firebase-config}.js`)
were never assembled together.

**Not live anywhere, despite the pitch materials' explicit claims.**
`SAIRNtype_Attorney_Pitch.md`/`_Investor_Business_Plan.md` both say
"live, operational... subscriptions active... Open sairn.vercel.app
right now" and cite "74 quality checks... all 74 passed." Verified
live: `sairn.vercel.app` (root, no path) serves **StoneDesk**, not
SAIRNtype (confirmed by response `<title>` and content — a single
stray "SAIRNtype" text match, not the app). `sairntype.com` is a
**parked-domain placeholder page** (4KB generic template), not a
deployment. The claims in both pitch documents do not match verified
reality.

**The code that does exist is mostly real, not pure vaporware** —
important nuance, this isn't a total fabrication:
- `SAIRNtype_UNIVERSE.html`'s 4 mechanical scanners (`sairn-portfolio-
  triage`'s duplicate-global, missing-DOM-target, panel-nesting,
  key-collision) all pass clean; `checkblocks.py` syntax-clean (2/2
  blocks).
- Stripe checkout (`api/checkout.js`) and verify (`api/verify.js`) in
  `SAIRNtype_PRO (1)/sairntype_stripe/api/` are genuine, correct
  Stripe Checkout Session + session-retrieve integrations — real
  `mode:'subscription'`, real env-var config, no stub/fake logic.
- The chat panel wires to a real `/api/claude` proxy, with real
  `localStorage`-backed usage tracking, style-memory, and a clips
  library — not fabricated UI-only theater.

**Two real silent-failure/fabrication bugs found** (`sairn-silent-
failure-sweep` class):
1. **`handleWaitlist()` (`SAIRNtype_UNIVERSE.html:1107`) is fake.** It
   shows "✓ You're in!" success feedback and clears the input — but
   never sends the email anywhere (no fetch, no storage). The email is
   silently discarded while the UI claims success. Exact pattern this
   platform's Guardian sweeps have caught repeatedly elsewhere.
2. **`isSubscribed()` (`SAIRNtype_UNIVERSE.html:1131`) ignores the real
   subscription expiry and is trivially bypassable.** `/api/verify`
   already computes a real `expiresAt` from Stripe's
   `current_period_end` and returns it — but the client never uses it.
   Instead it checks `Date.now() - s.at > 35 days` against its own
   locally-recorded timestamp, with **no server-side re-verification
   on any subsequent load**. Any user can set
   `localStorage.sairn_sub = {valid:true, at:Date.now()}` in devtools
   for permanent free Pro access, and a real cancellation wouldn't be
   detected until the arbitrary 35-day local window happens to expire.

**No trial-then-charge flow exists in the code at all today** — it's
direct freemium (permanent free tier vs. one-click Stripe Checkout to
$9.99/mo). This means the "silent auto-renewal" competitor complaint
pattern doesn't apply to a bug in the existing code — there's no trial
to silently renew. It's a clean slate for §3.2 below, not a fix.

## 1. What SAIRNcash keeps, repurposes, and drops

**Reused as-is (once §4's fixes land):** Stripe checkout/verify
integration, the `/api/claude` chat-dispatch pattern, the account/
sign-out flow (`showAccount()`'s "Manage at stripe.com" — a real
mechanism, needs a UI upgrade per §3.2).

**Repurposed:** the "calculator panel" concept becomes the tax/
retirement estimator (quarterly set-aside amount, SEP IRA/Solo 401(k)
contribution optimization); the "memory panel"/style-memory concept
becomes ongoing income/deduction tracking (the same `localStorage`-
then-sync pattern every other SAIRN app on this platform already uses,
via the Bridge — see below).

**Dropped entirely:** Ghost Complete, Tone Shift, Smart Reply, File
Manager, Voice Mode, Compose Mode, and the whole "AI keyboard"
framing/native iOS-Android-Desktop keyboard-extension work
(`SAIRNtype_iOS`, `SAIRNtype_Desktop_Cell2`) — none of it serves the
financial co-pilot use case, and none of it is what's oversaturated-
category-differentiated per the market research that motivated this
pivot.

**New — the real differentiator:** for existing SAIRN B2B customers
(StoneDesk, SAIRNbuild, SAIRNbiz, etc.), income/expense data can pull
directly from their existing SAIRN business app via the Bridge, zero
extra setup. No competitor in this category (Keeper, QuickBooks
Self-Employed, FlyFin) can do this — they all require manual entry or
a third-party bank-account connection (Plaid) as the *only* path in.
An existing SAIRN customer's real transaction data is already sitting
in their business app; SAIRNcash reading it directly is a structural
advantage, not a feature to build from scratch per customer.

## 2. Explicit non-goals

- No tax filing, no e-filing integration, no state-specific filing
  logic of any kind (see §3.1 — this is the product's core positioning,
  not an omission).
- No write access to the source SAIRN B2B app's data via the Bridge —
  read-only.
- No bank-account-direct (Plaid) integration in v1 — the Bridge pull
  from an existing SAIRN app is the v1 differentiator; a generic Plaid
  path for non-SAIRN-customer freelancers is later, separate scope.

## 3. The two requirements folded in for this pivot

### 3.1 — Explicit "does not file taxes" positioning, by design

States directly, in the product's own copy — not just a ToS clause —
that SAIRNcash does not file taxes. This is a deliberate category
positioning, not a limitation being disclosed reluctantly: it
structurally avoids the single most common complaint pattern in this
category (multi-state filing errors — the recurring, damaging
complaint against Keeper specifically).

- **Landing/marketing copy:** a direct line near the top of the page,
  same register as the pricing/feature copy — e.g. "SAIRNcash tracks,
  categorizes, and estimates what you owe. It does not file your taxes
  — hand off to your accountant or filing software (TurboTax, a CPA,
  H&R Block) when it's time to file." Not buried in a footer or FAQ.
- **In-app, persistent:** a one-line disclaimer anchored near the tax
  estimator panel itself (not just shown once at onboarding).
- **In the AI system prompt for any tax-related response:** an explicit
  instruction that the assistant must never draft, estimate, or imply
  it is filing anything, and must actively redirect ("export this and
  bring it to your accountant/filing software") rather than let a user
  believe SAIRNcash is finishing the job — same anti-scope-creep
  discipline already used in this session's other AI system prompts
  (e.g. SAIRNlegacy's `sendAI()`: "never provide your own estimate...
  say so plainly and stop").
- Applies to the estimator's own output too: every tax/retirement
  number it shows should be labeled an **estimate**, not a filing-ready
  figure, with the same "this is a draft, review before use" framing
  already proven on SAIRNlegacy's obituary generator.

### 3.2 — Honest, explicit trial-ending notice, no silent auto-renewal

Directly counters the closest competitor's most damaging complaint
pattern (silent auto-renewal, surprise charges). Real requirements,
given §0's finding that no trial mechanism exists in the reused code
today:

- **Before Stripe Checkout begins:** show the exact trial length,
  exact charge date, and exact charge amount in SAIRNcash's own UI —
  not left to Stripe's generic checkout copy alone. E.g.: "14 days
  free. On [real computed date], you'll be charged $X.XX/mo unless you
  cancel before then."
- **A real pre-charge notice, not just a promise of one.** Requires
  actual infrastructure that doesn't exist in the reused code: either
  a scheduled job checking trial-end dates and sending a real email
  (needs an email-send capability — not present anywhere in the
  current SAIRNtype stack) or, at minimum, an in-app banner that
  appears starting N days before the real charge date, computed from
  the real Stripe subscription's trial-end timestamp (not a guessed
  local value — same lesson as §4.1 below: use the real
  server-provided date, never a client-side approximation).
- **Cancellation must be as easy as subscribing, and directly
  reachable** — replace the current `showAccount()`'s plain-text
  `alert()` pointing users to "stripe.com" with a real Stripe Billing
  Portal session link (`stripe.billingPortal.sessions.create`, a
  standard Stripe API call not yet present in this codebase),
  surfaced as a direct in-app button.
- **No dark patterns:** no pre-selected annual-plan default, no
  "forgot to cancel" framing, no charge that happens without the exact
  amount and date having been shown to the user first, in SAIRNcash's
  own copy, before checkout.

## 4. Concrete engineering fixes required before any reuse

1. `isSubscribed()` must be rewritten to use the real `expiresAt` from
   `/api/verify` (already computed server-side from Stripe's
   `current_period_end`) instead of the arbitrary client-only 35-day
   timer, and must re-verify against a real subscription-status source
   periodically rather than trusting one `localStorage` flag
   indefinitely. Given SAIRNcash handles financial planning data —
   more sensitive than a generic chat log — shipping with a
   trivially-forgeable free-access bypass is not acceptable, where it
   might have been a lower-stakes gap for the original AI-keyboard
   product.
2. `handleWaitlist()` (if reused for a SAIRNcash pre-launch waitlist)
   must actually persist the email somewhere real before shipping —
   currently discards input while showing a fabricated success state.
3. The scattered SAIRNtype source (§0) needs to be unified into one
   deployable project and brought into version control as the actual
   first implementation task — not attempted as part of this design
   pass, but a hard prerequisite before any pivot code is written on
   top of it. Building on top of files nobody can diff or roll back is
   the same risk class already found and corrected elsewhere on this
   platform (untracked local variants proliferating instead of one
   real source of truth).

## 5. Testing / verification (once an implementation plan exists)

- Real interaction test of the trial → charge flow against Stripe's
  test mode: confirm the in-app pre-charge notice shows the real
  computed date/amount, confirm no charge occurs before that date,
  confirm the Billing Portal cancel path actually cancels the
  subscription (verified via Stripe, not assumed from a UI state).
- `isSubscribed()` fix verified the same way §4's audit found the bug:
  attempt the same `localStorage` forgery and confirm it no longer
  grants access without a real, current server-verified subscription.
- Tax/retirement estimator output spot-checked against a real,
  hand-computed example (same discipline as this platform's
  fabricated-KPI checks — a number with no real computation behind it
  is not acceptable).
- Bridge read-path tested against a real SAIRN B2B app's real seeded
  data, confirming read-only (no write capability reachable from
  SAIRNcash's side).

## 6. Open questions for the next pass (not resolved by this spec)

- Which SAIRN B2B apps' data shapes actually map cleanly to
  "income"/"expense" for the Bridge pull, and whether that mapping is
  1:1 per app or needs a per-app translation layer (same class of
  decision as SAIRNbiz's `sb_exps`→`sb_bud` mapping gap logged
  elsewhere in `SAIRN-BACKLOG.md`).
- Real competitive pricing research for this specific category
  (Keeper, FlyFin, QuickBooks Self-Employed current pricing) — not
  done as part of this pass, required before finalizing SAIRNcash's
  own price point per this platform's standing market-readiness gate.
- Whether the existing Stripe product/price (`$9.99/mo`, SAIRNtype
  Pro) is reused or a new price point is created for SAIRNcash — not
  decided here.
