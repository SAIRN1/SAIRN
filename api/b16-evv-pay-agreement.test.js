// api/b16-evv-pay-agreement.test.js
//
// Run:  node api/b16-evv-pay-agreement.test.js
//
// REQUIREMENT (MICHAEL'S DECISION, 2026-10-15 -- fourth's F2): the EVV checks
//   read the SAME effective clock pay uses, so an EVV export and a pay run
//   cannot disagree about the same visit.
//
// ── THE DIVERGENCE THIS CLOSES, AS THE b15 HANDOFF STATED IT ──────────────
//   "AN EVV EXPORT AND A PAY RUN CAN NOW DISAGREE ABOUT THE SAME VISIT.
//    api/_lib/sen-evv-readiness.js and the client's EVV anomaly checks still
//    read the raw clock ... Nothing reconciles the two numbers."
//
// b15 made pay read the effective clock and deliberately did NOT touch the EVV
// side, because F2 was reserved for Michael. The reserved question is now
// answered, so the two sides are brought onto one function.
//
// CONCRETELY: a visit whose clock-out was never recorded and whose approved
// correction supplies it is, after b15, a PAID visit with real minutes. The
// readiness check still called it "No clock-out time recorded" -- so the same
// visit was simultaneously payable and not EVV-submittable, and a state EVV
// programme reconciling an export against a payroll register would find hours
// paid for a visit the export says has no end time. That is the shape of
// finding that costs an agency its certification, and neither number is
// obviously the wrong one to a reader of either alone.
//
// ── WHAT STAYS RAW, AND WHY IT IS NOT AN INCONSISTENCY ───────────────────
// GPS. `clock_out_lat` is a property of the clock EVENT, and a correction
// supplies a TIME and never a location. An approved correction therefore must
// not clear "No GPS on clock-out" -- it has not produced one. The time-span
// element is the one F2 is about and the only one moved. E5 asserts the GPS
// arms did NOT move, because a sweep that moved them all would be the easier
// change and the wrong one.
//
// ── E8 WAS A DELIBERATE DISAGREEMENT AND IT IS NOW CLOSED (b17) ──────────
// AS WRITTEN IN b16: "a run of a CLOSED period reads the clock AS AT paid_at,
// while an EVV export reads it as at now. Those two CAN differ, and that
// difference is the restatement trail rather than a bug."
//
// THAT WAS WRONG, and fourth's b26 Q(b)2 is why: it was not a trail, it was
// F2 HALF-LANDED. Both sides called effectiveClock() -- the same function, as
// b16 required -- and only payroll passed the as-of ARGUMENT. So a correction
// approved after a period was paid made a visit submittable in the export
// while the register paid nothing for it, and because both halves pointed at
// one function it LOOKED settled.
//
// b17 threads the as-of through (api/_lib/sen-evv-readiness.js now takes
// `options.closed_periods`), and api/b17-evv-closed-period-asof.test.js
// drives the agreement in BOTH directions. E8 below is kept and RE-AIMED: it
// now pins the ONE case where the two still differ, which is a caller that
// does not tell the readiness check about the freeze at all -- and that is a
// caller-side omission rather than a rule.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const READINESS_SRC = path.join(__dirname, '_lib', 'sen-evv-readiness.js');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 500));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 500));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

function freshReadiness() {
  delete require.cache[require.resolve('./_lib/sen-evv-readiness')];
  delete require.cache[require.resolve('./_lib/sen-evv-clock')];
  return require('./_lib/sen-evv-readiness');
}
function freshPayroll() {
  delete require.cache[require.resolve('./_lib/sen-payroll')];
  delete require.cache[require.resolve('./_lib/sen-evv-clock')];
  return require('./_lib/sen-payroll');
}

// ── THE FIXTURE: the exact visit that is payable and unsubmittable ───────
const DAY = '2026-10-06';
const REC_IN = DAY + 'T09:00:00.000Z';
const COR_OUT = DAY + 'T13:00:00.000Z';   // 240 minutes, supplied by correction

function correction(field, from, to, status) {
  return { id: 'C1', field: field, original_at: from, proposed_at: to,
           reason_code: 'FORGOT_TO_CLOCK_OUT', filed_by: 'E1',
           filed_at_server: DAY + 'T18:00:00.000Z',
           status: status || 'approved', approved_by: 'S1',
           approved_at_server: DAY + 'T19:00:00.000Z' };
}

// A visit complete in every EVV element EXCEPT the clock-out, which only the
// correction supplies. Everything else is filled so the time-span element is
// the only thing that can be missing -- otherwise a 'not ready' verdict would
// prove nothing about the clock.
function visitMissingClockOut(status) {
  return {
    id: 'V1', visit_id: 'V1', assigned_employee_id: 'E1', client_id: 'C1',
    scheduled_date: DAY, status: 'completed',
    clock_in_at: REC_IN, clock_out_at: null,
    clock_in_lat: 41.1, clock_in_lng: -81.5,
    clock_out_lat: 41.1, clock_out_lng: -81.5,
    service_code: 'T1019', service_description: 'Personal care',
    clock_corrections: [correction('clock_out_at', null, COR_OUT, status)]
  };
}

function timeSpanMissing(res) {
  return ((res && res.missing) || []).filter((m) => m.element === 'time_span');
}

// ── THE CLIENT SIDE, lifted out of the real page ─────────────────────────
const HTML = (function () {
  try { return fs.readFileSync(path.join(ROOT, 'sairnsenior.html'), 'utf8'); }
  catch (e) { return null; }
})();
function lift(name) {
  if (HTML === null) return null;
  const re = new RegExp('\\nfunction ' + name + '\\([^)]*\\)\\{[\\s\\S]*?\\n\\}');
  const m = HTML.match(re);
  return m ? m[0] : null;
}
function world(names) {
  const src = [];
  const missing = [];
  names.forEach(function (n) {
    const s = lift(n);
    if (s === null) missing.push(n); else src.push(s);
  });
  if (missing.length) return { missing: missing };
  const sandbox = { console: console, isFinite: isFinite, Date: Date,
                    Math: Math, JSON: JSON, String: String, Number: Number,
                    Array: Array, Object: Object };
  vm.createContext(sandbox);
  try { vm.runInContext(src.join('\n'), sandbox); }
  catch (e) { return { error: e }; }
  return { sandbox: sandbox };
}

// ── ABLATION on api/_lib/sen-evv-readiness.js ────────────────────────────
function ablate(anchor, replacement, fn) {
  const src = fs.readFileSync(READINESS_SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 1) return { ok: false, why: 'anchor occurs ' + n + ' times, not 1' };
  try {
    fs.writeFileSync(READINESS_SRC, src.split(anchor).join(replacement));
    return { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(READINESS_SRC, src);
    if (fs.readFileSync(READINESS_SRC, 'utf8') !== src) {
      console.log('  HARD ERROR the ablation did not restore '
        + 'api/_lib/sen-evv-readiness.js -- DO NOT COMMIT');
      process.exit(1);
    }
  }
}

const A_READ = "const outOk = isIsoInstant(effOut);";

function main() {
  console.log('api/b16-evv-pay-agreement.test.js');
  console.log('  an EVV export and a pay run read ONE clock');

  // ── E1: THE AGREEMENT, driven on BOTH modules at once ───────────────────
  // This is the arm the requirement is written in: the same visit, through the
  // thing that pays and the thing that exports, and they must not disagree.
  let e1ready = null;
  try {
    const readiness = freshReadiness();
    const payroll = freshPayroll();
    const v = visitMissingClockOut('approved');
    e1ready = readiness.checkVisit(v, { id: 'C1' }, { id: 'E1' }, null);
    const pay = payroll.computePayroll({
      visits: [v], period_start: DAY, period_end: DAY, week_start_day: 'sunday',
      resolveRate: () => ({ status: 'applied', rate_per_hour: 20 })
    });
    const b = pay.caregivers && pay.caregivers[0];
    const paidMinutes = b ? b.minutes : 0;
    const spans = timeSpanMissing(e1ready);
    is(paidMinutes === 240 && spans.length === 0,
       'E1. AGREEMENT -- a visit whose clock-out comes only from an APPROVED '
     + 'correction is paid 240 minutes AND has no time_span gap in the EVV '
     + 'readiness check. One clock, one answer',
       'paidMinutes=' + paidMinutes + ' time_span missing='
     + JSON.stringify(spans.map((m) => m.reason)));
  } catch (e) {
    bad('E1. AGREEMENT -- pay and EVV readiness agree on the same visit', e && e.stack);
  }

  // ── E2: CONTROL -- a PENDING correction moves NEITHER side ─────────────
  // Without this arm "readiness reads any correction" passes E1, and a
  // caregiver's own unapproved assertion would make a visit EVV-submittable.
  // That is worse than the divergence: it manufactures a compliant-looking
  // record for a time nobody verified, which is what this module's own note at
  // element 6 says must never happen.
  try {
    const readiness = freshReadiness();
    const payroll = freshPayroll();
    const v = visitMissingClockOut('pending');
    const res = readiness.checkVisit(v, { id: 'C1' }, { id: 'E1' }, null);
    const pay = payroll.computePayroll({
      visits: [v], period_start: DAY, period_end: DAY, week_start_day: 'sunday',
      resolveRate: () => ({ status: 'applied', rate_per_hour: 20 })
    });
    const b = pay.caregivers && pay.caregivers[0];
    const spans = timeSpanMissing(res);
    is(spans.length === 1 && /clock-out/i.test(spans[0].reason)
       && (!b || b.minutes === 0),
       'E2. CONTROL -- a PENDING correction moves NEITHER side: readiness '
     + 'still reports no clock-out and payroll still pays nothing. Only an '
     + 'APPROVED correction is a time, on both sides',
       'time_span=' + JSON.stringify(spans.map((m) => m.reason))
     + ' paidMinutes=' + (b && b.minutes));
  } catch (e) {
    bad('E2. CONTROL -- a PENDING correction moves neither side', e && e.stack);
  }

  // ── E3: CONTROL -- no corrections at all, nothing changed ─────────────
  try {
    const readiness = freshReadiness();
    const v = visitMissingClockOut('approved');
    delete v.clock_corrections;
    const res = readiness.checkVisit(v, { id: 'C1' }, { id: 'E1' }, null);
    const spans = timeSpanMissing(res);
    is(spans.length === 1 && /No clock-out time recorded/.test(spans[0].reason),
       'E3. CONTROL -- an uncorrected visit with no clock-out still reports '
     + '"No clock-out time recorded". The check did not stop checking',
       'time_span=' + JSON.stringify(spans.map((m) => m.reason)));
  } catch (e) {
    bad('E3. CONTROL -- an uncorrected missing clock-out still reports', e && e.stack);
  }

  // ── E4: AN APPROVED CORRECTION THAT INVERTS THE VISIT ─────────────────
  // payroll excludes it as a non-positive duration; readiness must report the
  // same fact rather than passing the raw pair it no longer uses.
  try {
    const readiness = freshReadiness();
    const payroll = freshPayroll();
    const v = visitMissingClockOut('approved');
    v.clock_out_at = DAY + 'T13:00:00.000Z';
    v.clock_corrections = [correction('clock_out_at', v.clock_out_at,
      DAY + 'T08:00:00.000Z', 'approved')];
    const res = readiness.checkVisit(v, { id: 'C1' }, { id: 'E1' }, null);
    const pay = payroll.computePayroll({
      visits: [v], period_start: DAY, period_end: DAY, week_start_day: 'sunday',
      resolveRate: () => ({ status: 'applied', rate_per_hour: 20 })
    });
    const spans = timeSpanMissing(res);
    is(spans.length === 1 && /positive duration/i.test(spans[0].reason)
       && pay.excluded.non_positive_duration === 1,
       'E4. an APPROVED correction that INVERTS the visit is a non-positive '
     + 'duration on BOTH sides -- payroll excludes it, readiness reports it. '
     + 'Not a silently submittable record',
       'time_span=' + JSON.stringify(spans.map((m) => m.reason))
     + ' excluded=' + JSON.stringify(pay.excluded));
  } catch (e) {
    bad('E4. an inverting correction is non-positive on both sides', e && e.stack);
  }

  // ── E5: THE GPS ELEMENTS DID NOT MOVE ─────────────────────────────────
  // A correction supplies a TIME and never a LOCATION. If a sweep had moved
  // every clock read, an approved correction would clear "No GPS on
  // clock-out" without any GPS existing.
  {
    const src = fs.readFileSync(READINESS_SRC, 'utf8');
    const gpsRawReads = (src.match(/v\.clock_(in|out)_(lat|lng)/g) || []).length;
    const rawTimeReads = (src.match(/isIsoInstant\(v\.clock_(in|out)_at\)/g) || []).length;
    is(gpsRawReads > 0 && rawTimeReads === 0,
       'E5. the GPS elements still read the RAW coordinate fields ('
     + gpsRawReads + ' reads) while NO time element reads a raw clock field. '
     + 'A correction is a time and never a location',
       'gpsRawReads=' + gpsRawReads + ' rawTimeReads=' + rawTimeReads);
  }

  // ── E6: ONE SOURCE FOR THE RULE, not a second copy ───────────────────
  {
    const src = fs.readFileSync(READINESS_SRC, 'utf8');
    const requiresClock = /require\(['"]\.\/sen-evv-clock['"]\)/.test(src);
    const localApprovedRule = /status\s*===\s*['"]approved['"]/.test(src);
    is(requiresClock && !localApprovedRule,
       'E6. readiness gets the effective clock from api/_lib/sen-evv-clock.js '
     + 'and carries NO second copy of what "approved" means. A second copy is '
     + 'a second thing to drift on a compliance verdict',
       'requires sen-evv-clock=' + requiresClock
     + ' local approved rule=' + localApprovedRule);
  }

  // ── E7: THE CLIENT'S ANOMALY CHECK, lifted from the real page ─────────
  {
    const w = world(['senEffClock', 'senEvvException']);
    if (w.missing) {
      bad('E7. the client EVV anomaly check uses the effective clock',
          'could not lift from sairnsenior.html: ' + w.missing.join(', '));
    } else if (w.error) {
      cannot('E7. the client EVV anomaly check uses the effective clock',
             String(w.error));
    } else {
      const f = w.sandbox.senEvvException;
      const corrected = {
        clock_in_at: REC_IN, clock_out_at: null, status: 'in_progress',
        clock_in_lat: 41.1, clock_out_lat: 41.1,
        clock_corrections: [correction('clock_out_at', null, COR_OUT, 'approved')]
      };
      const pendingRow = {
        clock_in_at: REC_IN, clock_out_at: null, status: 'in_progress',
        clock_in_lat: 41.1, clock_out_lat: 41.1,
        clock_corrections: [correction('clock_out_at', null, COR_OUT, 'pending')]
      };
      const noGps = {
        clock_in_at: REC_IN, clock_out_at: COR_OUT, status: 'completed',
        clock_in_lat: 41.1, clock_out_lat: null
      };
      is(f(corrected) === null
         && f(pendingRow) === 'Clocked in, never clocked out'
         && f(noGps) === 'No GPS on clock-out',
         'E7. the client\'s EVV anomaly check reads the effective clock for '
       + 'the TIME SPAN (an approved correction clears "never clocked out", a '
       + 'pending one does not) and the RAW field for GPS',
         'corrected=' + JSON.stringify(f(corrected))
       + ' pending=' + JSON.stringify(f(pendingRow))
       + ' noGps=' + JSON.stringify(f(noGps)));
    }
  }

  // ── E8: THE ONE DISAGREEMENT THAT REMAINS, STATED ────────────────────
  // b16's freeze reads a CLOSED period as at paid_at; an EVV export reads now.
  // That is deliberate and it is the restatement trail. The arm asserts the
  // difference exists and is attributable -- a frozen run that did not say so
  // would be the silent restatement the freeze was built to prevent.
  try {
    const readiness = freshReadiness();
    const payroll = freshPayroll();
    const v = visitMissingClockOut('approved');
    const res = readiness.checkVisit(v, { id: 'C1' }, { id: 'E1' }, null);
    const pay = payroll.computePayroll({
      visits: [v], period_start: DAY, period_end: DAY, week_start_day: 'sunday',
      closed_periods: [{ period_start: '2026-10-01', period_end: '2026-10-31',
                         paid_at: DAY + 'T18:30:00.000Z' }],
      resolveRate: () => ({ status: 'applied', rate_per_hour: 20 })
    });
    const b = pay.caregivers && pay.caregivers[0];
    is(timeSpanMissing(res).length === 0
       && (!b || b.minutes === 0) && !!pay.period_closed
       && pay.period_closed.paid_at === DAY + 'T18:30:00.000Z',
       'E8. RE-AIMED b17 -- the disagreement survives ONLY for a caller that '
     + 'passes NO closed_periods (this arm passes null): pay says 0 minutes, '
     + 'the EVV check reads now, and period_closed names the instant so the '
     + 'difference is attributable. When the caller DOES pass the list the two '
     + 'agree -- api/b17-evv-closed-period-asof.test.js arms R1-R3 drive it',
       'evv time_span=' + timeSpanMissing(res).length
     + ' paidMinutes=' + (b && b.minutes)
     + ' period_closed=' + JSON.stringify(pay.period_closed));
  } catch (e) {
    bad('E8. RE-AIMED b17 -- the disagreement survives only without closed_periods',
        e && e.stack);
  }

  // ── E9: ABLATION -- put the raw read back, E1 must flip ──────────────
  if (e1ready && timeSpanMissing(e1ready).length === 0) {
    const r = ablate(A_READ, 'const outOk = isIsoInstant(v.clock_out_at);', () => {
      const readiness = freshReadiness();
      return readiness.checkVisit(visitMissingClockOut('approved'),
        { id: 'C1' }, { id: 'E1' }, null);
    });
    if (!r.ok) {
      cannot('E9. ABLATION -- the raw read put back flips E1', r.why);
    } else {
      const spans = timeSpanMissing(r.result);
      is(spans.length === 1,
         'E9. ABLATION -- with the clock-out read reverted to the raw field '
       + 'the same visit goes back to "no clock-out time recorded", so E1 is '
       + 'testing THAT read and not some other element',
         'ablated time_span=' + JSON.stringify(spans.map((m) => m.reason))
       + ' -- still clean, so E1 passes for another reason');
    }
  } else {
    cannot('E9. ABLATION -- the raw read put back flips E1',
           'E1 did not produce a clean time_span, so there is nothing to ablate');
  }

  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
