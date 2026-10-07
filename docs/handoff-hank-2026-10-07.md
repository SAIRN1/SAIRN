# Hank handoff — 2026-10-07, batch 11

**Written at a point where nothing is half-finished.** Every item below is
either committed with its evidence, or named as open with the exact next step.

**Transcript / working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\16753c01-e018-4c71-af08-342c1baa72e6\scratchpad`
— every `capture_exit` status file and captured run, the register-add scripts
(`reg3.py`), the mutation-proof graft (`graft.py`), the register union-merge
(`resolve_reg2.py`), the citation re-measure (`cite_measure.py`), the audit
capability measurement (`audit_cap.py`), and the push loop that produced the
detached HEAD (`pushloop.sh`).

**Full detail:** `docs/2026-10-07-inventory-hank-batch11.md`.

---

## CLAIMS HELD — read this first

**`hank` / `platform`, ACTIVE, NOT RELEASED.** Landed at the claim commit after a
**one-hour andon**. Declared FILES: `api/sd-data.js`, 16 `api/*-auth.js`,
`api/stonedesk-track.js`, `api/sd-sub-data.js`, `tools/gate_parity_check.py`,
four new `tests/`, `docs/SAIRN-OPEN-WORK-INDEX.md`,
`docs/2026-10-06-hank-routed-to-fourth.md` and this batch's docs.

**THE ANDON, because it cost an hour and the next session needs to know the
shape.** `sairn_claim.py check` refused for ~55 minutes on **`blocked by: same
app: sairngrounds`** against hover2's live claim — a claim whose own text says
*"writes only to its own hover-audit-log and its own tools-hover2 directory"* and
*"read-evidence pass over hank's four divergence flags, **no edit**"*. hover2
carries no `FILES:` list, so the matcher fell back to word overlap and blocked on
the app name plus generic words (audit, role, session, flags, read, tools). Zero
declared-file overlap.

**I did not reword the task string to get past it** (PR §4.3). I raised the
andon in the shared status registry addressed to hover2 and to chat, did every
item's read-only re-derivation meanwhile, and polled until the claim expired
naturally. **Two narrowings were made and both were real scope reductions, not
rewordings:** `docs/tier-a-reviews.json` was REMOVED from my FILES (item 7
declined), and SAIRNgrounds was briefly removed and then restored once hover2
cleared.

**THREE CONFLICTS DECLARED, NONE REWORDED PAST:**

- **`docs/tier-a-reviews.json` — cc, cody AND fourth all hold it right now.**
  Verified with a fetch, `sairn_claim.py list` exit 0, 2026-10-07. **Item 7 is
  NOT DONE and that is correct.**
- **`tools/scrutiny_flag.py` + `docs/scrutiny-flags.json` — CC'S.** I edited
  neither. Rows in that file are its own tool's output about my commits,
  committed because the file is append-only and the record is what the gate
  exists to create.
- **`docs/METHODOLOGY.md` — mine, and NOT edited.** The methodology rule is
  routed to fourth rather than self-promoted.

---

## PER-ITEM MAP

| # | Item | State |
|---|---|---|
| 1 | `alf_staff`/`read` role gate | **DONE** |
| 2 | SAIRNgrounds session gates | **DONE** — 16 of 17 measured, 21 fixed |
| 3 | SAIRNcare cross-resource flags | **DONE** — 1 of 4 real, fixed |
| 4 | Provisioning attribution | **PARTIAL** — 6 paths of 16+2; 14 blocked on a migration |
| 5 | 12 gate_parity flags hand-verified | **DONE** — 2 real, 10 false positives, criteria fixed |
| 6 | Citation re-measure | **DONE** — and it found a SHA I had fabricated |
| 7 | Tier A discharge | **NOT DONE** — three sessions hold the file |
| 8 | Guard and gate suites | **PARTIAL** — two gate suites green, the full suite still RUNNING |
| 9 | Methodology rule + cause tags | **DONE** — routed, not promoted |
| 10 | Handoff | this file |

---

## WHAT LANDED, with the mutation proof for each

Every figure below is from a `capture_exit` status file, never a harness
completion status.

| Fix | Commit | At this tree | Against the parent |
|---|---|---|---|
| `alf_staff`/`read` PII | `23a63e30` | 18 passed / 0 failed, EXIT 0, **3 runs** | **6 passed / 12 failed, EXIT 1** |
| `derive_charges` PHI | `d75bd00b` | 14 / 0, EXIT 0, **3 runs** | **10 / 4, EXIT 1** |
| 21 SAIRNgrounds gates | `796e5c31` | 7 / 0, EXIT 0, **3 runs** | **2 / 5, EXIT 1** — A1 said *0 of 42 pairs refused* |
| Attribution, 6 paths | `b0e85e11` | 10 / 0, EXIT 0, **3 runs** | **3 / 7, EXIT 1** — A2 said *found 1* |
| gate_parity direction | `c3b61a50` | 11 / 0, EXIT 0, **3 runs** | **9 / 2, EXIT 1** — X4/X5 got `direction=None` |

**First run is included in every count above.** The `derive_charges` and
`attribution` suites each went red on their FIRST run for a defect of mine, and
both are recorded in their commit messages rather than compressed away.

**THE SHAs WILL MOVE AGAIN.** Four rebases happened during this batch and each
rewrote them. The defect register re-seats itself through
`.githooks/post-rewrite`; **the commit messages cannot be re-seated and three of
them cite pre-rebase SHAs in their prose.** Re-derive from `git log --grep`, not
from a prefix in a message.

---

## OPEN — exact next step per item

### 1. Item 4's other 14 apps — BLOCKED ON A MIGRATION, not on effort
`api/_lib/audit.js:40` allowlists exactly three audit tables: `sairnlaw`,
`sairncode`, `stonedesk`. Measured: of 17 `api/*-auth.js`, only 3 import
`writeAuditLog` and only 2 declare an `AUDIT_TABLE`. **NEXT STEP:** the 14 need a
per-app audit table before `setup` can be attributed. Either write the
migrations (needs Supabase, which this session does not have), or add an
`updated_by`/`created_by` column to each `*_employee_auth` table — also a
migration. There is no code-only route. `tests/provisioning_attribution.js` arm
A2 is a FLOOR (`>= 3`) so it will not go red as they land one at a time.

### 2. The role sets nobody has decided — still a product question
`alf_staff` (which roles see the full roster) and the 21 SAIRNgrounds resources
(which of owner / superintendent / manager / crew / office may write a BOQ rate
or an invoice). **Both fixes deliberately stopped at the session/projection
layer.** `crew` can still write a SAIRNgrounds invoice once signed in.
**NEXT STEP:** Michael's call, then one change per app with a test. Tracked as
`ALF-STAFF-READ-UNGATED-HANK-2026-10-06` and
`ROLE-SET-SWEEP-HANK-2026-10-06` in `docs/SAIRN-OPEN-WORK-INDEX.md`.

### 3. TWO AUDITOR REPROS NOW REPORT FIXED DEFECTS AS LIVE — routed to hover2
Both still exit 1 at this tree and **both are right about their own criterion
and wrong about the world**:

- `tools-hover2/grd_session_gate_repro.py` asks whether `verifySessionToken`
  appears **INSIDE** each resource's dispatch block. The fix is ONE SHARED
  PRELUDE, which `gate_parity_check.py` calls *"the single most common correct
  shape on this platform"*. A lexical inside-the-block test cannot see it.
- `tools-hover2/alf_cross_resource_repro.py` tests for the **PRESENCE** of
  `medication_name` in the `derive_charges` block. The string is still there,
  behind `ALF_MAR_ROLES[session.role]`. A presence test cannot see a role-gated
  redaction.

**NEXT STEP: nothing by hank.** That tree is the hover auditors' and is read-only
to a build agent — I ran both tools and edited neither. The behavioural tests
they need are `tests/sd_data_grd_session_gate.js` (arm A for the refusal, arm B
as the control) and `tests/sd_data_alf_mar_derive_charges_gate.js` (arm B1 for
reachability, arm D as the control). **The findings stay OPEN for their finder to
close** — I close only what I originate.

### 4. `msb_*` is the same licence-key-only shape and is NOT fixed
Nine `msb_*` resources sit in the SAME dispatch region as the SAIRNgrounds ones
and have the same gap. Different app, not in the routed finding, not in my claim.
**Arm D1 of `tests/sd_data_grd_session_gate.js` drives `msb_products` without a
session and asserts it STILL answers** — that is a measurement proving my prelude
did not silently catch a neighbour, **not an endorsement**. **NEXT STEP:** route
or claim it as its own item; the fix is the same shape as item 2 and would take
under an hour.

### 5. Three gate_parity false positives REMAIN FLAGGED, deliberately
`alf_clients`, `rf_claims`, `rf_jobs` are WEAKER by the tool's two lexical
booleans and false positives by **role-set containment** — every role reaching
the diverging branch is already inside the set that gets the owner's unfiltered
read. **NEXT STEP:** do NOT suppress them with three hardcoded table names;
that expires the day a role set changes (recurring-bug-class 26). Either teach
the tool to resolve `roleSet(...)` literals — a real feature, not a patch — or
leave the limit printed, which is what it does now.

### 6. 50 unresolvable citations, and ZERO are recoverable by fetching
Re-measured after `git fetch origin`, 2026-10-07: **385** sha-shaped citations
in `docs/SAIRN-OPEN-WORK-INDEX.md`, **335** reachable from HEAD, **0** on origin
but not HEAD, **10** objects only this clone holds, **40** not objects anywhere
this clone can see. **The two populations need different fixes and must not be
merged** — an unfetched commit and a typo are indistinguishable from here.
**NEXT STEP:** cc owns the root cause (`tools/doc_sha_reseat.py`). Wait for it,
run it in propose mode, adjudicate the 40 by hand. Do not hand-repoint rows —
that is what produced the backlog, and **it is also what produced the one
fabricated citation this batch found.**

### 7. Tier A — 23 eligible, 0 taken, and that is the right answer
Most overdue eligible: cody's `2026-09-27T02:06:03Z`, **236h**. **NEXT STEP:**
re-run `sairn_claim.py list` WITHOUT `--no-fetch` (it exits 4 and says so on a
stale read). If `docs/tier-a-reviews.json` is free, take the oldest with
`--discharge --takeover` and change nothing else. Right now cc, cody and fourth
all declare it.

---

## THREE THINGS ABOUT THIS REPO THAT COST ME TIME TODAY

1. **A `rebase --continue` that keeps refusing on a file nothing of yours is
   editing is a HOOK writing it between your two commands.**
   `docs/report-only-sweep-marker.txt` is rewritten by a PostToolUse hook on
   every git command, so there was always a fresh unstaged change. It only
   worked when the `git add` and the `rebase --continue` were in ONE command,
   with no tool call in between.
2. **A scripted push loop produced a DETACHED HEAD with a rebase paused 6 of 8
   commits in.** What recovered it was reading `git status` FIRST and never
   touching `--amend` inside the pause (recurring-bug-class 23). Do not script
   `pull --rebase` in a retry loop on this repo.
3. **The push gate takes ~2 minutes and three other sessions push continuously,
   so a single attempt loses the race most times.** Minimise the work between
   the pull and the push; regenerate the derived documents AFTER the rebase, not
   before.

---

## WHAT THIS BATCH WOULD SAY IF IT COULD SAY ONE THING

**A green check licenses only the claim it actually tested.** Twice today I used
one for something wider: a verified 8-character SHA prefix got padded by hand to
twelve, and `node --check` exiting 0 was taken for a guarantee that a name
resolves — it was a `ReferenceError` in both of my new audit calls. The first
survived my own closing measurement last batch because I reported a COUNT of
unresolvable citations rather than the LIST, and the count included the one I had
just minted. Routed as RULE C in
`docs/2026-10-06-hank-routed-to-fourth.md` §6.

---

## ITEM 8 — WHAT RAN, WHAT DID NOT, AND WHY THE DIFFERENCE MATTERS

**CITABLE, both run at `c3b61a50` BEFORE any document in this batch was
written, so nothing moved under them:**

    node tools/role_gate_invariants.js        EXIT 0
      "No invariant is violated by the role sets these modules export,
       declare internally, or inherit from the app role vocabulary."
      and its own disclosure: that is 63 checks, NOT the 22 it could not make.

    python tools/gate_parity_check.py --selftest   EXIT 0
      11 passed, 0 failed — 3 runs, first run included

**NOT KNOWN: `python tools/run_all_tests.py`.** Its `capture_exit` status file
still reads `RUNNING 82584 2026-10-07T12:48:31Z` after ~27 minutes with the
process alive and zero bytes flushed. **Per `capture_exit`'s own contract a
`RUNNING` file means the answer is NOT YET KNOWN, and that is a third state — it
is not folded into a pass and it is not reported as a failure.** cody's handoff
records the same harness running 3h30m where it was said to take 420s, so this is
expected behaviour rather than a hang.

**AND IT IS NOW CONTAMINATED, which is worth more than the number would have
been.** This handoff, the inventory and the active-work append were written into
the tree WHILE that run was in flight. Several of its probes depend on a clean
tree. **So even when it reports, its result is about a tree that changed under
it and must NOT be cited as a verdict on the final SHA.**

**NEXT STEP:** re-run it alone on a quiet tree and read the exit code from the
status file, not from a harness completion status. If it exits **3**, that is
`SKIPPED -- another run holds the lock`, not a failure: `LOCK_MAX_AGE` is 900s
and a run killed by a wall-clock timeout leaves the lock held for 15 minutes.
That happened twice in this batch and is the reason the lock is named here.
