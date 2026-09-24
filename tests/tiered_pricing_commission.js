// tests/tiered_pricing_commission.js
// REQUIREMENT: the B2B pricing tiers and the per-agent commission they carry
//   are ONE list, resolve to a rate that says where it came from, compute in
//   whole cents, and never silently pay 0% or reprice an existing quote
//
// Run:  node tests/tiered_pricing_commission.js
//
// ── WHY THIS IS TESTED AT ALL, when it is "just a lookup table" ────────────
// Because every failure mode here is a wrong number that looks right. A tier
// key that no longer exists reads as `undefined` and gets defended with a
// `|| 1.0` that reprices a distributor quote at full retail. An agent override
// of `''` becomes 0 through Number() and pays a rep nothing, indistinguishable
// from a deliberate 0%. A commission recomputed at read time changes every
// historical quote the day somebody edits the rate table. None of those throw.
//
// It extracts the real functions out of stonedesk.html and DRIVES them rather
// than matching source text: a regex asserting `commission: 0.015` appears
// somewhere would pass while the function ignored it.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'stonedesk.html'), 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// ── EXTRACTION, AND ITS FAILURE IS A REPORTED ARM ─────────────────────────
// Slicing by a hard-coded anchor is how tests/slab_reserve_client.js came to
// throw out of its own file when a signature changed, leaving later sections
// unrun and the exit code still 0. Every anchor here is checked and reported.
const ANCHORS = {
  TIERS: 'var TIERS = {',
  rates: 'function sdAgentCommissionRates(){',
  commFor: 'function sdCommissionFor(tierKey, agentId){',
  commAmt: 'function sdCommissionCents(totalDollars, rate){',
  toDollars: 'function sdCentsToDollars(cents){'
};
const missing = Object.keys(ANCHORS).filter(k => html.indexOf(ANCHORS[k]) < 0);

section('the pricing model is findable');
test('every function this suite drives is still in stonedesk.html', () => {
  assert.deepStrictEqual(missing, [],
    'anchors not found: ' + missing.join(', ') + '. They were renamed, and '
    + 'every arm below would be driving nothing. Update ANCHORS here.');
});

let ctx = null;
if (!missing.length) {
  // From `var TIERS = {` through the end of the LAST function in the block --
  // one contiguous region, taken whole so no arm can be satisfied by a
  // half-copied model. The end anchor is sdCentsToDollars, not
  // sdCommissionCents: getting that wrong is how the cents-to-dollars arm
  // first reported "is not a function" for a function sitting six lines below
  // the slice.
  const start = html.indexOf(ANCHORS.TIERS);
  const endAnchor = html.indexOf(ANCHORS.toDollars);
  const end = html.indexOf('\n}', endAnchor) + 2;
  ctx = { console, localStorage: null };
  vm.createContext(ctx);
  vm.runInContext(html.slice(start, end), ctx);
}
function withStore(obj) {
  ctx.localStorage = {
    getItem: function (k) { return k === 'sd_agent_commission' ? JSON.stringify(obj) : null; }
  };
}

section('the tiers are a ladder, and every rung carries its own commission');

test('the three the brief names all exist, plus the three already shipped', () => {
  ['retail', 'trade', 'distributor', 'contractor', 'builder', 'designer']
    .forEach(k => assert.ok(ctx.TIERS[k], 'tier "' + k + '" is missing'));
});

test('THE ONE THAT PROTECTS EXISTING QUOTES: no tier key was renamed away', () => {
  // currentTier is stored on every saved quote as a bare string. Renaming
  // contractor/builder/designer into "trade" would make TIERS[key] undefined
  // for every quote already on disk -- which throws, or gets defended with a
  // `|| 1.0` that reprices a builder's quote at full retail.
  ['retail', 'contractor', 'builder', 'designer']
    .forEach(k => assert.ok(ctx.TIERS[k],
      'tier "' + k + '" was removed; every saved quote carrying it now '
      + 'resolves to undefined'));
});

test('discount and commission move TOGETHER down the ladder', () => {
  // A distributor at 22% off cannot carry a retail commission: paying the same
  // rate across both is how a rep's incentive stops matching the shop's.
  const ladder = ['retail', 'designer', 'contractor', 'trade', 'builder', 'distributor'];
  for (let i = 1; i < ladder.length; i++) {
    const hi = ctx.TIERS[ladder[i - 1]], lo = ctx.TIERS[ladder[i]];
    assert.ok(lo.mult <= hi.mult,
      ladder[i] + ' prices HIGHER than ' + ladder[i - 1] + ' (' + lo.mult + ' > ' + hi.mult + ')');
    assert.ok(lo.commission <= hi.commission,
      ladder[i] + ' pays MORE commission than ' + ladder[i - 1]
      + ' on a thinner margin (' + lo.commission + ' > ' + hi.commission + ')');
  }
});

test('every tier has a usable rate -- none is missing, zero or absurd', () => {
  Object.keys(ctx.TIERS).forEach(k => {
    const c = ctx.TIERS[k].commission;
    assert.strictEqual(typeof c, 'number', k + ' has no numeric commission');
    assert.ok(c > 0 && c < 0.25, k + ' commission is ' + c);
    assert.ok(ctx.TIERS[k].label && ctx.TIERS[k].note, k + ' has no label or note');
  });
});

section('the rate resolves, and says where it came from');

test('with no override, the tier rate applies and is named', () => {
  withStore({});
  const r = ctx.sdCommissionFor('distributor', 'E-1');
  assert.strictEqual(r.rate, ctx.TIERS.distributor.commission);
  assert.match(r.source, /Distributor/);
});

test('an agent override wins, and is labelled as one', () => {
  withStore({ 'E-1': 0.07 });
  const r = ctx.sdCommissionFor('retail', 'E-1');
  assert.strictEqual(r.rate, 0.07);
  assert.strictEqual(r.source, 'agent override');
});

test('...but only for THAT agent', () => {
  withStore({ 'E-1': 0.07 });
  assert.strictEqual(ctx.sdCommissionFor('retail', 'E-2').rate, ctx.TIERS.retail.commission);
});

test('AN UNKNOWN TIER IS REPORTED, NOT DEFAULTED', () => {
  // Defaulting to retail here would pay retail commission on a distributor
  // deal and nothing would ever say so.
  withStore({});
  const r = ctx.sdCommissionFor('wholesale', 'E-1');
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.rate, null);
  assert.match(r.source, /unknown tier/);
});

[['', 'the Number(\'\') defect'], ['   ', 'whitespace'], ['abc', 'a non-number'],
 [-0.1, 'a negative rate'], [0.9, 'an absurd 90%'], [true, 'a boolean'],
 [null, 'null'], [{}, 'an object']].forEach(([bad, why]) => {
  test('an override of ' + JSON.stringify(bad) + ' (' + why + ') falls back to '
     + 'the tier rate and SAYS SO', () => {
    // A rep paid 0% because a settings field was left empty looks exactly like
    // a rep deliberately on 0%. The difference has to be visible.
    withStore({ 'E-1': bad });
    const r = ctx.sdCommissionFor('retail', 'E-1');
    assert.strictEqual(r.rate, ctx.TIERS.retail.commission,
      'an override of ' + JSON.stringify(bad) + ' was honoured as ' + r.rate);
    if (bad !== null) {
      assert.strictEqual(r.warn, true,
        'the unusable override was swapped out silently');
    }
  });
});

test('a corrupt sd_agent_commission blob does not take the rate with it', () => {
  ctx.localStorage = { getItem: function () { return '{not json'; } };
  assert.strictEqual(ctx.sdCommissionFor('trade', 'E-1').rate, ctx.TIERS.trade.commission);
  ctx.localStorage = { getItem: function () { return '["an","array"]'; } };
  assert.strictEqual(ctx.sdCommissionFor('trade', 'E-1').rate, ctx.TIERS.trade.commission);
});

section('the money is computed in whole cents');

test('a rate that cannot be resolved yields NO amount, never 0', () => {
  // `null` renders as "unavailable"; 0 renders as a commission of zero
  // dollars, which is a different and wrong claim.
  assert.strictEqual(ctx.sdCommissionCents(5000, null), null);
  assert.strictEqual(ctx.sdCommissionCents(5000, undefined), null);
  assert.strictEqual(ctx.sdCommissionCents(5000, NaN), null);
});

test('THE FLOAT ONE: the result is an INTEGER NUMBER OF CENTS, not dollars', () => {
  // This arm is why the function returns cents at all. The first version
  // returned dollars and this failed on an ordinary 3% commission: 12964/100
  // is 129.63999999999999 in IEEE754, so a "dollars" return value is a float
  // that cannot represent the amount it claims to be. 0.1+0.2 arithmetic on
  // money is the defect api/_lib/dnt-rollup.js already carries, and this is
  // what somebody is paid.
  assert.strictEqual(ctx.sdCommissionCents(0.1, 1), 10);
  assert.strictEqual(ctx.sdCommissionCents(1234.56, 0.035), 4321);
  assert.strictEqual(ctx.sdCommissionCents(8450, 0.015), 12675);
  assert.strictEqual(ctx.sdCommissionCents(19.99, 0.05), 100);
});

test('every tier on a real total yields a whole number of cents', () => {
  Object.keys(ctx.TIERS).forEach(k => {
    [999.99, 4321.45, 18750.01, 0.07].forEach(total => {
      const cents = ctx.sdCommissionCents(total, ctx.TIERS[k].commission);
      assert.strictEqual(typeof cents, 'number', k + ' on ' + total + ' gave ' + cents);
      assert.strictEqual(Number.isInteger(cents), true,
        k + ' on ' + total + ' produced ' + cents + ' cents, which is not an integer');
    });
  });
});

test('...and dollars are produced ONCE, at the edge, by a named function', () => {
  assert.strictEqual(ctx.sdCentsToDollars(4321), 43.21);
  assert.strictEqual(ctx.sdCentsToDollars(null), null);
  assert.match(html, /function sdCentsToDollars\(/,
    'the cents->dollars boundary has no single named place to look at');
});

section('there is ONE tier list, and the quote keeps its own copy of the rate');

test('the AI-quote panel no longer carries a hardcoded tier list', () => {
  // It held a copy of four tiers and would have silently offered no way to
  // price the two added on 2026-09-24.
  const i = html.indexOf('id="aiq-tier"');
  assert.ok(i > 0, 'the AI-quote tier select is gone');
  const el = html.slice(i, html.indexOf('</select>', i));
  assert.ok(!/<option/.test(el),
    'aiq-tier still hardcodes options -- a second tier list to keep in sync');
  assert.match(html, /function sdFillTierSelect\(/,
    'nothing fills aiq-tier, so it renders empty');
  assert.match(html, /sdFillTierSelect\('aiq-tier'/,
    'sdFillTierSelect is defined but aiq-tier is never filled');
});

test('the tier pills offer every tier in TIERS -- no rung is unreachable', () => {
  const pills = html.match(/setTier\('([a-z]+)'/g) || [];
  const offered = new Set(pills.map(s => s.match(/'([a-z]+)'/)[1]));
  const absent = Object.keys(ctx.TIERS).filter(k => !offered.has(k));
  assert.deepStrictEqual(absent, [],
    'priced but not selectable anywhere: ' + absent.join(', '));
});

test('setTier REFUSES an unknown key rather than setting it', () => {
  const i = html.indexOf('function setTier(t, el) {');
  assert.ok(i > 0, 'setTier is gone');
  const body = html.slice(i, i + 700);
  assert.match(body, /if \(!TIERS\[t\]\)/,
    'setTier will happily set a key TIERS cannot resolve');
  assert.ok(body.indexOf('if (!TIERS[t])') < body.indexOf('currentTier = t;'),
    'the guard is after the assignment, which is no guard');
});

test('THE SNAPSHOT: a saved quote stores the rate, not a pointer to it', () => {
  // A rate looked up at read time changes every historical quote the day
  // somebody edits TIERS -- so a commission report stops matching what a rep
  // was told, months later, with nothing to compare against.
  const i = html.indexOf('async function saveQuote() {');
  assert.ok(i > 0, 'saveQuote is gone');
  const body = html.slice(i, i + 2000);
  ['tierKey:', 'tierLabel:', 'agentId:', 'commissionRate:', 'commissionCents:']
    .forEach(f => assert.ok(body.indexOf(f) > 0,
      'the saved quote does not record ' + f));
});

test('the history row reads the SNAPSHOT and never recomputes', () => {
  const i = html.indexOf('function renderHistory()');
  assert.ok(i > 0, 'renderHistory is gone');
  const body = html.slice(i, html.indexOf('\n}', i));
  assert.match(body, /q\.commissionCents/,
    'the history row does not show the stored commission');
  assert.ok(!/sdCommissionFor\s*\(/.test(body),
    'the history row RECOMPUTES the rate, so editing TIERS rewrites history');
});

Promise.resolve().then(() => {
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' TIERED-PRICING ASSERTIONS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
});
