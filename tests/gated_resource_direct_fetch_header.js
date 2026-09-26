// tests/gated_resource_direct_fetch_header.js
//
// Run:  node tests/gated_resource_direct_fetch_header.js
//
// REQUIREMENT: every DIRECT fetch to the data API that names a resource in
//   SD_SESSION_GATED must carry the X-SD-Auth session token. A per-app
//   transport (sdnData, sdData, scData...) attaches it centrally; a direct
//   fetch built for its own reason builds its own headers and can forget.
//
// ── WHY THIS EXISTS, AND WHY THE GATE'S OWN SUITE COULD NOT SEE IT ─────────
// SAIRNdesign's five Tier A resources were session-gated on 2026-09-23
// (9db14368). The change was measured by counting `sdnData(` call sites and
// making that transport's header unconditional -- sound, and blind by
// construction to a path that does not use the transport.
//
// sairndesign.html's invoice-create is exactly that path: a DELIBERATE direct
// fetch, because it needs the real 409 DUPLICATE_INVOICE status that sdnData
// collapses to null. It built `{'Content-Type', 'Authorization'}` and no
// token, so from the moment the gate landed every invoice creation got 403
// FORBIDDEN and the user was told "Saved on this device only -- server sync
// failed, try again with a connection". A WRONG REASON for a real data loss,
// on a money record. Found 2026-09-25 while reviewing the gate; driven against
// the real handler (403 without the header, 200 with it) before being fixed.
//
// ── IT IS A CLASS CHECK, NOT A CHECK ABOUT ONE LINE ───────────────────────
// The gated list is read from api/sd-data.js, and the app files are swept, so
// a NEW gate on a resource some app direct-fetches fails here rather than in
// production. That is the half the gate's own suite cannot hold: it asserts
// the handler refuses, which is correct, and the app is the other side.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const API = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');

// ── THE GATED LIST IS DERIVED, NEVER TYPED ────────────────────────────────
// A second hand-written copy of this list is a copy that goes stale the day a
// resource is gated, and the arm would then pass over the very site the new
// gate breaks. Asserted non-trivial so a parse failure cannot read as "no
// gated resources, nothing to check".
const gatedBlock = API.slice(API.indexOf('SD_SESSION_GATED'),
                             API.indexOf('SD_GATE_APP'));
const GATED = [...new Set([...gatedBlock.matchAll(/'([a-z_]+)':\s*\[/g)]
  .map((m) => m[1]))];
assert.ok(GATED.length >= 20,
  'only ' + GATED.length + ' gated resources parsed out of api/sd-data.js -- '
  + 'the anchor moved and this suite would sweep for almost nothing');

let pass = 0;
function t(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

console.log('DIRECT fetches to a session-gated resource must carry X-SD-Auth');
console.log('  (' + GATED.length + ' gated resources, derived from api/sd-data.js)');

const apps = fs.readdirSync(ROOT).filter((f) => f.endsWith('.html'));

// A direct fetch is a `fetch(` whose body names `resource: '<gated>'` and which
// is NOT the app's own shared transport (those are the functions that attach
// the header centrally; they are covered by their own suites).
function directFetchSites(src) {
  const out = [];
  const re = /fetch\s*\(/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    // Close the call by counting parens so a multi-line body is one site --
    // a line-based scan reports a phantom every time a call wraps, which is
    // the defect this platform has recorded four times in other checkers.
    let depth = 1;
    let i = m.index + m[0].length;
    while (i < src.length && depth > 0) {
      if (src[i] === '(') depth++;
      else if (src[i] === ')') depth--;
      i++;
    }
    const seg = src.slice(m.index, i);
    const res = [...seg.matchAll(/resource\s*:\s*'([a-z_]+)'/g)].map((x) => x[1]);
    const hit = res.filter((r) => GATED.includes(r));
    if (!hit.length) continue;
    // The header object may be inline OR a variable assembled just above, so
    // the window includes the 12 lines before the call. A token attached two
    // lines up is attached.
    const before = src.slice(Math.max(0, m.index - 900), m.index);
    out.push({ resources: hit, hasToken: /X-SD-Auth/.test(seg + before),
               line: src.slice(0, m.index).split('\n').length });
  }
  return out;
}

const offenders = [];
let swept = 0;
apps.forEach((f) => {
  const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
  directFetchSites(src).forEach((s) => {
    swept++;
    if (!s.hasToken) offenders.push(f + ':' + s.line + ' -> ' + s.resources.join(','));
  });
});

t('every direct fetch naming a gated resource carries the session token', () => {
  assert.deepStrictEqual(offenders, [],
    offenders.length + ' direct fetch(es) to a session-gated resource send no '
    + 'X-SD-Auth, so the server answers 403 and the app reports a connection '
    + 'problem:\n       ' + offenders.join('\n       '));
});

// THE PAIRED POSITIVE. Without it, a scan that found ZERO sites would pass
// this suite forever -- the vacuous-sweep shape this platform keeps recording.
t('and the sweep actually found sites to check (not a vacuous pass)', () => {
  assert.ok(swept > 0,
    'the sweep matched NO direct fetch naming any gated resource. Either the '
    + 'idiom changed or the parser broke; either way this suite is asserting '
    + 'nothing.');
});

// THE KNOWN SITE, NAMED. The one this suite was written for, so a refactor
// that removes it says so rather than quietly shrinking the population.
t('the SAIRNdesign invoice-create direct fetch is among the sites swept', () => {
  const src = fs.readFileSync(path.join(ROOT, 'sairndesign.html'), 'utf8');
  const sites = directFetchSites(src).filter(
    (s) => s.resources.includes('sdn_invoices'));
  assert.strictEqual(sites.length, 1,
    'expected exactly one direct fetch writing sdn_invoices, found ' + sites.length);
  assert.ok(sites[0].hasToken,
    'the invoice-create direct fetch lost its X-SD-Auth header again -- this is '
    + 'the exact 2026-09-25 defect, and it costs a silent invoice loss');
});

console.log('\n' + pass + ' passed');
