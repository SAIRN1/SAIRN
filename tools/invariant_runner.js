// tools/invariant_runner.js
// Property-test the platform's financial invariants against the REAL pure
// engines, and report ACCURACY and STABILITY as two separate numbers.
//
//     node tools/invariant_runner.js
//     node tools/invariant_runner.js --fixtures      # the blind lock alone
//     node tools/invariant_runner.js --cases 20000
//     node tools/invariant_runner.js --json
//
// ── WHY A PROPERTY RUNNER AND NOT A STATIC CHECK ─────────────────────────
// A static checker cannot verify that arithmetic holds. The most it can do is
// assert that an invariant assertion EXISTS somewhere -- which is a presence
// check, and a presence check that can never fail is the shape this platform
// keeps finding. These engines are pure (`api/_lib/ledger.js`: "Pure
// functions, no I/O"), so the invariant can be RUN: generate inputs, call the
// real exported function, and check the identity on its real output.
//
// ── THE BLIND LOCK, RUN IN ISOLATION FIRST ───────────────────────────────
// Every pass/fail criterion is decided against SYNTHETIC fixtures in
// tools/invariant_registry.js -- a deliberately unbalanced posting, a rollup
// off by a cent, a release exceeding what was accrued -- and THIS RUNNER
// REFUSES TO CALL A SINGLE REAL ENGINE UNTIL ALL OF THEM CLASSIFY AS WRITTEN.
// The fixtures run against the criteria ALONE, on hand-built objects, never
// alongside real engine output: a lock that rides beside live data can be
// satisfied by the data.
//
// ── TWO NUMBERS, NEVER ONE ───────────────────────────────────────────────
// ACCURACY  did this row pick the right invariant TYPE for this engine? The
//           declared type carries a DISCRIMINATOR over the engine's own output
//           shape. A row whose discriminator fails is MISCLASSIFIED, and that
//           is a different problem from an invariant that breaks.
// STABILITY of the generated cases, how many held? 9,999/10,000 is a finding.
//           Collapsing it to PASS throws away the only signal that matters.
//
// ── MARGIN IS REPORTED ONLY WHERE IT MEANS SOMETHING ─────────────────────
// Double-entry is exact, so it has no distance-to-violation. Reading the
// engines showed the same is true of ROLLUP: "stated equals the sum of its
// lines" is an equality. Margin is therefore reported for INEQUALITIES only --
// released <= accrued -- and the alarm is set at 1% of accrued, TIGHTER than
// the actual failure point of zero, so a run that came within a penny is a
// finding before it is a violation.
//
// ── WHAT IT CANNOT SEE, said here rather than discovered later ───────────
//   * any engine not in the registry. Four are classified by hand; every other
//     money-named Tier A resource is UNCOVERED and the count is printed;
//   * whether an invariant is the RIGHT invariant for the business. It checks
//     internal consistency, never that the rule matches what a customer is owed;
//   * anything that is not a pure function. A write path's behaviour under
//     retry is the idempotency checker's subject, not this one's.
//
// Exit 0 when every registered invariant is accurate and fully stable, 1 on
// any instability or misclassification, 2 when the fixtures fail -- which
// means NOTHING REAL WAS RUN.
'use strict';

const path = require('path');
const R = require(path.join(__dirname, 'invariant_registry.js'));

const argv = process.argv.slice(2);
const CASES = (function () {
  const i = argv.indexOf('--cases');
  return i >= 0 && argv[i + 1] ? Math.max(1, parseInt(argv[i + 1], 10)) : 10000;
})();

function runFixtures() {
  const bad = [];
  R.FIXTURES.forEach(function (f) {
    let got;
    try { got = !!f.holds(f.input); } catch (e) { got = 'threw: ' + e.message; }
    if (got !== f.expect) bad.push({ name: f.name, expect: f.expect, got: got });
  });
  R.MARGIN_FIXTURES.forEach(function (f) {
    let alarmed;
    try {
      alarmed = f.row.margin(f.o) < f.row.alarmAt(f.o);
    } catch (e) { alarmed = 'threw: ' + e.message; }
    if (alarmed !== f.expectAlarm) {
      bad.push({ name: f.name, expect: f.expectAlarm, got: alarmed });
    }
  });
  return bad;
}

function exercise(row) {
  const r = R.rng(20260913);
  let held = 0, ran = 0, discOK = 0, threw = 0;
  let worstMargin = null, alarms = 0, firstFail = null;
  for (let i = 0; i < CASES; i++) {
    let out;
    try { out = row.run(row.gen(r)); } catch (e) {
      threw++;
      if (!firstFail) firstFail = { case: i, error: String(e && e.message || e) };
      continue;
    }
    ran++;
    if (row.discriminator(out)) discOK++;
    let ok;
    try { ok = !!row.holds(out); } catch (e) { ok = false; }
    if (ok) held++;
    else if (!firstFail) {
      firstFail = { case: i, out: JSON.parse(JSON.stringify(
        Object.assign({}, out, { raw: undefined }))) };
    }
    if (row.margin) {
      const m = row.margin(out);
      if (worstMargin === null || m < worstMargin) worstMargin = m;
      if (m < row.alarmAt(out)) alarms++;
    }
  }
  return {
    id: row.id, engine: row.engine, type: row.type, evidence: row.evidence,
    // ACCURACY -- was the TYPE right? Separate field, never folded into stability.
    accuracy: { cases_with_expected_shape: discOK, cases_run: ran,
                verdict: (ran && discOK === ran) ? 'TYPE CONFIRMED'
                         : (discOK === 0 ? 'MISCLASSIFIED' : 'PARTIAL') },
    // STABILITY -- how often did it hold? Never collapsed to PASS.
    stability: { held: held, of: ran, threw: threw,
                 rate: ran ? (held / ran) : 0 },
    margin: row.margin ? { worst: worstMargin, alarms: alarms,
                           note: 'alarm is set at 1% of accrued, tighter than the '
                                 + 'violation point of 0' }
                       : { note: 'not reported: this invariant is an EQUALITY, and '
                                 + 'the distance to violating an equality is zero '
                                 + 'or it is already violated' },
    first_failure: firstFail
  };
}

function main() {
  const bad = runFixtures();
  console.log('FINANCIAL INVARIANT RUNNER -- registry ' + R.VERSION + ', report only');
  if (bad.length) {
    console.log('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING REAL WAS RUN.');
    console.log('     The fixtures are hand-built objects, checked against the criteria');
    console.log('     ALONE -- never alongside real engine output, because a lock that');
    console.log('     rides beside live data can be satisfied by the data.');
    bad.forEach(function (b) {
      console.log('     ' + b.name + '  expected ' + b.expect + ', got ' + b.got);
    });
    process.exit(2);
  }
  console.log('  blind lock: ' + (R.FIXTURES.length + R.MARGIN_FIXTURES.length) +
              '/' + (R.FIXTURES.length + R.MARGIN_FIXTURES.length) +
              ' synthetic fixtures correct, run in isolation before any engine was called.');
  if (argv.indexOf('--fixtures') >= 0) return 0;

  const results = R.REGISTRY.map(exercise);
  if (argv.indexOf('--json') >= 0) {
    console.log(JSON.stringify({ version: R.VERSION, cases: CASES, results: results },
                               null, 1));
  } else {
    console.log('  generated cases per engine: ' + CASES +
                '  (deterministic seed -- a failing case is reproducible)');
    console.log('');
    console.log('  ENGINE                            TYPE          ACCURACY         STABILITY');
    results.forEach(function (r) {
      console.log('  ' + r.id.padEnd(34) + r.type.padEnd(14) +
                  r.accuracy.verdict.padEnd(17) +
                  (r.stability.held + '/' + r.stability.of) +
                  (r.stability.threw ? '  (' + r.stability.threw + ' threw)' : ''));
    });
    results.forEach(function (r) {
      console.log('');
      console.log('  ' + r.id);
      console.log('    why this type : ' + r.evidence);
      console.log('    accuracy      : ' + r.accuracy.verdict + ' -- ' +
                  r.accuracy.cases_with_expected_shape + '/' + r.accuracy.cases_run +
                  ' outputs carried the shape the declared type requires');
      console.log('    stability     : ' + r.stability.held + '/' + r.stability.of +
                  ' held' + (r.stability.rate === 1 ? '' :
                  '   <- NOT 10000/10000. A single break is a finding.'));
      if (r.margin.worst !== undefined && r.margin.worst !== null) {
        // PRECISION MATTERS HERE. Two decimals rendered a 0.005 tolerance band
        // as "0.01" -- wider than the band it was measuring, which makes the
        // number worse than useless. Six decimals, so a margin can never be
        // displayed as larger than the tolerance it sits inside.
        console.log('    margin        : worst ' + r.margin.worst.toFixed(6) +
                    ', ' + r.margin.alarms + ' run(s) inside the alarm band');
        console.log('                    ' + r.margin.note);
      } else {
        console.log('    margin        : ' + r.margin.note);
      }
      if (r.first_failure) {
        console.log('    FIRST FAILURE : ' + JSON.stringify(r.first_failure));
      }
    });
    console.log('');
    console.log('  COVERAGE, stated rather than implied: ' + R.REGISTRY.length +
                ' engines are classified by hand. Every other money-named Tier A');
    console.log('  resource is UNCOVERED by this runner -- 30 were counted, and a');
    console.log('  clean result here says nothing about the rest.');
  }
  const bad2 = results.filter(function (r) {
    return r.accuracy.verdict !== 'TYPE CONFIRMED' || r.stability.rate !== 1;
  });
  return bad2.length ? 1 : 0;
}

process.exit(main());
