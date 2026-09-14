// api/_lib/cron-jitter.js
// A bounded random delay at the START of a scheduled job, so two jobs that
// share a minute do not arrive at the same backend in the same instant.
//
// ── WHY, AND IT IS A MEASUREMENT RATHER THAN A PRECAUTION (2026-09-14) ─────
// `/api/sairndental/send-reminder` and `/api/alf-alerts` were both scheduled
// `0 * * * *` -- the identical minute, every hour. Vercel's runtime-error
// table over the preceding seven days:
//
//   send-reminder: dnt_appointments list failed 504   count=23
//     first 2026-09-12T00:00:29Z   last 2026-09-14T12:00:29Z
//   alf-alerts: facility sweep read failed, HTTP 504  count=20
//     first 2026-09-12T04:00:43Z   last 2026-09-14T13:00:43Z
//   ai rate limit: atomic RPC failed, HTTP 504        count=11  (/api/claude)
//     last 2026-09-14T10:00:51Z
//
// EVERY ONE OF THEM AT :00. About a third of the hourly runs of both jobs were
// failing -- appointment reminders not sent, medication-exception alerts not
// computed -- and the third line is /api/claude's Supabase rate-limit RPC
// timing out in the same minute, which is the 504 pattern that was open and
// unexplained.
//
// THE MECHANISM IS SHARED SUPABASE, NOT A CALL PATH, and the difference
// matters because the obvious reading is wrong. NEITHER cron calls /api/claude:
// read them and they call Supabase and Resend and nothing else. What they share
// with /api/claude is the Supabase project -- /api/claude does a licence
// validation and a rate-limit RPC against it before it ever reaches Anthropic.
// So this is contention on a common backend, not one job calling another.
//
// ── WHAT THIS DOES AND DOES NOT PROVE ─────────────────────────────────────
// The correlation is strong and the mechanism is plausible. It is NOT proven,
// and the change is deliberately shaped so the next week of logs answers it:
// the schedules move off :00, so if the failures MOVE WITH THEM the collision
// was the cause, and if they STAY AT :00 something else spikes at the top of
// the hour -- Vercel's own cron dispatch, a Supabase maintenance window -- and
// this was the wrong fix, cheaply. Recorded here rather than in a commit
// message because the reading happens later, by somebody else.
//
// ── WHY JITTER AND NOT JUST A DIFFERENT FIXED MINUTE ──────────────────────
// A fixed minute fixes THIS pair and nothing else: the next cron added to
// vercel.json will be typed by hand and can land on an occupied minute again,
// silently. A random offset means two jobs that DO share a minute still arrive
// seconds apart, and it decorrelates from anything outside this account that
// also fires on the hour. The schedule spread does the bulk of the work; this
// is the part that keeps working when somebody adds a fifth cron.
//
// ── THE BOUND IS SMALL ON PURPOSE, AND THE REASON IS HONEST ───────────────
// This burns WALL CLOCK inside a serverless invocation. `vercel.json` declares
// no `functions` block, so these run on the account default maxDuration and
// this file does NOT know what that is -- so the bound is kept far below any
// plausible limit rather than tuned against one. If a future change raises the
// jitter, establish the real maxDuration first; a delay that eats the budget
// turns a contention problem into a hard timeout, which is worse.
//
// Set SAIRN_CRON_JITTER_MS=0 to disable it entirely without a deploy.

const DEFAULT_MAX_MS = 20000;

// Milliseconds to wait, resolved from the environment. Anything unparseable or
// negative falls back to the default rather than to zero: a typo in an env var
// should not silently turn the mitigation off, which is the shape of failure
// this platform keeps writing down.
function jitterMs(maxMs) {
  const raw = process.env.SAIRN_CRON_JITTER_MS;
  let cap = (maxMs === undefined || maxMs === null) ? DEFAULT_MAX_MS : Number(maxMs);
  if (raw !== undefined && raw !== '') {
    const n = Number(raw);
    if (Number.isFinite(n) && n >= 0) cap = n;
  }
  if (!Number.isFinite(cap) || cap < 0) cap = DEFAULT_MAX_MS;
  return Math.floor(Math.random() * cap);
}

// Await this once, at the top of a scheduled handler, BEFORE its first backend
// read. Returns the number of milliseconds actually waited so the caller can
// report it -- a delay nobody can see is a delay nobody can rule out when the
// job is late.
async function jitter(maxMs) {
  const ms = jitterMs(maxMs);
  if (ms > 0) await new Promise((r) => setTimeout(r, ms));
  return ms;
}

module.exports = { jitter, jitterMs, DEFAULT_MAX_MS };
