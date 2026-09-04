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

// ── A DEAD STORE MUST NOT LOOK LIKE AN UNKNOWN PRACTICE (2026-09-03) ───────
// `if (!r.ok) return null;` collapsed a Supabase failure into "no such slug",
// and every caller renders null as a 404 "Booking link not found". So with a
// revoked service_role key, an unreachable database or a missing GRANT, a
// patient following a perfectly good booking link was told the link does not
// exist -- no error, no 502, no log line, on the one surface reached without
// signing in. Found while verifying the key rotation, where this was the only
// endpoint that would NOT have revealed a dead key.
//
// It THROWS rather than returning a sentinel, deliberately: all four consumers
// already wrap their handler in try/catch and answer 502 with a logged
// message, so throwing gives the right answer at every call site without
// changing any of them, and a future consumer that forgets to check a sentinel
// cannot reintroduce the 404.
async function resolveSlug(slug) {
  if (!slug) return null;
  const r = await fetch(rest('dnt_settings?booking_slug=eq.' + encodeURIComponent(slug) + '&select=license_hash&limit=1'), { headers: supabaseHeaders() });
  if (!r.ok) {
    const e = new Error('dnt_settings slug lookup failed: HTTP ' + r.status);
    e.code = 'UPSTREAM';
    throw e;
  }
  const rows = await r.json();
  // A genuine miss still returns null, and still means 404. Only the
  // could-not-ask case changed.
  return (Array.isArray(rows) && rows[0] && rows[0].license_hash) || null;
}

// windowMinutes: fixed-window size. maxCount: allowed requests per window
// per ip_hash.
//
// Returns one of THREE states, not two:
//   { allowed: true,  count }                 -- under the limit, and counted
//   { allowed: false, count, limited: true }  -- genuinely over the limit
//   { allowed: false, unavailable: true }     -- the counter could not be read
//                                                or could not be written
//
// ── WHY THREE AND NOT TWO (2026-09-03) ────────────────────────────────────
// This used to fail OPEN in two separate places, both silently:
//
//   1. `existing.ok ? await existing.json() : []` -- an unreachable store read
//      as count 0, so every request was allowed and none was ever refused.
//   2. The increment was `await fetch(...)` with NO `.ok` CHECK AT ALL. If the
//      write failed the counter never rose, so the read kept returning 0 and
//      the limit could never engage again for that window.
//
// Together those meant the limiter guarding 5 booking attempts and 5 complaint
// submissions per hour could be entirely absent while reporting nothing. On a
// patient-facing write endpoint that is an open door, not a degraded feature.
//
// FAILING CLOSED HERE COSTS ALMOST NOTHING, which is why it is the right
// answer: resolveSlug() hits the same database a few lines later and now
// throws, so a request that would be refused here was going to 502 anyway.
//
// AND IT IS A SEPARATE STATE RATHER THAN A 429. Telling a patient "too many
// requests" when the real cause is an unreachable database is a wrong reason
// given confidently -- the same class of thing as a fabricated number. The
// callers answer 503.
async function checkAndIncrementRateLimit(req, windowMinutes, maxCount, bucket) {
  const ipHash = hashIp(clientIp(req) + (bucket ? '|' + bucket : ''));
  const windowMs = windowMinutes * 60 * 1000;
  const windowStart = new Date(Math.floor(Date.now() / windowMs) * windowMs).toISOString();
  const headers = supabaseHeaders();

  let existing;
  try {
    existing = await fetch(rest('dnt_booking_rate_limits?ip_hash=eq.' + encodeURIComponent(ipHash) + '&window_start=eq.' + encodeURIComponent(windowStart) + '&select=count'), { headers });
  } catch (err) {
    console.error('dental rate limit: counter unreachable on read:', err && err.message);
    return { allowed: false, unavailable: true };
  }
  if (!existing.ok) {
    console.error('dental rate limit: counter read failed, HTTP', existing.status);
    return { allowed: false, unavailable: true };
  }
  const existingRows = await existing.json().catch(function () { return null; });
  if (!Array.isArray(existingRows)) {
    console.error('dental rate limit: counter read returned a non-array');
    return { allowed: false, unavailable: true };
  }
  const currentCount = (existingRows[0] && existingRows[0].count) || 0;

  if (currentCount >= maxCount) {
    return { allowed: false, count: currentCount, limited: true };
  }

  let wrote;
  try {
    wrote = await fetch(rest('dnt_booking_rate_limits?on_conflict=ip_hash,window_start'), {
      method: 'POST',
      headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates' }),
      body: JSON.stringify({ ip_hash: ipHash, window_start: windowStart, count: currentCount + 1 })
    });
  } catch (err) {
    console.error('dental rate limit: counter unreachable on increment:', err && err.message);
    return { allowed: false, unavailable: true };
  }
  // An increment that did not land means THIS request was never counted.
  // Allowing it would let the limit stay disengaged for as long as the write
  // keeps failing, which is exactly the state defect 2 above created.
  if (!wrote.ok) {
    console.error('dental rate limit: counter increment failed, HTTP', wrote.status);
    return { allowed: false, unavailable: true };
  }

  return { allowed: true, count: currentCount + 1 };
}

// ── A FAILED READ IS NOT AN EMPTY TABLE (2026-09-03) ──────────────────────
// The public booking endpoints did `const rows = r.ok ? await r.json() : []`
// nine times between them. Every one of those turns "we could not ask" into
// "the answer is none", and on a calendar that fabricates in BOTH directions:
//
//   * the provider-hours read failing shows a practice as fully booked, and
//   * the appointments read failing shows every slot as free.
//
// Neither says anything to anyone. THIS HAS ALREADY HAPPENED ONCE IN
// PRODUCTION: public-availability.js still carries the comment recording that
// a query filtering on a column that does not exist "failed the query silently
// (hoursRes.ok was false, defaulted to []), which made every availability
// request return zero slots regardless of real provider hours -- found live
// during the end-to-end booking test." The malformed query was fixed. The
// fail-open that hid it was left in place.
//
// Throws for the same reason resolveSlug() does: every consumer already
// catches and answers a logged 502, so there is no sentinel for a future
// caller to forget.
async function readRows(r, what) {
  if (!r.ok) {
    const e = new Error('dental public read failed (' + what + '): HTTP ' + r.status);
    e.code = 'UPSTREAM';
    throw e;
  }
  const rows = await r.json().catch(function () { return null; });
  if (!Array.isArray(rows)) {
    const e = new Error('dental public read returned a non-array (' + what + ')');
    e.code = 'UPSTREAM';
    throw e;
  }
  // A genuinely empty table is still []. Only the could-not-ask case changed.
  return rows;
}

module.exports = { resolveSlug, checkAndIncrementRateLimit, readRows, hashIp, clientIp };
