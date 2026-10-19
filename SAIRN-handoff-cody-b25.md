# Handoff — cody, batch b25, 2026-10-19 — STOPPED ON INSTRUCTION

**Written BEFORE the report**, at a point where **nothing is half-finished.**
A stop order arrived mid-batch and replaced the rest of b25. **Nothing was
mid-edit when it did:** every file was already written and staged, every check
had already been run, and no item was abandoned part-way. **Item 5 (the
B6-class check) was never started, by earlier instruction, and stays held
back unchanged.**

**NOTHING IS PUSHED YET.** §1 is a **PRE-PUSH** state. §7 is the push.

**REAL MEASURED CONTEXT: 70.0% of 1000k — 700,309 tokens.** Taken from the last
assistant turn's `message.usage` in this session's own jsonl:
`input_tokens 2 + cache_read_input_tokens 700,307`. **Measured, not estimated**,
and not the max-over-transcript figure earlier handoffs in this session used.

---

## 1. FINISHED vs PARTIAL vs UNTOUCHED — plainly, before anything else

| item | state | what that means |
|---|---|---|
| **1. Methodology — concept before code** | **FINISHED** | Every item that wrote logic carries its one-line concept **above** the code, in the file. Two of three findings were only findable because of it |
| **2. `rf_locations` live-verify** | **FINISHED** | 6/6 green **against the deployed endpoint**, controls first, seeded row deactivated and **queried back** |
| **3. SAIRNscape `customers` PII** | **FINISHED** | Retier **B/B → A/A** landed; both lists confirmed; write path measured **403** live; the ordering arm added (**80 → 92**) and ablated **both legs** |
| **4. scrutiny-flags commit-not-stash** | **FINISHED AS A RULE, PARTLY DEMONSTRATED** | The §3.5 complement is landed and was followed for every gate interaction so far — but **this batch's own push had not run when the stop came**, so the rule is proven on b24's measurement and on this batch's staging, not yet on a full b25 push loop. Said plainly rather than claimed whole |
| **5. B6-class check** | **UNTOUCHED, BY INSTRUCTION** | Not started. Scope unchanged at §3 of `docs/2026-10-19-cody-b24-sweep-continued.md` |
| *(unplanned)* **demo-credentials correction** | **FINISHED** | `RF-AUDIT-2026` was documented as dead; it is not. Corrected with both halves kept |

**ONE THING WAS IN FLIGHT AND IS NOT A WORK ITEM:** the handoff had been copied
to the Drive mount and sha-verified, and the **Drive-side API read had not yet
returned it** when the stop arrived. The mount write is confirmed by sha256; a
Drive API confirmation is a separate fact and §6 records which one holds.

---

## 2. Committed state — PRE-PUSH

| | |
|---|---|
| commits | the claim commit `chore(claims): cody claims platform` is on `origin/main`. The work is **staged and not yet committed** as this file is written |
| claim | `platform`, taken **BEFORE any work**, FILES list declared. **STILL HELD** — §6 |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, in any form, and no call to `tools/gate_skip.py` |
| boundaries | **`api/sd-data.js` and `docs/CRITICALITY-TIERS.md` ARE NORMALLY HANK'S AND I TOOK THEM ON MICHAEL'S EXPLICIT INSTRUCTION** because hank's window is stalled — declared in the claim string rather than assumed. **`sairnscape.html` was NOT touched** (fourth holds it). **NO `sql/` file touched. NO `tools/` file touched** — five were RUN |
| `api/sd-data.js` | **+37 / −2, COMMENT ONLY.** No handler logic changed. Diff shape checked before committing |
| `docs/CRITICALITY-TIERS.md` | **+1 / −1.** Exactly one row, rebuilt WHOLE |
| live writes | **ONE**, named: `LOC-B25-VERIFY` on demo licence `RF-AUDIT-2026`, seeded then **deactivated and queried back** |
| Stripe | **NONE.** SAIRNcash is HELD and was not touched |
| committer | `fx <fx@example.invalid>`, unchanged |

**Files staged — eight:**

```
docs/b25-logs/live_verify_rf_locations_is_default.py  +308   item 2, re-runnable
docs/b25-logs/ablate_b25_gate_order.py               +221   item 3, both legs
docs/CRITICALITY-TIERS.md                            +1/-1  customers B/B -> A/A
api/sd-data.js                                       +37/-2 the stale "retier is
                                                            owed" note answered
api/sd-data-scp-session-gate.test.js                 +41    the ordering arm, 80 -> 92
docs/SAIRN-PROCESS-RULES.md                          +25    the complement of 3.5
docs/2026-09-03-demo-credentials.md                  +24/-2 RF-AUDIT-2026 corrected
docs/2026-10-19-cody-b25-live-verify-and-scape-pii.md +311  the full account
```

---

## 3. Item 2 — the live verification. FINISHED, and the controls are the whole story

**THE CONCEPT:** *a change to a response shape is not done until the destination
is queried back, so read `rf_locations` through the real endpoint with a real
session and assert `is_default` on the rows that actually come out of it.*

```
C1 provisioned:true .............................................. ok
C2 at least one row came back .................................... ok
C3 default_location_id present (pre-dates b24, so a deploy tell) . ok
A1 EVERY row carries is_default .................................. ok
A2 ...and every one is a BOOLEAN .................................. ok
A3 is_default AGREES with default_location_id -- computed, not
   stamped to a constant ......................................... ok
6 checks run, 0 failed      EXIT=0
```

**WHY A SOURCE-LEVEL SUITE COULD NOT ANSWER THIS.** Every b24 arm reads
`api/sd-data.js` and `sairnroofing.html` **off disk**. This repo has a recorded
incident where a Vercel deploy failed, production kept serving the **last
successful build**, and several pushes reported clean while the live site stayed
on old code. A source-level suite is green against a tree nobody is serving.

**THREE THINGS THE CONTROLS CAUGHT:**

1. **THE REGISTRY WAS EMPTY** — `provisioned: true`, **zero rows**. C2 went red
   and **stopped the run**. *"`is_default` was not found"* over an empty list is
   satisfied for ever. Resolved by **seed-and-recheck**, this platform's named
   method for exactly that state:

   > **THE SEED CONCEPT:** an empty registry makes an absence unattributable, so
   > the verifier seeds ONE synthetic location through the real write path,
   > reads it back through the real read path, asserts the flag, and then
   > **deactivates it** — leaving a named inactive row rather than silently
   > mutating demo data.

2. **C3 SEPARATES "THE CHANGE IS BROKEN" FROM "THE DEPLOY IS OLD."**
   `default_location_id` has been on this response since 2026-09-16. Present
   while `is_default` was absent would mean the build predates b24 — a **deploy**
   question, not a code one. **No amount of re-reading source distinguishes
   those two.**

3. **THE `is_default: true` CASE WAS NOT EXERCISED LIVE**, and the verifier says
   so in its own output. No row carries the sentinel id; creating one would
   change what the demo tenant renders as *"Main"*. Covered at source level by
   `location-scope.test.js` arm E and
   `sairnroofing_default_location_from_server.js` arms B1/C1. **"6 of 6 green"
   over a one-row registry is a weaker claim than it looks and is not presented
   as a stronger one.**

---

## 4. Item 3 — the SAIRNscape PII retier and the ordering arm. FINISHED

**THE RETIER: B → A ON BOTH AXES**, `docs/CRITICALITY-TIERS.md` line 535.
Confidentiality B → A because the row's own basis cell already read *"A
CUSTOMER's NAME, PHONE, EMAIL AND STREET ADDRESS"* — **the basis was corrected
2026-09-30 and the LETTER was not**, and the letter is what the 2026-10-05 gate
sweep read. Integrity untouched, still genuinely B. Tier follows to A because
this register takes the worse axis, as `sd_sms_log` already does.

**IT WAS CORRECTLY NOT TAKEN IN 2026-10-05 AND THAT RECORD IS KEPT.** The
`SD_SESSION_GATED` note said *"THE RETIER IS OWED AND IT IS NOT MINE TO MAKE:
hank holds docs/CRITICALITY-TIERS.md under a live claim."* The gate shipped
**ahead of** the register with that comment as the explanation — the right call.
**Struck through, not deleted**, because it is the record of why they disagreed
for two weeks.

**BOTH LISTS CARRY IT, MEASURED:** `SD_SESSION_GATED` at `:1505`, `SD_GATE_APP`
at `:1842`. The pair is the point — a resource in the first without the second
resolves to `'stonedesk'` and then **every correctly signed-in SAIRNscape crew
lead is refused FORBIDDEN**.

**THE WRITE PATH IS ALREADY 403, MEASURED LIVE** on `SCP-DEMO-2026` with no
session: `read customers`, `write customers` **with an id-less payload**, and
`write customers` with a valid payload **all three answered 403 FORBIDDEN**, with
`invoices` and `scp_quotes` as controls. **The 400 the 2026-10-05 note records is
gone.**

**BUT NOTHING WOULD HAVE NOTICED IF IT CAME BACK, AND THAT IS THE REAL FINDING.**

> **THE CONCEPT:** an unauthenticated write to a session-gated resource must be
> refused by the GATE before the handler body reads the payload, so it answers
> 403 and not the handler's own 400 — a 400 proves the gate did not fire and
> discloses the validation rules to a caller who has not signed in.

The existing write arm sends a **valid** payload, so it answers 403 whether the
gate runs before or after validation. **The ordering is only observable with a
payload the body would refuse.** One arm per gated resource now sends `{}` and
asserts 403 + `code: FORBIDDEN`. **80 → 92 arms.** The payload is deliberately
empty because all twelve handler bodies validate *something*.

**ABLATED, BOTH LEGS, AND G1 IS THE WHOLE CLAIM:**

```
                                                PRE-REPAIR      POST-REPAIR
G3 CONTROL, unmutated copy                      exit 0          exit 0
G1 a payload check for customers placed
   BEFORE the gate                              ACCEPTED        REFUSED, and ONLY by
                                                (unprotected)   the empty-payload arm
G2 CONTROL, customers removed from
   SD_SESSION_GATED                             valid arm only  BOTH write arms red
```

**Under G1 the PRE-EXISTING write arm stays GREEN.** Only the empty-payload arm
goes red. G2 turns both red and so proves the new arm *runs*, not that it was
*needed*; **G1 proves it was needed.**

---

## 5. Items 4 and the unplanned correction

### 5.1 Item 4 — the rule existed and stated only half of itself

> **THE CONCEPT:** a file the GATE ITSELF wrote during a refused push is
> bookkeeping this session owns and must be COMMITTED on every round; only a
> file another session has declared may be stashed — because stashing the
> gate's own write leaves the tree dirty against the very rebase the gate's
> refusal asks for.

**`docs/SAIRN-PROCESS-RULES.md` §3.5 already prescribed the loop** and already
said what to do when the hook-written file belongs to somebody else: stash it,
do not commit it. **What it did not say is the complement** — the more common
case, where nobody else declares it. A reader carried the correct **no** across
to their own file, and that is how b24 spent four rounds inside the loop §3.5
itself names.

**MEASURED, b24:** `git pull --rebase` exited **128** on a tree whose only
modification was the gate's own write, and the refusal that produced it asked
for that rebase. **A stash is worse than dirty:** those rows are keyed **per
COMMIT**, so a stash held across a rebase keys them to shas that no longer
exist — a ledger entry pointing at nothing.

**Landed as an addition to §3.5, not a new section.** **PARTLY DEMONSTRATED,
said plainly:** the rule was followed for every gate interaction up to the stop,
but this batch's own push had not run yet, so the full-loop demonstration is
owed to the push in §7.

### 5.2 A STANDING DOCUMENT HAD GONE STALE IN THE DIRECTION THAT CLOSES A QUESTION

`docs/2026-09-03-demo-credentials.md` said `RF-AUDIT-2026` *"returns 401
INVALID_LICENSE"* because its seed was never run. **It returns 200 with a
session token.** The seed has since been run.

**THE COST IS WHY THIS IS A FINDING.** Read literally, that entry says there is
no usable SAIRNroofing licence and item 2 cannot be done. The only reason it was
done is that the verifier **tried the login and read the answer instead of the
document.** **A standing document that says a capability is absent is strictly
more expensive than one that says nothing, because it closes the question.**

**Corrected with both halves kept, and `RF-PINNACLE-2026` was re-measured in the
same run and is still `401 INVALID_CREDENTIALS`** — so the section is corrected,
not emptied.

---

## 6. Verification, and claims held

```
EXIT=0  python docs/b25-logs/live_verify_rf_locations_is_default.py   6/6, LIVE
EXIT=0  python docs/b25-logs/ablate_b25_gate_order.py                 POST, 0 unexpected
EXIT=0  python docs/b25-logs/ablate_b25_gate_order.py --before        PRE,  0 unexpected
EXIT=0  node api/sd-data-scp-session-gate.test.js                     92 arms (was 80)
EXIT=0  node api/_lib/location-scope.test.js                          8, b24 regression
EXIT=0  node api/_lib/roofing-locations.test.js                       17, regression
EXIT=0  node api/_lib/roofing-locations-endpoint.test.js              29, regression
EXIT=0  node tests/sairnroofing_default_location_from_server.js       15, b24 regression
EXIT=0  node tests/sairnlaw_trust_clearance.js                        11, b24 regression
EXIT=0  node --check api/sd-data.js and the gate suite
EXIT=0  python -m py_compile docs/b25-logs/*.py
EXIT=0  python tools/md_table_check.py
EXIT=0  python tools/open_work_shard.py --check
EXIT=0  python tools/tier_a_review_gate.py
```

**THE REGISTER ROW WAS MEASURED BOTH WAYS:** **663 → 663** lines, **434 → 434**
table rows, the row **one physical line**, pipe count **7 → 7**, and **every
other line in the file asserted byte-identical** by the inserter rather than
checked by eye.

**THE CONTROL REFUSED TWICE BEFORE IT PASSED AND BOTH REFUSALS WERE REAL** —
the temp tree lacked `tests/lib/fn_span.js`, then `sairnscape.html`. Each time
the harness printed **CONTROL FAILED — nothing below is attributable** and
stopped. Without it, two rounds of "REFUSED" verdicts would have come from a
copy that **never executed a single arm**.

**AND THE HARNESS'S OWN LABELLING WAS WRONG ON THE FIRST PRE RUN** — it applied
the POST expectation to both legs, so the PRE leg printed G1 and G2 as *"NOT AS
EXPECTED"* when both were behaving exactly as a pre-repair suite must.
Expectations are per leg now. **The fourth measurement-tool defect in three
batches, and each was in a tool written to honour a discipline.**

**THE LIVE TREE WAS NEVER WRITTEN BY ANY ABLATION**, asserted rather than
intended: `git status --porcelain` captured before and after and diffed.

**DRIVE: THE MOUNT WRITE IS CONFIRMED BY SHA256; THE DRIVE-SIDE API READ IS
NOT.** This file was copied to the mount and read back sha-identical
(`49947f30d8a099f5…`), and a Drive API search for it returned **empty** at that
moment. **A mount read-back does not prove Google acknowledged the upload** —
only an API read does, and this handoff is re-uploaded with the report and
digest, where the API confirmation is recorded.

**CLAIM `platform`, taken BEFORE any work with a FILES list declared, STILL HELD
as this file is written**, because the push has not happened and **a claim
released before the work lands is a claim that was never true.** Released with
the report. **Nothing was inherited:** b24's claim was released at the end of b24.

---

## 7. Open — every item, why, and the exact next step

### 7.1 → NOBODY STARTS A NEW BATCH. Awaiting a fresh-start paste

**This is a STOP, not a pause with a queue.** The instruction was to stop new
work, commit what exists, push, and wait. **Do not pick an item out of §7 and
begin it** — a fresh session should read this file and then wait for direction.

### 7.2 → FOUR TIER ROWS NOW DISAGREE WITH `customers`, AND IT IS A READ EACH

`bld_suppliers`, `sf_vendors`, `leg_clergy`, `dnt_vendor_contacts`. All four sat
in the class the `customers` row was held at B on, and that class reading is now
struck through for one member and standing for the other four.

**THE EXACT NEXT STEP, AND IT IS DELIBERATELY NOT A RETIER:** read each one's
columns out of its own `sql/` schema and its own write site — **not** out of the
register and **not** out of the `customers` decision — and record a tier per row
with the columns quoted. **Retiering four rows off one row's decision would
recreate the class-default reasoning that produced the original error.** Two of
the four may well be genuinely B: a supplier's company contact is not the same
population as a residential landscaping customer's home address.

### 7.3 → `LOC-B25-VERIFY` IS AN INACTIVE ROW ON `RF-AUDIT-2026`

Seeded to make the registry non-empty, deactivated, and **queried back** to
confirm `active=False` rather than trusting the write's exit code. SAIRNroofing
has no delete path for a location — a fact about the app, not a choice.
**Anybody with database access may delete the row; nothing depends on it.**

### 7.4 → THE `is_default: true` CASE IS STILL UNEXERCISED LIVE

Covered at source level in two suites. Exercising it live means creating a
registry row carrying the sentinel id on a demo tenant, which changes what that
tenant renders as *"Main"*. **Not done, and the reason is recorded rather than
the omission being silent.**

### 7.5 → ITEM 4's RULE IS OWED ONE FULL-LOOP DEMONSTRATION

The §3.5 complement is landed and was followed up to the stop. **The push in
this batch is its first end-to-end test.** If that push takes more than one
round, the round-by-round account belongs in the report's STATUS — and if it
takes one round, say that too rather than implying the rule was exercised hard.

### 7.6 → AN OWNER FOR THE B6-CLASS CHECK. Still not started, by instruction

Scope at §3 of `docs/2026-10-19-cody-b24-sweep-continued.md`. **Do not build it
without a precision number on a real sample** — b24 measured the arm-finding
half at **1-of-4** on the easier population, and that is the whole argument.

### 7.7 → WHOEVER TAKES THE NEXT SWEEP BATCH. 85 candidates, not mine

`green_but_worthless_sweep.py --all` reports 95; 10 are cody's. The other 85 are
**not mine, not read, and not counted as clean.** Read b24's window-bleed caveat
first: the FILE-DERIVED class is roughly **1-in-4 real** on the one sample
checked.

### 7.8 → HANK. Unchanged and NOT re-sent, plus a courtesy note

C1 in `tests/sd_data_not_provisioned_misclass.js` is still red on purpose: route
the `alf_op_audits` **existence SELECT** through
`notProvisioned(res, existingR, <the same message>)`, one guard earlier than
A1's fix. `notProvisionedDecide()` needs no change. Re-derive the line number.
`:14316` is still named and not driven.

**AND BECAUSE I CROSSED YOUR BOUNDARY TWICE NOW:** `api/sd-data.js` is **+37/−2
and COMMENT ONLY** — the stale *"the retier is owed and it is not mine to make"*
paragraph, struck through and answered. **No handler logic changed.**
`docs/CRITICALITY-TIERS.md` is **+1/−1**, one row rebuilt whole. Both on
Michael's instruction because your window is stalled.

### 7.9 → FOURTH. The b23 Tier A obligation on `dnt_rollup` is still open

Assigned to you by the gate in b23. It names what to try to break rather than
asking for a diff read, and it is **not** a substitute for your own live render
pass. **`sairnscape.html` was left alone this batch** — you hold it.

### 7.10 → CC. Carried from b22, unchanged

Open-work **row 449** records *"`dnt_rollup` appears 0 times in every `.html`
file"*, which is **false** — `sairndental.html:2543` is a real
`sdnData('read','dnt_rollup',{})` call. **Row 356**'s item-4 sentence still says
the shared multi-location architecture is NOT STARTED where **row 355**
contradicts it.

### 7.11 → MICHAEL. Nothing is blocked on you

Both of this batch's instructions are implemented and ablated. SAIRNcash stays
**HELD**.

### 7.12 → NOT TOUCHED IN b25, named so it is not mistaken for done

**No live RENDER of anything.** Items 2 and 3 are live **endpoint** checks,
which is a different and narrower thing than a rendered-page check.

The b17/b18 carry-overs are exactly as b19–b24 left them: `tooling_inventory
--hooked` failing open on an empty hook set; the two claims probes' retyped-task
fixtures; `sairnbuild.html`'s bare `catch(e){}` in `st()`; six named
`recurrence_open` register records; `run_capa_fields_probe.py`'s 200–420s
per-arm 2.46MB register rewrite; b16's three deterministic ablation arms. **The
151/57 sibling `NOT_PROVISIONED` guards are still NOT converted — a decision,
not a backlog.** The expensive known-red-`tail` census is still unmeasured.
`irs.gov/instructions/i8846` is still unread.

---

## 8. Scratch and transcript

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\9fe1b8da-047e-4787-9e87-9983dd2e2635.jsonl`
— **4,849,917 bytes, 2,561 lines.** This session also carries b22, b23 and b24;
b25 begins at the turn whose first item is the live-verification lane, and the
stop order is the turn after the Drive upload of this file's first version.

**REAL CONTEXT AT THIS LINE: 70.0% of 1000k — 700,309 tokens**, from the last
assistant turn's `message.usage` (`input_tokens 2 +
cache_read_input_tokens 700,307`). **This is a different and more honest figure
than the max-over-transcript number b22–b24's handoffs used**, which answers
"what was the largest single request" rather than "what is loaded now".

**Scratch:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\9fe1b8da-047e-4787-9e87-9983dd2e2635\scratchpad\`
— `retier_customers.py` (the row rebuilder with its assertions), `b25_live.log`,
`b25_gate_before.log`, `b25_gate_after.log`, `b25pre.txt`, `b25post.txt`, plus
b22–b24's logs still in place.

**No worktree was created this batch.** Every ablation used
`tempfile.mkdtemp()` directories removed in a `finally`.
`C:/Users/marsh/AppData/Local/Temp/gate-probe3-17976` is registered against this
clone, is **not mine**, and was left alone. The 109 files / 247 MB that `rm` has
refused across b14–b16 are still at the b16 path, listed in
`SAIRN-handoff-cody-b16.md` §6. **Nothing in the repo or on the Drive depends on
any of them.**

---

*Written before the report, at a point where nothing is half-finished. b25 was
STOPPED on instruction, not completed to its original plan, and §1 says which
items that leaves finished, partial and untouched.*
