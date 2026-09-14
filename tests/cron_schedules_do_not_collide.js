// tests/cron_schedules_do_not_collide.js
//
// Run:  node tests/cron_schedules_do_not_collide.js
//
// TWO SCHEDULED JOBS FIRED AT THE SAME MINUTE AND BOTH FAILED A THIRD OF THE
// TIME. This is not a tidiness suite.
//
// `/api/sairndental/send-reminder` and `/api/alf-alerts` were both `0 * * * *`.
// Vercel's runtime-error table for the preceding seven days:
//
//   send-reminder: dnt_appointments list failed 504    count=23
//     first 2026-09-12T00:00:29Z    last 2026-09-14T12:00:29Z
//   alf-alerts: facility sweep read failed, HTTP 504   count=20
//     first 2026-09-12T04:00:43Z    last 2026-09-14T13:00:43Z
//   ai rate limit: atomic RPC failed, HTTP 504         count=11   (/api/claude)
//     last 2026-09-14T10:00:51Z
//
// EVERY ONE AT :00. Appointment reminders that were never sent, medication
// exception alerts that were never computed, and -- in the same minute --
// /api/claude's Supabase rate-limit RPC timing out, which was the open and
// unexplained 504 pattern.
//
// THE MECHANISM IS A SHARED BACKEND, NOT A CALL PATH, and the obvious reading
// is wrong: neither cron calls /api/claude. Read them and they call Supabase
// and Resend and nothing else. What all three share is the Supabase project.
//
// WHAT THIS SUITE CAN AND CANNOT HOLD. It pins the SCHEDULE -- that no two
// hourly jobs share a minute, that the jitter helper is bounded and is
// actually called before the first read, and that the interactive paths do not
// wait. It CANNOT prove the 504s were caused by the collision; that is settled
// by the next week of logs, and the change is shaped so the answer is readable
// either way: if the failures move with the schedule the collision was the
// cause, and if they stay at :00 something else spikes at the top of the hour.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const rd = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8').replace(/\r\n/g, '\n');
const VERCEL = JSON.parse(rd('vercel.json'));
const JIT = require(path.join(ROOT, 'api/_lib/cron-jitter.js'));

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }
function section(s) { console.log('\n' + s); }

console.log('SAIRN: scheduled jobs do not all arrive at once\n');

// ── 1. NO TWO HOURLY JOBS SHARE A MINUTE ────────────────────────────────────
section('1. the schedule itself');

const crons = VERCEL.crons || [];
ok(crons.length > 0, 'vercel.json declares crons at all (' + crons.length + ')');

// A cron minute field can be a list or a step; every minute a job can fire on
// is expanded rather than the field compared as a string, because "0" and
// "0,30" collide on :00 and are not equal as text.
function minutes(expr) {
  const field = String(expr).trim().split(/\s+/)[0];
  const out = new Set();
  for (const part of field.split(',')) {
    const step = part.split('/');
    const every = step.length > 1 ? parseInt(step[1], 10) : 1;
    const range = step[0];
    if (range === '*') {
      for (let m = 0; m < 60; m += every) out.add(m);
    } else if (range.indexOf('-') > 0) {
      const [a, b] = range.split('-').map(Number);
      for (let m = a; m <= b; m += every) out.add(m);
    } else {
      out.add(Number(range));
    }
  }
  return out;
}
ok(minutes('0,30 * * * *').has(0) && minutes('*/15 * * * *').has(45) &&
   minutes('5-7 * * * *').has(6),
   'CONTROL: the minute expander handles lists, steps and ranges -- otherwise '
   + 'the collision check below is a string comparison wearing a costume');

const collisions = [];
for (let i = 0; i < crons.length; i++) {
  for (let j = i + 1; j < crons.length; j++) {
    const a = crons[i], b = crons[j];
    const ma = minutes(a.schedule), mb = minutes(b.schedule);
    const shared = [...ma].filter((m) => mb.has(m));
    if (!shared.length) continue;
    // Two jobs can share a minute harmlessly if their HOUR fields never
    // coincide -- a daily 03:30 job and an hourly :30 job collide once a day,
    // which is a real collision and is reported, but a daily job against a
    // daily job at different hours is not.
    const ha = String(a.schedule).trim().split(/\s+/)[1];
    const hb = String(b.schedule).trim().split(/\s+/)[1];
    if (ha !== '*' && hb !== '*' && ha !== hb) continue;
    collisions.push(a.path + ' and ' + b.path + ' both fire at minute ' + shared.join(','));
  }
}
ok(collisions.length === 0,
   'NO TWO CRONS SHARE A FIRING MINUTE -- the state that had two jobs and '
   + '/api/claude all timing out at :00: ' + collisions.join(' | '));

const byPath = {};
crons.forEach((c) => { byPath[c.path] = c.schedule; });
ok(!/^0\s/.test(byPath['/api/sairndental/send-reminder'] || '') &&
   !/^0\s/.test(byPath['/api/alf-alerts'] || ''),
   'and neither of the two is back on :00, the busiest minute of the hour '
   + 'for every scheduler on the internet');

// ── 2. THE JITTER IS BOUNDED, AND A TYPO DOES NOT SILENTLY DISABLE IT ───────
section('2. the jitter helper');

const saved = process.env.SAIRN_CRON_JITTER_MS;
try {
  delete process.env.SAIRN_CRON_JITTER_MS;
  let hi = 0;
  for (let i = 0; i < 400; i++) hi = Math.max(hi, JIT.jitterMs());
  ok(hi < JIT.DEFAULT_MAX_MS && hi > JIT.DEFAULT_MAX_MS * 0.5,
     'the default delay is bounded by DEFAULT_MAX_MS and actually spreads '
     + '(400 draws reached ' + hi + 'ms of ' + JIT.DEFAULT_MAX_MS + ')');

  process.env.SAIRN_CRON_JITTER_MS = '0';
  ok(JIT.jitterMs() === 0, 'it can be switched OFF by env without a deploy');

  // A TYPO MUST NOT READ AS "OFF". Number('') is 0 and Number('abc') is NaN,
  // and either silently disabling the mitigation is the exact shape of failure
  // this platform keeps writing down -- a setting that means "disabled" when
  // it means "unreadable".
  for (const junk of ['abc', '-5', 'twenty']) {
    process.env.SAIRN_CRON_JITTER_MS = junk;
    let seen = 0;
    for (let i = 0; i < 200; i++) seen = Math.max(seen, JIT.jitterMs());
    ok(seen > 0, 'an unparseable SAIRN_CRON_JITTER_MS=' + JSON.stringify(junk)
       + ' falls back to the default rather than to zero');
  }
} finally {
  if (saved === undefined) delete process.env.SAIRN_CRON_JITTER_MS;
  else process.env.SAIRN_CRON_JITTER_MS = saved;
}

// ── 3. IT IS ACTUALLY CALLED, AND IN THE RIGHT PLACE ───────────────────────
section('3. the helper is wired, not merely written');

// A helper nothing calls is the shape this repo has shipped before: the
// soft_delete branch existed for five days with no caller, and twenty-one
// verbs were wired into the API that nothing in the product ever invoked.
const REM = rd('api/sairndental/send-reminder.js');
const ALF = rd('api/alf-alerts.js');
for (const [name, src] of [['send-reminder', REM], ['alf-alerts', ALF]]) {
  ok(/require\((['"]).{0,4}\.\.?\/_lib\/cron-jitter\1\)/.test(src),
     name + ' requires the jitter helper');
  ok(/await jitter\(/.test(src), name + ' AWAITS it -- an un-awaited jitter() '
     + 'returns a promise and delays nothing');
}

// ORDER MATTERS AND IS THE ONLY PART THAT IS EASY TO GET WRONG. The wait must
// come AFTER the auth/config gates -- an unauthorised or misconfigured request
// should be refused immediately, not 20 seconds later -- and BEFORE the first
// backend read, which is the thing being spread.
const remJit = REM.indexOf('await jitter(');
const remAuth = REM.indexOf("Bearer ' + process.env.CRON_SECRET");
// The LIST read specifically, not the first mention of the table -- the stamp
// writer at the top of the file also names dnt_appointments and is not the
// read that was timing out. Anchoring on the wrong one would make this arm
// pass or fail for a reason that has nothing to do with the ordering.
const remRead = REM.indexOf("rest('dnt_appointments?status=eq.Confirmed");
ok(remAuth > 0 && remJit > remAuth,
   'send-reminder waits AFTER the bearer check -- an unauthorised caller is '
   + 'refused immediately, not after a delay');
ok(remRead > 0 && remJit < remRead,
   '...and BEFORE the appointment read, which is the read that was timing out');

const alfJit = ALF.indexOf('await jitter(');
const alfRead = ALF.indexOf("rest('alf_facility?select=");
const alfCron = ALF.indexOf('if (isCron) {');
ok(alfCron > 0 && alfJit > alfCron,
   'alf-alerts waits only on the CRON path -- the interactive path is somebody '
   + 'waiting on a response and has nothing to be spread away from');
ok(alfRead > 0 && alfJit < alfRead,
   '...and before the facility sweep, which is the read that was timing out');

console.log('\nALL ' + n + ' ASSERTIONS PASS');
