# Handoff — cody, batch b28, 2026-10-20

**Six instructed items. All six are done.** Two security defects reproduced,
fixed and armed; one live endpoint verification that b27 could not make; b27's
reverted item 4 redone and **measured at 12 of 12**; a currency sweep with
seven findings; pushed without `--force` and read back off the remote.

---

## 1. THE SIX ITEMS, PLAINLY

| item | state | what that means |
|---|---|---|
| **1. release the claim + drop the stash** | **DONE** | `release platform` committed and pushed; the stash diff was READ before dropping (50 lines of the gate's own `scrutiny-flags.json`, nothing else) and `git stash list` is now empty |
| **2. rt_routes LIVE** | **DONE — VERIFIED, 6 arms, exit 0** | A real authenticated request answers correctly against the real deployment. b27 §6.8 is **closed** |
| **3. role-from-token bypass** | **DONE — reproduced, fixed, 15 arms** | A demoted attorney could move client trust money for **12 hours**. Reproduced at 200, now 403. **The settling step was the second half and it was asking the wrong column** |
| **4. the patient photo cap** | **DONE — reproduced, fixed, 13 arms** | A 300KB booking photo could be neither confirmed nor declined. And the **:9857 1.5MB handler was the same defect one app over** — eight tables, not one, measured |
| **5. currency sweep + item 4 redone** | **DONE — 7 findings; 12 of 12 driven** | Two of my own rule records are measurably bad; two findings against my files are **not my defects**. Item 4's hook now EXECUTES |
| **6. push without force, confirm landed** | **DONE — see §2** | Read back off the remote, not inferred from the push's exit |

---

## 2. Committed and pushed state

| | |
|---|---|
| commits | **SIX, and five are bookkeeping.** The work is ONE commit — `b28(cody): the role in the token is not the role in the roster, a photo cap that was never the real ceiling, and a hook that finally runs` (`7e43c9dab`). The other five are what the gates asked for and the rebases forced: two derived-doc regenerations, the Tier A obligation + the path override replacement, and two of the push gate's own `scrutiny-flags.json` rows. **No squash was needed** — unlike b27, no commit carries a duplicate subject and no conflict markers reached a register, because the two conflicted generated documents were resolved by name rather than with `git add -A` |
| pushed | **LANDED AND VERIFIED BY READING THE REMOTE**, not by the push's exit. **FINAL REMOTE TIP `e721db4b723b`, `0 ahead / 0 behind`.** The work commit `7e43c9dab` proved an ANCESTOR of it with `git merge-base --is-ancestor`, and ten files read back off the remote tree — the handoff at **28,089 bytes, byte-identical AT THAT TIP** after CRLF normalisation — **this file is now longer, and it has to be**: the two rows recording a verified tip cannot be inside the push they describe, so the read-back proved the handoff as it was pushed and the bookkeeping commit below carries these two rows. Said rather than left as a byte count that no longer matches. plus both b28 suites, the live probe, both b28 documents, `api/_lib/countersign.js`, `api/sd-data.js`, `docs/known-red-suites.json` and `docs/sairn-path-manifest.json`. **PUSHED WITHOUT `--force`.** It took **four rebases** — the remote moved under three of them, which is ordinary with six sessions pushing |
| claim | `platform`, taken **BEFORE any work** with a FILES list. **RELEASED at the end of the batch** |
| overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE`, no call to `tools/gate_skip.py` |
| rebase | **31 commits behind at push time**, rebased onto `origin/main` with no conflicts. **Two of the sweep's seven findings were closed by cc's b27 inside that rebase** and the sweep says so rather than dropping them — §2 and §3.2 of `docs/2026-10-20-cody-b28-currency-sweep.md` |
| boundaries honoured | **`tools/` NOT TOUCHED** (cc's) — six were RUN. **`.claude/skills/` NOT TOUCHED** — one was READ, and §3.1 of the sweep is a report about it, not an edit. **`CLAUDE.md` NOT TOUCHED**, treated as shared by judgment and said so. **`docs/sairn-path-manifest.json` NOT TOUCHED** (hank holds it) — which is why the b27 override could not be pruned, see §4.9. **No `.html`** (fourth's). **`docs/CRITICALITY-TIERS.md` NOT TOUCHED** (fourth's). **`api/_lib/law-roles.js` NOT TOUCHED** (hank's) — item 3's fix went in `api/_lib/countersign.js`, which no active claim holds |
| live writes | **NONE. Asserted, not intended.** `tests/rt_routes_live_probe.py` is read-only by construction and arm A4b re-reads the probe key afterwards and FAILS if a row appeared. It did not |
| SQL for Michael | **NONE.** No new `sql/` file. Both caps were raised to numbers the database **already** carries |

---

## 3. The two security defects, and why each was a pair

### 3.1 Item 3 — `api/_lib/countersign.js`: the role came from the token

**THE SENTENCE:** a signed token proves WHO ASKED and WHEN THEY SIGNED IN. It
cannot prove what they may do NOW, because it was minted before now.
**Authentication survives in a token; authorisation does not.**

```js
// before
if (mode === MODE_PREPARED_ONLY && isSigner(profile, ctx.callerRole)) return null;
```

`ctx.callerRole` is `gateSession.role` — out of the signed session token, which
lives `SESSION_TTL_MS` = **12 hours** (`api/_lib/auth.js:104`). An attorney
demoted to paralegal went on writing `law_trusttx` with **no countersignature
and no second person** until the token expired. The firm does the one thing it
can do about someone it no longer trusts with client money, and the platform
honours yesterday's answer until tomorrow.

**THE SECOND HALF, AND IT IS THE SHARPER ONE.** The SETTLING STEP exists
because *"between the signature and the write the world has up to TOKEN_TTL_MS
to move"* — and it selected `employee_id` under `active=eq.true`. **A struck-off
attorney who is still on the payroll is `active`.** The one check that did reach
the database was asking the wrong column.

**THE FIX.** One helper, `currentStanding()`, with three outcomes and not two:
503 could-not-read, 403 no-active-row, or the role the roster holds **now**.
Called from both places. The settling step now asks `isSigner` of the
countersigner and `isPreparer` of the preparer — **two different questions**,
because asking `isSigner` of both would refuse every paralegal-prepared record,
which is the normal C2 case.

**IT ONLY EVER REFUSES MORE, AND THAT IS A DECISION.** The roster role is
required **in addition to** the token role, never instead of it. A paralegal
*promoted* to attorney who has not signed in again is still refused, with
`COUNTERSIGN_REQUIRED` and its obvious remedy — unchanged from before b28. Arm
**R3** asserts exactly that and goes red if someone "tidies" it into reading
authority purely from the roster, which would widen who can write from a path
that refuses today. A security fix is the wrong place to smuggle that in.

**AND IT FAILS CLOSED, DIFFERENTLY FROM THE CHECK ABOVE IT.** `api/sd-data.js`'s
per-request active re-check LOGS and CONTINUES when the roster is unreadable
(*"NO_ACTIVE_CHECK … NOT an admission"*). Right for a request something
downstream will still gate; **wrong here, because this IS the downstream gate
and the write is money out of a client trust account.** Arm R4 drives it: 503,
never the token's word as a fallback.

### 3.2 Item 4 — the payload cap was right about slabs and wrong about the platform

`api/sairndental/public-book.js` accepts **1.2MB** of patient photos on an
unauthenticated self-scheduled booking and writes them into `dnt_appointments`,
whose DB constraint was raised to **1,291,059** for exactly that reason.
`api/sd-data.js` capped **every** write at 65,536.

**WHAT THAT COST IS NOT "LARGE PHOTOS ARE REFUSED".** The booking lands, as
designed. Then the staff open it: `sairndental.html`'s pending queue reads the
row whole, photos included, and sends it back on confirm or decline — so **every
staff write on a photo-bearing booking was 413 PAYLOAD_TOO_LARGE. Not
confirmable AND not declinable.** A real patient request parked in a queue
nobody can empty, under a size error that points at the staff member's click
rather than at the photo. **And the branch's own `validatePhotosPayload` 1.2MB
answer could never fire on size**, sitting behind a 64KB gate.

**THE OVER-WIDE SENTENCE, QUOTED FROM THE FILE:** *"there's no per-resource
override at the DB layer, so there can't usefully be one here either — this cap
stays uniform across every resource."* **Right about `sd_slabs`. Wrong about the
platform**, and it became a platform-wide claim by sitting still. That line now
carries its own correction and points at the table below it.

**THE :9857 HANDLER WAS THE SAME DEFECT ONE APP OVER.** `rf_claim_photos`
answers 413 on a `rfcph_data_size` violation — a **1,572,864**-byte constraint —
and nothing behind a 64KB gate could ever violate it. Unreachable from above
AND from below. **The dead handler is how the second resource was found**, which
is the argument for not deleting dormant code until you know why it is dormant.

**IT IS STILL INERT AFTER THE FIX, AND THAT IS CORRECT RATHER THAN HALF-DONE.**
The API cap is now exactly 1,572,864 — the same number — so the API refuses
first with a clear 413 instead of an opaque Postgres error, which is the trade
the slabs paragraph records paying for the hard way. And the two measures are
not the same measure: the cap counts the **whole payload**, the constraint
counts `data` = `storedBlob(payload, ['id'])` with three fields promoted to
columns, a **subset**. So the handler is a drift backstop, and **arm R3 asserts
the ordering** (`api cap <= db constraint`) rather than leaving it to habit.

**EIGHT TABLES, NOT TWO. MEASURED:**

    grep -rhoE "constraint [a-z_]+ check \(octet_length\(data::text\) <= [0-9]+\)" sql/*.sql | sort -u

`dnt_appointments` and `rf_claim_photos` are fixed. **Six are not**, and the
sharpest is `rf_claim_agreements`, whose own schema comment says *"a captured
signature is an image, not app data, and must not be squeezed into the 64KB
ceiling"* — while the API squeezes it into the 64KB ceiling. §4.3 and
`docs/2026-10-20-cody-b28-notes.md` §3.3 carry the table. **Arm C7 PINS the
uncovered set at those six**, so closing one or adding a ninth both turn it red.

**`sd_locations` RUNS THE OTHER WAY** and is deliberately absent:
`sdlocations_data_size` is **16,384**, so the API already permits **four times**
what the database accepts. A fix there LOWERS a cap and can break a working
client. Arm C8 asserts its absence so it is not swept in as a seventh.

---

## 4. Open — every item, why, and the exact next step

### 4.1 → hank. `api/b19-iolta-reconcile-carveout.test.js` R2c + A1 are RED at HEAD

**NOT CAUSED BY b28, PROVED NOT ASSUMED:** `git stash push api/_lib/countersign.js`
then re-run gives the identical `32 passed, 2 failed / FAILED: R2c, A1`.

Both arms assert `LAW_RECONCILE_ATTESTATION.implemented !== true`, and hank's
`6bb2cbec8 feat(law-attest b23)` built the attestation. **That red is the
mechanism working** — the b19 comment at `:214` predicted it in writing. **Next
step: it is a POLICY question, not a re-aim** — "does `paralegal` go back on the
IOLTA reconcile list now the attestation exists?" Editing the assertion to
match is the decay those arms exist to prevent. `api/_lib/law-roles.js` is
hank's.

### 4.2 → cody, next batch. `api/b22-funeral-f1-f2-f3-wiring.test.js` D1 asks to be deleted

RED at HEAD, same stash check. The arm prints its own instruction: *"A FAILURE
HERE IS GOOD NEWS: it means the wiring landed. Do not silence it — delete this
arm and promote the F2/F3 arms above from module-level to handler-level."* b27
landed that wiring, so this is **cody's own** consequence. **Next step: both
halves together.** Deleting D1 without promoting the F2/F3 arms removes the only
thing asserting the wiring.

### 4.3 → cody. The six remaining oversized caps, `rf_claim_agreements` first

**Next step, per table:** confirm its write branch passes through the generic
gate in `api/sd-data.js`, confirm the client actually sends the large field,
confirm the DB number is current intent and not an abandoned plan, then add the
entry and **update `EXPECTED_UNCOVERED` in arm C7 in the same change** — C7 goes
red otherwise, by design. Not swept in because byte-identical is not
safe-in-context (item 7 of the cross-domain disciplines).

### 4.4 → cody or whoever owns `sd_locations`. The cap that over-permits

`sdlocations_data_size` = 16,384 vs a 65,536 API default. **Next step:** decide
whether the constraint or the cap is the intended number before changing either;
lowering the cap can refuse a write a client sends today.

### 4.5 → the owner of `tools/unproven_arm_check.py`. Two findings, not worked around

Full text in `docs/2026-10-20-cody-b28-currency-sweep.md` §3.3–§3.4. **A1 is a
false positive** against `tests/run_floor_layers_probe.py` (which does print the
unproven count at `:406` and does `sys.exit(3)` at `:413`). **A4 is cleared by
ANY durable write** — `tests/run_floor_layers_probe.py` clears it on a test
fixture at `:149` — so 5 of 9 files pass it without persisting a verdict.
**Next step:** A4 should require the durable write to be reachable from the
unproven path.

### 4.6 → Michael. The handoff naming convention describes 3 of 83 handoffs

**MEASURED, AND RE-MEASURED AFTER THE REBASE:** **83** files match
`SAIRN-handoff-<session>-b<NN>.md`; **3** match the documented
`APP-YYYY-MM-DD-subject-handoff.md`. `CLAUDE.md:33` tells a fresh session to
*"Sort by the date in the filename"* — **unexecutable for 83 of 86 files,
because there is no date in the filename.** A fresh session following it
literally finds three handoffs, none recent. **It was 80 before the rebase and
83 after**, so this is getting worse at roughly three files a day, and cc's b27
edit to `CLAUDE.md` touched the four deliverable rules and left this one.

**Not fixed, because it is not obvious which side is wrong** and both documents
are shared. Two opposite candidate fixes with pasteable text are in the sweep
§3.1; **the recommendation is Option A** — record the practice, since the scheme
in use is per-session and so cannot collide between sessions, and renaming 83
files to fix a sentence is the more expensive direction.

### 4.7 → cody. `SAIRN-ACTIVE-WORK-cody.md` is 795,238 bytes, 2.0× the ceiling

**Next step:** the split fourth already performed — `-closed-1.md` / `-closed-2.md`,
which is why fourth's live file is under. **Not done hurriedly at the end of a
batch:** a cut in the wrong place makes the history unsearchable in exactly the
way the ceiling exists to prevent.

### 4.8 → cody. My own rule compliance, measured

**16 of 23 cody digests exceed the 30-line rule** (b4 at 323 lines, 10.8×), and
**b27 wrapped at 92.0% context, not 80%**. b5–b10 were compliant, the rule broke
at b11 and never recovered. **Fourteen of my digests carry no `CONTEXT` line at
all, which is the worse number** — an unmeasured batch cannot be reported either
way. **AND BOTH RULES NOW EXIST IN WRITING, which they did not when either breach
happened.** The rebase before this push brought cc's b27, which added a *"Batch
deliverables"* section to `CLAUDE.md` naming the 80% trigger (with
`python tools/context_verify.py --digest-line` as the only thing that may write
a digest's `CONTEXT` line) and the 30-line cap (mechanically checked by
`tools/drive_upload_verify.py --max-lines 30`). **The sweep's §2 measured those
four rules as absent and was true when measured and false four minutes later** —
kept and marked rather than deleted, because that is the most useful thing the
sweep found: a snapshot of a five-session repository has a shelf life measured
in minutes. **b28's own digest used `context_verify.py`**, so from here the
figure is a tool's output rather than an estimate.

### 4.9 ~~→ hank holds it. The b27 path-manifest override is still there~~ — PRUNED

**CLOSED IN THIS BATCH, and the opening it took is worth recording.** b27's
handoff §6.9 said *"an override nobody prunes becomes an allowlist"* and then
could not prune it, because hank's active claim held
`docs/sairn-path-manifest.json`. **That claim has since expired and hank's b25
claim does not list the file**, checked with `sairn_claim.py list --full` rather
than assumed — so the prune happened here, in the same edit that declared b28's
paths. **Six of b27's nine paths are DROPPED**, not carried forward: b28 does not
touch them.

**REPLACED RATHER THAN EXTENDED, and that is the whole point.** An override list
that is only ever appended to becomes the split not existing, one batch at a
time. The new `_why` key says the next batch should replace it the same way, and
cites b27 as the evidence that *"remove it when the batch closes"* does not
happen on its own.

### 4.10 Still open from b27, unchanged

§6.2–6.7 of `SAIRN-handoff-cody-b27.md`: the three rollup findings routed to
fourth (fix proven, `PROBLEMS:14 → 9`), `leg_settings` in `LEG_RESOURCES` and
`prepare` as a declared verb routed to hank, the F2 livery grant,
the ten hanging suites (measured, undiagnosed), and the
`law_reconcile_role_vocab_check` re-aim target. **§6.1 and §6.8 are CLOSED.**

### 4.11 → Michael. Nothing is blocked on you and no SQL is owed

Both caps were raised to numbers the database already carries, so no migration
is needed. Three things want a decision rather than work: **§4.6** the naming
convention, **§4.1** the IOLTA paralegal policy question, **§4.4** which
`sd_locations` number is intended.

---

## 5. Verification — every line is a command that was run

```
EXIT=0  node --check  api/sd-data.js  api/_lib/countersign.js
                      api/_lib/dental-photo-validation.js  both b28 suites
                      tests/sairncare_compliance_window_boundary.test.js
EXIT=0  python -m py_compile docs/b27-logs/stable_last_line.py
                             tests/rt_routes_live_probe.py

EXIT=0  SD_LICENSE=SD-AUDIT-2026 SD_OWNER_PIN=... python tests/rt_routes_live_probe.py
        6 arms, LIVE, against https://sairn.vercel.app/api/sd-data
EXIT=0  node api/b28-role-from-token.test.js          15 arms, NEW
EXIT=0  node api/b28-photo-cap.test.js                13 arms, NEW
EXIT=0  node api/b18-countersign-lock.test.js         59, regression
EXIT=0  node api/b20-countersign-open.test.js         15, regression
EXIT=0  node api/b23-iolta-attestation.test.js        66, regression
EXIT=0  node api/b27-leg-settings.test.js             18, regression
EXIT=0  node api/sd-data-appointments-photos.test.js   3, regression
EXIT=0  node api/_lib/dental-photo-validation.test.js 26, regression
EXIT=0  node api/sairndental/public-book.test.js       7, regression
EXIT=0  node api/_lib/routes.test.js                  63, regression
EXIT=0  node api/sd-data-cross-tenant-dispatchers.test.js  418, regression
EXIT=0  node api/sd-data-leg-role-matrix.test.js      37, regression
EXIT=0  node api/sd-data-sv-role-matrix.test.js       33, regression
EXIT=0  node api/sv-witness.test.js                   41, regression
EXIT=0  node api/sairncare-witness.test.js            38, regression
EXIT=0  node api/sd-data-approvals.test.js            23, regression
EXIT=0  node api/b17-practitioner-role-maps.test.js   19, regression
EXIT=0  node api/fail-open-triage-2026-09-04.test.js  15, regression
EXIT=0  node api/sd-sub-data-auth-ordering.test.js    11, regression
EXIT=0  node tests/role_maps_have_no_prototype.js     13, the b27 guard
EXIT=0  python docs/b27-logs/stable_last_line.py --drive   12 of 12 (was 0 of 12)
EXIT=0  python tools/md_table_check.py                all files clean
EXIT=0  python tools/sairn_path_manifest.py --outgoing     39/39 arms
EXIT=0  python tools/live_probe_declaration_check.py       the new probe is readable
EXIT=1  python tools/tooling_inventory.py --standing-doc-sizes  8 over, as designed

RED AT HEAD, NOT CAUSED BY b28 -- each proved by stashing the b28 change and
re-running, which gave the identical result:
EXIT=1  node api/b19-iolta-reconcile-carveout.test.js  32/2, FAILED R2c A1  -> §4.1
EXIT=1  node api/b22-funeral-f1-f2-f3-wiring.test.js   17/1, FAILED D1      -> §4.2
EXIT=1  python tools/unproven_arm_check.py             5 findings, REPORT-ONLY -> §4.5
```

**THE ABLATION, PER ARM AND NOT PER EXIT CODE.** The b28 change was stashed and
both new suites re-run against HEAD:

| suite | against HEAD | with the fix |
|---|---|---|
| `b28-role-from-token` | R1 and S1 answered **200** — the demoted attorney's trust write LANDED, twice, by two different routes | 403, both |
| `b28-photo-cap` | **9 of 13 arms RED**; D1, D2, C5 and C8 green in **both** directions | 13 of 13 |

**D1/D2/C5/C8 green in both directions is the half that makes it a
measurement.** D1 and D2 are the 64KB default, unchanged; C5 is the SQL scan
finding anything at all; C8 is `sd_locations` staying out. If the fix had been a
global cap raise, D1 would have gone red.

**FOUR ARMS WERE WRONG ON THEIR FIRST SPELLING AND EVERY ONE FAILED LOUDLY
RATHER THAN PASSING QUIETLY.** Each is recorded at the arm:

1. **A5 of the live probe** asserted the rt_routes branch's terminal message
   against `action: 'frobnicate'` — which never reaches the branch, because the
   ACTION is whitelisted at the top of the handler. The arm was reading the
   **dispatcher's** refusal and would have gone green against a deployment where
   the branch does not exist. Re-aimed to `action: 'write'`, globally legal and
   not an rt_routes verb.
2. **R5 and R6/M2** named the wrong control. `api/sd-data.js` already re-reads
   the roster on **every** request for its active check, so R6/M2 counting
   `_employee_auth` requests reported a leak that was not there, and R5 credited
   b28 with a deactivation refusal that `CREDENTIAL_INACTIVE` already handles.
3. **P1, R1 and D2 asserted `statusCode !== 413`** — which passes on a 400 from
   any unrelated validator. Tightened to `=== 200`, and two of the three then
   failed: my fixtures used `phase: 'before'` / `elevation: 'north'` (not in the
   branch's vocabulary) and a patient with no adult `dob`. **"Some answer that
   was not a size refusal" is not "the staff member can confirm this booking".**
4. **`py_insert_line`'s own docstring** contained a literal triple-quote while
   explaining why a parser is needed to find one. It would not compile. The tool
   refused to run at all, which is the right direction to fail in.
5. **`LIVE_PROBE_CLASS = 'read-only'`** — honest prose, and not one of the three
   values `tools/live_probe_residue_audit.py` accepts. **The pre-commit gate
   REFUSED the commit** and it was right twice over: the auditor matches
   `'action': 'write'` in source, and arm A5 posts exactly that, deliberately,
   because `write` is the only globally-legal verb that is **not** an rt_routes
   verb and so the only input that reaches the branch's terminal refusal. **A
   source scan cannot tell a write that is SENT from a write that is ASSERTED TO
   BE REFUSED, and it should not guess.** Re-declared `VERIFICATION` with the
   residue line saying in full why the refused write leaves nothing; audit now
   exit 0.

---

## 6. Item 5's second half — the hook at the TOP, and b27 was wrong twice

```
python docs/b27-logs/stable_last_line.py --drive
-> 12 of 12 subjects now end with SUITE-RESULT      (b27: 0 of 12)
```

b27 appended the hook to the END of each file, drove it, measured 0 of 12 and
**reverted rather than leave a committed fix that does nothing.** Two
independent errors, and the second is the one worth keeping:

1. **UNREACHABLE.** These probes call `sys.exit(...)` at **module level**.
   `SystemExit` propagates out of the module body, so every line below it —
   including the `atexit.register()` call — never executes.
2. **THE REASONING WAS ALSO BACKWARDS.** b27's comment read *"the end of the
   file is the earliest registration, so it fires last."* It is the **latest**
   registration. `atexit` runs handlers in **reverse** order, so the end of the
   file would have printed the line **before** every cleanup handler even if it
   had run. **Top placement is correct on both counts:** it is reached, and
   being the first registration it fires last.

**"THE TOP" IS COMPUTED, NOT LINE 1.** A Python docstring must stay the first
statement or it stops being a docstring — and `tools/live_probe_declaration_check.py`
reads these docstrings. A JavaScript `'use strict'` must stay first in its
prologue or it **silently stops applying**, which would change the semantics of
the suite under test. So: `.py` → after the docstring, located with `ast`;
`.js` → after the directive if there is one.

**FOUR POST-CONDITIONS, AND ONE OF THEM IS b27's DEFECT AS A REFUSAL.**
`assert_reached()` refuses to write any file where the hook would land after a
module-level exit — re-checked on the **result** text, not inferred from the
input. b27 could assert *"the original is a PREFIX of the result"* because it
appended; an insert cannot, and the weaker *"the file got longer"* is what let an
earlier sweep delete 1,465 lines with a green assertion. So the hook is
**removed from the result and the remainder must equal the original byte for
byte**, plus the result must `compile()`, plus the marker must appear exactly
once.

`docs/known-red-suites.json` is updated: all 12 rows now carry a tail the runner
really produces, with `tail_before_b28` keeping each previous value.
`tail_verdict_2026_10_19` is **left alone** — it is a dated verdict about
2026-10-19 and the tool selects its subjects by it. **One subject drove exit 0**
(`tests/run_selftest_independence_probe.py`), recorded as observed rather than
reclassified: RECOVERED is `tools/known_red_check.py`'s verdict to make from a
real run, not this file's.

---

## 7. The push — FOUR GATES REFUSED AND ALL FOUR WERE SATISFIED AT CAUSE

**NOTHING WAS OVERRIDDEN. No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no
`SAIRN_SEED_GATE`, no call to `tools/gate_skip.py`.**

1. **`derived-docs`** — `docs/MASTER-PLAN.md`, `docs/TOOLING-INVENTORY.md` and
   `docs/traceability-matrix.md` stopped matching their sources at this tip.
   Regenerated with the three generators the refusal names. **Twice**: two of
   them conflicted on the second rebase, resolved by taking the UPSTREAM side,
   asserting zero conflict markers, and **regenerating afterwards** — a
   generated document is never merged by hand, and `git add` on a conflicted
   file is how you RESOLVE one, so it cannot tell "resolved" from "never
   looked". That is b27's 15-conflict-markers defect, avoided by naming the two
   files explicitly instead of `git add -A`.
2. **`tier-a`** — six Tier A resources with no open obligation
   (`dnt_appointments`, `dnt_patients`, `rf_claim_agreements`,
   `rf_claim_photos`, `rf_invoices`, `rf_proposals`; five more were already
   covered). **Obligation OPENED**, assigned to hank, naming **five things to
   try to break** rather than a summary — including the claim that four of the
   six are named only because the drift arms MENTION them and no code serving
   them changed, which is exactly the kind of claim a reviewer should check
   against the diff rather than take on my word.
3. **`path-scope`** — resolved by the manifest, not a skip. See §4.9: the b27
   override **replaced**, six paths dropped, `api/_lib/countersign.js` declared
   with the reason it is not one of hank's `api/*-countersign.js` endpoints.
   Re-measured after: **31 of 31 paths IN SCOPE.**
4. **`register-feed` could not tell what was being pushed** — a clone 3 ahead
   and 11 behind, so git was about to refuse the non-fast-forward itself and the
   hook got no ref lines. **Not a finding about the commits**, and the gate says
   so. Fixed by `git pull --rebase origin main`.

**AND ONE PRE-COMMIT GATE, before any of these:** the live-probe residue audit
refused `LIVE_PROBE_CLASS = 'read-only'` — see §5, item 5. Re-declared
`VERIFICATION`; audit exit 0.

**ONE THING IS LEFT ON THE TREE AND IT IS RECORDED RATHER THAN HIDDEN.** The
push gate writes its own `docs/scrutiny-flags.json` row on each attempt. It was
stashed once to allow a rebase, then committed with the batch, so it is content
in this push rather than a dirty tree — unlike b27, which left it as a stash
entry for the next session to drop.

## 8. Scratch, transcript and where the detail is

* **Concepts, the pattern, and every routed finding:**
  `docs/2026-10-20-cody-b28-notes.md`
* **The currency sweep, seven findings with pasteable text:**
  `docs/2026-10-20-cody-b28-currency-sweep.md`
* **The live probe:** `tests/rt_routes_live_probe.py` — read-only, needs
  `SD_LICENSE` and `SD_OWNER_PIN`
* **The measurement of item 5:** `docs/b27-logs/stable_last_line.json`
* **Transcript:**
  `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\cc73112b-c907-4081-b7af-37c09862bb32.jsonl`
  — this session carries **b28 only**, which is unusual and worth saying: b26 and
  b27 shared one transcript, so this is the first b-batch in a window of its own.
* **`SAIRN-digest-cody-b27.txt` was untracked and is committed in this batch.**
  b27's wrap-up wrote it and never committed it; it is b27's content, not b28's,
  and is included rather than left to look like an uncommitted leftover.
