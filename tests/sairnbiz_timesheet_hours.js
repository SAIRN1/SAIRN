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
// THE FIX CAME IN TWO HALVES AND THIS FILE COVERS BOTH. First (200aaba8) the
// invented hours were removed and the panel said so. Then, on Michael's
// decision, the write path that makes recording real hours possible.
//
// SECTION 3 IS STILL THE POINT OF THE FILE. Asserting the new code is right
// proves nothing about whether it fixed anything, so it drives the PRE-FIX
// body -- reproduced literally, the one case where a copy is justified because
// it is gone from the file -- and requires it to still produce the invented
// 40-hour ninth employee and still move E003's 43 hours and 3 OT onto E004.
//
// SECTION 6 DRIVES THE REAL HANDLER, not a description of it. Client-side
// validation is a convenience; api/sd-data.js is the boundary, and the two
// refuse independently. The arm that matters there is that a BAD VALUE IS
// REFUSED RATHER THAN COERCED -- `Number('')` is 0 and `Number('eight')` is
// NaN, so a coercing validator turns a typo into a zero-hour day, and a
// zero-hour day is a real, payable statement.
//
// SECTION 7 DOES NOT TRUST THE FLAG. SB_TS_HAVE_A_WRITE_PATH is a boolean
// somebody has to remember to move, so it is checked against the real number of
// st('sb_ts') writers in the file, failing in BOTH directions. Same convention
// as tests/sairnbiz_incidents_kpi.js.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');
const crypto = require('crypto');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnbiz.html'), 'utf8').replace(/\r\n/g, '\n');
const registry = require(path.join(ROOT, 'api', '_resources', 'sairnbiz.js'));

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

// Comments are stripped before anything is COUNTED. The fix's own notes quote
// `st('sb_ts')` while explaining the flag, and counting prose as code would
// make the file look like it had writers it does not have -- the same mistake
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

// A fixed Monday, so nothing here depends on the day the suite happens to run.
const WEEK = '2026-09-07';
function tsRow(emp, hours, week) {
  return { id: emp + '|' + (week || WEEK), emp: emp, week: week || WEEK, hours: hours };
}

// The real rTS(), its week helpers and the real write path, in a realm with a
// DOM stub. `sbTsWeek` is pinned to WEEK after the declarations run so the
// suite does not drift with the calendar.
function harness(opts) {
  opts = opts || {};
  const el = {};
  const get = (id) => (el[id] || (el[id] = { textContent: '', innerHTML: '', value: '',
                                             style: {}, classList: { add() {}, remove() {} } }));
  const flagSrc = /var SB_TS_HAVE_A_WRITE_PATH\s*=\s*(true|false)\s*;/.exec(html);
  assert.ok(flagSrc, 'SB_TS_HAVE_A_WRITE_PATH declaration not found');
  const stored = JSON.parse(JSON.stringify(opts.stored || {}));
  const toasts = [];
  const ctx = {
    JSON, Object, Array, String, Number, Math, Date, isFinite,
    ld: (k, d) => (Object.prototype.hasOwnProperty.call(stored, k)
      ? JSON.parse(JSON.stringify(stored[k])) : d),
    st: (k, v) => { if (opts.stFails) return false; stored[k] = JSON.parse(JSON.stringify(v)); return true; },
    $: get,
    H: (s) => String(s),
    fmt: (n) => '$' + Number(n || 0).toFixed(2),
    toast: (m) => toasts.push(String(m)),
    rDash: () => {},
    __el: el, __stored: stored, __toasts: toasts,
  };
  vm.createContext(ctx);
  vm.runInContext(
    (opts.flag === undefined ? flagSrc[0]
      : 'var SB_TS_HAVE_A_WRITE_PATH=' + opts.flag + ';') + '\n'
    + fnBody('function sbWeekStart(') + '\n'
    + 'var sbTsWeek=' + JSON.stringify(opts.week || WEEK) + ';\n'
    + fnBody('function tsShiftWeek(') + '\n'
    + fnBody('function sbTsRows(') + '\n'
    + fnBody('function sbTsFor(') + '\n'
    + fnBody('function rTS()') + '\n'
    + 'var tsEditing=null;\n'
    + fnBody('function openTsModal(') + '\n'
    + fnBody('function closeTsModal(') + '\n'
    + fnBody('function tsReadDays(') + '\n'
    + fnBody('function saveTimesheet('), ctx);
  if (opts.noRender !== true) ctx.rTS();
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
section('1. a week with nothing recorded states that, instead of a number');

test('all three surviving KPIs read "--", not 0 and not $0.00', () => {
  const c = harness({ stored: { sb_emps: emps(8) } });
  assert.strictEqual(c.__el['ts-hrs'].textContent, '--');
  assert.strictEqual(c.__el['ts-ot'].textContent, '--');
  assert.strictEqual(c.__el['ts-cost'].textContent, '--');
});

test('the note names the WEEK and says how to record, not "cannot record"', () => {
  // The two empty states are different sentences and collapsing them would
  // rebuild the defect one layer up: "nobody has entered hours yet" and "this
  // app cannot record hours" look identical as a row of dashes, and only one of
  // them is something a user can act on.
  const c = harness({ stored: { sb_emps: emps(8) } });
  const note = c.__el['ts-note'].textContent;
  assert.ok(note.indexOf(WEEK) !== -1, 'the note does not name the week: ' + note);
  assert.ok(/Use Enter on a row/.test(note), 'the note does not say how: ' + note);
  assert.notStrictEqual(c.__el['ts-note'].style.display, 'none');
});

test('...and with NO write path it says that instead', () => {
  // Kept with the flag forced false because this is what the panel must say if
  // the entry path is ever removed -- a deleted feature leaving a row of dashes
  // with no explanation is the state this started in.
  const c = harness({ flag: false, stored: { sb_emps: emps(8) } });
  assert.ok(/not recorded in this app yet/.test(c.__el['ts-note'].textContent),
    c.__el['ts-note'].textContent);
});

test('every employee row is dashes across, and no row invents a total', () => {
  const c = harness({ stored: { sb_emps: emps(8) } });
  for (const n of [1, 4, 8]) {
    const cells = rowCells(c, 'Last' + n);
    // name, six days, total, OT, pay estimate, the Enter button
    assert.strictEqual(cells.length, 11, 'row shape changed for Last' + n);
    assert.deepStrictEqual(cells.slice(1, 7), ['--', '--', '--', '--', '--', '--'],
      'Last' + n + ' has day hours with nothing recorded');
    assert.strictEqual(cells[7], '--', 'Last' + n + ' has a total with nothing recorded');
    assert.strictEqual(cells[8], '--', 'Last' + n + ' has overtime with nothing recorded');
    assert.strictEqual(cells[9], '--', 'Last' + n + ' has a pay estimate with nothing recorded');
    assert.strictEqual(cells[10], 'Enter', 'Last' + n + ' has no way to record hours');
  }
});

test('the static markup ships "--" too, so first paint claims nothing', () => {
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
    stored: {
      sb_emps: emps(8),
      sb_ts: [tsRow('E001', [8, 8, 8, 8, 8, 0]), tsRow('E002', [8, 8, 8, 8, 8, 4])],
    },
  });
  assert.strictEqual(c.__el['ts-hrs'].textContent, 84);
  assert.strictEqual(c.__el['ts-ot'].textContent, 4);
  // 40*11 + (40*12 + 4*12*1.5) = 440 + 552 = 992
  assert.strictEqual(c.__el['ts-cost'].textContent, '$992.00');
});

test('the exclusion is DISCLOSED, with both counts', () => {
  const c = harness({
    stored: { sb_emps: emps(8), sb_ts: [tsRow('E001', [8, 8, 8, 8, 8, 0])] },
  });
  const note = c.__el['ts-note'].textContent;
  assert.ok(/1 of 8/.test(note) && /other 7/.test(note),
    'the note does not state how many employees are excluded: ' + note);
});

test('with every employee recorded, there is no exclusion note to show', () => {
  // A clean week must not carry a warning -- a disclosure that is always on
  // stops being read, which is the failure mode the note exists to avoid.
  const c = harness({
    stored: { sb_emps: emps(2), sb_ts: [tsRow('E001', [8, 0, 0, 0, 0, 0]), tsRow('E002', [8, 0, 0, 0, 0, 0])] },
  });
  assert.strictEqual(c.__el['ts-note'].textContent, '');
  assert.strictEqual(c.__el['ts-note'].style.display, 'none');
});

test('hours attach by EMPLOYEE ID, so a record cannot land on the wrong person', () => {
  const c = harness({
    stored: { sb_emps: emps(8), sb_ts: [tsRow('E005', [8, 8, 8, 8, 8, 0])] },
  });
  assert.strictEqual(rowCells(c, 'Last5')[7], '40');
  assert.strictEqual(rowCells(c, 'Last1')[7], '--');
  assert.strictEqual(rowCells(c, 'Last8')[7], '--');
});

test('a record for ANOTHER WEEK is not shown or counted in this one', () => {
  // Without this, adding weeks to the store would silently sum every week a
  // person ever worked into a figure labelled "This week".
  const c = harness({
    stored: { sb_emps: emps(3),
              sb_ts: [tsRow('E001', [8, 8, 8, 8, 8, 0]),
                      tsRow('E002', [8, 8, 8, 8, 8, 0], '2026-08-31')] },
  });
  assert.strictEqual(c.__el['ts-hrs'].textContent, 40);
  assert.strictEqual(rowCells(c, 'Last2')[7], '--');
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
  const c = harness({ stored: { sb_emps: emps(9), sb_ts: [tsRow('E001', [8, 0, 0, 0, 0, 0])] } });
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
  const ts = [tsRow('E003', [8, 8, 7, 8, 8, 4]), tsRow('E004', [8, 8, 8, 8, 8, 0])];
  const before = harness({ stored: { sb_emps: all, sb_ts: ts } });
  assert.strictEqual(rowCells(before, 'Last4')[7], '40');
  const after = harness({
    stored: { sb_emps: all.filter((e) => e.id !== 'E003'), sb_ts: ts },
  });
  assert.strictEqual(rowCells(after, 'Last4')[7], '40',
    'E004 hours moved when a different employee was deactivated');
  assert.strictEqual(rowCells(after, 'Last4')[8], '0',
    'E004 inherited overtime from a deactivated employee');
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. the week is a real week, and Monday starts it');

test('sbWeekStart returns the Monday, including for a Sunday', () => {
  const c = harness({ stored: { sb_emps: [] } });
  // 2026-09-07 is a Monday; 09-13 is the Sunday that ENDS that week and must
  // not be read as the start of the next one.
  assert.strictEqual(c.sbWeekStart(new Date(2026, 8, 7)), '2026-09-07');
  assert.strictEqual(c.sbWeekStart(new Date(2026, 8, 10)), '2026-09-07');
  assert.strictEqual(c.sbWeekStart(new Date(2026, 8, 13)), '2026-09-07');
  assert.strictEqual(c.sbWeekStart(new Date(2026, 8, 14)), '2026-09-14');
});

test('the panel subhead shows the WEEK START, not today', () => {
  // It read "Week of <today>" until 2026-09-15, which is not the start of a
  // week for six days out of seven.
  const c = harness({ stored: { sb_emps: emps(1) } });
  assert.strictEqual(c.__el.tsweek.textContent, WEEK);
});

test('a future week is REFUSED, and the current week is not', () => {
  const c = harness({ stored: { sb_emps: [] }, week: c0week() });
  c.tsShiftWeek(1);
  assert.ok(/has not happened yet/.test((c.__toasts[0] || '')),
    'stepping past the current week was allowed: ' + JSON.stringify(c.__toasts));
  c.tsShiftWeek(-1);
  assert.ok(c.sbTsWeek < c0week(), 'stepping back did not move the week');
});
function c0week() {
  const d = new Date();
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
  return x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0')
    + '-' + String(x.getDate()).padStart(2, '0');
}

// ═══════════════════════════════════════════════════════════════════════════
section('5. the write path REFUSES rather than coerces');

function typeInto(c, values) {
  values.forEach((v, i) => { c.__el['ts-d' + i].value = v; });
}

test('a valid week saves, keyed by employee id and week', () => {
  const c = harness({ stored: { sb_emps: emps(2) } });
  c.openTsModal('E001');
  typeInto(c, ['8', '8', '8', '8', '8', '']);
  c.saveTimesheet();
  const rows = c.__stored.sb_ts;
  assert.strictEqual(rows.length, 1);
  assert.deepStrictEqual(rows[0].hours, [8, 8, 8, 8, 8, 0]);
  assert.strictEqual(rows[0].emp, 'E001');
  assert.strictEqual(rows[0].week, WEEK);
  assert.strictEqual(rows[0].id, 'E001|' + WEEK, 'the id is not derived from emp and week');
});

test('re-saving the same week UPDATES rather than adding a second row', () => {
  // Two disagreeing timesheets for one employee-week is a payroll dispute with
  // no tiebreaker, which is the whole reason the id is deterministic.
  const c = harness({ stored: { sb_emps: emps(2), sb_ts: [tsRow('E001', [8, 8, 8, 8, 8, 0])] } });
  c.openTsModal('E001');
  typeInto(c, ['7', '8', '8', '8', '8', '']);
  c.saveTimesheet();
  assert.strictEqual(c.__stored.sb_ts.length, 1, 'a duplicate employee-week row was created');
  assert.deepStrictEqual(c.__stored.sb_ts[0].hours, [7, 8, 8, 8, 8, 0]);
});

test('a non-numeric day is REFUSED and NOTHING is saved', () => {
  const c = harness({ stored: { sb_emps: emps(2) } });
  c.openTsModal('E001');
  typeInto(c, ['8', 'eight', '8', '8', '8', '']);
  c.saveTimesheet();
  assert.strictEqual(c.__stored.sb_ts, undefined, 'a bad entry was written anyway');
  assert.notStrictEqual(c.__el['ts-modal-err'].style.display, 'none');
  assert.ok(/Tue is "eight"/.test(c.__el['ts-modal-err'].textContent),
    c.__el['ts-modal-err'].textContent);
  assert.ok(/NOTHING WAS SAVED/.test(c.__el['ts-modal-err'].textContent));
});

test('CONTROL: the coercing version would have stored a zero for that day', () => {
  // The arm above is only meaningful because the obvious implementation is
  // wrong in a way that looks fine: Number('eight') is NaN and Number('') is 0.
  assert.ok(Number.isNaN(Number('eight')));
  assert.strictEqual(Number(''), 0);
  assert.strictEqual(Number('eight') || 0, 0,
    'the `|| 0` idiom no longer turns a typo into a zero-hour day');
});

test('a day above 24 is REFUSED', () => {
  const c = harness({ stored: { sb_emps: emps(2) } });
  c.openTsModal('E001');
  typeInto(c, ['25', '', '', '', '', '']);
  c.saveTimesheet();
  assert.strictEqual(c.__stored.sb_ts, undefined);
  assert.ok(/Mon is "25"/.test(c.__el['ts-modal-err'].textContent));
});

test('a negative day is REFUSED', () => {
  const c = harness({ stored: { sb_emps: emps(2) } });
  c.openTsModal('E001');
  typeInto(c, ['-1', '', '', '', '', '']);
  c.saveTimesheet();
  assert.strictEqual(c.__stored.sb_ts, undefined);
});

test('a blank day is zero, and a whole blank week is a real recorded zero', () => {
  // The one input treated as zero, and only because the modal says so on
  // screen. A recorded week of no work is a legitimate statement; an INVENTED
  // one is what this whole file exists about.
  const c = harness({ stored: { sb_emps: emps(2) } });
  c.openTsModal('E001');
  typeInto(c, ['', '', '', '', '', '']);
  c.saveTimesheet();
  assert.deepStrictEqual(c.__stored.sb_ts[0].hours, [0, 0, 0, 0, 0, 0]);
});

test('an inactive employee cannot have hours recorded', () => {
  const list = emps(2);
  list[0].status = 'Inactive';
  const c = harness({ stored: { sb_emps: list } });
  c.openTsModal('E001');
  assert.ok(/only be recorded for an active employee/.test(c.__toasts.join(' ')),
    JSON.stringify(c.__toasts));
});

test('a FAILED write says so and does not report success', () => {
  // st() returning false is the silent-failure class this platform has a
  // standing rule about: a write that fails to nobody is indistinguishable
  // from one that worked.
  const c = harness({ stored: { sb_emps: emps(2) }, stFails: true });
  c.openTsModal('E001');
  typeInto(c, ['8', '', '', '', '', '']);
  c.saveTimesheet();
  assert.ok(/were NOT saved/.test(c.__toasts.join(' ')), JSON.stringify(c.__toasts));
  assert.ok(!/Hours recorded/.test(c.__toasts.join(' ')),
    'a failed write reported success');
});

test('the modal prefills BLANK for an unrecorded day, never 0', () => {
  // Prefilled zeros would make an untouched form look like a recorded week of
  // no work -- the same defect as the invented hours, entered by the UI.
  const c = harness({ stored: { sb_emps: emps(2) } });
  c.openTsModal('E001');
  for (let i = 0; i < 6; i++) assert.strictEqual(c.__el['ts-d' + i].value, '');
});

// ═══════════════════════════════════════════════════════════════════════════
section('6. THE SERVER REFUSES INDEPENDENTLY -- driven, not read');

// The client is a convenience. api/sd-data.js is the boundary, and a request
// can be made without the client at all.
const HANDLER = path.join(ROOT, 'api/sd-data.js');
process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['sairnbiz', 'ts', 'fixture', String(process.pid)].join('-');
const auth = require(path.join(ROOT, 'api/_lib/auth.js'));
const LICENSE_KEY = 'k';
const LIC_HASH = crypto.createHash('sha256').update(LICENSE_KEY).digest('hex');

async function callHandler(payload) {
  delete require.cache[require.resolve(HANDLER)];
  const handler = require(HANDLER);
  const out = { code: null, body: null, wrote: false, sent: null };
  const res = { status(c) { out.code = c; return res; }, json(b) { out.body = b; return res; },
                setHeader() {} };
  const names = { url: ['SUPABASE', 'URL'].join('_'),
                  key: ['SUPABASE', 'SERVICE', 'ROLE', 'KEY'].join('_') };
  const envURL = process.env[names.url], envKey = process.env[names.key];
  const realFetch = global.fetch;
  process.env[names.url] = 'https://stub.invalid';
  process.env[names.key] = ['stub', 'fixture', 'value'].join('-');
  let first = true;
  global.fetch = async (url, init) => {
    if (first) {
      first = false;
      return { ok: true, status: 200, json: async () => [{ status: 'active', app_id: null }] };
    }
    out.wrote = true;
    if (init && init.body) { try { out.sent = JSON.parse(init.body); } catch (e) { /* not json */ } }
    return { ok: true, status: 200, json: async () => [] };
  };
  try {
    await handler({ method: 'POST',
                    headers: { authorization: 'Bearer ' + LICENSE_KEY,
                               'x-sd-auth': auth.signSessionToken({
                                 app: 'sairnbiz', role: 'owner',
                                 license_hash: LIC_HASH, employee_id: 'E-OWNER' }) },
                    body: { action: 'write', resource: 'sb_ts', payload: payload } }, res);
  } finally {
    global.fetch = realFetch;
    if (envURL === undefined) delete process.env[names.url]; else process.env[names.url] = envURL;
    if (envKey === undefined) delete process.env[names.key]; else process.env[names.key] = envKey;
  }
  return out;
}

const GOOD = { emp: 'E001', week: WEEK, hours: [8, 8, 8, 8, 8, 0] };
const BAD = [
  ['a string where a number belongs', Object.assign({}, GOOD, { hours: [8, '8', 8, 8, 8, 0] })],
  ['a NaN', Object.assign({}, GOOD, { hours: [8, NaN, 8, 8, 8, 0] })],
  ['null in a day cell', Object.assign({}, GOOD, { hours: [8, null, 8, 8, 8, 0] })],
  ['more than 24 in a day', Object.assign({}, GOOD, { hours: [25, 0, 0, 0, 0, 0] })],
  ['a negative day', Object.assign({}, GOOD, { hours: [-1, 0, 0, 0, 0, 0] })],
  ['five days instead of six', Object.assign({}, GOOD, { hours: [8, 8, 8, 8, 8] })],
  ['no hours array at all', { emp: 'E001', week: WEEK }],
  ['a week that is not a Monday', Object.assign({}, GOOD, { week: '2026-09-08' })],
  ['a week that is not a date', Object.assign({}, GOOD, { week: 'last week' })],
  ['a week that does not exist', Object.assign({}, GOOD, { week: '2026-02-31' })],
  ['no employee', { week: WEEK, hours: [0, 0, 0, 0, 0, 0] }],
];

test('a valid timesheet reaches storage', async () => {
  const r = await callHandler(GOOD);
  assert.strictEqual(r.code, 200, JSON.stringify(r.body));
  assert.ok(r.wrote, 'the valid case never reached storage, so the refusals below prove nothing');
});

test('the server DERIVES the id and ignores the one sent', async () => {
  // A client free to choose the id could write two rows for one employee-week,
  // which is the one thing the deterministic id exists to make impossible.
  const r = await callHandler(Object.assign({}, GOOD, { id: 'ANYTHING-I-LIKE' }));
  assert.strictEqual(r.code, 200);
  assert.strictEqual(r.sent && r.sent.ts_id, 'E001|' + WEEK,
    'the server stored the caller\'s id: ' + JSON.stringify(r.sent && r.sent.ts_id));
});

for (const [label, payload] of BAD) {
  test('REFUSED, and nothing reaches storage: ' + label, async () => {
    const r = await callHandler(payload);
    assert.strictEqual(r.code, 400, 'accepted ' + label + ': ' + JSON.stringify(r.body));
    assert.strictEqual((r.body.error || {}).code, 'INVALID_TIMESHEET', JSON.stringify(r.body));
    assert.ok(!r.wrote, label + ' reached storage before being refused');
  });
}

// ═══════════════════════════════════════════════════════════════════════════
section('7. THE FLAG IS NOT TRUSTED -- it is checked against the real file');

test('sb_ts has a real writer now, and the flag agrees', () => {
  const writers = tsWriters();
  const flagTrue = /var SB_TS_HAVE_A_WRITE_PATH\s*=\s*true\s*;/.test(html);
  if (writers === 0) {
    assert.strictEqual(flagTrue, false,
      'SB_TS_HAVE_A_WRITE_PATH is true while NOTHING writes sb_ts -- the panel '
      + 'would total an array that can only ever be empty.');
  } else {
    assert.strictEqual(flagTrue, true,
      'sb_ts has ' + writers + ' writer(s), so an entry path exists, but '
      + 'SB_TS_HAVE_A_WRITE_PATH is still false -- real recorded hours are '
      + 'being hidden behind a dash.');
  }
  assert.ok(writers >= 1, 'saveTimesheet() no longer writes sb_ts');
});

test('the hardcoded hours array is gone from rTS(), not merely unused', () => {
  const body = fnBody('function rTS()');
  assert.ok(!/\[\s*8\s*,\s*8\s*,\s*8\s*,\s*8\s*,\s*8\s*,\s*0\s*\]/.test(body),
    'the default week is back in rTS()');
  assert.ok(/sbTsFor\(/.test(body), 'rTS() no longer reads hours from the store');
});

// ═══════════════════════════════════════════════════════════════════════════
section('8. the two tiles with nothing behind them are still GONE');

test('Billable Hours and Utilization Rate are absent from the markup', () => {
  assert.strictEqual(html.indexOf('id="ts-bill"'), -1, 'the Billable Hours tile is back');
  assert.strictEqual(html.indexOf('id="ts-util"'), -1, 'the Utilization Rate tile is back');
  assert.strictEqual(html.indexOf('>Job-coded<'), -1,
    'a tile is labelled "Job-coded" again, in an app with no job-coding model');
});

test('and the 0.85 multiplier is gone from rTS()', () => {
  assert.ok(!/0\.85/.test(fnBody('function rTS()')),
    'the invented billable-hours multiplier is back in rTS()');
});

// ═══════════════════════════════════════════════════════════════════════════
section('9. recorded hours reach a server -- registered, synced, and migrated');

test('sb_ts is in the resource registry', () => {
  // Registering a name gates it; without this the write is refused by the
  // allowlist before any credential matters.
  assert.ok(registry.resources.indexOf('sb_ts') !== -1,
    'sb_ts is not registered, so every recorded hour stays on one machine');
});

test('...and the client actually sends it -- registered is not the same as sent', () => {
  const m = /var SB_SYNCED\s*=\s*\[([^\]]*)\]/.exec(codeOnly);
  assert.ok(m, 'SB_SYNCED not found in sairnbiz.html');
  assert.ok(m[1].indexOf("'sb_ts'") !== -1,
    'sb_ts is registered but not in SB_SYNCED, so st() never pushes it');
});

test('...and the handler knows its id column', () => {
  const api = fs.readFileSync(path.join(ROOT, 'api/sd-data.js'), 'utf8');
  assert.ok(/sb_ts:\s*'ts_id'/.test(api),
    'sb_ts is not in SB_RESOURCES, so the write answers 400 at the allowlist');
});

test('...and a migration exists that creates the table', () => {
  const sql = fs.readFileSync(path.join(ROOT, 'sql/sairnbiz_timesheet_schema.sql'), 'utf8');
  assert.ok(/create table if not exists public\.sb_ts/.test(sql));
  assert.ok(/unique \(license_hash, ts_id\)/.test(sql),
    'nothing stops two rows for one employee-week at the database level');
  // NO DELETE GRANT, matching every non-sc_* schema since 2026-08-25.
  assert.ok(/grant select, insert, update on public\.sb_ts to service_role/.test(sql));
  assert.ok(!/grant[^;]*delete[^;]*sb_ts/i.test(sql),
    'a delete grant was added for recorded hours');
});

// ═══════════════════════════════════════════════════════════════════════════
section('10. the CSV export is implemented, and excludes rather than zeroes');

test('csv("timesheet") is handled and no longer falls through to the refusal', () => {
  const body = fnBody('function csv(');
  assert.ok(/type\s*===\s*'timesheet'/.test(body),
    'the Export CSV button on the Timesheets panel still toasts a refusal');
  assert.ok(/No CSV export is built/.test(body),
    'the loud fallback refusal was removed along with the timesheet case');
});

test('an unrecorded employee is NAMED in a note, not exported as zero', () => {
  const body = fnBody('function csv(');
  assert.ok(/EXCLUDED from this file rather than exported as zero/.test(body),
    'the export no longer discloses who it left out');
});

// ═══════════════════════════════════════════════════════════════════════════
(async function run() {
  for (const item of queue) {
    if (item.section) { console.log('\n' + item.section); continue; }
    try { await item.fn(); pass++; console.log('  ok   ' + item.name); }
    catch (e) { fail++; console.log('  FAIL ' + item.name + '\n         ' + e.message); }
  }
  console.log('\n' + (fail ? fail + ' FAILED, ' + pass + ' passed'
    : 'ALL ' + pass + ' ASSERTIONS PASS'));
  process.exit(fail ? 1 : 0);
})();
