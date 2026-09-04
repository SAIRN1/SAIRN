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
  vm.runInContext(grab(src, 'function st(k,v){'), ctx);
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

  test('the empty catch is gone from the source, not merely bypassed', () => {
    const src = fs.readFileSync(path.join(ROOT, app.file), 'utf8')
      .replace(/\/\/[^\n]*/g, '');   // the new comment quotes the old code
    assert.ok(!/function st\(k,v\)\{try\{localStorage\.setItem\(k,JSON\.stringify\(v\)\);\}catch\(e\)\{\}\}/.test(src),
      'the swallowing one-liner is back');
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
    const stBody = grab(src, 'function st(k,v){');
    const bareInSt = stBody.match(/catch\s*\([A-Za-z_$][\w$]*\)\s*\{\s*\}/g) || [];
    assert.strictEqual(bareInSt.length, 1,
      'expected exactly one bare catch in st() -- the one guarding console.error -- got ' + bareInSt.length);
    assert.match(stBody, /catch\(_e\)\{\}/, 'the allowed bare catch is not the logger guard');
    void bare;
  });
});

// ---------------------------------------------------------------------------
section('the fix is the same one across the platform');

test('all three log in the same shape, so a reader learns it once', () => {
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
