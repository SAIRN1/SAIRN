// api/alf-append-only-read-order.test.js
// Run: node api/alf-append-only-read-order.test.js
//
// SIX SAIRNcare APPEND-ONLY TRAIL READS WITH NO `order=` CLAUSE, found
// 2026-09-22.
//
// Postgres promises nothing about the order of a SELECT that does not ask for
// one, and PostgREST forwards that straight through. On a small table a seq
// scan usually returns heap order, so an unordered read LOOKS like insertion
// order for the whole of development and stops looking like it the first time
// the planner picks an index or a reused page moves a row. Correct in dev,
// wrong in production, silent in both -- which is why this is a test and not a
// note in a handoff.
//
// ══ WHAT EACH OF THE SIX ACTUALLY COST, CHECKED NOT ASSUMED ════════════════
// The six do NOT share a severity and flattening them would overstate four of
// them. Read against sairncare.html rather than inferred from the API shape:
//
//   * alf_claim_routes -- WORST. prRenderRecorded maps the rows straight into
//     a table with no client-side sort of any kind, and renders created_at
//     sliced to 10 characters, so the display carries date-only precision. The
//     server order WAS the display order, and there was none.
//
//   * alf_mar and alf_incidents -- the renderers DO sort, but on a date-only
//     field from the jsonb payload (sortByDateDesc, and the incident sort).
//     Array.prototype.sort is stable, so every same-day entry ties and falls
//     back to the order the server sent. A sort that ties is the same defect
//     wearing a sort, and a MAR is a table where same-day is the normal case.
//
//   * alf_staff_credentials and alf_op_audits -- both renderers already sort by
//     created_at descending client-side, so these two were deterministic except
//     on an exact timestamp tie. Ordering them server-side is belt-and-braces,
//     recorded here as the smaller finding it is.
//
//   * alf_signals -- no consumer in sairncare.html at all today. Nothing was
//     being displayed wrongly; the API contract was simply nondeterministic for
//     whatever gets built on it. Named rather than quietly counted with the
//     rest.
//
// ══ WHY SIX AND NOT THE THREE THE WORK WAS HANDED OVER AS ══════════════════
// The handoff named alf_mar, alf_signals and alf_claim_routes. The other three
// trails have the identical defect at the identical call shape. Fixing three
// and shipping an arm called "append-only read order" would have published an
// all-clear over three reads it never looked at -- the exact shape CLAUDE.md
// names as the most common defect on this platform after a silent failure.
//
// ══ WHY DESC ══════════════════════════════════════════════════════════════
// Chosen against the consumer, not by taste: every SAIRNcare renderer that
// sorts this data sorts it newest-first. Server-side desc makes the tie-break
// agree with the direction the reader is already being shown, instead of
// fighting it. The wider file uses asc for supersede chains (rf_proposals,
// rf_photos) where oldest-first is semantically required; none of these six is
// that shape.
//
// alf_signals orders by recorded_at -- when the signal OCCURRED -- not
// created_at. It is the column the read already returns to the caller and the
// only one that means anything to a monitoring log; rf_certifications, the
// structural twin in this same file, orders the same way.
//
// ══ RESIDUAL, STATED RATHER THAN IMPLIED ═══════════════════════════════════
// A single-column order still ties when two rows share the timestamp to the
// microsecond. No read in sd-data.js uses a tiebreaker and this change does not
// introduce the first one. The real exposure is a batch insert inside one
// transaction, where now() is identical across the rows. NOT fixed here, and
// this file does not assert a tiebreaker exists.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

// FAIL CLOSED, NOT SKIP. This arm depends on two files it does not own. If
// either is missing or unreadable the answer is "this check did not run" with
// the filename said out loud -- never a silent pass, and never a pass counted
// alongside the real ones. PR §1.11.
function mustRead(p, why) {
  let src;
  try { src = fs.readFileSync(p, 'utf8'); }
  catch (e) {
    console.error('COULD NOT RUN: ' + p + ' is unreadable (' + e.code + ').');
    console.error('  This arm ' + why + ' and cannot do so without that file.');
    console.error('  This is NOT a pass. Nothing below was checked.');
    process.exit(2);
  }
  return src.replace(/\r\n/g, '\n');
}

const SRC = mustRead(path.join(__dirname, 'sd-data.js'), 'reads the six SAIRNcare trail reads');
// Comment lines stripped before any shape scan -- the fix's own header at the
// alf_mar read names every table and explains the ordering choice, and a raw
// file-wide match would score that prose as the code being present. Same trap
// api/alf-append-only-fail-closed.test.js already records.
const CODE = SRC.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');

// ── THE TABLE LIST IS NOT RETYPED HERE, IT IS READ FROM THE SIBLING ────────
// api/alf-append-only-fail-closed.test.js already owns the definition of which
// SAIRNcare tables are append-only trails. A second hand-typed copy is a list
// that silently stops matching the day a seventh trail is added to one of them
// -- and the failure mode of a stale copy is this arm reporting a clean sweep
// over a table it has never heard of. Parsed from the sibling's source so the
// two cannot drift.
const SIBLING = path.join(__dirname, 'alf-append-only-fail-closed.test.js');
const siblingSrc = mustRead(SIBLING, 'takes its table list from alf-append-only-fail-closed.test.js');
const listMatch = siblingSrc.match(/const TABLES = \[([\s\S]*?)\];/);
if (!listMatch) {
  console.error('COULD NOT RUN: no `const TABLES = [...]` found in ' + SIBLING + '.');
  console.error('  The sibling was renamed or restructured. This arm takes its table');
  console.error('  list from there on purpose and will not fall back to a local copy,');
  console.error('  because a local copy is what goes stale. This is NOT a pass.');
  process.exit(2);
}
const TABLES = (listMatch[1].match(/'([a-z_]+)'/g) || []).map((s) => s.slice(1, -1));

// The column each trail orders by. alf_signals is the one deliberate exception
// -- see the header. A table present in TABLES but absent from this map is an
// unhandled new trail, asserted below rather than skipped.
const ORDER_COLUMN = {
  alf_mar: 'created_at',
  alf_incidents: 'created_at',
  alf_signals: 'recorded_at',
  alf_claim_routes: 'created_at',
  alf_staff_credentials: 'created_at',
  alf_op_audits: 'created_at',
};

// ── THIS ARM WENT RED ON main WITHOUT THE SUBJECT CHANGING (2026-09-29) ─────
// The alf_incidents read was refactored from one inline `rest('...')` call into
// a query built up in a variable:
//
//     let incQ = 'alf_incidents?license_hash=eq.' + enc(licHash)
//       + '&select=entry_id,resident_id,data,created_at,recorded_by'
//       + '&order=created_at.desc';
//     if (!incBroad) incQ += '&recorded_by=eq.' + enc(String(session.employee_id));
//     const r = await fetch(rest(incQ), { headers });
//
// `&order=created_at.desc` IS THERE. The matcher below required the whole query
// to sit inside one `rest('...')` literal, so it found ZERO reads and the arm
// failed with "expected exactly 1 ... found 0".
//
// THE ARM WAS RIGHT TO GO RED AND THAT IS THE PART TO KEEP. Its own comment
// already says zero hits is not a pass, and it refused to call an unfindable
// read a clean one. The defect is the MATCHER'S REACH, not its verdict: a check
// that can only see one spelling of a call reports on the spelling, and every
// refactor then looks like a regression. That is the eighth cross-domain
// discipline -- nothing announces the day a check stops testing anything -- and
// here it announced itself only because the author happened to be running it.
//
// SO THE MATCHER RESOLVES THE VARIABLE TO ITS DEFINITION. Two shapes, and the
// union of what each finds:
//
//   INLINE     rest('<table>?license_hash=eq.' + enc(licHash) + '<tail>')
//   VARIABLE   <id> = '<table>?license_hash=eq.' ... ; [<id> += ...] ; rest(<id>)
//
// FOR THE VARIABLE SHAPE IT CONCATENATES EVERY SINGLE-QUOTED LITERAL in the
// declaration and in every later `<id> +=` statement, which is exactly what the
// runtime does to those fragments. It does NOT try to evaluate `enc(...)` or any
// other expression -- those contribute a value, never a query PARAMETER NAME, so
// an `&order=` can only ever arrive as a literal.
//
// AND IT REQUIRES THE VARIABLE TO REACH rest(). A variable assigned a query
// string and never passed to rest() is dead code, and crediting it would be the
// matcher inventing a read. `rest(<id>)` is asserted before the literals are
// collected.
//
// TRAILING COMMENTS ARE STRIPPED PER STATEMENT, not just per line. CODE above
// drops comment-ONLY lines, which is not enough here: `... '&select=a'; //
// &order=created_at.desc` is a code line carrying a claim in a comment, and a
// matcher that scored it would pass an unordered read. The control section
// drives exactly that fixture and requires a FAIL.
function _statementsFor(src, ident) {
  // The declaration plus every augmenting assignment, each cut at its
  // terminating `;` and stripped of any trailing `//` comment.
  const out = [];
  const pats = [
    new RegExp('(?:const|let|var)\\s+' + ident + '\\s*=', 'g'),
    new RegExp('(?:^|[^\\w.])' + ident + '\\s*\\+=', 'g'),
  ];
  pats.forEach((re) => {
    let m;
    while ((m = re.exec(src)) !== null) {
      const start = m.index;
      const semi = src.indexOf(';', re.lastIndex);
      const stmt = src.slice(start, semi < 0 ? src.length : semi);
      // Strip a trailing line comment from EVERY line of the statement. A
      // multi-line concatenation can carry one on any of its lines.
      out.push(stmt.split('\n').map((l) => l.replace(/\/\/.*$/, '')).join('\n'));
    }
  });
  return out;
}

function _literals(stmt) {
  // Single-quoted literals only -- every query fragment in api/sd-data.js is
  // single-quoted, and accepting double quotes would start scoring JSON keys.
  return (stmt.match(/'(?:[^'\\]|\\.)*'/g) || []).map((s) => s.slice(1, -1));
}

// The facility-wide LIST read for a trail: filtered by license_hash only, with
// a multi-column select. Deliberately NOT the `&entry_id=eq.` existence probes
// (one row by unique key -- ordering is meaningless there) and not the
// resident-filtered compute reads.
//
// Returns one entry per read found, each being the query text with the literal
// fragments joined -- so the caller's `&order=<col>.desc` check is unchanged and
// does not need to know which shape the read was written in.
function listReadIn(src, table) {
  const hits = [];

  const inline = new RegExp(
    "rest\\('" + table + "\\?license_hash=eq\\.' \\+ enc\\(licHash\\) \\+ '([^']*)'\\)",
    'g');
  let m;
  while ((m = inline.exec(src)) !== null) hits.push(m[1]);

  // VARIABLE SHAPE. The declaration must open with this table's own prefix, so
  // a query for a different table cannot be attributed here.
  const decl = new RegExp(
    "(?:const|let|var)\\s+([A-Za-z_$][\\w$]*)\\s*=\\s*'" + table
    + "\\?license_hash=eq\\.'", 'g');
  const seen = {};
  while ((m = decl.exec(src)) !== null) {
    const ident = m[1];
    if (seen[ident]) continue;
    seen[ident] = true;
    // Must actually be handed to rest(), or it is a string nobody queries with.
    if (!new RegExp('rest\\(\\s*' + ident + '\\s*[,)]').test(src)) continue;
    const parts = [];
    _statementsFor(src, ident).forEach((stmt) => {
      _literals(stmt).forEach((lit) => parts.push(lit));
    });
    if (parts.length) hits.push(parts.join(''));
  }
  return hits;
}

function listReadFor(table) {
  return listReadIn(CODE, table);
}

function main() {
  console.log('SAIRNcare append-only read order: an unordered trail read is not insertion order');

  test('the table list was actually parsed out of the sibling, not defaulted', () => {
    // A regex that matched but captured nothing would leave TABLES empty, and
    // every per-table assertion below would then vacuously pass over zero
    // tables -- a green run that checked nothing. This is the guard against
    // that, and it must stay a LOWER bound rather than an exact count: a
    // seventh trail added to the sibling must not fail HERE, it must fail in
    // the per-table assertions where the message names the table.
    //
    // THE BOUND USED TO BE THE LITERAL `>= 6`, AND THAT WAS THE ONE NUMBER IN
    // THIS FILE NOT DERIVED FROM ANYTHING (corrected 2026-09-23, from the
    // review of hank's 2026-09-22T12:02:38Z obligation). It typed a count
    // beside a list it otherwise parses, so a legitimate DROP to five trails
    // would have failed this arm about its own fixture rather than about its
    // subject -- the anchor-staleness class this repo recorded four times in a
    // single day, including arm 6 of tests/run_criticality_tier_probe.py.
    //
    // ORDER_COLUMN is the right floor because it is the file's own declaration
    // of every trail it knows how to check, and the very next test asserts the
    // other direction (every sibling table must appear in ORDER_COLUMN). The
    // two together pin the sets equal without either one naming a number.
    const DECLARED = Object.keys(ORDER_COLUMN);
    assert.ok(DECLARED.length > 0,
      'ORDER_COLUMN is empty, so this arm has no floor to check against and ' +
      'every per-table assertion below would pass vacuously.');
    assert.ok(TABLES.length >= DECLARED.length,
      'parsed ' + TABLES.length + ' trail(s) from the sibling but this file ' +
      'declares an ordering column for ' + DECLARED.length + '. A trail ' +
      'declared here and absent from the sibling means the parse lost rows, ' +
      'or the sibling dropped a trail and this file was not updated -- either ' +
      'way the per-table assertions below would be checking fewer trails than ' +
      'this file believes exist. Parsed: ' + JSON.stringify(TABLES) +
      '; declared: ' + JSON.stringify(DECLARED));
  });

  test('every trail in the sibling list has an ordering column declared here', () => {
    const undeclared = TABLES.filter((t) => !ORDER_COLUMN[t]);
    assert.deepStrictEqual(undeclared, [],
      'new append-only trail(s) with no ordering column declared in this arm: ' +
      undeclared.join(', ') + '. Add the order= clause to the read in sd-data.js ' +
      'and the column to ORDER_COLUMN -- do not delete the table from the list.');
  });

  TABLES.forEach((table) => {
    test(table + ' list read carries an explicit order= clause', () => {
      const hits = listReadFor(table);
      // Zero hits is NOT a pass. It means the read was renamed or restructured
      // and this arm can no longer see it -- indistinguishable from a clean
      // sweep unless it is asserted.
      assert.strictEqual(hits.length, 1,
        'expected exactly 1 facility-wide list read for ' + table + ', found ' +
        hits.length + '. Zero means this arm can no longer find the read, which ' +
        'is a broken check, not a passing one.');
      const col = ORDER_COLUMN[table];
      assert.ok(hits[0].indexOf('&order=' + col + '.desc') !== -1,
        table + ' list read has no `&order=' + col + '.desc`; its rows come back ' +
        'in whatever order the planner produced. Query was: ' + hits[0]);
    });
  });

  // ── KNOWN-BAD CONTROLS FOR THE MATCHER ITSELF ────────────────────────────
  // Driven against SYNTHETIC source, never against sd-data.js. A control that
  // can only be exercised by breaking the real file is a control nobody runs,
  // and one that passes because the real file happens to suit it is not a
  // control at all. Each fixture is the smallest thing that discriminates.
  const FX_INLINE_OK =
    "const r = await fetch(rest('alf_fx?license_hash=eq.' + enc(licHash) + "
    + "'&select=entry_id,data&order=created_at.desc'), { headers });";
  const FX_VAR_OK =
    "let q = 'alf_fx?license_hash=eq.' + enc(licHash)\n"
    + "  + '&select=entry_id,data,created_at'\n"
    + "  + '&order=created_at.desc';\n"
    + "if (!broad) q += '&recorded_by=eq.' + enc(String(session.employee_id));\n"
    + "const r = await fetch(rest(q), { headers });";
  const FX_VAR_NO_ORDER =
    "let q = 'alf_fx?license_hash=eq.' + enc(licHash)\n"
    + "  + '&select=entry_id,data,created_at';\n"
    + "const r = await fetch(rest(q), { headers });";
  const FX_VAR_ORDER_IN_COMMENT =
    "let q = 'alf_fx?license_hash=eq.' + enc(licHash)\n"
    + "  + '&select=entry_id,data,created_at'; // &order=created_at.desc\n"
    + "const r = await fetch(rest(q), { headers });";
  const FX_VAR_NEVER_QUERIED =
    "let q = 'alf_fx?license_hash=eq.' + enc(licHash)\n"
    + "  + '&select=entry_id,data&order=created_at.desc';\n"
    + "console.log(q);";

  function ordered(src) {
    const hits = listReadIn(src, 'alf_fx');
    return hits.length === 1
      && hits[0].indexOf('&order=created_at.desc') !== -1;
  }

  test('CONTROL: the matcher still sees the INLINE shape and its order clause',
    () => {
      assert.strictEqual(ordered(FX_INLINE_OK), true,
        'the inline shape stopped being recognised, so widening the matcher ' +
        'traded one blindness for another');
    });

  test('THE REFACTOR THIS ARM WENT RED ON: a VARIABLE-built read with an ' +
    'order clause is seen', () => {
      assert.strictEqual(listReadIn(FX_VAR_OK, 'alf_fx').length, 1,
        'a query built in a variable and passed to rest() is still invisible; ' +
        'this is the exact shape the alf_incidents read was refactored into');
      assert.strictEqual(ordered(FX_VAR_OK), true,
        'the variable-built read was found but its &order= was not resolved ' +
        'out of the concatenated fragments');
    });

  test('KNOWN-BAD: a VARIABLE-built read with NO order clause FAILS', () => {
    assert.strictEqual(listReadIn(FX_VAR_NO_ORDER, 'alf_fx').length, 1,
      'the fixture was not even found, so this control proves nothing about ' +
      'the order check -- it would pass for a matcher that sees nothing');
    assert.strictEqual(ordered(FX_VAR_NO_ORDER), false,
      'an unordered variable-built read was reported as ordered. Resolving the ' +
      'variable is only useful if the resolved text is then actually checked.');
  });

  test('KNOWN-BAD: an order clause that exists ONLY IN A TRAILING COMMENT FAILS',
    () => {
      assert.strictEqual(listReadIn(FX_VAR_ORDER_IN_COMMENT, 'alf_fx').length, 1,
        'the fixture was not found, so this control is vacuous');
      assert.strictEqual(ordered(FX_VAR_ORDER_IN_COMMENT), false,
        'an `&order=` written in a trailing // comment was scored as the code ' +
        'being present. CODE above strips comment-ONLY lines, which does not ' +
        'cover a claim parked at the end of a real statement.');
    });

  test('KNOWN-BAD: a query variable never handed to rest() is NOT a read', () => {
    assert.deepStrictEqual(listReadIn(FX_VAR_NEVER_QUERIED, 'alf_fx'), [],
      'a string that looks like a query but is never passed to rest() was ' +
      'counted as a read. That is the matcher inventing coverage.');
  });

  test('CONTROL: the matcher does not attribute another table\'s query here',
    () => {
      assert.deepStrictEqual(
        listReadIn(FX_VAR_OK.replace(/alf_fx/g, 'alf_other'), 'alf_fx'), [],
        'a read for a different table was attributed to alf_fx');
    });

  test('the entry_id existence probes were NOT given an order= clause', () => {
    // Scope discipline in the arm, not just in the diff. The five
    // `&entry_id=eq.` probes select a single row by unique key; ordering one is
    // meaningless and would only signal that the fix was applied by blind
    // pattern across the file. Asserted so a later bulk edit is caught.
    // Matched by LINE rather than by one regex over the whole call: the probe
    // URL is built as `'...&entry_id=eq.' + enc(String(payload.id)) + '&select=id'`,
    // so a single string-literal pattern cannot span it and a first draft of
    // this assertion silently found zero -- which the >= 5 lower bound below is
    // what caught. That is the point of asserting the probes are PRESENT before
    // asserting something about them.
    const probes = CODE.split('\n').filter(
      (l) => /rest\('alf_[a-z_]+\?license_hash=eq\./.test(l) && l.indexOf('&entry_id=eq.') !== -1);
    assert.ok(probes.length >= 5,
      'expected the 5+ entry_id existence probes to still be present, found ' + probes.length);
    const ordered = probes.filter((p) => p.indexOf('&order=') !== -1);
    assert.deepStrictEqual(ordered, [],
      'an entry_id existence probe was given an order= clause: ' + ordered.join(' | '));
  });

  console.log('\n' + passed + ' assertions passed');
}

main();
