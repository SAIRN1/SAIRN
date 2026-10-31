# SAIRN handoff — cody b70 (2026-10-30)

**Citations:** every SHA below is the LANDED one. The push rebased my commits and the old SHAs were re-seated. Findings are cited by function, record `opened_at` or SHA, never by line alone.

## Committed / pushed state
- **Landed through the full gate.** The final SHA is in `SAIRN-report-cody-b70.txt`.
- **The manifest** adds `sairnvet.html` for cody (`_assigned_overrides_why_cody_b70_ADDS_ONE`).
- **Claims:** none held.
- **Tier A obligation** for this batch's app changes is assigned to **cc**.

## 1 + 7. B69-REENTRY-14: 9 fixed, 5 not re-entrant
**Method:** every candidate was decided by a **NO-REFILL double press**: fill the form once, press twice, the wait held. `H.drive` refills the form before every press, so it can report a duplicate that a real double press cannot make. The dental agent caught that, and every later handler was proven without it.

**Fixed (9).** Each has a per-function flag, checked first, set, and released in `finally`. Each arm was RED on HEAD's file, is GREEN now, and goes RED again in a copy with only its guard line deleted (the broken-copy proof):
| app | function | flag | arms | landed |
|---|---|---|---|---|
| sairngrounds | `sendDesignToQuote` | `grdDesignQuoting` | SQ1-3 | `414794471` |
| sairngrounds | `grdUploadProgressPhoto` | `grdPhotoUploading` | PA1-3, PB1-3 | `414794471` |
| sairnscape | `scpSendDesignToQuote` | `scpDwQuoting` | DQ1-4 | `3a133ef2f` |
| sairnscape | `scpSendIrrZoneToQuote` | `scpIrrQuoting` | IZ1-4 | `3a133ef2f` |
| sairnscape | `scpSendWfToQuote` | `scpWfQuoting` | WF1-4 | `3a133ef2f` |
| sairnscape | `scpUploadProgressPhoto` | `scpPhotoUploading` | PA1-4, PB1-4 | `3a133ef2f` |
| sairnsenior | `generateClaim` | `senClaimGenerating` | C1-3 | `fb10f57f3` |
| stonedesk | `intakeAccept` | `intakeAccepting` | IA1-3 | `bb2a99a20` |
| stonedesk | `sdAIQGenerate` | `sdAIQGenerating` | AQ1-3 | `bb2a99a20` |

- **Arm 4 is a permanent no-refill arm** in the scape tests.
- **New test files:** `tests/sairnscape_save_reentry.js` (30/0) and `tests/sairnsenior_save_reentry.js` (5/0). grounds is 63/0 and stonedesk 28/0.
- **Existing tests that cut a fixed function out without its new flag** each gained the declaration: `sairnscape_send_button_and_licence` 10/0, `sairnscape_outbound_queue_review_probe` exit 0, `sairnsenior_contract_auth_save` 29/0, `sairnsenior_negative_hours_claim` 22/0, `intake_no_false_success` 23/23.

**Not re-entrant (5), unchanged:**
| app | function | why |
|---|---|---|
| sairndental | `addProcedureType` | `cancelProcedureRevise()` clears the form before the await; measured writes=1 |
| sairndental | `saveGfe` | `gfeLines=[]` before the await |
| sairngrounds | `msbCheckout` | `msbCart[which]=[]` before the await; a second press reads "Cart is empty" |
| sairnlegacy | `generateAftercareSchedule` | it skips existing types, and its ids are fixed (`legAftercareId`) |
| stonedesk | `sdLocAdd` | input comes from a modal `prompt()` on every press |

## 2. The checker's recall misses, root-caused; one excluded shape now covered
`tools/reentry_hold_check.py` criteria `2026-10-30.cody-b70.5`, 25 fixtures locked.
- **The 7 b64 misses, measured on `c654f1152^`:**
  - 3 were `.then` handlers outside the universe: `alfFamilySave`, `mechCredAdd`, `mechAssetAdd`.
  - 4 were async handlers ruled NOT-SUBJECT: `confirmPayment` (an amount applied by assignment), `saveCsCount` and `respondToComplaint` (no creation shape), and `dcCreateInvoiceAndSchedule` (`rDreamClose()` read as a dismissal).
- **`.5` adds two things:**
  - **`.then` handlers:** plain functions are in the universe, and with no await the wait is the first `.then(`.
  - **Two creation shapes:** `.push({`/`.unshift({`, and `x=(Number(x)||0)+a`.
- **Recall on b64's known fixes: 44 of 47** (was 40). **Still missed (3):** `saveCsCount` and `respondToComplaint` write to an existing id, which no creation shape matches. `dcCreateInvoiceAndSchedule` matches the dismissal pattern through `rDreamClose()`.
- **At HEAD:** 2828 handlers: 110 HELD, 49 RE-ENTRANT, 1 COULD-NOT-PARSE. **Precision of `.5`'s 29 NEW candidates is NOT measured yet.**
- **The checker also missed the 5 non-re-entrant shapes above**: helper-cleared forms, source variables reset, modal prompts. Each needs a fixture before it is taught.

## 3. rf_schedule/set_status attribution test (`e514c26af`)
- **`b96d7ae684af` resolves in NO clone** (cody, hank, cc, fourth) and appears in no tracked file. I could not cite it, so the work was located by subject.
- **The suite was red (17/3) on correct code.** `d7773533f` (2026-10-13) moved the stamp out of the blob into the real columns `status_changed_by`, `status_changed_by_role` and `status_changed_at`, which are present in the live schema.
- **What the arms now check, driving the real handler and its PATCH:**
  - B: the three columns come from the SESSION;
  - C1: a hostile `payload.status_changed_by` is discarded;
  - D3: the PATCH carries NO `data` key.
- **Result: 20/0.**
- **Ablated in temp copies of `api/`:** an actor taken from the payload → B and C1 red; a blob written back → D3 red.

## 4. quotes / stonedesk_quote_history COULD-NOT-TELL
- **Re-seated** record `2026-10-30T08:33:24Z` from `50e0df33bb96` to `3d4ff0400` (EXACT FILE SET), through `--reseat-shas --include-reviewed --write --only`.
- **The real review was done in cody b69** against `3d4ff0400`: SOUND, arms 9-10 re-driven RED on its parent. The record now names the commit that review read.

## 5. Licence re-key guards: mech, cash, vet (`3cbfa6d2d`)
- **sairnvet: NEEDED, built.** It stores `sv_license` (JSON) beside 51 `sv_` keys.
- **sairnmechanical: NEEDED, built.** It stores `sairnmechanical_license_key` raw, beside its quotes, checks, docs, takeoffs and pricing keys. The guard is called on both entry paths: `doLogin` and `mechBootstrap`.
- **sairncash: NOT needed.** It stores no licence key: Firebase RTDB, keyed by `customerId`, single user, with no `license_hash` anywhere.
- **Build:** the guard is ported from sairnbiz with the b66 legacy-device and b68 case checks, and called before the key is stored.
- **Fixture first:** both apps were added to both guard suites before the port. They were COULD NOT RUN and 16 FAIL; now 90/90 and 78/78.
- **Live check:** sairnvet and sairnmechanical are served byte-identical to HEAD (section 7).

## 6. Citation audit, the next 10 commits (item 6)
**Commits:** `5ae8958d3`, `80db646f8`, `db0ea6f49`, `010e5e58a`, `cce3c0eb6`, `7bf01a080`, `582d6ff8f`, `9e4993243`, `de3547365`, `de72af904`. Two interleaved cc commits were excluded.
- **Two slips, both the SDN write sites cited by line alone:**
  - `9e4993243` ("`:15860` and `:6746`");
  - `db0ea6f49` ("re-measured at HEAD (`:15876`, `:6762`)").
- **Both are superseded** by row `B67-SDN-WRITE-UNCONFIRMED-CODY-2026-10-30`, re-anchored in b68 on blob `881804937a60` and the quoted code. The other matches were timestamp minutes.

## 7. Live verification
- **All six changed apps are served byte-identical to HEAD** (sha256 after CR strip, no-cache fetch with `tools/sairn_http.py`): grounds, scape, senior, stonedesk, vet, mechanical.

## Open, and the exact next step
| # | open item | owner | next step |
|---|---|---|---|
| 1 | Tier A review of the b70 app changes | cc | discharge |
| 2 | Precision of the checker's 29 new `.5` candidates | cody | no-refill read of each |
| 3 | Checker shapes it still misses: existing-id writes, helper-cleared forms, source resets, modal prompts | cody | one fixture each, then teach |
| 4 | SDN write-unconfirmed (`B67-SDN-WRITE-UNCONFIRMED-CODY-2026-10-30`) | hank | as the row says |
| 5 | Rows carried from b69 (cc, fourth, hover2) | as listed | `SAIRN-handoff-cody-b69.md` |
