// api/sd-render.js
// ---------------------------------------------------------------------------
// "Visualize on Your Kitchen" -- swaps the countertop surface in a client's kitchen photo with
// a real in-stock slab's material, via a third-party image-edit vendor. License-scoped, same
// Bearer-license auth model as api/sd-data.js.
//
// VENDOR: Stability AI's Search-and-Replace edit API
// (POST https://api.stability.ai/v2beta/stable-image/edit/search-and-replace).
// Chosen over fal.ai/Replicate's FLUX Kontext for this specific job: sdSlabs records (see
// stonedesk.html's sd_slabs module) carry material/colorName TEXT metadata, not a reference
// photo of the actual slab -- there is currently no slab-photo field anywhere in the data model
// (confirmed by reading the live slab-creation code paths before choosing a vendor, per Guardian
// Check 0e). Search-and-Replace's whole design center is exactly "find <search_prompt> in this
// image, replace it per <prompt>", driven entirely by text -- a better fit for text-only
// material data than Kontext-style models, which are strongest when given a REFERENCE IMAGE of
// the material to transfer. It's also a single synchronous REST call (no async job + polling),
// simpler than Replicate's prediction-lifecycle API. If/when slab photos get added to the data
// model, swapping to a reference-image-conditioned vendor for higher-fidelity vein/pattern
// matching is the natural Phase 2 upgrade -- flagged here, not silently assumed permanent.
//
// BILLING DECISION (2026-08-04): no usage-based passthrough, no Stripe metering, no per-shop
// invoicing -- flat subscription, generous free cap instead. RENDER_CAP = 75/month per shop.
// Picked from the requested 50-100 range: a typical small stone shop quoting roughly 10-30 real
// jobs/month, showing a client maybe 2-3 material options per sales conversation, lands around
// 20-90 renders/month for an actively-used feature -- 75 sits mid-range: generous for real sales
// use without being maximally exposed if usage runs hotter than expected for some shops. Nothing
// happens at the cap beyond a plain "renders reset next month" message (see RENDERS_CAPPED_
// MESSAGE) -- no upsell flow, per spec; that's a future decision if real usage ever approaches it.
//
// REQUIRES env:
//   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY  -- existing, already set
//   STABILITY_API_KEY                        -- NEW, NOT YET SET as of this write. Until an
//     operator adds this in Vercel (Project Settings > Environment Variables), every render
//     request fails closed with a clear 503 VENDOR_NOT_CONFIGURED -- never a fake/placeholder
//     image. This is the one real external dependency this feature needs before it's live.
// ---------------------------------------------------------------------------

const { validateLicenseKey } = require('./_lib/license');

const RENDER_CAP = 75; // renders per shop per calendar month (UTC) -- see reasoning above
const MAX_PHOTO_BYTES = 8 * 1024 * 1024; // 8MB raw photo cap -- generous for a phone photo, rejected before any vendor spend
const RENDERS_CAPPED_MESSAGE = "You've used this shop's free renders for this month — renders reset next month.";

function currentMonthUTC() {
  return new Date().toISOString().slice(0, 7); // 'YYYY-MM'
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  // ── license_key from Authorization: Bearer, same as api/sd-data.js ──
  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) {
    res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  const photoBase64 = body && body.photo_base64;
  const materialDescription = body && body.material_description;
  if (!photoBase64 || typeof photoBase64 !== 'string') {
    res.status(400).json({ error: { message: 'photo_base64 is required' } });
    return;
  }
  if (!materialDescription || typeof materialDescription !== 'string' || !materialDescription.trim()) {
    res.status(400).json({ error: { message: 'material_description is required' } });
    return;
  }
  const photoBytes = Buffer.byteLength(photoBase64, 'base64');
  if (photoBytes > MAX_PHOTO_BYTES) {
    res.status(413).json({
      error: { code: 'PHOTO_TOO_LARGE', message: 'Photo is ' + photoBytes + ' bytes; the limit is ' + MAX_PHOTO_BYTES + ' (8MB)' }
    });
    return;
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  // ── license validation (identical pattern to api/sd-data.js) ──
  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err.code === 'CONFIG') {
      console.error('sd-render config error:', err.message);
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    console.error('sd-render license validation error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) {
    res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } });
    return;
  }
  if (!lic.active) {
    res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } });
    return;
  }
  const isPaid = !!lic.stripe_subscription_id;
  if (!isPaid && lic.trial_ends_at && new Date(lic.trial_ends_at).getTime() < Date.now()) {
    res.status(402).json({ error: { code: 'TRIAL_EXPIRED', message: 'Your trial has ended. Please subscribe to continue.' } });
    return;
  }

  const licHash = lic.license_hash;
  const month = currentMonthUTC();
  const sbHeaders = { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' };
  const rest = (path) => SUPABASE_URL + '/rest/v1/' + path;
  const enc = encodeURIComponent;

  // ── CAP CHECK (before spending anything on the vendor call) ──
  let currentCount = 0;
  let usageTableProvisioned = true;
  try {
    const r = await fetch(rest(
      'sd_render_usage?license_hash=eq.' + enc(licHash) + '&month=eq.' + enc(month) + '&select=count&limit=1'
    ), { headers: sbHeaders });
    if (r.status === 404 || r.status === 400) {
      // Table doesn't exist yet -- migration not run. See sql/sd_render_usage_schema.sql.
      usageTableProvisioned = false;
    } else if (r.ok) {
      const rows = await r.json();
      currentCount = (Array.isArray(rows) && rows[0] && rows[0].count) || 0;
    }
    // A non-ok, non-400/404 response falls through with currentCount left at 0 -- see the
    // comment on the catch block just below for why that's the deliberate fail-open choice here.
  } catch (e) {
    // A usage-READ blip should not block a render the shop is entitled to; worst case on a
    // transient failure is one under-counted render, not a hard failure of the whole feature.
  }

  if (!usageTableProvisioned) {
    res.status(503).json({
      error: { code: 'NOT_PROVISIONED', message: 'Render usage tracking is not set up yet — run sql/sd_render_usage_schema.sql in Supabase first.' }
    });
    return;
  }

  if (currentCount >= RENDER_CAP) {
    // 200, not an error status -- this is an expected, normal state the frontend renders as a
    // plain message, not a failure. Per spec: no upsell flow here, just the reset-next-month note.
    res.status(200).json({ ok: false, capped: true, count: currentCount, cap: RENDER_CAP, message: RENDERS_CAPPED_MESSAGE });
    return;
  }

  // ── VENDOR CALL ──
  const STABILITY_KEY = process.env.STABILITY_API_KEY;
  if (!STABILITY_KEY) {
    res.status(503).json({
      error: { code: 'VENDOR_NOT_CONFIGURED', message: 'Image rendering is not configured yet — STABILITY_API_KEY is not set.' }
    });
    return;
  }

  let renderedBase64;
  try {
    const imgBuffer = Buffer.from(photoBase64, 'base64');
    const form = new FormData();
    form.append('image', new Blob([imgBuffer]), 'kitchen.jpg');
    form.append('search_prompt', 'the countertop surface');
    form.append('prompt', 'a photorealistic ' + materialDescription.trim() + ' stone countertop surface, matching the original photo\'s lighting, reflections, and perspective');
    form.append('output_format', 'png');

    const vendorRes = await fetch('https://api.stability.ai/v2beta/stable-image/edit/search-and-replace', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + STABILITY_KEY, Accept: 'application/json' },
      body: form
    });
    if (!vendorRes.ok) {
      const errText = await vendorRes.text().catch(() => '');
      console.error('Stability search-and-replace failed:', vendorRes.status, errText.slice(0, 300));
      res.status(502).json({ error: { code: 'VENDOR_ERROR', message: 'Image rendering failed — try again' } });
      return;
    }
    const vendorJson = await vendorRes.json();
    renderedBase64 = vendorJson.image; // Stability's application/json response shape: { image, finish_reason, seed }
    if (!renderedBase64) {
      res.status(502).json({ error: { code: 'VENDOR_ERROR', message: 'Image rendering returned no image' } });
      return;
    }
  } catch (err) {
    console.error('sd-render vendor call error:', err);
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }

  // ── INCREMENT USAGE -- only on a render that actually reached the vendor and returned an
  // image. A request refused earlier (bad auth, over cap, vendor not configured) never gets here,
  // so the counter only ever reflects real vendor spend, never attempts. Non-atomic read-then-
  // write -- see sql/sd_render_usage_schema.sql's KNOWN LIMITATION note for why that's an
  // accepted tradeoff at this feature's real volume.
  const newCount = currentCount + 1;
  try {
    await fetch(rest('sd_render_usage?on_conflict=license_hash,month'), {
      method: 'POST',
      headers: Object.assign({}, sbHeaders, { Prefer: 'resolution=merge-duplicates' }),
      body: JSON.stringify({ license_hash: licHash, month: month, count: newCount, updated_at: new Date().toISOString() })
    });
  } catch (e) {
    console.error('sd-render usage increment failed (render still returned to client):', e);
  }

  res.status(200).json({ ok: true, image_base64: renderedBase64, count: newCount, cap: RENDER_CAP });
};
