# leg_aftercare Tier A — the preservation argument does not cover the rows that matter

**fourth / b24 item 1, 2026-10-15.** Discharged: `cody 2026-10-15T01:18:14Z`
(`leg_aftercare`), reviewer **fourth, not cody**, as that record requires. The
full verdict is in `docs/tier-a-reviews.json` on that record; this file is the
routable summary with `file:line`.

**THE CARVED-OUT HALF OF `hank 2026-10-15T01:21:13Z` IS REVIEWED HERE TOO.**
That record was discharged in b23 with `leg_aftercare` and `leg_cases`
explicitly listed in its body as NOT reviewed, deferred by Michael's decision.
Both conditions are now met and the review is done. **The register cannot carry
it: `tier_a_review_gate.py` has no `--amend` and no append, so a record
discharged with a carve-out has nowhere for the carve-out's later completion to
land. ROUTED TO cc as a tool gap.**

Driven: `node <scratchpad>/leg_aftercare_drive_b24.js` → log
`leg_aftercare_drive_b24.log`. Both halves extracted **by text** from the
shipped files and run in a `vm` against a fake `localStorage` — the method
hank's own b12 suite adopted. Nothing retyped; the live tree was never written.

---

## What HOLDS, established rather than accepted

* **The only creation path uses three literal types** —
  `sairnlegacy.html:4302`, `plan = [{type:'1 Week'},{type:'1 Month'},{type:'1 Year'}]`
  — and the case id comes from the `$('accase')` select of existing cases.
* **`newId('CS')` is `^CS-[0-9]+-[0-9]+$` for every value it can produce** —
  `sairnlegacy.html:1561`, `prefix + '-' + Date.now() + '-' + Math.floor(Math.random()*1000)`.
  The random segment is 1–3 digits and the regex accepts any width, so the
  historic branch is taken for every `newId('CS')` case id. **Checked, because a
  fixed-width regex would have been the defect.**
* **Both derivations agree on a shipped pair**, driven: server
  `AC-CS-1760000000000-42-1-WEEK`, client the same string.
* **`api/leg-aftercare-key-unambiguous.test.js` → exit 0, 14 passed / 0 failed.**
  **That green is not evidence against F2–F4:** it tests the derivation's
  preservation property, which holds. F2–F4 are about rows whose id was never
  derived, and about the local merge.

---

## F1 — cody's. THE PROBE CANNOT RUN AT HEAD. It fails closed, which is right, but ARM 1 is UNRUN rather than RED

    PYTHONIOENCODING=utf-8 python -u tests/run_b14_leg_aftercare_probe.py
    -> EXIT=3
    "COULD NOT RUN: the `const acKey = 'AC-' ...` derivation was not found in
     api/sd-data.js, so the server half could not be extracted. Nothing was
     verified."

hank's fix replaced the server derivation, so cody's extraction anchor no longer
matches. **The probe does the right thing** — PR §1.11's third state, the
opposite of the failure mode it was built to catch.

**But `docs/known-red-suites.json` now describes a state that does not exist:**
its entry for this file records `exit_code: 1` and
`expected_red_scope: "ARM 1 ONLY. Any other failure in this suite is NEW."`
**An exit 3 is neither**, and the scope sentence cannot classify it.

**NEXT STEP (cody):** re-anchor the server-half extraction on the two-form
derivation — the anchor to use is `const acEsc = (s) =>` plus the `acKey`
ternary that follows, `api/sd-data.js:15870-15878` — then re-drive and move the
row to `recovered` or re-diagnose it with the exit code it actually has.
**And add a third control while re-anchoring: an arm that FAILS when the
extraction anchor stops matching**, so the next refactor produces a red arm
rather than an exit 3 nobody is looking for. The probe's ARM 2 covers exactly
this class for a different anchor; it does not cover its own.

**cody's criticism of E4 is CONFIRMED, not accepted.**
`api/sd-data-leg-role-matrix.test.js:456-478`: its `cases` list literally
contains both `['CS-7','1 Week']` and `['CS-7-1','Week']`, and its assertion is
`disagree.length === 0` — *"the CLIENT's `legAftercareId()` and the SERVER's
derivation produce the same key for every case tried"*. **So E4 drives the
colliding pair and passes, because both halves agree on the wrong answer.** A
cross-implementation test is necessary and not sufficient. ARM 1's two controls
— liveness, and not-everything-collides — are what make it trustworthy.

---

## F2 — hank's, HIGH. Rows written by shipped builds DO change id, and hank's own code says so

The question *"prove no row any shipped build could have written changes key"*
is the wrong shape, and that is the finding. **The derived key is stable for
every shipped pair. The row's id is not**, because rows written before the
deterministic-id change never had a derived id at all — they carried
`newId('AC')`, e.g. `AC-1759999999999-7`. And `api/sd-data.js` rewrites
`payload.id` on **every** `leg_aftercare` write carrying both fields
(`:15872-15884`), so completing an old check-in lands on `AC-CS-…-1-WEEK`, a
**different row**. Driven: `SAME ROW? false`.

**hank's code already knows this** — `sairnlegacy.html:4358-4360`:
*"an old-page device's existing row has a RANDOM id, so completing it is exactly
the write the server canonicalises"* — and `legAdoptServerId` exists to rename
the local row afterwards.

---

## F3 — hank's, HIGH. The server-side orphan is never removed, which reintroduces the duplicate the key exists to prevent

`legAdoptServerId` repairs the **local** store. **Nothing repairs the server.**
`legServerWinsMerge` (`sairnlegacy.html:5474-5500`) only **adds** server rows
(`local.push(row)`) or overwrites a matching id; it never deletes a local row
the server lacks, and nothing deletes the stranded server row. Driven, with the
server holding both rows for one `(case_id, checkin_type)` pair:

    after hydrate the device holds 2 row(s):
      AC-1759999999999-7             status=Pending    notes=""
      AC-CS-1760000000000-42-1-WEEK  status=Completed  notes="family declined…"
    ** THE COMPLETED CHECK-IN REAPPEARS AS A SECOND PENDING ROW. **

That is a duplicate grief-support follow-up to a bereaved family — the exact harm
`sairnlegacy.html:4308-4310` names as the reason the deterministic key exists.

**NEXT STEP (hank):** the canonicalising write must also **delete the row id it
replaced, server-side, in the same request** — the server is the only place that
knows both ids. A client-side delete cannot be trusted here: the device that
would need to issue it is the one still on the old page.

---

## F4 — hank's, MODERATE-TO-HIGH. `legAdoptServerId` is a whole-row replace and loses data the kept row has

When a canonical row already exists the code does `keep[at] = mine` — **the
pre-existing canonical row is replaced wholesale**, so any field present only on
it is gone. Driven on exactly the precondition the function's own comment names
(*"a device that hydrated the canonical row and still has its own random one"*):

    before: the canonical row carries notes "family declined a visit"
    after legAdoptServerId, 1 row:
      AC-CS-1760000000000-42-1-WEEK  status=Pending  notes=""  completed_date=""
    ** DATA LOST **

**And it propagates:** the renamed row is the local row, and the next push sends
it — so a completion recorded on device A, with the family's note, is reverted
to Pending with an empty note by device B merely syncing.

**Controls driven, so this is not a hostile-fixture artefact:** ids equal → store
unchanged; no local row with that id → store unchanged. Both hold, so the
function's guards work and the loss is in the merge and nowhere else.

**NEXT STEP (hank):** the renamed row should win **only on the fields this write
set**, and the canonical row keep everything else. That field list is knowable —
it is the payload the write just sent — and it is **not currently passed in**.
`Object.assign({}, canonical, mine)` is *not* the fix: `mine` carries
`notes:''` and `status:'Pending'` as real values.

---

## NOT CHECKED — stated as gaps

* **Whether any `leg_cases` row can carry a case_id that is not `newId('CS')`
  shape.** An import path or a hand-typed id would send its aftercare rows down
  the `ACX-` branch. I did not enumerate every `leg_cases` writer. **If one
  exists, F2 widens from "pre-change rows" to those rows too.**
* **The real production rows.** No production read, so *"rows written before the
  change exist"* is an inference from the code's own comment at `:4358-4360`
  saying they do, not an observation.
* **The full HTTP round trip.** The server derivation was extracted and run, not
  reached through a request.
