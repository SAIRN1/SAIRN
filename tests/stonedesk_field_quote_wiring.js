// tests/stonedesk_field_quote_wiring.js
//
// Run:  node tests/stonedesk_field_quote_wiring.js
//
// FIELD QUOTE IS A `.page`, NOT A PANEL, AND THAT IS WHY ITS WIRING NEEDS A
// TEST RATHER THAN A DIFF.
//
// StoneDesk has THREE navigation systems in one file. `showPanel` shows a
// `.panel`; `showPage` shows a `.page` by inline-locking every other one to
// display:none!important; and `sbNav` is the sidebar wrapper over showPanel.
// page-field-quote lives in the second system and is reached through the
// first, via a lookup table inside showPanel. A button that LOOKS correct in
// a diff can still route into the gap between them, and the failure is a blank
// content area with a working sidebar -- which reads as a crash, not a
// mis-wire.
//
// ── SECTION 3 IS THE ONE THAT MATTERS ─────────────────────────────────────
// The Back button called showPage('dashboard'), and NOTHING IN THIS FILE HAS
// THAT ID -- no page-dashboard, no panel-dashboard. It worked anyway, by
// accident, for as long as the only ways in were q-btns calling openFQ(),
// because openFQ does not touch `.panel` classes: the source panel stayed
// active underneath and reappeared when the page was hidden.
//
// Adding a SIDEBAR entry changed that. sbNav routes through showPanel, which
// clears every panel before showing the page -- so Back would have hidden
// Field Quote and revealed nothing at all. Section 3 drives both arrival
// routes against a fake DOM and asserts a real panel is showing afterwards,
// because the static half of this file cannot see that distinction.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

// SD_HTML lets a negative control point this suite at a MUTATED COPY rather
// than patching the tracked file. Same convention DNT_HTML, SV_HTML, ALF_HTML
// and MECH_HTML already carry.
const html = fs.readFileSync(process.env.SD_HTML
  || path.join(__dirname, '..', 'stonedesk.html'), 'utf8')
  .replace(/\r\n/g, '\n');

// ── ASSERTED ON THE CODE FORM, NOT ON THE BARE STRING ────────────────────
// The arm below counts calls to showPage('field-quote'). Its first draft
// counted the bare substring and went red against a correct file, because the
// comments THIS change added to stonedesk.html explaining the wiring contain
// the same characters. That is PR-rules 1.2 -- grep cannot tell code from text
// that describes code -- committed inside the test written to catch it.
//
// TWO COMMENT-STRIPPERS WERE WRITTEN AND BOTH ARE GONE. A line filter kept
// every continuation line inside a multi-line `<!-- -->` block; a regex that
// removed whole `/* */` blocks then matched across an unintended span and ate
// the real statement, taking the count from two to ZERO -- a false PASS in the
// other direction if the assertion had been `<= 1`. tier_a_review_gate.py's
// _strip_code_noise carries the same warning from the same platform: the regex
// version of this has already shipped a defect here.
//
// So no stripper. The STATEMENT ends in a semicolon and the prose does not,
// which is precise, needs no parser, and is what the arm was always about.

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// The slice of markup belonging to one panel: from its id to the next panel's.
// Crude on purpose -- a real parse of a 2MB single-file app is a bigger
// dependency than this arm is worth -- but it is BOUNDED, which is the part
// that matters: a button in a neighbouring panel cannot be credited here.
function panelSlice(id) {
  const at = html.indexOf('id="panel-' + id + '"');
  assert.ok(at > 0, 'no panel-' + id + ' in stonedesk.html');
  const next = html.indexOf('id="panel-', at + 10);
  return html.slice(at, next === -1 ? at + 4000 : next);
}
// The header action row is the first flex row of q-btns after the panel's
// <h2>. Entry points are asserted to be IN IT rather than merely somewhere in
// the panel, because a button buried 900 lines down a panel body is not an
// entry point anybody finds.
function headerActions(id) {
  const s = panelSlice(id);
  const h2 = s.indexOf('<h2');
  assert.ok(h2 > 0, 'panel-' + id + ' has no <h2> header');
  const row = s.indexOf('display:flex;gap:8px;flex-wrap:wrap', h2);
  assert.ok(row > 0, 'panel-' + id + ' has no header action row');
  const end = s.indexOf('</div>', s.indexOf('</button>', row));
  return s.slice(row, end === -1 ? row + 1500 : end + 6);
}

console.log('StoneDesk -- the Field Quote page is reachable, and Back goes back');

section('1. the four entry points Michael asked for, each in a panel HEADER');

// Named with the label the SIDEBAR uses, not the panel's own heading, because
// those disagree in two places and the sidebar is what a user reads.
const ENTRY_POINTS = [
  ['customers', 'Customers'],
  // "Jobs" resolves to this one and the reasoning is in stonedesk.html beside
  // the button: StoneDesk has no panel called Jobs, the sidebar labels this
  // one "Job History" (its own heading says "Quote History"), and it is the
  // job list a shop browses. `schedule` already had a Field Quote button
  // before this change and still does -- see section 2.
  ['history', 'Job History'],
  // The dashboard. Nothing is NAMED dashboard in this file; this panel is it
  // by every measure the file actually has, which section 4 pins.
  ['ai', 'AI Assistant'],
  ['admin', 'Shop Settings'],
];

ENTRY_POINTS.forEach(([id, label]) => {
  test('panel-' + id + ' (' + label + ') has a Field Quote button in its header', () => {
    const row = headerActions(id);
    assert.ok(row.indexOf('openFQ()') !== -1,
      'no openFQ() call in the header action row of panel-' + id +
      '\n' + row.slice(0, 300));
    assert.ok(/Field Quote/.test(row),
      'openFQ() is called but the button is not labelled Field Quote');
  });
});

test('every entry point calls openFQ(), not a second route of its own', () => {
  // The failure this prevents is two ways in that drift apart -- one that
  // records the return panel and one that does not. There is one entry
  // function and these are callers of it.
  const calls = html.match(/onclick="openFQ\(\)"/g) || [];
  assert.ok(calls.length >= 6,
    'expected at least six openFQ() call sites (4 new + schedule + customer '
    + 'detail), found ' + calls.length);
  assert.strictEqual((html.match(/showPage\('field-quote'\);/g) || []).length, 1,
    'more than one place calls showPage(\'field-quote\') directly -- openFQ() '
    + 'should be the only one');
});

section('2. the two entry points that already existed are NOT lost');

test('the Schedule panel still has one', () => {
  assert.ok(headerActions('schedule').indexOf('openFQ()') !== -1);
});
test('the customer DETAIL card still has one', () => {
  // Built as a JS string, not markup, so it is matched in the escaped form the
  // renderer writes.
  assert.ok(html.indexOf("'<button class=\"q-btn\" onclick=\"openFQ()\">") !== -1,
    'the customer detail card lost its Field Quote button');
});

section('3. IT IS IN THE SIDEBAR, AND BACK RETURNS TO A REAL PANEL');

test('the sidebar has a Field Quote button routing through sbNav', () => {
  assert.ok(/id="sb-field-quote"[^>]*onclick="sbNav\('field-quote'\)"/.test(html),
    'page-field-quote is still absent from the sidebar, which is how it was '
    + 'undiscoverable -- its sibling pages sb-doc-scan and sb-check-register '
    + 'both have one');
});

test('showPanel maps field-quote through its pageIds table, so sbNav reaches it', () => {
  // Without this entry showPanel falls through to
  // getElementById('panel-field-quote'), which does not exist, and throws.
  const m = html.match(/const pageIds = \{[^}]*\}/);
  assert.ok(m, 'the pageIds table is gone from showPanel');
  assert.ok(m[0].indexOf("'field-quote':'field-quote'") !== -1, m[0]);
});

test('BACK no longer calls showPage with an id that matches nothing', () => {
  assert.ok(html.indexOf("onclick=\"showPage('dashboard')\"") === -1,
    'the Back button still routes to a non-existent page id');
  assert.ok(html.indexOf('onclick="closeFQ()"') !== -1,
    'the Back button does not call closeFQ()');
});

test('...and there really is no dashboard element to route to', () => {
  // The premise of the fix, asserted rather than assumed. If somebody adds a
  // page-dashboard later, this arm says so and closeFQ can be simplified.
  assert.ok(html.indexOf('id="page-dashboard"') === -1
            && html.indexOf('id="panel-dashboard"') === -1,
    'a dashboard element now exists -- re-check closeFQ()');
});

// ── THE BEHAVIOURAL HALF ────────────────────────────────────────────────
// A fake DOM with just enough to run the three routing functions. Small, and
// it is the only thing here that can tell "Back blanks the screen" from "Back
// works", because both look identical in the source.
function grab(sig, terminator) {
  const at = html.indexOf(sig);
  assert.ok(at > 0, 'not found in stonedesk.html: ' + sig);
  const end = html.indexOf(terminator, at);
  assert.ok(end > at, 'terminator not found after ' + sig);
  return html.slice(at, end + terminator.length);
}

function fakeDom() {
  const els = {};
  function el(id, cls) {
    return { id: id, _cls: new Set(cls ? [cls] : []), style: { cssText: '' },
             classList: { add: function (c) { this._o._cls.add(c); },
                          remove: function (c) { this._o._cls.delete(c); } },
             getAttribute: function () { return null; } };
  }
  function mk(id, cls) {
    const e = el(id, cls);
    e.classList._o = e;
    els[id] = e;
    return e;
  }
  ['ai', 'customers', 'history', 'admin', 'schedule'].forEach(
    p => mk('panel-' + p, p === 'ai' ? 'active' : null));
  ['field-quote', 'doc-scan', 'check-register'].forEach(p => mk('page-' + p, null));
  ['field-quote', 'ai', 'customers'].forEach(p => mk('sb-' + p, null));
  const all = () => Object.keys(els).map(k => els[k]);
  return {
    els: els,
    doc: {
      getElementById: id => els[id] || null,
      querySelector: sel => {
        if (sel === '.panel.active')
          return all().find(e => e.id.startsWith('panel-') && e._cls.has('active')) || null;
        return null;
      },
      querySelectorAll: sel => {
        if (sel === '.panel') return all().filter(e => e.id.startsWith('panel-'));
        if (sel === '.page') return all().filter(e => e.id.startsWith('page-'));
        if (sel === '.sb-btn') return all().filter(e => e.id.startsWith('sb-'));
        return [];
      },
      body: { classList: { add() {}, remove() {} } }
    }
  };
}

function routingCtx() {
  const dom = fakeDom();
  const win = {};
  const ctx = {
    document: dom.doc, window: win, sessionStorage: { getItem: () => '' },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    setTimeout: () => 0, console: { log() {}, warn() {} },
    notify: () => {}, closeSidebar: () => {},
    Object, Array, String, Number, Boolean, JSON, Math, RegExp, Set,
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(grab('function showPanel(id) {', '\n}\n'), ctx, { filename: 'showPanel' });
  vm.runInContext(grab('  function showPage(id) {', '\n  }'), ctx, { filename: 'showPage' });
  vm.runInContext(grab('  window.showPage = showPage;', 'showPage(\'__none__\');\n  };'),
                  ctx, { filename: 'openFQ+closeFQ' });
  vm.runInContext('window.showPanel = showPanel; window.sbNav = function(id){ showPanel(id); };',
                  ctx, { filename: 'sbNav-stub' });
  return { ctx, dom };
}

function visible(dom) {
  const page = Object.keys(dom.els)
    .filter(k => k.startsWith('page-') && /display:block/.test(dom.els[k].style.cssText));
  const panel = Object.keys(dom.els)
    .filter(k => k.startsWith('panel-') && dom.els[k]._cls.has('active'));
  return { page: page, panel: panel };
}

test('ROUTE A -- q-btn: openFQ() shows the page, Back restores the panel you left', () => {
  const { ctx, dom } = routingCtx();
  ctx.showPanel('customers');
  assert.deepStrictEqual(visible(dom).panel, ['panel-customers'], 'setup failed');
  ctx.window.openFQ();
  const on = visible(dom);
  assert.deepStrictEqual(on.page, ['page-field-quote'], JSON.stringify(on));
  ctx.window.closeFQ();
  const back = visible(dom);
  assert.deepStrictEqual(back.page, [], 'the page is still showing after Back');
  assert.deepStrictEqual(back.panel, ['panel-customers'],
    'Back did not return to the panel the user came from: ' + JSON.stringify(back));
});

test('ROUTE B -- SIDEBAR: sbNav() shows the page, and Back does NOT blank the screen', () => {
  // THE ARM THIS FILE EXISTS FOR. sbNav clears every panel before showing the
  // page, so the old showPage('dashboard') Back had nothing to reveal.
  const { ctx, dom } = routingCtx();
  ctx.showPanel('admin');
  ctx.window.sbNav('field-quote');
  const on = visible(dom);
  assert.deepStrictEqual(on.page, ['page-field-quote'], JSON.stringify(on));
  assert.deepStrictEqual(on.panel, [],
    'sbNav left a panel active underneath the page');
  ctx.window.closeFQ();
  const back = visible(dom);
  assert.deepStrictEqual(back.page, [], 'the page is still showing after Back');
  assert.strictEqual(back.panel.length, 1,
    'BACK LEFT A BLANK SCREEN -- no page and no panel: ' + JSON.stringify(back));
  assert.deepStrictEqual(back.panel, ['panel-admin'],
    'Back did not return to the panel the user came from: ' + JSON.stringify(back));
});

test('a cold Back with no recorded panel falls back to the home panel', () => {
  // Reachable after a reload straight onto the page. Must not blank either.
  const { ctx, dom } = routingCtx();
  ctx.window.sdLastPanel = undefined;
  ctx.window.closeFQ();
  assert.deepStrictEqual(visible(dom).panel, ['panel-ai'],
    'the fallback did not land on the home panel');
});

section('4. the premises this wiring rests on');

test('panel-ai is the home panel -- it is the only one that ships active', () => {
  // Matched as MARKUP (`<div class=...`), not as a bare string: the phrase
  // also appears in two comments in this file explaining that it appears once.
  const actives = html.match(/<div class="panel active"/g) || [];
  assert.strictEqual(actives.length, 1, 'more than one panel ships active');
  assert.ok(/class="panel active" id="panel-ai"/.test(html),
    'the home panel is no longer panel-ai -- closeFQ\'s fallback needs re-aiming');
});

test('sb-ai is the only sidebar button that ships active', () => {
  const m = html.match(/class="sb-btn active"[^>]*id="sb-([a-z0-9-]+)"/g) || [];
  assert.strictEqual(m.length, 1, m.join(' | '));
  assert.ok(m[0].indexOf('id="sb-ai"') !== -1, m[0]);
});

section('5. the legacy modal is gone and did not come back');

test('no sairn-fq-modal element exists', () => {
  // Removed 2026-09-02. The only surviving mentions must be the two comments
  // recording the removal -- an element would mean it was restored.
  assert.ok(html.indexOf('id="sairn-fq-modal"') === -1,
    'the legacy Field Quote modal element is back');
  const mentions = (html.match(/sairn-fq-modal/g) || []).length;
  assert.strictEqual(mentions, 1,
    'expected exactly one mention (the removal comment), found ' + mentions);
});

test('nothing calls the modal\'s old open/close functions', () => {
  assert.ok(html.indexOf('sairnFQOpen(') === -1, 'sairnFQOpen still has a caller');
  // sairnFQClose survives only inside a comment explaining who used to call it.
  const live = html.split('\n').filter(
    l => l.indexOf('sairnFQClose') !== -1 && l.trim().indexOf('//') !== 0);
  assert.strictEqual(live.length, 0, live.join('\n'));
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
