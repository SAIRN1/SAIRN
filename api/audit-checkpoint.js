// api/audit-checkpoint.js
// ---------------------------------------------------------------------------
// DAILY CHECKPOINTS OVER THE THREE AUDIT LOGS, AND THE VERIFIER THAT MAKES THEM
// MEAN SOMETHING. Item 35. Michael's decision 2026-09-14: daily cadence, over
// CLOSED windows.
//
// Cron-only, same gate as the other cron endpoints: Bearer CRON_SECRET.
//
//   POST {"action":"checkpoint"}   default -- write every window that has
//                                  closed since the last checkpoint
//   POST {"action":"verify"}       recompute EVERY closed window and report the
//                                  first one that disagrees, per table
//
// ── WHAT IT DETECTS, AND THE TWO THINGS IT DELIBERATELY DOES NOT ────────────
// The three audit tables carry `grant select, insert` and nothing else, so a
// row cannot be altered or removed through the API. Those modes are closed BY
// CONSTRUCTION and this file does not re-buy them. The mode the grant leaves
// open is INSERTION -- the grant is table-level, `api/_lib/audit.js` lets
// `created_at` default, and so anyone with the service key can insert a row
// with any timestamp under any license_hash. That is what a checkpoint catches.
//
// It does NOT catch an insertion into the current, not-yet-closed window --
// bounded by one day, not open-ended -- and it does NOT bind anyone with direct
// database access, who can rewrite rows AND recompute every checkpoint over
// them. Both are in sql/audit_checkpoint_schema.sql's header too, because a
// reader who finds only one of the two files must still find the limits.
//
// ── WHY NOT A PER-ROW CHAIN ────────────────────────────────────────────────
// It would put a READ on api/_lib/audit.js, whose contract is that it must
// never block and whose seven callers all ignore its return value; and two
// concurrent audit writes would read the same previous hash and FORK the chain,
// which with no UPDATE grant NOTHING CAN REPAIR. A window is CLOSED before it
// is hashed, so concurrency inside it cannot fork anything.
//
// ── THE PAGING IS THE PART MOST LIKELY TO BE WRONG SILENTLY ────────────────
// PostgREST caps a response. A digest computed over the FIRST PAGE of a busy
// day would be perfectly stable, perfectly reproducible, and cover a fraction
// of the window -- a vacuous checkpoint that passes every verification while
// protecting almost nothing. So every page is fetched explicitly AND the total
// from Content-Range is compared against what was actually read; a mismatch is
// a REFUSAL, not a short digest.
// ---------------------------------------------------------------------------

const crypto = require('crypto');
const { beat } = require('./_lib/heartbeat');

const TABLES = ['sairnlaw_audit_log', 'sairncode_audit_log', 'stonedesk_audit_log'];
const CHECKPOINT_TABLE = 'sairn_audit_checkpoint';
// The chain's first link. A literal rather than an empty string so a row whose
// prev_digest was lost or never set is distinguishable from a genuine genesis.
const GENESIS = 'genesis:sairn-audit-checkpoint:v1';
const DAY_MS = 24 * 60 * 60 * 1000;
const PAGE = 1000;
// How many recent windows the DAILY run re-verifies. 14 rather than a round
// number: two weeks is long enough that a tamper has to beat a fortnight of
// runs to age out of it, and short enough that the daily job's cost does not
// grow with the log's age. The figure is reported in every response so a
// reader never has to find it here.
const RECENT_VERIFY_WINDOWS = 14;

function headers() {
  const k = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return { apikey: k, Authorization: 'Bearer ' + k, 'Content-Type': 'application/json' };
}
function rest(path) {
  return String(process.env.SUPABASE_URL).replace(/\/+$/, '') + '/rest/v1/' + path;
}
function enc(s) { return encodeURIComponent(s); }
function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('42P01') !== -1 ||
         s.indexOf('does not exist') !== -1;
}
// Midnight UTC of the day containing `ms`. UTC and not local, deliberately:
// this runs on a server whose timezone nobody controls, and a window boundary
// that moved with a deploy region would make two adjacent digests disagree for
// a reason that has nothing to do with tampering.
function dayStart(ms) { return Math.floor(ms / DAY_MS) * DAY_MS; }

// ── THE CANONICAL FORM IS THE WHOLE THING ──────────────────────────────────
// Two serialisations of the same window must produce the same digest or the
// verifier reports tampering on an untouched table; two different windows must
// never collide or the checkpoint is decorative. Keys sorted recursively,
// NOTHING else normalised -- no trimming, no case folding, no dropping of
// nulls. A `detail` differing only in whitespace is a different row, and
// deciding otherwise here would be this file quietly editing an audit record to
// make a digest fit.
function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  const keys = Object.keys(value).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
}

function digestOf(prevDigest, rows) {
  // ORDERED BY (created_at, id), NOT by whatever PostgREST returns. Two rows
  // can share a created_at to the microsecond; without the id tiebreak the
  // order is the database's to choose and a re-verification could hash the same
  // window in a different order and call a correct table tampered.
  const ordered = rows.slice().sort((a, b) => {
    if (a.created_at < b.created_at) return -1;
    if (a.created_at > b.created_at) return 1;
    return a.id < b.id ? -1 : (a.id > b.id ? 1 : 0);
  });
  const h = crypto.createHash('sha256');
  h.update(prevDigest + '\n');
  for (const r of ordered) h.update(canonical(r) + '\n');
  return h.digest('hex');
}

// Every row in [startISO, endISO), paged, with the count CHECKED against the
// server's own total rather than assumed from what came back.
async function readWindow(table, startISO, endISO) {
  const base = table + '?created_at=gte.' + enc(startISO) +
    '&created_at=lt.' + enc(endISO) +
    '&select=id,license_hash,employee_id,role,event_type,detail,created_at' +
    '&order=created_at.asc,id.asc';
  const rows = [];
  let offset = 0;
  let total = null;
  for (;;) {
    const r = await fetch(rest(base), {
      headers: Object.assign({}, headers(), {
        Range: offset + '-' + (offset + PAGE - 1),
        'Range-Unit': 'items',
        Prefer: 'count=exact'
      })
    });
    const body = await r.json().catch(() => null);
    if (!r.ok) {
      const e = new Error('read failed');
      e.detail = body;
      throw e;
    }
    // "0-999/12345" -- the total after the slash is the only statement of how
    // many rows the window really holds.
    const cr = r.headers.get('content-range') || '';
    const slash = cr.indexOf('/');
    if (slash !== -1) {
      const t = cr.slice(slash + 1);
      if (t !== '*' && !isNaN(Number(t))) total = Number(t);
    }
    const page = Array.isArray(body) ? body : [];
    rows.push.apply(rows, page);
    if (page.length < PAGE) break;
    offset += PAGE;
    if (offset > 5000000) { const e = new Error('runaway paging'); e.detail = cr; throw e; }
  }
  if (total === null) {
    // ── THE GUARD USED TO VANISH WHEN ITS INPUT DID (found 2026-09-14 by an
    // independent review of this file, by DRIVING it rather than reading it).
    //
    // The check below was `total !== null && total !== rows.length`, so a
    // response carrying NO Content-Range, or `0-0/*`, left `total` null and
    // skipped the comparison entirely. Driven against the real handler with a
    // fake returning ONE row of three: with `0-0/3` it correctly refused 503
    // WINDOW_INCOMPLETE; with `0-0/*` and with no header at all it returned
    // HTTP 200 AND WROTE A CHECKPOINT WITH row_count 1.
    //
    // That is exactly the outcome this file's own header calls the thing it
    // must never produce -- "a vacuous checkpoint that passes every
    // verification while protecting almost nothing" -- and it arrived through
    // the ABSENCE of the count rather than a wrong one. PR 1.11: could-not-tell
    // is a third state and is never folded into a pass.
    //
    // `Prefer: count=exact` is sent on every request, so a missing total means
    // the server did not answer the question that was asked, and the read
    // cannot be confirmed complete. Refusing is loud and says what to do.
    const e = new Error('row count not stated');
    e.detail = { table: table, read: rows.length,
                 why: 'the server returned no exact Content-Range total, so the '
                      + 'read could not be confirmed complete' };
    e.incomplete = true;
    throw e;
  }
  if (total !== rows.length) {
    // A SHORT DIGEST IS NOT A DIGEST. Refusing is the only safe answer: a
    // checkpoint over part of a window would verify cleanly forever while
    // covering a fraction of the rows.
    const e = new Error('paging incomplete');
    e.detail = { expected: total, read: rows.length, table: table };
    e.incomplete = true;
    throw e;
  }
  return rows;
}

async function lastCheckpoint(table) {
  const r = await fetch(rest(CHECKPOINT_TABLE + '?audit_table=eq.' + enc(table) +
    '&select=window_end,digest&order=window_end.desc&limit=1'), { headers: headers() });
  const body = await r.json().catch(() => null);
  if (!r.ok) { const e = new Error('checkpoint read failed'); e.detail = body; throw e; }
  return (Array.isArray(body) && body[0]) || null;
}

async function earliestRow(table) {
  const r = await fetch(rest(table + '?select=created_at&order=created_at.asc&limit=1'),
    { headers: headers() });
  const body = await r.json().catch(() => null);
  if (!r.ok) { const e = new Error('earliest read failed'); e.detail = body; throw e; }
  return (Array.isArray(body) && body[0] && body[0].created_at) || null;
}

async function allCheckpoints(table) {
  const r = await fetch(rest(CHECKPOINT_TABLE + '?audit_table=eq.' + enc(table) +
    '&select=window_start,window_end,row_count,digest,prev_digest&order=window_end.asc'),
    { headers: headers() });
  const body = await r.json().catch(() => null);
  if (!r.ok) { const e = new Error('checkpoint read failed'); e.detail = body; throw e; }
  return Array.isArray(body) ? body : [];
}

async function checkpointTable(table, nowMs) {
  const closedThrough = dayStart(nowMs);          // today's window is still OPEN
  const last = await lastCheckpoint(table);
  let cursor;
  if (last) {
    cursor = Date.parse(last.window_end);
  } else {
    const first = await earliestRow(table);
    // NO ROWS IS NOT AN ERROR AND IS NOT A CHECKPOINT EITHER. Writing a digest
    // over an empty table would create a chain link attesting to nothing, and
    // the next real window would chain onto it correctly -- so the lie would be
    // permanent and verifiable.
    if (!first) return { table: table, written: 0, note: 'no audit rows yet' };
    cursor = dayStart(Date.parse(first));
  }
  let prev = last ? last.digest : GENESIS;
  const written = [];
  while (cursor + DAY_MS <= closedThrough) {
    const startISO = new Date(cursor).toISOString();
    const endISO = new Date(cursor + DAY_MS).toISOString();
    const rows = await readWindow(table, startISO, endISO);
    const d = digestOf(prev, rows);
    const r = await fetch(rest(CHECKPOINT_TABLE), {
      method: 'POST',
      headers: Object.assign({}, headers(), { Prefer: 'return=minimal' }),
      body: JSON.stringify({
        audit_table: table, window_start: startISO, window_end: endISO,
        row_count: rows.length, digest: d, prev_digest: prev
      })
    });
    if (!r.ok) {
      const body = await r.text().catch(() => '');
      const e = new Error('checkpoint write failed');
      e.detail = body;
      throw e;
    }
    written.push({ window_end: endISO, row_count: rows.length });
    prev = d;
    cursor += DAY_MS;
    // A cron has a wall clock. Stopping at a bound and SAYING so beats being
    // killed mid-window and leaving a gap nobody is told about -- the next run
    // picks up exactly where this one stopped, because the cursor is derived
    // from the last checkpoint rather than from a counter.
    if (written.length >= 60) break;
  }
  return { table: table, written: written.length, windows: written };
}

// `limit` re-verifies only the most recent N windows. THE CAP IS REPORTED, NOT
// SILENT: a bounded check that reads as a full one is the defect this platform
// keeps recording, so the result carries `verified` AND `checkpoints` and says
// `full` only when they are equal. The daily run uses a bound because a full
// re-verification is O(all history) and would grow until the cron times out --
// at which point it would stop verifying anything and say nothing about it.
async function verifyTable(table, limit) {
  const cps = await allCheckpoints(table);
  if (!cps.length) return { table: table, checkpoints: 0, verified: 0, full: true, ok: true, note: 'nothing checkpointed yet' };
  let prev = GENESIS;
  // Walking from genesis is what makes prev_digest checkable at all. When a
  // bound is set the LINK is still walked over everything -- it is free, it is
  // just string equality -- and only the expensive half, re-reading the window
  // and recomputing its digest, is skipped for the older ones.
  const from = (limit && limit > 0) ? Math.max(0, cps.length - limit) : 0;
  let verified = 0;
  for (let i = 0; i < cps.length; i++) {
    const cp = cps[i];
    if (i < from) {
      if (cp.prev_digest !== prev) {
        return { table: table, ok: false, kind: 'CHAIN_BROKEN', window_end: cp.window_end,
                 expected_prev: prev, found_prev: cp.prev_digest };
      }
      prev = cp.digest;
      continue;
    }
    verified++;
    // THE LINK FIRST. A checkpoint whose prev_digest does not match the digest
    // of the one before it means the CHECKPOINT TABLE was tampered with, which
    // is a different finding from the audit rows moving and must not be
    // reported as the same thing.
    if (cp.prev_digest !== prev) {
      return { table: table, ok: false, kind: 'CHAIN_BROKEN', window_end: cp.window_end,
               expected_prev: prev, found_prev: cp.prev_digest };
    }
    const rows = await readWindow(table, cp.window_start, cp.window_end);
    const recomputed = digestOf(prev, rows);
    if (recomputed !== cp.digest) {
      return {
        table: table, ok: false, kind: 'WINDOW_CHANGED', window_end: cp.window_end,
        rows_now: rows.length, rows_at_checkpoint: cp.row_count,
        // The row count is reported beside the digest because it separates the
        // two shapes: a count that GREW is the insertion this exists to catch;
        // an unchanged count with a changed digest means a row's CONTENT moved,
        // which the grants say is impossible through the API and therefore
        // points at direct database access.
        expected: cp.digest, recomputed: recomputed
      };
    }
    prev = cp.digest;
  }
  return {
    table: table, checkpoints: cps.length, verified: verified,
    full: verified === cps.length, ok: true
  };
}

module.exports = async (req, res) => {
  if (!process.env.CRON_SECRET) {
    console.error('audit-checkpoint: CRON_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }
  const missing = [
    !process.env.SUPABASE_URL ? 'SUPABASE_URL' : null,
    !process.env.SUPABASE_SERVICE_ROLE_KEY ? 'SUPABASE_SERVICE_ROLE_KEY' : null
  ].filter(Boolean);
  if (missing.length) {
    console.error('audit-checkpoint: not configured, missing: ' + missing.join(', '));
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  body = body || {};
  const action = body.action === 'verify' ? 'verify' : 'checkpoint';
  const nowMs = Date.now();

  try {
    const results = [];
    for (const t of TABLES) {
      results.push(action === 'verify' ? await verifyTable(t, 0) : await checkpointTable(t, nowMs));
    }
    // ── THE DAILY RUN VERIFIES TOO, OR NOTHING EVER DOES ────────────────────
    // A checkpointer without a verifier is a column of hashes nobody has ever
    // seen detect anything -- the state checkbocks.py sat in for months while
    // always exiting 0. Vercel's cron sends a GET with no body, so `checkpoint`
    // is what actually runs in production; if the verification were only on the
    // other action it would never run at all.
    //
    // BOUNDED, AND THE BOUND IS IN THE RESPONSE. A full re-verification is
    // O(all history) and would grow until the daily job timed out, at which
    // point it would verify NOTHING and say nothing about that. The recent
    // windows are where a tamper is both most likely and most actionable; the
    // whole history is one POST {"action":"verify"} away and the response says
    // `full:false` every day until somebody runs it.
    let recent = null;
    if (action === 'checkpoint') {
      recent = [];
      for (const t of TABLES) recent.push(await verifyTable(t, RECENT_VERIFY_WINDOWS));
    }
    const bad = results.filter((r) => r.ok === false)
      .concat((recent || []).filter((r) => r.ok === false));
    // LOGGED, NOT JUST RETURNED, and the reason is the one item 54 exists for:
    // Vercel discards a cron's response body, so a run that found nothing and a
    // run that never happened look identical from outside unless the run says
    // so in the log. api/sairndental/send-reminder.js already does this and its
    // own comment says why.
    console.log('audit-checkpoint: ' + action + ' complete -- ' +
      results.map((r) => r.table + '=' + (action === 'verify'
        ? (r.ok === false ? 'FAILED:' + r.kind : 'ok/' + (r.checkpoints || 0) +
           (r.full === false ? '/PARTIAL' : ''))
        : (r.written + ' written'))).join(', ') +
      (recent ? ' | recent-verify(' + RECENT_VERIFY_WINDOWS + '): ' +
        recent.map((r) => r.table + '=' + (r.ok === false ? 'FAILED:' + r.kind
          : r.verified + '/' + r.checkpoints)).join(', ') : ''));
    if (bad.length) {
      console.error('audit-checkpoint: VERIFICATION FAILED -- ' + JSON.stringify(bad));
    }
    // ── THE HEARTBEAT (item 54) ─────────────────────────────────────────
    // `partial` when a verification FAILED: the job itself is healthy -- it ran
    // and did its work -- but its ANSWER is a finding, and the watchdog must
    // not report that as an ordinary ok while the finding sits in a response
    // body Vercel throws away.
    await beat({
      job: '/api/audit-checkpoint',
      outcome: bad.length ? 'partial' : 'ok',
      expected_interval_seconds: 86400,
      detail: {
        action: action, failures: bad.length,
        written: results.reduce(function (n, r) { return n + (r.written || 0); }, 0)
      }
    });
    res.status(200).json({
      ok: bad.length === 0, action: action, results: results,
      // NAMED, not folded into `results`: these are a DIFFERENT question
      // answered in the same run, and a reader who cannot tell them apart
      // cannot tell "wrote 1 checkpoint" from "verified 14 windows".
      recent_verify: recent,
      recent_verify_windows: action === 'checkpoint' ? RECENT_VERIFY_WINDOWS : null
    });
  } catch (err) {
    // ── THESE TWO REFUSALS BEAT TOO, AND THEY DID NOT (fixed 2026-09-16) ────
    // The success path beats and the generic catch beats. These two early
    // returns did neither -- they answered 503 and returned.
    //
    // WHAT THAT COSTS IS NOT A MISSING LOG LINE. `cron-watchdog` classifies a
    // job with no heartbeat row as NEVER_BEAT, whose own message reads "it has
    // never completed a run, or sql/cron_heartbeat_schema.sql predates it". So
    // a job that fires daily and refuses daily -- because its table is absent,
    // or because it could not read a whole window -- is INDISTINGUISHABLE from
    // a job that never fires at all. The one state that most needs telling
    // apart from silence produced silence.
    //
    // `failed` rather than `partial` in both cases, deliberately: `partial` in
    // this file means the job DID its work and the ANSWER is a finding. Here
    // nothing was written, so the job did not do its work, and calling that
    // partial would put a refusal in the same bucket as a completed run that
    // found something.
    if (isMissingTable(err && err.detail)) {
      await beat({
        job: '/api/audit-checkpoint', outcome: 'failed',
        expected_interval_seconds: 86400,
        detail: { refused: 'NOT_PROVISIONED',
                  why: 'sql/audit_checkpoint_schema.sql has not been run',
                  retry_helps: false }
      });
      res.status(503).json({
        error: {
          code: 'NOT_PROVISIONED',
          message: 'The audit checkpoint table is not set up yet -- run ' +
                   'sql/audit_checkpoint_schema.sql. Nothing was checkpointed, ' +
                   'and that is not the same as a clean run.'
        }
      });
      return;
    }
    if (err && err.incomplete) {
      // COULD NOT READ THE WHOLE WINDOW is a third state and must not be filed
      // as either a clean checkpoint or a tampering finding.
      console.error('audit-checkpoint: paging incomplete', err.detail);
      await beat({
        job: '/api/audit-checkpoint', outcome: 'failed',
        expected_interval_seconds: 86400,
        detail: { refused: 'WINDOW_INCOMPLETE',
                  why: 'a window could not be read in full, so nothing was written',
                  retry_helps: true }
      });
      res.status(503).json({
        error: {
          code: 'WINDOW_INCOMPLETE',
          message: 'A window could not be read in full, so nothing was written. ' +
                   'A digest over part of a window would verify cleanly forever ' +
                   'while covering a fraction of the rows.',
          detail: err.detail
        }
      });
      return;
    }
    console.error('audit-checkpoint: error', err && err.message, err && err.detail);
    // RAN AND FAILED still beats -- silence and failure need different answers.
    await beat({ job: '/api/audit-checkpoint', outcome: 'failed',
                 expected_interval_seconds: 86400,
                 detail: { error: String((err && err.message) || err).slice(0, 200) } });
    res.status(502).json({ error: { message: 'Upstream error -- try again' } });
  }
};

module.exports.canonical = canonical;
module.exports.digestOf = digestOf;
module.exports.dayStart = dayStart;
module.exports.TABLES = TABLES;
module.exports.GENESIS = GENESIS;
