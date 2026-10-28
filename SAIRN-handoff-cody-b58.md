# SAIRN handoff — cody b58 (2026-10-28)

Items 1, 2, 3 and 5 are DONE. Item 4 stopped at a floor, as Michael directed after the memory kill. No half-finished edits are left in the tree.

## Committed / pushed state
- **The main b58 work LANDED, tip `70c7e1b86`.**
  - It took the full gate. `merge-base --is-ancestor` is true, and every commit is authored "Michael Dibert".
  - Production deployment `dpl_2P91m6M7…` built `70c7e1b86` and is READY.
- **The M17 fix LANDED, tip `3d46219db`.**
  - Try 1 passed the full gate, but the remote had moved (ref lock).
  - Try 2 was a **pure-base skip decided by `tools/pure_base_skip.py`**, its first real use: the whole-tree re-check was green. It is logged in `docs/BYPASS-LOG.jsonl`.
- **Live check:** `tools/sairn_http.py` POSTed to https://sairn.vercel.app/api/sd-data with `mech_site_assets` and with `mech_quotes`. Both answered a structured 401 INVALID_LICENSE, so the new `sd-data.js` loads in production.
  - **UNVERIFIED live:** the "store returned `[]`" arm. A real save always echoes a row, so that arm cannot be driven against production without a fault. It is covered by `tests/sd_data_mech_write_unconfirmed.js` and its ablation.
- **Gate blocks this batch, each fixed at the cause:**
  1. register feed: records added;
  2. a probe anchor, `run_unconfirmed_write_sweep_sabotage_probe`: I had reworded `refuseUnconfirmedWrite()`, so I restored it byte for byte and added a `refuseUnstoredWrite()` sibling;
  3. Tier A: an obligation was opened and assigned to **cc**;
  4. derived docs: regenerated;
  5. path scope: 19 paths were foreign under the manifest. **Michael approved** adding them to `assigned_overrides.cody`, following the b57 precedent. The b58 list replaces b57's, and `write_without_readback_check.py` was added for M17;
  6. a `no-defect-record` line, for the anchor-restore commit.
- **Claims:** sairnmechanical released once the deliverables push lands; the report confirms it.

## 1. sairnmechanical server write path: REAL defect, FIXED
- There is no `api/sd-mech-data.js`. The server is `api/sd-data.js`, with resources registered in `api/_resources/sairnmechanical.js`. The client calls actions `write`, `read`, `eligibility` and `readiness`.
- **The premature ack, server half.** All four mech write branches POST with `return=representation` and answered ok even when no row came back:
  - **MECH_RECORDS** (quotes, checks, docs, takeoffs) returned the request payload as if it had been stored;
  - **mech_site_assets, mech_insurance_policies and mech_credentials** returned `data:null`.
  - The app clears the form on ok, and mechPushOne reports a backup.
  - All four now answer **502 WRITE_UNCONFIRMED**, through `wroteRow()` + `refuseUnstoredWrite()`.
- **Silent skip:** none on the server. A payload with no id is a 400.
- **Silent hydrate:** none. The reads distinguish 404/400 with `provisioned:false` (and `unreadableNotEmpty`), and a non-ok answer goes to `upstream()`.
- **Test:** `tests/sd_data_mech_write_unconfirmed.js` has 22 arms:
  - echo gives 200, for all 7 resources;
  - `[]` gives 502, for all 7;
  - an ablation restores the old lines in a copy, and all 7 then answer ok.
- **Regression check:** of 144 sd-data POST suites, 8 are red. All 8 are equally red at HEAD without this change.

## 2. WRITE_RE action sweep (sairnmechanical.html + sd-data.js)
- WRITE_RE (`tools/write_without_readback_check.py`) matches `write` and `write_batch`. sairnmechanical sends only `write`, from 4 sites:
  - mechPushOne, fixed in b57;
  - credentials (:2761), site assets (:3041) and insurance (:3199). Each shows the server's message on failure and clears only on ok. They are correct now that the server's ok is real.
- The read sites are all loud. Those are credentials :2362, assets :2921 and insurance :3141, the eligibility (:2685) and readiness (:3221) calls, and mechHydrateAll (b57).
- **Outside mech, routed:** the same ok-with-null shape remains at `sd-data.js` `supplier_lead_times` (:3194), `sd_approvals` (:3911) and `alf_family_contacts` (:15129).
- WRITE_RE still does not know `soft_delete` (7 server sites), `upsert`, `delete` or `add_payment`. None are used by sairnmechanical.

## 3. b55 MEDIUM leftovers: ALL CLOSED (M2–M23, plus M17)
Every row was still real at HEAD. Each has an arm that is red on the pre-fix copy, and I re-ran every probe myself afterwards.
- **M2** verify_citator_feedback: PARTIAL now exits 2. New probe.
- **M3** guard_ablation: new SILENT-PARTIAL verdict; exits 2.
- **M4/M5/M6** assertion_label_shape:
  - the count was structurally 0 and is now 35;
  - the denominator is fixed;
  - NOT JUDGED is now counted.
- **M7/M8** parse_zero_third_state: the `value=2` false match is fixed, and a COULD NOT TELL line is added.
- **M10** unproven_arm: NOT ASSESSED now exits 2. The live run's exit moves 1 → 2. Caller: report_only, via `by_exit`.
- **M11/M12** metamorphic: a crashing checker, and an unexercised relation, each now count as could-not-run.
- **M13** entry_point_scope: checked 99 → 94 of 362.
- **M14** control_char: an absent file is no longer counted as scanned, and a `--rev` path outside the repo exits 2.
- **M15/M16** clone_health and git_config_isolation selftests now drive the code they name.
- **M18** route_suite_failures: COULD-NOT-RUN rows are routed (7 live), and a bad claim file exits 2.
- **M19** overrun_inversion: an empty or partial scan exits 2.
- **M20** dead_function_sweep: >25% blanked is now UNTRUSTED and exits 2.
- **M21** external_file_index_audit: an absent claim is a finding.
- **M22** session_surface: COULD-NOT-TELL when there are no transcripts.
- **M23** dead_rule_sweep: the overlay's exit code is checked.
- **M17** write_without_readback: an empty target list exits 2, and the count now shows targets and writers separately. With the old main() the arm is red.
- M1 (hover_separation_audit) and M9 were not on the routed list. M9 was already fixed in b55. M1 is still open; see O5.

## 4. run_all_tests continuation: STOPPED, floor recorded (Michael: do not restart blind)
- **Population at HEAD `b4cea6792`:** 469 js + 434 py = **903**. 536 passed in b55, so 367 remain.
- **This run:** 42 files, one at a time, in a throwaway clone with `node_modules` linked in. **7 ok, 33 FAIL, 2 SKIPPED**, after which Claude Code killed it on low memory.
- **Floor: 543 / 903 passing.** The log is in this session's scratchpad as `b58-alltests.log`. The clone is removed; its node_modules link was unlinked first, and the real node_modules is intact.
- **The 33-failure rate is as measured and NOT triaged.** I re-ran 3 of them in the live clone (`api/sd-data-family-contacts.test.js`, `sd_tax_money_coercion.js`, `dnt_complaint_qr.js`) and all 3 are red there too. The other 30 are unconfirmed, and the clone environment may contribute.

## 5. C3 enforced in a tool, and test-covered
- **`tools/pure_base_skip.py`** returns 0 to skip, 1 to gate, and 2 if it could not decide (which also gates).
- **The re-gate set is DERIVED from the hook** and `.githooks/pre-push`, plus the tier register and `.githooks/`: 41 tools today. If fewer than 20 are found, it exits 2.
- **`tests/run_pure_base_skip_probe.py`**, 22 arms:
  - a change to any of the tier register, the hooks, the gate code or a gate-run tool forces GATE;
  - a re-check rc of 1, 2 or None forces GATE;
  - an underivable read set gives could-not-decide;
  - **ablations** remove the re-gate rule and the floor, and require the matching arms to flip.
- C3 in `docs/recurring-bug-classes-2.md` is updated.
- This batch's push script calls the tool, and the gate passed through it.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | Tier A review of the b58 mech write change (5 resources) + b57 row | cc: discharge both in `docs/tier-a-reviews.json` |
| O2 | 33 untriaged reds in the 543/903 floor | cody: diff each against its own last-green commit before calling any of them real; no full re-run |
| O3 | ok-with-null write acks outside mech (supplier_lead_times, sd_approvals, alf_family_contacts) | owners of those apps (sd_approvals → stonedesk, alf → sairncare) |
| O4 | dead_function_sweep 25% threshold now exits 2 on sairnbiz/sairncash/sairnsenior | Michael/cody: recalibrate the threshold (longest blanked run is under 5k chars, so it is real comment density) |
| O5 | b55 M1: hover_separation_audit narrows silently with one of two hover logs missing | cody: add a could-not-run entry per hover claim with no log. The probe G11/G14/G21 are red at HEAD (b55) |
| O6 | assertion_label_shape: the JS extractor cannot judge 35 bare-truthiness asserts | cody: extend the extractor; E5b pins 35 as a ceiling |
| O7 | push_retry.py should call pure_base_skip.py | cc (C1/C3 routing) |
| O8 | WRITE_RE does not know soft_delete/upsert/delete | cody: widen with a fixture per verb |
