# Cross-App Intelligence — Feasibility & Design Scoping

**Status:** Design-only, not built. No app files touched for this task.
**Date:** 2026-08-18
**Author:** CC

## The idea being scoped

A customer running both StoneDesk and SAIRNbiz gets AI insight that spans
both apps — e.g. flagging a slow-paying customer in StoneDesk who also has
an overdue invoice in SAIRNbiz.

## What was checked

Read `api/sd-data.js` (2168 lines), `api/_lib/license.js`, and every
`sql/*license_seed.sql` file to see what the real shared-knowledge
infrastructure (`business_profiles`, `ai_memories`, `sd_shared_knowledge`,
`license_hash` keying) actually supports today, rather than assuming from
the "shared company-knowledge layer" note in an earlier session's summary.

## Core finding: there is no cross-app tenant identity today

`api/_lib/license.js` validates a bearer `license_key` against the
`license_keys` table. Every seed file (`sairnbiz_test_license_seed.sql`,
`demo_license_keys_seed.sql`, etc.) confirms `license_keys` is keyed by
`(key, app_id)` — **one license key per app, per customer.** A business
running StoneDesk and SAIRNbiz today holds two separate license keys (e.g.
`SB-TEST-2026` for SAIRNbiz, a different key for StoneDesk).

`license_hash = sha256(license_key)` is what every StoneDesk-owned table
(`business_profiles`, `ai_memories`, `sd_shared_knowledge`, `sd_slabs`,
etc.) is scoped by. Since the two apps' keys are different strings, **the
same real business produces two different, unrelated `license_hash`
values** — one per app. `sd_shared_knowledge` looks unscoped by `app_id`
at first glance (its query is `license_hash=eq...` with no `app_id`
filter), but that doesn't matter: the hash itself already diverges per
app, so in practice it's still siloed per app, not shared.

There is no `accounts`/`tenants`/`organizations` table anywhere in `sql/`
joining a business's StoneDesk key to its SAIRNbiz key. `customer_email`
exists on each `license_keys` row and is the only field that could
plausibly link the two, but:
- it's not used as a join key anywhere in `sd-data.js` today
- there's no guarantee the same email was used at signup for both app
  purchases (different sales conversations, different point of contact)
- it's provided by whoever fills the form at purchase time, so it's
  unvalidated as an identity key (typos, personal vs. business email, etc.)

**Conclusion: this is not "expose an existing shared layer to a second
app." It requires new infrastructure — a real account-linking layer that
does not exist yet.**

## What would actually be needed

1. **An account-linking table.** Something like
   `cross_app_links(account_id, license_hash, app_id, linked_at)` — a real
   table an owner explicitly opts into (e.g. "link my SAIRNbiz account to
   my StoneDesk account"), not an automatic email match. Auto-matching on
   `customer_email` is a real risk: two different businesses could share a
   generic email (a shared bookkeeper, a franchise parent), silently
   leaking one tenant's AR/customer data into another's AI context. This
   needs to be an explicit, verifiable action (e.g. a confirmation code
   sent to the email on file for *both* licenses) — same category of
   caution Hank's SAIRNlaw work just flagged for privilege-isolation on
   shared-knowledge, applied here to tenant-isolation instead.

2. **A narrow, purpose-built read**, not a data merge. The example given
   (slow-paying StoneDesk customer + overdue SAIRNbiz invoice) needs a
   customer-identity match *within* the linked account — StoneDesk's
   customer record and SAIRNbiz's AR/invoice record need to resolve to
   the same real person, which today only happens by name/phone/email
   fuzzy-matching (no shared customer ID exists between the two apps'
   schemas either — this is a second identity problem, separate from and
   on top of the account-linking one above). Whatever endpoint answers
   "does this StoneDesk customer have SAIRNbiz AR exposure" should return
   only that flag plus the minimum supporting fields (amount, days
   overdue), not raw access to the other app's dataset.

3. **Consent and scope, per direction.** Linking should be revocable, and
   probably needs to be asymmetric-safe: a StoneDesk employee querying
   into SAIRNbiz AR data is exposing SAIRNbiz's financial data to a
   different app's staff, which may be a different set of employees under
   a different role model (StoneDesk's roles vs. SAIRNbiz's owner/hr/
   accounting/manager/staff roles are not the same list). The gate needs
   to be role-aware in *both* apps' role models, not just "the account is
   linked."

4. **A real endpoint**, not a client-side merge — `sd-data.js`'s existing
   pattern (bearer license key -> `license_hash` -> scoped table read) is
   the right shape to extend, but it currently assumes one key = one
   tenant = one app. A cross-app read would need to accept both apps'
   keys (or an account-level token minted only after step 1's linking) and
   explicitly enumerate which fields cross the boundary — not a generic
   passthrough.

## What's NOT needed to be built to answer "is this real"

No app files were touched for this task, per scope. This is a design/
feasibility answer only.

## Recommendation

Feasible, but it's a new subsystem (account linking + consent + a narrow
cross-app read + dual role-model gating), not a small addition to the
existing shared-knowledge layer. Suggest treating it as its own scoped
build (own SQL migration, own spec doc, own decision-gate pass given it
touches two tenants' financial data across an explicit trust boundary) —
not something to bolt onto the next StoneDesk or SAIRNbiz session in
passing.
