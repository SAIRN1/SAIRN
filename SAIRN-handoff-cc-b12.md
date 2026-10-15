# SAIRN handoff -- cc batch b12 -- 2026-10-14

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished:
every change is committed and on `origin/main` at `0 0`, every selftest and
ablation named below was re-run after the final rebase, no background job is
in flight, no file is mid-edit, zero stashes remain, and no scratch file or
worktree of mine is left in any repo.
**Companions:** `SAIRN-report-cc-b12.txt`, `SAIRN-digest-cc-b12.txt`,
`SAIRN-latest-cc.md`, `docs/2026-10-14-cc-b12-routed.md`.
**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\5521d10f-06f8-4089-8534-150e3e3c8d84.jsonl`
— a NEW session, not the one b9/b10/b11 shared, so the context figure covers
this batch alone. Raw logs:
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\5521d10f-06f8-4089-8534-150e3e3c8d84\scratchpad\`
(`msg2.txt`, `msg3.txt`, `file_defects.py`).

---

## Committed / pushed state

**HEAD `d19ae6bb`, `git rev-list --left-right --count origin/main...HEAD` =
`0 0`, tree clean.** No `--force` in any spelling — the one `grep -i force`
hit in a push log is the word inside "UNENFORCEABLE" in the gate's own text.
**No override of any form was used**: not `SAIRN_SEED_GATE=off`, not
`SAIRN_GATE_EXEMPT=seed`, not `SAIRN_SKIP`. `docs/BYPASS-LOG.jsonl` carries
exactly one row for today and it is the `REFUSED, not honoured` row my own
measurement of the blanket form wrote. Two rebases during landing, both clean.
No hook added or restored; `.claude/settings.json` never committed.

| SHA | what |
|---|---|
| `46128d86` | feat(drive board) — `tools/sairn_board_publish.py`, event-driven, plus the two defects it exposed in `sairn_status.py`; and item 2's `tools/runbook_constant_agreement.py` + the `.githooks/pre-push` hint fix |
| `c7c758ed` | fix(push gate, floor) — `OVERRIDE_HINT` derived from `gate_skip`; the test-file floor made a ratchet; items 3, 4 and the rest of 5 |
| `0e6a055f` | chore(defect register) — three records, each with contributing factors |
| `620a55a1` | chore(derived) — traceability matrix regenerated, the gate refused without it |
| `bf188c1e`, `9e5a3786`, `d19ae6bb` | chore — scrutiny-ledger rows, register re-seat after the rebase, ledger rows for the rebased shas |

**Five gate refusals during landing, every one satisfied rather than
overridden:** register-feed (twice — the second after the rebase moved the
shas), derived-docs (traceability matrix), and two non-fast-forwards. The
gate's own refusal text printed the NEW derived hint, with the full
eight-gate list — which is item 5's fix verified in production output rather
than in a selftest.

**No live deployed-URL check, and that is not a skipped step:** this batch
changed no `api/`, `sql/` or app file. Nothing it touched is deployed.

---

## The six items

| # | item | state | evidence |
|---|---|---|---|
| 1 | Drive status bridge, event-driven, all six agents | **DONE** | `--selftest` 14/14, `--ablation` 10 layers all load-bearing; 7 files on the Drive, read back by sha256; Drive id `19GSUTWQLddPwZiLEUNfssAjrMxK4vVE1` unchanged across three publishes |
| 2 | sweep for a third override-hint copy; runbook-vs-code guard | **DONE** | two prose copies found and one fixed; `runbook_constant_agreement.py` `--selftest` 10/10 both directions, `--ablation` 4/4 load-bearing; finds the real divergence today |
| 3 | wire hank's two suites | **DONE** | `GUARD_TESTS` 14 entries, no dupes, both suites green BEFORE wiring (31/0/0, 18/0/0) |
| 4 | `fmea_draft --save` for hank's nine files | **DONE** | nine drafts saved, drafts only, none blessed |
| 5 | cody b11's three findings + seam check + stashes + stale root files | **DONE, and two of the five answers are "the routing was wrong"** | below |
| 6 | push without force, confirm landed | **DONE** | `0 0`, HEAD `d19ae6bb` |

---

## Item 1 — and the two defects it found by printing a field nobody consumed

`tools/sairn_board_publish.py` writes `SAIRN-board.md` plus
`SAIRN-latest-<agent>.md` for hank, cc, cody, fourth, H1 and H2. It is called
from `sairn_status.py` after every row write and from `sairn_claim.py` through
`sairn_status.publish_claims()`, so a state change, a claim, a release and a
context reading all republish as a side effect of the thing the agent was
already doing.

**`in place at a fixed Drive file id` is a property of the sync mount, and the
tool cannot see it — so the id was read back through the connector and
recorded.** Created `23:37:11Z`; the second and third publishes left `id`
unchanged and moved only `modifiedTime`. That pair is the whole evidence. The
mount read-back proves sha256 of the bytes in the sync set; it does NOT prove
Google acknowledged the write, and one measured discrepancy says so out loud:
immediately after the third publish the connector reported `fileSize` 14600
while the mount held 14514 — one revision behind.

**A new `set --context <pct>` records the live reading, and `context_set`
stamps when** — so the age of the NUMBER is visible beside the age of the row.
Without it the board falls back to the newest digest's own CONTEXT line and
labels which it used.

**THE TWO DEFECTS, and the reason they had been invisible:**

1. **`sairn_status.payload()` rebuilt the row and dropped the three keys
   `publish_claims()` owns.** A session claims and then sets `working`, in that
   order, so the cross-clone early warning was erased within seconds of being
   written, every single time. **Nothing said so and nothing could have:** an
   absent `claims` key is also exactly what a session running an older
   `sairn_claim.py` looks like, which `read_claims()` documents as the ordinary
   state during a rollout. The wipe was indistinguishable from the one benign
   case.
2. The board read a claim's subject from `app`; `sairn_claim` writes
   `subject`. Every claim rendered as `?`.

**Both were found because a REPORTER printed a field nothing had ever
consumed.** cc holds a claim and the board said 0. That is the honest
attribution and it is the `found-by-tool` on the register record.

**The ablation corrected the arms rather than confirming them.** A8's first
fixture used an 1,800-character digest field — which is one line, and the
renderer caps it at 900 characters anyway — so `latest-ceiling` could be
deleted with no arm noticing. The real path to an overlong per-agent file is
the uncapped `claims` list, and A8 now asserts against a **literal 60** rather
than against `LATEST_MAX_LINES`: an arm checking the file against the same
constant the code used is a tautology.

---

## Item 2 — no third printed copy, two prose copies, and the guard

**The sweep.** `.githooks/`, `docs/` and `.claude/skills/` searched for the
refusal sentence. **No third copy of the PRINTED text.** Two prose copies that
named only the blanket form:

- **`.githooks/pre-push:24`** — fixed. A live comment in the hook the gate
  actually runs from, pointing the reader at the flag that disables everything.
- **`docs/2026-09-09-tooling-inventory.md:94`** — **deliberately not edited.**
  A dated inventory is a historical snapshot and rewriting it is rewriting the
  record.

`docs/SAIRN-PROCESS-RULES.md` and `CLAUDE.md` both already named the scoped
form first — and both were wrong in a different way, which is item 5.

**`tools/runbook_constant_agreement.py`** closes the half the b11 handoff
named: `secrets_inventory._IRREVERSIBLE` locks the CODE constant on every
invocation and **nothing watched the Markdown**. It compares what an operator
must be able to ACT on, not the wording — and the needle list is **imported
from the lock**, so a sixth needle there starts being required in the prose
here with no edit. Arm A9 is the one that proves it: it adds a needle to the
lock and requires the registry to demand it.

Live: `AGREES docs/SECRETS-INVENTORY.md`, `DIVERGES docs/NHI-REGISTER.md` on
all five needles.

**Report-only, in `report_only_checks.REGISTRY` and in `_FRONT`.** Not a gate,
because it finds a real divergence today in fourth's file: wired blocking it
would deny every push by every session until fourth lands one edit, which is
how a gate gets switched off rather than satisfied. `_FRONT` is not a
preference — that file documents that only 36 of 73 entries clear the 540s
budget, so appending to the tail wires a tool that provably never runs.
Measured cost 0.17s; entry 35 starts at cumulative 333.3s and still clears.

---

## Item 5 — cody was right twice, and the routing was wrong twice

**The override hint.** cody routed two lines that contradict each other.
Chasing them found that **b11's own fix landed on a mechanism retired the day
before.** Measured, not read:

    echo "" | SAIRN_SEED_GATE=off python tools/sairn_push_gate_hook.py --pre-push
    -> exit 1, "REFUSED: ... the BLANKET form and it no longer works."

So the hint was false in two ways at once: the blanket form disables nothing
and denies the push, and the hint named `SAIRN_GATE_EXEMPT=seed` as THE scoped
form while the gate's own refusal recommends `SAIRN_SKIP=<gate>` — **eight**
gates against EXEMPTABLE's one. **All eight selftest arms were green over it,
because all eight only ever asked about the ORDER of two variable names.**

The hint is **derived** from `gate_skip` now. Four new arms ask about the
CLAIMS the sentence makes, and the second ablation uses the **b11 text**,
which passes all eight original arms and fails exactly the four new ones.
22/22. Corrected in four other places; both standing documents now end with
the instruction not to write it down a sixth time.

**The test-file floor.** 370 against 802 — **432 files deletable with the
guard silent.** It is a ratchet now (`docs/test-file-floor.json`), rising
only, with the literal 370 as the floor of last resort. **Two things here were
found by running cody's probe, not by reading it:** the first ratchet raised
the floor ABOVE the tree (807 vs 802) because the probe writes fixture files
into the real `tests/` and `discover()` walks the working tree — so the basis
is now the discovered list **intersected with `git ls-files`**; and arm 7
counts the constant's assignment in the raw source, where a tuple unpack
counts zero and my own explanatory comment counted as a second one. `tests/`
is cody's and was not edited. ALL CHECKS PASS.

**The seam check.** 96 clean, 0 not-forwarded, **19 could-not-tell**, exit 2.
hank reported "at least one pair". It is nineteen — and **one root cause**:
`roleSet()` at `api/_lib/auth.js:72` is a deliberate whole-object copy, so the
tool's `literal.field` scan cannot see it. A tool limitation on a known-good
pattern, and still not a pass. Both remedies routed; the `tools/` half
deliberately not taken.

**The stash was not dirt.** "Clear your two stashes" — there was **one**, and
it held **260 added lines across six `tools/` files**: the shared open-work row
reader from b6 item 5, never landed. Dropping it on the instruction's word
would have destroyed it silently. Preserved as
`docs/unlanded/2026-10-13-cc-b6-open-work-shard-read-rows.patch` with a README,
**then** dropped. Zero stashes remain. `*.patch` and `*.diff` are now `-text`:
a patch is a byte-level description and `git apply` reports a CRLF-mangled one
as corrupt rather than as a line-ending problem.

**The stale root files are in the auditor's own clone.** H1 has carried this
since b29 and reconfirmed three times that "cc has not acted". Its own b29
handoff names them — `SAIRN-report-h1-b27.txt`, `SAIRN-digest-h1-b27.txt`,
untracked, **`rm -f` DENIED BY THE PERMISSION SYSTEM in b28** — and b31 says in
the same breath that no scratch files were created in the platform repo.
Measured here: zero h1 root files in this clone, zero untracked root `.txt` of
any agent. **A build agent must not reach into `Documents\SAIRN-hover`.**
Re-routed to H1 or Michael, with the permission denial named as the real
blocker.

---

## Claims held

**`cc`, claimed as the first action of this batch.** Released after this
handoff, the report and the digest are written and uploaded, then the status
row set to `idle`:

    python tools/sairn_claim.py release cc
    python tools/sairn_status.py set --state idle

**Files written that were NOT in cc's declared b12 FILES**, said out loud:
`CLAUDE.md` and `docs/SAIRN-PROCESS-RULES.md` (§3's blanket-override paragraph
was actively false and nobody holds either file — cody routed it to "whoever
owns CLAUDE.md"), `.gitattributes` (the `*.patch` rule, needed the moment the
stash was preserved), `tools/run_all_tests.py` (the floor lives there),
`docs/test-file-floor.json`, `docs/unlanded/*`, `docs/traceability-matrix.md`
and `docs/scrutiny-flags.json` and `docs/defect-density-register.json` (each
required by a gate before it would accept the push — the same collision b8–b11
all named and resolved the same way), and `docs/BYPASS-LOG.jsonl` (one row,
written by the gate during my own measurement of the blanket form, committed
rather than reverted because it IS a record).

**Conflicts declared and NOT overridden (PR §4.3):** `tests/` is cody's and
read-only here — when my floor change failed cody's arm 7, the TOOL was
reshaped rather than the arm. hank's `api/`, `sql/` and app HTML read-only; the
two suites were wired by registering them, not by editing them. fourth's live
claim covers `docs/CRITICALITY-TIERS.md`, `docs/tier-a-reviews.json` and
`docs/batch-manifest-fourth-b20.json` — none touched. `docs/NHI-REGISTER.md` is
fourth's, which is why step 4a is still routed rather than fixed. No auditor
clone entered or written.

---

## Open, and whose — with the exact next step

| item | owner | exact next step |
|---|---|---|
| **adversarially check the Drive board** | **H1 and H2** | `docs/2026-10-14-cc-b12-routed.md` section 1 is a table of seven specific attack surfaces with the reason each is attackable and how to check it. The one that needs a capability cc does not have: read `SAIRN-board.md` through the Drive API and compare its bytes to the mount |
| **five of six agents show zero mirrored claims** | **each clone** | nothing re-mirrors an existing claim. The row repopulates on that clone's next `sairn_claim.py` claim or release, once it has pulled `46128d86`. Until then the board says so in the cell rather than printing `0` bare |
| **`docs/NHI-REGISTER.md:69` still omits step 4a** | **fourth** | exact text in `docs/2026-10-14-cc-b11-routed.md`. It is now DETECTED rather than remembered: `python tools/runbook_constant_agreement.py`. **Promote it to blocking once the register copy lands** |
| **19 seam could-not-tells, one root cause** | **hank** (test) / **cc** (tool) | hank: a hand-written test pinning `roleSet`'s input contract, shape of `api/_lib/deadline-endpoint-inputs.test.js`. cc: teach `sairn_seam_check.py` the whole-object-copy shape — **its own batch**, with a fixture proving a PARTIAL copy is still not recognised, because converting 19 unknowns to 19 clean verdicts is the direction that can hide a real dropped field |
| **`sql-run-order-agreement.test.js` not wired** | **hank** | file the defect record (`python tools/defect_register.py --add --commit <sha> ...`) and it qualifies on both halves of the registry's bar; cc wires it |
| **`rf-settings-tier.test.js` not wired** | **hank** | name the two independently-maintained sides and cc wires it |
| **`api/_lib/sd-store.js:203` RAW + `writeSlab()` duplicating `id`** | **hank** | carried from b10 and b11, unchanged: `python tools/blob_conversion_coverage.py --list RAW` |
| **five stale root `.txt` pairs** | **H1, or Michael** | they are inside `Documents\SAIRN-hover` and `rm -f` was denied by the permission system in b28. cc structurally cannot clear them. The permission denial is the blocker |
| **`C:\Users\marsh\SAIRN-SESSION66-HANDOFF.md`** | **Michael** | byte-identical to the tracked copy here (md5 `316774fd75d3a1688870dfee167b7763` both). Breaks the rule that a handoff lives only in a clone. In your home directory, so cc reported it rather than deleting it |
| **`*.jsonl` has no `.gitattributes` entry** | **whoever next touches `.gitattributes`** | and **the obvious rule is wrong**: all three tracked `.jsonl` blobs are ALREADY CRLF, so `text eol=lf` would renormalise 178 lines of audit log including two files inside the hover auditor's skill directory. Same shape as the `archive/**` case that file already documents |
| **FMEA drafts for cc's own tools** | any session **except cc** | `sairn_push_gate_hook.py`, `tier_a_review_gate.py`, `secrets_inventory.py`, `register_feed_gate.py`, `obligation_surface.py`, and now `sairn_board_publish.py`, `runbook_constant_agreement.py`, `.githooks/pre-push` |
| **obligations open past 48h** | **each named owner** | `python tools/obligation_surface.py`, `--mine` filters. Not re-measured this batch |
| **the Tier A obligation cc opened in b10** | **fourth** (auto-assigned) | still open; cc cannot discharge its own |

---

## Three things that will cost the next session time if nobody says them

1. **A fix can land on a mechanism that was already retired, and every arm
   over it can stay green.** `OVERRIDE_HINT` was corrected in b11 and was
   still false in two ways the next morning, because the eight arms guarding
   it asked only about the ORDER of two variable names — never about whether
   the sentence was true. **An arm that checks the SHAPE of a claim is not an
   arm that checks the claim.** The fix is to derive the text from the tool
   that owns the fact, and to write the ablation against **the version you
   just replaced** rather than against some older one: the b11 text passes
   all eight original arms and fails exactly the four new ones, which is the
   only thing that demonstrates what the new arms are for.

2. **"Clear your stashes" and "delete the stale files" are instructions about
   dirt, and twice this batch the thing named was not dirt.** The stash held
   260 lines of unlanded work; dropping it on the instruction's word would
   have destroyed it with nothing anywhere saying so. The stale root files are
   inside the auditor's clone, where a build agent must not reach, and had
   been re-routed to cc three times by an auditor who could not see why cc
   never acted. **Read the target before removing it, and when a routing
   cannot be executed, say WHY rather than carrying it forward silently** —
   four batches of "cc has not acted" was the cost of nobody writing that
   sentence.

3. **A detector a fixture can drive is a detector that fails on correct code
   tomorrow.** The first version of the test-file ratchet raised the floor to
   807 against a real 802, because cody's probe writes five fixture files into
   the real `tests/` directory and `discover()` walks the working tree. The
   next clean run would have reported a shrunken suite. **The basis for any
   self-adjusting number must be something a test run cannot move** — here,
   the discovered list intersected with `git ls-files`, because an untracked
   file is on one person's disk and in nobody's clone, so it is not a guard.
   And the first attempt at THAT counted `git ls-files tests` and read 688
   against 802, because `discover()` also picks up `api/*.test.js`: a basis
   that looked principled and would have pinned the floor 114 low for ever.
