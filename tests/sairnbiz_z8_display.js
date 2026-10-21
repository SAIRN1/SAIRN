// tests/sairnbiz_z8_display.js
// Run: node tests/sairnbiz_z8_display.js [path-to-sairnbiz.html]
//
// fourth b47 Z8 display, committed in b49 after cc's b36 review found its
// tests only in fourth's session scratchpad. CONCEPT: the run table and the
// payroll CSV show what sbPayLine() records -- the table reads the lines the
// run STORED, never a re-pricing from today's roster; the CSV builds its line
// columns with sbPayLine() itself. Workweek start, 29 CFR 516.2(a)(5), is READ
// from sbWeekStart() rather than typed in; sex, 516.2(a)(4), is stored as
// entered and never leaves the device.
//
// Every function is EXTRACTED BY NAME from the shipped sairnbiz.html and run
// in a vm. sbPayLine is STUBBED in the CSV and run arms on purpose: the arms
// are about where the line columns come from, so a known line in proves the
// same line comes out. An extraction that fails REFUSES (exit 2).
//
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnbiz.html');
const html = fs.readFileSync(FILE, 'utf8');
function grab(head, oneLine) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  return oneLine ? html.slice(i, html.indexOf('\n', i)) : html.slice(i, html.indexOf('\n}\n', i) + 2);
}
const SRC = [
  grab('function H(s){', true), grab('function fmt(n){', true), grab('function fdate(d){', true),
  grab('function sbCsvCell(v){', true), grab('function openEmpModal(){', true),
  grab('function sbWeekStart(d){'), grab('function sbWorkweekStart(){'),
  grab('function runPayroll() {'), grab('function rPayRuns(){'), grab('function csv(type){'),
  grab('function editEmp(id){'), grab('function saveEmp(){'), grab('function syncEmps(emps){'),
].join('\n');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 300) : '')); }
}

const LINE = (e) => ({ employee_id: e.id, name: e.fn + ' ' + e.ln, period_start: '2026-10-12', period_end: '2026-10-18',
  pay_date: '2026-10-30', regular_hours: 40, ot_hours: 10, rate: 20, straight_time_earnings: 1000, ot_premium: 100,
  gross: 1100, withholding: 'not computed', net_pay: 'not computed' });

function make(opts) {
  opts = opts || {};
  const store = Object.assign({ sb_emps: [{ id: 'EA', fn: 'Ann', ln: 'Able', rate: 20, status: 'Active', type: 'Full Time' }] }, opts.store || {});
  const els = {};
  const el = (id) => (els[id] = els[id] || { id, value: (opts.form || {})[id] || '', innerHTML: '', textContent: '', style: {},
    classList: { add() {}, remove() {} } });
  const sent = [], files = [];
  const ctx = {
    JSON, Object, Array, String, Number, Math, Boolean, Date, isFinite, parseFloat, parseInt, RegExp, Promise,
    console: { warn() {}, log() {} },
    $: el, toast() {}, sessionStorage: { getItem: () => null },
    ld: (k, d) => (store[k] !== undefined ? JSON.parse(JSON.stringify(store[k])) : d),
    st: (k, v) => { store[k] = JSON.parse(JSON.stringify(v)); return true; },
    sbLocalToday: () => '2026-10-21',
    sbPayLine: opts.payLine || ((e) => LINE(e)),
    checkPayrollAnomalies: () => [], renderPayrollAnomalyBanner() {}, sbGlPost() {},
    sbPayrollTotals: () => ({ employees: 1, gross: 1100, taxes_fica: 84.15, benefits: 0, total: 1184.15, frequencies: {},
      employees_on_default_frequency: 0, employees_on_assumed_benefit_cost: 0, annual_gross: 57200 }),
    SB_PAY_PERIOD_RULE: 'rule', sbPayrollBasisText: () => 'basis',
    sbPayFreq: () => 'Weekly', sbPayFreqIsDefault: () => false, sbHoursPerPeriod: () => 50, sbGrossPerPeriod: () => 1100,
    sbAnnualGross: () => 57200, sbBenefitPerPeriod: () => 0, sbBenefitIsAssumed: () => false,
    sbVendorPaidYTD: () => ({}), sbBudgetActuals: () => ({ rows: [] }),
    SB_PAY_FREQ_DEFAULT: 'Biweekly', eid: null, sbNextId: () => 'E9', closeEmpModal() {}, rEmps() {},
    sbRecordSyncResult: () => true,
    DATA_API: '/api/sd-data', APP_ID: 'sairnbiz',
    fetch: (u, o) => { sent.push(o && o.body || ''); return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ok: true }) }); },
    Blob: function (parts) { this.text = parts.join(''); },
    URL: { createObjectURL: (b) => b },
    document: { createElement: () => ({ click() { files.push({ name: this.download, body: this.href.text }); } }) },
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { ctx, store, els, sent, files };
}

(async () => {
  console.log('516.2(a)(5) workweek start');
  let t = make();
  const ww = t.ctx.sbWorkweekStart();
  check('W1. names the day sbWeekStart() starts on, at local midnight', /^Monday 00:00/.test(ww), ww);
  t.ctx.sbWeekStart = () => '2026-10-18';   // a Sunday
  check('W2. DERIVED, not typed: if the week boundary moved to Sunday, the record would say Sunday', /^Sunday 00:00/.test(t.ctx.sbWorkweekStart()), t.ctx.sbWorkweekStart());

  console.log('the run record and the run table');
  t = make({ form: { prpaydate: '2026-10-30' }, store: { sb_payruns: [{ id: 'PROLD', run_on: '2026-09-01', employees: 1, gross: 100, taxes_fica: 7.65, benefits: 0, total: 107.65 }] } });
  t.ctx.runPayroll();
  const run = t.store.sb_payruns[0];
  check('R1. a run stamps its workweek start', run.workweek_start === t.ctx.sbWorkweekStart(), JSON.stringify(run.workweek_start));
  check('R2. a run stores one line per active employee and the entered pay date', run.lines.length === 1 && run.pay_date === '2026-10-30' && run.pay_date_source === 'entered', JSON.stringify(run));
  // The table must read STORED lines: a sbPayLine that throws proves nothing re-prices.
  t.ctx.sbPayLine = () => { throw new Error('re-priced'); };
  let threw = '';
  try { t.ctx.rPayRuns(); } catch (e) { threw = e.message; }
  check('R3a. rendering the table does not re-price (sbPayLine never called)', threw === '', threw);
  const rows = t.ctx.$('prtbody').innerHTML;
  check('R3. the table renders from the STORED lines (sbPayLine is not called)', /1,100\.00/.test(rows), rows.slice(0, 200));
  check('R4. the newest row shows the pay date', /Oct 30, 2026/.test(rows), rows.slice(0, 200));
  check('R5. withholding and net pay read "not computed", never $0', /not computed/.test(rows) && !/\$0\.00/.test(rows));
  check('R6. a run from before b46 says "not recorded" for lines and pay date', (rows.match(/not recorded/g) || []).length >= 2, rows.slice(-400));
  t.store.sb_payruns[0].lines[0].name = '<img src=x onerror=1>';
  try { t.ctx.rPayRuns(); } catch (e) {}
  check('R7. a name with markup is escaped', t.ctx.$('prtbody').innerHTML.indexOf('<img') === -1);

  console.log('the payroll CSV');
  t = make({ form: { prpaydate: '2026-10-30' } });
  let asked = null;
  t.ctx.sbPayLine = (e, runOn, payDate) => { asked = [runOn, payDate]; return LINE(e); };
  t.ctx.csv('payroll');
  const lines = (t.files[0] || { body: '' }).body.split('\n');
  const head = lines[0].split(',').map((c) => c.replace(/^"|"$/g, ''));
  const row = (lines[1] || '').split(',').map((c) => c.replace(/^"|"$/g, ''));
  const col = (n) => row[head.indexOf(n)];
  check('C1. the line columns are present', ['Period Start', 'Period End', 'Pay Date', 'Regular Hours', 'OT Hours', 'Straight-time Earnings',
    'OT Premium', 'Withholding', 'Net Pay', 'Workweek Start'].every((c) => head.indexOf(c) !== -1), head.join('|'));
  check('C2. the line columns come FROM sbPayLine (period, OT premium, withholding)',
    col('Period Start') === '2026-10-12' && col('OT Premium') === '100.00' && col('Withholding') === 'not computed', row.join('|'));
  check('C3. sbPayLine is asked for today and the pay date in the run box', JSON.stringify(asked) === JSON.stringify(['2026-10-21', '2026-10-30']), JSON.stringify(asked));
  check('C4. no home address or DOB column', !head.some((h) => /address|dob|birth/i.test(h)), head.join('|'));

  console.log('516.2(a)(4) sex');
  t = make({ form: { efn: 'Bo', eln: 'Baker', etype: 'Full Time', ehr: '30', esex: 'Female', estatus: 'Active' },
    store: { sb_lic: 'SB-TEST' } });
  t.ctx.saveEmp();
  await new Promise((r) => setImmediate(r));
  const bo = t.store.sb_emps.find((e) => e.fn === 'Bo');
  check('S1. saved on the employee as entered', bo && bo.sex === 'Female', JSON.stringify(bo));
  check('S2. control: the roster sync really went out', t.sent.length === 1 && /Baker/.test(t.sent[0]), t.sent.join(' '));
  check('S3. the sync does NOT carry it', !/Female/.test(t.sent.join(' ')), t.sent.join(' '));
  t.ctx.$('esex').value = 'X'; if (bo) t.ctx.editEmp(bo.id);
  check('S4. edit pre-fills the stored value', t.ctx.$('esex').value === 'Female', t.ctx.$('esex').value);
  t.ctx.openEmpModal();
  check('S5. a new employee starts blank (not recorded)', t.ctx.$('esex').value === '', t.ctx.$('esex').value);

  console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnbiz Z8 display: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('HARNESS ERROR: ' + (e && e.stack || e)); process.exit(2); });
