// tests/sairnbiz_incidents_kpi.js
//
// Run:  node tests/sairnbiz_incidents_kpi.js
//
// THE SAFETY-INCIDENTS TILE READ "0" UNDER THE SUBTITLE "YTD OSHA log".
// That tells a customer their year-to-date OSHA log is clean. The count was
// real and the array was really empty, so this is not Guardian Check 0b -- no
// number was fabricated. It is worse in one specific way: `st('sb_incidents',
// [])` appears exactly once, inside seed(), and nothing in sairnbiz.html
// writes it again. There is no add-incident path anywhere in the app, so the
// tile could only ever say 0. "No incidents" and "no way to record one"
// rendered identically, and the reassuring one is the one that showed.
//
// The fix does not build the feature -- that is a product decision and the
// open-work row stays open for it. It makes the app say which of the two it
// means: `--` and "Not recorded here yet" while no writer exists, the real
// count and "YTD OSHA log" the moment one does.
//
// THE POINT OF THIS FILE IS THE FOURTH SECTION. A boolean flag saying "there
// is no write path" is only true until someone adds one, and a flag nobody
// re-checks is how a REAL incident count would end up hidden behind a dash.
// So the flag is not trusted: the number of st('sb_incidents') writers is
// counted out of the file and must agree with it.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

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

// A whole `var NAME={...};` statement, lifted rather than retyped.
function declSrc(open) {
  const at = html.indexOf(open);
  assert.ok(at > 0, 'not found in sairnbiz.html: ' + open);
  const end = html.indexOf('};', at);
  assert.ok(end > at, 'unterminated declaration: ' + open);
  return html.slice(at, end + 2);
}

// Every st('sb_incidents', ...) in the file. This is the ground truth the
// flag is checked against -- not a copy of it.
//
// COMMENTS ARE STRIPPED FIRST, and that is not incidental: the note this fix
// added to rTrain() quotes `st('sb_incidents',` twice while explaining the
// defect, and counting those made the file look like it had three writers.
// A checker that reads prose as code is the same mistake the push gate made
// when a commit message quoting a flag disabled it.
const codeOnly = html.split('\n')
  .map((l) => l.replace(/^(\s*)\/\/.*$/, '$1'))
  .join('\n');
function incidentWriters() {
  return (codeOnly.match(/st\(\s*'sb_incidents'/g) || []).length;
}

// A realm with the real rTrain() and the real flag declaration. The other
// four tiles are given real data so a change that broke them would show here
// too rather than being masked by empty inputs.
function harness(opts) {
  opts = opts || {};
  const el = {};
  const get = (id) => (el[id] || (el[id] = { textContent: '', innerHTML: '' }));
  const flagSrc = /var SB_INCIDENTS_HAVE_A_WRITE_PATH\s*=\s*(true|false)\s*;/.exec(html);
  assert.ok(flagSrc, 'SB_INCIDENTS_HAVE_A_WRITE_PATH declaration not found');
  const ctx = {
    JSON, Object, Array, String, Number, Math, Date,
    ld: (k, d) => (Object.prototype.hasOwnProperty.call(opts.stored || {}, k)
      ? JSON.parse(JSON.stringify(opts.stored[k])) : d),
    st: () => true,
    $: get,
    H: (s) => String(s),
    fmt: (n) => '$' + Number(n || 0).toFixed(2),
    fdate: (d) => String(d || ''),
    sbNormalizeTrain: (t) => t,
    sbCertStatus: () => 'Expiring Soon',
    sbLocalToday: () => '2026-09-10',
    __el: el,
  };
  vm.createContext(ctx);
  // The counter, the two label maps and the log renderer are LIFTED from the
  // file alongside rTrain(), not stubbed. A stub would let the tile and the log
  // agree with the test while disagreeing with the app -- the drift
  // tests/sairnlaw_hydrate.js already learned once by hardcoding a resource
  // list the app had outgrown.
  vm.runInContext(
    (opts.flag === undefined ? flagSrc[0]
      : 'var SB_INCIDENTS_HAVE_A_WRITE_PATH=' + opts.flag + ';') + '\n'
    + declSrc('var SB_INCIDENT_CLASS={') + '\n'
    + declSrc('var SB_INCIDENT_TYPE={') + '\n'
    + fnBody('function sbIncidentsYTD(') + '\n'
    + fnBody('function rIncidents(') + '\n'
    + fnBody('function rTrain()'), ctx);
  ctx.rTrain();
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('1. if the write path is ever REMOVED, the dash comes back');

// These four were the whole of this file on 2026-09-09, when there was no way
// to record an incident. They are kept, with the flag forced false, because
// the fallback is what makes the tile honest if the feature is ever taken out
// again -- a deleted feature leaving a hardcoded 0 behind is exactly the state
// this started in.

test('with no write path the value is "--", not "0"', () => {
  const c = harness({ flag: false });
  assert.strictEqual(c.__el['tr-safe'].textContent, '--');
});

test('and the subtitle says why, instead of naming a log nobody can write', () => {
  const c = harness({ flag: false });
  assert.strictEqual(c.__el['tr-safe-note'].textContent, 'Not recorded here yet');
});

test('the static HTML still ships "--", so first paint claims nothing', () => {
  // Unchanged by the feature and deliberately so: before rTrain() has run,
  // the app does not yet know the count. A hardcoded 0 in the markup would
  // state a clean log for the length of that gap.
  const at = html.indexOf('id="tr-safe"');
  assert.ok(at > 0, 'tr-safe tile not found');
  const tile = html.slice(at, at + 140);
  assert.ok(/id="tr-safe">--</.test(tile), 'the markup ships a hardcoded count again');
  assert.ok(html.indexOf('id="tr-safe-note"') > 0, 'the subtitle has no id to update');
  assert.ok(html.indexOf('>YTD OSHA log<') === -1,
    'the subtitle is hardcoded in the markup again, so it cannot switch');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. with the write path, the tile is a real measurement');

test('a real count is displayed', () => {
  const c = harness({ stored: { sb_incidents: [
    { id: 'I-1', year: '2026' }, { id: 'I-2', year: '2026' }] } });
  assert.strictEqual(c.__el['tr-safe'].textContent, 2);
  assert.strictEqual(c.__el['tr-safe-note'].textContent, 'YTD OSHA log');
});

test('a genuine zero from a real log still reads 0, not "--"', () => {
  // The distinction the whole change is about: an empty log that CAN be
  // written to is a real measurement and must say so.
  const c = harness({ stored: { sb_incidents: [] } });
  assert.strictEqual(c.__el['tr-safe'].textContent, 0);
  assert.strictEqual(c.__el['tr-safe-note'].textContent, 'YTD OSHA log');
});

test('NEGATIVE CONTROL: the old body showed 0 for both cases alike', () => {
  // Same harness, the pre-fix assignment. If this ever stops showing 0 with
  // no writer, the tests above prove nothing.
  const ctx = { JSON, Object, Array, String, Number,
    ld: (k, d) => d, $: (id) => (ctx.__el[id] || (ctx.__el[id] = { textContent: '' })),
    __el: {} };
  vm.createContext(ctx);
  vm.runInContext("$('tr-safe').textContent=ld('sb_incidents',[]).length;", ctx);
  assert.strictEqual(ctx.__el['tr-safe'].textContent, 0,
    'the old shape must produce the reassuring zero this replaces');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. the other four tiles on this row are unchanged');

test('certs, expiring, hours and spend still render from sb_train', () => {
  const c = harness({ stored: { sb_train: [
    { id: 'T-1', hrs: 3, cost: 100 }, { id: 'T-2', hrs: 2, cost: 50 }] } });
  assert.strictEqual(c.__el['tr-cert'].textContent, 2);
  assert.strictEqual(c.__el['tr-exp'].textContent, 2);   // the stub reports both expiring
  assert.strictEqual(c.__el['tr-hrs'].textContent, 5);
  assert.strictEqual(c.__el['tr-bud'].textContent, '$150.00');
});

// ═══════════════════════════════════════════════════════════════════════════
section('4. THE FLAG IS NOT TRUSTED -- it is checked against the real file');

test('sb_incidents now has a real writer, and the flag agrees', () => {
  // UPDATED 2026-09-10. This assertion was the reverse until the feature was
  // built: exactly ONE writer (sbSeedRows' empty-array initialiser) and the
  // flag false. Its own failure message said that more than one writer means
  // somebody added a way to record an incident and the flag must move in the
  // same change. That is what happened, so the assertion moved with it -- the
  // DIRECTION is the point, not the number: the flag and the code must never
  // disagree, whichever way round they are.
  const writers = incidentWriters();
  const flag = /var SB_INCIDENTS_HAVE_A_WRITE_PATH\s*=\s*true\s*;/.test(html);
  assert.ok(writers >= 2,
    'sb_incidents has ' + writers + ' writer(s). The seed initialiser plus at '
    + 'least one real entry path is expected; if the feature was removed, set '
    + 'SB_INCIDENTS_HAVE_A_WRITE_PATH=false in the same change so the tile goes '
    + 'back to a dash instead of claiming a clean OSHA log.');
  assert.strictEqual(flag, true,
    'SB_INCIDENTS_HAVE_A_WRITE_PATH is false while saveIncident() exists -- a '
    + 'real injury count would be hidden behind a dash.');
});

test('the seed initialiser is still there, and still writes an EMPTY array', () => {
  // sbSeedRows(), not seed(). seed() is a four-line wrapper that pauses sync
  // and delegates. Named exactly, because "it is in seed()" was my own first
  // guess here and it was wrong.
  const seedBody = fnBodyAt(html.indexOf('function sbSeedRows()'));
  assert.ok(/st\('sb_incidents',\s*\[\s*\]\s*\)/.test(seedBody),
    'sbSeedRows() no longer initialises sb_incidents to an empty array');
  const wrapper = fnBodyAt(html.indexOf('function seed()'));
  assert.ok(/sbSeedRows\(\)/.test(wrapper), 'seed() no longer delegates to sbSeedRows()');
  // The demo seed must stay EMPTY. Every other collection here ships sample
  // rows; a sample INJURY would be a fabricated safety record sitting on a
  // real customer's OSHA log, which is the one place in this app where demo
  // data would be actively harmful rather than merely noise.
  assert.ok(!/st\('sb_incidents',\s*\[\s*\{/.test(seedBody),
    'sbSeedRows() now seeds sample injuries -- a demo injury on a real OSHA log');
});

test('sb_incidents IS in the backup registry now that it has a writer', () => {
  // The reverse of what this asserted on 2026-09-09, for the reason that
  // assertion gave: syncing a collection nothing writes backs up an empty
  // array forever and reads as coverage. It has a writer now, and an injury
  // log is a five-year record (29 CFR 1904.33) that cannot be reconstructed
  // from anything else in the app if the browser is lost.
  assert.ok(registry.resources.indexOf('sb_incidents') !== -1,
    'sb_incidents is not registered, so every injury logged stays on one machine');
  assert.strictEqual(registry.resources.length, 10);
});

test('and the client actually syncs it -- registered is not the same as sent', () => {
  // Registering a name gates it; SB_SYNCED is what makes st() push it.
  // "REGISTERING A NAME IS NECESSARY AND NOT SUFFICIENT" is written into
  // api/_resources/sairnlaw.js after exactly that gap shipped, so both halves
  // are asserted here rather than one.
  const m = /var SB_SYNCED\s*=\s*\[([^\]]*)\]/.exec(html);
  assert.ok(m, 'SB_SYNCED not found');
  const names = (m[1].match(/'(sb_\w+)'/g) || []).map((x) => x.replace(/'/g, ''));
  assert.ok(names.indexOf('sb_incidents') !== -1,
    'sb_incidents is registered server-side but the client never pushes it');
  names.forEach((n) => assert.ok(registry.resources.indexOf(n) !== -1,
    n + ' is in SB_SYNCED but not registered -- its writes will be refused'));
});

test('the server-side handler knows the resource, not just the allowlist', () => {
  // A name that passes the allowlist with no handler branch falls through to
  // "Unsupported action/resource combination" -- worse than not registering
  // it at all, per the note in api/_resources/sairnlaw.js.
  const sd = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
  assert.ok(/sb_incidents:\s*'incident_id'/.test(sd),
    'sb_incidents has no id-column entry in SB_RESOURCES');
});

test('and the table exists in the schema file, with the same id column', () => {
  const sql = fs.readFileSync(path.join(ROOT, 'sql', 'sairnbiz_data_schema.sql'), 'utf8');
  assert.ok(/create table if not exists public\.sb_incidents/.test(sql),
    'no sb_incidents table -- every write answers 503 NOT_PROVISIONED');
  assert.ok(/incident_id text not null/.test(sql), 'the id column name does not match');
  assert.ok(/grant select, insert, update on public\.sb_incidents to service_role;/.test(sql),
    'the grant line is missing or grants more than the platform standard three');
  assert.ok(!/delete[^\n]*public\.sb_incidents/i.test(sql),
    'a delete grant was added -- the platform removed those on 2026-08-25');
});

// ═══════════════════════════════════════════════════════════════════════════
section('5. the log itself: what saveIncident() will and will not store');

function incidentHarness(fields, stored) {
  const el = {};
  const get = (id) => (el[id] || (el[id] = { textContent: '', innerHTML: '', value: '', checked: false }));
  Object.keys(fields || {}).forEach((k) => {
    const e = get(k);
    if (typeof fields[k] === 'boolean') e.checked = fields[k]; else e.value = fields[k];
  });
  const toasts = [];
  const written = {};
  const ctx = {
    JSON, Object, Array, String, Number, Math, Date, parseInt, isNaN,
    ld: (k, d) => (stored && Object.prototype.hasOwnProperty.call(stored, k)
      ? JSON.parse(JSON.stringify(stored[k])) : d),
    st: (k, v) => { written[k] = v; return true; },
    $: get,
    toast: (m) => toasts.push(m),
    sbLocalToday: () => '2026-09-10',
    closeIncModal: () => {},
    rTrain: () => {},
    __el: el, __toasts: toasts, __written: written,
  };
  vm.createContext(ctx);
  vm.runInContext(fnBody('function sbNextCaseNo(') + '\n' + fnBody('function saveIncident()'), ctx);
  ctx.saveIncident();
  return ctx;
}

const FULL = { incdate: '2026-03-04', incemp: 'Marcus Thompson', incjob: 'Shop Foreman',
  incwhere: 'Fabrication bay 2', incdesc: 'Laceration to left forearm from slab edge',
  incclass: 'other', inctype: 'injury', incaway: '', increst: '', incpriv: false };

test('a complete entry is stored with every Form 300 column', () => {
  const c = incidentHarness(FULL, {});
  const rows = c.__written.sb_incidents;
  assert.ok(Array.isArray(rows) && rows.length === 1, 'nothing was stored');
  const r = rows[0];
  assert.strictEqual(r.date, '2026-03-04');
  assert.strictEqual(r.emp, 'Marcus Thompson');
  assert.strictEqual(r.job, 'Shop Foreman');
  assert.strictEqual(r.where, 'Fabrication bay 2');
  assert.strictEqual(r.classification, 'other');
  assert.strictEqual(r.type, 'injury');
  assert.strictEqual(r.privacy, false);
  assert.ok(r.id, 'no id -- sbEnsureIds warns and the record never reaches the server');
});

test('the case number is assigned, per YEAR, and does not collide', () => {
  const c = incidentHarness(FULL, { sb_incidents: [
    { id: 'IN-a', year: '2026', case_no: 1 }, { id: 'IN-b', year: '2026', case_no: 2 },
    { id: 'IN-c', year: '2025', case_no: 7 }] });
  const r = c.__written.sb_incidents.slice(-1)[0];
  assert.strictEqual(r.year, '2026');
  assert.strictEqual(r.case_no, 3, '2025 case 7 must not push the 2026 numbering');
});

test('a new year starts its numbering again at 1', () => {
  const c = incidentHarness(Object.assign({}, FULL, { incdate: '2027-01-02' }),
    { sb_incidents: [{ id: 'IN-a', year: '2026', case_no: 9 }] });
  const r = c.__written.sb_incidents.slice(-1)[0];
  assert.strictEqual(r.year, '2027');
  assert.strictEqual(r.case_no, 1);
});

test('the three columns the form cannot be transcribed without are REFUSED empty', () => {
  ['incdate', 'incemp', 'incdesc'].forEach((field) => {
    const patch = {};
    patch[field] = '';
    const c = incidentHarness(Object.assign({}, FULL, patch), {});
    assert.strictEqual(c.__written.sb_incidents, undefined,
      'a record was stored with no ' + field);
    assert.strictEqual(c.__toasts.length, 1, 'the refusal said nothing');
  });
});

test('a day count that contradicts its classification is refused, not stored', () => {
  // Storing it would make the panel look broken later for no visible cause --
  // the same standard saveCertRenewal() applies to an expiry before its own
  // completion date.
  const away = incidentHarness(Object.assign({}, FULL, { incclass: 'away', incaway: '0' }), {});
  assert.strictEqual(away.__written.sb_incidents, undefined);
  const rest = incidentHarness(Object.assign({}, FULL, { incclass: 'restricted', increst: '' }), {});
  assert.strictEqual(rest.__written.sb_incidents, undefined);
  const ok = incidentHarness(Object.assign({}, FULL, { incclass: 'away', incaway: '3' }), {});
  assert.strictEqual(ok.__written.sb_incidents[0].days_away, 3);
});

test('a privacy case still STORES the name -- the modal says so, and it is true', () => {
  const c = incidentHarness(Object.assign({}, FULL, { incpriv: true }), {});
  const r = c.__written.sb_incidents[0];
  assert.strictEqual(r.privacy, true);
  assert.strictEqual(r.emp, 'Marcus Thompson',
    'the name was dropped -- the modal tells the user it is stored');
});

test('and the toast does not put a privacy-case name on screen', () => {
  const c = incidentHarness(Object.assign({}, FULL, { incpriv: true }), {});
  assert.strictEqual(c.__toasts.length, 1);
  assert.ok(c.__toasts[0].indexOf('Marcus Thompson') === -1,
    'the confirmation toast printed a privacy-case name');
});

test('a refused localStorage write does NOT report a save', () => {
  // runPayroll() announced ACH transfers it never sent. st() returns false on
  // a refused write and reports that itself; this must not add a second,
  // contradicting message on top of it.
  const el = {};
  const get = (id) => (el[id] || (el[id] = { textContent: '', value: '', checked: false }));
  Object.keys(FULL).forEach((k) => {
    const e = get(k);
    if (typeof FULL[k] === 'boolean') e.checked = FULL[k]; else e.value = FULL[k];
  });
  const toasts = [];
  const ctx = { JSON, Object, Array, String, Number, Math, Date, parseInt, isNaN,
    ld: (k, d) => d, st: () => false, $: get, toast: (m) => toasts.push(m),
    sbLocalToday: () => '2026-09-10', closeIncModal: () => {}, rTrain: () => {}, __el: el };
  vm.createContext(ctx);
  vm.runInContext(fnBody('function sbNextCaseNo(') + '\n' + fnBody('function saveIncident()'), ctx);
  ctx.saveIncident();
  assert.strictEqual(toasts.length, 0, 'it announced a save that did not happen');
});

// ═══════════════════════════════════════════════════════════════════════════
section('6. the tile counts YTD, because that is what its label says');

test('only the current year is counted', () => {
  const c = harness({ stored: { sb_incidents: [
    { id: 'a', year: '2026' }, { id: 'b', year: '2026' }, { id: 'c', year: '2025' }] } });
  assert.strictEqual(c.__el['tr-safe'].textContent, 2);
  assert.strictEqual(c.__el['tr-safe-note'].textContent, 'YTD OSHA log');
});

test('a real, empty YTD log reads 0 -- not a dash', () => {
  const c = harness({ stored: { sb_incidents: [{ id: 'c', year: '2025' }] } });
  assert.strictEqual(c.__el['tr-safe'].textContent, 0);
});

test('the log renders newest first, and says so when it is empty', () => {
  const c = harness({ stored: { sb_incidents: [
    { id: 'a', year: '2026', case_no: 1, date: '2026-01-05', emp: 'Early', desc: 'x' },
    { id: 'b', year: '2026', case_no: 2, date: '2026-08-09', emp: 'Later', desc: 'y' }] } });
  const body = c.__el['inctbody'].innerHTML;
  assert.ok(body.indexOf('Later') < body.indexOf('Early'), 'not newest first');
  const empty = harness({ stored: { sb_incidents: [] } });
  assert.ok(/No injuries or illnesses recorded/.test(empty.__el['inctbody'].innerHTML),
    'an empty log renders an empty table body, which reads as a failed load');
});

test('a privacy case is NOT named in the rendered log', () => {
  const c = harness({ stored: { sb_incidents: [
    { id: 'a', year: '2026', case_no: 1, date: '2026-01-05', emp: 'Marcus Thompson',
      desc: 'x', privacy: true }] } });
  const body = c.__el['inctbody'].innerHTML;
  assert.ok(body.indexOf('Marcus Thompson') === -1, 'a privacy case printed the name');
  assert.ok(/Privacy Case/.test(body), 'it did not say why the name is absent');
});

// ═══════════════════════════════════════════════════════════════════════════
(async () => {
  for (const item of queue) {
    if (item.section) { console.log('\n' + item.section); continue; }
    try { await item.fn(); console.log('  ok   - ' + item.name); pass++; }
    catch (e) { console.log('  FAIL - ' + item.name + '\n         ' + e.message); fail++; }
  }
  console.log('\n' + pass + '/' + (pass + fail) + ' passed');
  process.exit(fail ? 1 : 0);
})();
