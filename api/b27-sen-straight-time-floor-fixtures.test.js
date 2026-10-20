// api/b27-sen-straight-time-floor-fixtures.test.js
//
// Run:  node api/b27-sen-straight-time-floor-fixtures.test.js
//
// CONCEPT. A live probe is only worth running if the numbers it will assert were
// proven offline first, against the real module, from the SAME file the probe
// reads -- otherwise the first live run is also the first time anybody learns
// whether the fixture means what its author thought.
//
// docs/2026-10-20-hank-b27-sen-straight-time-floor-live-probe.py writes the fixtures in
// docs/2026-10-20-hank-b27-sen-straight-time-floor-fixtures.json to SEN-AUDIT-2026 as soon as that
// licence exists. This file feeds the same JSON to the real
// api/_lib/sen-payroll.js and the real api/_lib/sen-evv-clock.js, so:
//   * the DOWNWARD visit lands in overpayments[] with the stated minutes/cents,
//   * the UPWARD control lands in adjustments[] (so a guard that drops
//     everything cannot pass),
//   * total_payable_cents >= gross_cents on every caregiver,
//   * and with the sign guard ABLATED (`dMin > 0` -> `dMin !== 0`) the same
//     fixture drives total_payable_cents below gross_cents -- fourth's H2.
// It also runs the exact request objects through the real propose/approve/clock
// validators, which is what can be checked about the wire without the key.
//
// WHAT THIS DOES NOT PROVE: that SEN-AUDIT-2026's deployed endpoints accept the
// sequence. That is the live probe's job and stays UNPROVEN until the key exists.
//
// Exit: 0 all arms passed - 1 an arm FAILED

'use strict';
const fs = require('fs');
const path = require('path');

const FIX = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', '2026-10-20-hank-b27-sen-straight-time-floor-fixtures.json'), 'utf8'));
const CLOCK = require('./_lib/sen-evv-clock');
const PAYROLL_FILE = path.join(__dirname, '_lib', 'sen-payroll.js');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 500) : '')); }
}
function section(s) { console.log('\n' + s); }

const NOW = new Date();
const NOW_ISO = NOW.toISOString();
const y = NOW.getUTCFullYear(), m = NOW.getUTCMonth();
const pad = (n) => String(n).padStart(2, '0');
const PERIOD_START = y + '-' + pad(m + 1) + '-01';
const PERIOD_END = y + '-' + pad(m + 1) + '-' + pad(new Date(Date.UTC(y, m + 1, 0)).getUTCDate());

// ── the wire: the same objects the probe sends, through the same validators ──
section('1. the request objects pass the real validators');
const visitsAsStored = FIX.visits.map((v) => {
  const clockCheck = CLOCK.checkClockEvent(Object.assign({ id: v.id }, FIX.clock), {}, NOW_ISO);
  ok('1a[' + v.id + ']. the caregiver clock write is accepted (past times are flagged, not refused)',
    clockCheck.ok === true, JSON.stringify(clockCheck.error || clockCheck));
  const data = Object.assign({}, FIX.schedule, FIX.clock);
  const prop = CLOCK.proposeCorrection(data,
    { field: 'clock_out_at', proposed_at: v.proposed_clock_out_at, reason_code: FIX.correction_reason_code },
    'audit-owner', NOW_ISO);
  ok('1b[' + v.id + ']. the owner may propose the correction', prop.ok === true, JSON.stringify(prop.error || ''));
  const appr = prop.ok ? CLOCK.approveCorrection(prop.entry, 'audit-owner', NOW_ISO, 'owner') : { ok: false };
  ok('1c[' + v.id + ']. ...and the OWNER may approve their own (one account is enough, no second scheduler)',
    appr.ok === true && appr.entry.status === 'approved' && appr.entry.self_approved === true,
    JSON.stringify(appr.error || appr.entry || ''));
  data.clock_corrections = [appr.entry];
  return Object.assign({ id: v.id, assigned_employee_id: FIX.caregiver_id }, data);
});
const selfNotOwner = CLOCK.approveCorrection(
  CLOCK.proposeCorrection({}, { field: 'clock_out_at', proposed_at: FIX.visits[0].proposed_clock_out_at,
    reason_code: FIX.correction_reason_code }, 'someone', NOW_ISO).entry, 'someone', NOW_ISO, 'scheduler');
ok('1d. CONTROL: a non-owner approving their own correction is REFUSED, so 1c is not a validator that approves anything',
  selfNotOwner.ok === false && selfNotOwner.error.code === 'SELF_APPROVAL_REFUSED', JSON.stringify(selfNotOwner));

function run(modulePath) {
  delete require.cache[require.resolve(modulePath)];
  const mod = require(modulePath);
  return mod.computePayroll({
    visits: visitsAsStored,
    period_start: PERIOD_START, period_end: PERIOD_END,
    week_start_day: 'sunday',
    closed_periods: [{ period_start: FIX.closing.period_start, period_end: FIX.closing.period_end,
                       paid_at: FIX.closing.paid_at, closing_id: FIX.closing.closing_id }],
    resolveRate: () => ({ status: 'applied', rate_per_hour: FIX.rate.rate_per_hour })
  });
}

section('2. the real pay run, fixture in, numbers out');
const out = run('./_lib/sen-payroll');
ok('2a. the run was not refused', !out.refused, JSON.stringify(out.refused || ''));
FIX.visits.forEach((v) => {
  const list = out[v.expect.bucket] || [];
  const hit = list.filter((e) => e.visit_id === v.id);
  ok('2b[' + v.id + ']. it lands in ' + v.expect.bucket + '[] exactly once', hit.length === 1, JSON.stringify(list));
  if (v.expect.bucket === 'overpayments') {
    ok('2c[' + v.id + ']. ' + v.expect.minutes + ' minutes, ' + v.expect.cents + ' cents, flagged for a human',
      hit[0] && hit[0].minutes_overpaid === v.expect.minutes && hit[0].cents_overpaid === v.expect.cents
        && hit[0].requires_human_act === true, JSON.stringify(hit[0]));
  } else {
    ok('2c[' + v.id + ']. ' + v.expect.minutes + ' minutes, ' + v.expect.cents + ' cents paid as an adjustment',
      hit[0] && hit[0].minutes_delta === v.expect.minutes && hit[0].cents_delta === v.expect.cents, JSON.stringify(hit[0]));
  }
});
const cgs = out.caregivers || [];
ok('2d. THE INVARIANT H2 BROKE: total_payable_cents >= gross_cents on every caregiver',
  cgs.length > 0 && cgs.every((c) => c.total_payable_cents >= c.gross_cents), JSON.stringify(cgs.map((c) => [c.gross_cents, c.total_payable_cents])));
ok('2e. the overpayment is reported in its own total and NOT netted into pay',
  out.overpayment_cents === 2000 && cgs.every((c) => c.adjustment_cents === 2000), JSON.stringify([out.overpayment_cents, cgs.map((c) => c.adjustment_cents)]));

section('3. ablation: remove the sign guard and the same fixture must break the invariant');
const src = fs.readFileSync(PAYROLL_FILE, 'utf8');
const GUARD = 'if (dMin > 0) {';
ok('3a. the guard anchor is present exactly once in the real module', src.split(GUARD).length === 2);
const ablFile = path.join(__dirname, '_lib', '_b27_ablate_payroll.js');
let abl;
try {
  fs.writeFileSync(ablFile, src.replace(GUARD, 'if (dMin !== 0) {'));
  abl = run('./_lib/_b27_ablate_payroll');
} finally { try { fs.unlinkSync(ablFile); } catch (e) { /* checked below */ } }
const ablCgs = abl.caregivers || [];
ok('3b. WITHOUT the guard, total_payable_cents < gross_cents -- the $20 silent deduction fourth drove',
  ablCgs.some((c) => c.total_payable_cents < c.gross_cents) || ablCgs.some((c) => c.adjustment_cents < 2000),
  JSON.stringify(ablCgs.map((c) => [c.gross_cents, c.adjustment_cents, c.total_payable_cents])));
ok('3c. ...and the downward visit is no longer an overpayment (it was silently netted)',
  (abl.overpayments || []).length === 0, JSON.stringify(abl.overpayments));
ok('3d. no ablation copy left behind', !fs.existsSync(ablFile));

section('4. b33: the LIVE run failed A2/A2b/B1/B2/B4 -- reproduce it with the closing ABSENT');
// The live close answered 503 AUDIT_UNAVAILABLE, so NO closed period existed when
// the pay run ran. computePayroll only computes a carry-forward for a visit that
// is `inClosed && !inPeriod`, so with no closing the two August visits are simply
// outside the run. If that explains the live result, this run must fail exactly
// B1, B2 and B4 and still pass B3 -- which is what the live probe reported.
const noClose = (function () {
  delete require.cache[require.resolve('./_lib/sen-payroll')];
  return require('./_lib/sen-payroll').computePayroll({
    visits: visitsAsStored, period_start: PERIOD_START, period_end: PERIOD_END,
    week_start_day: 'sunday', closed_periods: [],
    resolveRate: () => ({ status: 'applied', rate_per_hour: FIX.rate.rate_per_hour })
  });
})();
const ncg = noClose.caregivers || [];
ok('4a. B1 shape: NO overpayment for the downward visit', (noClose.overpayments || []).length === 0, JSON.stringify(noClose.overpayments));
ok('4b. B2 shape: NO adjustment for the upward visit', (noClose.adjustments || []).length === 0, JSON.stringify(noClose.adjustments));
ok('4c. B4 shape: overpayment_cents is 0, not 2000', noClose.overpayment_cents === 0, noClose.overpayment_cents);
ok('4d. B3 STILL HOLDS: total_payable_cents >= gross_cents (the invariant is not what failed)',
  ncg.every((c) => c.total_payable_cents >= c.gross_cents), JSON.stringify(ncg));
ok('4e. so the sign guard is NOT implicated: with the closing present (section 2) the same visits land where they should',
  (out.overpayments || []).length === 1 && (out.adjustments || []).length === 1);

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  b27 straight-time-floor fixtures: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
