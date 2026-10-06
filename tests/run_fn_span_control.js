// tests/run_fn_span_control.js
//
// Run:  node tests/run_fn_span_control.js
//
// THE CONTROL FOR THE 2026-10-06 SPAN SWEEP. Five arms across four suites were
// reading a function body bounded by something other than that function's own
// closing brace. FOUR were repointed at tests/lib/fn_span.js; the fifth
// (tests/stonedesk_server_backup.js) is BLOCKED by hank's active claim on
// stonedesk and is routed, not fixed -- its arm below says so in its name.
// This file proves, per arm, that the repoint CHANGES THE ANSWER on a planted
// input, because a fix that cannot be shown to bite is a fix nobody can tell
// from a no-op.
//
// A SIXTH SITE IS NOT HERE AND THAT IS NOT AN OVERSIGHT:
// tests/sairnbiz_vendor_ytd_derivation.js:100 bounds rVends() with a marker
// that is 30 bytes short of the close, under an ABSENCE assertion -- the
// silent direction. That file is in cc's active claim; it is routed, not
// touched. See docs/2026-10-06-fourth-routed-to-cc.md.
//
// ── WHY IT PLANTS INSTEAD OF ASSERTING ────────────────────────────────────
// Every one of the five arms is GREEN both before and after the fix. That is
// exactly the situation in which a span repoint looks like a cosmetic edit.
// So each arm here builds a source string in which the OLD bound and the NEW
// bound must disagree, and asserts BOTH sides:
//
//   HOLE   -- under the OLD bound the arm's predicate gives the WRONG answer
//   CLOSED -- under the NEW bound it gives the right one
//
// An arm that cannot demonstrate the hole is reported as NOT PROVEN rather
// than counted, because "the planted case did not bite" and "the fix works"
// are different statements and only one of them is evidence.
//
// ── IT MUTATES NOTHING ON DISK ────────────────────────────────────────────
// The planting happens in memory, on a copy of the app source. No app file is
// written, so there is no restore step to forget and no sha to re-verify.
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { fnBody, fnSpan } = require('./lib/fn_span.js');

const ROOT = path.join(__dirname, '..');
const read = (f) => fs.readFileSync(path.join(ROOT, f), 'utf8');

let pass = 0;
let fail = 0;
let notProven = 0;

// Plant `text` immediately AFTER the function's balanced close, so it lands
// inside the old over-long bound and outside the new one.
function plantAfter(src, signature, text) {
  const sp = fnSpan(src, signature);
  return src.slice(0, sp.end) + text + src.slice(sp.end);
}

// Plant `text` at the far END of the function body, past a short window's
// reach but inside the function.
function plantAtEnd(src, signature, text) {
  const sp = fnSpan(src, signature);
  return src.slice(0, sp.end - 1) + text + src.slice(sp.end - 1);
}

function arm(name, opts) {
  // opts: { file, signature, oldBound(src,start), predicate(body),
  //         plant, wrongAnswerIsTrue }
  try {
    const src = read(opts.file);
    const planted = opts.plant(src);
    const start = planted.indexOf(opts.signature);
    const oldBody = planted.slice(start, opts.oldBound(planted, start));
    const newBody = fnBody(planted, opts.signature);

    const oldSays = opts.predicate(oldBody);
    const newSays = opts.predicate(newBody);

    if (oldSays === newSays) {
      notProven++;
      console.log('  NOT PROVEN - ' + name
        + '\n        the planted input did not separate the two bounds '
        + '(both said ' + oldSays + '). The fix may still be right; this arm '
        + 'is not evidence for it.');
      return;
    }
    assert.strictEqual(oldSays, opts.wrongAnswerIsTrue,
      'the OLD bound did not give the wrong answer on the planted input');
    assert.strictEqual(newSays, !opts.wrongAnswerIsTrue,
      'the NEW bound did not give the right answer on the planted input');

    // And the unplanted source must still read correctly under the new bound,
    // so the fix is not simply making everything fail.
    const clean = fnBody(src, opts.signature);
    assert.strictEqual(opts.predicate(clean), opts.cleanAnswer,
      'on the REAL source the new bound gives ' + opts.predicate(clean)
      + ', expected ' + opts.cleanAnswer);

    pass++;
    console.log('  ok - ' + name
      + '\n        old bound said ' + oldSays + ' (wrong), new bound says '
      + newSays + ', real source still ' + opts.cleanAnswer);
  } catch (e) {
    fail++;
    console.log('  FAIL - ' + name + '\n        ' + e.message);
  }
}

console.log('SPAN CONTROL -- five repointed arms, each shown to change the answer\n');

// ── 1. sairnlegacy shareProcessionLocation: `start + 1200` over 923 bytes ──
// POSITIVE assertion + LONG span = false green. Plant the sensor call just
// after the function's close; the old window reaches it, the new one does not.
arm('tests/sairnlegacy_processions_isolation.js -- the GPS sensor call', {
  file: 'sairnlegacy.html',
  signature: 'function shareProcessionLocation',
  oldBound: (s, start) => start + 1200,
  // NOTE THE /g AND THE NON-PREFIX REPLACEMENT. The first draft used
  // String.replace with a STRING (first occurrence only) and renamed to a
  // token the predicate still matched as a prefix -- both arms came back NOT
  // PROVEN, which is the control reporting that it had not separated the two
  // bounds rather than quietly counting itself as evidence.
  plant: (s) => plantAfter(
    s.replace(/navigator\.geolocation\.getCurrentPosition/g, 'navigator.geolocation.getXXX'),
    'function shareProcessionLocation',
    '\n/* planted outside the function */ navigator.geolocation.getCurrentPosition(0);\n'),
  predicate: (b) => /navigator\.geolocation\.getCurrentPosition\(/.test(b),
  wrongAnswerIsTrue: true,
  cleanAnswer: true,
});

// ── 2. sairnlegacy rProcession: `start + 1400` over 1118 bytes ─────────────
arm('tests/sairnlegacy_processions_isolation.js -- the Maps link', {
  file: 'sairnlegacy.html',
  signature: 'function rProcession',
  oldBound: (s, start) => start + 1400,
  plant: (s) => plantAfter(
    s.replace(/maps\?q=/g, 'mapsREMOVED?q='),
    'function rProcession',
    "\n/* planted outside the function */ var x = 'maps?q=';\n"),
  predicate: (b) => /maps\?q=/.test(b),
  wrongAnswerIsTrue: true,
  cleanAnswer: true,
});

// ── 3. sairnvet scribePreflight: bounded by the NEXT symbol, 80 bytes past ─
arm('tests/sairnvet_scribe_review_probe.js -- C0 rule transcription', {
  file: 'sairnvet.html',
  signature: 'function scribePreflight()',
  oldBound: (s, start) => s.indexOf('window.scribeAsk = function'),
  plant: (s) => plantAfter(
    s.replace("if(code === 'CONSENT_REF_REQUIRED'){", "if(code === 'CONSENT_REF_REQUIRED_RENAMED'){"),
    'function scribePreflight()',
    "\n/* planted outside */ if(code === 'CONSENT_REF_REQUIRED'){}\n"),
  predicate: (b) => b.indexOf("if(code === 'CONSENT_REF_REQUIRED'){") !== -1,
  wrongAnswerIsTrue: true,
  cleanAnswer: true,
});

// ── 4. stonedesk sdHydrateStore: `start + 200` over 96 bytes ───────────────
// ROUTED, NOT APPLIED. hank holds stonedesk under an active claim (2026-10-06
// 06:55Z, FILES includes stonedesk.html) and sairn_claim.py BLOCKS on
// "same app: stonedesk". tests/stonedesk_server_backup.js is therefore
// UNCHANGED at HEAD -- this arm documents a hole that is still open, with the
// one-line repoint it needs, rather than claiming a fix that did not land.
arm('tests/stonedesk_server_backup.js -- the hydrate seam suppresses [HOLE STILL OPEN, ROUTED TO hank]', {
  file: 'stonedesk.html',
  signature: 'function sdHydrateStore(',
  oldBound: (s, start) => start + 200,
  plant: (s) => {
    const sp = fnSpan(s, 'function sdHydrateStore(');
    const gutted = s.slice(0, sp.start)
      + sp.body.replace(/sdWhileSuppressed/g, 'sdXXSuppressed')
      + s.slice(sp.end);
    return plantAfter(gutted, 'function sdHydrateStore(',
      '\n/* planted outside */ sdWhileSuppressed;\n');
  },
  predicate: (b) => b.indexOf('sdWhileSuppressed') !== -1,
  wrongAnswerIsTrue: true,
  cleanAnswer: true,
});

// ── 5. sairnvet calculateDoseAI: `start + 4000` over 9,895 bytes ───────────
// NEGATIVE assertion + SHORT span = false green, the other silent direction.
// Plant a refusal at the END of the function: the old 4000-byte window never
// reaches it and reports ABSENT; the full body finds it.
arm('tests/sairnvet_formulary_source_honesty.js -- no refusal on a copied dose', {
  file: 'sairnvet.html',
  signature: 'function calculateDoseAI',
  oldBound: (s, start) => start + 4000,
  plant: (s) => plantAtEnd(s, 'function calculateDoseAI',
    '\n/* planted past byte 4000 */ if (svCopiedDoseIndex[k]) { return; }\n'),
  predicate: (b) => /svCopiedDoseIndex[\s\S]{0,400}?(return;|blocked|refuse)/i.test(b),
  wrongAnswerIsTrue: false,     // the old window wrongly says "no refusal here"
  cleanAnswer: false,
});

// ── 6. sairnscape scpInit: `start + 900` over 726 bytes (2026-10-06) ──────
// The ONE real silent-direction disagreement in the 2026-10-06 re-measurement
// of all 26 span sites. The 174-byte overrun lands in a comment block that
// names sync functions -- "// Read-through sync -- same honest-degrade
// behavior as SAIRNgrounds' // grdSyncFromServer(): ..." -- so a removed call
// plus a comment mentioning it would have kept this arm green.
arm('api/sd-data-scp-session-gate.test.js -- scpInit calls scpSyncFromServer', {
  file: 'sairnscape.html',
  signature: 'function scpInit(){',
  oldBound: (s, start) => start + 900,
  plant: (s) => plantAfter(
    s.replace(/scpSyncFromServer\(\);/g, 'scpSyncFromServerXX();'),
    'function scpInit(){',
    '\n// planted outside: scpSyncFromServer();\n'),
  predicate: (b) => /scpSyncFromServer\(\);/.test(b),
  wrongAnswerIsTrue: true,
  cleanAnswer: true,
});

console.log('\n' + pass + ' proven, ' + notProven + ' NOT PROVEN, ' + fail + ' failed');
process.exit(fail || notProven ? 1 : 0);
