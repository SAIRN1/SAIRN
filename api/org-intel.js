// api/org-intel.js
// ---------------------------------------------------------------------------
// SAIRNscape Organization Intelligence Layer -- backend for the client-side
// getOrgIntelligence()/saveOrgIntelligence() functions already present in
// sairnscape.html (Organization Intelligence Layer section) but never wired
// into sendMessage() and, until this file, calling a URL that returned a
// bare 404 -- the same "client assumed an endpoint existed that was never
// committed" pattern already found and fixed once before for api/bridge.js
// (see that file's own header note, 2026-07-31).
//
// SAIRNscape has no per-shop license-key system (confirmed: no auth/license
// grep hits anywhere in sairnscape.html) -- org_id is a plain user-typed
// string (the "Connect" modal in the Organization Intelligence Layer
// section), not a validated/hashed credential. This endpoint is
// unauthenticated by design, matching that reality rather than pretending
// a security boundary exists where the client has none to offer -- same
// posture as api/bridge.js's push/pull actions.
//
// PRIVACY NOTE (disclosed, not silently narrower than the StoneDesk-family
// pattern): unlike sd_shared_knowledge's word-frequency-only design, this
// table stores a short, readable insight string -- that shape was already
// fixed by the pre-existing client contract (getOrgIntelligence's own
// comment: "What your other locations know about this"), not redesigned
// here. The caller truncates to ~200 chars before sending; this file
// enforces that cap server-side too rather than trusting the client alone.
//
// ACTION: query   { action:'query', org_id, app_id, query? }
//   Returns up to 10 most recent insights for this org_id (+ app_id),
//   newest first. If `query` is provided, does a light ILIKE filter against
//   insight text first and falls back to "most recent" if nothing matches --
//   not semantic search, just enough to be more useful than pure recency
//   when there's a lot of history.
//   Response: { ok:true, insights:[{location, insight, category}, ...] }
//
// ACTION: save    { action:'save', org_id, location_id?, location_name?,
//                    app_id, insight, category? }
//   Inserts one row. insight capped at 200 chars server-side.
//   Response: { ok:true, saved:true }
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// ---------------------------------------------------------------------------

const MAX_INSIGHT_CHARS = 200;

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
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

  const orgId = String(body.org_id || '').trim();
  const appId = String(body.app_id || 'sairnscape').trim();
  if (!orgId) {
    res.status(400).json({ error: { message: 'org_id is required' } });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('org-intel: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }
  const headers = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  if (body.action === 'save') {
    const insightRaw = String(body.insight || '').trim();
    if (!insightRaw) {
      res.status(400).json({ error: { message: 'insight is required for action:save' } });
      return;
    }
    const insight = insightRaw.slice(0, MAX_INSIGHT_CHARS);
    const row = {
      org_id: orgId,
      app_id: appId,
      location_id: body.location_id ? String(body.location_id).slice(0, 128) : null,
      location_name: body.location_name ? String(body.location_name).slice(0, 128) : 'Main Office',
      insight: insight,
      category: body.category ? String(body.category).slice(0, 64) : 'general'
    };
    try {
      const r = await fetch(rest('sairnscape_org_intel'), {
        method: 'POST',
        headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
        body: JSON.stringify(row)
      });
      if (!r.ok) {
        const detail = await r.json().catch(function () { return null; });
        const code = detail && detail.code;
        if (code === '42P01' || code === 'PGRST205') {
          res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'org-intel storage not set up yet — run sql/sairnscape_org_intel_schema.sql in Supabase first' } });
          return;
        }
        console.error('org-intel save upstream error:', detail);
        res.status(502).json({ error: { message: 'Data store error — try again' } });
        return;
      }
      res.status(200).json({ ok: true, saved: true });
    } catch (err) {
      console.error('org-intel save error:', err);
      res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    }
    return;
  }

  if (body.action === 'query') {
    const query = body.query ? String(body.query).trim() : '';
    try {
      let rows = null;
      if (query) {
        const r = await fetch(rest(
          'sairnscape_org_intel?org_id=eq.' + enc(orgId) + '&app_id=eq.' + enc(appId) +
          '&insight=ilike.' + enc('%' + query.slice(0, 100) + '%') +
          '&select=location_name,insight,category&order=created_at.desc&limit=10'), { headers });
        if (r.ok) rows = await r.json();
      }
      if (!rows || !rows.length) {
        const r2 = await fetch(rest(
          'sairnscape_org_intel?org_id=eq.' + enc(orgId) + '&app_id=eq.' + enc(appId) +
          '&select=location_name,insight,category&order=created_at.desc&limit=10'), { headers });
        if (!r2.ok) {
          const detail = await r2.json().catch(function () { return null; });
          const code = detail && detail.code;
          if (code === '42P01' || code === 'PGRST205') {
            res.status(200).json({ ok: true, insights: [] }); // not provisioned yet -- empty, not an error, for the read path
            return;
          }
          console.error('org-intel query upstream error:', detail);
          res.status(502).json({ error: { message: 'Data store error — try again' } });
          return;
        }
        rows = await r2.json();
      }
      const insights = (rows || []).map(function (row) {
        return { location: row.location_name || 'Unknown', insight: row.insight, category: row.category };
      });
      res.status(200).json({ ok: true, insights: insights });
    } catch (err) {
      console.error('org-intel query error:', err);
      res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    }
    return;
  }

  res.status(400).json({ error: { message: "action must be 'query' or 'save'" } });
};
