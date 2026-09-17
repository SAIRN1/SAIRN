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
// SV_HTML is honoured here too, so a negative control can point this suite at a
// MUTATED COPY rather than patching the tracked file. Same convention four
// other SAIRNvet and platform suites already carry.
const src = fs.readFileSync(process.env.SV_HTML || HTML, 'utf8');

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
  SV_FETCH_TIMEOUT_MS: 40,        // short, so the hang-guard arm is testable
  svData: null,
  JSON, Object, String, Array, Promise, Math, Date, setTimeout, console,
  Intl, isNaN
};
const vm = require('node:vm');
const ctx = vm.createContext(sandbox);
vm.runInContext(
  'var _svAuditRows = []; var _svAuditSource = ""; var _svAuditLoaded = false;\n' +
  fn('function svDoseAuditLocal(') + '\n' +
  fn('function svAuditLocalOnly(') + '\n' +
  fn('function svRenderDoseAudit(') + '\n' +
  fn('function svAuditZone(') + '\n' +
  fn('function svAuditLocalTime(') + '\n' +
  fn('function svAuditDayPrefix(') + '\n' +
  fn('function svAuditHaystack(') + '\n' +
  fn('function svClearDoseAuditFilters(') + '\n' +
  fn('function svRenderDoseAuditTable(') + '\n', ctx);

// The extraction is ASSERTED, so an arm written as "must say X" cannot pass
// because nothing was defined.
['svDoseAuditLocal', 'svAuditLocalOnly', 'svRenderDoseAudit', 'svAuditZone',
 'svAuditLocalTime', 'svAuditDayPrefix', 'svAuditHaystack',
 'svClearDoseAuditFilters', 'svRenderDoseAuditTable'].forEach((n) => {
  ok('A. ' + n + ' was lifted out of the real file', typeof ctx[n] === 'function');
});

const ENTRY = (o) => Object.assign({ timestamp: '2026-09-10T10:00:00.000Z', id: 'au1' }, o);

function render(rows, source) {
  ctx._svAuditRows = rows;
  ctx._svAuditSource = source || 'server';
  ctx._svAuditLoaded = true;      // these arms are about a SETTLED read
  ctx.svRenderDoseAuditTable();
  return { body: dom.els['doseaudit-tbody'].innerHTML, count: dom.els['doseaudit-count'].textContent };
}

// The read is genuinely asynchronous now -- it races the response against a
// hang guard -- so every arm that drives it has to await. The previous harness
// handed svData a SYNCHRONOUS thenable, which meant no arm could ever observe
// the IN-FLIGHT state, and the in-flight state turned out to hold a real
// defect (section C2). A double that cannot reach a state is a control that
// cannot fail there.
const tick = () => new Promise((r) => setTimeout(r, 5));

let banner = '';
let out = null;

async function main() {

// ── B. the source banner ───────────────────────────────────────────────────
console.log('B. which copy is on screen');
// `envelope` is what svData(..., wantEnvelope=true) resolves to: an object
// carrying BOTH the rows and the server's `provisioned` flag, or null when the
// read failed. The flag half is section C1 and it is not cosmetic.
async function readWith(envelope, localRows) {
  dom.els['doseaudit-source'] = { innerHTML: '' };
  dom.els['doseaudit-tbody'] = { innerHTML: '' };
  dom.els['doseaudit-count'] = { textContent: '' };
  ctx.svData = () => Promise.resolve(envelope);
  ctx.localStorage = { getItem: () => JSON.stringify(
    localRows || [ENTRY({ type: 'dose_calc' })]) };
  ctx.svRenderDoseAudit();
  await tick();
  return dom.els['doseaudit-source'].innerHTML;
}
const SERVED = (rows) => ({ data: rows, provisioned: true });

banner = await readWith(SERVED([ENTRY({ type: 'dose_calc' }), ENTRY({ type: 'controlled_log', id: 'au2' })]));
ok('a server read says so and gives the count', /server record/i.test(banner) && /2 entries/.test(banner), banner);
ok('...and names what this device holds, so the two can be compared',
   /this device holds 1/.test(banner), banner);

banner = await readWith(null);
ok('A FAILED SERVER READ FALLS BACK TO LOCAL AND SAYS THE READ FAILED',
   /server read failed/i.test(banner), banner);
ok('...and warns the local copy is capped and may be incomplete',
   /capped at 500/.test(banner) && /incomplete/i.test(banner), banner);
ok('...and does NOT present it as the full record',
   /not the full record/i.test(banner), banner);

ctx.svData = null;
dom.els['doseaudit-source'] = { innerHTML: '' };
ctx.svRenderDoseAudit();
await tick();
ok('with no transport at all it still labels the local copy rather than going silent',
   /this device only/i.test(dom.els['doseaudit-source'].innerHTML),
   dom.els['doseaudit-source'].innerHTML);

// ── C. empty is not the same as failed ─────────────────────────────────────
console.log('C. an empty trail and a failed read must not look alike');
out = render([], 'server');
ok('an EMPTY trail says the empty answer is a correct one', /correct answer/i.test(out.body), out.body);
ok('...and explicitly says it is not a failed read', /not a failed read/i.test(out.body), out.body);

// THIS ARM USED TO READ THE WRONG ELEMENT AND COULD NOT FAIL.
//
// It was written as `!/correct answer/i.test(banner)` where `banner` is
// `doseaudit-source`.innerHTML. The string "correct answer" only ever appears
// in the TBODY template. So the assertion tested an element that could never
// contain the string it was looking for: rewriting the failed-read branch to
// say literally "the trail is empty" still passed it. The one arm defending
// the headline claim of this whole feature was inert. Found by independent
// review, 2026-09-16; it is asserted on the TBODY now, which is where the
// sentence lives.
await readWith(null);
ok('while a FAILED read never claims the trail is empty (ASSERTED ON THE TBODY, '
   + 'which is where that sentence lives)',
   !/correct answer/i.test(dom.els['doseaudit-tbody'].innerHTML),
   dom.els['doseaudit-tbody'].innerHTML);

// ── C0. THE TRANSPORT ITSELF, because C1 below drives a DOUBLE ────────────
//
// THIS ARM EXISTS BECAUSE ITS ABSENCE WAS CAUGHT BY A SABOTAGE PASS, and the
// failure was the same shape as the one this whole commit is fixing. C1 hands
// svRenderDoseAudit a stand-in svData that already returns an envelope, so
// reverting the REAL svData to discard `provisioned` left every C1 arm green.
// A control that cannot reach the code it is defending is not a control. So
// this drives the real svData against a fake fetch and checks the contract in
// BOTH modes.
console.log('C0. svData carries the provisioned flag, and only when asked');
const tctx = vm.createContext({
  SV_DATA_API: '/api/sd-data',
  svLoad: () => 'LIC-1',
  svFetchTimeoutSignal: () => undefined,
  fetch: null, JSON, Object, String, Array, Promise, console
});
vm.runInContext(fn('function svData('), tctx);
ok('svData was lifted out of the real file', typeof tctx.svData === 'function');
const serve = (body, okFlag) => { tctx.fetch = () => Promise.resolve({
  ok: okFlag !== false, status: 200, json: () => Promise.resolve(body) }); };

serve({ ok: true, data: [], provisioned: false });
let env = await tctx.svData('read', 'sv_audit_log', {}, true);
ok('an UNPROVISIONED read reaches the caller WITH the flag, not as a bare []',
   env && env.provisioned === false && Array.isArray(env.data) && env.data.length === 0,
   JSON.stringify(env));
serve({ ok: true, data: [{ id: 'au1' }], provisioned: true });
env = await tctx.svData('read', 'sv_audit_log', {}, true);
ok('a provisioned read carries provisioned:true and the rows',
   env && env.provisioned === true && env.data.length === 1, JSON.stringify(env));
// THE OTHER FORTY-ONE CALLERS ARE UNCHANGED, and that is asserted rather than
// assumed -- the whole reason `wantEnvelope` is a fourth parameter instead of
// a changed return type.
serve({ ok: true, data: [{ id: 'au1' }], provisioned: true });
const bare = await tctx.svData('read', 'sv_patients', {});
ok('without the flag svData still returns bare data, so no other caller moved',
   Array.isArray(bare) && bare.length === 1 && bare[0].id === 'au1', JSON.stringify(bare));
// A response with NO flag at all is UNKNOWN, never false. Several branches in
// api/sd-data.js do not set it, and reading silence as "not provisioned" would
// invent a refusal and send a clinic to run a migration it already ran.
serve({ ok: true, data: [{ id: 'au1' }] });
env = await tctx.svData('read', 'sv_audit_log', {}, true);
ok('an ABSENT provisioned flag is undefined, NOT false',
   env && env.provisioned === undefined, JSON.stringify(env));
serve({ ok: false, error: { code: 'NOPE' } }, false);
env = await tctx.svData('read', 'sv_audit_log', {}, true);
eq('a REFUSED read is still null in envelope mode, so failed-vs-empty is intact',
   env, null);

// ── C1. NOT SET UP IS A THIRD ANSWER, and it used to render as the second ──
// api/sd-data.js answers a missing table with {ok:true, data:[],
// provisioned:false}. svData() discarded the flag, so a clinic that had never
// run the migration was told, on a DEA record, that the empty answer was the
// correct one -- while entries sat unread on the device.
console.log('C1. an UNPROVISIONED server is neither empty nor a failed read');
banner = await readWith({ data: [], provisioned: false },
                        [ENTRY({ type: 'controlled_log' }), ENTRY({ type: 'dose_calc', id: 'au2' })]);
ok('an UNPROVISIONED server says the trail is NOT SET UP',
   /not set up/i.test(banner), banner);
ok('...and says explicitly that this is not a claim that nothing was dosed',
   /not a statement that nothing was dosed/i.test(banner), banner);
ok('...and names the migration that fixes it',
   /sairnvet_data_schema\.sql/.test(banner), banner);
ok('...and does NOT present it as the server record',
   !/showing the server record/i.test(banner), banner);
ok('...and the TABLE does not say the empty answer is correct either',
   !/correct answer/i.test(dom.els['doseaudit-tbody'].innerHTML),
   dom.els['doseaudit-tbody'].innerHTML);
ok('...and it falls back to the LOCAL entries rather than showing nothing',
   /controlled_log/.test(dom.els['doseaudit-tbody'].innerHTML),
   dom.els['doseaudit-tbody'].innerHTML);

// ── C2. IN FLIGHT IS A FOURTH ANSWER, reachable with no misconfiguration ───
// The filters are live while the read is outstanding and call the TABLE
// renderer directly, so typing one character during a 15s read printed the
// same "it is not a failed read" sentence under a banner still saying
// Loading.
console.log('C2. a read still in flight is not an answer about the trail');
dom.els['doseaudit-source'] = { innerHTML: '' };
dom.els['doseaudit-tbody'] = { innerHTML: '' };
dom.els['doseaudit-count'] = { textContent: '' };
ctx.svData = () => new Promise(() => {});      // never settles
ctx.localStorage = { getItem: () => '[]' };
ctx.svRenderDoseAudit();
ctx.svRenderDoseAuditTable();                  // what a keystroke in a filter does
ok('an in-flight read does NOT claim the trail is empty',
   !/correct answer/i.test(dom.els['doseaudit-tbody'].innerHTML),
   dom.els['doseaudit-tbody'].innerHTML);
ok('...it says the read is still running',
   /still reading/i.test(dom.els['doseaudit-tbody'].innerHTML),
   dom.els['doseaudit-tbody'].innerHTML);
ok('...and the count says so too rather than printing 0 of 0',
   /reading the trail/i.test(dom.els['doseaudit-count'].textContent),
   dom.els['doseaudit-count'].textContent);

// ── C3. AND A READ THAT NEVER ANSWERS MUST NOT SIT ON "Loading" FOR EVER ───
// svFetchTimeoutSignal() is feature-detected and returns undefined on an
// engine without AbortSignal.timeout; on such an engine this promise neither
// resolves nor rejects. svPushOne races a timer for exactly this reason.
await new Promise((r) => setTimeout(r, sandbox.SV_FETCH_TIMEOUT_MS + 2000 + 60));
ok('a read that never answers falls back to local and SAYS it timed out',
   /did not answer/i.test(dom.els['doseaudit-source'].innerHTML),
   dom.els['doseaudit-source'].innerHTML);
ok('...and says that is not a statement that the trail is empty',
   /not a statement that the trail is empty/i.test(dom.els['doseaudit-source'].innerHTML),
   dom.els['doseaudit-source'].innerHTML);

// ── C4. LOCAL IS NOT ALWAYS A SUBSET OF SERVER ─────────────────────────────
// Entries written while a push was refused or timed out live only on the
// device. The banner framed local as a subset ("the server copy is not
// capped; this device holds N"), which is inverted exactly then.
console.log('C4. entries this device holds and the server does not are disclosed');
banner = await readWith(SERVED([ENTRY({ id: 'au1', type: 'a' })]),
                        [ENTRY({ id: 'au1', type: 'a' }),
                         ENTRY({ id: 'au7', type: 'controlled_log' }),
                         ENTRY({ id: 'au8', type: 'controlled_log' })]);
ok('the banner NAMES how many entries are on this device only',
   /2 entries are on this device and NOT on the server/i.test(banner), banner);
ok('...and says why they are there',
   /refused or timed out/i.test(banner), banner);
ok('...and says they are not in the table', /not in the table below/i.test(banner), banner);
banner = await readWith(SERVED([ENTRY({ id: 'au1', type: 'a' })]),
                        [ENTRY({ id: 'au1', type: 'a' })]);
ok('and when every local entry IS on the server it says nothing extra, because '
   + 'a disclosure that is always on stops being read',
   !/on this device and NOT on the server/i.test(banner), banner);

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
ok('...and the count says how many are undated', /no usable timestamp/.test(out.count), out.count);
ok('the count always shows shown-of-total, so a filter cannot hide the total',
   /of 3 entries shown/.test(out.count), out.count);

// AN UNPARSEABLE TIMESTAMP IS THE SAME CASE AS A MISSING ONE, and the code
// used to guard only the missing half while its own comment claimed both.
// `ts &&` is true for "Sept 15 2026", whose slice(0,10) is "Sept 15 2" and
// compares LEXICALLY, so every `to` filter dropped it silently. The entry that
// vanished in the review's reproduction was a controlled_log_blocked -- a
// refusal, the entry an inspector is most likely asking about.
const BADTS = { type: 'refused', id: 'au4', timestamp: 'Sept 15 2026' };
dom.els['doseaudit-from'] = { value: '' };
dom.els['doseaudit-to'] = { value: '2026-12-31' };
out = render([B, BADTS], 'server');
ok('AN ENTRY WITH AN UNPARSEABLE TIMESTAMP SURVIVES A to-FILTER',
   />refused</.test(out.body), out.body);
dom.els['doseaudit-to'] = { value: '' };
dom.els['doseaudit-from'] = { value: '2000-01-01' };
out = render([B, BADTS], 'server');
ok('...and a from-filter too', />refused</.test(out.body), out.body);
ok('...and it is COUNTED as having no usable timestamp rather than passing silently',
   /1 with no usable timestamp/.test(out.count), out.count);

dom.els['doseaudit-from'] = { value: '' };
dom.els['doseaudit-to'] = { value: '' };
dom.els['doseaudit-q'] = { value: 'ketamine' };
out = render([ENTRY({ type: 'x', drug: 'Ketamine' }), ENTRY({ type: 'y', drug: 'Butorphanol', id: 'au2' })], 'server');
ok('the free-text filter matches across every field, not just the named ones',
   /Ketamine/.test(out.body) && !/Butorphanol/.test(out.body), out.body);

// IT MATCHES VALUES, NOT FIELD NAMES. Searching JSON.stringify(e) matched the
// KEYS too, so the very words the placeholder suggests -- drug, patient, type
// -- matched every row, and "N of M shown" read as a narrowing that had not
// happened.
dom.els['doseaudit-q'] = { value: 'drug' };
out = render([ENTRY({ type: 'x', drug: 'Ketamine' }), ENTRY({ type: 'y', drug: 'Butorphanol', id: 'au2' })], 'server');
ok('a FIELD NAME does not match every row just by being a field name',
   /0 of 2 entries shown/.test(out.count), out.count);
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
ok('the table the export reads is the table that exists',
   src.indexOf('id="panel-doseaudit-table"') !== -1);
ok('the panel states it is NOT tamper-evident rather than implying it is',
   /not tamper-evident/i.test(src));
ok('...and explains the au / ac id prefixes, which is the only way to tell '
   + 'an issued id from a computed one', /issued at the moment of the event/i.test(src));

// ── G. THE PROVENANCE LEAVES THE BUILDING WITH THE ROWS ────────────────────
// Every sentence the panel spent its design on -- which copy, the cap, the
// filters in force, append-only, not-tamper-evident -- lives OUTSIDE the
// <table>, and exportTableCSV serialises the table and nothing else. A
// dosing-audit-trail.csv handed to an inspector was indistinguishable between
// the full server record and a capped local copy taken after a failed read.
console.log('G. the exported file says which record it is');
ok('the Export button calls the dose-audit exporter, not the generic one',
   /onclick="svExportDoseAudit\(\)"/.test(src)
   && src.indexOf("exportTableCSV('panel-doseaudit-table'") === -1, 'still generic');
const exp = fn('function svExportDoseAudit(');
[['which copy is on screen', /WHICH COPY/],
 ['how many rows are in the file', /ROWS IN THIS FILE/],
 ['the filters that were in force', /FILTERS IN FORCE/],
 ['that the record is append-only', /APPEND-ONLY/],
 ['that it is NOT tamper-evident', /NOT TAMPER-EVIDENT/],
 ['the UTC basis of the date filters', /UTC day/]].forEach(([what, re]) => {
  ok('the CSV carries ' + what, re.test(exp), exp.slice(0, 200));
});
ok('and the generic exporter is still there for every other table',
   /function exportTableCSV\(/.test(src));

// ── H. the date filters name their basis on screen ────────────────────────
// The column header always read "When (UTC)" but the two pickers said only
// "From date"/"To date", so a US-Eastern practice filtering one day loses
// every evening dose after 20:00 local to the next UTC day.
ok('H. the screen says the date filters are UTC, not local',
   /filter on the <strong>UTC<\/strong> day/i.test(src));

// ── I. LOCAL TIME IS A DISPLAY; UTC IS STILL THE RECORD ───────────────────
//
// Michael's decision, 2026-09-16: UTC stays the stored, immutable basis --
// FDA's Part 11 guidance says for systems spanning time zones the recorded
// stamp is not expected to be the signer's local time -- and the LOCAL time is
// added as a labelled display beside it, never instead of it.
//
// THE DST ARMS ARE THE POINT OF THIS SECTION AND THEY USE REAL Intl, NOT A
// MOCK. A conversion that is right in July and wrong in November is the shape
// this fails in, and a stubbed formatter would prove nothing about it. The
// fall-back arm is the sharp one: 01:30 local happens TWICE on 2026-11-01 and
// the two instants are an hour apart, so without the zone abbreviation beside
// it the two rows would be indistinguishable on a controlled-substance record.
console.log('I. local time is displayed, labelled, and correct across DST');
const TZ = 'America/New_York';
const L = (iso) => ctx.svAuditLocalTime(iso, TZ);

eq('I spring-forward, the EST side (06:30Z is 01:30 EST)',
   L('2026-03-08T06:30:00.000Z'), '2026-03-08, 01:30:00 EST');
eq('I spring-forward, the EDT side one hour later (07:30Z is 03:30 EDT, and '
   + '02:30 local never happened)',
   L('2026-03-08T07:30:00.000Z'), '2026-03-08, 03:30:00 EDT');
eq('I fall-back, the EDT side (05:30Z is 01:30 EDT)',
   L('2026-11-01T05:30:00.000Z'), '2026-11-01, 01:30:00 EDT');
eq('I fall-back, the EST side an hour later -- SAME wall clock, and only the '
   + 'zone abbreviation tells the two instants apart',
   L('2026-11-01T06:30:00.000Z'), '2026-11-01, 01:30:00 EST');
ok('I and those two are genuinely different instants rendered at the same '
   + 'wall-clock time, which is why the abbreviation is not decoration',
   L('2026-11-01T05:30:00.000Z') !== L('2026-11-01T06:30:00.000Z'), 'identical');

// THE CASE THE REVIEW NAMED. An evening dose local lands on the NEXT UTC day,
// which is why the date filters carry their own disclosure and why a reader
// needs the local column at all.
eq('I an evening dose sits on the previous LOCAL day from its UTC day',
   L('2026-09-15T23:30:00.000Z'), '2026-09-15, 19:30:00 EDT');
eq('...and its UTC day is the next one, which is what the filters compare',
   ctx.svAuditDayPrefix('2026-09-16T03:30:00.000Z'), '2026-09-16');

// FAILS CLOSED. A time it cannot convert or cannot label is NOT converted.
eq('I an unparseable timestamp converts to null, never to a guessed local time',
   L('Sept 15 2026'), null);
eq('I a missing timestamp converts to null', L(undefined), null);
eq('I and with NO resolvable zone it returns null rather than an unlabelled time',
   ctx.svAuditLocalTime('2026-09-15T12:00:00.000Z', '__not_a_zone__'), null);

// THE CELL, THE HEADER AND THE RECORD.
const _zone = ctx.svAuditZone;
ctx.svAuditZone = () => TZ;
dom.els['doseaudit-zone-th'] = { textContent: '' };
out = render([ENTRY({ type: 'dose_calc', timestamp: '2026-09-15T23:30:00.000Z' })], 'server');
ok('I the row shows the LOCAL time', /19:30:00 EDT/.test(out.body), out.body);
ok('...and STILL shows the stored UTC value, because that is the record',
   /2026-09-15T23:30:00\.000Z/.test(out.body), out.body);
ok('...and the ZONE is named in the column header, so it survives printing',
   /Local time — America\/New_York/.test(dom.els['doseaudit-zone-th'].textContent),
   dom.els['doseaudit-zone-th'].textContent);

out = render([{ type: 'refused', id: 'au4', timestamp: 'Sept 15 2026' }], 'server');
ok('I a row whose timestamp will not parse says "see UTC" rather than a '
   + 'converted time', /see UTC/.test(out.body), out.body);
ok('...and that row is still SHOWN, not dropped', /refused/.test(out.body), out.body);

ctx.svAuditZone = () => null;
dom.els['doseaudit-zone-th'] = { textContent: '' };
out = render([ENTRY({ type: 'dose_calc' })], 'server');
ok('I with no resolvable zone the header says so outright',
   /UNAVAILABLE/.test(dom.els['doseaudit-zone-th'].textContent),
   dom.els['doseaudit-zone-th'].textContent);
ok('...and no row invents a local time', !/EDT|EST/.test(out.body), out.body);
ctx.svAuditZone = _zone;

// NOTHING WRITES A CONVERTED TIME. The display is derived on read; the store
// still holds toISOString() and only toISOString().
ok('I logDoseAudit still writes toISOString and nothing else',
   /function logDoseAudit\([\s\S]{0,1200}?toISOString\(\)/.test(src), 'writer changed');
ok('I no write path calls the local-time formatter',
   !/st\('sv_audit_log'[\s\S]{0,200}svAuditLocalTime/.test(src)
   && !/svAuditLocalTime[^\n]{0,80}(localStorage|setItem)/.test(src), 'a converted time is being stored');
ok('I the exported CSV names the zone of its local column',
   /TIME ZONE OF THE "When \(local\)" COLUMN/.test(fn('function svExportDoseAudit(')));
ok('I ...and says UTC is the stored basis and local is derived',
   /stored, immutable basis/.test(fn('function svExportDoseAudit(')));
ok('I the table header still carries the UTC column beside the local one',
   /<th>When <span id="doseaudit-zone-th">\(local\)<\/span><\/th><th>When \(UTC\)<\/th>/.test(src),
   'the UTC column was replaced rather than joined');
ok('I the empty-state colspan matches the widened table',
   /colspan="8"[^>]*>'\s*\+\s*\(!_svAuditLoaded/.test(src)
   || /tb\.innerHTML = '<tr><td colspan="8"/.test(src), 'colspan not widened');

console.log('\n' + '='.repeat(60));
console.log(pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);

}

main().catch((e) => { console.error(e); process.exit(1); });
