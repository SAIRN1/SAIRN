// tests/sairnbiz_po_recv_reach_the_server.js
//
// Run:  node tests/sairnbiz_po_recv_reach_the_server.js
//
// SAIRNBIZ'S TWO MATCH DOCUMENTS LIVED ON ONE WORKSTATION AND NOWHERE ELSE.
//
// `python tools/local_only_collection_check.py` reported sairnbiz.html as
// 2 of 13 collections with NO route to a server, and named them: sb_po and
// sb_recv -- the purchase order and the receipt, built into the app on
// 2026-09-14 by the three-way-match work, after the pass that provisioned
// everything else, and so never provisioned at all.
//
// WHY THAT PAIR IS SHARPER THAN AN ORDINARY LOCAL-ONLY COLLECTION, which is
// what this suite exists to hold: sb_ap -- the bill -- was ALREADY backed up,
// and the double-entry ledger entry settling it is durable in Postgres. The PO
// and the receipt are the only two documents that say the bill was ever
// entitled to be paid. Clear the browser and a payable and a payment survive
// with nothing left that justifies either -- and sbThreeWayMatch, reading an
// empty sb_po, reports "no purchase order PO-2026-001 exists" against a bill
// that WAS correctly matched when it was paid. The control does not go quiet.
// It starts making a false accusation about work that was done right.
//
// FOUR PLACES HAVE TO AGREE FOR A COLLECTION TO ACTUALLY REACH THE SERVER and
// this platform has shipped three-of-four before. Section 1 checks all four
// BIDIRECTIONALLY -- not "the two new ones are present" but "these four lists
// are the same set" -- because the failure that matters is the one nobody adds
// a test for: a fifth collection added later to three of the four.
//
// THE FUNCTIONS ARE EXTRACTED FROM THE SHIPPED sairnbiz.html AND DRIVEN.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const rd = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8').replace(/\r\n/g, '\n');

const HTML = rd(process.env.SB_HTML ? path.relative(ROOT, process.env.SB_HTML) : 'sairnbiz.html');
const SDDATA = rd('api/sd-data.js');
const SCHEMA = rd('sql/sairnbiz_data_schema.sql');
const MIGRATION = rd('sql/sairnbiz_po_recv_migration.sql');
const REGISTRY = require(path.join(ROOT, 'api/_resources/sairnbiz.js'));

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }
function section(s) { console.log('\n' + s); }

// Lift a top-level function or var declaration out of the shipped file by
// brace-matching, skipping strings and comments. Same extractor as
// tests/sairnbiz_bill_cannot_settle_unmatched.js.
function grab(sig) {
  const start = HTML.indexOf(sig);
  assert.ok(start > 0, 'not found in sairnbiz.html: ' + sig);
  let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < HTML.length; i++) {
    const c = HTML[i], p = HTML[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
    if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
  }
  throw new Error('unterminated: ' + sig);
}

// A `var X=[...];` / `var X={...};` literal, read out of the shipped file and
// evaluated. Deliberately NOT re-declared in the test: a hand-copied list is a
// second source of truth that drifts, which is the exact class this suite is
// about.
function grabLiteral(name) {
  const m = new RegExp('var\\s+' + name + '\\s*=\\s*([\\[{][\\s\\S]*?[\\]}])\\s*;', 'm').exec(HTML);
  assert.ok(m, 'literal not found in sairnbiz.html: ' + name);
  return vm.runInNewContext('(' + m[1] + ')');
}

console.log('SAIRNbiz: the purchase order and the receipt reach a server\n');

// ── 1. THE FOUR PLACES AGREE, IN BOTH DIRECTIONS ────────────────────────────
section('1. client list, API map, resource registry and schema are the SAME SET');

const SB_SYNCED = grabLiteral('SB_SYNCED');
const SB_ID_PREFIX = grabLiteral('SB_ID_PREFIX');

// The API's id-column map, read out of api/sd-data.js rather than restated.
const sbResBlock = /const SB_RESOURCES = \{([\s\S]*?)\};/.exec(SDDATA);
assert.ok(sbResBlock, 'SB_RESOURCES not found in api/sd-data.js');
const SB_RESOURCES = vm.runInNewContext('({' + sbResBlock[1] + '})');

// Tables actually created, read out of the schema file.
const schemaTables = new Set();
for (const m of SCHEMA.matchAll(/create table if not exists public\.(sb_\w+)/g)) schemaTables.add(m[1]);

// The registry's sb_ resources.
const registrySb = REGISTRY.resources.filter((r) => /^sb_/.test(r));

const synced = new Set(SB_SYNCED);
const apiSet = new Set(Object.keys(SB_RESOURCES));
const regSet = new Set(registrySb);

ok(synced.has('sb_po') && synced.has('sb_recv'),
   'sairnbiz.html SB_SYNCED carries sb_po and sb_recv');
ok(apiSet.has('sb_po') && apiSet.has('sb_recv'),
   'api/sd-data.js SB_RESOURCES carries both');
ok(regSet.has('sb_po') && regSet.has('sb_recv'),
   'api/_resources/sairnbiz.js registers both');
ok(schemaTables.has('sb_po') && schemaTables.has('sb_recv'),
   'sql/sairnbiz_data_schema.sql creates both tables');

// BIDIRECTIONAL. Presence arms above would pass on a fifth collection added to
// three of the four lists later -- the drift shape, not the shape of today.
const diff = (a, b) => [...a].filter((k) => !b.has(k));
ok(diff(synced, apiSet).length === 0,
   'every synced collection has an API id-column -- otherwise the client pushes to a resource the server refuses: ' + diff(synced, apiSet));
ok(diff(apiSet, synced).length === 0,
   'every API resource is actually synced by the client -- otherwise the table backs up nothing forever and reads as coverage: ' + diff(apiSet, synced));
ok(diff(apiSet, regSet).length === 0,
   'every API resource is registered -- an unregistered name is refused by the allowlist before any credential matters: ' + diff(apiSet, regSet));
ok(diff(regSet, apiSet).length === 0,
   'every registered sb_ resource has an API branch: ' + diff(regSet, apiSet));
ok(diff(apiSet, schemaTables).length === 0,
   'every API resource has a table -- without one every write answers 503 NOT_PROVISIONED: ' + diff(apiSet, schemaTables));

// The id column follows the file's own stated rule, checked against the schema
// rather than against a second copy of the rule written here.
for (const [res, idCol] of Object.entries(SB_RESOURCES)) {
  const decl = new RegExp('create table if not exists public\\.' + res + '\\b[\\s\\S]*?\\n\\s*' + idCol + ' text not null');
  assert.ok(decl.test(SCHEMA), res + ': schema has no `' + idCol + ' text not null` column');
}
ok(true, 'every SB_RESOURCES id column exists in the schema with the name the API upserts on');

// The upsert target is what makes a duplicate id destructive, so the unique
// constraint backing it has to exist -- without it merge-duplicates has
// nothing to merge on and PostgREST rejects the write outright.
for (const [res, idCol] of Object.entries(SB_RESOURCES)) {
  assert.ok(new RegExp('unique \\(license_hash, ' + idCol + '\\)').test(SCHEMA),
            res + ': no unique(license_hash, ' + idCol + ') for the upsert to conflict on');
}
ok(true, 'every id column carries the unique(license_hash, <id>) the upsert conflicts on');

// COMMENTS STRIPPED FIRST. Both files DISCUSS delete grants at length -- the
// 2026-08-06 incident and why re-adding one is the overcorrection -- so a
// naive search over the raw text matches the warning against the practice and
// reports the file as committing it. A check that fires on its own
// documentation is a check nobody keeps.
const sqlCode = (s) => s.split('\n').filter((l) => !/^\s*--/.test(l)).join('\n');
ok(!/grant[^;]*\bdelete\b/i.test(sqlCode(MIGRATION)) && !/grant[^;]*\bdelete\b/i.test(sqlCode(SCHEMA)),
   'neither the schema nor the migration grants DELETE -- there is no delete path in api/sd-data.js to grant for');
// ...and the arm above is only worth having if it can fire, which a
// grant-line test cannot demonstrate from the passing side alone.
ok(/grant[^;]*\bdelete\b/i.test(sqlCode('grant select, delete on public.sb_po to service_role;')),
   'CONTROL: the same check DOES fire on a grant line that carries delete');

// The migration is what Michael actually runs against an already-live install,
// so a table present in the schema but missing from it is a silent half-fix.
for (const t of ['sb_po', 'sb_recv']) {
  assert.ok(new RegExp('create table if not exists public\\.' + t + '\\b').test(MIGRATION),
            'sql/sairnbiz_po_recv_migration.sql does not create ' + t);
}
ok(true, 'the standalone migration creates both tables, so an already-migrated install is not left behind');

// ── 2. A PO WITH NO ID IS NOT SILENTLY SKIPPED ──────────────────────────────
section('2. existing POs migrate in place -- a record with no id is never pushed');

function idCtx() {
  const store = {};
  const ctx = {
    console: { warn: () => {} },
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); }
    },
    store: store,
    SB_ID_PREFIX: SB_ID_PREFIX,
    _sbNoIdWarned: {}
  };
  vm.createContext(ctx);
  vm.runInContext(grab('function sbEnsureIds(key,arr){'), ctx);
  return ctx;
}

{
  // Rows raised before 2026-09-14 carry po_num and no id at all. sbSyncCollection
  // SKIPS any record without one, so without minting these back-fill to nothing
  // while the newer rows sync -- half a collection backed up, no error.
  const ctx = idCtx();
  const rows = [{ po_num: 'PO-2026-001', vendor: 'Stone World', amt: 1200 },
                { po_num: 'PO-2026-002', vendor: 'Atlas Marble', amt: 800 }];
  const changed = ctx.sbEnsureIds('sb_po', rows);
  ok(changed === true, 'sbEnsureIds reports it changed sb_po');
  ok(rows.every((r) => typeof r.id === 'string' && r.id.length > 0),
     'every pre-existing PO now carries an id');
  ok(rows[0].id !== rows[1].id, 'and the ids are distinct');
  ok(JSON.parse(ctx.store.sb_po)[0].id === rows[0].id,
     'the ids are PERSISTED, so the next load does not mint different ones and back the same PO up twice');
}
{
  // THE DECISION UNDER TEST, stated as a behaviour rather than a comment: the
  // minted id must NOT be the PO number. po_num comes from a per-device
  // counter, so two workstations both raise PO-2026-001; keying the upsert on
  // it would let the second device's PO silently overwrite the first through
  // resolution=merge-duplicates -- one row, two real purchase orders, no error.
  const ctx = idCtx();
  const rows = [{ po_num: 'PO-2026-001', vendor: 'Stone World', amt: 1200 },
                { po_num: 'PO-2026-001', vendor: 'Atlas Marble', amt: 9900 }];
  ctx.sbEnsureIds('sb_po', rows);
  ok(rows[0].id !== rows[1].id,
     'TWO POs SHARING A NUMBER GET DIFFERENT IDS -- the second does not overwrite the first on the server');
  ok(rows[0].id !== rows[0].po_num && !rows.some((r) => r.id === 'PO-2026-001'),
     '...because the synced id is not the PO number at all');
}
{
  // The rule sbEnsureIds already carries for the five user-visible-id
  // collections has to still hold -- this change adds a minting key and must
  // not have turned minting on everywhere.
  const ctx = idCtx();
  const rows = [{ inv_no: 'INV-1' }];
  const changed = ctx.sbEnsureIds('sb_invs', rows);
  ok(changed === false && rows[0].id === undefined,
     'CONTROL: sb_invs still does NOT mint -- its id is user-visible and a generated string would reach a customer');
}

// ── 3. TWO RECEIPTS IN ONE MILLISECOND ARE TWO RECEIPTS ─────────────────────
section('3. receipt ids do not collide');

const recsOf = (store) => JSON.parse(store.sb_recv || '[]');

function recvCtx(store) {
  const els = {};
  const ctx = {
    console: console,
    toasts: [],
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); }
    },
    store: store, els: els,
    toast: (m) => { ctx.toasts.push(String(m)); },
    $: (id) => (id in els ? els[id] : null),
    sbLocalToday: () => '2026-09-14',
    ld: (k, d) => { try { const v = JSON.parse(store[k]); return v === null ? d : v; } catch (e) { return d; } },
    st: function (k, v) { store[k] = JSON.stringify(v); return true; },
    rAP: () => {}
  };
  ctx.setFields = (f) => { Object.keys(f).forEach((k) => { els[k] = { value: String(f[k]) }; }); };
  vm.createContext(ctx);
  vm.runInContext(grab('function sbRecvAll(){'), ctx);
  vm.runInContext(grab('function sbPOAll(){'), ctx);
  // sbIsVoid joined 2026-09-14 with the void mechanism -- sbRecvLog now refuses
  // a receipt against a voided PO, and this sandbox threw ReferenceError the
  // moment it landed.
  vm.runInContext(grab('function sbIsVoid(r){'), ctx);
  vm.runInContext(grab('function sbRecvLog(){'), ctx);
  return ctx;
}

{
  // Date.now() is frozen for the whole block, which is the same-millisecond
  // case made deterministic rather than raced for. Before the collision loop
  // both receipts got 'RC'+the same base36 stamp; harmless while these rows
  // never left the device, and a SILENT OVERWRITE from the moment sb_recv is
  // upserted on (license_hash, recv_id) with resolution=merge-duplicates. Two
  // deliveries would become one and the three-way match would then refuse the
  // bill for a short receipt total that is an artefact of the id, not the goods.
  const store = { sb_po: JSON.stringify([{ po_num: 'PO-2026-001', vendor: 'Stone World', amt: 1200, id: 'POx' }]) };
  const ctx = recvCtx(store);
  // Frozen INSIDE the vm context only -- the extracted function reads the
  // context's Date, and this test process's own clock is never touched, so
  // there is nothing to restore afterwards.
  ctx.Date = { now: () => 1757808000000 };
  ctx.setFields({ rcvpo: 'PO-2026-001', rcvvendor: 'Stone World', rcvval: '700' });
  ctx.sbRecvLog();
  ctx.setFields({ rcvpo: 'PO-2026-001', rcvvendor: 'Stone World', rcvval: '500' });
  ctx.sbRecvLog();
  ok(recsOf(store).every((r) => /^RC/.test(String(r.id))),
     'both ids were minted by the frozen clock, so this is genuinely the same-millisecond case');
  const recs = JSON.parse(store.sb_recv);
  ok(recs.length === 2, 'two receipts logged in the same millisecond are both stored');
  ok(recs[0].id !== recs[1].id,
     '...WITH DIFFERENT IDS -- otherwise the second silently replaces the first on the server');
  ok(recs.map((r) => Number(r.val)).sort().join(',') === '500,700',
     '...and both amounts survive, so the match sees the full delivery');
}

// ── 4. A DUPLICATED PO NUMBER IS A REFUSAL, NOT A PICK-THE-FIRST ────────────
section('4. the match refuses an ambiguous PO number');

function matchCtx(store) {
  const ctx = {
    console: console,
    localStorage: {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); }
    },
    store: store,
    fmt: (v) => '$' + Number(v).toFixed(2),
    ld: (k, d) => { try { const v = JSON.parse(store[k]); return v === null ? d : v; } catch (e) { return d; } }
  };
  vm.createContext(ctx);
  vm.runInContext('var SB_MATCH_TOLERANCE = 0.00;', ctx);
  // sbMatchPure is the FUNCTIONAL CORE and loads BEFORE the shell that calls
  // it (item 92, 2026-09-14). A hand-listed sandbox like this one throws
  // ReferenceError on a CORRECT file the moment a declaration moves -- which is
  // exactly what it did here, loudly, rather than going quietly green.
  for (const sig of ['function sbMoneyCents(v){', 'function sbPOAll(){', 'function sbRecvAll(){',
                     'function sbVendorKey(v){', 'function sbIsVoid(r){',
                     'function sbMatchPure(pos,recs,po_num,vendor,amt){',
                     'function sbThreeWayMatch(po_num,vendor,amt){']) {
    vm.runInContext(grab(sig), ctx);
  }
  return ctx;
}

{
  // REACHABLE ONLY BECAUSE OF THIS CHANGE, which is why the arm is in this
  // suite and not the match suite. Before sync, two devices each held their own
  // PO-2026-001 and neither could see the other's. After hydration one device
  // holds both -- and sbThreeWayMatch took `[0]`, array order, validating the
  // bill against whichever happened to be first with no sign that a second PO
  // of the same number and a different amount sat next to it.
  const store = {
    sb_po: JSON.stringify([
      { id: 'POa', po_num: 'PO-2026-001', vendor: 'Stone World', amt: 1200 },
      { id: 'POb', po_num: 'PO-2026-001', vendor: 'Stone World', amt: 9900 }
    ]),
    sb_recv: JSON.stringify([{ id: 'RC1', po_num: 'PO-2026-001', vendor: 'Stone World', val: 1200 }])
  };
  const ctx = matchCtx(store);
  const r = ctx.sbThreeWayMatch('PO-2026-001', 'Stone World', 1200);
  ok(r.ok === false, 'a bill matching the FIRST of two same-numbered POs exactly is REFUSED');
  ok(/2 different purchase orders are numbered PO-2026-001/.test(r.reasons.join(' ')),
     '...and the refusal says how many and which number, so the duplicate can be found');
}
{
  // CONTROL. Without this the arm above passes on a match that refuses
  // everything, which would be the same as having no three-way match at all.
  const store = {
    sb_po: JSON.stringify([{ id: 'POa', po_num: 'PO-2026-001', vendor: 'Stone World', amt: 1200 }]),
    sb_recv: JSON.stringify([{ id: 'RC1', po_num: 'PO-2026-001', vendor: 'Stone World', val: 1200 }])
  };
  const ctx = matchCtx(store);
  const r = ctx.sbThreeWayMatch('PO-2026-001', 'Stone World', 1200);
  ok(r.ok === true, 'CONTROL: ONE PO with that number and everything agreeing still MATCHES');
}

console.log('\nALL ' + n + ' ASSERTIONS PASS');
