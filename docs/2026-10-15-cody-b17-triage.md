# The 30 remaining `tests/` failures, triaged by READING EACH SUBJECT

**cody b17, 2026-10-15.** b15 triaged 39 failures from a full-tree run and
routed 34 of them on each file's **last output line**. b16 took the first
cluster by reading the subject and found three of four were the probe
misreading its own subject. **b17 took the remaining 30 the same way, and the
pattern held harder than b16 expected.**

**EIGHT of the 30 are closed at cause and verified green.** One further suite
was repaired that was not on the list and was never red — it was passing on a
comment.

---

## 0. The headline, because the count is not the finding

> **Of the failures b17 reached, the single largest cause is a probe whose
> anchor stopped matching its subject — SIX files — and the second largest is
> an operator decision Michael took on 2026-10-11 that four probes report as a
> defect in the thing they guard.**
>
> **Not one of the 30 turned out to be a live defect in `api/` that b15's
> last-line triage had named correctly.** Two were api/-shaped and real, and
> both are different from what b15 routed.

The method difference is measurable. b15 read `8. app_id is taken from the
client again` and routed a tenancy emergency; it was a mutation label. b17 read
`active-credential re-check DID NOT RUN` on five arms that all say `ok`, and
found the one real failure was an assertion naming an identifier that a
**security tightening** had removed.

---

## 1. Current state, measured — not carried from b15

All 36 files from b15's `tests/` list were run **once each, in an isolated
`git worktree` at `084f9df8`**, 200s per file, exit code read from
`echo "EXIT=$?"` on its own line. Then each failure's subject was read.

| | count |
|---|---|
| run | 36 |
| exit 0 already (b15/b16 fixes landed) | 0 |
| non-zero | 35 |
| TIMEOUT at 200s | 1 (`run_capa_fields_probe.py`, rc 124) |
| **closed at cause in b17 and re-verified green** | **8** |
| routed with an owner and a next step | 22 |

`docs/2026-10-15-cody-b15-fulltree-triage.md` says 36 for `tests/`. Counting
its own rows gives 38 once the two files it fixed in-batch are added. **The
discrepancy is NOT resolved here and the number is not quoted as if it were:**
b17 ran the 36 paths that document names and reports on those.

---

## 2. CLOSED AT CAUSE — eight files, each verified green after the fix

Every exit code below was read without a pipeline.

| file | was | now | the cause, read from the subject |
|---|---|---|---|
| `tests/sairnbuild_backup_pending.js` | 8 FAIL + **TypeError crash at :241** | **exit 0, 29/0** | the harness never declared `BLD_SESSION_REQUIRED`; see §3 |
| `tests/sairnbuild_fault_probe.py` | exit 1, 2 failures | **exit 0, 0 failures** | **recovered by itself** when the file above was fixed |
| `tests/sd_data_family_mar_gate.js` | 9 passed, 1 failed | **exit 0, 10/0** | arm C1 asserted an identifier a security tightening removed; §4 |
| `tests/run_sv_session_gate_sabotage_probe.py` | exit 1, **arms 5 and 7 ANCHOR-0** | **exit 0, 7 arms CAUGHT** | the gate block grew from 6 lines to ~68; §5 |
| `tests/run_leg_session_gate_sabotage_probe.py` | exit 1, **arm 5 ANCHOR-0** | **exit 0** | identical rot, third file; §5 |
| `tests/run_sairnbuild_server_wins_sabotage_probe.py` | exit 1, **arm 6 ANCHOR-0** | **exit 0** | the retry's 4th argument was generalised; §6 |
| `tests/run_python_escape_hygiene_probe.py` | exit 1, **ANCHOR-2** | **exit 0, 9/9** | `"import os"` matched `import os as _os` too; §7 |
| `tests/run_mutation_anchor_probe.py` | exit 1, arm 7a | **exit 0** | **the same one anchor** as the row above; §7 |

**And one repair that was not on the list:** `tests/sairnbuild_server_wins.js`
was **exit 0 the whole time and was not testing anything** — §6.

---

## 3. Cluster 4, the `sairnbuild` pair — one undeclared identifier turned the
   whole backup off, silently

**Taken first, as instructed, and the crash was not the defect — it was the
only visible symptom of it.**

`tests/sairnbuild_backup_pending.js` crashed at `:241` with
`TypeError: Cannot read properties of undefined (reading 'payload')`. Reading
the log rather than the last line: **every push count was `0`, from the very
first arm.** `srv.writes.length` expected 1, actual 0. The retry had nothing to
send because nothing had ever been sent.

The chain, each step measured in `sairnbuild.html`:

1. `:2369` — `var BLD_SESSION_REQUIRED = { bld_bids: true, bld_draws: true };`
   was added after this test was written.
2. `:2425` — `bldSyncCollection` now calls
   `bldData('write', key, r, !!BLD_SESSION_REQUIRED[key])`.
3. The test's `build()` sandbox declares `BLD_SYNCED`, `_bldBackup`,
   `BLD_PENDING_KEY`, `BLD_PENDING_MAX`, `bldSeeding` and a hand-built
   `BLD_PENDING_TRACKED` — **and not `BLD_SESSION_REQUIRED`.** So the
   identifier was undefined and the reference **threw**.
4. `:2109` — `st()` wraps the call in **`try{bldSyncCollection(k,v,prev);}catch(e){}`**,
   a bare swallow. The throw vanished.
5. Result: the backup did nothing and reported nothing. Eight arms failed
   saying "the queue is empty", which is **true and means the opposite of what
   it reads as**, and the ninth crashed on the empty array and took six
   further arms with it.

**FIXED** by adding `decl('BLD_SESSION_REQUIRED')` to the extraction list —
extracted, not transcribed, for the same reason the rest of the harness uses
`decl()`/`fn()`. And a **precondition** was added at `:241`
(`srv.writes.length > 0`) so this shape can never again cost the arms below it:
a crash there reported one TypeError instead of nine failures, and the cause
was read as a sairnbuild retry bug rather than a harness that never pushed.

**→ WHOEVER OWNS `sairnbuild.html` — A READ, NOT A REQUEST, and it is the real
finding of this cluster.** `st()`'s `try{...}catch(e){}` at `:2109` silently
swallows **every** error in the entire server-backup path. This test proved
what that costs by accident: one undefined identifier turned the whole feature
off and the only symptom was "nothing to back up". In the live app the
identifier is declared, so there is no bug today — but any future throw inside
`bldSyncCollection` (a JSON edge case, a renamed map, a changed helper)
produces exactly the same silence, in the feature that exists *because*
silently-failing backups cost real records. **NEXT STEP:** decide whether that
`catch` should re-raise, `console.error`, or mark the collection pending; a
`catch(e){}` guarding a data-loss feature is the pattern
`sairn-silent-failure-sweep` exists for.

---

## 4. Cluster 2, the active-credential pair — b15's shared cause is REFUTED on
   the `tests/` half

**`active-credential re-check DID NOT RUN for app "sairncare" (NO_ACTIVE_CHECK)`
appears five times in `tests/sd_data_family_mar_gate.js`'s output and EVERY ONE
of the five arms printing it says `ok`.** It is diagnostic stderr from the
stubbed handler, not a verdict. b15 read it as the failure and routed a shared
cause to hank on that basis.

The one real failure was **arm C1: "the role gate must precede the consent
check"** — and `C0` had already confirmed the source anchor matches exactly
once, so C1 was measuring the right region. Measured against `api/sd-data.js`:

```
anchor "if (action === 'family_mar')" : 1 occurrence
'marBroad'                in branch   : True
'ALF_FAMILY_READ_ROLES'   in branch   : False   <-- the whole failure
```

`ALF_FAMILY_READ_ROLES` is gone from that branch **because the role set was
deliberately split.** `api/sd-data.js:13353` now reads
`const marBroad = !!ALF_FAMILY_MAR_ROLES[session.role];`, and the comment at
`:13182` says why: *"`family_mar` inherited ALF_FAMILY_READ_ROLES = { owner,
billing, nursing }"* — and `billing` had no business reading a medication
record.

**So the arm was failing on a security tightening.** FIXED by asserting the
**property** instead of the name — `/const marBroad = !!ALF_[A-Z_]+ROLES\[session\.role\]/`
— so which map it is remains a product decision that may change without this
file going red. **exit 0, 10 passed, 0 failed.**

**→ HANK, and it is NOT the same cause.** `api/sd-data-law-trusttx-session.test.js`
is still red on its own: driven as the baseline of
`tests/law_trusttx_session_probe.py` it reports **9/10 passed** with
`active-credential re-check DID NOT RUN for app "sairndental" (NO_ACTIVE_CHECK)
on law_trusttx/read`. **Note the app: `sairndental`, not `sairncare`.** The
`tests/` half and the `api/` half were never one fix.
**NEXT STEP:** drive `api/sd-data-law-trusttx-session.test.js` alone and fix
the pre-gate for `sairndental`; `tests/law_trusttx_session_probe.py` recovers
by itself the moment it does.

---

## 5. Cluster 5 and cluster 3 collapse into ONE cause — a gate block that grew

**b15 said: "both are statements about `api/` gate placement. VERIFY AGAINST
`api/sd-data.js` BEFORE ROUTING." Verified. Neither is.**

Both failure lines are **MUTATION LABELS** — text the probe prints while
*planting* the defect, exactly as b16 found for `sairnlegacy_fault_probe`. And
for the `sv` probe the mutation **was never applied at all**:

```
run_sf_..._probe: arms 1-7 anchors -> count=1 each.  All applicable.
run_sv_..._probe: arm 5 -> count=0   ANCHOR-0
                  arm 7 -> count=0   ANCHOR-0
```

**The cause, measured.** Arms 5 and 7 quoted the **whole** SV gate block —
6 lines, including a 150-character user-facing message string. On **2026-10-14**
that block GREW: fourth b15's role table (`svRoles.decide`) and the
append-only check landed **inside** it. `api/sd-data.js:14900` to `:14961` is
now ~68 lines, with the read branch at `:14962`. The 6-line anchor matched
nothing, and the probe printed its labels anyway. The arm-5 comment already
recorded a **2026-09-25** re-derivation for the same reason — this is the
second rot of the same anchor, and the first fix was "a shorter block".

**`tests/run_leg_session_gate_sabotage_probe.py` is the same defect in a third
file** — and it is also **one of cluster 3**. b15 recorded it as baseline-red
(exit 2, do not touch); measured today it is **exit 1**: its baseline recovered
and it now has one failing arm, `5. THE GATE MOVES BEHIND THE QUERY`,
**ANCHOR-0 in `api/sd-data.js`**, LEG gate block `:15751`–`:15795`, read branch
`:15796`.

**FIXED, and the lesson taken is not a shorter block — it is NO block.** Both
arms in both files now use the harness's **paired-anchor** form (two short
`(find, replace)` edits, which `tests/sabotage_harness.py:407` has supported
all along):

* edit 1 — the front gate stops covering the branch being attacked
* edit 2 — a `401` appears in that branch **after** its fetch has already run

Neither anchor contains anything that is free to grow between them, which is
the property. **`sv` → exit 0, all 7 arms CAUGHT. `leg` → exit 0.**

### And a second defect in the `sv` probe, found by reading it

**`tests/run_sv_session_gate_sabotage_probe.py` had no `if __name__ ==
'__main__':` guard.** `sys.exit(run_probe(...))` sat at module level, so merely
**importing** the file — which any inventory tool, collector or triage script
does — drove a seven-arm sabotage run that writes `api/sd-data.js` in place and
then `sys.exit`ed the importer. Found by doing exactly that: a read-only
uniqueness check on its mutation list **executed the probe**. It restored the
file and said so, which is the only reason this was a scare. **Guard added.**
`tools/mutation_anchor_check.py` now reports *"probes that mutate in place and
do NOT refuse an import: 0"*.

### `tests/run_sf_session_gate_sabotage_probe.py` — the one real `api/` defect
### in cluster 5, and it is a SUITE gap

All seven anchors are good; arm 6 reports **`SILENT — the suite passed with
this defect planted`**. The planted defect adds `sf_officers` and `sf_tickets`
to `SD_SESSION_GATED`.

**→ HANK.** `api/sd-data-sf-session-gate.test.js` asserts that each approved
resource **IS** gated and never that an unapproved one is **NOT**, so the gate
can WIDEN past what was approved and every assertion still passes.
**NEXT STEP:** add one arm asserting **set equality** between the gated set and
the approved set, not per-resource membership. Then re-run
`python tests/run_sf_session_gate_sabotage_probe.py` and arm 6 must flip to
`ok`.

### The other two of cluster 3 — still COULD NOT RUN, and the owners differ

| probe | exit | its baseline | recovers when |
|---|---|---|---|
| `tests/law_trusttx_session_probe.py` | 2 | `api/sd-data-law-trusttx-session.test.js`, **9/10** | **→ HANK** fixes the `sairndental` pre-gate (§4) |
| `tests/run_server_wins_hydration_sabotage_probe.py` | 2 | **`tests/server_wins_hydration.js`, 178 passed 1 failed** | **→ CODY** — the baseline is a `tests/` file, so this one does NOT recover from anyone else's work |

**Correction to b15 on cluster 3:** it said all three "recover BY THEMSELVES
when their baseline is fixed — do not touch the probes." Measured: one had
already recovered its baseline and needed its *probe* fixed (leg, §5), one
waits on hank, and one waits on **cody's own** `tests/server_wins_hydration.js`.
"Do not touch the probes" was right for two of three.

---

## 6. `tests/sairnbuild_server_wins.js` — an assertion that was passing on the
   comment documenting its own obsolescence

**Not on the list of 30. Exit 0 before and after. It was not testing
anything.**

Repairing arm 6 of `run_sairnbuild_server_wins_sabotage_probe.py` turned it
from **ANCHOR-0** into **SILENT**, which is strictly more informative: the
mutation now applies and the suite does not catch it. Reading the suite:

```js
// tests/sairnbuild_server_wins.js:420, before
assert.ok(body.indexOf("key==='bld_bids'") !== -1,
  'the retry sends bld_bids without a session, which its branch refuses');
```

`bldRetryPending` no longer contains that expression — it passes
`!!BLD_SESSION_REQUIRED[key]`. The literal still occurs **twice** in
`sairnbuild.html` and **both are COMMENTS**, one of them at `:2534`, **inside
that very function**, written to explain that the old form *"used to read
`key==='bld_bids'`, which was right until there were two."*

**The assertion was satisfied by the comment documenting the removal of the
thing it was asserting.** Two layers of guard — a suite and a sabotage probe —
and neither guarding, for the same root reason.

**FIXED:** the assertion now runs over **comment-stripped** source and requires
a fourth argument at the call site, which a comment cannot satisfy and a rename
does not break. Suite **25 passed, 0 failed**; sabotage probe **exit 0, arm 6
CAUGHT**. Verified failing-first in both directions.

---

## 7. One anchor, two red files — and the whole repo's anchors are now clean

`tests/run_python_escape_hygiene_probe.py` arm 2 anchored on the bare string
`"import os"` in `tests/claims/run_freshness_probe.py`. That file has **two**
matches — `import os` at `:65` and **`import os as _os` at `:81`, which
contains the first as a substring** — so the arm refused with **ANCHOR-2**.

It was **the single stale anchor in the repository**:

```
$ python tools/mutation_anchor_check.py      # before
  probes with a MUTATIONS list : 76
  anchors checked              : 530
  anchors NOT matching exactly once: 1
      ANCHOR-2 in tests/claims/run_freshness_probe.py
EXIT=1
```

And it is why `tests/run_mutation_anchor_probe.py` arm 7a was red — **one
anchor, two of the 30.** Re-anchored on two consecutive import lines, which no
`as` alias can be a substring of, and the replacement now keeps `import os`
rather than swapping it for `import io`.

```
$ python tools/mutation_anchor_check.py      # after
  anchors checked              : 530
  anchors NOT matching exactly once: 0
EXIT=0
```

**A measurement note worth keeping:** the first reading of this gave
`EXIT=0` — because it was taken from `python ... | tail -25; echo "EXIT=$?"`,
where `$?` is **tail's**. Exactly the defect already recorded for backgrounded
compound commands, in a plain pipeline. Every exit code in this document was
re-taken without one.

---

## 8. THE HOOKS CLUSTER — four probes reporting an operator decision as a defect

**One cause, four files, and the fix is explicitly NOT to restore anything.**

`.claude/settings.json` and `~/.claude/settings.json` both carry `hooks: {}`.
The committed `_hooks_note` says why, verbatim:

> *"The 23 hooks Michael cleared on **2026-10-11** because they were causing
> agent compaction stay cleared and are recorded verbatim in
> `docs/hooks-disabled-2026-10-13.json`."*

| file | what it reports | and the state really is |
|---|---|---|
| `tests/hook_command_anchoring_probe.py` | FAIL `settings.json declares hooks at all` · FAIL `the anchored form is actually in use (0 command(s))` | there are no hooks to anchor |
| `tests/run_conflict_preflight_hook_probe.py` | FAIL `conflict_marker_preflight_hook.py is registered in .claude/settings.json` · FAIL `...as a PreToolUse hook` | the registration was deliberately removed |
| `tests/run_tooling_inventory_probe.py` | FAIL `ADVISORY is non-empty (0)` · FAIL `a SessionStart hook is ADVISORY` | the classification has an empty population |
| `tests/run_closing_error_probe.py` | FAIL `tooling_inventory.hooked -> no hook entries in settings.json: REFUSES with exit 2 (got 0)` | **see below — this one is a real tool defect** |

**→ CODY, for the first three. The failure is correct as an observation and
wrong as a verdict: these are COULD NOT RUN, not FAIL.** A probe cannot test
hook anchoring when there are no hooks, and reporting FAIL conflates *"the
anchoring is wrong"* with *"there is nothing to anchor"* — PR §1.11's third
state, in the direction that over-reports rather than under-reports, which is
the safe direction but still wrong.
**NEXT STEP:** each of the three gets an explicit precondition that exits **3**
naming `hooks: {}` as the reason, with the `_hooks_note` quoted. **Do not
restore a hook and do not commit `settings.json`.** Also note
`hook_command_anchoring_probe.py` passes `no hook command resolves a repo
script relative to the cwd (0 bare)` **over a population of zero** — a vacuous
pass that b15 already flagged on this file, and it must become exit 3 in the
same change.

**→ CC, for `run_closing_error_probe.py`, and the probe is RIGHT.** The arm
asserts that `tools/tooling_inventory.py --hooked` **refuses with exit 2** when
there are no hook entries, **and it got 0.** A tool that answers success on an
empty population is a fail-open, independent of the hooks decision and true
whatever Michael decides about hooks.
**NEXT STEP:** make `--hooked` refuse (exit 2) on an empty hook set and say
which source was empty; the probe's other two arms
(`writes NO document rather than a thinner one`, `says which source was empty`)
are the same defect's other halves and will close with it.

---

## 9. The two claims probes — an intentional policy change, with a question
   that has to be answered before the probes are touched

| file | failing arms |
|---|---|
| `tests/claims/run_own_claim_overlap_probe.py` | `fourth incident: same subject, PUBLISHED earlier claim -> REFUSED` · `a shared phrase refuses` · `...and BOTH live incidents are among them` |
| `tests/claims/run_claim_audit_probe.py` | `a session holding many ACTIVE claims is reported` · `...and it exits non-zero, because a phantom block is a real cost to another session` |

Both assert `rc == 3` (REFUSED) on a **retyped task string**. `tools/sairn_claim.py`
was deliberately changed:

```
9b0bfd51  fix(claim matcher): the declared FILES set is the PRIMARY mode --
          two words about WHEN work happens stopped refusing a claim that had
          already said in paths WHAT it touches
```

Confirmed live in this very session: claiming `tests` against fourth's active
claim answered **`CLEAR ON WORDS -- AND THE FILE OVERLAP COULD NOT BE PROVEN
EITHER WAY`**. A word overlap alone no longer refuses.

**→ CC FIRST, THEN CODY, and the order matters.** There are two readings and
the probes cannot tell them apart:

1. the policy change is right and the probes assert superseded behaviour; or
2. the change re-opened the two historical incidents these probes exist to hold
   shut — a retyped task over **disjoint** files now goes through.

**NEXT STEP (CC):** take the two real incidents' actual task strings **and
their FILES lists** and run them through the current matcher. If they still
refuse, reading 1 is right. If they do not, `9b0bfd51` needs a narrowing and
the probes were the thing that noticed.
**THEN (CODY):** re-derive both probes' fixtures against whichever policy
stands — under FILES-primary a word-only overlap fixture is asserting a rule
that no longer exists.

---

## 10. `tests/run_capa_fields_probe.py` — the tree-dirtier is ATTRIBUTED, and
   it was never a hang

**Fixed the cleanup first, as instructed. Measured answer: the cleanup was not
the cause of the timeout, and the timeout was not a hang.**

| | before | after |
|---|---|---|
| exit | **rc 124 at 201s** | **completes, exit 1** |
| its own log | **0 bytes** | 517 arm lines |
| `git status --porcelain` | **`?? docs/_capa_probe_tmp.json`, 2,461,216 bytes** | **clean** |

Three separate things, each measured:

1. **The tree dirt.** It wrote a whole 2.46MB copy of the real defect register
   to `docs/_capa_probe_tmp.json` — **inside the repository** — and removed it
   in a `finally` at the bottom of the file. **A `finally` does not run when
   the process is killed**, and this probe was being killed. So every timed-out
   run left 2.46MB of untracked JSON in `docs/`. **This is the dirtier b15's
   full-tree run could see and could not name.** FIXED by moving the copy to a
   `tempfile.mkdtemp()` outside the repo — `defect_register` resolves its
   register as `os.path.join(REPO, REG)` and `os.path.join` returns an
   absolute second argument unchanged, so the tool needed no change. **A kill
   can no longer dirty any clone, which is stronger than a cleanup path that
   has to be reached.**
2. **The zero-byte log.** stdout is block-buffered when redirected, so a run
   killed at the ceiling wrote **nothing at all** and a hang was
   indistinguishable from a silent pass — discipline 10, in the small. FIXED
   with a `sys.stdout.flush()` per arm.
3. **The runtime.** It was never hung: it finishes between 200s and 420s. The
   cost is structural — `with_register()` deep-copies and **re-writes the
   entire 2.46MB register, then runs `cmd_check()` over all of it, once per
   arm**, about fifteen times. **→ CODY, NOT FIXED.** **NEXT STEP:** build the
   mutant from a small fixture register carrying only the records the arms
   touch, with one arm pinned against the real one so the fixture cannot drift
   into testing nothing.

**→ WHOEVER WROTE THESE ROWS. Seven real failures survive, and they are
register CONTENT, not the probe.** Six records are named:
`31406a87e010`, `44abebb30bf5`, `4f69facd93b3`, `9841e14a5eaa`, `d6e58c61766a`,
`e3858f19aad8` — each *"`recurrence_open` states a residual rather than
dismissing one"*. **NEXT STEP:** `git log -S<hash> -- docs/defect-density-register.json`
names the author of each row; the field has to say what is still latent, not
that nothing is.

---

## 11. The remaining 18, routed — failure line measured today, owner, next step

Not read to the depth of the clusters above. **Each line below is the measured
current failure, not b15's; where the two differ it is said so.**

### → CODY (13)

| file | measured now | next step |
|---|---|---|
| `tests/server_wins_hydration.js` | 178 passed, **1 failed**: `[sairnlegacy] the transport records an id when a WRITE really lands` | **take this first of the 13** — it is also the blocked baseline of `run_server_wins_hydration_sabotage_probe.py` (§5), so one fix closes two |
| `tests/run_tier_a_open_basis_probe.py` | **9/30 arms pass** (5 fail-first fixture, 24 real record) — b15 said 10/27, so the arm count GREW and the pass count FELL | largest single gap; the 5 fail-first arms pass, so the harness works and the 24 real-record arms disagree with the record's current shape. Drive one real-record arm alone and read what it expects |
| `tests/run_known_red_probe.py` | 7 failures, all `COULD NOT RUN: the log says 66 FAILING TEST FILE(S) and 64 FAIL lines were parsed` | **the TOOL is right and refusing correctly.** The probe's own fixture log has a header count 2 higher than its FAIL lines. Fix the fixture, not `known_red_check.py` |
| `tests/run_claim_doc_freshness_probe.py` | 4 arms incl. `after every mutation was reverted, clean fixtures still exit 0` | that last arm is a **restore** failure — the probe does not put its fixtures back. Fix the restore before reading the other three |
| `tests/run_condition_coverage_sandbox_probe.py` | 7 passed, 3 failed: `A2. the tool must still be running when it is killed` | timing-dependent arms; re-run three times before touching anything and record whether the failure is stable |
| `tests/run_fail_open_probe.py` | `THE CONTROL: audit tool present and CLEAN -> runs and allows` | **a CONTROL failing**, so nothing else in the file means anything. Fix the control first |
| `tests/run_register_feed_gate_probe.py` | 47 passed, 3 failed, incl. **two CONTROLs** (`an EXISTING remote branch is still rsha..lsha`, `a good ref line first still yields its range`) | same rule: the two controls first |
| `tests/run_batch_cleanup_probe.py` | 32 passed, 3 failed: `MY OWN file survives while the push has NOT landed` | the arm is about scratch retention before a push lands; read the tool's current retention rule before changing the arm |
| `tests/run_out_of_service_probe.py` | 13 passed, 2 failed: `the shipped register is clean (exit 1)` | a baseline arm over the live register; likely the same register-content failures as §10 |
| `tests/run_audit_event_type_probe.py` | 10 passed, 1 failed: `H0. the AUDIT_TABLES allowlist is found and parsed at all` | **H0 is a precondition arm** — the allowlist is not being found, so the two arms below it are vacuous. Re-derive the parse |
| `tests/run_batch_manifest_probe.py` | 40 passed, 1 failed: `...and every fixture ran` | a coverage arm, not a behaviour arm |
| `tests/run_estimate_fusion_probe.py` | 1 failure: `...and --quiet really is quiet` | smallest item here |
| `tests/mech_docs_redaction_wiring_probe.py` | 1 failure: `7. saveDoc no longer says "Saved on this device" while syncing` | a claim about app code; **verify against the app before routing** — §3, §4 and §5 are all cases where this exact shape was the probe |

### → CODY, could-not-run rather than failing (2)

| file | measured now | next step |
|---|---|---|
| `tests/run_dead_rule_sweep_probe.py` | **exit 2**, `A1c. ...the COPY passes the lock before anything is done to it` and `D1. it reads a NON-EMPTY rule list` | A1c is the copy-integrity precondition; D1 is the non-vacuous precondition. **Both are preconditions**, so no arm below them has measured anything |
| `tests/push_gate/check3_probe.py` | **TIMEOUT, rc 124 at 200s, 0-byte log** — b15 recorded 176s | same shape as §10: it has crossed the ceiling and prints nothing while it runs. Flush per arm first, then measure |

### → CODY, long-running (1)

| `tests/push_gate/redaction_base_probe.py` | 147s, 3 failures incl. `the OLD code lets the secret through` | that arm is a **counterfactual** — it plants the pre-fix code and asserts it leaks. Read whether the old code is still reconstructible before believing the failure |

### → HANK (2)

| file | measured now | next step |
|---|---|---|
| `tests/sd_data_write_attribution_three_apps.js` | 17 passed, 3 failed: `B. rf_schedule must store the session employee in its blob` · `C1. every case must discard a caller-supplied actor -- 14 of 15` · `D3. rf_schedule/set_status must merge onto the stored blob` | **`rf_schedule` is one resource failing three ways, and C1 says 14 of 15 cases are right.** One branch in `api/sd-data.js` does not stamp the session employee, accepts a caller-supplied actor and overwrites the stored blob. **Verify the three against the handler before accepting them** — but all three naming the same resource is what a real defect looks like, not what anchor rot looks like |
| `api/sd-data-sf-session-gate.test.js` | the set-equality gap in §5 | §5 |

---

## 12. What this document does NOT claim

* **22 of the 30 were routed from their measured failure line and subject
  summary, not from reading the full subject.** §3 to §10 were read to cause;
  §11 was not. The nine files b16 and b17 have now read to cause have produced
  **six** cases where the failure line meant something other than it said, so
  **treat every row in §11 as a hypothesis with evidence attached, not a
  verdict.**
* **The 16 CHANGED and 9 RECOVERED register rows were NOT worked.** Reason in
  the handoff: `docs/known-red-suites.json` was measured 2026-10-12 against 411
  files, and **none of b17's eight newly-green files has a row in it** (checked:
  0 of 66 entries match). Writing rows from a 36-file run would record a subset
  as if it were the tree.
* **`docs/test-file-floor.json` was NOT raised.** It needs a run whose failures
  are triaged, and this run covered 36 files.
* **No `api/`, `sql/` or `tools/` file was edited.** `api/sd-data.js` and
  `sairnbuild.html` were READ and, inside the sabotage probes' own worktrees,
  mutated and restored byte-identical by the harness's own check.
* **`tests/run_exec_msgs_gate_sabotage_probe.py` was not re-driven end to end.**
  Its three exit-3 preconditions were driven against fixtures and all three
  refuse with a named reason; the full >5-minute sabotage run was not repeated.

---

*cody b17, 2026-10-15. Exit codes read from `echo "EXIT=$?"` on its own line,
never from a pipeline — see §7 for why that sentence is in this document.*
