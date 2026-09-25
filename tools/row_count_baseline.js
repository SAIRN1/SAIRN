// tools/row_count_baseline.js
//
//   SAIRN_BASELINE_URL=... SAIRN_BASELINE_KEY=... node tools/row_count_baseline.js
//   ... --out db/row_count_baseline.json     # default is that path
//   ... --write                              # without it this is a DRY RUN
//   ... --force                              # allow a capture that covers LESS
//   ... --json
//
// ITEM 65b: THE FILE NOTHING WROTE.
//
// tools/restore_coherence_check.js has accepted `--baseline
// db/row_count_baseline.json` since 2026-09-14 and NOTHING ON THIS PLATFORM
// EVER WROTE THAT FILE. The reader half shipped, the writer half did not, and
// the gap was found by writing docs/2026-09-25-restore-acceptance-rubric.md --
// section 1 of that rubric answers COULD NOT TELL for every table precisely
// because this file did not exist. This is that file's writer.
//
// ── THE BASELINE COMES FROM PRODUCTION. NEVER FROM A RESTORE. ──────────────
// A baseline captured from the copy you are about to check is the check that
// cannot fail: it will agree with itself perfectly while every row is missing.
// This tool takes SAIRN_BASELINE_URL/KEY rather than reusing the checker's
// SAIRN_TARGET_URL/KEY ON PURPOSE -- two different variable names make it
// harder to point both halves at the same database by muscle memory, and the
// run prints which host it read.
//
// ── A TABLE THAT COULD NOT BE COUNTED IS NEVER WRITTEN AS ZERO ─────────────
// This is the whole correctness argument and it is one line of behaviour: a
// zero in this file means "the table exists and is empty", and a restore that
// lost every row in it would then compare EQUAL and pass. So a table that
// 404s, errors, or returns no exact count is OMITTED from the count map and
// listed under `_not_provisioned` / `_could_not_count`, where the checker's
// `Object.keys(baseline).filter(t => !t.startsWith('_'))` will not read it and
// its own "N of M baseline table(s) compared" line stays honest.
//
// ── THE COUNT QUERY IS THE CHECKER'S QUERY, CHARACTER FOR CHARACTER ────────
// `?select=id&limit=1` with `Prefer: count=exact` and `Range: 0-0`, parsed off
// content-range the same way. If the two ever diverge the comparison becomes
// apples-to-oranges while still producing a confident number, so
// tests/run_row_count_baseline_probe.js asserts the fragment appears in BOTH
// files and fails if either moves. This is the one place where a second
// implementation must NOT be an independent opinion.
//
// ── IT WILL NOT SILENTLY REPLACE A GOOD BASELINE WITH A WORSE ONE ──────────
// A capture that could count FEWER tables than the baseline already on disk is
// either a shrinking database or a degraded run, and both are findings. It
// refuses and says which tables it lost, unless --force. Overwriting on a
// cadence is the point of this file; overwriting with less is how the only
// reference point on the platform would quietly become useless.
//
// Exit 0 wrote (or dry-ran) cleanly, 1 a refusal that needs a human, 2 could
// not run at all. Three states, never two.

'use strict';
const fs = require('fs');
const path = require('path');

const REPO = path.dirname(__dirname);
const EXIT_CLEAN = 0, EXIT_REFUSED = 1, EXIT_COULD_NOT_RUN = 2;
const DEFAULT_OUT = path.join('db', 'row_count_baseline.json');

// ── THE FUNCTIONAL CORE ─────────────────────────────────────────────────────
// Everything below this line to `main()` is pure: same inputs, same output, no
// network, no filesystem, no clock. The probe drives these directly.

// The count query, in one place. See the header: this fragment is asserted
// against tools/restore_coherence_check.js by the probe.
function countQuery(table) {
  return table + '?select=id&limit=1';
}
function countHeaders() {
  return { Prefer: 'count=exact', Range: '0-0' };
}

// PostgREST returns `0-0/1234`; the total is what follows the slash.
function parseCount(contentRange) {
  const s = String(contentRange || '');
  const i = s.indexOf('/');
  if (i === -1) return null;
  const n = Number(s.slice(i + 1));
  return Number.isFinite(n) ? n : null;
}

function isMissingTable(status, text) {
  const s = String(text || '');
  return status === 404 || status === 400
    || s.indexOf('PGRST205') !== -1 || s.indexOf('42P01') !== -1
    || s.indexOf('does not exist') !== -1;
}

// One table's outcome, from one response. THREE outcomes, never two.
function classify(res) {
  if (!res || res.ok !== true) {
    if (res && isMissingTable(res.status, res.text)) {
      return { kind: 'not_provisioned',
               why: 'HTTP ' + res.status + ' -- the table is not in this database' };
    }
    return { kind: 'could_not_count',
             why: 'HTTP ' + ((res && res.status) || '?') + ' -- read failed' };
  }
  const n = parseCount(res.contentRange);
  if (n === null) {
    return { kind: 'could_not_count',
             why: 'no exact count in content-range (' +
                  JSON.stringify(res.contentRange || null) + ')' };
  }
  return { kind: 'counted', count: n };
}

// Fold per-table outcomes into the file the checker reads. Meta keys are
// underscore-prefixed so the checker's own filter skips them.
function buildBaseline(outcomes, meta) {
  const counts = {}, notProvisioned = [], couldNot = {};
  Object.keys(outcomes).sort().forEach(function (t) {
    const o = outcomes[t];
    if (o.kind === 'counted') counts[t] = o.count;
    else if (o.kind === 'not_provisioned') notProvisioned.push(t);
    else couldNot[t] = o.why;
  });
  const out = {};
  out._schema = 'sairn.row-count-baseline/1';
  out._what_this_is =
    'Row counts captured from PRODUCTION, so a restore can be compared against '
    + 'something other than itself. A table absent from this file was NOT '
    + 'counted -- absent is not zero, and a zero here means the table really '
    + 'was empty.';
  out._captured_at = meta.capturedAt;
  out._captured_from = meta.host;
  out._tool = 'tools/row_count_baseline.js';
  out._tables_counted = Object.keys(counts).length;
  out._not_provisioned = notProvisioned;
  out._could_not_count = couldNot;
  Object.keys(counts).sort().forEach(function (t) { out[t] = counts[t]; });
  return out;
}

function tablesIn(baseline) {
  return Object.keys(baseline || {}).filter(function (t) {
    return t.charAt(0) !== '_';
  }).sort();
}

// The refusal: a new capture that covers fewer tables than the old one.
// Returns the list of tables the new capture LOST, which is empty when it is
// safe to write.
function coverageLost(previous, next) {
  if (!previous) return [];
  const have = {};
  tablesIn(next).forEach(function (t) { have[t] = true; });
  return tablesIn(previous).filter(function (t) { return !have[t]; });
}

// ── THE IMPERATIVE SHELL ────────────────────────────────────────────────────

function hdrs(key) {
  return { apikey: key, Authorization: 'Bearer ' + key,
           'Content-Type': 'application/json' };
}

async function countOne(base, key, table) {
  const r = await fetch(base + '/rest/v1/' + countQuery(table), {
    headers: Object.assign({}, hdrs(key), countHeaders())
  });
  const text = await r.text().catch(function () { return ''; });
  return { ok: r.ok, status: r.status, text: text,
           contentRange: r.headers && r.headers.get('content-range') };
}

function readSnapshotTables() {
  const p = path.join(REPO, 'db', 'schema_snapshot.json');
  const snap = JSON.parse(fs.readFileSync(p, 'utf8'));
  return Object.keys(snap).sort();
}

function readPrevious(outPath) {
  try { return JSON.parse(fs.readFileSync(outPath, 'utf8')); }
  catch (e) { return null; }
}

async function main(argv) {
  const wantJson = argv.indexOf('--json') !== -1;
  const write = argv.indexOf('--write') !== -1;
  const force = argv.indexOf('--force') !== -1;
  const oIdx = argv.indexOf('--out');
  const outPath = path.join(REPO, oIdx !== -1 ? argv[oIdx + 1] : DEFAULT_OUT);

  const base = (process.env.SAIRN_BASELINE_URL || '').replace(/\/+$/, '');
  const key = process.env.SAIRN_BASELINE_KEY || '';
  if (!base || !key) {
    console.error(
      'COULD NOT RUN: set SAIRN_BASELINE_URL and SAIRN_BASELINE_KEY to the '
      + 'PRODUCTION database. Nothing was captured, and an absent baseline is '
      + 'not an empty one.\n'
      + 'These are deliberately NOT the checker\'s SAIRN_TARGET_* names: a '
      + 'baseline captured from the copy you are about to check is the check '
      + 'that cannot fail.');
    return EXIT_COULD_NOT_RUN;
  }

  let tables;
  try { tables = readSnapshotTables(); }
  catch (e) {
    console.error('COULD NOT RUN: db/schema_snapshot.json could not be read ('
      + e.message + '), so there is no table list to count.');
    return EXIT_COULD_NOT_RUN;
  }

  const host = base.replace(/^https?:\/\//, '').split('/')[0];
  console.error('capturing ' + tables.length + ' table(s) from ' + host + ' ...');
  const outcomes = {};
  for (const t of tables) {
    try { outcomes[t] = classify(await countOne(base, key, t)); }
    catch (e) { outcomes[t] = { kind: 'could_not_count', why: 'request threw: ' + e.message }; }
  }

  const baseline = buildBaseline(outcomes, {
    capturedAt: new Date().toISOString(),
    host: host
  });
  const counted = baseline._tables_counted;
  const missing = baseline._not_provisioned.length;
  const failed = Object.keys(baseline._could_not_count).length;

  const previous = readPrevious(outPath);
  const lost = coverageLost(previous, baseline);

  if (wantJson) {
    console.log(JSON.stringify({
      counted: counted, not_provisioned: missing, could_not_count: failed,
      coverage_lost: lost, would_write: outPath, wrote: false
    }, null, 2));
  } else {
    console.log('ROW COUNT BASELINE -- ' + host);
    console.log('  tables counted        %s'.replace('%s', String(counted)));
    console.log('  NOT PROVISIONED       ' + missing
      + '   <- omitted, never written as 0');
    console.log('  COULD NOT COUNT       ' + failed
      + '   <- omitted, never written as 0');
  }

  if (failed && !force) {
    console.error('\nREFUSING: ' + failed + ' table(s) could not be counted, so '
      + 'this capture is degraded. They are omitted rather than zeroed, but a '
      + 'partial baseline replacing a complete one is how the only reference '
      + 'point on this platform goes quietly useless. Re-run, or --force.');
    Object.keys(baseline._could_not_count).slice(0, 10).forEach(function (t) {
      console.error('  ' + t + ': ' + baseline._could_not_count[t]);
    });
    return EXIT_REFUSED;
  }
  if (lost.length && !force) {
    console.error('\nREFUSING: this capture covers ' + lost.length + ' FEWER '
      + 'table(s) than the baseline already on disk. That is either a '
      + 'shrinking database or a degraded run, and both are findings rather '
      + 'than things to overwrite. Lost: ' + lost.slice(0, 10).join(', ')
      + (lost.length > 10 ? ' ...' : '') + '\nRe-run, or --force.');
    return EXIT_REFUSED;
  }

  if (!write) {
    console.log('\nDRY RUN -- nothing was written. Add --write to capture to '
      + path.relative(REPO, outPath) + '.');
    return EXIT_CLEAN;
  }
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(baseline, null, 2) + '\n', 'utf8');
  console.log('\nWROTE ' + path.relative(REPO, outPath) + ' -- ' + counted
    + ' table(s). Check a restore against it with:\n'
    + '  node tools/restore_coherence_check.js --baseline '
    + path.relative(REPO, outPath));
  return EXIT_CLEAN;
}

module.exports = {
  countQuery: countQuery, countHeaders: countHeaders, parseCount: parseCount,
  isMissingTable: isMissingTable, classify: classify,
  buildBaseline: buildBaseline, tablesIn: tablesIn, coverageLost: coverageLost
};

if (require.main === module) {
  main(process.argv.slice(2)).then(function (c) { process.exitCode = c; },
    function (e) {
      console.error('COULD NOT RUN: ' + (e && e.message));
      process.exitCode = EXIT_COULD_NOT_RUN;
    });
}
