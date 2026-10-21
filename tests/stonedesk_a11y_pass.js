// tests/stonedesk_a11y_pass.js
// Run: node tests/stonedesk_a11y_pass.js [path-to-stonedesk.html]
//
// fourth b53 accessibility pass on StoneDesk (next in the launch wave):
// Chromium accessibility tree + axe-core 4.10.2 + real keyboard events on the
// live demo login (SD-AUDIT-2026), every write blocked. Before: 53 mouse-only
// controls, 187 unnamed fields (label x86, select-name x101), no current-page
// marking, focus left on the sidebar after navigation. After: 6 mouse-only
// (cards whose own inner controls are reachable -- deliberately skipped), 123
// unnamed (label x44, select-name x79), aria-current set, focus on the new
// panel's heading for 60/67 targets (7 have no heading at all -- filed).
//
// sdA11yPass() and sbNav() are EXTRACTED BY NAME from the shipped file and run
// in a vm; an extraction that fails exits 2 rather than testing a copy.
//
// Exit: 0 all passed - 1 an arm FAILED - 2 COULD NOT RUN

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const FILE = process.argv[2] || path.join(__dirname, '..', 'stonedesk.html');
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
function El(tag, opts) {
  opts = opts || {};
  const attrs = Object.assign({}, opts.attrs || {}), listeners = {};
  const el = { tagName: tag, id: opts.id || '', htmlFor: '', style: {}, nextElementSibling: null, clicked: 0, kids: opts.kids || [],
    classList: { add() {}, remove() {} },
    setAttribute: (k, v) => { attrs[k] = String(v); }, removeAttribute: (k) => { delete attrs[k]; },
    getAttribute: (k) => (k in attrs ? attrs[k] : null), hasAttribute: (k) => k in attrs,
    querySelector: (s) => (opts.inner && /button|input|select|textarea/.test(s) ? {} : null),
    addEventListener: (t, f) => { listeners[t] = f; }, click() { el.clicked++; }, attrs, listeners };
  return el;
}

const passSrc = grab('var SD_A11Y_BUTTON_HANDLER', '\nfunction sdA11yPass(root) {').replace(/\nfunction sdA11yPass\(root\) \{$/, '')
  + '\n' + grab('function sdA11yPass(root) {');

console.log('1. sdA11yPass: labels, keyboard buttons, decorative icons');
{
  const lab = (tag, id, nested) => { const l = El('LABEL'); const c = El(tag, { id }); l.nextElementSibling = c; if (nested) l.querySelector = () => ({}); return l; };
  const labels = [lab('SELECT', 'material'), lab('INPUT', 'q-sqft'), lab('DIV', 'x'), lab('INPUT', ''), lab('INPUT', 'wrapped', true)];
  const chip = El('DIV', { attrs: { onclick: 'selTrade(this)' } });
  const fileZone = El('DIV', { attrs: { onclick: "document.getElementById('pf-file').click()" } });
  const backdrop = El('DIV', { attrs: { onclick: 'closeModal()' } });
  const card = El('DIV', { attrs: { onclick: "sdIntegQuickAdd('x')" }, inner: true });
  const realBtn = El('BUTTON', { attrs: { onclick: "setTier('retail',this)" } });
  const icons = [El('SPAN'), El('SPAN')];
  const ctx = { getComputedStyle: () => ({ display: 'block' }),
    document: { readyState: 'complete', addEventListener() {},
      querySelectorAll: (s) => (s === 'label:not([for])' ? labels : s === '[onclick]' ? [chip, fileZone, backdrop, card, realBtn] : s === '.sb-btn .sb-icon' ? icons : []) } };
  ctx.document.querySelectorAll.bind(ctx.document);
  vm.createContext(ctx);
  vm.runInContext(passSrc.replace(/\nif \(document\.readyState[\s\S]*$/, ''), ctx);
  ctx.sdA11yPass(ctx.document);
  check('L1. a label before a select/input with an id is tied to it', labels[0].htmlFor === 'material' && labels[1].htmlFor === 'q-sqft');
  check('L2. non-controls, id-less controls and wrapping labels are left alone', labels[2].htmlFor === '' && labels[3].htmlFor === '' && labels[4].htmlFor === '');
  check('B1. an allowlisted handler div becomes a button (role, tabindex 0)', chip.attrs.role === 'button' && chip.attrs.tabindex === '0');
  check('B2. ...the file-picker zone pattern too', fileZone.attrs.role === 'button');
  chip.listeners.keydown({ key: 'Enter', preventDefault() {} }); chip.listeners.keydown({ key: ' ', preventDefault() {} }); chip.listeners.keydown({ key: 'Tab', preventDefault() {} });
  check('B3. Enter and Space activate it; other keys do not', chip.clicked === 2, chip.clicked);
  check('B4. a modal backdrop (not allowlisted) is NOT made a tab stop', !('role' in backdrop.attrs) && !('tabindex' in backdrop.attrs));
  check('B5. a card that already contains a control is skipped (no nested-interactive)', !('role' in card.attrs));
  check('B6. a native button is left alone', !('role' in realBtn.attrs));
  check('B7. the new targets get a 24px minimum height (WCAG 2.5.8)', chip.style.minHeight === '24px');
  check('I1. sidebar icons are hidden from the reader', icons.every((i) => i.attrs['aria-hidden'] === 'true'));
}

console.log('2. sbNav: current item and focus to the heading');
{
  const src = grab('function sbNav(id) {');
  const focused = [];
  const btns = { 'sb-quote': El('BUTTON', { id: 'sb-quote' }), 'sb-crm': El('BUTTON', { id: 'sb-crm' }) };
  btns['sb-quote'].setAttribute('aria-current', 'page');
  const heading = El('H2'); heading.focus = () => focused.push('crm');
  heading.offsetWidth = 10;
  const panel = El('DIV', { id: 'panel-crm' }); panel.offsetWidth = 10;
  panel.querySelectorAll = (s) => (/h1,h2,h3/.test(s) ? [heading] : []);
  const ctx = { closeSidebar() {}, showPanel() {}, sdA11yPass() {}, setTimeout: (f) => f(), Array,
    document: { getElementById: (id) => btns[id] || (id === 'panel-crm' ? panel : null),
      querySelectorAll: (s) => (s === '.sb-btn' ? Object.values(btns) : []) } };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  try { ctx.sbNav('crm'); } catch (e) { /* later render hooks are not stubbed */ }
  check('N1. aria-current moves to the chosen item and leaves the others',
    btns['sb-crm'].attrs['aria-current'] === 'page' && !('aria-current' in btns['sb-quote'].attrs));
  check('N2. focus lands on the panel\'s first heading, made focusable by script only', focused.join() === 'crm' && heading.attrs.tabindex === '-1', JSON.stringify(focused));
}

console.log('\n' + (fail ? 'FAILED' : 'ok') + '  stonedesk a11y pass: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
