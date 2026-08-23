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
//   Canada   -- CanLII's official REST API (api.canlii.org/v1) with a free
//               key. CanLII prohibits scraping; the keyed API is the
//               sanctioned route. That distinction is not academic -- CanLII
//               filed a claim in Nov 2024 against an AI legal-research
//               platform over systematic scraping of its records. Verified
//               live that the endpoint is real and returns 403 ACCESS_DENIED
//               without a valid key.
//
// GROUNDING CONTRACT, same as the CourtListener citator: every result carries
// the real source URL it came from. There is no success shape without one, and
// callers must never substitute model memory when a lookup fails.
// ---------------------------------------------------------------------------

const { sbClient } = require('./courtlistener');

// ── Jurisdiction coverage, stated as data so the UI can render it honestly ──
const COVERAGE = [
  { code: 'us', label: 'United States', covered: true, source: 'CourtListener', note: 'Federal and state opinions.' },
  { code: 'uk-ew', label: 'United Kingdom (England & Wales)', covered: true, source: 'Find Case Law (The National Archives)', note: 'Judgments and tribunal decisions from 2001 onwards, under the Open Justice Licence.' },
  { code: 'ca', label: 'Canada', covered: true, source: 'CanLII API', note: 'Official keyed API. Metadata and citator relationships; CanLII does not serve full decision text through the API.' },
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

async function checkLimit(table, seconds, max) {
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
  if (Array.isArray(rows) && rows.length >= max) return { limited: true, max, seconds };
  await fetch(rest(table), {
    method: 'POST',
    headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
    body: JSON.stringify({})
  });
  return { limited: false };
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

// ── CanLII ────────────────────────────────────────────────────────────────
const CANLII_BASE = 'https://api.canlii.org/v1';
// CanLII publishes no explicit rate limit. A conservative self-imposed ceiling
// is applied anyway rather than treating "undocumented" as "unlimited".
const CANLII_LIMIT = { seconds: 3600, max: 200 };

function canliiKey() {
  const k = process.env.CANLII_API_KEY;
  if (!k) { const e = new Error('CANLII_API_KEY not configured'); e.code = 'NOT_CONFIGURED'; throw e; }
  return k;
}

async function canliiRequest(path) {
  let key;
  try { key = canliiKey(); }
  catch (e) {
    return { ok: false, code: 'NOT_CONFIGURED', source: 'canlii',
      message: 'No CanLII API key is configured yet, so Canadian results are genuinely unavailable rather than incomplete. CanLII issues free keys on request; scraping is not an alternative, as CanLII prohibits it.' };
  }
  const gate = await checkLimit('canlii_rate_limit_log', CANLII_LIMIT.seconds, CANLII_LIMIT.max);
  if (gate.notProvisioned) {
    return { ok: false, code: 'NOT_PROVISIONED', source: 'canlii', message: gate.message };
  }
  if (gate.limited) {
    return { ok: false, code: 'RATE_LIMITED', source: 'canlii', message: 'CanLII lookups are rate limited by this tool. Try again shortly.' };
  }
  const url = CANLII_BASE + path + (path.indexOf('?') === -1 ? '?' : '&') + 'api_key=' + encodeURIComponent(key);
  let r;
  try {
    r = await fetch(url, { headers: { 'User-Agent': UA, Accept: 'application/json' } });
  } catch (e) {
    return { ok: false, code: 'UPSTREAM', source: 'canlii', message: 'Could not reach CanLII just now.' };
  }
  const text = await r.text();
  if (r.status === 403 || r.status === 401) {
    return { ok: false, code: 'BAD_KEY', source: 'canlii', message: 'CanLII rejected the configured API key (HTTP ' + r.status + ').' };
  }
  if (!r.ok) {
    return { ok: false, code: 'UPSTREAM', source: 'canlii', status: r.status, message: 'CanLII returned HTTP ' + r.status + '.' };
  }
  let data;
  try { data = JSON.parse(text); } catch (e) {
    return { ok: false, code: 'UPSTREAM', source: 'canlii', message: 'CanLII returned a response that could not be parsed.' };
  }
  // The key is in the URL; never hand it back to a caller.
  return { ok: true, source: 'canlii', data, query_url: url.replace(/api_key=[^&]*/, 'api_key=REDACTED'), retrieved_at: new Date().toISOString() };
}

function canliiBrowse(databaseId, offset, count) {
  const n = Math.min(Math.max(parseInt(count, 10) || 10, 1), 25);
  const o = Math.max(parseInt(offset, 10) || 0, 0);
  return canliiRequest('/caseBrowse/en/' + encodeURIComponent(databaseId) + '/?offset=' + o + '&resultCount=' + n);
}

// The real citator relationships CanLII exposes. metadataType is one of
// citedCases / citingCases / citedLegislations, per CanLII's own documented
// caseCitator endpoint -- rejected rather than passed through if it is
// anything else, so a caller cannot construct an arbitrary API path.
const CANLII_CITATOR_TYPES = { citedCases: true, citingCases: true, citedLegislations: true };
function canliiCitator(databaseId, caseId, metadataType) {
  if (!CANLII_CITATOR_TYPES[metadataType]) {
    return Promise.resolve({ ok: false, code: 'BAD_REQUEST', source: 'canlii',
      message: 'metadataType must be one of: ' + Object.keys(CANLII_CITATOR_TYPES).join(', ') });
  }
  return canliiRequest('/caseCitator/en/' + encodeURIComponent(databaseId) + '/' + encodeURIComponent(caseId) + '/' + metadataType);
}

module.exports = {
  COVERAGE,
  FCL_BASE, FCL_LIMIT, fclSearch, parseFclAtom,
  CANLII_BASE, CANLII_LIMIT, CANLII_CITATOR_TYPES,
  canliiRequest, canliiBrowse, canliiCitator,
  checkLimit, xmlTagText
};
