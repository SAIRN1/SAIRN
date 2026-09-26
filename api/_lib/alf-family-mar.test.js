// api/_lib/alf-family-mar.test.js
//
//   node api/_lib/alf-family-mar.test.js
//
// THE ARM THAT MATTERS IS THE ONE THAT LETS NOTHING THROUGH.
//
// This engine decides what leaves the building. Every other property here --
// the adherence arithmetic, the sort order, the status vocabulary -- is a
// convenience; the one that carries the harm is whether a field nobody named
// can reach a family member. So the projection is driven with a record
// carrying every clinical field the app writes today PLUS one that does not
// exist yet, and the assertion is on what SURVIVES rather than on what is
// removed. A deny-list passes a removal test and leaks the next field added.
//
// The second is consent, and it is driven in every falsy AND truthy-but-wrong
// shape: null, undefined, 0, '' and the string 'true'. Boolean('false') is
// true in JavaScript and this platform has already been bitten by exactly that
// coercion on a tri-state flag.

'use strict';
const assert = require('assert');
const m = require('./alf-family-mar');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n         ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

const CONSENTED = {
  contact_id: 'FC1', name: 'Jane Doe', relationship: 'daughter',
  mar_consent: true, consent_granted_at: '2026-09-26T00:00:00Z',
  consent_granted_by: 'emp-1', active: true
};

// An administration record carrying EVERY field sairncare.html writes today,
// plus one that does not exist yet.
const FULL_ADMIN = {
  entry_type: 'administration', resident_id: 'RES-1',
  data: {
    id: 'ADM1', medication_id: 'MED-9', date: '2026-09-25', time: '08:00',
    status: 'given', administered_by: 'emp-7',
    prn_reason: 'agitation at breakfast', effectiveness_check: 'settled by 09:15',
    refusal_reason: '', supervisor_notified: true, notes: 'family called',
    a_field_added_next_year: 'whatever this turns out to be'
  }
};

section('THE PROJECTION: an allow-list, so an unknown field cannot leak');

test('THE ARM THAT MATTERS: exactly four keys survive, and nothing else -- '
   + 'including a field that did not exist when this was written', () => {
  const r = m.familyRow(FULL_ADMIN);
  assert.deepStrictEqual(Object.keys(r).sort(),
    ['date', 'resident_id', 'status', 'time']);
});

test('...and every clinical field is gone BY NAME, checked one at a time', () => {
  const r = m.familyRow(FULL_ADMIN);
  ['medication_id', 'prn_reason', 'effectiveness_check', 'refusal_reason',
   'notes', 'administered_by', 'supervisor_notified', 'id',
   'a_field_added_next_year'].forEach(function (f) {
    assert.strictEqual(r[f], undefined, f + ' reached a family member');
  });
});

test('CONTROL: the arm above would pass on an empty object, so the fields that '
   + 'SHOULD survive are asserted with real values', () => {
  const r = m.familyRow(FULL_ADMIN);
  assert.strictEqual(r.date, '2026-09-25');
  assert.strictEqual(r.time, '08:00');
  assert.strictEqual(r.status, 'given');
  assert.strictEqual(r.resident_id, 'RES-1');
});

section('ONLY ONE ENTRY TYPE EVER SURVIVES');

test('a controlled-substance COUNT yields nothing -- excluded by the decision '
   + 'and because a narcotics register is not a care event', () => {
  assert.strictEqual(m.familyRow({ entry_type: 'count', resident_id: 'RES-1',
    data: { date: '2026-09-25', time: '08:00', status: 'given' } }), null);
});

test('a medication ORDER yields nothing -- the standing order IS the '
   + 'medication list', () => {
  assert.strictEqual(m.familyRow({ entry_type: 'medication_order',
    data: { date: '2026-09-25', name: 'Risperidone', dose: '1mg' } }), null);
});

test('reconciliation and assessment_refusal yield nothing either', () => {
  ['reconciliation', 'assessment_refusal'].forEach(function (t) {
    assert.strictEqual(m.familyRow({ entry_type: t,
      data: { date: '2026-09-25', time: '08:00', status: 'given' } }), null, t);
  });
});

test('an entry with no type at all yields nothing, rather than defaulting in', () => {
  assert.strictEqual(m.familyRow({ data: { date: '2026-09-25', status: 'given' } }), null);
  assert.strictEqual(m.familyRow(null), null);
});

section('CONSENT DEFAULTS TO OFF, AND ONLY AN EXPLICIT TRUE OPENS IT');

test('THE SECOND ARM THAT MATTERS: every falsy and truthy-but-wrong consent '
   + 'shape is REFUSED -- including the string "true", because '
   + 'Boolean("false") is true and this platform has been bitten by it', () => {
  [undefined, null, false, 0, '', 'true', 'yes', 1, {}].forEach(function (v) {
    const c = Object.assign({}, CONSENTED); c.mar_consent = v;
    const r = m.familyMarView({ contact: c, entries: [FULL_ADMIN] });
    assert.strictEqual(r.ok, false, 'consent opened on ' + JSON.stringify(v));
    assert.strictEqual(r.error.code, 'NO_MAR_CONSENT');
  });
});

test('a contact record with NO consent field at all is refused', () => {
  const c = Object.assign({}, CONSENTED); delete c.mar_consent;
  assert.strictEqual(m.familyMarView({ contact: c, entries: [FULL_ADMIN] })
    .error.code, 'NO_MAR_CONSENT');
});

test('the refusal SAYS consent was not granted -- it does not return an empty '
   + 'list, which a family member would read as "on no medication"', () => {
  const c = Object.assign({}, CONSENTED, { mar_consent: false });
  const r = m.familyMarView({ contact: c, entries: [FULL_ADMIN] });
  assert.ok(!('events' in r), 'an events list was returned on a refusal');
  assert.ok(/has not been shared/.test(r.error.message), r.error.message);
});

test('a DEACTIVATED contact is refused even with consent recorded -- '
   + 'revocation must not depend on unsetting a second field', () => {
  const c = Object.assign({}, CONSENTED, { active: false });
  assert.strictEqual(m.familyMarView({ contact: c, entries: [FULL_ADMIN] })
    .error.code, 'CONTACT_INACTIVE');
});

test('no contact at all is refused, never treated as a public view', () => {
  assert.strictEqual(m.familyMarView({ entries: [FULL_ADMIN] }).error.code, 'NO_CONTACT');
});

test('consent GRANTED returns the events, with the grant recorded beside them', () => {
  const r = m.familyMarView({ contact: CONSENTED, entries: [FULL_ADMIN],
                              resident_id: 'RES-1' });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.events.length, 1);
  assert.strictEqual(r.consent.granted, true);
  assert.strictEqual(r.consent.granted_by, 'emp-1');
});

section('STATUS VOCABULARY AND ADHERENCE');

test('the statuses map to the family-facing words, and not_given reads missed', () => {
  const at = function (s) {
    return m.familyRow(Object.assign({}, FULL_ADMIN,
      { data: Object.assign({}, FULL_ADMIN.data, { status: s }) })).status;
  };
  assert.strictEqual(at('given'), 'given');
  assert.strictEqual(at('refused'), 'refused');
  assert.strictEqual(at('held'), 'held');
  assert.strictEqual(at('not_given'), 'missed');
  assert.strictEqual(at('GIVEN'), 'given', 'case should not change the answer');
});

test('an UNRECOGNISED status is `unknown` -- not dropped, which would hide a '
   + 'real dose event, and not guessed, which would report an outcome nobody '
   + 'recorded', () => {
  const r = m.familyRow(Object.assign({}, FULL_ADMIN,
    { data: Object.assign({}, FULL_ADMIN.data, { status: 'partially-given' }) }));
  assert.strictEqual(r.status, 'unknown');
});

test('adherence counts given against given+refused+missed, and HELD is '
   + 'excluded from the denominator rather than scored', () => {
  const a = m.adherence([{ status: 'given' }, { status: 'given' },
                         { status: 'missed' }, { status: 'held' }]);
  assert.strictEqual(a.scored_events, 3);
  assert.strictEqual(a.percent_given, 66.7);
  assert.strictEqual(a.held_excluded, 1);
});

test('an EMPTY window reports null, never 0% -- a zero on no data reads as a '
   + 'facility failing, which is a claim from an absence', () => {
  assert.strictEqual(m.adherence([]).percent_given, null);
  assert.strictEqual(m.adherence([{ status: 'held' }]).percent_given, null);
});

test('the adherence figure carries its own limits, in the payload', () => {
  const a = m.adherence([{ status: 'given' }]);
  assert.ok(/never recorded at all/.test(a.limits), a.limits);
});

test('the view says in the PAYLOAD what it is NOT showing, so a consumer can '
   + 'tell the family member', () => {
  const r = m.familyMarView({ contact: CONSENTED, entries: [FULL_ADMIN] });
  ['medication names', 'PRN', 'controlled-substance', 'read-only']
    .forEach(function (s) {
      assert.ok(r.not_included.indexOf(s) !== -1, 'not_included omits ' + s);
    });
});

test('events come back newest first, so the most recent dose is the first row', () => {
  const mk = function (d, t) {
    return { entry_type: 'administration', resident_id: 'R',
             data: { date: d, time: t, status: 'given' } };
  };
  const r = m.familyMarView({ contact: CONSENTED,
    entries: [mk('2026-09-24', '08:00'), mk('2026-09-25', '20:00'),
              mk('2026-09-25', '08:00')] });
  assert.deepStrictEqual(r.events.map(e => e.date + ' ' + e.time),
    ['2026-09-25 20:00', '2026-09-25 08:00', '2026-09-24 08:00']);
});

section('THE ENGINE IS PURE, AND CARRIES NO ALLOW-LIST BY ACCIDENT');

test('NEGATIVE CONTROL: the module reaches for no clock, no randomness and no I/O', () => {
  const src = require('fs').readFileSync(require.resolve('./alf-family-mar.js'), 'utf8');
  const code = src.split('\n').filter(l => !/^\s*(\/\/|\*)/.test(l)).join('\n');
  ['Date.now', 'new Date', 'Math.random', 'fetch(', 'process.env']
    .forEach(n => assert.ok(code.indexOf(n) === -1, 'the engine reaches for ' + n));
});

test('the allow-list is FOUR fields and one entry type -- if somebody widens '
   + 'either, this arm is where they have to say so', () => {
  assert.deepStrictEqual(m.FAMILY_FIELDS, ['date', 'time', 'status']);
  assert.strictEqual(m.FAMILY_ENTRY_TYPE, 'administration');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' FAMILY-MAR ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
