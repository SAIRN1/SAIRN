// tests/discarded_verdict_check.test.js
//
// Run:  node tests/discarded_verdict_check.test.js
//
// Guards tools/discarded_verdict_check.py, which finds the shape that turned up
// three times in one session on 2026-09-04: a function whose whole purpose is
// to say NO is called, and its answer is never consulted.
//
// A detector that has never been red is not known to be a detector, so the
// first assertion here runs it against the REAL pre-fix source of
// api/_lib/courtlistener.js, pulled out of git rather than retyped. It found
// all four sites at the right lines; if it stops doing that, this fails.

'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const { execFileSync, execFileSync: run } = require('child_process');

const ROOT = path.join(__dirname, '..');
const TOOL = path.join(ROOT, 'tools', 'discarded_verdict_check.py');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// The tool exits 1 when it has something to report, so a non-zero status is a
// finding rather than a crash. Distinguished by whether stdout parsed.
function check(relPaths) {
  try {
    return { code: 0, out: run('python', [TOOL].concat(relPaths), { cwd: ROOT, encoding: 'utf8' }) };
  } catch (e) {
    if (e.stdout && e.stdout.indexOf('discarded verdicts found:') !== -1) {
      return { code: e.status, out: e.stdout };
    }
    throw new Error('the tool did not run: ' + (e.stderr || e.message));
  }
}

function found(out) {
  const m = /discarded verdicts found: (\d+)\s+\(to read (\d+)/.exec(out);
  assert.ok(m, 'could not parse the tool output:\n' + out);
  return { total: Number(m[1]), live: Number(m[2]) };
}

// Writes a fixture into api/_lib so the tool's default roots see it, and
// removes it afterwards whatever happens.
function withFixture(name, source, fn) {
  const p = path.join(ROOT, 'api', '_lib', name);
  fs.writeFileSync(p, source);
  try { return fn(path.posix.join('api/_lib', name)); }
  finally { if (fs.existsSync(p)) fs.unlinkSync(p); }
}

// ---------------------------------------------------------------------------
section('IT GOES RED ON THE REAL PRE-FIX SOURCE');

test('the four discarded checkAndLogRateLimit() calls are found', () => {
  // Pulled from git, not retyped: a detector proven against a hand-written
  // imitation of a bug is proven against the imitation.
  const sha = execFileSync('git',
    ['log', '--format=%H', '-1', '--grep=the CourtListener limiter raced'],
    { cwd: ROOT, encoding: 'utf8' }).trim();
  assert.ok(/^[0-9a-f]{40}$/.test(sha), 'could not locate the courtlistener fix commit');
  const before = execFileSync('git', ['show', sha + '^:api/_lib/courtlistener.js'],
    { cwd: ROOT, encoding: 'utf8' });
  assert.ok(before.indexOf('await checkAndLogRateLimit();') !== -1,
    'the pre-fix source does not contain the defect -- wrong commit');

  withFixture('zz_dv_prefix.js', before, (rel) => {
    const r = check([rel]);
    const n = found(r.out);
    assert.strictEqual(n.live, 4,
      'expected all four discarded call sites, got ' + n.live + '\n' + r.out);
    assert.match(r.out, /checkAndLogRateLimit\(\)\s+returns \{limited: \.\.\.\}/);
    assert.strictEqual(r.code, 1, 'a finding must exit non-zero');
  });
});

test('...and GREEN on the same file after the fix', () => {
  const r = check(['api/_lib/courtlistener.js']);
  assert.strictEqual(found(r.out).live, 0,
    'the fixed file still reports a discarded verdict:\n' + r.out);
  assert.strictEqual(r.code, 0);
});

// ---------------------------------------------------------------------------
section('what it does and does not call a finding');

test('a verdict that IS read is not reported', () => {
  const src = [
    'async function mayI() { return { allowed: false }; }',
    'async function go() {',
    '  const v = await mayI();',
    '  if (!v.allowed) return;',
    '}',
    'module.exports = { go };',
  ].join('\n');
  withFixture('zz_dv_ok.js', src, (rel) => {
    assert.strictEqual(found(check([rel]).out).live, 0);
  });
});

test('a verdict that is DISCARDED is reported', () => {
  const src = [
    'async function mayI() { return { allowed: false }; }',
    'async function go() {',
    '  await mayI();',
    '  return 1;',
    '}',
    'module.exports = { go };',
  ].join('\n');
  withFixture('zz_dv_bad.js', src, (rel) => {
    const r = check([rel]);
    assert.strictEqual(found(r.out).live, 1);
    assert.match(r.out, /mayI\(\)\s+returns \{allowed: \.\.\.\}/);
  });
});

test('a function that returns NOTHING is not a discarded verdict', () => {
  // Otherwise every void call in the codebase is a finding and the tool gets
  // ignored, which is how a check dies.
  const src = [
    'async function logIt() { console.log("x"); }',
    'async function go() { await logIt(); }',
    'module.exports = { go };',
  ].join('\n');
  withFixture('zz_dv_void.js', src, (rel) => {
    assert.strictEqual(found(check([rel]).out).live, 0);
  });
});

test('a returned value with no verdict-shaped key is not a finding', () => {
  const src = [
    'async function loadRows() { return { rows: [], count: 0 }; }',
    'async function go() { await loadRows(); }',
    'module.exports = { go };',
  ].join('\n');
  withFixture('zz_dv_data.js', src, (rel) => {
    assert.strictEqual(found(check([rel]).out).live, 0);
  });
});

test('THE DEFECT INSIDE A COMMENT IS NOT A FINDING', () => {
  // Four assertions in this repo have matched their own documentation today.
  // The tool strips comments; this is the arm that keeps it that way.
  // The commented occurrence has to be one a line-anchored regex WOULD match
  // if comments were not stripped -- i.e. `await` at the start of a line
  // INSIDE a block comment. A first version put it after `// ` on the same
  // line, where `^\s*await` never matches either way, so the arm passed
  // whether stripping happened or not. A negative control caught that.
  const src = [
    '/*',
    '  await mayI();     <- this is what the bug looked like',
    '*/',
    'async function mayI() { return { allowed: false }; }',
    'async function go() { const v = await mayI(); if (!v.allowed) return; }',
    'module.exports = { go };',
  ].join('\n');
  withFixture('zz_dv_comment.js', src, (rel) => {
    assert.strictEqual(found(check([rel]).out).live, 0);
  });
});

// ---------------------------------------------------------------------------
section('the tool is honest about its own limits');

test('it states the cross-file blind spot on every run', () => {
  const r = check(['api/_lib/courtlistener.js']);
  assert.match(r.out, /cannot see across files/,
    'the tool no longer discloses that a verdict dropped in another file is missed');
});

test('the whole tree is currently clean, which is a fact about today', () => {
  // If this goes red, something reintroduced the shape -- or the tool learned
  // to see further. Either is worth reading rather than silencing.
  const r = check([]);
  assert.strictEqual(found(r.out).live, 0, r.out);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' DISCARDED-VERDICT ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
