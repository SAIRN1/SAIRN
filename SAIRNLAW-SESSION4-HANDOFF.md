# SAIRN — SAIRNlaw Session 4 Handoff

Written at natural stopping point (end of session), 2026-08-17.
Claims below are independently verified against the actual repo/live
site, not assumed from memory — same standard as prior sessions in
this series (Sessions 1-3).

## 1. Verified current state

- `origin/main` HEAD: `26b2ad1f29a4ba475cd174659d0e424eb4801d86` —
  confirmed via `git rev-parse origin/main`, cross-checked against local
  `git rev-parse HEAD` (identical, nothing unpushed).
- `sql/sairnlaw_trust_disbursement_atomic_check.sql` has been run in
  Supabase — confirmed via Michael's real screenshot ("Success. No rows
  returned") AND independently live-verified via curl (not trusted from
  the screenshot alone): a fresh `TR-RETRY-TEST2` disbursement, then a
  retry of the same `trusttx_id`, both returned identical real data
  (same `created_at` timestamp), and a follow-up read confirmed exactly
  one row exists.
- Live-verified against `sairn.vercel.app/api/sd-data` with the
  `LAW-TEST-2026` test license: the full concurrency test (below), all 5
  final-review fixes, and the retry-echo follow-up fix — all real HTTP
  round trips against production, not simulated.

## 2. Commits this session, in order

- `29b5ecc` — SQL: `law_check_and_insert_disbursement` (advisory-lock
  atomic check-and-write function), `amount`/`type`/`status` promoted to
  real columns on `law_trusttx` with backfill + constraints
- `786f333` — fix: reject NULL/non-positive `amount` in the atomic
  function (found in Task 1's own task-review, before this ever shipped)
- `f1c2e05` — feat: `api/sd-data.js` routes new Disbursement writes
  through the atomic function; Deposits/voids keep the unchanged plain
  upsert from step 1
- `bc56913` — feat: `sairnlaw.html` rolls back the optimistic local write
  when the server genuinely rejects a disbursement (structured
  `{rejected:true,...}` return from `sdnData()`, scoped to one error code
  only, verified not to affect any of the ~29 other `sdnData()` callers)
- `751e1bc` — fix: final whole-branch review's 5 Important findings
  (retry-idempotency bypass, negative-balance shown as positive, missing/
  wrong `type` bypassing validation entirely, plain-upsert path
  misclassifying real constraint violations as "not provisioned", and an
  inconsistent success response shape between the two write paths)
- `9aed952` — fix: a follow-up gap found while live-verifying commit
  `751e1bc`'s retry-idempotency fix — the fix correctly stopped false
  rejections, but the retry's HTTP response echoed `data:null` instead of
  the real transaction (stored data was always intact; only the response
  body was wrong). Restructured the function to a single unified
  `return v_row;` instead of two separate return sites.
- `26b2ad1` — docs: logged one more edge case found during `9aed952`'s own
  re-review to `SAIRN-BACKLOG.md` rather than fixing it (see §4)

**The real concurrency test** (the actual bug this whole session exists to
fix): two simultaneous `$500` disbursement requests against a client with
exactly `$500` real balance — exactly one succeeded, the other got a real
`409 INSUFFICIENT_TRUST_BALANCE`. Confirmed via a follow-up read that only
one row actually landed in the database, not just trusting the two HTTP
responses.

## 3. What was CORRECTED, not just added

- **A real, uncaught process gap: commits sat unpushed for an entire
  review cycle.** Tasks 1-3 (`29b5ecc` through `bc56913`) were committed
  locally but never pushed — the subagent-driven-development loop commits
  per task but doesn't push per task, and no push happened until Task 4's
  live-verification step, where a file 404'd on GitHub despite being
  "confirmed" present via local `git ls-files` (which only proves local
  tracked state, says nothing about origin). Caught because Michael
  pushed back explicitly rather than accepting the confirmation ("verify
  against origin specifically, not just local"). Fixed by `git fetch` +
  `git ls-tree origin/main` (the real check) before trusting any
  "this file exists" claim again this session.
- **The spec's retry-idempotency claim was wrong, and shipped that way
  once already.** The original design spec (step 2's own spec doc)
  asserted a network retry of the same `trusttx_id` was already safe via
  `on conflict do nothing` — final review found this false (the balance
  check ran before the conflict check, so a genuine retry of an
  already-committed disbursement could be wrongly rejected, and the new
  client-side rollback would then delete a real, already-committed
  transaction from local storage on that false rejection). Fixed in
  `751e1bc`; the fix itself then had its own follow-up correction in
  `9aed952` (see above) — two real corrections on the same underlying
  claim, not one.
- **"Already re-run" was asked and trusted with real verification this
  time, not assumed** — same discipline as step 1's Session 3 handoff,
  which explicitly flagged getting burned by trusting a verbal
  confirmation once. This session, every "confirm you've run the
  migration" answer was followed by an independent live curl check before
  proceeding, and one of those checks (the very first, pre-push) correctly
  caught the file not existing on origin yet.

## 4. Open items, prioritized

1. **Cross-client `trusttx_id` collision race** (logged `SAIRN-BACKLOG.md`,
   2026-08-17 entry): `law_check_and_insert_disbursement`'s
   `on conflict (license_hash, trusttx_id) do nothing` has no `client_id`
   in its conflict target; the advisory lock only serializes same-client
   calls. Two different clients somehow generating the identical
   `trusttx_id` (client-generated via `newId('TR')`, timestamp+random)
   could hit this — effectively unreachable in practice, genuinely lower
   risk class than the retry-idempotency bug already fixed this session,
   not chased into another fix round.
2. **Voiding a deposit that already has disbursements against it is still
   unguarded** (carried from step 1's own disclosed gap, logged
   `SAIRN-BACKLOG.md` 2026-08-16 entry, unchanged by this session) — a
   different failure mode (single-actor, reason-required audit action)
   from the cross-device race this session closed.
3. **Client-side reads for `law_clients`/`law_matters`/`law_trusttx` are
   still unwired** (carried from step 1's final review, unchanged) —
   writes are real server-sync; reads are still 100% localStorage. Not
   touched by step 2, which only added the atomic write-time check.
4. No further work is currently planned on this feature beyond the two
   backlog items above — step 2 was the last piece of the originally
   scoped "trust disbursement server-sync" work (step 1: durability, step
   2: atomicity).

## 5. Standard verification reminder for whoever reads this next

Verify main HEAD, verify branch, re-run relevant checks before trusting
any claim in this document — including this one. In particular: verify
against `origin/main` directly (`git fetch` + `git ls-tree`/`git log
origin/main`), not local `git log`/`git ls-files` alone — that exact gap
cost real time this session.
