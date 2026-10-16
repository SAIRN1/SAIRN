// api/b17-evv-closed-period-asof.test.js
//
// Run:  node api/b17-evv-closed-period-asof.test.js
//
// ROUTED BY fourth, b26, Q(b)2: "MICHAEL'S SAME-CLOCK DECISION IS NOT FULLY
// IMPLEMENTED. api/_lib/sen-evv-readiness.js:339-340 calls
// effectiveClock(v, field) -- the no-as-of form. So for an OPEN period EVV and
// pay agree, and FOR A CLOSED PERIOD PAY READS AS AT paid_at WHILE EVV READS
// NOW. effectiveClockAsOf already exists, so the gap is threading the as-of
// through, not building anything. Reported, not decided by me -- this is the
// shape of Michael's decision."
//
// ── WHAT THE DISAGREEMENT ACTUALLY LOOKS LIKE ─────────────────────────────
// One visit, clock-out supplied ONLY by a correction approved AFTER the period
// was paid. b16's own arm E8 measured it:
//
//     pay  -> 0 minutes      (as at paid_at the clock-out did not exist)
//     EVV  -> ready          (as at now it does)
//
// A state EVV programme reconciling the export against the payroll register
// finds a visit the export calls complete and the register pays nothing for.
// Neither number looks wrong to a reader of one of them, which is the whole
// reason b16's F2 made the two read one function in the first place -- and it
// only half-landed, because the ARGUMENT was not threaded with it.
//
// ── THE FIX IS ONE SOURCE FOR TWO QUESTIONS, NOT A SECOND COPY ───────────
// "Which closing contains this service date" and "what instant was it paid
// at" are PAYROLL facts. b17 extracts them from computePayroll into
// api/_lib/sen-payroll.js's exported normalizeClosedPeriods /
// closedPeriodFor, and the readiness check CONSUMES them. Arm R6 asserts
// there is no second containment test in the readiness file, because a second
// copy of this rule is the exact defect shape F1 was.
//
// ── AND IT FAILS CLOSED ON A LIST IT CANNOT DATE (R5) ────────────────────
// computePayroll REFUSES a run on an undatable closed period. The readiness
// check must not quietly fall back to reading NOW, because that is the
// disagreement coming back by a route nobody is watching. It reports
// `read_as_of_unavailable` and makes the visit not-ready rather than issuing
// a verdict it cannot stand behind.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');

const READINESS_SRC = path.join(__dirname, '_lib', 'sen-evv-readiness.js');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

function freshReadiness() {
  delete require.cache[require.resolve('./_lib/sen-evv-readiness')];
  delete require.cache[require.resolve('./_lib/sen-evv-clock')];
  delete require.cache[require.resolve('./_lib/sen-payroll')];
  return require('./_lib/sen-evv-readiness');
}
function freshPayroll() {
  delete require.cache[require.resolve('./_lib/sen-payroll')];
  delete require.cache[require.resolve('./_lib/sen-evv-clock')];
  return require('./_lib/sen-payroll');
}

// ── b16's E8 FIXTURE, CARRIED FORWARD UNCHANGED ──────────────────────────
// Same visit, same instants, so the numbers here are comparable to the ones
// the disagreement was measured with.
const DAY = '2026-10-06';
const REC_IN = DAY + 'T09:00:00.000Z';
const COR_OUT = DAY + 'T13:00:00.000Z';         // 240 minutes, by correction
const PAID_AT = DAY + 'T18:30:00.000Z';         // the freeze instant
const APPROVED_AFTER = DAY + 'T19:00:00.000Z';  // AFTER paid_at
const APPROVED_BEFORE = DAY + 'T18:00:00.000Z'; // BEFORE paid_at

const CLOSED = { period_start: '2026-10-01', period_end: '2026-10-31',
                 paid_at: PAID_AT };

function visitMissingClockOut(approvedAtServer) {
  return {
    id: 'V1', visit_id: 'V1', assigned_employee_id: 'E1', client_id: 'C1',
    scheduled_date: DAY, status: 'completed',
    clock_in_at: REC_IN, clock_out_at: null,
    clock_in_lat: 41.1, clock_in_lng: -81.5,
    clock_out_lat: 41.1, clock_out_lng: -81.5,
    service_code: 'T1019', service_description: 'Personal care',
    clock_corrections: [{
      id: 'C1', field: 'clock_out_at', original_at: null, proposed_at: COR_OUT,
      reason_code: 'FORGOT_TO_CLOCK_OUT', filed_by: 'E1',
      filed_at_server: DAY + 'T17:00:00.000Z',
      status: 'approved', approved_by: 'S1',
      approved_at_server: approvedAtServer
    }]
  };
}

// ── WHY NO ARM ASSERTS `ready === true` ──────────────────────────────────
// This fixture can NEVER be ready, and that is a fact about the app rather
// than about the fixture: `service_type`, the client's payer member ID and the
// caregiver's state ID are three elements SAIRNsenior does not capture at all,
// so `missing` is never empty for any visit. b16's E8 asserted on the
// time_span element alone for exactly this reason and these arms do the same.
// Asserting `ready` here would be a passing arm that tests the three
// uncaptured fields instead of the clock.
function timeSpanMissing(res) {
  return ((res && res.missing) || []).filter((m) => m.element === 'time_span');
}
function locationNotes(res) {
  const m = ((res && res.missing) || []).filter((x) => x.element === 'location');
  const w = ((res && res.warnings) || []).filter((x) => x.element === 'location');
  return m.map((x) => 'MISSING:' + x.reason).concat(w.map((x) => 'WARN:' + x.reason));
}

function payMinutes(visit, closedPeriods) {
  const payroll = freshPayroll();
  const out = payroll.computePayroll({
    visits: [visit], period_start: DAY, period_end: DAY,
    week_start_day: 'sunday', closed_periods: closedPeriods,
    resolveRate: () => ({ status: 'applied', rate_per_hour: 20 })
  });
  const b = out.caregivers && out.caregivers[0];
  return { minutes: b ? b.minutes : 0, out: out };
}

function ablate(anchor, replacement, fn) {
  const src = fs.readFileSync(READINESS_SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 1) return { ok: false, why: 'anchor occurs ' + n + ' times, not 1' };
  const backup = src;
  try {
    fs.writeFileSync(READINESS_SRC, src.split(anchor).join(replacement));
    const back = fs.readFileSync(READINESS_SRC, 'utf8');
    if (back.indexOf(replacement) === -1) {
      return { ok: false, why: 'the mutant did not land on disk' };
    }
    return { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(READINESS_SRC, backup);
    if (fs.readFileSync(READINESS_SRC, 'utf8') !== backup) {
      console.log('  HARD ERROR the ablation did not restore '
        + 'api/_lib/sen-evv-readiness.js -- DO NOT COMMIT, the file on disk is a mutant');
      process.exit(1);
    }
  }
}

function main() {
  console.log('api/b17-evv-closed-period-asof.test.js');
  console.log('  a CLOSED period\'s EVV check reads the clock as at paid_at, like pay does');

  // ── R1: THE DISAGREEMENT IS GONE WHEN THE CHECK IS TOLD ABOUT THE FREEZE
  let r1 = null;
  try {
    const readiness = freshReadiness();
    r1 = readiness.checkVisit(visitMissingClockOut(APPROVED_AFTER),
      { id: 'C1' }, { id: 'E1' }, { closed_periods: [CLOSED] });
    const spans = timeSpanMissing(r1);
    is(spans.length === 1 && /No clock-out time recorded/.test(spans[0].reason)
       && r1.read_as_of === PAID_AT
       && r1.period_closed && r1.period_closed.paid_at === PAID_AT,
       'R1. a correction approved AFTER paid_at does not make a CLOSED visit submittable',
       JSON.stringify({ spans: spans.map((m) => m.reason),
         as_of: r1.read_as_of, closed: r1.period_closed }));
  } catch (e) { bad('R1. the closed-period EVV read is as at paid_at', e && e.stack); }

  // ── R2: AND PAY SAYS THE SAME THING ABOUT THE SAME VISIT ───────────────
  // THIS IS THE ARM THAT MATTERS. b16's E8 measured EVV=ready against
  // pay=0 minutes. Both halves are asserted here in one place so the
  // agreement is the assertion rather than two numbers in two files.
  try {
    const v = visitMissingClockOut(APPROVED_AFTER);
    const p = payMinutes(v, [CLOSED]);
    is(p.minutes === 0 && r1 && timeSpanMissing(r1).length === 1,
       'R2. AGREEMENT -- pay pays 0 minutes and EVV reports the clock-out missing, on one visit',
       'payMinutes=' + p.minutes + ' evvSpans=' + (r1 ? timeSpanMissing(r1).length : -1));
  } catch (e) { bad('R2. AGREEMENT on the frozen visit', e && e.stack); }

  // ── R3: AND THEY AGREE IN THE OTHER DIRECTION TOO ──────────────────────
  // A correction approved BEFORE paid_at WAS in the figure that was paid, so
  // the visit really is complete as at the freeze instant. An implementation
  // that simply refused every closed visit would pass R1 and R2 and be wrong.
  try {
    const readiness = freshReadiness();
    const v = visitMissingClockOut(APPROVED_BEFORE);
    const res = readiness.checkVisit(v, { id: 'C1' }, { id: 'E1' },
      { closed_periods: [CLOSED] });
    const p = payMinutes(v, [CLOSED]);
    is(timeSpanMissing(res).length === 0 && res.read_as_of === PAID_AT
       && p.minutes === 240,
       'R3. AGREEMENT -- a correction approved BEFORE paid_at leaves the clock '
     + 'COMPLETE and paid 240 minutes, so R1 is not "every closed visit is refused"',
       'evvSpans=' + timeSpanMissing(res).length + ' asOf=' + res.read_as_of
       + ' payMinutes=' + p.minutes);
  } catch (e) { bad('R3. AGREEMENT in the other direction', e && e.stack); }

  // ── R4: BACKWARD COMPATIBILITY. No closed_periods -> exactly b16. ──────
  // Every existing caller passes `{ state }` or null. If this arm moves, the
  // change is not additive and api/sd-data.js's EVV action has changed answer
  // for every agency that has never closed a period.
  try {
    const readiness = freshReadiness();
    const a = readiness.checkVisit(visitMissingClockOut(APPROVED_AFTER),
      { id: 'C1' }, { id: 'E1' }, null);
    const b = readiness.checkVisit(visitMissingClockOut(APPROVED_AFTER),
      { id: 'C1' }, { id: 'E1' }, { state: 'OH' });
    is(timeSpanMissing(a).length === 0 && a.read_as_of === null
       && a.read_as_of_unavailable === false && a.period_closed === null
       && timeSpanMissing(b).length === 0 && b.read_as_of === null,
       'R4. CONTROL -- with NO closed_periods the answer is b16\'s: the clock-out '
     + 'is present, read_as_of is null and nothing claims a freeze',
       JSON.stringify({ aSpans: timeSpanMissing(a).length, aAsOf: a.read_as_of,
         aUnavail: a.read_as_of_unavailable, aClosed: a.period_closed,
         bSpans: timeSpanMissing(b).length }));
  } catch (e) { bad('R4. CONTROL -- no closed_periods', e && e.stack); }

  // ── R5: AN UNDATABLE CLOSED PERIOD FAILS CLOSED ────────────────────────
  // computePayroll REFUSES the run. The readiness check must not silently
  // read NOW instead, which would be the disagreement returning by a route
  // nobody is watching. Three states, and this is the third.
  try {
    const readiness = freshReadiness();
    const res = readiness.checkVisit(visitMissingClockOut(APPROVED_AFTER),
      { id: 'C1' }, { id: 'E1' },
      { closed_periods: [{ period_start: '2026-10-01', period_end: '2026-10-31',
                           paid_at: 'not an instant' }] });
    const spans = timeSpanMissing(res);
    is(res.ready === false && res.read_as_of === null
       && res.read_as_of_unavailable === true
       && spans.length === 1 && /cannot be dated|could not be dated/i.test(spans[0].reason),
       'R5. FAILS CLOSED -- an undatable closed period makes the visit not ready '
     + 'and SAYS the clock could not be read as of anything',
       JSON.stringify({ ready: res.ready, unavailable: res.read_as_of_unavailable,
         spans: spans.map((m) => m.reason) }));
  } catch (e) { bad('R5. an undatable closed period fails closed', e && e.stack); }

  // ── R6: ONE IMPLEMENTATION, asserted structurally ──────────────────────
  // The readiness file must CONSUME api/_lib/sen-payroll.js's exported
  // helpers and must not carry its own containment test. A second copy would
  // drift, and the drift would be invisible on both sides -- the file's own
  // F2 note already says that about the approval rule.
  try {
    const src = fs.readFileSync(READINESS_SRC, 'utf8');
    const usesHelper = /closedPeriodFor\s*\(/.test(src)
      && /normalizeClosedPeriods\s*\(/.test(src)
      && /require\(['"]\.\/sen-payroll['"]\)/.test(src);
    // A hand-rolled containment test looks like `>= c.period_start` or
    // `<= period_end`. Either one in this file means the rule was copied.
    const ownCopy = /period_start\s*&&|>=\s*[A-Za-z_.$]*period_start|<=\s*[A-Za-z_.$]*period_end/
      .test(src);
    is(usesHelper && !ownCopy,
       'R6. the readiness check CONSUMES the payroll helpers and carries no '
     + 'second copy of "which closing contains this service date"',
       'usesHelper=' + usesHelper + ' ownCopy=' + ownCopy);
  } catch (e) { bad('R6. one implementation of the closing lookup', e && e.stack); }

  // ── R7: GPS STILL DID NOT MOVE ─────────────────────────────────────────
  // b16's E5 asserts this for the no-as-of form. Threading an as-of through
  // must not reach the location elements: a correction supplies a TIME and
  // never a COORDINATE, and an as-of that cleared "no GPS" would be
  // asserting a location that does not exist.
  try {
    const readiness = freshReadiness();
    const v = visitMissingClockOut(APPROVED_AFTER);
    v.clock_out_lat = null; v.clock_out_lng = null;
    const withFreeze = readiness.checkVisit(v, { id: 'C1' }, { id: 'E1' },
      { closed_periods: [CLOSED] });
    const without = readiness.checkVisit(v, { id: 'C1' }, { id: 'E1' }, null);
    const a = locationNotes(withFreeze), b2 = locationNotes(without);
    is(a.length >= 1 && JSON.stringify(a) === JSON.stringify(b2),
       'R7. GPS did not move -- the location verdict on a clock-out with no '
     + 'coordinate is BYTE-IDENTICAL with and without the freeze',
       JSON.stringify({ withFreeze: a, without: b2 }));
  } catch (e) { bad('R7. GPS did not move', e && e.stack); }

  // ── R8: summarize() THREADS IT TOO ─────────────────────────────────────
  // The batch path is the one api/sd-data.js actually calls. A per-visit fix
  // that the batch path does not carry is the half-landing this arm exists
  // to stop happening twice.
  try {
    const readiness = freshReadiness();
    const sum = readiness.summarize([visitMissingClockOut(APPROVED_AFTER)],
      { C1: { id: 'C1' } }, { E1: { id: 'E1' } }, { closed_periods: [CLOSED] });
    const r = sum.results && sum.results[0];
    is(sum.not_ready === 1 && sum.ready === 0
       && r && r.read_as_of === PAID_AT
       && timeSpanMissing(r).length === 1,
       'R8. summarize() passes closed_periods through to every visit',
       JSON.stringify({ ready: sum.ready, not_ready: sum.not_ready,
         as_of: r && r.read_as_of }));
  } catch (e) { bad('R8. summarize threads closed_periods', e && e.stack); }

  // ── R9: ABLATION. Put the no-as-of read back and R1 must flip. ─────────
  const A_READ = "const effIn = senEvvClock.effectiveClockAsOf(v, 'clock_in_at', asOf).value;";
  try {
    const r = ablate(A_READ,
      "const effIn = senEvvClock.effectiveClock(v, 'clock_in_at').value;", () => {
        const readiness = freshReadiness();
        return readiness.checkVisit(visitMissingClockOut(APPROVED_AFTER),
          { id: 'C1' }, { id: 'E1' }, { closed_periods: [CLOSED] });
      });
    if (!r.ok) {
      cannot('R9. ABLATION -- the no-as-of read put back flips R1', r.why);
    } else {
      // clock_in is read raw on BOTH paths, so neutering the clock_in read
      // alone must not change the verdict -- which proves the clock_OUT read
      // is what R1 is about. The second half of the ablation does that one.
      const spans = timeSpanMissing(r.result);
      is(spans.length === 1,
         'R9a. ABLATION -- neutering the clock_IN as-of leaves R1 unchanged, so '
       + 'R1 is about the clock-OUT read',
         JSON.stringify(spans.map((m) => m.reason)));
    }
  } catch (e) { bad('R9a. ABLATION on the clock_in read', e && e.stack); }

  const A_READ_OUT = "const effOut = senEvvClock.effectiveClockAsOf(v, 'clock_out_at', asOf).value;";
  try {
    const r = ablate(A_READ_OUT,
      "const effOut = senEvvClock.effectiveClock(v, 'clock_out_at').value;", () => {
        const readiness = freshReadiness();
        return readiness.checkVisit(visitMissingClockOut(APPROVED_AFTER),
          { id: 'C1' }, { id: 'E1' }, { closed_periods: [CLOSED] });
      });
    if (!r.ok) {
      cannot('R9b. ABLATION -- the no-as-of clock-OUT read put back flips R1', r.why);
    } else {
      const spans = timeSpanMissing(r.result);
      is(spans.length === 0,
         'R9b. ABLATION -- with the clock-OUT as-of removed the frozen visit\'s '
       + 'clock-out comes BACK, so R1 is testing THAT argument and not '
       + 'something else (`ready` is not asserted -- see the note on why)',
         JSON.stringify({ spans: spans.length, ready: r.result.ready }));
    }
  } catch (e) { bad('R9b. ABLATION on the clock_out as-of', e && e.stack); }

  console.log('');
  console.log('  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
