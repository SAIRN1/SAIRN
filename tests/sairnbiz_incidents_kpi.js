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
    __el: el,
  };
  vm.createContext(ctx);
  vm.runInContext(
    (opts.flag === undefined ? flagSrc[0]
      : 'var SB_INCIDENTS_HAVE_A_WRITE_PATH=' + opts.flag + ';') + '\n'
    + fnBody('function rTrain()'), ctx);
  ctx.rTrain();
  return ctx;
}

// ═══════════════════════════════════════════════════════════════════════════
section('1. today, with no writer, the tile does not claim a clean OSHA log');

test('the value is "--", not "0"', () => {
  const c = harness({});
  assert.strictEqual(c.__el['tr-safe'].textContent, '--');
});

test('and the subtitle says why, instead of naming a log that does not exist', () => {
  const c = harness({});
  assert.strictEqual(c.__el['tr-safe-note'].textContent, 'Not recorded here yet');
});

test('the static HTML also ships "--", so it is honest before rTrain() runs', () => {
  // A tile that reads 0 until the first render is the same false statement,
  // just briefer. The default in the markup has to agree with the code.
  const at = html.indexOf('id="tr-safe"');
  assert.ok(at > 0, 'tr-safe tile not found');
  const tile = html.slice(at, at + 140);
  assert.ok(/id="tr-safe">--</.test(tile), 'the markup still ships a hardcoded 0');
  assert.ok(html.indexOf('id="tr-safe-note"') > 0, 'the subtitle has no id to update');
  assert.ok(html.indexOf('>YTD OSHA log<') === -1,
    'the hardcoded "YTD OSHA log" subtitle is still in the markup');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. the moment a write path exists, the real count is shown');

test('with the flag true, a real count is displayed', () => {
  const c = harness({ flag: true, stored: { sb_incidents: [{ id: 'I-1' }, { id: 'I-2' }] } });
  assert.strictEqual(c.__el['tr-safe'].textContent, 2);
  assert.strictEqual(c.__el['tr-safe-note'].textContent, 'YTD OSHA log');
});

test('a genuine zero from a real log still reads 0, not "--"', () => {
  // This is the distinction the whole change is about: an empty log that CAN
  // be written to is a real measurement and must say so.
  const c = harness({ flag: true, stored: { sb_incidents: [] } });
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

test('exactly one writer of sb_incidents today, and the flag agrees', () => {
  const writers = incidentWriters();
  const flag = /var SB_INCIDENTS_HAVE_A_WRITE_PATH\s*=\s*true\s*;/.test(html);
  // seed()'s `st('sb_incidents',[])` is the one write, and it is not an entry
  // path -- it initialises the key. More than one writer means somebody added
  // a way to record an incident.
  assert.strictEqual(writers, 1,
    'sb_incidents now has ' + writers + ' writers. If an add-incident path was '
    + 'built, set SB_INCIDENTS_HAVE_A_WRITE_PATH=true in the same change, or '
    + 'the real count stays hidden behind a dash.');
  assert.strictEqual(flag, false,
    'SB_INCIDENTS_HAVE_A_WRITE_PATH is true while seed() is still the only '
    + 'writer -- the tile would claim a clean OSHA log again.');
});

test('the one writer is the empty-array initialiser in the seed path', () => {
  // sbSeedRows(), not seed(). seed() is a four-line wrapper that pauses sync
  // and delegates; the rows are in sbSeedRows(). Named exactly, because
  // "it is in seed()" was my own first guess here and it was wrong.
  const seedBody = fnBodyAt(html.indexOf('function sbSeedRows()'));
  assert.ok(/st\('sb_incidents',\s*\[\s*\]\s*\)/.test(seedBody),
    'the one sb_incidents write is not the empty-array initialiser in sbSeedRows()');
  const wrapper = fnBodyAt(html.indexOf('function seed()'));
  assert.ok(/sbSeedRows\(\)/.test(wrapper), 'seed() no longer delegates to sbSeedRows()');
});

test('sb_incidents stays out of the backup registry while it has no writer', () => {
  // Syncing a collection nothing writes backs up an empty array forever and
  // reads as coverage. api/_resources/sairnbiz.js says so in its own comment;
  // this pins it so the two cannot disagree.
  assert.ok(registry.resources.indexOf('sb_incidents') === -1,
    'sb_incidents was registered while nothing writes it');
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
