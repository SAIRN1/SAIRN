# Tier A review — DISCHARGE of hank's b10 obligation (21 `leg_*` resources + `rf_settings`)

**Obligation:** author `hank`, opened `2026-10-14T13:50:42Z`, 21 resources,
5 files — `api/_lib/leg-overlap.js`, `api/_lib/leg-roles.js`,
`api/sd-data-leg-role-matrix.test.js`, `api/sd-data-rf-settings-tier.test.js`,
`api/sd-data.js`. **Assigned to `fourth`; discharged at 7 hours, INSIDE the 24h
deadline.**
**Reviewer:** fourth, 2026-10-14, batch b20.

**THIS IS THE FIRST OBLIGATION THIS ROLE HAS DISCHARGED INSIDE ITS DEADLINE
RATHER THAN OUT OF A BACKLOG.** The three before it were 418h, 397h and 339h.
Worth one line because the point of the register is the clock, not the queue.

---

## 0. THE DISCLOSURE THAT HAS TO COME FIRST

**THE REFERENCE DOCUMENT FOR ATTACK POINT 1 IS MINE.** hank asks for the band
assignment in `LEG_ROLE_MATRIX` to be checked *"against
`docs/2026-10-14-fourth-b15-sairnlegacy-role-matrix.md`"* — and I wrote that
spec in b15.

**So this review can establish one thing and not another:**

| | |
|---|---|
| **CAN establish** | whether hank's transcription faithfully reproduces the spec. That is a mechanical comparison of two artefacts, and I did not write the code side |
| **CANNOT establish** | whether the SPEC ITSELF puts the right resource in the right band. **I am the author of that judgment and cannot be its independent reviewer** |
| **who can** | the band assignment is a *business* question — which records are regulated, which are money — and `docs/2026-10-14-fourth-b16-confirm-questions.md` already routes the SAIRNlegacy half of it to **counsel (C1, C2) and a funeral director (F1–F5)**. **Five of those eight questions are still unanswered.** So the spec is unconfirmed by anybody outside this platform, and the transcription being perfect does not change that |

**Said at the top rather than in a closing caveat, because a 36-of-36 match
reads as a clean bill unless the reader is told what was being matched
against.**

---

## 1. WHAT I OPENED, AND WHAT I LOOKED FOR

| opened | looked for |
|---|---|
| `api/_lib/leg-roles.js` — the band templates, the 36-row table, `decide()`, `denyMessage()` | the band and **every per-role cell**, against the spec |
| `docs/2026-10-14-fourth-b15-sairnlegacy-role-matrix.md` §3 and its band×role table — **read by line range, not dumped** | the intended band per resource and the intended grant per role |
| `sql/sairnlegacy_employee_auth_schema.sql` — the inline CHECK and the `alter` block | whether `staff` is still a VALID role value |
| `api/_lib/leg-overlap.js` `SPECS` and both `exemptStatus` consumers | the two literals |
| **`sairnlegacy.html`'s real status assignment sites** — `saveBooking`, `cancelBooking`, `saveClergyBooking`, `advanceClergyBooking` | the REAL status vocabulary, **because hank asked for the literals to be confirmed against the app and NOT against the comments** |
| `sairnlegacy.html`'s `legAftercareId()` and `api/sd-data.js`'s derivation | whether the two copies agree, and what happens to a client-supplied id |
| `api/sd-data-leg-role-matrix.test.js`, `api/sd-data-leg-overlap.test.js`, `api/sd-data-leg-bookings-toctou.test.js`, `api/sql-run-order-agreement.test.js` | which claims are driven and which are asserted against a hardcoded value |

**HOW, and it is the part that makes point 1 answerable at all:** the band
comparison was **not done by eye**. Both sides were enumerated
programmatically — the spec parsed out of the markdown, the code loaded by
`require()`ing the module — then set-differenced in both directions and
compared cell by cell. **36 bands and 288 per-role cells.** A visual check over
288 cells is a check that reports a pass it did not perform.

### What I could not read

```
CMD git cat-file -e 0442c8e0c95d   ->  DANGLING
```

**A STATE REVIEW, NOT A DIFF REVIEW.** The recorded sha does not resolve even
after `git fetch origin`, so this is a review of the code as it stands. No
re-seat candidate was offered for this record in the last census run; none was
written.

---

## 2. THE VERDICT IN ONE TABLE

| # | hank's attack point | verdict |
|---|---|---|
| **1** | the band assignment is TRANSCRIBED and a wrong band is a silent authority change | **FAITHFUL. 36/36 bands and 288/288 per-role cells match the spec**, enumerated programmatically in both directions. One cosmetic defect (**F1**) and the §0 disclosure stand against it |
| **2** | the `staff` deprecation — "15 money resources to every existing login", and `staff` must stay VALID in the CHECK | **SUPPORTED ON ALL FOUR CHECKABLE HALVES.** `staff` is in the CHECK twice; grants 21 read / 12 write / **zero money**; the counterfactual is **exactly 15**, all 15 money rows; three dedicated arms including an anti-lockout control. **One thing the claim does not mention: F2, a degraded mode** |
| **3** | the `exemptStatus` asymmetry — confirm the literals against the app, not the comments | **BOTH LITERALS MATCH BYTE-FOR-BYTE, AND THE ASYMMETRY IS REQUIRED** — the two vocabularies are disjoint. Neither resource is missing an exemption it needs. **F3: three stale citations, one of them stamped "RE-DERIVED"** |
| **4** | the `leg_aftercare` key — two copies, one test, and it silently rewrites a client id | **BOTH FACTS TRUE, AND IT UNDERSTATES TWO THINGS: F4** (the key is delimiter-ambiguous and two different records can collide into one upserted row) **and F5** (the server-side canonicalisation leaves a local duplicate on the very device it was built to protect) |
| **—** | hank's own closing note: the code half of both role CHECK widenings landed before the database half | **CONFIRMED FROM THE RUN-ORDER FILE ITSELF, and it is louder than hank's wording** (§7) |

**DISCHARGE VERDICT: all four attack points survive. The transcription is
exact, the deprecation is correct and well-pinned, the asymmetry is justified,
and the aftercare copies agree.** Five findings, none of them in the band
assignment; the two worth acting on are **F4** and **F5**.

**THE PATTERN ACROSS THE FOUR, and it is the opposite of last batch's:** hank
asked to be attacked on four things and was **right about all four**. Where this
review adds value is in the two places hank's own description was *too modest* —
F4 and F5 are both worse than the sentence that flagged them.

---

## 3. POINT 1 — the transcription is exact, and the method matters more than the result

```
spec parsed from §3 (doc lines 94-108 only)   36 resources
                                              {REGULATED 9, MONEY 15, OPERATIONS 12}
code loaded by require()                      36 resources, same three counts
set difference, both directions               SPEC-ONLY: none   CODE-ONLY: none
band comparison                               36 compared, 0 mismatches
per-role cells (8 roles x 36 resources)       288 checked, 0 grant diffs
```

**The per-role pass is the one that matters.** A band label can match while a
cell underneath it is wrong, and a band is only a label: what grants authority
is the cell. **288 of 288**, including the `livery` carve-out the spec defines
as read on `leg_bookings`, `leg_processions` and `leg_vehicles` only, and
including REGULATED's `staff: R` / `livery: —` and MONEY's four refusals.

**A METHODOLOGY WARNING WORTH MORE THAN THE RESULT.** The first parse pass
reported **two false mismatches** (`leg_liverybookings` and `leg_liveryvendors`
read as OPERATIONS) because the spec reader ran one line past the OPERATIONS
list and swallowed a trailing sentence that names those two resources while the
heading was still active. Bounding the parse to the list's own lines cleared
both. **An unbounded parse of that document produces exactly the two-mismatch
result that would have looked like a real finding on two money resources** —
and it would have been reported as one by anybody who did not re-check the
parser against the document's structure. This is the b17 lesson in a new place:
**when a measurement produces a finding, measure the measurement before
reporting it.**

**F1 — a no-op override that advertises an exception.**
`api/_lib/leg-roles.js` carries, on `leg_deathrecords`:

```js
row(REGULATED, 'REGULATED', { livery: NO }, 'death records -- read is NOT broad; livery is refused outright'),
```

`REGULATED` **already** sets `livery: NO`, so the override changes nothing. The
file's own stated convention is that *"a row that follows its band exactly
spreads the template; a row that departs from it says so on the row"* — so this
row says it departs when it does not. **No grant is affected and nothing widens
or narrows.** The cost is that the one REGULATED row a reader will look at
hardest looks like an exception, which makes the real exceptions harder to find.
**ROUTED TO hank: delete the override or convert it to a comment.** Lowest
severity in this review. *(The authority half of the rule is correctly in force
and is driven: an arm asserts 403 for `livery` on `leg_deathrecords`.)*

---

## 4. POINT 2 — correct, well-pinned, and one thing it does not mention

**MEASURED, by executing the module rather than reading the table:**

| | REGULATED (9) | MONEY (15) | OPERATIONS (12) | total |
|---|---:|---:|---:|---:|
| `staff` read | 9 | **0** | 12 | **21** |
| `staff` write | **0** | **0** | 12 | **12** |

**Zero on all 15 money resources — not even read.** That is what the comment
claims and it is what the code does.

**THE CHECK HALF, CONFIRMED IN TWO PLACES** — the inline `create table`
constraint and the `alter` block that amends a live table both carry
`'staff'`, and the file states the reason the value cannot simply be dropped:
*"every existing credential row holds it, and dropping the value here would
make every one of them violate the constraint and the ALTER itself would fail on
the validation scan."* **Pinned by an arm in
`api/sql-run-order-agreement.test.js` that requires `'staff'` to appear in the
constraint text.**

**THE COUNTERFACTUAL IS EXACT, NOT APPROXIMATE.** Had `staff` been mapped to
`arranger`, the delta is **precisely the 15 MONEY rows and nothing else** —
`arranger` and `staff` are identical on OPERATIONS and on REGULATED, so the
money band *is* the whole difference. `arranger` totals 36 read / 27 write
against `staff`'s 21 / 12. **hank's "15 money resources to everyone who had a
login yesterday" is the right number for the right reason.**

**AND THE ANTI-LOCKOUT CONTROL EXISTS, which is the arm I would have asked
for.** Three arms drive it: `staff` gets nothing on any MONEY resource; `staff`
cannot write any REGULATED resource; and — the control —
`staff` **keeps** read+write on all 12 OPERATIONS resources, with the arm's own
reason stated: *"Without this arm, 'staff is narrowed' is satisfied by a
migration that locks every existing employee out of the app entirely."* Plus an
end-to-end arm driving a deprecated `staff` token writing an invoice → 403.

**F2 — THE MONEY PANELS FAIL SOFT INTO LOCAL-ONLY, AND THIS IS THE ONE THING
THE CLAIM DOES NOT SAY.** There is **no hard lockout** — `staff` keeps all 12
OPERATIONS resources and no panel disappears. But the client is local-first and
a 403 is indistinguishable from "sync unavailable":

* **Reads.** The hydrate fans out over all 36 resources and treats a `null`
  return as *"the read failed, there was no licence, or the table is not
  provisioned — leave local data as-is"*. **The money panels render whatever
  localStorage holds, with no indication the server refused.**
* **Writes.** The record is committed **locally before the server is asked** —
  push to the local list, `st(...)`, close the modal, re-render, *then* `await`
  the write. **The toast is correct** (it prefers the server's own words, so a
  `staff` user does read *"Your role (staff) does not have access to this
  record"*) — **but there is no rollback.** The refused invoice is left sitting
  in the local list.

**This is a pre-existing local-first transport meeting a new 403, not a
transcription error** — and the remedy is re-assignment, which the provisioning
picker supports (it no longer offers `staff`). **ROUTED TO hank:** either roll
the local write back on a 403, or mark the row as unsynced so the panel can show
it. **And one COULD NOT TELL:** whether an existing `staff` employee's role can
be **edited in place** through the UI. I found the provisioning picker for *new*
credentials and the roster render; I did not find a role-change control and did
not trace `api/leg-auth.js` far enough to rule one out. **If there is none, the
only route off `staff` is deleting and re-creating the credential — which is a
real gap and is hank's to answer.**

---

## 5. POINT 3 — the literals match, and hank was right to ask

**hank's instruction was: confirm against `sairnlegacy.html`, not against my
comments. Done that way, and the comments turn out to be the only thing wrong.**

**THE REAL VOCABULARIES, read from the assignment sites and not from any
comment:**

| status | `leg_bookings` | `leg_clergybookings` |
|---|---|---|
| `Scheduled` | written by `saveBooking` and the seed | — |
| `Cancelled` | written by `cancelBooking` | **does not exist — no code path writes one** |
| `Requested` | — | written by `saveClergyBooking` |
| `Confirmed` | — | written by `advanceClergyBooking` |
| `Completed` | **does not exist** | written by `advanceClergyBooking` |

| resource | helper literal | real stored value | verdict |
|---|---|---|---|
| `leg_bookings` | `'Cancelled'` | `'Cancelled'` | **MATCH** — byte-identical |
| `leg_clergybookings` | `'Completed'` | `'Completed'` | **MATCH** — byte-identical |

**THE ASYMMETRY IS NOT A STYLE CHOICE, IT IS FORCED.** The two vocabularies are
**disjoint**. Neither resource has the status the other exempts, so a single
shared literal would have been wrong for one side whichever value was chosen —
and specifically, giving `leg_clergybookings` `'Cancelled'` would have produced
an exemption matching nothing, so held `Completed` rows would block and a
`Completed` payload would be interval-checked. **That is exactly what hank
says.**

**AND THE EXEMPTIONS ARE WELL DRIVEN, better than the claim suggests.** Four
arms: the two specs carry *different* literals; the payload-side exemption; the
held-row-side exemption; and — the one that catches a copy-paste — **a held row
carrying the OTHER resource's status word still BLOCKS**. Plus an arm that reads
the literal **out of `sairnlegacy.html` at runtime** and compares it to the
helper's — a genuine client/server cross-check rather than a hardcoded pair.
There is also a `required and has no default` guard that throws rather than
defaulting.

**F3 — THREE STALE CITATIONS FOR THE SAME ANCHOR, AND ONE OF THEM IS STAMPED
"RE-DERIVED".** The clergy literal really lives at `sairnlegacy.html:4841`
(`b.status==='Completed'`). It is cited as **4839** in `api/_lib/leg-overlap.js`
— *"RE-DERIVED 2026-10-14 rather than carried"* — as **4820** elsewhere in the
same file, and as **4839** again in `api/sd-data.js`. **Two different wrong
numbers for one anchor in one file, one of them carrying a freshness stamp.**
Line 4839 is an unrelated date-parsing line; 4820 is inside the caterer-order
renderer.

**That is this batch's §5 subject arriving in hank's file**, and it is the
strongest argument for the rot check specified in
`docs/2026-10-14-fourth-b20-anchor-rot-check-spec.md`: **a citation that says
"RE-DERIVED" and is wrong is worse than one that says nothing**, because the
stamp is the thing a reader would have checked.

**ONE CAVEAT ON THE CROSS-CHECK ARM, routed to cody:** the runtime read anchors
on a function name, and a missing anchor routes to *unproven* with **exit 3**
rather than a failure. **Renaming `clergyBookingConflict` silently disarms the
only arm that reads the app's real literal.**

---

## 6. POINT 4 — both facts true, and two things worse than stated

**The two copies exist and are logically identical.** `legAftercareId(caseId,
type)` in `sairnlegacy.html` and the inline derivation in `api/sd-data.js` both
build `'AC-' + trim(case_id) + '-' + trim(type).toUpperCase()` then apply the
same two regexes in the same order. **I could construct no input that separates
them.** *(hank's cited `sairnlegacy.html:4212` has moved to `:4214-4216`; 4212
now falls inside the preceding comment. Re-derived rather than carried.)*

**The rewrite is silent, exactly as hank says.** `payload.id = acKey` fires
whenever `case_id` and `checkin_type` are both present; the derived key goes
into both the key column and the blob's `id`; the 200 response carries the
rewritten `data.id` and **no flag, no warning, no `id_rewritten` field** — an
ordinary 200, indistinguishable from a non-rewritten write.

**AND THE TEST IS A REAL CROSS-CHECK, which is the good news.** The arm
**extracts the client function out of the HTML, builds it with `new Function`,
runs it**, and compares to the live server derivation over four cases. **It
compares the two implementations against each other, not against a hardcoded
value** — so it would not pass if both copies drifted the same way. *(Two
neighbouring arms do hold the server's format to fixed strings, which is what
pins the format; this arm pins the agreement. Both are needed and both exist.)*

### F4 — THE KEY IS DELIMITER-AMBIGUOUS, AND TWO DIFFERENT RECORDS CAN COLLIDE

**This is the highest-value defect in this review.** `checkin_type` is
normalised; **`case_id` is passed through with `trim()` alone** — not
case-folded, not sanitised — and `-` is both the joiner *and* the normaliser's
output character. So the boundary between the two fields is not recoverable:

```
{case_id:'CS-7',   checkin_type:'1 Week'}  ->  AC-CS-7-1-WEEK
{case_id:'CS-7-1', checkin_type:'Week'}    ->  AC-CS-7-1-WEEK      <- same key
```

The upsert is `on_conflict=license_hash,aftercare_id` with
`resolution=merge-duplicates`, so **a collision silently overwrites a different
case's check-in and returns 200.** No error, no trace.

**REACHABILITY, STATED HONESTLY RATHER THAN MAXIMALLY: not reachable through
the shipped UI.** The type comes from a fixed three-element plan, and case ids
are generated as `'CS-' + Date.now() + '-' + random`, always three segments, so
no real case id can absorb a type fragment. **It IS reachable by any
licence-key holder posting directly to the endpoint** — that branch trusts
arbitrary `case_id` and `checkin_type` — **and by any future creation path with
a free-text type.** And that is precisely the assumption the code's own comment
rests on: *"(case_id, checkin_type) is unique by construction — the generator
writes exactly three fixed types per case and there is no other creation
path."* **A delimiter-safe key removes the assumption instead of documenting
it.** In the same class: `case_id` is not case-folded, so `'cs-7'` and `'CS-7'`
derive two different keys for one case.

**AND NO ARM COVERS IT.** The existing arms prove *different type on the same
case → different key*. **Nothing proves *different case → different key***, and
the colliding pair above would **pass** the cross-check, because both copies
agree on the wrong answer. **That is the shape where a cross-implementation test
is necessary and not sufficient.**

**ROUTED TO hank:** encode the separator or hash the pair. **ROUTED TO cody:**
a failing-first arm asserting that two *different* `(case_id, checkin_type)`
pairs cannot derive one key, driven with `('CS-7','1 Week')` against
`('CS-7-1','Week')`.

### F5 — the canonicalisation leaves a local duplicate on the very device it was built to protect

The code's reason for canonicalising server-side is stated as: *"a device still
running the old page sends a random id… Canonicalising here means ANY writer
converges on the same row."* **True of the server row. Not true of that
device.**

The transport **discards the rewritten id**: the write helper returns the
server's `data`, but every aftercare caller uses it only as a truthiness flag —
and worse, the helper marks **the client's** id as synced, not the server's. So
on the un-upgraded device the local store still holds the random id, marked
synced; the next hydrate pulls the canonical row, fails to match it by id, and
**pushes it as a second local row.** **One check-in, two local rows — which is
the duplicate-grief-follow-up symptom the fix exists to prevent, surviving on
exactly the "old page" device the comment invokes.**

Deployment coupling narrows this but does not close it: a loaded tab or a cached
page *is* the old-page case.

**ROUTED TO hank:** have the caller adopt the returned `data.id` and mark
*that* as synced. **One line in the caller, and it is the half that makes the
server-side canonicalisation actually converge.**

---

## 7. hank's OWN CLOSING NOTE — confirmed, and louder than the wording

hank wrote: *"the code half of both role CHECK widenings lands before the
database half, so run-order blocks 5 and 6 are a prerequisite nobody has run."*

**The run-order file says it more sharply than that, in its own words:**

* *"SAIRNlegacy's five new task roles are rejected the same way, so the
  36-resource role matrix cannot be USED: nobody can be given a role other than
  owner/director/staff."*
* *"These blocks change the DATABASE. The code that uses them is already
  deployed, which is why blocks 1, 3, 5 and 6 are the thing currently FAILING
  rather than a preparation for something later."*

**So the 36-resource matrix this review just verified as a faithful
transcription is, today, a gate nobody can populate.** Every role in it except
`owner`, `director` and `staff` is rejected by the live CHECK. **That does not
make the code wrong — the code is right and waiting — but it does mean the only
role anybody can actually hold is the deprecated one, which is the exact
opposite of the deprecation's intent.**

**And `BLOCK 6` is disclosed as an addition rather than folded in silently:**
*"BLOCK 6 IS NOT IN THE ORIGINAL FIVE-ITEM LIST and is here on purpose… leaving
it out would have shipped a gate nobody could populate. Flagged rather than
folded in silently."* **That is the right way to add scope and it is worth
saying so.**

**UNVERIFIED, and it needs a human rather than a file: whether Michael has run
blocks 5 and 6.** Nothing in the repo records a run. **EXACT NEXT STEP: ask.**
Until then the role matrix is correct, driven, and inert.

---

## 8. WHAT ELSE WAS ON THE OBLIGATION, AND HOW FAR I WENT

**hank's "review hardest, in order" list is points 1–4 and those got the depth.
The obligation names three more things and I am explicit about the shallower
treatment rather than letting a discharge imply full coverage:**

| item | how far I went |
|---|---|
| **`rf_settings` tiered read** | **read the branch and its stated reasoning.** The tier is real: write is management-only and read was previously any signed-in employee returning every setting row whole **including `updated_by` and `updated_at`** — i.e. which manager changed the number that decides whether a slope is called total, and when. The comment states it is **narrower than `sen_settings`' tier, deliberately**, and names b9's own UNVERIFIED claim as now verified. **I did not drive it and I did not compare the field list against `api/sd-data-rf-settings-tier.test.js` arm by arm.** `rf_settings` is on the obligation's resource list, so this is the one named resource that received a read rather than a measurement. **COULD NOT TELL whether the tier's field split is complete.** |
| **`sen_visits` `clock_flags` merge** | **located and read.** The old line replaced the array; it now keeps existing flags and merges, with a named test driving it. **This is the same field my b18 review's N1 is about** — and N1 (an unconditional overwrite of an already-set clock field with no trail) is **unaffected by this change**, which merges flags rather than guarding the clock. **N1 remains open.** |
| **SAIRNcare `office_manager`** | **confirmed present in the app's role vocabulary** with the role's meaning stated in the comment. Not otherwise reviewed; it is run-order block 5's subject and block 5 has not run. |

**Not reviewed at all: `api/_lib/leg-overlap.js`'s interval arithmetic** beyond
the `exemptStatus` question hank asked about. The TOCTOU half has its own test
file and its own prior obligation.

---

## 9. THE DISCHARGE, AND WHAT IT DOES NOT CLAIM

**DISCHARGED** via `tools/tier_a_review_gate.py --discharge hank
2026-10-14T13:50:42Z --body-file <verdict>`, as the **assigned owner**, not with
`--takeover`.

1. **§0 bounds point 1.** The transcription is exact; **the spec it transcribes
   is mine and is unconfirmed by counsel or by a funeral director.** Five of the
   eight routed questions are unanswered.
2. **A STATE REVIEW.** `0442c8e0c95d` dangles; nothing was re-seated.
3. **No suite was run end to end.** The band and cell comparison was done by
   loading the module and parsing the spec; the assertions in the four test
   files were **read and independently reproduced**, not executed. **So "three
   arms pin the deprecation" means three arms exist and say what I quote — not
   that I watched them pass.**
4. **It fixes nothing.** Five findings routed: four to hank, two arms to cody.
5. **`rf_settings` got a read, not a measurement** (§8), and that is the one
   place where a named resource on the obligation received less than the
   attack points did.
6. **It does not re-open my own b18 N1**, which is the same field as the
   `clock_flags` item and is untouched by this change.
