// api/sql-run-order-agreement.test.js
//
// Run:  node api/sql-run-order-agreement.test.js
//
// REQUIREMENT: sql/2026-10-14-michael-run-order.sql is an EXTRACTION of five
//   other SQL files, and every statement in it is still a verbatim substring
//   of the file it was taken from.
//
// ── WHY THIS EXISTS ───────────────────────────────────────────────────────
// The run order is a second copy, and a second copy of SQL is the drift
// problem with the worst possible failure mode: a transcription error in a
// credential insert or in a CHECK list is invisible in review and presents
// as a 23514 or a 401 with correct-looking SQL. Cross-domain convention 8 --
// nothing announces the day a copy stops matching its source -- so this
// re-references against the SOURCE every run rather than on a cadence.
//
// IT CHECKS CONTAINMENT, NOT A HASH, AND THAT IS DELIBERATE. A SHA pin on the
// whole source file goes red the moment somebody fixes a typo in a comment
// three hundred lines away from the extracted block, and a check that cries
// wolf is a check somebody deletes. Containment asks the question that
// actually matters: is the SQL Michael will paste still the SQL the source
// file declares?
//
// ── WHAT IT DOES NOT SAY ──────────────────────────────────────────────────
// Nothing about whether the blocks have been RUN, and nothing about whether
// they are correct against the live database. It compares two files on disk.
// The run order's own per-block verify queries are the only thing that speaks
// to the database, and they have to be read by a human in Supabase.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const ORDER = path.join(ROOT, 'sql/2026-10-14-michael-run-order.sql');

// Each entry: a short anchor that must appear in the run order, the source
// file it came from, and the first+last line of the extracted statement so the
// comparison is over the REAL span rather than over a single line.
const BLOCKS = [
  { n: 1, src: 'sql/2026-10-14-hank-b9-ai-safeguards.sql',
    from: 'do $$', to: 'end $$;',
    must: ['ai_notice_version text', 'ai_notice_acked_at timestamptz',
           "like '%\\_employee\\_auth'"] },
  { n: 2, src: 'sql/audit_checkpoint_schema.sql',
    from: 'create table if not exists sairn_audit_checkpoint (',
    to: '  with check (true);',
    must: ['sairn_audit_checkpoint_audit_table_check',
           'revoke update, delete on public.sairn_audit_checkpoint'] },
  { n: 3, src: 'sql/sairnlaw_audit_log_schema.sql',
    from: 'alter table public.sairnlaw_audit_log',
    to: "    'credential_change_refused'\n  ));",
    must: ["'credential_deactivated'", "'credential_reactivated'",
           "'credential_change_refused'"] },
  { n: 4, src: 'sql/sairnfreedom_demo_owner_credential_2026-10-13.sql',
    from: 'begin;', to: 'commit;',
    must: ['sairnfreedom_employee_auth', "'post.govern'",
           'ZERO active provisioners'] },
  { n: 5, src: 'sql/sairncare_employee_auth_schema.sql',
    from: 'alter table public.sairncare_employee_auth',
    to: "'activities','office_manager'));",
    must: ["'office_manager'", 'sairncare_employee_auth_role_check'] },
  { n: 6, src: 'sql/sairnlegacy_employee_auth_schema.sql',
    from: 'alter table public.sairnlegacy_employee_auth',
    to: "'apprentice','livery','staff'));",
    must: ["'arranger'", "'staff'", 'sairnlegacy_employee_auth_role_check'] }
];

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// LF-normalised on both sides. A CRLF-vs-LF difference is not drift, and this
// repo has produced three false alarms from exactly that comparison.
function read(p) {
  try { return fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n'); }
  catch (e) { return null; }
}

// THE BLOCK'S OWN SECTION, and the uniqueness guard lives HERE rather than on
// the SQL anchors. `do $$` and `alter table public.X` each appear more than
// once across the file -- and twice INSIDE a block, because a widening is a
// drop followed by an add -- so an anchor-uniqueness test over the whole file
// is UNPROVEN for a reason that is not a defect. What must be unique is the
// numbered heading, which is the thing that identifies a block.
function section(text, n) {
  const head = '-- BLOCK ' + n + ' --';
  const nHead = text.split(head).length - 1;
  if (nHead !== 1) return { err: 'the heading ' + JSON.stringify(head)
                                 + ' matched ' + nHead + ' time(s), not once' };
  const a = text.indexOf(head);
  // The heading sits INSIDE a banner pair, so the first `-- ====` after it is
  // its own closer, not the next block's. Skip that one. Without this the
  // section is three lines long and every arm below reports "anchor not
  // found" -- a could-not-tell that reads exactly like a drift.
  const ownCloser = text.indexOf('\n-- ====', a);
  const nextBanner = ownCloser === -1 ? -1
    : text.indexOf('\n-- ====', ownCloser + 1);
  const b = nextBanner === -1 ? text.length : nextBanner;
  return { text: text.slice(a, b) };
}

// The span between two anchors INSIDE one block's section: from the FIRST
// occurrence of `from` to the LAST occurrence of `to`. Deterministic because
// the section is already pinned to one block.
function span(sec, from, to) {
  const a = sec.indexOf(from);
  if (a === -1) return { err: 'start anchor not found in this block' };
  const b = sec.lastIndexOf(to);
  if (b === -1 || b < a) {
    return { err: 'end anchor not found after the start anchor in this block' };
  }
  return { text: sec.slice(a, b + to.length) };
}

console.log('SQL RUN ORDER -- an extraction, re-checked against its sources '
          + '-- criteria 2026-10-14.1\n');

(function main() {
  const order = read(ORDER);
  if (order === null) {
    cannot('A1. sql/2026-10-14-michael-run-order.sql is not readable, so '
         + 'nothing below could be compared', ORDER);
    console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + unproven
              + ' unproven');
    process.exit(3);
  }

  console.log('A. the run order itself');
  const headings = (order.match(/^-- BLOCK \d+ --/gm) || []);
  is(headings.length === BLOCKS.length,
     'A1. the file carries ' + BLOCKS.length + ' numbered BLOCK headings, one '
   + 'per entry in this suite\'s table',
     'found ' + headings.length + ': ' + JSON.stringify(headings));

  const verifies = (order.match(/^-- .. VERIFY BLOCK \d+/gm) || []);
  is(verifies.length === BLOCKS.length,
     'A2. EVERY block has its own VERIFY section. A block with no verify is a '
   + 'block whose result is unknown, and a clean Supabase run is not evidence',
     'found ' + verifies.length);

  is(/EXPECTED:/.test(order)
     && (order.match(/EXPECTED:/g) || []).length >= BLOCKS.length,
     'A3. there are at least as many EXPECTED: answers as blocks -- a verify '
   + 'query with no stated answer puts the judgement back on the reader',
     (order.match(/EXPECTED:/g) || []).length + ' EXPECTED: lines');

  console.log('\nB. every block is still a verbatim substring of its source');
  BLOCKS.forEach(function (b) {
    const srcText = read(path.join(ROOT, b.src));
    if (srcText === null) {
      cannot('B' + b.n + '. ' + b.src + ' is not readable, so block ' + b.n
           + ' could not be compared against anything', 'ENOENT');
      return;
    }
    const sec = section(order, b.n);
    if (sec.err) {
      cannot('B' + b.n + '. block ' + b.n + '\'s section could not be isolated '
           + 'in the run order (' + sec.err + '), so this arm cannot say '
           + 'whether it matches', 'heading guard');
      return;
    }
    const inOrder = span(sec.text, b.from, b.to);
    if (inOrder.err) {
      cannot('B' + b.n + '. the SQL could not be located inside block ' + b.n
           + '\'s section (' + inOrder.err + '), so this arm cannot say '
           + 'whether it matches',
             'anchors: ' + JSON.stringify([b.from, b.to]));
      return;
    }
    if (srcText.indexOf(inOrder.text) !== -1) {
      ok('B' + b.n + '. block ' + b.n + ' is byte-identical to a span of '
       + b.src + ' (' + inOrder.text.split('\n').length + ' lines)');
    } else {
      // Report WHERE it diverges, not just that it does -- "they differ" over
      // a 120-line block is not an actionable finding.
      const want = inOrder.text.split('\n');
      const srcLines = srcText.split('\n');
      const at = srcLines.indexOf(want[0]);
      let firstBad = 'the first line of the block is not in the source at all';
      if (at !== -1) {
        for (let i = 0; i < want.length; i++) {
          if (srcLines[at + i] !== want[i]) {
            firstBad = 'line ' + (i + 1) + ' of the block: run order has '
                     + JSON.stringify(want[i]) + ', source has '
                     + JSON.stringify(srcLines[at + i]);
            break;
          }
        }
      }
      bad('B' + b.n + '. block ' + b.n + ' has DRIFTED from ' + b.src
        + '. The SQL Michael would paste is not the SQL that file declares',
          firstBad);
    }
  });

  // ── C. THE LOAD-BEARING STRINGS, ASSERTED SEPARATELY ──────────────────────
  // Containment alone would pass if a block were replaced by a short, correct
  // but USELESS span of the same file. These are the strings each block exists
  // to deliver.
  console.log('\nC. the load-bearing strings each block exists to deliver');
  // SCOPED TO THE BLOCK'S OWN SECTION, not to the whole file. Searching the
  // whole file is how this arm would pass on a broken block: 'office_manager'
  // appears in block 5's prose as well as in its SQL, so a file-wide match
  // finds the sentence and reports the statement present.
  BLOCKS.forEach(function (b) {
    const sec = section(order, b.n);
    if (sec.err) {
      cannot('C' + b.n + '. block ' + b.n + '\'s section could not be isolated '
           + '(' + sec.err + ')', 'heading guard');
      return;
    }
    const missing = b.must.filter((s) => sec.text.indexOf(s) === -1);
    is(missing.length === 0,
       'C' + b.n + '. block ' + b.n + ' still carries everything it is for ('
     + b.must.length + ' string(s) checked, inside its own section)',
       'missing: ' + JSON.stringify(missing));
  });

  // ── D. THE CONTROL ────────────────────────────────────────────────────────
  // Without this, every arm above would pass against a comparison that cannot
  // fail. A string that is NOT in the sources must not be found in them.
  console.log('\nD. the control -- the comparison can actually fail');
  const sentinel = 'office_manager_THIS_STRING_IS_NOT_IN_ANY_SOURCE';
  const anySource = BLOCKS.some(function (b) {
    const t = read(path.join(ROOT, b.src));
    return t !== null && t.indexOf(sentinel) !== -1;
  });
  is(!anySource,
     'D1. CONTROL -- a deliberately absent string is NOT found in any source, '
   + 'so the containment test above is answering a real question rather than '
   + 'matching everything',
     'the sentinel was found, which means the comparison is vacuous');

  console.log('\n' + pass + ' passed, ' + fail + ' failed, '
            + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  console.log('\nWHAT A GREEN RUN DOES NOT SAY: that any block has been RUN, '
            + 'or that it is right against the live database. It compares two '
            + 'files on disk. The per-block verify queries are the only thing '
            + 'that speaks to the database.');
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})();
