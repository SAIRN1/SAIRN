# The cron collision: the fix landed 12 days ago, and nobody read the answer it asked for

**2026-09-26 (Hank).** Dispatched to stagger `/api/sairndental/send-reminder` and
`/api/alf-alerts` off an identical `0 * * * *`. **They are not on it.** The
premise is 12 days stale, and the genuinely outstanding work was something else.

## What `vercel.json` actually holds

    /api/sairndental/send-reminder    7 * * * *
    /api/alf-alerts                 37 * * * *
    /api/cron-watchdog              15 * * * *
    /api/audit-checkpoint           30 3 * * *

Thirty minutes apart, neither at `:00`, landed **2026-09-14 in `b162c871`** —
`fix(cron): two hourly jobs fired at the same minute and both failed a third of
their runs`. That commit's analysis is the dispatch's analysis, from the same
production table: 23 `send-reminder` 504s, 20 `alf-alerts` 504s, 11
`/api/claude` rate-limit RPC 504s, **every one at `:00`**, over seven days. It
identified the mechanism as a shared Supabase project rather than a call path —
*"NEITHER cron calls /api/claude"* — and shipped in-code jitter as well as a
different minute, because a fixed minute fixes two crons and not the fifth one
somebody types by hand later. `api/_lib/cron-jitter.js`, called from both, after
the auth and config gates and before the first backend read.

## The part that WAS outstanding

**That commit set a falsifiable test and nobody ever read the result.** Its own
words:

> CAUSATION IS NOT ESTABLISHED, and the change is shaped so the next week of logs
> answers it: if the failures MOVE WITH THE SCHEDULE the collision was the cause;
> if they STAY AT :00, something else spikes at the top of the hour — Vercel's own
> cron dispatch, a Supabase maintenance window — and this was the wrong fix,
> cheaply.

A prediction with a stated refutation condition, twelve days old, unread. So it
was read.

## The answer, from the live table the commit quoted

`mcp__claude_ai_Vercel__get_runtime_errors`, project `prj_bj475nKLxC1TTmpFU6j7HVCSMEhn`,
`since=7d`, 2026-09-27:

    1 error group, most frequent first:
      DeprecationWarning: `url.parse()` ... count=32  routes=/api/bridge, /api/network

**One group, and it is a deprecation notice on two unrelated routes.** No
`send-reminder` 504. No `alf-alerts` facility-sweep 504. No `/api/claude`
rate-limit RPC 504. **54 failures in seven days became zero.**

The failures did not stay at `:00` and they did not move to `:07` and `:37`
either — they stopped. **The collision was the cause.** The commit's hypothesis is
confirmed, by the same aggregation it was measured against, which is what makes
the two figures comparable rather than merely both true.

## What this does not claim

- **Zero in the error table is not zero failures in the world.** It is zero in the
  pre-aggregated runtime-error grouping over a 7-day window, which is the same
  instrument that produced the 54. A failure shape that does not reach that table
  would not appear in either number.
- **It does not say the jitter is what did it**, only that the pair no longer
  collides. The commit changed the minute AND added the wait in the same landing,
  so this measurement cannot separate them — and does not need to, because the
  next cron somebody adds is the case the jitter exists for.
- **Nothing in `vercel.json` changed today.** The correct action for a dispatch
  whose premise is already satisfied is to read the open question behind it, not
  to re-apply the fix.
