// tests/sairnbiz_timesheet_hours.js
//
// Run:  node tests/sairnbiz_timesheet_hours.js
//
// THE TIMESHEET PANEL REPORTED A WEEK OF HOURS NOBODY EVER ENTERED.
// rTS() built every table cell and five KPIs from `td`, an eight-row array of
// hours written into the source and indexed by each employee's POSITION in the
// filtered Active list, with `|| [8,8,8,8,8,0]` for anyone past the eighth.
// The pay RATES are real, so "Labor Cost (Week)" multiplied a real rate by an
// invented week and printed a plausible wrong dollar figure in a payroll
// product. Nothing on screen said where the hours came from.
//
// THE TWO ARMS IN SECTION 3 ARE THE POINT OF THIS FILE. Position-indexing has
// two failure modes that a reader does not see by looking at the array:
//
//   * DEACTIVATE AN EMPLOYEE AND THE HOURS BELOW SHIFT UP. Set E003 inactive
//     and E004 lands on index 2, inheriting E003's 47-hour week and its 7
//     hours of overtime. Nobody edited a timesheet. Two people's weeks swapped
//     and the app reported both as fact.
//   * THE NINTH ACTIVE EMPLOYEE GETS EXACTLY 40 HOURS. Not a placeholder
//     anyone would read as a placeholder -- an ordinary full week, invented.
//
// Both are driven here against the PRE-FIX shape as well as the current one,
// because an assertion that the new code is right proves nothing about whether
// it fixed anything unless the old code is shown to be wrong in the same
// harness. The pre-fix body is reproduced literally in section 3 for the only
// reason that justifies a copy: it no longer exists in the file to lift.
//
// SECTION 4 DOES NOT TRUST THE FLAG. SB_TS_HAVE_A_WRITE_PATH is a boolean
// somebody has to remember to move. It is checked against the real number of
// st('sb_ts') writers in the file, so the day an entry path lands the dash is
// replaced by a measurement rather than by somebody's memory. Same convention
// as tests/sairnbiz_incidents_kpi.js, which this fix follows throughout.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnbiz.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
const queue = [];
function test(name, fn) { queue.push({ name, fn }); }
function section(t) { queue.push({ section: t }); }

function fnBodyAt(at) {
  const open = html.indexOf('{', at);
  let depth = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}
function fnBody(name) {
  const at = html.indexOf(name);
  assert.ok(at > 0, 'not found in sairnbiz.html: ' + name);
  return fnBodyAt(at);
}

// Comments are stripped before anything is COUNTED. The fix's own note quotes
// `st('sb_ts')` while explaining the flag, and counting prose as code would
// make the file look like it had a writer it does not have -- the same mistake
// tests/sairnbiz_incidents_kpi.js documents for sb_incidents.
const codeOnly = html.split('\n')
  .map((l) => l.replace(/^(\s*)\/\/.*$/, '$1'))
  .join('\n');
function tsWriters() {
  return (codeOnly.match(/st\(\s*'sb_ts'/g) || []).length;
}

// Eight employees with DISTINCT rates, so a cost figure attributed to the
// wrong person is visible as a different number rather than hidden by a
// shared rate.
function emps(n) {
  const out = [];
  for (let i = 1; i <= n; i++) {
    out.push({
      id: 'E' + String(i).padStart(3, '0'),
      fn: 'First' + i, ln: 'Last' + i,
      rate: 10 + i, status: 'Active',
    });
  }
  return out;
}

// The real rTS() and the real flag declaration, in a realm with a DOM stub.
function harness(opts) {
  opts = opts || {};
  const el = {};
  const get = (id) => (el[id] || (el[id] = { textContent: '', innerHTML: '', style: {} }));
  const flagSrc = /var SB_TS_HAVE_A_WRITE_PATH\s*=\s*(true|false)\s*;/.exec(html);
  assert.ok(flagSrc, 'SB_TS_HAVE_A_WRITE_PATH declaration not found');
  const stored = opts.stored || {};
  const ctx = {
    JSON, Object, Array, String, Number, Math,
    ld: (k, d) => (Object.prototype.hasOwnProperty.call(stored, k)
      ? JSON.parse(JSON.stringify(stored[k])) : d),
    st: () => true,
    $: get,
    H: (s) => String(s),
    fmt: (n) => '$' + Number(n || 0).toFixed(2),
    __el: el,
  };
  vm.createContext(ctx);
  vm.runInContext(
    (opts.flag === undefined ? flagSrc[0]
      : 'var SB_TS_HAVE_A_WRITE_PATH=' + opts.flag + ';') + '\n'
    + fnBody('function rTS()'), ctx);
  ctx.rTS();
  return ctx;
}

// Cells of one rendered row, by employee surname, so an assertion names a
// PERSON rather than a row index -- the defect under test is precisely that a
// row index stopped meaning a person.
function rowCells(ctx, surname) {
  const rows = ctx.__el.tstbody.innerHTML.split('<tr>').slice(1);
  const row = rows.find((r) => r.indexOf(surname + '</strong>') !== -1);
  assert.ok(row, 'no rendered row for ' + surname);
  return row.split('<td').slice(1).map((c) => {
    const gt = c.indexOf('>');
    return c.slice(gt + 1).replace(/<[^>]*>/g, '').replace('</td', '').trim();
  });
}

// ═══════════════════════════════════════════════════════════════════════════
section('1. with no write path the panel states that, instead of a number');

test('all three surviving KPIs read "--", not 0 and not $0.00', () => {
  const c = harness({ stored: { sb_emps: emps(8) } });
  assert.strictEqual(c.__el['ts-hrs'].textContent, '--');
  assert.strictEqual(c.__el['ts-ot'].textContent, '--');
  assert.strictEqual(c.__el['ts-cost'].textContent, '--');
});

test('and the note says WHY, and is shown', () => {
  const c = harness({ stored: { sb_emps: emps(8) } });
  assert.ok(/not recorded in this app yet/.test(c.__el['ts-note'].textContent),
    'the note no longer explains the dashes: ' + c.__el['ts-note'].textContent);
  assert.notStrictEqual(c.__el['ts-note'].style.display, 'none',
    'the note is hidden while the KPIs read "--", so the dashes are unexplained');
});

test('every employee row is dashes across, and no row invents a total', () => {
  const c = harness({ stored: { sb_emps: emps(8) } });
  for (const n of [1, 4, 8]) {
    const cells = rowCells(c, 'Last' + n);
    // name, six days, total, OT, pay estimate
    assert.strictEqual(cells.length, 10, 'row shape changed for Last' + n);
    assert.deepStrictEqual(cells.slice(1, 7), ['--', '--', '--', '--', '--', '--'],
      'Last' + n + ' has day hours with nothing recorded');
    assert.strictEqual(cells[7], '--', 'Last' + n + ' has a total with nothing recorded');
    assert.strictEqual(cells[8], '--', 'Last' + n + ' has overtime with nothing recorded');
    assert.strictEqual(cells[9], '--', 'Last' + n + ' has a pay estimate with nothing recorded');
  }
});

test('the static markup ships "--" too, so first paint claims nothing', () => {
  // Before rTS() runs the app does not know any hours. A hardcoded 0 in the
  // markup would state a zero-hour week for the length of that gap, and "$0"
  // under "Labor Cost (Week)" is a statement about payroll.
  for (const id of ['ts-hrs', 'ts-ot', 'ts-cost']) {
    const at = html.indexOf('id="' + id + '"');
    assert.ok(at > 0, id + ' tile not found');
    assert.ok(/^id="[a-z-]+">--</.test(html.slice(at, at + 40)),
      id + ' ships a hardcoded value in the markup again');
  }
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. with hours recorded, an employee WITHOUT a record is excluded');

test('recorded hours are totalled and unrecorded employees contribute nothing', () => {
  // E001 at $11/hr works 40; E002 at $12/hr works 44 (4 OT). The other six
  // have no record at all. Nothing about the six may reach any total.
  const c = harness({
    flag: true,
    stored: {
      sb_emps: emps(8),
      sb_ts: { E001: [8, 8, 8, 8, 8, 0], E002: [8, 8, 8, 8, 8, 4] },
    },
  });
  assert.strictEqual(c.__el['ts-hrs'].textContent, 84);
  assert.strictEqual(c.__el['ts-ot'].textContent, 4);
  // 40*11 + (40*12 + 4*12*1.5) = 440 + 552 = 992
  assert.strictEqual(c.__el['ts-cost'].textContent, '$992.00');
});

test('the exclusion is DISCLOSED, with both counts', () => {
  const c = harness({
    flag: true,
    stored: { sb_emps: emps(8), sb_ts: { E001: [8, 8, 8, 8, 8, 0] } },
  });
  const note = c.__el['ts-note'].textContent;
  assert.ok(/1 of 8/.test(note) && /other 7/.test(note),
    'the note does not state how many employees are excluded: ' + note);
  assert.notStrictEqual(c.__el['ts-note'].style.display, 'none');
});

test('with every employee recorded, there is no exclusion note to show', () => {
  // A clean week must not carry a warning -- a disclosure that is always on
  // stops being read, which is the failure mode the note exists to avoid.
  const two = emps(2);
  const c = harness({
    flag: true,
    stored: { sb_emps: two, sb_ts: { E001: [8, 0, 0, 0, 0, 0], E002: [8, 0, 0, 0, 0, 0] } },
  });
  assert.strictEqual(c.__el['ts-note'].textContent, '');
  assert.strictEqual(c.__el['ts-note'].style.display, 'none');
});

test('hours attach by EMPLOYEE ID, so a record cannot land on the wrong person', () => {
  // Only E005 has hours. E005 is fifth in the list; under the old code index 4
  // meant "the fifth active employee", which is not the same statement.
  const c = harness({
    flag: true,
    stored: { sb_emps: emps(8), sb_ts: { E005: [8, 8, 8, 8, 8, 0] } },
  });
  assert.strictEqual(rowCells(c, 'Last5')[7], '40');
  assert.strictEqual(rowCells(c, 'Last1')[7], '--');
  assert.strictEqual(rowCells(c, 'Last8')[7], '--');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. NEGATIVE CONTROLS -- the pre-fix shape, proved wrong in this harness');

// The old body, reproduced literally. It is copied rather than lifted for the
// one reason that justifies a copy: it is gone from the file. If these two
// stop reproducing the defect, every assertion above is proving nothing about
// what was actually fixed.
const OLD_BODY = `
function rTSold(){
  var emps=ld('sb_emps',[]).filter(function(e){return e.status==='Active';});
  var td=[[8,8,8,8,8,0],[8,8,8,8,10,0],[8,8,7,8,8,4],[8,8,8,8,8,0],[8,8,8,8,8,0],[8,8,8,8,8,0],[8,8,8,8,8,0],[0,0,5,0,5,0]];
  var out={};
  emps.forEach(function(e,i){
    var d=td[i]||[8,8,8,8,8,0];var t=d.reduce(function(a,b){return a+b;},0);
    out[e.id]={total:t,ot:Math.max(0,t-40)};
  });
  return out;
}`;
function oldShape(empList) {
  const ctx = { Math, ld: (k, d) => (k === 'sb_emps' ? empList : d) };
  vm.createContext(ctx);
  vm.runInContext(OLD_BODY, ctx);
  return ctx.rTSold();
}

test('OLD: a ninth employee was handed exactly 40 hours, invented', () => {
  const old = oldShape(emps(9));
  assert.strictEqual(old.E009.total, 40,
    'the pre-fix control no longer reproduces the invented default week');
});

test('NEW: a ninth employee gets "--" and adds nothing to any total', () => {
  const c = harness({ flag: true, stored: { sb_emps: emps(9), sb_ts: { E001: [8, 0, 0, 0, 0, 0] } } });
  assert.strictEqual(rowCells(c, 'Last9')[7], '--');
  assert.strictEqual(c.__el['ts-hrs'].textContent, 8);
});

test('OLD: deactivating E003 moved its 43-hour week and 3 OT onto E004', () => {
  const all = emps(8);
  const withE003 = oldShape(all);
  assert.strictEqual(withE003.E003.total, 43, 'fixture drifted: E003 is not the 43-hour row');
  assert.strictEqual(withE003.E003.ot, 3);
  assert.strictEqual(withE003.E004.total, 40);
  assert.strictEqual(withE003.E004.ot, 0);
  const withoutE003 = oldShape(all.filter((e) => e.id !== 'E003'));
  assert.strictEqual(withoutE003.E004.total, 43,
    'the pre-fix control no longer reproduces the reassignment');
  assert.strictEqual(withoutE003.E004.ot, 3,
    'and E004 no longer inherits E003 overtime, so the control is not testing it');
});

test('NEW: deactivating one employee changes no other employee row', () => {
  const all = emps(8);
  const ts = { E003: [8, 8, 7, 8, 8, 4], E004: [8, 8, 8, 8, 8, 0] };
  const before = harness({ flag: true, stored: { sb_emps: all, sb_ts: ts } });
  assert.strictEqual(rowCells(before, 'Last4')[7], '40');
  const after = harness({
    flag: true,
    stored: { sb_emps: all.filter((e) => e.id !== 'E003'), sb_ts: ts },
  });
  assert.strictEqual(rowCells(after, 'Last4')[7], '40',
    'E004 hours moved when a different employee was deactivated');
  assert.strictEqual(rowCells(after, 'Last4')[8], '0',
    'E004 inherited overtime from a deactivated employee');
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. THE FLAG IS NOT TRUSTED -- it is checked against the real file');

test('nothing writes sb_ts, and the flag says so', () => {
  const writers = tsWriters();
  const flagFalse = /var SB_TS_HAVE_A_WRITE_PATH\s*=\s*false\s*;/.test(html);
  if (writers === 0) {
    assert.strictEqual(flagFalse, true,
      'SB_TS_HAVE_A_WRITE_PATH is true while NOTHING writes sb_ts -- the panel '
      + 'would total an array that can only ever be empty.');
  } else {
    assert.strictEqual(flagFalse, false,
      'sb_ts has ' + writers + ' writer(s), so an entry path exists, but '
      + 'SB_TS_HAVE_A_WRITE_PATH is still false -- real recorded hours are '
      + 'being hidden behind a dash. Move the flag in the same change that '
      + 'added the writer.');
  }
});

test('the hardcoded hours array is gone from rTS(), not merely unused', () => {
  const body = fnBody('function rTS()');
  assert.ok(!/\[\s*8\s*,\s*8\s*,\s*8\s*,\s*8\s*,\s*8\s*,\s*0\s*\]/.test(body),
    'the default week is back in rTS()');
  assert.ok(/ld\(\s*'sb_ts'/.test(body), 'rTS() no longer reads hours from a store');
});

// ═══════════════════════════════════════════════════════════════════════════
section('5. the two tiles with nothing behind them are GONE, not dashed');

test('Billable Hours and Utilization Rate are removed from the markup', () => {
  // Removed rather than dashed because neither had anything behind it even in
  // principle: billable was Math.round(total*0.85) in a file with no
  // job-coding model, and utilization was billable/total, which under that
  // definition can only ever print 85%. Precedent in this same app: the
  // fabricated FUTA/SUTA figures were removed rather than faked.
  assert.strictEqual(html.indexOf('id="ts-bill"'), -1,
    'the Billable Hours tile is back');
  assert.strictEqual(html.indexOf('id="ts-util"'), -1,
    'the Utilization Rate tile is back');
  assert.strictEqual(html.indexOf('>Job-coded<'), -1,
    'a tile is labelled "Job-coded" again, in an app with no job-coding model');
});

test('and the 0.85 multiplier is gone from rTS()', () => {
  assert.ok(!/0\.85/.test(fnBody('function rTS()')),
    'the invented billable-hours multiplier is back in rTS()');
});

test('the CSV export still REFUSES the timesheet view', () => {
  // It refused before this fix because the hours were hardcoded; it refuses
  // now because there are none. The refusal must survive the change -- an
  // export of an empty week is a spreadsheet stating a zero-hour payroll.
  const body = fnBody('function csv(');
  assert.ok(!/type\s*===\s*'timesheet'/.test(body),
    'csv() now handles "timesheet" -- check what it exports before allowing it');
  assert.ok(/No CSV export is built/.test(body),
    'the loud fallback refusal is gone from csv()');
});

// ═══════════════════════════════════════════════════════════════════════════
(function run() {
  for (const item of queue) {
    if (item.section) { console.log('\n' + item.section); continue; }
    try { item.fn(); pass++; console.log('  ok   ' + item.name); }
    catch (e) { fail++; console.log('  FAIL ' + item.name + '\n         ' + e.message); }
  }
  console.log('\n' + (fail ? fail + ' FAILED, ' + pass + ' passed'
    : 'ALL ' + pass + ' ASSERTIONS PASS'));
  process.exit(fail ? 1 : 0);
})();
