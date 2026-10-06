# Fourth / Ted — batch 11 inventory

**Written 2026-10-06.** Batch 11 ran out of context at 2% mid-item and was
interrupted; this file is the continuation's record. Every figure below carries
the command that produced it, the commit it was measured at, and the date.
Exit codes are read from the program's own stdout, never from a harness
completion status.

**HEAD at the start of the continuation:** `762b084b` (after `git pull
--ff-only`, which brought 12 files from hank's batch-10 push).

---

## THE CLONE WAS BROKEN WHEN THIS SESSION OPENED, and that is the batch's first finding

The very first command of this session — `git status --porcelain` — failed:

    fatal: this operation must be run in a work tree

`git config --get core.bare` returned **`true`** in
`C:\Users\marsh\Documents\SAIRN-fourth\.git\config`, alongside a fixture
identity (`fx@example.invalid`). That is the exact corruption this role
recorded in batch 9 and contained in batch 10. It was present in the live clone
at 2026-10-06T17:5x, i.e. **after** `b23dbc2e` ("fix(check8): ROOT CAUSE, not
containment"), and was repaired by hand with `git config --unset core.bare`.

**What that does and does not prove, stated carefully.** It does NOT prove
`b23dbc2e` failed: the corruption could have been left on disk by the run that
`b23dbc2e` was diagnosing, before the fix landed, and nothing repaired the
clone afterwards. A `.git/config` value is not tracked, so no commit, no `git
status` and no push gate can see it, and it survives every pull. It does prove
that **the damage outlives the fix** and that there is no detector for the
residue — which is a separate, unclaimed gap from the writer itself.

The selftest that distinguishes the two cases is item 4's, and it is recorded
below under its own heading.

---

## Item 5 — gap documents: **36 of 36** verified at `762b084b`

`python <scratchpad>/gapverify2.py $(cat gapdocs.txt)` — **PROGRAM_EXIT=0**,
read from the program's own invocation, run three times against this SHA. The
first run returned the same file-citation and count-claim totals as the last;
only the citation column moved, because the two states added between runs move
citations.

| measure | result |
|---|---|
| documents NAMED / READ / ABSENT | 36 / 36 / 0 |
| file citations | 321, **4 missing** |
| count claims | 47 hold, **17 broke**, 173 could-not-check (no file named), 4 could-not-check (ambiguous) |
| line citations | 6 hold, **5 broke**, 21 could-not-check (no file named), 1 ambiguous, **15 misattributed by the tool** |

**The dispatch premise was stale.** It said *"5 of 35 verified so far"* — that
is the batch-9 figure. Batch 10 checked all 35 at headline level; this pass
re-derived every checkable claim mechanically and the population re-enumerates
to **36**, not 35.

Full write-up appended to `docs/2026-10-06-gap-doc-verification-all-35.md`.
**15 of the 21 citations this tool called broken were its own wrong
denominator**, which became convention 17 — see item 12.

---

## Item 6 — span sweep: **34 of 34** sites measured at `762b084b`

`node <scratchpad>/spanparse.js` — **PROGRAM_EXIT=0**. The judge is **V8**, not
a brace counter: each span is written to a temp file and fed to `node --check`,
and a span that does not parse as a function expression is not a function body
whatever any counter says.

    SITES: 34   WALKER SPANS THAT PARSE: 34   SITE SPANS THAT PARSE: 31   COULD NOT EVALUATE: 0

**THE DENOMINATOR IS 34, AND THE DISPATCH SAID 38.** Re-derived rather than
carried: `<scratchpad>/spanscan2.txt` reports **143 sites matching a
function-start locator**, of which **110 take no span at all**. 143 − 110 = 33,
plus one `FIXED_WINDOW` site = **34**. The 38 was an earlier raw candidate
count that included sites later shown not to take a span. There is no
"14 remaining": every site in the re-derived universe is measured.

**3 site spans are NOT function bodies** — the defect, stated without
reference to any byte count:

| site | app / source |
|---|---|
| `tests/sairnbiz_vendor_ytd_derivation.js:268` | `sairnbiz.html`, `function rVends()`, bound `marker0` on `$('vntbody').innerHTML=html;` |
| `api/sd-data-leg-session-gate.test.js:211` | `sairnlegacy.html`, `function sdnData(...)`, bound `marker` on `return fetch(DATA_API` |
| `api/_lib/stonedesk-remnant-publishing.test.js:201` | `stonedesk.html`, `window.pcToggleRemnant=async function`, bound `func` on `function pcRenderRequests` |

All 34 **walker** spans (`tests/lib/fn_span.js`) parse, so the shared helper is
clean and the three defects are in what those three suites take for themselves.
**Not repointed here** — a repoint needs a planted control per site proving the
new span is the right one, which is per-site work and is the next step.

---

## Item 7 — red register: **8 of 50** empty `why` diagnosed (not 66 — see below)

`docs/known-red-suites.json` at `762b084b`: **79 entries, 50 with an empty
`why`** before this pass, **42 after**. The dispatch premise of *66* is the
batch-9 figure; batch 10 took it 66 → 50 and this pass takes it 50 → **42**.

Each of the eight was **run individually, its own exit code read from its own
stdout, and its failing arm read** — none is driven-not-diagnosed. Commit
`100b82fc`.

**SIX OF THE EIGHT ARE ONE ROOT CAUSE, and it runs in both directions:** a
probe arm that asserts something about the **live tree** is a drift tripwire,
not a test of the detector.

| suite | exit | diagnosis |
|---|---|---|
| `tests/run_truthy_sum_probe.py` | 1 | arm 11 asserts `truthy_sum_check.py` exits 0 on the real repo; it exits 1 with **16 new unbaselined `\|\| 0` additions**, all in `stonedesk.html:25471–28942`. Other 13 arms pass |
| `tests/run_primitive_obsession_probe.py` | 1 | same assertion **as arm 0, as a GATE** — one FAIL line prints and **none** of the mutation arms run. `primitive_obsession_check.py` exits 1 with **18 new occurrences across five apps** |
| `tests/run_subprocess_decode_probe.py` | 1 | final arm; `subprocess_decode_check.py` exits 1 naming **40 files** with text-mode subprocess calls and no `encoding=`. Reproduction arms pass — the locale here is cp1252 and a tracked file cannot be decoded as cp1252 |
| `tests/run_write_path_scan_probe.py` | 1 | two live-tree arms: the ratchet no longer passes, **and a baselined count FELL**. Mechanism arm passes. **NOT CLEARED** — the fallen key is not yet named |
| `tests/run_removal_path_probe.py` | 1 | last arm; one resource has no removal path and is not baselined. Both mechanism arms pass. **NOT CLEARED** — the resource is not yet named |
| `tests/run_completeness_probe.py` | 1 | **the other direction**: 3 arms assert the tool STILL FINDS `api/sen-portal.js MANAGEMENT_ROLES`; it exits 0, because that was fixed. A probe pinned to a current defect rots when the defect is fixed |
| `tests/run_two_axis_tier_parser_probe.py` | 1 | **probe defect** — arm 2 scores a HEADLINE-scope could-not-tell against an arm whose own words say ROW-level. Its fixture parses (`ROWS_MIGRATED_TWO_AXIS:2 of 2`) and arms 3–4 pass on it |
| `tests/run_financial_invariant_probe.py` | 1 | **probe defect** — arm 7f requires `JUDGED BUT NO LONGER UNGUARDED`, which `tools/idempotency_check.py:534` prints under `if stale:` only. Red **precisely because the register is in order** |

**ARM ORDERING DECIDES THE BLAST RADIUS, from an identical assertion.**
`primitive_obsession` puts it at arm 0 as a gate and loses every other arm;
`truthy_sum` puts it last and still reports 13 passes. That is the candidate
for the next methodology rule and it is named here rather than self-promoted
alongside item 12's — one rule per real catch, not two from one pass.

Nothing closed, nothing reclassified. The writer **refuses on a non-empty
`why`** rather than overwriting another session's diagnosis.

---

## Item 8 — convention 11's missing body: **DONE at `b23dbc2e`**, before the interruption

`docs/2026-09-13-cross-domain-disciplines.md` item 11 ("Human-gated
auto-remediation") now carries its body, with a note recording that the text
had been sitting forty lines further down under a heading reading *"The failure
mode seven of the first eight share"* — a title from when the file had eight
items. Nothing in the text changed; only its position and its heading. cc found
it while working an unrelated file and routed it rather than editing another
session's document.

---

## Item 11 — demo credentials: **16 of 16 OK** at `762b084b`

`python tools/demo_credentials_check.py` — **PROGRAM_EXIT=0**, one fresh run,
2026-10-06. Every app including **sairnvet** returns `OK role=owner`
(`sairncode` is `role=admin`, which is its documented provisioning role). No
`WRONG-PIN`, no `LICENCE-INACTIVE`, no `COULD-NOT-REACH`.

The universe is the 16 apps named in the untracked
`.demo-credentials.local.json`; the count is printed by the tool so a
shrinking list is visible. No PIN appears on any path.

---

## Item 12 — convention 17, from this batch's own defect

`docs/2026-09-13-cross-domain-disciplines.md` **item 17: a third state for
ABSENCE is not a third state for AMBIGUITY.** Commit `7c911e5c`. Full case is
in that file and in the gap-doc appendix; the short form is that the verifier
had a named state for *zero* candidate subjects and none for *two*, so absence
refused and ambiguity resolved silently, in identical output shape. 15 false
findings. Widening the lookback relocates the boundary instead of removing it,
which is what makes a state the answer rather than a parameter.

17 is **deliberately not** added to the eight conventions that share the
cannot-fire failure mode — item 17's check fires, on the wrong subject — and
the heading now says why rather than absorbing it silently.

---

## Cause tags for every confirmed defect this batch

| defect | phase | sub-phase | specific cause |
|---|---|---|---|
| gap verifier resolved an ambiguous subject silently | implementation | error handling | a third state written for absence, with no branch for multiplicity; `hits[-1]` on a multi-candidate window |
| gap verifier reported a verified-nothing run as success | implementation | input validation | empty `argv` not distinguished from a complete corpus; no fail-closed guard, exit 0 |
| 3 suites take a span that is not a function body | test design | fixture derivation | marker/`func` bounds hand-chosen against a moving app file, judged by a brace counter rather than a parser |
| 6 red suites assert live-tree state | test design | oracle selection | the live repository used as the fixture, so ordinary feature work changes the expected value |
| `run_primitive_obsession_probe` loses all arms when one fails | test design | arm ordering | a live-tree assertion placed as a precondition gate rather than as a reported result |
| `run_two_axis_tier_parser` arm 2 false red | test design | assertion scope | a helper collecting headline-scope problems into a row-scope assertion |
| `run_financial_invariant` arm 7f false red | test design | assertion scope | an unconditional assertion on a conditionally-printed section |
| `.git/config` residue outlives its fix | tooling | recovery | the writer was fixed; nothing detects or repairs the untracked residue it already left |

---

## Item 4 — the two clone-corrupting probes: the selftest, run in the LIVE clone

**The selftest is the one the dispatch named: a run leaves `git status`
clean.** Deliberately **not** run in a worktree — a worktree staying clean
proves nothing about the clone, and the clone is what was being damaged.
`.git/config` was copied byte-for-byte before each run and diffed after.

### `tests/seam_check/run_delegation_probe.py` — **FIXED, and green**

`python tests/seam_check/run_delegation_probe.py` — **PROGRAM_EXIT=0** at
`6984634e`, 2026-10-06, one run, read from its own invocation.

    arm1_sees          True
    arm2_propagates    True
    arm3_stops         True
    arm4_no_residue    True
    restored_baseline  True (96 clean, 0 not-forwarded, 19 could-not-tell)

    === CONFIG DELTA ===   CONFIG UNCHANGED
    === STATUS DELTA ===   STATUS UNCHANGED

And independently of the probe's own self-report, `node --check` on both files
it used to leave sabotaged: `api/sd-data.js` **PARSES**,
`api/_lib/subcontractor-compliance.js` **PARSES**. The arm that asserts no
residue (`arm4_no_residue`) is the probe judging itself; the two `node --check`
runs are not.

### `tests/push_gate/check8_probe.py` — **the CORRUPTION is fixed; the probe is still RED on 2 arms, and those are PRE-EXISTING**

`python tests/push_gate/check8_probe.py` — **PROGRAM_EXIT=1**, `check8_probe: 2
failed`, at `6984634e`.

**The corruption is gone and the probe now proves it itself:**

    ok   the repo was restored
    ok   ...and HEAD is back where it started
    ok   and the CLONE was never touched -- no commit, no modified file
    ok   ...and neither was .git/config -- byte-identical to the pre-run copy

    === CONFIG DELTA ===   CONFIG UNCHANGED
    === STATUS DELTA ===   STATUS UNCHANGED
    === HEAD ===           6984634e, unmoved

**The 2 failures are NOT a regression from `b23dbc2e`, and that is measured
rather than argued.** The pre-fix whole-tree run captured at **08:41**, long
before `b23dbc2e` landed at 16:03, already reads:

    FAIL py  tests/push_gate/check8_probe.py   FAILED  check8_probe: 2 failed

**The two arms, and what actually happens.**

| arm | expected | observed |
|---|---|---|
| `a PROBE-subject commit IS blocked` | check 8 refuses, naming the probe commit | the push is refused one layer EARLIER: `Blocked: this gate could not tell what is being pushed. / no ref lines on stdin` |
| `...and the refusal NAMES the commit` | the commit sha in the refusal text | same earlier refusal; no commit named |

Both arms assert *which* refusal happens. The gate's **fail-closed** path fires
first, so check 8 is never reached and the arm cannot see what it is asserting
about. The surrounding arms pass, including `...and the push exits non-zero`
and `...and the PreToolUse path denies it too` — so the gate is denying
correctly; only the *attribution* is wrong.

**IT IS ENVIRONMENT-DEPENDENT, which is the lead and not the answer.** The
same probe run from a throwaway dev copy at
`C:/Users/marsh/AppData/Local/Temp/ted-c8-dev/` exited **0** four separate
times (19:19:35Z, 19:24:30Z, 19:28:30Z, 19:57:58Z, each exit code captured to
its own `.status` file) while exiting **1** in this clone. So the two arms pass
in one clone and fail in another at the same code.

**NOT ESTABLISHED, stated rather than guessed:** *why* `git push --dry-run`
delivers no ref lines to the pre-push hook in this clone when it does in the
dev copy. The live clone was ahead of `origin/main` during the run, which is a
candidate and not a finding. **This is the next step on item 4** and it is a
separate defect from the config writer, which is closed.

### Reconciliation — one finding, one owner, deduped by first real evidence

Three records pointed at this one thing and they are not three findings:

| record | what it was | resolution |
|---|---|---|
| **fourth, batch 9** — `docs/2026-10-06-whole-tree-run-and-the-runner-that-corrupts-its-clone.md` | the **first real evidence**: named both probes, named `core.bare = true` and the fixture identity, attributed by digesting a watch-list after every suite | **the originating finding. Mine, and closed by the selftest above** |
| **cody, queue19** — "read-only `core.bare` cause hunt **routed to ted**" | a cause hunt on the same symptom, routed to this role | **same finding, not a second one.** Routed to the originator, which is the correct direction. Nothing for cody to close |
| **fourth → cc** — `.git/config` written from a worktree by `dry_push(probe_env=False)` in `tools/sairn_push_gate_hook.py` | the **mechanism one layer down**, in cc's file | **still cc's, and NOT closed by me.** The selftest above proves check8_probe's *fixture* can no longer reach this clone; it does **not** prove the hook cannot write shared config from a worktree by some other caller. Only the originating finder closes, and that layer's finder is cc |

The one genuinely new item is in the andon log as **pull 4**: `.git/config` is
untracked, so the residue a fixed writer already left is invisible to every
check on this platform and survives every pull. Fixed writer, no detector.
