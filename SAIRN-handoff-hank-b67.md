# SAIRN handoff — hank b67 — 2026-10-29

**Subject:**
- S3: triage of the 41 S2 sites.
- VT and DC primary sources.
- J4, J5 and J6 stated verbatim in the digest.
- The C1b discipline on shared files.

This handoff was written before the report.

## 1. S3 — the 41 S2 sites, triaged
| class | n | verdict |
|---|---|---|
| INSERT (POST with no upsert) | 30 | append only; nothing is overwritten, so not a lost update |
| compare-and-set write | 6 | GUARDED. These were S2 false positives: `spent_at=is.null` ×3 (countersign, sairncare-witness, sv-witness), `revoked_on=is.null` (accounting:318), `status=neq.revoked` (agent/register:83), `renewal_count=eq.<read>` (sairncash/trial-renew:120) |
| cross-table write | 2 | low: sd-sub-data:459 (sd_subs → sd_sub_jobs), stonedesk-track:163 (sd_customers → sd_order_links) |
| per-user row | 1 | low: ai-notice:226 (license_hash + employee_id) |
| terminal-status overwrite | 1 | low: agent/result:79 (a late result can overwrite) |
| **REAL CANDIDATE** | **1** | **`api/agent/poll.js:112`** |

- **The candidate:** `api/agent/poll.js:112` reads pending commands, then PATCHes `status: 'delivered'` by id with no
  `&status=eq.pending`. Two concurrent polls by the same agent could both deliver, and so execute, one command.
  - **Fix:** add `&status=eq.pending`, and deliver only the rows returned.
  - **NOT fixed here.** It is outside this batch's dispatch, and it is api/, so it is hank's for the next batch.
- **S2 fixed** (`1e892a1a6`): a filter on any non-id column now counts as a compare-and-set guard.
  - Selftest 10/10, including a CAS negative and an id-only positive. Removing the CAS check turns it red.
  - api/ re-scan: 41 → **35** sites. There is a register record.

## 2. VT — PRIMARY SOURCE FOUND (to be seeded next batch)
- **The source:** legislature.vermont.gov, the Legislative Committee on Judicial Rules, October 2017 meeting materials:
  https://legislature.vermont.gov/Documents/2018/WorkGroups/Judicial Rules/October 23, 2017 Meeting/W~Erik Fitzpatrick~Materials for Judicial Rules Meeting on October 24, 2017 ~10-23-2017.pdf
- It contains the Supreme Court's order: "That these rules and forms, as added or amended, are prescribed and
  promulgated effective January 1, 2018."
- **What is in it:** "RULE 6. TIME" (extracted line 189) and the Reporter's Notes: (a) "day is a day" (federal
  language), (a)(7) applicable statutes, and (e) adding three days.
- **Not seeded this batch:** context was at about 77%, and a seed cycle does not fit under the 85% wrap-up.
- **Next batch:**
  1. Read Rules 6/12/33/34/36/59 from it.
  2. Check vtcourts.gov's promulgated list for any later amendment.
  3. Then run the ND pattern.

## 3. DC — HARD BLOCKER: no primary source is reachable at all
- **Tried:**
  - dccourts.gov: every path returns 403. That covers the root, the rules pages, the Superior Court civil Rule 6 PDF,
    and the DR Rule 6 PDF that search surfaced.
  - A D.C. Register / Court of Appeals route turned up no official copy of the Superior Court civil rules. Search
    returned only third-party mirrors (courtrules.net, rulesofcivilprocedure.com).
- **Reachable:** D.C. Code § 28-2701 (holidays) at code.dccouncil.gov.
- **But the court's rule text is the computation source, and it is not reachable by any automated route.**
  - **Unblock:** a human downloads the dccourts.gov Superior Court Civil Rule 6 PDF and Rules 12/33/34/36/59, and
    commits them, or pastes them with the retrieval date.

## 4. C1b discipline on shared files this batch
- `docs/BYPASS-LOG.jsonl` was touched only through push_retry, and it is `merge=union eol=lf`. Its last fold printed
  "committed the BYPASS-LOG row".
- `docs/defect-density-register.json` is a JSON document, NOT line-appendable. Union would corrupt it, so it is NOT
  union-merged. It is guarded by push_retry's ACCUMULATED shrink check and the re-seat step instead.
- No other shared file was touched.

## 5. CLAIMS HELD
`sairnlaw`. It is released after this push lands.

## 6. OPEN
| # | open | owner | next step |
|---|---|---|---|
| S4 | `api/agent/poll.js:112` double-delivery | hank | `&status=eq.pending` on the PATCH; deliver only the returned rows |
| J5 | VT | hank (next) | seed from the LCJR 2017 order text (§2) |
| J6 | DC | Michael | a human-fetched dccourts.gov Rule 6 / 12 / 33 / 34 / 36 / 59 |
| J4 | 7 questions | Michael / counsel | the verbatim text is in the digest |
| A1, T1, P1, R1, G1 | carried | as before | unchanged |

## 7. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\58897a7d-eff3-428b-8fec-18274a858ae9.jsonl

## 8. CLOSE-OUT (Michael's stop order, 2026-10-29) — every open item and its exact next step
**No change was in flight.** No new work was started and no claim is held (`sairn_claim.py list` shows none for
hank). The final SHA, checked against origin/main, is in the report.

**Left uncommitted ON PURPOSE (U1, not hank's).** These 7 untracked root files predate this session, and committing
them would publish material nobody has reviewed: `.claude/settings.json.bak`, `.claude/settings.json.hooks.bak`,
`conflict_excerpt.txt`, `dir`, `full_conflict.txt`, `resolve_conflict.py`, `schema_snapshot_raw.json`.

| # | open item | owner | exact next step |
|---|---|---|---|
| S4 | `api/agent/poll.js:112` can deliver one command twice | hank | in the PATCH URL append `'&status=eq.pending'`, send `Prefer: return=representation`, deliver only the commands the PATCH returned; add a test with two concurrent polls; register record |
| J5 | Vermont not seeded | hank | open the LCJR PDF (handoff §2 URL), read RULE 6 (line 189) and Rules 12/33/34/36/59; check vtcourts.gov/attorneys/rules/promulgated for any VRCP 6/12/33/34/36/59 order after 2018-01-01; then the ND pattern: standards push → load → verify → seed push |
| J6 | DC not seeded (hard blocker) | Michael | a human downloads Superior Court Civil Rules 6, 12, 33, 34, 36 and 59 from dccourts.gov and commits them under `sql/` or `docs/` with the retrieval date; then hank gates and seeds |
| J2 | RI holiday reading needs confirmation | Michael / counsel | answer J4 question (7); if any answer differs, edit `JURISDICTION_COVERAGE.ri` and the calendar, reload, re-verify |
| J4 | 7 lawyer's questions (verbatim in the digest) | Michael / counsel | send them; each answer changes a named row or calendar, all of them currently EARLY |
| S5 | the 35 remaining S2 sites | file owners | the 30 inserts are not lost updates; read the 2 cross-table and 2 low sites only if their rows can be written concurrently |
| S6 | push_retry's fold logs "derived-docs commit failed" with an empty error when nothing is staged | hank | in `_regenerate_and_fold`, return `nothing to fold` when `git diff --cached --quiet` succeeds; one selftest arm |
| S7 | push_retry's ACCUMULATED shrink check false-positives on a LEGITIMATE upstream removal (known-red-suites 63→62, b66) | cc | compare our own commits' effect on the ledger, not the pre/post-rebase counts |
| T1 | Tier A review of cdf71e894 (#1274) | cc | `python tools/tier_a_review_gate.py --discharge hank <opened_at> "<verdict>"` |
| A1 | ALF audit-owner recovery SQL | Michael | run `sql/alf-audit-owner-recovery.sql` as-is; move the PIN from `.git\sairn-alf-audit-owner-pin` to a password manager and delete that file |
| P1 | SAIRNcode trial gate is client-side | Michael | decide whether to add `license_keys.trial_ends_at` plus a server check in `api/sc-auth.js` login |
| R1 | readiness state-ID presence for coordinator/scheduler | Michael | keep it, or suppress it for non-HR roles |
| G1 | fx identity in the other clones | cody, fourth | confirm there is no local `user.*` and run `tools/committer_identity_check.py` |
