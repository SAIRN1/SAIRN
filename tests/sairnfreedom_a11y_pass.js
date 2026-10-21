// tests/sairnfreedom_a11y_pass.js
// Run: node tests/sairnfreedom_a11y_pass.js [path-to-sairnfreedom.html]
//
// fourth b52 accessibility pass on SAIRNveterans (sairnfreedom.html), next in
// the launch wave: Chromium accessibility tree + axe-core 4.10.2 + real
// keyboard events on the live demo login (SF-PINNACLE-2026), writes blocked.
// Before: the WHOLE sidebar was <div onclick> -- no panel reachable by
// keyboard -- and 168 axe nodes (label x106, select-name x62: every field
// written <label>Text</label><input id> with no for=); Enter did nothing on
// the licence and sign-in fields; no current marking; panel changes silent.
// After: 0 axe nodes, 28/28 sidebar items are buttons, focus lands on the new
// panel's heading 28/28, Enter submits both sign-in steps.
//
// Each fix is pinned against the SHIPPED file, extracted by name; an
// extraction that fails exits 2 rather than testing a copy.
//
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'sairnfreedom.html');
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
function El(tag, id, cls) {
  const attrs = {}, classes = new Set((cls || '').split(' ').filter(Boolean));
  return { tagName: tag, id, attrs, htmlFor: '', textContent: '', nextElementSibling: null,
    classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c), contains: (c) => classes.has(c) },
    setAttribute: (k, v) => { attrs[k] = String(v); }, removeAttribute: (k) => { delete attrs[k]; },
    getAttribute: (k) => (k in attrs ? attrs[k] : null), querySelector: () => null };
}

console.log('1. the sidebar is reachable by keyboard');
{
  const nav = html.slice(html.indexOf('<nav>'), html.indexOf('</nav>'));
  const divs = (nav.match(/<div class="nitem/g) || []).length;
  const btns = (nav.match(/<button type="button" class="nitem[^"]*" id="nav-[a-z-]+"/g) || []).length;
  check('K1. every sidebar item is a <button type="button"> (none is a div)', divs === 0 && btns >= 28, 'divs=' + divs + ' buttons=' + btns);
  check('K2. Dashboard is marked current in the markup', /id="nav-dashboard" aria-current="page"/.test(nav));
  check('K3. Enter on the licence field unlocks, and on the PIN field signs in',
    /id="lic"[^>]*onkeydown="if\(event\.key==='Enter'\)sfUnlock\(\)"/.test(html) && /id="l-pin"[^>]*onkeydown="if\(event\.key==='Enter'\)sfLogin\(\)"/.test(html));
}

console.log('2. every visible label names its control');
{
  const iife = grab("(function(){var ls=document.querySelectorAll('label:not([for])');", '})();');
  const mk = (ctlTag, id, nested) => { const l = El('LABEL'); const c = El(ctlTag, id); l.nextElementSibling = c; if (nested) l.querySelector = () => ({}); return { l, c }; };
  const cases = [mk('INPUT', 'a1'), mk('SELECT', 's1'), mk('TEXTAREA', 't1'), mk('INPUT', ''), mk('DIV', 'd1'), mk('INPUT', 'n1', true)];
  const ctx = { document: { querySelectorAll: () => cases.map((x) => x.l) } };
  vm.createContext(ctx); vm.runInContext(iife, ctx);
  check('L1. a label before an input / select / textarea with an id is tied to it',
    cases[0].l.htmlFor === 'a1' && cases[1].l.htmlFor === 's1' && cases[2].l.htmlFor === 't1', cases.map((x) => x.l.htmlFor).join(','));
  check('L2. a control with no id, a non-control, and a label wrapping its own control are left alone',
    cases[3].l.htmlFor === '' && cases[4].l.htmlFor === '' && cases[5].l.htmlFor === '');
  check('L3. the district import file input has a name', /id="ds-import" aria-label="Import post reports \(JSON files\)"/.test(html));
}

console.log('3. headings, current item and focus on navigation');
{
  const heads = grab("(function(){var ts=document.querySelectorAll('.panel .ptitle');", '})();');
  const n = (html.match(/class="ptitle"/g) || []).length;
  const ts = Array.from({ length: n }, (_, i) => El('DIV', 't' + i, 'ptitle'));
  let ctx = { document: { querySelectorAll: () => ts } };
  vm.createContext(ctx); vm.runInContext(heads, ctx);
  check('H1. all ' + n + ' panel titles become level-2 headings', n >= 27 && ts.every((t) => t.attrs.role === 'heading' && t.attrs['aria-level'] === '2'), n);

  const src = grab('function sfNav(id){');
  const focused = [];
  const items = {}, panels = {};
  ['dashboard', 'members', 'access'].forEach((id) => {
    items['nav-' + id] = El('BUTTON', 'nav-' + id, 'nitem');
    const title = El(id === 'access' ? 'H3' : 'DIV', 't-' + id, id === 'access' ? '' : 'ptitle'); title.focus = () => focused.push(id);
    panels['panel-' + id] = Object.assign(El('DIV', 'panel-' + id, 'panel'), {
      querySelector: (s) => (s === '.ptitle' ? (id === 'access' ? null : title) : s === 'h1,h2,h3' ? title : null), _t: title });
  });
  items['nav-dashboard'].setAttribute('aria-current', 'page');
  ctx = { $: (id) => items[id] || panels[id] || null, sfRenderAccess() {},
    document: { querySelectorAll: (s) => (s === '.nitem' ? Object.values(items) : s === '.panel' ? Object.values(panels) : []) } };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  try { ctx.sfNav('members'); } catch (e) { /* later renderers are not stubbed */ }
  check('N1. aria-current moves to the chosen item and leaves the others',
    items['nav-members'].attrs['aria-current'] === 'page' && !('aria-current' in items['nav-dashboard'].attrs));
  check('N2. focus lands on the new panel\'s heading (tabindex=-1)', focused.join() === 'members' && panels['panel-members']._t.attrs.tabindex === '-1', JSON.stringify(focused));
  try { ctx.sfNav('access'); } catch (e) {}
  check('N3. a panel with no .ptitle (Access) falls back to its first heading', focused.join() === 'members,access', JSON.stringify(focused));
}

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  sairnfreedom a11y pass: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
