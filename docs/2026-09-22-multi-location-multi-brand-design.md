# Multi-location, multi-brand, and client multiplicity — one design, measured first

**Scope: DESIGN ONLY. No app code changes.** This document states what exists,
what is genuinely missing, and what shape the missing part should take. It does
not build any of it, and §8 lists what it deliberately does not decide.

**Written 2026-09-22 (cody) against the five apps Michael named — StoneDesk,
SAIRNlegacy, SAIRNgrounds, SAIRNsenior, SAIRNcare — plus the two apps that
already solved most of this and are therefore the references rather than the
subjects.**

**Do not quote a count from this document.** Every figure below was read out of
the files named beside it at the moment of writing; re-read the file.

---

## 0. The premise this document started from was wrong, and correcting it is what made it useful

The item is named *"multi-location/multi-brand under one backend"*, which reads
as *build the thing that does not exist*. It is the second time that premise has
been wrong in the same direction.

`docs/SAIRN-OPEN-WORK-INDEX.md:186` already records the first correction, Hank's,
2026-09-16: **it is not solved nowhere, it is solved in four places that
disagree**, and `'LOC-DEFAULT'` was a hardcoded literal in 30+ places across four
apps' JS, HTML and SQL. That row also carries a self-correction inside itself —
its author first wrote that nothing stamps a location onto a StoneDesk row,
having grepped `api/sd-data.js` for a `location_id` COLUMN when the value lives
in `sd_slabs.data` jsonb.

**This session repeated a version of that mistake and caught it before writing
it down.** I read `stonedesk.html:9115` — `localStorage.getItem('sd_locations')`
— saw `sd_locations` absent from `api/_resources/stonedesk.js`, and concluded
StoneDesk's yard registry was per-device: *"a stamped foreign key whose registry
only exists on one workstation."* That is false.

- `sql/stonedesk_locations_schema.sql` (2026-09-03) creates a real
  licence-scoped Supabase table.
- `api/sd-data.js:2068` and `:2102` serve it under the resource name
  **`locations`**, not `sd_locations`, which is why the registry grep missed it.
- `stonedesk.html`'s `sdLocHydrate()` calls `sdData('read','locations',null)`.
  The localStorage is a **cache**, exactly like every other resource in that app.
- `sdLocName()` already handles the case I thought was the defect, and names it:
  `'(yard not on this device)'` — *"A yard this device does not hold still had
  slabs in it. Saying so beats rendering a raw id, and beats relabelling them
  Unassigned — they were assigned, to something not here."*

The file's own comment at `:9108` warns about exactly this class of error:
*"grepping 'location' in this file suggested the feature was partly there when a
word-boundary search for `location_id` returned zero."*

**Both corrections run the same direction: the platform has more of this built
than the item name implies, and the real gaps are narrower and sharper than
"build multi-location".** That is what the rest of this document is about.

---

## 1. What exists, per app, read rather than assumed

| App | LOCATION axis | BRAND / ENTITY axis | Where |
|---|---|---|---|
| **SAIRNroofing** | yes — `rf_locations`, stamped | **yes** — `entity_id` on the location | `api/_lib/roofing-locations.js`, `api/_lib/roofing-consolidation.js` |
| **SAIRNdental** | yes — stamped at write, rolled up on read | no | `api/_lib/dnt-location.js`, `api/_lib/dnt-rollup.js` |
| **StoneDesk** | yes — `sd_locations`, server-backed; the **slab** carries it and everything else derives | no | `sql/stonedesk_locations_schema.sql`, `api/sd-data.js:2061`, `stonedesk.html:9105` |
| **SAIRNsenior** | yes — `sen_branches`, `branch_id` on clients and caregivers | **yes** — `sen_franchise_agreements`, keyed on `branch_id` | `api/_resources/sairnsenior.js:108`, `sairnsenior.html:2280`, `:4164` |
| **SAIRNlegacy** | **none** | none | `Chapel` is a facility TYPE inside scheduling (`{type: Chapel/Vehicle/Staff}`), not a location axis |
| **SAIRNgrounds** | **none** | none | every `yard` hit is a golf distance unit |
| **SAIRNcare** | **none** | none | the UI says *"this facility"*, singular, throughout |

`api/_lib/location-scope.js` already owns the shared stamp and the
`LOC-DEFAULT` constant, and its own boundary note states the finding this
document builds on: **LOCATION and BRAND/ENTITY are two axes, not one, and
roofing already models both while dental models one.**

### 1.1 Two apps derived the same principle independently, which is why it is the right one

**SAIRNroofing**, `roofing-consolidation.js`:

> `entity_id` lives ON THE LOCATION and nowhere else. No invoice, job, draw or
> schedule row carries one, and none ever should. … MOVING A BRANCH BETWEEN
> ENTITIES MOVES ITS ENTIRE HISTORY, because history was never labelled.

**StoneDesk**, `stonedesk_locations_schema.sql`:

> A slab is a physical object and it is AT a yard. Everything else — a quote, a
> job, a purchase order, a remnant — gets its location by looking at the slab…
> Stamping a location onto a job at creation FREEZES it: move the work to the
> other yard and the history stays attributed to the old one forever.

Two apps, two sessions, no shared code: **attribution is DERIVED on read, never
stamped on the dependent record.** Stamp the one thing that physically has the
property; derive everything else from it. That is the invariant this design
adopts, and it is adopted because it was reached twice rather than because it
sounds right.

### 1.2 And one invariant that makes it checkable

`roofing-consolidation.js` states the test that keeps a derived attribution
honest, and it should be the platform's:

> Reassigning a location changes the BUCKETS and must not change the GRAND
> TOTAL. Every result carries `input_total`, `grand_total` and `reconciles`.

A roll-up that silently loses rows is worse than no roll-up. `dnt-rollup.js`
reaches the same place from the other side: `UNASSIGNED` is a bucket and never a
rounding error, and a resource that could not be read yields `null` plus a named
entry — **never `0`, because zero is a measurement**.

---

## 2. The four real gaps

Stated separately because they have different sizes, different owners, and
three of them are not what the item name says.

### GAP A — three of the five named apps have no axis at all

SAIRNlegacy, SAIRNgrounds and SAIRNcare. This is the only gap the item name
describes, and it is the smallest: two proven reference implementations exist
and `location-scope.js` already holds the shared half.

**But the deadline is asymmetric and dental already argued it correctly**
(`dnt-location.js`):

> Of the whole multi-location problem, exactly one part has a deadline:
> CAPTURING which location a row belongs to at the moment it is written.
> Consolidated reporting, a per-location booking page, and a client-side
> location selector can all be built later at the same cost. **Attribution
> cannot** — a charge recorded without a location can never be assigned to one
> afterwards, because the information was never collected.

So GAP A's urgent half is *capture*, not *reporting*, and only for an app whose
customer actually operates more than one site. **A consolidator that owns
fourteen funeral homes is a real and common shape in that industry; a
single-chapel operator is not served by any of this.** Which of the three has
such a customer is a business question and §8 leaves it there.

### GAP B — there is no entity ABOVE the licence, and that is the structural one

`license_hash = sha256(license_key)` is the tenancy boundary for the entire
platform. **Nothing sits above it.** So a group operating six sites under one
brand has exactly two options today, and both are bad:

- **N licences.** No shared view of anything, no cross-site roll-up, and every
  cross-site question is answered by exporting and merging by hand.
- **One licence.** Every site sees every other site's data, because the licence
  key is a **bearer credential the whole shop holds** — `sd_exec_msgs`'
  criticality row records exactly what that means when it is the only boundary.

There is a partial precedent and it is **not** the model to copy.
`api/org-intel.js` has `org_id` and `location_id`, but its own header says
`org_id` is *"a plain user-typed string … not a validated/hashed credential"*
and the endpoint is *"unauthenticated by design"*. It is an insight-sharing
layer for SAIRNscape and it says so. **It is not tenancy and must not be
promoted into tenancy by anyone reading this table and seeing two familiar
column names.**

### GAP C — attribution is not access partitioning, and NOBODY has the second

Every implementation on the platform says this about itself, unprompted:

- StoneDesk: *"THIS IS ATTRIBUTION, NOT ACCESS CONTROL, and the panel says so in
  those words. Every employee still sees every yard."*
- SAIRNroofing's open-work row: *"`location_id` is ATTRIBUTION only."*
- StoneDesk's gap row: *"BUILT — ATTRIBUTION, NOT ACCESS PARTITIONING."*

**A location-scoped user does not exist anywhere on this platform.** Nobody can
say "this branch manager sees only this branch". That is a separate and larger
piece of work than multi-location attribution, it interacts with every role gate
in `api/sd-data.js`, and it must not be smuggled in under the same item name —
which is precisely how it would arrive, because "multi-location" sounds like it
already includes it.

### GAP D — client multiplicity, which is the same shape one level down

See §3. It is folded into this document rather than scoped separately because it
is the identical problem — *many records, one real-world entity, one unified
view that must not merge what should stay separate* — and it fails in the
identical way: **by matching on a display string.**

---

## 3. Client multiplicity (item 4), folded in

A single client has several work-items over time: StoneDesk jobs, SAIRNbuild
projects, SAIRNvet pets, SAIRNsenior and SAIRNcare family members. Two things
are wanted at once and they pull against each other — **a unified history** and
**properly separated individual records**.

### 3.1 The platform is at four different points on one spectrum

| App | How a work-item finds its client | Verdict |
|---|---|---|
| **StoneDesk** | `custJobs = sdJobs.filter(j => j.customer.toLowerCase() === n)` — the file's own comment: *"there is no customerId FK on jobs/invoices in this codebase"* (`stonedesk.html:7377`) | **no identity** |
| **SAIRNvet** | `sv_patients.owner` is a free-text *"Owner last name"* (`addPatient()`, `:5457`). `sv_clients` rows carry `patients:'1'` / `patients:'340 head'` — a **display string**, not a link. **No FK in either direction.** | **no identity** |
| **SAIRNsenior** | `client_id` FK — but `var key = v.client_id \|\| v.client_name \|\| ''` (`:2368`) | **FK that degrades to a name** |
| **SAIRNcare** | `resident_id` throughout (`:2408`, `:2463`, `:2529`) | **correct** |

### 3.2 Why this is more serious than a merged contact card

`docs/CRITICALITY-TIERS.md` already names the hazard on `sd_customers`: worst
case *"Customer contact records lost or **merged wrongly**"*. The code contains
the exact mechanism that causes it.

- Two customers called *J. Smith* share one lifetime-value figure, one job
  history, and one credit judgement.
- One customer who changes name — marriage, a business rename — becomes two
  customers, and the second one has no history.
- **In SAIRNvet the records on both ends are Tier A / Confidentiality-A**
  (`sv_patients` is a clinical record; `sv_clients` is its owner). A wrong
  owner→patient grouping is a clinical-record misattribution, not a CRM
  annoyance.

### 3.3 The rule, and it is one this session has already shipped

The KX accumulator built earlier today took exactly this position for a federal
threshold, and the same sentence should be the platform rule:

> **Identity comes from a key, or the row is unattributed. A name is never a
> key, and an unattributed row gets its own bucket — never folded into somebody
> and never dropped.**

Folding invents history for a person who does not have it; dropping makes the
per-person figures sum to less than the real total with nothing saying so.

### 3.4 Unified view must GROUP, never MERGE

Two invariants, and the second is borrowed intact from
`roofing-consolidation.js` because it is the same arithmetic:

1. **Adding or changing a grouping must not change any individual record.** The
   job, the pet, the visit is untouched; only the view over it moves.
2. **Regrouping changes the buckets and must not change the grand total.**
   Carry `input_total`, `grand_total` and `reconciles` so a caller or a test can
   check that rather than trust it.

---

## 4. The model

Three levels, and today the platform has only the third:

```
  ORG            a customer that owns more than one site            <- GAP B, absent
   |
  LOCATION       a site: yard, branch, chapel, community, office    <- GAP A, absent in 3 of 5
   |
  RECORD         a slab, a visit, a charge, a case                  <- exists everywhere
```

And a second axis hanging off LOCATION, not off RECORD:

```
  ENTITY / BRAND   the legal entity or franchisee that owns the location
                   -- roofing's entity_id, SAIRNsenior's franchisee
```

Four rules, each already proven in a shipped file rather than proposed here:

1. **Stamp the one record that physically HAS the property; derive the rest.**
   (StoneDesk's slab; roofing's location.)
2. **`entity_id` lives on the LOCATION and nowhere else**, so moving a branch
   between entities moves its whole history. (Roofing.)
3. **`UNASSIGNED` and `UNKNOWN` are two different buckets, and neither is
   dropped.** *"One is assign the branch, the other is create the branch."*
   (Roofing.) A registry that no longer lists an id still has history under it.
   (Dental's `unregistered_location_ids`; StoneDesk's *"(yard not on this
   device)"*.)
4. **An unreadable source yields `null` and names itself, never `0`.**
   (`dnt-rollup.js`.)

---

## 5. Per-app scope for the five named apps

| App | What it needs | Size |
|---|---|---|
| **StoneDesk** | nothing for GAP A. It has the axis and the derived-attribution rule. It needs GAP B (an org above the licence) to serve a consolidating multi-branch fabricator — which its own gap-7 audit says is *"exactly the … fabricator that has the budget"* | — |
| **SAIRNsenior** | nothing for GAP A or the brand axis — it has **both**. Its `branch_id`/franchisee pair is the closest thing on the platform to roofing's two-axis model and was built independently | — |
| **SAIRNcare** | **capture only**: a `location_id` on resident, staff, incident and billing rows, stamped through `location-scope.js`. The UI's singular *"this facility"* language is the tell that nobody has asked the question | S–M |
| **SAIRNlegacy** | **capture only**, and it is the strongest business case of the three: funeral-home consolidators owning dozens of homes are the industry norm. Note `leg_facilities` is a *type* vocabulary and must not be overloaded into a location axis | S–M |
| **SAIRNgrounds** | **verify there is a customer who needs it before building anything.** No location concept exists and no evidence was found that one is wanted. Building attribution nobody asked for is the speculative work CLAUDE.md forbids | verify first |

**Client multiplicity (§3), separately:** StoneDesk and SAIRNvet need a stable
key where there is none; SAIRNsenior needs its `|| client_name` fallback
removed; SAIRNcare is already right and is the reference.

---

## 6. Sequencing, cheapest and highest-risk-reduction first

1. **The identity floor (§3).** Add a stable key where there is none and stop
   name-matching. Cheapest, largest risk reduction, and it is a **prerequisite**
   — a cross-location client view built on name-matching would merge two people
   across two sites instead of one.
2. **GAP A capture**, for whichever of SAIRNcare / SAIRNlegacy has a real
   customer. Attribution has a deadline; reporting does not. Through
   `location-scope.js`; no fifth implementation.
3. **GAP B, `org_id` above `license_hash`.** The structural one. Needs Michael:
   it changes what a licence means commercially, not only technically.
4. **GAP C, access partitioning.** Explicitly last, explicitly separate.

---

## 7. What would make this design wrong

Stated so it can be falsified rather than admired:

- **If a real customer needs location-scoped ACCESS and not attribution**, the
  sequencing above is backwards — GAP C would become first, and it is the
  largest.
- **If the five named apps' customers are all single-site**, GAP A is
  speculative work and only §3 survives.
- **If `org_id` is wanted mainly for consolidated REPORTING** rather than for
  shared operation, a far cheaper answer exists: an export that merges N
  licences offline, with no change to the tenancy model at all.

---

## 8. What this document does NOT decide

- Whether any specific customer needs any of it. Every item above is
  conditional on that and none of it should start without it.
- What `org_id` means commercially — one contract or several, one bill or
  several, who may add a site. **Michael's call.**
- Whether a location-scoped ROLE should exist, and what it can see.
- Any schema. No column, no migration and no resource name is proposed here;
  §4's rules constrain a design, they are not one.
- The SAIRNgrounds question, which is *"is there a customer"* and not
  *"how would we build it"*.

---

*Companion reading: `api/_lib/location-scope.js` (the shared stamp and the
two-axis finding), `api/_lib/roofing-consolidation.js` (the two-axis reference
and the reconciliation invariant), `api/_lib/dnt-location.js` (why capture has a
deadline and reporting does not), `sql/stonedesk_locations_schema.sql` (the
derive-don't-stamp rule), `docs/SAIRN-OPEN-WORK-INDEX.md:186` (the measurement
this builds on).*
