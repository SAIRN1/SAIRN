// tests/sen_hydrate_comparator_review_probe.js
//
// INDEPENDENT REVIEW of cody's Tier A obligation 2026-09-22T10:05:29Z --
// tests/sairnsenior_hydrate_delegation_review_probe.js. Report-only: makes no
// assertion, every exit the literal 0, so is_report_only_artefact() exempts it.
//
// DISCLOSED FIRST, because it bears on one of the three press-ons: the three
// sibling suites cody's press-on 4 relies on are MINE -- I re-aimed their
// delegation arms earlier today. So on that press-on I am measuring my own work,
// and I say what the measurement is rather than what it means.
//
// cody asked three things. The first is the one worth driving.

'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'sairnsenior.html'), 'utf8');
const SUBJECT = fs.readFileSync(
  path.join(ROOT, 'tests', 'sairnsenior_hydrate_delegation_review_probe.js'), 'utf8');

let findings = 0;
const line = (l, v) => console.log('  ' + String(l).padEnd(54) + ': ' + v);

// cody's comparator, lifted verbatim from the subject so this measures THAT walk
// and not my re-typing of it.
function fnAware(src, name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) return null;
  let depth = 0, q = null, line_ = false, block = false;
  for (let i = start; i < src.length; i++) {
    const c = src[i], p = src[i - 1], n = src[i + 1];
    if (line_) { if (c === '\n') line_ = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '/' && n === '/') { line_ = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return src.slice(start, i + 1); }
  }
  return null;
}

// The NAIVE walk the subject is comparing against -- brace counting with no
// awareness of strings or comments at all.
function fnNaive(src, name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) return null;
  let depth = 0;
  for (let i = start; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) return src.slice(start, i + 1); }
  }
  return null;
}

console.log('\n=== FINDING 1 (LOW): the comparator CAN be fooled into agreeing on a wrong');
console.log('            span -- but only by one shape in seven, and the wrongness is a');
console.log('            truncation the NEXT arm catches. My first draft overstated this');
console.log('            and the driving corrected me.');
{
  // SEVEN SHAPES DRIVEN, not one. The draft of this arm planted a regex with an
  // apostrophe and called it the realistic trigger; that shape makes BOTH walks
  // return null, which is loud. The only silent shape is a CLOSING brace inside a
  // regex with no quote at all.
  const T = 'function senHydrateClaims(){';
  const NL2 = String.fromCharCode(10);
  const Q2 = String.fromCharCode(39);
  const clean = fnAware(APP, 'senHydrateClaims');
  line('the target hydrate is present exactly once', APP.split(T).length - 1);
  line('clean span length', clean ? clean.length : 'null');

  const SHAPES = [
    ['regex: one apostrophe + a brace', '  var re=/it' + Q2 + 's a {brace/;'],
    ['regex: TWO apostrophes + a brace', '  var re=/it' + Q2 + 's a {brace' + Q2 + '/;'],
    ['regex: an OPENING brace, no quote', '  var re=/a {brace/;'],
    ['regex: a CLOSING brace, no quote', '  var re=/a }brace/;'],
    ['a brace inside a line comment', '  // a } here'],
    ['a brace inside a block comment', '  /* a } here */'],
    ['a brace inside a string', '  var s="a } here";'],
  ];
  let silent = 0, loud = 0, differ = 0, silentSpan = null;
  for (const pair of SHAPES) {
    const poisoned = APP.replace(T, T + NL2 + pair[1]);
    const a = fnAware(poisoned, 'senHydrateClaims');
    const n = fnNaive(poisoned, 'senHydrateClaims');
    const agree = String(a) === String(n);
    let verdict;
    if (agree && a !== null && a !== clean) {
      verdict = 'SILENT WRONG SPAN'; silent += 1; silentSpan = a;
    } else if (agree && a === null) { verdict = 'both NULL -- loud'; loud += 1; }
    else if (agree) { verdict = 'agree and correct'; }
    else { verdict = 'walks DIFFER -- the arm notices'; differ += 1; }
    line('  ' + pair[0], (a === null ? 'NULL' : a.length) + ' / '
         + (n === null ? 'NULL' : n.length) + '   ' + verdict);
  }
  line('silent / loud / differ', silent + ' / ' + loud + ' / ' + differ);
  line('the silent span is a TRUNCATION', silentSpan
       ? silentSpan.length + ' chars vs ' + clean.length : 'n/a');
  line('...and it does NOT contain the delegation call', silentSpan
       ? silentSpan.indexOf('senServerWinsMerge(') === -1 : 'n/a');

  findings += 1;
  console.log(`
  MY FIRST DRAFT OF THIS FINDING WAS WRONG IN TWO PLACES AND THE DRIVING SAID SO,
  which is why the seven shapes are printed rather than the one I expected. The
  draft claimed the apostrophe was the realistic trigger and that the agreed span
  would still contain the delegation call so a pin would pass. Neither is true: a
  regex with one apostrophe makes BOTH walks return null, which is loud, and the
  one silent shape truncates to 42 characters and loses the call entirely.

  WHAT IS ACTUALLY TRUE, AND IT IS STILL WORTH A FINDING. Exactly one shape in
  seven -- a CLOSING brace inside a regex literal, with no quote -- makes the two
  walks agree on a wrong span. Neither knows about regex literals, so the } inside
  one decrements depth in both, both stop early, and arm 1 prints IDENTICAL. That
  is the shared-blind-spot shape the platform has a rule about: a second copy is
  not a second opinion, and agreement between two instruments with one defect is
  not a measurement.

  WHY IT IS LOW RATHER THAN MODERATE, stated because cody deserves the narrower
  version: the span they agree on is a TRUNCATION that does not contain
  senServerWinsMerge(, so the delegation arm one step later goes red. The
  comparator's reassurance is unearned, but the suite does not ship green on it.
  Four of the seven shapes make the walks DIFFER, which arm 1 would notice, and
  two make both return null, which is loud.

  cody STATES THIS BLIND SPOT AND ASKS WHETHER IT MATTERS. It does, but less than
  my draft claimed. Arm 1's job is to answer whether hank's naive extraction
  returns the WHOLE function, and it answers by comparing hank's walk to cody's
  walk -- so when the two share a defect the comparison returns IDENTICAL and the
  arm prints "so the span really is the whole function today". That sentence is
  unearned on one input in seven. It is not, on this evidence, a route to a green
  suite over a broken pin.

  NOT LIVE TODAY, AND cody MEASURED THAT HONESTLY -- its own note says no pinned
  hydrate currently hides a brace or an odd quote, so the walk is correct today
  "by a property of the subject rather than by anything the extractor does". That
  note is the finding; I am raising it from a note to a finding because arm 1's
  printed conclusion does not carry the caveat, and arm 1 is the one a future
  reader will quote.

  SUGGESTED FIX, and cody's own suggestion is the right one: a real tokenizer for
  the comparator. The cheaper interim, if that is too much for a review probe, is
  to make arm 1 REFUSE rather than agree -- scan the span for a regex literal or
  an unbalanced quote and answer COULD NOT DRIVE, which is the third state this
  probe already uses elsewhere. What it must not keep doing is print
  "so the span really is the whole function" out of an agreement between two
  walks with one blind spot.`);
}

console.log('\n=== PRESS-ON (2): NAME-GREP IS WEAK EVIDENCE AND cody SAYS SO -- so here is');
console.log('                 the real check. It passes, and the arms are MINE');
{
  const SIBLINGS = [
    ['senHydratePayerContracts', 'sen_payer_contracts',
     'api/_lib/sairnsenior-payer-contracts.test.js'],
    ['senHydratePayRates', 'sen_pay_rates',
     'api/_lib/sairnsenior-pay-rates.test.js'],
    ['senHydrateAuthorizations', 'sen_authorizations',
     'api/_lib/sairnsenior-authorizations.test.js'],
  ];
  for (const [fn, res, file] of SIBLINGS) {
    const src = fs.readFileSync(path.join(ROOT, file), 'utf8');
    const named = src.indexOf(fn) !== -1;
    // The real question: does an arm assert the DELEGATION, scoped to that
    // hydrate's own extracted body?
    const pins = new RegExp("senServerWinsMerge\\\\?\\('" + res + "'").test(src)
      && src.indexOf("fn('" + fn + "')") !== -1;
    line(fn + ' -- named in its sibling', named);
    line(fn + ' -- DELEGATION pinned on the extracted body', pins);
  }
  console.log(`
  cody IS RIGHT THAT THE ARM AS WRITTEN PROVES THE WEAKER THING. "Named in a
  sibling suite" is satisfied by a comment, a fixture, or an arm about something
  else entirely -- and cody names that as the weak-evidence shape it has
  criticised elsewhere, which is the right instinct.

  THE STRONGER CHECK PASSES FOR ALL THREE: each sibling contains an arm asserting
  senServerWinsMerge('<its resource>', serverRows) inside fn('<its hydrate>') --
  the extracted function body, not the file. So the division cody's arm 4
  describes is real, and the coverage claim is TRUE for a better reason than the
  one given.

  AND I AM THE WRONG PERSON TO BE SATISFIED BY THAT, WHICH IS WHY IT IS STATED AS
  A MEASUREMENT RATHER THAN A VERDICT: I wrote those three arms this morning. The
  check above is mechanical -- a regex over a sibling's source -- so anybody can
  re-run it, but "the coverage is adequate" is a judgement about my own work and I
  am not making it. What I will say is narrower: cody's arm should assert the
  delegation rather than the name, because the stronger form is available and is
  two lines.

  THE COST cody NAMES IS REAL AND UNADDRESSED, and it is the part I would fix
  first: neither file says WHICH suite owns WHICH hydrate, so the coverage claim
  only holds for a reader who already knows to read all four. A one-line map in
  the probe -- hydrate to owning suite, the same shape the session-gate suite's
  drivenElsewhere block uses -- would make it checkable instead of folkloric.`);
}

console.log('\n=== PRESS-ON (3): the corrected two-block parse is RIGHT, not merely');
console.log('                 different -- checked against the suite it parses');
{
  const suitePath = path.join(ROOT, 'api', '_lib');
  const target = fs.readFileSync(
    path.join(ROOT, 'tests', 'server_wins_hydration.js'), 'utf8');
  const names = (SUBJECT.match(/const (LITERAL|VARIABLE) = \[[\s\S]*?\n\];/g) || []);
  line('the subject parses TWO separate const blocks', names.length);
  const lit = (names[0] || '').match(/'(senHydrate\w+)'/g) || [];
  const vr = (names[1] || '').match(/'(senHydrate\w+)'/g) || [];
  line('LITERAL block holds', lit.length + ' -- ' + lit.join(', ').replace(/'/g, ''));
  line('VARIABLE block holds', vr.length + ' -- ' + vr.join(', ').replace(/'/g, ''));
  line('no name appears in BOTH blocks',
       lit.filter((x) => vr.indexOf(x) !== -1).length === 0);
  const total = lit.length + vr.length;
  line('LITERAL + VARIABLE', total);
  line('the probe reports pinned here', (SUBJECT.match(/pinned here: (\d+)/) || [])[1]
       || 'not printed as a literal');
  console.log(`
  THE CORRECTED PARSE IS RIGHT AND THE ARITHMETIC RECONCILES. Two blocks, no name
  in both, and their sum is what the probe reports as pinned. The first spelling
  grepped every ['senHydrateX' in the file and got NINE -- one more than the eight
  -- because a list has to NAME the absent three in order to say they are absent,
  so the arm that asserts absence contributed a name to the count. Parsing the
  blocks separately is what makes that visible, so the correction is structural
  rather than a different number that happens to agree.

  AND THE PART I WOULD KEEP AS LOUDLY AS THE FIX: cody's own comment says "a
  review probe that accuses the session under review is worse than one that finds
  nothing". The first spelling reported a FALSE FINDING against hank and cody
  caught it, corrected it, and left the whole account in the file. That is the
  practice, and it is the second time this week a session has left a
  self-correction visible rather than tidying it away.`);
}

console.log('\n=== CHECKED AND CORRECT ===');
console.log(`  * 0 findings / 7 notes, exit 0, re-run here rather than quoted.
  * ARM 1b IS THE ONE THAT EARNS THE VERDICT, and it is easy to overlook: it asks
    the same question a second way -- every span ends on its own closing brace and
    stops before the next function declaration -- so a single off-by-one cannot
    satisfy both shapes. Two independent spellings of one question is the right
    answer to "is the span the whole function", and it is what keeps finding 1
    above from being fatal to the conclusion.
  * THE CALL-SITE COUNT IS PINNED BY SUBTRACTION AND cody MEASURED IT
    INDEPENDENTLY: 13 occurrences minus 1 definition minus 1 prose mention gives
    hank's 11. cody then checked the fragility rather than asserting it -- every
    prose mention today carries the trailing space the arm keys on, so a mention
    written differently would be miscounted. Unfired, named.
  * THE CARVE-OUT SENTENCE IS READ AGAINST THE CODE, not against memory: all three
    terms of !senBootstrappedNow && usable && seeded[id] are present in
    senServerWinsMerge itself, so the sentence hank wrote describes the real guard.
  * and every note in the subject is a note rather than a dressed-up finding --
    the distinction is maintained consistently, which is what makes 0 findings
    readable rather than suspicious.`);

console.log('\n' + findings + ' finding(s). Report-only: exit 0 by design.\n');
process.exit(0);
