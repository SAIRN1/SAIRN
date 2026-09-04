// tests/ld_reports_unreadable.js
//
// Run:  node tests/ld_reports_unreadable.js
//
// Every SAIRN app's storage loader was
//
//     function ld(k,d){try{var r=localStorage.getItem(k);
//                          return r===null?d:JSON.parse(r);}catch(e){return d;}}
//
// so a record that will not parse returned exactly what a key that was never
// written returns. "Your data is corrupt" and "you have none yet" rendered
// identically, and neither the user nor the console was told which happened.
// Where the default is a seeded value rather than `[]` it renders as invented
// content -- the StoneDesk SEED-fallback shape in Guardian's lesson 6.
//
// Fourteen such loaders were enumerated by tools/fail_open_check.py's browser
// pass. FOUR are fixed here, two at a time, deliberately: sweeping thirteen
// apps mechanically in one pass is what that backlog row warns against.
//
// THE REAL FUNCTIONS ARE DRIVEN against a fake localStorage. The whole point is
// that the RETURN VALUE is unchanged and only the silence is fixed, and a
// reimplementation could not prove that.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const APPS = [
  { file: 'sairnlaw.html', name: 'SAIRNlaw' },
  { file: 'sairnlegacy.html', name: 'SAIRNlegacy' },
  { file: 'sairnbiz.html', name: 'SAIRNbiz' },
  { file: 'sairncare.html', name: 'SAIRNcare' },
];

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

function grab(src, sig) {
  const i = src.indexOf(sig);
  assert.ok(i > 0, sig + ' not found');
  const rel = src.slice(i).search(/\r?\n\}/);
  assert.ok(rel > 0, sig + ' is not terminated');
  return src.slice(i, i + rel) + '\n}';
}

// mode: 'ok' | 'corrupt' | 'absent' | 'throws'
function load(app, mode, stored) {
  const src = fs.readFileSync(path.join(ROOT, app.file), 'utf8');
  const errs = [];
  const ctx = {
    JSON: JSON, String: String,
    localStorage: {
      getItem(k) {
        if (mode === 'throws') { const e = new Error('storage disabled'); e.name = 'SecurityError'; throw e; }
        if (mode === 'absent') return null;
        if (mode === 'corrupt') return '{not json at all';
        return stored === undefined ? '[1,2]' : stored;
      },
    },
    console: { error: (...a) => errs.push(a.join(' ')), warn: () => {}, log: () => {} },
  };
  vm.createContext(ctx);
  vm.runInContext(grab(src, 'function ld(k,d){'), ctx);
  return { ctx, errs };
}

APPS.forEach((app) => {
  section(app.name);

  test('a healthy read returns the parsed value and says nothing', () => {
    const { ctx, errs } = load(app, 'ok');
    assert.deepStrictEqual(ctx.ld('k', []), [1, 2]);
    assert.strictEqual(errs.length, 0, 'a working read logged an error');
  });

  test('a GENUINELY ABSENT key returns the default, silently -- that is not a defect', () => {
    // The honest empty case. Logging here would make the console useless on
    // first run, when every key is absent.
    const { ctx, errs } = load(app, 'absent');
    assert.deepStrictEqual(ctx.ld('k', []), []);
    assert.strictEqual(errs.length, 0, 'a first-run read logged an error');
  });

  test('AN UNREADABLE RECORD STILL RETURNS THE DEFAULT -- no caller can break', () => {
    const { ctx } = load(app, 'corrupt');
    assert.deepStrictEqual(ctx.ld('k', []), [], 'the return contract changed');
    assert.deepStrictEqual(ctx.ld('k', { a: 1 }), { a: 1 }, 'a non-array default changed');
  });

  test('...but it is now LOGGED, and says it is not the same as empty', () => {
    const { ctx, errs } = load(app, 'corrupt');
    ctx.ld('law_matters', []);
    assert.strictEqual(errs.length, 1, 'the unreadable record was not logged exactly once');
    assert.match(errs[0], new RegExp(app.name + ': stored record'));
    assert.match(errs[0], /law_matters/, 'the log does not name the key');
    assert.match(errs[0], /UNREADABLE/);
    assert.match(errs[0], /NOT an empty record/,
      'the log does not distinguish corrupt from empty, which is the entire point');
  });

  test('THE LOG SAYS THE DATA IS STILL THERE, because the next question is "did I lose it"', () => {
    const { ctx, errs } = load(app, 'corrupt');
    ctx.ld('k', []);
    assert.match(errs[0], /has not been overwritten/,
      'the log does not say the stored data survived, which invites a panic or a wipe');
  });

  test('AN UNAVAILABLE STORE IS A DIFFERENT MESSAGE FROM A CORRUPT RECORD', () => {
    // A disabled or partitioned store and an unparseable value need different
    // fixes, so they must not read the same -- the same distinction the st()
    // fix makes between a quota error and everything else.
    const { ctx, errs } = load(app, 'throws');
    assert.deepStrictEqual(ctx.ld('k', []), []);
    assert.strictEqual(errs.length, 1);
    assert.match(errs[0], /localStorage is unavailable/);
    assert.ok(!/UNREADABLE/.test(errs[0]), 'an unavailable store was reported as a corrupt record');
  });

  test('ld() still never throws', () => {
    ['ok', 'absent', 'corrupt', 'throws'].forEach((mode) => {
      const { ctx } = load(app, mode);
      assert.doesNotThrow(() => ctx.ld('k', []), mode + ' threw');
    });
  });

  test('AN EMPTY STRING IS AN UNREADABLE RECORD, NOT AN ABSENT ONE', () => {
    // st() JSON.stringify()s and can never write '', so an empty string in the
    // store did not come from the app. SAIRNbiz is the reason this assertion
    // exists: its loader tested `r ? ... : d` -- truthiness, not `r === null`
    // like every other copy -- so '' took the absent branch SILENTLY. Same
    // return either way; only the silence changed.
    const { ctx, errs } = load(app, 'ok', '');
    assert.deepStrictEqual(ctx.ld('k', []), []);
    assert.strictEqual(errs.length, 1, 'an empty stored value was not reported');
    assert.match(errs[0], /UNREADABLE/);
  });

  test('the silent one-liner is gone from the source, not merely bypassed', () => {
    const src = fs.readFileSync(path.join(ROOT, app.file), 'utf8')
      .replace(/\/\/[^\n]*/g, '');   // the new comment quotes the old code
    // BOTH shapes, because they were not identical across the apps: eleven
    // wrote `r === null ? d : JSON.parse(r)` and SAIRNbiz wrote
    // `r ? JSON.parse(r) : d`. A regex for only the first passes SAIRNbiz
    // vacuously -- it would have gone green whether or not anything was fixed.
    assert.ok(!/function ld\(k,d\)\{try\{var r=localStorage\.getItem\(k\);return r===null\?d:JSON\.parse\(r\);\}catch\(e\)\{return d;\}\}/.test(src),
      'the swallowing one-liner is back');
    assert.ok(!/function ld\(k,d\)\{try\{var r=localStorage\.getItem\(k\);return r\?JSON\.parse\(r\):d;\}catch\(e\)\{return d;\}\}/.test(src),
      'the swallowing one-liner is back, in its truthiness spelling');
  });
});

// ---------------------------------------------------------------------------
section('the checker agrees these four are done');

const REMAINING = 10;   // of the original 14

function checkerOutput() {
  const { execFileSync } = require('child_process');
  try {
    return execFileSync('python', [path.join(ROOT, 'tools', 'fail_open_check.py')],
      { cwd: ROOT, encoding: 'utf8' });
  } catch (e) {
    return e.stdout || '';
  }
}

test('fail_open_check no longer lists any of them', () => {
  const out = checkerOutput();
  const start = out.indexOf('BROWSER-SIDE');
  assert.ok(start > 0, 'the browser-side section is missing from the tool output');
  const listed = out.slice(start);
  APPS.forEach((app) => {
    assert.ok(listed.indexOf(app.file) === -1, app.name + ' is still listed as silent');
  });
});

test('...and the other ten are still on the list, not quietly dropped', () => {
  const m = /\((\d+) storage loader\(s\)/.exec(checkerOutput());
  assert.ok(m, 'could not read the loader count');
  assert.strictEqual(Number(m[1]), REMAINING,
    'expected ' + REMAINING + ' remaining of the original 14 -- got ' + m[1] +
    '. If others were fixed, update this number; if it grew, a new app copied the shape.');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' ld() ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
