// tests/aiq_speed_and_waste_calc.js
// REQUIREMENT: the "fast AI quote" claim is a MEASUREMENT of this shop's own
//   quotes (median, minimum sample size, refusals untimed), and the public
//   waste calculator uses the QUOTE ENGINE's own waste factor -- never a
//   second model that can drift from what a customer is billed
//
// Run:  node tests/aiq_speed_and_waste_calc.js
//
// ── WHY THE SPEED CLAIM IS TESTED AS HARD AS MONEY ─────────────────────────
// The brief said "3-minute AI quote messaging". A 3 written into markup is a
// fabricated KPI -- a number with no function behind it, the exact class
// sairn-guardian-v2 Check 0b exists for -- and it would be a claim made to a
// paying customer. So the number must be measured, and every way a
// measurement can flatter itself is an arm here: a mean instead of a median,
// a refusal counted as a fast quote, a typical time stated from two samples.

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

section('no hardcoded speed claim anywhere in the panel');

test('THE GUARDIAN ONE: no "N-minute quote" promise is written into markup', () => {
  // The claim must come out of aiqMedianMs() or not exist. A literal
  // "3-minute" / "3 minute" / "three minute" quote promise in the HTML is the
  // fabricated-KPI shape, whatever the number is.
  // HTML comment BLOCKS are stripped whole, not filtered line-by-line -- the
  // comment explaining why the claim is measured names the claim, sits
  // mid-block, and a per-line `^\s*<!--` filter missed it on first run.
  const lines = html.replace(/<!--[\s\S]*?-->/g, '')
    .split(/\r?\n/)
    .filter(l => !/^\s*(\/\/|\*)/.test(l))
    .filter(l => /(\b\d+|three|two|five)[- ]minute\s+(AI\s+)?quote/i.test(l));
  assert.deepStrictEqual(lines, [],
    'a speed promise is hardcoded: ' + JSON.stringify(lines));
});

test('the speed element exists and nothing pre-fills it in markup', () => {
  const i = html.indexOf('id="aiq-speed"');
  assert.ok(i > 0, 'the measured-speed line is gone from the panel');
  const el = html.slice(i, html.indexOf('</div>', i));
  assert.ok(!/\d/.test(el.replace(/font-size:\d+px|margin-top:\d+px/g, '')),
    'aiq-speed carries a number in the markup itself: ' + el);
});

section('the measurement is honest, driven not read');

// Extract the timing block. Reported, never thrown at module scope.
const ANCHOR = 'var AIQ_TIMINGS_KEY=';
const s0 = html.indexOf(ANCHOR);
const e0 = s0 < 0 ? -1 : html.indexOf('window.sdAIQSendToQuote', s0);
let ctx = null;
test('the timing functions are findable', () => {
  assert.ok(s0 > 0 && e0 > s0, 'the AIQ timing block moved; update ANCHOR here');
});
if (s0 > 0 && e0 > s0) {
  ctx = { console, window: {}, localStorage: null,
          document: { getElementById: () => null } };
  vm.createContext(ctx);
  vm.runInContext('var store={};\nvar localStorage={getItem:function(k){return store[k]||null;},setItem:function(k,v){store[k]=String(v);}};\n'
    + html.slice(s0, e0), ctx);
}
function seed(arr) {
  vm.runInContext('store["sd_aiq_timings"]=' + JSON.stringify(JSON.stringify(arr)), ctx);
}

test('UNDER THE MINIMUM SAMPLE it refuses to state a typical time', () => {
  seed([40000, 45000]);
  assert.strictEqual(vm.runInContext('aiqMedianMs()', ctx), null,
    'a median was stated from two samples -- "not enough data" was folded into a number');
});

test('MEDIAN, NOT MEAN: one stalled request cannot drag the headline', () => {
  // Five quick runs and one 10-minute stall. A mean reports ~2 minutes; the
  // median stays where the customer's experience actually is.
  seed([30000, 32000, 34000, 36000, 38000, 600000]);
  const med = vm.runInContext('aiqMedianMs()', ctx);
  assert.strictEqual(med, 35000, 'median of the seeded set should be 35000, got ' + med);
});

test('garbage in the stored timings is filtered, not summed', () => {
  seed([30000, 'abc', null, -5, 32000, 34000, 36000, 38000]);
  const med = vm.runInContext('aiqMedianMs()', ctx);
  assert.strictEqual(med, 34000, 'non-numeric entries leaked into the median: ' + med);
});

test('a corrupt blob yields the honest empty state, not a crash or a zero', () => {
  vm.runInContext('store["sd_aiq_timings"]="{not json"', ctx);
  assert.strictEqual(vm.runInContext('aiqMedianMs()', ctx), null);
});

test('the sample is BOUNDED and the OLDEST are dropped', () => {
  seed(Array.from({ length: 50 }, (_, i) => 10000 + i));
  vm.runInContext('aiqRecordTiming(99999)', ctx);
  const t = JSON.parse(vm.runInContext('store["sd_aiq_timings"]', ctx));
  assert.strictEqual(t.length, 50, 'the window grew past its bound: ' + t.length);
  assert.strictEqual(t[t.length - 1], 99999, 'the new sample was the one dropped');
  assert.ok(t.indexOf(10000) === -1, 'the oldest sample survived the trim');
});

test('an unusable duration is never recorded', () => {
  seed([]);
  ['aiqRecordTiming(NaN)', 'aiqRecordTiming(-100)', 'aiqRecordTiming(0)']
    .forEach(call => vm.runInContext(call, ctx));
  assert.strictEqual(JSON.parse(vm.runInContext('store["sd_aiq_timings"]||"[]"', ctx)).length, 0,
    'a NaN, negative or zero duration reached the record');
});

section('the timer is wired to the real generator, honestly');

test('the clock starts at the click and a time is recorded on success', () => {
  const i = html.indexOf('window.sdAIQGenerate=async function(){');
  assert.ok(i > 0, 'the generator is gone');
  const body = html.slice(i, html.indexOf('window.sdAIQSendToQuote', i));
  assert.match(body, /aiqT0\s*=\s*Date\.now\(\)/, 'no clock is started');
  assert.match(body, /aiqRecordTiming\(/, 'no timing is ever recorded');
});

test('A REFUSAL IS NOT A FAST QUOTE: the early-exit paths record nothing', () => {
  // Counting "could not extract project type" as a 4-second quote is how the
  // median becomes flattering and false.
  const i = html.indexOf('window.sdAIQGenerate=async function(){');
  const body = html.slice(i, html.indexOf('window.sdAIQSendToQuote', i));
  const record = body.indexOf('aiqRecordTiming(');
  const extractFail = body.indexOf('Could not confidently extract');
  const priceFail = body.indexOf('Pricing calculation failed');
  assert.ok(extractFail > 0 && priceFail > 0, 'the refusal paths moved');
  assert.ok(record > extractFail && record > priceFail,
    'a timing is recorded before the refusal paths, so refusals count as quotes');
});

section('the waste calculator shares the engine\'s factor');

test('sdWasteFactorFor applies the SAME expression calc() uses', () => {
  // calc(): `proj.comp >= 1.20 ? 1.20 : 1.15`. Not asserted as prose -- both
  // occurrences are found and compared, so tuning one without the other fails.
  const inCalc = html.match(/const wasteMult = proj\.comp >= ([\d.]+) \? ([\d.]+) : ([\d.]+);/);
  assert.ok(inCalc, 'calc()\'s waste expression moved');
  const inPublic = html.match(/return proj\.comp >= ([\d.]+) \? ([\d.]+) : ([\d.]+);/);
  assert.ok(inPublic, 'sdWasteFactorFor\'s expression moved');
  assert.deepStrictEqual(inPublic.slice(1), inCalc.slice(1),
    'the public calculator and the quote engine use DIFFERENT waste factors -- '
    + 'a customer is shown one number and billed on another');
});

test('an unknown project type is refused, not defaulted to 1.15', () => {
  const i = html.indexOf('window.sdWasteFactorFor=function(typeKey){');
  assert.ok(i > 0, 'sdWasteFactorFor is gone');
  const body = html.slice(i, html.indexOf('\n  };', i));
  assert.match(body, /return null;/,
    'no refusal path -- an unknown type gets a waste allowance nobody computed');
});

test('the input is validated, not coerced -- Number(\'\') stays out', () => {
  const i = html.indexOf('window.sdWasteCalc=function(){');
  assert.ok(i > 0, 'sdWasteCalc is gone');
  const body = html.slice(i, html.indexOf('window.sdWasteCalcPrint', i));
  assert.match(body, /raw\.trim\(\)!==''/,
    'an empty field goes through Number() and becomes a 0 sq ft kitchen');
  assert.match(body, /isFinite\(sqft\)/, 'NaN reaches the arithmetic');
});

test('the project list is filled from PROJECTS, not typed into the markup', () => {
  const i = html.indexOf('id="pwc-type"');
  assert.ok(i > 0, 'the calculator project select is gone');
  const el = html.slice(i, html.indexOf('</select>', i));
  assert.ok(!/<option/.test(el), 'pwc-type hardcodes options -- a second project list');
  assert.match(html, /sdFillProjectSelect\('pwc-type'\)/, 'nothing fills pwc-type');
});

test('the customer-facing text explains the allowance and disclaims the estimate', () => {
  const i = html.indexOf('window.sdWasteCalc=function(){');
  const body = html.slice(i, html.indexOf('window.sdWasteCalcPrint', i));
  assert.match(body, /not a markup and it is not a fee/,
    'the explanation of WHY waste exists is gone -- the number alone reopens the argument');
  const p = html.indexOf('window.sdWasteCalcPrint=function(){');
  assert.match(html.slice(p, p + 1600), /not a quote/,
    'the printed page does not say it is an estimate of quantity, not a quote');
});

Promise.resolve().then(() => {
  console.log('\n' + (fail === 0
    ? 'ALL ' + pass + ' AIQ-SPEED/WASTE-CALC ASSERTIONS PASS'
    : pass + ' passed, ' + fail + ' FAILED'));
  process.exit(fail === 0 ? 0 : 1);
});
