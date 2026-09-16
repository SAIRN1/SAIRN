// api/_lib/roofing-asset-registry.test.js
// REQUIREMENT: an asset is identified by a server-issued id and its state transitions
//   are refused out of order, so a record cannot jump a lifecycle stage
//
// Plain node:assert tests -- no framework, matching api/'s zero-npm-dependency
// convention. Run: node api/_lib/roofing-asset-registry.test.js
//
// Every case is a way this registry could hand a building owner a capital plan
// that is quietly wrong, or tell them a roof is covered when it is not.

const assert = require('assert');
const r = require('./roofing-asset-registry');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ok - ' + name);
  } catch (e) {
    console.error('  FAIL - ' + name + '\n      ' + e.message);
    process.exitCode = 1;
  }
}

const TODAY = '2026-09-02';
const sec = (over) => Object.assign({
  section_id: 'SEC-1', building_id: 'BLD-1', name: 'Main roof',
  system_type: 'TPO', area_sqft: 12000,
  installed_on: '2010-06-01', expected_life_years: 20, life_source: 'our spec sheet'
}, over || {});

// ── it refuses to assume ──────────────────────────────────────────────────

test('every entry point REFUSES without today rather than defaulting to UTC now', () => {
  ['sectionState', 'portfolioForecast', 'warrantyCoverage'].forEach((fn) => {
    const out = r[fn]({});
    assert.strictEqual(out.ok, false, fn + ' should refuse');
    assert.strictEqual(out.error.code, 'NO_TODAY');
  });
});

test('NO EXPECTED LIFE means no plan date -- never a guessed industry figure', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ expected_life_years: null, life_source: null }) });
  assert.strictEqual(e.life_state, 'no_service_life_recorded');
  assert.strictEqual(e.remaining_life_years, null);
  assert.strictEqual(e.replacement_year, null, '"TPO lasts 20 years" is not this app to assert');
});

test('an expected life with NO SOURCE is not planned against either', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ life_source: '' }) });
  assert.strictEqual(e.life_state, 'no_source_for_service_life');
  assert.strictEqual(e.replacement_year, null);
  assert.ok(/name where it comes from/.test(e.flags.join(' ')));
});

test('no install date cannot produce an age, and says which fact is missing', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ installed_on: null }) });
  assert.strictEqual(e.life_state, 'no_install_date');
  assert.strictEqual(e.age_years, null);
});

// ── calendar life ─────────────────────────────────────────────────────────

test('a roof past its expected life says so, with a negative remaining', () => {
  // The default fixture is installed 2010-06-01 with a 20-year life, so on
  // 2026-09-02 it has ~3.7 years left and the default 5-year horizon makes it
  // DUE, not merely within life. My first draft asserted 'within_life' here and
  // it failed -- correctly, and it contradicted the very next test in this file.
  // A roof three years from replacement is exactly what the horizon exists to
  // surface.
  const e = r.sectionState({ today: TODAY, section: sec() });
  assert.strictEqual(e.life_state, 'due_within_horizon');
  assert.ok(e.remaining_life_years > 3 && e.remaining_life_years < 4);
  const young = r.sectionState({ today: TODAY, section: sec({ installed_on: '2024-06-01' }) });
  assert.strictEqual(young.life_state, 'within_life');
  const old = r.sectionState({ today: TODAY, section: sec({ installed_on: '2000-06-01' }) });
  assert.strictEqual(old.life_state, 'past_expected_life');
  assert.ok(old.remaining_life_years < 0);
  assert.strictEqual(old.replacement_year, 2020);
});

test('due_within_horizon is a caller setting, not an engineering figure', () => {
  const s = sec({ installed_on: '2010-06-01', expected_life_years: 20 });   // ~3.7y left
  assert.strictEqual(r.sectionState({ today: TODAY, section: s, horizon_years: 5 }).life_state, 'due_within_horizon');
  assert.strictEqual(r.sectionState({ today: TODAY, section: s, horizon_years: 1 }).life_state, 'within_life');
});

// ── condition is NOT folded into remaining life ───────────────────────────

test('condition is reported on its own terms, never blended into a year count', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ condition_score: 2, condition_on: '2026-08-01' }) });
  assert.strictEqual(e.condition, 2);
  assert.strictEqual(e.condition_state, 'poor');
  // The remaining life is still the CALENDAR figure -- no invented adjustment.
  const plain = r.sectionState({ today: TODAY, section: sec() });
  assert.strictEqual(e.remaining_life_years, plain.remaining_life_years);
});

test('poor condition inside its life is FLAGGED -- the disagreement is the point', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ installed_on: '2022-06-01', condition_score: 1, condition_on: '2026-08-01' }) });
  assert.strictEqual(e.life_state, 'within_life');
  assert.ok(/scored poor but not near/.test(e.flags.join(' ')));
});

test('good condition PAST its life is flagged the other way', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ installed_on: '2000-06-01', condition_score: 5, condition_on: '2026-08-01' }) });
  assert.ok(/may outlast the figure entered/.test(e.flags.join(' ')));
});

test('past its life and never inspected is its own flag', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ installed_on: '2000-06-01' }) });
  assert.strictEqual(e.condition_state, 'not_inspected');
  assert.ok(/never inspected/.test(e.flags.join(' ')));
});

test('a condition score with no date is used but its unknown age is flagged', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ condition_score: 5 }) });
  assert.strictEqual(e.condition, 5);
  assert.ok(/no inspection date/.test(e.flags.join(' ')));
});

test('an out-of-range condition score is flagged and NOT used', () => {
  const e = r.sectionState({ today: TODAY, section: sec({ condition_score: 9 }) });
  assert.strictEqual(e.condition, null);
  assert.strictEqual(e.condition_state, 'not_inspected');
  assert.ok(/not one of/.test(e.flags.join(' ')));
});

// ── the forecast ──────────────────────────────────────────────────────────

test('sections group into replacement years with their areas', () => {
  const f = r.portfolioForecast({ today: TODAY, sections: [
    sec({ section_id: 'A', installed_on: '2010-01-01', expected_life_years: 20, area_sqft: 1000 }),
    sec({ section_id: 'B', installed_on: '2010-01-01', expected_life_years: 20, area_sqft: 2000 }),
    sec({ section_id: 'C', installed_on: '2015-01-01', expected_life_years: 20, area_sqft: 500 })
  ] });
  assert.deepStrictEqual(f.years.map(y => y.year), [2030, 2035]);
  assert.strictEqual(f.years[0].sections, 2);
  assert.strictEqual(f.years[0].area_sqft, 3000);
});

test('UNPLANNABLE sections are surfaced with their area, not silently dropped', () => {
  const f = r.portfolioForecast({ today: TODAY, sections: [
    sec({ section_id: 'A', area_sqft: 1000 }),
    sec({ section_id: 'B', expected_life_years: null, life_source: null, area_sqft: 9000 })
  ] });
  assert.strictEqual(f.unplannable.length, 1);
  assert.strictEqual(f.unplannable[0].reason, 'no_service_life_recorded');
  assert.strictEqual(f.unplannable_area_sqft, 9000,
    'a forecast that hides the un-assessed roofs understates the plan by exactly the ones most likely to fail');
  assert.strictEqual(f.planned_area_sqft, 1000);
});

test('overdue, due-soon and poor-condition are listed separately', () => {
  const f = r.portfolioForecast({ today: TODAY, horizon_years: 5, sections: [
    sec({ section_id: 'OLD', installed_on: '2000-01-01' }),
    sec({ section_id: 'SOON', installed_on: '2010-01-01' }),
    sec({ section_id: 'BAD', installed_on: '2024-01-01', condition_score: 1, condition_on: '2026-08-01' })
  ] });
  assert.deepStrictEqual(f.overdue, ['OLD']);
  assert.deepStrictEqual(f.due_within_horizon, ['SOON']);
  assert.deepStrictEqual(f.poor_condition, ['BAD']);
});

// ── warranty cross-check ──────────────────────────────────────────────────

const warr = [
  { warranty_id: 'W-OK', status: 'registered', coverage_expires_on: '2040-01-01' },
  { warranty_id: 'W-OLD', status: 'registered', coverage_expires_on: '2020-01-01' },
  { warranty_id: 'W-VOID', status: 'void', coverage_expires_on: '2040-01-01' },
  { warranty_id: 'W-NODATE', status: 'registered' }
];

test('coverage is matched by an EXPLICIT id, and an active one reads active', () => {
  const c = r.warrantyCoverage({ today: TODAY, warranties: warr, sections: [sec({ warranty_id: 'W-OK' })] });
  assert.strictEqual(c.sections[0].coverage, 'active');
  assert.strictEqual(c.covered, 1);
  assert.strictEqual(c.needs_attention.length, 0);
});

test('a warranty id that is NOT on file is never reported as covered', () => {
  const c = r.warrantyCoverage({ today: TODAY, warranties: warr, sections: [sec({ warranty_id: 'W-TYPO' })] });
  assert.strictEqual(c.sections[0].coverage, 'warranty_not_found');
  assert.strictEqual(c.covered, 0, 'a typo must not read as coverage to a building owner');
});

test('expired, void, no-end-date and none-recorded are four different answers', () => {
  const c = r.warrantyCoverage({ today: TODAY, warranties: warr, sections: [
    sec({ section_id: 'a', warranty_id: 'W-OLD' }),
    sec({ section_id: 'b', warranty_id: 'W-VOID' }),
    sec({ section_id: 'c', warranty_id: 'W-NODATE' }),
    sec({ section_id: 'd', warranty_id: null })
  ] });
  assert.deepStrictEqual(c.sections.map(x => x.coverage),
    ['expired', 'void', 'no_end_date_recorded', 'none_recorded']);
  assert.strictEqual(c.needs_attention.length, 4);
});

// ── A PORTFOLIO THAT READS CLEAN WHILE ITS SECTIONS DO NOT (2026-09-13) ───
// `unplannable` carries sections with no replacement year. A section can be
// FULLY PLANNABLE -- counted in the year buckets and in planned_area_sqft --
// and still carry sectionState()'s own flags. Those were produced, tested at
// section level, and then discarded by portfolioForecast.

// A: condition_score 7 is not 1..5, so condition_state stays 'not_inspected'
// and A is EXCLUDED from poor_condition -- while its 10,000 sqft is counted.
const FL_A = sec({ section_id: 'A', area_sqft: 10000, installed_on: '2010-01-01',
                   expected_life_years: 20, condition_score: 7, condition_on: '2026-01-01' });
// C: a score with no date. Plannable, counted, and its age is unknown.
const FL_C = sec({ section_id: 'C', area_sqft: 2000, installed_on: '2015-01-01',
                   expected_life_years: 25, condition_score: 4, condition_on: null });
// CLEAN: plannable, scored, dated, sourced. Nothing to say about it.
const FL_OK = sec({ section_id: 'OK', area_sqft: 1000, installed_on: '2016-01-01',
                    expected_life_years: 25, condition_score: 4, condition_on: '2026-01-01' });

test('the sections themselves really do carry flags, or the rest proves nothing', () => {
  assert.ok(r.sectionState({ section: FL_A, today: TODAY }).flags.length,
    'fixture A must be flagged');
  assert.ok(r.sectionState({ section: FL_C, today: TODAY }).flags.length,
    'fixture C must be flagged');
  assert.deepStrictEqual(r.sectionState({ section: FL_OK, today: TODAY }).flags, [],
    'fixture OK must be CLEAN, or the control below is meaningless');
});

test('and the portfolio now carries them instead of dropping them', () => {
  const p = r.portfolioForecast({ today: TODAY, sections: [FL_A, FL_C, FL_OK] });
  assert.deepStrictEqual(p.flagged.map((f) => f.section_id).sort(), ['A', 'C']);
  assert.ok(/not one of/.test(p.flagged.find((f) => f.section_id === 'A').flags.join(' ')));
});

test('the flagged sections are COUNTED, which is what makes dropping them dangerous', () => {
  const p = r.portfolioForecast({ today: TODAY, sections: [FL_A, FL_C, FL_OK] });
  assert.strictEqual(p.sections_evaluated, 3);
  assert.strictEqual(p.planned_area_sqft, 13000,
    "A's 10000 is in the plan while its condition entry was rejected");
  assert.deepStrictEqual(p.poor_condition, [],
    'A is absent from poor_condition precisely BECAUSE its score was rejected');
});

test('CONTROL: a portfolio of clean sections reports NO flagged sections', () => {
  const p = r.portfolioForecast({ today: TODAY, sections: [FL_OK] });
  assert.deepStrictEqual(p.flagged, [],
    'without this, a field listing every section would pass the arm above');
  assert.strictEqual(p.not_evaluated, 0);
});

test('flagged and unplannable PARTITION -- a section cannot be counted in both', () => {
  // no life_source: unplannable, and it also carries a flag at section level
  const noSource = sec({ section_id: 'NS', installed_on: '2012-01-01',
                         expected_life_years: 20, life_source: null });
  const p = r.portfolioForecast({ today: TODAY, sections: [noSource, FL_A] });
  assert.deepStrictEqual(p.unplannable.map((u) => u.section_id), ['NS']);
  assert.deepStrictEqual(p.flagged.map((f) => f.section_id), ['A'],
    'NS has no replacement year, so it belongs in unplannable and nowhere else');
});

test('sections that could not be evaluated at all are named, not silently dropped', () => {
  const p = r.portfolioForecast({ today: TODAY, sections: [FL_OK, null, undefined] });
  assert.strictEqual(p.sections_evaluated, 1);
  assert.strictEqual(p.not_evaluated, 2,
    'before this, 1-of-3 and 1-of-1 were indistinguishable to a caller');
});

console.log(passed + ' passed');
