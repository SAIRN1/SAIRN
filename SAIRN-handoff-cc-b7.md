# SAIRN handoff -- cc batch b7 -- 2026-10-14

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished: all
six items are committed and on `origin/main`, every suite named below has been
run, and no file is mid-edit.
**Companions:** `SAIRN-report-cc-b7.txt`, `SAIRN-digest-cc-b7.txt`,
`docs/batch-manifest-cc-b7.json` (6 items, all `done` with evidence),
`docs/2026-10-13-cc-routed-b7.md` (the b6 account and the `:409` ruling).
**Transcript:** this session's scratchpad is
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\ac16263c-6d67-4305-aa08-5af5dd4be99b\scratchpad\`
— every figure in the report has its raw log there: `duv_probe.log`,
`srr_unpatched.log`, `srr_patched.log`, `srr_patched3.log`, `tiera_probe.log`,
`sgufb.log`, `sgufb2.log`, `shard_check.log`, `shard_check2.log`,
`rop_list.log`, `rop_base.log`.

---

## Committed / pushed state

**HEAD `6841af8f`, `git rev-list --left-right --count origin/main...HEAD` = `0 0`.**
No `--force` in any spelling. **`SAIRN_SEED_GATE` was never used.** Four rebases
during the landing, all conflicts resolved by `tools/sairn_rebase_resolve.py`
(two ledgers merged, two generated documents regenerated), and the two defect
records re-seated onto the rewritten SHAs each time.

| SHA (post-rebase) | what |
|---|---|
| `9603441d` | feat(drive upload verify) — the tool, the 35-arm probe, `batch_manifest --close`, the b7 manifest, the inventory entry |
| `b7aa45b2` | fix(tier a review gate) — `save_reviews` retry + the 10-arm failing-first probe |
| `ced0918e` | fix(open work) — row 221, and the shard regenerated |
| `e89e0a77` | fix(scope gate) — `_have_commit`, the 12-arm probe, the NOT_PROMOTED ruling, the routing doc |
| `c97d1d3b` | chore(defect register) — the two records this push owed |
| `68467498` | chore(derived docs) — MASTER-PLAN, TOOLING-INVENTORY, traceability-matrix regenerated |
| `01c529e2` | docs(routing) — the no-ref-lines refusal corrected to an OBSERVATION |
| + 7 chores | scrutiny-ledger rows the gate wrote per attempt, and three SHA re-seats |

**HOOKS: none added, none restored, `.claude/settings.json` NOT touched by this
batch.** Said precisely, because the honest version is not "this clone has no
hooks": **`.claude/settings.json` is TRACKED at HEAD and carries a SessionStart
hook committed by cc b6 (`eb53e267`, pre-rebase SHA) under a separate
authorisation.** b7 changed neither the file nor the hook. A reader who needs
hooks off in this clone has to decide about b6's commit, not about b7's diff.

---

## The six items

| # | item | state | evidence |
|---|---|---|---|
| 1 | b6 deliverables on the Drive | **DONE as a finding** | cc's b6 report, digest AND handoff **do not exist**, locally or on the Drive. Nothing was uploadable as `-b6-real`. See below. |
| 2 | `tools/drive_upload_verify.py` + manifest wiring | **DONE** | 35/35 arms, `tests/run_drive_upload_verify_probe.py`; `--audit` found **6 of 151** named Drive files whose name disagrees with their first line |
| 3 | `save_reviews()` retry | **DONE** | 335 → 0 `PermissionError` in 400 concurrent saves; 10/10 arms over 3 runs |
| 4 | open-work row 221 | **DONE** | one line changed, pipe count 8 → 8, count re-derived as 36 of 36 |
| 5 | `scope_gate.py:409` | **DONE, and the ruling is recorded** | fix applied + 12/12 arms; the 6-arm checker DECLINED with the measurement |
| 6 | push without force, confirm landed | **DONE** | `0 0` against `origin/main`, HEAD `6841af8f` |

### Item 1, stated plainly because it is a finding about cc

The Drive folder's newest cc digest and report are **b5's**. The one b6-named cc
file, `SAIRN-handoff-cc-b6.md`, is **2,162 bytes with the first line
`# cody b6 handoff (filename as requested)`** — and the local file of the same
name is **byte-identical** (`sha256 a2876991…`). So there was no cc b6 handoff
to upload under a corrected name; **cc b6 wrote none of its three
deliverables.** What b6 *did* push is listed by SHA in
`docs/2026-10-13-cc-routed-b7.md` §1: four tools, then a close with no report.
That is the failure item 2 exists to stop, and it was ours.

---

## Open, and whose — with the exact next step

| item | owner | exact next step |
|---|---|---|
| **the 6 Drive files whose name disagrees with their content** | each named agent | `python tools/drive_upload_verify.py --audit`. `SAIRN-handoff-cc-b6.md` (cody's content), `SAIRN-digest-cody-b5/b6/b7.txt` and `SAIRN-digest-hank-b7.txt` (first line names no agent), `SAIRN-digest-h1-b5.txt` (names batch U). **Each owner fixes their own**; the tool reports and never renames. |
| **every agent should run the verify at close** | all four build agents + both auditors | `python tools/drive_upload_verify.py --agent <you> --batch b<n>` then `python tools/batch_manifest.py --close --agent <you> --batch b<n>`. There is **no hook** — this is a command, deliberately. |
| the Drive-side API read that closes the sync-mount limit | any chat turn | the tool proves bytes are in the sync set, **not** that Google acknowledged them. One `google_drive` read of folder `14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` closes it. |
| **`register_feed_gate` refused twice with "stdin carried NO ref lines"** | whoever next claims that file | **a REPRODUCTION, not a patch.** The easy explanation is ruled out: this clone was behind later in the same batch and the refs arrived fine. `docs/2026-10-13-cc-routed-b7.md` §2.3 has both observations. |
| the WEAKENING flags this push wrote | a reviewer, not me | 3 paths in `docs/scrutiny-flags.json` under this batch's commits: all three are prose inside string literals (`ignore_errors=True` in a `rmtree` teardown, a label containing the word "skip"). **Reported, not discharged by the session that caused them.** |
| the 6-arm unfetched-base checker | nobody, by decision | **NOT_PROMOTED** with the reason in `tools/report_only_checks.py`. Promote it if a fourth instance appears despite arm 6 of `tests/run_scope_gate_unfetched_base_probe.py`, or if the population passes ~6 files (it is 3). |
| 4 FMEA drafts the register asked for | any session | `python tools/fmea_draft.py <path> --save` for `tier_a_review_gate.py`, `hover_auditor_scope_gate.py` and the two new probes. Not done here; it would have been four unreviewed drafts filed by the session that caused the defects. |
| **Tier A: the obligations cc still holds** | cc | `python tools/tier_a_review_gate.py --list`. Not discharged this batch and not re-measured either — **that is an UNVERIFIED line, not a zero.** |

---

## Claims held

**`cc`, claimed and pushed as `d29b8846` at the start of this sitting** (the
earlier b7 claim had expired; the first `claim` call did not reach `origin/main`
and the tool said so rather than reporting success — it was re-run after the
rebase, as it instructs). **Release it with
`python tools/sairn_claim.py release cc` once the three deliverables are
uploaded.** Status registry row set to `working` at the start.

**Conflicts declared and NOT overridden (PR §4.3):**
`docs/by-design-register.json`, `docs/METHODOLOGY.md`,
`docs/external-files-index.json` and `docs/2026-10-13-fourth-b11-routed-to-cc.md`
are in **fourth's live b12 FILES**. None was written. Item 5's ruling is in
`docs/2026-10-13-cc-routed-b7.md` and `tools/report_only_checks.py` instead of
in the by-design register, which is the mechanism fourth's own routing named.

**Files written that were NOT in cc's declared b7 FILES**, said out loud:
`tools/hover_auditor_scope_gate.py`, `tests/run_scope_gate_unfetched_base_probe.py`,
`tools/report_only_checks.py`, `tools/tooling_inventory.py`,
`docs/SAIRN-OPEN-WORK-INDEX.md`, `docs/open-work/sairnfreedom.md`,
`docs/defect-density-register.json`, `docs/scrutiny-flags.json`,
`docs/MASTER-PLAN.md`, `docs/TOOLING-INVENTORY.md`,
`docs/traceability-matrix.md`. No session held an active claim on any of them.
**The claim string named `tools/review_store.py` for item 3 and that file does
not exist** — `save_reviews()` lives in `tools/tier_a_review_gate.py`, which is
what was patched. No task string was reworded to slip the matcher.

---

## Three things that will cost the next session time if nobody says them

1. **A new `tools/*.py` cannot be committed without a PURPOSES entry, and the
   pre-commit hook says so at commit time rather than at push time.** Write the
   `tooling_inventory.py` entry *when you write the tool* — naming what it
   CATCHES, not what it does — and stage both together. Then expect the push
   gate to demand `master_plan.py`, `tooling_inventory.py` and
   `traceability_matrix.py` be regenerated, because adding a tool changes all
   three.

2. **Four rebases in one landing is the normal case now, not bad luck.** Five
   sessions push one branch; two of my attempts were rejected with
   `cannot lock ref` *mid-push* because another clone landed between the gate
   and the ref update. The loop that works: commit the ledger rows the gate just
   wrote → `git pull --rebase origin main` → `python tools/sairn_rebase_resolve.py`
   → `git rebase --continue` → commit the re-seated register → push. **Never
   `--force`.**

3. **`os.replace` is not atomic-and-safe on this platform, it is
   atomic-and-fragile.** Safety holds; a concurrent writer *errors*. 335 of 400
   is the measured rate. Any other tool that writes a shared file through
   `mkstemp` + `os.replace` has the same defect right now: **`grep -l
   "os.replace" tools/*.py` returns SEVEN** — `capture_exit.py`,
   `clone_health_check.py`, `ledger_append.py`, `sairn_status.py`,
   `session_lock_check.py`, `tier_a_review_gate.py`, `tooling_inventory.py`.
   **Only `tier_a_review_gate.py` was fixed, because it is the one cody
   measured.** The other six are UNEXAMINED, not cleared — `sairn_status.py`
   and `ledger_append.py` are the two with real concurrent writers.
