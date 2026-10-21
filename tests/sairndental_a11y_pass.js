// tests/sairndental_a11y_pass.js
// Run: node tests/sairndental_a11y_pass.js [path-to-sairndental.html]
//
// fourth b50 screen-reader / keyboard pass on sairndental. The pass itself was
// driven live (Chromium accessibility tree + axe-core 4.10.2 + real keyboard
// events, real demo login, every write blocked) -- NOT NVDA, which is not
// installed on the build machine. Before: 21 axe nodes (20 unlabelled vendor
// quantity boxes, 1 QR image with no alt), no heading in any of the 23 panels,
// no current-page marking, and the insurance-card drop zone unreachable by
// keyboard. After: 0 axe nodes, 23/23 headings, current marked, drop zone
// reached by Tab and opened by Enter.
//
// This suite pins each fix against the SHIPPED file, extracting by name; an
// extraction that fails exits 2 rather than testing a copy.
//
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairndental.html');
const html = fs.readFileSync(FILE, 'utf8').replace(/\r\n/g, '\n');
function grab(head, end) {
  const i = html.indexOf(head);
  if (i < 0 || html.indexOf(head, i + 1) !== -1) {
    console.log('COULD NOT RUN: "' + head.slice(0, 60) + '" found ' + (i < 0 ? 0 : 'more than one') + ' time(s) in ' + FILE);
    process.exit(2);
  }
  return html.slice(i, html.indexOf(end || '\n}\n', i) + (end ? end.length : 2));
}

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '\n       ' + String(detail).slice(0, 300) : '')); }
}

// A minimal element: attributes, classList, children by selector.
function El(id, cls) {
  const attrs = {}, classes = new Set((cls || '').split(' ').filter(Boolean));
  return { id, attrs, textContent: '',
    classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c), contains: (c) => classes.has(c) },
    setAttribute: (k, v) => { attrs[k] = String(v); }, removeAttribute: (k) => { delete attrs[k]; },
    getAttribute: (k) => (k in attrs ? attrs[k] : null), querySelector: () => null };
}

console.log('1. every panel title is a level-2 heading');
{
  const line = grab("document.querySelectorAll('.panel .ptitle').forEach(", '\n');
  const titles = Array.from({ length: (html.match(/class="ptitle"/g) || []).length }, (_, i) => El('t' + i, 'ptitle'));
  const ctx = { document: { querySelectorAll: (sel) => (sel === '.panel .ptitle' ? titles : []) } };
  vm.createContext(ctx); vm.runInContext(line, ctx);
  check('H1. all ' + titles.length + ' .ptitle elements get role=heading aria-level=2',
    titles.length >= 23 && titles.every((t) => t.attrs.role === 'heading' && t.attrs['aria-level'] === '2'), titles.length);
  check('H2. it runs at load, before nav() is defined (no call site to forget)',
    html.indexOf(line) < html.indexOf('function nav(id){') && html.indexOf(line) > html.lastIndexOf('class="ptitle"'));
}

console.log('2. the current sidebar item is marked for a screen reader');
{
  const src = grab('function nav(id){');
  const sbs = {}, panels = {};
  ['dashboard', 'patients', 'billing'].forEach((id) => { sbs['sb-' + id] = El('sb-' + id, 'sb'); panels['panel-' + id] = El('panel-' + id, 'panel'); });
  sbs['sb-dashboard'].setAttribute('aria-current', 'page');
  const ctx = { closeNav() {}, $: (id) => sbs[id] || panels[id] || (id === 'nav-announce' ? El('nav-announce') : null),
    document: { querySelectorAll: (sel) => (sel === '.sb' ? Object.values(sbs) : sel === '.panel' ? Object.values(panels) : []) } };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  try { ctx.nav('billing'); } catch (e) { /* panel renderers are not stubbed; the marking happens first */ }
  check('C1. nav() moves aria-current="page" to the chosen item', sbs['sb-billing'].attrs['aria-current'] === 'page', JSON.stringify(sbs['sb-billing'].attrs));
  check('C2. ...and removes it from every other item', !('aria-current' in sbs['sb-dashboard'].attrs) && !('aria-current' in sbs['sb-patients'].attrs));
  check('C3. the initial markup marks Dashboard current', /id="sb-dashboard" aria-current="page"/.test(html));
}

console.log('3. every vendor quantity box is named for its product');
{
  const row = grab("'<td><input type=\"number\" min=\"0\" value=\"'+(cart[p.id]||0)+'\" id=\"vqty-'", '\n');
  check('V1. the quantity input carries aria-label="Quantity of <product>"', /aria-label="Quantity of '\+H\(p\.name\)\+'"/.test(row), row.slice(0, 200));
}

console.log('4. the QR image says what it encodes');
{
  const src = grab('function cpRenderQR(slug){');
  const img = { alt: '' }, canvas = El('c');
  const box = Object.assign(El('cp-qr'), { innerHTML: '', querySelector: (s) => (s === 'img' ? img : s === 'canvas' ? canvas : null) });
  const els = { 'cp-qr-wrap': Object.assign(El('w'), { style: {} }), 'cp-qr': box, 'cp-qr-note': El('n'), 'cp-qr-print': El('b') };
  const ctx = { $: (id) => els[id], cpQRUrl: (s) => 'https://x/c?slug=' + s,
    QRCode: Object.assign(function () {}, { CorrectLevel: { M: 0 } }) };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  ctx.cpRenderQR('demo');
  check('Q1. the QR <img> gets alt text naming the link it encodes', /QR code/.test(img.alt) && img.alt.indexOf('https://x/c?slug=demo') !== -1, img.alt);
  check('Q2. the library\'s twin <canvas> is hidden from the reader', canvas.attrs['aria-hidden'] === 'true');
}

console.log('5. the insurance-card drop zone is a keyboard button');
{
  const tag = grab('<div class="icap-drop"', '>');
  check('K1. role="button" and tabindex="0"', /role="button"/.test(tag) && /tabindex="0"/.test(tag), tag);
  const fired = [];
  const ctx = { document: { getElementById: () => ({ click: () => fired.push('click') }) } };
  vm.createContext(ctx);
  const key = (tag.match(/onkeydown="([^"]*)"/) || [])[1] || '';
  const run = (k) => { const ev = { key: k, preventDefault() {} }; vm.runInContext('(function(event){' + key + '})', ctx)(ev); };
  run('Enter'); run(' '); run('Tab');
  check('K2. Enter and Space open the file picker; other keys do not', fired.length === 2, JSON.stringify(fired));
}

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairndental a11y pass: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
