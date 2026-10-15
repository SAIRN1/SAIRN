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
//   X2. The withholding message names a field the finding does not carry.
//       `window_days_elapsed` and `window_days_remaining` are computed and stay
//       on the INTERNAL window object, while a comment in the same module says
//       it hands "every consumer" both -- and evaluateTraining's staff finding
//       exposes neither. A message naming a field that is not there is the same
//       shape as a citation to a file that does not exist.
//
// ── BOTH ARMS WERE REWRITTEN 2026-10-15 (b15 item 4) TO DERIVE, NOT TRUST ──
// The b14 spelling typed its evidence: the claim sentence, the field name, and
// prose citing `:658,663` and `:943`. THOSE LINE NUMBERS WERE ALREADY WRONG
// WITHIN A DAY -- re-measured, the assignments are at :736 and :741 and the
// "every consumer" comment is at :1021, because hank landed work in the same
// file. Deliberately NOT re-typed here: X2 prints the assignment lines it
// finds, every run, so the citation cannot rot again. X1 parses the comment for
// its own scenario and its own expected verdicts and compares them to what the
// module returns, so a reviewer confirms both arms without trusting any number
// written by me.
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
// ONE INJECTION POINT, never set on an ordinary run. The b15 counterfactual
// points this at a MUTATED COPY of the module to drive each arm's failure
// path -- the comment corrected, the behaviour changed to match the comment,
// the fields surfaced, the message stripped. An env var rather than an edit,
// because api/ is hank's and this batch touches none of it.
const MODULE_ABS = process.env.SAIRN_B15_COMPLIANCE_RULES
  || path.join(ROOT, MODULE_REL);
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
// A THIRD STATE, so a derivation that finds nothing is never a pass. X1 reads
// its own scenario out of a comment; if that comment is reworded past
// recognition the arm has nothing to compare, and "nothing to compare" must
// not look like "they agree".
const unproven = [];
function cannot(name, why) {
  unproven.push(name);
  console.log('  UNPROVEN ' + name
            + (why ? '\n         ' + String(why).slice(0, 400) : ''));
}
function couldNotRun(why) {
  console.log('COULD NOT RUN: ' + why + ' Nothing was verified.');
  process.exit(3);
}

// ── PRECONDITIONS. Each is a third state, never folded into a pass ─────────
let e, moduleSrc, rows;
try {
  e = require(MODULE_ABS);
} catch (err) {
  couldNotRun(MODULE_REL + ' would not load (' + err.message + ').');
}
try {
  moduleSrc = fs.readFileSync(MODULE_ABS, 'utf8').replace(/\r\n/g, '\n');
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
// ── REWRITTEN 2026-10-15 (cody b15 item 4): BOTH ARMS DERIVE THEIR OWN
//    SUBJECT FROM SOURCE, so a reviewer confirms them without trusting me ───
// The b14 spelling typed its evidence in: `CLAIM = 'evaluated 2026-11-03 ->
// NON-COMPLIANT'`, `CITED = 'hours_window_days_remaining'`, and prose citing
// `:658,663` and `:943`. Three problems, and the third one bit within a day:
//   1. A typed claim means the arm hunts a STRING. It would pass the moment
//      somebody reworded the comment without fixing it, and fail if they fixed
//      the behaviour instead of the comment -- neither is the property.
//   2. A typed field name means the arm asserts MY reading of the message
//      rather than the message.
//   3. THE LINE NUMBERS HAD ALREADY ROTTED. Re-measured here: the two
//      assignments are at :736 and :741, not :658 and :663, and the "every
//      consumer" comment is at :1021, not :943 -- they moved when hank landed
//      work the same day b14 wrote them down. A citation is not evidence.
// So: X1 PARSES the comment for every `evaluated <date> -> <verdict>` claim it
// makes, DRIVES the module on that date with the hire and hours THE COMMENT
// ITSELF states, and compares. X2 reads the identifiers out of the withholding
// MESSAGE at runtime and asserts the finding carries each one. Nothing about
// either arm's subject is typed here.
{
  const commentLines = moduleSrc.split('\n')
    .map((l, i) => [i + 1, l])
    .filter((p) => /^\s*\/\//.test(p[1]));
  const flat = commentLines
    .map((p) => p[1].replace(/^\s*\/\/ ?/, ''))
    .join(' ')
    .replace(/\s+/g, ' ');

  // THE SCENARIO IS READ OUT OF THE COMMENT, not supplied by me: the hire
  // date, the hours, and the date those hours were completed.
  const scen = flat.match(/hire (\d{4}-\d{2}-\d{2}), ([a-z]+) hours completed (\d{4}-\d{2}-\d{2})/);
  const WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7,
                  eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12 };
  // EVERY date-bound verdict claim the comment makes, not just the one I
  // noticed. The 2026-11-02 half is checked by the same arm.
  const claims = [];
  const rx = /evaluated (\d{4}-\d{2}-\d{2}) -> ([A-Za-z-]+)/g;
  let m;
  while ((m = rx.exec(flat)) !== null) claims.push({ on: m[1], says: m[2] });

  if (!scen || !claims.length) {
    // NOT a pass. If the comment no longer states a drivable scenario, this arm
    // cannot compare anything and says so -- the same third state the module
    // itself uses. A reworded comment must not silently satisfy X1.
    cannot('X1. the hand-driven comment in ' + MODULE_REL + ' no longer states '
         + 'a drivable scenario (hire/hours/date) or makes no `evaluated <date> '
         + '-> <verdict>` claim, so there is nothing to compare',
           'scenario=' + JSON.stringify(scen && scen.slice(1))
           + ' claims=' + JSON.stringify(claims));
  } else {
    const hire = scen[1];
    const hours = WORDS[scen[2].toLowerCase()] || Number(scen[2]);
    const completed = scen[3];
    const recs = [{ hours: hours, category: 'general', completed_on: completed }];
    console.log('  ..   DERIVED FROM THE COMMENT (lines '
              + commentLines.filter((p) => /evaluated \d{4}/.test(p[1]))
                  .map((p) => p[0]).join(', ')
              + '): hire ' + hire + ', ' + hours + 'h completed ' + completed
              + ', claims ' + JSON.stringify(claims));

    // WHAT THE COMMENT'S WORDS MEAN AS A VERDICT, stated once and narrowly.
    // `null` is deliberately NOT mapped from any word: the point of X1 is that
    // no word in that comment describes withholding.
    function verdictOf(word) {
      const w = String(word).toLowerCase();
      if (w === 'compliant') return true;
      if (w === 'non-compliant' || w === 'noncompliant') return false;
      return undefined;
    }

    const wrong = [];
    for (const c of claims) {
      const got = drive(WV, 'caregiver', recs, hire, c.on);
      const said = verdictOf(c.says);
      const actual = got && got.meets;
      if (said === undefined) continue;        // a word this arm cannot read
      if (said !== actual) {
        wrong.push(c.on + ': the comment says ' + c.says + ' (meets '
                   + JSON.stringify(said) + ') and the module returns meets '
                   + JSON.stringify(actual));
      }
    }
    ok('X1 (RED UNTIL hank CORRECTS THE COMMENT): every `evaluated <date> -> '
       + '<verdict>` claim the comment makes agrees with what the module '
       + 'returns on that date, driven with the hire and hours the comment '
       + 'itself states (' + claims.length + ' claim(s) checked)',
       wrong.length === 0,
       wrong.join('; ')
       + '. THE COMPARISON IS BETWEEN TWO THINGS READ AT RUNTIME -- the '
       + 'comment supplies the scenario AND the expected verdict, the module '
       + 'supplies the answer -- so this arm goes green if the comment is '
       + 'corrected OR if the behaviour changes to match it, and neither can '
       + 'be faked by rewording. The day-zero withholding landed AFTER that '
       + 'sentence was hand-driven on 2026-09-29 and superseded it. Fix: say '
       + 'the anniversary verdict is WITHHELD (meets: null), or delete the '
       + 'date.');

    // THE PAIRED CONTROL. Without it, "the comment makes no readable claim"
    // and "every claim agrees" are the same green.
    ok('CONTROL: at least one claim in that comment was actually READ and '
       + 'DRIVEN, so X1 is not passing over a comment it could not parse',
       claims.filter((c) => verdictOf(c.says) !== undefined).length > 0,
       JSON.stringify(claims));
  }

  // ── X2: the identifiers are read out of the MESSAGE, not typed ──────────
  const measured = drive(WV, 'caregiver', EIGHT_BEFORE, HIRE, '2026-11-03');
  const reason = (measured || {}).meets_unknown_reason || '';
  // Any snake_case identifier the message names and then describes -- the
  // shape "<name> says/shows/reports ...". Derived so a message that starts
  // citing a different field is checked against THAT field instead.
  const cited = [];
  const crx = /\b([a-z][a-z0-9]*(?:_[a-z0-9]+){2,})\b/g;
  let c2;
  while ((c2 = crx.exec(reason)) !== null) {
    if (cited.indexOf(c2[1]) === -1) cited.push(c2[1]);
  }
  ok('CONTROL: the withholding message names at least one field identifier, so '
     + 'X2 below is about a missing FIELD and not about a message that stopped '
     + 'citing anything. named: ' + JSON.stringify(cited),
     cited.length > 0, reason);
  if (cited.length) {
    const absent = cited.filter(
      (k) => !(measured && Object.prototype.hasOwnProperty.call(measured, k)));
    // WHERE THE FIELDS REALLY ARE, re-derived every run instead of cited.
    const where = {};
    for (const k of ['window_days_elapsed', 'window_days_remaining']) {
      where[k] = moduleSrc.split('\n')
        .map((l, i) => [i + 1, l])
        .filter((p) => new RegExp('out\\.' + k + '\\s*=').test(p[1]))
        .map((p) => p[0]);
    }
    ok('X2 (RED UNTIL hank EXPOSES THE FIELD): the finding carries every field '
       + 'its own withholding message tells the reader to consult',
       absent.length === 0,
       'the message names ' + JSON.stringify(cited) + ' and the finding is '
       + 'missing ' + JSON.stringify(absent) + '. Present keys: '
       + Object.keys(measured || {}).join(',')
       + '. RE-DERIVED, NOT CITED: the assignments are at '
       + JSON.stringify(where) + ' and they land on the INTERNAL window object, '
       + 'not on the staff finding. Fix: surface them on the finding under the '
       + 'names the message uses, or stop naming a field that is not there.');
  }
}

console.log('\n' + pass + ' passed, ' + failed.length + ' failed, '
          + unproven.length + ' unproven');
if (unproven.length) {
  console.log(unproven.length + ' ARM(S) UNPROVEN: ' + unproven.join('; '));
}
if (failed.length) {
  console.log(failed.length + ' ARM(S) FAILED:');
  failed.forEach((f) => console.log('  - ' + f));
  console.log('\nX1 and X2 are EXPECTED RED and are routed to hank (api/ is '
            + 'hank\'s). If they are the only failures, this suite is in the '
            + 'state docs/known-red-suites.json records.');
  process.exit(1);
}
// UNPROVEN OUTRANKS A CLEAN EXIT. An arm that could not compare its subject is
// not a pass, and exit 0 here would report one.
process.exit(unproven.length ? 3 : 0);
