// api/law-attest.js
// ---------------------------------------------------------------------------
// THE IOLTA RECONCILIATION ATTESTATION -- the route.
//
// Policy and validation: api/_lib/law-attest.js (pure, no I/O).
// Record and setting:    sql/sairnlaw_trust_attestations.sql.
// Design:                docs/2026-10-19-hank-b21-attestation-design.md.
// Concept, stated before the code: docs/2026-10-19-hank-b23-notes.md item 3.
//
//   A completed three-way reconciliation becomes an ATTESTED record only when
//   a bar-admitted person signs a hash of the exact comparison that was run; a
//   firm that has EXACTLY ONE active owner/attorney may switch on a per-firm
//   single-signer setting and attest alone, and every attestation taken that
//   way is stored as signer_mode 'single'.
//
// ── WHY THIS IS A SECOND ROUTE AND NOT A RESOURCE ON api/law-countersign.js ─
// The design note expected `law_trust_attestation` to join that file's
// `lockedResources`. IT DOES NOT, and the reason is a real constraint rather
// than a preference: that profile carries ONE `preparerRoles` for every
// resource it locks -- `LAW_TRUST_PREPARE_ROLES`, which is `{ paralegal }`.
// Adding the attestation there would mean ONLY A PARALEGAL COULD PREPARE AN
// ATTESTATION AND AN ATTORNEY COULD NOT, which is wrong for a solo firm and
// wrong for any firm whose attorney runs the reconciliation themselves.
// Widening that list to fix it would change C2's DECIDED answer for
// `law_trusttx` as a side effect.
//
// So: its own profile, with `preparerRoles` { owner, attorney, paralegal } --
// anyone who may run the comparison may stage the attestation of it -- and
// `signerRoles` LAW_BAR_ADMITTED_ROLES, imported, never re-listed.
//
// A CONSEQUENCE WORTH STATING: arm E3 of api/b18-countersign-lock.test.js
// asserts law-countersign's locked list equals LAW_TRUST_TWO_STAGE. It STAYS
// GREEN and was not touched, because that is still true.
//
// ── MODE_ALWAYS, AND IT IS THE SHARPEST DECISION HERE ────────────────────
// Design §3 Alternative A: under MODE_PREPARED_ONLY an attorney who ran the
// reconciliation themselves would attest their own work with no second party
// and no token -- which is exactly the shape b20 withdrew a grant to avoid.
// The solo case is handled by a NAMED SINGLE-SIGNER MODE that says so on the
// row, not by an asymmetry that says nothing.
//
// ── THE TOKEN TABLE IS REUSED AND THAT WAS MEASURED ──────────────────────
// `sairnlaw_countersign_tokens.resource` is `text not null` with no CHECK on
// its value, and Michael has already run that schema -- so the two-signer path
// needs no new SQL at all. Only the attestation RECORD table is new.
//
// REQUIRES sql/sairnlaw_trust_attestations.sql AND
// sql/sairnlaw_countersign_schema.sql AND sql/sairnlaw_employee_auth_schema.sql.
// ---------------------------------------------------------------------------

'use strict';

const cs = require('./_lib/countersign');
const { runCountersignAction, ACTIONS: CS_ACTIONS } = require('./_lib/countersign-endpoint');
const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest, AUTH_TABLE_BY_APP } = require('./_lib/auth');
const lawRoles = require('./_lib/law-roles');
const attest = require('./_lib/law-attest');

const APP = 'sairnlaw';
const RECORD_TABLE = 'sairnlaw_trust_attestations';
const SETTINGS_TABLE = 'sairnlaw_firm_settings';

// The actions this file serves on top of the four the shared countersignature
// endpoint already serves (prepare, countersign, status, open).
const OWN_ACTIONS = ['attest', 'policy', 'set_policy', 'list'];

const PROFILE = Object.freeze({
  app: APP,
  employeeTable: AUTH_TABLE_BY_APP[APP],
  // THE SAME TOKEN TABLE AS api/law-countersign.js, with a different
  // `resource` value. The token lifecycle -- single use, ten-minute expiry,
  // content binding, the settling step -- is identical and is proved by
  // api/b18-countersign-lock.test.js's 59 arms. A second table would be a
  // second copy of that, and the copy nobody re-reads is the one that drifts.
  tokenTable: 'sairnlaw_countersign_tokens',
  sqlFile: 'sql/sairnlaw_trust_attestations.sql',
  lockedResources: Object.freeze(Object.assign(Object.create(null), {
    [attest.ATTEST_RESOURCE]: cs.MODE_ALWAYS
  })),
  signerRoles: lawRoles.LAW_BAR_ADMITTED_ROLES,
  // WHO MAY STAGE ONE: anyone who may run the comparison. A paralegal is here
  // because that is the delegation this whole mechanism exists to make safe --
  // Rule 5.3 supports a non-lawyer doing the WORK under supervision, and the
  // attestation is the record of the supervision.
  preparerRoles: Object.freeze(Object.assign(Object.create(null), {
    owner: true, attorney: true, paralegal: true
  })),
  signerLabel: 'an attorney or the firm owner',
  requiredMessage:
    'A trust reconciliation has to be attested by an attorney or the firm '
  + 'owner. This attestation is prepared and is waiting for that signature -- '
  + 'nothing has been recorded as attested.',
  preparerRefusal:
    'Only an attorney, the firm owner or a paralegal who ran the '
  + 'reconciliation can stage an attestation of it.',
  signerRefusal:
    'Only an attorney or the firm owner can attest a trust reconciliation. A '
  + 'paralegal may run the comparison and stage it, but attesting to it is the '
  + 'lawyer\'s duty under Rule 1.15 and is not delegable.'
});

cs.assertProfile(PROFILE);

// ── WHAT AN ATTESTATION DOES NOT CLAIM, RETURNED ON EVERY ANSWER ──────────
// Design non-goal 1: an attestation records that a qualified person looked and
// signed, and must never read as a correctness guarantee. The panel has to be
// able to print that sentence, so the server sends it rather than leaving
// seventeen front-ends to each write their own version of it.
const NOT_A_GUARANTEE =
  'An attestation records that a bar-admitted person reviewed and signed this '
+ 'exact comparison. It does not certify that the figures are correct.';

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
  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err && err.code === 'CONFIG') {
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

  // THE FOUR SHARED ACTIONS GO STRAIGHT TO THE SHARED ENDPOINT. prepare,
  // countersign, status and open behave here exactly as they do for a trust
  // disbursement, against this profile's resource.
  if (CS_ACTIONS.indexOf(action) !== -1) {
    return runCountersignAction(PROFILE, req, res, lic);
  }
  if (OWN_ACTIONS.indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: '
      + CS_ACTIONS.concat(OWN_ACTIONS).join(', ') } });
    return;
  }
  return handleOwnAction(action, body, req, res, lic);
};
module.exports.PROFILE = PROFILE;
module.exports.OWN_ACTIONS = OWN_ACTIONS;
module.exports.NOT_A_GUARANTEE = NOT_A_GUARANTEE;

async function handleOwnAction(action, body, req, res, lic) {
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY || !process.env.SD_AUTH_SECRET) {
    console.error('law-attest: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }
  const licHash = lic.license_hash;
  const headers = {
    apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY,
    'Content-Type': 'application/json'
  };
  const rest = (p) => SUPABASE_URL + '/rest/v1/' + p;
  const enc = encodeURIComponent;

  function upstream(detail) {
    console.error('law-attest upstream error:', detail);
    if (cs.isMissingTable(detail)) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED',
        message: 'The SAIRNlaw trust-attestation tables are not set up yet — '
               + 'run ' + PROFILE.sqlFile + '. Nothing was recorded.' } });
      return;
    }
    res.status(502).json({ error: { message: 'Data store error — try again' } });
  }

  // THE CALLER MUST BE A LIVE, ACTIVE EMPLOYEE, with the ROLE READ FROM THE
  // ROW. Same function, same argument, as api/_lib/countersign-endpoint.js: a
  // session outlives a demotion by up to its TTL, and an attestation carrying
  // a role the person no longer holds is a record that names a standing
  // nobody has.
  async function activeCaller() {
    const caller = verifySessionToken(tokenFromRequest(req), licHash, APP);
    if (!caller) return null;
    const r = await fetch(rest(PROFILE.employeeTable + '?license_hash=eq.' + enc(licHash)
      + '&employee_id=eq.' + enc(caller.employee_id)
      + '&active=eq.true&select=employee_id,role&limit=1'), { headers });
    const rows = await r.json().catch(() => null);
    if (!r.ok) { const e = new Error('caller lookup failed'); e.detail = rows; throw e; }
    const row = (Array.isArray(rows) && rows[0]) || null;
    if (!row) return null;
    return { employee_id: row.employee_id, role: row.role };
  }

  // ── THE COUNT THAT DECIDES SINGLE-SIGNER ELIGIBILITY ────────────────────
  // Returns the number of CURRENTLY ACTIVE owner/attorney employees, or NULL
  // for could-not-tell. NEVER 0 on a failed read: api/_lib/law-attest.js maps
  // null to a refusal and 0 to a DIFFERENT refusal, and collapsing them would
  // tell a solo firm it has no attorney when the truth is that nothing could
  // be read.
  //
  // IT RETURNS NULL RATHER THAN THROWING, and that is a correction made while
  // this file was being tested. The first draft threw, the catch-all below
  // turned it into a generic 502 "Data store error", and arm E5 caught it: the
  // refusal was still safe -- nothing was written -- but it had lost the one
  // thing that makes it actionable, which is that the ROSTER could not be read
  // rather than the attestation table. A refusal that cannot say what it could
  // not do sends somebody to look in the wrong place.
  //
  // THE ROLE LIST COMES FROM lawRoles.LAW_BAR_ADMITTED_ROLES, not from a
  // literal here. `in.(...)` is built from its keys, each one encoded.
  async function countActiveBarAdmitted() {
    const roles = Object.keys(lawRoles.LAW_BAR_ADMITTED_ROLES);
    const inList = roles.map((r) => enc(r)).join(',');
    const r = await fetch(rest(PROFILE.employeeTable + '?license_hash=eq.' + enc(licHash)
      + '&active=eq.true&role=in.(' + inList + ')&select=employee_id'), { headers });
    const rows = await r.json().catch(() => null);
    if (!r.ok || !Array.isArray(rows)) {
      console.error('law-attest: bar-admitted roster count failed:', rows);
      return null;
    }
    return rows.length;
  }

  // Reads the setting. Returns { on, row } or throws. An ABSENT ROW IS OFF,
  // which is the narrow default: absent-means-on would hand the weaker control
  // to every firm on the platform the day the table was created.
  //
  // A NON-BOOLEAN VALUE IS OFF, not truthy. `value === true` and not
  // `!!value`, because `"false"` and `0` and `{}` are all truthy in the
  // spelling that would have been shorter.
  async function readSetting() {
    const r = await fetch(rest(SETTINGS_TABLE + '?license_hash=eq.' + enc(licHash)
      + '&setting_key=eq.' + enc(attest.SETTING_KEY)
      + '&select=value,updated_by,updated_role,updated_at,bar_admitted_count_at_set&limit=1'),
      { headers });
    const rows = await r.json().catch(() => null);
    if (!r.ok) { const e = new Error('setting read failed'); e.detail = rows; throw e; }
    const row = (Array.isArray(rows) && rows[0]) || null;
    return { on: !!row && row.value === true, row: row };
  }

  try {
    // ══ policy ═════════════════════════════════════════════════════════════
    // Read-only. Any authenticated employee may see it: a paralegal who stages
    // an attestation needs to know whether a second signature is going to be
    // required, and hiding it makes the refusal they would otherwise get
    // unexplainable.
    if (action === 'policy') {
      const caller = await activeCaller();
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      const s = await readSetting();
      const count = await countActiveBarAdmitted();
      const elig = attest.singleSignerEligible(count);
      res.status(200).json({
        ok: true,
        setting_key: attest.SETTING_KEY,
        single_signer_enabled: s.on,
        // THE LIVE COUNT, BESIDE THE SETTING, because they can disagree and
        // the disagreement is the thing a firm needs to see: a setting that is
        // ON while the firm has two attorneys authorises nothing, and a panel
        // that showed only the setting would present it as working.
        active_bar_admitted: count,
        single_signer_available: !!elig.eligible && s.on,
        single_signer_would_be_accepted: !!elig.eligible,
        why: elig.refused ? elig.refused.message : null,
        set_by: s.row ? s.row.updated_by : null,
        set_at: s.row ? s.row.updated_at : null,
        not_a_guarantee: NOT_A_GUARANTEE
      });
      return;
    }

    // ══ set_policy ═════════════════════════════════════════════════════════
    // OWNER ONLY. Turning this on changes what a record of a regulated review
    // is allowed to claim, which is a provisioning-class decision rather than
    // an attorney's working preference. `attorney` is deliberately absent.
    if (action === 'set_policy') {
      const caller = await activeCaller();
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (caller.role !== 'owner') {
        res.status(403).json({ error: { code: 'FORBIDDEN',
          message: 'Only the firm owner can change how a trust reconciliation '
                 + 'is attested.' } });
        return;
      }
      if (typeof body.enabled !== 'boolean') {
        res.status(400).json({ error: { message: 'enabled must be true or false' } });
        return;
      }
      let count = null;
      if (body.enabled) {
        // THE FIRST OF THE TWO ENFORCEMENT POINTS. A firm with two
        // bar-admitted employees cannot turn this on at all.
        count = await countActiveBarAdmitted();
        const elig = attest.singleSignerEligible(count);
        if (elig.refused) {
          res.status(elig.refused.code === 'ELIGIBILITY_UNKNOWN' ? 503 : 409)
             .json({ error: elig.refused });
          return;
        }
      }
      const r = await fetch(rest(SETTINGS_TABLE + '?on_conflict=license_hash,setting_key'), {
        method: 'POST',
        headers: Object.assign({}, headers, {
          Prefer: 'resolution=merge-duplicates,return=representation' }),
        body: JSON.stringify({
          license_hash: licHash,
          setting_key: attest.SETTING_KEY,
          value: body.enabled,
          updated_by: caller.employee_id,
          updated_role: caller.role,
          updated_at: new Date().toISOString(),
          bar_admitted_count_at_set: count
        })
      });
      const rows = await r.json().catch(() => null);
      if (!r.ok) return upstream(rows);
      res.status(200).json({ ok: true, single_signer_enabled: body.enabled,
        active_bar_admitted: count,
        // SAID ON THE WAY IN, not only in a design document. The setting is a
        // claim about staffing and it is re-checked on every attestation.
        note: body.enabled
          ? 'Single-signer attestation is on. The roster is re-counted on every '
          + 'attestation: if this firm takes on a second attorney, single-signer '
          + 'attestations stop being accepted without anyone changing this '
          + 'setting.'
          : 'Single-signer attestation is off. A trust reconciliation now needs '
          + 'a prepared attestation and a second bar-admitted signature.' });
      return;
    }

    // ══ list ═══════════════════════════════════════════════════════════════
    // BAR-ADMITTED ONLY, because an attestation carries the three trust leg
    // balances and those are inside LAW_TRUST_LOCKED. NO TOKENS AND NO TOKEN
    // HASHES ARE RETURNED ANYWHERE in this file -- b20's `open` action makes
    // the same argument in the same words: a readable table of live tokens is
    // a table of signatures waiting to be borrowed.
    if (action === 'list') {
      const caller = await activeCaller();
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
      if (!lawRoles.LAW_BAR_ADMITTED_ROLES[caller.role]) {
        res.status(403).json({ error: { code: 'FORBIDDEN',
          message: lawRoles.denyMessage('law_trusttx', caller.role, 'read') } });
        return;
      }
      const r = await fetch(rest(RECORD_TABLE + '?license_hash=eq.' + enc(licHash)
        + '&select=attestation_id,content_hash,bank_balance_cents,'
        + 'ledger_balance_cents,client_subledger_total_cents,bank_as_of,'
        + 'ledger_as_of,subledger_as_of,verdict,negative_balances,prepared_by,'
        + 'prepared_role,attested_by,attested_role,attested_at,signer_mode'
        + '&order=attested_at.desc&limit=200'), { headers });
      const rows = await r.json().catch(() => null);
      if (!r.ok) return upstream(rows);
      res.status(200).json({ ok: true, provisioned: true, data: rows || [],
        not_a_guarantee: NOT_A_GUARANTEE });
      return;
    }

    // ══ attest ═════════════════════════════════════════════════════════════
    if (action === 'attest') {
      const caller = await activeCaller();
      if (!caller) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }

      const attestationId = String(body.attestation_id || '').trim();
      if (!attestationId || attestationId.length > 128) {
        res.status(400).json({ error: { message: 'attestation_id (max 128 chars) is required' } });
        return;
      }
      // VALIDATE THE COMPARISON FIRST, before anything about signatures. The
      // hash is computed over the NORMALISED object, so a caller cannot sign
      // one shape and store another.
      const norm = attest.normaliseComparison(body.comparison);
      if (norm.refused) { res.status(400).json({ error: norm.refused }); return; }
      const comparison = norm.comparison;

      const token = req.headers['x-law-countersign'] || body.countersign_token || '';
      // THE COUNT AND THE SETTING ARE ONLY READ WHEN THEY ARE GOING TO BE
      // USED. On the dual path the roster size and the setting are both
      // irrelevant, and reading them there would let a failed read refuse a
      // two-signature attestation that needs neither.
      let count = null;
      let settingOn = false;
      if (!token) {
        count = await countActiveBarAdmitted();
        settingOn = (await readSetting()).on;
      }
      const verdict = attest.decideAttestation({
        callerRole: caller.role,
        hasToken: !!token,
        settingOn: settingOn,
        activeBarAdmitted: count
      });
      if (verdict.refused) {
        // 503 for could-not-tell, 403 for every decided refusal. The
        // distinction is the whole of PR §1.11 here: "I could not read the
        // roster" and "you may not do this" must not arrive as one status.
        res.status(verdict.refused.code === 'ELIGIBILITY_UNKNOWN' ? 503 : 403)
           .json({ error: verdict.refused });
        return;
      }

      let preparedBy = caller.employee_id;
      let preparedRole = caller.role;
      let attestedBy = caller.employee_id;
      let attestedRole = caller.role;

      if (verdict.mode === attest.SIGNER_MODE_DUAL) {
        // THE SHARED LOCK DOES THE DECIDING. Content binding, single use,
        // expiry, the self-signature refusal, the qualified-signer check and
        // the settling step are all in api/_lib/countersign.js and none of
        // them is re-implemented here.
        const refusal = await cs.requireCountersignature(PROFILE, {
          resource: attest.ATTEST_RESOURCE,
          payload: comparison,
          licHash: licHash,
          rest: rest,
          headers: headers,
          token: token,
          callerRole: caller.role
        });
        if (refusal) { res.status(refusal.status).json(refusal.body); return; }

        // ── WHO SIGNED IT: READ BACK FROM THE SPENT TOKEN ROW ─────────────
        // requireCountersignature returns null on success and does not hand
        // back the identities, so they are read from the row it just spent.
        // IF THAT READ FAILS THE ATTESTATION IS REFUSED rather than written
        // with the caller's name in both places: a row that cannot name its
        // signers is not a record of a two-person review, and guessing here
        // would manufacture exactly the self-signature the lock just refused.
        const tr = await fetch(rest(PROFILE.tokenTable + '?license_hash=eq.' + enc(licHash)
          + '&token_hash=eq.' + enc(cs.hashToken(token))
          + '&select=prepared_by,prepared_role,countersign_employee_id,countersign_role&limit=1'),
          { headers });
        const trows = await tr.json().catch(() => null);
        const trow = (tr.ok && Array.isArray(trows) && trows[0]) || null;
        if (!trow || !trow.prepared_by || !trow.countersign_employee_id) {
          res.status(503).json({ error: { code: 'ATTESTATION_SIGNERS_UNREADABLE',
            message: 'The signature was accepted but who prepared and who '
                   + 'signed could not be read back, so nothing was recorded. '
                   + 'The signature has been used — prepare and sign again.' } });
          return;
        }
        preparedBy = trow.prepared_by;
        preparedRole = trow.prepared_role;
        // THE ATTESTER IS THE COUNTERSIGNER, NOT THE CALLER. It is the
        // signer's standing the record claims; api/_lib/countersign.js already
        // re-derives qualification from the stored role for the same reason.
        // The caller on this path is whoever is SAVING the record, which may
        // be the preparer, and attributing the attestation to them would be
        // the defect the stored-role rule exists to prevent.
        attestedBy = trow.countersign_employee_id;
        attestedRole = trow.countersign_role;
      }

      const row = {
        license_hash: licHash,
        attestation_id: attestationId,
        content_hash: cs.contentHash(attest.ATTEST_RESOURCE, comparison),
        bank_balance_cents: comparison.bank_balance_cents,
        ledger_balance_cents: comparison.ledger_balance_cents,
        client_subledger_total_cents: comparison.client_subledger_total_cents,
        bank_as_of: comparison.bank_as_of,
        ledger_as_of: comparison.ledger_as_of,
        subledger_as_of: comparison.subledger_as_of,
        verdict: comparison.verdict,
        negative_balances: comparison.negative_balances,
        prepared_by: preparedBy,
        prepared_role: preparedRole,
        attested_by: attestedBy,
        attested_role: attestedRole,
        attested_at: new Date().toISOString(),
        signer_mode: verdict.mode
      };
      const w = await fetch(rest(RECORD_TABLE), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
        body: JSON.stringify(row)
      });
      const wrows = await w.json().catch(() => null);
      if (!w.ok) {
        // A UNIQUE VIOLATION IS ITS OWN ANSWER. Re-using an attestation_id is
        // a client mistake with a fixable cause, and reporting it as a generic
        // data-store error would send somebody to look at Supabase.
        const s = JSON.stringify(wrows || '');
        if (s.indexOf('23505') !== -1 || s.indexOf('duplicate key') !== -1) {
          res.status(409).json({ error: { code: 'ATTESTATION_ID_TAKEN',
            message: 'This firm already has an attestation with that id. An '
                   + 'attestation is never amended — a corrected '
                   + 'reconciliation is a new comparison with a new id.' } });
          return;
        }
        return upstream(wrows);
      }
      res.status(200).json({
        ok: true,
        attestation_id: attestationId,
        signer_mode: verdict.mode,
        // SPELLED OUT ON THE SINGLE PATH. The response says what the record
        // says, so a panel cannot present a solo attestation as a two-person
        // review by omission.
        signers: verdict.mode === attest.SIGNER_MODE_SINGLE
          ? 'ONE bar-admitted person — this firm has exactly one, and the '
            + 'record says so (signer_mode: single).'
          : 'TWO people — prepared by ' + preparedRole + ', attested by '
            + attestedRole + '.',
        content_hash: row.content_hash,
        not_a_guarantee: NOT_A_GUARANTEE
      });
      return;
    }
  } catch (err) {
    return upstream((err && err.detail) || (err && err.message) || err);
  }
}
