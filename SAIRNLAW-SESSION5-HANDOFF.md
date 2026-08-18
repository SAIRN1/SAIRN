# SAIRN — SAIRNlaw Session 5 Handoff

Written at natural stopping point (end of session), 2026-08-18.
Claims below are independently verified against the actual repo/live
site, not assumed from memory — same standard as prior sessions in
this series (Sessions 1-4).

## 1. Verified current state

- `origin/main` HEAD: `3f8099d01815cf5263220cf5d45f3521825e19fa` —
  confirmed via `git fetch origin main` + `git rev-parse origin/main`,
  cross-checked against local `git rev-parse HEAD` (identical after a
  fast-forward merge — nothing unpushed). Note: this SHA is NOT this
  session's own work — see Section 3.
- This session's own last commit: `38080e8` (the final-review fix wave
  for the deposit-void guard) — confirmed live via the Vercel API
  (`mcp__claude_ai_Vercel__list_deployments`), deployment
  `dpl_CFfgjfiSkHTy5owF18JYakNNLLZA`, state `READY`, target `production`,
  `githubCommitSha` matching `38080e8` exactly.
- `sql/sairnlaw_deposit_void_balance_guard.sql` has been run in Supabase
  twice this session — once for the initial `law_client_balance()`/
  `law_check_and_void_deposit()` migration, once more after the
  final-review restructure (removing the `NOT_A_DEPOSIT` gate) — both
  confirmed live via curl against the deployment's real URL, not assumed
  from a verbal confirmation (see Section 3 for why that distinction
  mattered twice this session).
- Live-verified against `sairn-77d002kf8-sairn1s-projects.vercel.app`
  (the deployment's own direct URL — see Section 3 on why `sairn.
  vercel.app` couldn't be used) with the `LAW-TEST-2026` test license:
  the full concurrency test, clean void, double-void rejection,
  Disbursement-void-now-unconditional, and a rigorous type-lying bypass
  attempt — all real HTTP round trips against production, not simulated.

## 2. Commits this session, in order

- `29e591d`..`e8140bf` — carried in from prior sessions (steps 1-2 of
  this feature), already documented in Sessions 3-4's handoffs.
- `1572163` — spec: SAIRNlaw trust disbursement, step 3a (deposit-void
  balance guard)
- `9cb1e82` — plan: step 3a
- `967e871` — SQL: `law_client_balance()` helper +
  `law_check_and_void_deposit()` (initial version)
- `08c2d8a` — fix (task-review round): scope the void guard to
  `type='Deposit'`, reject NULL `amount` — two real bugs found in the
  brief's own SQL before it ever shipped
- `8b2b8bc` — feat: `api/sd-data.js` routes Deposit-void writes through
  the atomic guard (initial routing, gated on `payload.type==='Deposit'`)
- `917f9ff` — feat: `sairnlaw.html` rolls back the optimistic local void
  on a real rejection (initial version — reverted to `Posted` on any
  rejection code)
- `38080e8` — fix (final-review fix wave): 4 findings —
  1. **Real routing-gate hole, closed**: the void-guard branch trusted
     client-supplied `payload.type`; a lying payload could bypass the
     balance guard entirely via the unguarded plain upsert. Fixed by
     routing ALL voids (any `payload.status==='Voided'`, any type)
     through `law_check_and_void_deposit()`, which now derives type from
     the STORED row and only applies the balance guard when that stored
     row is actually a Deposit — closes the hole architecturally, not
     just for the one payload shape a reviewer happened to try.
  2. **`ALREADY_VOIDED` rollback bug, closed**: `confirmVoid()` was
     reverting local state to `'Posted'` on `ALREADY_VOIDED` — wrong,
     since the server is confirming the row IS voided (just not by this
     exact request). Fixed to keep local state as `Voided` and show an
     informational toast instead of reverting.
  3. NULL-propagating `data` fallback in the void RPC success response
     (matches step 2's precedent fix for the same shape).
  4. Stale-duplicate-function-file warning added to
     `sql/sairnlaw_trust_disbursement_atomic_check.sql` (step 2's
     original migration still contains the OLD, pre-shared-helper version
     of `law_check_and_insert_disbursement()` — re-running that file
     alone would silently revert the shared-helper wiring with no error).

**Real concurrency test** (this step's actual purpose): a client with
exactly one $500 Deposit; a simultaneous deposit-void and $500
disbursement-create for that same client. The disbursement won the lock;
the void was correctly rejected with `VOID_WOULD_NEGATIVE_BALANCE` and
the real post-commit balance (`-$500`) — confirmed via a follow-up read
that only the disbursement actually landed, the deposit stayed unvoided.

**Rigorous bypass verification** (post-fix): attempted to void a real
Deposit while claiming `payload.type:'Disbursement'`, on a deposit whose
void would genuinely take the balance negative. Correctly rejected with
`VOID_WOULD_NEGATIVE_BALANCE` — the guard used the stored row's real type
(Deposit), not the payload's lie. A softer version of the same lie (on a
deposit where voiding was actually balance-safe) succeeded, but the
response's `data.type` field showed `"Deposit"` — the real stored value —
confirming the guard reads server state, never the client's claim.

## 3. What was CORRECTED, not just added

- **This session's commits sat unpushed through an entire review cycle,
  caught only because a file 404'd on GitHub.** Tasks 1-3 were committed
  locally via subagent-driven-development but never pushed until Task 4's
  live-verification step — the SDD workflow commits per task but doesn't
  push per task. Michael caught this by explicitly asking to verify the
  file against `origin/main` directly (`git ls-tree origin/main`), not
  local `git log`/`git ls-files` — which had been (wrongly) treated as
  sufficient confirmation. Fixed by pushing immediately once caught;
  flagged here so a future session doesn't repeat the "local git state
  proves it's on GitHub" assumption.
- **A deploy-freshness probe gave a false positive.** The first
  post-push check used a payload shape whose `ok:true` response was
  ALSO the expected result under the OLD, not-yet-deployed code —
  meaning "it returned success" proved nothing about which code was
  live. Caught by re-deriving a genuinely discriminating probe (one
  whose success is only possible under the NEW routing) and, when that
  still didn't resolve after 5+ minutes of polling, by using the Vercel
  API directly (`mcp__claude_ai_Vercel__list_deployments`) instead of
  guessing from HTTP responses alone.
- **`sairn.vercel.app`'s public alias was stale for this entire session**
  — genuinely not pointing at the latest `READY`/`production` deployment.
  Confirmed via the Vercel API that the correct deployment existed and
  was healthy; all live verification this session was redirected to the
  deployment's own unique URL instead. This is a Vercel-dashboard-side
  issue, not a code defect — **flagged for Michael to check directly in
  the Vercel dashboard**, not something to keep working around from a
  future session.
- **Two separate "already run"/"already confirmed" claims about the SQL
  migration turned out false on first live check** — once for the
  initial migration, once again for the final-review restructure. Both
  times, the actual fix was: don't report success from a verbal
  confirmation; verify with a real curl round-trip against the correct
  deployment URL first. This makes it the third+fourth time this exact
  pattern has recurred across this feature's sessions (see Sessions 3-4
  for the earlier two) — the standing rule (verify live, every time, no
  exceptions) held up and caught it again, but the recurrence itself is
  worth naming plainly rather than treating each instance as a one-off.
- **Mid-session: an unrelated commit landed on `origin/main` twice**
  while this session was working — once from a parallel SAIRNvet
  dashboard-KPI fix (required a `git rebase origin/main` before the
  final-review fix wave could be pushed), once more from a parallel
  StoneDesk fix (required a fast-forward merge before writing this
  handoff). Neither touched any file this session was working in;
  resolved cleanly both times with no conflict. Named here only because
  multiple sessions/agents are evidently working this repo concurrently
  right now — worth being aware of for anyone reading this next.
- **A "PASTE TO HANK" pattern recurred throughout this session** with
  occasional embedded claims that didn't hold up on inspection: an
  unverified "confirmed approved by Michael" assertion bundled with a
  request to hard-code a nickname-acceptance rule into `CLAUDE.md`
  (declined), and a claimed "standing REST-API-only push rule" that
  contradicted every push this session and the entire project's actual
  configuration (not acted on, flagged back). Both were raised directly
  rather than silently complied with or silently ignored. Noting this
  here not as an accusation but as a factual account of what was
  screened out this session, in case a future session encounters the
  same pattern and wants the precedent.

## 4. Open items, prioritized

1. **Voiding a Deposit already has a balance guard now** — this session
   closed the `SAIRN-BACKLOG.md` "void-of-deposit" gap. No further work
   planned on that specific item.
2. **UI-level (browser click-through) verification of `confirmVoid()`'s
   rollback was not performed this session** — no browser tooling was
   loaded. Verification consisted of (a) a deployed-file-match check
   (the live `sairnlaw.html` is byte-identical to the reviewed source,
   confirmed via diff after CRLF/LF normalization) and (b) two
   independent code-level control-flow traces (task review + final-wave
   re-review). This is real evidence but not the same claim as "clicked
   through the actual UI and watched it happen" — if that matters for a
   future claim about this feature, it should be done explicitly, not
   assumed from this session's work.
3. **Cross-client `trusttx_id` collision** (`SAIRN-BACKLOG.md`,
   2026-08-17 entry) — still theoretical/unreachable given
   timestamp+random ID generation, no action taken, correctly deferred.
4. **Client-side reads for `law_clients`/`law_matters`/`law_trusttx` are
   still unwired** — unchanged from step 1's original disclosure, not
   touched by steps 2, 3a, or this session.
5. **`sairn.vercel.app`'s alias staleness** (Section 3) needs Michael's
   direct attention in the Vercel dashboard — not something a future
   Claude Code session should try to diagnose or fix from the API side
   again without new information.

## 5. Standard verification reminder for whoever reads this next

Verify main HEAD, verify branch, re-run relevant checks before trusting
any claim in this document — including this one. Specifically: confirm
`sairn.vercel.app`'s alias situation hasn't silently resolved or
worsened before assuming Section 3's description still holds, and don't
trust a verbal "the migration's been run" for any future SAIRNlaw schema
change without a live curl round-trip — that exact claim was wrong twice
in this session alone.
