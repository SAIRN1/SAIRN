# SAIRN handoff — cody b66 (2026-10-29)

**Methodology (item 5):** every routed cross-agent finding below names its session, its commit SHA and, for an auditor finding, its seq, inline. No bare labels.

## Committed / pushed state
- **Landed through the full gate.** The final SHA is in `SAIRN-report-cody-b66.txt`, measured after this file lands.
- **The manifest** (`_assigned_overrides_why_cody_b66_ADDS_SEVEN`) declares for cody:
  - `tools/sairn_done_line.py`: cc's file, and the hook item 1 names.
  - the six guard apps the scope gate refused: sairnsenior, sairnbuild, sairndesign, sairnroofing, sairnbiz, sairnscape. These are fourth's by the `*.html` split, and item 2 assigns the sweep.
- **Claim clash, cleared on Michael's go-ahead.** `862ed3591` touches `sairnlaw.html` while hank held a live claim (`hank-1793304448`, M5 trust reconcile). I asked; Michael said push, so it went with `SAIRN_CLAIM_GOAHEAD`. My edit is the 10 lines inside `lawLicenceGuard()` only. A status note FOR HANK says so.
- **Claims:** none held.

## 1. Done-line Stop hook (item 1): it ALREADY EXISTED; its one gap is closed
- **cc b66 built it:** `tools/sairn_done_line.py`, `a367bd0c2`, 2026-10-28.
- **It was already armed in this clone.** It is in `.claude/settings.local.json` as `.git/sairn-hooks/sairn_done_line.py --stop-hook`, and it refused my own b65 close until the message was exact. I did not build a second copy.
- **The gap:** with no record this turn, any final message passed, including a hand-typed `done b<n> <id>` with an id from memory.
- **The fix, `23421fd51`:** a done-shaped final message is now refused unless the tool produced it this turn, and the refusal names the command to run. The refusal is capped at 3 per turn, so it cannot loop. Ordinary "Done ..." prose is untouched.
- **Selftest:** 20/0, up from 16; the 3 new refusal arms were RED first. `CRITERIA_VERSION 2026-10-29.cody-b66.1`.
- **The armed copy** in `.git/sairn-hooks/` was updated and is byte-identical to the tracked file.
- **Not done:** an end-to-end run against this clone's live state file. The auto-mode classifier denied the cleanup step, so the selftest is the evidence.

## 2. Licence guards and the confirmed-set TTL (item 2)
- **The sweep: the b65 flaw was in 12 more apps,** from the same commit `343c5a327` (2026-09-03): sairndental, sairnsenior, sairncare, sairnbuild, sairndesign, sairnlaw, sairnlegacy, sairnroofing, sairncode, sairnbiz, sairngrounds and sairnscape.
  - All 12 are fixed in `862ed3591`, using b65's sairnfreedom fix (`f4d8c29fa`).
  - **How the key is read:** raw for the nine `*_license_key` apps; parsed as JSON for `sb_lic`, `grd_lic` and `scp_lic`.
  - **New test** `tests/licence_guard_legacy_device.js` covers 13 apps, with sairnfreedom as the control. L1/L2 were RED in all 12 first; 52/52 now.
  - **`tests/licence_rekey_isolation.js` had pinned the flaw as the requirement.** Its first-run fixture stored `'A'`, entered `'KEY-A-2026'` and asserted adopt. The fixture now stores the entered key: 70/70.
  - checkblocks: 0 failed in all 12. Every test naming a licence guard is green.
  - **Normalisation check.** Each app has exactly ONE writer of its stored key, the gate. In the 4 sampled (dental, biz, law, grounds), the gate has upper-cased the key since the file's first commit. So a same-licence legacy device is not offered a wipe on a case difference.
- **The TTL, `0f8c36e10`.** Only sairnfreedom has a confirmed set (`sf_server_confirmed`), so "platform-wide" is this one site.
  - The decision being applied is cc b70 gap (a), on cody b61 `7ae231b47`; the cc b70 verdict is in `docs/tier-a-reviews.json`, record opened 2026-10-29T11:12:43Z.
  - **How it works:** each id is stamped in `sf_server_confirmed_at` and reads as confirmed for 90 days. A write the server accepts, or a read that returns the row, re-stamps it.
  - **Untimed legacy entries read as NOT confirmed until re-stamped.** The id list is kept.
  - **An unreadable stamp record is COULD NOT TELL,** and is never overwritten.
  - **New test** `tests/sairnfreedom_confirmed_ttl.js` EXECUTES `sfConfirmOnServer`, which was cc b70 gap (c)'s point. T3/T6/T7/T8 were RED first; 10/10 now.

## 3. Schema snapshot re-capture (item 3), `d475bb091`
- **Method:** read-only SELECTs on Supabase `sairn-platform` (`ejrlrrkvhtllxbbypdjb`) at 2026-10-29 20:11:46Z.
  1. Group hashes found the drift since 10-21: three NEW tables, `mech_jobs`, `mech_invoices` and `mech_inspections`, from fourth b67's records `a4414c595`, each with a `_data_size` CHECK; and the safe-direction widening of `sairnlegacy_audit_log_event_type_check`.
  2. Those rows were fetched from live and written in.
  3. **Every group was re-compared: 70/70 column groups and 45/45 CHECK groups match.** 503 tables, 4198 columns, 564 CHECKs.
- `_generated_at` is the live `now()` of that comparison.
- **Not captured, as before:** UNIQUE/PK/FK.

## 4. Tier A reviews and R-12 (item 4)
| obligation | verdict | routed |
|---|---|---|
| hank 2026-10-06T07:29:58Z, `sdn_projects`, anchored `581e214fb133` | **SOUND-WITH-GAPS (low).** The `[]` column list, `updated_at`, sdn_clients reachability and the test are all sound. **Gap:** the b58 write-unconfirmed shape (cody b58's mech fix). The generic SDN 200 (`api/sd-data.js:15860`) and the sdn_clients write (`:6746`) answer ok when the store returned no row. | **hank**, in the verdict: apply `wroteRow()` + `refuseUnstoredWrite()` with red-first arms. Also stale citations `:12399`/`:12403`; they are now `:15801`/`:15805` (my verdict says `:15804`, one line off). |
| hank 2026-10-06T07:56:17Z, `sen_settings`, anchored `f98982410649` | **SOUND.** Every citation was read AT THE ANCHORED COMMIT. All 5 false-positive claims hold. Of the 20 "line N" de-citations, 13 are arrow pairs, and the other 7 name the current site in the same sentence. alf_staff `:4579`/`:4582` and bld_warranty `:6904` are correct. | none |

- **R-12** is cc b73's (`69c36d5ff`, `SAIRN-handoff-cc-b73.md`, row R-12): sairnmechanical `mechCredAdd`/`mechAssetAdd` with no rejection handler.
  - **Fixed in `824bab9dd`:** a rejected or answerless write now prints "Not saved -- ..." in `mech-cred-err`/`mech-asset-err`.
  - The handler covers the write alone, so a throw after a SAVED write is not misreported.
  - MC4/MA4 were RED first; 14/0.
- **No Tier A obligation is assigned to cody now.**

## 5. Live verification (after the push)
- All 14 touched apps are served byte-identical to HEAD (sha256 after CR strip), fetched no-cache with `tools/sairn_http.py`. 13 carry the guard fix; sairnmechanical has no guard and carries R-12.

## 6. Methodology
- **Fixture first** for every fix in items 1, 2 and 4.
- **Cause tags:** `docs/recurring-bug-classes.md`, "batch 66 (cody)", rows 1-4.
- **Register records:** 4 in `docs/defect-density-register.json`.
- **Tier A obligation** for the b66 app changes, assigned to **fourth**.

## Open, and the exact next step
| # | open item | owner | exact next step |
|---|---|---|---|
| 1 | Tier A review of the b66 app changes (12 guards, TTL, mech R-12, snapshot) | fourth | `--discharge cody <opened_at>`; the attack points are in the record |
| 2 | Tier A reviews of the b65 fixes, two obligations | cc | as opened in b65 |
| 3 | The b58 write-unconfirmed shape in the SDN generic write (`api/sd-data.js:15860`) and the sdn_clients write (`:6746`) | hank | b58 pattern, red-first arms; `tests/sd_data_mech_write_unconfirmed.js` is the template |
| 4 | `deploy_verify_notify` chained-push silent skip (cody b65 verdict on fourth's 2026-10-05T15:02:28Z record, anchored `9cc58a00f`) | fourth | decide per segment, two red-first arms |
| 5 | `exit_status_attributable` five silent suppressions, and the sb_ap non-ISO year (cody b65 verdict on cc's 2026-10-06T06:18:11Z record, `3cf3d5ec3e2c`) | cc | five red-first arms |
| 6 | H2: 10 unresolved calibration confidences, seq 1078, 1079, 1080, 1082, 1083, 1084, 1085, 1091, 1109, 1115 (row `B65-H2-CALIBRATION-CODY-2026-10-29`); seq813's "retired" corrected by seq871 (row `B63-H2-SEQ813-CODY-2026-10-29`) | hover2 | as each row says |
| 7 | sairn-app-scaffold still carries the OLD guard text, so a new app reintroduces the first-run adopt | cody / skill owner | put the corrected guard in the scaffold |
| 8 | `gcdMarkShotStart` is not held (cody b65 `f6a127280`) | cody | decided in the b65 grounds review |
| 9 | Make the re-entry sweep a standing checker (server, device and timer shapes) | cody | `tools/` checker with fixtures |
| 10 | Every other open item from b64 and b65 | as listed there | `SAIRN-handoff-cody-b64.md` rows 7-20; `SAIRN-handoff-cody-b65.md` rows 4, 6, 10, 12 |
