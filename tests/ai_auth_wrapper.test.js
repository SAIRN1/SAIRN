// tests/ai_auth_wrapper.test.js
//
// Run:  node tests/ai_auth_wrapper.test.js
//
// Exercises the licence-key fetch wrapper that was inserted into all sixteen
// apps on 2026-09-05, by EXTRACTING THE SHIPPED BLOCK FROM EACH .html AND
// RUNNING IT. Not a copy of it, and not a re-implementation -- the thing that
// ships is the thing under test. If a wrapper is edited in one app and not the
// others, that app fails here.
//
// WHY IT NEEDS A REAL TEST RATHER THAN A READ: the wrapper is the only place
// the credential is attached now, and it is invisible at all ~134 call sites.
// The trade was accepted deliberately (see
// docs/2026-09-05-claude-proxy-auth-rollout.md) ON THE CONDITION that the
// wrapper itself is held by something. This is that something.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');

// app -> the localStorage key the wrapper should read, and whether that app
// stores it JSON-encoded (through an ld()-style helper) or raw.
const APPS = {
  stonedesk: { key: 'stonedesk_license_key', quoted: false, alt: 'sairn_license_key_stonedesk' },
  sairnbiz: { key: 'sb_lic', quoted: true },
  sairnbuild: { key: 'bld_license_key', quoted: false },
  sairncare: { key: 'alf_license_key', quoted: false },
  sairncode: { key: 'sc_license_key', quoted: false },
  sairndental: { key: 'dnt_license_key', quoted: false },
  sairndesign: { key: 'sdn_license_key', quoted: false },
  sairnfreedom: { key: 'sf_license_key', quoted: false },
  sairngrounds: { key: 'grd_lic', quoted: true },
  sairnlaw: { key: 'law_license_key', quoted: false },
  sairnlegacy: { key: 'leg_license_key', quoted: false },
  sairnmechanical: { key: 'sairnmechanical_license_key', quoted: false },
  sairnroofing: { key: 'rf_license_key', quoted: false },
  sairnscape: { key: 'scp_lic', quoted: true },
  sairnsenior: { key: 'sen_license_key', quoted: false },
  sairnvet: { key: 'sv_license', quoted: false },
};

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}

function wrapperSource(app) {
  const html = fs.readFileSync(path.join(ROOT, app + '.html'), 'utf8');
  const m = html.match(/<script>\s*(\/\* ── LICENCE KEY ON EVERY AI CALL[\s\S]*?)<\/script>/);
  assert.ok(m, app + ': the licence-key wrapper block was not found -- was it removed?');
  return m[1];
}

// A sandbox with just enough browser to run the wrapper.
function sandbox(store) {
  const calls = [];
  const win = {};
  win.fetch = function (input, init) { calls.push({ input: input, init: init }); return 'REAL'; };
  const ctx = {
    window: win,
    localStorage: {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    },
    Object: Object, JSON: JSON, String: String, console: console,
    Headers: undefined,
  };
  ctx.globalThis = ctx;
  return { ctx: vm.createContext(ctx), calls: calls, win: win };
}

function authOf(call) {
  const h = (call.init && call.init.headers) || {};
  for (const k in h) if (k.toLowerCase() === 'authorization') return h[k];
  return undefined;
}

const CLAUDE_URL = 'https://sairn.vercel.app/api/claude';

console.log('--- every app attaches its own key, read from its own storage shape ---');

for (const app of Object.keys(APPS)) {
  const cfg = APPS[app];
  const src = wrapperSource(app);

  // BOTH STORAGE SHAPES ARE ASSERTED FOR EVERY APP, rather than each app being
  // tested only in the shape I believed it used. These apps genuinely differ --
  // sairnbiz/sairngrounds/sairnscape/sairnfreedom write through a JSON-encoding
  // ld()/st() helper so the value arrives quoted, while the others write raw --
  // and a per-app `quoted` flag in this file would be a second place for that
  // fact to live and go stale. Testing both removes the question.
  for (const shape of ['raw', 'json-encoded']) {
    t(app + ': attaches Bearer <key> to a proxy call (' + shape + ' storage)', () => {
      const store = {};
      store[cfg.key] = shape === 'raw' ? 'KEY-' + app : JSON.stringify('KEY-' + app);
      const s = sandbox(store);
      vm.runInContext(src, s.ctx);
      s.ctx.window.fetch(CLAUDE_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      assert.strictEqual(s.calls.length, 1, 'the real fetch was not reached');
      assert.strictEqual(authOf(s.calls[0]), 'Bearer KEY-' + app);
      assert.strictEqual(s.calls[0].init.headers['Content-Type'], 'application/json',
        'the original headers were dropped');
    });
  }

  t(app + ': touches a NON-proxy URL not at all', () => {
    const store = {};
    store[cfg.key] = cfg.quoted ? JSON.stringify('KEY') : 'KEY';
    const s = sandbox(store);
    vm.runInContext(src, s.ctx);
    s.ctx.window.fetch('https://sairn.vercel.app/api/sd-data', { method: 'POST', headers: {} });
    assert.strictEqual(authOf(s.calls[0]), undefined,
      'it attached a licence key to an endpoint it has no business touching');
  });

  t(app + ': with NO key stored, the call still goes out unchanged', () => {
    const s = sandbox({});
    vm.runInContext(src, s.ctx);
    s.ctx.window.fetch(CLAUDE_URL, { method: 'POST', headers: { 'X-Test': '1' } });
    assert.strictEqual(s.calls.length, 1, 'a call was swallowed when no key was present');
    assert.strictEqual(authOf(s.calls[0]), undefined);
  });
}

console.log('--- properties that must hold for all of them ---');

t('an EXISTING Authorization header is never overwritten', () => {
  const s = sandbox({ stonedesk_license_key: 'STORED' });
  vm.runInContext(wrapperSource('stonedesk'), s.ctx);
  s.ctx.window.fetch(CLAUDE_URL, { headers: { Authorization: 'Bearer CALLER-SUPPLIED' } });
  assert.strictEqual(authOf(s.calls[0]), 'Bearer CALLER-SUPPLIED');
});

t('a lower-case authorization header counts as present too', () => {
  const s = sandbox({ stonedesk_license_key: 'STORED' });
  vm.runInContext(wrapperSource('stonedesk'), s.ctx);
  s.ctx.window.fetch(CLAUDE_URL, { headers: { authorization: 'Bearer LOWER' } });
  const h = s.calls[0].init.headers;
  assert.strictEqual(h.authorization, 'Bearer LOWER');
  assert.strictEqual(h.Authorization, undefined, 'it added a duplicate header in the other case');
});

t('StoneDesk falls back to its SECOND key, matching sdLicenseKey()', () => {
  const s = sandbox({ sairn_license_key_stonedesk: 'FALLBACK' });
  vm.runInContext(wrapperSource('stonedesk'), s.ctx);
  s.ctx.window.fetch(CLAUDE_URL, {});
  assert.strictEqual(authOf(s.calls[0]), 'Bearer FALLBACK');
});

t('StoneDesk PREFERS the first key when both are present', () => {
  const s = sandbox({ stonedesk_license_key: 'PRIMARY', sairn_license_key_stonedesk: 'FALLBACK' });
  vm.runInContext(wrapperSource('stonedesk'), s.ctx);
  s.ctx.window.fetch(CLAUDE_URL, {});
  assert.strictEqual(authOf(s.calls[0]), 'Bearer PRIMARY');
});

t('installing twice is a no-op -- the second install must not wrap the first', () => {
  const s = sandbox({ stonedesk_license_key: 'K' });
  const src = wrapperSource('stonedesk');
  vm.runInContext(src, s.ctx);
  const afterFirst = s.ctx.window.fetch;
  vm.runInContext(src, s.ctx);
  assert.strictEqual(s.ctx.window.fetch, afterFirst,
    'a second install re-wrapped fetch -- repeated on every reload this grows without bound');
});

t('a throwing localStorage does not break the call', () => {
  const s = sandbox({});
  s.ctx.localStorage.getItem = function () { throw new Error('SecurityError'); };
  vm.runInContext(wrapperSource('stonedesk'), s.ctx);
  s.ctx.window.fetch(CLAUDE_URL, {});
  assert.strictEqual(s.calls.length, 1, 'a disabled localStorage swallowed the request');
  assert.strictEqual(authOf(s.calls[0]), undefined);
});

t('a call with NO init object at all still works', () => {
  const s = sandbox({ stonedesk_license_key: 'K' });
  vm.runInContext(wrapperSource('stonedesk'), s.ctx);
  s.ctx.window.fetch(CLAUDE_URL);
  assert.strictEqual(authOf(s.calls[0]), 'Bearer K');
});

t('a Request-like object with a .url is recognised, not only a string', () => {
  const s = sandbox({ stonedesk_license_key: 'K' });
  vm.runInContext(wrapperSource('stonedesk'), s.ctx);
  s.ctx.window.fetch({ url: CLAUDE_URL }, {});
  assert.strictEqual(authOf(s.calls[0]), 'Bearer K');
});

t('the return value of the real fetch is passed through', () => {
  const s = sandbox({ stonedesk_license_key: 'K' });
  vm.runInContext(wrapperSource('stonedesk'), s.ctx);
  assert.strictEqual(s.ctx.window.fetch(CLAUDE_URL, {}), 'REAL');
});

t('SAIRNcash is NOT patched -- it moved to its own endpoint instead', () => {
  const html = fs.readFileSync(path.join(ROOT, 'sairncash.html'), 'utf8');
  assert.strictEqual(html.indexOf('__sairnAiAuthInstalled'), -1,
    'sairncash got the licence wrapper, but it has no licence key -- it should '
    + 'be calling /api/sairncash/ai instead');
  const code = html.split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
  assert.strictEqual(code.indexOf("fetch('/api/claude'"), -1,
    'a sairncash call site still points at the shared proxy');
  assert.ok(code.indexOf('/api/sairncash/ai') !== -1, 'the new endpoint is not called');
});

console.log('\n' + (fail ? 'FAILED  ' : 'ok  ') +
  'ai auth wrapper: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
