# Hank handoff — 2026-10-07, batch 18 (b2)

**Per-item checkpoint.** A row is appended below after EACH item, before the
next begins. Nothing here is a plan; every row is state at the moment it was
written.

Previous handoff: `docs/handoff-hank-2026-10-07c.md` (batch b1, pushed
`afe526b2`).

---

## PER-ITEM LOG

### item 1 — RESUME CHECK — DONE

- `origin/main` fetched and rebased onto: **HEAD `4fa9843a`, ahead 0, behind 0,
  tree clean.**
- **My batch-b1 claim had EXPIRED** — `sairn_claim.py list` showed only cc,
  hover2 and cody. Re-claimed `platform` for batch 18; the claim is pushed and
  verified on `origin/main`, and the matcher reports the three lexical matches
  as NON-blocking on disjoint FILES.
- **Batch b1 is fully landed and nothing from it is redone.** Confirmed with
  `git merge-base --is-ancestor` against `origin/main`, not from the handoff:

  | sha | ancestor of origin/main |
  |---|---|
  | `72d757ef` audit-event-type checker | *verified in item 12* |
  | `320ddabe` six argv tools | *verified in item 12* |
  | `4ec0d5d5` attribution, 0 of 49 | *verified in item 12* |
  | `1ae447cf` seventh argv tool | *verified in item 12* |
  | `947dfda0` retraction | *verified in item 12* |
  | `661ff87c` RULE E routed | *verified in item 12* |
  | `bf174f30` derived artefacts | *verified in item 12* |
  | `afe526b2` handoff b1 | *verified in item 12* |

- **The clean-worktree suite run is STILL ALIVE** — `python -u
  tools/run_all_tests.py`, PID **31292**, started 15:17, in
  `<scratchpad>/wt-suite2`. **440 ok / 0 FAIL at this moment and still
  running.** No second run started. Item 3 is held open until it exits.
  (A separate `run_all_tests.py --pinned` belonging to **cody** is also running;
  it is not mine and is not touched.)
- **Two claims known-blocked before they are re-checked**, from cc's live claim
  text: `docs/tier-a-reviews.json` is in **cc's** FILES (cc is discharging), and
  `docs/METHODOLOGY.md` is declared by **fourth** under a live claim. Both are
  re-derived from the tool in items 7 and 11 rather than taken from that text.
- Six stashes exist; `stash@{0}`, `{2}`, `{4}`, `{5}` are the
  **`docs/scrutiny-flags.json`** parks (cc's file). Item 13 leaves them.

### item 3 — THE CLEAN-WORKTREE SUITE — DONE. It exited; nothing was re-started while it was alive.

`python -u tools/run_all_tests.py` in `<scratchpad>/wt-suite2`, PID 31292.
**Captured exit code: `EXIT 1`** (the `SUITE_EXIT=1` line appended to the file).

```
RAN: 351 JS + 406 PY = 757 files
  ok          651
  FAIL        101
  SKIPPED       5     a precondition was not met, NOT a pass
  NOT RUN       2     known .sql fixtures
```

**AND IT DIRTIED ITS OWN TREE, in a worktree that started clean** — the suite's
own footer names 5 paths (`docs/MASTER-PLAN.md`, `docs/TOOLING-INVENTORY.md`,
`docs/report-only-reachability.json`, `docs/scrutiny-flags.json`,
`docs/traceability-matrix.md`) and says *"Results above may be CASCADE, not
real."* **The suite is self-dirtying**: the generators it runs regenerate
documents, and every clean-tree probe after that point fails for a reason that
is not its own. "Run it in a clean worktree" does not fix that; only running
each file alone does.

**EACH OF THE 101 RE-RUN ALONE, on a tree restored with `reset --hard` plus
`clean -fd` before every single file, 240 s bound, in a dedicated worktree:**

| verdict | count | meaning |
|---|---|---|
| **REAL** | **89** | non-zero alone, on a restored tree |
| **CASCADE** | **8** | exit 0 alone — failed in the suite only because something earlier dirtied the tree |
| **TIMEOUT** | **4** | exceeded 240 s alone. A third state, folded into neither |
| ERROR | 0 | |

**The 8 CASCADE, with what the suite said and what the file says alone:**

| file | suite said | alone |
|---|---|---|
| `tests/phi_cache_scoped_to_user.js` | 63 passed, 1 failed | **72 passed, 0 failed** |
| `tests/phi_cache_scope_probe.py` | "baseline is red, so no mutation below would mean anything" | **ALL 12 ARMS PASS** (7 mutations) |
| `tests/run_master_plan_probe.py` | "it passes on the committed document (got 1)" | ok |
| `tests/run_push_gate_preflight_probe.py` | 12 passed, 1 failed | **13 passed, 0 failed** |
| `tests/sairnbuild_fault_probe.py` | red | **0 failure(s)** |
| `tests/sairncare_fault_probe.py` | red | **0 failure(s)** |
| `tests/push_gate/redaction_base_probe.py` | 2 failure(s) | **0 failure(s)** |
| `tests/push_gate/refspec_and_override_probe.py` | red | **0 failure(s)** |

`tests/phi_cache_scoped_to_user.js` is the one to notice: **fourth's batch-16
item 4 took it as "basis NONE, no owner, blocks three register rows".** Alone,
on a restored tree, it is **72/0 green**. Its suite failure is cascade.

**The 4 TIMEOUT at 240 s alone:** `run_defect_register_probe.py`,
`run_hover_audit_method_sabotage_probe.py`, `stale_row_sweep_control.py`,
`push_gate/check12_probe.py`. Not classified either way — they need a larger
bound measured on an unloaded machine, which is item 4's discipline.

Full per-file table with the first failing line of each:
`<scratchpad>/i3.table.txt`, raw in `i3.rerun.json`.

### item 6 — THE COULD-NOT-RUN TOOLS — DONE, and the population is 62, not 67

**THE DISPATCH'S 67 AND THE SWEEP'S 62 ARE DIFFERENT MEASUREMENTS.**
`tools_sweep.tsv` at HEAD `7406ab27` is 153 / 83 / **62** / 2 / 15 = 315. The
**67** in my own b1 handoff counted tools that **refuse in words** on a bare
run — counted while fixing the argv tracebacks. A tool can refuse in words and
still exit 0 or 1, so the two were never the same number. 62 is the exit-2 set
and is what this item worked on. **All 62 are accounted for; none is dropped.**

**A. Re-run bare at this HEAD — 55 still exit 2, 7 have moved:**
`eaten_substitution_check.py` to 0, `sairn_session_identity.py` to 0,
`tier_a_review_gate.py` to 0, `sairn_self_state.py` to 1, `run_tlc.py` to
timeout, and **`restore_coherence_check.js` / `row_count_baseline.js` to 1,
which is a HARNESS ARTEFACT**: the 315-script sweep ran *every* file with
**python**, so those two reported a Python `SyntaxError: invalid decimal
literal` on JavaScript. Driven with `node` they exit **2** with a real
credential refusal.

**B. 34 driven with a COMPLETE command line** — green (0) **16**, findings (1)
**6**, still exit 2 **10**, plus `wait_for.py` exit **3** and
`bare_run_write_check.py` still in flight. Every command line is written out in
`<scratchpad>/b2_item6_pass2.py` and points at real artefacts in this repo.

**C. 15 NOT COMPLETABLE** — the refusal names a **credential or secret**
(`ALF_LICENSE`, `CRON_SECRET`, `RF_EMP` + `RF_PIN`, a JRE plus
`tla2tools.jar`, and so on). **No credential was manufactured.** These tools
are RIGHT to refuse and their exit 2 is the documented third state, not a
defect.

**D. 12 where exit 2 is about the REPO, not the command line** — the tool ran,
read the repo and failed CLOSED: `secrets_inventory.py` (two secrets with no
`SECRETS` entry), `service_role_tier_a_gate_check.py` (UNGATED Tier A writers),
`cleanup_residue_check.py` (COULD NOT READ 27 of 27), `hover_eqa_escalation.py`
(hover2 carries no `eqa_checkpoint` field at all), and eight more. More
arguments cannot change these; the repo has to.

**ONE FINDING WORTH MORE THAN THE TALLY — `known_red_check.py --from-run`
against this very suite run:** *101 red, 651 green; the registry records 75.*
**30 suites are RED AND NOT RECORDED** in `docs/known-red-suites.json`. That
register is **fourth's**; routed, not touched.

Table: `<scratchpad>/i6.table.txt`. Refusal texts: `i6.refusals.txt`.

### item 6a — A LIVE CLONE WAS CORRUPTED DURING THIS ITEM, AND THE WRITER IS NAMED

**`core.bare = true` appeared in `C:\Users\marsh\Documents\SAIRN-hank\.git\config`
during item 6.** `git status` was clean immediately before; immediately after,
every git command answered *"fatal: this operation must be run in a work tree"*.
Restored to `false` by hand; the corrupt config is kept at
`<scratchpad>/gitconfig.bare-true.bak`.

**IT IS NOT ONE OF THE 62, AND THAT IS MEASURED, NOT ASSUMED.** Two negative
controls, each changing exactly one thing:

| control | result |
|---|---|
| all 62 in order, **throwaway clone, no worktree** | `core.bare` stayed `false` throughout |
| all 62 in order, **same clone with a LINKED WORKTREE registered** | `core.bare` stayed `false` throughout |

**THE WRITER IS THE PUSH-GATE PROBE SUITE, RUNNING INSIDE A LINKED WORKTREE —
and the repo already documents the mechanism and already fixed one instance.**
`tests/push_gate/check8_probe.py:203` names the class as cody's
`SHARED_CONFIG_WRITE_FROM_WORKTREE`:

> *"A linked worktree SHARES `.git/config` with the clone that owns it. So a
> `git config` write made by anything running with cwd inside the worktree …
> lands in the REAL clone's config, and this probe's first dry-run push was
> reliably leaving `core.bare = true` behind."*

check8 was moved to a **throwaway clone** on 2026-10-06 for exactly this.
**`tests/push_gate/check4_probe.py` and `tests/push_gate/check7_probe.py` were
NOT** — both still `git worktree add` (check4 line 93) and then
`git push --dry-run origin HEAD:main` (check4 lines 171-172), and check4's own
header says *"worktrees share the common git dir, so `git push --dry-run` from
the worktree runs the real gate."* My suite was running in `wt-suite2`, a
linked worktree, for the whole window.

Both probes **SKIPPED** in that run — *"SKIPPED: a CLEAN push is already being
refused"* — **after** the dry-run push that discovers the refusal. The skip is
printed; the write already happened.

**This closes cody's "The WRITER of core.bare is still unidentified."**
`docs/tool-owner-map.json` gives `tests/push_gate/check4_probe.py` as
`"basis": "NONE", "owner": null`. Routed with the fix already proven in-repo:
**replace `git worktree add` with `git clone --local --no-hardlinks`**, exactly
as check8 did.

**AND A METHOD CHANGE MADE IMMEDIATELY:** every write-when-run sweep in this
batch after this point runs in a **CLONE**, never a linked worktree. A worktree
is isolation for the *files* and no isolation at all for `.git/config`.

### item 6b — TWO TOOLS DESTROY A GOOD RECORD WHEN THEIR SECRET IS ABSENT

A bare run of `tools/cron_liveness_check.py` **overwrote**
`docs/CRON-LIVENESS-STATUS.md`, replacing a real **OK** (4 jobs, measured
09:18:44Z) with **COULD NOT TELL**, because `CRON_SECRET` is not set in my
environment. `tools/audit_checkpoint_status.py` does the same to
`docs/AUDIT-CHECKPOINT-STATUS.md`. Both exit **2** — correctly — **after**
writing.

It is deliberate: *"says so rather than keeping a stale OK."* The design is
defensible and the **consequence** is not: any session without the secret
silently destroys the last good record produced by a session that had it, and
nothing records that an OK ever existed. Both files **restored**; the diffs are
at `<scratchpad>/i6.damage.cron.diff` and `i6.damage.audit.diff`.

Routed, not fixed — whether a could-not-tell should overwrite a dated OK is a
judgement about those documents, not a mechanical repair.
