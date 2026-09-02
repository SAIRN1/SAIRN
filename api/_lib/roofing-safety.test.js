// api/_lib/roofing-safety.test.js
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention. Run: node api/_lib/roofing-safety.test.js
//
// Roofing is a top-three deadliest US occupation and every case below is a way
// this could quietly report a harness, an anchor or a crew as fine.

const assert = require('assert');
const s = require('./roofing-safety');

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

const TODAY = '2026-09-02';
const item = (o) => Object.assign({
  equipment_id: 'EQ-1', kind: 'harness', identifier: 'H-4471', status: 'in_service',
  last_inspected_on: '2026-08-01', inspection_interval_days: 180,
  interval_source: 'manufacturer instructions, our programme s.4'
}, o || {});

// ── it refuses to assume ──────────────────────────────────────────────────

test('every entry point REFUSES without today rather than defaulting to UTC now', () => {
  ['equipmentState', 'jhaState', 'safetyBoard'].forEach((fn) => {
    const r = s[fn]({});
    assert.strictEqual(r.ok, false, fn + ' should refuse');
    assert.strictEqual(r.error.code, 'NO_TODAY');
  });
});

// ── the interval is never this app's to invent ────────────────────────────

test('NO interval means no due date -- never a default from the standard', () => {
  const e = s.equipmentState({ today: TODAY, item: item({ inspection_interval_days: null }) });
  assert.strictEqual(e.inspection, 'no_interval_stated');
  assert.strictEqual(e.due_on, null,
    'an invented interval is a contractor repeating this app number to an inspector');
});

test('an interval with NO SOURCE does not run the clock either', () => {
  const e = s.equipmentState({ today: TODAY, item: item({ interval_source: '' }) });
  assert.strictEqual(e.inspection, 'no_source_for_interval');
  assert.strictEqual(e.due_on, null);
  assert.ok(/name where it comes from/.test(e.problems.join(' ')));
});

test('never inspected is its own answer, not overdue and certainly not fine', () => {
  const e = s.equipmentState({ today: TODAY, item: item({ last_inspected_on: null }) });
  assert.strictEqual(e.inspection, 'never_inspected');
});

// ── the clock ─────────────────────────────────────────────────────────────

test('a due date is derived from the last inspection plus the stated interval', () => {
  const e = s.equipmentState({ today: TODAY, item: item({ last_inspected_on: '2026-08-01', inspection_interval_days: 180 }) });
  assert.strictEqual(e.due_on, '2027-01-28');
  assert.strictEqual(e.inspection, 'current');
});

test('overdue and due_soon are distinguished, and the window is the caller s', () => {
  const over = s.equipmentState({ today: TODAY, item: item({ last_inspected_on: '2026-01-01', inspection_interval_days: 90 }) });
  assert.strictEqual(over.inspection, 'overdue');
  assert.ok(over.days_left < 0);
  const soon = item({ last_inspected_on: '2026-06-01', inspection_interval_days: 100 });  // due 2026-09-09
  assert.strictEqual(s.equipmentState({ today: TODAY, item: soon }).inspection, 'due_soon');
  assert.strictEqual(s.equipmentState({ today: TODAY, item: soon, warn_days: 2 }).inspection, 'current');
});

// ── out of service is the END of the clock, not a state of it ─────────────

test('removed-from-service kit does not nag, and says why', () => {
  ['removed_from_service', 'failed_inspection', 'retired'].forEach((st) => {
    const e = s.equipmentState({ today: TODAY, item: item({ status: st, last_inspected_on: '2020-01-01' }) });
    assert.strictEqual(e.inspection, 'out_of_service', st + ' should short-circuit');
    assert.strictEqual(e.due_on, null, 'a due-soon nag about a harness in a bin buries the real ones');
  });
});

test('an unrecognised status becomes null WITH a problem, never passed through', () => {
  const e = s.equipmentState({ today: TODAY, item: item({ status: 'probably-fine' }) });
  assert.strictEqual(e.status, null);
  assert.ok(/unrecognised equipment status/.test(e.problems[0]));
});

// ── the JHA cross-check, which is the point ───────────────────────────────

const jha = (o) => Object.assign({
  jha_id: 'JHA-1', job_id: 'J1', assessed_on: '2026-09-02', competent_person: 'fmA',
  hazards: ['leading edge', 'skylight'], acknowledged_by: ['fmA', 'crw1']
}, o || {});

test('it names who is on the crew today and has NOT signed', () => {
  const r = s.jhaState({ today: TODAY, jha: jha(), crew: ['fmA', 'crw1', 'crw2', 'crw3'], valid_for_days: 1 });
  assert.deepStrictEqual(r.acknowledged.sort(), ['crw1', 'fmA']);
  assert.deepStrictEqual(r.missing_acknowledgement.sort(), ['crw2', 'crw3']);
  assert.strictEqual(r.crew_size, 4);
});

test('a signature from someone NOT on the crew is surfaced, not dropped', () => {
  const r = s.jhaState({ today: TODAY, jha: jha({ acknowledged_by: ['fmA', 'ghost'] }), crew: ['fmA'], valid_for_days: 1 });
  assert.deepStrictEqual(r.acknowledged_not_on_crew, ['ghost'],
    'it is the shape of a signature collected for the wrong day');
});

test('a duplicated crew id counts once', () => {
  const r = s.jhaState({ today: TODAY, jha: jha(), crew: ['crw2', 'crw2'], valid_for_days: 1 });
  assert.strictEqual(r.crew_size, 1);
  assert.deepStrictEqual(r.missing_acknowledgement, ['crw2']);
});

test('NO stated validity is not "valid forever"', () => {
  const r = s.jhaState({ today: TODAY, jha: jha({ assessed_on: '2020-01-01' }), crew: [] });
  assert.strictEqual(r.currency, 'no_validity_stated');
});

test('a stale assessment is stale, and a current one is current', () => {
  assert.strictEqual(s.jhaState({ today: TODAY, jha: jha({ assessed_on: '2026-08-01' }), crew: [], valid_for_days: 1 }).currency, 'stale');
  assert.strictEqual(s.jhaState({ today: TODAY, jha: jha(), crew: [], valid_for_days: 1 }).currency, 'current');
});

test('an EMPTY assessment is flagged -- it looks like the work was done', () => {
  const r = s.jhaState({ today: TODAY, jha: jha({ hazards: [] }), crew: [], valid_for_days: 1 });
  assert.ok(/empty assessment reads as though one was carried out/.test(r.problems.join(' ')));
});

test('a missing competent person and a missing date are each flagged', () => {
  const r = s.jhaState({ today: TODAY, jha: jha({ competent_person: '', assessed_on: null }), crew: [], valid_for_days: 1 });
  assert.ok(/no competent person/.test(r.problems.join(' ')));
  assert.ok(/cannot be shown to be current/.test(r.problems.join(' ')));
});

// ── the board ─────────────────────────────────────────────────────────────

test('the board splits overdue from records whose clock CANNOT run', () => {
  const b = s.safetyBoard({ today: TODAY, equipment: [
    item({ equipment_id: 'OVER', last_inspected_on: '2026-01-01', inspection_interval_days: 30 }),
    item({ equipment_id: 'NOINT', inspection_interval_days: null }),
    item({ equipment_id: 'NOSRC', interval_source: '' }),
    item({ equipment_id: 'NEVER', last_inspected_on: null }),
    item({ equipment_id: 'GONE', status: 'retired' }),
    item({ equipment_id: 'OK' })
  ] });
  assert.deepStrictEqual(b.overdue, ['OVER']);
  assert.deepStrictEqual(b.unusable_record.sort(), ['NOINT', 'NOSRC'],
    'a record whose clock cannot run is not a chase -- it is a data fix');
  assert.deepStrictEqual(b.never_inspected, ['NEVER']);
  assert.deepStrictEqual(b.out_of_service, ['GONE']);
  assert.strictEqual(b.current, 1);
});

test('the board carries its own disclaimer so a UI cannot omit it', () => {
  const b = s.safetyBoard({ today: TODAY, equipment: [] });
  assert.ok(/not a compliance determination/.test(b.disclaimer));
  assert.ok(/no interval here comes from this application/.test(b.disclaimer));
});

console.log(passed + ' passed');
