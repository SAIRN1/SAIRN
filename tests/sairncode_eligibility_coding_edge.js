// tests/sairncode_eligibility_coding_edge.js
//
// Run:  node tests/sairncode_eligibility_coding_edge.js
//
// ── WHAT A2 WAS MISSING ────────────────────────────────────────────────────
// `panel-eligibility` and `sc_eligibility` shipped and worked. Nothing read a
// payer's answer back into the coding queue, so a payer could answer "Inactive"
// on Monday and a coder could clear the same encounter on Tuesday with nothing
// connecting the two -- the only thing joining them, `encounter_ref`, was never
// read across. The competitive-gap audit recorded it as "A2 IS HALF BUILT".
//
// ── THE LINE THIS EDGE MUST NOT CROSS, AND WHY THE ARMS ARE SHAPED LIKE THIS ─
// scDeriveCodedItemConfidence's own comment says its signals are safe to ship
// precisely because none asserts a coding fact this app invented, "and a
// hardcoded NCCI table would not be". A CPT-to-service-type-code mapping would
// be exactly that table. So the edge escalates on two things only:
//
//   D1  the payer said something unambiguously negative -- QUOTED, not
//       paraphrased. The term list is the X12 271 EB01 non-active benefit
//       statuses, not a vocabulary invented here.
//   D2  two checks on one encounter DISAGREE. No vocabulary at all: a fact
//       about the practice's own recorded data, the same shape as the existing
//       signal that counts prior human rejections.
//
// EVERY OTHER SHAPE IS SILENT, and the arms below drive that as hard as they
// drive the positives -- an "Active" answer, an unrecognised status, a
// different encounter, and no check at all. A gate that escalated every
// unchecked encounter would hold the whole queue, which is the
// fail-closed-in-the-wrong-direction mistake this app already records against
// the DMEPOS seven-element gate.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(ROOT, 'sairncode.html'), 'utf8');

let n = 0, failed = 0;
function ok(cond, name) {
  n += 1;
  console.log((cond ? '  ok   ' : '  FAIL ') + name);
  if (!cond) failed += 1;
}
function section(t) { console.log('\n' + t); }

function grab(sig) {
  const start = html.indexOf(sig);
  assert.ok(start > 0, 'not found in sairncode.html: ' + sig);
  let i = html.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < html.length; i++) {
    const c = html[i], p = html[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && html[i + 1] === '/') { i = html.indexOf('\n', i); continue; }
    if (c === '/' && html[i + 1] === '*') { i = html.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return html.slice(start, i + 1); }
  }
  throw new Error('unterminated: ' + sig);
}

console.log('SAIRNcode A2: an eligibility answer reaches the coding queue\n');

// THE REAL CODE, extracted. getEligibilityEntries is stubbed because it reads
// localStorage -- everything else is the shipped implementation.
const ctx = { ELIG: [] };
ctx.getEligibilityEntries = () => ctx.ELIG;
vm.createContext(ctx);
vm.runInContext(html.match(/var SC_ELIG_NEGATIVE_TERMS = \[[\s\S]*?\];/)[0], ctx);
vm.runInContext(grab('function scEligibilityChecksFor(encounterRef) {'), ctx);
vm.runInContext(grab('function scEligibilityConcerns(item) {'), ctx);

const concerns = (item) => ctx.scEligibilityConcerns(item);
const rec = (o) => Object.assign(
  { patient: 'A', payer: 'P1', status: 'Active Coverage', plan: 'PPO',
    encounter_ref: 'ENC-1', service_types: [], checked_for: '',
    date: '2026-09-20' }, o);

section('0. the fixture is the shipped code, and the term list came with it');
{
  ok(Array.isArray(ctx.SC_ELIG_NEGATIVE_TERMS)
     && ctx.SC_ELIG_NEGATIVE_TERMS.length >= 5,
     'SC_ELIG_NEGATIVE_TERMS was extracted from the file -- '
     + (ctx.SC_ELIG_NEGATIVE_TERMS || []).length + ' term(s)');
  ok(ctx.SC_ELIG_NEGATIVE_TERMS.every((t) => t === t.toLowerCase()),
     'every term is lower case, because the comparison lower-cases the payer '
     + 'status -- a capitalised term here would never match anything');
}

section('1. D1 -- a negative payer answer escalates, and is QUOTED');
{
  ctx.ELIG = [rec({ status: 'Inactive' })];
  const c = concerns({ encounter_ref: 'ENC-1' });
  ok(c.length === 1, 'one negative check -> one concern, got ' + c.length);
  ok(c.length === 1 && c[0].indexOf('"Inactive"') !== -1,
     '...and it quotes the payer verbatim: ' + (c[0] || '').slice(0, 70));
  ok(c.length === 1 && /payer's own wording/.test(c[0]),
     '...and says so explicitly, so nobody reads it as this app\'s verdict');
  ok(c.length === 1 && c[0].indexOf('2026-09-20') !== -1,
     '...and carries the date of the check, because an eligibility answer is '
     + 'a point-in-time fact');
}

section('2. ...for each of the real X12 non-active states, case-insensitively');
{
  for (const status of ['Inactive', 'INACTIVE - Pending Investigation',
                        'Non-Covered', 'not covered', 'Terminated',
                        'Ineligible', 'Cannot Process']) {
    ctx.ELIG = [rec({ status })];
    ok(concerns({ encounter_ref: 'ENC-1' }).length >= 1,
       '"' + status + '" escalates');
  }
}

section('3. THE OTHER DIRECTION -- everything else is silent');
{
  for (const status of ['Active Coverage', 'Active', 'Co-Insurance',
                        'Deductible', '1']) {
    ctx.ELIG = [rec({ status })];
    ok(concerns({ encounter_ref: 'ENC-1' }).length === 0,
       '"' + status + '" does NOT escalate');
  }
  // AN UNRECOGNISED STATUS IS SILENT, deliberately. Escalating on "anything
  // not on the active list" would be this app inventing a verdict out of a
  // payer string it does not understand.
  ctx.ELIG = [rec({ status: 'Some status nobody has seen before' })];
  ok(concerns({ encounter_ref: 'ENC-1' }).length === 0,
     'an unrecognised status is silent rather than escalated -- "we do not '
     + 'understand this" is not evidence of non-coverage');
}

section('4. NO CHECK AT ALL IS SILENT, and that is the deliberate departure');
{
  ctx.ELIG = [];
  ok(concerns({ encounter_ref: 'ENC-1' }).length === 0,
     'an encounter with no eligibility check escalates nothing');
  ctx.ELIG = [rec({ status: 'Inactive', encounter_ref: 'ENC-OTHER' })];
  ok(concerns({ encounter_ref: 'ENC-1' }).length === 0,
     'a negative check on a DIFFERENT encounter does not leak across');
  ctx.ELIG = [rec({ status: 'Inactive', encounter_ref: '' })];
  ok(concerns({ encounter_ref: '' }).length === 0,
     'an item with no encounter_ref matches nothing -- an empty key must not '
     + 'join to every unreferenced check');
}

section('5. D2 -- two checks on one encounter that disagree');
{
  ctx.ELIG = [rec({ status: 'Active Coverage' }),
              rec({ status: 'Inactive', date: '2026-09-22' })];
  const c = concerns({ encounter_ref: 'ENC-1' });
  ok(c.some((x) => /do not agree/.test(x)),
     'the disagreement is reported: ' + (c.find((x) => /do not agree/.test(x)) || '').slice(0, 80));
  ok(c.some((x) => /nothing here can say which/.test(x)),
     '...and it does NOT pick a winner, because it cannot');
  // The negative one still escalates on its own account -- two signals, two
  // concerns, not one collapsed message.
  ok(c.length === 2, 'both signals fire independently, got ' + c.length);
}

section('6. ...and two AGREEING checks are not a disagreement');
{
  ctx.ELIG = [rec({ status: 'Active Coverage' }),
              rec({ status: 'Active Coverage', date: '2026-09-22' })];
  ok(concerns({ encounter_ref: 'ENC-1' }).length === 0,
     'two identical active answers escalate nothing');
  // ...including when one is blank, which is an absent answer and not a
  // second opinion.
  ctx.ELIG = [rec({ status: 'Active Coverage' }), rec({ status: '' })];
  ok(concerns({ encounter_ref: 'ENC-1' }).length === 0,
     'a blank status is not counted as a disagreeing second answer');
}

// ── 7. IT IS ACTUALLY WIRED ───────────────────────────────────────────────
// A signal nothing calls is worse than no signal: it reads as covered.
section('7. scDeriveCodedItemConfidence consumes it');
{
  const body = grab('function scDeriveCodedItemConfidence(item, context){');
  ok(/scEligibilityConcerns/.test(body),
     'scDeriveCodedItemConfidence calls scEligibilityConcerns');
  ok(/basis\.push\(eligBasis\[e\]\)/.test(body),
     '...and pushes each concern into `basis`, which is what turns an item '
     + 'into needs_human_review');
  ok(/typeof scEligibilityConcerns === 'function'/.test(body),
     '...guarded, the same way the credential gate is, so a load-order change '
     + 'degrades to silence rather than throwing inside the review path');
}

// ── 8. THE NEGATIVE CONTROL -- no file is written ─────────────────────────
section('8. NEGATIVE CONTROL -- each arm fails when the edge is broken');
{
  const SRC = grab('function scEligibilityConcerns(item) {');
  const fresh = (src) => {
    const c2 = { ELIG: ctx.ELIG };
    c2.getEligibilityEntries = () => c2.ELIG;
    vm.createContext(c2);
    vm.runInContext(html.match(/var SC_ELIG_NEGATIVE_TERMS = \[[\s\S]*?\];/)[0], c2);
    vm.runInContext(grab('function scEligibilityChecksFor(encounterRef) {'), c2);
    vm.runInContext(src, c2);
    return c2;
  };
  const MUT = [
    ['D1 is deleted', "                        out.push('The payer answered \"'",
     "                        if (false) out.push('The payer answered \"'",
     (c2) => { c2.ELIG = [rec({ status: 'Inactive' })];
               return c2.scEligibilityConcerns({ encounter_ref: 'ENC-1' }).length === 0; }],
    ['D2 is deleted', '            if (distinct.length > 1) {',
     '            if (false) {',
     (c2) => { c2.ELIG = [rec({ status: 'Active Coverage' }),
                          rec({ status: 'Co-Insurance' })];
               return c2.scEligibilityConcerns({ encounter_ref: 'ENC-1' })
                        .every((x) => !/do not agree/.test(x)); }],
    ['an ABSENT check starts escalating -- the direction that holds the queue',
     '            if (!checks.length) return out;',
     "            if (!checks.length) { out.push('no check'); return out; }",
     (c2) => { c2.ELIG = [];
               return c2.scEligibilityConcerns({ encounter_ref: 'ENC-1' }).length > 0; }],
  ];
  for (const [label, find, replace, broke] of MUT) {
    const hits = SRC.split(find).length - 1;
    ok(hits === 1, '[' + label + '] the anchor matches EXACTLY once (' + hits + ')');
    if (hits !== 1) continue;
    const mutated = SRC.replace(find, replace);
    ok(mutated !== SRC, '...and the mutation changed the source');
    let c2 = null, why = '';
    try { c2 = fresh(mutated); } catch (e) { why = String(e && e.message); }
    ok(!!c2, '...and it still PARSES: ' + why);
    if (c2) ok(broke(c2), '...and the behaviour above NOTICES it');
  }
  const clean = fresh(SRC);
  clean.ELIG = [rec({ status: 'Active Coverage' })];
  ok(clean.scEligibilityConcerns({ encounter_ref: 'ENC-1' }).length === 0,
     'CONTROL: the UNMUTATED source through the same path is silent on an '
     + 'active answer -- otherwise every mutation above reads as caught for '
     + 'the wrong reason');
}

console.log('\n' + (failed
  ? failed + ' OF ' + n + ' ASSERTIONS FAILED'
  : 'ALL ' + n + ' ASSERTIONS PASS'));
process.exit(failed ? 1 : 0);
