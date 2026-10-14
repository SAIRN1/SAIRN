# SAIRN handoff -- cc batch b10 -- 2026-10-14

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished:
every change is committed and on `origin/main` at `0 0`, every suite named
below was re-run after the final rebase, no background job is in flight, no
file is mid-edit, and no worktree or temp directory of mine is left behind.
**Companions:** `SAIRN-report-cc-b10.txt`, `SAIRN-digest-cc-b10.txt`.
**Transcript:** this session continues the same file as b9 --
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\bb71ca91-ccbc-4a82-aa5e-0bff468b6ed5.jsonl`
(the `/model` switch continued the session rather than starting a new one, so
b9's history is in the same transcript and in this batch's context figure).
Raw logs for every number below are in that session's scratchpad:
`...\bb71ca91-ccbc-4a82-aa5e-0bff468b6ed5\scratchpad\` --
`blobcov_before.log`, `blobcov_after.log`, `blobcov_teeth.log`,
`citation_before.log`, `citation_after.log`, `bare_run_selftest*.log`,
`bare_run_teeth.log`, `prefix_match.log`, `drive_audit.log`,
`drive_audit2.log`, `astparse_sweep*.log`, `scopegate_probe.log`,
`tier_a_probe.log`, `save_retry_probe.log`, `allowlist_check.log`.

---

## Committed / pushed state

**HEAD `70a25041`, `git rev-list --left-right --count origin/main...HEAD` = `0 0`.**
No `--force` in any spelling. **No gate override of either form was used** --
not `SAIRN_SEED_GATE=off`, not `SAIRN_GATE_EXEMPT=seed`. One rebase during
landing, clean, no conflicts. No hook added or restored (`hooks` is `{}`);
`.claude/settings.json` was never committed.

| SHA | what |
|---|---|
| `b12a7631` | fix(blob coverage) -- `api_files()` walks `api/` recursively; the universe was 50 of 179 files |
| `3b1dc5fe` | fix(citation anchor) -- line-exact and code-only; three substring routes, two of which pull in opposite directions |
| `7788d3d1` | fix(bare-run sweep) -- a concurrent session's registry write is no longer attributed to the tool under test; plus the 2 allowlist entries hank routed |
| `d1308719` | fix(drive verify) -- `WRONG AGENT` split out from `NO AGENT NAMED`; the one dangerous case was buried among seven cosmetic ones |
| `3a2cd7fb` | docs(b10) -- the routing doc: `tests/` to cody, `api/` to hank, a wrong-batch digest to H1, one naming decision to Michael |
| `10668f1a` | docs(push protocol) -- CLAUDE.md §3 **and** PR §3.3 now teach `SAIRN_GATE_EXEMPT=seed`, not the retired blanket flag |
| `55554f39` | chore(defect register) -- 4 records this batch's fixes owed the push gate |
| `566666c2` | chore(tier a) -- the review obligation the drive-verify and bare-run changes owe, auto-assigned to fourth |
| `70a25041` | chore(scrutiny ledger) -- the gate's own row for `7788d3d1` |

---

## The six items

| # | item | state | evidence |
|---|---|---|---|
| 1 | scope gate `:409` + the unfetched-base checker | **ALREADY DONE in b7 — verified, not assumed** | `tests/run_scope_gate_unfetched_base_probe.py` 12/12 incl. the ablation; the DECIDE_OR_NOT_PROMOTED ruling is live in `report_only_checks.NOT_PROMOTED` |
| 2 | cody-routed: recursive coverage + line-exact anchor | **DONE** | `b12a7631`, `3b1dc5fe`; one of cody's two suites went green, the other fails for the *opposite* reason now — said out loud below |
| 3 | save_reviews retry, hank's 13 bare-run findings, H1's 7 Drive mismatches | **DONE; the retry was already landed** | `7788d3d1`, `d1308719`; retry verified by the routing doc's own criterion |
| 4 | CLAUDE.md §3, the `ast.parse`→`compile` sweep, the `git -C` rule | **DONE — the sweep found a population of 1, already fixed** | `10668f1a`; sweep logs; 7 `git -C` rules live |
| 5 | failing-first with control arms; no self-FMEA; the PEM-shaped file | **DONE — and the file is NOT safe, see below** | teeth logs for all three fixes |
| 6 | push without force, confirm landed | **DONE** | `0 0`, HEAD `70a25041` |

---

## Item 1 — already done, and I checked rather than took the registry's word

Both halves of fourth's b10 routing were already closed in **b7**, which the
brief did not know. I verified both against source rather than trusting the
`NOT_PROMOTED` text that claimed it:

- `tools/hover_auditor_scope_gate.py` carries `_have_commit` at `:247`, called
  at `:427`, with the merge-base fallback at `:442`.
- `tests/run_scope_gate_unfetched_base_probe.py` passes **12/12**, and arm 5 is
  an **ablation** — it stubs `_have_commit` to always say yes, which *is* the
  pre-fix code, and requires the opaque range refusal to come back. So the
  guard is what fixes it and nothing else.
- Arm 6 re-measures the population mechanically every run: **3** tools bind a
  remote sha from a pre-push ref line by field position, all 3 guarded. Arm 6b
  refuses an empty population, so the arm cannot pass vacuously.

**The one genuine gap I found, routed rather than fixed:** arm 6 checks a guard
exists *somewhere in the file*, not that it sits between the taint source and
the sink. A fourth author could define `_have_commit` and not call it on the
path that matters and arm 6 would still pass. That is a `tests/` file and
cody's; it is in the routing doc.

---

## Item 2 — one suite recovered, the other now fails for the opposite reason

**This is the thing most likely to be misread, so it is first.**

`tests/run_blob_coverage_scope_sabotage.py` **still exits 1**, and that is not
my fix failing. Its attack-point arm S1 now **passes**; the arm that fails is
S2, *"the unscanned region is NOT EMPTY"* — which fails **because the gap it
asserts exists has been closed**. It is a sabotage control written to prove the
unscanned region was non-empty, and there is no longer an unscanned region.
A reader seeing `exit 1` will conclude the opposite, and the suite cannot say
so itself. **S2 is cody's to re-aim** (inverting it to assert the region is now
empty would also catch a regression back to `os.listdir`), and the register row
`docs/known-red-suites.json:1229` needs **updating, not deleting**.

`tests/run_citation_anchor_hop_sabotage.py` did go green: **2/6 → 6/6**, and
its row `:1247` is a clean RECOVERED — delete it.

**Measured figures, both re-derived at HEAD rather than copied from cody's row:**

| | cody's row said | measured at HEAD |
|---|---|---|
| files outside the coverage universe | 126 | **129** (50 flat vs 179 recursive) |
| failing arms in the citation probe | 4 | 4, but the fix took **three** changes |

**The third change is the one I would have missed.** Cody's arm S1b tests a
*string literal* naming a storage constant — `log('K_COMMS was migrated away
from this path')`. I had just fixed comments by stripping them, and the resource
branch needs string literals **kept intact** (real access is
`getItem('sd_comms')`, a string). So the two branches needed opposite
treatment: strings preserved for the resource key, string *contents* blanked
for the constant identifier. Without S1b I would have shipped the comment fix
and called it done.

**A new finding the widened universe surfaced**, routed to hank:
`api/_lib/sd-store.js:203` is a **RAW** stored-blob write — invisible before,
and the +1 that took unconverted 57 → 58. Cody's probe also reports that
`writeSlab()` puts `slab_id` as a column beside the unstripped blob, duplicating
`id`.

**I did not `--repin`.** `docs/blob-conversion-coverage.json` was pinned over
the old narrow universe, so the tool now prints `IMPROVED -- unconverted fell
from 64 to 58` on a comparison across a universe change. That is
apples-to-oranges and re-pinning would bless it.

---

## Item 3 — one was already landed; one routed finding was FALSE

**save_reviews retry: already in `tools/tier_a_review_gate.py`** (`_REPLACE_RETRIES
= 20` at `:113`, loop at `:567`). Verified by the routing doc's own stated
acceptance criterion rather than by reading the code: the probe prints
`RETRY COUNT: save_reviews needed 0 retry/retries to get BOTH writers through`
— the doc said it "should fall to 0 on every run... if it does not fall to zero,
the fix is not working". `tests/run_save_reviews_retry_probe.py` 10/10,
including arm 4 (an `ENOSPC` escapes on the first attempt, so `except OSError`
was correctly not used).

**hank's sharpest bare-run finding was false, and that is the batch's main
result.** hank reported three tools writing *another session's* status row and
called it "the sharpest item in this table". It would be serious. **None of the
three can do it:** measured at HEAD, neither `idempotency_check.py`,
`register_freshness_check.py`, `shape_antipattern_check.py` nor `checker_kit`
(which two of them import) contains any reference to `SESSION-LOCKS`,
`sairn_status` or `status/`. What the three write targets have in common is only
that **hover, fourth and hover2 were live sessions during the sweep**. The
registry has five other writers by design; a before/after snapshot around a 25s
run records their writes and cannot tell them from the subject's. The implied
remedy was to go edit three correct tools.

Fixed in the sweep, not in the three tools: `shared_diff` returns attributable
and unattributable separately; `status/` changes are printed every run but are
never a finding. **Arm A8c is the control that makes A8 mean something** — a
lock file must stay attributable and stay a finding, so A8 cannot be satisfied
by classifying everything unattributable.

**The 2 `WRITES(bare)` findings were allowlist entries, as hank judged.** Both
paths re-derived from source. `mech_gate_live_probe.py` writes a **dated** file,
so it needed a one-line matcher change: a declared path ending in `/` is a
directory contract. Declaring one day's spelling would fail on every other day.

**H1's 7 Drive mismatches are 8**, and the new one
(`SAIRN-digest-hank-b9.txt`) is what tells you this is **ongoing, not a
backlog**. Seven are a digest not naming its agent on line 1 — a convention gap.
The eighth, `SAIRN-handoff-cc-b6.md` reading `# cody b6 handoff`, is one
agent's filename over another's content. All eight printed the same label, so
the only one that can mis-route a session's state was buried. **I declined H1's
option (a), relaxing the check** — it is the control that found the real
mis-file, and seven cosmetic failures are not a reason to retire it.

---

## Item 4 — the sweep's answer is a measurement, not a change

**The `ast.parse()`→`compile()` sweep found a population of ONE, already fixed
in b9.** Of 10 tools that both call `ast.parse` and open a file for writing,
only 3 parse-then-write inside one function, and **2 of those 3 are false
positives**: `clone_health_check._fixtures()` parses its *own* source for an
analysis arm, and `rewrite_convergence_map._tracked_writes()` *detects* writes
rather than performing them. The only real in-place source rewriter is
`subprocess_decode_check.fix_file()`, converted to `compile()` in b9. The other
known write-when-run mutators (`sabotage.py`, `line_endings.py`,
`guard_ablation.py`, `condition_coverage.py`, `cp1252_console_sweep.py`) are
byte/text-level or write only to tempdirs and a report — `cp1252_console_sweep`
in particular *prints* the insertion it recommends and never applies it.

**`git -C` rule confirmed live**, uncommitted by nature (it is in
`~/.claude/settings.json`, outside every repo): 7 spellings, 7
`additionalDirectories`, 112 deny rules, `hooks` `{}`, `statusLine` present.
Nothing to add.

---

## Item 5 — the PEM-shaped file is NOT safe, and that is a finding

Checked by git metadata only. **I did not open, read, or copy it.**

    git -C ...\SAIRN ls-files --error-unmatch .claude/MIGfMA0...txt  -> error: did not match
    git -C ...\SAIRN check-ignore -q .claude/MIGfMA0...txt           -> exit 1  (NOT ignored)
    git -C ...\SAIRN status --porcelain -- .claude/MIGfMA0...txt     -> ?? (untracked)

**It is untracked but it is NOT git-ignored**, so the requested confirmation
fails on its second half: a `git add -A` or `git add .` in that clone **would
stage it**, and it could then be pushed. Nothing in that clone's ignore rules
covers `.claude/` at all — `.claude/settings.json` is not ignored either.
Reported rather than fixed, per the brief: adding an ignore rule there means
editing a tracked file in a clone that is 7,810 commits behind and already
carries two dirty tracked files, and the safer fix is Michael moving or deleting
the file. **Chat's decision to leave that clone alone was honoured** — no
`pull --rebase`, no commit, nothing touched there this batch.

**No tool of mine was FMEA-drafted by me.** The register's FMEA loop suggested
drafts for five files after my records landed; all are left for another session.
Worth knowing: the citation defect came back **`PREDICTED`** — an existing draft
`docs/fmea/tools_citation_line_drift_check.py.json` had already cited rule 1.2
for that file. The loop worked.

---

## Claims held

**`cc`, claimed as the first action of this batch and NOT yet released** --
release with `python tools/sairn_claim.py release cc` once the three
deliverables are uploaded and verified. Status registry row set to `working`;
set it to `idle` after release.

**Files written that were NOT in cc's declared b10 FILES**, said out loud:

- `docs/SAIRN-PROCESS-RULES.md` — in no session's live claim. CLAUDE.md §3
  *points into* §3.3, so fixing one and leaving the other would have left a
  pointer to the contradicting page.
- `tools/blob_conversion_coverage.py`, `tools/bare_run_write_check.py`,
  `tools/bare_run_writers.py`, `tools/drive_upload_verify.py`,
  `tools/mech_gate_live_probe.py` — all under `tools/`, which is cc's, but none
  named individually in my claim string.
- `tools/tool_owner_map.py` — carries `# OWNER: cody`, is **not** in cody's live
  b11 claim, and hank routed it to cc. One comment line (the header the
  allowlist `--check` requires).
- `docs/defect-density-register.json`, `docs/tier-a-reviews.json`,
  `docs/scrutiny-flags.json` — each required by a push gate before it would
  accept the push, the same collision b8 and b9 both named and resolved the
  same way.

**Conflicts declared and NOT overridden (PR §4.3):** cody's `tests/` files are
read-only here and every test-side change is routed by file:line; hank's `api/`
and `sql/` are read-only; fourth's b18 `docs/` files untouched; no auditor clone
entered or written.

---

## Open, and whose — with the exact next step

| item | owner | exact next step |
|---|---|---|
| **`tests/run_blob_coverage_scope_sabotage.py` arm S2** | **cody** | it fails *because* the gap closed. Invert it to assert the unscanned region is EMPTY (catches a regression to `os.listdir`) or retire it keeping S1. Then **UPDATE** row `docs/known-red-suites.json:1229`, correcting 126→129 |
| **`tests/run_citation_anchor_hop_sabotage.py` register row** | **cody** | clean RECOVERED, 6/6. **DELETE** row `:1247`; note the fix took 3 changes, not 2 |
| **scope-gate arm 6 is presence-not-flow** | **cody** | it checks a guard exists somewhere in the file, not between source and sink. `tests/run_scope_gate_unfetched_base_probe.py` |
| **`api/_lib/sd-store.js:203` RAW, and `writeSlab()` duplicating `id`** | **hank** | `python tools/blob_conversion_coverage.py --list RAW` |
| **3 digests that never name hank (b7, b8, b9)** | **hank** | one token on line 1: `DIGEST hank b<n>`. Re-run `python tools/drive_upload_verify.py --audit` |
| **`SAIRN-digest-h1-b5.txt` says `batch U`, not `b5`** | **H1** | same single-token fix |
| **`SAIRN-handoff-cc-b6.md` holds cody's content** | **Michael** | "filename as requested" reads deliberate. It is the only copy of that state; confirm before anyone renames it. The tool now flags it `WRONG AGENT` |
| **the PEM-shaped file is untracked but not ignored** | **Michael** | `git add -A` in `Documents\SAIRN` would stage it. Move it out of the repo, or add an ignore rule — I did not touch that clone |
| **the push gate's own `OVERRIDE_HINT` still advertises only the blanket flag** | **cc, next batch** | `tools/sairn_push_gate_hook.py:845`. Its own design comment at `:990` claims the refusal text "now names the scoped form first"; the hint printed on every refusal this batch named only `SAIRN_SEED_GATE=off`. The documents are fixed; the hook's own string is not |
| **`fmea_draft.py --save` for 5 tools** | any session **except cc** | `blob_conversion_coverage.py`, `drive_upload_verify.py`, `mech_gate_live_probe.py`, `tool_owner_map.py`, and from b9 `batch_manifest.py`/`sairn_claim.py`. Not by me: my own fixes FMEA'd by me is detector-blesses-its-own-fix |
| **Tier A obligation opened this batch** | **fourth** (auto-assigned) | `python tools/tier_a_review_gate.py` — covers the drive-verify and bare-run changes; cc cannot discharge its own |

---

## Three things that will cost the next session time if nobody says them

1. **A sabotage control that passes is a control whose subject is broken; when
   you fix the subject, the control fails and looks like a regression.** That is
   `tests/run_blob_coverage_scope_sabotage.py` S2 exactly, and `exit 1` is the
   only thing a casual reader will see. When a routed defect is confirmed by a
   suite built to prove it, **fixing it is expected to turn that suite red**, and
   the suite needs re-aiming in the same breath as the fix — by whoever owns
   `tests/`, which is not the person who fixed the tool.

2. **Two tests of "does this line name the resource" needed OPPOSITE treatment
   of string literals, and getting one right hid the other.** A resource key is
   a string (`getItem('sd_comms')`) so strings must stay intact; a storage
   constant is an identifier (`st(K_COMMS, rows)`) so inside a string it is
   prose. I fixed comments, saw the comment arms go green, and would have
   shipped — cody's arm S1b is the only reason the second route was found. **A
   sabotage suite that tests one route per defect class is worth more than a
   tidier one that tests the class once.**

3. **A before/after snapshot cannot attribute a change in a multi-writer
   directory, and the false finding it produces is more credible than a miss.**
   `bare_run_write_check` watched `~/SAIRN-SESSION-LOCKS/` whole, so three
   correct tools were reported as editing other sessions' status rows — specific,
   plausible, naming real files, and the remedy it implied was to go break three
   working tools. Before trusting any snapshot-diff finding, ask **who else
   writes that path while the run is happening**, and check whether the accused
   tool can even reach it: a grep for the path in the subject settled all three
   in one command.
