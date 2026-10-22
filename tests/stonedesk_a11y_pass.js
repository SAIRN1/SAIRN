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
    querySelector: (s) => ((opts.inner || opts.hiddenInner) && /button|input|select|textarea/.test(s) ? {} : null),
    querySelectorAll: (s) => (/button|input|select|textarea/.test(s) ? (opts.inner ? [{ type: 'text', parentElement: null }] : opts.hiddenInner ? [{ type: 'file', _display: 'none', parentElement: null }] : []) : []),
    addEventListener: (t, f) => { listeners[t] = f; }, click() { el.clicked++; }, attrs, listeners };
  return el;
}

const passSrc = grab('var SD_A11Y_NAMES = {','\nfunction sdA11yPass(root) {').replace(/\nfunction sdA11yPass\(root\) \{$/, '')
  + '\n' + grab('function sdA11yPass(root) {');

console.log('1. sdA11yPass: labels, keyboard buttons, decorative icons');
{
  const lab = (tag, id, nested) => { const l = El('LABEL'); const c = El(tag, { id }); l.nextElementSibling = c; if (nested) l.querySelector = () => ({}); return l; };
  const labels = [lab('SELECT', 'material'), lab('INPUT', 'q-sqft'), lab('DIV', 'x'), lab('INPUT', ''), lab('INPUT', 'wrapped', true)];
  const chip = El('DIV', { attrs: { onclick: 'selTrade(this)' } });
  const fileZone = El('DIV', { attrs: { onclick: "document.getElementById('pf-file').click()" } });
  const backdrop = El('DIV', { attrs: { onclick: 'closeModal()' } });
  const card = El('DIV', { attrs: { onclick: "sdIntegQuickAdd('x')" }, inner: true });
  const upzone = El('DIV', { attrs: { onclick: "document.getElementById('doc-scan-file').click()" }, hiddenInner: true });
  const realBtn = El('BUTTON', { attrs: { onclick: "setTier('retail',this)" } });
  const icons = [El('SPAN'), El('SPAN')];
  const ctx = { getComputedStyle: (e) => ({ display: (e && e._display) || 'block' }),
    document: { readyState: 'complete', addEventListener() {}, getElementById: () => null, querySelector: () => null,
      querySelectorAll: (s) => (s === 'label:not([for])' ? labels : s === '[onclick]' ? [chip, fileZone, backdrop, card, realBtn, upzone] : s === '.sb-btn .sb-icon' ? icons : []) } };
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
  check('B8. a zone whose only inner control is a HIDDEN file input still becomes a button (doc-scan, b55)', upzone.attrs.role === 'button' && upzone.attrs.tabindex === '0');
  check('B6. a native button is left alone', !('role' in realBtn.attrs));
  check('B7. the new targets get a 24px minimum height (WCAG 2.5.8)', chip.style.minHeight === '24px');
  check('I1. sidebar icons are hidden from the reader', icons.every((i) => i.attrs['aria-hidden'] === 'true'));
}

console.log('2. b54: written names, a heading for every panel');
{
  // names: an unnamed control gets its written name; a labelled or aria-labelled one keeps its own
  const sel = El('SELECT', { id: 'int-budget' }); sel.labels = [];
  const labelled = El('SELECT', { id: 'crm-stage' }); labelled.labels = [{}];
  const own = El('SELECT', { id: 'tax-state', attrs: { 'aria-label': 'Ship-to state' } }); own.labels = [];
  const byId = { 'int-budget': sel, 'crm-stage': labelled, 'tax-state': own };
  // headings: a .ptitle becomes a level-2 heading; a panel with none gets a hidden h2 named from its sidebar item
  const ptitle = El('DIV');
  const kids = [];
  const bare = El('DIV', { id: 'panel-quote' }); bare.firstChild = null; bare.insertBefore = (h) => kids.push(h); bare.querySelector = () => null;
  const titled = El('DIV', { id: 'panel-crm' }); titled.insertBefore = () => { throw new Error('inserted into a panel that has a heading'); }; titled.querySelector = () => ({});
  const nameless = El('DIV', { id: 'panel-zzz' }); nameless.insertBefore = () => { throw new Error('inserted with no sidebar name'); }; nameless.querySelector = () => null;
  const ctx = { getComputedStyle: () => ({ display: 'block' }),
    document: { readyState: 'complete', addEventListener() {}, getElementById: (id) => byId[id] || null,
      // crm HAS a sidebar name, so only its own heading keeps the hidden h2 out
      querySelector: (q) => (q === '#sb-quote .sb-text' ? { textContent: ' Quote Builder ' } : q === '#sb-crm .sb-text' ? { textContent: 'Lead Pipeline' } : null),
      createElement: (t) => El(t.toUpperCase()),
      querySelectorAll: (q) => (q === '.ptitle:not([role])' ? [ptitle] : q.indexOf('.panel[id') === 0 ? [bare, titled, nameless] : []) } };
  vm.createContext(ctx);
  vm.runInContext(passSrc.replace(/\nif \(document\.readyState[\s\S]*$/, ''), ctx);
  let threw = null; try { ctx.sdA11yPass(ctx.document); } catch (e) { threw = e.message; }
  check('W1. an unnamed control gets its written name', sel.attrs['aria-label'] === 'Budget', JSON.stringify(sel.attrs));
  check('W2. a control with a real <label> or its own aria-label keeps it', !('aria-label' in labelled.attrs) && own.attrs['aria-label'] === 'Ship-to state');
  check('W3. every written name is non-empty text', Object.keys(ctx.SD_A11Y_NAMES).length > 0 && Object.values(ctx.SD_A11Y_NAMES).every((v) => typeof v === 'string' && v.trim() !== ''));
  check('H1. a page title (.ptitle) is a level-2 heading', ptitle.attrs.role === 'heading' && ptitle.attrs['aria-level'] === '2');
  check('H2. a panel with no heading gets an h2 with its sidebar name', kids.length === 1 && kids[0].tagName === 'H2' && kids[0].textContent === 'Quote Builder', threw || JSON.stringify(kids.map((k) => k.textContent)));
  check('H3. ...hidden visually (clipped), so the layout does not change', !!kids[0] && /clip:rect\(0,0,0,0\)/.test(kids[0].style.cssText || ''));
  check('H4. a panel that has a heading, or has no sidebar name, is left alone', threw === null, threw);
}

console.log('3. b54: contrast of the shipped colours');
{
  const lum = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)).reduce((a, x, i) => a + x * [0.2126, 0.7152, 0.0722][i], 0);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const tok = (n) => { const m = html.match(new RegExp('\\n\\s*--' + n + ':(#[0-9A-Fa-f]{6})')); return m && m[1]; };
  const brand2 = tok('brand2'), bg = tok('bg');
  check('C1. --brand2 text on --bg reaches 4.5:1', !!(brand2 && bg) && ratio(brand2, bg) >= 4.5, brand2 + ' on ' + bg + (brand2 && bg ? ' = ' + ratio(brand2, bg).toFixed(2) : ''));
  check('C2. white text on a --brand2 fill reaches 4.5:1', !!brand2 && ratio('#ffffff', brand2) >= 4.5);
  const colors2 = (html.match(/var colors2=\{[^}]*\}/) || [''])[0];
  const hexes = colors2.match(/#[0-9a-fA-F]{6}/g) || [];
  check('C3. the quote-history status colours all reach 4.5:1 on white', hexes.length === 3 && hexes.every((c) => ratio(c, '#ffffff') >= 4.5), colors2);
}

console.log('3a. b56: emoji in headings hidden from the reader; 24px targets');
{
  const mk = (txt) => {
    const h = El('H2'); const t = { nodeValue: txt }; t.parentNode = { closest: () => null, replaceChild: (frag) => { h.out = frag.kids; } };
    h.texts = [t]; return h;
  };
  const robot = mk('\u{1F916} StoneDesk AI Assistant'), arrow = mk('Expenses → SAIRNbiz'), warn = mk('⚠️ Market Signals');
  const heads = [robot, arrow, warn];
  const ctx = { getComputedStyle: () => ({ display: 'block' }),
    document: { readyState: 'complete', addEventListener() {}, getElementById: () => null, querySelector: () => null,
      createElement: (t) => El(t.toUpperCase()), createTextNode: (v) => ({ text: v }),
      createDocumentFragment: () => ({ kids: [], appendChild(x) { this.kids.push(x); } }),
      createTreeWalker: (h) => { let i = -1; return { get currentNode() { return h.texts[i]; }, nextNode() { i++; return i < h.texts.length; } }; },
      querySelectorAll: (q) => (q === 'h1,h2,h3,[role=heading]' ? heads : []) } };
  vm.createContext(ctx);
  vm.runInContext(passSrc.replace(/\nif \(document\.readyState[\s\S]*$/, ''), ctx);
  let threw = null; try { ctx.sdA11yPass(ctx.document); } catch (e) { threw = e.message; }
  const shape = (h) => (h.out || []).map((k) => (k.tagName ? 'HIDDEN:' + k.textContent + ':' + k.attrs['aria-hidden'] : 'TEXT:' + k.text));
  check('E1. the emoji in "🤖 StoneDesk AI Assistant" is wrapped aria-hidden; the words stay readable',
    JSON.stringify(shape(robot)) === JSON.stringify(['HIDDEN:\u{1F916}:true', 'TEXT: StoneDesk AI Assistant']), threw || JSON.stringify(shape(robot)));
  check('E2. a variation selector stays with its emoji (⚠️ hidden whole)', JSON.stringify(shape(warn)) === JSON.stringify(['HIDDEN:⚠️:true', 'TEXT: Market Signals']), JSON.stringify(shape(warn)));
  check('E3. an arrow is a word, not an emoji -- left alone', !arrow.out, JSON.stringify(shape(arrow)));
  robot.out = null; robot.texts = [{ nodeValue: '\u{1F916} again', parentNode: robot.texts[0].parentNode }];
  ctx.sdA11yPass(ctx.document);
  check('E4. a heading already done is not re-wrapped on the next pass', !robot.out);
  // nest-cut-label surfaced only after its neighbours grew (axe measures spacing too) -- the same class, fixed with them
  const ids = ['nest-slab-w', 'nest-slab-h', 'nest-cut-w', 'nest-cut-h', 'fq-client', 'nest-cut-label'];
  const small = ids.filter((id) => !new RegExp('id="' + id + '" style="min-height:24px"').test(html));
  check('T1. the six undersized inputs carry a 24px minimum height (WCAG 2.5.8)', small.length === 0, small.join(' '));
}

console.log('3b. b55: the missing-dom-fix stub fields carry real labels');
{
  const stubs = [...html.matchAll(/data-auto-container="missing-dom-fix"><label([^>]*)>([^<]*)<\/label><input type="text" id="([^"]+)"/g)];
  check('S1. all 17 labelled stub fields are found', stubs.length === 17, stubs.length);
  const bad = stubs.filter((m) => m[2].trim() === m[3] || !m[2].trim() || m[1].indexOf('for="' + m[3] + '"') === -1);
  check('S2. none shows its raw element id, and each is tied to its input by for=', stubs.length > 0 && bad.length === 0, bad.map((m) => m[3]).join(' '));
}

console.log('4. sbNav: current item and focus to the heading');
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
