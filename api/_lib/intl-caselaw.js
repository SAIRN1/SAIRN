// api/_lib/intl-caselaw.js
// ---------------------------------------------------------------------------
// International case-law grounding for SAIRNlaw's citator (Phase B).
//
// ── WHICH SOURCES, AND WHY NOT THE ONES ORIGINALLY ASKED FOR ─────────────
// The brief named BAILII (UK/Ireland), CanLII (Canada) and AustLII
// (Australia). Each was checked against its OWN primary terms before any code
// was written, and two of the three refuse this use outright:
//
//   BAILII  -- NOT USED. Prohibits bulk downloading and scraping in its
//              standard user agreement and restricts crawlers. Its stated
//              reason is concern about AI software built to predict case
//              outcomes -- i.e. it names this product category.
//   AustLII -- NOT USED. Its usage policy prohibits "spidering, scraping,
//              crawling, mirroring, page framing, API access, bulk querying,
//              automated agents", and it blocks automated access for
//              AI-related uses across its entire collection. Its
//              educational-permission carve-out is itself stated as
//              excluding AI-related uses.
//
// Neither is a bot-detection problem, so no amount of better scraping tooling
// would make it legitimate -- the permission is explicitly refused, and
// routing around that with a commercial scraping connector would make it a
// deliberate violation rather than an incidental one. Australia and
// Ireland/Scotland are therefore NOT COVERED, and the UI says so rather than
// implying worldwide reach the tool does not have.
//
// What IS used, under terms that actually permit it:
//   UK (E&W) -- Find Case Law, The National Archives. Real public API, no
//               authentication, published limit of 1,000 requests per rolling
//               5 minutes per IP. Content is under the Open Justice Licence,
//               which expressly permits commercial use and incorporation into
//               a product. IMPORTANT BOUNDARY: that licence does NOT cover
//               "computational analysis", defined as programmatic searching in
//               bulk to identify, extract or enrich contents. So this client
//               does on-demand lookups for a case the user actually asked
//               about and never sweeps the corpus. Coverage is England &
//               Wales from 2001, which is why it does not replace BAILII's
//               Irish and Scottish material.
// Canada was ALSO built, via CanLII's official keyed REST API, and has since
// been REMOVED ENTIRELY (2026-08-23) -- client, endpoints and helpers. It was
// never a terms problem: CanLII's keyed API is the sanctioned route and the
// implementation was correct. It was a scope decision. No CANLII_API_KEY was
// ever configured, so the code shipped dormant for its whole life while the
// coverage panel advertised Canada as supported, and no caller in
// sairnlaw.html ever referenced it. Deleted rather than left waiting for a
// key that is not coming. If Canada is ever back in scope, rebuild against
// CanLII's current API terms rather than restoring this from history --
// CanLII filed a claim in Nov 2024 against an AI legal-research platform over
// systematic scraping, so their position on automated use is actively
// evolving and a two-year-old implementation is not a safe starting point.
//
// GROUNDING CONTRACT, same as the CourtListener citator: every result carries
// the real source URL it came from. There is no success shape without one, and
// callers must never substitute model memory when a lookup fails.
// ---------------------------------------------------------------------------

const { sbClient } = require('./courtlistener');

// ── Jurisdiction coverage, stated as data so the UI can render it honestly ──
//
// SCOPE, decided 2026-08-23: SAIRNlaw's international footprint is the United
// States (CourtListener) and the United Kingdom, England & Wales only (Find
// Case Law). That is the whole list. Everything else is out of scope.
//
// CANADA WAS REMOVED, deliberately, and should not be re-added without a new
// decision. A Guardian pass the same day found this table asserting
// { code: 'ca', covered: true } while every canlii_browse call returned 503
// NOT_CONFIGURED -- the panel whose entire job is honest disclosure was the
// one making a false claim. The fix considered first was to derive Canada's
// status from whether CANLII_API_KEY was set; that was rejected in favour of
// dropping Canada outright, because a row reading "not yet configured" is an
// aspirational placeholder, and a placeholder in a coverage table reads to a
// lawyer as a roadmap promise. Not pursuing CanLII is a scope decision, not a
// blocked task, so the honest representation of it is absence.
//
// Scotland / NI / Ireland and Australia stay listed as NOT covered, because
// their exclusion is a fact a user needs (their own terms prohibit this use --
// no engineering closes it), not a gap anyone should try to fill.
const COVERAGE = [
  { code: 'us', label: 'United States', covered: true, source: 'CourtListener', note: 'Federal and state opinions.' },
  { code: 'uk-ew', label: 'United Kingdom (England & Wales)', covered: true, source: 'Find Case Law (The National Archives)', note: 'Judgments and tribunal decisions from 2001 onwards, under the Open Justice Licence.' },
  { code: 'uk-scot-ni-ie', label: 'Scotland, Northern Ireland, Ireland', covered: false, source: null, note: 'Not covered. The main free source (BAILII) prohibits automated access in its user agreement, and Find Case Law covers England & Wales only.' },
  { code: 'au', label: 'Australia', covered: false, source: null, note: 'Not covered. AustLII’s usage policy prohibits automated access and blocks AI-related uses across its entire collection.' }
];

// ── Find Case Law ─────────────────────────────────────────────────────────
const FCL_BASE = 'https://caselaw.nationalarchives.gov.uk';
// Published limit, read from the service's own public API documentation.
// Held well under the real ceiling rather than at it, because the limit is
// per-IP and this deployment shares one egress IP across every SAIRNlaw firm.
const FCL_LIMIT = { seconds: 300, max: 200 };
const UA = 'SAIRNlaw/1.0 (legal research tool; contact michael@sairn.com)';

// The one function that must exist for the atomic path; named here so a
// rename in the SQL is a one-line change rather than a silent fallback.
const CONSUME_RPC = 'sairnlaw_rate_limit_consume';

async function checkLimitRacy(table, seconds, max) {
  const { headers, rest } = sbClient();
  const since = new Date(Date.now() - seconds * 1000).toISOString();
  const r = await fetch(rest(table + '?requested_at=gte.' + encodeURIComponent(since) + '&select=id'), { headers });
  // Missing table (PostgREST 404/400) is reported as NOT_PROVISIONED naming
  // the migration, not as a generic upstream error -- the latter reads as a
  // network problem when the real cause is actionable. Still fails CLOSED:
  // without the ledger the published limit cannot be honoured, and a limit
  // that exists to be respected must not be skipped because its bookkeeping
  // is absent.
  if (r.status === 404 || r.status === 400) {
    return { limited: true, notProvisioned: true,
      message: 'The rate ledger (' + table + ') is not set up yet -- run ' +
        'sql/sairnlaw_wex_intl_schema.sql in Supabase. Lookups are refused ' +
        'until then rather than proceeding without honouring the source’s published limit.' };
  }
  if (!r.ok) throw new Error(table + ' limit check failed: HTTP ' + r.status);
  const rows = await r.json();
  if (Array.isArray(rows) && rows.length >= max) return { limited: true, max, seconds, racy: true };
  await fetch(rest(table), {
    method: 'POST',
    headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
    body: JSON.stringify({})
  });
  return { limited: false, racy: true };
}

// ── THE ATOMIC PATH. Item 78's race, swept here 2026-09-14. ───────────────
// checkLimitRacy above reads the window in one HTTP call and inserts in
// another, with nothing between them: N concurrent lookups all see the same
// count and all proceed. That is the shape docs/spec/RateLimitConsume.tla
// models and tools/rate_limit_race_model.js proves violates the cap. It was
// found and fixed for the AI limiter and for CourtListener; these two were
// never swept.
//
// THE FALLBACK IS KEPT AND IS LABELLED, not removed. Until
// sql/sairnlaw_rate_limit_consume_fn_2026-09-14.sql is run the RPC does not
// exist, and deleting the old path would take the feature down rather than
// leaving it exactly as it is today. Every result now carries `racy` so which
// path answered is visible in the return value rather than inferred -- the
// same decision api/_lib/ai-rate-limit.js made with its observe-racy mode.
async function checkLimit(table, seconds, max) {
  const { headers, rest } = sbClient();
  let r;
  try {
    r = await fetch(rest('rpc/' + CONSUME_RPC), {
      method: 'POST',
      headers: Object.assign({}, headers, { 'Content-Type': 'application/json' }),
      body: JSON.stringify({ p_table: table, p_window_seconds: seconds, p_max: max })
    });
  } catch (e) {
    // A NETWORK FAILURE IS NOT "UNDER THE LIMIT". Fall through to the racy
    // path, which does its own fail-closed handling, rather than returning a
    // permissive answer from a call that never completed.
    return checkLimitRacy(table, seconds, max);
  }
  if (r.status === 404) {
    // The function has not been created yet. Exactly today's behaviour.
    return checkLimitRacy(table, seconds, max);
  }
  if (!r.ok) return checkLimitRacy(table, seconds, max);
  const out = await r.json().catch(() => null);
  if (!out || typeof out.limited !== 'boolean') {
    // An allowlist refusal answers {error: ...} and has no `limited`. Treating
    // that as "not limited" would be the fail-open shape this whole sweep is
    // about, so it goes to the racy path, which still honours the window.
    return checkLimitRacy(table, seconds, max);
  }
  return out.limited
    ? { limited: true, max, seconds, racy: false }
    : { limited: false, racy: false };
}

function xmlTagText(chunk, tag) {
  const m = chunk.match(new RegExp('<' + tag + '[^>]*>([\\s\\S]*?)</' + tag + '>', 'i'));
  if (!m) return '';
  return m[1]
    .replace(/<[^>]+>/g, '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#0?39;|&apos;/g, "'")
    .replace(/\s+/g, ' ').trim();
}

function parseFclAtom(xml) {
  const entries = [];
  const re = /<entry>([\s\S]*?)<\/entry>/gi;
  let m;
  while ((m = re.exec(xml)) !== null) {
    const e = m[1];
    // The FIRST <link> is the judgment page. Later links in the same entry
    // point at data.xml, the PDF and the assets base, so an unanchored
    // match could hand back a PDF URL as though it were the case.
    const link = (e.match(/<link[^>]+href="([^"]+)"/i) || [])[1] || '';

    // The court sits in <author><name>, and the neutral citation in a
    // <tna:identifier type="ukncn">. BOTH WERE BEING DROPPED, and both
    // matter more here than ordinary metadata: the neutral citation is how
    // a lawyer actually cites the judgment, and the court is what tells
    // them its authority level. A Court of Appeal decision and a
    // first-instance High Court decision bind very differently, so a
    // result carrying neither is not merely thin -- it invites the reader
    // to weigh a case they cannot place. Found 2026-08-23 by diffing the
    // parsed output against the raw feed rather than assuming null meant
    // the field was absent upstream.
    const court = xmlTagText(e, 'name') || null;
    const ncnRaw = (e.match(/<tna:identifier[^>]*type="ukncn"[^>]*>([\s\S]*?)<\/tna:identifier>/i) || [])[1];
    const ncn = ncnRaw
      ? ncnRaw.replace(/<[^>]+>/g, '')
          .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"').replace(/&#0?39;|&apos;/g, "'")
          .replace(/\s+/g, ' ').trim()
      : null;

    entries.push({
      title: xmlTagText(e, 'title'),
      url: link,
      date: (xmlTagText(e, 'published') || xmlTagText(e, 'updated')).slice(0, 10),
      court: court,
      neutral_citation: ncn || null,
      jurisdiction: 'uk-ew',
      source_name: 'Find Case Law (The National Archives)'
    });
  }
  return entries;
}

// On-demand search for a case the user actually named. Deliberately capped and
// single-shot: the Open Justice Licence permits incorporating judgments into a
// product but NOT bulk programmatic searching to enrich a corpus, so this must
// stay a lookup and never become a sweep.
async function fclSearch(query, perPage) {
  const gate = await checkLimit('fcl_rate_limit_log', FCL_LIMIT.seconds, FCL_LIMIT.max);
  if (gate.notProvisioned) {
    return { ok: false, code: 'NOT_PROVISIONED', source: 'find-case-law', message: gate.message };
  }
  if (gate.limited) {
    return { ok: false, code: 'RATE_LIMITED', source: 'find-case-law',
      message: 'Find Case Law lookups are rate limited to stay well inside the service’s published ceiling. Try again shortly.' };
  }
  const n = Math.min(Math.max(parseInt(perPage, 10) || 5, 1), 10);
  const url = FCL_BASE + '/atom.xml?' + new URLSearchParams({
    query: String(query || '').slice(0, 300), order: '-date', per_page: String(n)
  }).toString();

  let r;
  try {
    r = await fetch(url, { headers: { 'User-Agent': UA, Accept: 'application/atom+xml' } });
  } catch (e) {
    return { ok: false, code: 'UPSTREAM', source: 'find-case-law', message: 'Could not reach Find Case Law just now.' };
  }
  if (r.status === 429) {
    return { ok: false, code: 'RATE_LIMITED', source: 'find-case-law', message: 'Find Case Law returned HTTP 429. Try again shortly.' };
  }
  if (!r.ok) {
    return { ok: false, code: 'UPSTREAM', source: 'find-case-law', status: r.status, message: 'Find Case Law returned HTTP ' + r.status + '.' };
  }
  const results = parseFclAtom(await r.text());
  return {
    ok: true, source: 'find-case-law', jurisdiction: 'uk-ew',
    source_name: 'Find Case Law (The National Archives)',
    licence: 'Open Justice Licence',
    query_url: url, results, retrieved_at: new Date().toISOString()
  };
}

module.exports = {
  COVERAGE,
  FCL_BASE, FCL_LIMIT, fclSearch, parseFclAtom,
  // checkLimit is the ATOMIC entry point; the racy path is exported too so a
  // probe can drive it directly rather than having to break the RPC to reach it.
  checkLimit, checkLimitRacy, xmlTagText
};
