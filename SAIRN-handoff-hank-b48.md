# SAIRN handoff — hank b48 — 2026-10-21

**Subject:** (1) the `leg_settings` audit rows read from the database; (2) SAIRNsenior straight-time floor coverage
beyond one agency / one closed period / two visits. Written before the report, nothing half-finished.

## 1. PUSHED STATE
- `040ac5a95` test(sairnsenior) — `api/b48-sen-straight-time-floor-coverage.test.js` (test only, no product code).
- `bec26b60e` Tier A obligation (cites `040ac5a95` on origin; sen_visits, sen_pay_rates, sen_settings → cc) +
  regenerated MASTER-PLAN / traceability.
- Both on `origin/main`, **NOT FORCED** (one ref race). This deliverables commit follows.

## 2. CLAIMS HELD
None (released at the end of the batch).

## 3. THE ITEMS
**1. Audit rows, read from the database — CLOSED.** Supabase project `sairn-platform` (`ejrlrrkvhtllxbbypdjb`;
the `SAIRN` project timed out), read-only `select` on `public.sairnlegacy_audit_log` for
sha256(`LEG-PINNACLE-2026`), `event_type = 'settings_changed'`: **exactly two rows**, both `sairn-demo-owner` /
`owner`, `resource leg_settings`, `first_save false`:
- 19:43:50.84 — `livery_billing through_the_home → direct_to_family`, `livery_grants {} → {b46-live-check-driver:
  {leg_dispatches: true}}` (the b47 write)
- 19:43:52.08 — the exact reverse (the b47 restore)
No rows from b46's attempts, which answered `audited:false` before the CHECK migration — consistent.

**2. Straight-time floor coverage — concept:** *the floor stays a floor in every shape — a correction to a paid
visit is priced at THAT visit's own rate, never negative and never netted, names its closed period, lands in
exactly ONE later run, and says when an overtime premium may also be owed rather than computing one it cannot see.*
Interpreted against the confirmed-clean record for `144dfb71587e`, whose stated limit is exactly "one agency, one
caregiver, one closed period and two visits ... says nothing about premium (overtime) cases, multi-rate weeks or
reopened periods". `api/b48-sen-straight-time-floor-coverage.test.js` **23/0**:
- **O (engine, `api/_lib/sen-payroll.js`):** 42h week with E1's rate changing $18→$22 mid-week: +60 on the $22 visit
  → adjustment 2200c, `premium_may_be_owed true`, 2520 min seen; −60 on the $18 visit → overpayment 1800c,
  `requires_human_act`, not netted; 39h+2h → true; 30h+1h → null (never false); the open run's own OT week uses
  the weighted regular rate and no closed week leaks in; a mixed-rate OT week → 84400 straight + 2010 premium.
- **P (engine):** corrections in two closed periods each name their own period/paid_at; an approval inside P2's
  window lands in the P2 run and not the later one; an approval before its period was paid never adjusts.
- **G (real pay-run handler in `api/sd-data.js`):** two agencies with identical visit/employee ids — only the one
  that closed P1 adjusts; every visits/rates/closings/settings read carries its own licence hash; a closed-then-
  reopened P1 freezes nothing.
- **M:** five mutants each turn their arm red — run-start rate (O3), no over-40 crossing check (O5), no approval-
  window start (P2), first-period mapping (P1), unscoped closings read in the handler (G1).
- Siblings: b17 11/0, b16 17/0, sen-payroll 27/0.

**Not covered and said so:** the dispatch also named the **trust-lock**. Its confirmed-clean record
(`7e43c9dab7dc`, SAIRNlaw) has a different limit ("one licence, one paralegal, one moment"), not the
agency/period/visit shape; it was not extended this batch. No live run of the new shapes (that needs writes to
SEN-AUDIT-2026).

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | next step |
|---|---|---|
| T1 | Tier A review of `040ac5a95` (and `38b2b5069`, b45) | cc |
| L1 | live run of the O/P shapes on SEN-AUDIT-2026 | hank, if a live write there is authorised |
| L2 | SAIRNlaw trust-lock coverage beyond one licence/paralegal | hank, if that is what was meant |
| B | schema snapshot re-export | Michael |

## 5. TRANSCRIPT
 C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
