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

function build(opts) {
  opts = opts || {};
  const field = { value: '' };
  const ctx = {
    console,
    INTAKE_FORM_URL: 'https://sairn.vercel.app/stonedesk-intake',
    // `in` rather than `||`, so a deliberately-null profile is not replaced by
    // the default and the fallback branch actually gets exercised.
    _sdBizProfile: ('profile' in opts) ? opts.profile : { company_name: 'Pinnacle Stone & Design' },
    slabLicKey: () => 'SD-PINNACLE-2026-SECRET',
    document: { getElementById: (id) => (id === 'intake-link-field' ? field : null) }
  };
  vm.createContext(ctx);
  vm.runInContext(src + '\nintakeBuildLink();', ctx);
  return field.value;
}

// ---------------------------------------------------------------------------
section('the link no longer carries a credential');

test('THE ONE THAT MATTERS: the licence key is not in the URL', () => {
  const url = build();
  assert.ok(!url.includes('SD-PINNACLE-2026-SECRET'),
    'the licence key is in a link the shop sends to customers: ' + url);
  assert.ok(!/[?&]lic=/.test(url), 'a lic parameter is back: ' + url);
});

test('...and not merely renamed or encoded around', () => {
  const url = build();
  assert.ok(!/SD-PINNACLE/i.test(decodeURIComponent(url)),
    'the key survives decoding: ' + decodeURIComponent(url));
});

test('the shop name still travels, so the link is still useful', () => {
  const url = build();
  assert.match(url, /\?shop=Pinnacle%20Stone%20%26%20Design/);
});

test('a shop with no profile falls back to a name, not to a key', () => {
  const url = build({ profile: null });
  assert.match(url, /\?shop=StoneDesk$/);
  assert.ok(!url.includes('SECRET'));
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
