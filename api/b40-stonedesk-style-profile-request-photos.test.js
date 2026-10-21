// api/b40-stonedesk-style-profile-request-photos.test.js
//
// Run:  node api/b40-stonedesk-style-profile-request-photos.test.js
//
// cody b35, defects 5 and 6, driven verbatim from stonedesk.html.
//
// DEFECT 6 -- sdLoadStyleProfile() and sdObserveStyle() called sdData(), which
// returns j.data, and then read `d.provisioned`, `d.data` and `d.ok` -- keys of
// the ENVELOPE. A stored profile therefore always loaded as null and a
// successful write never updated it. Fixed by calling sdDataEnvelope().
//
// DEFECT 5 -- api/sd-data.js answers request_photos since b34 and nothing in
// stonedesk.html asked it. pcShowRequestPhotos() is the caller.
//
// THE CONTROL: arm A5 rebuilds the pre-fix source (transport swapped back to
// sdData) and asserts the defect's state, so a pass here is a fact about the
// fix and not about a test that cannot fail. Run against the pre-fix
// stonedesk.html on 2026-10-21, this file reported 1 passed, 10 failed (A3,
// the failed-read case, was already right).

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  return Promise.resolve().then(fn)
    .then(function () { console.log('  ok   ' + name); pass++; })
    .catch(function (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; });
}
function eq(a, e, what) {
  if (JSON.stringify(a) !== JSON.stringify(e)) {
    throw new Error(what + ': got ' + JSON.stringify(a) + ', expected ' + JSON.stringify(e));
  }
}

// From the first '{' after `marker` to its balancing '}'. The three functions
// extracted here carry no brace inside a string or regex, and the result is
// checked to close, so a short extraction fails loudly rather than quietly.
function extract(src, marker) {
  const at = src.indexOf(marker);
  if (at < 0 || src.indexOf(marker, at + 1) >= 0) throw new Error('marker not unique: ' + marker);
  let i = src.indexOf('{', at), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}' && --depth === 0) return src.slice(at, i + 1) + ';';
  }
  throw new Error('unbalanced: ' + marker);
}

function styleRealm(src, transport) {
  const ctx = { window: {}, console: console, _sdStyleProfile: null, _sdStyleProvisioned: null, calls: [] };
  ctx.window.SAIRNStyle = { analyse: function (t) { return { samples: 1, text_len: String(t).length }; } };
  ctx.sdDataEnvelope = function (a, r, p) { ctx.calls.push(['envelope', a, r]); return Promise.resolve(transport(a, r, p)); };
  ctx.sdData = function (a, r, p) {
    ctx.calls.push(['sdData', a, r]);
    const j = transport(a, r, p);
    return Promise.resolve(j && j.ok ? j.data : null);
  };
  vm.createContext(ctx);
  vm.runInContext(extract(src, 'window.sdLoadStyleProfile = async function') + '\n' +
                  extract(src, 'window.sdObserveStyle = function'), ctx);
  return ctx;
}

const STORED = { ok: true, provisioned: true, data: { samples: 9, avg_words: 40 }, samples: 9 };

function photoRealm(src, answer) {
  const ctx = { console: console, appended: [], notes: [], calls: [], listeners: [], focused: [] };
  function el(name) {
    return { name: name, style: {}, attrs: {}, removed: false,
             setAttribute: function (k, v) { this.attrs[k] = String(v); },
             focus: function () { ctx.focused.push(name); },
             remove: function () { this.removed = true; } };
  }
  ctx.opener = el('opener');
  ctx.document = {
    activeElement: ctx.opener,
    createElement: function () { return el('overlay'); },
    body: { appendChild: function (e) { ctx.appended.push(e); } },
    addEventListener: function (t, fn, cap) { ctx.listeners.push({ t: t, fn: fn, cap: cap }); },
    removeEventListener: function (t, fn) {
      ctx.listeners = ctx.listeners.filter(function (l) { return !(l.t === t && l.fn === fn); });
    }
  };
  ctx.notify = function (m, k) { ctx.notes.push([m, k]); };
  ctx.escAttrJs = function (s) { return s; };
  ctx.sdDataEnvelope = function (a, r, p) { ctx.calls.push([a, r, p]); return Promise.resolve(answer); };
  ctx.window = ctx;
  vm.createContext(ctx);
  // The filter regex sits beside the function, not inside it, and carries
  // braces of its own -- so it is taken whole by line rather than by extract().
  const rx = src.match(/\n[ \t]*var PC_PHOTO_RX=[^\n]*\n/);
  vm.runInContext(extract(src, 'function pcHtml(v)') + '\n' + (rx ? rx[0] : '') + '\n' +
                  extract(src, 'window.pcShowRequestPhotos=async function'), ctx);
  return ctx;
}

// ── THE BARRIERS (b44, cc b38) ──────────────────────────────────────────────
// cc's three mutants each left the b40 arms 11/11, because B3's hostile sample
// ('javascript:') failed BOTH barriers at once. Each barrier is now driven with
// the OTHER one removed, and section M applies cc's mutants to the real source
// and requires the arm that holds that barrier to go red.
const VALID = 'data:image/png;base64,AAAA';
const HOSTILE_Q = 'data:image/png;base64,AAAA" onerror="alert(1)';
const SVG = 'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=';
const HTML_DOC = 'data:text/html;base64,PGI+eDwvYj4=';
function mutate(src, from, to) {
  const n = src.split(from).length - 1;
  if (n !== 1) throw new Error('mutant anchor found ' + n + ' times: ' + from);
  return src.replace(from, to);
}
const M_UNESCAPE_SRC = function (s) {
  return mutate(s, "src=\"'+pcHtml(p.photo_base64)+'\"", "src=\"'+p.photo_base64+'\"");
};
const M_WIDEN_FILTER = function (s) {
  const line = (s.match(/var PC_PHOTO_RX=[^\n]*/) || [''])[0];
  return mutate(s, line, 'var PC_PHOTO_RX=/^data:/;');
};
const M_UNESCAPE_SLOT = function (s) { return mutate(s, 'pcHtml(String(p.slot))', 'String(p.slot)'); };
const M_NO_KEY = function (s) { return mutate(s, "document.addEventListener('keydown',onKey,true);", ''); };

async function html(src, data) {
  const c = photoRealm(src, { ok: true, provisioned: true, data: data });
  await c.pcShowRequestPhotos('QR-7');
  return c.appended[0].innerHTML;
}
// C1: a quote-breakout value is not rendered, a valid one is.
async function armQuote(src) {
  const h = await html(src, [{ slot: 1, photo_base64: HOSTILE_Q }, { slot: 2, photo_base64: VALID }]);
  eq((h.match(/<img /g) || []).length, 1, 'img count');
  eq(/onerror/.test(h), false, 'hostile value rendered');
}
// C2: image/svg+xml and text/html are not rendered.
async function armTypes(src) {
  const h = await html(src, [{ slot: 1, photo_base64: SVG }, { slot: 2, photo_base64: HTML_DOC },
                             { slot: 3, photo_base64: VALID }]);
  eq((h.match(/<img /g) || []).length, 1, 'img count');
  eq(/svg\+xml|text\/html/.test(h), false, 'non-image type rendered');
}
// C4: with the FILTER removed, escaping alone stops the breakout.
async function armEscapeAlone(src) {
  const h = await html(M_WIDEN_FILTER(src), [{ slot: 1, photo_base64: HOSTILE_Q }]);
  eq(/" onerror/.test(h), false, 'raw quote breakout reached the markup');
  eq(/&quot; onerror/.test(h), true, 'quote not escaped');
}
// C5: a hostile slot label is escaped.
async function armSlot(src) {
  const h = await html(src, [{ slot: '"><b>x</b>', photo_base64: VALID }]);
  eq(/<b>/.test(h), false, 'slot markup rendered');
  eq(/&quot;&gt;&lt;b&gt;/.test(h), true, 'slot not escaped');
}
// K2: Escape closes, unhooks the listener and returns focus to the opener.
async function armEscapeKey(src) {
  const c = photoRealm(src, { ok: true, provisioned: true, data: [{ slot: 1, photo_base64: VALID }] });
  await c.pcShowRequestPhotos('QR-7');
  const ov = c.appended[0];
  const l = c.listeners.filter(function (x) { return x.t === 'keydown'; });
  eq(l.length, 1, 'keydown listeners');
  l[0].fn({ key: 'Escape', preventDefault: function () {} });
  eq([ov.removed, c.listeners.length, c.focused[c.focused.length - 1]], [true, 0, 'opener'], 'after Escape');
}
// C8: the INTAKE handler itself, driven: compiled from source text so section M
// can drive a mutated copy. Shop lookup and rate limit are stubbed; fetch
// records what would have been written.
const PUB_FILE = path.join(__dirname, 'stonedesk-public.js');
const PUB_SRC = fs.readFileSync(PUB_FILE, 'utf8');
function loadPublic(srcText, writes) {
  process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';
  const Module = require('module');
  const libPath = require.resolve('./_lib/stonedesk-public');
  const real = require(libPath);
  require.cache[libPath].exports = Object.assign({}, real, {
    resolveShopSlug: async function () { return { licenseHash: 'h', slug: 's', data: {} }; },
    checkAndIncrementRateLimit: async function () { return { allowed: true }; }
  });
  global.fetch = async function (url, opts) {
    writes.push(String(url).split('?')[0].split('/').pop());
    return { ok: true, status: 201, json: async function () { return []; } };
  };
  const m = new Module(PUB_FILE, module);
  m.filename = PUB_FILE;
  m.paths = Module._nodeModulePaths(__dirname);
  m._compile(srcText, PUB_FILE);
  require.cache[libPath].exports = real;
  return m.exports;
}
async function intake(srcText, photo) {
  const writes = [];
  const h = loadPublic(srcText, writes);
  const res = { statusCode: null, body: null, setHeader: function () { return res; },
                status: function (c) { res.statusCode = c; return res; },
                json: function (b) { res.body = b; return res; } };
  await h({ method: 'POST', headers: {}, socket: {}, body: { action: 'quote_request', slug: 's',
    request: { name: 'T', email: 't@example.com' }, photos: [photo] } }, res);
  return { status: res.statusCode, code: ((res.body || {}).error || {}).code, writes: writes };
}
async function armIntake(srcText) {
  const bad = await intake(srcText, HOSTILE_Q);
  eq([bad.status, bad.code, bad.writes.length], [400, 'INVALID_PHOTO', 0], 'hostile photo at intake');
  const good = await intake(srcText, VALID);
  eq([good.status, good.writes.indexOf('sd_quote_requests') > -1], [200, true], 'a valid photo was not accepted and written');
}
const M_PREFIX_INTAKE = function (s) {
  return mutate(s, '[A-Za-z0-9+\\/]+={0,2}$/.test(p)', '/.test(p)');
};

async function mustFail(arm, src, name) {
  let failed = false;
  try { await arm(src); } catch (e) { failed = true; }
  if (!failed) throw new Error(name + ' survived: the arm that holds this barrier stayed green');
}

(async function () {
  console.log('StoneDesk b40 -- style profile reads the envelope; request photos have a caller');

  console.log('\nA. DEFECT 6 (style profile)');
  await test('A1. a STORED profile loads: provisioned true and the profile is the data', async function () {
    const c = styleRealm(SRC, function () { return STORED; });
    await c.window.sdLoadStyleProfile();
    eq(c._sdStyleProvisioned, true, 'provisioned');
    eq(c._sdStyleProfile, STORED.data, 'profile');
  });
  await test('A2. an unprovisioned table loads as provisioned FALSE, profile null', async function () {
    const c = styleRealm(SRC, function () { return { ok: true, data: null, provisioned: false }; });
    await c.window.sdLoadStyleProfile();
    eq([c._sdStyleProvisioned, c._sdStyleProfile], [false, null], 'state');
  });
  await test('A3. a failed read leaves provisioned NULL (no evidence), not false', async function () {
    const c = styleRealm(SRC, function () { return null; });
    await c.window.sdLoadStyleProfile();
    eq([c._sdStyleProvisioned, c._sdStyleProfile], [null, null], 'state');
  });
  await test('A4. a successful observation write updates the profile to the merged data', async function () {
    const merged = { samples: 10, avg_words: 41 };
    const c = styleRealm(SRC, function () { return { ok: true, provisioned: true, data: merged, samples: 10 }; });
    c.window.sdObserveStyle('quote me a kitchen');
    await new Promise(function (r) { setImmediate(r); });
    eq([c._sdStyleProvisioned, c._sdStyleProfile], [true, merged], 'state');
  });
  await test('A5. CONTROL: the same arms on the pre-fix transport (sdData) FAIL -- the test can see the defect', async function () {
    const pre = SRC.replace("sdDataEnvelope('read', 'style_profile'", "sdData('read', 'style_profile'")
                   .replace("sdDataEnvelope('write', 'style_profile'", "sdData('write', 'style_profile'");
    if (pre === SRC) throw new Error('control could not rebuild the pre-fix source');
    const c = styleRealm(pre, function () { return STORED; });
    await c.window.sdLoadStyleProfile();
    eq([c._sdStyleProvisioned, c._sdStyleProfile], [false, null], 'pre-fix state (the defect)');
  });

  console.log('\nB. DEFECT 5 (request photos)');
  await test('B1. the request row offers Photos only when photo_count > 0, wired to pcShowRequestPhotos', function () {
    const row = extract(SRC, 'function pcRenderRequests()');
    if (!/Number\(q\.photo_count\)>0\s*\?\s*'<button[^\n]*pcShowRequestPhotos\(/.test(row)) {
      throw new Error('no photo_count-gated pcShowRequestPhotos button in pcRenderRequests');
    }
  });
  await test('B2. it asks request_photos on sd_quote_requests with the request id', async function () {
    const c = photoRealm(SRC, { ok: true, provisioned: true, data: [] });
    await c.pcShowRequestPhotos('QR-7');
    eq(c.calls, [['request_photos', 'sd_quote_requests', { id: 'QR-7' }]], 'call');
  });
  await test('B3. stored photos render as <img>; a non-image value is NOT rendered', async function () {
    const c = photoRealm(SRC, { ok: true, provisioned: true, data: [
      { slot: 1, photo_base64: 'data:image/png;base64,AAAA' },
      { slot: 2, photo_base64: 'javascript:alert(1)' },
      { slot: 3, photo_base64: 'data:image/jpeg;base64,BBBB' }] });
    await c.pcShowRequestPhotos('QR-7');
    const html = c.appended[0].innerHTML;
    eq((html.match(/<img /g) || []).length, 2, 'img count');
    eq(/javascript:/.test(html), false, 'non-image rendered');
  });
  await test('B4. a FAILED read says so and opens nothing', async function () {
    const c = photoRealm(SRC, null);
    await c.pcShowRequestPhotos('QR-7');
    eq([c.appended.length, c.notes.length, c.notes[0] && c.notes[0][1]], [0, 1, 'err'], 'state');
  });
  await test('B5. an unprovisioned table is said as not set up, not as "no photos"', async function () {
    const c = photoRealm(SRC, { ok: true, data: [], provisioned: false });
    await c.pcShowRequestPhotos('QR-7');
    eq(/not set up/.test(c.appended[0].innerHTML), true, 'not-set-up text');
  });
  await test('B6. provisioned but empty is said as none stored', async function () {
    const c = photoRealm(SRC, { ok: true, data: [], provisioned: true });
    await c.pcShowRequestPhotos('QR-7');
    eq(/none are stored/.test(c.appended[0].innerHTML), true, 'none-stored text');
  });

  console.log('\nC. THE TWO BARRIERS, each with the other removed (b44, cc b38)');
  await test('C1. a quote-breakout value is NOT rendered; the valid one is', function () { return armQuote(SRC); });
  await test('C2. image/svg+xml and text/html data URLs are NOT rendered', function () { return armTypes(SRC); });
  await test('C3. FILTER ALONE: with src escaping removed, C1 still holds', function () { return armQuote(M_UNESCAPE_SRC(SRC)); });
  await test('C4. ESCAPING ALONE: with the filter widened to /^data:/, the quote is escaped and cannot break out', function () { return armEscapeAlone(SRC); });
  await test('C5. a hostile slot label is escaped', function () { return armSlot(SRC); });
  await test('C6. a non-string or missing photo value does not throw and renders nothing', async function () {
    const h = await html(SRC, [{ slot: 1, photo_base64: 12345 }, null, { slot: 2 }]);
    eq([(h.match(/<img /g) || []).length, /none are stored/.test(h)], [0, true], 'state');
  });
  await test('C7. the INTAKE applies the same whole-value test (api/stonedesk-public.js)', function () {
    const pub = fs.readFileSync(path.join(__dirname, 'stonedesk-public.js'), 'utf8');
    const rx = (SRC.match(/var PC_PHOTO_RX=(\/[^\n]*\/);/) || [])[1];
    if (!rx) throw new Error('PC_PHOTO_RX not found in stonedesk.html');
    if (pub.indexOf('!' + rx + '.test(p)') === -1) {
      throw new Error('intake photo check is not the same whole-value regex: ' + rx);
    }
  });

  await test('C8. the INTAKE handler refuses a quote-breakout photo (400 INVALID_PHOTO, nothing written) and accepts a valid one', function () { return armIntake(PUB_SRC); });

  console.log('\nD. KEYBOARD CLOSE');
  await test('D1. the overlay is a modal dialog and takes focus', async function () {
    const c = photoRealm(SRC, { ok: true, provisioned: true, data: [{ slot: 1, photo_base64: VALID }] });
    await c.pcShowRequestPhotos('QR-7');
    const ov = c.appended[0];
    eq([ov.attrs.role, ov.attrs['aria-modal'], c.focused.indexOf('overlay') > -1], ['dialog', 'true', true], 'dialog');
  });
  await test('D2. Escape closes it, unhooks the listener, and returns focus to the opener', function () { return armEscapeKey(SRC); });
  await test('D3. another key does NOT close it; a click does', async function () {
    const c = photoRealm(SRC, { ok: true, provisioned: true, data: [{ slot: 1, photo_base64: VALID }] });
    await c.pcShowRequestPhotos('QR-7');
    const ov = c.appended[0];
    c.listeners[0].fn({ key: 'a', preventDefault: function () {} });
    eq([ov.removed, c.listeners.length], [false, 1], 'after "a"');
    ov.onclick();
    eq([ov.removed, c.listeners.length], [true, 0], 'after click');
  });

  console.log('\nM. cc b38 MUTANTS (+ keyboard) applied to the real source -- each must turn its arm red');
  await test('M1. un-escape src -> C4 red', function () { return mustFail(armEscapeAlone, M_UNESCAPE_SRC(SRC), 'un-escape src'); });
  await test('M2. widen the filter to /^data:/ -> C2 red', function () { return mustFail(armTypes, M_WIDEN_FILTER(SRC), 'widen filter'); });
  await test('M3. un-escape the slot -> C5 red', function () { return mustFail(armSlot, M_UNESCAPE_SLOT(SRC), 'un-escape slot'); });
  await test('M4. no keydown listener -> D2 red', function () { return mustFail(armEscapeKey, M_NO_KEY(SRC), 'no keyboard close'); });
  await test('M5. intake back to a PREFIX-only check -> C8 red', function () { return mustFail(armIntake, M_PREFIX_INTAKE(PUB_SRC), 'prefix-only intake'); });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
