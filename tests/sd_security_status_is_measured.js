// tests/sd_security_status_is_measured.js
//
// Run:  node tests/sd_security_status_is_measured.js
//
// StoneDesk's Layer 30 security-status panel, driven verbatim from
// stonedesk.html.
//
// THE DEFECT. Four of its lines were string literals:
//   'Idle timeout: 30min'
//   'PII protection: 24 patterns active'
//   'Prompt injection: Active'
//   'Rate limiting: 30 calls/min'
// None of them read anything. A layer that was DEFINED AND NEVER CALLED
// rendered here as "Active" exactly as loudly as one that worked -- and on
// 2026-08-31 a sweep found TEN layers in precisely that state, six of them on
// the Claude request path this panel was calling Active. The one screen whose
// entire job is to report whether the protections are on was asserting it.
//
// SAME SHAPE AS LAYER 12, ONE FLOOR UP. Layer 12 is the SRI walk whose trusted-
// host allowlist named the only two hosts it could ever have caught; it
// reported clean for its whole existence. Neither is a missing check. Both are
// checks that could only ever return the reassuring answer. That is the class
// this file exists to keep closed.
//
// ARMS 3 AND 5 ARE THE NEGATIVE CONTROLS. A panel that printed NOT WIRED for
// everything would pass a naive "no hardcoded Active" test while being just as
// useless, so the fully-wired case is asserted to report the REAL numbers, and
// the numbers are compared against the source they are supposed to be read
// from rather than against a constant retyped here.

'use strict';
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', 'stonedesk.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  if (cond) { pass++; console.log('PASS  ' + name + (detail ? '  ' + detail : '')); return; }
  fail++;
  console.log('FAIL  ' + name + (detail ? '  ' + detail : ''));
}
function eq(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; console.log('PASS  ' + name + '  ' + a); return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function slice(startMark, endMark) {
  const i = src.indexOf(startMark);
  if (i < 0) throw new Error('not found: ' + startMark);
  const j = src.indexOf(endMark, i + startMark.length);
  if (j < 0) throw new Error('end not found after ' + startMark);
  return src.slice(i, j);
}

const L30 = slice('// LAYER 30 — Security Status Dashboard', '\n};') + '\n};';
const L8  = slice('// LAYER 8 — PII Scrubbing', '// LAYER 9 —');

// Build a browser-ish world and run the REAL Layer 30 source in it.
function run(opts) {
  opts = opts || {};
  const toasts = [];
  const elements = opts.elements || [];
  const window = {
    SA_RATE_LIMIT_PER_MIN: 30,
    fetch: function () {}
  };
  if (opts.wireScrub !== false) {
    window.saScrubPII = function (t) { return t; };
    window.saScrubPII.patternCount = opts.patternCount === undefined ? 24 : opts.patternCount;
  }
  if (opts.wireInjection !== false) window.saSecureClaudeCall = function () {};
  if (opts.wireRate !== false) window.saCheckRateLimit = function () { return true; };
  if (opts.outboundWrapped !== false) window.fetch._saOutboundWrapped = true;

  const SAIRN_SEC = {
    version: '3.0', appName: 'StoneDesk',
    violationCount: 0, loginAttempts: 0, maxLoginAttempts: 5,
    sessionTimeout: opts.sessionTimeout === undefined ? 30 * 60 * 1000 : opts.sessionTimeout
  };
  const sessionStorage = { getItem: () => '[]' };
  const document = { querySelectorAll: () => elements };
  const location = { origin: 'https://sairn.vercel.app' };
  const showToast = (m) => toasts.push(String(m));

  // eslint-disable-next-line no-new-func
  new Function('window', 'SAIRN_SEC', 'sessionStorage', 'document', 'location', 'showToast', 'URL',
    L30 + '\nwindow.saShowSecurityStatus();'
  )(window, SAIRN_SEC, sessionStorage, document, location, showToast, URL);
  return toasts[0] || '';
}

console.log('StoneDesk Layer 30 -- measured, not asserted\n');

// ── ARM 1: the hardcoded assurances are gone from the CODE
// SEARCHED WITH COMMENTS STRIPPED, and the first version of this arm was wrong
// for the opposite reason: Layer 30's new header QUOTES all four dead literals
// to record what they were, so a raw substring search found them and failed a
// correct file. A check that cannot tell a quoted example from a live string
// is the same class of wrong as the panel it is testing.
const L30_CODE = L30.split('\n').filter(function (l) {
  return l.trim().slice(0, 2) !== '//';
}).join('\n');
const BANNED = [
  "'Prompt injection: Active",
  "'Rate limiting: 30 calls/min",
  "'PII protection: 24 patterns active",
  "'Idle timeout: 30min"
];
BANNED.forEach(function (lit) {
  ok('1  no hardcoded assurance in code: ' + lit.slice(1, 34), L30_CODE.indexOf(lit) === -1, '');
});
ok('1e  CONTROL: the header still RECORDS what the dead literals were',
   L30.indexOf("'Prompt injection: Active'") !== -1, 'quoted in the comment, not built into the report');

// ── ARM 2: an UNWIRED layer says so, and does not read as fine
const noScrub = run({ wireScrub: false });
ok('2a  an absent saScrubPII reports NOT WIRED', /PII protection: NOT WIRED/.test(noScrub),
   (noScrub.match(/PII protection: [^\n]*/) || [''])[0]);
const noRate = run({ wireRate: false });
ok('2b  an absent saCheckRateLimit reports NOT WIRED', /Rate limiting: NOT WIRED/.test(noRate),
   (noRate.match(/Rate limiting: [^\n]*/) || [''])[0]);
const noInj = run({ wireInjection: false });
ok('2c  an absent saSecureClaudeCall reports NOT WIRED', /Prompt injection: NOT WIRED/.test(noInj),
   (noInj.match(/Prompt injection: [^\n]*/) || [''])[0]);

// THE DISTINCTION THAT MATTERED. Defined is not the same as reached: the six
// layers wired on 2026-08-31 all EXISTED the whole time.
const definedNotReached = run({ outboundWrapped: false });
ok('2d  DEFINED but not on the request path is reported as its own state',
   /Prompt injection: DEFINED BUT NOT ON THE REQUEST PATH/.test(definedNotReached),
   (definedNotReached.match(/Prompt injection: [^\n]*/) || [''])[0]);

// ── ARM 3: NEGATIVE CONTROL -- fully wired reports the REAL values
const full = run({});
ok('3a  CONTROL: a wired panel does not say NOT WIRED anywhere', full.indexOf('NOT WIRED') === -1, '');
ok('3b  CONTROL: prompt injection reports active', /Prompt injection: active on every/.test(full), '');
ok('3c  CONTROL: rate limiting reports the number', /Rate limiting: 30 calls\/min/.test(full), '');

// ── ARM 4: the values MOVE when their source moves. A literal cannot do this.
const moved = run({ sessionTimeout: 12 * 60 * 1000, patternCount: 41 });
ok('4a  idle timeout follows SAIRN_SEC.sessionTimeout', /Idle timeout: 12min/.test(moved),
   (moved.match(/Idle timeout: [^\n]*/) || [''])[0]);
ok('4b  PII count follows the pattern array', /PII protection: 41 patterns active/.test(moved),
   (moved.match(/PII protection: [^\n]*/) || [''])[0]);

// ── ARM 5: patternCount equals the real array, measured from the source
const realPatterns = (L8.match(/\{\s*re:\s*\//g) || []).length;
const scrubWorld = { saScrubPII: null };
// eslint-disable-next-line no-new-func
new Function('window', L8)(scrubWorld);
eq('5a  saScrubPII.patternCount === patterns actually declared',
   scrubWorld.saScrubPII.patternCount, realPatterns);
ok('5b  and the array is non-trivial', realPatterns >= 20, realPatterns + ' patterns');
eq('5c  CONTROL: the scrubber still scrubs',
   scrubWorld.saScrubPII('ring 555-123-4567'), 'ring [PHONE-REDACTED]');

// ── ARM 6: the live SRI line reports what is true NOW
const hashed = run({ elements: [
  { tagName: 'SCRIPT', src: 'https://cdn.jsdelivr.net/npm/x@1', integrity: 'sha384-abc' },
  { tagName: 'LINK', href: 'https://fonts.googleapis.com/css2?x', integrity: '' }
] });
ok('6a  all-hashed (plus the fonts exception) reports clean',
   /Subresource integrity: every external resource is hashed/.test(hashed),
   (hashed.match(/Subresource integrity: [^\n]*/) || [''])[0]);
const unhashed = run({ elements: [
  { tagName: 'SCRIPT', src: 'https://evil.example/x.js', integrity: '' }
] });
ok('6b  an unhashed script is COUNTED, not excused by its host',
   /Subresource integrity: 1 external resource\(s\) with NO integrity hash/.test(unhashed),
   (unhashed.match(/Subresource integrity: [^\n]*/) || [''])[0]);

// ── ARM 7: the rate limit exists in ONE place
const limitLiterals = (src.match(/rate limit exceeded \(30 calls\/min\)/g) || []).length;
eq('7a  the old thrice-copied limit literal is gone', limitLiterals, 0);
ok('7b  and SA_RATE_LIMIT_PER_MIN is the single source',
   /window\.SA_RATE_LIMIT_PER_MIN = 30;/.test(src), '');

console.log('\n%d passed, %d failed', pass, fail);
process.exit(fail ? 1 : 0);
