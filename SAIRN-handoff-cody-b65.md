# SAIRN handoff — cody b65 (2026-10-29)

## Batch number
- **This dispatch ended "done b64 <id>", but b64 was already closed.** Its handoff, report and digest landed at `8ee053b9b` and `1467373a5`, with a STOP POINT. This batch is therefore **b65**, so that it does not overwrite a committed record. If b64 was meant, the b65 files are the ones to rename.

## Committed / pushed state
- **Landed through the full gate** in two pushes. The final SHA is in `SAIRN-report-cody-b65.txt`, measured after this file lands.
- **Three gate refusals on the way, each cleared at its cause:**
  1. A push run under `timeout` (push_timeout_guard). Re-run in the background.
  2. Tier A code with no obligation. Two obligations opened, both assigned to **cc**.
  3. A fix that did not feed the register. Four register records added.
- **The scope gate refused `docs/recurring-bug-classes.md`** (fourth's by the split).
  - It is the file Michael's item 5 names: "cause-tag every fix per recurring-bug-classes convention".
  - I declared it in `docs/sairn-path-manifest.json`. The key is `_assigned_overrides_why_cody_b65_ADDS_ONE`: one file, added to the b57 list, not a replacement.
  - A local history rewrite to move the rows was denied by the auto-mode classifier, and was not attempted another way.
- **One rebase conflict**, in `docs/defect-density-register.json`. `tools/sairn_rebase_resolve.py` merged it by identity: 784 + 2 + 2 = 788. `--check` OK.
- **Claims:** all cody claims are released.

## 1. Review obligations (item 3): FOUR discharged, the most overdue first
| opened | author | verdict |
|---|---|---|
| 10-05 15:02 (580h) | fourth | `deploy_verify_notify.classify_command`: **SOUND-WITH-GAPS (medium)**. The per-LINE `_MENTION_ONLY` test drops a chained real push silently: `echo "x"; git push origin main` and `grep -n x f && git push` both score not-a-push. `git -C <dir> push` scores unsure. No fifth pushing tool outside the auditor scope. **Routed to fourth in the verdict.** |
| 10-05 21:25 (573h) | fourth | `db/schema_snapshot.json`: **SOUND**, against the LIVE database |
| 10-20 14:10 (221h) | cc | the same snapshot, same verdict. Both records name captures since superseded, so I reviewed what they protect, at the current file. |
| 10-06 06:18 (565h) | cc | sb_ap buckets + `exit_status_attributable.status_was_measured`: **SOUND-WITH-GAPS (low)**. Five suppressions fail in the silent direction, e.g. `echo "$(tail -1 o) rc=$?"` (bash: `$?` is the substitution's). A non-ISO date buckets FUTURE, not PRIOR. **Routed to cc in the verdict.** |

- **The snapshot method** was read-only SELECTs on Supabase `sairn-platform` (`ejrlrrkvhtllxbbypdjb`), the project cc b34 matched:
  - **Tables and columns:** 500 tables, 4177 columns. md5 per prefix group: **70/70 match**.
  - **CHECK constraints:** 561 on 445 tables. 43/44 groups match. **The one drift:** `sairnlegacy_audit_log_event_type_check` now allows `settings_changed` live, from `sql/sairnlegacy_audit_log_settings_event.sql`, applied after the 10-21 capture. That is the safe direction. **Re-capture.**
  - **Not compared:** UNIQUE/PK/FK. The file carries CHECK only.
  - **`sql/restore_sairnvet_demo_pin_2026-10-05.sql` IS applied now:** the row was updated 2026-10-06 07:01Z. I read no hash or salt.
- **Still open and assigned to cody**, all past 48h:
  - hank 10-06 `sdn_projects` (storedBlob `[]` column list);
  - hank 10-06 `sen_settings` (13 register rows, 42 citations).

## 2. H2 routing (item 4)
- **H2's claim file is deny-scoped to builders.** `builder_auditor_deny_hook` refuses even a read of `.claude/claims/hover2.json`, so the route is the open-work index, which hover sessions do read.
- **NEW row `B65-H2-CALIBRATION-CODY-2026-10-29`, owner hover2:** the 10 confidences with no resolution row: 1078, 1079, 1080, 1082, 1083, 1084, 1085, 1091, 1109 and **1115**. It has a deciding test, and it cross-links `B63-H2-SEQ813` (already routed in b63).
  - **Not re-measured.** Whether H2 has resolved any since 10-20 cannot be seen from a builder clone.
- **A status-registry note FOR HOVER2** names both rows. Shards were regenerated: `open_work_shard --check` CLEAN, 824 rows.

## 3. Backlog fixes (item 2), each fixture-first and RED before the fix
| fix | commit | arm |
|---|---|---|
| cc b70 gap (a), mech: no arm checked the request `Prefer` shape | `e0e732364` | re-save sections 4-5, 35/0 (was 22/0); an ignore-duplicates ablation turns all 6 red |
| cc b70 gap (b), mech: the ablation copy was not gitignored | `e0e732364` | `git check-ignore` 1 -> 0 |
| cc b70 gap (b), sairnfreedom: a legacy device with no fingerprint ADOPTED any new key, so licence B opened A's records and A's confirmed set | `f4d8c29fa` | new `tests/sairnfreedom_licence_guard_legacy.js`, L1/L2 red, 6/6; `licence_rekey_isolation` 70/70 |
| cc b73 LOW, sairndental: the hold was taken outside the try, so a throwing render locked every later credential add | `f4d8c29fa` | CD4 red, 20/0 |
| b64 item 3, sairngrounds GPS waits | `f6a127280` | PO/MS 1-4, 46/0 |
| b64 item 3, stonedesk POS 2.5 s reset window | `03ad3006b` | S4 had pinned the duplicate as CONTROL; now S4/S4b, 17/0 |

- **Correction to b64's description of `gcdMarkShotEnd`.** On the old code a second press did NOT record a duplicate shot. It threw a TypeError on the already-cleared `gcdShotStart`. `gcdPlaceOrder`'s second order was empty and $0.
- **Regressions:** every JS test that reads each edited app was run.
  - **Red both before and after (pre-existing):** `sairn_storage_wrapper_honesty`, `dnt_complaint_qr`, plus 4 stonedesk files.
  - **Seen while the edit was uncommitted, gone after:** `phi_cache_scoped_to_user`'s SKIP.
  - **One real regression, caught and fixed before commit:** `licence_rekey_isolation` lifts the guard, so the stored-key read is direct rather than through `ld()`/`K_LIC`.

## 4. Live verification (after the second push)
- Fetched with `tools/sairn_http.py`, no-cache:
  - **sairngrounds, sairnfreedom and sairndental:** each served page carries its fix string.
  - **stonedesk:** the served page is byte-identical to local HEAD after CR stripping (sha256 `d1eef039ef2f`), and carries the fix.

## 5. Methodology (item 5)
- **Cause tags:** a "batch 65 (cody)" section in `docs/recurring-bug-classes.md`, with rows 1-5 in PHASE -> SUB-PHASE -> CAUSE form.
- **Register records:** 4 records in `docs/defect-density-register.json`, each with contributing factors and `recurrence_open`.

## Open, and the exact next step
| # | open item | owner | exact next step |
|---|---|---|---|
| 1 | Tier A reviews of the b65 fixes (two obligations: mech/freedom/dental; grounds/stonedesk) | cc | `tools/tier_a_review_gate.py --discharge cody <opened_at> "<verdict>"` |
| 2 | Two Tier A reviews still assigned to cody: hank 10-06 sdn_projects, hank 10-06 sen_settings | cody | discharge the older first; both are past 48h, so anyone may `--takeover` |
| 3 | The same first-run-adopt shape in the OTHER apps' licence guards (the ones `licence_rekey_isolation` lifts) | cody | for each, check whether the app stores its key beside the data; if so, apply the b65 sairnfreedom fix with a legacy arm |
| 4 | sairnfreedom cc b70 gaps (a), entries never expire, and (c): D4c is a regex, `sfConfirmOnServer` is never executed, and 3 ablations survive | cody | (c): drive `sfConfirmOnServer` in a vm, with the three ablations as arms. (a) is a design decision (TTL or re-verify): Michael |
| 5 | `gcdMarkShotStart` is not held, so a start during an end's pending fix can replace `gcdShotStart` | cody | decide in the b65 grounds review whether all three caddie GPS handlers share one hold |
| 6 | Handlers that never reset their inputs (b64 item 4) | cody, with each app's owner | unchanged from b64 |
| 7 | Make the re-entry sweep a standing checker, now with a device-await and timer-reset shape too | cody | `tools/` checker with fixtures for all three shapes |
| 8 | `deploy_verify_notify` chained-push silent skip | fourth | per-segment decision, two red-first arms (in the verdict) |
| 9 | `exit_status_attributable` silent suppressions; sb_ap non-ISO date bucket | cc | five red-first arms (in the verdict) |
| 10 | Re-capture `db/schema_snapshot.json` (one CHECK drift; UNIQUE/FK not captured) | Michael | the usual capture |
| 11 | H2: calibration row + seq813 row | hover2 | as each index row says |
| 12 | mechCredAdd/mechAssetAdd have no `.catch` (cc b73, out of scope) | cody | silent-failure shape; a toast on rejection, with an arm |
| 13 | All other b64 open items (7-20) | as b64 says | unchanged; `SAIRN-handoff-cody-b64.md` |
