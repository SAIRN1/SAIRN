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
// pass. ALL FOURTEEN are fixed, one to three at a time, deliberately: sweeping thirteen
// apps mechanically in one pass is what that backlog row warns against.
//
// THIRTEEN OF THE FOURTEEN ARE HERE. SAIRNvet's svLoad() is NOT, and that is not an
// omission: it has a different contract. That file carries a deliberate
// two-place unreadable-store guard, so a corrupt record there must BLOCK the
// app rather than return the default -- the opposite of what every assertion
// below requires. It has its own suite, tests/sv_storage_guard.js. Bending
// these assertions to cover both would have made them true of neither.
// The REMAINING count below is what keeps this suite honest about anything
// fixed elsewhere: it drops when anyone fixes one, whether or not it is
// driven here. SAIRNscape arrived that way and is now driven here too.
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
// `fn` is the loader's real name in that file. All but one are spelled `ld`;
// SAIRNscape's is `scpLd`, and hardcoding `ld` here is what would have let it
// join the list without ever being driven -- the app would have shown one
// fewer green section than there are entries, which reads as progress.
//
// ADDING AN ENTRY IS NOT THE SAME AS BEING COVERED, and that was learned here
// on 2026-09-04: a scripted edit inserted SAIRNdesign and SAIRNgrounds after
// an anchor that no longer existed, `String.replace` returned the string
// unchanged, and the suite went green at a HIGHER assertion count because
// another session had just added SAIRNscape. The count went up, the two new
// apps were never driven, and only a negative control caught it. Assert the
// anchor matched, and read the section headings in the output.
const APPS = [
  { file: 'sairnlaw.html', name: 'SAIRNlaw', fn: 'ld' },
  { file: 'sairnlegacy.html', name: 'SAIRNlegacy', fn: 'ld' },
  { file: 'sairnbiz.html', name: 'SAIRNbiz', fn: 'ld' },
  { file: 'sairncare.html', name: 'SAIRNcare', fn: 'ld' },
  { file: 'sairnfreedom.html', name: 'SAIRNfreedom', fn: 'ld' },
  { file: 'sairnscape.html', name: 'SAIRNscape', fn: 'scpLd' },
  { file: 'sairndesign.html', name: 'SAIRNdesign', fn: 'ld' },
  { file: 'sairngrounds.html', name: 'SAIRNgrounds', fn: 'ld' },
  { file: 'sairnbuild.html', name: 'SAIRNbuild', fn: 'ld' },
  { file: 'sairnsenior.html', name: 'SAIRNsenior', fn: 'ld' },
  { file: 'sairndental.html', name: 'SAIRNdental', fn: 'ld' },
  // StoneDesk's two spell their parameters differently, and itaLoad() spaces
  // its signature. `args`/`spaced` exist for exactly the reason `fn` does: a
  // suite that hardcodes the SIGNATURE cannot extract the function at all,
  // and one that hardcodes it in the SOURCE pattern passes vacuously instead.
  // Both are derived now.
  { file: 'stonedesk.html', name: 'StoneDesk', fn: 'sdLoad', args: ['k', 'def'] },
  { file: 'stonedesk.html', name: 'StoneDesk intake', fn: 'itaLoad', args: ['k', 'def'], spaced: true },
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
  const A = app.args || ['k', 'd'];
  const sig = app.spaced ? ('function ' + app.fn + '(' + A[0] + ', ' + A[1] + ') {')
                         : ('function ' + app.fn + '(' + A[0] + ',' + A[1] + '){');
  vm.runInContext(grab(src, sig), ctx);
  const ld = ctx[app.fn];
  assert.strictEqual(typeof ld, 'function', app.fn + ' did not define a function');
  return { ctx, errs, ld };
}

APPS.forEach((app) => {
  section(app.name);

  test('a healthy read returns the parsed value and says nothing', () => {
    const { errs, ld } = load(app, 'ok');
    assert.deepStrictEqual(ld('k', []), [1, 2]);
    assert.strictEqual(errs.length, 0, 'a working read logged an error');
  });

  test('a GENUINELY ABSENT key returns the default, silently -- that is not a defect', () => {
    // The honest empty case. Logging here would make the console useless on
    // first run, when every key is absent.
    const { errs, ld } = load(app, 'absent');
    assert.deepStrictEqual(ld('k', []), []);
    assert.strictEqual(errs.length, 0, 'a first-run read logged an error');
  });

  test('AN UNREADABLE RECORD STILL RETURNS THE DEFAULT -- no caller can break', () => {
    const { ld } = load(app, 'corrupt');
    assert.deepStrictEqual(ld('k', []), [], 'the return contract changed');
    assert.deepStrictEqual(ld('k', { a: 1 }), { a: 1 }, 'a non-array default changed');
  });

  test('...but it is now LOGGED, and says it is not the same as empty', () => {
    const { errs, ld } = load(app, 'corrupt');
    ld('law_matters', []);
    assert.strictEqual(errs.length, 1, 'the unreadable record was not logged exactly once');
    assert.match(errs[0], new RegExp(app.name + ': stored record'));
    assert.match(errs[0], /law_matters/, 'the log does not name the key');
    assert.match(errs[0], /UNREADABLE/);
    assert.match(errs[0], /NOT an empty record/,
      'the log does not distinguish corrupt from empty, which is the entire point');
  });

  test('THE LOG SAYS THE DATA IS STILL THERE, because the next question is "did I lose it"', () => {
    const { errs, ld } = load(app, 'corrupt');
    ld('k', []);
    assert.match(errs[0], /has not been overwritten/,
      'the log does not say the stored data survived, which invites a panic or a wipe');
  });

  test('AN UNAVAILABLE STORE IS A DIFFERENT MESSAGE FROM A CORRUPT RECORD', () => {
    // A disabled or partitioned store and an unparseable value need different
    // fixes, so they must not read the same -- the same distinction the st()
    // fix makes between a quota error and everything else.
    const { errs, ld } = load(app, 'throws');
    assert.deepStrictEqual(ld('k', []), []);
    assert.strictEqual(errs.length, 1);
    assert.match(errs[0], /localStorage is unavailable/);
    assert.ok(!/UNREADABLE/.test(errs[0]), 'an unavailable store was reported as a corrupt record');
  });

  test('ld() still never throws', () => {
    ['ok', 'absent', 'corrupt', 'throws'].forEach((mode) => {
      const { ld } = load(app, mode);
      assert.doesNotThrow(() => ld('k', []), mode + ' threw');
    });
  });

  test('AN EMPTY STRING IS AN UNREADABLE RECORD, NOT AN ABSENT ONE', () => {
    // st() JSON.stringify()s and can never write '', so an empty string in the
    // store did not come from the app. SAIRNbiz is the reason this assertion
    // exists: its loader tested `r ? ... : d` -- truthiness, not `r === null`
    // like every other copy -- so '' took the absent branch SILENTLY. Same
    // return either way; only the silence changed.
    const { errs, ld } = load(app, 'ok', '');
    assert.deepStrictEqual(ld('k', []), []);
    assert.strictEqual(errs.length, 1, 'an empty stored value was not reported');
    assert.match(errs[0], /UNREADABLE/);
  });

  test('the silent one-liner is gone from the source, not merely bypassed', () => {
    const src = fs.readFileSync(path.join(ROOT, app.file), 'utf8')
      .replace(/\/\/[^\n]*/g, '');   // the new comment quotes the old code
    // WHITESPACE IS STRIPPED FIRST, and that is not tidiness. This assertion
    // has now been vacuous TWICE for exactly the reason it is written to
    // catch. First it tested only `r === null ? d : JSON.parse(r)`, so
    // SAIRNbiz -- which wrote `r ? JSON.parse(r) : d` -- passed it whether or
    // not anything was fixed. Then the truthiness spelling was added as a
    // second literal, and SAIRNfreedom passed THAT vacuously too, because its
    // copy of the same line carried spaces:
    //
    //     function ld(k,d){ try{ var r=localStorage.getItem(k); ... } }
    //
    // Two literals cannot keep up with formatting. Normalising kills the whole
    // class -- a reformatted return of the defect is still the defect.
    //
    // THE NAME IS PARAMETERISED for the same reason the whitespace is stripped.
    // A pattern hardcoding `functionld` is vacuously true of SAIRNscape, whose
    // loader is `scpLd` -- it would have passed with the defect fully intact.
    // A third literal is not the fix; deriving it from app.fn is.
    const bare = src.replace(/\s+/g, '');
    // THE PARAMETER NAMES ARE DERIVED for the same reason the function name is.
    // StoneDesk's loaders take (k,def); a pattern hardcoding (k,d) is vacuously
    // true of them and would pass with the defect fully intact -- the third
    // time this one assertion has had to stop being a literal.
    const P = app.args || ['k', 'd'];
    const head = 'function' + app.fn + '\\(' + P[0] + ',' + P[1] +
                 '\\)\\{try\\{var' + P[0] + '=localStorage\\.getItem\\(' + P[0] + '\\);';
    const nul = 'return' + P[0] + '===null\\?' + P[1] + ':JSON\\.parse\\(' + P[0] +
                '\\);\\}catch\\(e\\)\\{return' + P[1] + ';\\}\\}';
    const tru = 'return' + P[0] + '\\?JSON\\.parse\\(' + P[0] + '\\):' + P[1] +
                ';\\}catch\\(e\\)\\{return' + P[1] + ';\\}\\}';
    assert.ok(!new RegExp(head + nul).test(bare), 'the swallowing one-liner is back');
    assert.ok(!new RegExp(head + tru).test(bare),
      'the swallowing one-liner is back, in its truthiness spelling');
    // ...and the pattern is not vacuous: it must match the defect it names,
    // rebuilt from this app's OWN name and parameters.
    assert.ok(new RegExp(head + tru)
      .test(('function ' + app.fn + '(' + P[0] + ',' + P[1] + '){try{var ' + P[0] +
             '=localStorage.getItem(' + P[0] + ');return ' + P[0] + '?JSON.parse(' + P[0] +
             '):' + P[1] + ';}catch(e){return ' + P[1] + ';}}').replace(/\s+/g, '')),
      'the negative control does not match, so the assertion above proves nothing');
  });
});

// ---------------------------------------------------------------------------
section('the checker agrees ALL FOURTEEN are done');

const REMAINING = 0;   // of the original 14 -- the row is CLOSED

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

test('...and NONE are left on the list -- the count is now the regression guard', () => {
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
