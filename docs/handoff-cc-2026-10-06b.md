# CC handoff — 2026-10-06 (second), batch 10

**Second handoff of the day.** The first (`docs/handoff-cc-2026-10-06.md`) closed
out batch 9. This one covers batch 10: the `checker_selftest_check` false-reason
fix, the **root-cause** fix for the rebase-orphaned SHA citations, the registry
import-refusal moves, and the active-work citation table.

**Baseline for every figure below: `411f29ce`, re-derived at HEAD after a fetch,
2026-10-06.** Every exit code was read from a status file written by
`tools/capture_exit.py`; none is quoted from a harness notification.

**Transcript:** this session's conversation. There is no file on disk — if it is
needed it must come from the terminal scrollback.

---

## 1. Committed and pushed

| what | where |
|---|---|
| `tools/checker_selftest_check.py` | the false third-state reason, §2 of the inventory |
| `tools/doc_sha_reseat.py` **(new)** | the root-cause fix, §3 |
| `tests/run_doc_sha_reseat_probe.py` **(new)** | 19 arms, EXIT 0 |
| `.githooks/post-rewrite` | second consumer wired; map captured once, fed twice |
| `tools/checker_control_check.py`, `tools/traceability_matrix.py`, `tests/run_export_coverage_probe.py` | bare module-level hoist |
| `tools/flaky_checker_quarantine.py`, `tools/invocation_path_scan.py` | **guarded** module-level hoist + the `sys.path` insert that had to move with it |
| `docs/2026-10-06-cc-batch-10-inventory.md` **(new)** | the full account |
| `docs/2026-10-06-cc-routed.md` §10–12 | three routings, each with a reproducing artifact |
| `SAIRN-ACTIVE-WORK-cc.md` | the 26-row SHA citation resolution table, appended |
| `docs/hook-manifest.json` | regenerated — a changed hook and a new hook-invoked tool |

**Verify it landed, don't trust this table:**

    git fetch origin && git rev-list --left-right --count origin/main...HEAD
    git log --oneline -3 origin/main

---

## 2. Claims

**Held by this session:** subject `cc`, batch 10. **Release when this handoff is
accepted:**

    python tools/sairn_claim.py release cc

**Three conflicts were declared in the claim text and none was reworded past
(PR §4.3):**

* **cody** — `docs/tier-a-reviews.json` AND the most-overdue-first discharge,
  claimed `2026-10-06T14:53:05Z`, task text that phrase verbatim. Also
  `tools/dead_rule_sweep.py`.
* **hank** — `docs/SAIRN-OPEN-WORK-INDEX.md`, `docs/METHODOLOGY.md`,
  `docs/CRITICALITY-TIERS.md`, `docs/TOOLING-INVENTORY.md`.
* **fourth** — `docs/2026-09-13-cross-domain-disciplines.md`.

---

## 3. OPEN — 25 review obligations, none discharged, and the reason

**Listed as instructed; not discharged.** 235 records in
`docs/tier-a-reviews.json`, 32 open, 7 authored by `cc` (not eligible — a change
is reviewed by a session other than its author), **25 eligible to me.**

**MOST OVERDUE: `(hank, 2026-09-27T01:22:40Z)`, 230h**, resources
`mech_insurance_policies`, `mech_site_assets`, `sc_anesthesia…`.

**WHY IT IS STILL OPEN.** cody holds that file under a live claim doing
most-overdue-first discharges right now. The file's `merge_policy` is
`union-by-identity` on `(author_session, opened_at)` and
`tools/sairn_rebase_resolve.py` **REFUSES** when both sides change the same
record differently — and two sessions both working most-overdue-first choose the
*same* record, not different ones.

**EXACT NEXT STEP:** when cody releases, run

    python tools/tier_a_review_gate.py --list

re-derive the oldest at that moment (it will have moved), and discharge from the
top. **Do not take the 230h one from this document** — by the time it is read,
cody may have discharged it, and this line is only true as of 17:03Z.

---

## 4. OPEN — the "universal" import guarantee is 7 of 13, not 13 of 13

The brief asked for all 7 deferred imports moved so the registry refusal always
arrives at import. **Six moved. The seventh is cody's.** And the premise turned
out to be incomplete, which matters more than the one I could not move.

**MEASURED, lines of a program's OWN output before the refusal, fault injected
in a detached worktree, control first:**

* **1 of 6 improved measurably** — `tests/run_export_coverage_probe.py`, **30 →
  0**.
* **3 of 6 were already 0**; the move removes a dependency on call order, which
  is real and which **nothing in this batch tests**.
* **2 of 6 improved in ways this metric cannot see** — `checker_selftest_check`
  (false reason → real cause) and `invocation_path_scan` (no cause → cause).
* **`flaky_checker_quarantine` stays at 36 by design** — its labelled REGEX
  FALLBACK is the better behaviour and a bare hoist would have deleted it.

**AND SIX PROBES ALREADY HAD MODULE-LEVEL IMPORTS AND STILL RUN 11–147 LINES
FIRST**, because a module-level import 184 lines down executes 183 lines of
module body before it: `run_baseline_readiness_probe` **147**,
`run_literal_drift_control_probe` 44, `run_optimistic_success_probe` 44,
`run_dora_metrics_probe` 21, `run_risk_event_tree_probe` 19,
`run_assurance_case_probe` 11.

**EXACT NEXT STEP:** "module level" is the wrong target; the **import header**
is. Those six are in nobody's claim. Hoisting each to the header beside its other
imports is the remaining work, and each needs a before/after on the same metric
rather than an assumption that it helped.

**13 of 13 fail closed under the fault; none reports a clean run.** That part was
already true and is unchanged.

---

## 5. OPEN — `tools/dead_rule_sweep.py`, COULD NOT RUN AT A 900s BOUND

The seventh deferred import, at `:488` inside `registry_tools()`. **Both arms of
a fault-injected run hit a 900-second ceiling — control `exit 124`, a timeout, no
verdict either way.** Per the bound rule in `67080039` that is **COULD NOT RUN at
a stated bound**, never a pass. The cause is that the sweep builds its own git
worktree before reaching the import.

**EXACT NEXT STEP:** cody's, routed in `docs/2026-10-06-cc-routed.md` §11 with
the two-line guarded-hoist shape and the warning not to hoist it bare.

---

## 6. OPEN — 37 open-work index rows, now proposed automatically

46 of 367 backticked SHA citations in `docs/SAIRN-OPEN-WORK-INDEX.md` do not
resolve on `main` (321 ON-MAIN / 8 ORPHAN / 38 ABSENT), across 37 rows.

**THE ROWS THEMSELVES ARE STILL UNFIXED** — hank holds the file. What changed is
that nobody has to paste a list any more: on the next rebase or `--amend` in any
clone, `.githooks/post-rewrite` runs `tools/doc_sha_reseat.py --post-rewrite`,
which prints the exact substitutions and **proposes rather than writes** while
another session holds the file.

**EXACT NEXT STEP (hank):** fix the index rows **first**, then regenerate
`docs/traceability-matrix.md`. The other order produces a generated file that
disagrees with its source and a push the gate refuses for staleness.
`docs/2026-10-06-cc-routed.md` §10 has the detail and the correction to §9.

---

## 7. OPEN — `docs/2026-09-13-cross-domain-disciplines.md` item 11 has no body

**Reproducing artifact:** `sed -n '447,449p' docs/2026-09-13-cross-domain-disciplines.md`
at `411f29ce` — two adjacent headings, and everything after them is item 12's.

`CLAUDE.md` tells every session to count the `## <n>.` headings rather than trust
a figure, so item 11 is counted as present on every read. It cost real time this
batch: `doc_sha_reseat.py`'s central design decision is propose-vs-apply, which
is item 11's subject, and the rule had to be reconstructed from
`.githooks/post-rewrite`'s own header instead.

**EXACT NEXT STEP:** fourth's file; routed in §12. Not fixed by me — writing the
body of somebody else's convention is not a formatting repair, and I have the gap
without the incident that bought the rule.

---

## 8. CLOSED this batch

* **`checker_selftest_check.py`'s false reason.** Three arms driven (raise /
  genuinely empty / module absent), each exit **2** with its own real cause; the
  **pre-fix** control produced byte-identical output for two different causes,
  `diff` 0 lines. `tests/run_checker_selftest_probe.py` **23 passed, 0 failed,
  EXIT 0**, and the clean-path output is byte-identical to before.
  **I reintroduced the defect one line lower and the drive caught it** — a
  reassurance that was true of the raise case and false of the absent case; the
  deletion is commented in place.
* **The root cause.** `tools/doc_sha_reseat.py` + the hook wiring. Driven end to
  end through the hook with a one-pair map, **EXIT 0**; both consumers saw the
  map; the HEAD control re-seated the register and said nothing about documents.
  **The first version of the file-class list was wrong and the drive found it** —
  `traceability-matrix.md` is GENERATED and a correct patch to it would have been
  discarded by the next generation while reading as fixed.
* **The two locked temp dirs.** Both gone; the lock was a live process, and the
  retry after it exited worked. Neither was registered as a worktree. The
  honest correction is that the first report should have said *"held by a live
  process"* rather than *"genuinely inert"*.
* **`SAIRN-ACTIVE-WORK-cc.md`'s citations.** **It is 26, not 19** — seven of the
  extra are mine from today. 16 RESOLVED by unique subject match, **6
  QUOTED-AS-DEAD and deliberately untouched** (repointing them would delete the
  finding), 3 UNRESOLVABLE, 1 NO-SUBJECT-MATCH. Appended as a table; nothing
  above it edited.
* **One methodology rule**, §8 of the inventory, routed to hank for
  `docs/METHODOLOGY.md`.

---

## 9. What this session did NOT do

* **Did not discharge a review obligation.** 25 eligible, oldest 230h. Correct
  refusal, still 25 open.
* **Did not touch** `docs/SAIRN-OPEN-WORK-INDEX.md`, `docs/METHODOLOGY.md`,
  `docs/CRITICALITY-TIERS.md`, `docs/TOOLING-INVENTORY.md`,
  `docs/tier-a-reviews.json`, `tools/dead_rule_sweep.py`,
  `docs/2026-09-13-cross-domain-disciplines.md` — all under live claims.
* **Did not test the call-order property** the three 0→0 import moves are
  justified by.
* **Did not run `doc_sha_reseat.py`'s write path on a real tracking document** —
  every REWRITE target was claimed all day. The write path is proven against
  temp trees in 19 probe arms and nowhere else.
* **Did not live-verify anything against a deployment.** Every item is a
  build-time tool, a hook or a document; none has a deployed surface.
* **`tests/run_report_only_checks_probe.py` is UNBOUNDED BY ME** — it exceeded
  two 2-minute foreground windows and a background run's status file still read
  `RUNNING`, which is the third state and not a pass. **Its subject
  (`tools/report_only_checks.py`) was not modified this batch and its import was
  already eager**, so it is not a regression gate for this work — but it is also
  not a green I am claiming.

---

## 10. ADDENDUM — written after the push, because three things only happened there

### The push gate refused three times and all three were correct

`06547eb4` is the pushed tip. It took two commits, not one, because the gate
stopped the first:

1. **`tools/doc_sha_reseat.py` had no `# OWNER:` line.** Added `# OWNER: cc`.
2. **A new `tools/*.py` cannot land without a `PURPOSES` entry**, and the
   generator exits 2 rather than emitting a blank cell. **`tools/tooling_inventory.py`
   is HANK'S under a live claim.** Declared, not reworded past: **one additive
   key, no existing entry edited, no generator logic touched**, with a comment at
   the insertion point stating that scope so hank can see it without reading a
   diff. **The coupling is the finding, not the edit** — any session adding any
   tool must write into whichever session happens to hold the inventory that
   hour. The gate is right to demand the entry; the two systems pull against each
   other and the only honest options were "declare and add one key" or "do not
   land the tool".
3. **Three generated documents were stale.** Regenerated, each generator **EXIT
   0**, and **every delta is attributable to this batch**: `docs/MASTER-PLAN.md`
   went 896 → 897 test files on disk, traced-gap 182 → 183, worst case 823 → 825
   — that is `tests/run_doc_sha_reseat_probe.py` and nothing else.

**AND THE GATE REACHED MY OWN CONCLUSION INDEPENDENTLY.** Two of those three
documents — `TOOLING-INVENTORY.md` and `traceability-matrix.md` — are exactly the
ones `doc_sha_reseat.py` classifies as GENERATED and refuses to patch. The gate's
instruction was *regenerate, do not edit*, which is what the tool's own drive
concluded hours earlier by a completely different route.

### The tool fired in production during my own rebase, and said the right thing

`git rebase origin/main` hit a conflict in two generated documents.
`tools/sairn_rebase_resolve.py` classified both as GENERATED, regenerated rather
than merged, and staged them. Then `git rebase --continue` fired
`.githooks/post-rewrite`, and the **last lines of the rebase output were my new
tool's**:

```
tracking documents. Nothing to do.
REPORT-ONLY, never rewritten (append-only logs):
  SAIRN-ACTIVE-WORK-{cc,cody,fourth,hank}.md
```

**That is the first real firing, and "Nothing to do" is the correct answer** — the
rewrite moved only my own two commits, which no tracking document cites. Blind
spot 3 of the inventory still stands: this exercised the no-op path, not the
write path.

### `docs/hook-manifest.json` needed regenerating TWICE and the second time was my fault

The first regeneration recorded `doc_sha_reseat.py` at `1fadc7381127`. Then the
gate made me add the `# OWNER:` line, which changed the file to `003baf096225`,
and the integrity check correctly refused again — *"CHANGED IN A COMMIT AND THE
MANIFEST WAS NOT REGENERATED."* **A manifest regenerated before the last edit is
a manifest that blesses the wrong bytes**, which is this batch's own methodology
rule in miniature: the act of completing the work changed the value I had just
recorded about it.

### State at the end

    git fetch origin && git rev-list --left-right --count origin/main...HEAD   # 0 0
    python tools/capture_exit.py --status /tmp/h.st -- python tools/hook_integrity_check.py
    python tools/capture_exit.py --read /tmp/h.st                              # expect EXIT 0

**`tests/run_report_only_checks_probe.py` is still unbounded by me** and is still
not a green I claim — see §9.
