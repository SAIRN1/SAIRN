// tests/run_row_count_baseline_probe.js
//
//   node tests/run_row_count_baseline_probe.js
//
// Does the 65b writer ever write a ZERO it did not measure?
//
// THAT IS THE ONLY ARM THAT REALLY MATTERS. A zero in
// db/row_count_baseline.json means "this table exists and is empty", so a
// table that 404'd or errored and was written as 0 would make a restore that
// lost every row in it compare EQUAL -- a confident pass, produced by the file
// whose whole purpose is to make that impossible. Every failure path is driven
// here and asserted to be OMITTED, not zeroed.
//
// NOTHING HERE TOUCHES THE NETWORK. The counting half is pure (see the tool's
// FUNCTIONAL CORE section): classify() takes a response shape, buildBaseline()
// takes outcomes. Both are driven directly with hand-built inputs, which is
// what makes the failure paths reachable at all -- a probe that needed a live
// database could never drive "the table 404s".

'use strict';
const fs = require('fs');
const path = require('path');

const REPO = path.dirname(__dirname);
const B = require(path.join(REPO, 'tools', 'row_count_baseline.js'));

const fails = [];
function check(name, cond, detail) {
  console.log((cond ? '  ok   ' : '  FAIL ') + name
    + (cond ? '' : '\n         ' + String(JSON.stringify(detail)).slice(0, 300)));
  if (!cond) fails.push(name);
}

console.log('row count baseline (item 65b) -- absent is never zero');

// ── 1. THE THREE OUTCOMES, EACH DRIVEN ─────────────────────────────────────
const ok = B.classify({ ok: true, status: 200, contentRange: '0-0/1234' });
check('a real count is COUNTED and the total is read off content-range',
  ok.kind === 'counted' && ok.count === 1234, ok);

const empty = B.classify({ ok: true, status: 200, contentRange: '*/0' });
check('a genuinely EMPTY table is counted as 0 -- the one legitimate zero',
  empty.kind === 'counted' && empty.count === 0, empty);

const gone = B.classify({ ok: false, status: 404, text: 'PGRST205 not found' });
check('a 404 is NOT_PROVISIONED, never a count',
  gone.kind === 'not_provisioned', gone);

const undeployed = B.classify({ ok: false, status: 400,
  text: 'relation "sen_x" does not exist (42P01)' });
check('a 400 naming 42P01 / does not exist is NOT_PROVISIONED too -- the '
  + 'never-run-migration shape this platform already has on record',
  undeployed.kind === 'not_provisioned', undeployed);

const broke = B.classify({ ok: false, status: 500, text: 'upstream timeout' });
check('a 500 is COULD_NOT_COUNT -- a read that failed is not a table that is '
  + 'absent, and the two must not be folded together',
  broke.kind === 'could_not_count', broke);

const noRange = B.classify({ ok: true, status: 200, contentRange: '' });
check('a 200 with NO exact count is COULD_NOT_COUNT, not 0',
  noRange.kind === 'could_not_count', noRange);

const nulled = B.classify(null);
check('a missing response object is COULD_NOT_COUNT and does not throw',
  nulled.kind === 'could_not_count', nulled);

check('parseCount returns null rather than NaN or 0 when there is no total',
  B.parseCount('') === null && B.parseCount('0-0/abc') === null
  && B.parseCount(null) === null,
  [B.parseCount(''), B.parseCount('0-0/abc'), B.parseCount(null)]);

// ── 2. THE FILE: NOTHING THAT FAILED APPEARS AS A NUMBER ───────────────────
const built = B.buildBaseline({
  good: { kind: 'counted', count: 42 },
  reallyEmpty: { kind: 'counted', count: 0 },
  missing: { kind: 'not_provisioned', why: 'HTTP 404' },
  broken: { kind: 'could_not_count', why: 'HTTP 500' }
}, { capturedAt: '2026-09-25T00:00:00.000Z', host: 'example.invalid' });

check('a NOT_PROVISIONED table is absent from the count map entirely',
  !('missing' in built) && built._not_provisioned.indexOf('missing') !== -1,
  built);
check('a COULD_NOT_COUNT table is absent from the count map entirely, with '
  + 'its reason kept',
  !('broken' in built) && 'broken' in built._could_not_count, built);
check('THE ARM THAT MATTERS: no table that failed is written as 0',
  built.missing !== 0 && built.broken !== 0
  && Object.keys(built).filter(function (k) { return k.charAt(0) !== '_'; })
      .every(function (k) { return k === 'good' || k === 'reallyEmpty'; }),
  built);
check('...and the one legitimate zero IS written, because an empty table that '
  + 'stays empty is a real comparison',
  built.reallyEmpty === 0, built.reallyEmpty);
check('_tables_counted matches what a reader would actually compare',
  built._tables_counted === B.tablesIn(built).length, built._tables_counted);

// ── 3. THE CHECKER'S OWN FILTER MUST SKIP EVERY META KEY ───────────────────
// restore_coherence_check.js does `Object.keys(baseline).filter(t =>
// !t.startsWith('_'))`. A metadata key without the underscore would be read as
// a table name and reported as a missing table on every run.
check('every metadata key is underscore-prefixed, so the checker\'s own '
  + 'filter drops it',
  Object.keys(built).filter(function (k) { return k.charAt(0) === '_'; }).length
    === Object.keys(built).length - B.tablesIn(built).length,
  Object.keys(built));
check('and the checker\'s filter, applied verbatim, yields exactly the '
  + 'counted tables',
  JSON.stringify(Object.keys(built).filter(function (t) {
    return !t.startsWith('_');
  }).sort()) === JSON.stringify(['good', 'reallyEmpty']),
  Object.keys(built).filter(function (t) { return !t.startsWith('_'); }));

// ── 4. IT WILL NOT REPLACE A GOOD BASELINE WITH A WORSE ONE ────────────────
const prev = { _schema: 'x', a: 1, b: 2, c: 3 };
check('a capture that covers FEWER tables reports exactly which it lost',
  JSON.stringify(B.coverageLost(prev, { a: 1, c: 3 })) === JSON.stringify(['b']),
  B.coverageLost(prev, { a: 1, c: 3 }));
check('a capture that covers the same or more loses nothing',
  B.coverageLost(prev, { a: 1, b: 2, c: 3, d: 4 }).length === 0);
check('NEGATIVE CONTROL: a changed COUNT is not a lost table -- the refusal is '
  + 'about coverage, and treating a count change as coverage loss would '
  + 'refuse every legitimate recapture',
  B.coverageLost(prev, { a: 999, b: 0, c: 3 }).length === 0,
  B.coverageLost(prev, { a: 999, b: 0, c: 3 }));
check('no previous baseline is not a loss', B.coverageLost(null, { a: 1 }).length === 0);

// ── 5. THE COUNT QUERY IS THE CHECKER'S QUERY ──────────────────────────────
// The one place a second implementation must NOT be an independent opinion:
// if the writer and the reader count differently, the comparison is
// apples-to-oranges while still producing a confident number.
const checkerSrc = fs.readFileSync(
  path.join(REPO, 'tools', 'restore_coherence_check.js'), 'utf8');
check('the writer builds the SAME count query the checker uses',
  checkerSrc.indexOf("'?select=id&limit=1'") !== -1
  && B.countQuery('t') === 't?select=id&limit=1',
  B.countQuery('t'));
check('...with the same count headers',
  checkerSrc.indexOf("Prefer: 'count=exact', Range: '0-0'") !== -1
  && B.countHeaders().Prefer === 'count=exact'
  && B.countHeaders().Range === '0-0',
  B.countHeaders());
check('...and the checker still parses the total off content-range the same '
  + 'way, so the two halves agree on what a count IS',
  checkerSrc.indexOf("cr.indexOf('/') + 1") !== -1, 'checker parse moved');

// ── 6. FAIL CLOSED WITH NO TARGET ──────────────────────────────────────────
const { execFileSync } = require('child_process');
let code = 0, out = '';
try {
  execFileSync(process.execPath, [path.join(REPO, 'tools', 'row_count_baseline.js')],
    { env: Object.assign({}, process.env, { SAIRN_BASELINE_URL: '', SAIRN_BASELINE_KEY: '' }),
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
} catch (e) {
  code = e.status; out = String(e.stderr || '') + String(e.stdout || '');
}
if (!code) {
  try {
    out = execFileSync(process.execPath,
      [path.join(REPO, 'tools', 'row_count_baseline.js')],
      { env: Object.assign({}, process.env, { SAIRN_BASELINE_URL: '', SAIRN_BASELINE_KEY: '' }),
        encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) { code = e.status; out = String(e.stderr || ''); }
}
check('with no target it exits 2 COULD NOT RUN -- never 0, and never writes',
  code === 2, { code: code, out: out.slice(0, 200) });
check('...and it says why the variable names differ from the checker\'s, '
  + 'because a baseline taken from the restore is the check that cannot fail',
  /cannot fail/.test(out), out.slice(0, 300));
check('no baseline file was created by any of the above',
  !fs.existsSync(path.join(REPO, 'db', 'row_count_baseline.json'))
  || fs.statSync(path.join(REPO, 'db', 'row_count_baseline.json')).size > 0);

console.log('');
if (fails.length) {
  console.log(fails.length + ' ARM(S) FAILED:');
  fails.forEach(function (f) { console.log('  - ' + f); });
  process.exitCode = 1;
} else {
  console.log('ALL ARMS PASS');
}
