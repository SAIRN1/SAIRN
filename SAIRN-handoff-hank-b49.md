# SAIRN handoff — hank b49 — 2026-10-21

**Subject:** live run of the b48 straight-time floor shapes (`040ac5a95`) on the DEPLOYED SAIRNsenior pay run;
status of cc's b38 finding on the b40 photo overlay. No code changed. Written before the report, nothing
half-finished.

## 1. PUSHED STATE
Only these three documents. **NOT FORCED.** Re-derive the tip after the push.

## 2. CLAIMS HELD
None (released at the end of the batch).

## 3. THE ITEMS
**1. Live run — VERIFIED, every arm green.** Concept carried from b48: *a correction to a paid visit is priced at
THAT visit's own rate, never netted, names its closed period, and flags a possible premium rather than computing one.*

*Method.* Audit licence `SEN-AUDIT-2026` only (no customer data); owner `audit-owner` (PIN read from
`sql/audit_owner_and_demo_caregiver_credentials_2026-10-20.sql`, never printed), identity confirmed by `whoami`.
Through the deployed API (`https://sairn.vercel.app/api/sen-auth`, `/api/sd-data`, `tools/sairn_http.py`):
1. provisioned caregiver `hank-b49-caregiver` (PIN generated, kept only in the scratchpad), whoami = caregiver;
2. rates `zz-b49-rate-18` ($18, effective 2026-01-01, **term_on 2026-09-15**) and `zz-b49-rate-22` ($22 from
   2026-09-16) — read back intact;
3. six visits scheduled by the owner and **clocked by the caregiver**: Sun–Tue 13–15 Sep 8h @ $18, Wed–Thu 16–17 Sep
   9h @ $22 (= 42h week of 2026-09-13), and Tue 22 Sep 8h;
4. closings `zz-b49-close-A` 2026-09-13..19 (paid 09-20) and `zz-b49-close-B` 2026-09-20..26 (paid 09-27) — read back;
5. corrections filed and approved by the owner (approved today, 2026-10-21): Thu +60, Mon −60, 22 Sep +45 — each
   read back as one approved correction with the recorded clock untouched;
6. `POST /api/sd-data {"action":"payroll","resource":"sen_visits","payload":{"period_start":"2026-10-01",
   "period_end":"2026-10-31","week_start_day":"sunday"}}` → **200**.

*Evidence (response excerpts, `data.adjustments` / `data.overpayments`):*
- `zz-b49-ot-thu` adjustment: period A, paid 09-20, as-paid 540 → 600 min, **week 2026-09-13 seen 2520**,
  **+60 min × 2200c = 2200c, premium_may_be_owed: true** — matches local O1/O2.
- `zz-b49-ot-mon` **overpayment**: −60 min at **1800c/h → 1800c**, `requires_human_act: true`, not in adjustments
  — matches O3.
- `zz-b49-pb-tue` adjustment: **period B**, paid 09-27, 480 → 525, **+45 × 2200 = 1650c, premium null** (480
  seen) — matches P1.
- caregiver totals: `gross 0, adjustment 3850 (=2200+1650), overpayment 1800, total_payable 3850` — payable ≥
  gross, overpayment not netted (O4). Run-level `overpayment_cents 3800` = this 1800 + b27's 2000 (approved
  2026-10-20, same run window) — consistent.
Full responses: `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517\scratchpad\b49\evidence.json`;
script: `...\scratchpad\b49\live.py` (+ `common.py`).

*Not driven live, and why:* two agencies (a second SAIRNsenior test licence would mean writing to the demo-facing
SEN-PINNACLE-2026), exactly-one-run across successive runs (approvals are server-timestamped "now"), and a
reopen. All three are covered by the local suite (G1–G4, P2–P3).

*Residue (undeletable by design, audit licence only):* 6 `sen_visits` (`zz-b49-*`), 2 append-only closings, 2 rates,
1 caregiver credential.

**2. Trust-lock** — left alone per dispatch.

**3. cc b38 finding on the b40 overlay — ALREADY FIXED in b44, `2fe89f267`** (on origin): whole-value data-URL
check at intake AND overlay, escaping kept as an independent barrier, cc's 3 surviving mutants plus 2 more killed
(section M), Escape/click close with focus return; `api/b40-stonedesk-style-profile-request-photos.test.js` 27/0
(16/11 on the pre-b44 source). Tier A review routed to cc then.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| T1 | Tier A reviews of `040ac5a95`, `38b2b5069`, `2fe89f267` | cc |
| L1 | two-agency / successive-run / reopen live shapes | only if a second test licence is authorised |
| B | schema snapshot re-export | Michael |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
