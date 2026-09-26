// tests/sairnvet_formulary_source_honesty.js
//
// REQUIREMENT: sairnvet.html must not tell a clinician that a dose is VERIFIED
//   unless the row it came from cites a source.
//
// Run:  node tests/sairnvet_formulary_source_honesty.js
//
// ── WHAT THIS IS ABOUT ──────────────────────────────────────────────────────
// The Drug Database screen rendered a green `✓ Verified` badge for every row
// whose `needsReview` was false -- 284 of the 485 rows in VET_DRUGS. There was
// no `reference` field on any row, no source recorded anywhere in the file, and
// nothing that could have been checked. `needsReview:false` is the ABSENCE OF A
// FLAG; the screen was reading it as the PRESENCE OF A VERIFICATION.
//
// The same word was in nine other places, including the system prompt of the AI
// Dosing Calculator -- "you may ONLY use the verified database record" -- which
// put the claim in the model's mouth and therefore in front of the vet.
//
// ── WHY THIS FILE IS A TEST AND NOT A NOTE ─────────────────────────────────
// The wording is the only thing holding the honesty, and wording regrows. A
// future edit restoring `✓ Verified` on an unsourced row is a one-character
// change to a ternary, would look like a UI tidy-up in review, and nothing else
// in this repo would notice. These arms are what notice.
//
// ── WHAT IS DELIBERATELY NOT ASSERTED ──────────────────────────────────────
// Nothing here says a dose is CORRECT. A citation is evidence that somebody
// looked something up, not that the figure is right for the patient in front of
// you -- and three rows carrying a reference out of 485 is a disclosure, not a
// coverage claim. The arms check the app's HONESTY ABOUT ITS OWN SOURCING,
// which is the only thing a static test can check.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const FILE = path.resolve(__dirname, '..', 'sairnvet.html');
const src = fs.readFileSync(FILE, 'utf8');

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

// The table, parsed rather than regex-sniffed -- an arm that reads the wrong
// thing is worse than no arm.
const m = /var VET_DRUGS = (\[[\s\S]*?\]);/.exec(src);
const DRUGS = m ? JSON.parse(m[1]) : null;

(function () {
  console.log('SAIRNVET FORMULARY -- the app must not claim a verification it did not do');

  section('THE TABLE ITSELF');
  test('VET_DRUGS parses and is non-trivial', function () {
    assert.ok(Array.isArray(DRUGS) && DRUGS.length > 100,
      'VET_DRUGS did not parse, or is too small to be the real table: '
      + (DRUGS ? DRUGS.length : 'null') + '. Every arm below reads it, so a '
      + 'parse failure must fail LOUDLY rather than skip.');
  });
  if (!DRUGS) { console.log('\n' + pass + ' passed, ' + (fail + 1) + ' failed'); process.exit(1); }

  const sourced = DRUGS.filter(function (d) { return d.reference; });
  const unsourced = DRUGS.filter(function (d) { return !d.reference; });
  console.log('  rows: ' + DRUGS.length + '   citing a source: ' + sourced.length
    + '   no source recorded: ' + unsourced.length);

  section('THE BADGE');
  // The rendering lives in searchDrugs(). Read the region rather than the whole
  // file: `✓ Verified` may legitimately appear elsewhere (the role badge is
  // genuinely server-verified), and a whole-file grep would conflate the two.
  const fnStart = src.indexOf('function searchDrugs(');
  test('searchDrugs() is findable -- the arms below scope to it', function () {
    assert.notStrictEqual(fnStart, -1,
      'function searchDrugs( is gone or renamed. The badge arms cannot scope '
      + 'themselves and must not silently widen to the whole file.');
  });
  const region = fnStart === -1 ? '' : src.slice(fnStart, fnStart + 6000);

  test('the formulary badge does NOT read "Verified"', function () {
    assert.ok(region.indexOf('Verified</span>') === -1,
      'searchDrugs() renders a badge ending "Verified</span>" again. '
      + '`needsReview:false` is the absence of a flag, not a verification, and '
      + Math.round(unsourced.length / DRUGS.length * 100) + '% of rows cite no '
      + 'source at all. Use the three-state badge: Needs Review / Referenced / '
      + 'No source recorded.');
  });

  test('the badge branches on `reference`, not on needsReview alone', function () {
    assert.ok(/d\.reference/.test(region),
      'searchDrugs() no longer reads d.reference when choosing the badge, so '
      + 'the green state is back to being unearned.');
  });

  test('there is an explicit NO-SOURCE state, and it is not the green one', function () {
    assert.ok(/No source recorded/.test(region),
      'the "No source recorded" badge is gone. Two states cannot express this: '
      + 'flagged-for-review and cited-a-source do not cover the 482 rows that '
      + 'are neither.');
    const greenAt = region.indexOf('#D1FAE5');          // the green chip
    const noSrcAt = region.indexOf('No source recorded');
    assert.ok(greenAt === -1 || noSrcAt === -1 || Math.abs(greenAt - noSrcAt) > 120,
      'the No-source badge appears to use the green chip colour (#D1FAE5). '
      + 'An unsourced dose must not look like a confirmed one.');
  });

  section('THE AI GROUNDING PATH -- the claim that reaches the clinician');
  test('the dosing system prompt does not call the record "verified"', function () {
    const p = src.indexOf('You are a veterinary pharmacology assistant');
    assert.notStrictEqual(p, -1, 'the dosing system prompt could not be found');
    const prompt = src.slice(p, src.indexOf("';", p));
    assert.ok(!/verified (database|record)/i.test(prompt),
      'the system prompt tells the model the record is verified, so the model '
      + 'tells the vet. Prompt text: ' + prompt.slice(0, 200));
  });

  test('the prompt instructs the model to disclose an unsourced figure', function () {
    const p = src.indexOf('You are a veterinary pharmacology assistant');
    const prompt = src.slice(p, src.indexOf("';", p));
    assert.ok(/unsourced|cites no source|no published source/i.test(prompt),
      'the prompt no longer tells the model to say when a figure has no source. '
      + 'Silence there reads to the clinician as confirmation.');
  });

  test('the grounding context passes the row\'s sourcing to the model', function () {
    const g = src.indexOf("groundingContext = 'Stored formulary record:");
    assert.notStrictEqual(g, -1,
      'the grounding context no longer says "Stored formulary record" -- check '
      + 'it has not gone back to "Verified database record".');
    const near = src.slice(g, g + 700);
    // THE CONDITION, NOT JUST THE IDENTIFIER. The first draft of this arm
    // asserted `/m\.reference/` anywhere in the region and the ablation caught
    // it immediately: `m.reference` appears twice here -- once as the ternary
    // test and once inside the true branch -- so replacing the TEST with
    // `false` left the arm green while the model stopped being told anything
    // about sourcing. A presence check where a dependency check was meant is
    // the quietest way for an arm to stop asserting.
    assert.ok(/\+\s*\(\s*m\.reference\s*$/m.test(near)
              || /\+\s*\(\s*m\.reference\s*\?/.test(near),
      'the grounding context no longer BRANCHES on m.reference (the identifier '
      + 'may still appear, which is not the same thing), so the model is given '
      + 'no way to tell a cited row from an uncited one.');
    assert.ok(/CITES NO PUBLISHED SOURCE/.test(near),
      'the uncited branch of the grounding context is gone, so an unsourced '
      + 'figure now reaches the model looking exactly like a sourced one.');
  });

  test('the calculator box says CALCULATED, not VERIFIED', function () {
    const b = src.indexOf("getElementById('dose-verified-calc').innerHTML");
    assert.notStrictEqual(b, -1, 'the calculation box assignment is gone');
    const line = src.slice(b, src.indexOf('\n', b));
    assert.ok(!/Verified calculation/.test(line),
      'the box reads "Verified calculation" again. The multiplication is real; '
      + 'the mg/kg range it multiplied may have no source, and the green box '
      + 'transfers the confidence of the arithmetic onto the input.');
  });

  section('THE PROSE -- a fixed badge beside an unfixed sentence is not fixed');
  [['dashboard', 'grounded in verified data'],
   ['Ask-AI card', 'connected to the verified database']].forEach(function (pair) {
    test(pair[0] + ' does not claim the data is verified', function () {
      assert.ok(src.indexOf(pair[1]) === -1,
        'sairnvet.html still says "' + pair[1] + '". The badge and the sentence '
        + 'make the same claim and both have to be true.');
    });
  });

  section('THE CITATIONS THAT EXIST -- shape, not correctness');
  test('every reference names a retrievable source and a retrieval date', function () {
    const bad = sourced.filter(function (d) {
      return !/(doi:|PMID|DailyMed|NADA)/i.test(d.reference)
          || !/Retrieved \d{4}-\d{2}-\d{2}/.test(d.reference);
    }).map(function (d) { return d.name + '/' + d.species; });
    assert.deepStrictEqual(bad, [],
      'reference(s) without an identifier (doi/PMID/DailyMed/NADA) or without a '
      + '"Retrieved YYYY-MM-DD" date: ' + JSON.stringify(bad) + '. A citation '
      + 'nobody can follow back is prose, and one with no date cannot be '
      + 'rechecked when the label changes.');
  });

  test('a referenced row is not ALSO flagged needsReview', function () {
    const both = sourced.filter(function (d) { return d.needsReview; })
      .map(function (d) { return d.name + '/' + d.species; });
    assert.deepStrictEqual(both, [],
      'row(s) both cite a source and are flagged for review: '
      + JSON.stringify(both) + '. The badge shows Needs Review and hides the '
      + 'citation, so the work of finding the source is invisible.');
  });

  section('CONTROL -- these arms must be able to fail');
  test('the file really contains the strings the arms search for', function () {
    // Without this, every `indexOf(...) === -1` assertion above passes on an
    // empty read, a moved file, or a renamed function.
    assert.ok(src.length > 500000, 'sairnvet.html read as ' + src.length
      + ' bytes -- too small to be the app, so the absence assertions above are '
      + 'vacuous.');
    assert.ok(src.indexOf('Needs Review') !== -1,
      'the string "Needs Review" is absent from the whole file, which means the '
      + 'badge region is not what these arms think it is.');
    assert.ok(sourced.length >= 1,
      'no row carries a reference at all, so the citation-shape arms above are '
      + 'checking an empty list.');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
