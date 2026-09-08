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

  test("a FAILED lookup leaves the verdict 'unavailable', never false and never absent", () => {
    // "Could not check" written down as "checked and false" would accuse a
    // real matter of being fabricated, on the strength of a network blip.
    // From the DECLARATION, not from the `if` -- the initialiser is what makes
    // "could not check" distinguishable, and slicing below it hid the very
    // line under test.
    //
    // UPDATED 2026-09-08: the initialiser used to be `null` for BOTH 'general'
    // and a non-general id awaiting its lookup, so one value carried two
    // facts and no consumer outside the panel could tell them apart. A
    // non-general id now starts at 'unavailable'.
    const block = CODE.slice(CODE.indexOf('let matter_verified'),
                             CODE.indexOf('const tools_used'));
    assert.match(block, /let matter_verified = null;/,
      "the 'general' case no longer starts null");
    assert.match(block, /matter_verified = 'unavailable';/,
      'a non-general id does not start at a value meaning "could not check"');
    assert.match(block, /if \(mr\.ok\)/, 'a non-ok response is not distinguished');
    assert.ok(!/catch \(e\) \{\s*matter_verified = false/.test(block),
      'a thrown lookup is recorded as a failed verification');
    assert.ok(!/catch \(e\) \{\s*matter_verified = null/.test(block),
      "a thrown lookup falls back to null, which is the 'general' value");
  });

  test("'unavailable' is separable by anything, not only by the panel", () => {
    // The open question on this row is whether ai_list should let a reviewer
    // FILTER to unconfirmed entries. A filter cannot separate what the record
    // does not: while 'general' and could-not-check shared `null`, the only
    // thing that told them apart was the panel's own `matter_id!=='general'`
    // guard, which no other consumer has.
    const block = CODE.slice(CODE.indexOf('let matter_verified'),
                             CODE.indexOf('const tools_used'));
    const generalValue = /let matter_verified = null;/.test(block);
    const failedValue = /matter_verified = 'unavailable';/.test(block);
    assert.ok(generalValue && failedValue,
      'the two states share a value again, so a filter cannot tell them apart');
    // And the projection must not coerce it on the way out.
    assert.match(CODE, /matter_verified: e\.detail \? e\.detail\.matter_verified : undefined/,
      'ai_list coerces the verdict, so the distinction dies at the API boundary');
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

  test('the panel renders FOUR outcomes and warns on two', () => {
    // CORRECTED 2026-09-08 by the independent review of this change, and this
    // assertion is the reason the defect survived. It PINNED
    //     e.matter_verified===undefined||e.matter_verified===null
    // -- the flattening itself -- under the failure message "a not-checked
    // record is not distinguished from a failed one". The message described
    // the flattening as the defect while the assertion required it, so
    // separating the two states turned the suite RED with a message saying
    // they had not been separated. A test that holds a defect in place and
    // mislabels why is worse than no test for it.
    assert.match(HTML_CODE, /e\.matter_verified===false/, 'the panel does not surface an unconfirmed matter');
    assert.match(HTML_CODE, /matter UNCONFIRMED/, 'there is no visible marker for the reviewer');
    assert.match(HTML_CODE, /e\.matter_verified==='unavailable'\|\|e\.matter_verified===null/,
      'a lookup that FAILED is not distinguished from one that never ran');
    assert.match(HTML_CODE, /attribution CHECK FAILED/,
      'a failed lookup has no distinct label, so it reads as something else');
    assert.match(HTML_CODE, /e\.matter_verified===undefined/,
      'a pre-change record is no longer matched on its own');
    assert.match(HTML_CODE, /attribution not checked/,
      'a pre-change record has no distinct label');
  });

  test('a failed check is never labelled as a record that predates the check', () => {
    // The live defect: an entry logged TODAY whose lookup did not complete was
    // shown "Logged before the server began checking matter attribution
    // (2026-09-05)" -- a specific, false claim about the record's age, in a
    // legal audit trail. Driven on the branch text rather than grepped for a
    // phrase, because the phrase itself is still in the file and correct for
    // the state it now belongs to.
    const squashed = HTML_CODE.replace(/\s+/g, '');
    const failedBranch = squashed.slice(
      squashed.indexOf("e.matter_verified==='unavailable'"),
      squashed.indexOf('e.matter_verified===undefined'));
    assert.ok(failedBranch.length > 0, 'the failed-lookup branch is gone');
    assert.ok(failedBranch.indexOf('Loggedbeforetheserverbegan') === -1,
      'a failed lookup is still described as a record that predates the check');
    assert.match(failedBranch, /couldnotgetananswer|CHECKFAILED/,
      'the failed-lookup branch does not say the check is what failed');
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

  // ── ai_list's completeness claim, added 2026-09-08 ─────────────────────
  // Same log, adjacent defect: the listing's own note claimed something it
  // had not checked.

  test('the note counts INTERACTIONS and names the window separately', () => {
    // It used to read "Showing the N most recent ... events" where N was the
    // interaction count and the query had fetched `limit` rows of FOUR event
    // types -- the number named one thing and the word named another.
    assert.match(CODE, /Showing ' \+ entries\.length \+ ' AI interaction'/,
      'the note does not say what the number actually counts');
    assert.match(CODE, /most recent log events for this licence/,
      'the note does not distinguish the window from the interactions in it');
  });

  test('TRUNCATION IS DETECTED AND SAID OUT LOUD', () => {
    assert.match(CODE, /const truncated = all\.length >= limit;/,
      'a full window is not detected, so a partial log reads as the whole one');
    assert.match(CODE, /THAT WINDOW IS FULL/,
      'a truncated listing does not say older interactions exist');
    assert.match(CODE, /this is not the complete log/,
      'the truncated wording does not deny completeness');
  });

  test('...and a COMPLETE listing says so positively, rather than staying silent', () => {
    // Silence is what the old note effectively was. A reviewer needs to know
    // which of the two they are looking at, not just be warned sometimes.
    assert.match(CODE, /the listing is complete/,
      'a complete listing makes no positive claim, so the two cases look alike');
  });

  test('the raw numbers are returned, so the sentence is checkable', () => {
    assert.match(CODE, /truncated: truncated,/, 'the flag is not exposed to the client');
    assert.match(CODE, /scanned: all\.length,/, 'the window size is not exposed');
    assert.match(CODE, /limit: limit,/, 'the cap is not exposed');
  });

  test('the panel makes a truncated listing LOOK different', () => {
    // Muted grey beside a complete listing is how a partial log gets mistaken
    // for the whole one.
    assert.match(HTML_CODE, /if\(r\.data\.truncated\)\{/,
      'the client ignores the truncation flag');
    assert.match(HTML_CODE, /noteEl\.style\.color='var\(--warn\)'/,
      'a truncated listing renders in the same muted style as a complete one');
    assert.match(HTML_CODE, /noteEl\.style\.color='var\(--muted\)'/,
      'the style is never restored, so one truncated load leaves the panel shouting forever');
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
