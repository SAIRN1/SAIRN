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
//
// ── COMMENTS ARE STRIPPED, AND THE HOLE THAT CLOSES WAS FOUND IN REVIEW ────
// 2026-09-29 (A3). The token test was `/X-SD-Auth/.test(seg + before)` over the
// RAW source, so A COMMENT MENTIONING THE HEADER SATISFIED IT. That is PR 1.2
// exactly: grep cannot tell code from text that describes code. And the text is
// there to find -- sairndesign.html names `X-SD-Auth` in prose at three places,
// including the comment block that RECORDS the 2026-09-25 fix. A future direct
// fetch added within 900 characters of any of them would have been reported as
// carrying a token it does not send.
//
// MEASURED BEFORE BEING FIXED, in both directions, because the fix is only worth
// making if the hole is real and only worth trusting if the pass survives it: on
// the day this was written there was exactly ONE `X-SD-Auth` occurrence in the
// invoice-create window and it was the REAL header, so the suite's pass was
// honest and the hole was LATENT. It is fixed as a latent hole, not as a live
// failure, and saying which is the difference between a fix and a claim.
//
// THE STRIPPER IS THE SHARED ONE, NOT A FOURTH COPY. tests/lib/strip_comments.js
// exists because three suites each grew their own and all three were wrong in
// different ways -- a line filter, an unbounded regex, and a state machine that
// read `/*` inside a string. Its header records that.
//
// LINE NUMBERS SURVIVE THE STRIP, which is why the scan can run on the stripped
// source and still report a location a human can open. The module keeps every
// newline inside a removed region on purpose (`keepNewlines`), so a stripped
// file has the same line count as the original -- VERIFIED here rather than
// assumed, by the arm below that compares the two counts on every app swept. If
// that ever stops being true, offender locations silently start pointing at the
// wrong lines, which is worse than the hole this closed.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { stripComments } = require('./lib/strip_comments.js');

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

// Written out rather than escaped: this file is edited by scripts often enough
// that a literal backslash-n in a source edit has gone wrong before.
const NL = String.fromCharCode(10);

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

// ── READ ONCE, STRIPPED ONCE, per app. `codeOf` is what every arm below
// scans, so no arm can quietly go back to the raw text.
const stripped = new Map();
const lineDrift = [];
function codeOf(f) {
  if (!stripped.has(f)) {
    const raw = fs.readFileSync(path.join(ROOT, f), 'utf8');
    const code = stripComments(raw);
    // The invariant the line numbers depend on, checked per file rather than
    // trusted once: a removed comment must leave its newlines behind.
    const rawLines = raw.split(NL).length;
    const codeLines = code.split(NL).length;
    if (rawLines !== codeLines) {
      lineDrift.push(f + ' (' + rawLines + ' -> ' + codeLines + ')');
    }
    stripped.set(f, code);
  }
  return stripped.get(f);
}

const offenders = [];
let swept = 0;
apps.forEach((f) => {
  directFetchSites(codeOf(f)).forEach((s) => {
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
// THE INVARIANT THE LOCATIONS REST ON. Not a tidiness arm: if stripping ever
// eats a newline, every offender above starts naming a line that is not the one
// to open, and a check that reports the wrong location is one people stop
// following.
t('stripping comments does not move any line -- offender locations stay openable', () => {
  assert.deepStrictEqual(lineDrift, [],
    'stripComments changed the line count of ' + lineDrift.length + ' file(s), so '
    + 'every location this suite reports is now off by an unknown amount: '
    + lineDrift.join(', '));
});

// THE KNOWN-BAD, IN THE ONE DIRECTION THAT MATTERS. A comment naming the header
// must NOT satisfy the token test. Driven through the real directFetchSites() on
// a synthetic source rather than by editing an app -- and the fixture asserts
// its own validity first, because a fixture that never looked like a pass proves
// nothing about the strip.
t('a COMMENT naming X-SD-Auth does not count as sending it', () => {
  const H = 'X-SD' + '-Auth';
  const body = "fetch('/api/sd-data',{method:'POST',"
    + "headers:{'Content-Type':'application/json'},"
    + "body:JSON.stringify({action:'write',resource:'" + GATED[0] + "'})})";
  const withComment = '<script>' + NL + '// this path needs ' + H + ' one day' + NL
    + body + NL + '</script>';
  const withHeader = '<script>' + NL
    + body.replace("'Content-Type':'application/json'",
                   "'Content-Type':'application/json','" + H + "':'Bearer '+tok")
    + NL + '</script>';

  const rawHit = directFetchSites(withComment);
  assert.strictEqual(rawHit.length, 1, 'the fixture site was not even matched');
  assert.ok(rawHit[0].hasToken,
    'FIXTURE INVALID: the UNSTRIPPED fixture must LOOK like it carries a token, '
    + 'or this arm proves nothing about stripping');

  const stripHit = directFetchSites(stripComments(withComment));
  assert.strictEqual(stripHit.length, 1,
    'the site vanished when comments were stripped -- over-stripping ate real code');
  assert.strictEqual(stripHit[0].hasToken, false,
    'a comment mentioning the header still satisfies the token test -- PR 1.2, and '
    + 'the exact hole this arm exists for');

  const realHit = directFetchSites(stripComments(withHeader));
  assert.strictEqual(realHit.length, 1, 'the real-header fixture was not matched');
  assert.ok(realHit[0].hasToken,
    'stripping now hides a REAL header, which is the over-stripping direction and '
    + 'is worse than the hole: it would report a working path as broken');
});

t('the SAIRNdesign invoice-create direct fetch is among the sites swept', () => {
  const sites = directFetchSites(codeOf('sairndesign.html')).filter(
    (s) => s.resources.includes('sdn_invoices'));
  assert.strictEqual(sites.length, 1,
    'expected exactly one direct fetch writing sdn_invoices, found ' + sites.length);
  assert.ok(sites[0].hasToken,
    'the invoice-create direct fetch lost its X-SD-Auth header again -- this is '
    + 'the exact 2026-09-25 defect, and it costs a silent invoice loss');
});

console.log('\n' + pass + ' passed');
