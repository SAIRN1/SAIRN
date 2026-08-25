// api/_lib/roofing-locations.test.js
// Isolation suite for Phase 4a -- location attribution and crew scheduling.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const loc = require('./roofing-locations.js');

const MGMT = { owner: true, admin: true };
const BROAD = { estimator: true };

test('a write with no location is stamped with the default, never rejected', () => {
  const out = loc.stampLocation({ id: 'J1', name: 'A job' });
  assert.strictEqual(out.location_id, 'LOC-DEFAULT');
  assert.strictEqual(out.name, 'A job'); // everything else survives
});

test('a real location_id is kept as given', () => {
  assert.strictEqual(loc.stampLocation({ location_id: 'LOC-CBUS' }).location_id, 'LOC-CBUS');
});

test('blank, whitespace, non-string and over-length all fall back rather than failing the save', () => {
  // A job must never fail to save because of an optional attribution field.
  assert.strictEqual(loc.stampLocation({ location_id: '' }).location_id, 'LOC-DEFAULT');
  assert.strictEqual(loc.stampLocation({ location_id: '   ' }).location_id, 'LOC-DEFAULT');
  assert.strictEqual(loc.stampLocation({ location_id: 12345 }).location_id, 'LOC-DEFAULT');
  assert.strictEqual(loc.stampLocation({ location_id: 'x'.repeat(65) }).location_id, 'LOC-DEFAULT');
  assert.strictEqual(loc.stampLocation({ location_id: 'x'.repeat(64) }).location_id, 'x'.repeat(64));
});

test('stampLocation does not mutate its input', () => {
  const original = { id: 'J1' };
  loc.stampLocation(original);
  assert.strictEqual(original.location_id, undefined);
});

test('a location needs an id and a name', () => {
  const p = loc.validateLocation({});
  assert.ok(p.some((x) => /location_id/.test(x)));
  assert.ok(p.some((x) => /needs a name/.test(x)));
  assert.deepStrictEqual(loc.validateLocation({ id: 'LOC-CBUS', name: 'Columbus' }), []);
});

test('a schedule entry always belongs to a job and a real date', () => {
  const p = loc.validateSchedule({ id: 'S1' });
  assert.ok(p.some((x) => /job_id is required/.test(x)));
  assert.ok(p.some((x) => /YYYY-MM-DD/.test(x)));
});

test('a malformed or impossible date is refused', () => {
  assert.ok(loc.validateSchedule({ id: 'S1', job_id: 'J1', scheduled_date: '08/26/2026' }).length);
  assert.ok(loc.validateSchedule({ id: 'S1', job_id: 'J1', scheduled_date: '2026-13-45' }).length);
  assert.deepStrictEqual(loc.validateSchedule({ id: 'S1', job_id: 'J1', scheduled_date: '2026-08-26' }), []);
});

test('an unknown status is refused, a known one accepted', () => {
  assert.ok(loc.validateSchedule({ id: 'S1', job_id: 'J1', scheduled_date: '2026-08-26', status: 'vibing' }).length);
  assert.deepStrictEqual(loc.validateSchedule({ id: 'S1', job_id: 'J1', scheduled_date: '2026-08-26', status: 'confirmed' }), []);
});

test('crew must be an array if given at all', () => {
  assert.ok(loc.validateSchedule({ id: 'S1', job_id: 'J1', scheduled_date: '2026-08-26', crew: 'fmA' }).length);
});

test('the crew list is de-duplicated, trimmed and order-preserving', () => {
  // The same person twice on one day would double-count in any capacity view,
  // and would do it silently.
  assert.deepStrictEqual(loc.normalizeCrew([' fmA ', 'fmB', 'fmA', '', null, 'fmC']), ['fmA', 'fmB', 'fmC']);
  assert.deepStrictEqual(loc.normalizeCrew(undefined), []);
});

test('management and broad-read see the whole schedule board', () => {
  const e = { crew: [] };
  assert.strictEqual(loc.canSeeSchedule({ role: 'owner', employee_id: 'O' }, e, 'SOMEONE', MGMT, BROAD), true);
  assert.strictEqual(loc.canSeeSchedule({ role: 'estimator', employee_id: 'E' }, e, 'SOMEONE', MGMT, BROAD), true);
});

test('a narrow-tier employee sees a day they are ON THE CREW for, even on someone else\'s job', () => {
  // The clause that is easy to miss: a crew member who is not the job's
  // assignee would otherwise be scheduled to work a day they cannot see.
  const e = { crew: ['fmB'] };
  assert.strictEqual(loc.canSeeSchedule({ role: 'crew', employee_id: 'fmB' }, e, 'fmA', MGMT, BROAD), true);
});

test('a narrow-tier employee sees a day on a job assigned to them even if not listed on the crew', () => {
  const e = { crew: ['someone-else'] };
  assert.strictEqual(loc.canSeeSchedule({ role: 'foreman', employee_id: 'fmA' }, e, 'fmA', MGMT, BROAD), true);
});

test('a narrow-tier employee sees NEITHER when they are on neither', () => {
  const e = { crew: ['fmB'] };
  assert.strictEqual(loc.canSeeSchedule({ role: 'foreman', employee_id: 'fmC' }, e, 'fmA', MGMT, BROAD), false);
});

test('an unassigned job does not become visible to everyone through the schedule', () => {
  const e = { crew: [] };
  assert.strictEqual(loc.canSeeSchedule({ role: 'foreman', employee_id: 'fmA' }, e, null, MGMT, BROAD), false);
});

test('no session sees nothing', () => {
  assert.strictEqual(loc.canSeeSchedule(null, { crew: ['fmA'] }, 'fmA', MGMT, BROAD), false);
});

test('the status vocabulary is closed', () => {
  assert.deepStrictEqual(loc.SCHEDULE_STATUSES, ['planned', 'confirmed', 'in_progress', 'done', 'cancelled']);
});
