// api/legal-reference.js
// ---------------------------------------------------------------------------
// SAIRNlaw grounded legal reference — Phase A (legal term definitions) and
// Phase B (international case-law grounding).
//
// SAME GROUNDING CONTRACT AS THE CITATOR: every successful response carries
// the real source URL the content came from. There is no code path here that
// composes a definition or a case summary, and no path that falls back to
// model memory when a source is unreachable. A failed lookup returns an
// honest failure with a reason, because a plausible-sounding legal definition
// with no source behind it is worse than no answer in this domain.
//
// Auth mirrors api/legal-citator.js exactly: bearer license key, scoped to
// sairnlaw, with an OPTIONAL session token used only to attribute the audit
// entry. Requiring a session here would break existing callers, and the
// endpoint's real access control is the license.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { tokenFromRequest, verifySessionToken } = require('./_lib/auth');
const { writeAuditLog } = require('./_lib/audit');
const { wexLookup } = require('./_lib/wex');
const { COVERAGE, fclSearch, canliiBrowse, canliiCitator } = require('./_lib/intl-caselaw');

const ACTIONS = ['define', 'coverage', 'intl_search', 'canlii_browse', 'canlii_citator'];

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
  const action = body && body.action;
  if (ACTIONS.indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: ' + ACTIONS.join(', ') } });
    return;
  }

  let lic;
  try { lic = await validateLicenseKey(licenseKey); }
  catch (err) {
    if (err.code === 'CONFIG') { console.error('legal-reference config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    console.error('legal-reference license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  if (lic.app_id && lic.app_id !== 'sairnlaw') { res.status(403).json({ error: { code: 'WRONG_APP', message: 'This license is not issued for sairnlaw' } }); return; }

  const caller = verifySessionToken(tokenFromRequest(req), lic.license_hash, 'sairnlaw');
  const audit = (detail) => writeAuditLog(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
    license_hash: lic.license_hash,
    employee_id: caller ? caller.employee_id : null,
    role: caller ? caller.role : null,
    event_type: 'legal_reference_lookup',
    detail
  }).catch((e) => { console.error('legal-reference audit write failed:', e && e.message); });

  try {
    // ── COVERAGE: the honest jurisdiction statement. Deliberately its own
    // action so the UI can show what is NOT covered, and why, without having
    // to run a lookup first and infer the gaps from an empty result. ──
    if (action === 'coverage') {
      res.status(200).json({
        ok: true,
        coverage: COVERAGE,
        note: 'Jurisdictions marked not covered are excluded because their own terms of use prohibit automated access, not because of a technical limitation.'
      });
      return;
    }

    // ── PHASE A: grounded legal term definition from Cornell LII's Wex ──
    if (action === 'define') {
      const term = body.term;
      if (!term || !String(term).trim()) {
        res.status(400).json({ error: { message: 'define requires a term' } });
        return;
      }
      const result = await wexLookup(term);
      await audit({ action: 'define', term: String(term).slice(0, 120), found: !!result.ok });
      if (!result.ok) {
        // Not an error status for NOT_FOUND: the lookup ran correctly and the
        // honest answer is that Wex has no entry. The client shows that
        // instead of a definition, and must not substitute its own.
        const status = result.code === 'RATE_LIMITED' ? 429
          : result.code === 'NOT_PROVISIONED' ? 503
          : result.code === 'NOT_FOUND' || result.code === 'EMPTY' || result.code === 'BAD_TERM' ? 200
          : 502;
        res.status(status).json({ ok: false, grounded: false, ...result });
        return;
      }
      res.status(200).json({ ok: true, grounded: true, ...result });
      return;
    }

    // ── PHASE B: UK (England & Wales) via Find Case Law ──
    if (action === 'intl_search') {
      const q = body.query;
      if (!q || !String(q).trim()) {
        res.status(400).json({ error: { message: 'intl_search requires a query' } });
        return;
      }
      const result = await fclSearch(q, body.per_page);
      await audit({ action: 'intl_search', jurisdiction: 'uk-ew', query: String(q).slice(0, 200), results: result.ok ? result.results.length : 0 });
      res.status(result.ok ? 200 : (result.code === 'NOT_PROVISIONED' ? 503 : result.code === 'RATE_LIMITED' ? 429 : 502)).json(result);
      return;
    }

    // ── PHASE B: Canada via CanLII's official keyed API ──
    if (action === 'canlii_browse') {
      const db = body.database_id;
      if (!db) { res.status(400).json({ error: { message: 'canlii_browse requires database_id' } }); return; }
      const result = await canliiBrowse(db, body.offset, body.count);
      await audit({ action: 'canlii_browse', database_id: String(db).slice(0, 60), ok: !!result.ok, code: result.code || null });
      res.status(result.ok ? 200 : (result.code === 'NOT_CONFIGURED' ? 503 : result.code === 'RATE_LIMITED' ? 429 : 502)).json(result);
      return;
    }

    if (action === 'canlii_citator') {
      const { database_id: db, case_id: caseId, metadata_type: mt } = body;
      if (!db || !caseId || !mt) {
        res.status(400).json({ error: { message: 'canlii_citator requires database_id, case_id and metadata_type' } });
        return;
      }
      const result = await canliiCitator(db, caseId, mt);
      await audit({ action: 'canlii_citator', database_id: String(db).slice(0, 60), case_id: String(caseId).slice(0, 60), metadata_type: String(mt).slice(0, 40), ok: !!result.ok, code: result.code || null });
      res.status(result.ok ? 200 : (result.code === 'NOT_CONFIGURED' ? 503 : result.code === 'BAD_REQUEST' ? 400 : result.code === 'RATE_LIMITED' ? 429 : 502)).json(result);
      return;
    }

    res.status(400).json({ error: { message: 'Unsupported action' } });
  } catch (err) {
    console.error('api/legal-reference error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
