// api/_lib/dental-public.js
// Shared helpers for SAIRNdental's two genuinely public, unauthenticated
// endpoints (public-availability.js, public-book.js) -- NOT routed by
// Vercel (leading underscore), same convention as every other api/_lib file.
//
// resolveSlug(): looks up a practice's license_hash by its public
// booking_slug -- never the license key itself. A slug is a real, indexed
// column on dnt_settings (sql/sairndental_availability_booking_schema.sql),
// not a jsonb-buried value, so this is a fast, real lookup, not a scan.
//
// checkAndIncrementRateLimit(): real, persistent, Supabase-backed rate
// limiting -- the first on this platform (confirmed before writing this;
// every prior "rate limit" mention elsewhere in this codebase was a
// documented gap, not an implementation). HONEST LIMITATION: the counter
// increment itself is read-then-write, not a single atomic SQL statement
// (PostgREST's upsert can't express "count = count + 1" directly without a
// stored procedure, which this pass doesn't add). Under a very tight
// concurrent burst, this can undercount by a request or two within the
// same window -- acceptable for abuse deterrence on a booking form (self-
// correcting every new window), a fundamentally smaller gap than the
// in-memory demo_limit counter's "doesn't work at all across serverless
// invocations" problem. Not acceptable to reuse this same approximate
// pattern anywhere a hard security/financial boundary is needed.

const crypto = require('crypto');

function hashIp(ip) {
  const salt = process.env.DENTAL_RATE_LIMIT_SALT || 'sairndental-fallback-salt';
  return crypto.createHash('sha256').update(String(ip || 'unknown') + salt).digest('hex');
}

function clientIp(req) {
  const fwd = req.headers['x-forwarded-for'];
  if (fwd) return String(fwd).split(',')[0].trim();
  return req.socket && req.socket.remoteAddress || 'unknown';
}

function supabaseHeaders() {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}

async function resolveSlug(slug) {
  if (!slug) return null;
  const r = await fetch(rest('dnt_settings?booking_slug=eq.' + encodeURIComponent(slug) + '&select=license_hash&limit=1'), { headers: supabaseHeaders() });
  if (!r.ok) return null;
  const rows = await r.json();
  return (Array.isArray(rows) && rows[0] && rows[0].license_hash) || null;
}

// windowMinutes: fixed-window size. maxCount: allowed requests per window
// per ip_hash. Returns {allowed: boolean, count: number}.
async function checkAndIncrementRateLimit(req, windowMinutes, maxCount, bucket) {
  const ipHash = hashIp(clientIp(req) + (bucket ? '|' + bucket : ''));
  const windowMs = windowMinutes * 60 * 1000;
  const windowStart = new Date(Math.floor(Date.now() / windowMs) * windowMs).toISOString();
  const headers = supabaseHeaders();

  const existing = await fetch(rest('dnt_booking_rate_limits?ip_hash=eq.' + encodeURIComponent(ipHash) + '&window_start=eq.' + encodeURIComponent(windowStart) + '&select=count'), { headers });
  const existingRows = existing.ok ? await existing.json() : [];
  const currentCount = (Array.isArray(existingRows) && existingRows[0] && existingRows[0].count) || 0;

  if (currentCount >= maxCount) {
    return { allowed: false, count: currentCount };
  }

  await fetch(rest('dnt_booking_rate_limits?on_conflict=ip_hash,window_start'), {
    method: 'POST',
    headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates' }),
    body: JSON.stringify({ ip_hash: ipHash, window_start: windowStart, count: currentCount + 1 })
  });

  return { allowed: true, count: currentCount + 1 };
}

module.exports = { resolveSlug, checkAndIncrementRateLimit, hashIp, clientIp };
