// api/sv-witness.js
// ---------------------------------------------------------------------------
// THE WITNESSING LOCK for SAIRNvet's controlled-substance register.
//
// Not a checker that flags a bad write and not a gate that blocks a push: a
// HARD WORKFLOW LOCK. The write cannot fire at all until the verification step
// for that exact record completes, the way an embryology system will not let
// the next handling step begin until the current one is scanned.
//
// ── WHY sv_controlled AND NOTHING ELSE ──────────────────────────────────────
// `python tools/removal_path_check.py --burn-down` ranks it TIER A WITH NO
// REMOVAL PATH, and api/_resources/sairnvet.js calls it "the
// controlled-substance register (DEA-relevant)". A wrong row cannot be taken
// back through the product: a correction is a SECOND row and the wrong one
// stands forever. That is the right shape for a regulated record and it is
// precisely why verification has to precede the write.
//
// The other ~14 append-only resources across the platform are Class A in
// docs/2026-09-13-irreversible-write-witnessing-scoping.md and are a later,
// separately-sized piece. Class B -- the 53 Tier A resources with no removal
// path -- is a DIFFERENT problem needing a removal path, and a lock there
// would be a gate in front of a door nobody meant to shut.
//
// ── WHAT THE RESEARCH ACTUALLY SAYS, BOTH HALVES ────────────────────────────
// Electronic witnessing exists because even INDEPENDENT DOUBLE-REVIEW has a
// measured, non-zero failure rate where mistakes cannot be undone. That is an
// argument for a lock. It is equally an argument against believing a lock
// makes anything safe, and this file says so in its refusals rather than
// implying a confirmed write is a correct one. A witness attests that somebody
// looked; it does not attest that they were right.
//
// ── THE DECISION THIS IMPLEMENTS (Michael, 2026-09-13) ──────────────────────
// SINGLE-OPERATOR CONFIRM NOW, witness identity recorded in the token,
// TWO-PERSON AS A PER-LICENCE SETTING rather than a platform policy. Both
// options are defensible and that is why it is a setting: a single-operator
// confirm is weaker, because the person who erred is the person confirming; a
// true second witness is not a workflow a one-vet practice can produce at all.
// The mechanism and the schema are built for two from the start, so a practice
// that can staff it turns it on and the code path does not change.
//
// ── THE THREE PROPERTIES, EACH LEARNED HERE THE HARD WAY ────────────────────
//   1. The token is bound to a HASH OF THE RECORD, not to "a write is coming".
//      A token bound to the event can be spent on a different record -- the
//      same class as a session token outliving its credential, one layer over.
//   2. CHECKED AGAINST THE TABLE, never an in-memory map. This runs
//      serverless; a second request is a second process and anything held in
//      memory is already gone. api/sairndental/public-complaint-submit.js
//      records exactly this.
//   3. A FAILED CHECK REFUSES rather than writing unwitnessed. A failed check
//      is not the same answer as "verified", and the same endpoint records
//      that too -- it answers 503 rather than filing unchecked.
//
// ── WHO MAY WITNESS ─────────────────────────────────────────────────────────
// PRESCRIBER_ROLES from api/sv-auth.js -- owner and dvm, the licensed
// veterinarians. IMPORTED, never re-listed: re-typing role names in two places
// is the drift that cost SAIRNsenior a real bug, and here the two places would
// be an access-control surface and a DEA-relevant register. It deliberately
// excludes 'manager': a Practice Manager runs the office and is not a
// clinician, and a controlled-substance entry is a legal act by a licensed
// veterinarian.
//
// Actions, all POST, licence via Authorization: Bearer, session via X-SD-Auth:
//
//   policy         {}                                    -> { require_two_person }
//   set_policy     { require_two_person }                 (owner)
//   request        { resource, payload }                 -> { token, expires_at }
//   countersign    { token }                              (a DIFFERENT prescriber)
//
// REQUIRES sql/sairnvet_witness_schema.sql AND
// sql/sairnvet_employee_auth_schema.sql.
// ---------------------------------------------------------------------------

const crypto = require('crypto');
const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');
const svAuth = require('./sv-auth');

const APP = 'sairnvet';
const POLICY_TABLE = 'sairnvet_witness_policy';
const TOKEN_TABLE = 'sairnvet_witness_tokens';
const EMPLOYEE_TABLE = svAuth.EMPLOYEE_TABLE;
// The ONE resource this lock covers. A list rather than a literal so widening
// it is a visible, reviewable change and not a condition somebody loosens.
const LOCKED_RESOURCES = { sv_controlled: true };
// Ten minutes. Long enough to read a record back and confirm it, short enough
// that a signature stays attached to the act it witnessed.
const TOKEN_TTL_MS = 10 * 60 * 1000;
const ACTIONS = ['policy', 'set_policy', 'request', 'countersign'];

// ── THE CANONICAL FORM IS THE WHOLE BINDING ─────────────────────────────────
// Two JSON encodings of the same record must produce the same hash or the
// write endpoint refuses a token that was legitimately issued; two DIFFERENT
// records must never collide or the lock is decorative. Keys are sorted
// recursively and nothing else is normalised -- no trimming, no case folding,
// no dropping of nulls. A record differing only in whitespace inside a STRING
// is a different record, and deciding otherwise here would be this file
// quietly editing a controlled-substance entry.
function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  const keys = Object.keys(value).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
}
function contentHash(resource, payload) {
  // The RESOURCE is inside the hash. Without it a token issued for one table
  // could be spent on another, which is the content-binding hole wearing a
  // different hat.
  return crypto.createHash('sha256')
    .update(String(resource) + '\n' + canonical(payload))
    .digest('hex');
}
function hashToken(tok) {
  return crypto.createHash('sha256').update(String(tok)).digest('hex');
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
    console.error('sv-witness: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  // Envelope gate BELOW licence validation, from the first commit -- see
  // api/sv-auth.js's note and api/preauth-envelope-ordering.test.js.
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
    // ABSENT MEANS SINGLE-OPERATOR, and that is the safe default to be
    // missing: a practice that never configured this is not silently held to a
    // rule it cannot meet. A practice that turned it ON has a row saying so.
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
      if (!caller || svAuth.PROVISIONING_ROLES.indexOf(caller.role) === -1) {
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
      // THE TIER IS IMPORTED. A controlled-substance entry is a legal act by a
      // licensed veterinarian, and re-typing the role list here is the drift
      // this platform has already paid for once.
      if (!svAuth.isPrescriber(caller)) {
        res.status(403).json({
          error: {
            code: 'NOT_A_PRESCRIBER',
            message: 'Only a licensed veterinarian (Owner/DVM or Associate DVM) can witness a controlled-substance entry.'
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
      if (!svAuth.isPrescriber(caller)) {
        res.status(403).json({ error: { code: 'NOT_A_PRESCRIBER', message: 'Only a licensed veterinarian can countersign.' } });
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
      // A COUNTERSIGNATURE BY THE AUTHOR IS NOT A COUNTERSIGNATURE. This is the
      // entire content of "two person", and without it the setting is a second
      // click by the same hand.
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
      // return=representation is set, and parsing unconditionally turns a
      // landed write into a 502. Proven live on rf-auth 2026-08-27.
      if (!patch.ok) { const d = await patch.json().catch(() => null); return upstream(res, d); }
      res.status(200).json({ ok: true, countersigned: true, countersign_employee_id: caller.employee_id });
      return;
    }
  } catch (err) {
    if (err && isMissingTable(err.detail)) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The SAIRNvet witnessing tables are not set up yet — run sql/sairnvet_witness_schema.sql' } });
      return;
    }
    console.error('api/sv-witness error:', err);
    res.status(502).json({ error: { message: 'Upstream error — try again' } });
    return;
  }
};

// ── THE HALF api/sd-data.js CALLS ───────────────────────────────────────────
// Exported rather than duplicated at the write site: a second implementation of
// "is this witnessed" is a second place for the answer to drift, and the whole
// point is that there is exactly one gate.
//
// IT RETURNS A REFUSAL OR NULL. Never a boolean -- a boolean invites `if
// (!ok) { /* log and continue */ }`, and this must be the thing that stops the
// write rather than a fact about it.
async function requireWitness(ctx) {
  const { resource, payload, licHash, rest, headers, token } = ctx;
  const enc = encodeURIComponent;
  if (!LOCKED_RESOURCES[resource]) return null;          // not a locked resource

  if (!token) {
    return { status: 403, body: { error: { code: 'WITNESS_REQUIRED',
      message: 'This is the controlled-substance register. Confirm the record first — the write cannot proceed without it.' } } };
  }
  const r = await fetch(rest(TOKEN_TABLE + '?license_hash=eq.' + enc(licHash) +
    '&token_hash=eq.' + enc(hashToken(token)) +
    '&select=id,content_hash,witness_employee_id,countersign_employee_id,spent_at,expires_at&limit=1'), { headers });
  const rows = await r.json();
  if (!r.ok) {
    // A FAILED CHECK IS NOT "VERIFIED". It is also not "unwitnessed" -- it is
    // could-not-tell, and the only safe answer to could-not-tell on an
    // irreversible write is refusal.
    if (isMissingTable(rows)) {
      return { status: 503, body: { error: { code: 'NOT_PROVISIONED',
        message: 'The SAIRNvet witnessing tables are not set up yet — run sql/sairnvet_witness_schema.sql. The write was refused rather than filed unwitnessed.' } } };
    }
    return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
      message: 'The confirmation could not be verified, so nothing was written. This is not the same as the record being unconfirmed.' } } };
  }
  const row = (Array.isArray(rows) && rows[0]) || null;
  if (!row) {
    return { status: 403, body: { error: { code: 'WITNESS_REQUIRED', message: 'That confirmation is not recognised.' } } };
  }
  if (row.spent_at) {
    return { status: 409, body: { error: { code: 'WITNESS_ALREADY_SPENT',
      message: 'That confirmation has already been used. Each confirmation covers exactly one write.' } } };
  }
  if (new Date(row.expires_at).getTime() <= Date.now()) {
    return { status: 409, body: { error: { code: 'WITNESS_EXPIRED',
      message: 'That confirmation has expired — confirm the record again.' } } };
  }
  // THE CONTENT BINDING. Recomputed from the payload actually being written,
  // so a token issued for one record cannot be spent on another.
  if (row.content_hash !== contentHash(resource, payload)) {
    return { status: 409, body: { error: { code: 'WITNESS_CONTENT_MISMATCH',
      message: 'This is not the record that was confirmed. Confirm this record before saving it.' } } };
  }
  const policy = await (async () => {
    const pr = await fetch(rest(POLICY_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&select=require_two_person&limit=1'), { headers });
    const prows = await pr.json();
    if (!pr.ok) return null;          // could-not-tell, handled below
    const prow = (Array.isArray(prows) && prows[0]) || null;
    return { require_two_person: !!(prow && prow.require_two_person === true) };
  })();
  if (!policy) {
    return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
      message: 'The witnessing policy could not be read, so nothing was written. Refusing rather than assuming the weaker rule.' } } };
  }
  if (policy.require_two_person && !row.countersign_employee_id) {
    return { status: 403, body: { error: { code: 'COUNTERSIGN_REQUIRED',
      message: 'This practice requires a second licensed veterinarian to countersign before this record can be saved.' } } };
  }
  // ── THE SETTLING STEP. Item 101, added 2026-09-14. ───────────────────────
  // Everything above this line re-checks the TOKEN -- that it exists, is
  // unspent, is unexpired, covers THIS payload, and carries the countersign the
  // policy demands. Not one of those is a fact about the WORLD, and between the
  // confirmation and the write the world has up to TOKEN_TTL_MS to move.
  //
  // THE SHAPE IS NASA'S DOCKING SEQUENCE AND THE MIDDLE PHASE WAS MISSING. Soft
  // capture, then ATTENUATION -- damp the relative motion and re-check
  // alignment, still able to back out -- and only then hard capture. This lock
  // had soft capture (`request`) and hard capture (`spend` + write) with
  // nothing between them. The TTL is not an attenuation phase; it is a
  // DEADLINE, and a deadline re-verifies nothing.
  //
  // THE REACHABLE CASE, and this file already names the hazard 300 lines above
  // in activeCaller(): "a witness signature from a revoked account is worse
  // than no signature: it carries a name that no longer means anything."
  // activeCaller() is called on `policy`, `set_policy`, `request` and
  // `countersign` -- and was never called here. So a vet could confirm a
  // controlled-substance entry, be deactivated (struck off, dismissed, licence
  // pulled -- exactly when deactivation is urgent), and the write would still
  // land attributed to them inside the next ten minutes. On a DEA-relevant,
  // append-only register with no removal path, where a correction is a SECOND
  // row and the wrong one stands forever.
  //
  // It re-reads the WITNESS from the token row rather than the current caller,
  // which is the stronger check: it is the attester's standing that the record
  // claims, not the saver's.
  const attesters = [row.witness_employee_id];
  if (row.countersign_employee_id) attesters.push(row.countersign_employee_id);
  for (const who of attesters) {
    if (!who) continue;
    const ar = await fetch(rest(EMPLOYEE_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&employee_id=eq.' + enc(who) + '&active=eq.true&select=employee_id&limit=1'),
      { headers });
    const arows = await ar.json().catch(() => null);
    if (!ar.ok) {
      // Could-not-tell, on an irreversible write. Same answer as every other
      // could-not-tell in this function.
      return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
        message: 'Whether the confirming employee is still active could not be verified, so nothing was written. This is not the same as the record being unconfirmed.' } } };
    }
    if (!(Array.isArray(arows) && arows[0])) {
      return { status: 403, body: { error: { code: 'WITNESS_NO_LONGER_ACTIVE',
        message: 'The employee who confirmed this record is no longer active. Confirm it again with a current employee — the record was not saved.' } } };
    }
  }
  // SPEND IT BEFORE THE WRITE, NOT AFTER. If the write then fails the token is
  // burned and the record must be confirmed again -- which is the direction to
  // fail in. Spending afterwards leaves a window where a retry reuses the same
  // signature, and a reusable signature is the defect this exists to prevent.
  const spend = await fetch(rest(TOKEN_TABLE + '?id=eq.' + enc(row.id) + '&spent_at=is.null'), {
    method: 'PATCH',
    headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
    body: JSON.stringify({ spent_at: new Date().toISOString(), spent_on_resource: resource })
  });
  const spent = await spend.json().catch(() => null);
  if (!spend.ok) {
    return { status: 503, body: { error: { code: 'WITNESS_CHECK_FAILED',
      message: 'The confirmation could not be recorded as used, so nothing was written.' } } };
  }
  // `&spent_at=is.null` makes the spend a COMPARE-AND-SET: two concurrent
  // writes racing the same token, one wins and the other gets zero rows back.
  // Without this the check-then-spend gap is exactly wide enough for a double
  // submit to write two controlled-substance rows on one signature.
  if (!Array.isArray(spent) || spent.length === 0) {
    return { status: 409, body: { error: { code: 'WITNESS_ALREADY_SPENT',
      message: 'That confirmation was used by another request a moment ago. Confirm the record again.' } } };
  }
  return null;                                            // witnessed. proceed.
}

function isMissingTable(detail) {
  const s = JSON.stringify(detail || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('does not exist') !== -1;
}
function upstream(res, detail) {
  console.error('sv-witness upstream error:', detail);
  if (isMissingTable(detail)) {
    res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'The SAIRNvet witnessing tables are not set up yet — run sql/sairnvet_witness_schema.sql' } });
    return;
  }
  res.status(502).json({ error: { message: 'Data store error — try again' } });
}

module.exports.requireWitness = requireWitness;
module.exports.contentHash = contentHash;
module.exports.canonical = canonical;
module.exports.LOCKED_RESOURCES = LOCKED_RESOURCES;
module.exports.TOKEN_TTL_MS = TOKEN_TTL_MS;
