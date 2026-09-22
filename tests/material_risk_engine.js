// tests/material_risk_engine.js
// REQUIREMENT: [0072] a per-material job-risk verdict is COMPUTED from the shop's own remake
//   records and its own baseline rate, and refuses to answer where the evidence is too thin
//
// Run:  node tests/material_risk_engine.js
//
// [0072] THE MATERIAL-CORRELATED JOB-RISK ENGINE.
//
// Before this, StoneDesk's risk detection was material-BLIND: runAlertScan() had two time
// rules and the health score had three, and not one of them read `material`. The remake log
// had been recording material, a seven-value failure mode and a cost per job the whole time,
// and the only thing consuming it was a Claude prompt -- a different answer every run, nothing
// stored, nothing thresholded, nothing testable.
//
// MOST OF WHAT IS ASSERTED BELOW IS NOT THE ARITHMETIC. A rate is easy. The four places this
// kind of engine goes quietly wrong are:
//
//   * A DENOMINATOR THAT IS ALWAYS EMPTY. sd_jobs writes `material:''` at its only creation
//     site and nothing sets it -- the same frozen-field shape fixed in the Seam AI panel this
//     same session. The source arms at the bottom assert the engine does not read it.
//   * A SILENT ZERO. A material with remakes whose name matches no job must be reported, not
//     dropped: dropped, it reads exactly like a clean shop.
//   * A MATCHER THAT MERGES TWO ROCKS. Quartz and Quartzite are different materials and the
//     distinction is the one a fabricator cares about most. Normalise case and whitespace,
//     and nothing else.
//   * A REFUSAL RENDERED AS A PASS. "not enough jobs to have an opinion" and "this material is
//     fine" are different answers; sdMaterialRiskFor() returns null for the first and an
//     object with level 'ok' for the second.
//
// The implementation is extracted from the real stonedesk.html rather than restated here, so
// this file fails if what ships changes.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

function grab(startMarker, endMarker) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const e = html.indexOf(endMarker, s);
  assert.ok(e > s, 'unterminated: ' + startMarker);
  return html.slice(s, e);
}

const ctx = { console, Date, Math, JSON, String, Number, Array, Object, sdCustomers: [], sdRemakes: [] };
vm.createContext(ctx);
// The REAL escHtml, not a stub: the renderer prints material names the shop typed, and a stub
// would make the escaping arm below assert against itself.
vm.runInContext(grab('function escHtml(s){', 'window.escHtml=escHtml;'), ctx);
vm.runInContext(grab('var SD_MATRISK_MIN_JOBS = 4;', 'function runAlertScan() {'), ctx);
vm.runInContext(grab('function sdRenderMaterialRisk(rep){', '\n// == EXECUTIVE SUITE'), ctx);
const { sdMaterialRisk, sdMaterialRiskFor, sdMatKey,
        SD_MATRISK_MIN_JOBS, SD_MATRISK_MIN_REMAKES,
        SD_MATRISK_YELLOW_X, SD_MATRISK_RED_X } = ctx;

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; }
function eq(a, b, label) { assert.strictEqual(a, b, label); n++; }
function close(a, b, label) { assert.ok(Math.abs(a - b) < 1e-9, label + ' (got ' + a + ', want ' + b + ')'); n++; }

function custs(spec) {
  const out = [];
  Object.keys(spec).forEach((mat) => {
    for (let i = 0; i < spec[mat]; i++) out.push({ id: mat + i, name: mat + ' cust ' + i, material: mat });
  });
  return out;
}
function remakes(list) {
  return list.map((r, i) => ({ id: 'RM' + i, customer: 'x' + i, material: r[0],
                               reason: r[1] || 'cut_error', cost: r[2] === undefined ? 0 : r[2] }));
}
function run(c, r) { ctx.sdCustomers = c; ctx.sdRemakes = r; return sdMaterialRisk(); }

eq(SD_MATRISK_MIN_JOBS, 4, 'the job floor is the same 4 computePricingInsight() already chose');
eq(SD_MATRISK_MIN_REMAKES, 2, 'one remake is an incident, not a pattern');
eq(SD_MATRISK_YELLOW_X, 2, 'yellow at 2x the shop baseline');
eq(SD_MATRISK_RED_X, 3, 'red at 3x');

// ── IT REFUSES BEFORE IT GUESSES. Two different reasons, both reported, neither collapsed
// ── into "no elevated material".
let rep = run([], []);
eq(rep.available, false, 'no customers at all -> not available');
ok(/no customer record carries a material/.test(rep.reason), 'and it says which of the two it is');
rep = run(custs({ Granite: 10 }), []);
eq(rep.available, false, 'customers but no remakes -> not available');
ok(/no remake has been logged/.test(rep.reason), 'and the reason distinguishes it from the first');
eq(rep.materials.length, 0, 'an unavailable report offers no verdicts');

// ── A CUSTOMER WITH NO MATERIAL IS NOT A DENOMINATOR. Counting it would dilute every rate
// ── and make the baseline quietly optimistic.
rep = run(custs({ Granite: 10 }).concat([{ id: 'z', name: 'z', material: '' }, { id: 'y', name: 'y' }]),
          remakes([['Granite', 'cut_error', 100], ['Granite', 'cut_error', 100]]));
eq(rep.baseline.jobs, 10, 'customers with no material are not in the denominator');
eq(rep.baseline.remakes, 2, 'and the numerator counts only remakes on materials that have jobs');

// ── THE HEADLINE CASE. Granite 20 jobs / 0 remakes, Marble 5 jobs / 4 remakes.
// ── baseline 4/25 = 0.16; marble 0.8 -> ratio 5.0 -> red.
rep = run(custs({ Granite: 20, Marble: 5 }),
          remakes([['Marble', 'material_defect', 400], ['Marble', 'material_defect', 300],
                   ['Marble', 'edge_error', 100], ['Marble', 'material_defect', 200]]));
eq(rep.available, true, 'enough evidence -> available');
close(rep.baseline.rate, 4 / 25, 'the baseline is the shop\'s own rate, not a constant');
const marble = rep.materials.find((m) => m.material === 'Marble');
const granite = rep.materials.find((m) => m.material === 'Granite');
close(marble.rate, 0.8, 'marble rate is remakes over jobs of that material');
close(marble.ratio, 0.8 / (4 / 25), 'the ratio is against the shop baseline');
eq(marble.level, 'red', 'five times the shop baseline is red');
eq(granite.level, 'ok', 'a material with no remakes is ok, not null and not flagged');
eq(marble.cost, 1000, 'cost is summed across that material\'s remakes');
eq(marble.topReason, 'material_defect', 'the dominant failure mode is the mode, not the first seen');
eq(marble.topReasonCount, 3, 'and it carries its own count');
eq(rep.materials[0].material, 'Marble', 'materials are ordered worst-ratio first');

// ── YELLOW SITS BETWEEN. Granite 10/1, Marble 10/6, Quartz 10/0 -> baseline 7/30;
// ── marble 0.6 -> ratio 2.57 -> yellow, not red.
rep = run(custs({ Granite: 10, Marble: 10, Quartz: 10 }),
          remakes([['Granite', 'cut_error'], ['Marble', 'cut_error'], ['Marble', 'cut_error'],
                   ['Marble', 'cut_error'], ['Marble', 'cut_error'], ['Marble', 'cut_error'],
                   ['Marble', 'cut_error']]));
eq(rep.materials.find((m) => m.material === 'Marble').level, 'yellow', '2.57x is yellow');
eq(rep.materials.find((m) => m.material === 'Granite').level, 'ok', 'below the shop baseline is ok');

// ── ONE REMAKE NEVER FLAGS, however extreme the ratio. Without this floor a single remake
// ── against four jobs is a 25% rate that outranks everything real.
rep = run(custs({ Granite: 40, Marble: 4 }),
          remakes([['Marble', 'cut_error'], ['Granite', 'cut_error']]));
const m1 = rep.materials.find((m) => m.material === 'Marble');
ok(m1.ratio >= SD_MATRISK_RED_X, 'the ratio really is above the red line');
eq(m1.level, 'ok', '...and it is still not flagged, because one remake is not a pattern');

// ── TOO FEW JOBS IS A THIRD ANSWER, not a verdict. It appears in `insufficient` and NOT in
// ── `materials`, so nothing downstream can read it as ok.
rep = run(custs({ Granite: 20, Marble: 3 }),
          remakes([['Marble', 'cut_error'], ['Marble', 'cut_error'], ['Granite', 'cut_error'],
                   ['Granite', 'cut_error']]));
eq(rep.materials.some((m) => m.material === 'Marble'), false, 'below the job floor -> no verdict');
eq(rep.insufficient.some((m) => m.material === 'Marble'), true, '...and it is named, not dropped');
eq(sdMaterialRiskFor('Marble', rep), null, 'sdMaterialRiskFor returns null, which is not "ok"');

// ── A SILENT ZERO IS THE FAILURE THIS CATCHES. Remakes against a material no job carries --
// ── a deleted customer, or the intake select and the remake input disagreeing.
rep = run(custs({ Granite: 20 }),
          remakes([['Granite', 'cut_error'], ['Granite', 'cut_error'],
                   ['Calacatta Gold', 'material_defect', 900]]));
const un = rep.unmatched.find((u) => u.material === 'Calacatta Gold');
ok(un, 'a material with remakes and no jobs is reported as unmatched');
eq(un.remakes, 1, 'with its count');
eq(un.cost, 900, 'and its cost, so the money is not lost with it');
eq(rep.baseline.jobs, 20, 'an unmatched material does not enter the denominator');
eq(rep.baseline.remakes, 2, 'nor the numerator -- it would be a rate over a population of zero');

// ── THE NAME IS TYPED TWICE, BY TWO PEOPLE, IN TWO WIDGETS.
eq(sdMatKey('  Quartz   (ENGINEERED) '), sdMatKey('quartz (engineered)'),
   'case and internal whitespace are normalised');
rep = run(custs({ 'Quartz (Engineered)': 10 }),
          remakes([['  quartz   (ENGINEERED)  ', 'cut_error'], ['quartz (engineered)', 'cut_error']]));
eq(rep.unmatched.length, 0, 'a spelling difference does not become an unmatched material');
eq(rep.materials.find((m) => m.material === 'Quartz (Engineered)').remakes, 2,
   'both spellings land on the one material');

// ── AND IT MUST NOT MERGE TWO ROCKS. This is the one distinction a fabricator cares about
// ── most, and any fuzzy matcher gets it wrong.
rep = run(custs({ Quartz: 10, Quartzite: 10 }),
          remakes([['Quartzite', 'cut_error'], ['Quartzite', 'cut_error'], ['Quartzite', 'cut_error'],
                   ['Quartzite', 'cut_error'], ['Quartzite', 'cut_error'], ['Quartzite', 'cut_error']]));
eq(rep.materials.find((m) => m.material === 'Quartz').remakes, 0, 'Quartz keeps its own zero');
eq(rep.materials.find((m) => m.material === 'Quartzite').remakes, 6, 'Quartzite keeps its own six');

// ── A NON-NUMERIC COST IS ZERO, NOT NaN. One bad row must not turn the whole cost figure
// ── into NaN on screen, which is the shape that gets read as a rendering bug and ignored.
rep = run(custs({ Granite: 10 }),
          remakes([['Granite', 'cut_error', 'not a number'], ['Granite', 'cut_error', 250]]));
eq(rep.materials.find((m) => m.material === 'Granite').cost, 250, 'an unparseable cost contributes 0');

// ── THE STATED LIMITATION IS ASSERTED, so it cannot be quietly "fixed" into a leave-one-out
// ── baseline without this arm failing and forcing the comment to be re-read.
rep = run(custs({ Granite: 20 }),
          remakes([['Granite', 'cut_error'], ['Granite', 'cut_error'], ['Granite', 'cut_error']]));
close(rep.materials[0].ratio, 1, 'a single-material shop is its own baseline -> ratio 1');
eq(rep.materials[0].level, 'ok', '...and is never flagged, which the header states outright');

// ── sdMaterialRiskFor FALLS BACK AND FAILS SOFT.
eq(sdMaterialRiskFor('', rep), null, 'no material -> null');
eq(sdMaterialRiskFor('Nonexistent', rep), null, 'unknown material -> null, never a fabricated ok');

// ── THE WIRING. The engine can be perfect and read by nothing, which is [0040] exactly.
ok(/\[0072\][^\n]*THE FIRST RULE IN THIS SCAN THAT READS THE MATERIAL/.test(html),
   'runAlertScan carries the material rule');
ok(/const mr = sdMaterialRiskFor\(c\.material, matRisk\);/.test(html),
   'and it asks the engine per customer, reusing the one report');
ok(/const matRisk = sdMaterialRisk\(\);/.test(html),
   'computed once per scan, not once per customer');
ok(/if\(matRisk&&matRisk\.level==='red'\)score-=20;/.test(html),
   'the health score subtracts 20 on red');
ok(/else if\(matRisk&&matRisk\.level==='yellow'\)score-=10;/.test(html),
   'and 10 on yellow');
ok(/Health score reduced by/.test(html),
   'the modal says WHY the score moved rather than moving it silently');

// ── AND IT DOES NOT BUILD ON THE EMPTY DENOMINATOR. sd_jobs.material is written '' at its
// ── only creation site and set by nothing; a rate over it would be the frozen-field defect
// ── again, one panel across.
const engine = grab('var SD_MATRISK_MIN_JOBS = 4;', 'function runAlertScan() {');
eq(/sd_jobs|sdJobs/.test(engine), false, 'the engine never reads sd_jobs, whose material is always empty');
eq(/sdFinJobs|sd_fin_jobs/.test(engine), false, 'nor sd_fin_jobs, which is optional bookkeeping');

// ── THE RENDERER. The engine shipped with `unmatched` reaching NO SCREEN -- a correct
// ── producer with no reader, which is [0040]'s shape. These arms exist so it cannot go
// ── unreachable again quietly.
const { sdRenderMaterialRisk } = ctx;
ok(typeof sdRenderMaterialRisk === 'function', 'the renderer was extracted');

// The refusal is PRINTED. A shop that sees nothing cannot tell "the check ran and found
// nothing" from "the check is waiting on you".
let h = sdRenderMaterialRisk(run([], []));
ok(/no verdict yet/.test(h), 'an unavailable report renders its refusal rather than nothing');
ok(/no customer record carries a material/.test(h), 'and prints which reason it was');
ok(h.indexOf('' + SD_MATRISK_MIN_JOBS) !== -1, 'and what it is waiting for');

// THE GAP THIS COMMIT CLOSES.
h = sdRenderMaterialRisk(run(custs({ Granite: 20 }),
      remakes([['Granite', 'cut_error'], ['Granite', 'cut_error'],
               ['Calacatta Gold', 'material_defect', 900]])));
ok(/Calacatta Gold/.test(h), 'an unmatched material is RENDERED, not merely computed');
ok(/in no material.{0,10}s rate/.test(h), 'and says plainly that it is in no rate');
ok(/900/.test(h), 'and names the cost that sits outside the analysis');

// Flagged materials render with the figures behind the verdict, not just a colour.
h = sdRenderMaterialRisk(run(custs({ Granite: 20, Marble: 5 }),
      remakes([['Marble', 'material_defect', 400], ['Marble', 'material_defect', 300],
               ['Marble', 'edge_error', 100], ['Marble', 'material_defect', 200]])));
ok(/Marble/.test(h), 'the flagged material is named');
ok(/80% of 5 job/.test(h), 'with its own rate and denominator');
ok(/16%/.test(h), "and the shop's own baseline it was judged against");
ok(/material defect/.test(h), 'and the dominant failure mode, underscores unpicked');
ok(/Granite/.test(h) === false, 'an ok material is not listed as a risk');

// The third list was unreachable too. Shipping `unmatched` alone would repeat the half-sweep
// that left First-Pass Approval at 100% beside a tile cleaned twice in this same file.
h = sdRenderMaterialRisk(run(custs({ Granite: 20, Marble: 3 }),
      remakes([['Marble', 'cut_error'], ['Marble', 'cut_error'],
               ['Granite', 'cut_error'], ['Granite', 'cut_error']])));
ok(/Not enough jobs to judge yet/.test(h), 'insufficient materials are rendered too');
ok(/Marble/.test(h), 'and named');

// ── A MATERIAL NAME IS TEXT THE SHOP TYPED, and it is going into innerHTML.
h = sdRenderMaterialRisk(run(custs({ Granite: 20 }),
      remakes([['Granite', 'cut_error'], ['Granite', 'cut_error'],
               ['<img src=x onerror=alert(1)>', 'other', 50]])));
eq(/<img src=x/.test(h), false, 'a hostile material name is not emitted raw');
ok(/&lt;img src=x/.test(h), '...it is escaped, through the real escHtml');

// ── AND THE RENDERER IS ACTUALLY CALLED. The whole point of this commit.
ok(/zone\.innerHTML=html\+\(typeof sdRenderMaterialRisk==='function'\?sdRenderMaterialRisk\(\):''\)/.test(html),
   'runRemakeAlerts appends the report to the remakes panel');
ok(/if\(reds\.length\) html=/.test(html),
   '...without replacing the urgency banner it already rendered');

console.log(n + ' assertions pass');
