// api/sairncare-witness.js
// ---------------------------------------------------------------------------
// THE WITNESSING LOCK for SAIRNcare controlled-substance COUNTS.
//
// Not a checker that flags a bad write and not a gate that blocks a push: a
// HARD WORKFLOW LOCK. The alf_mar count cannot fire at all until a DIFFERENT,
// currently-active, qualified employee has witnessed that exact record on the
// server.
//
// ── THE DEFECT ──────────────────────────────────────────────────────────────
// alf_mar records `witness_id` as a CALLER-SUPPLIED STRING. One employee alone
// can record a two-person count naming any colleague as the second signature.
// The browser refuses to save without a witness selected -- "A witness (second
// signature) is required for a controlled-substance count" -- and that is the
// whole control. The client is what an attacker replaces.
//
// api/sd-data.js already says so, in its own comment at the alf_mar write:
// "`witness_id` IS DELIBERATELY NOT HERE. It names a SECOND person who is by
// definition not the caller, so it cannot come from the session. SAIRNcare has
// no server-side witness verification at all, where SAIRNvet has
// api/sv-witness.js and a witness token -- that is a real and separate
// finding." This is that finding, closed.
//
// ── MODELLED ON api/sv-witness.js DELIBERATELY ─────────────────────────────
// Two apps must not grow two different answers to one question. The four
// properties that do the work are the same and are not restated here; read
// that file. THREE THINGS ARE DIFFERENT, and all three NARROW it:
//
//   1. ONLY entry_type 'count' IS LOCKED. An administration has one actor by
//      definition; a reconciliation and an assessment refusal have one author.
//      The count is the only MAR entry the regulation and the UI both treat as
//      a two-signature act. Locking all five would be a gate in front of doors
//      nobody meant to shut.
//
//   2. THE FIRST SIGNATURE IS ALREADY TRUSTWORTHY. `counted_by` has been
//      server-set since d6d7efd1, so only the SECOND is unverified. SAIRNvet
//      had to solve both at once; here half the problem is already solved, and
//      that changes the SHAPE: in SAIRNvet the requester IS the first
//      signature. Here the requester is the WITNESS -- the second person --
//      and the counter is whoever then performs the write.
//
//   3. A SELF-WITNESSED COUNT IS REFUSED, NOT FLAGGED. This diverges
//      deliberately from the sen_visits clock-correction decision made the same
//      day. There a flag was right: a one-person agency has nobody else and the
//      correction still has to be possible. Here, a count whose witness is the
//      counter is NOT A TWO-PERSON COUNT AT ALL, and recording it as one is the
//      false record. A shift that cannot produce a second person defers the
//      count -- which `require_two_person = false` already permits, WITHOUT
//      claiming a signature nobody gave.
//
// ── WHO MAY WITNESS ─────────────────────────────────────────────────────────
// owner and nursing -- the same set api/sd-data.js already calls
// ALF_MAR_ORDER_ROLES for clinical-decision entry types. DELIBERATELY EXCLUDES
// med_aide, who may perform and record a count but is not the clinical second
// signature on a controlled substance. Re-typing role names in two places is
// the drift this platform has already paid for once, so the list is derived
// from api/_lib/auth.js's own vocabulary and checked against it at load.
//
// ── WHAT THIS DOES NOT CLAIM ────────────────────────────────────────────────
// A witness attests that somebody looked. It does not attest that they were
// right. Electronic witnessing exists because independent double-review has a
// measured, non-zero failure rate -- an argument for the mechanism and equally
// an argument against believing the mechanism makes anything safe.
//
// NO GOVERNING REGULATION WAS READ. Whether a specific state requires a second
// signature on a personal-care-home controlled-substance count, and who may
// give it, is a legal question this file does not answer.
//
// Actions, all POST, licence via Authorization: Bearer, session via X-SD-Auth:
//
//   policy       {}                          -> { require_two_person }
//   set_policy   { require_two_person }        (owner)
//   request      { resource, payload }       -> { token, expires_at }
//   countersign  { token }                     (a DIFFERENT qualified employee)
//
// REQUIRES sql/sairncare_witness_schema.sql AND
// sql/sairncare_employee_auth_schema.sql.
// ---------------------------------------------------------------------------

const crypto = require('crypto');
const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest, ROLES_BY_APP, roleSet } = require('./_lib/auth');

const APP = 'sairncare';
const POLICY_TABLE = 'sairncare_witness_policy';
const TOKEN_TABLE = 'sairncare_witness_tokens';
const EMPLOYEE_TABLE = 'sairncare_employee_auth';

// Checked against the app's OWN vocabulary at load, so a role renamed in
// api/_lib/auth.js cannot leave a silently-empty set here -- which would be a
// lock that refuses everybody, or worse, a countersign check comparing against
// names nobody holds.
const WITNESS_ROLE_NAMES = ['owner', 'nursing'];
(function assertRolesExist() {
  const known = ROLES_BY_APP[APP] || [];
  const unknown = WITNESS_ROLE_NAMES.filter((r) => known.indexOf(r) === -1);
  if (unknown.length) {
    throw new Error('sairncare-witness: role(s) ' + unknown.join(', ')
      + ' are not in ROLES_BY_APP.' + APP + '. A witness role list that names '
      + 'nobody is a lock that refuses everybody.');
  }
}());
const WITNESS_ROLES = roleSet({ owner: true, nursing: true });
const PROVISIONING_ROLES = ['owner'];

// ONLY the count. A list rather than a literal so widening it is a visible,
// reviewable change and not a condition somebody loosens.
const LOCKED_RESOURCES = { alf_mar: true };
const LOCKED_ENTRY_TYPES = { count: true };

// Ten minutes, as SAIRNvet. Long enough to read a record back and confirm it,
// short enough that a signature stays attached to the act it witnessed.
const TOKEN_TTL_MS = 10 * 60 * 1000;
const ACTIONS = ['policy', 'set_policy', 'request', 'countersign'];

// ── THE CANONICAL FORM IS THE WHOLE BINDING ─────────────────────────────────
// Two JSON encodings of the same record must produce the same hash or the write
// refuses a token legitimately issued; two DIFFERENT records must never collide
// or the lock is decorative. Keys sorted recursively and NOTHING else
// normalised -- no trimming, no case folding, no dropping of nulls. A record
// differing only in whitespace inside a STRING is a different record, and
// deciding otherwise here would be this file quietly editing a
// controlled-substance entry.
function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  const keys = Object.keys(value).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
}
function contentHash(resource, payload) {
  // The RESOURCE is inside the hash. Without it a token issued for one table
  // could be spent on another -- the content-binding hole wearing a hat.
  return crypto.createHash('sha256')
    .update(String(resource) + '\n' + canonical(payload))
    .digest('hex');
}
function hashToken(tok) {
  return crypto.createHash('sha256').update(String(tok)).digest('hex');
}
function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}
function notProvisioned() {
  return { error: { code: 'NOT_PROVISIONED',
    message: 'The SAIRNcare witnessing tables are not set up yet — run '
      + 'sql/sairncare_witness_schema.sql in Supabase first.' } };
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) {
    res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('sairncare-witness: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  // Envelope gate BELOW licence validation -- see api/sv-auth.js's note and
  // api/preauth-envelope-ordering.test.js.
  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') {
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  body = body || {};
  const action = body.action;
  if (ACTIONS.indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: ' + ACTIONS.join(', ') } });
    return;
  }

  const licHash = lic.license_hash;
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  // THE CALLER MUST BE A LIVE, ACTIVE EMPLOYEE -- not merely the holder of a
  // token that says so. A session outlives its credential's deactivation by up
  // to 12h, and a witness signature from a revoked account is worse than no
  // signature: it carries a name that no longer means anything.
  async function activeCaller() {
    const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
    if (!caller) return null;
    const r = await fetch(rest(EMPLOYEE_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&employee_id=eq.' + enc(caller.employee_id) +
      '&active=eq.true&select=employee_id,role&limit=1'), { headers });
    const rows = await r.json();
    if (!r.ok) { const e = new Error('caller lookup failed'); e.detail = rows; throw e; }
    const row = (Array.isArray(rows) && rows[0]) || null;
    if (!row) return null;
    // ROLE FROM THE DATABASE ROW, not from the token, so a demotion takes
    // effect at once rather than waiting out the token's life.
    return { employee_id: row.employee_id, role: row.role };
  }

  async function readPolicy() {
    const r = await fetch(rest(POLICY_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&select=require_two_person&limit=1'), { headers });
    const rows = await r.json();
    if (!r.ok) { const e = new Error('policy read failed'); e.detail = rows; throw e; }
    const row = (Array.isArray(rows) && rows[0]) || null;
    // ABSENT MEANS SINGLE-OPERATOR, and that is the safe default to be missing:
    // a facility that never configured this is not silently held to a rule it
    // cannot meet. A facility that turned it ON has a row saying so.
    return { require_two_person: !!(row && row.require_two_person === true), configured: !!row };
  }

  try {
    if (action === 'policy') {
      const caller = await activeCaller();
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const p = await readPolicy();
      res.status(200).json({ ok: true, require_two_person: p.require_two_person, configured: p.configured });
      return;
    }

    if (action === 'set_policy') {
      const caller = await activeCaller();
      if (!caller || PROVISIONING_ROLES.indexOf(caller.role) === -1) {
        res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Only an Owner can change the witnessing policy' } });
        return;
      }
      if (typeof body.require_two_person !== 'boolean') {
        res.status(400).json({ error: { message: 'require_two_person must be true or false' } });
        return;
      }
      const r = await fetch(rest(POLICY_TABLE + '?on_conflict=license_hash'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash, require_two_person: body.require_two_person,
          updated_by: caller.employee_id, updated_at: new Date().toISOString()
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      res.status(200).json({ ok: true, require_two_person: body.require_two_person });
      return;
    }

    if (action === 'request') {
      const caller = await activeCaller();
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!WITNESS_ROLES[caller.role]) {
        res.status(403).json({
          error: {
            code: 'NOT_A_WITNESS_ROLE',
            message: 'Only an Owner or Nursing can witness a controlled-substance count. '
              + 'A medication aide may perform and record the count, but is not the '
              + 'clinical second signature.'
          }
        });
        return;
      }
      const resource = String(body.resource || '');
      if (!LOCKED_RESOURCES[resource]) {
        res.status(400).json({ error: { message: 'resource must be one of: ' + Object.keys(LOCKED_RESOURCES).join(', ') } });
        return;
      }
      if (!body.payload || typeof body.payload !== 'object') {
        res.status(400).json({ error: { message: 'payload is required and must be the exact record to be written' } });
        return;
      }
      // THE NARROWING, ENFORCED AT THE MINT RATHER THAN ONLY AT THE SPEND. A
      // token for an administration should not exist at all -- issuing one and
      // then refusing to honour it would leave a row in the token table
      // claiming a witnessing of something that is not witnessed.
      if (!LOCKED_ENTRY_TYPES[String(body.payload.entry_type || '')]) {
        res.status(400).json({
          error: {
            message: 'Only a controlled-substance count is witnessed. entry_type must be '
              + 'one of: ' + Object.keys(LOCKED_ENTRY_TYPES).join(', ')
              + '. An administration has one actor by definition.'
          }
        });
        return;
      }
      const tok = crypto.randomBytes(32).toString('base64url');
      const expires = new Date(Date.now() + TOKEN_TTL_MS).toISOString();
      const r = await fetch(rest(TOKEN_TABLE), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify({
          license_hash: licHash,
          token_hash: hashToken(tok),
          content_hash: contentHash(resource, body.payload),
          witness_employee_id: caller.employee_id,
          witness_role: caller.role,
          expires_at: expires
        })
      });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const policy = await readPolicy();
      // THE TOKEN IS RETURNED ONCE AND STORED HASHED. There is no way to read
      // it back; a lost token is re-requested, which costs one confirmation
      // rather than leaving a readable table of live signatures.
      res.status(200).json({
        ok: true, token: tok, expires_at: expires,
        require_two_person: policy.require_two_person,
        countersigned: false,
        witness_employee_id: caller.employee_id
      });
      return;
    }

    if (action === 'countersign') {
      const caller = await activeCaller();
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!WITNESS_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'NOT_A_WITNESS_ROLE', message: 'Only an Owner or Nursing can countersign.' } });
        return;
      }
      const tok = String(body.token || '');
      if (!tok) { res.status(400).json({ error: { message: 'token is required' } }); return; }
      const r = await fetch(rest(TOKEN_TABLE + '?license_hash=eq.' + enc(licHash) +
        '&token_hash=eq.' + enc(hashToken(tok)) +
        '&select=id,witness_employee_id,countersign_employee_id,spent_at,expires_at&limit=1'), { headers });
      const rows = await r.json();
      if (!r.ok) return upstream(res, rows);
      const row = (Array.isArray(rows) && rows[0]) || null;
      if (!row) { res.status(404).json({ error: { code: 'NO_SUCH_TOKEN', message: 'That confirmation is not recognised.' } }); return; }
      if (row.spent_at) { res.status(409).json({ error: { code: 'ALREADY_SPENT', message: 'That confirmation has already been used.' } }); return; }
      if (new Date(row.expires_at).getTime() <= Date.now()) {
        res.status(409).json({ error: { code: 'EXPIRED', message: 'That confirmation has expired — confirm the record again.' } });
        return;
      }
      // A COUNTERSIGNATURE BY THE WITNESS IS NOT A COUNTERSIGNATURE. This is
      // the entire content of "two person", and without it the setting is a
      // second click by the same hand. The schema's
      // scwit_witness_is_not_countersigner check enforces the same fact, because
      // an application-only check shares state with the thing it checks.
      if (row.witness_employee_id === caller.employee_id) {
        res.status(409).json({
          error: {
            code: 'SAME_PERSON',
            message: 'A second person must countersign. You confirmed this record yourself.'
          }
        });
        return;
      }
      if (row.countersign_employee_id) {
        res.status(409).json({ error: { code: 'ALREADY_COUNTERSIGNED', message: 'That record has already been countersigned.' } });
        return;
      }
      const patch = await fetch(rest(TOKEN_TABLE + '?id=eq.' + enc(row.id)), {
        method: 'PATCH', headers,
        body: JSON.stringify({ countersign_employee_id: caller.employee_id, countersign_role: caller.role })
      });
      // Only parse on failure: PostgREST answers a PATCH 204 No Content unless
      // return=representation is set, and parsing unconditionally turns a landed
      // write into a 502. Proven live on rf-auth 2026-08-27.
      if (!patch.ok) { const d = await patch.json().catch(() => null); return upstream(res, d); }
      res.status(200).json({ ok: true, countersigned: true, countersign_employee_id: caller.employee_id });
      return;
    }
  } catch (err) {
    if (err && isMissingTable(err.detail)) {
      res.status(503).json(notProvisioned());
      return;
    }
    console.error('api/sairncare-witness error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
};

// ── THE HALF api/sd-data.js CALLS ───────────────────────────────────────────
// Exported rather than duplicated at the write site: a second implementation of
// "is this witnessed" is a second place for the answer to drift, and the whole
// point is that there is exactly one gate.
//
// IT RETURNS A REFUSAL OR NULL. Never a boolean -- a boolean invites
// `if (!ok) { /* log and continue */ }`, and this must be the thing that stops
// the write rather than a fact about it.
async function requireWitness(ctx) {
  const { resource, payload, licHash, rest, headers, token, callerEmployeeId } = ctx;
  const enc = encodeURIComponent;
  if (!LOCKED_RESOURCES[resource]) return null;             // not a locked resource
  // ONLY THE COUNT. Checked on the payload rather than on a flag the caller
  // sets, and checked here as well as at the mint, because the mint is the
  // convenience and this is the gate.
  if (!payload || !LOCKED_ENTRY_TYPES[String(payload.entry_type || '')]) return null;

  if (!token) {
    return { status: 403, body: { error: { code: 'WITNESS_REQUIRED',
      message: 'A controlled-substance count needs a second signature recorded on the '
        + 'server before it can be saved. Have a nurse or the owner confirm this exact '
        + 'count, then save.' } } };
  }
  const r = await fetch(rest(TOKEN_TABLE + '?license_hash=eq.' + enc(licHash) +
    '&token_hash=eq.' + enc(hashToken(token)) +
    '&select=id,content_hash,witness_employee_id,countersign_employee_id,spent_at,expires_at&limit=1'), { headers });
  const rows = await r.json();
  if (!r.ok) {
    // A FAILED CHECK IS NOT "VERIFIED". It is also not "unwitnessed" -- it is
    // could-not-tell, and the only safe answer to could-not-tell on an
    // append-only MAR with no delete verb is refusal.
    if (isMissingTable(rows)) {
      return { status: 503, body: { error: { code: 'NOT_PROVISIONED',
        message: 'The SAIRNcare witnessing tables are not set up yet — run '
          + 'sql/sairncare_witness_schema.sql. The count was refused rather than '
          + 'filed unwitnessed.' } } };
    }
    return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
      message: 'The second signature could not be verified, so nothing was written. '
        + 'This is not the same as the count being unconfirmed.' } } };
  }
  const row = (Array.isArray(rows) && rows[0]) || null;
  if (!row) {
    return { status: 403, body: { error: { code: 'WITNESS_REQUIRED',
      message: 'That confirmation is not recognised.' } } };
  }
  if (row.spent_at) {
    return { status: 409, body: { error: { code: 'WITNESS_ALREADY_SPENT',
      message: 'That confirmation has already been used. Each confirmation covers '
        + 'exactly one count.' } } };
  }
  if (new Date(row.expires_at).getTime() <= Date.now()) {
    return { status: 409, body: { error: { code: 'WITNESS_EXPIRED',
      message: 'That confirmation has expired — confirm the count again.' } } };
  }
  // ── THE SAIRNCARE-SPECIFIC REFUSAL ────────────────────────────────────────
  // A SELF-WITNESSED COUNT IS REFUSED, NOT FLAGGED. `counted_by` is stamped
  // from the writing session, so the counter is exactly `callerEmployeeId`. A
  // count whose witness is the counter is not a two-person count at all, and
  // recording it as one is the false record -- which is why this diverges from
  // the sen_visits flag decision made the same day.
  //
  // IT REFUSES WHEN IT CANNOT TELL, TOO. An absent callerEmployeeId means the
  // write site did not pass one, and allowing the count then would make this
  // check silently optional at exactly the site it exists to protect.
  if (!callerEmployeeId) {
    return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
      message: 'The identity of the person recording this count could not be read, so '
        + 'nothing was written. A count cannot be witnessed by an unknown counter.' } } };
  }
  if (row.witness_employee_id === callerEmployeeId) {
    return { status: 403, body: { error: { code: 'SELF_WITNESS_REFUSED',
      message: 'You confirmed this count yourself. A controlled-substance count needs a '
        + 'SECOND person — have a colleague confirm it, or defer the count. It was not '
        + 'saved, and it was not saved as a one-person count either.' } } };
  }
  // THE CONTENT BINDING. Recomputed from the payload actually being written, so
  // a token issued for one count cannot be spent on another, and editing the
  // numbers after witnessing invalidates it.
  if (row.content_hash !== contentHash(resource, payload)) {
    return { status: 409, body: { error: { code: 'WITNESS_CONTENT_MISMATCH',
      message: 'This is not the count that was confirmed. Confirm this count before '
        + 'saving it.' } } };
  }
  const policy = await (async () => {
    const pr = await fetch(rest(POLICY_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&select=require_two_person&limit=1'), { headers });
    const prows = await pr.json();
    if (!pr.ok) return null;                                // could-not-tell
    const prow = (Array.isArray(prows) && prows[0]) || null;
    return { require_two_person: !!(prow && prow.require_two_person === true) };
  })();
  if (!policy) {
    return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
      message: 'The witnessing policy could not be read, so nothing was written. '
        + 'Refusing rather than assuming the weaker rule.' } } };
  }
  if (policy.require_two_person && !row.countersign_employee_id) {
    return { status: 403, body: { error: { code: 'COUNTERSIGN_REQUIRED',
      message: 'This facility requires a second confirmation before a '
        + 'controlled-substance count can be saved.' } } };
  }
  // ── THE SETTLING STEP ────────────────────────────────────────────────────
  // Everything above re-checks the TOKEN. Not one of those is a fact about the
  // WORLD, and between the confirmation and the write the world has up to
  // TOKEN_TTL_MS to move. The TTL is a DEADLINE, and a deadline re-verifies
  // nothing.
  //
  // THE REACHABLE CASE: a nurse confirms a count, is dismissed, and the write
  // still lands carrying their name inside the next ten minutes -- on a MAR a
  // state surveyor reads, append-only, with no delete verb, where a correction
  // is a SECOND row and the wrong one stands forever.
  const attesters = [row.witness_employee_id];
  if (row.countersign_employee_id) attesters.push(row.countersign_employee_id);
  for (const who of attesters) {
    if (!who) continue;
    const ar = await fetch(rest(EMPLOYEE_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&employee_id=eq.' + enc(who) + '&active=eq.true&select=employee_id&limit=1'),
      { headers });
    const arows = await ar.json().catch(() => null);
    if (!ar.ok) {
      return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
        message: 'Whether the confirming employee is still active could not be verified, '
          + 'so nothing was written. This is not the same as the count being '
          + 'unconfirmed.' } } };
    }
    if (!(Array.isArray(arows) && arows[0])) {
      return { status: 403, body: { error: { code: 'WITNESS_NO_LONGER_ACTIVE',
        message: 'The employee who confirmed this count is no longer active. Confirm it '
          + 'again with a current employee — the count was not saved.' } } };
    }
  }
  // SPEND IT BEFORE THE WRITE, NOT AFTER. If the write then fails the token is
  // burned and the count must be confirmed again -- which is the direction to
  // fail in. Spending afterwards leaves a window where a retry reuses the same
  // signature, and a reusable signature is the defect this exists to prevent.
  const spend = await fetch(rest(TOKEN_TABLE + '?id=eq.' + enc(row.id) + '&spent_at=is.null'), {
    method: 'PATCH',
    headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
    body: JSON.stringify({
      spent_at: new Date().toISOString(),
      spent_on_resource: resource,
      spent_on_entry_id: payload && payload.id ? String(payload.id) : null
    })
  });
  const spent = await spend.json().catch(() => null);
  if (!spend.ok) {
    return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
      message: 'The confirmation could not be recorded as used, so nothing was written.' } } };
  }
  // `&spent_at=is.null` makes the spend a COMPARE-AND-SET: two concurrent
  // writes racing the same token, one wins and the other gets zero rows back.
  // Without this the check-then-spend gap is exactly wide enough for a double
  // submit to write two controlled-substance counts on one signature.
  if (!Array.isArray(spent) || spent.length === 0) {
    return { status: 409, body: { error: { code: 'WITNESS_ALREADY_SPENT',
      message: 'That confirmation was used by another request a moment ago. Confirm the '
        + 'count again.' } } };
  }
  return null;                                              // witnessed. proceed.
}

function upstream(res, detail) {
  console.error('sairncare-witness upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json(notProvisioned());
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}

module.exports.requireWitness = requireWitness;
module.exports.contentHash = contentHash;
module.exports.canonical = canonical;
module.exports.LOCKED_RESOURCES = LOCKED_RESOURCES;
module.exports.LOCKED_ENTRY_TYPES = LOCKED_ENTRY_TYPES;
module.exports.WITNESS_ROLES = WITNESS_ROLES;
module.exports.TOKEN_TTL_MS = TOKEN_TTL_MS;
