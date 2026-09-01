// JURISDICTION_COVERAGE is the contract for a disclosed coverage gap.
//
// TWO DECISIONS MADE BY MICHAEL ON 2026-09-01, and this file is what keeps
// both true rather than true-for-now.
//
//   1. COVERAGE IS THE CHANNEL. An EARLY-direction omission is disclosed here,
//      not in a rule's own authority note. Utah and Nevada previously declared
//      no entry and asserted that absence, on the view that their gaps were
//      "row-level". An audit measured that claim: only 2 of Utah's 9 rows and
//      2 of Nevada's 10 carried any omission-flavoured note, and the ones
//      sampled explained rule STRUCTURE rather than naming the omissions the
//      gate docs listed -- so a caller was told through neither channel. Both
//      are now on the table with the other sixteen.
//
//   2. A LATE-DIRECTION DISCLOSURE IS ITS OWN CATEGORY. The header comment on
//      the table states a dichotomy -- REFUSED when a gap can report LATE,
//      DISCLOSED when it can only report EARLY -- and exactly one entry does
//      not fit it. Alabama's Ala. Code Sec. 1-3-8(f)(1) lets a state office
//      STAY OPEN on a state holiday on sixty days' notice, which cannot be
//      refused on (no readable signal) and cannot be modelled (discretionary,
//      per-office). It carried `direction: 'early'` and the danger sat in the
//      middle of a paragraph. It is now `direction: 'late'` with a structured
//      `late_exposure` block.
//
// THE POINT OF THE INVARIANT IS THAT A SECOND ONE CANNOT ARRIVE QUIETLY. An
// entry that is 'late' without the block, or carries the block without being
// 'late', fails at module load. That is deliberate: this is in-code data, so a
// defect is a bug, and a bug that stops the engine loading is caught by the
// first test that requires it rather than by a caller filing late.

const engine = require('./deadline-engine.js');
const C = engine.JURISDICTION_COVERAGE;

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

// ── The table is well formed, by the engine's own validator ───────────────
check('the shipped table has zero defects', engine.coverageTableDefects(C), []);
check('the validator is exported, so this file and the load-time check are the same code',
  typeof engine.coverageTableDefects, 'function');

// ── Decision 1: coverage is the channel ──────────────────────────────────
check('Utah is on the table', !!C.ut, true);
check('Nevada is on the table', !!C.nv, true);
check('both are EARLY-direction', [C.ut.direction, C.nv.direction], ['early', 'early']);
check("Utah's entry names the clerk-inaccessibility omission the gate doc listed",
  /INACCESSIBILITY/i.test(C.ut.detail), true);
check("Utah's entry names the 2026 calendar cap, which is the other thing a caller cannot see",
  /2026/.test(C.ut.summary) && /refus/i.test(C.ut.summary), true);
check("Nevada's entry names all three unmodelled limbs from its standard's comment",
  [/6\(a\)\(2\)/.test(C.nv.detail), /6\(a\)\(4\)\(A\)/.test(C.nv.detail), /6\(a\)\(3\)/.test(C.nv.detail)],
  [true, true, true]);

// Every entry carries the four fields a caller reads.
const missingFields = Object.keys(C).filter(k =>
  typeof C[k].complete !== 'boolean' || !C[k].direction || !C[k].summary || !C[k].detail);
check('every entry has complete, direction, summary and detail', missingFields, []);

// Prose and field must agree in the safe direction: an 'early' entry has to
// say EARLIER somewhere in its summary, or the label and the text disagree.
const earlySilent = Object.keys(C).filter(k => C[k].direction === 'early' && !/EARLIER/i.test(C[k].summary));
check("every EARLY entry's summary actually says EARLIER", earlySilent, []);

// ── Decision 2: the late category stands alone ───────────────────────────
const late = Object.keys(C).filter(k => C[k].direction === 'late');
check('exactly one jurisdiction carries a LATE-direction disclosure', late, ['al']);
check('and it is the only one carrying a late_exposure block',
  Object.keys(C).filter(k => C[k].late_exposure), ['al']);
check("Alabama's late_exposure names the authority, not just the risk",
  C.al.late_exposure.authority, 'Ala. Code Sec. 1-3-8(f)(1)');
check('it says why refusing was not available, so the choice is auditable',
  /discretionary/i.test(C.al.late_exposure.why_not_refused), true);
check('and it tells the caller what to actually do',
  /confirm that the court was in fact closed/i.test(C.al.late_exposure.caller_action), true);

// The whole point: a caller switching on direction must be able to find it.
check('a LATE jurisdiction is distinguishable from every EARLY one by the field alone',
  Object.keys(C).filter(k => C[k].direction !== 'early').length, 1);

// ── The invariant refuses the shapes that would let a second one hide ────
const base = { complete: false, summary: 'EARLIER', detail: 'd' };
check("'late' with no late_exposure is a defect",
  engine.coverageTableDefects({ x: { ...base, direction: 'late' } }).length, 1);
check('a late_exposure block on an early entry is a defect',
  engine.coverageTableDefects({ x: { ...base, direction: 'early',
    late_exposure: { authority: 'a', summary: 's', why_not_refused: 'w', caller_action: 'c' } } }).length, 1);
check('a direction outside early/late is a defect',
  engine.coverageTableDefects({ x: { ...base, direction: 'mixed' } }).length, 1);
check('a late_exposure missing any required key is a defect, one per key',
  engine.coverageTableDefects({ x: { ...base, direction: 'late', late_exposure: { authority: 'a' } } }).length, 3);
check('a well-formed late entry is accepted',
  engine.coverageTableDefects({ x: { ...base, direction: 'late',
    late_exposure: { authority: 'a', summary: 's', why_not_refused: 'w', caller_action: 'c' } } }), []);

// ── The disclosure actually reaches a computation ────────────────────────
// Not a structural claim: the text has to ride on a real result, which is the
// entire reason this table exists rather than a comment in the seed.
const fs = require('fs');
const path = require('path');
const SQL = path.join(__dirname, '..', '..', 'sql');
function computeFor(state, code) {
  const seed = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_seed_' + state + '.json'), 'utf8'));
  const cal = JSON.parse(fs.readFileSync(path.join(SQL, 'sairnlaw_deadline_calendars_' + state + '.json'), 'utf8'));
  const calendars = {};
  for (const row of cal.holiday_calendars) {
    calendars[row.jurisdiction] = calendars[row.jurisdiction] || {};
    calendars[row.jurisdiction][String(row.year)] = row.dates;
  }
  const rule = seed.rules[0];
  const ev = typeof rule.trigger_event === 'string' ? rule.trigger_event : rule.trigger_event.id;
  return engine.computeDeadline({
    jurisdiction: code, domain: rule.domain, trigger_event: ev,
    trigger_date: '2026-06-01', rules: seed.rules, calendars, as_of: '2026-06-01'
  });
}
for (const [state, code] of [['utah', 'ut'], ['nevada', 'nv'], ['alabama', 'al']]) {
  const r = computeFor(state, code);
  check(code + ': a real computation carries the coverage disclosure',
    [r.ok, !!r.coverage, r.coverage && r.coverage.direction],
    [true, true, C[code].direction]);
}
check('and the Alabama result carries the late_exposure block itself, not just the label',
  !!computeFor('alabama', 'al').coverage.late_exposure, true);

console.log('\ndeadline-coverage-contract: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
