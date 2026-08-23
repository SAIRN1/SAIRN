// api/_lib/wex.js
// ---------------------------------------------------------------------------
// Grounded legal-term lookup against Cornell LII's Wex.
//
// WHY WEX, AND WHY NOT THE ALTERNATIVES (decided before building, not after):
//   * Black's Law Dictionary is commercial with no free API -- licensing
//     problem, not a build problem.
//   * Bouvier's Law Dictionary is public domain but dates from 1856, which
//     makes it actively wrong for modern and statutory terms.
//   * Wex is Cornell LII's free, maintained legal dictionary/encyclopedia.
//
// ACCESS BASIS, verified live before any code was written rather than
// assumed: Wex has NO official public API, so this reads the public term
// pages. law.cornell.edu/robots.txt was checked directly -- it does NOT
// disallow /wex (only Drupal infrastructure paths and /search/), and it sets
// `Crawl-delay: 10` for all user-agents. That crawl-delay is honoured by the
// real, Supabase-backed limiter below rather than ignored, and every request
// sends an identifying User-Agent.
//
// This is deliberately an ON-DEMAND single-term lookup. It never crawls,
// never walks the term index, and never bulk-downloads. Contrast with BAILII
// and AustLII, which were researched at the same time and are NOT used
// anywhere in SAIRNlaw because their own terms prohibit exactly this class of
// automated/AI access -- see api/_lib/intl-caselaw.js for that finding.
//
// GROUNDING CONTRACT: this returns the real retrieved text and the real
// source URL, or it returns notFound/error. It never composes a definition,
// and callers must never fall back to model memory when it fails -- that is
// the whole point of the module.
// ---------------------------------------------------------------------------

const { sbClient } = require('./courtlistener');

const WEX_BASE = 'https://www.law.cornell.edu/wex/';
// Straight from law.cornell.edu/robots.txt (`Crawl-delay: 10`).
const WEX_CRAWL_DELAY_SECONDS = 10;
const WEX_USER_AGENT = 'SAIRNlaw/1.0 (legal research tool; contact michael@sairn.com)';

// Wex slugs are lowercase with underscores. Anything outside that shape is
// rejected rather than guessed at, so a malformed term can never be turned
// into a request for some other page.
function toWexSlug(term) {
  const slug = String(term || '')
    .trim()
    .toLowerCase()
    .replace(/[‘’']/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
  return slug;
}

// Honours the published crawl-delay across the whole deployment. Cannot be an
// in-memory timer: these are stateless serverless functions and every SAIRNlaw
// firm shares this egress, so an in-process cooldown would be wrong the moment
// two instances are warm. Same reasoning and same table pattern as the
// CourtListener limiter.
async function checkWexCrawlDelay() {
  const { headers, rest } = sbClient();
  const since = new Date(Date.now() - WEX_CRAWL_DELAY_SECONDS * 1000).toISOString();
  const r = await fetch(
    rest('wex_rate_limit_log?requested_at=gte.' + encodeURIComponent(since) + '&select=id'),
    { headers }
  );
  // A missing table (PostgREST answers 404/400) must NOT be reported as a
  // generic upstream failure -- that reads as "the network is flaky" when the
  // real answer is "a migration has not been run", which is actionable. It
  // still fails CLOSED: without the ledger the crawl-delay cannot be
  // enforced, and a limit that exists to be respected must not be skipped
  // just because its bookkeeping is missing.
  if (r.status === 404 || r.status === 400) {
    return {
      delayed: true, notProvisioned: true,
      message: 'The Wex crawl-delay ledger is not set up yet — run ' +
        'sql/sairnlaw_wex_intl_schema.sql in Supabase. Lookups are refused ' +
        'until then rather than proceeding without honouring Cornell LII’s ' +
        'published Crawl-delay.'
    };
  }
  if (!r.ok) throw new Error('wex crawl-delay check failed: HTTP ' + r.status);
  const rows = await r.json();
  if (Array.isArray(rows) && rows.length > 0) {
    return { delayed: true, retryAfterSeconds: WEX_CRAWL_DELAY_SECONDS };
  }
  await fetch(rest('wex_rate_limit_log'), {
    method: 'POST',
    headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
    body: JSON.stringify({})
  });
  return { delayed: false };
}

function decodeEntities(s) {
  return String(s)
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#0?39;|&apos;|&#x27;/g, "'")
    .replace(/&#8217;|&rsquo;/g, '’')
    .replace(/&#8216;|&lsquo;/g, '‘')
    .replace(/&#8220;|&ldquo;/g, '“')
    .replace(/&#8221;|&rdquo;/g, '”')
    .replace(/&#8212;|&mdash;/g, '—')
    .replace(/&#8211;|&ndash;/g, '–');
}

// Exact-match page furniture that Cornell renders as bare <p> elements in
// the taxonomy block after a Wex definition. Deliberately a closed list of
// exact strings, not a pattern -- see the note at its use below.
const WEX_PAGE_FURNITURE = new Set(['Keywords', 'Wex', 'Wex Definitions', 'wex', 'Wex Articles']);

// Pulls the definition paragraphs that follow the page title. Deliberately
// conservative: it takes the <p> run immediately after the <h1>, and if the
// page shape ever changes it returns nothing rather than returning whatever
// text happened to be nearby. An empty result is reported honestly upstream.
function parseWexPage(html) {
  const titleMatch = html.match(/<h1[^>]*id="page-title"[^>]*>([\s\S]*?)<\/h1>/i);
  const title = titleMatch ? decodeEntities(titleMatch[1].replace(/<[^>]+>/g, '')).trim() : '';
  if (!titleMatch) return { title: '', paragraphs: [], crossReferences: [] };

  const after = html.slice(titleMatch.index + titleMatch[0].length);
  // Stop at the first structural break after the definition body.
  const stop = after.search(/<(?:h2|div class="[^"]*(?:footer|sidebar|related)|footer|nav)\b/i);
  const region = stop === -1 ? after.slice(0, 20000) : after.slice(0, stop);

  const paragraphs = [];
  const crossReferences = [];
  const pRe = /<p\b[^>]*>([\s\S]*?)<\/p>/gi;
  let m;
  while ((m = pRe.exec(region)) !== null) {
    const raw = m[1];
    // Record the Wex cross-links, which are real navigable related terms.
    const aRe = /<a[^>]+href="(https:\/\/www\.law\.cornell\.edu\/wex\/[^"#?]+)"[^>]*>([\s\S]*?)<\/a>/gi;
    let a;
    while ((a = aRe.exec(raw)) !== null) {
      const label = decodeEntities(a[2].replace(/<[^>]+>/g, '')).trim();
      if (label && !crossReferences.some((c) => c.term === label)) {
        crossReferences.push({ term: label, url: a[1] });
      }
    }
    const text = decodeEntities(raw.replace(/<[^>]+>/g, '')).replace(/\s+/g, ' ').trim();
    // Drop page furniture. The <p> run after the title sometimes ends with
    // the taxonomy block Cornell renders as bare paragraphs -- "Keywords",
    // then "Wex" and its category names. Those ARE on the page, so this is
    // not a fabrication question; the problem is that every paragraph this
    // parser returns is presented to a lawyer as definition text, and a
    // one-word nav label shown in that position reads as though the source
    // said it. Matched exactly and case-sensitively against a short closed
    // list rather than by length or position: a heuristic like "drop short
    // trailing paragraphs" would eventually eat a genuinely terse
    // definition, which is the failure that actually costs something.
    if (text && !WEX_PAGE_FURNITURE.has(text)) paragraphs.push(text);
  }
  return { title, paragraphs, crossReferences };
}

// Returns one of:
//   { ok:true,  term, definition, paragraphs, crossReferences, source_url, retrieved_at }
//   { ok:false, code:'NOT_FOUND'|'RATE_LIMITED'|'EMPTY'|'UPSTREAM', ... }
// There is no success shape that lacks a real source_url, by design.
async function wexLookup(term) {
  const slug = toWexSlug(term);
  if (!slug) return { ok: false, code: 'BAD_TERM', message: 'Enter a legal term to look up.' };

  const gate = await checkWexCrawlDelay();
  if (gate.notProvisioned) {
    return { ok: false, code: 'NOT_PROVISIONED', message: gate.message };
  }
  if (gate.delayed) {
    return {
      ok: false,
      code: 'RATE_LIMITED',
      retryAfterSeconds: gate.retryAfterSeconds,
      message: 'Cornell LII asks for ' + WEX_CRAWL_DELAY_SECONDS +
        ' seconds between automated requests, and this tool honours that. Try again shortly.'
    };
  }

  const url = WEX_BASE + encodeURIComponent(slug);
  let r;
  try {
    r = await fetch(url, { headers: { 'User-Agent': WEX_USER_AGENT, Accept: 'text/html' } });
  } catch (e) {
    return { ok: false, code: 'UPSTREAM', message: 'Could not reach Cornell LII just now.' };
  }

  if (r.status === 404) {
    return {
      ok: false, code: 'NOT_FOUND', slug, source_url: url,
      message: 'Wex has no entry at this exact term. It may be spelled differently there, ' +
        'or may not be covered. No definition is shown rather than one being composed.'
    };
  }
  if (!r.ok) {
    return { ok: false, code: 'UPSTREAM', status: r.status, message: 'Cornell LII returned HTTP ' + r.status + '.' };
  }

  const html = await r.text();
  const parsed = parseWexPage(html);
  if (!parsed.paragraphs.length) {
    return {
      ok: false, code: 'EMPTY', slug, source_url: url,
      message: 'The Wex page was reached but no definition text could be read from it. ' +
        'Open the source directly rather than relying on this tool for this term.'
    };
  }

  return {
    ok: true,
    term: parsed.title || slug.replace(/_/g, ' '),
    definition: parsed.paragraphs[0],
    paragraphs: parsed.paragraphs,
    crossReferences: parsed.crossReferences.slice(0, 12),
    source_url: url,
    source_name: 'Cornell Law School, Legal Information Institute (Wex)',
    retrieved_at: new Date().toISOString()
  };
}

module.exports = {
  WEX_BASE, WEX_CRAWL_DELAY_SECONDS, WEX_USER_AGENT,
  toWexSlug, parseWexPage, wexLookup, checkWexCrawlDelay
};
