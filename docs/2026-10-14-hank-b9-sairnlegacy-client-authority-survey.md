# SAIRNlegacy — the other 34 resources, surveyed for the `leg_bookings` shape

**2026-10-14, hank b9 item 4. A SURVEY, NOT A FIX.** The instruction was to
survey and report with `file:line`. Nothing in this document has been changed in
code; the five findings below are open and each carries its next step.

---

## The shape being looked for, stated once

`sairnlegacy.html:2999` `bookingConflict()` was a **correct** interval-overlap
test that **hard-blocked** a save — and it read `bookings()`, this device's
`localStorage`. The server did no equivalent check, so two devices with stale
caches each passed their own check and **both writes were accepted**, because a
new booking carries a new `booking_id` and nothing collides. Fixed in b8 at
`api/sd-data.js:15154`.

So the shape is: **a client-side guard that refuses or blocks a save, decided on
local data, with no equivalent server-side re-check.**

A guard that validates the record **against itself** — a non-empty name, a
required case selection — is **not** the shape. There is nothing for a server to
re-check and no second device involved. 29 of the 34 are that, and they are
listed rather than omitted so the denominator is real.

## How this was established, and the one thing it rests on

`api/_resources/sairnlegacy.js` owns 36 resources. `leg_merch_units` (the
reservation lock, 2026-08-10) and `leg_bookings` (b8) are already fixed and are
excluded, leaving 34.

**THE LOAD-BEARING FACT, AND IT IS ONE GREP:**

    grep -n "resource === 'leg_" api/sd-data.js
    15077:      if (resource === 'leg_merch_units' && payload.status === 'Reserved') {
    15154:      if (resource === 'leg_bookings' && payload.status !== 'Cancelled') {

**There are exactly two bespoke `leg_` branches in the whole handler, and they
are the two already-fixed resources.** Every one of the other 34 falls through
to the generic `LEG_RESOURCES` upsert — a blind `merge-duplicates` POST with no
business-rule check of any kind. So for all 34, the "server check" column is the
same answer, and it is the absence of one.

That makes the whole survey turn on ONE measurement, which is a weakness worth
naming: re-run that grep before trusting this document. Line numbers move; the
count of two does not, until somebody adds a third.

**Delegated and then spot-checked.** The per-resource walk was run by a
read-only subagent. The strongest finding was re-verified by hand against the
file at this HEAD before being written down — `clergyBookingConflict` at
`sairnlegacy.html:4817`, its blocking call at `:4854`, its write at `:4858`, and
the absent server branch by the grep above. The other four were taken from the
survey with their stated nuances intact rather than upgraded.

---

## (a) All 34, classified

| resource | classification | client guard | server check |
|---|---|---|---|
| `leg_clergybookings` | **MATCHES THE SHAPE** | `sairnlegacy.html:4817` def, `:4854` block | none — generic upsert only |
| `leg_monuments` | **MATCHES THE SHAPE** | `sairnlegacy.html:4591` def, `:4642` block | none — generic upsert only |
| `leg_deathrecords` | **MATCHES THE SHAPE** | `sairnlegacy.html:2946` | none — generic upsert only |
| `leg_invoices` | **MATCHES THE SHAPE** (weaker) | `sairnlegacy.html:3393`, composed at `:3650` | none — generic upsert only |
| `leg_aftercare` | **MATCHES THE SHAPE** (weaker) | `sairnlegacy.html:4235`, `:4240` | none — generic upsert only |
| `leg_cases` | no blocking guard | `:2501` required-field | generic upsert |
| `leg_dispatches` | no blocking guard | `:2550` required-field | generic upsert |
| `leg_custodylog` | no blocking guard | `:2601`, `:2603` required-field | generic upsert |
| `leg_merch_catalog` | no blocking guard | `:2654` required-field | generic upsert |
| `leg_documents` | no blocking guard | `:2857`, `:2883` required-field | generic upsert |
| `leg_facilities` | no blocking guard | `:3015` required-field | generic upsert |
| `leg_plots` | no blocking guard | `:3127` required-field | generic upsert |
| `leg_cremations` | no blocking guard | `:3176` required-field | generic upsert |
| `leg_preneed` | no blocking guard | `:3233` required-field | generic upsert |
| `leg_insurance` | no blocking guard | `:3253` required-field | generic upsert |
| `leg_gplservices` | no blocking guard | none found | generic upsert |
| `leg_obituaries` | no blocking guard | `:4106`, `:4119` required-field | generic upsert |
| `leg_memorials` | no blocking guard | `:4165` non-blocking | generic upsert |
| `leg_guestbook` | no blocking guard | `:4178`, `:4180` required-field | generic upsert |
| `leg_processions` | no blocking guard | `:4298` required-field | generic upsert |
| `leg_vehicles` | no blocking guard | `:4354` required-field | generic upsert |
| `leg_maintenance` | no blocking guard | `:4371` required-field | generic upsert |
| `leg_certs` | no blocking guard | `:4444` required-field | generic upsert |
| `leg_petcases` | no blocking guard | `:4492` required-field | generic upsert |
| `leg_keepsakes` | no blocking guard | `:4525` required-field | generic upsert |
| `leg_keepsakeorders` | no blocking guard | `:4542` required-field | generic upsert |
| `leg_florists` | no blocking guard | `:4686` required-field | generic upsert |
| `leg_floristorders` | no blocking guard | `:4703` required-field | generic upsert |
| `leg_caterers` | no blocking guard | `:4754` required-field | generic upsert |
| `leg_catererorders` | no blocking guard | `:4770` required-field | generic upsert |
| `leg_clergy` | no blocking guard | `:4832` required-field | generic upsert |
| `leg_liveryvendors` | no blocking guard | `:4913` required-field | generic upsert |
| `leg_liverybookings` | no blocking guard | `:4938` required-field | generic upsert |
| `leg_tributes` | no blocking guard | `:4986` required-field | generic upsert |

**`leg_liverybookings` IS THE ONE TO LOOK AT TWICE and it is called out rather
than buried.** It is a BOOKING resource with only required-field checks — so it
is classified "no blocking guard" because there is no conflict check to be
racing, not because it is safe. A livery vehicle can already be double-booked
**on one device**, which is a different and simpler defect than the one this
survey is about. Recorded here; not this survey's finding.

## (b) The five, with the consequence in the app's own terms

### 1. `leg_clergybookings` — HIGH CONFIDENCE, and it is the same defect twice

`clergyBookingConflict()` (`sairnlegacy.html:4817`) is the **same algorithm** as
the fixed `bookingConflict()`, and the file says so itself at `:4809`: *"Same
overlap-interval-test algorithm as Service & Facility Scheduling's
`bookingConflict()` — applied to its own `leg_clergybookings` store"*. It reads
`clergyBookings()` — local storage. It hard-blocks at `:4854`. The write at
`:4858` goes to the generic upsert with a fresh `CB-` id, so nothing collides.

Two staff on two devices, each holding a clergy calendar taken before the
other's booking synced, both pass and both write a `Requested` booking for the
**same officiant at an overlapping time**. The officiant is double-booked for
two funerals in the same hour. One family's service begins with no clergy
present, and it is discovered when they do not arrive.

**This is the b8 defect with a different resource name.** The b8 handoff said
*"leg_bookings is the SECOND instance found in one app, so a third is worth
looking for rather than waiting for."* This is the third.

**NEXT STEP:** the b8 fix, applied verbatim to this branch — a SELECT of the
server's non-`Completed` rows for the same `clergy_id`, a 409 on overlap, and
the `saveClergyBooking` rollback. `api/sd-data.js:15154` is the template and
`api/sd-data-leg-bookings-toctou.test.js` is the suite to copy. **BUT the
`status` vocabulary differs** — `leg_bookings` exempts `Cancelled`,
`clergyBookingConflict` skips `Completed`. Copying the status literal would be
cross-domain convention 7 exactly: byte-identical is not safe-in-context.

### 2. `leg_monuments` — a permanent, physical error

`monumentMismatches()` (`sairnlegacy.html:4591`) cross-checks the inscription
name and dates against the linked case's `decedent_name` / `decedent_dob` /
`decedent_dod`, read from the **locally cached** `cases()` list, and blocks
finalising unless an override box is ticked (`:4642`).

If this device's cached case is stale — another device just corrected a
misspelled name or a death date — the mismatch check passes on the old values
and a monument order is finalised with the wrong inscription. **A headstone is
engraved**, and the family sees it at the cemetery. Expensive, sometimes
impossible to correct.

**NEXT STEP:** this one is NOT the booking fix. The race is against a RELATED
record, so the server check is "re-read the case row and re-run the comparison
server-side before accepting a non-Draft status" — a different shape, and the
override path has to survive it or the feature breaks.

### 3. `leg_deathrecords` — a permit issued while the cause is open

`savePermit()` blocks `Filed` / `Issued` while the on-screen cause-of-death
pending box is ticked (`:2946`), and that box is populated from this device's
cached record at `:2929`.

The dangerous direction is the stale one: a device whose cache predates another
device marking the cause pending can push `Issued` through. A cremation or
burial permit reads as issued while the coroner's review is genuinely still
open — a compliance and chain-of-custody failure attached to a named death case.

**NEXT STEP:** the server must re-read the stored record's pending flag before
accepting a `Filed` / `Issued` transition. Narrow, one transition, same shape as
the `sc_auth_requests` sign-off gate this handler already carries.

### 4. `leg_invoices` — WEAKER, and the nuance is kept

`saveInvoice()` refuses whenever the locally composed statement has a
`severity:'refuse'` problem (`:3393`), most often `PRICE_NOT_ON_FILE`, computed
at `:3650` from the **locally cached** merchandise catalogue and GPL services.

This is a weaker match and is labelled so: the race is against this home's own
price list rather than against another device writing the same record. The
realistic failure is a stale catalogue producing a signed Funeral-Rule statement
with a price wrong or missing relative to the home's true current list — a
billing and disclosure problem on a specific family's bill.

**NEXT STEP:** decide whether the server re-prices before accepting an invoice.
That is a product decision about where pricing authority lives, not a bug fix,
and it should be made before code is written.

### 5. `leg_aftercare` — WEAKER, duplicate contacts with a bereaved family

`generateAftercareSchedule()` reads local `aftercareCheckins()` to decide which
of the three standard check-ins already exist and refuses to write if all three
do (`:4235`, `:4240`). Two devices that have not synced each other's writes each
believe none exist and each create a set.

A grieving family gets duplicate grief-support follow-ups — or worse, duplicates
compete for staff attention and some are skipped as already handled.

**NEXT STEP:** the cheapest real fix is not a server gate at all: make the
check-in id DETERMINISTIC (`case_id` + type) so the upsert de-duplicates by
construction. A conflict check is the wrong tool when the collision can be made
impossible by the key.

## (c) Counts

| classification | count |
|---|---|
| **MATCHES THE SHAPE** | **5** |
| server re-checks the same condition | **0** |
| no blocking guard (required-field only) | **29** |
| total surveyed | **34** |

**ZERO is the number worth reading.** Not one of the 34 has a server-side
re-check of a client-side rule. The two resources that do are the two that were
fixed after being found as defects — which means this platform's SAIRNlegacy
server has never had a business rule on it that somebody did not first have to
report as a bug.

## What this survey did NOT do

* **It did not read the other 20 apps.** The shape is not SAIRNlegacy's; the
  b8 handoff asked for this app and this is this app. `rf_settings`
  (`api/sd-data.js:8757`) was noticed in passing while tiering `sen_settings`
  and has the identical open-read shape SAIRNsenior just had — unverified, not
  surveyed, and recorded only so the next person has a starting point.
* **It did not fix anything**, including `leg_clergybookings`, which is one
  verbatim application of an existing fix away. The instruction was to survey.
* **It did not drive any of the five.** Every consequence above is read out of
  the code, not reproduced against two devices. A reproduction would upgrade
  these from "the code permits this" to "this happens", and none of the five has
  had that done.
