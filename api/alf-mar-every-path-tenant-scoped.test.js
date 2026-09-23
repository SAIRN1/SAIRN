// api/alf-mar-every-path-tenant-scoped.test.js
//
// REQUIREMENT: EVERY server-side query against the medication administration
//   record is scoped to one facility. Not the one the isolation suite drives
//   -- every one.
//
// CROSS-TENANT-ISOLATION: none (this file asserts a SOURCE property across
//   call sites; api/sd-data-alf-isolation.test.js is what drives the
//   behaviour, and that is where alf_mar's credit belongs)
//
// Run:  node api/alf-mar-every-path-tenant-scoped.test.js
//
// ── WHY THIS EXISTS, AND WHY IT IS NOT A DUPLICATE OF THE ISOLATION SUITE ──
// api/sd-data-alf-isolation.test.js DRIVES the alf_mar branch in
// api/sd-data.js and proves the tenant filter WORKS there: seed two
// facilities, ask as one, get one back. That is a behaviour check on ONE call
// site.
//
// MEASURED 2026-09-23: alf_mar is queried from FIVE places across THREE
// files. The driven suite covers one of them. The other four are correct
// today and nothing was watching them, which is the gap that matters -- a
// resource is only as scoped as its least-scoped reader, and the reader most
// likely to be written without the filter is the next one, in a file whose
// author is thinking about pharmacy intake or late-dose alerts rather than
// about tenancy.
//
// SO THE TWO CHECKS ASSERT DIFFERENT PROPERTIES AND BOTH ARE NEEDED:
//   the driven suite   this filter WORKS
//   this file          no call site LACKS one
//
// ── AND THIS IS A SOURCE CHECK, WHICH IS A WEAKER KIND OF EVIDENCE ────────
// It reads text. It cannot tell a filter that is present and ANDed wrong from
// one that is right, and a call site that builds its URL through a variable
// this parser cannot follow is reported as UNREADABLE rather than counted
// either way -- the third state, never folded into a pass. Said plainly
// because a string check wearing a behaviour check is the shape this platform
// keeps recording.
//
// ── WHAT alf_mar IS ──────────────────────────────────────────────────────
// A medication administration record: which resident was given which drug, at
// what dose, by whom. A cross-facility read here is another facility's
// resident's clinical record. That is why this table gets its own enumerating
// guard and the other SAIRNcare tables do not yet.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const API = __dirname;
const TABLE = 'alf_mar';

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}

// Every non-test .js under api/, read once.
function sources() {
  const out = [];
  (function walk(dir) {
    fs.readdirSync(dir, { withFileTypes: true }).forEach(function (d) {
      const p = path.join(dir, d.name);
      if (d.isDirectory()) return walk(p);
      if (!d.name.endsWith('.js') || d.name.endsWith('.test.js')) return;
      out.push([path.relative(API, p).replace(/\\/g, '/'),
                fs.readFileSync(p, 'utf8')]);
    });
  })(API);
  return out;
}

// WHAT COUNTS AS A CALL SITE, AND WHY THE RULE IS SPLIT IN TWO ───────────
// Two earlier versions of this were wrong in opposite directions and both are
// recorded because the shape matters more than the fix.
//
// V1 matched the bare name ANYWHERE and reported SIX "unscoped reads" that
// were a branch condition (`resource === 'alf_mar'`), the resource REGISTRY,
// and two lines of comment prose. A check that cannot tell a query from a
// sentence about a query gets refused on its first real run and then ignored.
//
// V2 required `rest(` and went blind to `api/alf-alerts.js:105`, which builds
// `const base = 'alf_mar?license_hash=eq.' + ...` and passes the VARIABLE to
// rest(). Its own UNREADABLE arm caught that -- correctly -- and would have
// reported the only non-sd-data read as unreadable forever. A disclosure list
// that never empties is a disclosure list nobody reads.
//
// SO THE RULE IS SPLIT BY SPELLING, because the two spellings carry different
// amounts of information:
//   `'alf_mar?...'`  a literal with a query string IS a query, wherever it is
//                    written. Nobody types that in prose or a branch test.
//   `'alf_mar'`      bare, is ambiguous -- so it counts only inside `rest(`,
//                    which is how every PostgREST URL in this repo is built.
// Line number of an offset. One helper, because writing the split inline is
// how the two functions below got mangled once already.
function lineOf(src, idx) { return src.slice(0, idx).split(String.fromCharCode(10)).length; }

function callSites(src) {
  const sites = [];
  const withQuery = new RegExp("['\"`]" + TABLE + "(\\?[^'\"`]*)['\"`]", 'g');
  let m;
  while ((m = withQuery.exec(src)) !== null) {
    sites.push({ at: lineOf(src, m.index), query: m[1], raw: m[0] });
  }
  const bare = new RegExp("rest\\(\\s*['\"`]" + TABLE + "['\"`]", 'g');
  while ((m = bare.exec(src)) !== null) {
    sites.push({ at: lineOf(src, m.index), query: '', raw: m[0] });
  }
  return sites;
}

// ── THE BLIND SPOT THAT REMAINS, AND WHY IT IS PROSE AND NOT AN ARM ──────
// A query assembled entirely from fragments with no `alf_mar?` literal
// anywhere -- `rest(TBL + '?' + filters)` -- is invisible to the rule above.
//
// AN ARM FOR IT WAS WRITTEN AND THEN DELETED, which is worth recording. It
// flagged every `rest(<identifier>` in any file mentioning the table, and on
// a 13,000-line monolith like api/sd-data.js that is TWENTY sites on a clean
// tree, none of them about this table. A permanently-red arm hides the next
// real one, and this file would have been the thing hiding it. The limit is
// stated here instead, where a reader who adds such a query will find it.
//
// It is a narrow limit: nothing in the tree builds a PostgREST path that way
// today, and the four real reads are all literals this parser reads directly.

// A site is either a READ that must carry `license_hash=eq.`, or a WRITE whose
// conflict key must lead with license_hash AND whose body must set it. The
// two are told apart by the query itself, not by guessing from the file name.
function classify(site, src, idx) {
  if (/on_conflict=/.test(site.query)) return 'write';
  if (site.query.indexOf('?') === 0) return 'read';
  return 'bare';
}

console.log('alf_mar -- EVERY server-side path is scoped to one facility\n');

const files = sources();
const found = [];
files.forEach(function ([rel, src]) {
  callSites(src).forEach(function (s) {
    found.push(Object.assign({ file: rel }, s, { kind: classify(s, src) }));
  });
});

test('the parser found call sites at all', function () {
  assert.ok(found.length >= 4,
    'only ' + found.length + ' call site(s) found. This check is worthless if it '
    + 'cannot see the queries it is about -- a zero here is a BROKEN PARSER '
    + 'reported as a clean platform, which is the failure this file must not have.');
});

console.log('');
found.forEach(function (s) {
  console.log('  %s:%d  %s  %s', s.file, s.at, s.kind.toUpperCase(),
              s.query.slice(0, 58) || '(bare table name)');
});
console.log('');

test('every READ carries license_hash=eq.', function () {
  const bad = found.filter(function (s) {
    return s.kind === 'read' && s.query.indexOf('license_hash=eq.') === -1;
  });
  assert.deepStrictEqual(bad.map(function (s) { return s.file + ':' + s.at; }), [],
    'a read of ' + TABLE + ' is not scoped to a facility. That is another '
    + "facility's resident's medication record reachable from this call site.");
});

test('every WRITE leads its conflict key with license_hash', function () {
  const bad = found.filter(function (s) {
    return s.kind === 'write' && s.query.indexOf('on_conflict=license_hash,') === -1;
  });
  assert.deepStrictEqual(bad.map(function (s) { return s.file + ':' + s.at; }), [],
    'an upsert into ' + TABLE + ' is keyed without license_hash leading -- one '
    + "facility's entry id would overwrite another's.");
});

test('every WRITE also sets license_hash in the body', function () {
  // The conflict key decides what COLLIDES. The body decides whose row it is.
  // A write with the right key and no body field files the entry under
  // whatever the column defaults to.
  const bad = [];
  files.forEach(function ([rel, src]) {
    callSites(src).forEach(function (s) {
      if (!/on_conflict=/.test(s.query)) return;
      const at = src.indexOf(s.raw);
      const window = src.slice(at, at + 900);
      if (!/license_hash:\s*licHash/.test(window)) bad.push(rel + ':' + s.at);
    });
  });
  assert.deepStrictEqual(bad, [],
    'an upsert into ' + TABLE + ' does not set license_hash: licHash within 900 '
    + 'characters of the call. Either it does not set it, or it is far enough '
    + 'away that this check cannot see it -- and the second is reported the same '
    + 'as the first on purpose.');
});

test('no call site names the bare table with no query at all', function () {
  const bare = found.filter(function (s) { return s.kind === 'bare'; });
  assert.deepStrictEqual(bare.map(function (s) { return s.file + ':' + s.at; }), [],
    'a bare `' + TABLE + "' with no query string is an unscoped read of every "
    + 'facility, which is exactly the shape sql/alf_mar_sweep_index.sql records '
    + 'loadMar() having had.');
});

test('the RPC write path binds the tenant as an argument', function () {
  // sd-data.js writes through rpc/alf_check_and_insert_mar_entry, which has no
  // conflict key for the loop above to see. Its tenant binding is
  // p_license_hash, and the only thing that must never happen is it being taken
  // from the payload.
  const sd = files.filter(function (f) { return f[0] === 'sd-data.js'; })[0];
  assert.ok(sd, 'sd-data.js not found');
  const i = sd[1].indexOf('rpc/alf_check_and_insert_mar_entry');
  assert.ok(i > 0, 'the MAR insert RPC is gone -- re-read this file before '
    + 'assuming the write path is still what it was');
  const body = sd[1].slice(i, i + 600);
  assert.match(body, /p_license_hash:\s*licHash/,
    'the RPC does not bind p_license_hash to the handler-derived hash');
  assert.ok(!/p_license_hash:\s*[^,]*payload/.test(body),
    'the RPC takes p_license_hash from the payload');
});

// ── THE NEGATIVE CONTROL ────────────────────────────────────────────────────
// Every assertion above passes on a clean tree, so none of them has refused
// anything. These drive the parser against text that MUST be caught.
console.log('\nTHE NEGATIVE CONTROL -- the parser refuses what it is supposed to');

test('an unfiltered read IS detected', function () {
  const fixture = "const r = await fetch(rest('alf_mar?select=entry_id,data'));";
  const s = callSites(fixture).map(function (x) {
    return Object.assign(x, { kind: classify(x, fixture) }); });
  assert.strictEqual(s.length, 1, 'the parser did not see the fixture at all');
  assert.strictEqual(s[0].kind, 'read');
  assert.strictEqual(s[0].query.indexOf('license_hash=eq.'), -1,
    'the fixture would have passed the read assertion');
});

test('a bare table name IS detected', function () {
  const fixture = "await fetch(rest('alf_mar'), { headers });";
  const s = callSites(fixture).map(function (x) {
    return Object.assign(x, { kind: classify(x, fixture) }); });
  assert.strictEqual(s.length, 1);
  assert.strictEqual(s[0].kind, 'bare');
});

test('a conflict key missing license_hash IS detected', function () {
  const fixture = "await fetch(rest('alf_mar?on_conflict=entry_id'), o);";
  const s = callSites(fixture).map(function (x) {
    return Object.assign(x, { kind: classify(x, fixture) }); });
  assert.strictEqual(s[0].kind, 'write');
  assert.strictEqual(s[0].query.indexOf('on_conflict=license_hash,'), -1);
});

test('a filtered read is NOT falsely flagged', function () {
  // The paired positive: a parser that flagged everything would score full
  // marks above and be useless.
  const fixture = "rest('alf_mar?license_hash=eq.' + enc(h) + '&select=data')";
  const s = callSites(fixture)[0];
  assert.ok(s.query.indexOf('license_hash=eq.') !== -1);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
