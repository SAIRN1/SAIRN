// api/cron-watchdog.test.js
//
// Run:  node api/cron-watchdog.test.js
//
// Control for item 54 -- the thing that notices a scheduled job stopped.
//
// THE ARM THAT MATTERS IS THE DRIFT ARM, not the staleness arithmetic.
// EXPECTED_JOBS is a hand-written list and vercel.json is the real schedule.
// A job added to the schedule and not to the list would be UNWATCHED and
// nothing would say so -- the watchdog would report a clean sweep while a job
// nobody monitors quietly died. So the two lists are asserted equal in BOTH
// directions, against the real vercel.json, every run.
//
// A WATCHDOG IS THE EASIEST THING ON THIS PLATFORM TO GET VACUOUSLY GREEN. It
// reports "all ok" when everything is healthy AND when it is looking at
// nothing at all, and those two outputs are identical. So every arm below that
// asserts ok is paired with one that makes the same code say something else.
//
// THE STALENESS ARMS USE A FIXED CLOCK. assess() takes `nowMs` as a parameter
// precisely so this file never has to sleep, and so a slow test machine cannot
// turn a healthy fixture into a LATE one.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const W = require('./cron-watchdog.js');
const HB = require('./_lib/heartbeat.js');

let pass = 0, fail = 0;
const queue = [];
function t(name, fn) { queue.push([name, fn]); }
function section(s) { queue.push([s, null]); }

const NOW = Date.UTC(2026, 8, 14, 12, 0, 0);
const ago = (sec) => new Date(NOW - sec * 1000).toISOString();
function hb(job, ageSec, outcome, interval) {
  return {
    job: job, last_run_at: ago(ageSec), outcome: outcome || 'ok',
    detail: null, expected_interval_seconds: interval || W.EXPECTED_JOBS[job] || 3600
  };
}
const ALL_FRESH = () => Object.keys(W.EXPECTED_JOBS).map((j) => hb(j, 60));
const find = (rep, job) => rep.filter((x) => x.job === job)[0];

// ── 1. THE DRIFT ARM ───────────────────────────────────────────────────────
section('1. the declared list and the real schedule');
{
  const vercel = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'vercel.json'), 'utf8'));
  const scheduled = (vercel.crons || []).map((c) => c.path).sort();
  const declared = Object.keys(W.EXPECTED_JOBS).sort();
  t('every scheduled cron is WATCHED', () => {
    const unwatched = scheduled.filter((p) => declared.indexOf(p) === -1);
    assert.deepStrictEqual(unwatched, [],
      'these run on a schedule and nothing watches them: ' + unwatched.join(', '));
  });
  t('...and every watched job is actually SCHEDULED', () => {
    const phantom = declared.filter((p) => scheduled.indexOf(p) === -1);
    assert.deepStrictEqual(phantom, [],
      'these are watched but not in vercel.json, so they would alarm forever: '
      + phantom.join(', '));
  });
  t('the list is not empty -- an empty one passes both arms above vacuously', () => {
    assert.ok(declared.length >= 3, 'only ' + declared.length + ' job(s) declared');
  });
  t('the watchdog watches ITSELF, or nothing records that it stopped', () => {
    assert.ok(W.EXPECTED_JOBS['/api/cron-watchdog'] > 0);
  });
}

// ── 2. the alarm sits tighter than the failure point ───────────────────────
section('2. the alarm, and the margin');
t('a beat from within the last interval is ok, not late', () => {
  const rep = W.assess(NOW, ALL_FRESH());
  assert.deepStrictEqual(rep.filter((x) => x.status !== 'ok'), []);
});
t('ONE FULL INTERVAL OLD IS STILL ok -- a beat lands at the END of a run', () => {
  const rows = ALL_FRESH();
  rows[0] = hb(rows[0].job, W.EXPECTED_JOBS[rows[0].job]);
  assert.strictEqual(find(W.assess(NOW, rows), rows[0].job).status, 'ok');
});
t('two intervals plus the grace is LATE', () => {
  const job = '/api/alf-alerts';
  const rows = ALL_FRESH().filter((r) => r.job !== job)
    .concat([hb(job, W.lateAfter(3600) + 1)]);
  assert.strictEqual(find(W.assess(NOW, rows), job).status, 'LATE');
});
t('three intervals plus the grace is DEAD, which is a different word on purpose', () => {
  const job = '/api/alf-alerts';
  const rows = ALL_FRESH().filter((r) => r.job !== job)
    .concat([hb(job, W.deadAfter(3600) + 1)]);
  assert.strictEqual(find(W.assess(NOW, rows), job).status, 'DEAD');
});
t('MARGIN IS REPORTED, not just the verdict', () => {
  const rep = W.assess(NOW, ALL_FRESH());
  const e = find(rep, '/api/alf-alerts');
  assert.strictEqual(typeof e.seconds_until_late, 'number');
  assert.ok(e.seconds_until_late > 0, 'a healthy job reported no headroom');
});
t('...and the margin goes negative exactly when the status turns', () => {
  const job = '/api/alf-alerts';
  const rows = ALL_FRESH().filter((r) => r.job !== job)
    .concat([hb(job, W.lateAfter(3600) + 10)]);
  const e = find(W.assess(NOW, rows), job);
  assert.ok(e.seconds_until_late < 0, 'LATE with positive headroom is incoherent');
});
t('the grace is not zero -- a cron fires on a schedule, not a stopwatch', () => {
  assert.ok(W.GRACE_SECONDS > 0);
});

// ── 3. the states that are NOT staleness ───────────────────────────────────
section('3. silence, failure and absence are three different things');
t('A JOB THAT NEVER BEAT IS FOUND, though it has no row to be stale', () => {
  const rows = ALL_FRESH().filter((r) => r.job !== '/api/audit-checkpoint');
  const e = find(W.assess(NOW, rows), '/api/audit-checkpoint');
  assert.strictEqual(e.status, 'NEVER_BEAT');
});
t('...and NEVER_BEAT is not reported as LATE -- a different fix entirely', () => {
  const rows = ALL_FRESH().filter((r) => r.job !== '/api/audit-checkpoint');
  const e = find(W.assess(NOW, rows), '/api/audit-checkpoint');
  assert.notStrictEqual(e.status, 'LATE');
  assert.ok(/never/i.test(e.why));
});
t('a job that RAN AND FAILED is FAILING, not late -- it is alive and unhappy', () => {
  const job = '/api/sairndental/send-reminder';
  const rows = ALL_FRESH().filter((r) => r.job !== job).concat([hb(job, 60, 'failed')]);
  assert.strictEqual(find(W.assess(NOW, rows), job).status, 'FAILING');
});
t('a partial run is PARTIAL, which is neither ok nor failed', () => {
  const job = '/api/sairndental/send-reminder';
  const rows = ALL_FRESH().filter((r) => r.job !== job).concat([hb(job, 60, 'partial')]);
  assert.strictEqual(find(W.assess(NOW, rows), job).status, 'PARTIAL');
});
t('SILENCE WINS OVER OUTCOME -- a dead job that last said "ok" is still DEAD', () => {
  const job = '/api/alf-alerts';
  const rows = ALL_FRESH().filter((r) => r.job !== job)
    .concat([hb(job, W.deadAfter(3600) + 1, 'ok')]);
  assert.strictEqual(find(W.assess(NOW, rows), job).status, 'DEAD');
});
t('a beating job nobody declared is reported, not ignored', () => {
  const rep = W.assess(NOW, ALL_FRESH().concat([hb('/api/ghost', 60, 'ok', 3600)]));
  const e = find(rep, '/api/ghost');
  assert.strictEqual(e.status, 'UNDECLARED');
});
t('every declared job appears in the report even when all are healthy', () => {
  const rep = W.assess(NOW, ALL_FRESH());
  assert.strictEqual(rep.length, Object.keys(W.EXPECTED_JOBS).length);
});

// ── 4. the handler: could-not-tell is never a clean sweep ──────────────────
section('4. the handler');
function makeRes() {
  const out = { code: null, body: null };
  return { out, status(c) { out.code = c; return this; }, json(b) { out.body = b; return this; } };
}
// ── THE CLOCK IS PINNED, AND IT WAS NOT (found 2026-09-14) ─────────────────
// These arms build heartbeats relative to the fixed NOW above, but the HANDLER
// calls the real Date.now(). So "a heartbeat 60 seconds old" aged with the wall
// clock: the suite passed while the machine's time was near 12:00 UTC on
// 2026-09-14 and went RED a few hours later, reporting every healthy fixture as
// DEAD. A test that passes in the morning and fails in the afternoon is worse
// than one that always fails -- it gets blamed on whatever was committed nearest
// to when somebody noticed.
//
// assess() already takes nowMs as a parameter for exactly this reason. The
// handler cannot, because a cron has a real clock, so the clock is stubbed here
// the way api/audit-checkpoint.test.js stubs it.
async function call(fetchImpl) {
  const realFetch = global.fetch;
  const realNow = Date.now;
  global.fetch = fetchImpl;
  Date.now = () => NOW;
  process.env.CRON_SECRET = 'secret';
  process.env.SUPABASE_URL = 'https://example.test';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'srv';
  const res = makeRes();
  try { await W({ headers: { authorization: 'Bearer secret' } }, res); }
  finally { global.fetch = realFetch; Date.now = realNow; }
  return res.out;
}
const reply = (status, text) => ({
  ok: status >= 200 && status < 300, status: status,
  text: async () => text, json: async () => JSON.parse(text)
});

t('a wrong bearer is refused', async () => {
  process.env.CRON_SECRET = 'secret';
  const res = makeRes();
  await W({ headers: { authorization: 'Bearer nope' } }, res);
  assert.strictEqual(res.out.code, 401);
});
t('A MISSING TABLE IS NOT "no stale jobs"', async () => {
  const out = await call(async () => reply(404, '{"code":"PGRST205","message":"does not exist"}'));
  assert.strictEqual(out.code, 503);
  assert.strictEqual(out.body.error.code, 'NOT_PROVISIONED');
});
t('...and it names the file and says NOTHING was checked', async () => {
  const out = await call(async () => reply(404, '{"code":"PGRST205"}'));
  assert.ok(/sql\/cron_heartbeat_schema\.sql/.test(out.body.error.message));
  assert.ok(/NOTHING was checked/.test(out.body.error.message));
});
t('an unreadable heartbeat read reports that, rather than a clean sweep', async () => {
  const out = await call(async () => reply(200, 'not json'));
  assert.strictEqual(out.code, 502);
  assert.ok(/nothing was checked/i.test(out.body.error.message));
});
// ── `ok` NOW INCLUDES "CAN THIS THING TELL ANYBODY", 2026-09-15 ───────────
// This arm used to pass with NO alert channel configured, which is how the
// production instance ran for a day answering 200 while every alert it planned
// ended "nobody was told". A healthy platform includes a usable channel, so the
// arm configures one -- and the arm immediately below is the other direction,
// without which this one would pass just as happily on a widened `ok` that had
// silently stopped checking anything.
const CHANNEL_VARS = ['SAIRN_OPS_EMAIL', 'RESEND_API_KEY', 'RESEND_FROM_EMAIL'];
function withChannel(on, fn) {
  const saved = CHANNEL_VARS.map((k) => [k, process.env[k]]);
  for (const k of CHANNEL_VARS) {
    if (on) process.env[k] = 'set-for-test';
    else delete process.env[k];
  }
  return Promise.resolve()
    .then(fn)
    .finally(() => {
      for (const [k, v] of saved) {
        if (v === undefined) delete process.env[k];
        else process.env[k] = v;
      }
    });
}
// ── THE WATCHDOG MUST REPORT ITS OWN FAILURE (added 2026-09-16) ──────────
// Two of its refusal paths returned 502 without beating. That is the same
// defect found the same day in api/audit-checkpoint.js and
// api/sairndental/send-reminder.js, and it is the WORST instance: NOTHING
// ELSE WATCHES THE WATCHDOG. This file is the only reader of the heartbeat
// table, and the row it writes about ITSELF is the only evidence the sweep
// ran -- so failing these two ways made the monitor go silent exactly when it
// was broken, and its own staleness check for /api/cron-watchdog is what
// would otherwise have caught that.
//
// `beats()` captures every POST to the heartbeat table so a beat can be
// OBSERVED. The arms below assert on that, not on the 502 -- Vercel throws a
// cron response body away and nobody reads it.
function beats(readReply) {
  const seen = [];
  const run = call(async (url, init) => {
    if (String(url).indexOf('sairn_cron_heartbeat?select=') !== -1) return readReply;
    seen.push(JSON.parse(init.body));
    return reply(201, '');
  });
  return run.then((out) => ({ out: out, beats: seen }));
}

t('A HEARTBEAT READ THAT FAILS STILL BEATS -- the monitor must not go silent '
  + 'when it is the broken one', async () => {
  const r = await beats(reply(502, 'upstream exploded'));
  assert.strictEqual(r.out.code, 502);
  assert.strictEqual(r.beats.length, 1, 'it refused without beating');
  assert.strictEqual(r.beats[0].job, '/api/cron-watchdog');
  assert.strictEqual(r.beats[0].outcome, 'failed');
  assert.strictEqual(r.beats[0].detail.error, 'HEARTBEAT_READ_FAILED');
  assert.strictEqual(r.beats[0].detail.checked, 0,
    'a run that checked nothing must not imply it checked something');
});

t('A NON-ARRAY READ STILL BEATS, and says so distinctly', async () => {
  const r = await beats(reply(200, '{"not":"an array"}'));
  assert.strictEqual(r.out.code, 502);
  assert.strictEqual(r.beats.length, 1, 'it refused without beating');
  assert.strictEqual(r.beats[0].detail.error, 'HEARTBEAT_READ_NOT_AN_ARRAY',
    'the two refusals must be told apart by more than their status code');
});

// THE ONE CASE WHERE NOT BEATING IS CORRECT, pinned so a later sweep does not
// "fix" it into a beat that cannot be written. The heartbeat table is the
// thing that is missing; beat() writes to that same table and would fail
// identically, so the console line and the 503 are the whole signal available.
t('NOT_PROVISIONED does NOT beat -- the table it would beat to is the missing '
  + 'one, and that is deliberate', async () => {
  const r = await beats(reply(404, JSON.stringify(
    { code: 'PGRST205', message: 'relation "sairn_cron_heartbeat" does not exist' })));
  assert.strictEqual(r.out.code, 503);
  assert.strictEqual(r.out.body.error.code, 'NOT_PROVISIONED');
  assert.strictEqual(r.beats.length, 0,
    'it tried to beat to the table it just reported absent');
});

// THE CONTROL. Without it every arm above is satisfied by a handler that beats
// on every path, including one that beats `failed` on a clean sweep.
t('CONTROL: a HEALTHY sweep beats too, and not as a failure', async () => {
  const r = await beats(reply(200, JSON.stringify(ALL_FRESH())));
  assert.strictEqual(r.out.code, 200);
  assert.strictEqual(r.beats.length, 1);
  assert.notStrictEqual(r.beats[0].outcome, 'failed',
    'a clean sweep is reporting itself as a failure');
  assert.strictEqual(r.beats[0].detail.error, undefined,
    'a clean sweep is reporting an error');
});

const healthy = () => call(async (url) => {
  if (String(url).indexOf('sairn_cron_heartbeat?select=') !== -1) {
    return reply(200, JSON.stringify(ALL_FRESH()));
  }
  return reply(201, '');         // the watchdog's own beat
});

t('a healthy table AND a configured channel answers ok:true', async () => {
  const out = await withChannel(true, healthy);
  assert.strictEqual(out.code, 200);
  assert.strictEqual(out.body.ok, true, JSON.stringify(out.body));
  assert.strictEqual(out.body.notify_channel.configured, true);
});
t('EVERY JOB HEALTHY BUT NO CHANNEL IS NOT ok -- it can tell nobody', async () => {
  const out = await withChannel(false, healthy);
  assert.strictEqual(out.code, 200);
  assert.strictEqual(out.body.ok, false, JSON.stringify(out.body));
  assert.strictEqual(out.body.notify_channel.configured, false);
  // ON ITS OWN AXIS. A reader must be able to tell "a job is down" from
  // "nobody can be told" -- they send you to completely different places.
  assert.deepStrictEqual(out.body.jobs.filter((j) => j.status !== 'ok'), []);
  assert.ok(out.body.notify_channel.missing.indexOf('SAIRN_OPS_EMAIL') !== -1);
});
t('the escalation address is reported separately, because its absence is not fatal', async () => {
  const out = await withChannel(true, healthy);
  // alertTo() falls back to SAIRN_OPS_EMAIL for an escalation, so a missing
  // SAIRN_ESCALATION_EMAIL changes WHO is told, not WHETHER anybody is. It
  // must not appear in `missing` or it would make a working channel read broken.
  assert.strictEqual(out.body.notify_channel.escalation_has_own_address, false);
  assert.strictEqual(out.body.notify_channel.missing.length, 0);
  assert.strictEqual(out.body.notify_channel.configured, true);
});
// -- THE FREEZE IS LOAD-BEARING, AND NOTHING PINNED IT UNTIL NOW ------------
// The arm above builds "fresh" heartbeats relative to the fixed NOW, so it is
// only deterministic because call() also freezes Date.now to NOW. Without that
// freeze the rows age against the real wall clock and the handler correctly
// answers DEAD: CC hit exactly that on 2026-09-14 and reported 54 passed,
// 1 failed. The freeze arrived in 7099d99f as a side effect of item 94's date
// work, which means the arm was repaired by a commit that was not about it --
// and NOTHING asserted the repair had to stay.
//
// Reproduced before writing this: removing the one freeze line reproduces
// 54 passed / 1 failed on that same arm, and the file restores byte-identical.
// This is the eighth discipline's exact shape -- nothing announces the day a
// check stops testing anything -- so the announcement is here.
t('THE HARNESS FREEZES THE CLOCK -- remove it and the arm above rots silently '
  + 'against the wall clock instead of failing on the code', async () => {
  let seen = null;
  await call(async (url) => {
    if (seen === null) seen = Date.now();
    if (String(url).indexOf('sairn_cron_heartbeat?select=') !== -1) {
      return reply(200, JSON.stringify(ALL_FRESH()));
    }
    return reply(201, '');
  });
  assert.strictEqual(seen, NOW,
    'Date.now() inside the handler was ' + seen + ', not the fixed NOW (' + NOW
    + '). Every fixture in this file is built relative to NOW, so an unfrozen '
    + 'clock makes them age in real time.');
});
t('CONTROL: the real clock is NOT frozen outside call(), so the arm above is '
  + 'asserting a property of the harness and not of the process', () => {
  assert.notStrictEqual(Date.now(), NOW);
});
t('A DEAD JOB MAKES THE HANDLER ANSWER ok:false -- the pair for the arm above', async () => {
  const rows = ALL_FRESH().filter((r) => r.job !== '/api/alf-alerts')
    .concat([hb('/api/alf-alerts', W.deadAfter(3600) + 1)]);
  const out = await call(async (url) => {
    if (String(url).indexOf('sairn_cron_heartbeat?select=') !== -1) {
      return reply(200, JSON.stringify(rows));
    }
    return reply(201, '');
  });
  assert.strictEqual(out.body.ok, false);
  assert.strictEqual(find(out.body.jobs, '/api/alf-alerts').status, 'DEAD');
});

// ── 4b. ITEM 55: the response, decided in advance ──────────────────────────
// planResponse() is PURE, so these arms need no fake at all -- which is why the
// decision half is where the coverage is. A planner driven through a mail
// provider would be tested the way the provider allows rather than the way the
// decision needs.
section('4b. the pre-planned response');
const CR = require('./_lib/cron-response.js');
const dead = (job) => ({ job: job, status: 'DEAD' });

t('EVERY status the watchdog can produce has a planned response', () => {
  // Derived from the source rather than hand-listed: a new status added to
  // assess() with no RESPONSE row is the drift this arm exists to catch, and a
  // hand-list here would go stale in exactly the same way.
  const src = fs.readFileSync(path.join(__dirname, 'cron-watchdog.js'), 'utf8');
  const produced = new Set();
  const re = /status = '([A-Z_]+)'|status: '([A-Z_]+)'/g;
  let m;
  while ((m = re.exec(src))) produced.add(m[1] || m[2]);
  const missing = [...produced].filter((s) => s !== 'ok' && !CR.RESPONSE[s]);
  assert.deepStrictEqual(missing, [],
    'these statuses can be produced and have no planned response: ' + missing.join(', '));
});
t('...and every planned response is for a status that can actually occur', () => {
  const src = fs.readFileSync(path.join(__dirname, 'cron-watchdog.js'), 'utf8');
  const phantom = Object.keys(CR.RESPONSE).filter((s) => src.indexOf("'" + s + "'") === -1);
  assert.deepStrictEqual(phantom, [], 'planned for but unreachable: ' + phantom.join(', '));
});
t('a NEW dead job is alerted AND retried once', () => {
  const p = CR.planResponse([dead('/api/alf-alerts')], {}, NOW);
  const kinds = p.actions.map((a) => a.action).sort();
  assert.deepStrictEqual(kinds, ['alert', 'retry']);
});
t('THE SAME DEAD JOB AN HOUR LATER IS SUPPRESSED, and not retried again', () => {
  const first = CR.planResponse([dead('/api/alf-alerts')], {}, NOW);
  const second = CR.planResponse([dead('/api/alf-alerts')], first.memo, NOW + 3600 * 1000);
  const kinds = second.actions.map((a) => a.action);
  assert.ok(kinds.indexOf('alert') === -1, 'it alerted twice in an hour');
  assert.ok(kinds.indexOf('retry') === -1, 'it retried a job it already retried');
  assert.ok(kinds.indexOf('suppressed') !== -1, 'the suppression was silent');
});
t('...and the suppression SAYS why and when the next one comes', () => {
  const first = CR.planResponse([dead('/api/alf-alerts')], {}, NOW);
  const second = CR.planResponse([dead('/api/alf-alerts')], first.memo, NOW + 3600 * 1000);
  const s = second.actions.filter((a) => a.action === 'suppressed')[0];
  assert.ok(/next alert after/.test(s.reason), s.reason);
});
t('after the re-alert window it DOES alert again -- suppression is not silence forever', () => {
  let memo = CR.planResponse([dead('/api/alf-alerts')], {}, NOW).memo;
  const later = NOW + (CR.REALERT_SECONDS + 60) * 1000;
  const p = CR.planResponse([dead('/api/alf-alerts')], memo, later);
  assert.ok(p.actions.some((a) => a.action === 'alert'), 'it went permanently quiet');
});
t('IT ESCALATES at the declared count, and only once', () => {
  let memo = {};
  let escalations = 0;
  for (let i = 0; i < 8; i++) {
    const p = CR.planResponse([dead('/api/alf-alerts')], memo, NOW + i * 3600 * 1000);
    escalations += p.actions.filter((a) => a.action === 'escalate').length;
    memo = p.memo;
  }
  assert.strictEqual(escalations, 1, 'escalated ' + escalations + ' times over 8 checks');
});
t('...at the threshold the table declares, not a number invented here', () => {
  let memo = {};
  let at = null;
  for (let i = 0; i < 8; i++) {
    const p = CR.planResponse([dead('/api/alf-alerts')], memo, NOW + i * 3600 * 1000);
    const e = p.actions.filter((a) => a.action === 'escalate')[0];
    if (e && at === null) at = e.count;
    memo = p.memo;
  }
  assert.strictEqual(at, CR.RESPONSE.DEAD.escalate_after);
});
t('RECOVERY CLEARS THE STREAK -- a job that comes back and dies again alerts again', () => {
  const first = CR.planResponse([dead('/api/alf-alerts')], {}, NOW);
  const recovered = CR.planResponse([{ job: '/api/alf-alerts', status: 'ok' }],
                                    first.memo, NOW + 3600 * 1000);
  assert.deepStrictEqual(recovered.actions, [], 'a healthy job produced an action');
  assert.deepStrictEqual(recovered.memo, {}, 'the streak survived a recovery');
  const again = CR.planResponse([dead('/api/alf-alerts')], recovered.memo, NOW + 7200 * 1000);
  assert.ok(again.actions.some((a) => a.action === 'alert'), 'the second outage was silent');
});
t('NEVER_BEAT is NOT retried -- re-invoking a never-deployed job cannot help', () => {
  const p = CR.planResponse([{ job: '/api/alf-alerts', status: 'NEVER_BEAT' }], {}, NOW);
  assert.ok(!p.actions.some((a) => a.action === 'retry'));
  assert.ok(p.actions.some((a) => a.action === 'alert'));
});
t('PARTIAL is NOT retried -- on an alert sweep a retry re-sends rather than fixes', () => {
  const p = CR.planResponse([{ job: '/api/alf-alerts', status: 'PARTIAL' }], {}, NOW);
  assert.ok(!p.actions.some((a) => a.action === 'retry'));
});
t('A STATUS WITH NO PLAN IS A FINDING, not silence', () => {
  const p = CR.planResponse([{ job: '/api/x', status: 'BRAND_NEW' }], {}, NOW);
  assert.strictEqual(p.actions[0].action, 'NO_PLAN');
});
t('two jobs in trouble each get their own action, not one merged alert', () => {
  const p = CR.planResponse([dead('/api/a'), dead('/api/b')], {}, NOW);
  assert.strictEqual(p.actions.filter((a) => a.action === 'alert').length, 2);
});

// ── 4b-bis. A MONITOR DOES NOT ACT ON ITSELF ───────────────────────────────
// Added 2026-09-15 from four hours of PRODUCTION logs, not from reading the
// code. `/api/cron-watchdog` is in its own EXPECTED_JOBS, and it was planning
// a retry against itself -- the running function invoking itself, answered by
// Vercel with HTTP 508 LOOP DETECTED at 21:15:29Z -- and latching itself
// FAILING for ever, because an undelivered alert wrote outcome `failed`, which
// it then read back next hour as evidence it was failing.
section('4b-bis. the watchdog does not respond to itself');
const SELF = '/api/cron-watchdog';
t('WITH NO selfJob, the old behaviour is unchanged -- alert AND retry', () => {
  // The control for every arm below. If this one ever goes green for the wrong
  // reason -- because planResponse stopped acting on ANYTHING -- the three
  // arms after it would pass while testing nothing at all.
  const p = CR.planResponse([{ job: SELF, status: 'FAILING' }], {}, NOW);
  assert.ok(p.actions.some((a) => a.action === 'alert'));
  assert.ok(p.actions.some((a) => a.action === 'retry'));
});
t('THE RETRY AGAINST ITSELF IS GONE -- that call was answered with HTTP 508', () => {
  const p = CR.planResponse([{ job: SELF, status: 'FAILING' }], {}, NOW, SELF);
  assert.deepStrictEqual(p.actions.filter((a) => a.action === 'retry'), []);
  assert.deepStrictEqual(p.actions.filter((a) => a.action === 'alert'), []);
  assert.deepStrictEqual(p.actions.filter((a) => a.action === 'escalate'), []);
});
t('...but it is REPORTED, not silently dropped', () => {
  const p = CR.planResponse([{ job: SELF, status: 'FAILING' }], {}, NOW, SELF);
  const self = p.actions.filter((a) => a.action === 'self');
  assert.strictEqual(self.length, 1);
  assert.strictEqual(self[0].job, SELF);
  assert.strictEqual(self[0].status, 'FAILING');
  assert.ok(self[0].reason, 'a self action with no reason is a silent drop wearing a label');
});
t('NO MEMO ENTRY for itself -- a streak counter nothing acts on reads as a pending escalation', () => {
  const p = CR.planResponse([{ job: SELF, status: 'FAILING' }], {}, NOW, SELF);
  assert.strictEqual(Object.prototype.hasOwnProperty.call(p.memo, SELF), false,
    JSON.stringify(p.memo));
});
t('THE LATCH IS BROKEN -- five consecutive runs produce no escalation and no growing count', () => {
  // The production shape exactly: FAILING every hour, for ever, because the
  // thing it was reporting was its own inability to send the report.
  let memo = {};
  for (let i = 0; i < 5; i++) {
    const p = CR.planResponse([{ job: SELF, status: 'FAILING' }], memo, NOW + i * 3600 * 1000, SELF);
    assert.deepStrictEqual(p.actions.filter((a) => a.action === 'escalate'), [],
      'escalated on run ' + i);
    memo = p.memo;
  }
  assert.deepStrictEqual(memo, {});
});
t('OTHER JOBS ARE STILL ACTED ON in the same report -- this is not a mute button', () => {
  const p = CR.planResponse([{ job: SELF, status: 'FAILING' }, dead('/api/alf-alerts')],
                            {}, NOW, SELF);
  assert.strictEqual(p.actions.filter((a) => a.action === 'alert').length, 1);
  assert.strictEqual(p.actions.filter((a) => a.action === 'alert')[0].job, '/api/alf-alerts');
  assert.ok(p.actions.some((a) => a.action === 'retry' && a.job === '/api/alf-alerts'));
  assert.ok(p.memo['/api/alf-alerts']);
});
t('a HEALTHY self row still produces no self action -- ok drops out before the check', () => {
  const p = CR.planResponse([{ job: SELF, status: 'ok' }], {}, NOW, SELF);
  assert.deepStrictEqual(p.actions, []);
});
t('the endpoint passes its OWN job id, not a retyped string', () => {
  // The exclusion is worthless if the endpoint and EXPECTED_JOBS disagree about
  // how the route is spelled, and a second spelling is exactly how a
  // self-exclusion silently stops excluding.
  assert.ok(Object.prototype.hasOwnProperty.call(W.EXPECTED_JOBS, SELF),
    'EXPECTED_JOBS no longer contains ' + SELF + ' -- the arms above test nothing');
});

section('4c. delivery, and the rule that an undelivered alert is not handled');
t('WITH NO DESTINATION CONFIGURED, an alert is delivered:false -- never skipped', async () => {
  const keepOps = process.env.SAIRN_OPS_EMAIL;
  delete process.env.SAIRN_OPS_EMAIL;
  delete process.env.SAIRN_ESCALATION_EMAIL;
  try {
    const out = await W.executeActions([{ job: '/api/a', status: 'DEAD', action: 'alert', reason: 'x' }]);
    assert.strictEqual(out[0].delivered, false);
    assert.ok(/SAIRN_OPS_EMAIL/.test(out[0].detail.error));
    assert.ok(/nobody was told/.test(out[0].detail.error));
  } finally { if (keepOps) process.env.SAIRN_OPS_EMAIL = keepOps; }
});
t('a SUPPRESSED action carries no `delivered` key, so it cannot count as undelivered', async () => {
  const out = await W.executeActions([{ job: '/api/a', status: 'DEAD', action: 'suppressed', reason: 'x' }]);
  assert.ok(!('delivered' in out[0]), 'a suppression was counted as a delivery outcome');
});
t('a retry with no base URL is delivered:false and SAYS there is no address', async () => {
  const keepBase = process.env.SAIRN_BASE_URL, keepVercel = process.env.VERCEL_URL;
  delete process.env.SAIRN_BASE_URL; delete process.env.VERCEL_URL;
  try {
    const out = await W.executeActions([{ job: '/api/a', status: 'DEAD', action: 'retry', reason: 'x' }]);
    assert.strictEqual(out[0].delivered, false);
    assert.ok(/no address to retry against/.test(out[0].detail.error));
  } finally {
    if (keepBase) process.env.SAIRN_BASE_URL = keepBase;
    if (keepVercel) process.env.VERCEL_URL = keepVercel;
  }
});
t('escalation prefers the escalation address and falls back to ops, not to nobody', () => {
  const keepOps = process.env.SAIRN_OPS_EMAIL, keepEsc = process.env.SAIRN_ESCALATION_EMAIL;
  try {
    process.env.SAIRN_OPS_EMAIL = 'ops@x.test';
    delete process.env.SAIRN_ESCALATION_EMAIL;
    assert.strictEqual(W.alertTo(true), 'ops@x.test');
    process.env.SAIRN_ESCALATION_EMAIL = 'boss@x.test';
    assert.strictEqual(W.alertTo(true), 'boss@x.test');
    assert.strictEqual(W.alertTo(false), 'ops@x.test');
  } finally {
    if (keepOps) process.env.SAIRN_OPS_EMAIL = keepOps; else delete process.env.SAIRN_OPS_EMAIL;
    if (keepEsc) process.env.SAIRN_ESCALATION_EMAIL = keepEsc; else delete process.env.SAIRN_ESCALATION_EMAIL;
  }
});
t('AN UNDELIVERED RESPONSE MAKES THE WHOLE RUN ok:false, even though detection worked', async () => {
  const keepOps = process.env.SAIRN_OPS_EMAIL;
  delete process.env.SAIRN_OPS_EMAIL;
  delete process.env.SAIRN_ESCALATION_EMAIL;
  const rows = ALL_FRESH().filter((r) => r.job !== '/api/alf-alerts')
    .concat([hb('/api/alf-alerts', W.deadAfter(3600) + 1)]);
  try {
    const out = await call(async (url) => {
      if (String(url).indexOf('sairn_cron_heartbeat?select=') !== -1) {
        return reply(200, JSON.stringify(rows));
      }
      return reply(201, '');
    });
    assert.strictEqual(out.body.ok, false);
    assert.ok(out.body.actions.some((a) => a.delivered === false),
      'the run reported ok while nobody had been told');
  } finally { if (keepOps) process.env.SAIRN_OPS_EMAIL = keepOps; }
});

// ── 5. the heartbeat writer's contract ─────────────────────────────────────
section('5. beat() must never be the thing that breaks a job');
t('a beat with no job name is REFUSED, not defaulted', async () => {
  assert.strictEqual(await HB.beat({ outcome: 'ok', expected_interval_seconds: 60 }), false);
});
// BEHAVIOURAL, NOT A GREP FOR THE COMMENT. The first version of this arm
// matched the prose in heartbeat.js explaining WHY there is no default, and
// broke when that sentence wrapped onto a second line -- an assertion about a
// paragraph rather than about the code, which would also have passed against a
// file whose comment was right and whose behaviour was wrong.
t('...and an incomplete beat issues NO REQUEST AT ALL, rather than a defaulted one', async () => {
  const realFetch = global.fetch;
  let calls = 0;
  global.fetch = async () => { calls++; return { ok: true, status: 201, text: async () => '' }; };
  process.env.SUPABASE_URL = 'https://example.test';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'srv';
  try {
    await HB.beat({ outcome: 'ok', expected_interval_seconds: 60 });          // no job
    await HB.beat({ job: '/x', expected_interval_seconds: 60 });              // no outcome
    await HB.beat({ job: '/x', outcome: 'ok' });                              // no interval
    assert.strictEqual(calls, 0, 'an incomplete beat reached the database');
    // ...and the CONTROL, or the arm above passes against a beat() that never
    // writes anything at all.
    assert.strictEqual(await HB.beat({ job: '/x', outcome: 'ok', expected_interval_seconds: 60 }), true);
    assert.strictEqual(calls, 1, 'a COMPLETE beat did not reach the database');
  } finally { global.fetch = realFetch; }
});
t('a beat writes the job name it was given, never a substitute', async () => {
  const realFetch = global.fetch;
  let sent = null;
  global.fetch = async (url, init) => { sent = JSON.parse(init.body); return { ok: true, status: 201, text: async () => '' }; };
  process.env.SUPABASE_URL = 'https://example.test';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'srv';
  try {
    await HB.beat({ job: '/api/alf-alerts', outcome: 'partial', expected_interval_seconds: 3600 });
    assert.strictEqual(sent.job, '/api/alf-alerts');
    assert.strictEqual(sent.outcome, 'partial');
    assert.strictEqual(sent.expected_interval_seconds, 3600);
  } finally { global.fetch = realFetch; }
});
t('an unknown outcome is refused -- the schema CHECK would reject it anyway', async () => {
  assert.strictEqual(await HB.beat({ job: '/x', outcome: 'fine', expected_interval_seconds: 60 }), false);
});
t('a missing interval is refused -- the watchdog cannot judge without one', async () => {
  assert.strictEqual(await HB.beat({ job: '/x', outcome: 'ok' }), false);
});
t('IT NEVER THROWS, even when fetch does -- that is its whole contract', async () => {
  const realFetch = global.fetch;
  global.fetch = async () => { throw new Error('network is gone'); };
  process.env.SUPABASE_URL = 'https://example.test';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'srv';
  try {
    assert.strictEqual(await HB.beat({ job: '/x', outcome: 'ok', expected_interval_seconds: 60 }), false);
  } finally { global.fetch = realFetch; }
});
t('it upserts on the primary key rather than inserting a second row', () => {
  const src = fs.readFileSync(path.join(__dirname, '_lib', 'heartbeat.js'), 'utf8');
  assert.ok(/on_conflict=job/.test(src));
  assert.ok(/merge-duplicates/.test(src));
});

// ── 6. the schema and the code agree ───────────────────────────────────────
section('6. the schema');
{
  const RAW = fs.readFileSync(path.join(__dirname, '..', 'sql', 'cron_heartbeat_schema.sql'), 'utf8');
  const NL = String.fromCharCode(10);
  // Comment-stripped: this schema's header explains at length what it does NOT
  // grant, and a grep over the raw text matches the explanation.
  const SQL = RAW.split(NL).map((l) => {
    const i = l.indexOf('--');
    return i === -1 ? l : l.slice(0, i);
  }).join(NL);
  t('DELETE is revoked -- deleting a heartbeat is how a dead job stops being noticed', () => {
    assert.ok(/revoke delete on public\.sairn_cron_heartbeat/i.test(SQL));
    assert.ok(!/grant[^;]*delete[^;]*sairn_cron_heartbeat/i.test(SQL));
  });
  t('UPDATE is granted -- unlike the audit logs, and deliberately', () => {
    assert.ok(/grant select, insert, update on public\.sairn_cron_heartbeat/i.test(SQL));
  });
  t('anon and authenticated are revoked', () => {
    assert.ok(/revoke all on public\.sairn_cron_heartbeat from anon, authenticated/i.test(SQL));
  });
  t('job is the PRIMARY KEY, so two concurrent beats cannot fork into two rows', () => {
    assert.ok(/job text primary key/i.test(SQL));
  });
  t('the outcome CHECK matches the writer\'s own allowlist', () => {
    for (const o of Object.keys(HB.OUTCOMES)) {
      assert.ok(SQL.indexOf("'" + o + "'") !== -1, o + ' is not in the schema CHECK');
    }
  });
  t('the verify block states an expected answer per query', () => {
    assert.ok((SQL.match(/^select /gim) || []).length >= 4);
    assert.ok(/Expect/i.test(RAW));
  });
}

// ── 4b-ter. A MONITOR DOES NOT GRADE ITSELF EITHER ─────────────────────────
// Added 2026-09-17 from production logs, same as 4b-bis and the same shape one
// layer down. 4b-bis stopped the watchdog RESPONDING to its own row. The
// outcome it WRITES about itself was still derived from a `bad` list containing
// that row, so `partial` read back as PARTIAL and wrote `partial` again, for
// ever, with no input from the world. The first latch was loud -- HTTP 508 and
// an hourly alert storm. This one is silent: a monitor simply red for ever.
//
// EVERY ARM BELOW THAT ASSERTS `ok` IS PAIRED WITH ONE MAKING THE SAME CALL
// SAY SOMETHING ELSE, because `selfOutcome` returning a constant `'ok'` would
// satisfy the release arm on its own and that is the exact defect being fixed.
section('4b-ter. the watchdog does not grade itself');
const badSelf = [{ job: SELF, status: 'PARTIAL' }];
const badOther = { job: '/api/alf-alerts', status: 'DEAD' };

t('CONTROL -- with no selfJob the OLD behaviour is unchanged: self row => partial', () => {
  // Without this, every arm after it could pass against a function that had
  // stopped looking at `bad` at all.
  assert.strictEqual(W.selfOutcome(badSelf, [], true, undefined), 'partial');
});
t('THE LATCH IS RELEASED -- self PARTIAL alone, channel configured => ok', () => {
  assert.strictEqual(W.selfOutcome(badSelf, [], true, SELF), 'ok');
});
t('...and it is the EXCLUSION doing it, not the channel: same call, self absent => ok', () => {
  assert.strictEqual(W.selfOutcome([], [], true, SELF), 'ok');
});
t('ANOTHER job in trouble still degrades this one -- that term is NOT self-referential', () => {
  assert.strictEqual(W.selfOutcome([badOther], [], true, SELF), 'partial');
  assert.strictEqual(W.selfOutcome(badSelf.concat([badOther]), [], true, SELF), 'partial');
});
t('...and that one RECOVERS rather than latching: the other job clears => ok', () => {
  assert.strictEqual(W.selfOutcome([], [], true, SELF), 'ok');
});
t('AN UNCONFIGURED CHANNEL is still partial with nothing else wrong', () => {
  assert.strictEqual(W.selfOutcome([], [], false, SELF), 'partial');
});
t('A REAL UNDELIVERED ALERT is still `failed`, and it outranks everything', () => {
  assert.strictEqual(W.selfOutcome([], [{ job: '/api/alf-alerts' }], true, SELF), 'failed');
  assert.strictEqual(W.selfOutcome(badSelf, [{ job: '/api/alf-alerts' }], false, SELF), 'failed');
});
t('SELF_JOB is the SAME STRING the report is keyed on -- not a second spelling', () => {
  assert.strictEqual(W.SELF_JOB, SELF);
  assert.ok(W.EXPECTED_JOBS[W.SELF_JOB], 'SELF_JOB is not a key of EXPECTED_JOBS');
});

// THE LATCH DRIVEN END TO END THROUGH THE TWO REAL FUNCTIONS, because the bug
// was never visible in either one alone -- it lived in the handoff between
// them. assess() turns last_outcome `partial` into status PARTIAL; selfOutcome
// decides what gets written back. Five runs is the production shape: that is
// how many consecutive live runs it took to be sure the old one never left.
t('FIVE CONSECUTIVE RUNS: the self row heals in one and stays healed', () => {
  let outcome = 'partial';                       // the state found live at 00:15Z
  const seen = [];
  for (let i = 0; i < 5; i++) {
    const rows = ALL_FRESH().filter((r) => r.job !== SELF)
      .concat([hb(SELF, 60, outcome)]);
    const report = W.assess(NOW, rows);
    const bad = report.filter((x) => x.status !== 'ok');
    outcome = W.selfOutcome(bad, [], true, SELF);
    seen.push(outcome);
  }
  assert.deepStrictEqual(seen, ['ok', 'ok', 'ok', 'ok', 'ok']);
});
t('TEETH -- the OLD expression latches on the same five runs, or this proves nothing', () => {
  // If this arm ever goes green, the fixture stopped reproducing the bug and
  // the arm above is asserting a property of nothing.
  let outcome = 'partial';
  const seen = [];
  for (let i = 0; i < 5; i++) {
    const rows = ALL_FRESH().filter((r) => r.job !== SELF)
      .concat([hb(SELF, 60, outcome)]);
    const bad = W.assess(NOW, rows).filter((x) => x.status !== 'ok');
    outcome = bad.length ? 'partial' : 'ok';     // the expression that shipped
    seen.push(outcome);
  }
  assert.deepStrictEqual(seen, ['partial', 'partial', 'partial', 'partial', 'partial'],
    'the fixture no longer reproduces the latch -- the arm above tests nothing');
});

// ── 4c. THE ALERT CHANNEL'S RESTORE TEST ───────────────────────────────────
// `notify_channel.configured` says three variables are SET. Resend accepting a
// send says the provider took it. NEITHER is delivery, and this platform has
// twice mistaken one of those for another -- the 2026-09-15 state where every
// planned alert ended "nobody was told" under an HTTP 200, and the note that
// said an accepted resend_id proved the mail path worked.
//
// THE TWO PHASES ARE THE POINT. Delivery is asynchronous, so polling in the
// same request records `sent` -- a non-answer -- as the answer.
section('4c. the alert channel proves itself, and accepted is not delivered');

t('NO PROOF AT ALL IS DUE -- never tested must not read as recently fine', () => {
  assert.strictEqual(W.proofIsDue(null, NOW), true);
  assert.strictEqual(W.proofIsDue({}, NOW), true);
});
t('a FRESH proof is not due again', () => {
  const p = { sent_at: new Date(NOW - 3600 * 1000).toISOString() };
  assert.strictEqual(W.proofIsDue(p, NOW), false);
});
t('...and an OLD one is, at the declared interval and not a retyped number', () => {
  const old = new Date(NOW - (W.CHANNEL_PROOF_INTERVAL_SECONDS + 60) * 1000);
  assert.strictEqual(W.proofIsDue({ sent_at: old.toISOString() }, NOW), true);
});
t('an UNPARSEABLE sent_at is DUE, not silently fresh', () => {
  assert.strictEqual(W.proofIsDue({ sent_at: 'not a date' }, NOW), true);
});

t('ACCEPTED IS NOT TERMINAL -- `sent` and `queued` need a follow-up', () => {
  assert.strictEqual(W.proofNeedsFollowUp({ id: 'x', last_event: 'sent' }), true);
  assert.strictEqual(W.proofNeedsFollowUp({ id: 'x', last_event: 'queued' }), true);
  assert.strictEqual(W.proofNeedsFollowUp({ id: 'x', last_event: null }), true);
});
t('...and `delivered` is, so it stops asking', () => {
  assert.strictEqual(W.proofNeedsFollowUp({ id: 'x', last_event: 'delivered' }), false);
});
t('A BOUNCE IS TERMINAL TOO -- a failed delivery is an answer, not a pending one', () => {
  for (const e of ['bounced', 'complained', 'failed', 'canceled']) {
    assert.strictEqual(W.proofNeedsFollowUp({ id: 'x', last_event: e }), false, e);
  }
});
t('a proof with NO id cannot be followed up -- nothing to ask about', () => {
  assert.strictEqual(W.proofNeedsFollowUp({ last_event: null }), false);
  assert.strictEqual(W.proofNeedsFollowUp(null), false);
});
t('TEETH -- `sent` is NOT in the terminal list, which is the whole distinction', () => {
  assert.strictEqual(W.PROOF_TERMINAL.indexOf('sent'), -1,
    'accepted was folded into delivered, which is the confusion this exists to end');
  assert.strictEqual(W.PROOF_TERMINAL.indexOf('queued'), -1);
  assert.ok(W.PROOF_TERMINAL.indexOf('delivered') !== -1);
});
t('FOLLOW-UP WINS when both would fire -- and this arm found that it can', () => {
  // WRITTEN AS "mutually exclusive" FIRST AND THAT WAS WRONG. A record with an
  // id and no `sent_at` -- a send that was accepted while the write of its
  // timestamp was lost -- makes BOTH predicates true. The handler is safe
  // because it is `if (followUp) ... else if (due)`, so the follow-up wins; but
  // the ordering was an unstated property of the code rather than a rule, and
  // the wrong version of this arm is what surfaced it.
  //
  // THE ORDER MATTERS AND IS NOT ARBITRARY: sending again while the previous
  // message is unresolved is how a weekly cadence turns into a storm, and it
  // would also overwrite the id nobody had finished asking about.
  const both = { id: 'x', last_event: null };
  assert.strictEqual(W.proofNeedsFollowUp(both), true);
  assert.strictEqual(W.proofIsDue(both, NOW), true,
    'the fixture no longer makes both true, so this arm tests nothing');
  const src = require('fs').readFileSync(
    require('path').join(__dirname, 'cron-watchdog.js'), 'utf8');
  const i = src.indexOf('proofNeedsFollowUp(priorProof)');
  const j = src.indexOf('proofIsDue(priorProof, nowMs)');
  assert.ok(i !== -1 && j !== -1 && i < j,
    'the follow-up branch no longer comes first, so a pending proof can be '
    + 'overwritten by a fresh send');
  assert.ok(/\}\s*else if \(proofIsDue/.test(src),
    'the two branches are no longer else-if, so both can fire in one run');
});

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + (e && e.message)); fail++; }
  }
  console.log('\ncron-watchdog: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
