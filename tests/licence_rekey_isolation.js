// tests/licence_rekey_isolation.js
//
// Run:  node tests/licence_rekey_isolation.js
//
// The licence re-key guard, across every app that has one.
//
// This code DELETES A CUSTOMER'S DATA. That is the whole reason it exists and
// it is also the reason it is the most dangerous thing shipped tonight. Two
// failures matter and neither of them throws:
//
//   1. IT WIPES TOO MUCH. Every SAIRN app is served from the same origin and
//      shares one localStorage -- a real browser checked in August held 201
//      keys across eight apps. A prefix of `sd` rather than `sd_` matches
//      `sdn_clients` and deletes a design studio's client list from inside
//      StoneDesk. That is not hypothetical: stonedesk.html's own Layer 27
//      comment records it as the reason its scoped wipe exists at all.
//   2. IT WIPES TOO LITTLE, OR NOT AT ALL, and the next licence to open the
//      app on that device sees the previous customer's records as its own.
//
// So the assertions below are mostly about what was NOT deleted, and the
// cross-app matrix at the end is the one that would catch a widened prefix in
// any of the eleven files at once.
//
// The guard is lifted out of each real app file rather than reimplemented.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

const ROOT = path.join(__dirname, '..');

// file -> prefix. Every app carrying the guard.
const APPS = {
  'sairndental.html': 'dnt_',
  'sairnsenior.html': 'sen_',
  'sairncare.html': 'alf_',
  'sairnbuild.html': 'bld_',
  'sairndesign.html': 'sdn_',
  'sairnlaw.html': 'law_',
  'sairnlegacy.html': 'leg_',
  'sairnroofing.html': 'rf_',
  'sairncode.html': 'sc_',
  'sairnbiz.html': 'sb_',
  'sairngrounds.html': 'grd_',
  'sairnscape.html': 'scp_',
  'sairnfreedom.html': 'sf_'
};

// Apps WITHOUT the guard, and why -- recorded as a failing-if-forgotten
// assertion rather than as prose, so this list can only shrink deliberately.
const NO_GUARD = {
  // Two different licence key names in one 2MB file -- it writes
  // `stonedesk_license_key` at the activation path and reads `sd_license_key`
  // elsewhere -- so the fingerprint has to decide which one identifies the
  // licence before any wipe can be safe. It also owns the widest key space on
  // the platform (83 distinct sd_ keys plus stonedesk_, stonedesk:, stondesk_
  // and legacy fab_ forms, per its own Layer 27 inventory), and another
  // session was working in it tonight. Its own scoped wipe already exists and
  // is the right foundation; wiring the re-key hook onto it is a scoped change
  // of its own, not a rider on an eleven-app pass.
  'stonedesk.html': 'two key names, the widest key space, and a live editor',
  // Never SETS a licence key -- it reads StoneDesk's `sd_license_key` and
  // shares StoneDesk's namespace entirely. There is no re-key event here to
  // hook; whatever StoneDesk does covers it. Verified by grep, not assumed.
  'stonedesk-hr.html': 'reads StoneDesk’s key, never sets one'
};

const MARK = '// -- LICENCE RE-KEY ISOLATION (2026-09-03)';

function guardSource(file) {
  const src = fs.readFileSync(path.join(ROOT, file), 'utf8').replace(/\r\n/g, '\n');
  const a = src.indexOf(MARK);
  assert.ok(a > 0, file + ' has no re-key guard');
  // Ends at the close of the guard function.
  const end = src.indexOf('\n  return true;\n}\n', a);
  assert.ok(end > a, file + ': guard end not found');
  return src.slice(a, end + '\n  return true;\n}\n'.length);
}

function load(file, opts) {
  opts = opts || {};
  const pfx = APPS[file];
  const p = pfx.replace(/_$/, '');
  // Storage doubles: the DATA keys are own enumerable properties so
  // Object.keys(localStorage) sees exactly them, and the methods are
  // non-enumerable so they are not mistaken for stored records. A Proxy was
  // tried first and was wrong -- its ownKeys trap has to report the target's
  // own non-configurable properties, so it threw, the guard's try/catch
  // swallowed it, and every wipe silently became a no-op that still passed
  // the "nothing was deleted" assertions. Worth recording: the first version
  // of this harness made the code under test look SAFER than it is.
  function makeStorage(seed) {
    const o = Object.assign({}, seed || {});
    Object.defineProperties(o, {
      getItem: { value: (k) => (Object.prototype.hasOwnProperty.call(o, k) ? o[k] : null), enumerable: false },
      setItem: { value: (k, v) => { o[k] = String(v); }, enumerable: false },
      removeItem: { value: (k) => { delete o[k]; }, enumerable: false }
    });
    return o;
  }
  const localData = makeStorage(opts.local);
  const sessionData = makeStorage(opts.session);
  const prompts = [];
  const ctx = {
    console, String, Object, Number, Reflect,
    localStorage: localData,
    sessionStorage: sessionData,
    confirm: (m) => { prompts.push({ kind: 'confirm', m }); return opts.confirm !== false; },
    alert: (m) => { prompts.push({ kind: 'alert', m }); },
    __local: localData,
    __session: sessionData,
    __prompts: prompts
  };
  vm.createContext(ctx);
  vm.runInContext(guardSource(file), ctx);
  ctx.guard = ctx[p + 'LicenceGuard'];
  ctx.isOwn = ctx[p + 'IsOwnKey'];
  ctx.fp = ctx[p + 'LicFingerprint'];
  ctx.FPKEY = pfx + 'lic_fp';
  ctx.pfx = pfx;
  return ctx;
}

console.log('licence re-key isolation');

// ── EVERY APP HAS ONE ──────────────────────────────────────────────────────
section('coverage');

test('every listed app carries the guard and it parses', () => {
  Object.keys(APPS).forEach((f) => {
    const c = load(f);
    assert.strictEqual(typeof c.guard, 'function', f + ': no guard function');
    assert.strictEqual(typeof c.isOwn, 'function', f + ': no ownership test');
  });
});

test('the guard is CALLED, not merely defined, in every app', () => {
  // A guard nothing invokes is the dormant-code failure: the exposure is
  // untouched and the tracking row says closed.
  Object.keys(APPS).forEach((f) => {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    const p = APPS[f].replace(/_$/, '');
    const defs = src.split('function ' + p + 'LicenceGuard(').length - 1;
    const uses = src.split(p + 'LicenceGuard(').length - 1;
    assert.ok(uses > defs, f + ': ' + p + 'LicenceGuard is defined but never called');
  });
});

test('it is called BEFORE the key is stored, not after', () => {
  // Called after, the new key is already written when the wipe runs and the
  // guard removes the key it was supposed to admit.
  Object.keys(APPS).forEach((f) => {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    const p = APPS[f].replace(/_$/, '');
    // The CALL, not the definition. Function declarations hoist, so the guard
    // block sits after the gate handler in some files and that is fine at
    // runtime -- an earlier version of this test used lastIndexOf and reported
    // sairnscape as broken when what it had found was the `function` keyword.
    const callRe = new RegExp("(?<!function )\\b" + p + "LicenceGuard\\(");
    const cm = callRe.exec(src);
    assert.ok(cm, f + ': no call site found, only a definition');
    const call = cm.index;
    // Four real shapes across the platform, and the app-specific wrappers are
    // not optional to handle: sairnscape stores through scpSt(), sairnfreedom
    // through a K_LIC constant. A regex that knew only the two common forms
    // reported "could not find where the key is stored" for sairnscape -- which
    // would have been easy to soften into a skip, and a skipped ordering check
    // is how a guard that runs AFTER the write ships looking green.
    const storeRe = new RegExp(
      "(setItem\\('" + APPS[f] + "lic(ense_key)?'"
      + "|st\\('" + APPS[f] + "lic'"
      + "|scpSt\\('" + APPS[f] + "lic'"
      + "|st\\(K_LIC)");
    const m = storeRe.exec(src);
    assert.ok(m, f + ': could not find where the key is stored');
    assert.ok(call < m.index, f + ': the guard runs after the key is stored');
  });
});

// ── THE FIRST-RUN RULE ─────────────────────────────────────────────────────
section('first run adopts, and never wipes on a guess');

test('no fingerprint yet -> adopt, delete nothing', () => {
  // An existing install has no fingerprint and there is no way to know which
  // licence its data belongs to. Wiping on that guess is the worse error.
  const c = load('sairndental.html', { local: { dnt_patients: '[1,2,3]', dnt_license_key: 'DNT-A' } });
  assert.strictEqual(c.guard('DNT-A-2026'), true);
  assert.strictEqual(c.__local.dnt_patients, '[1,2,3]');
  assert.ok(c.__local[c.FPKEY], 'the fingerprint was not recorded');
  assert.strictEqual(c.__prompts.length, 0, 'it asked the user something on first run');
});

test('the same key twice -> no prompt, no wipe', () => {
  const c = load('sairndental.html');
  c.guard('DNT-PINNACLE-2026');
  const fpAfterFirst = c.__local[c.FPKEY];
  c.__local.dnt_patients = '[1]';
  assert.strictEqual(c.guard('DNT-PINNACLE-2026'), true);
  assert.strictEqual(c.__local.dnt_patients, '[1]');
  assert.strictEqual(c.__local[c.FPKEY], fpAfterFirst);
  assert.strictEqual(c.__prompts.length, 0);
});

test('a different key with NOTHING stored -> adopt silently', () => {
  const c = load('sairndental.html');
  c.guard('DNT-A-2026');
  assert.strictEqual(c.guard('DNT-B-2026'), true);
  assert.strictEqual(c.__prompts.length, 0, 'it asked about data that does not exist');
});

// ── THE RE-KEY ─────────────────────────────────────────────────────────────
section('a real re-key: asked, and only this app is touched');

function rekeyFixture(file, confirmAnswer) {
  const pfx = APPS[file];
  const c = load(file, {
    confirm: confirmAnswer,
    local: {
      // this app's
      [pfx + 'patients']: '[1,2]',
      [pfx + 'settings']: '{}',
      [pfx + 'license_key']: 'OLD-KEY',
      // OTHER APPS -- must survive
      sd_jobs: '[9]', sdn_clients: '[8]', sb_lic: 'SB-X', law_matters: '[7]',
      leg_cases: '[6]', scp_jobs: '[5]', sc_license_key: 'SC-X', grd_jobs: '[4]',
      // shared platform state -- owned by nobody
      sairn_created: '2026-01-01', sairn_privacy_accepted: 'true',
      sairn_learned_global: '{}', s_attempts: '0'
    },
    session: { [pfx + 'session_token']: 'tok', sd_session: 'other-app' }
  });
  // establish the first licence, then change it
  c.guard('KEY-A-2026');
  const before = Object.keys(c.__local).length;
  const ok = c.guard('KEY-B-2026');
  return { c, ok, before };
}

Object.keys(APPS).forEach((file) => {
  const pfx = APPS[file];
  test(file + ': a re-key wipes this app and NOTHING else', () => {
    const { c, ok } = rekeyFixture(file, true);
    assert.strictEqual(ok, true);
    // gone
    assert.ok(!(pfx + 'patients' in c.__local), pfx + 'patients survived');
    assert.ok(!(pfx + 'settings' in c.__local), pfx + 'settings survived');
    assert.ok(!(pfx + 'session_token' in c.__session), 'the session token survived');
    // NOT gone -- other apps
    ['sd_jobs', 'sdn_clients', 'sb_lic', 'law_matters', 'leg_cases', 'scp_jobs',
     'sc_license_key', 'grd_jobs'].forEach((k) => {
      if (k.indexOf(pfx) === 0) return;   // genuinely this app's own
      assert.ok(k in c.__local, file + ' deleted another app\'s key: ' + k);
    });
    assert.ok('sd_session' in c.__session || pfx === 'sd_', 'another app\'s session was cleared');
    // NOT gone -- shared platform state
    ['sairn_created', 'sairn_privacy_accepted', 'sairn_learned_global', 's_attempts']
      .forEach((k) => assert.ok(k in c.__local, file + ' deleted shared key ' + k));
    // and the fingerprint now names the new licence
    assert.strictEqual(c.__local[c.FPKEY], c.fp('KEY-B-2026'));
  });
});

test('the user is ASKED, and told what will be removed', () => {
  const { c } = rekeyFixture('sairndental.html', true);
  const ask = c.__prompts.filter((x) => x.kind === 'confirm')[0];
  assert.ok(ask, 'it wiped without asking');
  assert.match(ask.m, /DIFFERENT licence/i);
  assert.match(ask.m, /3 locally stored items/, 'the count is wrong or missing');
  // The one sentence that stops a support call: the server copy is fine.
  assert.match(ask.m, /server records are\s+stored per licence/i);
  assert.match(ask.m, /Local-only records are gone for good/i);
});

test('CANCEL means nothing is deleted and the key is refused', () => {
  const { c, ok, before } = rekeyFixture('sairndental.html', false);
  assert.strictEqual(ok, false, 'a cancelled re-key was allowed through');
  assert.strictEqual(Object.keys(c.__local).length, before, 'something was deleted anyway');
  assert.strictEqual(c.__local.dnt_patients, '[1,2]');
  // and the fingerprint still names the ORIGINAL licence
  assert.strictEqual(c.__local[c.FPKEY], c.fp('KEY-A-2026'));
});

// ── FAIL CLOSED ────────────────────────────────────────────────────────────
section('when the safety check itself is broken');

test('a failed scope assertion refuses BOTH the wipe and the entry', () => {
  const c = load('sairndental.html', {
    local: { dnt_patients: '[1]', sd_jobs: '[2]' }
  });
  c.guard('KEY-A');
  c.DNT_SCOPE_OK = false;            // simulate a widened prefix
  const ok = c.guard('KEY-B');
  assert.strictEqual(ok, false, 'it let the new licence in with a broken scope check');
  assert.strictEqual(c.__local.dnt_patients, '[1]', 'it wiped with a broken scope check');
  assert.strictEqual(c.__local.sd_jobs, '[2]');
  assert.ok(c.__prompts.some((x) => x.kind === 'alert'), 'it failed closed silently');
});

test('the scope assertion is TRUE in every shipped app', () => {
  Object.keys(APPS).forEach((f) => {
    const c = load(f);
    const P = APPS[f].replace(/_$/, '').toUpperCase();
    assert.strictEqual(c[P + '_SCOPE_OK'], true, f + ': its own scope assertion is failing');
  });
});

// ── THE CROSS-APP MATRIX ───────────────────────────────────────────────────
section('no app claims any other app\'s keys');

test('every app\'s ownership test rejects every other app\'s keys', () => {
  // The assertion that would catch a widened prefix anywhere in the eleven
  // files at once. Real keys, one per app, plus the two that share a leading
  // two characters -- sd_/sdn_ and sc_/scp_ -- which are exactly the pairs the
  // underscore in the prefix exists to separate.
  const SAMPLE = {
    'dnt_': ['dnt_patients', 'dnt_license_key'],
    'sen_': ['sen_clients'],
    'alf_': ['alf_residents'],
    'bld_': ['bld_jobs', 'bld_lien_waivers'],
    'sdn_': ['sdn_clients', 'sdn_invoices'],
    'law_': ['law_matters'],
    'leg_': ['leg_cases'],
    'rf_': ['rf_claims'],
    'sc_': ['sc_license_key', 'sc_claims'],
    'sb_': ['sb_lic', 'sb_projects'],
    'grd_': ['grd_jobs'],
    'sd_': ['sd_jobs', 'sd_license_key'],       // StoneDesk -- no guard yet, but its keys must survive
    'scp_': ['scp_jobs'],                        // SAIRNscape -- ditto
    'sv_': ['sv_patients'],
    'sf_': ['sf_permit_flags']
  };
  Object.keys(APPS).forEach((f) => {
    const c = load(f);
    const mine = APPS[f];
    Object.keys(SAMPLE).forEach((otherPfx) => {
      SAMPLE[otherPfx].forEach((k) => {
        const expected = (otherPfx === mine);
        assert.strictEqual(c.isOwn(k), expected,
          f + ' (' + mine + ') ' + (expected ? 'does not claim its OWN key ' : 'CLAIMS ') + k);
      });
    });
  });
});

test('shared platform keys belong to no app', () => {
  const SHARED = ['sairn_created', 'sairn_privacy_accepted', 'sairn_learned_global',
                  'sairn_tone_prefs', 's_attempts', 'sairn_audit'];
  Object.keys(APPS).forEach((f) => {
    const c = load(f);
    SHARED.forEach((k) => assert.strictEqual(c.isOwn(k), false, f + ' claims shared key ' + k));
  });
});

test('an app never claims its own fingerprint key -- it is rewritten, not wiped', () => {
  Object.keys(APPS).forEach((f) => {
    const c = load(f);
    assert.strictEqual(c.isOwn(c.FPKEY), false, f + ': the fingerprint would be deleted by its own wipe');
  });
});

// ── THE FINGERPRINT ────────────────────────────────────────────────────────
section('the fingerprint is a change detector and nothing more');

test('the same key gives the same fingerprint, a different key a different one', () => {
  const c = load('sairndental.html');
  assert.strictEqual(c.fp('DNT-PINNACLE-2026'), c.fp('DNT-PINNACLE-2026'));
  assert.notStrictEqual(c.fp('DNT-PINNACLE-2026'), c.fp('DNT-PINNACLE-2027'));
  assert.notStrictEqual(c.fp('DNT-A'), c.fp('DNT-B'));
});

test('it does not contain the key it fingerprints', () => {
  const c = load('sairndental.html');
  const k = 'DNT-DISTINCTIVE-KEY-2026';
  assert.strictEqual(c.fp(k).indexOf('DISTINCTIVE'), -1);
  assert.match(c.fp(k), /^[0-9a-f]{8}$/);
});

test('one-character differences are detected', () => {
  // A weak hash that collides on near-identical keys would let one customer's
  // key be swapped for a similar one with no wipe at all.
  const c = load('sairndental.html');
  const seen = new Set();
  for (let i = 0; i < 500; i++) seen.add(c.fp('DNT-CUSTOMER-' + i + '-2026'));
  assert.strictEqual(seen.size, 500, 'the fingerprint collided across 500 near-identical keys');
});

test('storage being unavailable does not lock anybody out', () => {
  // Private browsing throws on getItem. Refusing entry there would be a worse
  // bug than the one being fixed.
  const c = load('sairndental.html');
  c.localStorage = { getItem: () => { throw new Error('blocked'); }, setItem: () => {}, removeItem: () => {} };
  vm.createContext(c);
  vm.runInContext(guardSource('sairndental.html'), c);
  assert.strictEqual(c.dntLicenceGuard('ANY-KEY'), true);
});

test('the not-covered list is accurate, and nothing has quietly joined it', () => {
  Object.keys(NO_GUARD).forEach((f) => {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    assert.strictEqual(src.indexOf(MARK), -1,
      f + ' now HAS a re-key guard but is still listed as not covered -- move it ' +
      'into APPS so the cross-app matrix actually checks it');
  });
});

test('every app that stores a licence key is in exactly one list', () => {
  // The accounting check. An app with a licence gate that appears in neither
  // list is an unguarded re-key nobody is tracking.
  const files = fs.readdirSync(ROOT).filter((f) => /^sairn.*\.html$|^stonedesk.*\.html$/.test(f));
  const known = Object.keys(APPS).concat(Object.keys(NO_GUARD));
  files.forEach((f) => {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    const storesAKey = /setItem\('[a-z]{2,10}_lic(ense_key)?'|st\('[a-z]{2,4}_lic'|scpSt\('scp_lic'|st\(K_LIC/.test(src);
    if (!storesAKey) return;
    assert.ok(known.indexOf(f) !== -1,
      f + ' stores a licence key and is in neither APPS nor NO_GUARD -- a re-key ' +
      'there silently hands the next licence the previous one’s records');
  });
});

console.log('');
if (fail) { console.log(fail + ' FAILED, ' + pass + ' passed'); process.exit(1); }
console.log('ALL ' + pass + ' RE-KEY ISOLATION ASSERTIONS PASS');
