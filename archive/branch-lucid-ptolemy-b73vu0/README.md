# Archive — `claude/lucid-ptolemy-b73vu0`

**Archived 2026-08-28. The branch was deleted after this landed.**

167 files that existed only on that branch and never on `main`. Everything here
is dead code by definition — nothing on `main` imports, routes to, or depends on
any of it. It is kept because the platform has repeatedly gone looking for
things that turned out to be in here.

## Why this exists rather than a branch deletion

Three findings during triage made deletion irreversible in a way that mattered:

**1. `db/schema_license_keys.sql` — the table the platform documents as
nonexistent.** `sairn-grant-sweep` and `sql/demo_license_keys_seed.sql` both
state *"this repo has no tracked CREATE TABLE for license_keys."* It is here,
and it carries `key TEXT UNIQUE NOT NULL` — which answers the question that
forced every licence seed on this platform to use `WHERE NOT EXISTS` instead of
`ON CONFLICT`, because the constraint could not be confirmed from source.

**2. The licence-key generation system, described in `api/_lib/license.js`'s own
header as "not-yet-built", was built.** `api/webhooks/stripe.js` verifies the
Stripe signature, generates and stores keys on `checkout.session.completed`, and
cancels them on `customer.subscription.deleted`, with a real `storeLicenseKey()`
writing to `license_keys`. `api/stripe-checkout.js` is its front half.

**3. `skills/sairn-code-guardian/` — 1,230 lines.** `CLAUDE.md` states it *"was
deleted outright, not stubbed… Do not go looking for it, and do not recreate
it."* That is true of the skill stores and was not true of the repo. This is
Guardian v2's ancestor, and it is where the duplicate-global-identifier check
(now Check 13) came from, *"added after the June 2026 StoneDesk outage."*

**None of these corrections cost anything to keep. All of them cost something to
lose.**

## What is in here

| group | count | verdict |
|---|---|---|
| `*UPLOAD_TO_GITHUB*.html` | 27 | versioned dumps, disposable |
| `.github/scripts/.github/scripts/…` | 32 | path-duplication accident, disposable |
| `fabricor*.html` | 5 | the abandoned duplicate `CLAUDE.md` already names |
| `*-ad-N-*.html` | 6 | marketing mockups |
| binaries (`.zip` ×3, `.bat` ×2) | 5 | disposable |
| `skills/` | 11 | **none exist in the canonical store today** |
| `db/` schemas | 7 | 5 have no equivalent in `sql/` on main |
| `api/` endpoints | 9 | incl. the Stripe/licence-key system above |
| root `.html` | 43 | see below |
| SDK / connectors / misc | 22 | `sairn-sdk.js`, `sairn-db-sdk.js`, `sairnbiz-connector.js`, `schema.sql`, `schema_b2b.sql` |

### The apps, all four reviewed in depth before archiving

- **`sairnmechanical.html` — RECOVERED.** Now live on `main` at
  `/sairnmechanical`, with real auth built first. The copy here is the
  pre-recovery June state and is superseded.
- **`sairntrade.html` — blueprint only.** 35 panels, 45 AI touchpoints, and a
  **hard parse error**: a stray `}` means the single script block has never
  executed in a browser. Its own v2.0 commit says *"full audit passed"*, which
  did not include a syntax check. Read it as someone's plan, not proof.
- **`sairnvetglobal.html` — parked, market decision.** 26 panels, syntax clean,
  **zero fabricated data**, 66 localStorage refs, computes from real records.
  Not superseded by SAIRNvet: only 3 of 26 panels overlap, and it targets zoo /
  aquarium collection management (studbooks, SSP, CITES, AZA, USDA APHIS) —
  a vertical nothing on `main` touches. Self-describes as a *"ZIMS alternative."*
- **`stonedesk-hr.html` — merge candidate, not an app.** A stone-fabrication
  new-hire compliance packet. Its silica/OSHA material is already in StoneDesk,
  more thoroughly (PPE 475 vs 31). What is nowhere on the platform is the
  onboarding paperwork: I-9, W-4, direct deposit, employment agreement. Those
  belong inside StoneDesk.

### A consumer product line, explicitly out of scope

Fourteen files dated 2026-06-07 sharing one architecture — **exactly 18
`api/claude` integrations each**, ~50 `localStorage` refs: SAIRN Roam, Money,
Legal, Home, Health, Senior, Lingual, Study, Biz, Hope, Vets, Flow, Learn, and
`index.html` (SAIRNtype). Real wired apps, not mockups. **B2B only per Michael;
these are archived, not proposed.**

## Rules for anything taken out of here

Everything here predates the platform's current discipline. It was written
before per-employee auth, before the grant-sweep rules, before the
silent-failure and fabricated-data standards. Two of the four apps reviewed
carried hardcoded PIN objects; one fabricated AI analysis from a fixture.

**Nothing leaves this directory without the same review SAIRNmechanical got:**
syntax per block, auth built before it goes live, fabricated data stripped, and
live verification. See `sairn-employee-auth-scaffold` and `sairn-guardian-v2`.

## Provenance

Branch tip `7d9b2d6` (2026-06-21). Files extracted at that commit and verified
167/167. The full 901-commit history is preserved under the tag
`archive/lucid-ptolemy-b73vu0` — the file copy here is for reading; the tag is
for recovering anything with its history intact.
