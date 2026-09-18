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
//
// ── THE SECOND ONE ARRIVED, AND IT DID NOT ARRIVE QUIETLY (2026-09-18) ─────
// Pennsylvania, on Michael's direction. This file asserted `['al']` in three
// places and FAILED ON THE WAY IN, which is the entire behaviour those
// assertions were written for -- the expectation is updated here as a decision
// with its reasoning attached, not edited to make a suite green.
//
// PA IS A DIFFERENT SPECIES OF LATE AND THE ARMS BELOW KEEP THEM APART.
// Alabama's exposure is an UNMODELLABLE TRIGGER -- real law the engine cannot
// see fire. Pennsylvania's is AN ASSUMPTION THE ENGINE ITSELF MAKES:
// Pa.R.J.A. 107(b) says a weekend or holiday last day is "omitted from the
// computation" and never says the period runs on, and the engine rolls it
// anyway on practice rather than on a citation. If that reading is wrong,
// eleven live rules return dates that are LATE. So this file now asserts the
// PAIR and asserts that PA's own block says "assumption" -- a third entry
// still cannot arrive without editing a stated expectation.

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
check('exactly two jurisdictions carry a LATE-direction disclosure', late.sort(), ['al', 'pa']);
check('and they are the only ones carrying a late_exposure block',
  Object.keys(C).filter(k => C[k].late_exposure).sort(), ['al', 'pa']);
check("Alabama's late_exposure names the authority, not just the risk",
  C.al.late_exposure.authority, 'Ala. Code Sec. 1-3-8(f)(1)');
check('it says why refusing was not available, so the choice is auditable',
  /discretionary/i.test(C.al.late_exposure.why_not_refused), true);
check('and it tells the caller what to actually do',
  /confirm that the court was in fact closed/i.test(C.al.late_exposure.caller_action), true);

// Pennsylvania: the ASSUMPTION species. Each arm below is a way the disclosure
// could decay into a label that no longer carries the uncomfortable half.
check("Pennsylvania's late_exposure names the rule the assumption turns on",
  /Pa\.R\.J\.A\. 107\(b\)/.test(C.pa.late_exposure.authority), true);
check('it quotes the words that DO NOT say the period rolls',
  /omitted from the computation/i.test(C.pa.late_exposure.summary), true);
check('it says out loud that this is an ASSUMPTION and not a citation',
  /STATED ASSUMPTION AND NOT A CITATION/.test(C.pa.late_exposure.why_not_refused), true);
check('it names the direction of the risk in the summary a caller actually reads',
  /LATER than the true deadline/.test(C.pa.summary), true);
check('and the action it asks for is a confirmation from counsel, not a workaround',
  /counsel/i.test(C.pa.late_exposure.caller_action), true);

// The two are NOT the same kind of problem and the table must keep saying so.
// Alabama's cannot be fixed by anybody; Pennsylvania's is settled by one
// sentence. A reader who conflated them would treat a resolvable question as
// permanent weather.
check("Alabama's is an unmodellable trigger, Pennsylvania's is an assumption",
  [/discretionary/i.test(C.al.late_exposure.why_not_refused),
   /assumption/i.test(C.pa.late_exposure.why_not_refused),
   /discretionary/i.test(C.pa.late_exposure.why_not_refused)],
  [true, true, false]);

// The whole point: a caller switching on direction must be able to find it.
check('every non-EARLY jurisdiction is one of the two declared LATE ones',
  Object.keys(C).filter(k => C[k].direction !== 'early').sort(), ['al', 'pa']);

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
  // Most states ship calendars in their own file; Pennsylvania's live inside
  // the seed. Fall back rather than special-case, so adding a state here does
  // not depend on remembering which layout it used.
  const calFile = path.join(SQL, 'sairnlaw_deadline_calendars_' + state + '.json');
  const cal = fs.existsSync(calFile)
    ? JSON.parse(fs.readFileSync(calFile, 'utf8'))
    : seed;
  if (!cal.holiday_calendars) throw new Error('no holiday_calendars for ' + state);
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
for (const [state, code] of [['utah', 'ut'], ['nevada', 'nv'], ['alabama', 'al'], ['pennsylvania', 'pa']]) {
  const r = computeFor(state, code);
  check(code + ': a real computation carries the coverage disclosure',
    [r.ok, !!r.coverage, r.coverage && r.coverage.direction],
    [true, true, C[code].direction]);
}
check('and the Alabama result carries the late_exposure block itself, not just the label',
  !!computeFor('alabama', 'al').coverage.late_exposure, true);
// The Pennsylvania one is the arm that matters most on this file: the whole
// reason the assumption was allowed to ship is that it rides on the result. If
// this stops being true the engine is silently asserting a rollover the rule
// text does not state.
check('a real Pennsylvania result carries the rollover assumption to the caller',
  [!!computeFor('pennsylvania', 'pa').coverage.late_exposure,
   /Pa\.R\.J\.A\. 107\(b\)/.test(computeFor('pennsylvania', 'pa').coverage.late_exposure.authority)],
  [true, true]);

console.log('\ndeadline-coverage-contract: ' + pass + ' passed, ' + fail + ' failed');
if (fail) process.exit(1);
