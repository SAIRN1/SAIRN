// api/_lib/stonedesk-public.js
// Shared helpers for StoneDesk's genuinely public, unauthenticated endpoints
// (api/stonedesk-public.js). NOT routed by Vercel (leading underscore), same
// convention as every other api/_lib file.
//
// Deliberately a SIBLING of api/_lib/dental-public.js rather than a
// generalisation of it. Two reasons, and the second is the real one:
//   * they read different slug columns on different tables, so the only shared
//     code would be the rate limiter and the IP hashing;
//   * dental-public.js serves a live, provisioned, in-production booking flow.
//     Refactoring it to host a second app's public surface would put a working
//     patient-booking path at risk to save roughly forty lines. The duplication
//     is the cheaper mistake, and it is a deliberate one.
//
// resolveShopSlug(): looks up a shop's license_hash by its public shop_slug --
// never the license key itself. shop_slug is a real, unique, indexed column on
// sd_public_shop, not a jsonb-buried value.
//
// PUBLISHED IS CHECKED HERE, NOT BY THE CALLER. A slug that exists but whose
// shop has not been published resolves to null, so an unpublished catalog is
// indistinguishable from a slug that was never claimed. A shop that turns
// publication off goes dark immediately rather than staying reachable to
// anyone who already knows the URL.
//
// checkAndIncrementRateLimit(): per-IP-hash fixed-window counter over
// sd_public_rate_limits. HONEST LIMITATION, carried over verbatim from
// dental-public.js because it is the same shape: the increment is read-then-
// write, not one atomic statement, so a very tight concurrent burst can
// undercount by a request or two inside a window. Acceptable for abuse
// deterrence on a public form and self-correcting every new window. NOT
// acceptable anywhere a hard security or financial boundary is needed.

const crypto = require('crypto');

function hashIp(ip) {
  // Reuses the dental salt env var if a StoneDesk-specific one is not set, so
  // this works the moment it deploys rather than silently hashing everything
  // to the same fallback constant. The salt only has to be secret and stable.
  const salt = process.env.STONEDESK_RATE_LIMIT_SALT ||
               process.env.DENTAL_RATE_LIMIT_SALT ||
               'stonedesk-fallback-salt';
  return crypto.createHash('sha256').update(String(ip || 'unknown') + salt).digest('hex');
}

function clientIp(req) {
  const fwd = req.headers['x-forwarded-for'];
  if (fwd) return String(fwd).split(',')[0].trim();
  return (req.socket && req.socket.remoteAddress) || 'unknown';
}

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({
    apikey: SERVICE_KEY,
    Authorization: 'Bearer ' + SERVICE_KEY,
    'Content-Type': 'application/json'
  }, extra || {});
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}

async function resolveShopSlug(slug) {
  if (!slug) return null;
  const r = await fetch(
    rest('sd_public_shop?shop_slug=eq.' + encodeURIComponent(slug) +
         '&published=eq.true&select=license_hash,shop_slug,data&limit=1'),
    { headers: supabaseHeaders() });
  if (!r.ok) return null;
  const rows = await r.json();
  if (!Array.isArray(rows) || !rows[0] || !rows[0].license_hash) return null;
  return { licenseHash: rows[0].license_hash, slug: rows[0].shop_slug, data: rows[0].data || {} };
}

async function checkAndIncrementRateLimit(req, windowMinutes, maxCount, bucket) {
  const ipHash = hashIp(clientIp(req) + (bucket ? '|' + bucket : ''));
  const windowMs = windowMinutes * 60 * 1000;
  const windowStart = new Date(Math.floor(Date.now() / windowMs) * windowMs).toISOString();
  const headers = supabaseHeaders();

  const existing = await fetch(
    rest('sd_public_rate_limits?ip_hash=eq.' + encodeURIComponent(ipHash) +
         '&window_start=eq.' + encodeURIComponent(windowStart) + '&select=count'),
    { headers });
  const existingRows = existing.ok ? await existing.json() : [];
  const currentCount = (Array.isArray(existingRows) && existingRows[0] && existingRows[0].count) || 0;

  if (currentCount >= maxCount) return { allowed: false, count: currentCount };

  await fetch(rest('sd_public_rate_limits?on_conflict=ip_hash,window_start'), {
    method: 'POST',
    headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates' }),
    body: JSON.stringify({ ip_hash: ipHash, window_start: windowStart, count: currentCount + 1 })
  });

  return { allowed: true, count: currentCount + 1 };
}

// ── THE PUBLIC SLAB SHAPE, BUILT BY NAMING WHAT GOES IN ────────────────────
// A slab's jsonb blob carries what the SHOP needs: vendor, supplier, cost,
// internal status, lineage. A visitor gets a whitelist, constructed field by
// field, so no future field added to the blob can leak by default. That is the
// same "no filter can fail open" construction SAIRNfreedom's district report
// used, and the reason it is a builder rather than a delete-list.
//
// PRICE IS NOT IN IT, deliberately. A slab's cost is what the shop paid, not
// what a customer pays, and publishing it would be both commercially wrong and
// factually misleading. The catalog shows what a slab IS; what it costs is a
// quote, which is what the form is for.
function publicSlabView(slab) {
  const d = slab || {};
  return {
    id: String(d.id || ''),
    material: String(d.material || ''),
    color_name: String(d.colorName || d.color_name || ''),
    usable_sqft: Number(d.usableSqft || d.usable_sqft || 0) || null,
    thickness: String(d.thickness || ''),
    finish: String(d.finish || ''),
    photo_base64: typeof d.photo_base64 === 'string' ? d.photo_base64 : ''
  };
}

// A slab reaches the public catalog only if the shop said so. Absent means no.
function isPublished(slab) {
  return !!(slab && slab.published === true);
}

// ── THE PUBLIC REMNANT SHAPE (GAP 8, 2026-09-02) ──────────────────────────
// Same builder construction as publicSlabView, for the same reason: a
// whitelist assembled field by field cannot fail open when someone adds a
// field to the blob later.
//
// THE PRICE IS PUBLISHED HERE, AND THAT IS THE OPPOSITE OF THE SLAB RULE.
// publicSlabView withholds a slab's cost, correctly -- that is what the SHOP
// PAID and publishing it would be commercially wrong and misleading about what
// a customer would be charged. A REMNANT'S `price` is the ASKING price: the
// piece is being cleared rather than quoted, and the number a visitor needs is
// the number they would pay. Stated at length because the two rules look
// contradictory side by side and "fixing the inconsistency" would delete the
// feature.
//
// `age` IS DELIBERATELY NOT PUBLISHED. The remnant record carries it as a
// STORED DAY COUNT that nothing increments. Internally it is the number
// somebody last wrote down; published, it is a fact that decays -- a piece
// shown as "12 days old" still says 12 a year later. Omitted rather than
// printed getting more wrong every day.
//
// NOR IS `location`. The yard row a piece sits in is how staff find it and is
// of no use to a visitor; publishing it maps the inside of the building to
// anyone who asks.
function publicRemnantView(remnant) {
  const d = remnant || {};
  return {
    id: String(d.id || ''),
    stone: String(d.stone || ''),
    size: String(d.size || ''),
    sqft: Number(d.sqft || 0) || null,
    price: Number(d.price || 0) || null,
    notes: String(d.notes || ''),
    photo_base64: typeof d.photo_base64 === 'string' ? d.photo_base64 : ''
  };
}

// A remnant reaches the catalog only if the shop published it AND the piece is
// still Available. A Reserved or Sold remnant with the flag left on is dropped
// -- a catalog offering a piece that is already gone is the double-sale problem
// in miniature, which is the failure the slab reservation compare-and-swap
// exists to stop. The shop's own panel says the piece is being withheld rather
// than leaving a ticked box that mysteriously produces nothing.
function isRemnantPublishable(remnant) {
  return !!(remnant && remnant.published === true &&
            String(remnant.status || '') === 'Available');
}

module.exports = {
  resolveShopSlug, checkAndIncrementRateLimit, hashIp, clientIp,
  supabaseHeaders, rest, publicSlabView, isPublished,
  publicRemnantView, isRemnantPublishable
};
