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

  // ── EVERY `verified` IN THE FILE, NOT THE FOUR THIS TEST HAPPENED TO NAME ──
  //
  // ADDED 2026-09-26, HOURS AFTER THE ARMS ABOVE PASSED, and the reason it was
  // added is the reason it has to exist. The badge fix swept the Drug Database
  // panel and the Dosing Calculator, and the arms above pinned every site it
  // touched -- by NAME: this prompt, that grounding context, those two prose
  // strings. All of them stayed green while THREE unearned claims survived in
  // the Treatment Protocol panel and one more in Ask-AI:
  //
  //   'This diagnosis/species combination is not in our verified database.'
  //   'Verified database record(s) for this diagnosis: ' + JSON.stringify(...)
  //   '...cite which part of your answer comes from the verified database record'
  //   '...use the AI Dosing Calculator (for verified, bounds-checked doses)'
  //
  // They were found by the post-push live check searching the WHOLE deployed
  // file, which is the one thing the arms above never did. A named-site arm can
  // only ever pin the sites somebody already knew about, and the defect was
  // never "this string is wrong" -- it was "this app believes its tables are
  // verified", which reappears wherever a new panel is written.
  //
  // AND THE TABLE BEHIND THE PROTOCOL PANEL IS WORSE-PLACED THAN THE FORMULARY:
  // VET_DRUGS has a `reference` field, 5 of 485 filled. VET_DIAGNOSES has 465
  // rows and keys name/signs/species/system -- NO SOURCE FIELD AT ALL, so not
  // one entry could cite anything even if somebody looked it up.
  //
  // SO THIS ARM INVERTS THE DEFAULT. The word is refused everywhere in the file
  // unless its context is one of the ADMITTED shapes below. Admitting a new one
  // is a deliberate edit to this list with a reason, which is the point: a new
  // panel that calls a table verified fails here rather than shipping.
  section('EVERY "verified" IN THE FILE -- the sweep the named-site arms cannot do');

  // Each entry: a regex the 280-character window around a hit may match, and
  // WHY that context is honest. Nothing is admitted by position or count.
  const ADMITTED = [
    [/never describe that record as verified/i,
     'a prompt PROHIBITING the claim'],
    [/not as verified reference material/i,
     'a grounding context denying the claim in the same breath'],
    [/not the same as a verified dose/i,
     'Ask-AI distinguishing a calculation from a verification'],
    [/must be verified against the current product label/i,
     'an INSTRUCTION to go and verify -- the opposite of a claim'],
    [/not yet verified for this species/i,
     'the needsReview gap notice, which says NOT verified'],
    [/server-verified|verified by the server|SERVER-VERIFIED|which verified role/,
     'the role badge, which really is checked by whoami -- the one genuine '
     + 'verification in this file'],
    [/_svKeyVerified|dose-verified-calc/,
     'an identifier: a storage-guard flag and a DOM element id, neither of '
     + 'which is read by a clinician'],
    [/completeness VERIFIED/,
     'the dose-audit banner\'s computed three-state, about row COMPLETENESS '
     + 'and not about sourcing'],
    [/no\s+\/\/?\s*verified identity|verified identity to put in one/,
     'a comment about the ABSENCE of a verified identity'],
    [/carries no\s+\/\/?\s*verified jurisdiction|no\s+\/\/ verified jurisdiction/,
     'a comment about the ABSENCE of a verified jurisdiction'],
    [/built and verified in StoneDesk/,
     'a porting note about CODE reused from another app, not about data'],
    [/is never verified" -- true when written|never server-verified"/,
     'a comment quoting a superseded comment, historically'],
    [/THE GREEN TICK USED TO BE A CLAIM|displayed the word VERIFIED|needsReview:false` is not a verification|WRONG PLACE FOR AN UNEARNED TICK|"Verified" next/,
     'the comment block narrating this very defect'],
    [/"Stored", not "verified"|NOT "verified"|"Calculated", not "Verified"|Saying Verified|not "verified" --|calls the table verified is what the next editor/,
     'a comment explaining why the word was removed here'],
    [/IS NOT A VERIFIED DATABASE|"Verified" here was not an overstatement|removed "verified" from the Drug|verified database record" cannot tell that nothing was verified/,
     'the comment block narrating the protocol-panel defect'],
  ];

  function admit(window) {
    for (let i = 0; i < ADMITTED.length; i++) {
      if (ADMITTED[i][0].test(window)) return ADMITTED[i][1];
    }
    return null;
  }

  // `unverified` CONTAINS `verified` and is the honest word; it is not a hit.
  function claimHits(text) {
    const out = [];
    const re = /verified/gi;
    let m;
    while ((m = re.exec(text)) !== null) {
      if (/un$/i.test(text.slice(Math.max(0, m.index - 2), m.index))) continue;
      out.push(m.index);
    }
    return out;
  }

  // VET_DRUGS's own row text says "Verify current product label..." many times.
  // That is an instruction to the reader inside DATA, it is not a claim, and it
  // is not matched by /verified/ at all -- but the table is excluded anyway so
  // that a future row containing the past participle cannot hide in 200KB of
  // one line. The exclusion is NARROW and its own arm below proves it is not
  // swallowing the rest of the file.
  const tableStart = src.indexOf('var VET_DRUGS = [');
  const tableEnd = tableStart === -1 ? -1 : src.indexOf('];', tableStart);
  const scanned = tableStart === -1 ? src
    : src.slice(0, tableStart) + src.slice(tableEnd);

  test('every "verified" outside VET_DRUGS is an ADMITTED context', function () {
    const unadmitted = claimHits(scanned).map(function (h) {
      const w = scanned.slice(Math.max(0, h - 140), h + 140).replace(/\s+/g, ' ');
      return admit(w) ? null : w;
    }).filter(Boolean);
    assert.deepStrictEqual(unadmitted, [],
      unadmitted.length + ' context(s) use the word "verified" in a way this '
      + 'file has not admitted. Either the claim is unearned -- in which case '
      + 'reword it, as the Treatment Protocol and Ask-AI prompts were on '
      + '2026-09-26 -- or it is genuinely honest, in which case ADD IT TO '
      + '`ADMITTED` with a sentence saying why. Do not widen an existing '
      + 'pattern to cover it; a pattern that matches two different '
      + 'justifications stops testing either. Context(s):\n\n'
      + unadmitted.map(function (w) { return '    ...' + w + '...'; }).join('\n\n'));
  });

  test('the four sites found by the live check are specifically absent', function () {
    // Named as well as swept. The sweep is the general guard; these four are
    // the instances that actually shipped, and a regression to any of them
    // must name itself rather than arriving as "an unadmitted context".
    [['Treatment Protocol miss-branch', 'not in our verified database'],
     ['Treatment Protocol grounding', 'Verified database record(s)'],
     ['Treatment Protocol prompt', 'comes from the verified database record'],
     ['Ask-AI prompt', 'for verified, bounds-checked doses']].forEach(function (p) {
      assert.strictEqual(src.indexOf(p[1]), -1,
        p[0] + ' says "' + p[1] + '" again.');
    });
  });

  test('VET_DIAGNOSES has no source field, and the protocol path SAYS so', function () {
    const m2 = /var VET_DIAGNOSES = (\[[\s\S]*?\]);/.exec(src);
    assert.ok(m2, 'VET_DIAGNOSES did not parse -- the arm below is vacuous '
      + 'without it and must not pass on a failed read.');
    const DX = JSON.parse(m2[1]);
    const withSource = DX.filter(function (d) { return d.reference || d.source; });
    assert.strictEqual(withSource.length, 0,
      'VET_DIAGNOSES rows have acquired a source field (' + withSource.length
      + ' of ' + DX.length + '). That is GOOD, and it means this arm and the '
      + 'prompt wording below both need rewriting: the prompt currently tells '
      + 'the model the library records no source for ANY entry, which would '
      + 'now be false, and a false disclosure is its own defect.');
    assert.ok(/THIS LIBRARY RECORDS NO SOURCE FOR ANY ENTRY/.test(src),
      'the protocol grounding context no longer tells the model that the '
      + 'diagnosis library cites nothing. ' + DX.length + ' entries, zero '
      + 'source fields; silence there reads to the clinician as confirmation, '
      + 'which is exactly what the formulary badge did.');
  });

  test('CONTROL -- the sweep fires on a planted claim', function () {
    // Without this the arm above passes on an empty `scanned`, on a regex that
    // never matches, and on an ADMITTED list that has quietly grown to admit
    // everything. Item 12 of the cross-domain disciplines in one assertion.
    const planted = 'groundingContext = \'Verified database record for this '
      + 'patient, use it as your source of truth\';';
    assert.strictEqual(claimHits(planted).length, 1,
      'the hit-finder does not find the planted claim, so the sweep above is '
      + 'scanning for something that cannot be found.');
    assert.strictEqual(admit(planted), null,
      'the ADMITTED list matches a plainly unearned claim: '
      + JSON.stringify(planted) + '. It has grown until it admits everything, '
      + 'which is the state in which this whole section reports a pass it '
      + 'never performed.');
    // ...and the honest word must still be ignored, or the arm cries wolf on
    // every disclosure in the file and gets switched off.
    assert.strictEqual(claimHits('the record is unverified and says so').length, 0,
      '"unverified" is being counted as a claim. It is the disclosure, not the '
      + 'overclaim, and an arm that fails on it will be deleted rather than '
      + 'satisfied.');
  });

  test('CONTROL -- excluding VET_DRUGS did not exclude the file', function () {
    assert.ok(scanned.length > 400000,
      'the VET_DRUGS exclusion removed ' + (src.length - scanned.length)
      + ' of ' + src.length + ' bytes, leaving ' + scanned.length
      + '. The sweep is meant to skip one table, not most of the app.');
    assert.ok(claimHits(scanned).length > 20,
      'only ' + claimHits(scanned).length + ' "verified" hit(s) outside '
      + 'VET_DRUGS. This file had 37 when the sweep was written; a collapse to '
      + 'near zero means the slice is wrong, not that the app got honest.');
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

  // ── THE CROSS-SPECIES COPY, MEASURED ON EVERY RUN ───────────────────────
  // FOUND 2026-09-26 while sourcing the controlled substances. The formulary
  // was largely built by propagating ONE dose across a drug's species rows,
  // and that is item 43 (Ariane 5) in clinical form: the copy is faithful and
  // the species is not. It is REPORTED rather than gated, because a shared
  // dose is sometimes correct -- chlorhexidine really is 0.05% in every
  // species -- so a threshold here would refuse legitimate rows. What IS
  // pinned is the instance that was measured WRONG.
  section('CROSS-SPECIES DOSE COPYING -- reported, not gated');
  const byName = {};
  DRUGS.forEach(function (d) { (byName[d.name] = byName[d.name] || []).push(d); });
  const numRe = /^\s*([0-9.]+\s*-\s*[0-9.]+\s*[a-z/%]+|[0-9.]+\s*[a-z/%]+)/i;
  let copiedNames = 0, copiedRows = 0;
  Object.keys(byName).forEach(function (n) {
    const rows = byName[n];
    if (rows.length < 2) return;
    const seen = {};
    rows.forEach(function (d) {
      const m = numRe.exec(String(d.dose == null ? '' : d.dose));
      if (m) {
        const k = m[1].replace(/\s+/g, '').toLowerCase();
        (seen[k] = seen[k] || []).push(d.species);
      }
    });
    const keys = Object.keys(seen);
    if (keys.length === 1 && seen[keys[0]].length > 1) {
      copiedNames++; copiedRows += seen[keys[0]].length;
    }
  });
  console.log('  ' + copiedNames + ' drug name(s) carry ONE numeric dose across every '
    + 'species row -- ' + copiedRows + ' of ' + DRUGS.length + ' rows.');
  console.log('  Reported, not gated: a shared dose is sometimes correct. It is also '
    + 'how butorphanol/horse came to read 2-4x the FDA-approved equine dose.');

  test('the butorphanol HORSE row no longer carries the dog/cat figure', function () {
    const bh = DRUGS.filter(function (d) {
      return d.name === 'Butorphanol' && d.species === 'horse';
    })[0];
    const bd = DRUGS.filter(function (d) {
      return d.name === 'Butorphanol' && d.species === 'dog';
    })[0];
    assert.ok(bh && bd, 'the butorphanol horse or dog row is gone');
    assert.ok(!/0\.2-0\.4/.test(String(bh.dose)),
      'butorphanol/horse reads ' + JSON.stringify(bh.dose) + ' again. The FDA '
      + 'label (Torbugesic, NADA 135-780) is 0.1 mg/kg IV; 0.2-0.4 is the '
      + 'dog/cat figure copied across all five species rows and is 2-4x the '
      + 'approved equine dose.');
    assert.notStrictEqual(String(bh.dose), String(bd.dose),
      'the horse and dog rows carry the same dose string again');
    assert.ok(bh.reference && /Torbugesic/.test(bh.reference),
      'the horse row lost its FDA label citation');
  });

  test('the buprenorphine CAT row names the formulation trap', function () {
    const bc = DRUGS.filter(function (d) {
      return d.name === 'Buprenorphine' && d.species === 'cat';
    })[0];
    assert.ok(bc, 'the buprenorphine cat row is gone');
    // THE FIGURES, NOT THE BRAND NAME. The first version of this arm asserted
    // only /SIMBADOL/i, and the ablation walked straight through it: the flag
    // mentions Simbadol twice, so deleting the sentence that carries the
    // CONCENTRATION left the arm green while the trap stopped being described.
    // A brand name is not a warning; 1.8mg/mL against 0.3mg/mL is.
    assert.ok(/SIMBADOL/i.test(String(bc.flag)) && /1\.8\s*mg\/mL/i.test(String(bc.flag))
              && /0\.24\s*mg\/kg/i.test(String(bc.flag)),
      'the cat row no longer states the Simbadol CONCENTRATION and DOSE. Two '
      + 'FDA-approved feline products differ about tenfold in mg/kg (0.3mg/mL '
      + 'conventional vs 1.8mg/mL Simbadol at 0.24mg/kg SC); naming the brand '
      + 'without the figures does not tell a vet which vial they are holding. '
      + 'flag was: ' + String(bc.flag).slice(0, 200));
    assert.ok(!bc.reference,
      'the buprenorphine cat row has acquired a citation. It must NOT be cited '
      + 'to the Simbadol label, which CONTRADICTS the 0.01-0.03 figure -- a '
      + 'green tick beside a number its own source disagrees with is worse '
      + 'than no tick.');
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
