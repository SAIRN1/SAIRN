// Isolated test of api/_lib/sen-evv-readiness.js.
// PURE engine, so every case runs against the REAL module -- no fixtures of
// the module's own output, no mocks, no infrastructure.
'use strict';
const path = require('path');
const m = require(path.join(__dirname, '..', '..', 'api/_lib/sen-evv-readiness.js'));

let pass = 0, fail = 0;
function check(n, f) { try { f(); pass++; console.log('PASS ' + n); } catch (e) { fail++; console.log('FAIL ' + n + ' -- ' + e.message); } }
function assertEq(a, b, msg) {
  if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(b) + ' got ' + JSON.stringify(a));
}
function assertTrue(v, msg) { if (!v) throw new Error(msg || 'expected truthy'); }
function assertFalse(v, msg) { if (v) throw new Error(msg || 'expected falsy'); }
function missingElements(r) { return r.missing.map((x) => x.element).sort(); }

// A visit that satisfies all six elements. Every test below starts from this
// and removes ONE thing, so a failure names exactly which element broke.
function fullVisit(over) {
  return Object.assign({
    id: 'VS-1', status: 'completed', client_id: 'CL-1', assigned_employee_id: 'EMP-1',
    service_type: 'personal_care', scheduled_date: '2026-08-27',
    clock_in_at: '2026-08-27T13:00:00.000Z', clock_out_at: '2026-08-27T15:00:00.000Z',
    clock_in_lat: 41.49, clock_in_lng: -81.69,
    clock_out_lat: 41.49, clock_out_lng: -81.69
  }, over || {});
}
const FULL_CLIENT = { id: 'CL-1', name: 'A. Client', member_id: 'MED-99' };
const FULL_CG = { id: 'EMP-1', name: 'B. Caregiver', state_caregiver_id: 'OH-CG-7' };

// ── the happy path exists and is reachable ───────────────────────────────
check('a fully-populated completed visit is READY with nothing missing', () => {
  const r = m.checkVisit(fullVisit(), FULL_CLIENT, FULL_CG, { state: 'OH' });
  assertEq(r.missing, []);
  assertTrue(r.ready);
  assertTrue(r.checkable);
});

// ── not-finished is NOT the same as not-ready ────────────────────────────
check('scheduled and in_progress visits are NOT checkable and report no gaps', () => {
  ['scheduled', 'in_progress'].forEach((s) => {
    const r = m.checkVisit(fullVisit({ status: s }), FULL_CLIENT, FULL_CG, {});
    assertFalse(r.checkable, s + ' should not be checkable');
    assertEq(r.missing, [], s + ' should report no missing');
    assertFalse(r.ready, s + ' must not claim ready');
  });
});

check('an unknown status is not checkable either -- it is not silently treated as completed', () => {
  const r = m.checkVisit(fullVisit({ status: 'cancelled' }), FULL_CLIENT, FULL_CG, {});
  assertFalse(r.checkable);
  assertEq(r.missing, []);
});

// ── the four elements SAIRNsenior genuinely cannot supply today ──────────
check('service_type is missing because the app captures none', () => {
  const r = m.checkVisit(fullVisit({ service_type: undefined }), FULL_CLIENT, FULL_CG, {});
  assertEq(missingElements(r), ['service_type']);
  assertFalse(r.ready);
});

check('a client with no member_id fails on recipient, even with a name', () => {
  const r = m.checkVisit(fullVisit(), { id: 'CL-1', name: 'A. Client' }, FULL_CG, {});
  assertEq(missingElements(r), ['recipient']);
  assertTrue(/member\/Medicaid ID/.test(r.missing[0].reason), 'reason should name the member ID');
});

check('a caregiver with no state_caregiver_id fails on provider', () => {
  const r = m.checkVisit(fullVisit(), FULL_CLIENT, { id: 'EMP-1', name: 'B. Caregiver' }, {});
  assertEq(missingElements(r), ['provider']);
});

check('an unresolved client or caregiver reference is reported, not ignored', () => {
  assertEq(missingElements(m.checkVisit(fullVisit(), null, FULL_CG, {})), ['recipient']);
  assertEq(missingElements(m.checkVisit(fullVisit(), FULL_CLIENT, null, {})), ['provider']);
});

// ── location: the real behaviour of the live clock-in path ──────────────
check('NO GPS at all fails location -- this is the live default when permission is denied', () => {
  const r = m.checkVisit(fullVisit({
    clock_in_lat: undefined, clock_in_lng: undefined, clock_out_lat: undefined, clock_out_lng: undefined
  }), FULL_CLIENT, FULL_CG, {});
  assertEq(missingElements(r), ['location']);
});

check('PARTIAL GPS warns rather than fails, and names the ambiguity', () => {
  const inOnly = m.checkVisit(fullVisit({ clock_out_lat: undefined, clock_out_lng: undefined }), FULL_CLIENT, FULL_CG, {});
  assertEq(inOnly.missing, [], 'partial location must not be a hard miss');
  assertEq(inOnly.warnings.length, 1);
  assertTrue(/has not been verified/.test(inOnly.warnings[0].reason), 'warning must disclose the unverified part');
  assertTrue(inOnly.ready, 'a warning alone does not block readiness');

  const outOnly = m.checkVisit(fullVisit({ clock_in_lat: undefined, clock_in_lng: undefined }), FULL_CLIENT, FULL_CG, {});
  assertEq(outOnly.warnings.length, 1);
});

check('a lone latitude is NOT a location -- both halves are required', () => {
  const r = m.checkVisit(fullVisit({
    clock_in_lng: undefined, clock_out_lat: undefined, clock_out_lng: undefined
  }), FULL_CLIENT, FULL_CG, {});
  assertEq(missingElements(r), ['location']);
});

check('zero is a VALID coordinate and must not be discarded by a truthiness test', () => {
  const r = m.checkVisit(fullVisit({
    clock_in_lat: 0, clock_in_lng: 0, clock_out_lat: 0, clock_out_lng: 0
  }), FULL_CLIENT, FULL_CG, {});
  assertEq(r.missing, [], '0,0 is a real coordinate pair');
  assertEq(r.warnings, []);
});

check('NaN and Infinity are refused as coordinates', () => {
  [NaN, Infinity, -Infinity].forEach((bad) => {
    const r = m.checkVisit(fullVisit({
      clock_in_lat: bad, clock_in_lng: bad, clock_out_lat: bad, clock_out_lng: bad
    }), FULL_CLIENT, FULL_CG, {});
    assertEq(missingElements(r), ['location'], String(bad) + ' must not pass as a coordinate');
  });
});

check('a stringified coordinate is refused -- "41.49" is not a number', () => {
  const r = m.checkVisit(fullVisit({
    clock_in_lat: '41.49', clock_in_lng: '-81.69', clock_out_lat: '41.49', clock_out_lng: '-81.69'
  }), FULL_CLIENT, FULL_CG, {});
  assertEq(missingElements(r), ['location']);
});

// ── time span: verified time, never the schedule ────────────────────────
check('missing clock times fail, and the reason distinguishes which one', () => {
  assertTrue(/clock-in or clock-out/.test(
    m.checkVisit(fullVisit({ clock_in_at: undefined, clock_out_at: undefined }), FULL_CLIENT, FULL_CG, {}).missing[0].reason));
  assertTrue(/No clock-in time/.test(
    m.checkVisit(fullVisit({ clock_in_at: undefined }), FULL_CLIENT, FULL_CG, {}).missing[0].reason));
  assertTrue(/No clock-out time/.test(
    m.checkVisit(fullVisit({ clock_out_at: undefined }), FULL_CLIENT, FULL_CG, {}).missing[0].reason));
});

check('the SCHEDULE never substitutes for a real clock-in -- a scheduled window does not make a visit verified', () => {
  const r = m.checkVisit(fullVisit({
    clock_in_at: undefined, clock_out_at: undefined,
    scheduled_start: '09:00', scheduled_end: '11:00'
  }), FULL_CLIENT, FULL_CG, {});
  assertEq(missingElements(r), ['time_span'], 'a scheduled window must not satisfy time_span');
});

check('a non-positive duration is refused, including exactly equal times', () => {
  const equal = m.checkVisit(fullVisit({ clock_out_at: '2026-08-27T13:00:00.000Z' }), FULL_CLIENT, FULL_CG, {});
  assertEq(missingElements(equal), ['time_span']);
  const backwards = m.checkVisit(fullVisit({ clock_out_at: '2026-08-27T12:00:00.000Z' }), FULL_CLIENT, FULL_CG, {});
  assertEq(missingElements(backwards), ['time_span']);
  assertTrue(/positive duration/.test(backwards.missing[0].reason));
});

check('an unparseable timestamp is refused, not coerced', () => {
  const r = m.checkVisit(fullVisit({ clock_out_at: 'yesterday afternoon' }), FULL_CLIENT, FULL_CG, {});
  assertEq(missingElements(r), ['time_span']);
});

check('service_date is required and an empty string does not count', () => {
  assertEq(missingElements(m.checkVisit(fullVisit({ scheduled_date: '' }), FULL_CLIENT, FULL_CG, {})), ['service_date']);
});

// ── every gap at once, and the elements stay distinct ───────────────────
check('an empty completed visit reports all six elements, each exactly once', () => {
  const r = m.checkVisit({ id: 'VS-2', status: 'completed' }, null, null, {});
  assertEq(missingElements(r), ['location', 'provider', 'recipient', 'service_date', 'service_type', 'time_span']);
  assertEq(r.missing.length, 6, 'no element should be reported twice');
});

// ── the honesty contract ────────────────────────────────────────────────
check('the federal floor is reported as UNVERIFIED on every single result', () => {
  const r = m.checkVisit(fullVisit(), FULL_CLIENT, FULL_CG, { state: 'OH' });
  assertEq(r.federal_source.verified, false);
  assertTrue(/NOT been checked against primary text/.test(r.federal_source.note));
});

check('a configured state is never reported as compliant -- only as not_verified', () => {
  assertEq(m.checkVisit(fullVisit(), FULL_CLIENT, FULL_CG, { state: 'OH' }).state_rules, 'not_verified');
  assertEq(m.checkVisit(fullVisit(), FULL_CLIENT, FULL_CG, {}).state_rules, 'none_configured');
});

check('a READY visit still carries the unverified disclosure -- ready never means compliant', () => {
  const r = m.checkVisit(fullVisit(), FULL_CLIENT, FULL_CG, { state: 'OH' });
  assertTrue(r.ready);
  assertFalse(r.federal_source.verified, 'a green result must still say the floor is unverified');
  assertEq(r.state_rules, 'not_verified');
});

// ── the engine PERSISTS NOTHING and MUTATES NOTHING ─────────────────────
check('checkVisit does not mutate the visit, client or caregiver it is given', () => {
  const v = fullVisit({ service_type: undefined });
  const c = { id: 'CL-1', name: 'A. Client' };
  const g = { id: 'EMP-1', name: 'B. Caregiver' };
  const vBefore = JSON.stringify(v), cBefore = JSON.stringify(c), gBefore = JSON.stringify(g);
  m.checkVisit(v, c, g, { state: 'OH' });
  assertEq(JSON.stringify(v), vBefore, 'visit was mutated');
  assertEq(JSON.stringify(c), cBefore, 'client was mutated');
  assertEq(JSON.stringify(g), gBefore, 'caregiver was mutated');
});

// ── roll-up ─────────────────────────────────────────────────────────────
check('summarize counts REAL rows and never invents a denominator', () => {
  const s = m.summarize(
    [fullVisit({ id: 'A' }), fullVisit({ id: 'B', service_type: undefined }), fullVisit({ id: 'C', status: 'scheduled' })],
    { 'CL-1': FULL_CLIENT }, { 'EMP-1': FULL_CG }, { state: 'OH' });
  assertEq(s.total_visits, 3);
  assertEq(s.checkable, 2, 'the scheduled visit is not checkable');
  assertEq(s.not_checkable, 1);
  assertEq(s.ready, 1);
  assertEq(s.not_ready, 1);
  assertEq(s.by_element.service_type, 1);
  assertEq(s.by_element.location, 0);
});

check('by_element counts a visit ONCE per element even with two reasons under it', () => {
  // No name AND no member_id both sit under 'recipient'. Counting reasons
  // would report 2 and make the worst-blocker ranking wrong.
  const s = m.summarize([fullVisit()], { 'CL-1': { id: 'CL-1' } }, { 'EMP-1': FULL_CG }, {});
  assertEq(s.by_element.recipient, 1);
  assertEq(s.results[0].missing.length, 2, 'both reasons are still reported to the user');
});

check('summarize on an empty list returns zeroes, not NaN or a fabricated total', () => {
  const s = m.summarize([], {}, {}, {});
  assertEq(s.total_visits, 0); assertEq(s.checkable, 0); assertEq(s.ready, 0); assertEq(s.not_ready, 0);
  m.FEDERAL_ELEMENTS.forEach((e) => assertEq(s.by_element[e.key], 0, e.key + ' should be 0'));
});

check('summarize tolerates junk input without throwing', () => {
  assertEq(m.summarize(null, null, null, null).total_visits, 0);
  assertEq(m.summarize(undefined).total_visits, 0);
  const s = m.summarize([null], {}, {}, {});
  assertEq(s.total_visits, 1);
  assertEq(s.checkable, 0, 'a null row is not checkable');
});

check('summarize carries the same unverified disclosure as checkVisit', () => {
  const s = m.summarize([fullVisit()], { 'CL-1': FULL_CLIENT }, { 'EMP-1': FULL_CG }, { state: 'OH' });
  assertEq(s.federal_source.verified, false);
  assertEq(s.state_rules, 'not_verified');
  assertEq(s.elements.length, 6);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
