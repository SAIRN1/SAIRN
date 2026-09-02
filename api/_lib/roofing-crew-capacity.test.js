// api/_lib/roofing-crew-capacity.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention. Run: node api/_lib/roofing-crew-capacity.test.js
//
// Every case is a way this report could quietly say the week is clear when it
// is not, or invent a conflict that stops someone scheduling real work.

const assert = require('assert');
const c = require('./roofing-crew-capacity');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (e) {
    console.error('  FAIL - ' + name + '\n      ' + e.message);
    process.exitCode = 1;
  }
}

const FROM = '2026-09-01', TO = '2026-09-07';
const day = (id, job, date, crew, status) => ({
  schedule_id: id, job_id: job, scheduled_date: date, crew: crew, status: status || 'planned'
});

// ── the range is the caller's ─────────────────────────────────────────────

test('crewLoad REFUSES without an explicit range rather than guessing a week', () => {
  assert.strictEqual(c.crewLoad({ schedule: [] }).error.code, 'NO_RANGE');
  assert.strictEqual(c.crewLoad({ from: FROM, schedule: [] }).error.code, 'NO_RANGE');
  assert.strictEqual(c.crewLoad({ from: TO, to: FROM }).error.code, 'BAD_RANGE');
});

// ── the thing that did not exist ──────────────────────────────────────────

test('the same person on TWO jobs on one day is a conflict, and it is named', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [
    day('S1', 'JOB-A', '2026-09-03', ['emp1', 'emp2']),
    day('S2', 'JOB-B', '2026-09-03', ['emp1'])
  ] });
  assert.strictEqual(r.conflicts.length, 1);
  assert.strictEqual(r.conflicts[0].employee_id, 'emp1');
  assert.deepStrictEqual(r.conflicts[0].jobs.sort(), ['JOB-A', 'JOB-B']);
  assert.strictEqual(r.load.filter(x => x.employee_id === 'emp2')[0].conflict, false);
});

test('the same person on the SAME job twice is a DUPLICATE, not a conflict', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [
    day('S1', 'JOB-A', '2026-09-03', ['emp1']),
    day('S2', 'JOB-A', '2026-09-03', ['emp1'])
  ] });
  assert.strictEqual(r.conflicts.length, 0, 'one job is not two jobs');
  assert.strictEqual(r.duplicates.length, 1);
  assert.deepStrictEqual(r.duplicates[0].duplicate, ['JOB-A']);
});

test('two people on two jobs, neither shared, is not a conflict', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [
    day('S1', 'JOB-A', '2026-09-03', ['emp1']),
    day('S2', 'JOB-B', '2026-09-03', ['emp2'])
  ] });
  assert.strictEqual(r.conflicts.length, 0);
  assert.strictEqual(r.days[0].people, 2);
  assert.strictEqual(r.days[0].job_count, 2);
});

// ── what counts as occupying a day ────────────────────────────────────────

test('a CANCELLED day does not occupy anyone and cannot create a conflict', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [
    day('S1', 'JOB-A', '2026-09-03', ['emp1']),
    day('S2', 'JOB-B', '2026-09-03', ['emp1'], 'cancelled')
  ] });
  assert.strictEqual(r.conflicts.length, 0, 'inventing conflicts stops people scheduling real work');
  assert.strictEqual(r.skipped.not_occupying, 1);
});

test('a DONE day still occupies -- history is not forgotten', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [
    day('S1', 'JOB-A', '2026-09-03', ['emp1'], 'done'),
    day('S2', 'JOB-B', '2026-09-03', ['emp1'])
  ] });
  assert.strictEqual(r.conflicts.length, 1, 'a capacity report that forgets completed work understates every past week');
});

test('an unrecognised status does not occupy, and the skip is COUNTED not silent', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [day('S1', 'JOB-A', '2026-09-03', ['emp1'], 'maybe')] });
  assert.strictEqual(r.load.length, 0);
  assert.strictEqual(r.skipped.not_occupying, 1);
});

test('a row with an unreadable date is skipped and COUNTED, never silently dropped', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [day('S1', 'JOB-A', 'thursday', ['emp1'])] });
  assert.strictEqual(r.load.length, 0);
  assert.strictEqual(r.skipped.unreadable_date, 1);
});

test('rows outside the range are excluded without being counted as skipped', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [day('S1', 'JOB-A', '2026-10-01', ['emp1'])] });
  assert.strictEqual(r.load.length, 0);
  assert.deepStrictEqual(r.skipped, { unreadable_date: 0, not_occupying: 0 });
});

test('a crew listed twice in ONE row counts once -- old rows predate normalizeCrew', () => {
  const r = c.crewLoad({ from: FROM, to: TO, schedule: [day('S1', 'JOB-A', '2026-09-03', ['emp1', 'emp1'])] });
  assert.strictEqual(r.load.length, 1);
  assert.strictEqual(r.load[0].job_count, 1);
  assert.strictEqual(r.load[0].conflict, false, 'one person on one job is not a conflict with himself');
});

// ── the write-path check ──────────────────────────────────────────────────

test('conflictsFor names who would end up on two jobs', () => {
  const r = c.conflictsFor({
    schedule: [day('S1', 'JOB-A', '2026-09-03', ['emp1', 'emp2'])],
    candidate: day('S2', 'JOB-B', '2026-09-03', ['emp1'])
  });
  assert.strictEqual(r.conflicts.length, 1);
  assert.strictEqual(r.conflicts[0].employee_id, 'emp1');
  assert.deepStrictEqual(r.conflicts[0].with_jobs, ['JOB-A']);
});

test('EDITING a day never reports it colliding with itself', () => {
  const existing = day('S1', 'JOB-A', '2026-09-03', ['emp1']);
  const r = c.conflictsFor({ schedule: [existing], candidate: day('S1', 'JOB-A', '2026-09-03', ['emp1', 'emp2']) });
  assert.deepStrictEqual(r.conflicts, [], 'excluding the row by its own id is what makes this usable');
  assert.deepStrictEqual(r.duplicates, []);
});

test('same person, same job, different row is reported as a duplicate not a conflict', () => {
  const r = c.conflictsFor({
    schedule: [day('S1', 'JOB-A', '2026-09-03', ['emp1'])],
    candidate: day('S2', 'JOB-A', '2026-09-03', ['emp1'])
  });
  assert.strictEqual(r.conflicts.length, 0);
  assert.strictEqual(r.duplicates.length, 1);
});

test('a cancelled candidate says NOT APPLICABLE rather than returning an empty all-clear', () => {
  const r = c.conflictsFor({
    schedule: [day('S1', 'JOB-A', '2026-09-03', ['emp1'])],
    candidate: day('S2', 'JOB-B', '2026-09-03', ['emp1'], 'cancelled')
  });
  assert.strictEqual(r.applicable, false);
  assert.ok(/does not occupy/.test(r.reason));
});

test('an existing cancelled day cannot be conflicted with', () => {
  const r = c.conflictsFor({
    schedule: [day('S1', 'JOB-A', '2026-09-03', ['emp1'], 'cancelled')],
    candidate: day('S2', 'JOB-B', '2026-09-03', ['emp1'])
  });
  assert.deepStrictEqual(r.conflicts, []);
});

test('a candidate with no readable date is an explicit error, not a silent all-clear', () => {
  const r = c.conflictsFor({ schedule: [], candidate: day('S2', 'JOB-B', 'soon', ['emp1']) });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.error.code, 'NO_DATE');
  const r2 = c.conflictsFor({ schedule: [] });
  assert.strictEqual(r2.error.code, 'NO_CANDIDATE');
});

test('a day on a different date is not a conflict', () => {
  const r = c.conflictsFor({
    schedule: [day('S1', 'JOB-A', '2026-09-04', ['emp1'])],
    candidate: day('S2', 'JOB-B', '2026-09-03', ['emp1'])
  });
  assert.deepStrictEqual(r.conflicts, []);
});

console.log(passed + ' passed');
