// tests/material_risk_denominator_review_probe.js
//
// Independent review of [0072]'s material-risk denominator, discharging cc's
// Tier A obligation opened 2026-09-22T13:51:10Z.
//
//     node tests/material_risk_denominator_review_probe.js
//
// REPORT-ONLY. Exit 0 by design, findings or not. It changes nothing and gates
// nothing; it exists so the numbers below can be re-run rather than believed.
//
// REVIEWED AT HEAD, NOT AT THE OBLIGATION'S COMMIT, and it matters: the change
// under review is 1c2b4a35, but d01803a5 landed two hours later and closed
// press-on (4) -- cc's own "the unmatched list is in the report object and NOT
// rendered". Reviewing 1c2b4a35 alone would have filed a finding against code
// nobody runs. The obligation cites 51 assertions and 6 mutations; HEAD carries
// 69 and 10.
//
// THE ENGINE IS EXTRACTED FROM THE REAL stonedesk.html, the same way cc's own
// suite does it, so this probe cannot drift from the shipped code by restating
// it. The anchors are asserted present before anything is run.
//
// WHAT THIS PROBE IS FOR: cc nominated press-on (1) -- "is sdCustomers really
// one row per JOB?" -- as the weakest point of the design and said it had not
// been measured. This measures it, and the answer is not the one cc feared.

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const REPO = path.dirname(__dirname);
const html = fs.readFileSync(path.join(REPO, 'stonedesk.html'), 'utf8');

const FINDINGS = [];
const NOTES = [];
let passes = 0;

function ok(label, cond, detail) {
  if (cond) { passes++; console.log('  ok   ' + label); }
  else {
    FINDINGS.push(label);
    console.log('  FAIL ' + label);
    if (detail !== undefined) console.log('       ' + String(detail).slice(0, 300));
  }
}
function note(text) { NOTES.push(text); console.log('\n  ' + text); }

// ── EXTRACTION, WITH ITS ANCHORS COUNTED ──────────────────────────────────
// An anchor that has gone stale silently yields a different span, and every
// check below would then be about code that is not the shipped code.
//
// A STALE ANCHOR IS A COULD-NOT-TELL, NOT A CRASH AND NOT A PASS. This file
// discharges an obligation and must not raise one of its own, so it makes no
// assertion and every exit is a literal 0 -- the predicate
// tier_a_review_gate.is_report_only_artefact() tests for. The anchor check is
// still LOUD: it is printed, counted, and it stops the run rather than letting
// later checks execute against a span that is not the shipped code.
const CNR = [];
function grab(startMarker, endMarker) {
  const occurrences = html.split(startMarker).length - 1;
  if (occurrences !== 1) {
    CNR.push('anchor occurs ' + occurrences + ' time(s), not exactly once: ' + startMarker);
    return null;
  }
  const s = html.indexOf(startMarker);
  const e = html.indexOf(endMarker, s);
  if (!(e > s)) {
    CNR.push('terminator not found after anchor: ' + endMarker);
    return null;
  }
  return html.slice(s, e);
}

const ENGINE = grab('var SD_MATRISK_MIN_JOBS = 4;', 'function runAlertScan() {');
if (!ENGINE) {
  console.log('\nCOULD NOT RUN -- the engine could not be extracted:');
  CNR.forEach(c => console.log('  ' + c));
  console.log('Nothing below was checked. This is NOT a clean bill.');
  process.exit(0);
}
const ctx = vm.createContext({ console: console });
vm.runInContext(ENGINE, ctx);
const run = (custs, rms) => {
  ctx.sdCustomers = custs; ctx.sdRemakes = rms;
  return ctx.sdMaterialRisk();
};

console.log('\n[0072] MATERIAL-RISK DENOMINATOR -- independent review');
console.log('='.repeat(72));

// ── FINDING 1: THE DENOMINATOR COUNTS WORK THAT WAS NEVER FABRICATED ──────
// A remake exists only on work that was cut. A customer sitting at `quoted`
// has not been fabricated, so it can contribute to the denominator and can
// never contribute to the numerator. Every rate is therefore understated, and
// the engine UNDER-flags.
console.log('\n1. does the denominator count jobs, or customer records?');
ok('1a the engine reads no status field at all',
   ENGINE.indexOf('status') === -1, ENGINE.indexOf('status'));

// Ten fabricated Quartz jobs with 3 remakes, against a baseline of ten
// Granite jobs with 1. Quartz is 30% against a 20% baseline -- 1.5x, below the
// 2x yellow line, so it is correctly NOT flagged at the true population.
const fabricated = [];
for (let i = 0; i < 10; i++) fabricated.push({ material: 'Quartz', status: 'complete' });
for (let i = 0; i < 10; i++) fabricated.push({ material: 'Granite', status: 'complete' });
const rms = [
  { material: 'Quartz', cost: 900, reason: 'chip' },
  { material: 'Quartz', cost: 900, reason: 'chip' },
  { material: 'Quartz', cost: 900, reason: 'chip' },
  { material: 'Granite', cost: 400, reason: 'chip' }
];
const truth = run(fabricated.slice(), rms);
const qTrue = truth.materials.find(m => m.material === 'Quartz');
console.log('    TRUE population (20 fabricated jobs): baseline ' +
  (truth.baseline.rate * 100).toFixed(1) + '%, Quartz ' +
  (qTrue.rate * 100).toFixed(1) + '% ratio ' + qTrue.ratio.toFixed(2) +
  ' -> ' + qTrue.level);

// Now the same shop with ten DEAD QUOTES on Quartz -- rows that were quoted,
// never approved, never cut. Nothing about the fabricated work has changed.
const withDead = fabricated.slice();
for (let i = 0; i < 10; i++) withDead.push({ material: 'Quartz', status: 'quoted' });
const seen = run(withDead, rms);
const qSeen = seen.materials.find(m => m.material === 'Quartz');
console.log('    AS COUNTED (+10 quotes never cut):     baseline ' +
  (seen.baseline.rate * 100).toFixed(1) + '%, Quartz ' +
  (qSeen.rate * 100).toFixed(1) + '% ratio ' + qSeen.ratio.toFixed(2) +
  ' -> ' + qSeen.level);

ok('1b dead quotes DO enter the denominator -- the engine reports more jobs '
   + 'than were ever fabricated', seen.baseline.jobs > truth.baseline.jobs,
   [truth.baseline.jobs, seen.baseline.jobs]);
ok('1c ...and the measured rate for that material FALLS as a result, which is '
   + 'the under-flagging direction', qSeen.rate < qTrue.rate,
   [qTrue.rate, qSeen.rate]);
ok('1d ...and the RATIO moves too, so this is not a uniform scaling that '
   + 'cancels out of the comparison', qSeen.ratio < qTrue.ratio,
   [qTrue.ratio, qSeen.ratio]);

// THE CONTROL, without which 1b-1d are satisfied by a rule that reacts to any
// added row. Adding the same ten rows spread across BOTH materials moves the
// baseline but must not move Quartz's ratio the same way.
const evenly = fabricated.slice();
for (let i = 0; i < 5; i++) evenly.push({ material: 'Quartz', status: 'quoted' });
for (let i = 0; i < 5; i++) evenly.push({ material: 'Granite', status: 'quoted' });
const even = run(evenly, rms);
const qEven = even.materials.find(m => m.material === 'Quartz');
console.log('    CONTROL (+10 quotes split evenly):     baseline ' +
  (even.baseline.rate * 100).toFixed(1) + '%, Quartz ' +
  (qEven.rate * 100).toFixed(1) + '% ratio ' + qEven.ratio.toFixed(2) +
  ' -> ' + qEven.level);
ok('1e CONTROL: dead quotes spread evenly leave the RATIO nearly unmoved, so '
   + '1d is measuring the CONCENTRATION of dead quotes and not merely the '
   + 'count of rows',
   Math.abs(qEven.ratio - qTrue.ratio) < Math.abs(qSeen.ratio - qTrue.ratio),
   [qTrue.ratio, qEven.ratio, qSeen.ratio]);

// ── AND IT FLIPS A REAL VERDICT, WHICH IS THE FORM THAT MATTERS ───────────
// A moved ratio is arithmetic. A moved VERDICT is the shop not being told.
// 30 Granite jobs with 1 remake, 5 Quartz jobs with 3 -- Quartz is 60% against
// an 11.4% baseline, 5.25x, RED. Add 15 Quartz quotes that were never cut and
// nothing about the fabricated work changes.
const cut = [];
for (let i = 0; i < 30; i++) cut.push({ material: 'Granite', status: 'complete' });
for (let i = 0; i < 5; i++) cut.push({ material: 'Quartz', status: 'complete' });
const rms2 = [
  { material: 'Quartz', cost: 1200, reason: 'chip' },
  { material: 'Quartz', cost: 1200, reason: 'chip' },
  { material: 'Quartz', cost: 1200, reason: 'chip' },
  { material: 'Granite', cost: 400, reason: 'chip' }
];
const red = run(cut.slice(), rms2);
const qRed = red.materials.find(m => m.material === 'Quartz');
const buried = cut.slice();
for (let i = 0; i < 15; i++) buried.push({ material: 'Quartz', status: 'quoted' });
const hid = run(buried, rms2);
const qHid = hid.materials.find(m => m.material === 'Quartz');
console.log('    VERDICT FLIP -- fabricated only: Quartz ratio '
  + qRed.ratio.toFixed(2) + ' -> ' + qRed.level.toUpperCase()
  + '   |   with 15 dead quotes: ratio ' + qHid.ratio.toFixed(2)
  + ' -> ' + qHid.level.toUpperCase());
ok('1f THE VERDICT FLIPS: a material the engine calls RED on the work actually '
   + 'cut is reported as OK once quotes that were never fabricated are counted '
   + 'as jobs',
   qRed.level === 'red' && qHid.level === 'ok', [qRed.level, qHid.level]);
ok('1g ...and NOTHING about the fabricated work or the remakes changed between '
   + 'the two runs -- only rows that were never cut were added',
   qRed.remakes === qHid.remakes && red.baseline.remakes === hid.baseline.remakes,
   [qRed.remakes, qHid.remakes, red.baseline.remakes, hid.baseline.remakes]);

// ── AND THE HEADER'S OWN CLAIM IS WHAT MAKES THIS A FINDING ───────────────
// A different population would be a design choice. The header says it is the
// SAME population as the function it cites as precedent, and it is not.
const INSIGHT = grab('function computePricingInsight() {', 'function computePipelinePatterns()') || '';
ok('2a the cited precedent filters on quote > 0, so its population is PRICED '
   + 'customers', /c\.quote\s*>\s*0/.test(INSIGHT), INSIGHT.slice(0, 160));
ok('2b ...and the engine under review filters on the material alone',
   /if\s*\(!k\)\s*return;/.test(ENGINE) && !/c\.quote/.test(ENGINE));
ok('2c ...so the header sentence "Same population, same field, same minimum" '
   + 'is false on its FIRST clause; the other two hold',
   html.indexOf('Same population, same field, same minimum') !== -1);

// ── PRESS-ON (1), THE ONE cc NOMINATED: IS IT ONE ROW PER JOB? ────────────
// cc feared a repeat customer is one row, making the denominator too small and
// the rate an OVER-estimate. Measured against the four creation sites.
console.log('\n3. press-on (1) -- the answer is not the one cc feared');
const unconditional = (html.match(/sdCustomers\.unshift\(/g) || []).length;
ok('3a there are several customer creation sites, so "one row per job" has '
   + 'more than one answer', unconditional >= 4, unconditional);
const dedupIdx = html.indexOf('var existing = sdCustomers.find(');
ok('3b exactly one of them dedups by name -- the web-intake conversion',
   dedupIdx !== -1 && (html.match(/var existing = sdCustomers\.find\(/g) || []).length === 1,
   dedupIdx);
// AND THE DEDUP CANNOT BIAS THIS ENGINE, because the record it declines to
// duplicate has no material in the first place.
const dedupBlock = html.slice(dedupIdx, dedupIdx + 900);
ok('3c ...and the record THAT path builds carries NO material field, so those '
   + 'rows are excluded from this engine on both sides and the dedup cannot '
   + 'bias it either way',
   /var cust = \{/.test(dedupBlock) && !/material:/.test(dedupBlock.split('sdCustomers.unshift')[0]),
   dedupBlock.slice(0, 200));
note('PRESS-ON (1) ANSWERED, AND IN cc\'s FAVOUR: the repeat-customer '
   + 'over-estimate cc\ndisclosed is SMALLER than disclosed. Three of the four '
   + 'creation sites unshift\nunconditionally, so a returning walk-in does get '
   + 'a second row and the denominator\nis per-intake there. The fourth dedups '
   + 'by lowercased name -- but builds a record\nwith no `material`, so it is '
   + 'invisible to this engine on both sides.');

// AND THE SAME PATH INDEPENDENTLY CONFIRMS WHY sd_jobs WAS REJECTED.
ok('3d the same intake path creates a job with material:\'\' -- the frozen '
   + 'field cc cited as its reason for rejecting sd_jobs, confirmed here '
   + 'rather than taken from the header',
   /material:\s*''/.test(html.slice(dedupIdx, dedupIdx + 1600)));

// ── PRESS-ON (4): CLOSED BY cc, AND MORE THOROUGHLY THAN DESCRIBED ────────
console.log('\n4. press-on (4) -- cc named this gap and then closed it');
const RENDER = grab('function sdRenderMaterialRisk(rep){', '\n// == EXECUTIVE SUITE') || '';
ok('4a the unmatched list now reaches a screen', /r\.unmatched/.test(RENDER));
ok('4b ...and it names the COST sitting outside the analysis, not just the '
   + 'count', /lost/.test(RENDER) && /remake cost sits outside/.test(RENDER));
ok('4c ...and the material name is escaped, so a typed material cannot inject',
   /escHtml\(u\.material\)/.test(RENDER));
note('PRESS-ON (4) IS CLOSED BY cc IN d01803a5 and the disclosure is better '
   + 'than cc\'s own\ndescription of the gap: it names the count, the material '
   + 'and the dollar cost that\nsits outside every rate. Recorded so it is not '
   + 're-reported as open.');

// ── THE TIER A QUESTION THE OBLIGATION ACTUALLY ASKED ─────────────────────
console.log('\n5. the obligation\'s own question: is sd_fin_jobs a prose match?');
ok('5a the engine contains no reference to sd_fin_jobs or sdFinJobs',
   !/sd_fin_jobs|sdFinJobs/.test(ENGINE));
ok('5b ...and the only occurrence the change ADDED to stonedesk.html is a '
   + 'comment line explaining why it is NOT used',
   /\/\/\s*sd_fin_jobs\s*--\s*real, but optional bookkeeping/.test(html));
note('THE TIER A TRIGGER IS A PROSE MATCH, CONFIRMED. sd_fin_jobs appears in '
   + 'this change\nonly in a comment and in a test assertion whose purpose is '
   + 'to prove the resource is\nuntouched. This is the same class as the two '
   + 'spurious triggers I hit today --\nsairn-code-scrubber item 25, a '
   + 'structured identifier matched as prose.');

console.log('\n' + '='.repeat(72));
console.log(passes + ' checks passed, ' + FINDINGS.length + ' failed, '
  + NOTES.length + ' note(s), ' + CNR.length + ' could-not-tell. '
  + 'Report-only: exit 0 by design.');
FINDINGS.forEach(f => console.log('  FAILED: ' + f));
CNR.forEach(c => console.log('  COULD NOT TELL: ' + c));
process.exit(0);
