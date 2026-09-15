// tests/dnt_complaint_qr.js
//
// Run:  node tests/dnt_complaint_qr.js
//
// The QR distribution half of SAIRNdental's anonymous-complaint feature.
//
// ── WHY THIS HALF NEEDED ITS OWN SUITE ─────────────────────────────────────
// Four of the five named sub-features of this system shipped in 2026-09 and
// were verified per-feature on 2026-09-15: the two-way thread, the 256-bit
// unguessable link, the no-PII record, and the nav badge. QR distribution was
// the one that never got built, and it is the one that decides whether a
// patient reaches any of the other four. A URL on a waiting-room wall is not a
// URL anybody types, and a patient who has just had a bad visit is exactly the
// person who will not type it.
//
// ── THE ARMS THAT MATTER ARE THE DEGRADATION ONES ──────────────────────────
// The library is served from a CDN, so the interesting question is not "does it
// draw a QR" -- it is what the panel does when the script is BLOCKED, which on
// a locked-down surgery network is the ordinary case rather than the exotic
// one. A silently absent QR reads as "this practice has no feedback channel",
// which is the exact opposite of what the feature exists to say. Sections 3
// and 4 drive that, in both directions.
//
// ── WHAT THIS CANNOT SEE, STATED RATHER THAN IMPLIED ───────────────────────
// It does NOT render a real QR and cannot prove one scans. `qrcodejs` is
// stubbed, so what is proven is the WIRING and the REFUSALS: which string is
// encoded, that the print path refuses rather than producing a blank poster,
// and that nothing beyond the already-public slug reaches the image. Whether
// the library draws a scannable symbol is a property of a pinned, unmodified
// third-party file, and `stonedesk.html` has been relying on it in production
// since 2026-09.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'sairndental.html'), 'utf8');
const STONEDESK = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function check(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(s) { console.log('\n' + s); }

// Pull a function out of the document by name, the same way
// tests/sairncode_gates.js reads scWriteRefusalText -- these live in an inline
// <script>, so there is nothing to require().
function grab(sig) {
  const at = APP.indexOf(sig);
  assert.ok(at > 0, 'not found in sairndental.html: ' + sig);
  let depth = 0, i = APP.indexOf('{', at);
  const start = at;
  for (; i < APP.length; i++) {
    if (APP[i] === '{') depth++;
    else if (APP[i] === '}') { depth--; if (depth === 0) return APP.slice(start, i + 1); }
  }
  throw new Error('unbalanced braces after ' + sig);
}

// ════════════════════════════════════════════════════════════════════════════
section('1. the library is loaded the way stonedesk.html loads it');
check('the script tag is present, deferred, and SRI-pinned', () => {
  const m = /qrcodejs\/1\.0\.0\/qrcode\.min\.js"\s*\n\s*integrity="(sha384-[^"]+)"\s*\n\s*crossorigin="anonymous"[^>]*defer/.exec(APP);
  assert.ok(m, 'expected a deferred, SRI-pinned, crossorigin qrcodejs tag');
});
check('the SRI hash is BYTE-IDENTICAL to the one stonedesk.html already pins', () => {
  // Two hashes for one file is the claim-in-two-places drift this repo keeps
  // recording. If someone re-derives one, this arm says so.
  const pat = /qrcodejs\/1\.0\.0\/qrcode\.min\.js"\s*\n\s*integrity="([^"]+)"/;
  const a = pat.exec(STONEDESK), b = pat.exec(APP);
  assert.ok(a && b, 'both files must pin the same library');
  assert.strictEqual(b[1], a[1],
    'sairndental pins ' + (b && b[1]) + ' but stonedesk pins ' + (a && a[1]));
});
check('crossorigin is present, or the browser never checks the hash at all', () => {
  const tag = /<script src="https:\/\/cdnjs[^>]*qrcodejs[^>]*>/s.exec(APP);
  assert.ok(tag && /crossorigin="anonymous"/.test(tag[0]), tag && tag[0]);
});
check('it is DEFERRED, so a slow CDN cannot block the app from loading', () => {
  const tag = /<script src="https:\/\/cdnjs[^>]*qrcodejs[^>]*>/s.exec(APP);
  assert.ok(tag && /\bdefer\b/.test(tag[0]));
});

// ════════════════════════════════════════════════════════════════════════════
section('2. what the QR encodes -- and what it must never encode');
const ctxBase = () => ({ console: console, encodeURIComponent: encodeURIComponent,
                         String: String, Math: Math, Error: Error });
check('it encodes the public slug URL and nothing else', () => {
  const c = vm.createContext(ctxBase());
  vm.runInContext(grab('function cpQRUrl(slug){'), c);
  const url = vm.runInContext('cpQRUrl("smilecare")', c);
  assert.strictEqual(url, 'https://sairn.vercel.app/sairndental-complaint?slug=smilecare');
});
check('the slug is URL-ENCODED, so a slug with a & cannot forge a parameter', () => {
  const c = vm.createContext(ctxBase());
  vm.runInContext(grab('function cpQRUrl(slug){'), c);
  const url = vm.runInContext('cpQRUrl("a&token=stolen")', c);
  assert.ok(url.indexOf('&token=') === -1, url);
  assert.ok(url.indexOf('a%26token%3Dstolen') !== -1, url);
});
check('the ONLY thing ever encoded is cpQRUrl(...) -- checked on the payload, '
      + 'not on prose', () => {
  // THE FIRST VERSION OF THIS ARM SEARCHED THE SOURCE FOR THE WORD "patient"
  // AND FAILED ON ITS OWN UI COPY -- the note reads "no patient or practice
  // data", which is the feature working. A scanner that reads comments and
  // display strings as payload is the my-own-comment-trips-my-own-checker
  // shape this repo has recorded before.
  //
  // The real property is narrow and structural: every `text:` handed to QRCode
  // must be exactly `cpQRUrl(...)`. Nothing else can reach the symbol.
  const src = grab('function cpRenderQR(slug){') + grab('function cpPrintQRPoster(){');
  const payloads = src.match(/text:\s*([^,}]+)/g) || [];
  assert.ok(payloads.length >= 2, 'both render paths must encode something: ' + payloads);
  payloads.forEach((p) => assert.ok(/text:\s*cpQRUrl\(/.test(p),
    'a QR payload that is not cpQRUrl(): ' + p));
});
check('...and no adversarial slug can smuggle a token into the encoded URL', () => {
  // Driven rather than read. The access_token is what makes a thread private,
  // and a QR is photographed, forwarded and stuck on a wall.
  const c = vm.createContext(ctxBase());
  vm.runInContext(grab('function cpQRUrl(slug){'), c);
  ['x&access_token=abc', 'x#access_token=abc', 'x?complaint_id=7', 'x/../admin']
    .forEach((evil) => {
      const url = vm.runInContext('cpQRUrl(' + JSON.stringify(evil) + ')', c);
      const query = url.slice(url.indexOf('?') + 1);
      assert.strictEqual(query.split('&').length, 1,
        'exactly one parameter may survive: ' + url);
      assert.ok(query.indexOf('slug=') === 0, url);
    });
});

// ════════════════════════════════════════════════════════════════════════════
section('3. DEGRADATION -- the library is absent');
function fakeDom() {
  const made = {};
  const el = (id) => {
    if (!made[id]) made[id] = { id: id, innerHTML: '', textContent: '',
                                style: {}, disabled: false, title: '' };
    return made[id];
  };
  return { el: el, made: made };
}
function runRender(withLibrary, slug) {
  const dom = fakeDom();
  const notes = [];
  const sandbox = Object.assign(ctxBase(), {
    $: dom.el,
    notify: (m, k) => notes.push([m, k])
  });
  if (withLibrary) {
    sandbox.QRCode = function (node, opts) { node.innerHTML = '<img data-text="' + opts.text + '">'; };
    sandbox.QRCode.CorrectLevel = { M: 0 };
  }
  const c = vm.createContext(sandbox);
  vm.runInContext(grab('function cpQRUrl(slug){'), c);
  vm.runInContext(grab('function cpRenderQR(slug){'), c);
  vm.runInContext('cpRenderQR(' + JSON.stringify(slug) + ')', c);
  return { dom: dom, notes: notes };
}
check('with NO library, the panel SAYS the QR is missing', () => {
  const r = runRender(false, 'smilecare');
  assert.ok(/did not load/i.test(r.dom.made['cp-qr'].innerHTML),
    'the box must name the failure: ' + r.dom.made['cp-qr'].innerHTML);
  assert.ok(/No QR code/i.test(r.dom.made['cp-qr-note'].innerHTML),
    'and so must the note');
});
check('...and it says the LINK STILL WORKS, so the channel is not read as absent', () => {
  const r = runRender(false, 'smilecare');
  assert.ok(/link above still works/i.test(r.dom.made['cp-qr-note'].innerHTML),
    'a silently missing QR reads as "this practice has no feedback channel"');
});
check('...and the print button is DISABLED rather than making a blank poster', () => {
  const r = runRender(false, 'smilecare');
  assert.strictEqual(r.dom.made['cp-qr-print'].disabled, true);
});
check('CONTROL: WITH the library, a QR is rendered and printing is enabled', () => {
  // Without this, "it degrades" is also satisfied by a feature that never works.
  const r = runRender(true, 'smilecare');
  assert.ok(/<img/.test(r.dom.made['cp-qr'].innerHTML), r.dom.made['cp-qr'].innerHTML);
  assert.strictEqual(r.dom.made['cp-qr-print'].disabled, false);
  assert.ok(/no patient or practice data/i.test(r.dom.made['cp-qr-note'].textContent));
});
check('the rendered QR carries the public URL, read back off the element', () => {
  const r = runRender(true, 'smilecare');
  assert.ok(r.dom.made['cp-qr'].innerHTML.indexOf(
    'https://sairn.vercel.app/sairndental-complaint?slug=smilecare') !== -1,
    r.dom.made['cp-qr'].innerHTML);
});
check('with NO SLUG the whole block is hidden -- no QR to a broken link', () => {
  const r = runRender(true, '');
  assert.strictEqual(r.dom.made['cp-qr-wrap'].style.display, 'none');
});
check('a library that THROWS is caught and named, not left half-rendered', () => {
  const dom = fakeDom();
  const sandbox = Object.assign(ctxBase(), { $: dom.el, notify: () => {} });
  sandbox.QRCode = function () { throw new Error('bad input'); };
  sandbox.QRCode.CorrectLevel = { M: 0 };
  const c = vm.createContext(sandbox);
  vm.runInContext(grab('function cpQRUrl(slug){'), c);
  vm.runInContext(grab('function cpRenderQR(slug){'), c);
  vm.runInContext('cpRenderQR("x")', c);
  assert.ok(/could not be rendered/i.test(dom.made['cp-qr'].innerHTML));
  assert.strictEqual(dom.made['cp-qr-print'].disabled, true);
});

// ════════════════════════════════════════════════════════════════════════════
section('4. the POSTER refuses rather than printing something useless');
function runPoster(opts) {
  const o = opts || {};
  const notes = [];
  let written = '';
  const sandbox = Object.assign(ctxBase(), {
    $: fakeDom().el,
    H: (s) => String(s || ''),
    settings: () => ({ booking_slug: o.slug, practice_name: 'Smile Care' }),
    notify: (m, k) => notes.push([m, k]),
    document: { createElement: () => ({ innerHTML: '', querySelector: (sel) =>
      (o.produceImage && sel === 'img') ? { outerHTML: '<img src="qr.png">' } : null }) },
    window: { open: () => (o.popupBlocked ? null : {
      document: { write: (h) => { written += h; }, close: () => {} }, focus: () => {} }) }
  });
  if (o.library !== false) {
    sandbox.QRCode = o.throws
      ? function () { throw new Error('nope'); }
      : function (node) { node.innerHTML = '<img src="qr.png">'; };
    sandbox.QRCode.CorrectLevel = { M: 0 };
  }
  const c = vm.createContext(sandbox);
  vm.runInContext(grab('function cpQRUrl(slug){'), c);
  vm.runInContext(grab('function cpPrintQRPoster(){'), c);
  vm.runInContext('cpPrintQRPoster()', c);
  return { notes: notes, written: written };
}
check('no slug -> refuses with a reason, opens nothing', () => {
  const r = runPoster({ slug: '', produceImage: true });
  assert.strictEqual(r.written, '');
  assert.ok(/slug/i.test(r.notes.map((n) => n[0]).join(' ')), JSON.stringify(r.notes));
});
check('no library -> REFUSES rather than printing a poster with a blank square', () => {
  const r = runPoster({ slug: 'x', library: false, produceImage: true });
  assert.strictEqual(r.written, '');
  assert.ok(/blank square/i.test(r.notes.map((n) => n[0]).join(' ')), JSON.stringify(r.notes));
});
check('the library throwing -> refuses and names the error', () => {
  const r = runPoster({ slug: 'x', throws: true, produceImage: true });
  assert.strictEqual(r.written, '');
});
check('a blocked pop-up is REPORTED, not silently nothing', () => {
  const r = runPoster({ slug: 'x', produceImage: true, popupBlocked: true });
  assert.ok(/pop-?ups/i.test(r.notes.map((n) => n[0]).join(' ')), JSON.stringify(r.notes));
});
check('CONTROL: a good run writes a poster carrying the QR and the typed URL', () => {
  const r = runPoster({ slug: 'smilecare', produceImage: true });
  assert.ok(r.written.indexOf('<img') !== -1, 'the QR image is on the poster');
  assert.ok(r.written.indexOf('sairndental-complaint?slug=smilecare') !== -1,
    'and the URL is printed underneath for anyone who cannot scan');
  assert.ok(/anonymous/i.test(r.written),
    'the poster must say the patient can stay anonymous -- that is the feature');
});
check('it does NOT auto-print: an auto-print races the image decode', () => {
  const src = grab('function cpPrintQRPoster(){');
  assert.ok(!/\bw\.print\(\)/.test(src),
    'firing print() immediately prints a blank square on a slow decode');
});

// ════════════════════════════════════════════════════════════════════════════
section('5. it is actually WIRED -- a renderer nothing calls is dormant code');
check('rComplaints() calls cpRenderQR with the slug', () => {
  assert.ok(/cpRenderQR\(s\.booking_slug\)/.test(APP),
    'the complaints render must refresh the QR, or a slug change never reaches it');
});
check('the panel carries the wrap, the box, the note and the print button', () => {
  ['cp-qr-wrap', 'cp-qr', 'cp-qr-note', 'cp-qr-print']
    .forEach((id) => assert.ok(APP.indexOf('id="' + id + '"') !== -1, id + ' missing'));
});
check('the print button is bound to the function that exists', () => {
  assert.ok(/onclick="cpPrintQRPoster\(\)"/.test(APP));
  assert.ok(/function cpPrintQRPoster\(\)\{/.test(APP));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
