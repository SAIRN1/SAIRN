// tests/vercel_frame_headers.js
// OWNER: cody   written 2026-10-27, batch b52
//
// REQUIREMENT: every response from the deployment carries the HEADER form of
//   anti-framing -- `Content-Security-Policy: frame-ancestors 'none'` and
//   `X-Frame-Options: DENY` -- set in vercel.json, not only in the page.
//
// WHY: fourth b43 drove the attack and found 0 of 17 apps resisted framing.
// The inline guard (fourth b43/b44) hides a framed page, but `frame-ancestors`
// in a <meta> CSP is ignored by browsers, and a browser that ignores the
// inline guard was still unprotected. fourth's handoff left "the header form"
// open by instruction; this is it. No app embeds another (no <iframe> in any
// *.html, measured), and the satellites are link pages, never embeds, so
// 'none' rather than 'self'.
//
//   node tests/vercel_frame_headers.js       Exit: 0 pass · 1 fail · 3 could not run
//
// The deployed half is checked live by the b52 run against
// https://sairn.vercel.app, not here: this file proves the config says it.

'use strict';
const fs = require('fs');
const path = require('path');

const REPO = path.dirname(__dirname);
let cfg;
try { cfg = JSON.parse(fs.readFileSync(path.join(REPO, 'vercel.json'), 'utf8')); }
catch (e) { console.log('COULD NOT RUN: vercel.json unreadable -- ' + e.message); process.exit(3); }

let pass = 0, fail = 0;
function is(cond, label, detail) {
  if (cond) { pass++; console.log('  ok    ' + label); }
  else { fail++; console.log('  FAIL  ' + label + (detail ? '\n        ' + detail : '')); }
}

const routes = Array.isArray(cfg.routes) ? cfg.routes : [];
const first = routes[0] || {};
const h = first.headers || {};
is(first.src === '/(.*)' && first.continue === true,
   'F1. the FIRST route matches every path and continues, so its headers reach every response',
   JSON.stringify(first));
is(h['Content-Security-Policy'] === "frame-ancestors 'none'",
   "F2. Content-Security-Policy: frame-ancestors 'none'", JSON.stringify(h));
is(h['X-Frame-Options'] === 'DENY', 'F3. X-Frame-Options: DENY (for browsers without frame-ancestors)', JSON.stringify(h));
const later = routes.slice(1).filter((r) => r.headers
  && Object.keys(r.headers).some((k) => /^(x-frame-options|content-security-policy)$/i.test(k)));
is(later.length === 0, 'F4. no later route overrides either header', JSON.stringify(later));
const htmlRoutes = routes.filter((r) => /\.html$/.test(String(r.dest || '')));
is(htmlRoutes.length > 0 && routes.indexOf(htmlRoutes[0]) > 0,
   'F5. CONTROL: the app routes exist and all sit after the header route (' + htmlRoutes.length + ' of them)');
is(!('headers' in cfg),
   'F6. no top-level `headers` key -- Vercel refuses `headers` beside legacy `routes`, so the build would fail');

console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
