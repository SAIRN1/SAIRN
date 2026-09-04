// tests/pricing_single_source.js
//
// Run:  node tests/pricing_single_source.js
//
// StoneDesk carried TWO price lists that disagreed, in two files, with nothing
// forcing them to match:
//
//   * the service-agreement generator in stonedesk.html offered
//     Founding $199 / Solo $299 / Pro $499 / Shop $799;
//   * the AI advisors' price book in api/_lib/exec-context.js told the CEO and
//     CFO advisors "Starter $199/mo, Professional $299/mo, Enterprise $599/mo".
//
// Four tiers against three, two names in common with different money attached
// to one of them, and the generator's list is THE ONE A CUSTOMER SIGNS. Both
// were wrong as of 2026-09-04; the confirmed tiers are Business $299,
// Professional $599, Enterprise $799, plus custom pricing for larger shops, and
// no entry-level tier.
//
// Correcting both is a one-off. This file is the part that lasts: the two lists
// are still in two files, so the next edit to either can drift again exactly as
// this one did. This asserts they agree, by reading both.
//
// It also holds the two behaviours the new Custom tier introduced, because a
// tier that can print the wrong number on a contract is worse than no tier.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const exec = fs.readFileSync(path.join(ROOT, 'api', '_lib', 'exec-context.js'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// ---------------------------------------------------------------------------
// THE CONFIRMED PRICE BOOK. Written here once, deliberately, so this file is a
// third opinion rather than a diff of the other two agreeing with each other --
// if both files were edited wrongly in the same way, comparing them to each
// other would still pass.
const TIERS = [
  { key: 'business',     name: 'Business',     price: 299 },
  { key: 'professional', name: 'Professional', price: 599 },
  { key: 'enterprise',   name: 'Enterprise',   price: 799 }
];
// Prices that must no longer appear as a CURRENT StoneDesk tier anywhere.
const RETIRED_PRICES = [199, 499];

function grabTopLevel(sig) {
  const s = html.indexOf(sig);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + sig);
  const rest = html.slice(s);
  const m = rest.match(/\r?\n\};?(?=\r?\n)/);
  assert.ok(m, 'not terminated: ' + sig);
  return rest.slice(0, m.index + m[0].length);
}

console.log('StoneDesk pricing -- one price book, in two files, that must agree\n');

// ══ 1. the generator ══════════════════════════════════════════════════════
section('the service-agreement generator');

const AG_PLANS = (() => {
  const ctx = {};
  vm.createContext(ctx);
  vm.runInContext(grabTopLevel('var AG_PLANS = {') + '\nthis.out = AG_PLANS;', ctx);
  return ctx.out;
})();

test('AG_PLANS carries exactly the confirmed tiers, plus custom', () => {
  assert.deepStrictEqual(Object.keys(AG_PLANS).sort(),
    ['business', 'custom', 'enterprise', 'professional']);
});

TIERS.forEach(t => {
  test(t.name + ' is $' + t.price + '/mo in the generator', () => {
    assert.strictEqual(AG_PLANS[t.key].price, t.price);
    assert.strictEqual(AG_PLANS[t.key].label, t.name + ' — $' + t.price + '/mo');
  });
});

test('custom carries NO hardcoded price -- it comes from the agreed rate', () => {
  assert.strictEqual(AG_PLANS.custom.price, null);
});

test('the <select> the user actually sees offers the same four and nothing else', () => {
  // The map being right does not help if the dropdown still lists Solo and Pro.
  const s = html.indexOf('<select id="ag-plan"');
  assert.ok(s > 0, 'the plan select is gone');
  const block = html.slice(s, html.indexOf('</select>', s));
  const values = (block.match(/value="([a-z]+)"/g) || []).map(v => v.slice(7, -1));
  assert.deepStrictEqual(values, ['business', 'professional', 'enterprise', 'custom']);
  ['Founding', 'Solo —', 'Pro —', 'Shop —'].forEach(gone => {
    assert.ok(block.indexOf(gone) === -1, 'a retired tier is still offered: ' + gone);
  });
});

test('there is NO entry-level tier -- nothing under $299 is offered', () => {
  const cheapest = Math.min.apply(null, TIERS.map(t => t.price));
  assert.strictEqual(cheapest, 299);
  Object.keys(AG_PLANS).forEach(k => {
    const p = AG_PLANS[k].price;
    if (p !== null) assert.ok(p >= 299, k + ' is priced below the floor at ' + p);
  });
});

// ══ 2. the AI price book ══════════════════════════════════════════════════
section('the AI advisors are told the same thing');

// The two lines that carry pricing, isolated so a match elsewhere in the file
// (a comment recording the old numbers, which this change deliberately keeps)
// cannot make this pass or fail by accident.
function advisorPricingLines() {
  return exec.split('\n').filter(l =>
    !l.trim().startsWith('//') && /StoneDesk pricing is|StoneDesk pricing:/.test(l));
}

test('both the ceo and the cfo advisor carry a pricing line', () => {
  assert.strictEqual(advisorPricingLines().length, 2,
    'expected exactly two live pricing lines, found ' + advisorPricingLines().length);
});

advisorPricingLines().forEach((line, i) => {
  const who = i === 0 ? 'ceo' : 'cfo';
  TIERS.forEach(t => {
    test(who + ' advisor states ' + t.name + ' $' + t.price + '/mo', () => {
      assert.ok(new RegExp(t.name + ' \\$' + t.price + '/mo').test(line),
        'line was: ' + line.trim());
    });
  });
  test(who + ' advisor is told there is no entry-level tier', () => {
    assert.match(line, /NO entry-level tier/);
  });
  test(who + ' advisor is told custom pricing exists for larger shops', () => {
    assert.match(line, /custom pricing for larger shops/);
  });
  RETIRED_PRICES.forEach(p => {
    test(who + ' advisor no longer quotes the retired $' + p, () => {
      assert.ok(line.indexOf('$' + p) === -1, 'line was: ' + line.trim());
    });
  });
});

test('the retired "Starter" tier name is gone from every live advisor line', () => {
  const live = exec.split('\n').filter(l => !l.trim().startsWith('//'));
  live.forEach(l => assert.ok(!/Starter \$/.test(l), 'still present: ' + l.trim()));
});

// ══ 3. the two files agree ════════════════════════════════════════════════
section('the two lists cannot drift apart again without this failing');

test('every tier the generator can sell is a tier the advisors know about', () => {
  const lines = advisorPricingLines().join(' ');
  Object.keys(AG_PLANS).forEach(k => {
    if (k === 'custom') { assert.match(lines, /custom pricing/i); return; }
    const spec = AG_PLANS[k];
    const name = spec.label.split(' —')[0];
    assert.ok(lines.indexOf(name + ' $' + spec.price + '/mo') !== -1,
      'the generator sells ' + name + ' $' + spec.price + ' and no advisor line says so');
  });
});

// ══ 4. the Custom tier's two hazards ══════════════════════════════════════
section('Custom: a tier that could print the wrong number on a contract');

function driveSave(planValue, customValue) {
  const els = {};
  const mk = v => ({ value: v === undefined ? '' : v, style: {}, disabled: false });
  ['ag-shop', 'ag-contact', 'ag-email', 'ag-phone', 'ag-address', 'ag-notes',
   'ag-date', 'ag-status', 'ag-custom-price', 'ag-plan', 'ag-form', 'ag-custom-wrap']
    .forEach(id => { els[id] = mk(''); });
  els['ag-shop'].value = 'Main Street Stone';
  els['ag-plan'].value = planValue;
  els['ag-custom-price'].value = customValue === undefined ? '' : String(customValue);

  const stored = [];
  const toasts = [];
  const ctx = {
    document: { getElementById: id => els[id] || null },
    showToast: m => toasts.push(m),
    sdStore: (k, v) => stored.push({ k, v }),
    sdLocalToday: () => '2026-09-04',
    agRender: () => {}, agPrint: () => {},
    agAgreements: [],
    console
  };
  vm.createContext(ctx);
  vm.runInContext(
    grabTopLevel('var AG_PLANS = {') + '\n' +
    html.slice(html.indexOf('function agSave(andPrint) {'),
               html.indexOf('\n}', html.indexOf('function agSave(andPrint) {')) + 2) + '\n' +
    'this.run = function(){ agSave(false); };', ctx);
  ctx.run();
  return { stored, toasts, saved: stored.length ? stored[stored.length - 1].v[0] : null };
}

test('a Custom agreement with no rate is REFUSED, not saved at $0', () => {
  const r = driveSave('custom', '');
  assert.strictEqual(r.saved, null, 'a $0/month contract was saved');
  assert.ok(/agreed monthly rate/i.test(r.toasts.join(' ')), 'toasts: ' + r.toasts.join(' | '));
});

test('a Custom agreement with a negative or zero rate is REFUSED', () => {
  [0, -50].forEach(v => {
    assert.strictEqual(driveSave('custom', v).saved, null, 'saved at ' + v);
  });
});

test('a Custom agreement with a real rate saves that rate and labels it', () => {
  const r = driveSave('custom', 1200);
  assert.strictEqual(r.saved.price, 1200);
  assert.strictEqual(r.saved.planLabel, 'Custom — $1200/mo');
});

TIERS.forEach(t => {
  test('a ' + t.name + ' agreement stores $' + t.price + ' and its own label', () => {
    const r = driveSave(t.key);
    assert.strictEqual(r.saved.price, t.price);
    assert.strictEqual(r.saved.planLabel, t.name + ' — $' + t.price + '/mo');
  });
});

// ══ 5. retired tiers still REPRINT ════════════════════════════════════════
section('agreements already signed under a retired tier must still reprint');

test('the founding rate-lock clause is still in the printer', () => {
  // Deleting it would silently reprint a signed contract WITHOUT the clause the
  // customer agreed to. It is unreachable for new agreements and load-bearing
  // for old ones.
  assert.match(html, /FOUNDING MEMBER RATE LOCK/);
  assert.match(html, /rate of \$199\/month is guaranteed to never increase/);
});

test('and it is explicitly marked as legacy-only, so nobody re-offers it', () => {
  assert.match(html, /var AG_RETIRED_PLANS = \{ founding: true, solo: true, pro: true, shop: true \};/);
  assert.match(html, /LEGACY ONLY[\s\S]{0,400}founding/);
});

test('a stored agreement prints its OWN label and price, not a lookup', () => {
  // This is why retiring a tier is safe at all: nothing downstream re-derives
  // the price from the plan key.
  assert.ok(html.indexOf("escHtml(ag.planLabel || '')") !== -1);
  assert.ok(html.indexOf("'$' + ag.price + '.00 / month'") !== -1 ||
            html.indexOf("$' + ag.price + '.00 / month") !== -1,
            'the printed rate box no longer reads ag.price');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exitCode = 1;
