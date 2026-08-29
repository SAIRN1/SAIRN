// api/reference-fingerprint.js
// ---------------------------------------------------------------------------
// PLATFORM-WIDE LOAD-STATE FINGERPRINTING for per-licence reference content.
//
// WHY THIS EXISTS. A reference rule is corrected in a seed file, the commit
// lands, and a live licence keeps serving the old value indefinitely. That is
// not hypothetical: on 2026-08-27 two committed SAIRNlaw corrections were never
// loaded and LAW-PINNACLE-2026 computed federal answer deadlines three days
// late for a day. Nothing on the platform could see it -- row COUNTS were
// right, and every seed row in every app is `version: 1`, so a stale row and a
// corrected row are byte-distinguishable but not version-distinguishable.
//
// api/legal-deadlines.js grew a `rules_fingerprint` action for SAIRNlaw. This
// is the same idea for every OTHER app's reference tables, in one place rather
// than one action per endpoint, because the answer is identical in every app:
// hash what the licence holds so a checker can diff it against the repo.
//
// ── WHY THE WHOLE ROW, NOT JUST `data` ─────────────────────────────────────
// SAIRNlaw keeps everything in one `data` blob. The others DO NOT. Promoted
// columns carry compute-relevant content directly -- rf_contingency_rules keeps
// `count` and `unit` as real columns, dnt_cred_rules keeps `state` /
// `requirement_type` / `role`, alf_compliance_rules keeps `facility_class`. A
// fingerprint over `data` alone would miss a wrong `count` or `unit` entirely,
// which is the exact defect class this exists to catch. (Credit where due: that
// observation is from the DB-side gate this supersedes, and it was right.)
//
// So the hash is taken SUBTRACTIVELY over the whole row: everything except a
// fixed list of bookkeeping columns. Nothing enumerates the columns that
// matter, so a compute column added to a table later is compared by default
// instead of being silently skipped. A hand-picked list of "the fields that
// count" is a list that goes stale in silence.
//
// ── READ-ONLY, AND SCOPED ──────────────────────────────────────────────────
// One action, no writes, no branch that can reach a write. Every query is
// filtered on the CALLER'S license_hash, so a licence can only ever fingerprint
// its own rows; the response carries hashes, not content, so this is not a bulk
// export of another tenant's reference data even in principle. Table names are
// checked against the reference-content name shape before being interpolated --
// the same shape sql/platform_reference_rules_divergence_2026-08-28.sql uses to
// DISCOVER these tables rather than enumerate them.
// ---------------------------------------------------------------------------

const crypto = require('crypto');
const { validateLicenseKey } = require('./_lib/license');
const { sbClient } = require('./_lib/courtlistener');

// Bookkeeping. Present on every one of these tables, cannot change a computed
// result, and `verified_by` in particular MUST be excluded: it is stamped from
// the caller's session at load time, so it records HOW a licence was loaded and
// not what the rule says. Leaving it in is what made 87 SAIRNlaw rules and 48
// calendars read as diverged when none of them had.
const INERT_COLUMNS = ['id', 'license_hash', 'app_id', 'created_at', 'updated_at', 'verified_by'];

// Same name shape as the platform divergence audit. Deliberately a SHAPE and
// not a list of tables: a new reference table is covered the day it is created.
const REFERENCE_TABLE = /^[a-z][a-z0-9_]*(_rules?|_rates?|_codes?|_requirements?|_holidays?|_standards?|_units)$/;
const IDENTIFIER = /^[a-z][a-z0-9_]*$/;

function stableJson(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(stableJson).join(',') + ']';
  return '{' + Object.keys(v).sort().map(
    (k) => JSON.stringify(k) + ':' + stableJson(v[k])).join(',') + '}';
}

// Key order is normalised away on purpose: two writes of the same content
// through different code paths can serialise in a different order, and
// reporting that as drift would train people to ignore this check.
//
// NULL-VALUED KEYS ARE DROPPED, which is load-bearing and not tidying. A
// nullable column the seed simply omits (`effective_to`, `role`,
// `facility_class`, `business_day_basis`) comes back from Postgres as an
// explicit null. Without this, every such row would read as drifted forever. A
// column that holds a REAL value live while the seed omits it still differs,
// because only the null side disappears.
function rowHash(row, idCol) {
  const out = {};
  for (const k of Object.keys(row)) {
    if (INERT_COLUMNS.indexOf(k) !== -1 || k === idCol) continue;
    if (row[k] === null || row[k] === undefined) continue;
    out[k] = row[k];
  }
  return crypto.createHash('sha256').update(stableJson(out)).digest('hex').slice(0, 16);
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) { res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } }); return; }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { res.status(400).json({ error: { message: 'Invalid JSON body' } }); return; }
  }
  if (!body || body.action !== 'fingerprint') {
    res.status(400).json({ error: { message: 'action must be: fingerprint' } });
    return;
  }

  // [{ table, id_col }] -- the caller names what it wants to compare, because
  // the checker is the thing that knows which seed files exist. Both values are
  // validated below; neither is trusted into SQL on the caller's say-so.
  const want = Array.isArray(body.tables) ? body.tables : [];
  if (!want.length) {
    res.status(400).json({ error: { message: 'tables must be a non-empty array of { table, id_col }' } });
    return;
  }
  if (want.length > 25) {
    res.status(400).json({ error: { message: 'at most 25 tables per request' } });
    return;
  }

  let lic;
  try { lic = await validateLicenseKey(licenseKey); }
  catch (err) {
    if (err.code === 'CONFIG') { console.error('reference-fingerprint config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    console.error('reference-fingerprint license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  let sb;
  try { sb = sbClient(); }
  catch (err) { console.error('reference-fingerprint supabase config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }

  const out = {};
  for (const spec of want) {
    const table = spec && spec.table;
    const idCol = (spec && spec.id_col) || 'rule_id';
    if (!REFERENCE_TABLE.test(String(table || ''))) {
      out[String(table)] = { ok: false, code: 'NOT_A_REFERENCE_TABLE',
        message: 'Only per-licence reference tables can be fingerprinted here, matched by name shape (…_rules, _rates, _codes, _requirements, _holidays, _standards, _units).' };
      continue;
    }
    if (!IDENTIFIER.test(String(idCol))) {
      out[table] = { ok: false, code: 'BAD_ID_COLUMN', message: 'id_col must be a plain lowercase identifier.' };
      continue;
    }
    try {
      const r = await fetch(sb.rest(table + '?license_hash=eq.' + encodeURIComponent(lic.license_hash) + '&select=*'), { headers: sb.headers });
      if (r.status === 404 || r.status === 400) {
        // The table does not exist, or does not carry license_hash. Reported
        // per table rather than failing the whole request: a checker asking
        // about five tables should not lose four answers to one absent one.
        out[table] = { ok: false, code: 'NOT_PROVISIONED',
          message: 'No such per-licence table, or it has no license_hash column. Run its schema file in Supabase.' };
        continue;
      }
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const rows = (await r.json()) || [];
      const missingId = rows.filter((x) => x && x[idCol] === undefined).length;
      if (missingId) {
        out[table] = { ok: false, code: 'NO_SUCH_ID_COLUMN',
          message: 'Column ' + idCol + ' is not present on ' + table + '.' };
        continue;
      }
      // The comparable column set, reported so the checker can build the
      // expected side over exactly the columns that exist rather than guessing
      // from the seed. It also lets the checker name a seed key that NO column
      // accepts -- the write paths in api/sd-data.js store an explicit column
      // list and silently discard anything else, so a seed field nobody stores
      // is a real finding that would otherwise be invisible from both ends.
      const columns = rows.length
        ? Object.keys(rows[0]).filter((k) => INERT_COLUMNS.indexOf(k) === -1 && k !== idCol).sort()
        : null;
      out[table] = {
        ok: true,
        columns,
        entries: rows.map((x) => ({ entry_id: String(x[idCol]), hash: rowHash(x, idCol) }))
          .sort((a, b) => (a.entry_id < b.entry_id ? -1 : a.entry_id > b.entry_id ? 1 : 0))
      };
    } catch (err) {
      console.error('reference-fingerprint read failed for ' + table + ':', err && err.message);
      out[table] = { ok: false, code: 'READ_FAILED', message: 'Could not read ' + table + ' — try again.' };
    }
  }

  res.status(200).json({
    ok: true,
    app_id: lic.app_id || null,
    algorithm: 'sha256/16 over the row minus [' + INERT_COLUMNS.join(', ') + '] and the id column, null-valued keys dropped, object keys sorted',
    tables: out,
    note: 'A hash that differs from the seed file means the stored row is not what the repo says it should be. That is drift whether or not any `version` field changed — the version fields on this platform are all 1, including on rows that corrections have since altered.'
  });
};
