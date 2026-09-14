// tests/public_token_leaves_the_address_bar.js
//
// Run:  node tests/public_token_leaves_the_address_bar.js
//
// THREE PUBLIC PAGES CARRY A CREDENTIAL IN THE QUERY STRING.
//
//   stonedesk-catalog.html      ?shop=<public>&track=<TOKEN>
//   sairndental-complaint.html  ?slug=<public>&token=<TOKEN>
//   sairnsenior.html            ?portal=<TOKEN>
//
// api/stonedesk-track.js says it in its own header: "The token IS the
// credential, like a calendar-share link -- 256-bit crypto-random, revocable,
// scoped to exactly one customer record." A credential in the address bar
// reaches the browser history, the Referer header of every outbound link, and
// every logging layer in between -- independently of what any analytics product
// does or does not store. It was the thing to fix before adding a page script,
// and it is worth fixing on its own.
//
// THE ARM THAT EARNED ITSELF IS ARM 2. The first version of this change
// replaced the whole URL with `location.pathname`, which threw away ?shop= and
// ?slug= as well. Both are PUBLIC identifiers, both are captured before the
// strip, so the FIRST LOAD still worked perfectly -- and a REFRESH would have
// shown "no shop". An identifier belongs in a shareable URL; a credential does
// not, and the difference is the whole point.
//
// The real replaceState block is extracted from each shipped page and RUN
// against a fake history, so this fails if what ships changes.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; console.log('  ok   ' + label); }

// Pull the `try{ ... }catch(e){}` block that owns the searchParams.delete call.
function grabStrip(file) {
  const src = fs.readFileSync(path.join(ROOT, file), 'utf8').replace(/\r\n/g, '\n');
  const del = src.indexOf('_u.searchParams.delete(');
  assert.ok(del > 0, file + ': no searchParams.delete -- the strip is gone');
  const start = src.lastIndexOf('try{', del);
  const end = src.indexOf('}catch(e){}', del);
  assert.ok(start > 0 && end > start, file + ': could not bound the strip block');
  return src.slice(start, end + '}catch(e){}'.length);
}

// Run one strip block against a URL and report what the address bar ends up as.
function runStrip(file, href) {
  let finalUrl = href;
  const sandbox = {
    URL: URL,
    window: {
      location: { href: href },
      history: { replaceState: (_s, _t, url) => { finalUrl = url; } }
    },
    document: { title: 't' }
  };
  vm.createContext(sandbox);
  vm.runInContext(grabStrip(file), sandbox);
  return finalUrl;
}

const CASES = [
  { file: 'stonedesk-catalog.html', cred: 'track', keep: 'shop',
    href: 'https://sairn.vercel.app/stonedesk-catalog?shop=westlake&track=SECRET123' },
  { file: 'sairndental-complaint.html', cred: 'token', keep: 'slug',
    href: 'https://sairn.vercel.app/sairndental-complaint?slug=smilecare&token=SECRET123' },
  { file: 'sairnsenior.html', cred: 'portal', keep: null,
    href: 'https://sairn.vercel.app/sairnsenior?portal=SECRET123' }
];

console.log('a public token does not stay in the address bar\n');

console.log('1. the credential is removed');
for (const c of CASES) {
  const out = runStrip(c.file, c.href);
  ok(out.indexOf('SECRET123') === -1,
     c.file + ': the token value is gone from the URL');
  ok(out.indexOf(c.cred + '=') === -1,
     c.file + ': and so is the ?' + c.cred + '= key');
}

console.log('\n2. THE PUBLIC IDENTIFIER SURVIVES -- the arm that earned itself');
for (const c of CASES.filter(x => x.keep)) {
  const out = runStrip(c.file, c.href);
  ok(out.indexOf(c.keep + '=') !== -1,
     c.file + ': ?' + c.keep + '= is still there, so a REFRESH still works');
}

console.log('\n3. CONTROL -- a URL with no credential is left completely alone');
for (const c of CASES.filter(x => x.keep)) {
  const clean = 'https://sairn.vercel.app/x?' + c.keep + '=westlake';
  ok(runStrip(c.file, clean) === clean,
     c.file + ': replaceState is not called at all when there is nothing to strip');
}
// Without this the strip could be rewriting every URL unconditionally and
// arms 1 and 2 would both still pass.
ok(runStrip('sairnsenior.html', 'https://sairn.vercel.app/sairnsenior')
   === 'https://sairn.vercel.app/sairnsenior',
   'sairnsenior.html: a bare URL is untouched');

console.log('\n4. the analytics script is on every root app page, and only once');
// ── TRACKED FILES, NOT WHATEVER IS ON DISK. Hardened 2026-09-14. ──────────
// This read `fs.readdirSync(ROOT)` and so asserted over every .html sitting in
// a clone's working directory, untracked ones included. An untracked
// `piac.html` turned this suite RED while it was GREEN on a clean origin/main
// worktree, verified. THE RULE LIVES IN tests/rootpages.js because three other
// suites had the same shape and survived it by luck -- four copies of a rule is
// four places for it to drift.
const roots = require('./rootpages.js').rootPages(ROOT);
let withScript = 0;
for (const f of roots) {
  const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
  const hits = (src.match(/_vercel\/insights\/script\.js/g) || []).length;
  assert.strictEqual(hits, 1, f + ': expected exactly 1 insights script, found ' + hits);
  withScript++;
}
ok(withScript === roots.length && roots.length >= 20,
   'all ' + roots.length + ' root app pages carry it exactly once');

// stonedesk.html has 64 `</head>` and 63 of them build PRINTABLE documents
// inside document.write strings. A blind insert would have put a tracker in a
// printed quote.
const sd = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const firstHead = sd.indexOf('</head>');
const scriptAt = sd.indexOf('_vercel/insights/script.js');
ok(scriptAt > 0 && scriptAt < firstHead,
   'stonedesk.html: it sits before the FIRST </head>, not inside one of the 63 printed ones');

console.log('\nALL ' + n + ' ASSERTIONS PASS');
