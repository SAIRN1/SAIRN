// tests/sairnlegacy_a11y_pass.js
// Run: node tests/sairnlegacy_a11y_pass.js [path-to-sairnlegacy.html]
//
// fourth b51 accessibility pass on SAIRNlegacy (first in the launch wave):
// Chromium accessibility tree + axe-core 4.10.2 + real keyboard events on the
// live demo login (LEG-PINNACLE-2026), every write blocked. Before: 88 axe
// nodes (70 colour-contrast on the 11px KPI captions, 12 unlabelled inputs,
// 6 unnamed selects), no heading in any of 27 panels, no current marking, a
// panel change silent to a screen reader, 4 mouse-only AI prompt chips.
// After: 0 axe nodes, 27/27 headings, current marked, focus on the new
// panel's heading for 27/27, the chips are buttons.
//
// Each fix is pinned against the SHIPPED file, extracted by name; an
// extraction that fails exits 2 rather than testing a copy.
//
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnlegacy.html');
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
function El(id, cls) {
  const attrs = {}, classes = new Set((cls || '').split(' ').filter(Boolean));
  return { id, attrs, textContent: '',
    classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c), contains: (c) => classes.has(c) },
    setAttribute: (k, v) => { attrs[k] = String(v); }, removeAttribute: (k) => { delete attrs[k]; },
    getAttribute: (k) => (k in attrs ? attrs[k] : null), querySelector: () => null };
}
// WCAG relative luminance contrast against white.
function contrastOnWhite(hex) {
  const c = hex.replace('#', '').match(/../g).map((h) => parseInt(h, 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  const L = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  return 1.05 / (L + 0.05);
}

console.log('1. headings, current item, focus on navigation');
{
  const line = grab("document.querySelectorAll('.panel .ptitle').forEach(", '\n');
  const n = (html.match(/class="ptitle"/g) || []).length;
  const titles = Array.from({ length: n }, (_, i) => El('t' + i, 'ptitle'));
  let ctx = { document: { querySelectorAll: (s) => (s === '.panel .ptitle' ? titles : []) } };
  vm.createContext(ctx); vm.runInContext(line, ctx);
  check('H1. all ' + n + ' panel titles become level-2 headings', n >= 27 && titles.every((t) => t.attrs.role === 'heading' && t.attrs['aria-level'] === '2'), n);

  const src = grab('function nav(id){');
  const focused = [];
  const sbs = {}, panels = {};
  ['dashboard', 'cases'].forEach((id) => {
    sbs['sb-' + id] = El('sb-' + id, 'sb');
    const t = Object.assign(El('t-' + id, 'ptitle'), { focus() { focused.push(id); } });
    panels['panel-' + id] = Object.assign(El('panel-' + id, 'panel'), { querySelector: (s) => (s === '.ptitle' ? t : null), _t: t });
  });
  sbs['sb-dashboard'].setAttribute('aria-current', 'page');
  ctx = { closeNav() {}, $: (id) => sbs[id] || panels[id] || null,
    document: { querySelectorAll: (s) => (s === '.sb' ? Object.values(sbs) : s === '.panel' ? Object.values(panels) : []) } };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  try { ctx.nav('cases'); } catch (e) { /* panel renderers are not stubbed; the a11y work happens first */ }
  check('N1. aria-current="page" moves to the chosen item and leaves the others',
    sbs['sb-cases'].attrs['aria-current'] === 'page' && !('aria-current' in sbs['sb-dashboard'].attrs));
  check('N2. focus lands on the new panel\'s heading', focused.join() === 'cases', JSON.stringify(focused));
  check('N3. the heading is focusable by script only (tabindex=-1)', panels['panel-cases']._t.attrs.tabindex === '-1');
  check('N4. the initial markup marks Dashboard current', /id="sb-dashboard" aria-current="page"/.test(html));
}

console.log('2. every form control has a name');
{
  ['sec-new-eid', 'sec-new-name', 'sec-new-role', 'sec-new-pin', 'sec-share-eid', 'cclogcase', 'obcase', 'mmcase', 'accase', 'prcase']
    .forEach((id) => check('L. <label for="' + id + '"> is tied to its control', html.indexOf('<label for="' + id + '">') !== -1));
  const row = grab("<td><input id=\"gplprice-'+s.id+'\"", '\n');
  check('L. each GPL price input is named for its service', /aria-label="Price for '\+H\(s\.category\)\+'"/.test(row), row);
}

console.log('3. KPI captions meet 4.5:1 and the AI chips are buttons');
{
  const kt = (html.match(/\n\.kt\{[^}]*color:(#[0-9A-Fa-f]{6})/) || [])[1];
  const ktd = (html.match(/\n\.kt\.d\{color:(#[0-9A-Fa-f]{6})/) || [])[1];
  check('K1. .kt caption colour is a literal with >= 4.5:1 on white', kt && contrastOnWhite(kt) >= 4.5, kt + ' ' + (kt && contrastOnWhite(kt).toFixed(2)));
  check('K2. .kt.d caption colour >= 4.5:1 on white', ktd && contrastOnWhite(ktd) >= 4.5, ktd + ' ' + (ktd && contrastOnWhite(ktd).toFixed(2)));
  const chips = html.match(/<(\w+)[^>]*class="qt"[^>]*>/g) || [];
  check('Q1. all four AI prompt chips are <button type="button">', chips.length === 4 && chips.every((c) => /^<button type="button"/.test(c)), chips.join(' | '));
}

console.log('4. (b52, from the real NVDA run) sidebar emoji icons are hidden from the reader');
{
  const line = grab("document.querySelectorAll('.sb .sico').forEach(", '\n');
  const icons = Array.from({ length: (html.match(/class="sico"/g) || []).length }, (_, i) => El('i' + i, 'sico'));
  const ctx = { document: { querySelectorAll: (s) => (s === '.sb .sico' ? icons : []) } };
  vm.createContext(ctx); vm.runInContext(line, ctx);
  check('E1. every sidebar .sico gets aria-hidden="true" (NVDA read "bar chart Dashboard")',
    icons.length >= 23 && icons.every((x) => x.attrs['aria-hidden'] === 'true'), icons.length);
}

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnlegacy a11y pass: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
