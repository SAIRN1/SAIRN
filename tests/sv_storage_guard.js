// tests/sv_storage_guard.js
//
// Run:  node tests/sv_storage_guard.js
//
// SAIRNvet's storage layer is NOT the platform's standard st()/ld() pair and
// must not be tested as if it were. It carries a deliberate two-place
// unreadable-store guard -- st() refuses to overwrite a corrupted value, and
// svIntegrityScan() blocks the whole app at boot -- built because "sample data
// presented as a real record -- a controlled-substance log, a patient list --
// is worse than a clinic that cannot start."
//
// WHAT THIS FILE PINS, and both were found by reading that guard rather than
// by pattern-matching the other apps:
//
//   1. st()'s OUTER catch was silent. It already returned false, which is why
//      this file never appeared on the swallowing-catch list -- but of 176
//      saveX() call sites, 171 DISCARD the boolean. A quota failure produced a
//      false no code read and no console recorded.
//
//   2. svLoad() ENTERED NEITHER HALF of the guard. The 39 get*() collections
//      are covered by both: a mid-session parse failure falls through to seed,
//      calls saveX(seed), enters st(), and is blocked before the render
//      returns. svLoad() never calls st(), so nothing tripped -- it returned
//      the caller's default in silence. Its four call sites are pc_identity,
//      license, auth and ROLE, so a corrupted sv_role did not read as
//      "unreadable", it read as **Doctor**.
//
// THE REAL FUNCTIONS ARE DRIVEN against a fake localStorage and a fake DOM.
// The claim being tested is that the guard is now entered from the read side
// too, and a reimplementation could not prove that.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const FILE = 'sairnvet.html';

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

// store: a map of key -> raw string. mode shapes how getItem/setItem misbehave.
function load(opts) {
  opts = opts || {};
  const src = fs.readFileSync(path.join(ROOT, FILE), 'utf8');
  const errs = [];
  const blocked = [];
  const store = Object.assign({}, opts.store);
  const toastEl = { textContent: '', className: '', classList: { remove: () => {} } };
  const ctx = {
    JSON: JSON, String: String, Object: Object, Array: Array,
    _svUnreadable: {}, _svKeyVerified: {}, _svWriteFailed: null,
    setTimeout: () => 0, clearTimeout: () => {},
    escHtml: (s) => String(s),
    // svBlockForCorruptStore is the REAL one unless a caller asks for a stub;
    // the real one writes document.body.innerHTML, so a fake DOM is enough.
    document: {
      body: { innerHTML: '' }, title: '',
      getElementById: (id) => (id === 'sv-toast' ? toastEl : null),
    },
    localStorage: {
      getItem(k) {
        if (opts.getThrows) { const e = new Error('storage disabled'); e.name = 'SecurityError'; throw e; }
        return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null;
      },
      setItem(k, v) {
        if (opts.setThrows) throw opts.setThrows();
        store[k] = v;
      },
    },
    console: { error: (...a) => errs.push(a.join(' ')), warn: () => {}, log: () => {} },
  };
  vm.createContext(ctx);
  vm.runInContext(grab(src, 'function svBlockForCorruptStore(keys){'), ctx);
  // Wrap it so the test can see it fire without losing the real behaviour.
  const realBlock = ctx.svBlockForCorruptStore;
  // Array.from, not keys.slice(): an array built inside the vm realm has a
  // different Array.prototype, and deepStrictEqual compares prototypes -- it
  // reports "same structure but not reference-equal", which reads like a real
  // failure and is not one.
  ctx.svBlockForCorruptStore = function (keys) { blocked.push(Array.from(keys)); return realBlock(keys); };
  vm.runInContext(grab(src, 'function svIsQuotaError(e){'), ctx);
  vm.runInContext(grab(src, 'function st(key,data){'), ctx);
  vm.runInContext(grab(src, 'function svLoad(k,d){'), ctx);
  vm.runInContext(grab(src, 'function showToast(msg, type, dur) {'), ctx);
  return { ctx, errs, blocked, store, toastEl };
}

const quota = () => { const e = new Error('exceeded'); e.name = 'QuotaExceededError'; return e; };
const security = () => { const e = new Error('blocked by policy'); e.name = 'SecurityError'; return e; };

// ── st(), the write side ───────────────────────────────────────────────
section('st() -- a refused write is no longer a boolean nobody reads');

test('a healthy write returns true and actually stores', () => {
  const { ctx, errs, store } = load({});
  assert.strictEqual(ctx.st('sv_x', [1, 2]), true);
  assert.strictEqual(store['sv_x'], '[1,2]');
  assert.strictEqual(errs.length, 0, 'a working write logged an error');
});

test('A FULL DISK RETURNS FALSE AND IS NOW LOGGED, naming the key', () => {
  const { ctx, errs } = load({ setThrows: quota });
  assert.strictEqual(ctx.st('sv_controlled', [1]), false);
  assert.strictEqual(errs.length, 1, 'the failed write was not logged exactly once');
  assert.match(errs[0], /SAIRNvet: localStorage write FAILED for "sv_controlled"/);
  assert.match(errs[0], /storage is FULL/);
});

test('A NON-QUOTA FAILURE IS NOT BLAMED ON THE QUOTA', () => {
  // Sending a clinic to delete its own records over a SecurityError is its
  // own damage.
  const { ctx, errs } = load({ setThrows: security });
  assert.strictEqual(ctx.st('sv_x', [1]), false);
  assert.ok(!/storage is FULL/.test(errs[0]), 'a SecurityError was reported as a full disk');
  assert.match(errs[0], /blocked by policy/, 'the real reason was not passed through');
});

test('all three spellings of "full" are recognised, not just this browser\'s', () => {
  [{ name: 'QuotaExceededError' }, { name: 'NS_ERROR_DOM_QUOTA_REACHED' },
   { code: 22 }, { code: 1014 }].forEach((shape) => {
    const { ctx, errs } = load({ setThrows: () => Object.assign(new Error('x'), shape) });
    ctx.st('sv_x', [1]);
    assert.match(errs[0], /storage is FULL/, JSON.stringify(shape) + ' was not recognised');
  });
});

test('THE UNREADABLE-STORE REFUSAL IS UNTOUCHED -- it still will not overwrite', () => {
  // The pre-existing half of the guard, pinned here because the change above
  // is inside the same function and must not have moved it.
  const { ctx, blocked, store } = load({ store: { 'sv_controlled': '{not json' } });
  assert.strictEqual(ctx.st('sv_controlled', [{ real: 'record' }]), false);
  assert.strictEqual(store['sv_controlled'], '{not json',
    'the corrupted value was overwritten -- that is the data loss this guard exists to prevent');
  assert.strictEqual(blocked.length, 1, 'the app was not blocked');
  assert.deepStrictEqual(blocked[0], ['sv_controlled']);
});

test('st() still never throws', () => {
  [{}, { setThrows: quota }, { setThrows: security }, { getThrows: true },
   { store: { 'sv_x': '{bad' } }].forEach((opts, i) => {
    const { ctx } = load(opts);
    assert.doesNotThrow(() => ctx.st('sv_x', [1]), 'case ' + i + ' threw');
  });
});

// ── svLoad(), the read side ────────────────────────────────────────────
section('svLoad() -- the one read path that entered neither half of the guard');

test('a healthy read returns the parsed value and says nothing', () => {
  const { ctx, errs, blocked } = load({ store: { 'sv_role': '"Nurse"' } });
  assert.strictEqual(ctx.svLoad('role', 'Doctor'), 'Nurse');
  assert.strictEqual(errs.length, 0);
  assert.strictEqual(blocked.length, 0, 'a working read blocked the app');
});

test('a GENUINELY ABSENT key returns the default, silently -- that is not a defect', () => {
  const { ctx, errs, blocked } = load({});
  assert.strictEqual(ctx.svLoad('role', 'Doctor'), 'Doctor');
  assert.strictEqual(errs.length, 0, 'a first-run read logged an error');
  assert.strictEqual(blocked.length, 0, 'a first-run read blocked the app');
});

test('AN EMPTY STRING IS TREATED AS ABSENT HERE, DELIBERATELY UNLIKE THE OTHER APPS', () => {
  // st() and svIntegrityScan() both skip '' for these keys. Disagreeing would
  // block a clinic on a value the other two halves of the guard call absent.
  const { ctx, errs, blocked } = load({ store: { 'sv_role': '' } });
  assert.strictEqual(ctx.svLoad('role', 'Doctor'), 'Doctor');
  assert.strictEqual(errs.length, 0);
  assert.strictEqual(blocked.length, 0);
});

test('AN UNREADABLE RECORD BLOCKS instead of quietly becoming "Doctor"', () => {
  // The whole finding. A corrupted sv_role did not read as unreadable, it read
  // as a privilege-shaped default arrived at by a parse failure.
  const { ctx, errs, blocked } = load({ store: { 'sv_role': '{not json' } });
  ctx.svLoad('role', 'Doctor');
  assert.strictEqual(blocked.length, 1, 'the guard was not entered from the read side');
  assert.deepStrictEqual(blocked[0], ['sv_role']);
  assert.strictEqual(ctx._svUnreadable['sv_role'], true,
    'the key was not marked, so a later write could still overwrite it');
  assert.strictEqual(errs.length, 1);
  assert.match(errs[0], /stored record "sv_role" is UNREADABLE/);
  assert.match(errs[0], /Nothing has been deleted or overwritten/,
    'the log does not say the record survived, which invites a panic or a wipe');
});

test('...and the WRITE side then refuses that key too, which is the point of marking it', () => {
  const { ctx, store } = load({ store: { 'sv_role': '{not json' } });
  ctx.svLoad('role', 'Doctor');
  assert.strictEqual(ctx.st('sv_role', 'Doctor'), false, 'the marked key was still writable');
  assert.strictEqual(store['sv_role'], '{not json', 'the corrupted value was overwritten');
});

test('A STORE THAT WILL NOT OPEN IS LOGGED BUT NOT BLOCKED', () => {
  // Nothing is corrupt, so there is nothing to protect -- svIntegrityScan()
  // takes exactly the same view of a store it cannot read at all.
  const { ctx, errs, blocked } = load({ getThrows: true });
  assert.strictEqual(ctx.svLoad('role', 'Doctor'), 'Doctor');
  assert.strictEqual(blocked.length, 0, 'an unavailable store blocked the app');
  assert.strictEqual(errs.length, 1);
  assert.match(errs[0], /localStorage is unavailable/);
  assert.ok(!/UNREADABLE/.test(errs[0]), 'an unavailable store was reported as a corrupt record');
});

test('svLoad() still never throws, including when the block itself fails', () => {
  [{}, { getThrows: true }, { store: { 'sv_x': '{bad' } }].forEach((opts, i) => {
    const { ctx } = load(opts);
    assert.doesNotThrow(() => ctx.svLoad('x', null), 'case ' + i + ' threw');
  });
  // The real svBlockForCorruptStore writes document.body.innerHTML. If the DOM
  // is not there at all it must not turn a bad read into an exception.
  const { ctx } = load({ store: { 'sv_x': '{bad' } });
  ctx.document = null;
  assert.doesNotThrow(() => ctx.svLoad('x', null), 'a missing DOM turned a bad read into a throw');
});

// ── the toast rule ─────────────────────────────────────────────────────
section('a success toast must not follow a refused write');

test('THE LATCH IS DECLARED IN THE FILE, not only in this harness', () => {
  // Added 2026-09-04 (Cody) by independent review. The harness seeds
  // `_svWriteFailed: null` into the VM context, so every assertion below
  // would go green even if `var _svWriteFailed = null;` were deleted from
  // sairnvet.html -- and in a real browser showToast() would then throw a
  // ReferenceError on the first refused write, turning a warning into a
  // broken toast. A fixture that supplies the thing it is testing passes for
  // the wrong reason; this is the same vacuous-pass shape the ld() and st()
  // suites each hit once already.
  const src = fs.readFileSync(path.join(ROOT, 'sairnvet.html'), 'utf8');
  assert.match(src, /var\s+_svWriteFailed\s*=\s*null\s*;/,
    'the latch is not declared in sairnvet.html -- the tests below are vacuous');
  // And it must be a FILE-level declaration, not one nested inside a function
  // where showToast() could not see it.
  assert.match(src, /\n\s*var\s+_svWriteFailed\s*=\s*null\s*;/,
    'the latch declaration is not at file scope');
});

test('an ordinary success toast is untouched when nothing failed', () => {
  const { ctx, toastEl } = load({});
  ctx.st('sv_whiteboard', [1]);
  ctx.showToast('Updated Rex', 'success');
  assert.strictEqual(toastEl.textContent, 'Updated Rex');
  assert.strictEqual(toastEl.className, 'toast show success');
});

test('A SUCCESS TOAST AFTER A REFUSED WRITE IS REPLACED -- the whole finding', () => {
  // 29 call sites in this file fire "Updated X" on the line after a save whose
  // boolean they discard. st() logs the refusal to the console; the clinician
  // is looking at the screen.
  const { ctx, toastEl } = load({ setThrows: quota });
  assert.strictEqual(ctx.st('sv_controlled', [1]), false);
  ctx.showToast('Updated Rex', 'success');
  assert.match(toastEl.textContent, /NOT SAVED/);
  assert.match(toastEl.textContent, /sv_controlled/, 'the message does not name the key that failed');
  assert.strictEqual(toastEl.className, 'toast show error', 'it still rendered as a success');
});

test('the latch is CONSUMED, so the next honest success reports normally', () => {
  const { ctx, toastEl } = load({ setThrows: quota });
  ctx.st('sv_x', [1]);
  ctx.showToast('Updated Rex', 'success');
  ctx.showToast('Updated Milo', 'success');
  assert.strictEqual(toastEl.textContent, 'Updated Milo',
    'one failure suppressed every later success message');
});

test('A LATER SUCCESSFUL WRITE CLEARS IT, so a recovered save is not slandered', () => {
  const { ctx, toastEl } = load({});
  ctx._svWriteFailed = 'sv_old';
  ctx.st('sv_x', [1]);
  ctx.showToast('Updated Rex', 'success');
  assert.strictEqual(toastEl.textContent, 'Updated Rex');
});

test('the BLOCKED-KEY path latches too, because the block screen can itself fail', () => {
  // svBlockForCorruptStore() replaces the DOM, but its own catch admits that
  // write can fail. An app still running after that must not go on saying
  // "Updated".
  const { ctx, toastEl } = load({ store: { 'sv_controlled': '{not json' } });
  ctx.st('sv_controlled', [1]);          // first call: detects and blocks
  ctx.showToast('Updated', 'success');
  assert.match(toastEl.textContent, /NOT SAVED/);
  ctx.st('sv_controlled', [1]);          // second call: the early _svUnreadable return
  ctx.showToast('Updated', 'success');
  assert.match(toastEl.textContent, /NOT SAVED/, 'the already-blocked path does not latch');
});

test('NO TOAST ELEMENT IS SURVIVED, NOT THROWN ON -- and the latch is kept', () => {
  // Added 2026-09-05 (Cody) by independent review, answering its own question
  // "does the blocked-key latch double-report alongside the full-page block
  // screen". It did not double-report -- it THREW. svBlockForCorruptStore()
  // replaces document.body.innerHTML, which destroys #sv-toast, and st()
  // returns NORMALLY on that path, so the caller carried on to its usual
  // renderX(); showToast(...) and dereferenced null.
  const { ctx } = load({ setThrows: quota });
  ctx.st('sv_controlled', [1]);
  ctx.document.getElementById = () => null;          // the block screen is up
  assert.doesNotThrow(() => ctx.showToast('Updated Rex', 'success'),
    'a missing toast element turned a refused write into a TypeError');
  // The warning must not be spent on a toast nobody could see.
  assert.strictEqual(ctx._svWriteFailed, 'sv_controlled',
    'the latch was consumed by a toast that never rendered');
});

test('the corrected message names the TIMING, not just the failure', () => {
  // A handful of success toasts in this file follow no storage write at all --
  // a copied link, an AI answer, a CSV export. The warning is TRUE for them (a
  // record really was not saved) but a bare "NOT SAVED" on "Scan complete"
  // reads as the scan having failed. The window is accepted rather than
  // narrowed -- a false alarm costs a re-read, a missed one costs a clinical
  // record -- so the wording has to carry the distinction.
  const { ctx, toastEl } = load({ setThrows: quota });
  ctx.st('sv_controlled', [1]);
  ctx.showToast('Scan complete', 'success');
  assert.match(toastEl.textContent, /an earlier save/,
    'the message does not say the refusal was an EARLIER action');
  assert.match(toastEl.textContent, /sv_controlled/);
});

test('error and info toasts are never rewritten -- only success claims are', () => {
  const { ctx, toastEl } = load({ setThrows: quota });
  ctx.st('sv_x', [1]);
  ctx.showToast('Something else went wrong', 'error');
  assert.strictEqual(toastEl.textContent, 'Something else went wrong');
  ctx.showToast('Heads up', 'info');
  assert.strictEqual(toastEl.textContent, 'Heads up');
  // ...and the latch survives both, so the success claim is still corrected.
  ctx.showToast('Updated Rex', 'success');
  assert.match(toastEl.textContent, /NOT SAVED/);
});

// ── source ─────────────────────────────────────────────────────────────
section('the silent shapes are gone from the source, not merely bypassed');

test('neither one-liner is back, in any formatting', () => {
  // Whitespace-normalised, for the reason the ld() suite learned twice: two
  // literals cannot keep up with formatting, and a reformatted return of the
  // defect is still the defect.
  const squashed = fs.readFileSync(path.join(ROOT, FILE), 'utf8')
    .replace(/\/\/[^\n]*/g, '')      // the new comments quote the old code
    .replace(/\s+/g, '');
  assert.ok(!/functionsvLoad\(k,d\)\{try\{varr=localStorage\.getItem\('sv_'\+k\);returnr\?JSON\.parse\(r\):d;\}catch\(e\)\{returnd;\}\}/.test(squashed),
    'the swallowing svLoad one-liner is back');
  assert.ok(!/localStorage\.setItem\(key,JSON\.stringify\(data\)\);returntrue;\}catch\(e\)\{returnfalse;\}/.test(squashed),
    "st()'s silent outer catch is back: false to nobody, and nothing logged");
});

test('the checker no longer lists SAIRNvet as a silent loader', () => {
  const { execFileSync } = require('child_process');
  let out;
  try {
    out = execFileSync('python', [path.join(ROOT, 'tools', 'fail_open_check.py')],
      { cwd: ROOT, encoding: 'utf8' });
  } catch (e) { out = e.stdout || ''; }
  const start = out.indexOf('BROWSER-SIDE');
  assert.ok(start > 0, 'the browser-side section is missing from the tool output');
  assert.ok(out.slice(start).indexOf('sairnvet.html') === -1,
    'SAIRNvet is still listed as a silent loader');
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' SAIRNvet STORAGE-GUARD ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
