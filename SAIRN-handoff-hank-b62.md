# SAIRN handoff — hank b62 — 2026-10-28

**Subject:** SAIRNlaw jurisdiction seeding, A1 ALF recovery SQL, a push_retry --loop re-verify, a live re-check of the
"[0053]" concurrency fix, and an fx-identity scan of this clone.

**Two of the five premises did not hold. Neither was acted on:**
- **Item 1:** there is no next seedable jurisdiction.
- **Item 2:** the A1 SQL already exists.

No code changed this batch. This handoff was written before the report.

## 1. SAIRNlaw JURISDICTION SEEDING — NOT SEEDED, and there is nothing seedable to take
- **`docs/MASTER-PLAN.md` does not track jurisdiction seeding.** It has one SAIRNlaw row (line 43: app tiering) and no
  jurisdiction status. The status lives in the seed files and the gate docs, so it was read from those.
- **Seeded:** 38 states have a `sql/sairnlaw_deadline_seed_<state>` file, plus federal and the cross-cutting sets.
- **Gated but not seeded. Every one is BLOCKED or FAILED by its own gate doc:**
  - Colorado: SPLIT, rules blocked pending a decision.
  - Iowa: DO NOT SEED.
  - Louisiana: not seedable (parish-only Saturday holidays).
  - Tennessee: FAILED.
  - Arizona and Kentucky: blockers, no permitted primary source.
- **Never gated:** Alaska, North Dakota, Rhode Island, South Dakota, Vermont, Wyoming and DC. None is claimed.
- **Why nothing was seeded.** Seeding one of these needs a NEW gate first: primary-source reads of the rules, the
  holiday statute and the weekend-coverage standing check. Every past gate was a 170–300 line write-up. Seeding without
  one would put unverified legal deadlines into an attorney-facing engine.
- **DECISION (Michael):** which never-gated jurisdiction to gate next, or which blocker to resolve (for example,
  Colorado's pending decision).

## 2. A1 — NOT WRITTEN: the recovery SQL already exists
- `sql/alf-audit-owner-recovery.sql` (hank b58/b59, run-ready, placeholder-free since `b676e7e79`) IS the A1 file.
- A1 in b59/b60 says "Michael runs it". It does not say "hank writes it".
- A second `sql/alf_recovery.sql` would be a duplicate, and the duplicate is the copy that goes stale.
- No SAIRNcare "ALF demo licence" blocker distinct from it was found in `docs/open-work/sairncare.md` or the hank
  handoffs.
- If a different recovery is meant (for example a demo licence other than ALF-AUDIT-2026), it needs naming.
- **A1 unchanged: Michael runs the existing file.** The PIN is at `.git\sairn-alf-audit-owner-pin`, per the file header.

## 3. push_retry --loop — RE-VERIFIED
- At origin `a2bdf5ea7`, `tools/push_retry.py` is identical to the clone, and the last change to it is hank b61
  `fdb5ca7ee`.
- `--selftest`: exit 0, 56 ok / 0 FAIL, **C1 arms 15/15 ok**.
- The end-to-end run is this batch's own push, through `python tools/push_retry.py --loop --attempts 5`. Its result is
  in the report.
- `.claude/settings.local.json` already allow-lists several `push_retry.py --loop` forms. b61's denial came from the
  auto-mode classifier, not from a permission rule.

## 4. "[0053]" TOKEN-DEDUCTION CONCURRENCY FIX — PASS (the race), with one drift FOUND
- **What it is.** The repo identifies "[0053]" as item 78 target 2, the AI rate-limit count-then-insert race
  (`docs/open-work/platform.md:159`). The self-log `[0053]` itself is a Kepler note (`docs/2026-09-15-...`).
- **The fix** is `public.sairn_ai_rate_limit_consume` (`sql/sairn_ai_rate_limit_consume_fn.sql`), called by
  `api/_lib/ai-rate-limit.js`.
- **Live, read-only, on Supabase project `sairn-platform` (ejrlrrkvhtllxbbypdjb), 2026-10-28:**
  - The function EXISTS (1 overload).
  - Its args `p_app_id text, p_limit integer, p_window_seconds integer` match the client's RPC call exactly.
  - It is SECURITY INVOKER. EXECUTE is granted only to postgres and service_role.
  - The body is: `pg_advisory_xact_lock(hashtext('sairn_ai_rl:'||p_app_id))`, then count, then insert, all inside one
    function call.
  - `sairn_ai_rate_limit_log` has the columns the body uses (id, app_id, requested_at).
  - `default_transaction_isolation` = read committed. service_role has no rolconfig override.
  - **So the cap holds under the live settings: the race is closed.**
- **DRIFT: the live body is the PRE-2026-09-15 version.**
  - It has NO `transaction_isolation` guard (live def md5 `fe098da9…`).
  - The committed file (`5b4410f10`, 2026-09-15) adds a guard that raises under repeatable read or serializable.
  - Today that is harmless, because the isolation is read committed. If service_role's default isolation is ever
    changed, the cap over-runs silently with the lock working.
  - **Fix: Michael re-runs `sql/sairn_ai_rate_limit_consume_fn.sql`. It is `create or replace` and idempotent.**
    hank did not apply production DDL.
- The other project (`SAIRN`, ohzqfwndmuowbswpbxxp) timed out on connect. That is a labelled error, and the function
  was not looked for there.

## 5. fx@example.invalid SCAN — this clone only
- **Method:** fx-authored commits on all refs (1631), intersected with commits this clone's reflog shows it CREATED
  (commit, amend, merge, or a rebase pick/continue). The reflog reaches back to 2026-09-28.
- **426 fx-authored commits were created in SAIRN-hank**, from 2026-10-07 (`ab758c004`) to 2026-10-28 07:27
  (`a4afe6535`, "hank releases sql"). 412 are on origin/main. The rest are rebased-away originals.
- **None since:** all 90 commits created here after `a4afe6535` are authored mikied68. The b59 identity fix holds.
- History is NOT rewritten. That would be a force push on a shared branch, and it needs Michael's decision.
- **Not hank's:** `79c4f10cf` (push_retry, 14:17) was not created in this clone.
- Nothing in the cody or fourth clones was touched.

## 6. CLAIMS HELD
None.

## 7. OPEN
| # | open | owner | next step |
|---|---|---|---|
| J1 | the next SAIRNlaw jurisdiction | Michael decides | pick a never-gated one (AK, ND, RI, SD, VT, WY, DC), or a blocker to resolve, then gate it before seeding |
| A1 | run sql/alf-audit-owner-recovery.sql | Michael | unchanged; this batch did not write a duplicate |
| D1 | the live rate-limit RPC lacks the isolation guard | Michael | re-run `sql/sairn_ai_rate_limit_consume_fn.sql` |
| H1 | 426 historical fx-authored hank commits | Michael decides | leave them (recommended: rewriting shared history means a force push), or record them in the identity ledger |
| T1, P1, R1, G1, U1 | carried from b60 | as before | unchanged |

## 8. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\58897a7d-eff3-428b-8fec-18274a858ae9.jsonl
