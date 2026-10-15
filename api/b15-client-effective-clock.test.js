// api/b15-client-effective-clock.test.js
//
// Run:  node api/b15-client-effective-clock.test.js
//
// FOURTH's b23 F3: sairnsenior.html reads the raw clock about twenty times and
// uses `effective_clock` ZERO times. Measured at the start of b15:
//
//   grep -c effective_clock sairnsenior.html                  -> 0
//   grep -c 'clock_in_at\|clock_out_at' sairnsenior.html      -> 25 lines
//
// So every client-side figure derived from a clock -- delivered hours, the
// authorisation burn-down, the billed hours on a claim -- ignored an APPROVED
// correction, the same way payroll did (F1). The server read branch has been
// attaching `effective_clock` to every corrected visit since b13 and nothing
// consumed it.
//
// ── THE SITES ARE NOT ALL THE SAME AND THEY ARE NOT ALL CHANGED ───────────
// Three kinds, and only two of them should move:
//
//   DURATION / MONEY   delivered hours, visitHours(), the authorisation
//                      burn-down. These must use the effective value: they are
//                      the client-side mirror of the payroll bug.
//   DISPLAY            "Clocked in <time>". Effective value, WITH the original
//                      still visible -- api/_lib/sen-evv-clock.js's own rule is
//                      that a screen showing only the corrected value has
//                      become the overwrite the trail exists to avoid.
//   CLOCK-ACTION GATES `canClockIn = !v.clock_in_at`, and the payloads
//                      vsClockIn/vsClockOut send. THESE STAY RAW and that is
//                      the point: whether a clock EVENT was recorded is a fact
//                      about the raw field. Substituting here would let an
//                      approved correction re-enable the Clock In button on a
//                      visit that was already clocked.
//   EVV ANOMALIES      "clocked in, never clocked out", "no GPS on clock-in".
//                      LEFT RAW AND NOT TOUCHED: that is fourth's F2, which is
//                      HELD FOR MICHAEL. Building it here would be deciding a
//                      question that was explicitly reserved.
//
// Every arm extracts the real functions from sairnsenior.html and runs them in
// a vm. A reimplementation would pass against the unfixed page.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '..');

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

const DAY = '2026-10-06';
const REC_IN = DAY + 'T13:00:00.000Z';
const COR_IN = DAY + 'T12:00:00.000Z';
const REC_OUT = DAY + 'T17:00:00.000Z';

function approved(field, from, to) {
  return { field: field, original_at: from, proposed_at: to,
           reason_code: 'transcription_error', proposed_by: 'E1',
           proposed_at_server: from, status: 'approved',
           approved_by: 'S1', approved_at_server: from };
}
// A visit as the SERVER returns it for a corrected row: the raw fields
// untouched, the corrections on the row, and `effective_clock` added by
// api/sd-data.js's read branch.
function serverVisit() {
  return { id: 'V1', assigned_employee_id: 'E1', scheduled_date: DAY,
           client_id: 'C1', status: 'completed',
           clock_in_at: REC_IN, clock_out_at: REC_OUT,
           clock_corrections: [approved('clock_in_at', REC_IN, COR_IN)],
           effective_clock: { clock_in_at: { value: COR_IN, corrected: true,
                                             original_at: REC_IN,
                                             pending: false, pending_count: 0 } } };
}
// The same visit as a LOCAL row that has not round-tripped: corrections
// present, no `effective_clock` key. The helper has to handle both or it only
// works after a hydrate.
function localVisit() {
  const v = serverVisit();
  delete v.effective_clock;
  return v;
}
function uncorrected() {
  return { id: 'V2', assigned_employee_id: 'E1', scheduled_date: DAY,
           client_id: 'C1', status: 'completed',
           clock_in_at: REC_IN, clock_out_at: REC_OUT };
}
function pendingVisit() {
  const v = localVisit();
  v.clock_corrections[0].status = 'pending';
  v.clock_corrections[0].approved_by = null;
  return v;
}

console.log('b15 / fourth b23 F3. the client must read the EFFECTIVE clock\n');

(function () {
  if (HTML === null) {
    ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8'].forEach(function (n) {
      cannot(n + '. sairnsenior.html is not readable', 'ENOENT');
    });
    return;
  }

  // ── THE HELPER EXISTS AT ALL ────────────────────────────────────────────
  const w = world(['senEffClock']);
  if (w.missing) {
    // A MISSING FUNCTION IS A FAIL, NOT AN UNPROVEN. "The helper is not there"
    // and "I could not measure it" are different answers.
    ['C1', 'C2', 'C3', 'C4'].forEach(function (n) {
      bad(n + '. senEffClock() is not in sairnsenior.html -- the helper the '
        + 'duration and display sites need does not exist',
          'missing: ' + w.missing.join(', '));
    });
  } else if (w.error) {
    cannot('C1. senEffClock() would not run', String(w.error));
  } else {
    const f = w.sandbox.senEffClock;
    is(f(serverVisit(), 'clock_in_at') === COR_IN,
       'C1. senEffClock() returns the APPROVED corrected value when the server '
     + 'has attached effective_clock',
       'got ' + JSON.stringify(f(serverVisit(), 'clock_in_at')));
    is(f(localVisit(), 'clock_in_at') === COR_IN,
       'C2. ...and computes it from clock_corrections when the row has NOT '
     + 'round-tripped. A helper that only works after a hydrate is a helper '
     + 'that reports the raw time on every locally-created visit',
       'got ' + JSON.stringify(f(localVisit(), 'clock_in_at')));
    is(f(pendingVisit(), 'clock_in_at') === REC_IN,
       'C3. CONTROL -- a PENDING correction is IGNORED and the recorded time '
     + 'is returned. Without this arm the helper could apply every correction, '
     + 'which would show and bill an unverified self-asserted time',
       'got ' + JSON.stringify(f(pendingVisit(), 'clock_in_at')));
    is(f(uncorrected(), 'clock_in_at') === REC_IN
       && f({}, 'clock_in_at') === null
       && f(null, 'clock_in_at') === null,
       'C4. CONTROL -- an uncorrected row returns its raw value, and a row '
     + 'with no clock at all returns null rather than undefined. Every caller '
     + 'below tests the result for truthiness',
       'uncorrected=' + JSON.stringify(f(uncorrected(), 'clock_in_at'))
     + ' empty=' + JSON.stringify(f({}, 'clock_in_at')));
  }

  // ── THE DURATION SITES USE IT ───────────────────────────────────────────
  const wh = world(['senEffClock', 'visitHours', 'visitClockReversed']);
  if (wh.missing) {
    bad('C5. visitHours()/visitClockReversed() could not be extracted with '
      + 'the helper', 'missing: ' + wh.missing.join(', '));
    bad('C6. depends on C5', 'missing: ' + wh.missing.join(', '));
  } else if (wh.error) {
    cannot('C5. the extracted duration functions would not run', String(wh.error));
  } else {
    const vh = wh.sandbox.visitHours;
    is(vh(serverVisit()) === 5 && vh(localVisit()) === 5,
       'C6a. visitHours() is 5 on a visit with an APPROVED correction moving '
     + 'the clock-in an hour earlier -- not 4. This is the client-side mirror '
     + 'of the payroll bug: the figure a claim is built from',
       'server=' + vh(serverVisit()) + ' local=' + vh(localVisit()));
    is(vh(uncorrected()) === 4 && vh(pendingVisit()) === 4,
       'C6b. CONTROL -- 4 hours with no correction and 4 with a PENDING one',
       'uncorrected=' + vh(uncorrected()) + ' pending=' + vh(pendingVisit()));
    const rev = wh.sandbox.visitClockReversed;
    const bad1 = localVisit();
    bad1.clock_corrections = [approved('clock_in_at', REC_IN, DAY + 'T23:00:00.000Z')];
    is(rev(bad1) === true && rev(uncorrected()) === false,
       'C6c. visitClockReversed() sees the EFFECTIVE values, so an approved '
     + 'correction that inverts a visit is detected as reversed instead of '
     + 'quietly producing a negative duration downstream',
       'inverted=' + rev(bad1) + ' control=' + rev(uncorrected()));
  }

  // ── THE GATES AND THE EVV ANOMALIES STAY RAW ────────────────────────────
  {
    // Read off the SOURCE rather than driven, because these are the sites that
    // must NOT have changed and the cheapest proof of that is that the raw
    // field is still what they read.
    const gateLine = /var canClockIn\s*=\s*!v\.clock_in_at/.test(HTML);
    const gateLine2 = /var canClockOut\s*=\s*v\.clock_in_at\s*&&\s*!v\.clock_out_at/.test(HTML);
    is(gateLine && gateLine2,
       'C7. CONTROL -- the clock-action gates still read the RAW field. '
     + 'Whether a clock EVENT was recorded is a fact about the raw value, and '
     + 'substituting here would let an approved correction re-enable the Clock '
     + 'In button on a visit that was already clocked',
       'canClockIn=' + gateLine + ' canClockOut=' + gateLine2);
    const anomalyRaw = /v\.clock_in_at&&\(!v\.clock_in_lat/.test(HTML);
    is(anomalyRaw,
       'C8. CONTROL -- the EVV anomaly checks still read the RAW field, '
     + 'UNTOUCHED. That is fourth\'s F2 and it is HELD FOR MICHAEL; changing '
     + 'it here would be deciding a question that was explicitly reserved',
       'the raw EVV anomaly read was not found');
  }

  // ── AND THE COUNT fourth MEASURED HAS MOVED ─────────────────────────────
  {
    const uses = (HTML.match(/senEffClock\(/g) || []).length;
    is(uses >= 6,
       'C9. senEffClock() is actually CALLED in the page, at least six times '
     + '(the two delivered-hours sites, visitHours, visitClockReversed and the '
     + 'two display rows). A helper nothing calls is the same zero fourth '
     + 'measured, with an extra function in the file',
       'senEffClock( appears ' + uses + ' time(s)');
  }
})();

console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
process.exit(fail ? 1 : (unproven ? 3 : 0));
