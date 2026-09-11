// tests/sairnlaw_csp.js
//
// Run:  node tests/sairnlaw_csp.js
//
// SAIRNlaw's Content-Security-Policy, read verbatim out of sairnlaw.html.
//
// WHY IT EXISTS. tesseract.min.js is pinned and hashed, and that covers exactly
// one of four fetched artefacts. It then fetches worker.min.js, and that worker
// fetches tesseract.js-core (wasm) and the @tesseract.js-data traineddata, all
// from jsDelivr, none with an integrity attribute and no supported way to give
// them one. A hostile worker receives every client document put through OCR --
// privileged material -- and can reach the network. SRI answers "is this the
// file I expected". Only a CSP answers "which hosts may this page talk to at
// all", and sairnlaw.html had none: no http-equiv, no csp.content, nothing.
//
// THIS FILE IS THE STATIC HALF. A policy string is easy to weaken by accident
// and the weakening is invisible -- `'unsafe-eval'` added to make one thing
// work, a wildcard host pasted in, `object-src` dropped -- so the directives
// that carry the guarantee are asserted by name, and the ones that must NOT
// appear are asserted absent.
//
// THE DYNAMIC HALF WAS RUN IN A REAL BROWSER and cannot be reproduced here;
// it is recorded in the commit message and repeated in ARM 4's comment so the
// next reader knows what was actually exercised rather than only parsed.

'use strict';
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, '..', 'sairnlaw.html'), 'utf8');

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

console.log('SAIRNlaw Content-Security-Policy\n');

// ── ARM 1: the policy exists, and is delivered by META not by script
const meta = src.match(/<meta http-equiv="Content-Security-Policy" content="([^"]+)">/);
ok('1a  a CSP meta tag is present', !!meta, '');
if (!meta) { console.log('\n%d passed, %d failed', pass, fail + 1); process.exit(1); }
const policy = meta[1];
const directives = {};
policy.split(';').forEach(function (d) {
  const parts = d.trim().split(/\s+/);
  if (parts[0]) directives[parts[0]] = parts.slice(1);
});
// A meta CSP binds from the moment the parser reaches it. stonedesk.html builds
// its policy in script at run time, which cannot bind anything the page did
// before that script ran -- asserted here so the weaker delivery is not copied
// into this file later on the grounds that "the other app does it that way".
ok('1b  it is a static meta tag, not assembled in JS',
   !/csp\.content\s*=/.test(src), 'no run-time policy assembly in this file');
ok('1c  and it sits in <head> before any script runs',
   src.indexOf('Content-Security-Policy') < src.indexOf('<script'), '');

// ── ARM 2: the sources are exactly what this file uses -- no more
eq('2a  connect-src is the API host and the OCR CDN, nothing else',
   directives['connect-src'], ["'self'", 'https://sairn.vercel.app', 'https://cdn.jsdelivr.net']);
// law.cornell.edu appears in this file FOUR times, every one of them as a
// `source_url` rendered into an href -- link text, never a fetch. A policy that
// listed it would be permitting a host on the strength of a string.
ok('2b  law.cornell.edu is NOT in the policy, because nothing fetches it',
   policy.indexOf('law.cornell.edu') === -1,
   'it appears only as source_url link text');
ok('2c  no wildcard host anywhere', !/(^|\s)\*|https:\/\/\*/.test(policy), '');
ok('2d  worker-src covers both ways tesseract.js v5 starts its worker',
   (directives['worker-src'] || []).includes('blob:') &&
   (directives['worker-src'] || []).includes('https://cdn.jsdelivr.net'), '');

// ── ARM 3: the dangerous relaxations are absent, and the required one is present
ok('3a  no unsafe-eval', policy.indexOf("'unsafe-eval'") === -1, '');
// Counted, not assumed -- this is what makes 3a safe to assert. COUNTED WITH
// COMMENTS STRIPPED, and the first version of this arm was wrong for the second
// time today in exactly the same way: the CSP comment block in sairnlaw.html
// says "this file contains zero eval() and zero new Function()", so a raw
// substring count found its own documentation and failed a correct file. The
// Layer 30 probe made the identical mistake this morning. A check that cannot
// tell a quoted example from a live call is the same class of wrong as the
// thing it is testing, and it is apparently the easy mistake to make twice.
const CODE = src
  .replace(/<!--[\s\S]*?-->/g, '')
  .split('\n')
  .filter(function (l) { return l.trim().slice(0, 2) !== '//'; })
  .join('\n');
const evalUses = (CODE.match(/\beval\(|new Function\(/g) || []).length;
eq('3b  CONTROL: the file contains zero eval() / new Function()', evalUses, 0);
ok('3c  CONTROL: and the comment that SAYS so is still there, deliberately',
   src.indexOf('zero eval() and zero') !== -1, 'quoted in a comment, never called');
// But WASM does need its own opt-in, and omitting it is the failure mode that
// looks correct and silently breaks OCR.
ok('3d  wasm-unsafe-eval IS present, or the OCR core cannot instantiate',
   (directives['script-src'] || []).includes("'wasm-unsafe-eval'"), '');
eq('3e  object-src is none', directives['object-src'], ["'none'"]);
eq('3f  frame-ancestors is none', directives['frame-ancestors'], ["'none'"]);
eq('3g  base-uri is self', directives['base-uri'], ["'self'"]);

// ── ARM 4: unsafe-inline is REQUIRED here, and the reason is measurable
// Dropping it would not harden this file, it would break it. Recorded with the
// real count so a future reader can see when that stops being true.
const inlineHandlers = (src.match(/\son[a-z]+="/g) || []).length;
ok('4a  script-src allows unsafe-inline', (directives['script-src'] || []).includes("'unsafe-inline'"), '');
ok('4b  CONTROL: because the file carries inline handlers that need it',
   inlineHandlers > 100, inlineHandlers + ' inline event handlers');

// VERIFIED IN A REAL BROWSER 2026-09-10, against this exact policy, served over
// http from 127.0.0.1 so the origin was real rather than file://:
//   * page load, zero securitypolicyviolation events;
//   * loadTesseract() resolved in 793ms -- the hashed entry script;
//   * Tesseract.recognize() on a generated image returned "MOTION" in 8.7s,
//     which exercises the worker, the wasm core AND the traineddata, i.e. the
//     three fetches SRI cannot cover;
//   * NEGATIVE CONTROLS, because zero violations proves nothing unless the
//     policy can refuse: fetch to example.com -> blocked (connect-src),
//     <script src=example.com> -> blocked (script-src-elem), new Function()
//     -> blocked (script-src eval);
//   * the API call failed from 127.0.0.1 and that is CORS, NOT CSP -- proven by
//     a no-cors request to the same host going out with no violation recorded.

console.log('\n%d passed, %d failed', pass, fail);
process.exit(fail ? 1 : 0);
