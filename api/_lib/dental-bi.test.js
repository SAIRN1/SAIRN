// api/_lib/dental-bi.test.js
// Isolation suite for SAIRNdental B5 -- the open BI / data-warehouse feed.
//
// Run:  node --test api/_lib/dental-bi.test.js
//
// Three things can go wrong with a reporting feed, in descending order of how
// long it takes anyone to notice:
//
//   1. IT SHOWS SOMEBODY SOMETHING THEY MAY NOT SEE. A feed is a second door
//      onto the same data as api/sd-data.js. If it does not carry the same two
//      gates, it is an authorisation bypass with a reporting label on it. The
//      first section asserts the gates match sd-data.js's, role by role.
//   2. IT LEAKS AN IDENTIFIER. Off by default is only true if a test says so.
//   3. IT IS QUIETLY WRONG. A mistyped path yields null, a null renders as
//      blank, and a blank column reads as "we have no data" rather than "this
//      feed is broken" -- which is why the projection tests use record shapes
//      copied from the real writers in sairndental.html, not invented ones.

'use strict';
const test = require('node:test');
const assert = require('node:assert');
const bi = require('./dental-bi.js');

const LIC = 'lic-hash-abc';
const SECRET = 'test-secret';
const CTX = { licenseHash: LIC, secret: SECRET, includeIdentifiers: false };
const CTX_IDS = { licenseHash: LIC, secret: SECRET, includeIdentifiers: true };

// ── 1. THE GATES MATCH api/sd-data.js ──────────────────────────────────────

// Transcribed from api/sd-data.js:8064 (DNT_FINANCIAL_RESOURCES). If sd-data
// grows or loses one of these, this list is the thing that should fail.
const SD_DATA_FINANCIAL_RESOURCES = {
  dnt_charges: true, dnt_payments: true, dnt_denial: true,
  dnt_ar: true, dnt_revenue: true, dnt_coverage_rules: true,
  dnt_txplans: true, dnt_gfe: true
};
// api/sd-data.js:8103 (DNT_PATIENT_SCOPED_RESOURCES) plus dnt_appointments,
// which is scoped by its own dedicated handler at :8352.
const SD_DATA_PATIENT_SCOPED_RESOURCES = {
  dnt_patients: true, dnt_referrals: true, dnt_gfe: true,
  dnt_recall_outreach: true, dnt_txplans: true, dnt_denial: true,
  dnt_appointments: true
};

test('every dataset classified financial matches sd-data.js, both directions', () => {
  Object.keys(bi.DATASETS).forEach((k) => {
    const d = bi.DATASETS[k];
    assert.strictEqual(
      !!d.financial, !!SD_DATA_FINANCIAL_RESOURCES[d.resource],
      'dataset "' + k + '" (' + d.resource + ') disagrees with sd-data.js about being financial'
    );
  });
});

test('every dataset classified patient-scoped matches sd-data.js, both directions', () => {
  Object.keys(bi.DATASETS).forEach((k) => {
    const d = bi.DATASETS[k];
    assert.strictEqual(
      !!d.patientScoped, !!SD_DATA_PATIENT_SCOPED_RESOURCES[d.resource],
      'dataset "' + k + '" (' + d.resource + ') disagrees with sd-data.js about patient scoping'
    );
  });
});

test('the financial roles are exactly owner and frontdesk', () => {
  assert.deepStrictEqual(Object.keys(bi.FINANCIAL_ROLES).sort(), ['frontdesk', 'owner']);
  assert.deepStrictEqual(Object.keys(bi.PATIENT_BROAD_READ_ROLES).sort(), ['frontdesk', 'owner']);
});

test('a provider cannot reach one financial dataset', () => {
  const visible = bi.datasetsForRole('provider');
  visible.forEach((k) => assert.strictEqual(bi.DATASETS[k].financial, false, k + ' reached a provider'));
  ['charges', 'payments', 'denials', 'treatment_plans'].forEach((k) => {
    assert.ok(visible.indexOf(k) === -1, k + ' is in a provider\'s catalog');
    const r = bi.canRead(k, 'provider');
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.code, 'ROLE_NOT_PERMITTED');
  });
});

test('owner and frontdesk reach every dataset', () => {
  const all = Object.keys(bi.DATASETS).length;
  assert.strictEqual(bi.datasetsForRole('owner').length, all);
  assert.strictEqual(bi.datasetsForRole('frontdesk').length, all);
});

test('an unknown or empty role reaches nothing financial -- it fails CLOSED', () => {
  ['', null, undefined, 'admin', 'superuser'].forEach((role) => {
    bi.datasetsForRole(role).forEach((k) => {
      assert.strictEqual(bi.DATASETS[k].financial, false,
        'role ' + JSON.stringify(role) + ' reached financial dataset ' + k);
    });
  });
});

test('a provider is patient-scoped on every patient-bearing dataset', () => {
  Object.keys(bi.DATASETS).forEach((k) => {
    const expected = bi.DATASETS[k].patientScoped;
    const scope = bi.scopeFor(k, 'provider');
    assert.strictEqual(scope.kind !== 'none', expected, k + ' scope for a provider is wrong');
  });
});

test('owner and frontdesk are NOT patient-scoped -- they run the practice', () => {
  ['owner', 'frontdesk'].forEach((role) => {
    Object.keys(bi.DATASETS).forEach((k) => {
      assert.strictEqual(bi.scopeFor(k, role).kind, 'none', k + '/' + role);
    });
  });
});

test('appointments scope in the DATABASE, not after the read', () => {
  // The whole point: an appointment blob can carry ~1.26 MB of patient photos.
  const s = bi.scopeFor('appointments', 'provider');
  assert.strictEqual(s.kind, 'provider_column');
  assert.strictEqual(s.column, 'provider_id');
});

test('a row with no scope key is DROPPED, never kept by default', () => {
  const rows = [
    { id: 'RC-1', patient_id: 'PT-1' },
    { id: 'RC-2', patient_id: 'PT-9' },
    { id: 'RC-3' },                    // no patient_id at all
    { id: 'RC-4', patient_id: null }
  ];
  const out = bi.applyPatientScope('recall_outreach', rows, { 'PT-1': true });
  assert.deepStrictEqual(out.map((r) => r.id), ['RC-1']);
});

test('an empty allow-list yields no rows, not every row', () => {
  const rows = [{ id: 'RC-1', patient_id: 'PT-1' }];
  assert.strictEqual(bi.applyPatientScope('recall_outreach', rows, {}).length, 0);
  assert.strictEqual(bi.applyPatientScope('recall_outreach', rows, null).length, 0);
});

// ── 2. IDENTIFIERS ARE OFF BY DEFAULT ──────────────────────────────────────

// Named per dataset, NOT as a bare column-name list. The first version of this
// test used one flat list containing "name" and failed on providers.name --
// correctly, in the sense that the test was wrong: a clinician's name is how
// every productivity report is read and is not a patient identifier. Pairing
// the column with its dataset is what makes the assertion mean what it says.
const DIRECT_IDENTIFIERS = {
  patients: ['name', 'date_of_birth', 'phone', 'email', 'insurance_member_id', 'guardian_name'],
  referrals: ['patient_name']
};

test('every column marked phi is absent by default, in every dataset', () => {
  Object.keys(bi.DATASETS).forEach((k) => {
    const flagged = bi.DATASETS[k].columns.filter((c) => c[3]).map((c) => c[0]);
    const visible = bi.visibleColumns(k, false).map((c) => c[0]);
    flagged.forEach((n) => assert.ok(visible.indexOf(n) === -1,
      'dataset ' + k + ' emits phi column ' + n + ' with identifiers OFF'));
  });
});

test('the columns that identify a patient are the ones actually marked phi', () => {
  // Guards the other direction: an unflagged identifier is invisible to the
  // test above, because it would never appear in `flagged` to begin with.
  Object.keys(DIRECT_IDENTIFIERS).forEach((k) => {
    const flagged = bi.DATASETS[k].columns.filter((c) => c[3]).map((c) => c[0]).sort();
    assert.deepStrictEqual(flagged, DIRECT_IDENTIFIERS[k].slice().sort(),
      'the phi flags on ' + k + ' are not the columns that identify a patient');
  });
});

// Columns that can only ever be about a person. "name" is deliberately NOT in
// this list: on its own it says nothing -- operatories.name is a room and
// providers.name is a clinician -- so it is governed by NAME_COLUMNS below
// instead of by a keyword match that would have to be exempted twice.
const PERSON_ONLY_COLUMNS = ['date_of_birth', 'dob', 'phone', 'email',
  'insurance_member_id', 'guardian_name', 'guardian_phone', 'guardian_email',
  'patient_name', 'ssn'];

test('no dataset outside the phi list carries a person-only column at all', () => {
  Object.keys(bi.DATASETS).forEach((k) => {
    const flagged = bi.DATASETS[k].columns.filter((c) => c[3]).map((c) => c[0]);
    bi.DATASETS[k].columns.map((c) => c[0]).forEach((n) => {
      if (flagged.indexOf(n) !== -1) return;   // flagged is covered above
      assert.ok(PERSON_ONLY_COLUMNS.indexOf(n) === -1,
        'dataset ' + k + ' carries an UNFLAGGED person-only column: ' + n);
    });
  });
});

// Every `name` column in the feed, and what each one is about. A new dataset
// with a `name` column has to be added here consciously, which is the point:
// the question "whose name is this" is the one that decides whether it is PHI.
const NAME_COLUMNS = {
  providers: 'a clinician -- how every productivity report is read',
  operatories: 'a treatment room',
  patients: 'A PATIENT -- flagged phi'
};

test('every `name` column in the feed has been classified on purpose', () => {
  Object.keys(bi.DATASETS).forEach((k) => {
    const hasName = bi.DATASETS[k].columns.some((c) => c[0] === 'name');
    if (!hasName) return;
    assert.ok(NAME_COLUMNS[k], 'dataset ' + k + ' added a `name` column nobody classified');
  });
  // And the one that IS a patient is flagged, so it cannot quietly become the
  // exception the other two are.
  const ptName = bi.DATASETS.patients.columns.filter((c) => c[0] === 'name')[0];
  assert.strictEqual(ptName[3], true, 'patients.name lost its phi flag');
});

test('identifiers are dropped from the SCHEMA too, not blanked in the rows', () => {
  // A column of nulls reads as "this practice records no phone numbers".
  const cols = bi.visibleColumns('patients', false).map((c) => c[0]);
  assert.ok(cols.indexOf('phone') === -1);
  const row = bi.projectRow('patients', { id: 'PT-1', phone: '555-0100' }, CTX);
  assert.ok(!('phone' in row), 'phone came back as a null column');
});

test('turning identifiers ON is what puts them back, and nothing else does', () => {
  const row = bi.projectRow('patients',
    { id: 'PT-1', name: 'Jane Roe', dob: '1990-04-02', phone: '555-0100' }, CTX_IDS);
  assert.strictEqual(row.name, 'Jane Roe');
  assert.strictEqual(row.date_of_birth, '1990-04-02');
  assert.strictEqual(row.phone, '555-0100');
});

test('a truthy-but-not-true includeIdentifiers does NOT unlock identifiers', () => {
  // The flag arrives from a database boolean and from a JSON body. Anything
  // other than the actual boolean true is treated as off.
  ['true', 1, 'yes', {}].forEach((v) => {
    const row = bi.projectRow('patients', { id: 'PT-1', name: 'Jane Roe' },
      { licenseHash: LIC, secret: SECRET, includeIdentifiers: v });
    assert.ok(!('name' in row), 'identifiers unlocked by ' + JSON.stringify(v));
  });
});

test('non-identifying facts about an identifier still get through', () => {
  // has_guardian answers the pediatric question without naming the guardian.
  const row = bi.projectRow('patients',
    { id: 'PT-1', guardian_name: 'Ann Roe', guardian_relationship: 'Mother' }, CTX);
  assert.strictEqual(row.has_guardian, true);
  assert.strictEqual(row.guardian_relationship, 'Mother');
  assert.ok(!('guardian_name' in row));
});

test('a provider row reports THAT a login is linked, never WHICH', () => {
  const row = bi.projectRow('providers',
    { id: 'PV-1', name: 'Dr Vance', linked_employee_id: 'emp-7' }, CTX);
  assert.strictEqual(row.is_linked_to_login, true);
  assert.strictEqual(JSON.stringify(row).indexOf('emp-7'), -1, 'the employee id leaked');
});

test('appointment photo BYTES never reach the feed -- only the count', () => {
  const row = bi.projectRow('appointments',
    { id: 'AP-1', patient_id: 'PT-1', photos: ['data:image/png;base64,AAAA', 'data:image/png;base64,BBBB'],
      patient_notes: 'chipped a molar on Sunday' }, CTX_IDS);
  assert.strictEqual(row.photo_count, 2);
  const s = JSON.stringify(row);
  assert.strictEqual(s.indexOf('base64'), -1, 'photo bytes leaked');
  assert.strictEqual(s.indexOf('molar'), -1, 'patient notes leaked');
});

test('a field added to the blob later cannot appear on its own', () => {
  // The projection is a builder, not a delete-list -- this is the property that
  // makes that claim true rather than aspirational.
  const row = bi.projectRow('patients',
    { id: 'PT-1', ssn: '123-45-6789', some_future_field: 'x' }, CTX_IDS);
  assert.ok(!('ssn' in row));
  assert.ok(!('some_future_field' in row));
});

// ── 3. THE PSEUDONYM ───────────────────────────────────────────────────────

test('the same patient gets the same key every time -- joins hold', () => {
  const a = bi.patientKey(LIC, 'PT-1', SECRET);
  const b = bi.patientKey(LIC, 'PT-1', SECRET);
  assert.strictEqual(a, b);
  assert.ok(a && a.length === 24);
});

test('the same patient id at two practices does NOT collide', () => {
  assert.notStrictEqual(bi.patientKey('lic-A', 'PT-1', SECRET), bi.patientKey('lic-B', 'PT-1', SECRET));
});

test('the key does not contain the patient id it stands for', () => {
  const k = bi.patientKey(LIC, 'PT-DISTINCTIVE-1', SECRET);
  assert.strictEqual(k.indexOf('PT-DISTINCTIVE-1'), -1);
});

test('a missing patient id yields null, not a key for the empty string', () => {
  // Otherwise every orphaned row would join to one fictitious shared patient.
  assert.strictEqual(bi.patientKey(LIC, null, SECRET), null);
  assert.strictEqual(bi.patientKey(LIC, '', SECRET), null);
  assert.strictEqual(bi.patientKey(LIC, undefined, SECRET), null);
});

test('the same patient joins across datasets', () => {
  const p = bi.projectRow('patients', { id: 'PT-1' }, CTX);
  const a = bi.projectRow('appointments', { id: 'AP-1', patient_id: 'PT-1' }, CTX);
  const c = bi.projectRow('charges', { id: 'CH-1', patient_id: 'PT-1' }, CTX);
  assert.strictEqual(p.patient_key, a.patient_key);
  assert.strictEqual(a.patient_key, c.patient_key);
});

// ── 4. TYPES, AND THE DIFFERENCE BETWEEN ZERO AND UNRECORDED ───────────────

test('a numeric string becomes a number, so a BI tool does not sort it as text', () => {
  assert.strictEqual(bi.coerce('number', '12.50'), 12.5);
  assert.strictEqual(bi.coerce('number', 9), 9);
});

test('an unparseable number is null, NEVER zero', () => {
  // "$0.00 collected" and "nobody recorded a collection" are different facts.
  assert.strictEqual(bi.coerce('number', 'abc'), null);
  assert.strictEqual(bi.coerce('number', ''), null);
  assert.strictEqual(bi.coerce('number', null), null);
  assert.strictEqual(bi.coerce('number', undefined), null);
});

test('a real zero survives as zero -- it was recorded', () => {
  assert.strictEqual(bi.coerce('number', 0), 0);
  assert.strictEqual(bi.coerce('number', '0'), 0);
});

test('a date is NOT reinterpreted through the local timezone', () => {
  // The whole UTC-vs-local class: new Date("2026-09-02") is UTC midnight, and a
  // BI tool west of Greenwich would render it as 2026-09-01.
  assert.strictEqual(bi.coerce('date', '2026-09-02'), '2026-09-02');
  assert.strictEqual(bi.coerce('date', '2026-09-02T14:30:00Z'), '2026-09-02');
});

test('a malformed date is null, not a guess', () => {
  assert.strictEqual(bi.coerce('date', 'soon'), null);
  assert.strictEqual(bi.coerce('date', '09/02/2026'), null);
});

test('a datetime keeps its instant', () => {
  assert.strictEqual(bi.coerce('datetime', '2026-09-02T14:30:00Z'), '2026-09-02T14:30:00.000Z');
  assert.strictEqual(bi.coerce('datetime', 'not a time'), null);
});

test('booleans accept what a jsonb blob actually holds', () => {
  assert.strictEqual(bi.coerce('boolean', true), true);
  assert.strictEqual(bi.coerce('boolean', 'false'), false);
  assert.strictEqual(bi.coerce('boolean', 'no'), false);
  assert.strictEqual(bi.coerce('boolean', 'maybe'), null);
});

test('every column in every dataset declares a type this file knows', () => {
  const KNOWN = { string: 1, number: 1, date: 1, datetime: 1, boolean: 1 };
  Object.keys(bi.DATASETS).forEach((k) => {
    bi.DATASETS[k].columns.forEach((c) => {
      assert.ok(KNOWN[c[1]], 'dataset ' + k + ' column ' + c[0] + ' has type ' + c[1]);
    });
  });
});

test('no dataset declares the same column name twice', () => {
  Object.keys(bi.DATASETS).forEach((k) => {
    const names = bi.DATASETS[k].columns.map((c) => c[0]);
    assert.strictEqual(new Set(names).size, names.length, 'duplicate column in ' + k);
  });
});

// ── 5. PROJECTIONS AGAINST THE REAL RECORD SHAPES ──────────────────────────
// Each fixture below is the object literal its writer in sairndental.html
// actually constructs, copied field for field. A path that drifts fails here
// rather than shipping a blank column.

test('charges: addChargeEntry()\'s record projects with nothing missing', () => {
  const rec = { id: 'CH-1', patient_id: 'PT-1', appointment_id: 'AP-1', procedure_type_id: 'PC-1',
    amount: 240, estimated_insurance_portion: 120, date: '2026-09-02' };
  const row = bi.projectRow('charges', rec, CTX);
  assert.strictEqual(row.charge_id, 'CH-1');
  assert.strictEqual(row.amount, 240);
  assert.strictEqual(row.estimated_insurance_portion, 120);
  assert.strictEqual(row.charge_date, '2026-09-02');
  assert.strictEqual(row.appointment_id, 'AP-1');
  assert.strictEqual(row.procedure_type_id, 'PC-1');
});

test('payments: addPaymentEntry()\'s record projects with nothing missing', () => {
  const row = bi.projectRow('payments',
    { id: 'PM-1', patient_id: 'PT-1', amount: 80, method: 'card', date: '2026-09-02' }, CTX);
  assert.strictEqual(row.payment_id, 'PM-1');
  assert.strictEqual(row.amount, 80);
  assert.strictEqual(row.method, 'card');
  assert.strictEqual(row.payment_date, '2026-09-02');
});

test('procedure_types: the length column is default_length_minutes, as written', () => {
  // The first draft of this feed called it default_minutes and would have
  // shipped a blank column to every practice.
  const row = bi.projectRow('procedure_types',
    { id: 'PC-1', cdt_code: 'D1110', description: 'Prophylaxis', default_fee: 110,
      default_length_minutes: 45, cdt_version: 'CDT 2026', effective_from: '2026-01-01',
      recall_months: 6, created_at: '2026-08-01' }, CTX);
  assert.strictEqual(row.default_length_minutes, 45);
  assert.strictEqual(row.cdt_version, 'CDT 2026');
  assert.strictEqual(row.effective_from, '2026-01-01');
  assert.strictEqual(row.recall_months, 6);
});

test('recall_outreach: the contact date lives on `on`, not `date`', () => {
  const row = bi.projectRow('recall_outreach',
    { id: 'RC-1', patient_id: 'PT-1', procedure_type_id: 'PC-1', on: '2026-09-01',
      channel: 'phone', outcome: 'booked', note: 'left a voicemail first', created_at: '2026-09-01' }, CTX);
  assert.strictEqual(row.contacted_on, '2026-09-01');
  assert.strictEqual(row.channel, 'phone');
  assert.strictEqual(row.outcome, 'booked');
  assert.ok(!('note' in row), 'a free-text note reached the feed');
});

test('denials: saveDenial()\'s record projects, and carries NO derived deadline', () => {
  const row = bi.projectRow('denials',
    { id: 'DN-1', patient_id: 'PT-1', charge_id: 'CH-1', payer: 'Delta', denied_on: '2026-08-20',
      amount: 240, code: 'CO-197', reason: 'No prior authorization', stage: 'appealed',
      submitted_on: '2026-08-25', decided_on: '', recovered: 0, note: 'x', created_at: '2026-08-20' }, CTX);
  assert.strictEqual(row.amount_denied, 240);
  assert.strictEqual(row.code, 'CO-197');
  assert.strictEqual(row.recovered, 0);
  assert.strictEqual(row.decided_on, null, 'an empty decided_on became something other than null');
  // The deadline belongs to dnAppealWindow() in the app and nowhere else.
  assert.ok(!('appeal_deadline' in row));
  assert.ok(!('note' in row));
});

test('treatment_plans: total_fee sums the stored item fees and nothing else', () => {
  const row = bi.projectRow('treatment_plans',
    { id: 'TP-1', patient_id: 'PT-1', provider_id: 'PV-1', title: 'Quadrant 1',
      status: 'accepted', decided_on: '2026-09-01',
      items: [{ fee: 900 }, { fee: 250.5 }, { fee: 'not a number' }], created_at: '2026-08-28' }, CTX);
  assert.strictEqual(row.item_count, 3);
  assert.strictEqual(row.total_fee, 1150.5);
  // NOT tpPlanTotals(): no modelled insurance estimate crosses into the feed.
  assert.ok(!('estimated_insurance' in row));
  assert.ok(!('patient_portion' in row));
});

test('a plan with no items has NO fee, rather than a fee of zero', () => {
  const row = bi.projectRow('treatment_plans', { id: 'TP-2', patient_id: 'PT-1', items: [] }, CTX);
  assert.strictEqual(row.item_count, 0);
  assert.strictEqual(row.total_fee, null);
});

test('appointments: a staff-created row reports source "staff", not null', () => {
  const staff = bi.projectRow('appointments',
    { id: 'AP-1', patient_id: 'PT-1', provider_id: 'PV-1', start_time: '2026-09-03T14:00:00.000Z',
      end_time: '2026-09-03T14:45:00.000Z', status: 'Confirmed' }, CTX);
  assert.strictEqual(staff.source, 'staff');
  const self = bi.projectRow('appointments',
    { id: 'AP-2', patient_id: 'PT-1', source: 'self-scheduled' }, CTX);
  assert.strictEqual(self.source, 'self-scheduled');
});

test('a recall override of 0 means unset, and reports as unset', () => {
  const zero = bi.projectRow('patients', { id: 'PT-1', recall_months_override: 0 }, CTX);
  assert.strictEqual(zero.recall_months_override, null);
  const set = bi.projectRow('patients', { id: 'PT-2', recall_months_override: 4 }, CTX);
  assert.strictEqual(set.recall_months_override, 4);
});

test('a projection never throws on a malformed row -- it reports nulls', () => {
  Object.keys(bi.DATASETS).forEach((k) => {
    assert.doesNotThrow(() => bi.projectRow(k, null, CTX), k + ' threw on null');
    assert.doesNotThrow(() => bi.projectRow(k, { items: 'not an array', photos: 7 }, CTX), k + ' threw');
  });
});

// ── 6. PAGING IS SAFE TO LOOP ON ───────────────────────────────────────────

test('paging defaults are sane and the maximum is enforced', () => {
  assert.deepStrictEqual(bi.pageParams({}), { limit: bi.DEFAULT_PAGE_SIZE, offset: 0 });
  assert.strictEqual(bi.pageParams({ limit: '999999' }).limit, bi.MAX_PAGE_SIZE);
  assert.strictEqual(bi.pageParams({ limit: '-5' }).limit, bi.DEFAULT_PAGE_SIZE);
  assert.strictEqual(bi.pageParams({ limit: 'abc' }).limit, bi.DEFAULT_PAGE_SIZE);
  assert.strictEqual(bi.pageParams({ offset: '-1' }).offset, 0);
  assert.strictEqual(bi.pageParams({ offset: '40' }).offset, 40);
});

test('paging over an unsorted read visits every row exactly once', () => {
  // The failure this prevents: without a deterministic order, two pages can
  // both contain one row and both miss another, and the tool cannot tell.
  const rows = [];
  for (let i = 0; i < 25; i++) rows.push({ id: 'PM-' + String(i).padStart(3, '0'), patient_id: 'PT-1', amount: i });
  const shuffled = rows.slice().reverse();
  const projected = bi.projectRows('payments', shuffled, CTX);

  const seen = [];
  for (let off = 0; off < 30; off += 10) {
    seen.push.apply(seen, bi.orderAndPage('payments', projected, 10, off).rows.map((r) => r.payment_id));
  }
  assert.strictEqual(seen.length, 25);
  assert.strictEqual(new Set(seen).size, 25, 'a row appeared on two pages or was skipped');
  assert.deepStrictEqual(seen, rows.map((r) => r.id), 'the order was not stable');
});

test('the total is the whole set, not the page', () => {
  const rows = [];
  for (let i = 0; i < 7; i++) rows.push({ id: 'PM-' + i, patient_id: 'PT-1' });
  const out = bi.orderAndPage('payments', bi.projectRows('payments', rows, CTX), 3, 0);
  assert.strictEqual(out.rows.length, 3);
  assert.strictEqual(out.total, 7);
});

test('an offset past the end is an empty page, not an error', () => {
  const out = bi.orderAndPage('payments', bi.projectRows('payments', [{ id: 'PM-1' }], CTX), 10, 500);
  assert.deepStrictEqual(out.rows, []);
  assert.strictEqual(out.total, 1);
});

// ── 7. THE CATALOG TELLS THE TRUTH ─────────────────────────────────────────

test('the catalog lists exactly what the role can actually pull', () => {
  const provider = bi.catalog('provider', false);
  assert.deepStrictEqual(
    provider.datasets.map((d) => d.dataset).sort(),
    bi.datasetsForRole('provider').sort()
  );
  provider.datasets.forEach((d) => assert.strictEqual(d.contains_financial_data, false));
});

test('the catalog says which datasets will be narrowed, before anyone pulls one', () => {
  const provider = bi.catalog('provider', false);
  const appts = provider.datasets.filter((d) => d.dataset === 'appointments')[0];
  assert.strictEqual(appts.scoped_to_your_patients, true);
  const ops = provider.datasets.filter((d) => d.dataset === 'operatories')[0];
  assert.strictEqual(ops.scoped_to_your_patients, false);
});

test('the catalog hides identifier columns when the feed does', () => {
  const off = bi.catalog('owner', false);
  const pts = off.datasets.filter((d) => d.dataset === 'patients')[0];
  assert.strictEqual(off.identifiers_included, false);
  pts.columns.forEach((c) => assert.ok(DIRECT_IDENTIFIERS.patients.indexOf(c.name) === -1, c.name + ' listed'));

  const on = bi.catalog('owner', true);
  const ptsOn = on.datasets.filter((d) => d.dataset === 'patients')[0];
  assert.ok(ptsOn.columns.some((c) => c.name === 'name'));
});

test('the catalog says out loud that derived measures are not in it', () => {
  assert.match(bi.catalog('owner', false).note, /not duplicated here/i);
});

// ── 8. TOKENS ──────────────────────────────────────────────────────────────

test('a minted token is prefixed, long, and never repeats', () => {
  const seen = new Set();
  for (let i = 0; i < 200; i++) {
    const t = bi.mintToken();
    assert.match(t, /^dntbi_[0-9a-f]{64}$/);
    assert.ok(!seen.has(t), 'mintToken repeated inside 200 draws');
    seen.add(t);
  }
});

test('the hash is stable, and does not contain the token', () => {
  const t = bi.mintToken();
  assert.strictEqual(bi.hashToken(t), bi.hashToken(t));
  assert.strictEqual(bi.hashToken(t).indexOf(t.slice(6)), -1);
  assert.match(bi.hashToken(t), /^[0-9a-f]{64}$/);
});

test('two different tokens do not hash alike', () => {
  assert.notStrictEqual(bi.hashToken(bi.mintToken()), bi.hashToken(bi.mintToken()));
});
