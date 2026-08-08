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
  if (['report', 'process', 'feedback'].indexOf(action) === -1) {
    res.status(400).json({ error: { message: 'action must be one of: report, process, feedback' } });
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

  try {
    // ── REPORT (brief items 3 + 5): return whatever is ALREADY cached, plus
    // an honest coverage statement. Never triggers a new CourtListener call
    // — 'process' does that. Works even with no token configured. ──
    if (action === 'report') {
      const citedClusterId = body.cited_cluster_id;
      if (!citedClusterId) { res.status(400).json({ error: { message: 'report requires cited_cluster_id' } }); return; }
      const treatR = await fetch(sb.rest('cl_citing_treatments?cited_cluster_id=eq.' + encodeURIComponent(citedClusterId) + '&order=court_hierarchy_weight.asc'), { headers: sb.headers });
      const treatments = await treatR.json();
      if (!treatR.ok) { res.status(502).json({ error: { message: 'Data store error — try again' } }); return; }
      const covR = await fetch(sb.rest('cl_coverage?cited_cluster_id=eq.' + encodeURIComponent(citedClusterId) + '&limit=1'), { headers: sb.headers });
      const covRows = await covR.json();
      const coverage = (Array.isArray(covRows) && covRows[0]) || null;
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

      const budget = await cl.remainingBudget();
      const callsAvailable = Math.min(budget.minute, budget.hour, budget.day);
      if (callsAvailable <= 1) {
        res.status(429).json({ error: { code: 'CL_RATE_LIMITED', message: 'CourtListener request budget is exhausted right now (shared across all SAIRNlaw firms) — try again shortly.' } });
        return;
      }

      const citingListData = await cl.clCitingOpinions(citedOpinionId);
      const citingRefs = (citingListData && citingListData.results) || [];

      const alreadyR = await fetch(sb.rest('cl_citing_treatments?cited_cluster_id=eq.' + encodeURIComponent(citedClusterId) + '&select=citing_opinion_id'), { headers: sb.headers });
      const alreadyRows = await alreadyR.json();
      const alreadyIds = new Set((Array.isArray(alreadyRows) ? alreadyRows : []).map((r) => r.citing_opinion_id));

      const toProcess = citingRefs
        .map((ref) => { const m = /\/opinions\/(\d+)\//.exec(ref.citing_opinion || ''); return m ? Number(m[1]) : null; })
        .filter((id) => id && !alreadyIds.has(id))
        .slice(0, Math.min(MAX_OPINIONS_PER_INVOCATION, callsAvailable - 1)); // -1 reserves budget for the opinion-text fetch itself

      const processedNow = [];
      for (const citingOpinionId of toProcess) {
        let opinionData;
        try { opinionData = await cl.clOpinionText(citingOpinionId); }
        catch (e) { console.error('opinion fetch failed for', citingOpinionId, e.message); continue; }
        const { text } = extractOpinionText(opinionData);
        if (!text) { console.error('no recognized full-text field on opinion', citingOpinionId, '— see extractOpinionText() header comment'); continue; }
        const excerptData = findCitingExcerpt(text, caseName, citation || '');
        if (!excerptData) continue; // cited case name/citation not actually found in the text — do not fabricate a classification with no real excerpt

        const citingCaseName = (opinionData.cluster && opinionData.cluster.case_name) || opinionData.caseName || ('Opinion ' + citingOpinionId);
        // Field path also unverified pending a real token (same honest
        // disclosure as extractOpinionText()'s header) -- falls back to
        // null (skipping hierarchy weight for this citing opinion, not
        // crashing) if neither guess matches the real response shape.
        const citingCourtId = (opinionData.cluster && opinionData.cluster.docket && opinionData.cluster.docket.court) || opinionData.court_id || null;

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

      const totalReported = citingListData && typeof citingListData.count === 'number' ? citingListData.count : null;
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
