// api/legal-citator.js
// ---------------------------------------------------------------------------
// SAIRNlaw legal-research citator — classification orchestration layer.
// Built on api/_lib/courtlistener.js (real CourtListener v4 client + rate
// limiter). This is the "Phase A (foundation)" build per the brief's 6
// numbered requirements — see the comment block above each function for
// which requirement it implements.
//
// HONEST STATUS AS OF THIS COMMIT: COURTLISTENER_API_TOKEN is not yet
// configured (no token exists — see api/courtlistener.js's header). Every
// code path below is written against CourtListener's REAL, live-confirmed
// v4 API shapes (not guessed), but the token-gated paths (fetching citing-
// opinion full text, the actual classification run) have NOT been live-
// exercised end-to-end, because doing so requires the token. One specific
// unverified detail, flagged rather than silently assumed: the exact field
// name for an opinion's full text on GET /opinions/{id}/ (plausible
// candidates from CourtListener's known schema: plain_text, html,
// html_lawbox, html_columbia, html_with_citations, xml_harvard) —
// extractOpinionText() below checks all of them in priority order and logs
// if none are present, rather than assuming one is correct.
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ANTHROPIC_API_KEY
// (same key api/claude.js already uses), COURTLISTENER_API_TOKEN (for the
// 'process' action only — 'report' and 'feedback' work without it, reading
// whatever has already been cached).
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');
const { tokenFromRequest, verifySessionToken } = require('./_lib/auth');
const { writeAuditLog } = require('./_lib/audit');
const cl = require('./_lib/courtlistener');

// The 5 real treatment labels from the brief, plus 'unclear' — added so a
// low-agreement result has somewhere honest to land instead of being forced
// into a confident-looking label it didn't earn (see aggregateTreatment()).
const TREATMENT_LABELS = ['followed', 'distinguished', 'questioned', 'overruled', 'criticized', 'unclear'];
const NEGATIVE_LABELS = ['overruled', 'questioned', 'criticized', 'distinguished']; // severity order, most to least serious
const MAX_OPINIONS_PER_INVOCATION = 3; // stay well inside the per-minute CourtListener budget in one request

function sbClient() { return cl.sbClient(); }

function extractOpinionText(opinionData) {
  const candidates = ['plain_text', 'html_with_citations', 'html_lawbox', 'html_columbia', 'html', 'xml_harvard'];
  for (const field of candidates) {
    if (opinionData && opinionData[field] && String(opinionData[field]).trim()) {
      return { text: String(opinionData[field]), field };
    }
  }
  return { text: '', field: null };
}

// Real text search for the sentence(s) that actually mention the cited
// case, by case name and/or citation string — item 3 requires the real
// supporting sentence, not an AI-invented one, so this is done by string
// search against the real fetched text BEFORE the text is ever sent to
// Claude, and the same extracted excerpt is what gets stored as evidence.
function findCitingExcerpt(fullText, caseName, citation) {
  const plain = fullText.replace(/<[^>]+>/g, ' '); // strip any HTML tags if the field was an HTML variant
  const sentences = plain.split(/(?<=[.;])\s+(?=[A-Z(])/);
  const needles = [citation, caseName].filter(Boolean).map((s) => s.toLowerCase());
  let bestIdx = -1;
  for (let i = 0; i < sentences.length; i++) {
    const lower = sentences[i].toLowerCase();
    if (needles.some((n) => n && lower.indexOf(n) !== -1)) { bestIdx = i; break; }
  }
  if (bestIdx === -1) return null;
  const start = Math.max(0, bestIdx - 1);
  const end = Math.min(sentences.length, bestIdx + 2);
  return {
    supporting_sentence: sentences[bestIdx].trim().slice(0, 2000),
    supporting_sentence_context: sentences.slice(start, end).join(' ').trim().slice(0, 4000)
  };
}

// Real multi-pass classification via the same Anthropic key api/claude.js
// already uses. Three passes, varied framing (not three identical calls) —
// one neutral, one deliberately checking for negative treatment first, one
// deliberately checking for positive treatment first — so a single framing
// bias in one direction doesn't silently dominate the result. CRITICAL:
// the model is given ONLY the real extracted excerpt, never asked to recall
// anything about either case from training data — this is the same
// citation-grounding discipline as the AI Assistant/AI Document Drafting,
// applied to classification instead of generation.
async function classifyPass(excerpt, citedCaseLabel, citingCaseLabel, framingHint) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) { const e = new Error('ANTHROPIC_API_KEY not set'); e.code = 'CONFIG'; throw e; }
  const system = 'You classify how one court opinion treats a case it cites, using ONLY the real excerpt of the citing opinion given to you below — never your own knowledge of either case, which you must not rely on or reference. Respond in exactly this format: first line is exactly one of these words: followed, distinguished, questioned, overruled, criticized, unclear. Second line onward: quote the exact sentence(s) from the given excerpt that support your classification, copied verbatim, no paraphrasing. If the excerpt does not clearly show a treatment, respond "unclear" and quote the most relevant available sentence anyway.' + (framingHint ? (' ' + framingHint) : '');
  const userMsg = 'Cited case: ' + citedCaseLabel + '\nCiting opinion: ' + citingCaseLabel + '\n\nExcerpt:\n' + excerpt;
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 400, system, messages: [{ role: 'user', content: userMsg }] })
  });
  const data = await r.json();
  if (!r.ok) { const e = new Error((data && data.error && data.error.message) || 'Anthropic error'); e.status = r.status; throw e; }
  const text = (data.content && data.content[0] && data.content[0].text) || '';
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  const firstWord = (lines[0] || '').toLowerCase().replace(/[^a-z]/g, '');
  const label = TREATMENT_LABELS.indexOf(firstWord) !== -1 ? firstWord : 'unclear';
  const quote = lines.slice(1).join(' ').trim();
  return { label, quote };
}

// ASYMMETRIC CAUTION (brief item 4), implemented as a concrete, auditable
// rule — not a prompt instruction alone, which is exactly the kind of
// mitigation the AI Assistant's own citation rule already disclosed is
// NOT a hard guarantee. This function is the real enforcement point:
//   - ANY single pass flagging a negative treatment (distinguished/
//     questioned/overruled/criticized) is enough to surface that as the
//     final label — a low bar, deliberately, because a missed overrule is
//     the malpractice-class failure named in the brief.
//   - "followed" (affirmatively still-good-law) is reported with its TRUE
//     agreement fraction, never rounded up to full confidence just because
//     no pass disagreed — a 2-of-3 "followed" result is shown as 67%
//     agreement, not silently promoted to a clean "followed" badge.
function aggregateTreatment(passResults) {
  const total = passResults.length || 1;
  const counts = {};
  passResults.forEach((p) => { counts[p.label] = (counts[p.label] || 0) + 1; });
  for (const label of NEGATIVE_LABELS) {
    if (counts[label]) {
      const supportingPass = passResults.find((p) => p.label === label);
      return { treatment: label, agreement_pct: counts[label] / total, evidence_quote: supportingPass ? supportingPass.quote : '' };
    }
  }
  if (counts.followed) {
    const supportingPass = passResults.find((p) => p.label === 'followed');
    return { treatment: 'followed', agreement_pct: counts.followed / total, evidence_quote: supportingPass ? supportingPass.quote : '' };
  }
  const unclearPass = passResults.find((p) => p.label === 'unclear') || passResults[0];
  return { treatment: 'unclear', agreement_pct: (counts.unclear || 0) / total, evidence_quote: unclearPass ? unclearPass.quote : '' };
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
  const action = body && body.action;
  if (['report', 'process', 'feedback', 'verify'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: report, process, feedback, verify' } });
    return;
  }

  let lic;
  try { lic = await validateLicenseKey(licenseKey); }
  catch (err) {
    if (err.code === 'CONFIG') { console.error('legal-citator config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }
    console.error('legal-citator license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  if (lic.app_id && lic.app_id !== 'sairnlaw') { res.status(403).json({ error: { code: 'WRONG_APP', message: 'This license is not issued for sairnlaw' } }); return; }

  let sb;
  try { sb = sbClient(); }
  catch (err) { console.error('legal-citator supabase config error:', err.message); res.status(500).json({ error: { message: 'Server configuration error — contact support' } }); return; }

  // AUDIT (2026-08-08, Phase 3): who ran which research lookup. The session
  // token is OPTIONAL here on purpose -- this endpoint's own access control
  // is the bearer license (unchanged), and requiring a session token would
  // break every existing caller. When a valid SAIRNlaw session token IS
  // present, the log names the actual attorney; when it isn't, employee_id
  // is logged as null rather than guessed or attributed to anyone.
  const caller = verifySessionToken(tokenFromRequest(req), lic.license_hash, 'sairnlaw');
  const auditLookup = (detail) => writeAuditLog(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
    license_hash: lic.license_hash,
    employee_id: caller ? caller.employee_id : null,
    role: caller ? caller.role : null,
    event_type: 'citator_lookup',
    detail
  });

  try {
    // ── REPORT (brief items 3 + 5): return whatever is ALREADY cached, plus
    // an honest coverage statement. Never triggers a new CourtListener call
    // — 'process' does that. Works even with no token configured. ──
    // ── VERIFY: does this citation resolve to a real case? ──────────────
    // Added 2026-08-23. The mock-trial panel was calling a 'lookup' action
    // that never existed, so EVERY citation it checked came back unverified
    // -- including Brady v. Maryland. It failed safe but was a false
    // negative on 100% of inputs, which makes the badge worthless.
    //
    // TWO DESIGN CONSTRAINTS DROVE THE SHAPE, both from the real limits
    // documented in api/courtlistener.js rather than assumed:
    //
    // 1. CACHE FIRST. A citation-to-case resolution is immutable -- Brady is
    //    always 373 U.S. 83 -- so a cached hit costs no upstream budget at
    //    all. Reuses cl_case_cache rather than adding a table, deliberately:
    //    an unrun migration would leave this feature dead on arrival, which
    //    is the failure mode already blocking Wex and CanLII.
    //
    // 2. BATCH THE MISSES INTO ONE UPSTREAM CALL. CourtListener allows 5
    //    requests/minute, 50/hour, 125/day for ALL SAIRNlaw firms combined
    //    through one shared token. The mock-trial panel checks up to six
    //    citations per run, so one-call-per-citation would exhaust the
    //    per-minute budget on a single run and the daily budget in about
    //    twenty. /citation-lookup/ extracts every citation from one blob of
    //    text, which is how it is meant to be used, so six citations cost
    //    ONE budget unit instead of six.
    //
    // Budget exhaustion is reported as UNAVAILABLE, never as 'not found'.
    // Those are different facts and conflating them is the exact defect this
    // action exists to fix.
    if (action === 'verify') {
      const raw = Array.isArray(body.citations) ? body.citations : (body.citation ? [body.citation] : []);
      const cites = raw.map((c) => String(c || '').replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, 12);
      if (!cites.length) { res.status(400).json({ error: { message: 'verify requires citations (array) or citation (string)' } }); return; }

      const out = {};
      cites.forEach((c) => { out[c] = { citation: c, state: 'unavailable', reason: 'not checked yet' }; });

      // Cache pass -- costs no upstream budget.
      try {
        const q = cites.map((c) => '"' + c.replace(/"/g, '') + '"').join(',');
        const cr = await fetch(sb.rest('cl_case_cache?citation=in.(' + encodeURIComponent(q) + ')&select=cl_cluster_id,case_name,citation'), { headers: sb.headers });
        if (cr.ok) {
          const rows = await cr.json();
          (Array.isArray(rows) ? rows : []).forEach((row) => {
            if (row && row.citation && out[row.citation]) {
              out[row.citation] = { citation: row.citation, state: 'verified', source: 'cache',
                cluster_id: row.cl_cluster_id, case_name: row.case_name,
                source_url: 'https://www.courtlistener.com/opinion/' + row.cl_cluster_id + '/' };
            }
          });
        }
      } catch (e) { /* a cache miss is not a failure; fall through to upstream */ }

      const misses = cites.filter((c) => out[c].state !== 'verified');

      if (misses.length) {
        if (!process.env.COURTLISTENER_API_TOKEN) {
          misses.forEach((c) => { out[c] = { citation: c, state: 'unavailable', reason: 'CourtListener API token is not configured, so citations cannot be checked.' }; });
        } else {
          let budget = null;
          try { budget = await cl.remainingBudget(); } catch (e) { budget = null; }
          if (budget && (budget.minute <= 0 || budget.hour <= 0 || budget.day <= 0)) {
            misses.forEach((c) => { out[c] = { citation: c, state: 'unavailable', reason: 'CourtListener rate limit reached; try again shortly. This is a limit, not a finding about the citation.' }; });
          } else {
            try {
              const lookup = await cl.clCitationLookup(misses.join('\n'));
              const results = Array.isArray(lookup) ? lookup : (lookup && lookup.results) || [];
              results.forEach((r) => {
                const key = misses.find((m) => m === String(r.citation || '').trim()) ||
                  misses.find((m) => String(r.citation || '').indexOf(m) !== -1) ||
                  misses.find((m) => m.indexOf(String(r.citation || '').trim()) !== -1);
                if (!key) return;
                const clusters = r.clusters || [];
                if (Number(r.status) === 200 && clusters.length) {
                  const c0 = clusters[0];
                  out[key] = { citation: key, state: 'verified', source: 'courtlistener',
                    cluster_id: c0.id || null, case_name: c0.case_name || c0.caseName || null,
                    date_filed: c0.date_filed || null,
                    source_url: c0.absolute_url ? ('https://www.courtlistener.com' + c0.absolute_url)
                      : (c0.id ? 'https://www.courtlistener.com/opinion/' + c0.id + '/' : null) };
                } else if (Number(r.status) === 404) {
                  out[key] = { citation: key, state: 'not_found',
                    reason: 'CourtListener has no case at this citation. It may be misquoted, or it may not exist.' };
                } else if (Number(r.status) === 300) {
                  out[key] = { citation: key, state: 'ambiguous', matches: clusters.length,
                    reason: 'This citation matches more than one case, so it was not resolved to one. Check it by hand.' };
                } else {
                  out[key] = { citation: key, state: 'unavailable',
                    reason: 'CourtListener returned status ' + r.status + ' for this citation.' };
                }
              });
              // Anything the upstream never mentioned was not checked.
              misses.forEach((c) => {
                if (out[c].state === 'unavailable' && out[c].reason === 'not checked yet') {
                  out[c] = { citation: c, state: 'not_found',
                    reason: 'CourtListener did not recognise this as a citation at all.' };
                }
              });
              // Write verified resolutions back so the next check is free.
              const fresh = misses.map((c) => out[c]).filter((v) => v.state === 'verified' && v.cluster_id);
              for (const v of fresh) {
                try {
                  await fetch(sb.rest('cl_case_cache?on_conflict=cl_cluster_id'), { method: 'POST',
                    headers: Object.assign({}, sb.headers, { Prefer: 'resolution=merge-duplicates,return=minimal' }),
                    body: JSON.stringify({ cl_cluster_id: v.cluster_id, case_name: v.case_name || v.citation, citation: v.citation }) });
                } catch (e) { /* caching is an optimisation, never a correctness requirement */ }
              }
            } catch (e) {
              console.error('citation-lookup failed:', e && e.message);
              misses.forEach((c) => {
                if (out[c].state === 'unavailable') {
                  out[c] = { citation: c, state: 'unavailable', reason: 'Citation checking is temporarily unavailable.' };
                }
              });
            }
          }
        }
      }

      const results = cites.map((c) => out[c]);
      await auditLookup({ action: 'verify', checked: cites.length,
        verified: results.filter((r) => r.state === 'verified').length,
        upstream_calls: misses.length ? 1 : 0 });
      res.status(200).json({ ok: true, results: results,
        note: 'A citation is only reported verified when CourtListener resolves it to a real case. Anything else is reported as what it is -- not found, ambiguous, or unchecked -- never as a silent pass.' });
      return;
    }

    if (action === 'report') {
      const citedClusterId = body.cited_cluster_id;
      if (!citedClusterId) { res.status(400).json({ error: { message: 'report requires cited_cluster_id' } }); return; }
      const treatR = await fetch(sb.rest('cl_citing_treatments?cited_cluster_id=eq.' + encodeURIComponent(citedClusterId) + '&order=court_hierarchy_weight.asc'), { headers: sb.headers });
      const treatments = await treatR.json();
      if (!treatR.ok) { res.status(502).json({ error: { message: 'Data store error — try again' } }); return; }
      const covR = await fetch(sb.rest('cl_coverage?cited_cluster_id=eq.' + encodeURIComponent(citedClusterId) + '&limit=1'), { headers: sb.headers });
      const covRows = await covR.json();
      const coverage = (Array.isArray(covRows) && covRows[0]) || null;
      await auditLookup({ action: 'report', cited_cluster_id: Number(citedClusterId) });
      const breakdown = {};
      TREATMENT_LABELS.forEach((l) => { breakdown[l] = 0; });
      (treatments || []).forEach((t) => { breakdown[t.final_treatment] = (breakdown[t.final_treatment] || 0) + 1; });
      res.status(200).json({
        ok: true,
        data: {
          treatments: treatments || [],
          breakdown,
          coverage: coverage || { cited_cluster_id: Number(citedClusterId), total_citing_reported: null, total_citing_processed: 0, processing_status: 'not_started' }
        }
      });
      return;
    }

    // ── FEEDBACK (brief item 6): log a real attorney confirm/correction. ──
    if (action === 'feedback') {
      const treatmentId = body.treatment_id, fbAction = body.feedback_action, correctedTo = body.corrected_to, note = body.note;
      if (!treatmentId || (fbAction !== 'confirmed' && fbAction !== 'corrected')) {
        res.status(400).json({ error: { message: 'feedback requires treatment_id and feedback_action (confirmed|corrected)' } });
        return;
      }
      if (fbAction === 'corrected' && TREATMENT_LABELS.indexOf(correctedTo) === -1) {
        res.status(400).json({ error: { message: 'corrected_to must be one of: ' + TREATMENT_LABELS.join(', ') } });
        return;
      }
      const logRec = { license_hash: lic.license_hash, app_id: 'sairnlaw', treatment_id: treatmentId, action: fbAction, corrected_to: fbAction === 'corrected' ? correctedTo : null, note: (note || '').slice(0, 2000) };
      const r = await fetch(sb.rest('cl_feedback_log'), { method: 'POST', headers: Object.assign({}, sb.headers, { Prefer: 'return=minimal' }), body: JSON.stringify(logRec) });
      if (!r.ok) { const errBody = await r.text(); console.error('feedback insert failed:', errBody); res.status(502).json({ error: { message: 'Data store error — try again' } }); return; }
      const counterField = fbAction === 'confirmed' ? 'feedback_confirm_count' : 'feedback_correct_count';
      const curR = await fetch(sb.rest('cl_citing_treatments?id=eq.' + encodeURIComponent(treatmentId) + '&select=' + counterField), { headers: sb.headers });
      const curRows = await curR.json();
      const current = (Array.isArray(curRows) && curRows[0] && curRows[0][counterField]) || 0;
      await fetch(sb.rest('cl_citing_treatments?id=eq.' + encodeURIComponent(treatmentId)), {
        method: 'PATCH', headers: Object.assign({}, sb.headers, { Prefer: 'return=minimal' }),
        body: JSON.stringify({ [counterField]: current + 1, updated_at: new Date().toISOString() })
      });
      res.status(200).json({ ok: true });
      return;
    }

    // ── PROCESS (brief item 2): fetch + classify a real, rate-limit-bounded
    // batch of not-yet-processed citing opinions. Meant to be called
    // repeatedly (e.g. by the client, or a future scheduled job) — each
    // call advances real coverage by up to MAX_OPINIONS_PER_INVOCATION,
    // never claims to finish a large case in one request. Requires the
    // token (guarded below), unlike 'report'/'feedback'. ──
    if (action === 'process') {
      if (!process.env.COURTLISTENER_API_TOKEN) {
        res.status(503).json({ error: { code: 'NOT_CONFIGURED', message: 'CourtListener API token is not configured yet — see api/courtlistener.js.' } });
        return;
      }
      const citedClusterId = body.cited_cluster_id, citedOpinionId = body.cited_opinion_id, caseName = body.case_name, citation = body.citation;
      if (!citedClusterId || !citedOpinionId || !caseName) {
        res.status(400).json({ error: { message: 'process requires cited_cluster_id, cited_opinion_id, case_name' } });
        return;
      }
      await auditLookup({ action: 'process', cited_cluster_id: Number(citedClusterId), case_name: String(caseName).slice(0, 300) });

      // LIVE-VERIFIED 2026-08-08 (real token, real data, first end-to-end
      // run): opinionData.cluster is a plain URL STRING
      // ("https://.../clusters/{id}/"), not a nested object -- the earlier
      // guess (opinionData.cluster.case_name / .docket.court) was wrong,
      // confirmed via a real /opinions/{id}/ response, and silently
      // produced null/placeholder values rather than crashing. Real fix:
      // resolve that URL to a real cluster fetch (cached in cl_case_cache
      // so repeat lookups of the same citing case don't re-spend budget) to
      // get the real case_name. Court info requires a SECOND real hop past
      // that (cluster.docket is ALSO just a URL, to a docket that has no
      // court field inlined -- confirmed live) -- deferred, not fixed here,
      // specifically because of the real, very small rate budget: adding a
      // third real call per citing opinion (opinion text + cluster + docket)
      // would make MAX_OPINIONS_PER_INVOCATION=3 cost up to 9 CourtListener
      // calls in one request, dangerously close to blowing the per-minute
      // safety margin. court_hierarchy_weight stays null until a follow-up
      // adds a docket-detail helper and the budget math is redone for a
      // 3-calls-per-opinion cost -- flagged here, not silently left broken.
      async function resolveClusterCaseName(clusterUrl) {
        const m = /\/clusters\/(\d+)\//.exec(clusterUrl || '');
        if (!m) return null;
        const clusterId = Number(m[1]);
        const cacheR = await fetch(sb.rest('cl_case_cache?cl_cluster_id=eq.' + clusterId + '&limit=1'), { headers: sb.headers });
        const cacheRows = await cacheR.json();
        if (Array.isArray(cacheRows) && cacheRows[0]) return cacheRows[0].case_name;
        const clusterData = await cl.clCluster(clusterId);
        if (clusterData && clusterData.case_name) {
          await fetch(sb.rest('cl_case_cache'), { method: 'POST', headers: Object.assign({}, sb.headers, { Prefer: 'resolution=merge-duplicates,return=minimal' }), body: JSON.stringify({ cl_cluster_id: clusterId, case_name: clusterData.case_name, citation: (clusterData.citations && clusterData.citations[0]) ? (clusterData.citations[0].volume + ' ' + clusterData.citations[0].reporter + ' ' + clusterData.citations[0].page) : null, cite_count: clusterData.citation_count || null }) });
          return clusterData.case_name;
        }
        return null;
      }

      const budget = await cl.remainingBudget();
      const callsAvailable = Math.min(budget.minute, budget.hour, budget.day);
      if (callsAvailable <= 2) {
        res.status(429).json({ error: { code: 'CL_RATE_LIMITED', message: 'CourtListener request budget is exhausted right now (shared across all SAIRNlaw firms) — try again shortly.' } });
        return;
      }

      // Real total_citing_reported (brief item 5): the cited case's own
      // cluster.citation_count -- NOT opinions-cited's own `count` field,
      // which live-verified 2026-08-08 does not reliably return a plain
      // number (returned a cursor-pagination URL string in a real test
      // against a high-citation-count case). Cached the same way as citing
      // opinions' case names, so this doesn't re-spend budget on repeat
      // report views of the same case.
      let citedCaseCiteCount = null;
      try {
        const citedCacheR = await fetch(sb.rest('cl_case_cache?cl_cluster_id=eq.' + citedClusterId + '&limit=1'), { headers: sb.headers });
        const citedCacheRows = await citedCacheR.json();
        if (Array.isArray(citedCacheRows) && citedCacheRows[0] && citedCacheRows[0].cite_count !== null) {
          citedCaseCiteCount = citedCacheRows[0].cite_count;
        } else {
          const citedClusterData = await cl.clCluster(citedClusterId);
          citedCaseCiteCount = (citedClusterData && typeof citedClusterData.citation_count === 'number') ? citedClusterData.citation_count : null;
          await fetch(sb.rest('cl_case_cache'), { method: 'POST', headers: Object.assign({}, sb.headers, { Prefer: 'resolution=merge-duplicates,return=minimal' }), body: JSON.stringify({ cl_cluster_id: citedClusterId, case_name: caseName, citation: citation || null, cite_count: citedCaseCiteCount }) });
        }
      } catch (e) { console.error('cited-case cluster fetch failed:', e.message); }

      const citingListData = await cl.clCitingOpinions(citedOpinionId);
      const citingRefs = (citingListData && citingListData.results) || [];

      const alreadyR = await fetch(sb.rest('cl_citing_treatments?cited_cluster_id=eq.' + encodeURIComponent(citedClusterId) + '&select=citing_opinion_id'), { headers: sb.headers });
      const alreadyRows = await alreadyR.json();
      const alreadyIds = new Set((Array.isArray(alreadyRows) ? alreadyRows : []).map((r) => r.citing_opinion_id));

      // Each citing opinion now costs 2 real CourtListener calls (opinion
      // text + cluster, for the real case name) instead of 1 -- budget math
      // updated accordingly rather than left stale after the fix above.
      const maxByBudget = Math.floor((callsAvailable - 1) / 2); // -1 reserves the opinions-cited call already spent above
      const toProcess = citingRefs
        .map((ref) => { const m = /\/opinions\/(\d+)\//.exec(ref.citing_opinion || ''); return m ? Number(m[1]) : null; })
        .filter((id) => id && !alreadyIds.has(id))
        .slice(0, Math.max(0, Math.min(MAX_OPINIONS_PER_INVOCATION, maxByBudget)));

      const processedNow = [];
      for (const citingOpinionId of toProcess) {
        let opinionData;
        try { opinionData = await cl.clOpinionText(citingOpinionId); }
        catch (e) { console.error('opinion fetch failed for', citingOpinionId, e.message); continue; }
        const { text } = extractOpinionText(opinionData);
        if (!text) { console.error('no recognized full-text field on opinion', citingOpinionId, '— see extractOpinionText() header comment'); continue; }
        const excerptData = findCitingExcerpt(text, caseName, citation || '');
        if (!excerptData) continue; // cited case name/citation not actually found in the text — do not fabricate a classification with no real excerpt

        let citingCaseName = 'Opinion ' + citingOpinionId;
        try {
          const resolvedName = await resolveClusterCaseName(opinionData.cluster);
          if (resolvedName) citingCaseName = resolvedName;
        } catch (e) { console.error('cluster case-name resolve failed for', citingOpinionId, e.message); }
        // Deferred pending a docket-detail helper -- see the header comment
        // on resolveClusterCaseName() above for exactly why, not silently
        // left unexplained.
        const citingCourtId = null;

        let courtWeight = null;
        if (citingCourtId) {
          const courtCacheR = await fetch(sb.rest('cl_court_cache?id=eq.' + encodeURIComponent(citingCourtId) + '&limit=1'), { headers: sb.headers });
          const courtCacheRows = await courtCacheR.json();
          if (Array.isArray(courtCacheRows) && courtCacheRows[0]) {
            courtWeight = courtCacheRows[0].position;
          } else {
            try {
              const courtData = await cl.clCourt(citingCourtId);
              const courtRow = courtData && courtData.results && courtData.results[0];
              if (courtRow) {
                courtWeight = courtRow.position;
                await fetch(sb.rest('cl_court_cache'), { method: 'POST', headers: Object.assign({}, sb.headers, { Prefer: 'resolution=merge-duplicates,return=minimal' }), body: JSON.stringify({ id: courtRow.id, full_name: courtRow.full_name, jurisdiction: courtRow.jurisdiction, position: courtRow.position, parent_court: courtRow.parent_court, appeals_to: courtRow.appeals_to || [] }) });
              }
            } catch (e) { console.error('court fetch failed for', citingCourtId, e.message); }
          }
        }

        // Three passes, varied framing — see classifyPass()'s own comment.
        let passes;
        try {
          passes = await Promise.all([
            classifyPass(excerptData.supporting_sentence_context, caseName + (citation ? ' (' + citation + ')' : ''), citingCaseName, ''),
            classifyPass(excerptData.supporting_sentence_context, caseName + (citation ? ' (' + citation + ')' : ''), citingCaseName, 'Look specifically for any sign of negative treatment (disagreement, limitation, distinguishing, or rejection) first — only conclude "followed" if you find no such sign.'),
            classifyPass(excerptData.supporting_sentence_context, caseName + (citation ? ' (' + citation + ')' : ''), citingCaseName, 'Look specifically for any sign of positive/affirming treatment first — only conclude a negative label if the text does not read as simply following the cited case.')
          ]);
        } catch (e) { console.error('classification failed for', citingOpinionId, e.message); continue; }

        const agg = aggregateTreatment(passes);
        const record = {
          cited_cluster_id: citedClusterId,
          citing_opinion_id: citingOpinionId,
          citing_case_name: citingCaseName,
          citing_court_id: citingCourtId,
          court_hierarchy_weight: courtWeight,
          run_results: passes,
          final_treatment: agg.treatment,
          agreement_pct: agg.agreement_pct,
          caution_threshold_applied: NEGATIVE_LABELS.indexOf(agg.treatment) !== -1 ? (1 / passes.length) : 1.0,
          supporting_sentence: agg.evidence_quote || excerptData.supporting_sentence,
          supporting_sentence_context: excerptData.supporting_sentence_context,
          source_url: 'https://www.courtlistener.com/opinion/' + citingOpinionId + '/'
        };
        await fetch(sb.rest('cl_citing_treatments?on_conflict=cited_cluster_id,citing_opinion_id'), {
          method: 'POST', headers: Object.assign({}, sb.headers, { Prefer: 'resolution=merge-duplicates,return=minimal' }), body: JSON.stringify(record)
        });
        processedNow.push({ citing_opinion_id: citingOpinionId, treatment: agg.treatment, agreement_pct: agg.agreement_pct });
      }

      // citedCaseCiteCount (real cluster.citation_count, resolved above) is
      // the reliable real total -- opinions-cited's own `count` field is
      // kept only as a fallback for the rare case the cluster fetch failed.
      const totalReported = citedCaseCiteCount !== null ? citedCaseCiteCount : (citingListData && typeof citingListData.count === 'number' ? citingListData.count : null);
      const totalProcessedR = await fetch(sb.rest('cl_citing_treatments?cited_cluster_id=eq.' + encodeURIComponent(citedClusterId) + '&select=id'), { headers: sb.headers });
      const totalProcessedRows = await totalProcessedR.json();
      const totalProcessed = Array.isArray(totalProcessedRows) ? totalProcessedRows.length : 0;
      const status = totalReported !== null && totalProcessed >= totalReported ? 'complete_within_filter' : 'in_progress';
      await fetch(sb.rest('cl_coverage?on_conflict=cited_cluster_id'), {
        method: 'POST', headers: Object.assign({}, sb.headers, { Prefer: 'resolution=merge-duplicates,return=minimal' }),
        body: JSON.stringify({ cited_cluster_id: citedClusterId, total_citing_reported: totalReported, total_citing_processed: totalProcessed, last_processed_at: new Date().toISOString(), processing_status: status, updated_at: new Date().toISOString() })
      });

      res.status(200).json({ ok: true, data: { processed_this_call: processedNow, total_citing_reported: totalReported, total_citing_processed: totalProcessed, more_remaining: totalReported !== null ? totalProcessed < totalReported : null } });
      return;
    }

    res.status(400).json({ error: { message: 'Unsupported action' } });
  } catch (err) {
    console.error('api/legal-citator error:', err);
    if (err.code === 'NOT_CONFIGURED') { res.status(503).json({ error: { code: 'NOT_CONFIGURED', message: err.message } }); return; }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }
};
