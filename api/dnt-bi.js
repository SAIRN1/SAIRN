// api/dnt-bi.js
// ---------------------------------------------------------------------------
// SAIRNdental B5 -- open BI / data-warehouse feed. HTTP half.
// Pure logic, dataset definitions and the two access gates live in
// api/_lib/dental-bi.js; read that file's header first, it carries the design.
//
// TWO REQUEST SHAPES, ONE FILE, AND THEY SHARE NOTHING.
//
//   MANAGEMENT   POST, authenticated as a staff member exactly like every other
//                dental endpoint: Bearer license key + X-SD-Auth session token.
//                Owner only. Actions: mint, list, revoke.
//
//   FEED         GET, authenticated by a BI token and NOTHING else. No license
//                key, no session. This is what Power BI / Tableau / Looker
//                actually poll.
//
// The feed path never accepts a license key and the management path never
// accepts a BI token. Keeping them disjoint is what stops a BI token -- which
// lives in a shared BI workspace and is the likeliest of the two to leak --
// from ever being usable to mint another one, revoke one, or reach any other
// endpoint on this platform.
//
// READ-ONLY IS ENFORCED BY THE ROUTER, NOT PROMISED IN A COMMENT: the feed only
// answers GET, and the only writes this file performs anywhere are the token
// row's own last_used_at/use_count stamps.
//
// ⚠ KNOWN LIMITATION, STATED RATHER THAN DISCOVERED LATER: THE FEED DOES NOT
// RE-CHECK LICENCE STATUS ON EACH POLL.
// Minting requires a valid, active licence. Polling does not, because it
// cannot: a BI token stores only the practice's license_hash, and
// `license_keys` HAS NO license_hash COLUMN -- confirmed by the live
// column-existence probe recorded in sql/demo_license_keys_seed.sql, which
// lists license_hash among the names that are absent. api/_lib/license.js
// looks a licence up by `key`, and the raw key is deliberately not stored here.
//
// What that does and does not mean:
//   * It is NOT a cross-tenant hole. Every read is filtered by the token's own
//     license_hash, so a feed can only ever return that practice's own data.
//   * It IS a billing-enforcement gap: a practice whose licence lapses keeps
//     its own reporting feed working until somebody revokes the token.
// Closing it properly needs a license_hash (or a generated digest column) on
// the shared platform-wide `license_keys` table, which is a change well outside
// this feature and is not being made as a side effect of it. Until then,
// cancelling a practice means revoking its feed tokens too.
//
// TOKEN IN A HEADER IS PREFERRED. TOKEN IN THE URL IS SUPPORTED AND WORSE.
// Power BI's Web source can send an Authorization header; Tableau's WDC and
// Looker Studio's community connectors most easily send a query parameter. Both
// are accepted because refusing the query parameter would mean refusing two of
// the three tools the gap names. It is worse and it is labelled worse: URLs end
// up in proxy logs, browser history and shared workbook definitions in a way
// headers do not. The app says so where the URL is copied.
// ---------------------------------------------------------------------------

const bi = require('./_lib/dental-bi');
const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');

const TOKEN_TABLE = 'sairndental_bi_tokens';
const AUTH_TABLE = 'sairndental_employee_auth';
const MANAGEMENT_ROLES = { owner: true };
const MAX_TOKENS_PER_LICENSE = 25;

function env() {
  return {
    url: process.env.SUPABASE_URL,
    key: process.env.SUPABASE_SERVICE_ROLE_KEY,
    secret: process.env.DENTAL_BI_KEY || process.env.SD_AUTH_SECRET
  };
}

// A table that has never been created comes back from PostgREST as a 404 with a
// PGRST205-shaped body, not an empty list. Told apart from "no rows" because
// they mean opposite things to a practice: one is "run the schema file", the
// other is "you have no tokens yet".
function isMissingTable(status, body) {
  if (status === 404 || status === 400) return true;
  const s = JSON.stringify(body || '');
  return /PGRST205|does not exist|Could not find the table/i.test(s);
}

module.exports = async (req, res) => {
  const E = env();
  if (!E.url || !E.key) {
    console.error('dnt-bi: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }
  const headers = { apikey: E.key, Authorization: 'Bearer ' + E.key, 'Content-Type': 'application/json' };
  const rest = (p) => E.url + '/rest/v1/' + p;
  const enc = encodeURIComponent;

  if (req.method === 'GET') return feed(req, res, { headers, rest, enc, E });
  if (req.method === 'POST') return manage(req, res, { headers, rest, enc, E });
  res.status(405).json({ error: { message: 'Method not allowed — GET to read the feed, POST to manage tokens' } });
};

// ── THE FEED ───────────────────────────────────────────────────────────────
async function feed(req, res, ctx) {
  const { headers, rest, enc, E } = ctx;
  const q = req.query || {};

  const authz = req.headers['authorization'] || '';
  const bearer = authz.startsWith('Bearer ') ? authz.slice(7).trim() : '';
  const token = bearer || (typeof q.token === 'string' ? q.token.trim() : '');
  if (!token) {
    res.status(401).json({ error: { code: 'NO_TOKEN',
      message: 'Send your feed token as an Authorization: Bearer header, or as ?token=' } });
    return;
  }

  // Resolve the token. Deliberately ONE indexed lookup on the hash: the token
  // itself is never compared, stored or logged anywhere in this file.
  const tokenHash = bi.hashToken(token);
  const tr = await fetch(rest(TOKEN_TABLE + '?token_hash=eq.' + enc(tokenHash) +
    '&select=id,license_hash,employee_id,include_identifiers,revoked_at,use_count&limit=1'), { headers });
  const trows = await tr.json().catch(() => null);
  if (!tr.ok) {
    if (isMissingTable(tr.status, trows)) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED',
        message: 'The BI feed is not set up for this deployment yet — run sql/sairndental_bi_tokens_schema.sql' } });
      return;
    }
    res.status(502).json({ error: { code: 'UPSTREAM', message: 'Upstream connection error — try again' } });
    return;
  }
  const trow = Array.isArray(trows) && trows[0];
  // A revoked token and an unknown token get the SAME answer. Distinguishing
  // them would confirm to whoever holds a revoked token that it was once real.
  if (!trow || trow.revoked_at) {
    res.status(401).json({ error: { code: 'INVALID_TOKEN', message: 'This feed token is not valid' } });
    return;
  }

  // THE LIVE ROLE RE-READ. Not a snapshot -- see the schema file's header. An
  // employee who has been deactivated or whose row is gone fails closed here,
  // at the next poll, without anyone having to remember to revoke the token.
  const er = await fetch(rest(AUTH_TABLE + '?license_hash=eq.' + enc(trow.license_hash) +
    '&employee_id=eq.' + enc(trow.employee_id) + '&active=eq.true&select=employee_id,role&limit=1'), { headers });
  const erows = await er.json().catch(() => null);
  if (!er.ok) {
    res.status(502).json({ error: { code: 'UPSTREAM', message: 'Upstream connection error — try again' } });
    return;
  }
  const emp = Array.isArray(erows) && erows[0];
  if (!emp) {
    res.status(403).json({ error: { code: 'EMPLOYEE_INACTIVE',
      message: 'The staff member this feed belongs to is no longer active, so the feed is closed. Ask the practice owner to mint a new one.' } });
    return;
  }
  const role = emp.role;
  const includeIds = trow.include_identifiers === true;

  const datasetName = typeof q.dataset === 'string' ? q.dataset.trim() : '';

  // The catalog. Answered before any dataset gating because it IS the thing
  // that tells a person which datasets their role can reach.
  if (!datasetName || datasetName === '_catalog') {
    stampUse(rest, headers, enc, trow);
    res.status(200).json(bi.catalog(role, includeIds));
    return;
  }

  const allowed = bi.canRead(datasetName, role);
  if (!allowed.ok) {
    if (allowed.code === 'UNKNOWN_DATASET') {
      res.status(404).json({ error: { code: 'UNKNOWN_DATASET',
        message: 'No dataset named "' + datasetName + '". GET ?dataset=_catalog for the list.' } });
      return;
    }
    // 403, not an empty 200. An empty list would be indistinguishable from a
    // practice that has posted no charges, and the BI tool would render a real
    // zero -- a fabricated figure produced by a permission check, which is the
    // exact silent-failure shape Guardian Check 0b exists to catch. Same
    // reasoning, verbatim, as api/sd-data.js:8168.
    res.status(403).json({ error: { code: allowed.code, message: allowed.message } });
    return;
  }

  const def = bi.DATASETS[datasetName];
  const scope = bi.scopeFor(datasetName, role);

  // A provider-scoped role needs its provider link before anything is read.
  let providerId = null;
  if (scope.kind !== 'none') {
    const pr = await fetch(rest('dnt_providers?license_hash=eq.' + enc(trow.license_hash) +
      '&select=provider_id,data'), { headers });
    const prows = await pr.json().catch(() => null);
    if (!pr.ok || !Array.isArray(prows)) {
      res.status(502).json({ error: { code: 'SCOPE_LOOKUP_FAILED', message: 'Could not determine your patient list. Try again.' } });
      return;
    }
    const match = prows.filter((x) => x && x.data && x.data.linked_employee_id === emp.employee_id)[0];
    providerId = match ? (match.data.id || match.provider_id) : null;
    if (!providerId) {
      // Same refusal, same wording as api/sd-data.js:8185. An unlinked provider
      // sees NOTHING, and is told why rather than handed an empty dataset.
      res.status(403).json({ error: { code: 'PROVIDER_NOT_LINKED',
        message: 'This feed belongs to a provider whose sign-in is not linked to a provider record, so no rows are shown. Ask the practice owner to open the Providers panel and link that login.' } });
      return;
    }
  }

  // Read. The provider_column scope filters in the DATABASE, matching
  // sd-data.js:8352 -- an appointment blob can carry photos up to ~1.26 MB, so
  // reading the practice to discard most of it would be both a privacy and a
  // payload problem.
  let path = def.resource + '?license_hash=eq.' + enc(trow.license_hash);
  if (scope.kind === 'provider_column') path += '&' + scope.column + '=eq.' + enc(providerId);
  path += '&select=data';
  const dr = await fetch(rest(path), { headers });
  const drows = await dr.json().catch(() => null);
  if (!dr.ok) {
    if (isMissingTable(dr.status, drows)) {
      // Honest empty: the table does not exist in this deployment. Said as a
      // flag on the envelope rather than as rows, so a dashboard cannot read
      // "not set up" as "zero".
      stampUse(rest, headers, enc, trow);
      res.status(200).json(envelope(datasetName, role, includeIds, [], 0, 0, 0, false));
      return;
    }
    res.status(502).json({ error: { code: 'UPSTREAM', message: 'Upstream connection error — try again' } });
    return;
  }

  let raw = (Array.isArray(drows) ? drows : []).map((x) => x.data).filter(Boolean);

  if (scope.kind === 'patient_ids') {
    // The provider's own patients: everyone they have an appointment with.
    // Same derivation as sd-data.js's dntPatientIdsForProvider.
    const ar = await fetch(rest('dnt_appointments?license_hash=eq.' + enc(trow.license_hash) +
      '&provider_id=eq.' + enc(providerId) + '&select=data'), { headers });
    const arows = await ar.json().catch(() => null);
    if (!ar.ok || !Array.isArray(arows)) {
      res.status(502).json({ error: { code: 'SCOPE_LOOKUP_FAILED', message: 'Could not determine your patient list. Try again.' } });
      return;
    }
    const ids = {};
    arows.forEach((x) => { if (x && x.data && x.data.patient_id) ids[String(x.data.patient_id)] = true; });
    raw = bi.applyPatientScope(datasetName, raw, ids);
  }

  const { limit, offset } = bi.pageParams(q);
  const projected = bi.projectRows(datasetName, raw, {
    licenseHash: trow.license_hash, secret: E.secret, includeIdentifiers: includeIds
  });
  const paged = bi.orderAndPage(datasetName, projected, limit, offset);

  stampUse(rest, headers, enc, trow);
  res.status(200).json(envelope(datasetName, role, includeIds, paged.rows, paged.total, limit, offset, true));
}

// The response envelope. `has_more` is computed, not guessed, so a BI tool can
// page with a while-loop instead of pulling until a short page and hoping that
// meant the end.
function envelope(dataset, role, includeIds, rows, total, limit, offset, provisioned) {
  return {
    ok: true,
    dataset: dataset,
    role: role,
    identifiers_included: includeIds,
    provisioned: provisioned,
    columns: bi.visibleColumns(dataset, includeIds).map((c) => ({ name: c[0], type: c[1] })),
    total: total,
    limit: limit,
    offset: offset,
    has_more: offset + rows.length < total,
    rows: rows
  };
}

// Best-effort usage stamp. Deliberately NOT awaited and deliberately swallowing
// its own failure: a feed that 500s because a bookkeeping UPDATE failed would
// take a practice's dashboard down over a statistic. Read-then-write, so two
// simultaneous polls can lose a count -- said plainly because use_count is a
// "has anyone touched this" signal, not an audited total, and must never be
// quoted as one.
function stampUse(rest, headers, enc, trow) {
  fetch(rest(TOKEN_TABLE + '?id=eq.' + enc(trow.id)), {
    method: 'PATCH', headers,
    body: JSON.stringify({ last_used_at: new Date().toISOString(), use_count: (trow.use_count || 0) + 1 })
  }).catch(() => {});
}

// ── TOKEN MANAGEMENT ───────────────────────────────────────────────────────
async function manage(req, res, ctx) {
  const { headers, rest, enc } = ctx;

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) {
    res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } });
    return;
  }
  if (!process.env.SD_AUTH_SECRET) {
    console.error('dnt-bi: SD_AUTH_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  body = body || {};

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') { res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  const licHash = lic.license_hash;

  const sess = verifySessionToken(tokenFromRequest(req), licHash, 'sairndental');
  if (!sess) { res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } }); return; }
  // Owner only. Minting a feed is a decision to send this practice's data to an
  // outside tool -- the same class of decision as provisioning a login, and
  // gated to the same role (api/dnt-auth.js PROVISIONING_ROLES).
  if (!MANAGEMENT_ROLES[sess.role]) {
    res.status(403).json({ error: { code: 'ROLE_NOT_PERMITTED',
      message: 'Only the practice owner can create or revoke a BI feed' } });
    return;
  }

  const action = body.action;

  if (action === 'list') {
    const r = await fetch(rest(TOKEN_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&select=id,label,employee_id,include_identifiers,created_by,created_at,revoked_at,last_used_at,use_count&order=created_at.desc'), { headers });
    const rows = await r.json().catch(() => null);
    if (!r.ok) {
      if (isMissingTable(r.status, rows)) { res.status(200).json({ ok: true, provisioned: false, tokens: [] }); return; }
      res.status(502).json({ error: { code: 'UPSTREAM', message: 'Upstream connection error — try again' } });
      return;
    }
    // token_hash is not in the select list and never leaves the database.
    res.status(200).json({ ok: true, provisioned: true, tokens: Array.isArray(rows) ? rows : [] });
    return;
  }

  if (action === 'mint') {
    const label = String(body.label || '').trim().slice(0, 80);
    const employeeId = String(body.employee_id || sess.employee_id || '').trim();
    const includeIds = body.include_identifiers === true;
    if (!employeeId) {
      res.status(400).json({ error: { message: 'employee_id is required' } });
      return;
    }

    // The named employee must exist and be active RIGHT NOW. Minting a feed for
    // a deactivated login would create a credential that is dead on arrival and
    // looks alive in the list.
    const er = await fetch(rest(AUTH_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&employee_id=eq.' + enc(employeeId) + '&active=eq.true&select=employee_id,role&limit=1'), { headers });
    const erows = await er.json().catch(() => null);
    if (!er.ok) {
      if (isMissingTable(er.status, erows)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Employee logins are not set up for this practice yet' } });
        return;
      }
      res.status(502).json({ error: { code: 'UPSTREAM', message: 'Upstream connection error — try again' } });
      return;
    }
    if (!(Array.isArray(erows) && erows[0])) {
      res.status(404).json({ error: { code: 'EMPLOYEE_NOT_FOUND',
        message: 'No active staff login with that id. A feed inherits a real person\'s access, so it needs one.' } });
      return;
    }

    const existing = await fetch(rest(TOKEN_TABLE + '?license_hash=eq.' + enc(licHash) +
      '&revoked_at=is.null&select=id'), { headers });
    const exrows = await existing.json().catch(() => null);
    if (existing.ok && Array.isArray(exrows) && exrows.length >= MAX_TOKENS_PER_LICENSE) {
      res.status(409).json({ error: { code: 'TOO_MANY_TOKENS',
        message: 'This practice already has ' + MAX_TOKENS_PER_LICENSE + ' live feed tokens. Revoke one first.' } });
      return;
    }

    const token = bi.mintToken();
    const ins = await fetch(rest(TOKEN_TABLE), {
      method: 'POST',
      headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
      body: JSON.stringify({
        license_hash: licHash, app_id: 'sairndental', token_hash: bi.hashToken(token),
        label: label, employee_id: employeeId, include_identifiers: includeIds,
        created_by: sess.employee_id || ''
      })
    });
    const insrows = await ins.json().catch(() => null);
    if (!ins.ok) {
      if (isMissingTable(ins.status, insrows)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED',
          message: 'The BI feed is not set up for this deployment yet — run sql/sairndental_bi_tokens_schema.sql' } });
        return;
      }
      res.status(502).json({ error: { code: 'UPSTREAM', message: 'Could not create the feed token — nothing was changed' } });
      return;
    }
    // THE ONLY TIME THE TOKEN IS EVER RETURNED. Only its hash was stored, so
    // there is no path that can show it again -- said in the response so the
    // app can say it to the person before they navigate away.
    res.status(200).json({
      ok: true,
      token: token,
      shown_once: true,
      id: (Array.isArray(insrows) && insrows[0] && insrows[0].id) || null,
      include_identifiers: includeIds
    });
    return;
  }

  if (action === 'revoke') {
    const id = String(body.id || '').trim();
    if (!id) { res.status(400).json({ error: { message: 'id is required' } }); return; }
    // license_hash is in the filter, so one practice cannot revoke another's
    // token by guessing a uuid.
    const r = await fetch(rest(TOKEN_TABLE + '?id=eq.' + enc(id) + '&license_hash=eq.' + enc(licHash) +
      '&revoked_at=is.null'), {
      method: 'PATCH',
      headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
      body: JSON.stringify({ revoked_at: new Date().toISOString() })
    });
    const rows = await r.json().catch(() => null);
    if (!r.ok) { res.status(502).json({ error: { code: 'UPSTREAM', message: 'Could not revoke — nothing was changed' } }); return; }
    // Zero rows means it was already revoked or never existed. Reported as such
    // rather than as a success, because "revoked" and "there was nothing there"
    // are different answers to the person clicking the button.
    const n = Array.isArray(rows) ? rows.length : 0;
    if (!n) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No live feed token with that id' } }); return; }
    res.status(200).json({ ok: true, revoked: n });
    return;
  }

  res.status(400).json({ error: { message: 'action must be one of: list, mint, revoke' } });
}

module.exports.feed = feed;
module.exports.manage = manage;
