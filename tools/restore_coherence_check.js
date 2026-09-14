// tools/restore_coherence_check.js
//
//   SAIRN_TARGET_URL=... SAIRN_TARGET_KEY=... node tools/restore_coherence_check.js
//   ... --baseline db/row_count_baseline.json      # compare counts too
//   ... --json                                     # machine-readable
//
// IS THIS RESTORED DATABASE COHERENT? Item 65a.
//
// ── WHY AN EXTERNAL CHECKER IS THE RESTORE TEST, NOT A REFINEMENT OF IT ─────
// Measured 2026-09-14 across every schema file in sql/: **ONE foreign-key
// clause, against 459 declared tables.** Every other relationship on this
// platform -- a draw to its job, a trust transaction to its matter -- is held by
// convention in application code.
//
// So POSTGRES WILL ACCEPT A PARTIAL RESTORE WITHOUT COMPLAINT. There are no
// constraints for a dangling reference to violate. A restore that silently
// dropped half of rf_draws produces a database that starts, answers queries, and
// is wrong. The database cannot be its own oracle here.
//
// ── AND THE CONTEXT THIS EXISTS IN, CONFIRMED 2026-09-14 BY MICHAEL ─────────
// Supabase FREE TIER: no automated database backups, one-day log retention. So
// there is no backup to restore and no tooling to restore it with. THIS TOOL IS
// THEREFORE FOR THE HAND RESTORE -- the one somebody does at 3am from whatever
// copy exists, which is what will actually happen the first time it matters. It
// needs no scratch environment, no pipeline and no baseline capture: point it at
// a database and it answers.
//
// ── THE HEADLINE CHECK NEEDS NO BASELINE AT ALL ────────────────────────────
// api/audit-checkpoint.js writes a daily digest over every row in a CLOSED
// window, chained on the previous digest. That chain is an INDEPENDENTLY
// COMPUTED FINGERPRINT OF HISTORY, carried inside the data itself -- so a
// restored copy can be checked against its own past without anyone having
// captured anything at backup time:
//
//   every window whose digest still matches  -> restored byte-faithfully
//   the first window that disagrees          -> names WHEN it diverged, and its
//                                               row count says LOST or GAINED
//
// A row-count comparison would need a trustworthy count from the source at the
// moment of the backup. Nobody has one. The digest needs nothing but the
// restored data.
//
// THE CANONICAL FORM IS IMPORTED FROM api/audit-checkpoint.js, never re-derived.
// A second implementation of that serialisation would diverge and then report
// tampering on a faithful restore -- the worst possible false alarm, because it
// arrives at exactly the moment somebody is deciding whether to trust the data.
//
// ── WHAT IT CANNOT TELL YOU, SAID HERE RATHER THAN LEARNED LATER ───────────
//   * The checkpoint chain covers the THREE AUDIT TABLES. It says nothing about
//     sv_controlled, the ledger, or anything else.
//   * A window that was never checkpointed cannot be verified. If the migration
//     was never run there is nothing to check and this says so rather than
//     reporting a clean run over an empty chain.
//   * Referential coherence below is DERIVED and is REPORT-ONLY. An orphan is a
//     question, not a verdict: some `*_id` columns legitimately hold free text.
//
// Exit 0 coherent, 1 a finding, 2 could not run. Three states, never two.

'use strict';
const fs = require('fs');
const path = require('path');

const REPO = path.dirname(__dirname);
const AC = require(path.join(REPO, 'api', 'audit-checkpoint.js'));

const EXIT_CLEAN = 0, EXIT_FINDING = 1, EXIT_COULD_NOT_RUN = 2;
const CHECKPOINT_TABLE = 'sairn_audit_checkpoint';
const PAGE = 1000;
// Cap on how many rows of a child table are pulled for the derived referential
// pass. REPORTED whenever it bites -- a silent cap would make a huge table read
// as clean on its first thousand rows.
const REF_SAMPLE = 5000;

const TARGET_URL = (process.env.SAIRN_TARGET_URL || process.env.SUPABASE_URL || '').replace(/\/+$/, '');
const TARGET_KEY = process.env.SAIRN_TARGET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || '';

const findings = [];
const couldNotRun = [];
const notes = [];

function hdrs() {
  return { apikey: TARGET_KEY, Authorization: 'Bearer ' + TARGET_KEY, 'Content-Type': 'application/json' };
}
function isMissingTable(s) {
  s = String(s || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('42P01') !== -1 || s.indexOf('does not exist') !== -1;
}

async function getJson(pathAndQuery, extraHeaders) {
  const r = await fetch(TARGET_URL + '/rest/v1/' + pathAndQuery, {
    headers: Object.assign({}, hdrs(), extraHeaders || {})
  });
  const text = await r.text().catch(() => '');
  let body = null;
  try { body = JSON.parse(text); } catch (e) { body = null; }
  return { ok: r.ok, status: r.status, body: body, text: text, headers: r.headers };
}

// Every row in a window, paged, with the count CHECKED against the server's own
// total. A digest over the FIRST PAGE of a busy day is stable, reproducible and
// covers a fraction of the window -- it would verify cleanly forever.
async function readWindow(table, startISO, endISO) {
  const q = table + '?created_at=gte.' + encodeURIComponent(startISO) +
    '&created_at=lt.' + encodeURIComponent(endISO) +
    '&select=id,license_hash,employee_id,role,event_type,detail,created_at' +
    '&order=created_at.asc,id.asc';
  const rows = [];
  let offset = 0, total = null;
  for (;;) {
    const r = await getJson(q, {
      Range: offset + '-' + (offset + PAGE - 1), 'Range-Unit': 'items', Prefer: 'count=exact'
    });
    if (!r.ok) { const e = new Error('read failed'); e.detail = r.text; throw e; }
    const cr = (r.headers && r.headers.get('content-range')) || '';
    const slash = cr.indexOf('/');
    if (slash !== -1) {
      const t = cr.slice(slash + 1);
      if (t !== '*' && !isNaN(Number(t))) total = Number(t);
    }
    const page = Array.isArray(r.body) ? r.body : [];
    rows.push.apply(rows, page);
    if (page.length < PAGE) break;
    offset += PAGE;
    if (offset > 5000000) { const e = new Error('runaway paging'); e.detail = cr; throw e; }
  }
  if (total !== null && total !== rows.length) {
    const e = new Error('paging incomplete');
    e.incomplete = { expected: total, read: rows.length, table: table };
    throw e;
  }
  return rows;
}

// ── 1. THE HEADLINE: the checkpoint chain, against the restored data ────────
async function verifyCheckpoints() {
  const cpRes = await getJson(CHECKPOINT_TABLE +
    '?select=audit_table,window_start,window_end,row_count,digest,prev_digest' +
    '&order=audit_table.asc,window_end.asc');
  if (!cpRes.ok) {
    if (isMissingTable(cpRes.text)) {
      couldNotRun.push('the ' + CHECKPOINT_TABLE + ' table does not exist in the target, so '
        + 'NO window could be verified. If sql/audit_checkpoint_schema.sql was never run there '
        + 'is no fingerprint to check against -- which is not the same as a faithful restore.');
      return;
    }
    couldNotRun.push('could not read ' + CHECKPOINT_TABLE + ' (HTTP ' + cpRes.status + '), so no '
      + 'window was verified');
    return;
  }
  const cps = Array.isArray(cpRes.body) ? cpRes.body : [];
  if (!cps.length) {
    couldNotRun.push('the checkpoint table is EMPTY, so there is no fingerprint of history to '
      + 'check the restore against. A clean run over an empty chain would be a statement about '
      + 'nothing.');
    return;
  }
  const byTable = {};
  for (const cp of cps) (byTable[cp.audit_table] = byTable[cp.audit_table] || []).push(cp);

  for (const table of Object.keys(byTable).sort()) {
    let prev = AC.GENESIS;
    let verified = 0;
    let broke = false;
    for (const cp of byTable[table]) {
      if (cp.prev_digest !== prev) {
        findings.push('CHAIN_BROKEN in ' + table + ' at the window ending ' + cp.window_end +
          ' -- the CHECKPOINT TABLE itself does not chain. That is a different finding from the '
          + 'audit rows moving: it means the fingerprint was rewritten, or restored out of order.');
        broke = true;
        break;
      }
      let rows;
      try {
        rows = await readWindow(table, cp.window_start, cp.window_end);
      } catch (e) {
        if (e.incomplete) {
          couldNotRun.push('the window ending ' + cp.window_end + ' in ' + table + ' could not be '
            + 'read in full (' + e.incomplete.read + ' of ' + e.incomplete.expected + '), so it was '
            + 'NOT verified. A digest over part of a window verifies cleanly while covering a '
            + 'fraction of the rows.');
        } else if (isMissingTable(e.detail)) {
          couldNotRun.push(table + ' does not exist in the target, but it has checkpoints -- the '
            + 'restore is missing a table the fingerprint says existed.');
        } else {
          couldNotRun.push('could not read ' + table + ' for the window ending ' + cp.window_end);
        }
        broke = true;
        break;
      }
      const recomputed = AC.digestOf(prev, rows);
      if (recomputed !== cp.digest) {
        const dir = rows.length > cp.row_count ? 'GAINED ' + (rows.length - cp.row_count) + ' row(s)'
          : rows.length < cp.row_count ? 'LOST ' + (cp.row_count - rows.length) + ' row(s)'
          : 'the same number of rows with DIFFERENT CONTENT';
        findings.push('WINDOW_CHANGED in ' + table + ' at the window ending ' + cp.window_end +
          ' -- this window has ' + dir + ' since it was fingerprinted (' + cp.row_count +
          ' then, ' + rows.length + ' now). Everything BEFORE this window verified; this is where '
          + 'the restore diverged.');
        broke = true;
        break;
      }
      prev = cp.digest;
      verified++;
    }
    if (!broke) {
      notes.push('FINGERPRINT OK: ' + table + ' -- ' + verified + ' of ' + byTable[table].length +
        ' checkpointed window(s) restored byte-faithfully, verified against the chain carried in '
        + 'the data itself. No baseline was needed.');
    }
  }
  const missing = AC.TABLES.filter((t) => !byTable[t]);
  if (missing.length) {
    // NOT a finding: a table with no checkpoints has nothing to verify against.
    // Reported so the coverage is legible rather than implied by silence.
    notes.push('NOT COVERED by any fingerprint: ' + missing.join(', ') +
      ' -- no checkpoint rows exist for these, so nothing here says whether they restored.');
  }
}

// ── 2. DERIVED referential coherence, report-only ───────────────────────────
// Candidates are DERIVED from db/schema_snapshot.json rather than hand-listed: a
// hand list of relations on a platform with 459 tables and one foreign key
// would be stale before it was finished. The derivation is stated in the output
// so a reader judges the rule rather than trusting the count.
function appPrefix(table) {
  const m = /^([a-z]{2,4})_/.exec(table);
  return m ? m[1] : '';
}

function deriveRelations(snapshot) {
  // owner SET, not a single owner. THE FIRST VERSION OF THIS KEPT ONE OWNER PER
  // COLUMN AND IT WAS WRONG IN THE LOUDEST POSSIBLE WAY: `job_id` is owned by
  // rf_jobs AND scp_jobs AND grd_jobs, last write won, and the derivation
  // produced `rf_jobs.job_id -> scp_jobs` -- which would have reported EVERY
  // roofing job as an orphan. Caught by reading the first eight derived
  // relations before wiring any of them to a check, which is the only reason it
  // is not in the output.
  const owners = {};       // 'job_id' -> Set('rf_jobs','scp_jobs',...)
  for (const table of Object.keys(snapshot)) {
    if (table.startsWith('_')) continue;
    const cols = snapshot[table];
    if (!Array.isArray(cols)) continue;
    for (const c of cols) {
      if (!/_id$/.test(c)) continue;
      const stem = c.slice(0, -3);
      // A table OWNS an id column when the table name ends in that stem,
      // pluralised or not: rf_jobs owns job_id.
      if (new RegExp('_' + stem + 's?$').test(table) || new RegExp('^' + stem + 's?$').test(table)) {
        (owners[c] = owners[c] || new Set()).add(table);
      }
    }
  }
  const rels = [];
  const ambiguous = [];
  for (const table of Object.keys(snapshot)) {
    if (table.startsWith('_')) continue;
    const cols = snapshot[table];
    if (!Array.isArray(cols)) continue;
    for (const c of cols) {
      const set = owners[c];
      if (!set) continue;
      // A TABLE THAT OWNS A COLUMN IS THE PARENT FOR IT, NEVER A CHILD. Without
      // this, `sd_comms` and `sv_comms` each own `comm_id`, each excludes itself
      // from the candidates, and the derivation produces the pair
      // `sd_comms.comm_id -> sv_comms` and `sv_comms.comm_id -> sd_comms` --
      // two apps' unrelated tables declared to reference each other, which
      // would report every row on both sides as an orphan.
      if (set.has(table)) continue;
      const cands = [...set];
      if (!cands.length) continue;
      let parent = null;
      if (cands.length === 1) {
        parent = cands[0];
      } else {
        // AMBIGUITY IS RESOLVED ONLY BY THE APP PREFIX, and only when exactly
        // one candidate shares it. Anything else is left UNRESOLVED and
        // reported rather than guessed -- a wrong parent turns every child row
        // into a false orphan, which is how a report-only checker gets ignored.
        const same = cands.filter((p) => appPrefix(p) && appPrefix(p) === appPrefix(table));
        if (same.length === 1) parent = same[0];
      }
      if (parent) rels.push({ child: table, column: c, parent: parent });
      else ambiguous.push(table + '.' + c + ' (candidates: ' + cands.join(', ') + ')');
    }
  }
  return { relations: rels, ambiguous: ambiguous };
}

async function checkReferential(derived) {
  const rels = derived.relations;
  let checked = 0, skipped = 0, capped = 0;
  for (const rel of rels) {
    const kidRes = await getJson(rel.child + '?select=' + rel.column + '&limit=' + REF_SAMPLE);
    if (!kidRes.ok || !Array.isArray(kidRes.body)) { skipped++; continue; }
    const kids = kidRes.body.map((r) => r[rel.column]).filter((v) => v !== null && v !== undefined && v !== '');
    if (!kids.length) { skipped++; continue; }
    if (kidRes.body.length >= REF_SAMPLE) capped++;
    const parentRes = await getJson(rel.parent + '?select=' + rel.column + '&limit=' + REF_SAMPLE);
    if (!parentRes.ok || !Array.isArray(parentRes.body)) { skipped++; continue; }
    const have = new Set(parentRes.body.map((r) => String(r[rel.column])));
    const orphans = [...new Set(kids.map(String))].filter((k) => !have.has(k));
    checked++;
    if (orphans.length) {
      findings.push('ORPHANS: ' + orphans.length + ' distinct ' + rel.column + ' value(s) in ' +
        rel.child + ' have no row in ' + rel.parent + ' (e.g. ' + orphans.slice(0, 3).join(', ') +
        '). The database has no foreign key here and would never have complained. REPORT-ONLY: '
        + 'some *_id columns legitimately hold free text -- read this as a question.');
    }
  }
  // THE DENOMINATOR, PRINTED. A rate over the subset you looked at is not a rate.
  notes.push('REFERENTIAL: ' + checked + ' relation(s) checked, ' + skipped +
    ' skipped (table absent, column empty, or unreadable), out of ' + rels.length +
    ' derived from db/schema_snapshot.json.');
  // AMBIGUOUS IS ITS OWN NUMBER, never folded into `skipped`. A column owned by
  // three tables is not a relation somebody chose not to check -- it is one this
  // derivation CANNOT name a parent for, and guessing would turn every child row
  // into a false orphan.
  if (derived.ambiguous.length) {
    notes.push('AMBIGUOUS: ' + derived.ambiguous.length + ' column(s) are owned by more than one '
      + 'table and no app prefix resolves them, so NO parent was guessed and they were not '
      + 'checked at all. e.g. ' + derived.ambiguous.slice(0, 2).join('; '));
  }
  if (capped) {
    notes.push('CAPPED: ' + capped + ' relation(s) hit the ' + REF_SAMPLE + '-row sample limit, so '
      + 'their orphan count is a FLOOR, not a total.');
  }
}

// ── 3. row counts against an optional baseline (item 65b) ───────────────────
async function checkCounts(baselinePath) {
  let baseline = null;
  try { baseline = JSON.parse(fs.readFileSync(baselinePath, 'utf8')); }
  catch (e) {
    couldNotRun.push('the baseline ' + baselinePath + ' could not be read (' + e.code +
      '), so no row count was compared. Absent is not equal.');
    return;
  }
  const tables = Object.keys(baseline).filter((t) => !t.startsWith('_'));
  let compared = 0;
  for (const t of tables) {
    const r = await getJson(t + '?select=id&limit=1', { Prefer: 'count=exact', Range: '0-0' });
    if (!r.ok) {
      couldNotRun.push(t + ' is in the baseline and could not be read in the target -- that is '
        + 'either a missing table or an unreadable one, and both matter here.');
      continue;
    }
    const cr = (r.headers && r.headers.get('content-range')) || '';
    const total = Number(cr.slice(cr.indexOf('/') + 1));
    if (isNaN(total)) { couldNotRun.push(t + ' returned no exact count, so it was not compared.'); continue; }
    compared++;
    if (total !== baseline[t]) {
      findings.push('COUNT: ' + t + ' has ' + total + ' row(s), baseline says ' + baseline[t] +
        ' (' + (total < baseline[t] ? 'LOST ' + (baseline[t] - total) : 'GAINED ' + (total - baseline[t])) + ').');
    }
  }
  notes.push('COUNTS: ' + compared + ' of ' + tables.length + ' baseline table(s) compared.');
}

(async () => {
  const argv = process.argv.slice(2);
  const wantJson = argv.indexOf('--json') !== -1;
  const bIdx = argv.indexOf('--baseline');
  const baselinePath = bIdx !== -1 ? argv[bIdx + 1] : null;

  if (!TARGET_URL || !TARGET_KEY) {
    console.error('COULD NOT RUN: set SAIRN_TARGET_URL and SAIRN_TARGET_KEY (or SUPABASE_URL and '
      + 'SUPABASE_SERVICE_ROLE_KEY) to the database you want checked. Nothing was checked, and '
      + 'that is not the same as nothing being wrong.');
    process.exitCode = EXIT_COULD_NOT_RUN;
    return;
  }

  try {
    await verifyCheckpoints();
    let snapshot = null;
    try { snapshot = JSON.parse(fs.readFileSync(path.join(REPO, 'db', 'schema_snapshot.json'), 'utf8')); }
    catch (e) {
      couldNotRun.push('db/schema_snapshot.json could not be read, so NO referential relation was '
        + 'derived and none was checked.');
    }
    if (snapshot) await checkReferential(deriveRelations(snapshot));
    if (baselinePath) await checkCounts(baselinePath);
    else notes.push('COUNTS: no --baseline given, so no row count was compared. That is a gap in '
      + 'this run, not a clean result.');
  } catch (e) {
    console.error('COULD NOT RUN: ' + (e && e.message));
    process.exitCode = EXIT_COULD_NOT_RUN;
    return;
  }

  if (wantJson) {
    console.log(JSON.stringify({ findings: findings, could_not_run: couldNotRun, notes: notes }, null, 2));
  } else {
    console.log('RESTORE COHERENCE -- ' + TARGET_URL);
    for (const n of notes) console.log('  . ' + n);
    // COULD NOT RUN IS PRINTED FIRST AND ITS EXIT CODE WINS. A run that found
    // nothing because it could not look is not a clean restore, and folding the
    // two together is the single most repeated defect in this repo's tooling.
    if (couldNotRun.length) {
      console.log('\nCOULD NOT CHECK (' + couldNotRun.length + ') -- this is NOT a pass:');
      for (const c of couldNotRun) console.log('  ? ' + c);
    }
    if (findings.length) {
      console.log('\nFINDINGS (' + findings.length + '):');
      for (const f of findings) console.log('  ! ' + f);
    }
    if (!couldNotRun.length && !findings.length) {
      console.log('\nCOHERENT -- every checkpointed window verified against the fingerprint '
        + 'carried in the data, and no derived relation is orphaned.');
    }
  }
  // ── exitCode, NOT process.exit() ──────────────────────────────────────────
  // process.exit() tears the process down before stdout has flushed. On Windows
  // that showed up as a TRUNCATED report and an exit status of 0xC0000409
  // instead of 2 -- so a correct could-not-check answer arrived cut off
  // mid-sentence with a crash code, which any caller would read as the tool
  // having broken rather than as the verdict it was trying to give.
  process.exitCode = couldNotRun.length ? EXIT_COULD_NOT_RUN
                   : (findings.length ? EXIT_FINDING : EXIT_CLEAN);
})();
