// api/courtlistener.js
// ---------------------------------------------------------------------------
// Thin, real proxy to CourtListener's REST API v4 (courtlistener.com, part
// of the Free Law Project) for direct search/browse use from the client.
// api/legal-citator.js is the classification orchestration layer built on
// the same shared client (api/_lib/courtlistener.js) — this file is just
// the pass-through endpoint for the parts a user directly searches/browses.
//
// RESEARCHED LIVE 2026-08-08 (not assumed from memory — confirmed against
// the real API and its docs at wiki.free.law/c/courtlistener/help/api/rest/v4):
//   - /search/?type=o and /courts/ work with ZERO authentication.
//   - /clusters/{id}/, /opinions/{id}/, /opinions-cited/, /citation-lookup/
//     all return 401 "Authentication credentials were not provided" without
//     a token — confirmed via live curl against each endpoint.
//   - Token auth: `Authorization: Token <token>` header, generated at
//     https://www.courtlistener.com/profile/api-token/ (free, self-serve
//     account signup — not something this server can create for itself).
//   - Documented rate limit for authenticated requests: 5/minute, 50/hour,
//     125/day, on a rolling window. Shared by every SAIRNlaw firm through
//     this one server-side token — see api/_lib/courtlistener.js for the
//     real Supabase-backed limiter this enforces against, not an in-memory
//     counter (which would not survive this being a stateless function).
//
// NO TOKEN IS CONFIGURED AS OF THIS COMMIT. Actions that need one degrade
// to a clear 503 NOT_CONFIGURED rather than a confusing passthrough 401 —
// same graceful-degradation pattern as every NOT_PROVISIONED branch in
// api/sd-data.js. Once COURTLISTENER_API_TOKEN is set as a Vercel env var,
// those actions start working with no code change.
//
// AUTH MODEL: same as api/sd-data.js — Authorization: Bearer <license_key>
// from a SAIRNlaw license, validated before any CourtListener call is made.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (rate-limit log),
// COURTLISTENER_API_TOKEN (token-gated actions only).
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const cl = require('./_lib/courtlistener');

const ACTIONS_REQUIRING_TOKEN = { citing: true, citation_lookup: true, opinion_text: true, cluster: true };

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

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  const action = body && body.action;
  const VALID_ACTIONS = { search: true, courts: true, citing: true, citation_lookup: true, opinion_text: true, cluster: true };
  if (!VALID_ACTIONS[action]) {
    res.status(400).json({ error: { message: 'action must be one of: search, courts, citing, citation_lookup, opinion_text, cluster' } });
    return;
  }

  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') {
      console.error('courtlistener proxy config error:', err.message);
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    console.error('courtlistener proxy license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  if (lic.app_id && lic.app_id !== 'sairnlaw') {
    res.status(403).json({ error: { code: 'WRONG_APP', message: 'This license is not issued for sairnlaw' } });
    return;
  }

  if (ACTIONS_REQUIRING_TOKEN[action] && !process.env.COURTLISTENER_API_TOKEN) {
    res.status(503).json({
      error: {
        code: 'NOT_CONFIGURED',
        message: 'CourtListener API token is not configured yet — this action needs COURTLISTENER_API_TOKEN set as a Vercel env var. Get a free token at courtlistener.com/profile/api-token/ after creating an account.'
      }
    });
    return;
  }

  try {
    if (action === 'search') {
      if (!body.q) { res.status(400).json({ error: { message: 'search requires q' } }); return; }
      const data = await cl.clSearch(body.q);
      res.status(200).json({ ok: true, data });
      return;
    }
    if (action === 'courts') {
      if (!body.court_id) { res.status(400).json({ error: { message: 'courts requires court_id' } }); return; }
      const data = await cl.clCourt(body.court_id);
      res.status(200).json({ ok: true, data });
      return;
    }

    // Token-gated, rate-limit-consuming actions from here down.
    const budget = await cl.remainingBudget();
    if (budget.minute <= 0 || budget.hour <= 0 || budget.day <= 0) {
      const exhausted = budget.minute <= 0 ? 'minute' : budget.hour <= 0 ? 'hour' : 'day';
      res.status(429).json({ error: { code: 'CL_RATE_LIMITED', message: 'CourtListener request budget for this ' + exhausted + ' is exhausted (shared across all SAIRNlaw firms) — try again shortly.' } });
      return;
    }

    if (action === 'citing') {
      if (!body.cited_opinion) { res.status(400).json({ error: { message: 'citing requires cited_opinion' } }); return; }
      const data = await cl.clCitingOpinions(body.cited_opinion);
      res.status(200).json({ ok: true, data });
      return;
    }
    if (action === 'citation_lookup') {
      if (!body.text) { res.status(400).json({ error: { message: 'citation_lookup requires text' } }); return; }
      const data = await cl.clCitationLookup(body.text);
      res.status(200).json({ ok: true, data });
      return;
    }
    if (action === 'opinion_text') {
      if (!body.opinion_id) { res.status(400).json({ error: { message: 'opinion_text requires opinion_id' } }); return; }
      const data = await cl.clOpinionText(body.opinion_id);
      res.status(200).json({ ok: true, data });
      return;
    }
    if (action === 'cluster') {
      if (!body.cluster_id) { res.status(400).json({ error: { message: 'cluster requires cluster_id' } }); return; }
      const data = await cl.clCluster(body.cluster_id);
      res.status(200).json({ ok: true, data });
      return;
    }

    res.status(400).json({ error: { message: 'Unsupported action' } });
  } catch (err) {
    console.error('api/courtlistener error:', err);
    if (err.status) { res.status(err.status).json({ error: { message: err.message } }); return; }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
