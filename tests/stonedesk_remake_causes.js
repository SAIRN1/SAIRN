// tests/stonedesk_remake_causes.js
//
// Run:  node tests/stonedesk_remake_causes.js
//
// "Cause Breakdown" WAS A TITLED CARD WITH NOTHING IN IT.
//
// `#rm-causes` had been empty since the old IIFE render was removed, and the
// open-work row called it cosmetic. It is not invisible: it is a bordered card
// headed "Cause Breakdown" that a shop owner sees, permanently blank, sitting
// beside a Remake Log that fills. Adjacent live and dead displays is a shape
// this platform keeps finding, and the dead one reads as BROKEN rather than as
// absent.
//
// NOTHING NEW IS COMPUTED. `reasonCounts` was already built inside
// renderRemakes() and only its TOP entry was ever used -- `sv('rm-top', ...)`
// -- and the rest was discarded two lines later. So the card renders real data
// by construction: there is no figure here to fabricate, which is what Check 0b
// asks of any number on a panel. That is the property section 3 pins.
//
// The empty state is asserted separately because a blank card and "no remakes
// yet" look identical to a user and mean different things -- and telling them
// apart is the whole reason this was worth fixing rather than deleting.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8').replace(/\r\n/g, '\n');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   - ' + name); pass++; }
  catch (e) { console.log('  FAIL - ' + name + '\n         ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function bodyAt(at) {
  const open = html.indexOf('{', at);
  let d = 0;
  for (let i = open; i < html.length; i++) {
    if (html[i] === '{') d++;
    else if (html[i] === '}') { d--; if (d === 0) return html.slice(at, i + 1); }
  }
  throw new Error('unbalanced braces');
}

// The REAL renderRemakes(), lifted rather than retyped.
function renderWith(remakes) {
  const el = {};
  // A stub element carrying the surfaces renderRemakes() touches. classList
  // and style are included because the function toggles both on nodes it
  // looks up -- omitting them fails as a TypeError deep in the render, which
  // reads like a defect in the code under test rather than a gap in the
  // harness. That mis-read cost time twice today on other probes.
  const mk = () => ({ textContent: '', innerHTML: '', value: '',
    style: {}, dataset: {},
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false } });
  const get = (id) => (el[id] || (el[id] = mk()));
  const ctx = {
    JSON, Object, Array, String, Number, Math, Date, isNaN, parseInt, parseFloat,
    console: { warn() {}, error() {}, log() {} },
    // document.body too: renderRemakes() reads
    // document.body.classList.contains('is-exec') to decide whether to draw
    // the approve button. Found by grepping the function for classList
    // rather than by adding stubs one TypeError at a time.
    document: { getElementById: get, querySelector: () => mk(),
      querySelectorAll: () => [], createElement: () => mk(), body: mk() },
    sdRemakes: remakes,
    escHtml: (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'),
    sdLocalToday: () => '2026-09-10',
    // Stubs for the helpers renderRemakes() leans on. Named individually
    // rather than blanket-mocked so a NEW dependency shows up as a loud
    // ReferenceError here instead of being silently absorbed.
    remakeUrgency: () => 'green',
    remakeHoursElapsed: () => 1,
    remakeHoursLimit: () => 24,
    remakeMaxHours: () => 24,
    remakeApprove: () => {},
    remakeComplete: () => {},
    remakeDelete: () => {},
    escAttrJs: (s) => String(s),
    sv: function (id, v) { get(id).textContent = v; },
    fmt: (n) => '$' + Number(n || 0).toFixed(2),
    fdate: (d) => String(d || ''),
    __el: el,
  };
  vm.createContext(ctx);
  const at = html.indexOf('function renderRemakes');
  assert.ok(at > 0, 'renderRemakes not found in stonedesk.html');
  vm.runInContext(bodyAt(at), ctx);
  ctx.renderRemakes();
  return ctx;
}

const R = (reason, status) => ({ id: 'r' + Math.random().toString(36).slice(2),
  reason: reason, status: status || 'open', createdAt: '2026-09-01T00:00:00Z',
  customer: 'C', material: 'M' });

// ═══════════════════════════════════════════════════════════════════════════
section('1. the card renders the breakdown it is titled for');

test('every recorded cause appears, with a count', () => {
  const c = renderWith([R('cut_error'), R('cut_error'), R('measure_error')]);
  const out = c.__el['rm-causes'].innerHTML;
  assert.ok(/Cut Error/.test(out), 'the top cause is missing');
  assert.ok(/Measure Error/.test(out), 'a second cause is missing');
  assert.ok(/2 · 67%/.test(out), 'the count/percentage for Cut Error is wrong or absent: ' + out.slice(0, 200));
  assert.ok(/1 · 33%/.test(out), 'the count/percentage for Measure Error is wrong or absent');
});

test('it is ordered most-common first', () => {
  const c = renderWith([R('other'), R('edge_error'), R('edge_error'), R('edge_error')]);
  const out = c.__el['rm-causes'].innerHTML;
  assert.ok(out.indexOf('Edge Error') < out.indexOf('Other'), 'not ranked by count');
});

test('an unknown reason code falls back to the raw value rather than vanishing', () => {
  const c = renderWith([R('a_code_nobody_mapped')]);
  assert.ok(/a_code_nobody_mapped/.test(c.__el['rm-causes'].innerHTML),
    'an unmapped cause is silently dropped from the breakdown');
});

test('the bar uses a colour this file actually declares', () => {
  // The first version used var(--brand), which does not exist in stonedesk.html
  // -- the bar would have rendered invisible. --brand2 (#16C762) is the real
  // accent. Pinned because an undeclared custom property fails silently.
  const c = renderWith([R('cut_error')]);
  assert.ok(/var\(--brand2\)/.test(c.__el['rm-causes'].innerHTML), 'the bar lost its colour');
  assert.ok(/--brand2:/.test(html), 'stonedesk.html no longer declares --brand2');
});

// ═══════════════════════════════════════════════════════════════════════════
section('2. the empty states SAY which empty they are');

test('no remakes at all says so', () => {
  const c = renderWith([]);
  assert.ok(/No remakes logged yet/.test(c.__el['rm-causes'].innerHTML),
    'an empty log renders a blank card, which reads as broken');
});

test('remakes with no cause recorded is a DIFFERENT message', () => {
  const c = renderWith([R(''), R(undefined)]);
  const out = c.__el['rm-causes'].innerHTML;
  assert.ok(/No cause recorded on any remake yet/.test(out),
    'a log with no causes is indistinguishable from an empty log: ' + out.slice(0, 160));
  assert.ok(!/No remakes logged yet/.test(out), 'the two empty states were conflated');
});

// ═══════════════════════════════════════════════════════════════════════════
section('3. nothing here is invented -- it renders what was already computed');

test('the breakdown and the "top cause" KPI come from the same tally', () => {
  // rm-top existed before this change and read from reasonCounts. If the card
  // ever disagreed with the KPI beside it, that is the two-adjacent-displays
  // defect this fix exists to remove, reintroduced.
  const c = renderWith([R('installer_damage'), R('installer_damage'), R('other')]);
  assert.strictEqual(c.__el['rm-top'].textContent, 'Installer Damage');
  const out = c.__el['rm-causes'].innerHTML;
  assert.ok(out.indexOf('Installer Damage') < out.indexOf('Other'),
    'the card ranks a different cause first than the KPI names');
});

test('the source tally is still built from sdRemakes and nothing else', () => {
  const at = html.indexOf('function renderRemakes');
  const body = bodyAt(at);
  assert.ok(/sdRemakes\.forEach\(r=>\{if\(r\.reason\)reasonCounts/.test(body),
    'reasonCounts is no longer derived from sdRemakes -- check what it reads now');
  assert.ok(!/rm-causes[\s\S]{0,400}?(SEED|demo|sample)/i.test(body),
    'the breakdown now references seed or sample data');
});

// ═══════════════════════════════════════════════════════════════════════════
console.log('\n' + pass + '/' + (pass + fail) + ' passed');
process.exit(fail ? 1 : 0);
