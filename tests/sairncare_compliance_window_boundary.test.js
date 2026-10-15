// tests/sairncare_compliance_window_boundary.test.js
// OWNER: cody
// written 2026-10-14, batch b14, item 4
// REQUIREMENT: a per-staff training verdict is anchored to that person's hire
//   anniversary, so the window boundary must roll ON the anniversary rather
//   than a day either side, must survive a 29 February hire in a year that has
//   no 29 February without publishing an impossible date, and must WITHHOLD a
//   shortfall verdict on the day the window opens -- meets null, not false --
//   because a surveyor reads window_from on a regulated finding and nobody may
//   be reported non-compliant on the morning their training year reset.
//
//   node tests/sairncare_compliance_window_boundary.test.js
//
// Exit: 0 every arm passed · 1 an arm FAILED · 3 COULD NOT RUN
//
// THE THREE ARMS N4 NAMED, AND TWO MORE THAT MEASURING FOUND.
//
// docs/2026-10-14-fourth-b18-tier-a-queue14-discharge.md N4 found three claims
// in api/_lib/compliance-rules.js that read as references to committed arms and
// were not:
//
//   * "Driven: hire 2024-11-03 ... evaluated 2026-11-02 -> compliant;
//     evaluated 2026-11-03 -> NON-COMPLIANT" -- no arm passes either date; the
//     sole anchor arm drives the mid-year case 2026-09-27.
//   * "an arm drives that", of the leap-day hire normalisation -- no arm
//     drives 02-29 at all.
//   * the day-zero behaviour (`window_days_elapsed`, `windowJustOpened`,
//     `dayZeroWithheld`, the `meets: null` withholding) -- asserted by nothing.
//
// Fourth's own verdict on that is the reason these are arms and not a scolding:
// "driven" in those comments most likely means driven BY HAND during
// development, which is a real activity. The defect is that a hand-drive
// leaves no artefact -- six weeks later the comment is the only evidence, and
// NOTHING FAILS WHEN THE BEHAVIOUR CHANGES. These arms are that artefact.
//
// ── WHY THIS LIVES IN tests/ AND NOT BESIDE THE MODULE ─────────────────────
// api/ is hank's this batch. api/_lib/compliance-rules-staff-join.test.js is
// where these would naturally sit and it is not cody's to edit, so the arms
// are written here against the module's PUBLIC exports. No api/ file is
// changed; two are read and one is required.
//
// ── TWO ARMS ARE RED ON PURPOSE AND BOTH ARE ROUTED TO hank ────────────────
// Both were found by MEASURING the behaviour this batch was sent to assert,
// which is the only reason they are here rather than in a follow-up:
//
//   X1. The hand-driven comment is now WRONG, not merely unproven. It says the
//       exact-anniversary evaluation is NON-COMPLIANT. Measured, it is
//       `meets: null` -- withheld, with a stated reason. The day-zero fix that
//       landed after 2026-09-29 superseded the sentence and nothing updated it.
//   X2. The withholding message tells the reader that
//       "hours_window_days_remaining says how much of it is left", and THE
//       FINDING DOES NOT CARRY THAT FIELD. `window_days_elapsed` and
//       `window_days_remaining` are computed (compliance-rules.js:658,663) and
//       live on the internal window object; the module's comment at :943 says
//       it hands "every consumer" both, and evaluateTraining's staff finding
//       exposes neither. A message citing a field that is not there is the
//       same shape as a citation to a file that does not exist.
//
// If arms X1 and X2 are the ONLY failures, this suite is in the state
// docs/known-red-suites.json records. Any other failure here is new.
//
// ── WHAT IS DELIBERATELY NOT ASSERTED ──────────────────────────────────────
// Not whether any requirement total is RIGHT -- that is the seeded rule's
// business and other arms cover the vocabulary. Not what day-zero policy
// SHOULD be: the module argues narrowness on purpose and picking a different
// point in the window would be a product decision. Not the hire-date regex's
// shape-only weakness (fourth's smaller finding), which is a different arm.

'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const MODULE_REL = 'api/_lib/compliance-rules.js';
const SEED_REL = 'sql/sairncare_compliance_seed.json';

let pass = 0;
const failed = [];

function ok(name, cond, detail) {
  if (cond) { console.log('  ok   ' + name); pass += 1; }
  else {
    console.log('  FAIL ' + name + (detail ? '\n         ' + String(detail).slice(0, 460) : ''));
    failed.push(name);
  }
}
function section(t) { console.log('\n' + t); }
function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + ' Nothing was verified.');
  process.exit(3);
}

// ── PRECONDITIONS. Each is a third state, never folded into a pass ─────────
let e, moduleSrc, rows;
try {
  e = require(path.join(ROOT, MODULE_REL));
} catch (err) {
  couldNotRun(MODULE_REL + ' would not load (' + err.message + ').');
}
try {
  moduleSrc = fs.readFileSync(path.join(ROOT, MODULE_REL), 'utf8').replace(/\r\n/g, '\n');
} catch (err) {
  couldNotRun(MODULE_REL + ' is not readable (' + err.message + ').');
}
try {
  const raw = JSON.parse(fs.readFileSync(path.join(ROOT, SEED_REL), 'utf8'));
  rows = Array.isArray(raw) ? raw : (raw.rows || raw.rules || []);
} catch (err) {
  couldNotRun(SEED_REL + ' is not readable or not JSON (' + err.message + ').');
}
for (const fn of ['evaluateTraining', 'normalizeRequirements', 'matchAudience']) {
  if (typeof e[fn] !== 'function') {
    couldNotRun(MODULE_REL + ' no longer exports ' + fn + '(), so these arms '
              + 'cannot drive it through its public surface.');
  }
}

// THE REAL SEED, not a fixture -- the convention
// api/_lib/compliance-rules-staff-join.test.js states and the reason it gives:
// a fixture written from the same reading as the code cannot contradict it.
const training = rows.filter((r) => r.requirement_type === 'training');
const WV = training.filter((r) => r.state === 'WV')[0];
if (!WV) {
  couldNotRun('no WV training rule in ' + SEED_REL + ', so the anchored window '
            + 'cannot be driven against a real rule.');
}

// `applies_to` is derived through the module's OWN matcher rather than typed,
// so a change to the audience vocabulary cannot leave these arms passing over
// a requirement set they assembled themselves.
function drive(rule, position, records, hire, onDate) {
  const norm = e.normalizeRequirements(rule);
  const applies = norm
    .filter((r) => e.matchAudience(r, { position: position }).applies === true)
    .map((r) => r.who);
  const out = e.evaluateTraining([rule], {
    state: rule.state, facility_class: rule.facility_class, on_date: onDate,
    staff: [{ staff_id: 'S', position: position, applies_to: applies,
              hire_date: hire, records: records }]
  });
  return (out.staff_findings || [])[0] || null;
}

const HIRE = '2024-11-03';
const LEAP_HIRE = '2024-02-29';
const EIGHT_BEFORE = [{ hours: 8, category: 'general', completed_on: '2026-10-15' }];

console.log('the compliance window boundary -- the three cases N4 said were '
          + 'driven by hand and by nothing else');

// THE LIVENESS CONTROL COMES FIRST. Every arm below reads a field off the
// finding, and `undefined === undefined` would satisfy several of them if the
// drive silently produced nothing.
section('0. the control that makes the rest readable');
{
  const f = drive(WV, 'caregiver', EIGHT_BEFORE, HIRE, '2026-11-02');
  ok('CONTROL: the drive produces a real per-staff finding with a computed '
     + 'requirement, so the arms below are reading values and not undefined',
     !!f && typeof f.required_annual_hours === 'number'
     && f.required_annual_hours > 0 && typeof f.hours_window_from === 'string',
     JSON.stringify(f).slice(0, 300));
}

// ── 1. THE EXACT ANNIVERSARY ───────────────────────────────────────────────
// mmdd = '-11-03'; on.slice(4) < mmdd is '-11-03' < '-11-03' -> false, so the
// year is NOT decremented and the anniversary is day zero of the NEW window,
// inclusive at the lower bound. Fourth verified that boundary by hand; this is
// the arm that keeps it verified.
section('1. the exact anniversary -- on_date = hire_date + 2 years');
{
  const before = drive(WV, 'caregiver', EIGHT_BEFORE, HIRE, '2026-11-02');
  ok('the DAY BEFORE the anniversary still sits in the OLD window, which opened '
     + 'on the previous anniversary -- window_from 2025-11-03',
     !!before && before.hours_window_from === '2025-11-03',
     JSON.stringify(before).slice(0, 300));
  ok('...and the eight hours completed 2026-10-15 fall inside it, so the '
     + 'verdict is a determinate PASS',
     !!before && before.meets === true && before.recorded_annual_hours === 8,
     JSON.stringify(before).slice(0, 300));

  const on = drive(WV, 'caregiver', EIGHT_BEFORE, HIRE, '2026-11-03');
  ok('ON the anniversary the window ROLLS rather than being decremented -- '
     + 'window_from is the evaluation date itself, 2026-11-03, which is the '
     + 'off-by-one this boundary could have had in either direction',
     !!on && on.hours_window_from === '2026-11-03',
     JSON.stringify(on).slice(0, 300));
  ok('...so the SAME eight hours now fall OUTSIDE the window and are not '
     + 'counted -- which is the fact that makes the day-zero rule below '
     + 'necessary rather than cosmetic',
     !!on && on.recorded_annual_hours === 0 && on.shortfall_hours > 0,
     JSON.stringify(on).slice(0, 300));
}

// ── 2. A 2024-02-29 HIRE EVALUATED IN A COMMON YEAR ───────────────────────
section('2. a leap-day hire, evaluated in a year that has no 29 February');
{
  const common = drive(WV, 'caregiver', [], LEAP_HIRE, '2026-03-15');
  ok('hired 2024-02-29 and evaluated 2026-03-15, the window opens 2026-02-28 -- '
     + 'the day-decrement normalisation, and NOT an invalid 2026-02-29',
     !!common && common.hours_window_from === '2026-02-28',
     JSON.stringify(common).slice(0, 300));

  // THE PAIRED POSITIVE. Without it, "it returns 02-28" is also satisfied by
  // code that normalises unconditionally -- which would be wrong in a leap
  // year and would move a real anniversary by a day.
  const leap = drive(WV, 'caregiver', [], LEAP_HIRE, '2028-03-15');
  ok('PAIRED POSITIVE: in a LEAP year the same hire keeps its real anniversary, '
     + 'window_from 2028-02-29 -- so the normalisation is conditional on the '
     + 'target year rather than applied to every 29 February hire',
     !!leap && leap.hours_window_from === '2028-02-29',
     JSON.stringify(leap).slice(0, 300));

  // ...and the other side of the same boundary: a date BEFORE the normalised
  // anniversary must still fall in the previous window.
  const justBefore = drive(WV, 'caregiver', [], LEAP_HIRE, '2026-02-27');
  ok('...and the day before the normalised anniversary is still the PREVIOUS '
     + 'window, 2025-02-28, so the decrement moved the boundary rather than '
     + 'erasing it',
     !!justBefore && justBefore.hours_window_from === '2025-02-28',
     JSON.stringify(justBefore).slice(0, 300));
}

// ── 3. THE DAY-ZERO SHORTFALL ─────────────────────────────────────────────
section('3. a day-zero shortfall is WITHHELD, and only the false half is');
{
  const withheld = drive(WV, 'caregiver', EIGHT_BEFORE, HIRE, '2026-11-03');
  ok('a shortfall on the day the window opens yields meets === null, NOT false '
     + '-- strictly null, because `!meets` would read false and null alike and '
     + 'that collapse is the bug being refused',
     !!withheld && withheld.meets === null,
     'meets=' + JSON.stringify(withheld && withheld.meets)
     + ' shortfall=' + JSON.stringify(withheld && withheld.shortfall_hours));
  ok('...and it SAYS WHY, naming the window opening today, so a null verdict is '
     + 'readable rather than an absence',
     !!withheld && /window opened today/i.test(withheld.meets_unknown_reason || ''),
     (withheld || {}).meets_unknown_reason);
  ok('...and the shortfall is still REPORTED alongside the withheld verdict, '
     + 'so withholding the judgement is not hiding the number',
     !!withheld && withheld.shortfall_hours > 0
     && withheld.required_annual_hours > 0,
     JSON.stringify(withheld).slice(0, 300));

  // THE PAIRED POSITIVE, and the module states this one itself: "MEETING THE
  // REQUIREMENT ON DAY ZERO IS STILL true ... Only the FALSE half is
  // withheld." Without this arm, "day zero is unknowable" would satisfy
  // everything above.
  const met = drive(WV, 'caregiver',
    [{ hours: 2, category: 'general', completed_on: '2026-11-03' }],
    HIRE, '2026-11-03');
  ok('PAIRED POSITIVE: somebody who front-loads the hours ON day zero is '
     + 'determinately COMPLIANT -- true, not null. Only the FALSE half is '
     + 'withheld, which is the module\'s own claim',
     !!met && met.meets === true && met.shortfall_hours === 0,
     JSON.stringify(met).slice(0, 300));
}

// ── X. THE TWO FOUND BY MEASURING. BOTH RED, BOTH ROUTED TO hank ──────────
section('X. found by measuring the three above -- RED ON PURPOSE, routed to hank');
{
  // X1. The comment claims a verdict the code no longer produces.
  const flat = moduleSrc.split('\n')
    .map((l) => l.replace(/^\s*\/\/ ?/, ''))
    .join(' ')
    .replace(/\s+/g, ' ');
  const CLAIM = 'evaluated 2026-11-03 -> NON-COMPLIANT';
  const measured = drive(WV, 'caregiver', EIGHT_BEFORE, HIRE, '2026-11-03');
  ok('X1 (RED UNTIL hank CORRECTS THE COMMENT): no comment in ' + MODULE_REL
     + ' claims the exact-anniversary evaluation is NON-COMPLIANT, because '
     + 'measured it is meets === ' + JSON.stringify(measured && measured.meets),
     flat.indexOf(CLAIM) === -1,
     'the comment still says ' + JSON.stringify(CLAIM) + ' while the module '
     + 'returns meets=' + JSON.stringify(measured && measured.meets)
     + '. The day-zero withholding landed AFTER that sentence was hand-driven '
     + 'on 2026-09-29 and superseded it. The sentence is no longer merely '
     + 'unproven -- it is wrong, and it is the kind of claim a reader checks '
     + 'least because it names its own evidence. Fix: say the anniversary '
     + 'verdict is WITHHELD (meets: null), or delete the date.');

  // X2. The withholding message cites a field the finding does not carry.
  const CITED = 'hours_window_days_remaining';
  const reason = (measured || {}).meets_unknown_reason || '';
  ok('CONTROL: the withholding message really does cite ' + CITED + ', so X2 '
     + 'below is about a missing FIELD and not about a message that changed',
     reason.indexOf(CITED) !== -1, reason);
  ok('X2 (RED UNTIL hank EXPOSES THE FIELD): the finding carries the field its '
     + 'own withholding message tells the reader to consult',
     !!measured && Object.prototype.hasOwnProperty.call(measured, CITED),
     'the message says "' + CITED + ' says how much of it is left" and the '
     + 'finding has no such key. Present keys: '
     + Object.keys(measured || {}).join(',')
     + '. window_days_elapsed and window_days_remaining ARE computed '
     + '(compliance-rules.js:658,663) and stay on the internal window object, '
     + 'while the comment at :943 says the module hands "every consumer" both. '
     + 'Fix: surface them on the staff finding as hours_window_days_elapsed / '
     + 'hours_window_days_remaining, or stop citing a field that is not there.');
}

console.log('\n' + pass + ' passed, ' + failed.length + ' failed');
if (failed.length) {
  console.log(failed.length + ' ARM(S) FAILED:');
  failed.forEach((f) => console.log('  - ' + f));
  console.log('\nX1 and X2 are EXPECTED RED and are routed to hank (api/ is '
            + 'hank\'s). If they are the only failures, this suite is in the '
            + 'state docs/known-red-suites.json records.');
  process.exit(1);
}
process.exit(0);
