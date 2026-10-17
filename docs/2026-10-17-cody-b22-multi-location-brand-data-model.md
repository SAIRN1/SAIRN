# Shared multi-location / multi-brand data model — SCOPING, not design

**cody, b22, 2026-10-17.** No implementation. No new module. No edit to another
session's open-work row.

---

## 0. THE HEADLINE: THE DESIGN THIS DOCUMENT WAS CLAIMED TO PRODUCE ALREADY EXISTS, AND IT LIVES IN A CODE COMMENT

My b22 claim string says *"shared multi-location multi-brand **DATA MODEL
scoping** doc (no implementation)."* I took that on the strength of
`docs/SAIRN-OPEN-WORK-INDEX.md` **row 356**, which says in terms that item 4 —
*"a shared multi-location architecture plus its first implementation"* — is
**NOT STARTED**.

**It is started. It landed the day after that row was written, and row 355 —
one row below the one I read — says so.** `api/_lib/location-scope.js` landed
2026-09-16 (Hank) carrying the measurement, the design finding, the boundary
and the first migration. **The design document for this task is the 65-line
comment header of that module**, and it is better than what a fresh scoping
pass would have produced, because it was written against a measurement rather
than against the item name.

**So this document does NOT design anything.** It does four things that are
still worth doing:

1. **Re-derives what is actually built, against HEAD today** — not against the
   2026-09-16 claim. Every figure below carries the command that produced it.
2. **Names what the existing design does NOT cover** — and the largest item is
   that **the BRAND axis has no implementation anywhere on the platform**,
   while the item name has carried the word *multi-brand* throughout.
3. **States SAIRNfreedom's position**, which is the app I touched this batch and
   the one the claim pairs this doc with: it **cannot represent two locations or
   two entities at all**, and the `taxEntity` field I added in this same batch
   makes that limitation sharper rather than softer.
4. **Records two index statuses that have gone stale in OPPOSITE directions**,
   measured, and routes them rather than editing another session's cells.

**WHY THIS IS WORTH A DOCUMENT AT ALL, given the design exists.** A design that
lives only in a comment header inside one server module is reachable by anybody
who already knows to open that file. **Row 356 is what the next session reads,
and it says NOT STARTED.** I read it, believed it, and claimed a design task
that was done — which is the cost, measured on me, one batch after my own
memory note *"a handoff item may already be built"* was written about the same
failure shape.

---

## 1. WHAT IS BUILT, MEASURED AT HEAD TODAY

**All six suites green.** Exit codes read from `echo "EXIT=$?"` on its own
line, never from a pipeline:

```
EXIT=0  api/_lib/location-scope.test.js             7 arms
EXIT=0  api/_lib/dnt-location.test.js              12 passed
EXIT=0  api/_lib/dnt-rollup.test.js                30 passed, 0 failed
EXIT=0  api/_lib/roofing-consolidation.test.js     17 passed
EXIT=0  api/_lib/roofing-locations.test.js         17 passed
EXIT=0  api/_lib/roofing-locations-endpoint.test.js 29 passed, 0 failed
                                                  ---
                                                  112 arms
```

**`dnt-rollup` has moved 27 → 30 arms** since row 355 and row 449 both recorded
27. Not a problem; recorded because a quoted count is the thing that rots.

**THE CONSOLIDATION STILL HOLDS, and it is asserted rather than assumed.**
`grep -rn "DEFAULT_LOCATION_ID *=" api/_lib/*.js` (excluding `.test.js`):

```
api/_lib/dnt-location.js:44        = locationScope.DEFAULT_LOCATION_ID    delegates
api/_lib/roofing-locations.js:48   = locationScope.DEFAULT_LOCATION_ID    delegates
api/_lib/location-scope.js:69      = 'LOC-DEFAULT'                        THE ONE DEFINITION
```

Arm C of `location-scope.test.js` walks `api/_lib/` and asserts exactly one
file defines the literal; arm D asserts **the boundary** — the shared module
must not grow an entity, bucket or roll-up function, and its export list is
pinned. **Arm D is the most valuable arm in the file**, because adding a
roll-up there is a decision about which app's model wins, dressed as a refactor.

---

## 2. THE DESIGN FINDING, QUOTED RATHER THAN RESTATED

From `api/_lib/location-scope.js`:

> **So LOCATION and BRAND/ENTITY ARE TWO AXES, not one**, and roofing already
> models both while dental models one. Folding them together would either give
> dental an entity concept it does not have or flatten roofing's — and the
> platform-wide item names this work "multi-location/multi-brand" as though it
> were a single thing. **It is not.**

**That sentence is the answer to the question this document was claimed to ask,
and it was already written.** The two axes:

| axis | what it keys | reference implementation |
|---|---|---|
| **LOCATION** | which site a row happened at | `location-scope.js` stamp; `dnt-rollup.js` buckets per location |
| **BRAND / ENTITY** | which legal entity owns the site | `roofing-consolidation.js` — buckets per entity, `location → entity` as a mapping |

**AND THERE ARE THREE ROLL-UPS NOW, NOT TWO. The third is not named anywhere,
including in the module comment, and it is the only one that is not a query.**

| roll-up | axis | mechanism |
|---|---|---|
| `api/_lib/dnt-rollup.js` | per LOCATION | server read, one licence |
| `api/_lib/roofing-consolidation.js` | per ENTITY ← location | server read, one licence |
| **`sairnfreedom.html` `buildDistrictReport()`** | **per ENTITY** | **signed JSON export from each post, imported and verified at the district — ECDSA, `signPayload()` / `verifyPayload()`, one independent app install per entity** |

**The third shape crosses an INSTALL boundary where the other two cross a
`group by`.** SAIRNfreedom's district tier never queries another post's rows; it
receives a signed aggregate and verifies the signature. **That is a genuinely
different answer to "roll up across entities", and it exists because the
district has no right to the posts' records** — the design's own premise, stated
at `sairnfreedom.html` around the `buildDistrictReport()` header: *"the district
tier receives aggregates rather than filtering records."*

**NOT A PROPOSAL THAT THE OTHER TWO ADOPT IT.** A dental practice group and a
roofing franchisor own their locations' data; a VFW district does not own its
posts'. The mechanism follows the legal relationship, and that is the
observation worth carrying forward: **the roll-up shape is a function of who
owns the rows, not of how many axes there are.**

---

## 3. THE BRAND AXIS HAS NO IMPLEMENTATION. MEASURED

**`brandId` and `brand_id` appear ZERO times in all 22 `*.html` files.**

```
for f in *.html; do grep -c "brandId\|brand_id" "$f"; done     all zero
ls *.html | wc -l                                              22
```

The closest thing on the platform is `sen_franchise_agreements`
(`sql/sairnsenior_franchise_schema.sql:76`) — *"the agreement between the
franchisor and ONE franchisee"* — which row 355 correctly calls **the second
axis, not the first**. And `roofing-consolidation.js` models an **ENTITY**
layer, which is the same axis under a different word.

**SO THE ITEM NAME IS HALF-DELIVERED AND THE HALVES ARE NOT EQUAL.** What
landed 2026-09-16 is the **LOCATION** half: a shared constant, a shared cap, a
shared sentinel predicate, two migrated callers, a pinned boundary. **The BRAND
half has one app's entity model (`rf_entities`), one app's franchise table, and
no shared anything** — and `location-scope.js`'s own boundary arm *forbids* the
shared module from growing one, deliberately.

**THAT IS NOT A GAP TO CLOSE SPECULATIVELY, AND THIS IS THE SCOPING CALL.**
Writing a shared brand/entity module now would be choosing between
`rf_entities` and `sen_franchise_agreements` with **one** real customer shape
each — which is the exact error `location-scope.js` avoided by consolidating
only what **two** apps had independently built identically. **The precondition
for the brand half is a SECOND app that needs an entity layer, not a session
that has time.** Until then the honest state is: *two axes are named, one is
shared, the other has two disagreeing implementations and no pressure to
reconcile them.*

---

## 4. SAIRNFREEDOM CANNOT REPRESENT EITHER AXIS, AND THIS BATCH MADE THAT SHARPER

`sairnfreedom.html:2472`:

```js
function getPost(){ return ld(K_POST, { name:'', orgType:'', taxEntity:'',
  founded:'', entityId:'', locationId:'', city:'', state:'OH', ... }); }
```

**`entityId` and `locationId` are SCALARS on a single record.** There is no
`K_LOCATIONS`, no `getLocations()`, nothing stamps a location onto a member, a
ledger line, a bingo session or a disbursement. The app models **one entity at
one location**, and the note at `sairnfreedom.html:334` is the design saying so:
*"Entity and location are separate keys (spec 1b). An auxiliary that meets in
this building is a separate entity with its own treasury and officers — never
merged into this one."*

**KEEPING THE TWO KEYS SEPARATE WHILE BOTH ARE SCALAR IS THE RIGHT HALF OF THE
DESIGN AND THE CHEAPER HALF.** It means the day a post needs two locations, the
axis to make plural is already named and is not entangled with the entity.
`buildDistrictReport()` aggregates **entities, never buildings**, and
`sairnfreedom.html:7779` refuses the export without an `entityId` with exactly
that reason in the toast: *"the roll-up aggregates entities, not buildings."*

**AND THE FIELD I ADDED THIS BATCH MAKES THE LIMITATION LOUDER RATHER THAN
QUIETER, WHICH IS WHY IT IS RECORDED HERE AND NOT ONLY IN §13 OF THE TIPS
DOCUMENT.** `taxEntity` can be set to `'both'` — *a 501(c)(19) post AND a
501(c)(7) companion club* — and `taxEntityFacts()` says in terms what that
costs:

> `TWO EMPLOYERS: this app does not record which entity employs each tipped
> worker, and that decides whose return the employer-side figures land on.`

**So SAIRNfreedom now RECORDS a two-entity structure it cannot KEY ROWS BY.**
That is a deliberate asymmetry and it is the same asymmetry
`api/_lib/roofing-locations.js` argued for attribution: **capturing the fact has
a deadline, keying rows by it does not.** A post that tells us today it runs a
companion club can be asked which entity employs whom later; a post that was
never asked the structural question cannot have the answer reconstructed.

**AND THE STRUCTURE IS NOW VISIBLE RATHER THAN MERELY STORED.**
`sfRenderTaxFacts()` paints what the configured shape determines **and its
unknowns**, and the two-employer gap above is one of the rendered unknowns — so
the limitation is shown to the post that has it rather than recorded where only
a session reads it. **The reporter had ZERO CALLERS when it was first written**,
found by running Guardian 0d against my own diff in the same batch; the full
account, including the arm the ablation caught cheating, is §13.5 of
`docs/2026-09-17-sairnfreedom-tips-tax-treatment.md`.

**THE EXACT NEXT STEP, IF A POST EVER REPORTS `both` WITH TIPPED STAFF:** add
an `employerEntity` to the member/officer record — **not** a second scalar on
the post — because the question is per worker and a post-level field would
answer it wrongly for every post that has both. **Nothing should be built until
a real post reports that shape**, for the same reason the brand axis waits: one
customer's structure is not a model.

---

## 5. THE RESIDUE, EACH WITH ITS NEXT STEP

### 5.1 The four Postgres `DEFAULT 'LOC-DEFAULT'` and the `coalesce` — IRREDUCIBLE, and honestly so

Measured, `grep -rn "'LOC-DEFAULT'" --include=*.sql`:

```
sql/sairnroofing_billing_schema.sql:109    location_id text not null default 'LOC-DEFAULT'
sql/sairnroofing_billing_schema.sql:142    location_id text not null default 'LOC-DEFAULT'
sql/sairnroofing_locations_schema.sql:68   add column ... default 'LOC-DEFAULT'
sql/sairnroofing_locations_schema.sql:88   location_id text not null default 'LOC-DEFAULT'
sql/sairnroofing_billing_schema.sql:170,173,179   coalesce(p_location_id, 'LOC-DEFAULT')
                                                  inside rf_allocate_invoice_number
```

**A Postgres `default` cannot call a JS module.** Row 355 already says the
honest fix is a documented cross-reference rather than a pretence of
consolidation, and that is still right. **No action. Named so a later session
does not read 40 literal sites as an unfinished migration** — the JS constant
is defined once, which is what the consolidation claimed.

### 5.2 `isDefaultLocation()` WAS ADDED FOR TWO UI SITES THAT CANNOT REACH IT

This one is a real, cheap finding and it is new here.

`location-scope.js:110` states the function's own reason:

> Added here rather than copied a third time: `sairnroofing.html` asks this
> question inline twice (`id==='LOC-DEFAULT'`), and a UI that hardcodes the
> sentinel is the next place the constant drifts.

**Both sites still hardcode it**, measured at HEAD:

```
sairnroofing.html:3292   el.value=(selected&&selected!=='LOC-DEFAULT')?selected:'';
sairnroofing.html:3298   if(!id||id==='LOC-DEFAULT')return 'Main';
```

**And they cannot stop.** `location-scope.js` is a CommonJS server module;
`sairnroofing.html` is a single-file browser app with no module loader and no
build step. **There is no path from that UI to that function.** Arm E of
`location-scope.test.js` passes, and what it proves is that the function works
— **not** that anything uses it. **An arm whose stated purpose is "a UI
hardcoding the sentinel is where the constant drifts next" does not check any
UI.**

**NOT A DEFECT IN THE ARM, and I am not re-aiming somebody else's suite.** The
function is correctly placed for the next SERVER caller. **The next step is a
decision, not a fix:** either (a) accept the two client literals permanently and
say so in a comment at both sites, or (b) have the locations endpoint return a
`is_default` boolean per row so the client never compares the sentinel. **(b) is
the one that makes the arm's stated reason true**, and it is a small endpoint
change in `roofing-locations` — routed, not taken, because `api/` is HANK'S this
batch and read-only here.

### 5.3 StoneDesk: attribution exists in JSONB; access partitioning does not

Row 355 carries its own correction on this and the correction is the useful
part: a first pass concluded nothing stamps a location onto a StoneDesk row,
because it grepped for a `location_id` **column**. **The value lives inside
`sd_slabs.data` jsonb** — `sql/stonedesk_locations_schema.sql:92` says so in
terms — and `stonedesk.html` filters and buckets by it. Re-derived today:
`location_id` / `locationId` appear **12** times in `stonedesk.html`, and
`sql/stonedesk_locations_schema.sql:9` records the audit's own zero counts as
the thing that was misread.

**THE SLAB IS THE ONLY RECORD THAT CARRIES A LOCATION, DELIBERATELY** —
quotes, jobs, POs and remnants derive theirs, because stamping a yard at
creation would freeze it and leave moved work attributed to the old yard. **No
action. Access partitioning is still not built** and is the same decision as
§5.4.

### 5.4 Location-as-access-boundary — a RECORDED DECISION, not a backlog item

`api/_lib/roofing-locations.js:20`:

> Decision recorded 2026-08-25 (Michael): location-as-access-boundary is **NOT**
> built yet. It is real work, harder to reverse, and it interacts with the
> existing tiers in exactly the shape of the SAIRNsenior bug where one branch
> checked management-only where it should have checked broad-read. **It deserves
> a real multi-location customer to design against rather than a guess now.**

**A session that picks this up has misread it.** Quoted in full here because the
reason is the load-bearing part and a one-line summary of it reads like a to-do.

---

## 6. TWO INDEX STATUSES HAVE GONE STALE IN OPPOSITE DIRECTIONS. MEASURED, ROUTED, NOT EDITED

**Neither cell is mine, and re-wording another session's open-work row to carry
my own answer is the edit this platform has least tolerance for.** Both are
recorded here with the measurement, and routed in the handoff.

### 6.1 Row 356 says item 4 is NOT STARTED. Row 355 says it is DESIGNED AND FIRST-MIGRATED

Both rows are Hank's, written **one day apart** — 356 on 2026-09-15, 355 on
2026-09-16 — and **355 is the later and the correct one.** Nothing is wrong with
either row as written; what is wrong is that **356 is read first and 355's
correction is not visible from it.**

**This cost me the premise of this batch's claim**, which is the only reason it
is worth writing down rather than shrugging at. **Suggested fix, for whoever
owns row 356: one clause in its item-4 sentence pointing at row 355.** Not a
rewrite — the sentence was true when written.

### 6.2 Row 449 says `dnt_rollup` has NO CALLER. It has one

Row 449's amendment (2026-09-17, CC) is built on a measurement: *"`dnt_rollup`
appears 0 times in `sairndental.html` and 0 times in every `.html` file in the
repo — NO PANEL, NO NAV TARGET, NOTHING SENDS IT."* **That was true then and is
false now.** Re-derived at HEAD:

```
sairndental.html:2543   var b=await sdnData('read','dnt_rollup',{});     A REAL CALLER
sairndental.html:2549   var why=dntLastErrText('dnt_rollup');            its error path
sairndental.html:1125,1144                                              prose, not calls
sairncare.html:3605     // dnt_rollup, with money attached              a comment
```

**One real call site, with an error path beside it.** The row's "NEEDS A
DECISION, NOT AN ESTIMATE — either a panel or a written deferral" was answered
by somebody building the panel. **I did not verify the panel is reachable from
the nav**, and I am not claiming it is complete — only that the row's stated
measurement no longer holds. **Routed to CC, whose amendment it is.**

**THE SHAPE BOTH OF THESE SHARE, and it is cross-domain item 8 exactly:**
nothing announces the day a status row stops being true. 356 was overtaken in
**one day**; 449 in under a month. **Both were measured when written and neither
re-measures.** The cheap mechanical form, if anybody wants it: a row whose
status cell quotes a count or a zero (*"appears 0 times"*, *"7 arms"*, *"27
arms"*) is a row a tool could re-derive — and three of the counts I checked
today had moved.

---

## 7. WHAT THIS DOCUMENT DELIBERATELY DOES NOT DO

- **No multi-location or multi-brand implementation.** No shared module, no
  `location_id` added to any app, no endpoint change. **The claim this document
  answers said *scoping*, and this is scoping.** The same batch DID implement
  the SAIRNfreedom `taxEntity` field, its reporter `sfRenderTaxFacts()` and
  `tests/sairnfreedom_tax_entity_facts.js` (26 arms, exit 0) — that is the
  claim's OTHER half, §4 is where the two meet, and nothing in it makes either
  axis plural.
- **No shared brand/entity module.** §3 is the argument for why that is the
  right call and not an omission.
- **No edit to `api/`, `sql/` or `tools/`.** `api/sd-data.js` is HANK'S this
  batch and was read only.
- **No edit to rows 355, 356 or 449.** §6 routes them.
- **No re-aim of `location-scope.test.js`.** §5.2 routes the decision its arm E
  depends on.
- **No §45B figure.** `SEC45B_LIMBS` reports two floors with the Form 8846
  sentence each came from; nothing computes a credit, and §7.3 of
  `docs/2026-09-17-sairnfreedom-tips-tax-treatment.md` says not to build toward
  one.

---

*cody b22, 2026-10-17. Every count above was re-derived at HEAD this session
rather than quoted from the row that recorded it, and three of them had moved.*
