// tests/intake_link_no_credential.js
//
// Run:  node tests/intake_link_no_credential.js
//
// The customer intake share link used to be built as
//
//     INTAKE_FORM_URL + '?shop=' + shop + '&lic=' + slabLicKey()
//
// and the Share button's own copy invites the shop to send it to every
// customer before an appointment: "Hi! Before your appointment, please take 2
// minutes to fill out this quick project form...".
//
// slabLicKey() is sdLicenseKey() -- the SAME string sent as
// `Authorization: Bearer` on every /api/sd-data call. Verified live against
// SD-AUDIT-2026 with the bearer key and NO employee session:
//
//     slabs   -> full inventory returned, and writable (reserve/write carry no
//                session gate)
//     profile -> the shop's business record
//     memory  -> its AI memories
//
// So the link put a working credential into the customer's SMS thread, their
// browser history and any referrer. This test exists so it cannot come back.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// Drive the real builder.
const s = html.indexOf('function intakeBuildLink() {');
assert.ok(s > 0, 'intakeBuildLink not found in stonedesk.html');
const rel = html.slice(s).search(/\r?\n\}/);
assert.ok(rel > 0, 'intakeBuildLink is not terminated');
const src = html.slice(s, s + rel) + '\n}';

// UPDATED 2026-09-03. The builder now resolves the PUBLIC SHOP SLUG from
// sd_public_shop instead of pasting a company display name, so it is async and
// this harness awaits it. The parameter is still `?shop=` -- the same spelling
// /stonedesk-catalog has used since 2026-09-02 -- but it now carries the value
// that spelling means everywhere else in the app.
//
// `opts.slug === null` models a shop that has not claimed an address;
// `opts.readFails` models the read itself failing, which must not produce a URL.
function build(opts) {
  opts = opts || {};
  const field = { value: '', placeholder: '' };
  const ctx = {
    console: { log() {}, warn() {}, error() {} },
    INTAKE_FORM_URL: 'https://sairn.vercel.app/stonedesk-intake',
    // Still supplied, and still must not appear in the URL.
    _sdBizProfile: ('profile' in opts) ? opts.profile : { company_name: 'Pinnacle Stone & Design' },
    slabLicKey: () => 'SD-PINNACLE-2026-SECRET',
    sdData: opts.noSdData ? undefined : (() => (opts.readFails
      ? Promise.reject(new Error('read failed'))
      : Promise.resolve(('slug' in opts) ? (opts.slug === null ? {} : { shop_slug: opts.slug })
                                         : { shop_slug: 'pinnacle-stone' }))),
    document: { getElementById: (id) => (id === 'intake-link-field' ? field : null) }
  };
  vm.createContext(ctx);
  vm.runInContext(src + '\nintakeBuildLink();', ctx);
  // One turn is enough: the builder awaits a single already-resolved promise.
  return Promise.resolve().then(() => Promise.resolve()).then(() => field);
}

async function atest(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}

(async function () {

// ---------------------------------------------------------------------------
section('the link no longer carries a credential');

await atest('THE ONE THAT MATTERS: the licence key is not in the URL', async () => {
  const url = (await build()).value;
  assert.ok(!url.includes('SD-PINNACLE-2026-SECRET'),
    'the licence key is in a link the shop sends to customers: ' + url);
  assert.ok(!/[?&]lic=/.test(url), 'a lic parameter is back: ' + url);
});

await atest('...and not merely renamed or encoded around', async () => {
  const url = (await build()).value;
  assert.ok(!/SD-PINNACLE/i.test(decodeURIComponent(url)),
    'the key survives decoding: ' + decodeURIComponent(url));
});

// ---------------------------------------------------------------------------
section('?shop= carries the PUBLIC SLUG, the same meaning /stonedesk-catalog gives it');

await atest('the slug travels, so the link can actually identify the shop', async () => {
  const url = (await build({ slug: 'pinnacle-stone' })).value;
  assert.match(url, /\?shop=pinnacle-stone$/);
});

await atest('THE OLD BEHAVIOUR IS GONE: a company display name is not the slug', async () => {
  // This used to emit ?shop=Pinnacle%20Stone%20%26%20Design. A display name
  // cannot identify a shop to api/stonedesk-public.js, so the link could never
  // have submitted anything even once the page existed.
  const url = (await build({ slug: 'pinnacle-stone' })).value;
  assert.ok(!/Pinnacle%20Stone/.test(url), 'the display name is back in the URL: ' + url);
  assert.ok(!/shop=StoneDesk/.test(url), 'the display-name fallback is back: ' + url);
});

await atest('a shop with NO public address gets no link and is told why', async () => {
  const f = await build({ slug: null });
  assert.strictEqual(f.value, '', 'a URL was emitted for a shop with no slug: ' + f.value);
  assert.match(f.placeholder, /Public Catalog panel/,
    'the field does not say how to fix it: ' + f.placeholder);
});

await atest('a FAILED read produces no link either, and says so', async () => {
  // Emitting a URL built from a failed read is the same shape as everything
  // else this panel was doing wrong: an unusable thing presented as ready.
  const f = await build({ readFails: true });
  assert.strictEqual(f.value, '');
  assert.match(f.placeholder, /Could not check/);
});

await atest('no sdData at all is handled without throwing', async () => {
  const f = await build({ noSdData: true });
  assert.strictEqual(f.value, '');
  assert.match(f.placeholder, /reload/i);
});

test('the builder never calls slabLicKey() at all any more', () => {
  const body = src.replace(/\/\/[^\n]*/g, '');   // strip comments; they discuss it on purpose
  assert.ok(!/slabLicKey\s*\(/.test(body),
    'the key is still being read into the link builder');
});

// ---------------------------------------------------------------------------
section('and the panel stops presenting a dead link as ready');

test('the 404 is stated in the panel, not left for a customer to find', () => {
  assert.match(html, /The intake form is not live yet/);
  assert.match(html, /currently returns a 404/);
});

test('the reason the key was removable is recorded next to the code', () => {
  // If someone later "fixes" the 404 by building the form, the note is what
  // tells them not to put the key back.
  const i = html.indexOf('function intakeBuildLink()');
  const block = html.slice(i, i + 2200);
  assert.match(block, /purpose-made public token, never this key/);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' INTAKE-LINK ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);

})();
