# StoneDesk `sdDemoCleared() ? [] : SEED` — the full audit

**2026-09-04 (Fourth).** Closes the standing follow-on task
`sairn-guardian-v2` has carried since 2026-08-22: *"audit the other 28 SEED
sites in `stonedesk.html` against the two-part test, and then check whether
other SAIRN apps carry the same fallback shape."*

The count in that task was an estimate. **There are 31 fallback sites**, and the
skill's own figure of "29 SEED constants / 56 fallback sites" counted every
occurrence including the duplicated `catch` arm of the same expression. One
audit, one number, derived: 31 `load()`-style sites across 30 storage keys.

---

## What the audit was looking for

Guardian's two-part test, from the Slabs incident (`501d15b`):

> *Can this panel's real store be empty while the demo-cleared flag is false,
> and does the panel compute any number from what it renders?*

Both true on the Slabs panel: `sd_slab_tracker` was absent, `load()` fell
through to an in-file `SEED`, and the panel rendered **8 invented slabs** and
computed **$4,420 of inventory value** from them — while a real, server-synced
slab was invisible and excluded from every count.

**Applying that test literally flags 18 of the 31 sites, and that answer is not
useful.** Every one of those 18 computes a number from its seed, because that
is what a demo seed is for. Taken at face value the test says the app's entire
demo experience is a defect, which is a product decision nobody asked for and
not what the Slabs finding was about.

## The question that actually separates them

**Can the seed MASK something real?**

A seed can only hide data if data exists somewhere else to be hidden. On a
purely local panel with no server resource behind it, a first-run seed is the
demo: there is nothing else it could be displacing. On a panel whose real
source of truth is the SERVER, the same seed answers on the server's behalf and
is indistinguishable from a real answer.

**Exactly one of the 31 sites has a server read behind it: `sd_crm`.**

Mechanically: for each site, the storage key, then
`html.indexOf("sdData('read','" + key + "'")`. One hit.

> ### ⚠ CORRECTED LATER THE SAME DAY — THAT ANSWER WAS WRONG, AND THE METHOD IS WHY
>
> **Three seed stores reach the server, not one.** The check above searched for
> the literal `sdData('read','<storage key>'`, which silently assumes the
> RESOURCE is named the same as the KEY. Two are not:
>
> | key | how it reaches the server | what the seed can do there |
> |---|---|---|
> | `sd_crm` | `sdData('read','sd_crm')` | mask real leads — fixed by `crmSeed()` |
> | **`sd_remnant`** | **`sdData('read','remnants')` and a WRITE via `sdRemnantSyncOne()`** | **mask real remnants AND be published to a real storefront** |
> | `sd_employees` | `sdData('read','employee_profile',{all:true})` — a different resource, used to enrich the roster | nothing: no roster row is ever written back, so a seeded employee cannot leave the device |
>
> **`sd_remnant` is the sharper of the two real ones, and it is the one this
> audit's method could never have found.** `sdRemnantHydrate()` is a MERGE that
> keeps local-only rows and then `save()`s the result — so on a device with an
> empty cache the six seed remnants were not merely rendered, they were WRITTEN
> INTO localStorage alongside the shop's real ones and became indistinguishable
> from them. From there one click of the publish toggle calls
> `sdRemnantSyncOne()`, which writes to Supabase, and the public catalog
> publishes anything `published` and `Available`. **Three of the six seed rows
> are Available**, with invented stone, invented dimensions and an invented
> price.
>
> Fixed by tagging seed rows `_demo` at load and refusing to sync a tagged row
> unless the licence is the demo one — the same gate the seeds themselves now
> use. The refusal returns a distinct value rather than null, so the caller says
> *"that is demo inventory"* instead of blaming the connection.
>
> **The method lesson, which is the transferable part:** matching a literal
> string is testing EXISTENCE where the requirement is USE — `sairn-code-scrubber`
> item 16, Shape B — and it produced a confident "exactly one" for an audit that
> had missed two. The corrected check asks whether the seed's own script block
> talks to the server AT ALL, and deliberately over-flags: `sd_employees` is
> listed with its exposure written out rather than filtered away, because
> narrowing the check is how it would go back to passing for the wrong reason.
> Held by `tests/crm_seed_not_a_pipeline.js`.

## The one real finding — `sd_crm`

`load()` is a documented local cache of the last real server read. With **no
cache and a FAILED read**, it returned six invented leads and `render()` did
real arithmetic on them:

| element | showed | truth |
|---|---|---|
| `crm-leads` | 6 | unknown |
| `crm-pipeline` | **$35,900** | unknown |
| `crm-hot` | 1 | unknown |
| `crm-conv` | 0% | unknown |
| `crm-avg` | $5,983 | unknown |

Nothing said the read had failed. A shop with a broken session, an expired key
or an unreachable database saw a populated CRM and a five-figure pipeline
presented as its own.

**Worth stating precisely, because it bounds the exposure:** `refresh()` already
degraded honestly on the *cache* — a failed read left an existing local cache
untouched rather than wiping it, and that was already right. The gap was the
case where there is **no cache to leave untouched**, where the seed stepped in
and answered for the server.

Also worth stating: a *successful* read of `[]` is saved as `[]`, which is
truthy, so the seed can never return after one good sync. The seed was only ever
reachable **before the first sync, or after a failed one** — and it is the
second of those that was lying.

### The fix, and what it deliberately is not

The seed is **not deleted**. Deleting it outright was the Slabs fix; here it
would also delete the demo, which is a product decision and not one to take
silently. Instead the seed is skipped for the case it never covered:

```js
function crmSeed(){ return (_crmReadFailed||sdDemoCleared())?[]:SEED; }
```

`_crmReadFailed` is set from `sdReadFailed('sd_crm')` — the mechanism added the
same day for the Public Catalog panel, which distinguishes a failed read from a
genuine empty one. Without it, a first-run user with no session is
indistinguishable from one whose database is unreachable.

When the read failed and there is no cache, the five KPIs render `--` rather
than a number, and the table says the leads could not be loaded. **A confident
`$0` pipeline would have been as wrong as `$35,900`** — it just looks more
innocent.

Held by `tests/crm_seed_not_a_pipeline.js`, 12 assertions, including a mutation
that restores the old fallback and asserts the $35,900 pipeline reappears.

---

## The full table

`$ KPIs computed` counts `textContent = '$'…` assignments in the panel block —
the places a dollar figure is written to the page from seed arithmetic.

**`money in the seed` is a regex sum of `amt`/`val`/`cost`/`price`/`total`/
`amount` fields in the seed constant. It is INDICATIVE, not exact** — it will
miss a differently-named field and can double-count a nested one. It is here to
rank the sites, not to be quoted.

| line | storage key | seed rows | $ KPIs computed | server-backed | money in the seed |
|---:|---|---:|---:|:---:|---:|
| 5701 | `sd_intakes` | 3 | 3 | no | — |
| 6395 | `sd_warranty` | 6 | 1 | no | — |
| 6745 | `sd_schedule` | 7 | 0 | no | — |
| 6947 | `sd_fieldmap` | 3 | 0 | no | — |
| 8259 | `sd_vendors` | 7 | 3 | no | — |
| 8876 | `sd_comms` | 4 | 0 | no | — |
| **27764** | **`sd_crm`** | **6** | **5** | **YES — FIXED** | **$35,900** |
| 28029 | `sd_jobcost` | 5 | 3 | no | — |
| 28235 | (shared `load`) | 9 | 0 | no | — |
| 28391 | `sd_remnant` | 6 | 1 | no | $810 |
| 28596 | `sd_pos` | 4 | 1 | no | $18,100 |
| 28720 | `sd_receiving` | 4 | 1 | no | $9,900 |
| 28845 | `sd_manifest` | 4 | 0 | no | — |
| 29400 | `sd_sintered` | 6 | 1 | no | $575 |
| 30241 | `sd_reviews` | 6 | 0 | no | — |
| 30404 | `sd_contractors` | 5 | 1 | no | — |
| 30531 | `sd_referrals` | 5 | 1 | no | $8,300 |
| 30671 | `sd_priceintel` | 5 | 2 | no | — |
| 30811 | `sd_equipment` | 8 | 1 | no | $471,000 |
| 31108 | `sd_employees` | 8 | 0 | no | — |
| 31113 | (shared `load`) | 8 | 0 | no | — |
| 31502 | `sd_stoneyard` | 8 | 2 | no | $8,600 |
| 32036 | `sd_bids` | 5 | 2 | no | $293,000 |
| 32166 | `sd_it_tickets` | 8 | 0 | no | $3,137 |
| 32168 | `sd_it_licenses` | 5 | 0 | no | $3,137 |
| 32294 | `sd_damage` | 3 | 2 | no | $1,230 |
| 32432 | `sd_training` | 11 | 0 | no | — |
| 32561 | `sd_bulletins` | 5 | 0 | no | — |
| 32698 | `sd_waste` | 5 | 1 | no | $155 |
| 32829 | `sd_nps` | 6 | 0 | no | — |
| 32962 | `sd_ap` | 6 | **4** | no | $20,770 |

---

## DECIDED, same day — the seeds are scoped to the demo licence

**Michael's call, 2026-09-04, after reading the numbers below:** not a blanket
delete. The demo account has to keep looking like a populated shop for real
sales use, but a real paying customer whose account happens to look untouched
must never see fabricated numbers presented as their own business.

So the seeds render for **`SD-PINNACLE-2026`** and every other licence gets the
honest empty state — the same answer Slabs got in `501d15b`.

**Implemented as one widened gate, not 32 edits.** Every seed site already calls
`sdDemoCleared()`; it now returns true for any licence that is not the demo one,
which reaches all of them at once. Rewriting 59 call sites in a 2MB file is
exactly the bulk find-replace CLAUDE.md's syntax rule forbids, and that rule
exists because it has broken this file before.

Three consequences worth knowing:

1. **The name is now narrower than the behaviour.** `sdDemoCleared()` answers
   *"should demo seed data be suppressed?"*, of which "the user cleared it" is
   one of two reasons. It was not renamed, for the reason above.
   `sdDemoClearedByUser()` carries the original meaning for the one caller that
   needs it — the Admin toggle's checked state, which reports a user action and
   would otherwise show every real customer as having cleared demo data they
   never had.
2. **An unlicensed install now gets empty states too.** That is a real change to
   the "fresh sales-demo install" case the old comment described. It follows
   from scoping to a named licence rather than to "demo-ish", and failing toward
   empty is the deliberate direction: an empty panel is a missing feature, an
   invented payables total is a wrong number.
3. **Re-enabling demo mode off the demo licence no longer claims it worked.**
   The flag still flips, nothing seeds, and the toast says so — a success
   message for an action that did nothing is the same class as the intake
   panel's *"Customer + Job created from intake!"*.

**A separate omission found while doing it, by deriving the list rather than
reading it:** `SAFE_DEMO_KEYS` — the single source of truth for what "Clear Demo
Data" wipes — was missing `sd_it_tickets` and `sd_it_licenses`. Their fallback
variables are named `TICKETS` and `LICENSES`, so every scan looking for `||SEED`
walked past them. Identical omission and identical cause to `sd_fieldmap` in
2026-08-04. Before this, Clear Demo Data reported success and left the IT panel
seeded. Both added.

Held by `tests/demo_seed_licence_scope.js`, 15 assertions — including that a
near-miss licence (`SD-PINNACLE-2027`, `SD-PINNACLE-2026-B`) is not the demo
licence, that a missing `sdLicenseKey` resolver fails toward empty rather than
toward seeded, and that `SAFE_DEMO_KEYS` covers every seeded key **by deriving
both sides** rather than by comparing two hand-written lists.

---

## The numbers the decision was made on

The 30 local sites are the demo. Nothing real is hidden behind any of them. But
a first-run shop that never clears demo data still sees, presented as its own
business:

- **`sd_ap`** — four dollar KPIs off six invented vendor bills: open payables,
  due-this-week, **overdue**, and month-to-date paid, plus a full aging table.
  The seed rows are dated **2024**, so the aging buckets read "60+ days" on
  bills that never existed. This is the sharpest of the 30.
- **`sd_equipment`** — ~$471,000 of invented equipment value.
- **`sd_bids`** — ~$293,000 of invented bid value.
- **`sd_pos`**, **`sd_receiving`**, **`sd_stoneyard`**, **`sd_referrals`** —
  five-figure invented totals each.

**All of the above is now suppressed on every licence except
`SD-PINNACLE-2026`** — see the decision section higher up. The numbers are kept
here because they are what the decision was made on, and because they are the
right list to re-check if the gate is ever changed.

A middle option was considered and not taken, recorded so it is not
re-discovered as new: a demo shop could be seeded on first run as *real local
records* the user can see and delete, rather than as a fallback that silently
answers when a store is empty. That converts an invisible fabrication into
visible sample data. It is a larger change than licence-scoping and buys little
once the seeds only ever reach the demo account.

## The second half of Guardian's task — other apps

**Not done, and explicitly not claimed.** The follow-on also asks whether other
SAIRN apps carry the same fallback shape. That is a separate pass across
fifteen app files and was not run here; this audit covers `stonedesk.html` only.
Saying so rather than letting "the SEED audit" read as platform-wide.
