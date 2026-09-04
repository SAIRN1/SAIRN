// tests/st_reports_failure.js
//
// Run:  node tests/st_reports_failure.js
//
// SAIRNdesign, SAIRNlaw and SAIRNlegacy each had
//
//     function st(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
//
// a bare empty catch, so a full disk was swallowed whole: the save appeared to
// succeed, the screen kept rendering whatever ld() returned, and nothing said
// otherwise. Same defect and same fix as SAIRNdental's st() (75b9c07), which
// was found the hard way -- a real sync pulled data off the server, dropped it,
// and the app said "Refreshed from server".
//
// THE REAL FUNCTIONS ARE DRIVEN, not a copy of them. Each app's st() and its
// quota helper are extracted from the HTML and run against a fake localStorage
// that can be told to be full. A reimplementation here would test the
// reimplementation.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const APPS = [
  { file: 'sairndesign.html', name: 'SAIRNdesign', prefix: 'dsn' },
  { file: 'sairnlaw.html', name: 'SAIRNlaw', prefix: 'law' },
  { file: 'sairnlegacy.html', name: 'SAIRNlegacy', prefix: 'lgy' },
  // Added 2026-09-04. These two already RETURNED a boolean, so they were never
  // on the swallowing-catch list -- and all 28 / 78 call sites respectively
  // ignore that boolean, and the catch logged nothing. A refused write
  // produced a `false` no code read and no console recorded.
  { file: 'sairncare.html', name: 'SAIRNcare', prefix: 'care' },
  { file: 'sairnfreedom.html', name: 'SAIRNfreedom', prefix: 'free' },
  // Added 2026-09-04 (Cody) -- the last three on the open-work row's list.
  // Measured per file rather than assumed from the siblings: sairnsenior's st()
  // has 32 call sites and ALL 32 ignore the return; sairnbuild's has 86 with 44
  // ignoring; stonedesk's has 101 with 24, plus stRaw()'s 22 with 19.
  //
  // They are not the same animal, which is why this harness grew two optional
  // fields rather than three copies of itself:
  //   * sairnbuild's st() takes (k,v) like the others but carries a
  //     server-backup hook and its own okWrite flag, so the catch had a log
  //     added rather than being restructured;
  //   * stonedesk's is `st(key,data)` and DELEGATES its message to a shared
  //     sdStorageFailed(), because st() and stRaw() must not carry two copies
  //     of the same wording.
  { file: 'sairnsenior.html', name: 'SAIRNsenior', prefix: 'sen' },
  { file: 'sairnbuild.html', name: 'SAIRNbuild', prefix: 'bld', bareCatches: 2 },
  { file: 'stonedesk.html', name: 'StoneDesk', prefix: 'sd',
    sig: 'function st(key,data){', extra: ['function sdStorageFailed(key,e){'],
    bareCatches: 0 },
];

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// BRACE-MATCHED, not "search for a newline followed by }" (2026-09-04). The
// original shape only terminated a multi-line function; StoneDesk's st() and
// stRaw() are one-liners, so the old version ran past the closing brace and
// swept in `window.st=st;`, which fails in a bare VM with "window is not
// defined". A slicer that depends on the formatting of the thing it slices
// fails on correct code, which is how a fixture teaches you to edit the test.
function grab(src, sig) {
  const i = src.indexOf(sig);
  assert.ok(i > 0, sig + ' not found');
  const open = src.indexOf('{', i);
  assert.ok(open > 0, sig + ' has no body');
  let depth = 0;
  for (let j = open; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') { depth--; if (depth === 0) return src.slice(i, j + 1); }
  }
  throw new assert.AssertionError({ message: sig + ' is not terminated' });
}

// A localStorage that can be told to fail, in each of the ways a browser
// actually spells "full" -- the helper checks three because they disagree.
function fakeStore(mode) {
  return {
    _d: {},
    setItem(k, v) {
      if (mode === 'quota-name') { const e = new Error('full'); e.name = 'QuotaExceededError'; throw e; }
      if (mode === 'quota-firefox') { const e = new Error('full'); e.name = 'NS_ERROR_DOM_QUOTA_REACHED'; throw e; }
      if (mode === 'quota-code') { const e = new Error('full'); e.name = 'Whatever'; e.code = 22; throw e; }
      if (mode === 'quota-code1014') { const e = new Error('full'); e.name = 'Whatever'; e.code = 1014; throw e; }
      if (mode === 'security') { const e = new Error('denied'); e.name = 'SecurityError'; throw e; }
      this._d[k] = v;
    },
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
  };
}

function load(app, mode) {
  const src = fs.readFileSync(path.join(ROOT, app.file), 'utf8');
  const errs = [];
  const ctx = {
    localStorage: fakeStore(mode),
    JSON: JSON, String: String, Number: Number,
    console: { error: (...a) => errs.push(a.join(' ')), warn: () => {}, log: () => {} },
  };
  vm.createContext(ctx);
  vm.runInContext(grab(src, 'function ' + app.prefix + 'IsQuotaError(e){'), ctx);
  // Some wrappers delegate the message to a named helper rather than inlining
  // it -- StoneDesk's st() and stRaw() share one, so that they cannot drift
  // into two wordings. The helper is loaded first so the wrapper can reach it.
  (app.extra || []).forEach((sig) => vm.runInContext(grab(src, sig), ctx));
  vm.runInContext(grab(src, app.sig || 'function st(k,v){'), ctx);
  return { ctx, errs };
}

APPS.forEach((app) => {
  section(app.name);

  test('a healthy write returns true and actually stores', () => {
    const { ctx, errs } = load(app, 'ok');
    assert.strictEqual(ctx.st('k', { a: 1 }), true);
    assert.strictEqual(ctx.localStorage.getItem('k'), '{"a":1}');
    assert.strictEqual(errs.length, 0, 'a working save logged an error');
  });

  test('A FULL DISK RETURNS FALSE -- it used to return undefined and say nothing', () => {
    const { ctx } = load(app, 'quota-name');
    assert.strictEqual(ctx.st('k', { a: 1 }), false);
  });

  test('...and is ALWAYS logged, naming the key and the cause', () => {
    const { ctx, errs } = load(app, 'quota-name');
    ctx.st('dsn_widgets', { a: 1 });
    assert.strictEqual(errs.length, 1, 'the failure was not logged exactly once');
    assert.match(errs[0], new RegExp(app.name + ': localStorage write FAILED'));
    assert.match(errs[0], /dsn_widgets/, 'the log does not name the key that was lost');
    assert.match(errs[0], /storage is FULL/, 'a quota error was not identified as one');
    assert.match(errs[0], /Nothing was saved/);
  });

  test('all four spellings of "full" are recognised, not just this browser\'s', () => {
    ['quota-name', 'quota-firefox', 'quota-code', 'quota-code1014'].forEach((mode) => {
      const { ctx, errs } = load(app, mode);
      assert.strictEqual(ctx.st('k', 1), false, mode + ' did not fail');
      assert.match(errs[0], /storage is FULL/, mode + ' was not recognised as a quota error');
    });
  });

  test('A NON-QUOTA FAILURE IS NOT BLAMED ON THE QUOTA', () => {
    // Sending someone to delete their data because of a SecurityError would be
    // its own damage -- the same distinction the SAIRNdental fix carries.
    const { ctx, errs } = load(app, 'security');
    assert.strictEqual(ctx.st('k', 1), false);
    assert.ok(!/storage is FULL/.test(errs[0]), 'a SecurityError was reported as a full disk');
    assert.match(errs[0], /denied/, 'the real reason was not passed through');
  });

  test('st() STILL NEVER THROWS, so no existing caller can break', () => {
    const { ctx } = load(app, 'quota-name');
    assert.doesNotThrow(() => ctx.st('k', 1));
    // An unserialisable value throws inside JSON.stringify, before storage is
    // reached -- that path must be caught too.
    const { ctx: c2 } = load(app, 'ok');
    const cyc = {}; cyc.self = cyc;
    assert.doesNotThrow(() => c2.st('k', cyc));
    assert.strictEqual(c2.st('k', cyc), false, 'an unserialisable value reported success');
  });

  test('the silent one-liner is gone from the source, not merely bypassed', () => {
    const src = fs.readFileSync(path.join(ROOT, app.file), 'utf8')
      .replace(/\/\/[^\n]*/g, '');   // the new comment quotes the old code
    // BOTH pre-fix spellings, because they were not the same across the apps.
    // Three had an empty catch; SAIRNcare and SAIRNfreedom returned FALSE and
    // logged nothing, which is why they were never on the swallowing-catch
    // list at all. Asserting only the first spelling passes those two
    // VACUOUSLY -- it would go green whether or not anything was fixed.
    //
    // WHITESPACE IS STRIPPED FIRST, and that is not tidiness. The ld() suite
    // learned this the expensive way: it added a second literal for the second
    // spelling, and then a THIRD app passed that one vacuously too, because
    // its copy of the identical line simply carried spaces. Literals cannot
    // keep up with formatting; a reformatted return of the defect is still the
    // defect.
    const squashed = src.replace(/\s+/g, '');
    assert.ok(!/functionst\(k,v\)\{try\{localStorage\.setItem\(k,JSON\.stringify\(v\)\);\}catch\(e\)\{\}\}/.test(squashed),
      'the swallowing one-liner is back');
    assert.ok(!/functionst\(k,v\)\{try\{localStorage\.setItem\(k,JSON\.stringify\(v\)\);returntrue;\}catch\(e\)\{returnfalse;\}\}/.test(squashed),
      'the silent return-false one-liner is back: false to nobody, and nothing logged');
    const bare = src.match(/catch\s*\([A-Za-z_$][\w$]*\)\s*\{\s*\}/g) || [];
    // `catch(_e){}` around the console.error itself is deliberate and is the
    // only one allowed inside st(): a logger that throws must not turn a failed
    // save into an exception.
    // Bound this to st() ITSELF, not to a fixed character window. It used to
    // be `slice(i, i + 700)`, which reached past st()'s closing brace into
    // whatever happened to follow it -- and when ld() was given its own
    // logger guards directly below st() in sairnlaw/sairnlegacy, this test
    // went red while st() was untouched. A fixture that fails on a NEIGHBOUR's
    // correct code is worse than no fixture: it trains you to edit the test.
    const stBody = grab(src, app.sig || 'function st(k,v){');
    const bareInSt = stBody.match(/catch\s*\([A-Za-z_$][\w$]*\)\s*\{\s*\}/g) || [];
    // Per-app because the wrappers are genuinely different, not because the
    // rule is soft. A count ABOVE the app's number still fails, so a new
    // silent catch cannot be added to any of them:
    //   * default 1 -- the logger guard inside st() itself;
    //   * SAIRNbuild 2 -- plus `catch(e){}` around bldSyncCollection(). That
    //     one is deliberate and pre-dates this work: a server-backup hook that
    //     throws must not turn a SUCCESSFUL local write into a failure. It is
    //     named here rather than waved through by a loosened count;
    //   * StoneDesk 0 -- its st() delegates to sdStorageFailed(), so the
    //     logger guard lives in the helper, which is where it is asserted.
    const expectBare = ('bareCatches' in app) ? app.bareCatches : 1;
    assert.strictEqual(bareInSt.length, expectBare,
      'expected exactly ' + expectBare + ' bare catch(es) in the wrapper -- got ' + bareInSt.length);
    // The logger guard must exist SOMEWHERE on the path that logs: a logger
    // that throws must not turn a failed save into an exception.
    const guardBody = (app.extra && app.extra.length) ? grab(src, app.extra[0]) : stBody;
    assert.match(guardBody, /catch\(_e\)\{\}/, 'the logger guard is missing');
    void bare;
  });
});

// ---------------------------------------------------------------------------
section('the fix is the same one across the platform');

test('all of them log in the same shape, so a reader learns it once', () => {
  APPS.forEach((app) => {
    const src = fs.readFileSync(path.join(ROOT, app.file), 'utf8');
    assert.ok(src.indexOf(app.name + ': localStorage write FAILED for "') !== -1,
      app.file + ' logs in a different shape');
  });
});

test('and SAIRNdental, the original, still does too', () => {
  const src = fs.readFileSync(path.join(ROOT, 'sairndental.html'), 'utf8');
  assert.ok(src.indexOf('SAIRNdental: localStorage write FAILED for "') !== -1,
    'the reference implementation changed shape -- the four have drifted apart');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' st() ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
