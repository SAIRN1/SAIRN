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
async function call(fetchImpl) {
  const realFetch = global.fetch;
  global.fetch = fetchImpl;
  process.env.CRON_SECRET = 'secret';
  process.env.SUPABASE_URL = 'https://example.test';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'srv';
  const res = makeRes();
  try { await W({ headers: { authorization: 'Bearer secret' } }, res); }
  finally { global.fetch = realFetch; }
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
t('a healthy table answers ok:true', async () => {
  const out = await call(async (url) => {
    if (String(url).indexOf('sairn_cron_heartbeat?select=') !== -1) {
      return reply(200, JSON.stringify(ALL_FRESH()));
    }
    return reply(201, '');       // the watchdog's own beat
  });
  assert.strictEqual(out.code, 200);
  assert.strictEqual(out.body.ok, true, JSON.stringify(out.body));
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

(async () => {
  for (const [name, fn] of queue) {
    if (!fn) { console.log('--- ' + name + ' ---'); continue; }
    try { await fn(); console.log('  ok   ' + name); pass++; }
    catch (e) { console.log('  FAIL ' + name + '\n       ' + (e && e.message)); fail++; }
  }
  console.log('\ncron-watchdog: ' + pass + ' passed, ' + fail + ' failed');
  if (fail) process.exit(1);
})();
