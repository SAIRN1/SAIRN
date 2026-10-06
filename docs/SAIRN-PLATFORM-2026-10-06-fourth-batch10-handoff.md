# Handoff — fourth, batch 10, 2026-10-06

**Nothing half-finished is left on disk.** Everything below is either committed
and pushed, or named here as open with its exact next step.

| | |
|---|---|
| clone | `Documents\SAIRN-fourth`, branch `main` |
| state at handoff | **0 ahead / 0 behind `origin/main`** |
| claim | **released** (`python tools/sairn_claim.py release fourth`) |
| status row | `idle` |
| working tree | clean except `sql/restore_demo_pins_2026-09-29.sql`, **untracked and NOT mine** — see §5 |
| transcript | this session's Claude Code transcript, project `C--Users-marsh-Documents-SAIRN-fourth`, session `c430231c-cc9c-43df-9850-e4efe2dd54a3`. Working files for every measurement below are in that session's scratchpad: `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\c430231c-cc9c-43df-9850-e4efe2dd54a3\scratchpad\` |

---

## 1. Landed, with the commit that carries it

| item | commit | what |
|---|---|---|
| 1 — SAIRNvet demo credential | (no code change) | `python tools/capture_exit.py --status demo.status -- python tools/demo_credentials_check.py` → **`EXIT 0`**. SAIRNvet: `OK sairnvet role=owner`. 16 of 16 apps OK |
| 3, 9, 11 — the two clone-corrupting probes, the andon log, recurring-bug-classes | `e3ebdf42` → pushed as `8b2cde17` | `run_delegation_probe` FIXED and green; `check8_probe` CONTAINED with the writer pinned to one step |
| 6 — span sweep | `d9f3754a` → `20bd5332` | all 26 sites re-measured at HEAD; one real silent defect fixed with a planted control |
| 7 — red register | `bb1aaddb` → `b20a26ac` | 15 of 66 empty-`why` entries diagnosed, 1 deleted as RECOVERED |
| 5 — gap docs | `68df00b5` → `41f3ddb8` | all 35 documents checked; 23 clean, 12 flagged, 5 of the 12 my own sweep being wrong |
| 8, 10, 12 — fold-in, guards, convention 16 | `002b2520` → `66f0532b` | |

---

## 2. OPEN, with the exact next step

### 2.1 Item 2 — the `_constraints` merge. **ANDON PULL 1. Needs Michael.**

**Blocked on an input that does not exist.** `constraints.json` is absent from
this clone (whole tree, `%USERPROFILE%`, Downloads, Desktop) and from all five
sibling clones. It can only come from the live database.

Measured, so the premise is not taken on trust:

```
python tools/capture_exit.py --status pre2.status -- \
  python tools/sairn_sql_preflight.py --live db/schema_snapshot.json sql/sairnlegacy_data_schema.sql
EXIT 0 2026-10-06T16:07:59Z

CHECK CONSTRAINTS
    COULD NOT CHECK      snapshot carries no _constraints key
```

`db/schema_snapshot.json` at HEAD: 439 tables, `_generated_at`
`2026-10-05 15:10:30+00`, underscore keys `_generated_at`,
`_anon_grant_baseline_2026_08_26`, `_anon_nontable_baseline_2026_08_26` — and
**no `_constraints`**.

**NEXT STEP, four lines, all of them already written down in
`sql/schema_snapshot_constraints_query.sql`:**

1. Run that file in the Supabase SQL editor.
2. Save the single JSON cell as `constraints.json` (anywhere).
3. Merge with the one-liner in that file's HOW TO USE block. **Merge an empty
   `{"_constraints": {}}` too** — empty means *asked, none exist*; missing
   means *never asked*, and the preflight tells them apart.
4. Re-run the preflight; CHECK CONSTRAINTS must report a comparison.

`constraints.json` is **not** to be committed.

### 2.2 Item 4 — the pinned re-run. **STILL RUNNING at handoff.**

`python tools/run_all_tests.py --pinned --pinned-ignore-dirty` was launched at
`2026-10-06T17:27:22Z` against `HEAD` and had written **446 of ~739** result
lines when this was written. Its status file is
`scratchpad/pinned.status` and reads `RUNNING 66464`; its log is
`scratchpad/pinned_run.txt`.

**The verdict it exists to re-judge, and what the partial log already says:**

* Batch 9's UNPINNED log reported `tests/sairnbiz_vendor_ytd_derivation.js` as
  `ok` while a hand drive exited 1 — cc's rename of
  `sbVendorPaidUndatedPriorYear` arrived mid-run. **The pinned log reports it
  `ok` at line 85**, and it is `ok` at HEAD too (cc repointed the test), so
  that entry was correctly deleted from the register in batch 9.
* **The verdict still to confirm is `tests/seam_check/run_probe.py`**, which
  the unpinned log reported as a failure with an `OSError` and which exits 0
  on a restored tree. Its failure was caused by `run_delegation_probe` leaving
  sabotage in `api/sd-data.js` — the defect fixed in this batch. The pinned run
  had not reached it yet. **NEXT STEP:** when the run finishes, read
  `python tools/capture_exit.py --read scratchpad/pinned.status` for the real
  exit code and `grep -n "seam_check/run_probe" scratchpad/pinned_run.txt`.
  A pinned run in a clean worktree should show it `ok`, which would close the
  loop on the sabotage-residue confound.

### 2.3 My nine Tier A review obligations — **NOT discharged. ANDON PULL 3.**

`docs/tier-a-reviews.json` is in **cody's live claim** and the claim's first
line is *"Tier A discharges most-overdue-first with adversarial controls"* —
the identical work. Two sessions writing one ledger in the same hour is the
collision the claim system exists for, so nothing was written to that file.

Listed so they are not lost. Most overdue first:

| opened | author | resources | overdue |
|---|---|---|---|
| 2026-09-27T03:42:29Z | hank | `alf_staff`, `sen_visits` | **228h** |
| 2026-09-28T03:34:57Z | cody | `dnt_ar`, `dnt_revenue` | 204h |
| 2026-09-28T03:40:54Z | hank | `alf_facility` | 204h |
| 2026-09-29T17:47:11Z | cc | `alf_activities`, `alf_billing`, `alf_clients`, `alf_facility`, `alf_mar` | 166h |
| 2026-09-30T10:58:02Z | cody | `rf_claims`, `rf_invoices`, `sen_visits` | 149h |
| 2026-09-30T12:08:26Z | cody | `sv_audit_log` | 148h |
| 2026-09-30T13:59:56Z | hover2 | `leg_insurance`, `mech_checks` | 146h |
| 2026-10-05T09:03:14Z | hank | `grd_irr_zones`, `grd_rounds` | 31h |
| 2026-10-05T13:23:46Z | cody | `invoices`, `scp_quotes`, `sd_sms_log` | 27h |

**NEXT STEP:** when cody's claim releases, `python tools/tier_a_review_gate.py
--list`, then discharge the 228h one first. Several carry
`** COULD-NOT-TELL **` because their recorded sha does not resolve in this
clone — those need `--reseat-shas` before they can be judged.

### 2.4 Still owed on items I did advance

| what | where it stands |
|---|---|
| **50 of 79 register entries still carry an empty `why`** | 66 → 50 this batch. `tools/red_suite_register_check.py` keeps a stale entry loud, so this is a backlog with a count, not a silent allow-list |
| **The `.git/config` root cause** | OPEN. Class named by cody: `SHARED_CONFIG_WRITE_FROM_WORKTREE`. Routed to **cc** (owner of `tools/sairn_push_gate_hook.py`). My containment holds on every path except a kill, and a kill is now loud |
| **28 leaked git worktrees** in `%TEMP%` | Measured by cody's `clone_health_check.py`. None swept — removing another session's temp worktree while it may be in use is not a cleanup |
| **4 gap-doc findings routed** | sairnfreedom (three ZEROES became non-zero — the consequential one), caller-level senior/stonedesk, SAIRNlaw `split_fees` 3,253-line drift, sairnvet pricing/CDS citing a companion doc not on `main`. All in `docs/2026-10-06-gap-doc-verification-all-35.md` |
| **`HOVER-H1-905-910` index row is stale** | The contradiction it names was fixed in batch 9. hank holds the index |
| **cc's three methodology conventions** | STILL NOT RECEIVED — the document naming them is not on `main`. Recorded as missing in `docs/METHODOLOGY.md` rather than invented |
| **283 `tools/*.py` with no `# OWNER:` line** | 15 of 298 have one. The checker (`tools/tool_owner_header_check.py`) already exists; the work is the headers |

---

## 3. Claims held at handoff

**None.** Released. During the batch I held one claim covering
`tools/demo_credentials_check.py`, `db/schema_snapshot.json`, the two probes,
`docs/2026-09-13-cross-domain-disciplines.md`, `docs/known-red-suites.json`,
`docs/recurring-bug-classes.md` and the andon log, plus a later check for the
three span-repoint files.

**Blocks I hit and did not work around:** `docs/tier-a-reviews.json` (cody),
`sairnfreedom.html` (hank), `docs/SAIRN-OPEN-WORK-INDEX.md` (hank),
`docs/METHODOLOGY.md` and `docs/CRITICALITY-TIERS.md` (hank),
`tests/sairnbiz_vendor_ytd_derivation.js` (cc's subject). Every one is named
in the document that needed it.

---

## 4. The three andon pulls

`docs/2026-10-06-fourth-andon-log.md`. Pull 2 was **closed the same day by
cody's independent work**, which is what a pull is for. Pulls 1 and 3 are open
and both are waiting on somebody else — Michael for the SQL, cody's claim for
the review ledger.

---

## 5. One thing in this clone that is not mine

`sql/restore_demo_pins_2026-09-29.sql` — untracked, 10KB, mtime 2026-10-05, a
credential-restore runbook from an earlier session. **Not committed, not
moved, not deleted.** It makes the push gate refuse any command that commits
and pushes in one step, which is why every push in this batch was two
commands. It writes credential rows, so per PR §3.4 it needs the
recoverability guard checked by whoever owns it.

---

## 6. What a reader should NOT conclude

* **23 gap documents reported "clean" have had their arithmetic checked, not
  their argument.** No verdict, competitor claim or severity judgement was
  re-derived in that sweep.
* **`check8_probe` is contained, not fixed.** Its new arm FAILS on purpose and
  will keep failing until the writer is found.
* **The pinned run was not finished at handoff**, so this batch does not carry
  a complete pinned census — only the one verdict already visible at line 85.
