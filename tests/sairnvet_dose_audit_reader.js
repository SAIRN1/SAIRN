// tests/sairnvet_dose_audit_reader.js
//
// Run:  node tests/sairnvet_dose_audit_reader.js
//
// THE DOSING AUDIT TRAIL READER (item 39). Driven verbatim out of
// sairnvet.html rather than reimplemented, the same way
// tests/sairnvet_audit_and_controlled.js does it.
//
// WHAT WAS WRONG FOR THE LIFE OF THE APP: logDoseAudit() wrote sv_audit_log
// from fourteen call sites and NOTHING IN THE PRODUCT READ IT. Scoped
// 2026-09-14 and stated precisely then, because the stronger claim would have
// been false -- the rows WERE retrievable by a direct authenticated API call.
// They were not retrievable through the product, by the person who would be
// asked for them, in the situation where they would be asked. On a
// DEA-relevant trail that is the only situation that counts.
//
// ── WHAT THESE ARMS ARE ACTUALLY DEFENDING ─────────────────────────────────
// Not "does the table render". The three ways a compliance reader lies:
//
//   1. IT SHOWS THE LOCAL COPY AND DOES NOT SAY SO. The local store is capped
//      at SV_AUDIT_CAP; the server copy is not. A screen that presents a
//      possibly-truncated subset as the record is asserting completeness it
//      does not have. Section B.
//   2. A FAILED READ RENDERS AS AN EMPTY TRAIL. svData() answers null on any
//      refusal or network error, and [] is a legitimate answer for a practice
//      that has dosed nothing. Those must never look the same. Section C.
//   3. IT DROPS THE ENTRY THAT MATTERS. logDoseAudit()'s call sites have
//      different shapes; a reader showing only the fields it knows about would
//      silently lose the REASON a dose was refused, which is the entry an
//      inspector is most likely to be asking about. Section D.
//
// Section E is the one that would have caught the original defect: the panel
// has to be REACHABLE and its renderer has to be INVOKED. A render function
// nothing calls leaves a panel permanently empty while the gap looks closed --
// this app's own svNav() comment records that exact failure from sairnbiz.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'sairnvet.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + (detail === undefined ? '' : '\n        ' + String(detail).slice(0, 300)));
}
function eq(name, actual, expected) {
  ok(name, JSON.stringify(actual) === JSON.stringify(expected),
     'expected ' + JSON.stringify(expected) + '\n        actual   ' + JSON.stringify(actual));
}

function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
// THROWS rather than returning '' when an anchor stops matching. A missing
// function would otherwise make every arm below fail with a ReferenceError,
// which reads as a defect in the app rather than as this file's anchor having
// rotted -- the exact confusion recorded in the sibling suite.
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('anchor no longer matches: ' + decl);
  return balanced(i);
}

// ── the DOM double ─────────────────────────────────────────────────────────
// Minimal on purpose: these arms are about WHAT IS SAID, so the double records
// innerHTML/textContent and nothing else pretends to be a browser.
function makeDom(values) {
  const els = {};
  const get = (id) => {
    if (!els[id]) els[id] = { id, innerHTML: '', textContent: '', value: (values && values[id]) || '' };
    return els[id];
  };
  return { els, document: { getElementById: (id) => get(id) } };
}

const dom = makeDom({});
const sandbox = {
  document: dom.document,
  localStorage: { getItem: () => null },
  SV_AUDIT_KEY: 'sv_audit_log',
  SV_AUDIT_CAP: 500,
  svData: null,
  JSON, Object, String, Array, console
};
const vm = require('node:vm');
const ctx = vm.createContext(sandbox);
vm.runInContext(
  'var _svAuditRows = []; var _svAuditSource = "";\n' +
  fn('function svDoseAuditLocal(') + '\n' +
  fn('function svRenderDoseAudit(') + '\n' +
  fn('function svClearDoseAuditFilters(') + '\n' +
  fn('function svRenderDoseAuditTable(') + '\n', ctx);

// The extraction is ASSERTED, so an arm written as "must say X" cannot pass
// because nothing was defined.
['svDoseAuditLocal', 'svRenderDoseAudit', 'svClearDoseAuditFilters',
 'svRenderDoseAuditTable'].forEach((n) => {
  ok('A. ' + n + ' was lifted out of the real file', typeof ctx[n] === 'function');
});

const ENTRY = (o) => Object.assign({ timestamp: '2026-09-10T10:00:00.000Z', id: 'au1' }, o);

function render(rows, source) {
  ctx._svAuditRows = rows;
  ctx._svAuditSource = source || 'server';
  ctx.svRenderDoseAuditTable();
  return { body: dom.els['doseaudit-tbody'].innerHTML, count: dom.els['doseaudit-count'].textContent };
}

// ── B. the source banner ───────────────────────────────────────────────────
console.log('B. which copy is on screen');
function readWith(result) {
  dom.els['doseaudit-source'] = { innerHTML: '' };
  ctx.svData = () => ({ then: (f) => { f(result); return { then: () => {} }; } });
  ctx.localStorage = { getItem: () => JSON.stringify([ENTRY({ type: 'dose_calc' })]) };
  ctx.svRenderDoseAudit();
  return dom.els['doseaudit-source'].innerHTML;
}
let banner = readWith([ENTRY({ type: 'dose_calc' }), ENTRY({ type: 'controlled_log', id: 'au2' })]);
ok('a server read says so and gives the count', /server record/i.test(banner) && /2 entries/.test(banner), banner);
ok('...and names what this device holds, so the two can be compared',
   /this device holds 1/.test(banner), banner);

banner = readWith(null);
ok('A FAILED SERVER READ FALLS BACK TO LOCAL AND SAYS THE READ FAILED',
   /server read failed/i.test(banner), banner);
ok('...and warns the local copy is capped and may be incomplete',
   /capped at 500/.test(banner) && /incomplete/i.test(banner), banner);
ok('...and does NOT present it as the full record',
   /not the full record/i.test(banner), banner);

ctx.svData = null;
dom.els['doseaudit-source'] = { innerHTML: '' };
ctx.svRenderDoseAudit();
ok('with no transport at all it still labels the local copy rather than going silent',
   /this device only/i.test(dom.els['doseaudit-source'].innerHTML),
   dom.els['doseaudit-source'].innerHTML);

// ── C. empty is not the same as failed ─────────────────────────────────────
console.log('C. an empty trail and a failed read must not look alike');
let out = render([], 'server');
ok('an EMPTY trail says the empty answer is a correct one', /correct answer/i.test(out.body), out.body);
ok('...and explicitly says it is not a failed read', /not a failed read/i.test(out.body), out.body);
banner = readWith(null);
ok('while a FAILED read never claims the trail is empty', !/correct answer/i.test(banner), banner);

// ── D. the entry an inspector asks about ───────────────────────────────────
console.log('D. nothing that was recorded is dropped');
out = render([ENTRY({ type: 'controlled_log_blocked', drug: 'Ketamine',
                      reason: 'missing_witness_schedule_II' })], 'server');
ok('a REFUSAL is shown at all', /controlled_log_blocked/.test(out.body), out.body);
ok('...and ITS REASON survives, though no named column holds it',
   /missing_witness_schedule_II/.test(out.body), out.body);
out = render([ENTRY({ type: 'dose_calc', drug: 'X', species: 'equine', weight: 450,
                      result: 'flagged_needs_review' })], 'server');
ok('every unnamed field is carried into the detail column',
   /species/.test(out.body) && /weight/.test(out.body) && /flagged_needs_review/.test(out.body), out.body);

// ── the id provenance, which is the only way to tell the two apart ─────────
out = render([ENTRY({ type: 'dose_calc', id: 'ac9f3' })], 'server');
ok('a COMPUTED id is labelled as computed', /computed/.test(out.body), out.body);
out = render([ENTRY({ type: 'dose_calc', id: 'au9f3' })], 'server');
ok('...and an issued-at-event id is NOT', !/\(computed\)/.test(out.body), out.body);
out = render([{ timestamp: '2026-09-10T10:00:00.000Z', type: 'dose_calc' }], 'server');
ok('an entry with no id at all says so rather than rendering blank',
   /none/.test(out.body), out.body);

// ── escaping, because these fields are free text a practice types ──────────
out = render([ENTRY({ type: 'dose_calc', patient: '<img src=x onerror=alert(1)>' })], 'server');
ok('free-text fields are escaped', !/<img/.test(out.body) && /&lt;img/.test(out.body), out.body);

// ── E. filters must not be able to hide a record ───────────────────────────
console.log('E. filtering narrows, it never silently drops');
const A = ENTRY({ type: 'a', timestamp: '2026-09-01T00:00:00.000Z', id: 'au1' });
const B = ENTRY({ type: 'b', timestamp: '2026-09-20T00:00:00.000Z', id: 'au2' });
const UNDATED = { type: 'c', id: 'au3' };
dom.els['doseaudit-from'] = { value: '2026-09-10' };
dom.els['doseaudit-to'] = { value: '' };
dom.els['doseaudit-q'] = { value: '' };
out = render([A, B, UNDATED], 'server');
ok('a from-date excludes what is genuinely earlier', !/>a</.test(out.body), out.body);
ok('...and keeps what is later', />b</.test(out.body), out.body);
// THE FAIL-VISIBLE DIRECTION. An entry whose timestamp is missing cannot
// answer a date filter, so it is KEPT and the count says how many -- dropping
// it would remove a compliance record because of a question it cannot answer.
ok('AN UNDATED ENTRY IS KEPT, NOT SILENTLY DROPPED', />c</.test(out.body), out.body);
ok('...and the count says how many are undated', /no timestamp/.test(out.count), out.count);
ok('the count always shows shown-of-total, so a filter cannot hide the total',
   /of 3 entries shown/.test(out.count), out.count);

dom.els['doseaudit-from'] = { value: '' };
dom.els['doseaudit-q'] = { value: 'ketamine' };
out = render([ENTRY({ type: 'x', drug: 'Ketamine' }), ENTRY({ type: 'y', drug: 'Butorphanol', id: 'au2' })], 'server');
ok('the free-text filter matches across every field, not just the named ones',
   /Ketamine/.test(out.body) && !/Butorphanol/.test(out.body), out.body);
dom.els['doseaudit-q'] = { value: '' };

// ── F. the panel is reachable and the renderer is INVOKED ──────────────────
// This is the arm that would have caught the original defect. The app's own
// svNav() comment records the sairnbiz shape: a render function nothing
// invoked, so the card stayed empty for ever and the gap looked closed.
console.log('F. reachable, and wired');
ok('the panel exists in the markup', src.indexOf('id="panel-doseaudit"') !== -1);
ok('a nav button reaches it', /svNav\('panel-doseaudit'\)/.test(src));
ok('svNav INVOKES the renderer on arrival, not only at boot',
   /panelId==='panel-doseaudit'\s*&&\s*typeof svRenderDoseAudit==='function'\)\s*svRenderDoseAudit\(\)/.test(src),
   'the renderer is not wired into svNav');
ok('the table id the export button names is the table that exists',
   src.indexOf("exportTableCSV('panel-doseaudit-table'") !== -1
   && src.indexOf('id="panel-doseaudit-table"') !== -1);
ok('the panel states it is NOT tamper-evident rather than implying it is',
   /not tamper-evident/i.test(src));
ok('...and explains the au / ac id prefixes, which is the only way to tell '
   + 'an issued id from a computed one', /issued at the moment of the event/i.test(src));

console.log('\n' + '='.repeat(60));
console.log(pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
