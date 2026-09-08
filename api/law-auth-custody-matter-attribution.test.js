// api/law-auth-custody-matter-attribution.test.js
// Run: node api/law-auth-custody-matter-attribution.test.js
//
// THE AI CHAIN OF CUSTODY LOG TOOK ITS MATTER LINK ON TRUST, and it was the
// only field in that handler that did.
//
// `ai_generate` in api/law-auth.js is careful about everything else, with its
// own comments saying why:
//
//   * `prompt` is derived from the REAL messages array rather than
//     body.prompt_for_log -- "a client could otherwise send a genuine question
//     in `messages` and a different prompt_for_log";
//   * `tools_used` is derived from the REAL assistant turns rather than
//     body.tools_used -- "no reason to trust client-asserted metadata about
//     which tools were actually used".
//
// And then: `const matter_id = body.matter_id ? String(body.matter_id) : 'general'`.
// Verbatim from the body, into a log whose own panel says "Every AI
// interaction, matter-linked and logged server-side... Nothing here can be
// edited or deleted." MIS-ATTRIBUTION is the failure that matters in a record
// like that: an interaction filed against the wrong matter, or one that never
// existed, is invisible to the matter it actually concerned.
//
// ══ WHY IT VERIFIES RATHER THAN REJECTS, AND WHY THAT IS THREE STATES ═════
// law_matters syncs to the server, but a matter created on a device that has
// not hydrated is genuinely absent from it. So "not found" CANNOT distinguish
// a fabricated id from a real matter the server has not seen yet. Rejecting
// would break the chat for the second case; coercing to 'general' would
// destroy its attribution. The record therefore keeps the claimed id AND
// records whether the server could confirm it:
//
//   true      -- confirmed against law_matters for this licence
//   false     -- this licence has no such matter (NOT proof of fabrication)
//   null      -- the lookup itself failed; "could not check" is a third answer
//                and must not be written down as "checked and false"
//   undefined -- the record predates the check entirely
//
// Every assertion below exists to keep those four apart. Flattening them is
// how a disclosure becomes an accusation.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

const RAW = fs.readFileSync(path.join(__dirname, 'law-auth.js'), 'utf8').replace(/\r\n/g, '\n');
// Comments stripped before any shape scan: the fix's own header quotes the old
// expression to explain what it replaced, and a file-wide match hits the
// explanation. The same trap has now caught four separate checks on this
// platform, so it is stripped by default rather than discovered again.
const CODE = RAW.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');
const HTML_CODE = HTML.split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n');

function main() {
  console.log('SAIRNlaw AI Chain of Custody: the matter link is checked, and the check is disclosed');

  test('the matter is looked up against law_matters, scoped to this licence', () => {
    assert.match(CODE, /rest\('law_matters\?license_hash=eq\.' \+ enc\(licHash\)/,
      'no licence-scoped law_matters lookup in ai_generate');
    assert.match(CODE, /matter_id=eq\.' \+ enc\(matter_id\)/,
      'the lookup does not filter on the claimed matter_id');
  });

  test('THE LOOKUP IS LICENCE-SCOPED -- a matter belonging to another firm must not confirm', () => {
    // The whole point of the check. An unscoped lookup would confirm any
    // matter id that exists anywhere on the platform, which is worse than not
    // checking: it would stamp a cross-tenant id as verified.
    // The whole rest(...) argument, not `[^)]*` -- that stops at the first
    // close-paren, which is inside enc(licHash), and the assertion then
    // inspects a fragment instead of the query. Caught by this test failing
    // on correct code, which is the cheap direction for that mistake.
    const i = CODE.indexOf("rest('law_matters?");
    assert.ok(i > 0, 'could not find the lookup to inspect');
    const q = CODE.slice(i, CODE.indexOf('), { headers })', i));
    assert.ok(q.indexOf('license_hash=eq.') !== -1, 'the lookup is not licence-scoped');
    assert.ok(q.indexOf('license_hash=eq.') < q.indexOf('matter_id=eq.'),
      'licence scope must be part of the same query, not applied after');
  });

  test("'general' is not looked up at all -- it is not a matter", () => {
    assert.match(CODE, /if \(matter_id !== 'general'\) \{/,
      "the check does not exempt 'general', so every general chat hits the database");
  });

  test('a FAILED lookup leaves the verdict null, never false', () => {
    // "Could not check" written down as "checked and false" would accuse a
    // real matter of being fabricated, on the strength of a network blip.
    // From the DECLARATION, not from the `if` -- the initialiser is what makes
    // "could not check" distinguishable, and slicing below it hid the very
    // line under test.
    const block = CODE.slice(CODE.indexOf('let matter_verified'),
                             CODE.indexOf('const tools_used'));
    assert.match(block, /let matter_verified = null;|matter_verified = null/,
      'the verdict does not start null');
    assert.match(block, /if \(mr\.ok\)/, 'a non-ok response is not distinguished');
    assert.ok(!/catch \(e\) \{\s*matter_verified = false/.test(block),
      'a thrown lookup is recorded as a failed verification');
  });

  test('the verdict is written into the custody record itself', () => {
    assert.match(CODE, /detail: \{ prompt, response, matter_id, matter_verified, tools_used \}/,
      'matter_verified is computed and then not stored');
  });

  test('...and ai_list hands it back, so a reviewer can see it', () => {
    assert.match(CODE, /matter_verified: e\.detail \? e\.detail\.matter_verified : undefined/,
      'the projection drops the verdict, so the check is invisible to the panel');
  });

  test('an OLD record with no such field stays undefined, not false', () => {
    // Every record written before this change carries no matter_verified at
    // all. `e.detail.matter_verified` on those is undefined, and the
    // projection must pass that through rather than defaulting it.
    const proj = CODE.match(/matter_verified: [^\n,]+/)[0];
    assert.ok(!/\|\|\s*false/.test(proj) && !/!!/.test(proj),
      'the projection coerces a missing field into a verdict: ' + proj);
  });

  test('the panel renders THREE outcomes and warns on only one', () => {
    assert.match(HTML_CODE, /e\.matter_verified===false/, 'the panel does not surface an unconfirmed matter');
    assert.match(HTML_CODE, /matter UNCONFIRMED/, 'there is no visible marker for the reviewer');
    assert.match(HTML_CODE, /e\.matter_verified===undefined\|\|e\.matter_verified===null/,
      'a not-checked record is not distinguished from a failed one');
    assert.match(HTML_CODE, /attribution not checked/,
      'a pre-change record has no distinct label');
  });

  test('the warning does NOT call an unconfirmed matter fabricated', () => {
    // A matter created on a device that has not hydrated is genuinely absent
    // from the server. Wording that asserts fraud would be wrong in exactly
    // the common case.
    const i = HTML_CODE.indexOf('matter UNCONFIRMED');
    const around = HTML_CODE.slice(i - 400, i + 500);
    assert.match(around, /has not synced|never real/,
      'the tooltip does not offer both readings');
    assert.ok(!/fabricated|forged|falsified/i.test(around.replace(/never real/g, '')),
      'the panel accuses rather than reports');
  });

  test("'general' shows no marker at all", () => {
    assert.match(HTML_CODE, /if\(e\.matter_id!=='general'\)\{/,
      "a general chat would carry an attribution marker it cannot have");
  });

  test('the unvalidated assignment is gone from the source', () => {
    // Whitespace-normalised: three separate assertions on this platform have
    // now gone vacuous on a reformatted copy of the thing they name.
    const squashed = CODE.replace(/\s+/g, '');
    assert.ok(!/constmatter_id=body\.matter_id\?String\(body\.matter_id\):'general';constlogged/.test(squashed),
      'the record is written straight from the body again, with no check between');
  });
}

main();
console.log(process.exitCode ? 'FAILED' : 'ALL ' + passed + ' CUSTODY-ATTRIBUTION ASSERTIONS PASS');
