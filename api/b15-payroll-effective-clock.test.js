// api/b15-payroll-effective-clock.test.js
//
// Run:  node api/b15-payroll-effective-clock.test.js
//
// FOURTH's b23 F1, AND IT IS MONEY. An APPROVED clock correction reaches
// nothing: payroll pays the ORIGINAL time.
//
// Fourth's repro (scratchpad/payroll_clock_repro_b23.js, log
// payroll_clock_repro_b23.log) measured ONE visit with ONE approved
// correction: 240 minutes / 8000 cents as shipped, against 300 minutes /
// 10000 cents with effectiveClock applied. SIXTY MINUTES AND 2000 CENTS
// UNPAID, per visit, per correction.
//
// WHY IT IS THE MIRROR OF THE THING THAT WAS VERIFIED SAFE. The same review
// asked whether an UNAPPROVED time could reach payroll and drove the answer
// NO -- a pending correction leaves payroll at 240, identical to no
// correction. Both halves come from the same cause: payroll never looks at
// `clock_corrections` at all. One direction was harmless and the other is a
// wage.
//
//   api/_lib/sen-payroll.js:200-201   reads row.clock_in_at / row.clock_out_at
//                                     raw; grep -c effectiveClock -> 0
//   api/sd-data.js:7678-7679          spreads x.data with no substitution
//   api/_lib/sen-evv-clock.js:342-344 claims the rule is "implemented HERE,
//                                     in the function payroll reads" -- and
//                                     payroll was not reading it
//
// THE FIX GOES IN THE MODULE, NOT IN THE HANDLER BRANCH. b14's own lesson:
// a rule enforced in one branch of one endpoint is a rule the next caller
// does not get. sen-payroll.js is the authority for PAY, so it is the thing
// that must read the effective clock; the endpoint's map then needs no change
// and arm P7 proves that end to end.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b15', 'fixture', String(process.pid)].join('-');
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// THE REAL MODULES. A reimplementation of either would pass against the
// unfixed code, which is the failure mode this platform keeps paying for.
const payroll = require('./_lib/sen-payroll');
const clock = require('./_lib/sen-evv-clock');

// ── FOURTH's FIXTURE, REBUILT FROM THEIR NUMBERS ─────────────────────────
// A four-hour recorded visit with an APPROVED correction moving the clock-in
// an hour earlier: 240 minutes recorded, 300 minutes as corrected. The rate
// is 2000 cents/hour so the money is the arithmetic fourth reported --
// 8000 against 10000.
const DAY = '2026-10-06';                    // a Monday, inside the period
const REC_IN = DAY + 'T13:00:00.000Z';
const COR_IN = DAY + 'T12:00:00.000Z';       // the APPROVED correction
const REC_OUT = DAY + 'T17:00:00.000Z';
const RATE_CENTS = 2000;

function approvedCorrection() {
  return { field: 'clock_in_at', original_at: REC_IN, proposed_at: COR_IN,
           reason_code: 'transcription_error', proposed_by: 'E1',
           proposed_at_server: REC_IN, status: 'approved',
           approved_by: 'S1', approved_at_server: REC_IN };
}
function pendingCorrection() {
  return Object.assign(approvedCorrection(),
                       { status: 'pending', approved_by: null, approved_at_server: null });
}
function visit(corrections) {
  const v = { id: 'V1', assigned_employee_id: 'E1', scheduled_date: DAY,
              clock_in_at: REC_IN, clock_out_at: REC_OUT };
  if (corrections) v.clock_corrections = corrections;
  return v;
}
function run(visits) {
  return payroll.computePayroll({
    visits: visits,
    period_start: '2026-10-05', period_end: '2026-10-11',
    week_start_day: 'Sunday',
    resolveRate: function () { return { status: 'applied', rate_per_hour: RATE_CENTS / 100 }; }
  });
}
function minutesOf(out) {
  const b = out && out.caregivers && out.caregivers[0];
  return b ? b.minutes : null;
}
function centsOf(out) {
  const b = out && out.caregivers && out.caregivers[0];
  return b ? b.gross_cents : null;
}

console.log('b15 / fourth b23 F1. an APPROVED correction must reach payroll\n');

(async () => {
  // ── BASELINE, so the arms below are reading a working computation ───────
  {
    const out = run([visit(null)]);
    is(minutesOf(out) === 240 && centsOf(out) === 8000,
       'P0. CONTROL -- an UNCORRECTED four-hour visit at 2000 cents/hour is '
     + '240 minutes and 8000 cents. This is fourth\'s baseline and it pins the '
     + 'fixture: if this arm moves, every number below means something else',
       'minutes=' + minutesOf(out) + ' cents=' + centsOf(out)
     + ' keys=' + JSON.stringify(Object.keys(out || {})).slice(0, 160));
  }

  // ── THE ARM THE FINDING IS ──────────────────────────────────────────────
  {
    const out = run([visit([approvedCorrection()])]);
    is(minutesOf(out) === 300,
       'P1. THE MONEY ARM -- an APPROVED correction moving the clock-in one '
     + 'hour earlier makes the visit 300 minutes, not 240. As shipped payroll '
     + 'read row.clock_in_at raw and paid the ORIGINAL time: 60 minutes '
     + 'unpaid on one visit with one approved correction',
       'minutes=' + minutesOf(out) + ' expected 300');
    is(centsOf(out) === 10000,
       'P2. ...and 10000 cents, not 8000. The 2000-cent gap is the finding in '
     + 'the unit that matters',
       'cents=' + centsOf(out) + ' expected 10000');
  }

  // ── A PENDING CORRECTION MUST STILL REACH NOTHING ───────────────────────
  {
    const out = run([visit([pendingCorrection()])]);
    is(minutesOf(out) === 240 && centsOf(out) === 8000,
       'P3. CONTROL, AND IT IS THE HALF THAT WAS ALREADY SAFE -- a PENDING '
     + 'correction leaves payroll at 240 / 8000, identical to no correction. '
     + 'Without this arm the fix could be "apply every correction", which '
     + 'would pay an unverified self-asserted time and is exactly what the '
     + 'two-person rule exists to stop',
       'minutes=' + minutesOf(out) + ' cents=' + centsOf(out));
  }
  {
    // A LEGACY ENTRY -- no `status` at all -- IS APPROVED, because every
    // correction written before b13 was effective the moment it was filed.
    const legacy = approvedCorrection();
    delete legacy.status; delete legacy.approved_by; delete legacy.approved_at_server;
    const out = run([visit([legacy])]);
    is(minutesOf(out) === 300,
       'P4. a correction with NO `status` is treated as APPROVED and DOES '
     + 'reach payroll. Reading a missing status as pending would silently '
     + 'un-pay every correction filed before b13 -- the same rule '
     + 'effectiveClock() already carries, reached through payroll',
       'minutes=' + minutesOf(out));
  }
  {
    // THE CLOCK-OUT HALF. A rule proven on one of two fields covers one of
    // two fields.
    const v = visit([{ field: 'clock_out_at', original_at: REC_OUT,
                       proposed_at: DAY + 'T18:00:00.000Z',
                       reason_code: 'forgot_to_clock_out', proposed_by: 'E1',
                       proposed_at_server: REC_OUT, status: 'approved',
                       approved_by: 'S1', approved_at_server: REC_OUT }]);
    const out = run([v]);
    is(minutesOf(out) === 300,
       'P5. clock_out_at is substituted too, not just clock_in_at',
       'minutes=' + minutesOf(out));
  }
  {
    // THE REFUSALS MUST STILL FIRE ON THE EFFECTIVE VALUES, not on the raw
    // ones -- otherwise a correction could create a negative duration and be
    // paid as a huge number.
    const v = visit([{ field: 'clock_in_at', original_at: REC_IN,
                       proposed_at: DAY + 'T23:00:00.000Z',   // AFTER clock-out
                       reason_code: 'transcription_error', proposed_by: 'E1',
                       proposed_at_server: REC_IN, status: 'approved',
                       approved_by: 'S1', approved_at_server: REC_IN }]);
    const out = run([v]);
    const b = out && out.caregivers && out.caregivers[0];
    is(!!out && !!out.excluded && out.excluded.non_positive_duration === 1
       && (!b || b.minutes === 0),
       'P6. an approved correction that makes the clock-out EARLIER than the '
     + 'clock-in is EXCLUDED as a non-positive duration, counted, and pays '
     + 'nothing. The guard has to run on the values actually used or the '
     + 'substitution becomes a route around it',
       'excluded=' + JSON.stringify(out && out.excluded)
     + ' minutes=' + (b ? b.minutes : null));
  }

  // ── END TO END THROUGH THE REAL HANDLER ─────────────────────────────────
  // The endpoint's map at api/sd-data.js:7678-7679 spreads x.data, so the
  // corrections are already on the row it builds. If the fix is in the
  // module, this arm passes with NO change to the handler -- which is the
  // claim being tested, not an assumption.
  {
    require.cache[require.resolve('./_lib/license')] = {
      id: require.resolve('./_lib/license'),
      filename: require.resolve('./_lib/license'),
      loaded: true,
      exports: {
        validateLicenseKey: async () => ({
          valid: true, active: true, license_hash: HASH,
          trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnsenior' })
      }
    };
    const { signSessionToken } = require('./_lib/auth');
    delete require.cache[require.resolve('./sd-data.js')];
    const handler = require('./sd-data.js');
    const res = { statusCode: null, body: null };
    res.status = (c) => { res.statusCode = c; return res; };
    res.json = (b) => { res.body = b; return res; };
    global.fetch = async function (url, init) {
      const u = String(url);
      const method = (init && init.method) || 'GET';
      if (/_employee_auth\?/.test(u)) {
        return { ok: true, status: 200, headers: { get: () => '' },
                 text: async () => '[]',
                 json: async () => [{ license_hash: HASH, employee_id: 'S1',
                                      role: 'owner', active: true }] };
      }
      if (/sen_pay_rates\?/.test(u)) {
        return { ok: true, status: 200, headers: { get: () => '' },
                 text: async () => '[]',
                 json: async () => [{ rate_id: 'R1',
                   data: { employee_id: 'E1', rate_per_hour: RATE_CENTS / 100,
                           effective_on: '2026-01-01', term_on: '' } }] };
      }
      if (/sen_visits\?/.test(u)) {
        return { ok: true, status: 200, headers: { get: () => '' },
                 text: async () => '[]',
                 json: async () => [{ visit_id: 'V1', assigned_employee_id: 'E1',
                   data: { scheduled_date: DAY, clock_in_at: REC_IN,
                           clock_out_at: REC_OUT,
                           clock_corrections: [approvedCorrection()] } }] };
      }
      if (method !== 'GET') {
        return { ok: true, status: 200, headers: { get: () => '' },
                 text: async () => '[]', json: async () => [JSON.parse(init.body)] };
      }
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]', json: async () => [] };
    };
    await handler({ method: 'POST',
      headers: { authorization: 'Bearer ' + KEY,
                 'x-sd-auth': signSessionToken({ app: 'sairnsenior',
                   employee_id: 'S1', role: 'owner', license_hash: HASH }) },
      body: { action: 'payroll', resource: 'sen_visits',
              payload: { period_start: '2026-10-05', period_end: '2026-10-11',
                         week_start_day: 'Sunday' } } }, res);
    const d = (res.body && res.body.data) || null;
    const b = d && d.caregivers && d.caregivers[0];
    is(res.statusCode === 200 && b && b.minutes === 300
       && b.gross_cents === 10000,
       'P7. END TO END through the real api/sd-data.js payroll action: 300 '
     + 'minutes and 10000 cents. The handler\'s map is UNCHANGED -- it already '
     + 'spreads x.data, so the corrections were always on the row and only '
     + 'the module was not reading them',
       'status=' + res.statusCode + ' minutes=' + (b && b.minutes)
     + ' cents=' + (b && b.gross_cents));
  }

  // ── AND THE MODULE SAYS SO IN ITS OWN SOURCE ────────────────────────────
  {
    const src = fs.readFileSync(path.join(ROOT, 'api/_lib/sen-payroll.js'), 'utf8');
    is(/effectiveClock/.test(src),
       'P8. api/_lib/sen-payroll.js references effectiveClock at all. '
     + 'fourth measured `grep -c effectiveClock` -> 0 while '
     + 'api/_lib/sen-evv-clock.js:342 claimed the rule was "implemented HERE, '
     + 'in the function payroll reads"',
       'no effectiveClock in sen-payroll.js');
    is(typeof clock.effectiveClock === 'function',
       'P9. CONTROL -- effectiveClock is still exported, so the substitution '
     + 'has one source rather than a second copy of the rule');
  }

  // ── THE OUTPUT SAYS WHEN MONEY MOVED BECAUSE OF A CORRECTION ────────────
  {
    const out = run([visit([approvedCorrection()])]);
    const b = out && out.caregivers && out.caregivers[0];
    const disclosed = JSON.stringify(out || {});
    is(/corrected/i.test(disclosed),
       'P10. the payroll output DISCLOSES that a corrected clock time was '
     + 'used. A wage that silently differs from the recorded clock time is a '
     + 'figure nobody can reconcile against the EVV record -- and reconciling '
     + 'them is the whole purpose of the trail',
       'nothing in the output mentions a correction: '
     + JSON.stringify(Object.keys(b || {})).slice(0, 220));
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
