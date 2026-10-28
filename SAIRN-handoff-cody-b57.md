# SAIRN handoff — cody b57 (2026-10-28)

All seven items are done. Nothing is half-finished in the tree.

## Committed / pushed state
- **The b57 work LANDED as `e31869242`..`bc1444274`.** It went through the full gate, after two gate blocks that I fixed at the cause (see §7). `merge-base --is-ancestor bc1444274 origin/main` is true, and every b57 commit is authored "Michael Dibert".

| commit | what |
|---|---|
| `e31869242` | identity |
| `40af6a301` | write_batch |
| `8259a6dd2` | sairnmechanical |
| `d48db33ef` | C3 doc, test requirement, derived docs |
| `21312d66e` | register records and manifest b57 |
| `f1d5c8297` | Tier A obligation |
| `bc1444274` | re-seat |

- **Live-verified on https://sairn.vercel.app/sairnmechanical.html.** Status 200. `mechBackup`, "Kept on this device only" and "NOT read back from the server" are all present. They appeared about 45 s after the push; the first fetch still served the old build.
- **This deliverables commit** (handoff, report, digest, scrutiny rows) is written before its own push. The report confirms whether it landed.
- **Claims:** none held. `sairn_claim.py list` shows no cody claim.
- **Tier A obligation OPEN:** `docs/tier-a-reviews.json`, cody b57, covering mech_quotes and mech_checks in sairnmechanical.html. **Assigned to cc.**
- **Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## 1–2. Worktree removed
- `git worktree remove --force` on `Temp\cody-b55-alltests` returned exit 0.
- `git worktree list` no longer shows it, and the directory is gone.
- The junction was removed first, in the step before this batch.

## 3. The "fx" identity leak: fixed in this clone and guarded
- **Cause:** cc b60, `58801d4c7`, already in HEAD. A pre-push hook running from a linked worktree inherits an absolute `GIT_DIR`, and that beats `git -C <tmp> init`. So a gate fixture re-initialised the shared repo. `.githooks/pre-push` now unsets `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and `GIT_COMMON_DIR` before any gate runs. `copy_exactly_gate` restores `core.bare` in a finally.
- **This clone:** the local `user.name=fx` / `user.email=fx@local` are unset, so the global "Michael Dibert" applies.
  - `core.bare` is false. It was already false.
  - The committer identity is verified on every b57 commit.
  - The 90 `fx <fx@local>` commits from b51–b56 stay in history and are NOT rewritten, the same as hank's fix.
- **Hardening:**
  - `tools/committer_identity_check.py` walked `tests/` only. The `fx` set by `tools/copy_exactly_gate.py` was therefore never on its throwaway list. It now walks `tools/` too: 29 → 45 identities.
  - My own `tools/rework_tracker.py` git fixture (b55) ran `git init` and 4 commits with the inherited environment. Under a worktree hook, that would re-init the real repo and put 4 `fx` commits on its HEAD. It now drops the `GIT_*` variables for that block. Driven with a hostile absolute `GIT_DIR`: HEAD, `core.bare` and the local identity were all unchanged.
  - **The push script refuses to push** if `committer_identity_check` fails or `core.bare` is not false. No gate reads the identity.
- **Not traced:** the spelling `fx@local` appears nowhere in this repo's history. `copy_exactly` uses `fx@example.invalid`, and that is the value in **fourth's** clone config today. That clone is fourth's, so I did not touch it.

## 4. write_readback_shape_probe: I read the growth before clearing anything. One red was a masked regression.
- **stonedesk 33 → 32 was NOT growth.** `sd_customers` moved to `sdData('write_batch', ...)`. `WRITE_RE` matched only `'write'`, so the resource left the write set and its read-back stopped being checked, silently.
  - **Fixed in the tool** (`write(?:_batch)?`). It was not re-baselined. arm2 is 33 again.
  - Fixture 10/10. With the old regex patched back in, the fixture fails.
- **sairncare 9 → 10** (`alf_claim_routes`, 3c28b9eac, 2026-09-18) and **sairnmechanical 2 → 3** (`mech_insurance_policies`, 72ba22610, 2026-09-25): real features, each written AND read by its app's wrapper. I re-baselined both, with that reason in the probe.
- The shape probe: ALL ARMS PASS.

## 5. The mechPushOne write and read sides
- **`api/sd-mech-data.js` does not exist.** The client is `sairnmechanical.html`, and the server is the generic `api/sd-data.js` path, with resources registered in `api/_resources/sairnmechanical.js`.
- **Alias-only writer, no record. FOUND and FIXED.**
  - Every save site (quotes, checks, docs, takeoffs) used `if(typeof window.mechPushRecord==='function')` with no else, so a missing backup module meant a silent skip. They now go through `mechBackup()`, which warns and returns null.
  - `saveDoc` used to toast "Saved and synced" before the async push answered, and also on failure. It now waits, and says "Kept on this device only -- the server backup did not complete" when the push did not finish.
  - `mechPushOne` returns a truthy value on success even when the response has no `data`.
- **Unparsed output read as pass. FOUND and FIXED.**
  - `mechHydrateAll()` returned silently on refused, unparseable or non-list reads and on a corrupt local copy, and swallowed errors. It merged 0, which looks exactly like an up-to-date device.
  - Each case now warns, naming the collection.
  - `provisioned:false` and an empty list stay silent, because both are real answers.
- **Tests:**
  - `tests/mech_backup_not_silent.js` (new): 13 arms, with an ablation in which the pre-b57 hydrate stays silent on a 500.
  - `mech_check_register_identity.js`: 20/0. It now lifts `mechBackup`.
  - `mech_docs_redaction_wiring_probe.py`: arm 7 had been **red since 2026-10-14**. Its extractor did not skip comments, so the apostrophe in "THE MODEL'S" ran `saveDoc`'s body on into `saveTakeoff`. Fixed; 0 failures.
  - `sairnmechanical_fault_probe`: 0 failures.
  - `node --check`: 7 of 7 blocks clean.
- **COULD NOT TELL:** I did not re-audit the generic `sd-data` server path for this class this batch, beyond its existing suites (mech redaction-scope 20/20).

## 6. The b56 UNVERIFIED flag: RESOLVED. Decided YES and implemented; C3 in `docs/recurring-bug-classes-2.md`
- **Every pure-base retry now runs a whole-tree re-check before `--no-verify`.** It runs `defect_register --check`, `master_plan --check` and `traceability_matrix --check` in parallel, which took **18 s, measured**. The gate takes 75 s to 4 min, and the remote moves every 1–3 min.
- **If any check is red,** the derived docs are regenerated and the push takes the full gate. A red never reaches `--no-verify`.
- **Incoming changes to `docs/CRITICALITY-TIERS.md`, the gate code or `.githooks/` always re-gate.** The overlap rule cannot see these, because they are what the gate itself reads.
- **This was measured, not theoretical:** one new test file turned both derived-doc checks red.
- **Two more push-script fixes, found by this batch's pushes:**
  - Re-seat by subject after every rebase. The register-feed gate refused the rebased fix commits otherwise. Re-seat-only commits are excluded from the patch-id set.
  - `--autostash`, from b56.

## 7. Push
- **Work:** the full gate blocked twice, and I fixed both at the cause.
  1. **Tier A, a REAL obligation.** sairnmechanical's mech_quotes and mech_checks save paths had changed. I opened it with `tier_a_review_gate.py --open` and it was assigned to cc.
  2. **Register feed.** The rebase rewrote the SHAs, and I had discarded the gate's own re-seat diff (my mistake). I re-seated by subject, and the script now does that every time.
- The next push landed on try 1.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | Tier A review of the sairnmechanical change | cc: discharge it in `docs/tier-a-reviews.json` (cody b57 row) |
| O2 | fourth's clone config still has `fx@example.invalid` | fourth: `git config --local --unset user.name` and the same for `user.email`, then `python tools/committer_identity_check.py` |
| O3 | Generic sd-data server path not re-audited for the not-run class | cody, next batch |
| O4 | WRITE_RE still knows only `write` and `write_batch` (not soft_delete or upsert variants) | cody: sweep the action names `sd-data` accepts |
| O5 | The push mechanism lives in a scratchpad script | cc: move the C1/C3 rules (patch-id skip, re-seat, whole-tree re-check, re-gate list) into `tools/push_retry.py` |
| O6 | hover_separation probe fixture; b55 MEDIUM leftovers; b54 carry | unchanged |
