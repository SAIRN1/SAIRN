// api/ai-notice.js
// ---------------------------------------------------------------------------
// THE PER-EMPLOYEE, ONE-TIME AI-SUGGESTION NOTICE. Two actions, one table
// column pair, no new table.
//
//   state  {app_id}                   -> { required, current_version,
//                                          acked_version, acked_at }
//   ack    {app_id, version}          -> { ok, acked_version, acked_at }
//
// Licence key via `Authorization: Bearer`, employee session via `X-SD-Auth`.
//
// ── WHY ONE SHARED ENDPOINT AND NOT SEVENTEEN LOGIN PAYLOADS ──────────────
// docs/2026-10-14-ai-safeguards-spec.md §3.2 proposes adding the flag to each
// `*-auth.js` login response plus an `ack_ai_notice` action on each. There are
// SEVENTEEN of those files. That is seventeen edits to ship one feature and
// seventeen places for it to drift -- and the same spec's §3.1 argues against
// exactly that shape for the helper ("not seventeen copies"). The reason given
// there for touching login at all is "no new endpoint", which is a cost, not a
// requirement.
//
// SO THIS IS ONE FILE, and the deviation is recorded rather than silent. The
// client asks after login instead of reading login's reply. One round trip, one
// implementation, and a new app needs no edit here at all -- it needs an entry
// in AUTH_TABLE_BY_APP, which it already needs for the active-credential
// re-check, so there is no second list to forget.
//
// ── THE EMPLOYEE IS TAKEN FROM THE SESSION, NEVER FROM THE BODY ───────────
// A cross-tenant or cross-employee ack is the highest-value bug in this
// feature: it would mark somebody else as having read the notice. `employee_id`
// and `license_hash` both come from the verified token, and the UPDATE is
// filtered on both. There is no request shape that can ack another row.
//
// ── THE APP COMES FROM THE BODY AND IS THEN RE-VERIFIED AGAINST THE TOKEN ─
// `app_id` picks which `*_employee_auth` table to touch, and then
// verifySessionToken's third argument REFUSES a token minted for a different
// app -- the Guardian Check 28 collision, because role names like 'owner'
// exist in several apps' vocabularies. Taking the app from the body alone
// would let a SAIRNdental session ack a SAIRNlaw row.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SD_AUTH_SECRET.
// REQUIRES sql/2026-10-14-hank-b9-ai-safeguards.sql to have been run.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest, AUTH_TABLE_BY_APP } = require('./_lib/auth');
const { CURRENT_NOTICE_VERSION, aiNoticeState } = require('./_lib/ai-safeguards');

const ACTIONS = ['state', 'ack'];

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
    console.error('ai-notice: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SD_AUTH_SECRET not set');
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
  const action = body.action;
  if (ACTIONS.indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: ' + ACTIONS.join(', ') } });
    return;
  }

  const app = body.app_id;
  const table = app && AUTH_TABLE_BY_APP[app];
  if (!table) {
    // NAMED REFUSAL RATHER THAN A FALLBACK. An app with no employee table has
    // nobody to ack on behalf of, and guessing a table from a prefix is how a
    // typo writes to the wrong tenant's credentials.
    res.status(400).json({ error: { code: 'UNKNOWN_APP', message: 'app_id is not an app with employee credentials' } });
    return;
  }

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey, app);
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
  if (lic.app_scope === 'mismatch') {
    res.status(403).json({ error: { code: 'LICENSE_WRONG_APP', message: 'This license key is not for this app' } });
    return;
  }

  const licHash = lic.license_hash;
  const session = verifySessionToken(tokenFromRequest(req), licHash, app);
  if (!session || !session.employee_id) {
    res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first — the AI notice is recorded against your own login' } });
    return;
  }

  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;
  const mine = table + '?license_hash=eq.' + enc(licHash)
    + '&employee_id=eq.' + enc(session.employee_id);

  // ── A COLUMN THAT IS NOT THERE YET IS A THIRD STATE ──────────────────────
  // If the migration has not been run, PostgREST answers 400 naming the
  // column. That is NOT "no ack recorded" -- it is "could not tell", and
  // answering `required: false` would silently switch the notice off for
  // everybody, while `required: true` would re-prompt on every login forever.
  // Both are wrong, so it refuses and names the file to run.
  const NOT_MIGRATED = {
    status: 503,
    code: 'AI_NOTICE_NOT_PROVISIONED',
    message: 'The AI-notice columns are not set up on the server yet — run '
      + 'sql/2026-10-14-hank-b9-ai-safeguards.sql in Supabase. Nothing was '
      + 'read or saved.'
  };
  const looksUnmigrated = (detail) => {
    const s = JSON.stringify(detail || '');
    return /ai_notice_version|ai_notice_acked_at|column .* does not exist/i.test(s);
  };

  if (action === 'state') {
    const r = await fetch(rest(mine + '&select=ai_notice_version,ai_notice_acked_at&limit=1'), { headers });
    const rows = await r.json();
    if (!r.ok) {
      if (looksUnmigrated(rows)) { res.status(503).json({ error: NOT_MIGRATED }); return; }
      res.status(502).json({ error: { message: 'Upstream error reading the AI notice state' } });
      return;
    }
    const row = (Array.isArray(rows) && rows[0]) || null;
    // No row for a token that VERIFIED means the credential was removed since
    // it was issued. Refused rather than answered: the alternative is telling
    // a deleted employee they are up to date.
    if (!row) {
      res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential no longer exists. Sign in again.' } });
      return;
    }
    res.status(200).json({ ok: true, data: aiNoticeState(row) });
    return;
  }

  // action === 'ack'
  //
  // THE VERSION IS CHECKED AGAINST THE SERVER'S CONSTANT, not accepted. A
  // client that could ack an arbitrary string could write `ai_notice_version`
  // to something that will never equal CURRENT_NOTICE_VERSION again -- or to a
  // future version -- and in the first case the notice re-prompts forever while
  // the row claims an ack, and in the second it never prompts again.
  if (body.version !== CURRENT_NOTICE_VERSION) {
    res.status(400).json({
      error: {
        code: 'NOTICE_VERSION_MISMATCH',
        message: 'The notice you acknowledged is not the current one. Reload '
          + 'the page and read it again.',
        current_version: CURRENT_NOTICE_VERSION
      }
    });
    return;
  }

  // IDEMPOTENT BY READ-THEN-SKIP. A second ack of the same version must not
  // move `acked_at` -- the date is evidence of when the person actually read
  // it, and a refresh loop that kept rewriting it would erase that.
  const pre = await fetch(rest(mine + '&select=ai_notice_version,ai_notice_acked_at&limit=1'), { headers });
  const preRows = await pre.json();
  if (!pre.ok) {
    if (looksUnmigrated(preRows)) { res.status(503).json({ error: NOT_MIGRATED }); return; }
    res.status(502).json({ error: { message: 'Upstream error reading the AI notice state' } });
    return;
  }
  const existing = (Array.isArray(preRows) && preRows[0]) || null;
  if (!existing) {
    res.status(403).json({ error: { code: 'CREDENTIAL_INACTIVE', message: 'This credential no longer exists. Sign in again.' } });
    return;
  }
  if (existing.ai_notice_version === CURRENT_NOTICE_VERSION) {
    res.status(200).json({ ok: true, data: aiNoticeState(existing), already: true });
    return;
  }

  const at = new Date().toISOString();
  const w = await fetch(rest(mine), {
    method: 'PATCH',
    headers: Object.assign({}, headers, { Prefer: 'return=representation' }),
    body: JSON.stringify({ ai_notice_version: CURRENT_NOTICE_VERSION, ai_notice_acked_at: at })
  });
  const wrote = await w.json();
  if (!w.ok) {
    if (looksUnmigrated(wrote)) { res.status(503).json({ error: NOT_MIGRATED }); return; }
    // A FAILED ACK MUST NEVER READ AS ACKED. The client re-shows the notice on
    // the next login because `state` will still say required -- which is only
    // true if this path refuses instead of returning ok.
    res.status(502).json({ error: { code: 'ACK_NOT_SAVED', message: 'The acknowledgement was not saved. You will be asked again.' } });
    return;
  }
  const after = (Array.isArray(wrote) && wrote[0]) || { ai_notice_version: CURRENT_NOTICE_VERSION, ai_notice_acked_at: at };
  res.status(200).json({ ok: true, data: aiNoticeState(after) });
};
