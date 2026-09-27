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
// The species-copy detector is LIFTED out of sairnvet.html and run here rather
// than reimplemented -- see the CROSS-SPECIES section.
const vm = require('vm');
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

  // ── THE CROSS-SPECIES COPY, NOW FLAGGED IN THE APP ──────────────────────
  // FOUND 2026-09-26 while sourcing the controlled substances. The formulary
  // was largely built by propagating ONE dose across a drug's species rows,
  // and that is item 43 (Ariane 5) in clinical form: the copy is faithful and
  // the species is not.
  //
  // IT WAS REPORTED-ONLY FOR HALF A DAY and is now a warning in the app --
  // still never a refusal, because a shared dose is sometimes correct and a
  // gate here would refuse legitimate rows and be switched off within a week.
  //
  // THE DETECTOR IS LIFTED OUT OF THE APP, NOT REIMPLEMENTED HERE, and that
  // is the whole reason this section was rewritten. This file previously
  // carried its OWN copy of the grouping logic. Two declarations of one answer
  // drift -- and they drifted the same day: the app's rule was corrected from
  // per-drug to per-figure, and a test with its own copy would have gone on
  // reporting the superseded number while agreeing with nothing.
  section('CROSS-SPECIES DOSE COPYING -- the app\'s own detector, lifted');

  function lift(name) {
    const at = src.indexOf('function ' + name + '(');
    assert.notStrictEqual(at, -1, 'function ' + name + ' not found in sairnvet.html');
    const end = src.indexOf('\n}', at);
    assert.notStrictEqual(end, -1, name + ' has no column-0 closing brace');
    return src.slice(at, end + 2);
  }
  const ctx = vm.createContext({});
  vm.runInContext(lift('svSpeciesCopiedDoses'), ctx);
  const copied = ctx.svSpeciesCopiedDoses(DRUGS);
  console.log('  ' + copied.names + ' drug name(s) carry a dose figure on MORE THAN ONE '
    + 'species row -- ' + copied.count + ' of ' + DRUGS.length + ' rows, all flagged '
    + 'in the Drug Database and in the calculator\'s grounding context.');
  console.log('  Warned, never refused: a shared dose is sometimes correct. It is also '
    + 'how butorphanol/horse came to read 2-4x the FDA-approved equine dose.');

  test('the detector really ran and flagged a substantial share of the table', function () {
    assert.ok(copied.count > 200 && copied.count < DRUGS.length,
      'the detector flagged ' + copied.count + ' of ' + DRUGS.length + ' rows. '
      + 'It measured 315 when written. Near zero means the lift or the parse is '
      + 'broken, not that the formulary got species-specific; all of them means '
      + 'the grouping collapsed and the marker now says nothing.');
    assert.ok(copied.names > 100,
      'only ' + copied.names + ' drug name(s) flagged, against 119 when written.');
  });

  test('PER FIGURE, not per drug -- fixing one row must not hide the others', function () {
    // THE ARM THAT EXISTS BECAUSE THE FIRST RULE FAILED THIS. The original
    // detector asked whether a drug carried ONE figure across every species
    // row. Correcting butorphanol/horse made the group non-uniform and the
    // rule went quiet on dog, bird and exotic -- three rows still carrying the
    // exact figure just found wrong on a fourth. A detector that is silenced
    // by a partial fix makes the remaining copies look reviewed.
    ['dog', 'bird', 'exotic (unspecified)'].forEach(function (sp) {
      const e = copied.rows['Butorphanol|' + sp];
      assert.ok(e, 'Butorphanol/' + sp + ' is NOT flagged. It carries 0.2-0.4mg/kg, '
        + 'shared with the other two, and the horse row having been corrected to '
        + '0.1mg/kg is exactly why a per-drug rule stops seeing it.');
      assert.ok(/0\.2-0\.4/.test(e.figure),
        'Butorphanol/' + sp + ' is flagged on figure ' + e.figure
        + ', not the copied 0.2-0.4 one.');
    });
    ['horse', 'cat'].forEach(function (sp) {
      assert.ok(!copied.rows['Butorphanol|' + sp],
        'Butorphanol/' + sp + ' is flagged. It now carries its own species-specific '
        + 'figure with a citation, and warning about a corrected row teaches the '
        + 'reader to ignore the marker.');
    });
  });

  test('the Drug Database renders the marker, and against the DOSE', function () {
    const fnStart = src.indexOf('function searchDrugs(');
    const region = src.slice(fnStart, fnStart + 9000);
    assert.ok(/svCopiedDoseIndex\(\)/.test(region),
      'searchDrugs() no longer computes the species-copy index, so the 315 rows '
      + 'are unflagged on the screen a clinician reads.');
    assert.ok(/same figure in all/.test(region),
      'the per-row marker text is gone from searchDrugs().');
    // AGAINST THE FIGURE, not appended to the status badge. They answer
    // different questions and a row can be Referenced AND copied.
    assert.ok(/doseCell \+=/.test(region),
      'the marker is no longer added to the dose cell. It belongs against the '
      + 'FIGURE -- the status badge answers "was this sourced", the marker '
      + 'answers "was this figure ever about this species", and butorphanol/dog '
      + 'is both referenced and copied.');
    assert.ok(/copiedShown/.test(region) && /rows shown carry a dose figure identical/.test(region),
      'the aggregate line above the table is gone. Without it a clinician '
      + 'scanning results has to notice 30 individual markers.');

    // ── THE CHAIN, NOT THE STRINGS. THIS ARM EXISTS BECAUSE THE ONES ABOVE
    //    ALL PASSED WITH THE MARKER SWITCHED OFF. ─────────────────────────
    // Ablation, run before this shipped: replacing the guard with `if (false)`
    // left every assertion above green -- each of them checks that a string is
    // PRESENT, and a dead branch contains all of them. That is the same defect
    // the grounding-context arm in this file already carries a note about, and
    // it reappeared in a fresh arm within the hour.
    //
    // So the GUARD is pinned, not the strings inside it. The chain has to be
    // index -> lookup -> that lookup's result as the condition.
    assert.ok(/var copyEntry = copiedIdx\.rows\[/.test(region),
      'copyEntry is no longer looked up out of the species-copy index, so '
      + 'whatever the branch below tests, it is not "is this row a copy".');
    assert.ok(/\n\s*if \(copyEntry\) \{/.test(region),
      'the marker branch is no longer guarded by `if (copyEntry)` exactly. A '
      + 'constant-false guard (`if (false)`), an added `&& false`, or any other '
      + 'condition makes the marker unreachable while leaving every string '
      + 'assertion above satisfied -- which is precisely how this was ablated.');
    assert.ok(/\n\s*if \(calcCopy\) \{/.test(src),
      'the calculator\'s species-copy branch is no longer guarded by '
      + '`if (calcCopy)`, so the model and the box may never be told.');
    assert.ok(/calcCopyForBox\s*\n?\s*\?/.test(src) || /\(calcCopyForBox\s*$/m.test(src)
              || /\? '<div style="margin-top:8px;padding:8px;background:#FFF7ED/.test(src),
      'the on-screen box no longer BRANCHES on calcCopyForBox. The identifier '
      + 'may still appear, which is not the same thing.');
  });

  test('the calculator tells the MODEL and shows it ON SCREEN', function () {
    assert.ok(/SPECIES-COPY WARNING, tell the user this plainly/.test(src),
      'the dosing grounding context no longer carries the species-copy warning, '
      + 'so the model presents a copied figure exactly like a species-specific '
      + 'one.');
    assert.ok(/calcCopyForBox/.test(src),
      'the on-screen calculation box no longer shows the warning. Telling only '
      + 'the model leaves it dependent on the model choosing to repeat it, and '
      + 'the green box is what a clinician reads first.');
    // The two disclosures must be SEPARATE. A row can cite a source and still
    // carry a copied figure, so folding them into one sentence loses an answer.
    const g = src.indexOf("groundingContext = 'Stored formulary record:");
    const near = src.slice(g, g + 1600);
    assert.ok(/CITES NO PUBLISHED SOURCE/.test(near) && /SPECIES-COPY WARNING/.test(near),
      'the sourcing disclosure and the species-copy disclosure are no longer '
      + 'both present at the grounding context. They are independent: '
      + 'butorphanol/dog cites a source AND carries a copied figure.');
  });

  test('the warning WARNS and does not refuse', function () {
    const w = src.indexOf('function svCopiedDoseWarning(');
    assert.notStrictEqual(w, -1, 'svCopiedDoseWarning is gone');
    const body = src.slice(w, src.indexOf('\n}', w));
    assert.ok(/sometimes genuinely correct/.test(body),
      'the warning no longer says a shared dose is sometimes correct. Without '
      + 'that sentence it reads as "this dose is wrong" on 315 rows, most of '
      + 'which nobody has checked either way -- and a marker that overclaims '
      + 'gets ignored.');
    assert.ok(/Confirm against a species-specific/.test(body),
      'the warning no longer tells the reader what to DO about it.');
    // Nothing anywhere may turn this into a block.
    assert.ok(!/svCopiedDoseIndex[\s\S]{0,400}?(return;|blocked|refuse)/i.test(
                src.slice(src.indexOf('function calculateDoseAI'), src.indexOf('function calculateDoseAI') + 4000)),
      'the calculator appears to REFUSE on a species-copied row. It must warn: '
      + 'a shared dose is sometimes correct, and a gate here refuses legitimate '
      + 'rows and gets switched off.');
  });

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

  // ── WHAT THE LABEL READS ACTUALLY FOUND (2026-09-26) ────────────────────
  // The sourcing pass is not only about adding citations. Reading the real FDA
  // labels for the controlled substances produced two facts that are MORE use
  // to a clinician than a citation would have been, and neither could be
  // recorded as a `reference` without lying:
  //
  //   * KETAMINE: the label figure is HIGHER than the stored one, by 2-6x.
  //     Ketaset NADA 043-304 says 11mg/kg IM for restraint and 22-33mg/kg for
  //     anaesthesia; this table stores 5-10mg/kg, which is balanced-anaesthesia
  //     co-induction practice. Citing the label here would put a tick beside a
  //     figure its own source contradicts -- the buprenorphine/cat mistake.
  //     And dogs are not an approved species on that label at all.
  //
  //   * BUTORPHANOL/DOG: there is NO FDA-approved injectable butorphanol label
  //     covering dogs. Torbugesic-SA is cats-only, Torbugesic and Butorphic are
  //     horses-only. A verified ABSENCE is a finding; it is recorded in the
  //     flag, and the row deliberately stays uncited.
  //
  // These arms exist because a verified absence is the easiest thing in this
  // file to delete by accident: it looks like prose, and nothing else would
  // notice it going.
  section('THE LABEL READS -- a verified ABSENCE is a finding, not a blank');

  function row(name, species) {
    return DRUGS.filter(function (d) {
      return d.name === name && d.species === species;
    })[0];
  }

  test('ketamine/cat records that the FDA label figure is HIGHER, and is not cited to it', function () {
    const kc = row('Ketamine', 'cat');
    assert.ok(kc, 'the ketamine cat row is gone');
    assert.ok(/043-304/.test(String(kc.flag)),
      'the ketamine cat flag no longer names NADA 043-304 (Ketaset). Without the '
      + 'label identifier a reader cannot check the conflict for themselves.');
    assert.ok(/11\s*mg\/kg/.test(String(kc.flag)) && /22\s*to\s*33\s*mg\/kg/.test(String(kc.flag)),
      'the flag no longer states the label FIGURES (11mg/kg restraint, 22-33mg/kg '
      + 'anaesthesia). Naming the label without its numbers does not tell a vet '
      + 'that the stored 5-10mg/kg is a different thing -- it is the '
      + 'buprenorphine/Simbadol lesson: a brand name is not a warning, the '
      + 'concentrations are. flag was: ' + String(kc.flag).slice(0, 200));
    assert.ok(!kc.reference,
      'the ketamine cat row has acquired a citation. It must NOT be cited to '
      + 'the Ketaset label, which gives 11-33mg/kg against the 5-10mg/kg stored '
      + 'here -- a green tick beside a figure its own source contradicts is '
      + 'worse than no tick.');
    assert.strictEqual(kc.needsReview, true,
      'the ketamine cat row is no longer flagged for review, although the only '
      + 'FDA label for the species disagrees with its figure by 2-6x.');
  });

  test('ketamine/dog records that NO label covers dogs at all', function () {
    const kd = row('Ketamine', 'dog');
    assert.ok(kd, 'the ketamine dog row is gone');
    assert.ok(/NO FDA-APPROVED KETAMINE LABEL COVERS DOGS/.test(String(kd.flag)),
      'the ketamine dog flag no longer states that no approved label covers '
      + 'dogs. Ketaset NADA 043-304 approves cats and subhuman primates only; '
      + 'every canine use is extra-label and that is a fact a reader cannot '
      + 'derive from a missing citation.');
    assert.ok(!kd.reference, 'the ketamine dog row has acquired a citation, '
      + 'and there is no canine label to cite.');
  });

  test('butorphanol/dog records the verified ABSENCE of a canine label', function () {
    const bd = row('Butorphanol', 'dog');
    assert.ok(bd, 'the butorphanol dog row is gone');
    assert.ok(/NO FDA-APPROVED INJECTABLE BUTORPHANOL LABEL COVERS DOGS/.test(String(bd.flag)),
      'the butorphanol dog flag no longer records that no canine label exists.');
    // THE THREE LABELS THAT WERE CHECKED, not just the conclusion. A claim that
    // "no label covers dogs" is only checkable if it says WHICH labels were
    // read -- otherwise it is an assertion of absence with nothing behind it,
    // which is the same shape as the green tick this whole file exists to stop.
    ['141-047', '135-780', '200-332'].forEach(function (id) {
      assert.ok(String(bd.flag).indexOf(id) !== -1,
        'the flag no longer names ' + id + '. The absence claim is only '
        + 'checkable if the labels that were READ are named: Torbugesic-SA '
        + '(NADA 141-047, cats), Torbugesic (NADA 135-780, horses), Butorphic '
        + '(ANADA 200-332, horses).');
    });
    assert.ok(!bd.reference, 'the butorphanol dog row has acquired a citation, '
      + 'and the whole point of the flag is that there is nothing to cite.');
  });

  test('CONTROL -- an absence claim is not the same as an uncited row', function () {
    // Without this, the three arms above pass on a table where every row has
    // no reference and no flag either -- which is the state the file was in
    // this morning and is precisely what is being improved on.
    const uncitedAndUnflagged = DRUGS.filter(function (d) {
      return !d.reference && !String(d.flag || '').trim();
    }).length;
    assert.ok(uncitedAndUnflagged < DRUGS.length,
      'EVERY row is both uncited and unflagged, so the arms above are not '
      + 'distinguishing a verified absence from an empty row.');
    const verifiedAbsences = DRUGS.filter(function (d) {
      return !d.reference && /NO FDA-APPROVED/.test(String(d.flag || ''));
    }).length;
    console.log('  rows recording a VERIFIED ABSENCE of an approved label: '
      + verifiedAbsences);
    assert.ok(verifiedAbsences >= 2,
      'only ' + verifiedAbsences + ' row(s) record a verified absence. Two were '
      + 'established by reading the labels on 2026-09-26; a drop below that '
      + 'means one was deleted as prose.');
  });

  test('the flunixin CATTLE row says the label route is IV ONLY', function () {
    // FOOD SAFETY, not just dosing. The row said route "IV/IM"; Banamine's
    // label (NADA 101-479) is intravenous only in cattle, and extra-label IM or
    // SC flunixin is a known cause of VIOLATIVE TISSUE RESIDUES -- the 4-day
    // withdrawal is established for the IV route and does not hold for another.
    // A wrong route here does not hurt the animal, it puts residue in the food
    // supply and the withdrawal time beside it says everything is fine.
    const fc = row('Flunixin Meglumine', 'cattle');
    assert.ok(fc, 'the flunixin cattle row is gone');
    assert.ok(/IV ONLY/i.test(String(fc.route)),
      'the cattle route reads ' + JSON.stringify(fc.route) + '. The label is '
      + 'slow intravenous only.');
    assert.ok(/VIOLATIVE TISSUE RESIDUES/i.test(String(fc.flag)),
      'the flag no longer says WHY the route matters. "IV only" on its own '
      + 'reads as a preference; the residue consequence is what makes it a '
      + 'food-safety fact.');
    assert.ok(/101-479/.test(String(fc.reference || '')),
      'the cattle row lost its Banamine NADA citation');
    assert.strictEqual(fc.withdrawalStatus, 'label_sourced',
      'withdrawalStatus is ' + fc.withdrawalStatus + '. The meat and milk times '
      + 'are now read from the label, so telling a reader to "Verify Label" '
      + 'sends them to look up a figure this app is holding with a citation.');
    assert.ok(/4 days/.test(String(fc.withdrawalMeat))
              && /36 hours/.test(String(fc.withdrawalMilk)),
      'the withdrawal times are ' + JSON.stringify([fc.withdrawalMeat, fc.withdrawalMilk])
      + ', expected 4 days meat and 36 hours milk.');
  });

  // ── THE CATTLE FIGURE ON THE SWINE ROW ─────────────────────────────────
  //
  // FOUR FOOD-ANIMAL DRUGS SOURCED 2026-09-27, eight rows, and the same defect
  // came back three times: the swine row carried the CATTLE route, the CATTLE
  // dose, or both. That is the species-copy marker's class -- item 43, Ariane
  // 5, in clinical form -- but it is invisible to that detector whenever the
  // two species genuinely share a FIGURE and differ only in ROUTE, which is
  // exactly what tulathromycin does. The marker keys on the dose string.
  //
  // A WRONG ROUTE ON A FOOD ANIMAL IS A RESIDUE PROBLEM BEFORE IT IS A DOSING
  // ONE, and the withdrawal time printed beside it says everything is fine.
  // Every arm below is a fact read off an FDA label and quoted in the row's
  // own `reference` field; none of them asserts that a dose is clinically
  // correct, which is not a thing a static test can decide.

  test('tulathromycin: cattle is SC and swine is IM, and the row had them swapped', function () {
    const c = row('Tulathromycin', 'cattle'), s = row('Tulathromycin', 'swine');
    assert.ok(c && s, 'a tulathromycin food-animal row is gone');
    assert.ok(/SC ONLY/i.test(String(c.route)),
      'the cattle route reads ' + JSON.stringify(c.route) + '. DRAXXIN (NADA '
      + '141-244) says "Inject subcutaneously" in cattle; the row said SC/IM.');
    assert.ok(/IM ONLY/i.test(String(s.route)),
      'the swine route reads ' + JSON.stringify(s.route) + '. The same label '
      + 'says "Inject intramuscularly" in swine.');
    // THE DOSE IS IDENTICAL IN BOTH SPECIES AND IS CORRECT, which is why the
    // species-copy marker cannot see this one. Asserting it here is the point:
    // a shared figure with unshared routes is a shape that detector is blind
    // to, and this arm is the only thing holding it.
    assert.strictEqual(c.doseMin, 2.5);
    assert.strictEqual(s.doseMin, 2.5);
    assert.ok(/18 days/.test(String(c.withdrawalMeat))
              && /5 days/.test(String(s.withdrawalMeat)),
      'the meat withdrawals are ' + JSON.stringify([c.withdrawalMeat, s.withdrawalMeat])
      + ', expected 18 days cattle and 5 days swine -- they are not the same '
      + 'number and a row that carried one for both would be wrong by 13 days.');
  });

  test('florfenicol: the swine row carried the CATTLE dose, 20-40 against a label 15', function () {
    const c = row('Florfenicol', 'cattle'), s = row('Florfenicol', 'swine');
    assert.ok(c && s, 'a florfenicol food-animal row is gone');
    assert.strictEqual(s.doseMin, 15,
      'the swine dose bound is ' + s.doseMin + '. NUFLOR-S (NADA 141-063) is '
      + '15 mg/kg IM; the row read 20-40mg/kg, which is the cattle figure and '
      + 'runs from 33% to 167% above the swine label.');
    assert.ok(/IM ONLY/i.test(String(s.route)),
      'the swine route reads ' + JSON.stringify(s.route) + '; SC is not a '
      + 'labelled swine route for this product.');
    // THE CATTLE ROW IS THE OPPOSITE FIX and must NOT gain numeric bounds.
    // 20 mg/kg is the IM dose and 40 mg/kg the single SC dose, with 28- and
    // 38-day withdrawals respectively. A doseMin/doseMax of 20/40 would let
    // the calculator rebuild the exact false range this correction removed.
    assert.strictEqual(c.doseMin, null,
      'the florfenicol CATTLE row has acquired a numeric lower bound. The two '
      + 'labelled regimens are 20mg/kg IM repeated at 48h and 40mg/kg SC once; '
      + 'a min/max spanning them is not a range and the calculator would '
      + 'multiply it by a body weight.');
    assert.strictEqual(c.doseMax, null, 'see above -- upper bound restored too');
    assert.ok(/28 days/.test(String(c.withdrawalMeat))
              && /38 days/.test(String(c.withdrawalMeat)),
      'the cattle meat withdrawal is ' + JSON.stringify(c.withdrawalMeat)
      + '. The label gives BOTH -- 28 days after IM, 38 after SC -- and a row '
      + 'carrying only one tells half the readers the wrong date.');
  });

  test('ceftiofur: the swine row carried the CATTLE dose, and this one UNDER-doses', function () {
    const c = row('Ceftiofur', 'cattle'), s = row('Ceftiofur', 'swine');
    assert.ok(c && s, 'a ceftiofur food-animal row is gone');
    assert.strictEqual(s.doseMin, 3,
      'the swine dose bound is ' + s.doseMin + '. EXCENEL RTU EZ (NADA 141-288) '
      + 'is 3-5 mg CE/kg IM in swine; the row read 1-2.2mg/kg, which is the '
      + 'CATTLE dose. The direction matters and is recorded: this one is an '
      + 'under-dose, a treatment-failure and resistance risk rather than a '
      + 'residue one, which is the opposite of the florfenicol swine error.');
    assert.strictEqual(s.doseMax, 5);
    assert.strictEqual(c.doseMin, 1.1,
      'the cattle low bound is ' + c.doseMin + '; the label minimum is 1.1 '
      + 'mg CE/kg and the row read 1.');
    assert.ok(/IM ONLY/i.test(String(s.route)),
      'the swine route reads ' + JSON.stringify(s.route) + '; the label is '
      + 'intramuscular in swine, and IM or SC in cattle.');
    assert.ok(/volume/i.test(String(s.withdrawalMeat)),
      'the swine meat withdrawal is ' + JSON.stringify(s.withdrawalMeat)
      + '. It depends on INJECTION SITE VOLUME -- 4 days at 5mL or less, 6 '
      + 'days above it -- so a single number here is wrong for one of the two '
      + 'cases whichever number is chosen.');
  });

  test('oxytetracycline: a single long-acting dose and a daily dose are not one range', function () {
    const c = row('Oxytetracycline', 'cattle'), s = row('Oxytetracycline', 'swine');
    assert.ok(c && s, 'an oxytetracycline food-animal row is gone');
    // THE STORED ROW SAID "10-20mg/kg SID". LA-200 (NADA 113-232) has TWO
    // regimens: 9 mg/lb (~20 mg/kg) as a SINGLE long-acting dose, and 3-5
    // mg/lb (~6.6-11 mg/kg) PER DAY. Flattening them into a once-daily range
    // invites 20 mg/kg every day, which is neither.
    assert.strictEqual(c.doseMin, null,
      'the cattle row has numeric bounds again. The two labelled regimens '
      + 'differ in FREQUENCY, not just in size, and a min/max cannot carry '
      + 'that -- the calculator would multiply and print a daily figure.');
    assert.strictEqual(s.doseMin, null, 'same for the swine row');
    assert.ok(/SINGLE/i.test(String(c.dose)) && /day/i.test(String(c.dose)),
      'the cattle dose string is ' + JSON.stringify(c.dose) + ' and no longer '
      + 'distinguishes the single long-acting dose from the daily one.');
    assert.ok(/IM ONLY/i.test(String(s.route)),
      'the swine route reads ' + JSON.stringify(s.route) + '. IV is labelled '
      + 'in CATTLE only for this product, and the label warns that rapid IV '
      + 'administration may result in animal collapse.');
    assert.ok(/96 hours/.test(String(c.withdrawalMilk)),
      'the cattle milk discard is ' + JSON.stringify(c.withdrawalMilk)
      + ', expected 96 hours.');
  });

  test('CONTROL -- every withdrawal time names the PRODUCT it was read from', function () {
    // A withdrawal period belongs to a PRODUCT, not to a drug name, and these
    // rows are generic. "28 days" beside "Oxytetracycline" reads as a fact
    // about oxytetracycline; it is a fact about LIQUAMYCIN LA-200, and a
    // short-acting injectable of the same drug has a different one. Every
    // label_sourced row therefore names its product or its NADA IN THE
    // WITHDRAWAL STRING, where the reader sees it, not only in the citation.
    const bare = DRUGS.filter(function (d) {
      if (d.withdrawalStatus !== 'label_sourced') return false;
      const m = String(d.withdrawalMeat || '');
      return !/NADA|\(/.test(m);
    }).map(function (d) { return d.name + '/' + d.species + ': ' + d.withdrawalMeat; });
    assert.deepStrictEqual(bare, [],
      'label_sourced row(s) whose meat withdrawal names no product: '
      + JSON.stringify(bare) + '. A bare number generalises one product\'s '
      + 'withdrawal to every formulation of the drug.');
  });

  test('a label_sourced row MUST carry a reference -- the badge shows it', function () {
    // The green withdrawal badge puts the reference in its tooltip. A row
    // marked label_sourced with no reference renders a green chip whose hover
    // text is an apology, which is worse than the amber "Verify Label" it
    // replaced.
    const bad = DRUGS.filter(function (d) {
      return d.withdrawalStatus === 'label_sourced' && !d.reference;
    }).map(function (d) { return d.name + '/' + d.species; });
    assert.deepStrictEqual(bad, [],
      'row(s) marked label_sourced with no citation: ' + JSON.stringify(bad));
  });

  test('the flunixin HORSE row records that the label is ONCE DAILY', function () {
    const fh = row('Flunixin Meglumine', 'horse');
    assert.ok(fh, 'the flunixin horse row is gone');
    assert.ok(/ONCE DAILY/i.test(String(fh.dose)),
      'the horse dose reads ' + JSON.stringify(fh.dose) + '. The label is once '
      + 'daily for up to 5 days; the row previously said SID-BID and BID is '
      + 'extra-label in the horse.');
    assert.ok(/101-479/.test(String(fh.reference || '')),
      'the horse row lost its Banamine NADA citation');
  });

  test('the species-copy marker still fires on flunixin -- and is CORRECT to', function () {
    // WORTH ASSERTING BECAUSE IT LOOKS LIKE A FALSE POSITIVE AND IS NOT. Horse
    // and cattle both carry 1.1mg/kg, so the marker flags them as a shared
    // figure -- and the labels confirm BOTH are genuinely 1.1mg/kg. This is the
    // case the marker was deliberately built to WARN about rather than refuse:
    // a shared dose is sometimes correct, and here it is correct for two
    // species on two separate label indications. If this ever becomes a gate,
    // this row is what it would wrongly reject.
    const fh = copied.rows['Flunixin Meglumine|horse'];
    assert.ok(fh, 'flunixin/horse is no longer flagged as sharing a figure. '
      + 'That may be right -- but if the doses have been differentiated, the '
      + 'comment in svSpeciesCopiedDoses about this case needs rewriting too.');
    assert.ok(/1\.1/.test(String(fh.figure)),
      'flunixin/horse is flagged on figure ' + fh.figure + ', not 1.1');
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
