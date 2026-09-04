// api/stonedesk-public.js
// ---------------------------------------------------------------------------
// StoneDesk's genuinely public, unauthenticated surface. Competitive-gap audit
// GAP 1 (no customer-facing portal), which the audit called "structural, and
// the largest", and which iBlocky -- the market leader that audit identified --
// leads with.
//
// NO LICENSE KEY ANYWHERE IN THIS FILE, and no employee session. A visitor has
// neither. The only thing that identifies a shop is its public shop_slug, and
// api/_lib/stonedesk-public.js resolves that to a license_hash server-side and
// refuses a slug whose shop is not published.
//
// ── WHY THIS IS NOT A MODE OF stonedesk.html ──
// stonedesk.html carries SAIRN's own chart of accounts, its price book and a
// patent deadline as literal strings in the HTML. The competitive audit's §4.1
// closed the panel gate and explicitly left that residual open, noting that
// gating a panel stops UI access and does nothing about View Source. Serving
// that file to an anonymous visitor would publish all of it. The public surface
// is therefore its own file (stonedesk-catalog.html) reading its own tables,
// and the only data that can reach a visitor is data a shop deliberately put
// somewhere built for publication.
//
// ── THREE THINGS THIS ENDPOINT WILL NOT DO ──
// 1. IT WILL NOT RETURN A SLAB THE SHOP DID NOT PUBLISH. Publication is an
//    explicit per-slab flag; absent means no. And the returned shape is BUILT
//    BY NAMING ITS FIELDS (publicSlabView), so a field added to the slab blob
//    later cannot leak by default -- there is no filter here that can fail
//    open.
// 2. IT WILL NOT PUBLISH WHAT A SLAB COST. That figure is what the shop paid,
//    not what a customer pays. The catalog says what a slab IS; what it costs
//    is a quote, which is what the form is for.
// 3. IT WILL NOT WRITE INTO THE SHOP'S CRM. A quote request lands in
//    sd_quote_requests as `pending` and a member of staff promotes it. Same
//    rule and same reason as api/sairndental/public-book.js's "new bookings
//    always land as Pending -- never auto-confirmed": an anonymous,
//    unauthenticated submitter must never write straight into the record the
//    business runs on.
//
// 4. IT WILL NOT SHOW A REMNANT THAT IS ALREADY GONE (GAP 8, 2026-09-02).
//    Publication is an explicit per-remnant flag AND the piece must still be
//    Available -- a Reserved or Sold remnant with the flag left on is dropped.
//    A catalog offering a piece that has been sold is the double-sale problem
//    in miniature. The remnant PRICE, unlike a slab's cost, IS published: it is
//    the asking price a customer would pay, not what the shop paid.
//
// Actions (POST body { action }):
//   catalog        { slug }              -> shop details + published slabs
//                                           and published available remnants
//   quote_request  { slug, request }     -> creates a pending lead
// ---------------------------------------------------------------------------

const {
  resolveShopSlug, checkAndIncrementRateLimit,
  supabaseHeaders, rest, publicSlabView, isPublished,
  publicRemnantView, isRemnantPublishable
} = require('./_lib/stonedesk-public');

const MAX_TEXT = 2000;
const MAX_SHORT = 200;

function newId(prefix) {
  return prefix + '-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
}
function clean(v, max) {
  return String(v == null ? '' : v).trim().slice(0, max || MAX_SHORT);
}
// Public input is stored as given, trimmed and length-capped, and is never
// interpreted. Escaping is the renderer's job in every SAIRN app and doing it
// here as well would double-encode a name like O'Hara on the way back out.
function validateRequest(r) {
  const name = clean(r.name, MAX_SHORT);
  const phone = clean(r.phone, MAX_SHORT);
  const email = clean(r.email, MAX_SHORT);
  if (!name) return { ok: false, message: 'A name is required' };
  if (!phone && !email) return { ok: false, message: 'A phone number or an email address is required -- there is no way to answer a quote request without one' };
  const sqftRaw = r.sqft;
  const sqft = (sqftRaw === '' || sqftRaw == null) ? null : Number(sqftRaw);
  if (sqft !== null && (!isFinite(sqft) || sqft < 0)) return { ok: false, message: 'Square footage must be a number' };
  return {
    ok: true,
    value: {
      name: name, phone: phone, email: email,
      project_type: clean(r.project_type, MAX_SHORT),
      material: clean(r.material, MAX_SHORT),
      sqft: sqft,
      budget: clean(r.budget, MAX_SHORT),
      timeline: clean(r.timeline, MAX_SHORT),
      message: clean(r.message, MAX_TEXT),
      slab_id: clean(r.slab_id, MAX_SHORT),
      slab_label: clean(r.slab_label, MAX_SHORT)
    }
  };
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { res.status(400).json({ error: { message: 'Invalid JSON body' } }); return; }
  }
  body = body || {};
  const action = body.action;
  if (action !== 'catalog' && action !== 'quote_request') {
    res.status(400).json({ error: { message: "action must be 'catalog' or 'quote_request'" } });
    return;
  }

  try {
    // Rate-limit first, before any database work. Browsing is cheap and
    // generous; submitting is not, and they get separate buckets so a visitor
    // reading the catalog can never exhaust their own ability to send one
    // request.
    const rl = (action === 'catalog')
      ? await checkAndIncrementRateLimit(req, 10, 120, 'catalog')
      : await checkAndIncrementRateLimit(req, 60, 5, 'quote');
    // ORDER MATTERS AND IS TESTED. The unavailable branch must be read BEFORE
    // the generic !rl.allowed branch: an unreachable counter also reports
    // allowed:false, so checking !rl.allowed first would tell a customer they
    // had made too many requests when the real cause was an outage -- a wrong
    // reason given confidently, on the shop's public storefront. Swapping these
    // two blocks is caught by api/_lib/stonedesk-public.test.js, which compiles
    // a deliberately-swapped mutant of this file and asserts it answers 429.
    if (rl.unavailable) {
      console.error('stonedesk-public: rate-limit store unavailable, refusing rather than failing open');
      // Wording is action-NEUTRAL on purpose: this branch serves both the
      // catalog read and the quote-request write, and "the shop catalog is
      // unavailable" is the wrong sentence to show somebody who was trying to
      // send a message.
      res.status(503).json({ error: { code: 'UNAVAILABLE', message: 'This shop page is temporarily unavailable -- please try again shortly, or call the shop directly' } });
      return;
    }
    if (!rl.allowed) {
      res.status(429).json({ error: { code: 'RATE_LIMITED', message: 'Too many requests -- please try again shortly, or call the shop directly' } });
      return;
    }

    const shop = await resolveShopSlug(body.slug);
    // A slug that does not exist and a shop that has not published are the SAME
    // answer on purpose. Distinguishing them would turn this endpoint into a
    // way to enumerate which shops exist.
    if (!shop) { res.status(404).json({ error: { code: 'NOT_FOUND', message: 'No published catalog at this address' } }); return; }

    const headers = supabaseHeaders();

    if (action === 'catalog') {
      const r = await fetch(rest('sd_slabs?license_hash=eq.' + encodeURIComponent(shop.licenseHash) + '&select=data'), { headers });
      if (!r.ok) { res.status(502).json({ error: { message: 'Could not load the catalog -- try again shortly' } }); return; }
      const rows = await r.json();
      const slabs = (Array.isArray(rows) ? rows : [])
        .map((x) => x && x.data)
        .filter(isPublished)
        .map(publicSlabView);
      // ── REMNANTS (GAP 8, 2026-09-02) ────────────────────────────────────
      // A SEPARATE, NON-FATAL FETCH -- BUT ONLY FOR THE ONE FAILURE IT WAS
      // MEANT TO TOLERATE. sd_remnants is a new table and a shop that has not
      // run the migration yet must still get its slab catalog: failing the
      // whole page because the remnant table is absent would take a working
      // public catalog down to add a feature to it. PostgREST answers 404 for
      // a relation that is not in the schema cache, so that is the shape of
      // "not provisioned", and it yields an empty list.
      //
      // NARROWED 2026-09-03. `if (rr.ok)` swallowed every other status too, so
      // a revoked key, a missing GRANT or a 500 rendered the page with the
      // remnant section simply gone -- a published, for-sale inventory silently
      // absent from the storefront, with no error to the visitor and no log
      // line for the shop. That is the same defect class as the slug lookup
      // above it: an operational failure wearing the costume of an empty
      // result. The slab fetch on the line above already 502s for exactly
      // these statuses; there is no reason the remnant fetch should not.
      let remnants = [];
      const rr = await fetch(rest('sd_remnants?license_hash=eq.' + encodeURIComponent(shop.licenseHash) + '&select=data'), { headers });
      if (rr.ok) {
        const rrows = await rr.json();
        remnants = (Array.isArray(rrows) ? rrows : [])
          .map((x) => x && x.data)
          .filter(isRemnantPublishable)
          .map(publicRemnantView);
      } else if (rr.status !== 404) {
        console.error('stonedesk-public: sd_remnants read failed, HTTP', rr.status);
        res.status(502).json({ error: { message: 'Could not load the catalog -- try again shortly' } });
        return;
      }
      const d = shop.data || {};
      res.status(200).json({
        ok: true,
        shop: {
          name: String(d.shop_name || ''), phone: String(d.phone || ''),
          email: String(d.email || ''), address: String(d.address || ''),
          blurb: String(d.blurb || '')
        },
        slabs: slabs,
        count: slabs.length,
        remnants: remnants,
        remnant_count: remnants.length
      });
      return;
    }

    // quote_request
    const v = validateRequest(body.request || {});
    if (!v.ok) { res.status(400).json({ error: { code: 'INVALID', message: v.message } }); return; }

    const requestId = newId('QR');
    const payload = Object.assign({}, v.value, { submitted_at: new Date().toISOString() });
    const w = await fetch(rest('sd_quote_requests'), {
      method: 'POST',
      headers: Object.assign({}, headers, { Prefer: 'return=minimal' }),
      body: JSON.stringify({
        license_hash: shop.licenseHash, app_id: 'stonedesk',
        request_id: requestId, status: 'pending', data: payload
      })
    });
    if (w.status === 404 || w.status === 400) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'This shop is not set up to take requests yet -- please call them directly' } });
      return;
    }
    if (!w.ok) { res.status(502).json({ error: { message: 'Could not send your request -- please try again, or call the shop' } }); return; }

    // The reference is returned so a caller has something to quote on the
    // phone. It is NOT a tracking token and grants nothing -- knowing it does
    // not let anyone read the request back, because there is no read action for
    // a quote request on this endpoint at all.
    res.status(200).json({ ok: true, reference: requestId });
  } catch (err) {
    console.error('stonedesk-public error:', err);
    res.status(502).json({ error: { message: 'Something went wrong -- please try again, or call the shop directly' } });
  }
};
