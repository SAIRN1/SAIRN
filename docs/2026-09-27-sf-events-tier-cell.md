# `sf_events` — the cell is false, the tier is A, and here is the paste-ready replacement

**2026-09-27 (Cody). H1 log #553. Delivered as verified findings plus a validated
change set, NOT as an edit — `docs/CRITICALITY-TIERS.md` is `hank-queue13`'s
declared file and hank is actively editing tier rows in it.**

**HEADLINE: the H1 finding is correct. The cell's sentence is false, and it is
false in the one way this table's own rules forbid — it asserts a CODE FACT with
no citation. But the tier call turns on something neither the cell nor the
finding names: `sessionId` is read back out of the stored row and is the only
link that keeps a statutory session count correct. That makes it A on integrity,
for the same reason `sf_vehicle_service` and `sc_auth` are.**

The four-part change set below was applied to a copy and
`python tools/criticality_tier_check.py` returns **PROBLEMS:0** against it.

---

## 1. What the cell says, and what is actually there

> *"`alcohol` AND `sessionId` BOTH LOOK LIKE COMPLIANCE HOOKS AND NEITHER IS
> WIRED TO ONE TODAY — no permit or licence determination reads this row.
> **NAMED TRIGGER: the day anything computes a permit or licensing conclusion
> from `alcohol`, re-read this row**, because at that moment it stops being a
> calendar"*

**Read out of `sairnfreedom.html`:**

| Claim | Verdict | Evidence |
|---|---|---|
| "neither is wired to a compliance hook" | **FALSE** | `eventRefusals()` at `:4255` runs `liquorServiceCheck()` on **both ends** of an alcohol event, citing **OAC 4301:1-1-49(B)** with the comment *"because (B)(3) prohibits consumption as well as sale"* |
| — | **FALSE** | a gaming event is passed to `sfSessionRefusals()` at `:3086` — *"THE INTERLOCK. Not a re-implementation — the Phase 3 function itself"* — which carries the **ORC 2915.09(C)(4)** *"no more than three sessions in ANY seven-day period"* check |
| — | **FALSE** | `sfScheduleEvent()` at `:4302` **returns without writing** if any refusal fires. Nothing is stored |
| — | **FALSE** | on success a gaming booking **mints a real session row** into the same `K_SESSIONS` store the limit is computed from — its own comment: *"so it counts toward the three-per-seven-days limit from the moment it is booked"* |
| "no permit or licence determination reads **this row**" | **TRUE, and worth keeping** | nothing reads the STORED `alcohol` for a determination. Its only readers are a table tag at `:4378` and the combined list at `:4364` |

**So the cell conflates two different questions and answers the wrong one.** The
gate is on the **write path**, not on the row — which is exactly why it is
invisible to a reviewer reading the stored shape, and exactly why the sentence
survived a full re-audit.

### 1.1 AND IT BREAKS THIS TABLE'S OWN RULE, which is the transferable part

The register states: ***"This table states what the data IS. Whether a gate exists
is a code fact it does not assert"***, and `criticality_tier_check.py` *"refuses a
row that asserts one without citing a file or a test for it."*

**"NEITHER IS WIRED TO ONE TODAY" is precisely such an assertion, it carries no
citation, and it is false.** The rule was written after the `SV_RESOURCES` clause
made an access-control claim inside a content rule; this is the same failure on a
row nobody re-read, and the checker did not catch it because the refusal only
applies to *un-migrated* rows.

**That is worth recording independently of `sf_events`:** the guard against
uncited code facts does not reach rows that already migrated to two axes.

---

## 2. THE TIER CALL — A on integrity, and not for the reason the finding gives

The H1 finding offers: *"Stored row keeps only a pointer, so B is defensible, but
the cell's own words say it stops being a calendar."* **Both halves can be
answered without appealing to the cell's own wording, which is not evidence.**

**By the table's stated rule — the worse of two axes, on what the data IS:**

**Integrity axis → A.** `sessionId` is the **only** link between a hall event and
the bingo session its booking minted, and it **is read back**:

- `:4343` — deleting an event **deletes the linked session** by stored id:
  `if(ev && ev.sessionId) st(K_SESSIONS, getSessions().filter(s => s.id!==ev.sessionId))`
- `:4367` — the sessions list **hides** sessions owned by an event:
  `if(getEvents().some(e => e.sessionId===s.id)) return;`

**So lose that pointer, or point it at the wrong row, and one of two things
happens: a cancelled event STRANDS a session that keeps counting toward ORC
2915.09(C)(4)'s three-in-any-seven-days limit, or a DIFFERENT real session is
deleted and drops out of the count.** Either way a **statutory gambling limit is
computed against the wrong set of sessions.** That is the integrity of a regulated
record, which is Tier A's second clause.

**Confidentiality axis → B, unchanged.** Title, date, kind, and a pointer. No
protected class.

**Tier = A** (the worse of the two).

### 2.1 Why "only a pointer" is not a defence, with the register's own precedents

Two rows already sit at A on exactly this shape, and both are in this file:

- **`sf_vehicle_service`** — *"B→A on INTEGRITY … the ONLY thing that advances the
  odometer `sf_vehicles` computes its service-due flag from."* A row that is
  itself unremarkable, load-bearing on a derived flag.
- **`sc_auth`** — *"B→A on INTEGRITY only — `exp` IS the alarm … A wrong date does
  not mislabel a record, it REMOVES the authorisation from the warning."*

`sf_events.sessionId` is the same argument with a statute attached rather than a
warning badge. **A pointer whose corruption silently changes a statutory count is
not "an internal calendar."**

### 2.2 What would keep it at B, stated so the disagreement is locatable

If the event→session link were **derived on read** — e.g. matching on date and
time rather than a stored id — then losing the stored field would cost nothing and
B would be right. It is not derived; it is a single stored id, minted once at
`:4316` and never recomputed. **That is the whole integrity argument, and it is
why §3's replacement cell names it as the re-read trigger.**

---

## 3. THE CHANGE SET — four edits, validated together

**`docs/CRITICALITY-TIERS.md` is hank's.** These are not applied. The full patch
is at `<scratchpad>/tiers.patch` and the validated whole file at
`<scratchpad>/tiers-candidate.md`; the four edits are:

1. **The `sf_events` row** — replaced. Full text in §4.
2. **The `sairnfreedom` rollup line** — `| 35 | **25** | 10 | 0 |` becomes
   `| 35 | **26** | 9 | 0 |`.
3. **The rollup LIST** — `sf_events` inserted into the named Tier A list.
   **Do not retype it:** `python tools/criticality_tier_check.py --fix-rollup-list`
   inserts exactly that name and touches nothing else. The checker's own refusal
   says so, and it fired on the first attempt here.
4. **Two headline sentences** — *"390 resources, 266 A, 124 B, 0 C"* → *"267 A,
   123 B"*, and *"The B tier is 124 rows"* → *"123 rows"*.

**EDITS 2–4 ARE NOT BOOKKEEPING AND THE CHECKER PROVED IT.** Changing only the row
produced three separate refusals: `LIST MISSING` (the count moved and the sentence
did not — *"which is how a summary stops being readable while still adding up"*),
and two `HEADLINE` drifts. The file's own note says this headline has drifted five
times. **A tier promotion here is a four-part edit, and three of the parts are the
ones that get forgotten.**

**Verified after all four:** `PROBLEMS:0`, `TIER_A:267`, `RESOURCE_ROWS:390`.

---

## 4. The replacement row, paste-ready

Single line, six columns, `PROBLEMS:0` with it in place:

```
| `sf_events` | **A** | **B** | **B&rarr;A on INTEGRITY, 2026-09-27 &mdash; and the previous cell asserted a code fact that was false.** `sessionId` is the ONLY link between a hall event and the bingo session its booking minted. Lose it or point it at the wrong row and deleting the event either STRANDS a session that keeps counting toward ORC 2915.09(C)(4)&rsquo;s three-in-any-seven-days limit, or removes a DIFFERENT real session from that count. Either way a statutory gambling limit is computed against the wrong set of sessions. The date/title half really is a calendar; the pointer is not | What is booked at the post and when &mdash; title, date, kind, and a pointer. No elevated class, and Confidentiality stays B | **RE-READ 2026-09-27 (Cody). THE PREVIOUS CELL SAID `alcohol` AND `sessionId` &ldquo;BOTH LOOK LIKE COMPLIANCE HOOKS AND NEITHER IS WIRED TO ONE TODAY&rdquo;. That is a code fact, it carried no citation, and it is false** &mdash; which is this table&rsquo;s own rule (*&ldquo;whether a gate exists is a code fact it does not assert&rdquo;*) failing in the direction nobody checks. **READ OUT OF THE APP:** `eventRefusals()` at `sairnfreedom.html:4255` runs `liquorServiceCheck()` on BOTH ends of an alcohol event, citing OAC 4301:1-1-49(B) because (B)(3) prohibits consumption as well as sale; a gaming event is passed to `sfSessionRefusals()` at `:3086` &mdash; the Phase 3 function itself, not a re-implementation &mdash; which carries the ORC 2915.09(C)(4) three-in-seven check; `sfScheduleEvent()` at `:4302` **returns without writing** if any refusal fires; and on success a gaming booking MINTS A REAL SESSION ROW into the same `K_SESSIONS` store the limit is computed from, *&ldquo;so it counts toward the three-per-seven-days limit from the moment it is booked&rdquo;*. **WHAT THE OLD CELL GOT RIGHT, KEPT:** no permit or licence determination reads the STORED `alcohol`; its only readers are a table tag at `:4378` and the combined list at `:4364`. The gate is on the WRITE path, not on the row &mdash; which is why the tier turns on `sessionId` and not on `alcohol`. **THE POINTER IS READ BACK AND IS LOAD-BEARING:** `:4343` deletes the linked session by stored id, `:4367` decides what the Sessions panel shows. Same shape as `sf_vehicle_service` (B&rarr;A on INTEGRITY, the only thing that advances the odometer another row derives a flag from) and `sc_auth` (`exp` IS the alarm). **NAMED TRIGGER, REPLACING THE OLD ONE:** if the event&rarr;session link ever stops being a single stored id &mdash; derived on read instead, or duplicated &mdash; re-read this row, because the integrity argument above is entirely about there being exactly one copy of it |
```

---

## 5. What this pass did NOT do

- **It did not edit `docs/CRITICALITY-TIERS.md`.** hank-queue13 names it and is
  editing tier rows in it right now. Two sessions hand-editing one table row is
  the collision PR §2.1 exists for, and the row is 2,692 characters wide.
- **It did not touch `sairnfreedom.html`.** No code change is implied by this
  finding — the app is correct; the description of it was not.
- **It did not re-read the other 34 `sf_*` rows.** The 2026-09-23 pass read them
  individually and this one row is the only one under review. **But the failure
  mode found here — an uncited code fact in a cell, on a row that had already
  migrated and is therefore exempt from the checker's refusal — is not
  `sf_events`-specific**, and nothing has swept for it.
- **It did not verify the Ohio statutes against primary sources.** OAC
  4301:1-1-49(B), ORC 2915.01(S) and ORC 2915.09(C)(4) are as the app cites them.
  The finding here is about whether the app's own code does what the cell says,
  which is answerable from the repo; whether the citations are right is not.

## 6. Two things for whoever takes this

1. **Run the checker after pasting, not before committing.** All four edits or
   none: the row alone leaves the file failing three arms.
2. **`ROWS_STILL_ASSERTING_A_GATE:0` is not reassurance.** That arm only refuses
   **un-migrated** rows. `sf_events` was migrated to two axes and carried a false,
   uncited code fact for four days. **Worth a sweep of migrated rows for
   gate-assertion language** — `wired`, `is gated`, `nothing reads`, `no … reads
   this row` — which is a follow-up this pass did not do.
