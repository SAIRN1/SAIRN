// api/_lib/sairncode-kx-accumulator.test.js
// REQUIREMENT: a year-to-date therapy total is never reported as complete when
//   rows were excluded, and is never accumulated from a free-text patient name
//   or from a BILLED amount
//
// Run: node api/_lib/sairncode-kx-accumulator.test.js
//
// EVERY ARM IS IN BOTH DIRECTIONS. The honest case must produce a figure and a
// verdict; the partial case must produce a FLOOR and a different verdict. A
// suite that only checked the happy path would pass against an accumulator
// that silently treated every unreadable row as zero -- which is the exact
// defect rule 2 and rule 3 of the module header exist to stop, and it is the
// direction that ends in a false attestation rather than a denial.
'use strict';
const assert = require('assert');
const {
  accumulateTherapy, cents, yearOf, DISCIPLINE_BUCKET, THRESHOLDS_BY_YEAR,
} = require('./sairncode-kx-accumulator');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass += 1; console.log('  ok   ' + name); }
  catch (e) { fail += 1; console.log('  FAIL ' + name + '\n         ' + e.message); }
}

const row = (o) => Object.assign({
  discipline: 'PT', beneficiary_id: 'B1', date: '2026-03-01', allowed_amount: 100,
}, o);

console.log('KX therapy accumulator -- a floor must never read as a total\n');

// ── PT AND SLP SHARE ONE BUCKET; OT HAS ITS OWN ─────────────────────────
t('PT and SLP accumulate into ONE bucket, OT into its own', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ discipline: 'PT', allowed_amount: 100 }),
      row({ discipline: 'SLP', allowed_amount: 50 }),
      row({ discipline: 'OT', allowed_amount: 25 })],
  });
  const b = r.beneficiaries[0];
  assert.strictEqual(b.pt_slp_cents, 15000, 'PT+SLP must be 150.00');
  assert.strictEqual(b.ot_cents, 2500, 'OT must be its own 25.00');
});
t('...and the mapping has exactly three disciplines, not one and not four', () => {
  assert.deepStrictEqual(Object.keys(DISCIPLINE_BUCKET).sort(), ['OT', 'PT', 'SLP']);
  assert.strictEqual(DISCIPLINE_BUCKET.PT, DISCIPLINE_BUCKET.SLP);
  assert.notStrictEqual(DISCIPLINE_BUCKET.OT, DISCIPLINE_BUCKET.PT);
});

// ── RULE 2: ALLOWED IS NOT BILLED ───────────────────────────────────────
t('a row with NO allowed_amount is EXCLUDED, not accumulated at its billed amount', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ allowed_amount: undefined, amount: 9999 })],
  });
  assert.strictEqual(r.excluded.no_allowed, 1);
  assert.strictEqual(r.beneficiaries[0].pt_slp_cents, 0,
    'the BILLED amount must never reach the total -- that is the overstate '
    + 'direction, and overstating ends in a false attestation');
});
t('...and the excluded row makes that beneficiary a FLOOR', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ allowed_amount: 100 }), row({ allowed_amount: null })],
  });
  assert.strictEqual(r.beneficiaries[0].is_floor, true);
  assert.strictEqual(r.beneficiaries[0].kx.pt_slp, 'BELOW_ON_RECORDED',
    'a partial year must NOT report the same verdict as a complete one');
});
t('THE PAIRED POSITIVE: a complete year reports BELOW, not BELOW_ON_RECORDED', () => {
  const r = accumulateTherapy({ year: 2026, rows: [row({ allowed_amount: 100 })] });
  assert.strictEqual(r.beneficiaries[0].is_floor, false);
  assert.strictEqual(r.beneficiaries[0].kx.pt_slp, 'BELOW',
    'if every year read as a floor the distinction would be decoration');
});

// ── RULE 1: IDENTITY, NEVER A NAME ──────────────────────────────────────
t('a row with no beneficiary_id goes to the UNATTRIBUTED bucket, not to a patient', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ beneficiary_id: '', patient: 'Jane Smith', allowed_amount: 40 })],
  });
  assert.strictEqual(r.beneficiaries.length, 0, 'no beneficiary may be invented');
  assert.strictEqual(r.unattributed.pt_slp_cents, 4000);
  assert.strictEqual(r.excluded.no_beneficiary, 1);
});
t('...and two DIFFERENT ids with the SAME patient name stay separate', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ beneficiary_id: 'B1', patient: 'J Smith', allowed_amount: 100 }),
      row({ beneficiary_id: 'B2', patient: 'J Smith', allowed_amount: 100 })],
  });
  assert.strictEqual(r.beneficiaries.length, 2,
    'name-matching here counts one patient’s therapy dollars against another’s '
    + 'federal threshold, in both directions at once');
});
t('...and the same id under two SPELLINGS of the name stays ONE beneficiary', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ beneficiary_id: 'B1', patient: 'J Smith', allowed_amount: 100 }),
      row({ beneficiary_id: ' B1 ', patient: 'Jane  Smith', allowed_amount: 100 })],
  });
  assert.strictEqual(r.beneficiaries.length, 1);
  assert.strictEqual(r.beneficiaries[0].pt_slp_cents, 20000);
});

// ── THE THRESHOLD ITSELF ────────────────────────────────────────────────
t('at exactly the threshold the verdict is AT_OR_OVER, not BELOW', () => {
  const r = accumulateTherapy({
    year: 2026, rows: [row({ allowed_amount: 2480 })],
  });
  assert.strictEqual(r.beneficiaries[0].kx.pt_slp, 'AT_OR_OVER',
    'the transmittal denies claims ABOVE the amount; the boundary belongs '
    + 'inside the attested side, not outside it');
});
t('a beneficiary OVER the threshold reports AT_OR_OVER even when rows are missing', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ allowed_amount: 3000 }), row({ allowed_amount: null })],
  });
  assert.strictEqual(r.beneficiaries[0].is_floor, true);
  assert.strictEqual(r.beneficiaries[0].kx.pt_slp, 'AT_OR_OVER',
    'a floor that has crossed has crossed -- missing rows can only push it '
    + 'further over, so this is the one verdict a partial year may state flatly');
});
t('the $3,000 MR threshold is reported SEPARATELY from KX and does not move it', () => {
  const r = accumulateTherapy({ year: 2026, rows: [row({ allowed_amount: 2600 })] });
  const b = r.beneficiaries[0];
  assert.strictEqual(b.kx.pt_slp, 'AT_OR_OVER');
  assert.strictEqual(b.mr.pt_slp, 'BELOW',
    'over the KX threshold and under MR is the normal case and must be two '
    + 'answers -- MR is a documentation-review exposure, not a denial');
});

// ── AN UNKNOWN YEAR IS A REFUSAL, NOT A DEFAULT ─────────────────────────
t('an unknown year yields NO thresholds and NO verdict', () => {
  const r = accumulateTherapy({ year: 2031, rows: [row({ date: '2031-02-01' })] });
  assert.strictEqual(r.year_known, false);
  assert.strictEqual(r.thresholds_cents, null);
  assert.strictEqual(r.beneficiaries[0].kx.pt_slp, 'UNKNOWN_YEAR',
    'defaulting to the latest amounts would price a future year against stale '
    + 'figures and report it as a normal answer');
});
t('...but the dollars are still accumulated, so the year is unpriced and not unread', () => {
  const r = accumulateTherapy({ year: 2031, rows: [row({ date: '2031-02-01', allowed_amount: 75 })] });
  assert.strictEqual(r.beneficiaries[0].pt_slp_cents, 7500);
});
t('2026 thresholds are the transmittal amounts, in cents', () => {
  assert.deepStrictEqual(THRESHOLDS_BY_YEAR[2026],
    { pt_slp: 248000, ot: 248000, mr: 300000 });
});

// ── DATES ───────────────────────────────────────────────────────────────
t('an IMPOSSIBLE date is not silently repaired into a neighbouring year', () => {
  assert.strictEqual(yearOf('2026-02-31'), null);
  assert.strictEqual(yearOf('2025-12-32'), null);
  assert.strictEqual(yearOf('2026-13-01'), null);
  assert.strictEqual(yearOf('2026-03-01'), 2026);
});
t('a row from ANOTHER year is excluded as wrong_year, not counted', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ date: '2025-12-31', allowed_amount: 5000 })],
  });
  assert.strictEqual(r.excluded.wrong_year, 1);
  assert.strictEqual(r.beneficiaries.length, 0);
});

// ── NOT-THERAPY IS NOT AN EXCLUSION ─────────────────────────────────────
t('a non-therapy claim is counted as not_therapy, NOT as a failed therapy row', () => {
  const r = accumulateTherapy({
    year: 2026,
    rows: [row({ discipline: undefined }), row({ discipline: 'DME' })],
  });
  assert.strictEqual(r.not_therapy_rows, 2);
  assert.deepStrictEqual(r.excluded,
    { no_allowed: 0, no_discipline: 0, no_date: 0, wrong_year: 0, no_beneficiary: 0 },
    'counting an ordinary claim as a lost therapy row would make every '
    + 'practice look like it had lost most of its therapy data');
});

// ── RULE 4: THE FIGURES TRACE BACK TO A POPULATION ──────────────────────
t('every row lands in exactly one place and the counts reconcile to total_rows', () => {
  const rows = [
    row({ allowed_amount: 100 }),                        // counted
    row({ allowed_amount: null }),                       // no_allowed
    row({ date: 'not-a-date' }),                         // no_date
    row({ date: '2025-01-01' }),                         // wrong_year
    row({ beneficiary_id: '' }),                         // no_beneficiary
    row({ discipline: 'X' }),                            // not therapy
  ];
  const r = accumulateTherapy({ year: 2026, rows: rows });
  const counted = r.beneficiaries.reduce((s, b) => s + b.rows_counted, 0);
  const excl = Object.keys(r.excluded).reduce((s, k) => s + r.excluded[k], 0);
  assert.strictEqual(counted + excl + r.not_therapy_rows, r.total_rows,
    'a row counted under two exclusion reasons would make the tally larger '
    + 'than the population it describes');
});

// ── MONEY ───────────────────────────────────────────────────────────────
t('cents() refuses what is not money, and null is not zero', () => {
  assert.strictEqual(cents(undefined), null);
  assert.strictEqual(cents(''), null);
  assert.strictEqual(cents('abc'), null);
  assert.strictEqual(cents(-5), null);
  assert.strictEqual(cents(0), 0);
  assert.strictEqual(cents('12.34'), 1234);
  assert.strictEqual(cents(0.1) + cents(0.2), cents(0.3));
});
t('a malformed row does not take the whole practice figure out', () => {
  const r = accumulateTherapy({ year: 2026, rows: [null, undefined, 7, row({})] });
  assert.strictEqual(r.beneficiaries[0].pt_slp_cents, 10000);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
