# SAIRN handoff — hank b63 — 2026-10-28

**Subject:**
- J1: gate and seed the never-gated jurisdictions.
- H1: decision log.
- D1: live isolation-guard re-verify.
- push_retry --loop stability across consecutive pushes.
- The UTC-calendar / read-await-write scan of hank's api/.

This handoff was written before the report. Nothing is half-finished.

## 1. J1 — AK and ND SEEDED and LIVE; RI GATED, NOT SEEDED; SD, VT, WY and DC not started
### Alaska — LIVE on LAW-PINNACLE-2026
- **Gate:** `docs/sairnlaw-alaska-deadline-seed-gate.md`. Read verbatim from courts.alaska.gov civ.pdf / app.pdf and
  akleg.gov AS 44.12.010–.025.
- **Engine:** `ak_civ_r_6a` / `ak_app_r_502a` (Ohio mechanism, under-7 tested on the base count) and `ak_civ_r_6c`
  (non-electronic mail +3, added to the period).
- **Coverage disclosure (`direction: 'early'`):** MLK Day ("as provided in (b)", employment-only); the AS 44.12.025
  Saturday→Friday shift (state employees only); proclamation days; and no mail days on the distribution-triggered
  59(b) / App.R.204 rows.
- The court-closure "legal holiday" sentence printed beside Rule 6 is **rescinded SCO 1875 note text**. It is not law.
- **Seed:** 12 rows, plus a 2026–2031 calendar that includes the Sunday→Monday shift.
- **Tests:** `api/_lib/deadline-alaska.test.js` 45/0, every date derived by hand first; 5 mutants red.
- **Live:** before the load, `NOT_PROVISIONED`. After the load, answer 2026-09-28 → **2026-10-20** and reply-by-mail
  2026-10-09 → **2026-10-20**, both equal to the hand derivation.
- **Push 2 used the scoped `SAIRN_GATE_EXEMPT=seed` (Michael approved, b63).** The seed gate requires load-before-push,
  but the live `add_rule` validator refused `ak_civ_r_6a` until the engine was deployed: a deadlock. The pair lost the
  race twice before landing as `f8f4c585e`. Rules were then loaded and drift is 0.
### North Dakota — LIVE
- **Gate:** `docs/sairnlaw-northdakota-deadline-seed-gate.md`. Read verbatim from ndcourts.gov and ndlegis.gov.
- **The holiday referent is EXPRESS** (6(a)(6) names N.D.C.C. 1-03-01/-02/-02.1), so BOTH weekend shifts are encoded.
  Friday 3 July 2026 IS a holiday in ND, where it is NOT in AK.
- **Engine:** `nd_rcp_6a` / `nd_app_r_26a` (federal count) and `nd_rcp_6e` / `nd_app_r_26c` (mail or carrier, +3
  AFTER expiry).
- **Coverage disclosure:** inaccessibility, proclamation days, Juneteenth, the Christmas Eve closure, the 45-day
  defendant floor, and no mail days on 59(c).
- **Seed:** 9 rows. **Tests:** 37/0; 4 mutants red.
- **No deadlock this time.** The engine standards shipped first (`ec23a9eac`). After the deploy, ND was loaded from the
  working tree and verified, then the seed was pushed (`443448988`) and the seed gate PASSED.
- **Live:** before, `NOT_PROVISIONED`. After: interrogatories by mail 2026-03-04 → **2026-04-09**, answer 2026-06-12 →
  **2026-07-06**, appeal by mail 2026-09-01 → **2026-11-05**. All match the hand derivation.
- **Load state:** `sairn_load_state_check --app sairnlaw` drift 0 (rules 457/457, holidays 158/158).
- **42/42 deadline suites green.** 'ak' and 'nd' were added to the 16 suites that pin the coverage key set, with a
  count-asserted edit per file.
### Rhode Island — GATED, NOT SEEDED
- **Record:** `docs/sairnlaw-rhodeisland-deadline-seed-blockers.md`.
- **What passes:** the rules. RI 6(d) is ONE day, and it covers electronic service too.
- **What blocks:** the holiday referent.
  - Rule 6(a) names no statute, and § 25-1-1 says "holidays".
  - Its weekend shifts are for "state employees".
  - The election-day clause has scope problems.
  - The open incorporation clause reaches federal days, including Thanksgiving.
  - No official Judiciary holiday list was found to converge against.
- **Needs** an official court holiday list or Michael's / counsel's direction. The preferred early-side reading is in
  the doc.
### Not started: South Dakota, Vermont, Wyoming and DC
**The pattern that worked (ND):** gate → engine standards push → deploy → load from the working tree → verify changed
live results → seed push.

## 2. H1 — DECIDED (Michael, b63): historical fx-authored commits are LEFT AS-IS
- These are the 426 fx-authored commits this clone created, 2026-10-07 to 10-28 07:27, measured in b62.
- No rewrite and no code change. Rewriting them would mean a force push on a shared branch.
- The identity fix holds: every commit since `a4afe6535` is mikied68.

## 3. D1 — PASS LIVE: the 09-15 isolation guard is now present
- **Where:** `public.sairn_ai_rate_limit_consume` on sairn-platform (ejrlrrkvhtllxbbypdjb). This is the project the
  app's api/ code names 13 times in the repo, against 2 for the other.
- **What was checked:**
  - The md5 moved from `fe098da9…` to `3699c57d…`.
  - `transaction_isolation` guard: yes. Lock: yes. The args are unchanged.
- **Both arms run live, each inside a transaction that was rolled back:**
  - REPEATABLE READ → `ERROR 25000 … requires READ COMMITTED … Refusing`.
  - READ COMMITTED → `{"limit":1,"limited":false,"prior_count":0}`.
  - Probe rows left: 0.
- **Not checked:** the "SAIRN" project (ohzqfwndmuowbswpbxxp) timed out on connect twice (b62 and b63).

## 4. push_retry --loop STABILITY — four b63 loop pushes, one of them not consecutive
| push | via | outcome |
|---|---|---|
| 1 AK gate | --loop | lost the race (transient), then **FAST RETRY, gate not re-run**, PUSHED. The live fast path is exercised for the first time; the BYPASS-LOG row was written. |
| 2 AK seed | `SAIRN_GATE_EXEMPT=seed` pair (not the loop) | 2 lost races (`fetch first`), and each rebase voided the sha-pinned exemption; the 3rd pair landed |
| 3 ND gate+standards | --loop | lost the race, then **full gate** ("our commits changed since the gate passed"), PUSHED |
| 4 ND seed | --loop | lost the race, then **full gate** (same reason), PUSHED |
| 5 these docs | --loop | see the report |

**Evidence, not a single pass.** Every loop push lost the first race, and the loop landed every one by attempt 2.

**Two findings for C1:**
1. **The fast path rarely fires.** After a rebase the loop's own regenerate-and-fold amends derived docs into OUR
   commit. That changes our patch-ids, so condition 2 sends it to the full gate. It is correct (conservative), but
   it means the fast retry only helps when no derived doc moved.
2. **`SAIRN_GATE_EXEMPT=seed` is pinned to the tip sha.** Under C1 traffic every lost race voids it. A seed-exempt push
   cannot go through `--loop` at all, because the first refusal is classed 'gate' and the loop STOPS. Both are routed
   to cc (push_retry owner) and to whoever owns the exemption store.

## 5. UTC-calendar / read-await-write scan, hank's api/ — 6 UTC derivations, 1 real (low)
- **The tool reads only `<script>` blocks.** Run on raw `api/*.js` it reports **0 of 191 files**, which is a vacuous
  pass on files it never read.
- It was re-run with each file wrapped in a script block. A planted fixture was DETECTED for UTC, which proves the arm
  works.
- **The planted read-await-write was NOT detected.** The stale-snapshot detector targets the client store shape. Its
  zero on api/ is **NOT evidence** of absence.
- **The 6 hits** (line numbers are for the unwrapped file):
  - `claude.js:238` daily demo bucket: intended UTC.
  - `legal-deadlines.js:981,1017` `retrieved_at` fallback stamp: metadata.
  - `sd-data.js:6540` and `sd-render.js:45` UTC month: consistent with each other.
  - **`sd-sub-data.js:71`**: COI/licence expiry is compared against the UTC day, so on a US evening it reads a
    same-day expiry as `expired` a few hours early. That is the blocking, conservative direction. **NOT fixed.**
    Open, owner hank.

## 6. CLAIMS HELD
`sairnlaw`. It is released after this push lands.

## 7. OPEN
| # | open | owner | next step |
|---|---|---|---|
| J2 | RI blockers | Michael / counsel | an official RI Judiciary holiday list, or direction on §25-1-1 readings 2–4 |
| J3 | SD, VT, WY, DC | hank (next) | the ND pattern: gate → standards push → load → verify → seed push |
| J4 | the AK/ND lawyer's questions: AK MLK (b), AK 6(c) on distribution, ND 59(c) mail, ND Juneteenth | Michael / counsel | bundle them with the existing SAIRNlaw lawyer's question |
| C1a | the fast retry is defeated by fold-amend; the seed exemption is sha-pinned under races | cc | decide whether derived-doc folds go in a separate commit, and whether the exemption can pin to patch-ids |
| U2 | `api/sd-sub-data.js:71` COI expiry vs the UTC day | hank | use a local-date helper (low) |
| S1 | `sairn_stale_snapshot_scan.py` reads `<script>` only, so it silently reads nothing on .js | tool owner | refuse, or say it read 0 blocks, rather than report a clean 0 |
| A1, T1, P1, R1, G1 | carried | as before | unchanged |

## 8. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\58897a7d-eff3-428b-8fec-18274a858ae9.jsonl
