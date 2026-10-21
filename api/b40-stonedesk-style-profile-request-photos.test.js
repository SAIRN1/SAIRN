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
  const ctx = { console: console, appended: [], notes: [], calls: [] };
  ctx.document = {
    createElement: function () { return { style: {}, remove: function () {} }; },
    body: { appendChild: function (el) { ctx.appended.push(el); } }
  };
  ctx.notify = function (m, k) { ctx.notes.push([m, k]); };
  ctx.escAttrJs = function (s) { return s; };
  ctx.sdDataEnvelope = function (a, r, p) { ctx.calls.push([a, r, p]); return Promise.resolve(answer); };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(extract(src, 'function pcHtml(v)') + '\n' +
                  extract(src, 'window.pcShowRequestPhotos=async function'), ctx);
  return ctx;
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

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
