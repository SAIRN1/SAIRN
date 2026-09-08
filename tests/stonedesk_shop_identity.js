// tests/stonedesk_shop_identity.js
//
// Run:  node tests/stonedesk_shop_identity.js
//
// Every export, print header, customer message template and AI prompt in
// stonedesk.html named ONE shop: "Pinnacle Stone & Design", with its phone
// ((216) 847-3200 / (555) 847-3200), its address and its domain. The
// open-work row estimated "roughly a dozen" sites from a grep and said to
// enumerate before editing. Enumerated: 132 lines, across
//
//   * ~30 CSV download filenames -- a fabricator in Ohio downloaded
//     `customers-pinnacle-2026-09-08.csv`
//   * ~70 print and render headers, titles and footers
//   * 12 AI prompts, so the advisor believed it worked for another company
//   * the SMS and email templates a shop sends to ITS OWN customers, signed
//     with another company's name AND another company's phone number
//
// THE STORAGE ALREADY EXISTED. fab_shop_name / fab_shop_addr / fab_shop_phone
// / fab_shop_email are written by the admin Company Profile form. What was
// missing was readers, so this suite guards the readers and the absence of the
// literals -- not one or the other, because either alone passes while the
// other is broken.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const FILE = path.join(__dirname, '..', 'stonedesk.html');
const html = fs.readFileSync(FILE, 'utf8');
const lines = html.split('\n');

let pass = 0, fail = 0;
const queue = [];
function test(n, f) { queue.push({ n, f }); }
function section(t) { queue.push({ section: t }); }

// The ONLY lines allowed to keep the literal, each for a stated reason. This
// list is the whole judgement in this suite: everything not on it is output a
// customer sees.
function allowed(line) {
  const s = line.trim();
  if (s.startsWith('//') || s.startsWith('*') || s.startsWith('/*')) return 'comment';
  if (s.startsWith("{id:'RV-")) return 'seeded demo review';
  if (s.indexOf('placeholder=') !== -1 && s.indexOf('ag-shop') !== -1) return 'form placeholder';
  if (s.indexOf('Show seeded') !== -1) return 'demo-mode toggle label';
  if (s.indexOf('SD-PINNACLE-2026') !== -1) return 'the demo LICENCE KEY, an identifier';
  // The seeded employee roster carries the demo owner's own contact details --
  // the same case as the seeded reviews. Demo data describing the demo shop is
  // correct; it is only wrong when it describes a REAL customer's shop.
  if (/^\{name:'[^']+',role:'/.test(s)) return 'seeded demo employee row';
  return null;
}

section('the literals are gone from everything a customer sees');

[['Pinnacle Stone', 'the shop name'],
 ['847-3200', 'the shop phone'],
 ['pinnaclesd.com', 'the shop domain'],
 ['4821 Industrial Pkwy', 'the shop address'],
 ['-pinnacle-', 'the export filename slug']].forEach(([needle, what]) => {
  test('no customer-facing line still hardcodes ' + what, () => {
    const hits = [];
    lines.forEach((l, i) => {
      if (l.indexOf(needle) === -1) return;
      if (allowed(l)) return;
      hits.push((i + 1) + ': ' + l.trim().slice(0, 120));
    });
    assert.deepStrictEqual(hits, [], hits.length + ' site(s):\n    ' + hits.join('\n    '));
  });
});

test('...and the allow-list is not swallowing the whole file', () => {
  // A leave-rule broad enough to match everything would make every assertion
  // above vacuously true.
  const allowedLines = lines.filter((l) => l.indexOf('innacle') !== -1 && allowed(l));
  assert.ok(allowedLines.length <= 12,
    'the allow-list now covers ' + allowedLines.length + ' lines -- it is doing the work the checks should');
  assert.ok(allowedLines.length >= 1, 'nothing is allow-listed; the demo seed data was scrubbed too');
});

section('the readers exist and behave');

function loadAccessors(store) {
  const start = html.indexOf('function sdShopRaw(key){');
  const end = html.indexOf('window.sdShopName=sdShopName;');
  assert.ok(start > 0 && end > start, 'the accessor block is gone from stonedesk.html');
  const ctx = {
    localStorage: { getItem: (k) => (store[k] === undefined ? null : store[k]) },
  };
  vm.createContext(ctx);
  vm.runInContext(html.slice(start, end), ctx);
  return ctx;
}

test('an unconfigured shop gets a generic name, never a real company', () => {
  const c = loadAccessors({});
  assert.strictEqual(c.sdShopName(), 'Your Stone Shop');
  assert.strictEqual(c.sdShopSlug(), 'your-stone-shop');
  assert.ok(!/pinnacle/i.test(c.sdShopName()), 'the fallback names a real company');
});

test('a configured shop is read from the key the admin form actually writes', () => {
  // fab_shop_name, not sd_shop_name. Both existed; only one has a writer.
  const c = loadAccessors({ fab_shop_name: '  Keystone Granite  ' });
  assert.strictEqual(c.sdShopName(), 'Keystone Granite', 'not trimmed, or the wrong key');
});

test('contact details are EMPTY when unset, not a placeholder', () => {
  // Printing "Phone: your phone here" on a customer's quote is worse than
  // printing nothing, and callers can only omit a line if it is falsy.
  const c = loadAccessors({});
  assert.strictEqual(c.sdShopPhone(), '');
  assert.strictEqual(c.sdShopEmail(), '');
  assert.strictEqual(c.sdShopAddr(), '');
  assert.strictEqual(c.sdShopContactLine(), 'Your Stone Shop',
    'the contact line left a dangling separator for unset fields');
});

test('the contact line joins only what is set', () => {
  const c = loadAccessors({ fab_shop_name: 'Keystone', fab_shop_email: 'hi@keystone.example' });
  assert.strictEqual(c.sdShopContactLine(), 'Keystone | hi@keystone.example');
});

test('a filename slug is safe for a shop with punctuation in its name', () => {
  const c = loadAccessors({ fab_shop_name: "O'Brien & Sons, Ltd." });
  assert.strictEqual(c.sdShopSlug(), 'o-brien-sons-ltd');
  assert.ok(!/[^a-z0-9-]/.test(c.sdShopSlug()), 'a slash or quote could reach a filename');
  assert.strictEqual(loadAccessors({ fab_shop_name: '!!!' }).sdShopSlug(), 'shop',
    'a name of pure punctuation produced an empty filename segment');
});

test('a storage failure returns the fallback rather than throwing', () => {
  const start = html.indexOf('function sdShopRaw(key){');
  const end = html.indexOf('window.sdShopName=sdShopName;');
  const ctx = { localStorage: { getItem() { throw new Error('storage disabled'); } } };
  vm.createContext(ctx);
  vm.runInContext(html.slice(start, end), ctx);
  assert.strictEqual(ctx.sdShopName(), 'Your Stone Shop');
});

section('the static markup is filled at runtime');

test('the spans exist, and their fallback text is generic', () => {
  const spans = html.match(/<span class="sd-shop-name">([^<]*)<\/span>/g) || [];
  assert.ok(spans.length >= 5, 'expected the panel subtitles and the AI greeting, found ' + spans.length);
  spans.forEach((s) => assert.ok(!/pinnacle/i.test(s), 'a span still falls back to a real company: ' + s));
});

test('sdFillShopName writes textContent, not innerHTML', () => {
  // A shop name is user input and this is the one place it reaches the DOM
  // without escHtml().
  const i = html.indexOf('function sdFillShopName(){');
  assert.ok(i > 0, 'the filler is gone');
  const body = html.slice(i, html.indexOf('window.sdFillShopName'));
  assert.ok(body.indexOf('textContent') !== -1, 'the filler does not set textContent');
  assert.ok(body.indexOf('innerHTML') === -1, 'the filler sets innerHTML on user input');
});

test('the real filler fills every span', () => {
  const i = html.indexOf('function sdFillShopName(){');
  const filled = [];
  const ctx = {
    sdShopName: () => 'Keystone Granite',
    document: { querySelectorAll: () => [{ set textContent(v) { filled.push(v); } },
                                         { set textContent(v) { filled.push(v); } }] },
  };
  vm.createContext(ctx);
  vm.runInContext(html.slice(i, html.indexOf('window.sdFillShopName')), ctx);
  ctx.sdFillShopName();
  assert.deepStrictEqual(filled, ['Keystone Granite', 'Keystone Granite']);
});

section('the export filenames really use the slug');

test('every CSV export that names a shop names the CALLER\'s shop', () => {
  // DELIBERATELY NOT "every export must carry the shop name". Eleven exports
  // (slabs-, saw-ticket-, manifest-, stonedesk-*) never named any shop and are
  // left alone: they were not the defect, and widening the rule to them would
  // be a new requirement rather than this fix. Recorded in the open-work row
  // instead. What must never come back is an export named for a FIXED shop.
  const downloads = lines.filter((l) => l.indexOf('a.download=') !== -1 && l.indexOf('.csv') !== -1);
  assert.ok(downloads.length >= 25, 'only found ' + downloads.length + ' csv downloads to check');
  const named = downloads.filter((l) => l.indexOf('sdShopSlug()') !== -1);
  assert.ok(named.length >= 25,
    'only ' + named.length + ' exports name the caller\'s shop -- the sweep shrank');
  const fixed = downloads.filter((l) => /-(pinnacle|acme|demo-shop)-/.test(l));
  assert.deepStrictEqual(fixed, [], 'an export is named for a fixed shop again');
});

(async () => {
  for (const item of queue) {
    if (item.section) { console.log('--- ' + item.section + ' ---'); continue; }
    try { await item.f(); console.log('  ok   ' + item.n); pass++; }
    catch (e) { console.log('  FAIL ' + item.n + '\n       ' + e.message); fail++; }
  }
  console.log('\nstonedesk_shop_identity: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
