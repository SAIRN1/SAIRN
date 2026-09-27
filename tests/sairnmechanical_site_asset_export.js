// tests/sairnmechanical_site_asset_export.js
//
// Run:  node tests/sairnmechanical_site_asset_export.js
//
// THE SITE-ASSET REGISTER CAN BE PRODUCED AS A FILE, AND THE FILE KEEPS THE
// THREE REFRIGERANT RULES APART.
//
// The 2026-08-21 worldwide trades research rates data portability and lock-in
// the DOMINANT real-world pain in this category -- above every trade-specific
// compliance gap -- and until 2026-09-26 SAIRNmechanical could produce exactly
// one register as a file. This was not it, on the register that carries a
// contractor's EPA and CARB position.
//
// ── WHAT THIS SUITE IS ACTUALLY FOR ──────────────────────────────────────
// Not "does a CSV come out". Four things that are each one keystroke from being
// wrong and none of which is visible in a diff:
//
// (1) THREE RULES, NEVER MERGED. api/_lib/mech-assets.js refuses to decide which
//     rule governs a unit, and a file with one "in scope" column would make that
//     decision on its behalf. Arms C1-C3 assert six separate columns, no merged
//     one, and that a unit disagreeing across two rules exports BOTH answers.
//
// (2) A CHARGE OF 0 IS A MEASUREMENT. `r.refrigerant_charge_lb || ''` is the
//     obvious accessor and it is wrong: 0 is falsy, and blank in this column
//     means NEVER WEIGHED. Arm B2 drives exactly 0 and arm B3 drives null, and
//     they must come out differently.
//
// (3) NEVER LOADED vs GENUINELY EMPTY. null makes the export refuse; [] writes a
//     header with nothing under it, which reads as an empty register to whoever
//     opens the file. Arms A1-A3.
//
// (4) THE MESSAGES ARE PER DATASET. Making credentials the only export left the
//     not-loaded toast saying "the credential register" and the success toast
//     claiming "including records the board supersedes". Both are FALSE of this
//     register -- evaluateRegistry does not reduce -- and arms D1-D3 hold both
//     datasets' messages so fixing one cannot break the other.
//
// ── THE BOARD COMES FROM THE REAL ENGINE, NOT FROM A HAND-WRITTEN FIXTURE ──
// tests/sairnmechanical_credential_export.js records what happens otherwise: its
// hand-built board asserted a status/flag pair no input can produce, a count the
// server disagreed with, and an off-by-one day figure -- every arm green against
// a fiction, one of them contradicting api/_lib/mech-credentials.test.js
// outright. So the assets here are raw asset rows and evaluateRegistry() builds
// the board, which means a fixture cannot drift from the engine.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(process.env.MECH_HTML
  || path.join(__dirname, '..', 'sairnmechanical.html'), 'utf8')
  .replace(/\r\n/g, '\n');
const mechAssets = require(path.join(__dirname, '..', 'api', '_lib', 'mech-assets.js'));

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairnmechanical.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// ── THE ASSETS, CHOSEN SO EACH ONE MAKES A DIFFERENT COLUMN MATTER ────────
// A1  60 lb R-22 in CA          -> 608 at/above (50 or more); AIM not applicable
//                                  (R-22 is not an HFC above GWP 53 once stated);
//                                  CARB needs > 50 AND GWP > 150 AND state CA.
// A2  20 lb R-410a, no state    -> THE DISAGREEMENT: below under 82.157 (under 50)
//                                  and at/above under 84.106 (over 15). CARB
//                                  cannot answer without a state ->
//                                  unknown_jurisdiction, which is NOT "below".
// A3  charge exactly 0          -> a real measurement that is falsy in JS.
// A4  charge null               -> never weighed. Must not look like A3.
// A5  exactly 50.0 lb in CA     -> IN under 82.157 (50 or more), OUT under CARB
//                                  (more than 50). The boundary asymmetry.
const ASSETS = [
  { asset_id: 'A1', customer_name: 'Northside Foods', site_name: 'Plant 1',
    site_state: 'CA', asset_type: 'chiller', make: 'Trane', model: 'RTAC',
    serial_no: 'SN-A1', installed_on: '2019-04-02',
    refrigerant_type: 'r22', refrigerant_charge_lb: 60,
    hfc_gwp_over_53: false, gwp_over_150: false },
  { asset_id: 'A2', customer_name: 'Bellweather Retail', site_name: 'Store 8',
    asset_type: 'rtu', make: 'Carrier', model: '48TC',
    serial_no: 'SN-A2', installed_on: '2023-07-15',
    refrigerant_type: 'r410a', refrigerant_charge_lb: 20,
    hfc_gwp_over_53: true },
  { asset_id: 'A3', customer_name: 'Zero Charge Co', asset_type: 'furnace',
    refrigerant_type: 'none', refrigerant_charge_lb: 0 },
  { asset_id: 'A4', customer_name: 'Never Weighed Co', asset_type: 'vrf',
    refrigerant_type: 'r410a' },
  { asset_id: 'A5', customer_name: 'Boundary Ltd', site_state: 'CA',
    asset_type: 'chiller', refrigerant_type: 'r410a',
    refrigerant_charge_lb: 50, hfc_gwp_over_53: true, gwp_over_150: true },
];
const BOARD = mechAssets.evaluateRegistry(ASSETS, '2026-09-26', {});

function harness(opts) {
  opts = opts || {};
  const files = [];
  const toasts = [];
  const src = [
    grab('function mechCsvCell(v){', '\n'),
    grab('var MECH_TYPE_LABELS = {', '\n  };'),
    grab('var MECH_SECTION_LABELS = {', '\n  };'),
    grab('function mechCsvField(v) {', '\n  }'),
    grab('function mechCredKey(r) {', '\n  }'),
    grab('var MECH_EXPORTS = {', '\n  };'),
    grab('function mechExportDataset(key) {', '\n  }')
  ].join('\n\n');
  const ctx = {
    JSON, Object, Array, String, Number, Math, Boolean, Date, RegExp,
    showToast: (m) => toasts.push(String(m)),
    Blob: function (parts) { this.text = parts.join(''); },
    document: { createElement: () => ({ click() { files.push({ name: this.download, body: this.href.text }); } }) },
    window: { URL: { createObjectURL: (b) => b, revokeObjectURL: () => {} } }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: 'sairnmechanical-exports-extract.js' });
  // Set AFTER the source runs, so the extract's own `var ... = null` cannot
  // clobber it -- the same seam the credential suite drives through.
  ctx._mechAssetLast = ('cache' in opts) ? opts.cache
    : { board: JSON.parse(JSON.stringify(BOARD)) };
  ctx._mechCredLast = null;
  return { ctx, files, toasts };
}

function csv(opts) {
  const h = harness(opts);
  h.ctx.mechExportDataset('site_assets');
  assert.strictEqual(h.files.length, 1, 'mechExportDataset wrote no file');
  const lines = h.files[0].body.split('\r\n');
  return { file: h.files[0], lines: lines, toasts: h.toasts };
}

/** Split one CSV line honouring the quoting mechCsvCell writes. */
function cells(line) {
  const out = [];
  let cur = '', q = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (q) {
      if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (c === '"') q = false;
      else cur += c;
    } else if (c === '"') q = true;
    else if (c === ',') { out.push(cur); cur = ''; }
    else cur += c;
  }
  out.push(cur);
  return out;
}

function headerLine(lines) {
  // The preamble rows come first; the header is the line carrying 'Asset ID'.
  const i = lines.findIndex(l => l.indexOf('Asset ID') === 0 || l.indexOf('"Asset ID"') === 0);
  assert.ok(i >= 0, 'no header row found:\n' + lines.slice(0, 14).join('\n'));
  return { idx: i, cols: cells(lines[i]) };
}
function rowFor(lines, id) {
  const { idx, cols } = headerLine(lines);
  for (let i = idx + 1; i < lines.length; i++) {
    const c = cells(lines[i]);
    if (c[0] === id) {
      const o = {};
      cols.forEach((name, j) => { o[name] = c[j]; });
      return o;
    }
  }
  throw new Error('no exported row for asset ' + id);
}

console.log('SAIRNmechanical -- the site-asset register exports, three rules kept apart');

// ── A. DECLARED, AND THE THREE LOAD STATES ───────────────────────────────
section('A. declared, and never-loaded is not empty');
test('A1. site_assets is declared with its resource and action', () => {
  const h = harness();
  const def = h.ctx.MECH_EXPORTS.site_assets;
  assert.ok(def, 'MECH_EXPORTS has no site_assets entry');
  assert.strictEqual(def.resource, 'mech_site_assets');
  assert.strictEqual(def.action, 'read');
  assert.ok(typeof def.rows === 'function' && Array.isArray(def.columns));
});
test('A2. NEVER LOADED refuses and writes no file', () => {
  const h = harness({ cache: null });
  h.ctx.mechExportDataset('site_assets');
  assert.strictEqual(h.files.length, 0,
    'a file was written from an unloaded register -- an empty file reads as an '
    + 'empty register to whoever opens it');
  assert.ok(h.toasts.some(t => /site-asset register/.test(t) && /not been loaded/.test(t)),
    'the refusal does not name the SITE-ASSET register: ' + JSON.stringify(h.toasts));
});
test('A3. GENUINELY EMPTY writes the header and says zero', () => {
  const r = csv({ cache: { board: { rows: [] } } });
  headerLine(r.lines);
  assert.ok(r.toasts.some(t => /^0 records exported/.test(t)),
    'an empty register did not report zero: ' + JSON.stringify(r.toasts));
});

// ── B. THE FALSY-ZERO TRAP ───────────────────────────────────────────────
section('B. a charge of 0 is a measurement; blank means never weighed');
test('B1. every fixture asset is exported -- none is silently dropped', () => {
  const r = csv();
  ASSETS.forEach(a => rowFor(r.lines, a.asset_id));
});
test('B2. a recorded charge of exactly 0 exports as "0", not blank', () => {
  const row = rowFor(csv().lines, 'A3');
  assert.strictEqual(row['Charge (lb)'], '0',
    'a charge of 0 exported as ' + JSON.stringify(row['Charge (lb)'])
    + ' -- `|| \'\'` is the obvious accessor and 0 is falsy, so a real '
    + 'measurement became "never weighed"');
});
test('B3. ...and a charge that was never recorded exports BLANK', () => {
  const row = rowFor(csv().lines, 'A4');
  assert.strictEqual(row['Charge (lb)'], '',
    'an unweighed asset exported ' + JSON.stringify(row['Charge (lb)']));
});
test('B4. the preamble says blank means never weighed, not zero', () => {
  const pre = csv().lines.slice(0, headerLine(csv().lines).idx).join('\n');
  assert.ok(/NEVER WEIGHED, NOT ZERO/i.test(pre),
    'the preamble does not distinguish blank from zero:\n' + pre);
});

// ── C. THREE RULES, SIX COLUMNS, NEVER MERGED ────────────────────────────
section('C. the three refrigerant rules stay apart');
test('C1. six columns -- a scope AND a reason for each rule', () => {
  const cols = headerLine(csv().lines).cols;
  ['Section 608 scope', 'Section 608 reason', 'AIM Act scope', 'AIM Act reason',
   'CARB scope', 'CARB reason'].forEach(want => {
    assert.ok(cols.some(c => c.indexOf(want) === 0),
      'no column starting ' + JSON.stringify(want) + ' in ' + JSON.stringify(cols));
  });
});
test('C2. NO merged "in scope" column exists', () => {
  const cols = headerLine(csv().lines).cols;
  const bad = cols.filter(c => /^in scope|^refrigerant scope$|^scope$/i.test(c));
  assert.deepStrictEqual(bad, [],
    'a merged scope column exists (' + JSON.stringify(bad) + ') -- that would be '
    + 'this app deciding which federal rule governs a customer\'s machine, which '
    + 'api/_lib/mech-assets.js exists to refuse');
});
test('C3. THE DISAGREEMENT TRAVELS: A2 is below under 608 and at/above under AIM', () => {
  const row = rowFor(csv().lines, 'A2');
  const s608 = row[Object.keys(row).find(k => k.indexOf('Section 608 scope') === 0)];
  const saim = row[Object.keys(row).find(k => k.indexOf('AIM Act scope') === 0)];
  assert.strictEqual(s608, 'below');
  assert.strictEqual(saim, 'at_or_above',
    'a 20 lb R-410A unit must read below under 82.157 and at/above under 84.106; '
    + 'got 608=' + s608 + ' AIM=' + saim);
});
test('C4. THE BOUNDARY: A5 at exactly 50.0 lb is IN under 608 and OUT under CARB', () => {
  const row = rowFor(csv().lines, 'A5');
  const s608 = row[Object.keys(row).find(k => k.indexOf('Section 608 scope') === 0)];
  const carb = row[Object.keys(row).find(k => k.indexOf('CARB scope') === 0)];
  assert.strictEqual(s608, 'at_or_above', '82.157 is 50 lb OR MORE');
  assert.strictEqual(carb, 'below', '17 CCR 95380 is MORE THAN 50 lb');
});
test('C5. unknown_jurisdiction travels rather than reading as "below"', () => {
  const row = rowFor(csv().lines, 'A2');
  const carb = row[Object.keys(row).find(k => k.indexOf('CARB scope') === 0)];
  assert.strictEqual(carb, 'unknown_jurisdiction',
    'an asset with no site state must not read as out of CARB scope; got ' + carb);
});
test('C6. each rule\'s REASON is non-empty -- the reason is the citation', () => {
  const row = rowFor(csv().lines, 'A1');
  ['Section 608 reason', 'AIM Act reason', 'CARB reason'].forEach(want => {
    const k = Object.keys(row).find(x => x.indexOf(want) === 0);
    assert.ok(String(row[k] || '').trim(),
      want + ' is empty -- the scope word alone does not tell an inspector why');
  });
});
test('C7. the preamble carries all three citations and the 50.0 asymmetry', () => {
  const pre = csv().lines.slice(0, headerLine(csv().lines).idx).join('\n');
  ['40 CFR 82.157', '40 CFR 84.106', '17 CCR 95380'].forEach(c =>
    assert.ok(pre.indexOf(c) !== -1, 'the preamble omits ' + c));
  assert.ok(/MUST NOT be summed/i.test(pre), 'the preamble does not forbid summing');
  assert.ok(/EXACTLY 50\.0/i.test(pre),
    'the preamble does not state the exactly-50.0 federal/state asymmetry');
});

// ── D. THE MESSAGES ARE PER DATASET ──────────────────────────────────────
section('D. adding a second export did not make the first one lie');
test('D1. site_assets does NOT claim supersession', () => {
  const r = csv();
  const t = r.toasts.join(' | ');
  assert.ok(!/supersede/i.test(t),
    'the site-asset toast claims the board supersedes records; evaluateRegistry '
    + 'does not reduce, so that is false here: ' + t);
});
test('D2. credentials STILL claims it, because there it is true', () => {
  const h = harness();
  const def = h.ctx.MECH_EXPORTS.credentials;
  assert.ok(/supersede/i.test(String(def.exportedNote || '')),
    'the credential export lost its supersession note, which IS true of that '
    + 'board and is the reason its export exists');
});
test('D3. each dataset names its OWN register in the not-loaded refusal', () => {
  const h = harness();
  assert.strictEqual(h.ctx.MECH_EXPORTS.site_assets.notLoaded, 'site-asset register');
  assert.strictEqual(h.ctx.MECH_EXPORTS.credentials.notLoaded, 'credential register');
});
test('D4. the filename names the dataset', () => {
  assert.ok(/site-assets/.test(csv().file.name),
    'filename is ' + csv().file.name);
});

// ── E. THE BUTTON EXISTS AND REACHES IT ──────────────────────────────────
section('E. a user can actually get to it');
test('E1. an Export CSV button calls mechExportDataset(\'site_assets\')', () => {
  assert.ok(html.indexOf("mechExportDataset('site_assets')") !== -1,
    'nothing in sairnmechanical.html calls the site_assets export -- a declared '
    + 'dataset with no button is the dormant-capability shape this platform keeps '
    + 'finding');
});
test('E2. the cache is cleared on every path that is not a real board', () => {
  // Three refusal paths in mechAssetRefresh: 401/403, !ok, provisioned===false.
  // Each must null the cache, or the export writes a file from a stale board
  // after the server has started refusing.
  const fn = grab('function mechAssetRefresh() {', '\n  }');
  assert.strictEqual((fn.match(/_mechAssetLast = null;/g) || []).length, 3,
    'expected 3 cache clears in mechAssetRefresh, found '
    + (fn.match(/_mechAssetLast = null;/g) || []).length
    + ' -- a refusal that leaves the cache set exports yesterday\'s register as '
    + 'today\'s');
  assert.strictEqual((fn.match(/_mechAssetLast = res\.body;/g) || []).length, 1,
    'the cache is set somewhere other than the one success path');
});

console.log('\n' + (fail ? 'FAIL' : 'ALL') + ' -- ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
