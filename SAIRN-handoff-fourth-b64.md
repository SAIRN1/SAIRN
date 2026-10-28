# HANDOFF — fourth / ted, batch b64, 2026-10-28

**READ THIS FILE ONLY.** It is the whole state.
- **Item 1, the EVV billing gate, was NOT started.** cc held an active `sairnsenior` claim (b67) for the whole batch, so I flagged it back per the standing rule. **Decision needed**, in section 2.
- **Item 3:** both defects are fixed and landed. **The live drive was not possible**: SAIRNvet has no audit licence, and the permission classifier denied a live probe for one. I wrote the mint SQL for Michael.
- **Items 4 and 5 are done.**
- No force. **One logged gate bypass:** the deliverables push landed through `push_retry --loop`'s pure-base fast retry. That is `--no-verify`, but only after the gate had passed on the same 3 patch-ids; the retry is logged in `docs/BYPASS-LOG.jsonl`, 2026-10-28T23:53:03Z. Wrapped at 47.9% real context.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\b6e28c25-eaee-4611-aeb3-d94f0198d47f.jsonl`
**Scratchpad:** `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\b6e28c25-eaee-4611-aeb3-d94f0198d47f\scratchpad\` (`docverify63.py` is the doc check)

## 1. STATE

| item | sha | state |
|---|---|---|
| 1 EVV billing gate + live test on real rows | none | **NOT STARTED.** It was blocked by cc's active `sairnsenior` claim (b67, "caregiver local purge on merge", FILES `sairnsenior.html`). `sairn_claim.py check` said BLOCKED at the start, twice mid-batch and at wrap |
| 2 methodology: real DB rows in both states | none | goes with item 1 |
| 3 sairnvet: SOAP body + witness token | `d21bf39aa` (fix), `b4592bd3b` (record), `69916b60f` (mint SQL) | **fixed and landed, tested 13/13; NOT live-driven** (section 3) |
| 4 deny-hook false positive | none | **held for cc**, as told. Not touched |
| 5 queued audits: mechanical, build, cash, grounds | `d92ead730`, `71fd4dd9d` | **all four landed** |

## 2. DECISION NEEDED: item 1

**The block.** cc's b67 claim on `sairnsenior` covers `sairnsenior.html`. The gate needs that file and `api/sd-data.js` (the `sen_claims` branch). The standing rule is: on an overlap, flag back and wait. **I did no item 1 work.**

**Recommendation.** The gate is small once the claim clears. Either give fourth a go-ahead naming cc's claim id, or release it after cc b67 lands. Item 1 then runs first next batch, in this shape:
- **Reviewable surface.** A "Clock flags" view lists every visit carrying `clock_flags`, `*_skew_ms` or `*_received_at` (written by `checkClockEvent()` `api/_lib/sen-evv-clock.js:149`; 0 reads in the html today). A reviewer action records `{reviewed_by, reviewed_at, note}` on the visit.
- **The gate, on the server.** In the `sen_claims` write, refuse any status move to `submitted` or `paid` for a claim whose visit has a flag with no review. The client-side mirror is `readyToBillVisits()` `sairnsenior.html:4276`.
- **The live test, on `SEN-AUDIT-2026` (it exists).** Two real visits and two real claims: one flagged and unreviewed, which must be refused; one reviewed, which must pay. The rows are read back, with residue SQL.

## 3. ITEM 3: sairnvet

**SOAP body.**
- `generateSOAP()` now stores `note` (the reviewed text) and the full `subjective` / `objective`. Before, it kept 60 characters of the complaint.
- `scribeAcceptDraft()` now stores `note`. Before, it cleared the draft from the screen, so the accepted note existed nowhere.

**Witness token.**
- `svPushOne()` requests a token for an `sv_controlled` write from `/api/sv-witness` (`request`), as the signed-in session, for the **exact outbound record**. It then writes with `X-SV-Witness`.
- A refused token sends **no** write, resolves null, and is shown on screen.
- `logControlledUse()` now requires the veterinarian to confirm the entry before anything is written. The token is the record of that confirmation.
- Every other collection still writes synchronously.

**Tests.**
- `tests/sairnvet_witness_token_client.js`: **13/13**. The server's own `contentHash()` proves the token is spendable on the record that was written. Against the unfixed file the suite is COULD NOT RUN.
- `tests/sairnvet_seed_never_syncs.js`: four arms moved from `sv_controlled` to `sv_patients`, because they read the write synchronously and test seed suppression, not the register. 23/23.
- `audit_and_controlled` 58/58; the dose reader and controlled export are green.
- `node --check`: 3 blocks, 0 errors.

**Why there is no live drive.** SAIRNvet has **no audit licence**: `SV-AUDIT-2026` was measured ABSENT on 2026-09-29. My live re-probe was **denied by the auto-mode classifier**, and I did not route around it. Writing to `SV-PINNACLE-2026` would put permanent register rows on the demo licence.

**What Michael runs:** `sql/mint_sv_audit_2026.sql`. It writes the licence row only; the file contains the bootstrap call and both live arms.

**Not fixed, and stated in the register record:** the register is still **rewritten in place** per drug on both client and server (an upsert by drug name). Append-only is its own change.

**Push incident.** The first push was refused by derived-docs, and by `api/b18-countersign-lock.test.js`, whose ablation could not open `api/sd-data.js` (Windows `UNKNOWN: open`, a transient lock). `api/sd-data.js` was verified unmodified afterwards. The next push passed the same guard.

## 4. ITEM 5: the four audits

All four are built from research on file, with no fetches and no regulator read. All were GFM-rendered and their citations checked. Each has defects in records the app already writes, routed below.

**Mechanical** (`docs/cloud-research/sairnmechanical-worldwide-…`):
- It is a compliance registry with **no job, invoice or inspection record**.
- `saveQuote()` does not store the client.

**Build** (`…sairnbuild-worldwide…`):
- **`awardSubBid()` has awarded nothing since `66cf7b930` (2026-08-09)**: its one mutating line was removed, and it still toasts "Awarded".
- The WIP forecast has no writer.
- The lien waiver gates no payment.

**Cash** (`…sairncash-worldwide…`):
- The September tax findings are fixed in code.
- **A hidden checkbox saved as an answer suppresses the 110% warning.**
- A typed $0 is dropped.
- Solo 401(k) room is uncapped at earnings.
- Entries are dated at the keystroke and cannot be corrected.

**Grounds** (`…sairngrounds-worldwide…`):
- **Clearing a day's alcohol sale hours opens it all day** (`saveMsbHours()`).
- There is no pesticide application record.
- Quote lines lose their text.
- Job completion is not photo-gated.

## 5. OPEN, with the exact next step

1. **Item 1:** a go-ahead, or cc releases `sairnsenior`; then section 2.
2. **Vet live drive:** Michael runs `sql/mint_sv_audit_2026.sql` and bootstraps `audit-owner`. fourth then drives both arms live (confirmed, then 200 plus a row; no token, then 403).
3. **Defects found by the audits.** Each needs a claim and a register record:
   - grounds sale hours (**first: an alcohol control**);
   - build `awardSubBid`;
   - cash profile checkbox and the Solo 401(k) cap;
   - mechanical quote client;
   - build forecast;
   - grounds quote lines.
4. **cc:** the deny-hook false positive on `sh -n` of a hook file (held, per item 4).
5. **The b62/b63 items still open:** orphan scrutiny rows (cc after b66); the install_git_hooks hook-fire commit; `--supersede`; the staging_discipline fixture; the allow-rule line.

## 6. CLAIMS

`fourth` held `sairnvet` and `sairnmechanical` (the audit docs). Both are released at wrap.
