// tests/sairndental_rollup_panel.js
// REQUIREMENT: a cross-location roll-up figure the server could not measure is
//   never rendered as a number, and the unattributed bucket is never rendered
//   as an office
//
// Run:  node tests/sairndental_rollup_panel.js
//
// ── WHY THIS SUITE EXISTS ──────────────────────────────────────────────────
// api/_lib/dnt-rollup.js shipped 2026-09-15 with four written rules, an
// owner-gated endpoint, 39 test arms, Tier A, and two independent reviews. It
// had no reader. `dnt_rollup` appeared ZERO times in every `.html` file in the
// repo -- the only one of SAIRNdental's 25 registered resources no client
// named -- while docs/SAIRN-OPEN-WORK-INDEX.md recorded competitive gap B2 as
// BUILT. docs/2026-09-17-sairndental-competitive-gap-rederived.md is that
// finding; the panel is the missing half and this is its guard.
//
// ── THE ARMS THAT MATTER ARE 2 AND 3, AND THEY ARE ABOUT THE SCREEN ────────
// A careful module stays careful only if the renderer keeps its distinctions.
// dnt-rollup.js returns `null` for a metric it could not read SPECIFICALLY so
// that it cannot be mistaken for a measurement -- rule 3 in its header: "A
// roll-up that silently omits an unprovisioned table prints 'Production:
// $12,400' when the true answer is 'we could not read charges'." A renderer
// that turns that null into `0`, `$0.00` or an em dash undoes the whole module
// at the last inch, and NOTHING SERVER-SIDE CAN CATCH THAT.
//
// Same for UNASSIGNED. The module hoists it out of `locations` deliberately,
// its own comment saying "so no client can render it as an office". That is an
// instruction to a client, and a server-side suite cannot check whether the
// client followed it.
//
// ── THE FIXTURE IS THE REAL SERVER OUTPUT, NOT A HAND-WRITTEN SHAPE ────────
// Every board below comes from calling the real `rollup()`. A hand-written
// fixture would let this suite pass against a shape the server cannot produce
// -- the exact drift hank corrected in tests/sairnmechanical_credential_export.js
// on 2026-09-17.
//
// DNT_HTML points this at a mutated copy in a temp directory, so a negative
// control can prove the arms bite without patching the tracked file. Same
// convention MECH_HTML, SB_HTML, SV_HTML and ALF_HTML already carry.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const { rollup } = require(path.join(__dirname, '..', 'api', '_lib', 'dnt-rollup.js'));

const html = fs.readFileSync(process.env.DNT_HTML
  || path.join(__dirname, '..', 'sairndental.html'), 'utf8')
  .replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in sairndental.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

// The REAL escaper and the REAL cell renderers, lifted from the shipped file.
const ctx = { console: console };
vm.createContext(ctx);
vm.runInContext(grab('function H(s){', '\n'), ctx);
vm.runInContext(grab('function rollupCell(m, kind){', '\n}\n'), ctx);
vm.runInContext(grab('function rollupRow(label, sub, mets, cls){', '\n}\n'), ctx);
vm.runInContext(grab('function rollupHasUnattributed(u){', '\n}\n'), ctx);
const cell = (m, kind) => ctx.rollupCell(m, kind);
const row = (l, s, m, c) => ctx.rollupRow(l, s, m, c);

const REGISTRY = [{ id: 'LOC-A', name: 'North Office' }, { id: 'LOC-B', name: 'South Office' }];
const METRICS = [
  { key: 'patients', resource: 'dnt_patients', kind: 'count', label: 'Patients' },
  { key: 'appointments', resource: 'dnt_appointments', kind: 'count', label: 'Appointments' },
  { key: 'production', resource: 'dnt_charges', kind: 'sum', field: 'amount', label: 'Production' }
];
const board = (sets) => rollup({ registry: REGISTRY, sets: sets, metrics: METRICS });

// ---------------------------------------------------------------------------
section('1. WIRING -- the resource is named, and the panel is reachable');

test('the app NAMES dnt_rollup -- the whole defect was that it did not', () => {
  assert.ok(html.indexOf('dnt_rollup') !== -1,
    'sairndental.html does not name dnt_rollup; the engine is unreachable again');
});

test('panel, sidebar button and nav dispatch all exist', () => {
  assert.ok(html.indexOf('id="panel-rollup"') !== -1, 'no panel-rollup');
  assert.ok(html.indexOf('id="sb-rollup"') !== -1, 'no sb-rollup sidebar button');
  assert.ok(/nav\('rollup'\)/.test(html), "nothing calls nav('rollup')");
  assert.ok(/if\(id==='rollup'\)rRollup\(\);/.test(html),
    "nav() does not dispatch to rRollup -- the panel would open blank");
});

// THE CENSUS THAT CANNOT SEE THE ORIGINAL DEFECT, asserted anyway because it
// catches the DIFFERENT defect of a half-wired panel.
test('panels, nav targets and sidebar ids are three identical sets', () => {
  const ids = (re) => new Set(Array.from(html.matchAll(re), (m) => m[1]));
  const panels = ids(/id="panel-([a-z0-9_-]+)"/g);
  const navs = ids(/nav\('([a-z0-9_-]+)'\)/g);
  const sbs = ids(/id="sb-([a-z0-9_-]+)"/g);
  const diff = (a, b) => [...a].filter((x) => !b.has(x));
  assert.deepStrictEqual(diff(panels, navs), [], 'panel with no nav target');
  assert.deepStrictEqual(diff(navs, panels), [], 'nav target with no panel');
  assert.deepStrictEqual(diff(sbs, panels), [], 'sidebar id with no panel');
  assert.ok(panels.has('rollup'));
});

test('it is owner-gated on screen, and says the server is the real gate', () => {
  assert.ok(html.indexOf('id="rollup-not-owner"') !== -1);
  assert.ok(/rollup[\s\S]{0,4000}the server is the real gate/i.test(html)
    || /DNT_MANAGEMENT_ROLES[\s\S]{0,200}regardless/i.test(html),
    'the panel does not record that the server, not this div, is the boundary');
});

// ---------------------------------------------------------------------------
section('2. THE ONE THAT MATTERS: an unmeasurable figure is never a number');

test('an unreadable RESOURCE renders COULD NOT READ, never 0 and never a dash', () => {
  const b = board({
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-A' }] },
    dnt_appointments: { rows: [] },
    dnt_charges: { unreadable: 'NOT_PROVISIONED' }      // the module's own shape
  });
  const loc = b.locations.find((l) => l.location_id === 'LOC-A');
  const m = loc.metrics.production;
  assert.strictEqual(m.value, null, 'fixture drifted: the server did not return null');
  const out = cell(m, 'money');
  assert.ok(/COULD NOT READ/.test(out), 'an unreadable amount did not say so: ' + out);
  assert.ok(!/\$0\b|\$0\.00/.test(out), 'an unreadable amount rendered as $0: ' + out);
  assert.ok(!/>\s*0\s*</.test(out), 'an unreadable amount rendered as 0: ' + out);
  assert.ok(!/&mdash;|—/.test(out), 'an unreadable amount rendered as a dash: ' + out);
});

test('and the REASON travels with it', () => {
  const b = board({
    dnt_patients: { rows: [] }, dnt_appointments: { rows: [] },
    dnt_charges: { unreadable: 'UPSTREAM_500' }
  });
  const out = cell(b.totals.production, 'money');
  assert.ok(/UPSTREAM_500/.test(out), 'the cell hides why it could not read: ' + out);
});

test('a REAL zero still renders as zero -- the distinction cuts both ways', () => {
  const b = board({
    dnt_patients: { rows: [] }, dnt_appointments: { rows: [] },
    dnt_charges: { rows: [{ id: 'C1', amount: 0, location_id: 'LOC-A' }] }
  });
  const out = cell(b.locations.find((l) => l.location_id === 'LOC-A').metrics.production, 'money');
  assert.ok(/\$0\.00/.test(out), 'a measured zero must still read as zero: ' + out);
  assert.ok(!/COULD NOT READ/.test(out), 'a measured zero was reported as unreadable: ' + out);
});

test('an unreadable FIELD is counted beside the total, not folded into it', () => {
  const b = board({
    dnt_patients: { rows: [] }, dnt_appointments: { rows: [] },
    dnt_charges: { rows: [
      { id: 'C1', amount: 100, location_id: 'LOC-A' },
      { id: 'C2', amount: '1,200', location_id: 'LOC-A' },   // parseFloat would say 1
      { id: 'C3', amount: '12abc', location_id: 'LOC-A' }
    ] }
  });
  const m = b.locations.find((l) => l.location_id === 'LOC-A').metrics.production;
  assert.strictEqual(m.unread, 2, 'fixture drifted: the server did not count 2 unread');
  const out = cell(m, 'money');
  assert.ok(/\$100\.00/.test(out), 'the readable part is missing: ' + out);
  assert.ok(/2 unreadable/.test(out), 'the unreadable rows are not surfaced: ' + out);
});

test('every figure carries its row count -- rule 4', () => {
  const b = board({
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-A' }, { id: 'P2', location_id: 'LOC-A' }] },
    dnt_appointments: { rows: [] }, dnt_charges: { rows: [] }
  });
  const out = cell(b.locations.find((l) => l.location_id === 'LOC-A').metrics.patients);
  assert.ok(/2 rows/.test(out), 'no row count on the figure: ' + out);
});

// ---------------------------------------------------------------------------
section('3. UNASSIGNED is never an office, and an unregistered id is labelled');

test('the module keeps UNASSIGNED out of locations -- the precondition', () => {
  const b = board({
    dnt_patients: { rows: [{ id: 'P1' }] },                 // no location_id
    dnt_appointments: { rows: [] }, dnt_charges: { rows: [] }
  });
  assert.ok(!b.locations.some((l) => l.location_id === '__unassigned__'),
    'the server leaked the unattributed bucket into locations');
  assert.ok(b.unassigned, 'the server did not report an unattributed bucket');
});

// DRIVEN, NOT GREPPED. The first version of the arm below was the ONLY one
// covering this rule, and it asserted the FILE CONTAINED the words "Not
// attributed to any office". A sabotage that suppressed the row entirely --
// the predicate forced to false -- left it GREEN, because an existence
// assertion over a whole file holds "the phrase is somewhere" and never "this
// row is rendered". The predicate was extracted into rollupHasUnattributed()
// so these two can drive it against real server output, in both directions.
test('the unattributed bucket IS shown whenever it holds rows', () => {
  const b = board({
    dnt_patients: { rows: [{ id: 'P1' }] },                 // no location_id
    dnt_appointments: { rows: [] }, dnt_charges: { rows: [] }
  });
  assert.strictEqual(ctx.rollupHasUnattributed(b.unassigned), true,
    'a practice with unattributed rows would not see the row at all');
});

test('...and is NOT shown when it is genuinely empty', () => {
  const b = board({
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-A' }] },
    dnt_appointments: { rows: [] }, dnt_charges: { rows: [] }
  });
  assert.strictEqual(ctx.rollupHasUnattributed(b.unassigned), false,
    'an empty bucket would raise a warning about nothing, which is how people '
    + 'learn to ignore the warning that matters');
});

test('the panel labels it as NOT an office rather than naming it like one', () => {
  const src = grab('async function rRollup(){', '\n}\n');
  assert.ok(/Not attributed to any office/.test(src),
    'the unattributed row is not labelled as unattributed');
  assert.ok(/NOT part of any office above/.test(src),
    'nothing tells the reader the unattributed row is excluded from the offices');
  // It must be rendered from `b.unassigned`, never merged into the office loop.
  assert.ok(/b\.unassigned/.test(src), 'the panel does not read b.unassigned');
  assert.ok(!/locations\.concat\(|locations\.push\(/.test(src),
    'the panel appends to the office list -- the bucket can be read as an office');
});

test('an office id not in the registry is shown AND named as unregistered', () => {
  const b = board({
    dnt_patients: { rows: [{ id: 'P1', location_id: 'LOC-GONE' }] },
    dnt_appointments: { rows: [] }, dnt_charges: { rows: [] }
  });
  const l = b.locations.find((x) => x.location_id === 'LOC-GONE');
  assert.ok(l, 'fixture drifted: the server dropped the unregistered office');
  assert.strictEqual(l.registered, false);
  const out = row('LOC-GONE', '<span class="badge br">not in the office registry</span> LOC-GONE', l.metrics);
  assert.ok(/not in the office registry/.test(out));
});

test('an office NAME is escaped -- it is practice-entered text', () => {
  const out = cell({ value: 1, rows: 1, unread: 0 });
  assert.ok(!/<script/.test(out));
  assert.strictEqual(ctx.H('<img src=x onerror=1>'),
    '&lt;img src=x onerror=1&gt;');
});

// ---------------------------------------------------------------------------
section('4. A REFUSAL IS NOT AN EMPTY PRACTICE');

test('the failure path shows nothing rather than a report', () => {
  const src = grab('async function rRollup(){', '\n}\n');
  assert.ok(/if\(!b\)\{/.test(src), 'there is no failure branch at all');
  assert.ok(/Not shown/.test(src),
    'a failed read does not leave the table saying it is not shown');
  assert.ok(/declined the roll-up/.test(src),
    'a refusal is not distinguished from a failure');
  assert.ok(!/No offices[\s\S]{0,80}\bif\(!b\)/.test(src),
    'the empty-practice sentence is reachable from the failure path');
});

test('the disclosure card is shown whenever the report is incomplete', () => {
  const src = grab('async function rRollup(){', '\n}\n');
  assert.ok(/d\.complete===false/.test(src), 'nothing reads disclosure.complete');
  assert.ok(/unread_fields/.test(src), 'nothing surfaces unread_fields');
  assert.ok(/unregistered_location_ids/.test(src), 'nothing surfaces unregistered ids');
  assert.ok(/registry_size===0/.test(src),
    'a practice with no office registry is not called out');
});

test('nothing is recomputed in the browser -- the panel renders, it does not derive', () => {
  const src = grab('async function rRollup(){', '\n}\n')
    + grab('function rollupCell(m, kind){', '\n}\n');
  // A reduce/+= over metrics would be the panel producing a second answer to
  // the same question, which is the defect dnt-rollup.js's own design refuses.
  assert.ok(!/\.reduce\(/.test(src), 'the panel reduces over server figures');
  assert.ok(!/totals\s*\+=|sum\s*\+=/.test(src), 'the panel accumulates its own total');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' ROLL-UP PANEL ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
