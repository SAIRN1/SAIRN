// tests/sairnvet_povidone_range.js
//
// REQUIREMENT: every Topical Antiseptic row in sairnvet.html must state the
//   concentration its cited source actually gives, and must carry that citation
//   -- a clinician reading a dilution off this screen is reading a clinical
//   instruction, and the only thing standing behind it is the quoted source.
//
// Run:  node tests/sairnvet_povidone_range.js
//
// ── WHAT THIS IS ABOUT ──────────────────────────────────────────────────────
// The source was retrieved on 2026-09-26 and is quoted verbatim in the row's own
// `reference` field:
//
//   Mickelson MA, Mans C, Colopy SA. Principles of Wound Management and Wound
//   Healing in the Exotic Pets. Vet Clin North Am Exot Anim Pract. 2016
//   Jan;19(1):33-53. PMID 26611923.
//   "If antiseptic solutions are chosen, 0.05% chlorhexidine and 0.5 or 1%
//    povidone-iodine would be considered appropriate."
//
// THE SOURCE GIVES 0.5% OR 1%. The table said "Dilute to 1%" on the one row that
// carried the citation and "Dilute 1:10 for lavage" on the other three, which is
// a ratio rather than a concentration and is only 1% if the stock is 10%. Neither
// is what the source says, and the row that cited the source was the one that
// disagreed with it most specifically -- it narrowed a range to its upper bound
// and presented that as sourced.
//
// AND THE SOURCE PLACES NO SPECIES RESTRICTION ON IT. Two rows read "generally
// safe across species at this dilution", which the quote does not say -- it says
// the concentration "would be considered appropriate". Safety across species is a
// stronger claim than appropriateness in one wound-management context, and the
// difference is the kind a clinician would act on.
//
// ── WHY A TEST AND NOT A CORRECTION ────────────────────────────────────────
// A corrected string is one edit away from regrowing, and this one regrew once
// already: the range was narrowed on the row that had just been given a citation,
// i.e. during the act of sourcing it. The arms below fail if any povidone row
// states a concentration the quote does not contain, if the four rows disagree
// with each other, or if the citation and the dose drift apart in either
// direction.

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

const m = /var VET_DRUGS = (\[[\s\S]*?\]);/.exec(src);
const DRUGS = m ? JSON.parse(m[1]) : null;

const PMID = '26611923';
const QUOTE = 'If antiseptic solutions are chosen, 0.05% chlorhexidine and 0.5 '
            + 'or 1% povidone-iodine would be considered appropriate.';

function rowsOf(name) {
  return (DRUGS || []).filter(function (d) { return d.name === name; });
}

// THE PREDICATE, ONE DEFINITION. Both the real rows and the known-bad synthetic
// row are judged by this same function, which is the only way the known-bad arm
// proves anything about the real arm.
function statesTheSourcedRange(dose) {
  if (typeof dose !== 'string') return false;
  // The range, either spelling the source supports.
  const hasRange = /0\.5\s*(?:-|–|to|or)\s*1\s*%/.test(dose)
                || /0\.5\s*%\s*(?:or|to|-|–)\s*1\s*%/.test(dose);
  // And NOT a bare upper bound or a bare ratio presented as the instruction.
  const narrowsToOne = /\bdilute\s+to\s+1\s*%/i.test(dose);
  const bareRatio = /1\s*:\s*10/.test(dose) && !hasRange;
  return hasRange && !narrowsToOne && !bareRatio;
}

// The claim the quote does NOT make.
function claimsCrossSpeciesSafety(s) {
  return typeof s === 'string' && /generally safe across species/i.test(s);
}

(function () {
  console.log('SAIRNVET TOPICAL ANTISEPTICS -- the dose must be what the source says');

  section('THE TABLE AND THE ANCHOR');

  test('A0. ANCHOR: VET_DRUGS parses, the class string is still "Topical '
    + 'Antiseptic", and the eight rows this file is about are all present. If '
    + 'any of that changes every arm below would pass against nothing',
    function () {
      assert.ok(Array.isArray(DRUGS) && DRUGS.length > 400,
        'VET_DRUGS did not parse');
      const anti = DRUGS.filter(function (d) {
        return d['class'] === 'Topical Antiseptic';
      });
      assert.strictEqual(anti.length, 8,
        'expected 8 Topical Antiseptic rows, found ' + anti.length
        + ' -- the population this file measures has changed');
      assert.strictEqual(rowsOf('Betadine (Povidone-Iodine)').length, 4,
        'expected 4 povidone rows');
      assert.strictEqual(rowsOf('Chlorhexidine Solution').length, 4,
        'expected 4 chlorhexidine rows');
    });

  section('A. THE FOUR POVIDONE ROWS STATE THE SOURCED RANGE');

  rowsOf('Betadine (Povidone-Iodine)').forEach(function (d) {
    test('A1[' + d.species + ']. the dose states 0.5-1%, the range the quote '
      + 'gives -- not "Dilute to 1%", which narrows a range to its upper bound, '
      + 'and not a bare 1:10 ratio, which is a concentration only if the stock '
      + 'happens to be 10%',
      function () {
        assert.ok(statesTheSourcedRange(d.dose),
          'dose is ' + JSON.stringify(d.dose));
      });
  });

  test('A2. KNOWN-BAD, judged by the SAME predicate: the exact string the table '
    + 'shipped -- "Dilute to 1% for lavage (1:10 from 10% stock)" -- must FAIL. '
    + 'Without this the arms above could be passing on a predicate that accepts '
    + 'anything',
    function () {
      assert.strictEqual(
        statesTheSourcedRange('Dilute to 1% for lavage (1:10 from 10% stock)'),
        false, 'the predicate accepts the string this fix exists to remove');
      assert.strictEqual(statesTheSourcedRange('Dilute 1:10 for lavage'), false,
        'the predicate accepts a bare ratio as a concentration');
      assert.strictEqual(statesTheSourcedRange('1% for lavage'), false,
        'the predicate accepts the upper bound alone');
      assert.strictEqual(statesTheSourcedRange('0.5-1% for lavage'), true,
        'the predicate rejects the correct range, so A1 is passing for some '
        + 'other reason');
    });

  test('A3. all four povidone rows state the SAME range. The defect arrived as '
    + 'one row disagreeing with the other three, and a per-species divergence '
    + 'is exactly what the quote does not support',
    function () {
      const ranges = rowsOf('Betadine (Povidone-Iodine)').map(function (d) {
        const mm = /0\.5\s*(?:-|–|to|or)\s*1\s*%/.exec(d.dose || '');
        return mm ? mm[0].replace(/\s+/g, '') : 'NONE(' + d.species + ')';
      });
      assert.strictEqual(new Set(ranges).size, 1,
        'the four rows state different ranges: ' + JSON.stringify(ranges));
    });

  section('B. THE CITATION IS ON ALL EIGHT, AND IT AGREES WITH THE DOSE');

  DRUGS.filter(function (d) { return d['class'] === 'Topical Antiseptic'; })
    .forEach(function (d) {
      test('B1[' + d.name.split(' ')[0] + '/' + d.species + ']. carries the '
        + 'reference, with the PMID and the verbatim quote. A dose a clinician '
        + 'acts on and cannot trace is the defect this app already has a suite '
        + 'about',
        function () {
          assert.ok(typeof d.reference === 'string' && d.reference.length > 40,
            'no reference on this row');
          assert.ok(d.reference.indexOf(PMID) > -1,
            'reference does not carry PMID ' + PMID);
          assert.ok(d.reference.indexOf(QUOTE) > -1,
            'reference does not carry the verbatim quote, so nothing on the row '
            + 'constrains what the dose may say');
        });
    });

  test('B2. THE TWO HALVES CANNOT DRIFT: the quote stored on the row actually '
    + 'contains both concentrations the rows state -- 0.05% for chlorhexidine '
    + 'and 0.5 or 1% for povidone. This is what makes A1 a check against the '
    + 'SOURCE rather than against another string in the same file',
    function () {
      assert.ok(QUOTE.indexOf('0.05% chlorhexidine') > -1,
        'the quote no longer supports the chlorhexidine concentration');
      assert.ok(QUOTE.indexOf('0.5 or 1% povidone-iodine') > -1,
        'the quote no longer supports the povidone range');
      const refs = DRUGS
        .filter(function (d) { return d['class'] === 'Topical Antiseptic'; })
        .map(function (d) { return d.reference; });
      refs.forEach(function (r) {
        assert.ok(r && r.indexOf(QUOTE) > -1,
          'a row stores a DIFFERENT quote than the one these arms check '
          + 'against, which is the drift this arm exists to catch');
      });
    });

  test('B3. KNOWN-BAD for B1: a reference with the citation but WITHOUT the '
    + 'verbatim quote must fail the same check. A bibliographic string is not '
    + 'evidence of what the source says',
    function () {
      const bare = 'Mickelson MA, Mans C, Colopy SA. Vet Clin North Am Exot '
                 + 'Anim Pract. 2016. PMID 26611923.';
      assert.strictEqual(bare.indexOf(QUOTE) > -1, false,
        'the check would accept a citation carrying no quote');
    });

  section('C. NO CLAIM THE QUOTE DOES NOT MAKE');

  test('C1. no Topical Antiseptic row says "generally safe across species". The '
    + 'quote says the concentration "would be considered appropriate" in one '
    + 'wound-management context; safety across species is a stronger and '
    + 'different claim, and it was on the two rows that carried the citation',
    function () {
      const offenders = DRUGS
        .filter(function (d) { return d['class'] === 'Topical Antiseptic'; })
        .filter(function (d) {
          return claimsCrossSpeciesSafety(d.dose)
              || claimsCrossSpeciesSafety(d.flag);
        })
        .map(function (d) { return d.name + '/' + d.species; });
      assert.deepStrictEqual(offenders, [],
        'these make a cross-species safety claim the source does not: '
        + offenders.join(', '));
    });

  test('C2. KNOWN-BAD for C1: the exact phrase the rows shipped must be '
    + 'detected',
    function () {
      assert.strictEqual(
        claimsCrossSpeciesSafety('0.05% flush or wipe — generally safe across '
          + 'species at this dilution'), true,
        'the detector misses the phrase it was written for');
    });

  test('C3. and the species-neutral wording is still SPECIES-NEUTRAL: none of '
    + 'the four povidone rows restricts the range to a species, because the '
    + 'source does not. A hedge naming one species would make the other three '
    + 'rows unsourced',
    function () {
      const bad = rowsOf('Betadine (Povidone-Iodine)').filter(function (d) {
        return /\b(?:in dogs|in cats|in horses|dogs only|cats only|exotics only)\b/i
          .test(String(d.dose) + ' ' + String(d.flag));
      }).map(function (d) { return d.species; });
      assert.deepStrictEqual(bad, [],
        'these rows scope the range to a species: ' + bad.join(', '));
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
