// api/b17-tier-a-count-agreement.test.js
//
// Run:  node api/b17-tier-a-count-agreement.test.js
//
// ── THE METHODOLOGY ITEM FOR b17, AND THE DEFECT CLASS IT CLOSES ─────────
// A HAND-TYPED COUNT BESIDE A DERIVED LIST. In docs/tier-a-reviews.json every
// record carries a `resources` array that the push gate produces from the
// commit's file set, and a `what` written by hand. Two of hank's own records
// open by stating a count that disagrees with their own array:
//
//     opened 2026-10-15T01:21:13Z   "b13: THREE Tier A resources changed"
//                                   resources: 4   (leg_cases uncounted)
//     opened 2026-10-15T15:04:38Z   "b16: SIX Tier A resources, three ..."
//                                   resources: 7   (sen_settings uncounted)
//
// NEITHER WAS A HARMLESS TYPO, AND THE SECOND PROVES IT. The resource the b16
// record failed to count was `sen_settings` -- which is exactly where fourth's
// b26 FINDING H3 turned out to live: the generic settings write path could
// REPLACE the closed-period key and silently unfreeze every paid wage. A
// reviewer reading "SIX" and a list of six named changes has been told, in the
// document whose entire job is to say what needs reviewing, that there are six
// things to attack.
//
// Both records now carry a `count_correction` field stating the discrepancy.
// THAT IS NOT THE FIX. A correction nobody re-measures is a sentence; this
// file is the fix, because it fails the next time the shape appears.
//
// ── THE CRITERIA ARE NARROW ON PURPOSE, AND WERE LOCKED FIRST ───────────
// Cross-domain convention 1: lock a check's criteria against SYNTHETIC
// FIXTURES before running it on real data. Arms C1 and C2 are that lock, in
// both directions, and they run BEFORE the real-data arm.
//
// The loose version of this check -- any "<N> Tier A resource(s)" anywhere in
// the text -- was measured against the real file first and produced FIVE FALSE
// POSITIVES, every one of them a count that legitimately describes a SUBSET
// and names it:
//
//     "FOUR Tier A resources gain a server-stamped acting employee ...
//      -- alf_signals, rf_locations, sen_caregivers, sen_claims"      (8 in the array)
//     "twenty-two Tier A resources THAT HAD NO cross-tenant arm"      (30)
//     "a SAIRNgrounds unit (6 Tier A resources, absent dispatcher)"   (11)
//     "SAIRNdesign session gate armed on the five Tier A resources"   (7)
//     "SAIRNscape's two Tier A resources (invoices, scp_quotes)"      (7)
//
// So the criteria match ONE anchored shape: the count as the record's OPENING
// SELF-SUMMARY -- a short batch label, a colon, the number, "Tier A
// resources", then a comma or the word "changed". That is the shape both real
// defects have and none of the five false positives does. It is deliberately
// unable to catch a count buried mid-paragraph; a check that over-reports is
// a check somebody switches off.
//
// ── AND C5 IS THE ARM THAT KEEPS IT HONEST OVER TIME ────────────────────
// Cross-domain convention 8: nothing announces the day a check stops testing
// anything. A narrow anchored pattern is exactly the kind that silently stops
// matching when the house style for `what` changes. C5 requires the pattern to
// match AT LEAST TWO records, and names them -- so the day the shape changes,
// this file goes red asking to be re-aimed rather than printing a clean pass
// over a file it can no longer read.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');

const REGISTER = path.join(__dirname, '..', 'docs', 'tier-a-reviews.json');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 900));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// ── THE WORD LIST REACHED TWELVE AND THE REGISTER REACHES TWENTY ────────
// EXTENDED 2026-10-16, on this check's FIRST real run -- which caught my own
// b17 obligation claiming SEVEN against an array of twenty, and then could not
// read the CORRECTION, because `twenty` was not in this map. A count the check
// cannot parse is a record the check SILENTLY DOES NOT EXAMINE, which is the
// same failure as a pattern that stops matching rather than a lesser one: C5
// counts matches for exactly that reason, and it is what showed the gap.
//
// WHY TWENTY AND NOT HIGHER: this is a word-form list and any ceiling on it is
// arbitrary -- obligations in this register run to hundreds of resources. What
// makes twenty enough is that a record naming more than twenty writes DIGITS,
// which the `\\d{1,3}` branch already handles. If a word above twenty ever
// appears, C5 drops by one and names the record rather than going quiet.
const WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7,
                eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12,
                thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
                seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20 };

// THE CRITERIA. Versioned, because a change to them changes what every
// recorded result means -- cross-domain convention 8's stamping rule. Bumped
// to .2 when the word list was extended: the .1 results were taken with a map
// that could not read `twenty`, and quoting them as comparable would be wrong.
const CRITERIA_VERSION = '2026-10-16.2';

// `<label>: <N> Tier A resources` followed by a comma or "changed", where the
// label is short and contains no sentence end. The label bound is what stops
// this matching a count that appears after a clause of its own.
//
// THE NUMBER ALTERNATION IS DERIVED FROM `WORDS` AND NOT RETYPED. It was a
// hand-written list of the same twelve names, which is a second copy of the
// thing above it -- in a file whose whole subject is a hand-typed figure
// disagreeing with a derived one.
const SELF_SUMMARY = new RegExp(
  '^[^.:]{0,40}:\\s*(' + Object.keys(WORDS).join('|') + '|\\d{1,3})'
  + '\\s+Tier A resources?\\s*(?:,|changed\\b)', 'i');

function claimedCount(what) {
  const m = SELF_SUMMARY.exec(String(what || ''));
  if (!m) return null;
  const w = m[1].toLowerCase();
  const v = Object.prototype.hasOwnProperty.call(WORDS, w) ? WORDS[w] : Number(w);
  return Number.isFinite(v) ? v : null;
}

// The whole check over a record list. Returns matched + disagreeing, so an arm
// can assert the pattern MATCHED something as well as what it found.
function audit(records) {
  const matched = [], bad_ = [];
  (records || []).forEach((r, i) => {
    const claim = claimedCount(r && r.what);
    if (claim === null) return;
    const n = (r && Array.isArray(r.resources)) ? r.resources.length : 0;
    const id = (r && r.author_session) + '@' + (r && r.opened_at);
    matched.push({ index: i, id: id, claim: claim, actual: n });
    if (claim !== n) {
      // A RECORDED DISCREPANCY IS NOT A PASS AND IS NOT A FAILURE EITHER. It
      // is the third state: somebody has looked at it and written down which
      // number is right. Without this, correcting a record would be the only
      // way to make the check green and the correction would have to rewrite
      // `what` -- which is the text a reviewer actually read, in a ledger that
      // is append-only across four clones.
      if (r && typeof r.count_correction === 'string' && r.count_correction.trim()) {
        matched[matched.length - 1].corrected = true;
        return;
      }
      bad_.push({ index: i, id: id, claim: claim, actual: n,
                  opening: String(r.what || '').slice(0, 110) });
    }
  });
  return { matched: matched, disagreeing: bad_ };
}

// ── THE SYNTHETIC FIXTURES. Written out in full rather than generated, so
//    the text being matched is visible next to the verdict it should produce.
const FIX_SHOULD_FLAG = [
  { author_session: 'fx', opened_at: 'A1', resources: ['a', 'b', 'c', 'd'],
    what: 'b13: THREE Tier A resources changed and each needs a question.' },
  { author_session: 'fx', opened_at: 'A2', resources: ['a', 'b', 'c', 'd', 'e', 'f', 'g'],
    what: 'b16: SIX Tier A resources, three distinct changes, all money.' },
  { author_session: 'fx', opened_at: 'A3', resources: ['a', 'b'],
    what: 'b99: 5 Tier A resources, digits rather than a word.' },
  // THE EXTENDED WORD RANGE, in the flagging direction. Before 2026-10-16
  // `twenty` was unparseable and this record would have been SKIPPED -- not
  // passed, not failed, simply not examined.
  { author_session: 'fx', opened_at: 'A4', resources: new Array(7).fill('x'),
    what: 'b17: TWENTY Tier A resources, and the array holds seven.' }
];
const FIX_SHOULD_NOT_FLAG = [
  // AGREES -- the ordinary case, and the one that must stay quiet.
  { author_session: 'fx', opened_at: 'B1', resources: ['a', 'b', 'c'],
    what: 'b20: THREE Tier A resources, and they agree.' },
  // AND THE EXTENDED RANGE AGREEING, so the extension is locked in BOTH
  // directions rather than only where it flags.
  { author_session: 'fx', opened_at: 'B1b', resources: new Array(20).fill('x'),
    what: 'b17: TWENTY Tier A resources, and they agree.' },
  // THE FIVE REAL FALSE-POSITIVE SHAPES, copied from the live file.
  { author_session: 'fx', opened_at: 'B2', resources: new Array(8).fill('x'),
    what: 'batch12 (hank): FOUR Tier A resources gain a server-stamped acting '
        + 'employee in api/sd-data.js -- alf_signals, rf_locations, sen_caregivers, '
        + 'sen_claims. The other four things in this batch are not that.' },
  { author_session: 'fx', opened_at: 'B3', resources: new Array(30).fill('x'),
    what: 'cross-tenant isolation coverage: twenty-two Tier A resources that had '
        + 'NO cross-tenant arm anywhere, plus a whole dispatcher.' },
  { author_session: 'fx', opened_at: 'B4', resources: new Array(11).fill('x'),
    what: 'isolation coverage third batch: a SAIRNgrounds unit (6 Tier A resources, '
        + 'absent dispatcher) plus rf_entities.' },
  { author_session: 'fx', opened_at: 'B5', resources: new Array(7).fill('x'),
    what: 'SAIRNdesign session gate armed on the five Tier A resources, 2026-09-23.' },
  { author_session: 'fx', opened_at: 'B6', resources: new Array(7).fill('x'),
    what: 'SAIRNscape\'s two Tier A resources (invoices, scp_quotes) gated on a '
        + 'verified sairnscape session.' },
  // A COUNT THAT ATTACHES TO SOMETHING ELSE. "three CHANGES touching Tier A
  // resources" is not a claim about how many resources there are.
  { author_session: 'fx', opened_at: 'B7', resources: new Array(10).fill('x'),
    what: 'hank b9: THREE changes touching Tier A resources. (1) ai-safeguards ...' },
  // A DISAGREEMENT THAT IS RECORDED. The third state.
  { author_session: 'fx', opened_at: 'B8', resources: ['a', 'b', 'c', 'd'],
    what: 'b13: THREE Tier A resources changed.',
    count_correction: 'The array is right and the count is wrong; leg_cases.' }
];

function main() {
  console.log('api/b17-tier-a-count-agreement.test.js');
  console.log('  a hand-typed count beside a derived list -- criteria '
    + CRITERIA_VERSION);

  // ── C1: THE CRITERIA FLAG WHAT THEY MUST ──────────────────────────────
  try {
    const r = audit(FIX_SHOULD_FLAG);
    is(r.disagreeing.length === 4
       && r.disagreeing.map((x) => x.id).join(',') === 'fx@A1,fx@A2,fx@A3,fx@A4',
       'C1. FIXTURE LOCK -- all four planted disagreements are flagged, '
     + 'including the digit form and the word form above twelve',
       JSON.stringify(r.disagreeing.map((x) => x.id + ' ' + x.claim + '/' + x.actual)));
  } catch (e) { bad('C1. FIXTURE LOCK -- planted disagreements are flagged', e && e.stack); }

  // ── C2: AND THEY ARE SILENT ON WHAT THEY MUST NOT ─────────────────────
  // The direction that matters more. A check that over-reports on five real
  // shapes gets switched off, and then it tests nothing at all.
  try {
    const r = audit(FIX_SHOULD_NOT_FLAG);
    is(r.disagreeing.length === 0,
       'C2. FIXTURE LOCK -- the nine shapes that must NOT flag are silent: TWO '
     + 'agreeing counts (one of them in the extended word range), the five '
     + 'real subset shapes, a count attached to "changes" rather than '
     + 'resources, and a RECORDED disagreement',
       JSON.stringify(r.disagreeing));
  } catch (e) { bad('C2. FIXTURE LOCK -- the must-not-flag shapes are silent', e && e.stack); }

  // ── C3: AND THE THIRD STATE IS DISTINGUISHABLE FROM A PASS ────────────
  // B8 disagrees AND is corrected. It must be matched-and-corrected, not
  // simply absent -- otherwise "nobody has looked at it" and "somebody has
  // written down which number is right" are the same answer.
  try {
    const r = audit(FIX_SHOULD_NOT_FLAG);
    const b8 = r.matched.filter((m) => m.id === 'fx@B8')[0];
    is(!!b8 && b8.corrected === true && b8.claim === 3 && b8.actual === 4,
       'C3. a RECORDED disagreement is reported as matched-and-corrected rather '
     + 'than folded into the clean set -- three states, not two',
       JSON.stringify(b8 || null));
  } catch (e) { bad('C3. the third state is distinguishable', e && e.stack); }

  // ── C4: THE REAL FILE ─────────────────────────────────────────────────
  let real = null;
  try {
    const raw = fs.readFileSync(REGISTER, 'utf8');
    const d = JSON.parse(raw);
    real = audit(d.records);
    is(real.disagreeing.length === 0,
       'C4. docs/tier-a-reviews.json: every self-summary count agrees with its '
     + 'own resources array, or carries a count_correction saying which number '
     + 'is right',
       real.disagreeing.map((x) => x.id + ' claims ' + x.claim + ' / array '
         + x.actual + ' :: ' + x.opening).join('\n           '));
  } catch (e) {
    cannot('C4. the real register parses and agrees', e && e.message);
  }

  // ── C5: THE PATTERN STILL MATCHES SOMETHING ───────────────────────────
  // CONVENTION 8. This is the arm that stops C4 from being a clean pass over
  // a file it can no longer read. Two is the floor rather than one, because
  // the two known records are the two it was written against -- if only one
  // matches, the house style has already moved under it.
  if (real) {
    try {
      const m = real.matched;
      const corrected = m.filter((x) => x.corrected);
      is(m.length >= 2,
         'C5. the self-summary pattern MATCHED ' + m.length + ' record(s) '
       + '(' + corrected.length + ' carrying a recorded correction). A narrow '
       + 'anchored pattern that matched nothing would print C4 green over a '
       + 'file it cannot read, which is the silent-rot shape this arm exists '
       + 'for -- re-aim the pattern if this goes red',
         'matched=' + JSON.stringify(m.map((x) => x.id + ' ' + x.claim + '/'
           + x.actual + (x.corrected ? ' CORRECTED' : ''))));
    } catch (e) { bad('C5. the pattern still matches something', e && e.stack); }
  } else {
    cannot('C5. the pattern still matches something', 'C4 could not run');
  }

  // ── C6: ABLATION -- REMOVE A CORRECTION AND C4 MUST GO RED ───────────
  // CONVENTION 12: remove ONE named layer on already-clean data and measure
  // what it alone catches. Without this, C4 passing proves only that the file
  // is currently clean -- it would pass identically if the criteria matched
  // nothing at all, which is what C5 guards, and identically if the
  // correction field were being ignored, which is what this guards.
  //
  // IT MUTATES AN IN-MEMORY COPY AND NEVER THE FILE. The register is an
  // append-only ledger shared across four clones; writing a mutant to it,
  // even restored in a finally, is a risk with no upside here.
  if (real) {
    try {
      const d = JSON.parse(fs.readFileSync(REGISTER, 'utf8'));
      const victims = d.records.filter((r) => typeof r.count_correction === 'string');
      if (!victims.length) {
        cannot('C6. ABLATION -- dropping a count_correction turns C4 red',
          'no record carries a count_correction, so there is nothing to ablate');
      } else {
        delete victims[0].count_correction;
        const after = audit(d.records);
        is(after.disagreeing.length === 1,
           'C6. ABLATION -- dropping ONE count_correction turns the real-data arm '
         + 'red with exactly that record named, so C4 is reading the correction '
         + 'field and the discrepancy is really there',
           JSON.stringify(after.disagreeing.map((x) => x.id + ' ' + x.claim + '/' + x.actual)));
      }
    } catch (e) { bad('C6. ABLATION on the correction field', e && e.stack); }
  } else {
    cannot('C6. ABLATION on the correction field', 'C4 could not run');
  }

  // ── C7: THE CORRECTIONS SAY WHICH NUMBER IS RIGHT, not just "noted" ──
  // A correction field that could hold "TODO" would make C4 green for free.
  // It has to name the array as the authority and name the uncounted resource.
  if (real) {
    try {
      const d = JSON.parse(fs.readFileSync(REGISTER, 'utf8'));
      const corr = d.records.filter((r) => typeof r.count_correction === 'string');
      const weak = corr.filter((r) => {
        const t = r.count_correction;
        return !(t.length > 200
                 && /array/i.test(t)
                 && /resources/i.test(t));
      });
      is(corr.length >= 2 && weak.length === 0,
         'C7. every count_correction is substantive -- over 200 chars, naming '
       + 'the `resources` array as the authority. A field that accepted "noted" '
       + 'would make C4 green for free',
         'corrections=' + corr.length + ' weak=' + JSON.stringify(
           weak.map((r) => r.author_session + '@' + r.opened_at)));
    } catch (e) { bad('C7. the corrections are substantive', e && e.stack); }
  } else {
    cannot('C7. the corrections are substantive', 'C4 could not run');
  }

  console.log('');
  console.log('  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
