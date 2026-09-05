// api/_lib/anon-rate-limit.js
// ---------------------------------------------------------------------------
// In-memory, per-instance cap on UNAUTHENTICATED licence-validation attempts.
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// On 2026-09-04 api/sd-data.js moved licence validation above its request
// envelope gate, to stop an anonymous caller enumerating all 268 registered
// resource names. That fix was right and is not in question. Its cost, raised
// by the independent review of it, is this:
//
//   before  a junk token with a garbage resource was refused LOCALLY, for free
//   after   every junk token costs one license_keys SELECT before anything else
//
// A previously-free anonymous path became a database-amplification path, with
// no limiter anywhere in the file.
//
// ── WHY THIS IS NOT api/_lib/ai-rate-limit.js's SHAPE, DELIBERATELY ────────
// That module is the platform's other limiter and it is Supabase-backed: one
// RPC per call. Putting it in front of this path would make every junk-token
// request cost TWO database round trips instead of one. It would make the
// exact problem it was brought in to solve measurably worse.
//
// That module's header calls in-memory counting unreliable, and it is right --
// for ITS job, which is a per-customer daily cost cap where an undercount is
// money. This job is different: blunt an anonymous flood before it reaches the
// database, at zero database cost. Approximate and free is the correct trade
// here, and exact-and-expensive is the wrong one. The conventions worth
// copying from it -- env-configurable, fails open, states its own limits in
// its header rather than in a row somebody has to find -- are copied.
//
// ── IT CAN NEVER REFUSE A WORKING CUSTOMER ─────────────────────────────────
// Only a FAILED licence validation is recorded. A caller holding a valid key
// never accumulates a count, so no amount of legitimate traffic can trip this,
// from any address, at any volume. That is why it enforces by default where
// ai-rate-limit.js observes by default: a refusal here can only ever land on a
// request that was already going to be refused, one HTTP status earlier.
//
// An INACTIVE licence (403) and an upstream failure (502) are NOT recorded
// either. Both mean a real key was presented, or that the database, not the
// caller, is the problem.
//
// ── WHAT IT DOES NOT DO, STATED HERE RATHER THAN DISCOVERED LATER ──────────
//  * PER-INSTANCE. Vercel runs many instances; each keeps its own map, and a
//    cold start resets it. A flood spread across instances is capped per
//    instance, not globally.
//  * THE ADDRESS IS NOT PROOF. `x-vercel-forwarded-for` is set by the platform
//    and is the value trusted first here, but a caller who can vary the
//    address it presents can rotate past this.
//  * SO THE WORST CASE IS TODAY'S BEHAVIOUR. Every degradation ends in
//    "allowed", never in a refused real request. It reduces the amplification
//    factor of the ordinary case; it is not a defence against a determined
//    distributed attacker, and must not be described as one.
//
// Env:
//   SAIRN_ANON_RATE_LIMIT_MODE=observe   count and report, never refuse
//   SAIRN_ANON_INVALID_LIMIT=20          failures per window before refusing
//   SAIRN_ANON_WINDOW_SECONDS=60         window length
// ---------------------------------------------------------------------------

const DEFAULT_LIMIT = 20;
const DEFAULT_WINDOW_SECONDS = 60;

// Bound on distinct addresses held at once. Reached only under a spread flood;
// past it the oldest-expiring entries go first. A limiter that can be made to
// exhaust an instance's memory is a denial of service wearing a fix's clothes.
const MAX_TRACKED = 5000;

const buckets = new Map();   // address -> { count, resetAt }

function limit() {
  const raw = Number(process.env.SAIRN_ANON_INVALID_LIMIT);
  return Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_LIMIT;
}

function windowMs() {
  const raw = Number(process.env.SAIRN_ANON_WINDOW_SECONDS);
  return (Number.isFinite(raw) && raw > 0 ? raw : DEFAULT_WINDOW_SECONDS) * 1000;
}

function isEnforcing() {
  return String(process.env.SAIRN_ANON_RATE_LIMIT_MODE || '').toLowerCase() !== 'observe';
}

// Vercel sets x-vercel-forwarded-for itself, so it is preferred over the
// x-forwarded-for chain a caller can prepend to. FIRST entry of that chain is
// the conventional client position when it is used at all.
function clientAddress(req) {
  const h = (req && req.headers) || {};
  const direct = h['x-vercel-forwarded-for'] || h['x-real-ip'];
  if (direct) return String(direct).trim();
  const chain = h['x-forwarded-for'];
  if (chain) return String(chain).split(',')[0].trim();
  return '';                                  // unknown: never tracked, always allowed
}

function prune(now) {
  for (const [addr, b] of buckets) {
    if (b.resetAt <= now) buckets.delete(addr);
  }
  if (buckets.size <= MAX_TRACKED) return;
  // Still over after dropping the expired: shed the entries closest to expiry.
  const byExpiry = [...buckets.entries()].sort((a, b) => a[1].resetAt - b[1].resetAt);
  for (let i = 0; i < byExpiry.length && buckets.size > MAX_TRACKED; i++) {
    buckets.delete(byExpiry[i][0]);
  }
}

// Has this address already failed licence validation too many times?
// Returns { refuse, count, limit, address, enforcing }. `refuse` is false in
// observe mode however high the count, so a deployment can measure first.
function checkAnonRate(req, now) {
  now = typeof now === 'number' ? now : Date.now();
  const address = clientAddress(req);
  if (!address) return { refuse: false, count: 0, limit: limit(), address: '', enforcing: isEnforcing() };
  const b = buckets.get(address);
  if (!b || b.resetAt <= now) return { refuse: false, count: 0, limit: limit(), address, enforcing: isEnforcing() };
  const over = b.count >= limit();
  return { refuse: over && isEnforcing(), count: b.count, limit: limit(), address, enforcing: isEnforcing(), over };
}

// Call ONLY when a licence was presented and found invalid. Not on a missing
// bearer (no database call was made), not on an inactive licence (a real key),
// not on an upstream error (the database's problem, not the caller's).
function recordInvalidLicence(req, now) {
  now = typeof now === 'number' ? now : Date.now();
  const address = clientAddress(req);
  if (!address) return 0;
  const b = buckets.get(address);
  let count;
  if (!b || b.resetAt <= now) {
    buckets.set(address, { count: 1, resetAt: now + windowMs() });
    count = 1;
  } else {
    b.count += 1;
    count = b.count;
  }
  // AFTER the insert, not before: pruning first leaves room for one more and
  // the map settles at MAX_TRACKED + 1. Caught by its own probe, which asserted
  // the ceiling rather than trusting the call order.
  prune(now);
  return count;
}

// Tests only. The map is module state and would otherwise leak between cases.
function _reset() {
  buckets.clear();
}

module.exports = {
  checkAnonRate,
  recordInvalidLicence,
  clientAddress,
  isEnforcing,
  limit,
  windowMs,
  _reset,
  _buckets: buckets,
};
