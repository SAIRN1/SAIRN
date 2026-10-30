# SAIRN handoff — hank b72 — 2026-10-30

**Subject:** b72 items 1 to 5.
- M5L on a scratch licence.
- VT against the more authoritative source.
- 1817T closed.
- 1734S, the server-side id check.
- Confirming the b71 push.

This handoff was written before the report. Every SHA is LANDED. HEAD was fast-forwarded to `76d05b432` before any work.

## 1. M5L — BLOCKED: the scratch licence is written but NOT minted, because database access was refused (`193a83757`)
- **LAW-PINNACLE-2026 was not used**, as instructed.
- **The existing scratch licence LAW-AUDIT-2026 cannot be used either.** It is active, but its bootstrap answers 409 ALREADY_PROVISIONED (an owner exists), and this session does not hold that owner's PIN.
- **The mint is ready as `sql/audit_license_seed_law_0002_2026-10-30.sql`.** It inserts `LAW-AUDIT-0002` into `public.license_keys` and nothing else. It is idempotent and ends with a verify select.
  - I tried to apply it through the Supabase MCP. The **auto-mode classifier refused even a read** ("Production Reads"), so nothing was written.
- **Next steps, in order:**
  1. Michael runs the SQL file in the Supabase SQL editor (project `SAIRN`, `ohzqfwndmuowbswpbxxp`) and confirms the verify row.
  2. hank bootstraps `audit-owner` on LAW-AUDIT-0002 with a fresh PIN through `/api/law-auth` (the file header gives the call). The PIN is written only to `.git/sairn-law-audit-owner-pin`.
  3. hank writes a `law_bankstatements` row and a `law_trusttx` deposit dated more than 30 days before it with `cleared: false`. The balances are arranged so the bank leg balances only by carrying that deposit.
  4. Read `law_trust_reconcile`. Expect `PARTIAL` with `bank_vs_ledger.stale_deposits_in_transit` listing the deposit.
  5. Open Trust Accounting on sairn.vercel.app signed in as that owner. Expect "Partly reconciled" plus the stale-deposit sentence.

## 2. VT (J5) — retried against the PROMULGATION ORDERS. Still not seeded (`e207cd9bf`)
- **Why the orders:** they are the Supreme Court's own instruments, so they *are* the amendments. A compiled copy is derived from them, and the Judiciary defers compilation to Lexis.
- **The orders were found and read.** Each is listed with its URL and sha256 in `docs/sairnlaw-vermont-deadline-seed-blockers.md` §b72:
  - 2020 Rules 26(c)/34(b);
  - 2021 Rules 7/56 and abrogating 78;
  - 2022 Rule 68;
  - 2022 emergency Rule 56(b).
- **Where they came from:** the Judiciary still serves unlisted orders under `/sites/default/files/documents/`. LCJR (committee 34) was enumerated in full: 440 documents.
- **What they show:**
  - **34(b) was amended** (effective 2020-12-07), but its 30/42-day periods are unchanged.
  - **No order found amends Rules 6, 12, 33, 36 or 59.**
  - **That is not proof that none exists.** Neither listing is an index; LCJR's list, for one, is missing orders the Judiciary still serves.
- **The narrowed unblock:** a Judiciary or Court Administrator statement that no order since 2018-01-01 amended 6/12/33/36/59, or their chronological list of civil orders for that window.

## 3. 1817T — CLOSED AS FINAL, per Michael
The b71 fix stands as it is: behaviour kept, comment corrected (`149c90b97`), and the test pins both windows. No per-licence time zone will be added.

## 4. 1734S — DONE: the server-side id check (`88ca53fbd`, register `d4f200dbb`, Tier A obligation `d0bef386c`)
- **What it refuses:** the SAIRNlegacy write branch in `api/sd-data.js` now answers 400 `BAD_ID` to a `payload.id` that is over 128 characters, or that holds a quote, backtick, `<`, `>`, `&`, backslash or control character.
  - The check runs AFTER the `leg_aftercare` key rewrite, so a key derived from a hostile `case_id` is refused too.
  - **It is a denylist, not an alphabet.** An alphabet broke `api/leg-aftercare-key-unambiguous.test.js` and `api/sd-data-leg-role-matrix.test.js`, because the ACX- aftercare key carries the case id verbatim and a space is legal there. Both suites pass now.
- **`api/b72-leg-id-format.test.js` passes 7/7:**
  - 35 resources × 7 hostile ids are refused, with 0 upstream writes. `leg_cremations` is refused earlier, by its countersignature lock.
  - 75 real id shapes are accepted: 35 newId prefixes, 38 seed literals and 2 aftercare keys.
  - Ablation: with the check removed, the hostile id reaches a write.
- **Suites:** every SAIRNlegacy and sd-data suite matches base. These six fail at base too:
  - `family-contacts`
  - `law-trusttx-clearance`
  - `leg-bookings-toctou`
  - `leg-session-gate`
  - `sv-session-gate`
  - `sairnlegacy_reservation_lock`
- **The push gate required a Tier A obligation.** It is opened and ASSIGNED TO cody, with three attack questions.
- **#1734 is now closed on both halves:** the client (`af2db16b3`) and the server (`88ca53fbd`). That is pending cody's Tier A review.

## 5. The b71 push — CONFIRMED CLEAN
- Every b71 commit is on origin/main, including the VT doc `74117f84e`, the handoff `a73a678ea`, report+digest `fda464d96` and the BYPASS-LOG row `775865625`.
- Nothing was held back. The working tree was clean at the start of this batch, apart from the 7 U1 files.

## 6. Process miss, stated
**I did not take claims this batch.** The gate's claim recheck found no overlap (0 active claims by others), but the protocol says claim before you start.

## 7. Cause tags
`docs/recurring-bug-classes.md`, batch 72, row 1: the server treated the id as opaque text.

## 8. OPEN — exact next steps
| # | item | owner | next step |
|---|---|---|---|
| M5L | live M5 | Michael, then hank | run `sql/audit_license_seed_law_0002_2026-10-30.sql`, then hank does steps 2–5 in section 1 |
| J5 | Vermont | Michael | the statement or chronological list in section 2 |
| T-1734S | Tier A review of `88ca53fbd` | cody | `tools/tier_a_review_gate.py --discharge hank <opened_at> "<verdict>"` |
| J6C | DC civil Rules 6/12/33/34/36/59 | hank | the same gate as Probate |
| carried | SDP, LGP, J4, J2, A1, P1, R1, G1, S5, S7, T1, M5r, RL1, LE1, HK1, H1z | as before | unchanged |
