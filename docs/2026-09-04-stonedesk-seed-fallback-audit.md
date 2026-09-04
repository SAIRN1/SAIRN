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

## What is left open, and it is a decision rather than a defect

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

**The Slabs precedent says delete the fallback and render an honest empty
state.** Doing that to 30 panels removes the demo experience from the product,
which is Michael's call and not a code fix. **Recorded here with the numbers so
the decision can be made on the numbers rather than on "~28 unaudited sites".**

A middle option exists and is worth naming: a demo shop could be seeded on
first run as *real local records* the user can see and delete, rather than as a
fallback that silently answers when a store is empty. That converts an
invisible fabrication into visible sample data. It is a larger change than
either alternative and is not proposed here, only recorded.

## The second half of Guardian's task — other apps

**Not done, and explicitly not claimed.** The follow-on also asks whether other
SAIRN apps carry the same fallback shape. That is a separate pass across
fifteen app files and was not run here; this audit covers `stonedesk.html` only.
Saying so rather than letting "the SEED audit" read as platform-wide.
