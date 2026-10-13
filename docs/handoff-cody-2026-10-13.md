# Handoff — cody, batch 27 (b5), 2026-10-13

**Landed and pushed: `054ffcd0` on `main`, 0 ahead / 0 behind.**
Written before the report, with nothing half-finished. Every figure here was
produced by `evidence.py` (path in §6) or by a named command quoted beside it.

---

## 1. Committed and pushed state

14 commits on this branch's own line (`--first-parent`), 13 files, **2,820
insertions / 41 deletions** over this batch's own paths.

| | |
|---|---|
| HEAD | `054ffcd0` |
| first b5 commit | `fa6a390e` (law role matrix) |
| branch | `main`, pushed, 0 ahead / 0 behind |
| claim | **released** — see §4 |

**This branch was MERGED into `origin/main`, not rebased, and that was forced.**
`tools/sairn_rebase_resolve.py` **correctly refused** to replay the rebase: one
of my commits re-stamps two register records' `commit` field onto post-rebase
shas, which is a MODIFICATION, and the resolver's rule is append-only — it read
it as "4 ancestor records DELETED" and said so out loud rather than letting a
union silently restore the stale versions. That refusal is the tool working. A
merge has no sha re-stamping to replay, so the register merged cleanly by
`(commit, summary)` identity: **517 ancestor + 2 only-ours + 3 only-upstream =
522, zero lost**, validated by `defect_register.py --check` before it was
written.

---

## 2. Per item

| # | item | state | where |
|---|---|---|---|
| 1 | law role matrix, 19 resources × 3 roles | **D** | `api/_lib/law-roles.js`, `api/sd-data.js` (2 call sites) |
| 2 | 19×3 role-matrix test, fails on any resource with no rule | **D** | `api/sd-data-law-role-matrix.test.js` |
| 3 | monotonicity metamorphic relation, control-paired | **D** | same file, sections D / D1 |
| 4 | per-firm permissions spec, docs only, no build | **D** | `docs/2026-10-13-cody-b5-law-permissions-spec.md` |
| 5 | sen_caregivers redaction across EVERY read path | **D** | `api/sd-data-sen-caregiver-read-paths.test.js` |
| 6 | check4/check7 verdicts runnable locally | **D** | `tests/push_gate/_local_remote.py` + both probes |
| 7 | `tools/dup_dom_ids_check.py`, report-only, control-paired | **D** | tool + `tests/run_dup_dom_ids_probe.py` |
| 8 | sabotage-probe flake: find the nondeterminism | **D** | cause found, and it is NOT what b4 said — §3 |
| 9 | FMEA drafts: locate or confirm never committed | **D** | §3 |
| 10 | 145 no-sha records: derivable vs absent, counts only | **D** | §3 |
| 11 | claim-matcher collision, finding + fix proposal for cc | **D** | `docs/2026-10-13-cody-b5-routed-to-cc.md` |
| 12 | citator verification script, prepared, NOT run | **D** | `tools/verify_citator_feedback.py` |
| 13 | this handoff | **D** | |
| 14 | report + digest | in progress at the time of writing | |

**Nothing is partial and nothing is not-done.** Two items produced answers that
contradict the brief's premise, which is in §3 rather than hidden in a D.

---

## 3. The four results that are not just "done"

### Item 8 — the b4 "flake" was NOT a flake, and I misattributed it in b4

**The b4 report called it a Windows `os.replace` flake. That was wrong and this
corrects it.** Measured three ways:

- **20 sabotage-probe runs in an isolated clone: 20 × exit 0.** No recurrence.
- **The b4 failure had a stated cause I under-read.** The b4 log says in its own
  words: *"FILES THIS CLONE HAS CHANGED THAT THE SUITE NAMES AND `stage` DOES
  NOT: docs/tier-a-reviews.json. The worktree is at HEAD, so the baseline just
  measured the OLD version of these against a suite that expects the new one."*
  My working tree had 5 reseated records in that ledger and the probe's `stage`
  did not include it. **The variable was tree cleanliness, not scheduling.**
- **But there IS a real, separate, permanent defect, found on the way.**
  Arms 11 and 12 of `tests/run_tier_a_review_gate_probe.py` start **two threads
  that both call `save_reviews()` on the same path**, barrier-synchronised to
  collide deliberately. `os.replace` is atomic on POSIX; on Windows it is
  `MoveFileEx`, which fails `ERROR_ACCESS_DENIED` when the destination is held
  open — including by a concurrent `MoveFileEx` on the same target.
  **Driven directly: 305 of 400 iterations raise `PermissionError [WinError 5]`.
  And all 12 of 12 gate-probe logs contain it while all 12 exit 0.**

  **So it is not a flake — it is a PERMANENT silent failure.** The exception
  happens in a thread, so `threading` prints it and the exit code is unaffected,
  and the arm's own assertions still pass because the *other* thread's save
  succeeded. **Arm 11 has been asserting atomicity against a race in which,
  three times out of four on this platform, only ONE writer ever completed.**
  The arm is weaker than it reads, permanently, on Windows.

  **NOT FIXED — item 8 asked for the cause.** Open, owner cody, §5 item 1.

### Item 9 — the FMEA drafts are not missing; two specific ones were never written

- `docs/fmea/` holds **112 files on disk and 112 git-tracked, zero drift in
  either direction.** Nothing is lost.
- The two the b4 FMEA loop named — `tools/tier_a_review_gate.py` and
  `tests/run_tier_a_review_gate_probe.py` — have **no draft on disk, none in
  git, and no history at all.** Never committed.
- **Coverage is the real finding: 831 distinct files appear in the defect
  register and 108 have a draft. 13%.** So "was this foreseen?" is
  unanswerable for seven files in eight.

### Item 10 — the 145 no-sha records, classified

| bucket | count |
|---|---:|
| derivable, STRONG (one superset commit in a 6h window) | **82** |
| derivable, needs a human to pick (ambiguous or partial overlap) | **61** |
| truly absent (nothing in the window touches its files) | **2** |

All 145 are status `reviewed`; none is open. By author: cc 45, hank 36, cody 35,
fourth 29. **Counts only — nothing was written.** And the floor is stated: the
window is 6h, the same number the gate uses for a WEAK basis, so a record whose
commit landed outside it classifies ABSENT here and may still be recoverable by
hand. **ABSENT is a floor on what is derivable, not a ceiling.**

### Item 11 — the collision is already fixed by cc; the residual gap is the majority case

Re-derived at HEAD from the **verbatim** claim strings: `block_reason()` still
returns `shared phrase: "digest plus"`, but cc's 2026-10-12 one-sided-FILES
narrowing demotes it to UNPROVABLE. **It would not block today.**

**The gap that remains:** that narrowing is conditional on ONE side declaring
FILES. When neither does, it never fires and a phrase hard-blocks. Measured over
the committed record: **375 of 1288 claims declare FILES — 29%. hank 21%.
hover2 0 of 13.** So the blocking case is the *majority* shape, and the audit
role is in it always.

**My first reproduction was invalid and the routed doc says so**: I retyped a
shortened task string and the shortening removed `plus` from beside `digest`, so
there was nothing left to collide. It now reads both strings from
`.claude/claims/*.json` and **asserts the colliding bigram is present in both
before reading any verdict.**

---

## 4. Claims held

**None. Released.** `python tools/sairn_claim.py release cody` ran after the
final push; `sairn_status.py set --state idle` followed.

The b5 claim was taken through `claim` normally (exit 0) — no direct write was
needed this batch, unlike b4. It did require declaring two other sessions' Drive
handoffs first, because the external-file-index check blocks the claim push.

---

## 5. Open, with the exact next step for each

| # | what | owner | exact next step |
|---|---|---|---|
| 1 | **Arms 11/12 race `PermissionError` on every run, silently** | **cody** | In `tests/run_tier_a_review_gate_probe.py`, catch the exception IN each thread and assert on what was caught: the arm should require that both saves either completed or failed loudly, and that the file parses. Today a dead thread is invisible. Reproduce first with the 400-iteration driver (§6). |
| 2 | **Run `sql/sairnlaw_citator_schema.sql`, then verify** | Michael, then anyone | 1. Michael runs the SQL in Supabase. 2. `python tools/verify_citator_feedback.py --check-only`. 3. `python tools/verify_citator_feedback.py --write`. Guardian Check 29 is NOT satisfied until step 3 passes. |
| 3 | **Live-verify the sairnlaw role gate against the deployed endpoint** | next session with network | POST `law_trusttx/read` with a paralegal token → expect 403 and the trust message; POST `law_matterdocs/write` with the same token → expect not-403. The suite proves this at the handler with a mocked PostgREST only. |
| 4 | **Discharge the sen_settings / sen_visits Tier A obligation** | **hank** (assigned) | `tier_a_review_gate.py --discharge cody <verdict>`. The record names the three things to check; the sharpest is the arm asserting the readiness fetch is still UNREDACTED. |
| 5 | **Discharge the 22-resource documents obligation from b4** | **cc** (assigned) | Same command. Confirm by diff that no api/ or sql/ file serving those resources is in the range. |
| 6 | **The claim matcher's neither-side-declares-FILES gap** | **cc** | Paste-ready patch in `docs/2026-10-13-cody-b5-routed-to-cc.md` §4, plus the BLOCK→CLEAR measurement that file's own convention demands. |
| 7 | **Thirteen Drive handoffs declared by sessions that did not write them** | **cc** (the check) + hover, hover2, fourth (the habit) | Make `external_file_index_check.py` read `belongs_in_git` and keep exit 1 only for the session that OWES the file. Or auditors write handoffs into their own clone, which CLAUDE.md already says. |
| 8 | **FMEA coverage at 13%** | unassigned | `python tools/fmea_draft.py <path> --save`, starting with the two the loop names: `tools/tier_a_review_gate.py` and its probe. A draft written AFTER a defect scores itself, so write them before the next one. |
| 9 | **The four §8 decisions in the permissions spec** | **Michael / the firm** | The sharpest: is `law_portalmessages` denied-by-default correct? If a paralegal obviously reads client messages, that is a DEFAULT change in `law-roles.js` so every firm gets it — not an override every firm repeats. |
| 10 | **143 of 145 no-sha records are derivable and none is backfilled** | unassigned | `tier_a_review_gate.py --backfill-shas` for the 82 strong; the 61 need a human to pick. |
| 11 | **`law_trust_reconcile` is owner-only while the trust policy is owner+attorney** | **Michael / the firm** | Decide whether the 20th resource joins the trust lock's membership. `api/sd-data.js:15719` records this as "the open question, not a rejected one". |

---

## 6. Evidence and reproduction

Scratchpad for this session:
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\b9e5be49-2b5f-401f-99a3-d7fe4cd27336\scratchpad\b5\`

| what | path |
|---|---|
| **the transcript** | `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\b9e5be49-2b5f-401f-99a3-d7fe4cd27336\` |
| every figure in the report, script-produced | `evidence.py` → `evidence.txt` |
| sabotage probe, 20 runs | `sab20b/tally.txt`, `sab20b/run_*.log` |
| gate probe, 12 runs | `gate12/t.txt`, `gate12/g_*.log` |
| the 400-iteration race driver | `race_repro.py` → `race.log` |
| the no-sha classifier | `classify_nosha.py` → `nosha.txt` |
| FMEA presence and coverage | `fmea_report.txt` |
| the matcher reproduction (verbatim strings) | `repro2.py`, `repro3.py` |
| the register merge by identity | `merge_register.py` |
| the Drive-declaration loop | `declare_drive.py` |
| the `_local_remote` failure-path driver | `drive_failpath.py` |

**These scripts are evidence for one batch, not checkers, and they live in the
scratchpad deliberately** — `tools/` enrols a file in four governance
populations, and a one-off driver does not belong there. The two that ARE
checkers (`dup_dom_ids_check.py`, `verify_citator_feedback.py`) are committed,
carry `# OWNER: cody`, and have `PURPOSES` entries.

**Re-run the verdicts locally, no network:**

    SAIRN_PROBE_LOCAL_REMOTE=1 python tests/push_gate/check4_probe.py
    SAIRN_PROBE_LOCAL_REMOTE=1 python tests/push_gate/check7_probe.py

---

## 7. What is NOT verified

- **No live request to any deployed endpoint.** The sairnlaw role gate and both
  sen_caregivers suites drive the real dispatcher against a mocked PostgREST.
  PR §3.2 applies to all of it.
- **No database.** `sql/sairnlaw_citator_schema.sql` was not run and
  `verify_citator_feedback.py` was exercised only on the path that touches
  nothing (credentials unset → exit 2).
- **No click-through.** `dup_dom_ids_check.py` reports 0 duplicates across 22
  files, which is id uniqueness in the markup — not a rendered-DOM check, and it
  says nothing about ids generated at runtime by a template string.
- **check 4 arm 1 and check 7 arms 1–2 are UNPROVEN, not passed.** A clean push
  is still refused by the external-file-index check over another session's Drive
  handoff, so "a clean change is not blocked by this check" was not
  demonstrated. Both probes say so in their verdict lines.
- **Item 8's fix is not written.** The cause is measured; the arm is unchanged.
