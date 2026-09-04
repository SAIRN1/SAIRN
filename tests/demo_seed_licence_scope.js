// tests/demo_seed_licence_scope.js
//
// Run:  node tests/demo_seed_licence_scope.js
//
// Demo seed data is scoped to ONE licence as of 2026-09-04.
//
// The audit in docs/2026-09-04-stonedesk-seed-fallback-audit.md found 32
// `sdDemoCleared()`-gated seed sites. Exactly one (sd_crm) could mask real
// server data and was fixed as its own defect. The other thirty-one mask
// nothing -- but a REAL PAYING CUSTOMER whose account happens to look untouched
// was still shown fabricated figures as its own business:
//
//   sd_ap          open payables, due-this-week, OVERDUE and MTD-paid, plus a
//                  full aging table, off six invented bills DATED 2024
//   sd_equipment   ~$471,000 of equipment value
//   sd_bids        ~$293,000 of bid value
//
// The decision was not a blanket delete -- the demo account has to keep looking
// like a populated shop for sales use. So the seeds render for SD-PINNACLE-2026
// and every other licence gets the honest empty state, the same answer Slabs
// got in `501d15b`.
//
// ── WHY ONE GATE AND NOT THIRTY-TWO EDITS ─────────────────────────────────
// Every site already calls the same function. Widening sdDemoCleared() reaches
// all of them with two edits; rewriting 59 call sites in a 2MB file is exactly
// the bulk find-replace CLAUDE.md's syntax rule forbids, and for good reason.
// The cost is that the NAME is now narrower than the behaviour, which is why
// sdDemoClearedByUser() exists for the one caller that means the original
// thing.
//
// This suite drives the real functions. The interesting cases are the ones
// where a wrong answer is invisible: an unlicensed install, a licence that
// differs only in case or whitespace, and the Admin checkbox that must keep
// reporting the user's own action rather than the new gate.

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

function grabLine(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  return html.slice(s, html.indexOf('\n', s));
}
function grabBlock(sig, indent) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const rest = html.slice(s);
  const m = rest.match(new RegExp('\\r?\\n' + indent + '\\};?(?=\\r?\\n)'));
  assert.ok(m, 'not terminated: ' + sig);
  return rest.slice(0, m.index + m[0].length);
}

const GATE = [
  grabLine("var SD_DEMO_LICENSE='SD-PINNACLE-2026';"),
  grabBlock('function sdIsDemoLicense(){', ''),
  grabLine('function sdDemoClearedByUser(){'),
  grabLine('function sdDemoCleared(){ return sdDemoClearedByUser()||!sdIsDemoLicense(); }')
].join('\n');

function build(opts) {
  const store = {};
  if (opts.cleared) store['sd_demo_cleared'] = '1';
  const ctx = {
    console,
    localStorage: { getItem: k => (k in store ? store[k] : null) },
    sdLicenseKey: opts.noResolver ? undefined : () => opts.licence === undefined ? '' : opts.licence,
    window: {}
  };
  vm.createContext(ctx);
  vm.runInContext(GATE + '\nthis.api={cleared:sdDemoCleared,byUser:sdDemoClearedByUser,isDemo:sdIsDemoLicense,KEY:SD_DEMO_LICENSE};', ctx);
  return ctx.api;
}

console.log('StoneDesk demo seeds -- populated for the demo licence, empty for a real one\n');

section('the demo licence still demos');

test('the licence is the one Michael named', () => {
  assert.strictEqual(build({}).KEY, 'SD-PINNACLE-2026');
});

test('SD-PINNACLE-2026 gets the seeds', () => {
  const a = build({ licence: 'SD-PINNACLE-2026' });
  assert.strictEqual(a.isDemo(), true);
  assert.strictEqual(a.cleared(), false, 'the demo licence lost its demo data');
});

test('...and Clear Demo Data still works ON the demo licence', () => {
  const a = build({ licence: 'SD-PINNACLE-2026', cleared: true });
  assert.strictEqual(a.cleared(), true);
});

test('a stray space or lowercase still demos -- a hand-typed key must not silently un-demo', () => {
  ['  SD-PINNACLE-2026 ', 'sd-pinnacle-2026', 'Sd-Pinnacle-2026\n'].forEach(k => {
    assert.strictEqual(build({ licence: k }).isDemo(), true, JSON.stringify(k));
  });
});

section('every other licence gets the honest empty state');

test('a real customer licence suppresses the seeds', () => {
  const a = build({ licence: 'SD-SOMESHOP-2026' });
  assert.strictEqual(a.isDemo(), false);
  assert.strictEqual(a.cleared(), true, 'a paying customer was shown invented figures');
});

test('a near-miss licence is NOT the demo licence', () => {
  // Substring and prefix matches are the way a check like this goes wrong.
  ['SD-PINNACLE-2027', 'SD-PINNACLE-2026-B', 'XSD-PINNACLE-2026', 'PINNACLE-2026']
    .forEach(k => assert.strictEqual(build({ licence: k }).isDemo(), false, k));
});

test('an UNLICENSED install gets empty states -- documented behaviour change', () => {
  // This is the case the old comment called "a fresh sales-demo install". It
  // now shows empty. Asserted rather than left implicit: an empty panel is a
  // missing feature, an invented payables total is a wrong number, and failing
  // toward the first is the deliberate choice.
  const a = build({ licence: '' });
  assert.strictEqual(a.isDemo(), false);
  assert.strictEqual(a.cleared(), true);
});

test('a missing sdLicenseKey resolver fails toward EMPTY, not toward seeded', () => {
  // The gate can run before the resolver is defined. It must not seed then.
  const a = build({ noResolver: true });
  assert.strictEqual(a.isDemo(), false);
  assert.strictEqual(a.cleared(), true);
});

section('the original meaning survives for the one caller that needs it');

test('sdDemoClearedByUser reports the USER ACTION, not the licence', () => {
  assert.strictEqual(build({ licence: 'SD-SOMESHOP-2026' }).byUser(), false,
    'a real customer would be told they had cleared demo data they never had');
  assert.strictEqual(build({ licence: 'SD-SOMESHOP-2026', cleared: true }).byUser(), true);
  assert.strictEqual(build({ licence: 'SD-PINNACLE-2026', cleared: true }).byUser(), true);
});

test('the Admin checkbox reads sdDemoClearedByUser, not sdDemoCleared', () => {
  assert.match(html, /demoEl\.checked=!sdDemoClearedByUser\(\);/);
  assert.ok(html.indexOf('demoEl.checked=!sdDemoCleared();') === -1,
    'the toggle went back to the widened gate');
});

test('re-enabling demo mode off the demo licence does not claim it worked', () => {
  // A flag flip that changes nothing, reported as success, is the same class as
  // the intake panel's "Customer + Job created from intake!".
  assert.match(html, /demo data only loads on the demo licence/);
});

section('the gate really is the only thing the seed sites consult');

test('all 32 seed sites still route through sdDemoCleared()', () => {
  const sites = html.split('\n').filter(l =>
    (l.indexOf('sdDemoCleared()') !== -1 && l.indexOf('?[]:') !== -1) ||
    l.indexOf('(d.length||sdDemoCleared())?d:SEED') !== -1);
  assert.strictEqual(sites.length, 32,
    'the seed-site count moved to ' + sites.length + ' -- re-run the audit before trusting this suite');
});

test('sd_crm reaches the same gate through crmSeed()', () => {
  // It is the 33rd consumer and the one that does not match the ?[]: shape.
  assert.match(html, /return \(_crmReadFailed\|\|sdDemoCleared\(\)\)\?\[\]:SEED;/);
});

test('no seed site reads sd_demo_cleared out of localStorage directly', () => {
  // Bypassing the gate is how a site would keep seeding for everyone.
  const direct = html.split('\n').filter(l =>
    l.indexOf("localStorage.getItem('sd_demo_cleared')") !== -1);
  assert.strictEqual(direct.length, 1, 'more than one reader of the raw flag: ' + direct.length);
  assert.match(direct[0], /function sdDemoClearedByUser\(\)/);
});

section('Clear Demo Data actually clears every seeded key');

test('SAFE_DEMO_KEYS covers every key that has a seed fallback', () => {
  // Two were missing until 2026-09-04 -- sd_it_tickets and sd_it_licenses,
  // whose fallback variables are named TICKETS and LICENSES, so every scan
  // looking for ||SEED walked past them. Same omission and same cause as
  // sd_fieldmap in 2026-08-04. This asserts the list by DERIVING it.
  const i = html.indexOf('var SAFE_DEMO_KEYS=[');
  assert.ok(i > 0, 'SAFE_DEMO_KEYS is gone');
  const safe = new Set((html.slice(i, html.indexOf('];', i)).match(/'(sd_[a-z_]+)'/g) || [])
    .map(s => s.slice(1, -1)));
  const seeded = new Set();
  html.split('\n').forEach(l => {
    if ((l.indexOf('sdDemoCleared()') !== -1 && l.indexOf('?[]:') !== -1) ||
        l.indexOf('crmSeed()') !== -1 ||
        l.indexOf('(d.length||sdDemoCleared())?d:SEED') !== -1) {
      const m = l.match(/localStorage\.getItem\('(sd_[a-z_]+)'\)/);
      if (m) seeded.add(m[1]);
    }
  });
  assert.ok(seeded.size >= 28, 'the derivation found only ' + seeded.size + ' seeded keys -- it has stopped working');
  const missing = [...seeded].filter(k => !safe.has(k));
  assert.deepStrictEqual(missing, [],
    'seeded but not cleared by Clear Demo Data: ' + missing.join(', '));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exitCode = 1;
