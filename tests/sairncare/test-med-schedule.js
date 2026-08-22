// Isolated test of api/_lib/med-schedule.js (Phase 3 items 1 + 4).
// PURE engine, so every case runs against the REAL module.
'use strict';
const path = require('path');
const m = require(path.join(__dirname, '..', '..', 'api/_lib/med-schedule.js'));

let pass = 0, fail = 0;
function check(n, f) { try { f(); pass++; console.log('PASS ' + n); } catch (e) { fail++; console.log('FAIL ' + n + ' -- ' + e.message); } }
function assertEq(a, b, msg) {
  if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error((msg || 'mismatch') + ': expected ' + JSON.stringify(b) + ' got ' + JSON.stringify(a));
}
function assertTrue(v, msg) { if (!v) throw new Error(msg || 'expected truthy'); }

// ── parsing ──────────────────────────────────────────────────────────────
check('explicit 24h clock times parse confidently', () => {
  const r = m.parseScheduleText('08:00, 14:00, 20:00');
  assertEq(r.times, ['08:00', '14:00', '20:00']);
  assertEq(r.confident, true);
});

check('am/pm times normalise to 24h', () => {
  assertEq(m.parseScheduleText('8:00 am and 8:00 pm').times, ['08:00', '20:00']);
  assertEq(m.parseScheduleText('12:00 am').times, ['00:00'], 'midnight');
  assertEq(m.parseScheduleText('12:30 pm').times, ['12:30'], 'noon stays 12');
});

check('PROSE IS REFUSED, NOT GUESSED -- the whole reason this module exists', () => {
  const r = m.parseScheduleText('twice daily');
  assertEq(r.times, []);
  assertEq(r.confident, false);
  assertTrue(/will not guess/i.test(r.reason), 'the refusal must say it will not guess');
});

check('other vague dosing prose is likewise refused', () => {
  ['BID', 'three times a day', 'nightly at bedtime', 'every 4 hours'].forEach((s) => {
    assertEq(m.parseScheduleText(s).times, [], s + ' must not produce invented times');
  });
});

check('an empty schedule is reported as empty, not defaulted', () => {
  const r = m.parseScheduleText('');
  assertEq(r.times, []);
  assertEq(r.confident, false);
});

check('structured schedule_times always win over free text', () => {
  const r = m.scheduleTimesFor({ schedule_times: ['09:00'], schedule: '08:00, 20:00' });
  assertEq(r.times, ['09:00']);
  assertEq(r.source, 'structured');
});

check('a legacy order with only free text falls back to parsing it', () => {
  const r = m.scheduleTimesFor({ schedule: '08:00, 20:00' });
  assertEq(r.times, ['08:00', '20:00']);
  assertEq(r.source, 'parsed_from_text');
});

check('invalid stored times are dropped and flagged rather than trusted', () => {
  const r = m.scheduleTimesFor({ schedule_times: ['08:00', '25:99'] });
  assertEq(r.times, ['08:00']);
  assertEq(r.confident, false);
});

// ── lateness ─────────────────────────────────────────────────────────────
const order = { id: 'MED-1', name: 'Metformin', resident_id: 'RES-1', schedule_times: ['08:00', '20:00'], start_date: '2026-01-01' };

check('a dose inside its window is due_now, not late', () => {
  const r = m.evaluateDay({ order: order, day: '2026-08-22', now_minutes_of_day: 8 * 60 + 30, grace_minutes: 60, administrations: [] });
  assertEq(r.findings[0].status, 'due_now');
  assertEq(r.findings[0].minutes_late, 0);
});

check('a dose past its window is late, by the right number of minutes', () => {
  const r = m.evaluateDay({ order: order, day: '2026-08-22', now_minutes_of_day: 10 * 60, grace_minutes: 60, administrations: [] });
  assertEq(r.findings[0].status, 'late');
  assertEq(r.findings[0].minutes_late, 60, '10:00 is 60 min past an 09:00 window end');
});

check('a later dose the same day is still upcoming', () => {
  const r = m.evaluateDay({ order: order, day: '2026-08-22', now_minutes_of_day: 10 * 60, grace_minutes: 60, administrations: [] });
  assertEq(r.findings[1].status, 'upcoming');
});

check('a recorded administration marks the dose given', () => {
  const r = m.evaluateDay({
    order: order, day: '2026-08-22', now_minutes_of_day: 10 * 60, grace_minutes: 60,
    administrations: [{ id: 'ADM-1', medication_id: 'MED-1', day: '2026-08-22', time: '08:15' }]
  });
  assertEq(r.findings[0].status, 'given');
  assertEq(r.findings[0].recorded_administration_id, 'ADM-1');
  assertEq(r.late_count, 0);
});

check('ONE administration cannot satisfy TWO doses of the same drug', () => {
  const r = m.evaluateDay({
    order: order, day: '2026-08-22', now_minutes_of_day: 23 * 60, grace_minutes: 60,
    administrations: [{ id: 'ADM-1', medication_id: 'MED-1', day: '2026-08-22', time: '08:15' }]
  });
  assertEq(r.findings[0].status, 'given');
  assertEq(r.findings[1].status, 'late', 'the 20:00 dose must still be late');
});

check('an administration for a DIFFERENT medication does not satisfy this one', () => {
  const r = m.evaluateDay({
    order: order, day: '2026-08-22', now_minutes_of_day: 10 * 60, grace_minutes: 60,
    administrations: [{ id: 'ADM-9', medication_id: 'MED-OTHER', day: '2026-08-22', time: '08:15' }]
  });
  assertEq(r.findings[0].status, 'late');
});

check('an administration on a DIFFERENT day does not satisfy today', () => {
  const r = m.evaluateDay({
    order: order, day: '2026-08-22', now_minutes_of_day: 10 * 60, grace_minutes: 60,
    administrations: [{ id: 'ADM-8', medication_id: 'MED-1', day: '2026-08-21', time: '08:00' }]
  });
  assertEq(r.findings[0].status, 'late');
});

check('PRN orders are never late -- they have no scheduled time', () => {
  const r = m.evaluateDay({ order: Object.assign({}, order, { prn: true }), day: '2026-08-22', now_minutes_of_day: 23 * 60, grace_minutes: 60, administrations: [] });
  assertEq(r.ok, false);
  assertEq(r.schedulable, false);
  assertTrue(/never "late"/.test(r.reason));
});

check('a discontinued order generates no alerts', () => {
  const r = m.evaluateDay({ order: Object.assign({}, order, { discontinued: true }), day: '2026-08-22', now_minutes_of_day: 23 * 60, grace_minutes: 60, administrations: [] });
  assertEq(r.schedulable, false);
});

check('an order that has not started yet generates no alerts', () => {
  const r = m.evaluateDay({ order: Object.assign({}, order, { start_date: '2026-09-01' }), day: '2026-08-22', now_minutes_of_day: 23 * 60, grace_minutes: 60, administrations: [] });
  assertEq(r.schedulable, false);
  assertTrue(/does not start until 2026-09-01/.test(r.reason));
});

check('a MISSING facility window policy is refused, never defaulted', () => {
  const r = m.evaluateDay({ order: order, day: '2026-08-22', now_minutes_of_day: 10 * 60, administrations: [] });
  assertEq(r.ok, false);
  assertTrue(/does not assume one/i.test(r.reason), 'must refuse rather than pick a window');
  assertEq(r.findings, []);
});

check('a prose-scheduled order is unschedulable, not silently never-late', () => {
  const r = m.evaluateDay({ order: { id: 'MED-2', name: 'Vitamin D', schedule: 'daily' }, day: '2026-08-22', now_minutes_of_day: 23 * 60, grace_minutes: 60, administrations: [] });
  assertEq(r.ok, false);
  assertEq(r.schedulable, false);
});

// ── facility roll-up ─────────────────────────────────────────────────────
check('facility roll-up separates late, due, upcoming and given', () => {
  const r = m.facilityAlerts({
    orders: [order, { id: 'MED-3', name: 'Lisinopril', resident_id: 'RES-2', schedule_times: ['09:00'] }],
    administrations: [{ id: 'A1', medication_id: 'MED-1', day: '2026-08-22', time: '08:10' }],
    day: '2026-08-22', now_minutes_of_day: 11 * 60, grace_minutes: 60
  });
  assertEq(r.given.length, 1);
  assertEq(r.late.length, 1, 'MED-3 at 09:00 with a 60-min window is late at 11:00');
  assertEq(r.late[0].medication, 'Lisinopril');
  assertEq(r.upcoming.length, 1, 'the 20:00 dose of MED-1');
});

check('unschedulable orders are SURFACED in the roll-up, never silently omitted', () => {
  const r = m.facilityAlerts({
    orders: [order, { id: 'MED-4', name: 'Calcium', resident_id: 'RES-3', schedule: 'twice daily' }],
    administrations: [], day: '2026-08-22', now_minutes_of_day: 23 * 60, grace_minutes: 60
  });
  assertEq(r.unschedulable.length, 1);
  assertEq(r.unschedulable[0].medication, 'Calcium');
  assertEq(r.coverage.have, 1);
  assertEq(r.coverage.need, 2);
  assertTrue(/cannot be tracked/.test(r.coverage.note), 'the coverage gap must be stated');
});

check('coverage note is null when every order is trackable', () => {
  const r = m.facilityAlerts({ orders: [order], administrations: [], day: '2026-08-22', now_minutes_of_day: 1, grace_minutes: 60 });
  assertEq(r.coverage.have, 1);
  assertEq(r.coverage.need, 1);
  assertEq(r.coverage.note, null);
});

check('high-priority and controlled flags ride through to the alert', () => {
  const r = m.facilityAlerts({
    orders: [{ id: 'MED-5', name: 'Insulin', resident_id: 'RES-9', schedule_times: ['07:00'], high_priority: true, controlled_substance: true }],
    administrations: [], day: '2026-08-22', now_minutes_of_day: 12 * 60, grace_minutes: 30
  });
  assertEq(r.late[0].high_priority, true);
  assertEq(r.late[0].controlled_substance, true);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
