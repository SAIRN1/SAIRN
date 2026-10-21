// api/route-map.js
// ---------------------------------------------------------------------------
// A STATIC MAP IMAGE OF ONE DAY'S STOPS, FOR STONEDESK'S FIELD MAP (b33, hank).
//
// CONCEPT: the map image is drawn by Google on the SERVER, so the Maps key
// never reaches the page; the page gets a picture, and gets it only for a
// signed-in employee of a licence that is allowed to ask.
//
// WHY A NEW ENDPOINT. Michael's call (b33): the Field Map shows BOTH the
// directions link (b27, keyless, client-side) AND an image, as an option. A
// Static Maps URL must carry the key, so building it in the page would publish
// the key to every visitor -- the reason b27 shipped the link alone. The shared
// routing primitive (rt_routes in api/sd-data.js) returns an ORDER, never an
// image, and that file is under another session's claim; this is a separate,
// narrow endpoint instead.
//
// THE GATE, IN ORDER: POST only -> bearer licence valid and active -> the
// licence's app is one that has a Field Map -> a SESSION for that app (the
// addresses are customers' addresses, so the licence alone is not enough) ->
// a bounded address list. Only then is Google asked.
//
// EVERY FAILURE IS NAMED AND NONE IS AN EMPTY IMAGE:
//   503 NO_MAPS_KEY       GOOGLE_MAPS_API_KEY is not configured -- the same
//                         variable api/_lib/routes.js reads, so one key serves both
//   502 UPSTREAM          Google answered non-200 or not an image; the key is
//                         never echoed in the message
//   504 UPSTREAM_TIMEOUT  no answer in 10 s
//   400 BAD_STOPS         empty, too many, or an address that is not a string
// SUCCESS: 200 { ok:true, image:'data:image/png;base64,...', stops:n, drawn:n }
// `drawn` can be less than `stops` only by the cap, and the page says so.
//
// GEOCODE MODE (b46): body { action:'geocode', addresses:[...] } -- same gate,
// same key -- returns coordinates instead of an image, so the optimiser's
// great-circle fallback has fixes to work with when drive times are not
// available. At most MAX_GEOCODE addresses per call (400 BAD_STOPS above it);
// 503 NO_MAPS_KEY as above. Otherwise 200 { ok:true, results, requested, located }
// with ONE result per address, in order, each either { address, lat, lng } or
// { address, error } where error is one of:
//   ZERO_RESULTS     Google found nothing for it
//   PARTIAL_MATCH    Google matched only part of it -- its guess, not a fix
//   BAD_LOCATION     an OK answer whose location is missing, out of range or 0,0
//   UPSTREAM_STATUS  Google's status was not OK (REQUEST_DENIED etc., in `status`)
//   UPSTREAM         Google answered non-200 (in `http`) or unreadable JSON
//   UPSTREAM_TIMEOUT no answer in 10 s;  NETWORK  Google could not be reached
//   BAD_ADDRESS      not a non-empty string of at most MAX_ADDRESS_LEN chars
// NO RESULT EVER CARRIES A GUESSED COORDINATE: unknown is an error, never 0,0.
// Google's error_message is never relayed (it can quote the request).
// ---------------------------------------------------------------------------
'use strict';

const { validateLicenseKey } = require('./_lib/license');
const { verifySessionToken, tokenFromRequest } = require('./_lib/auth');

const APPS_WITH_FIELD_MAP = ['stonedesk'];
const MAX_STOPS = 12;
const MAX_ADDRESS_LEN = 200;
const MAX_IMAGE_BYTES = 1024 * 1024;
const UPSTREAM_TIMEOUT_MS = 10000;
const STATIC_MAP_URL = 'https://maps.googleapis.com/maps/api/staticmap';
const GEOCODE_URL = 'https://maps.googleapis.com/maps/api/geocode/json';
const MAX_GEOCODE = 25;

// Labels are one character in the Static Maps API; 1-9 then A-C covers MAX_STOPS.
const LABELS = '123456789ABC';

function buildUrl(addresses, key) {
  const parts = ['size=640x360', 'scale=2', 'maptype=roadmap'];
  addresses.forEach(function (a, i) {
    parts.push('markers=' + encodeURIComponent('label:' + LABELS[i] + '|' + a));
  });
  if (addresses.length > 1) {
    parts.push('path=' + encodeURIComponent('weight:4|' + addresses.join('|')));
  }
  parts.push('key=' + encodeURIComponent(key));
  return STATIC_MAP_URL + '?' + parts.join('&');
}

// A coordinate is a finite number inside its range; anything else is not a fix.
function isCoord(v, lim) { return typeof v === 'number' && isFinite(v) && v >= -lim && v <= lim; }

// One address -> one named outcome; a coordinate only from an exact, in-range, non-0,0 OK answer.
async function geocodeOne(address, key) {
  if (typeof address !== 'string' || !address.trim() || address.length > MAX_ADDRESS_LEN) {
    return { address: address, error: 'BAD_ADDRESS' };
  }
  address = address.trim();
  const ctrl = typeof AbortController === 'function' ? new AbortController() : null;
  const timer = ctrl ? setTimeout(function () { ctrl.abort(); }, UPSTREAM_TIMEOUT_MS) : null;
  let up, j;
  try {
    up = await fetch(GEOCODE_URL + '?address=' + encodeURIComponent(address) + '&key=' + encodeURIComponent(key),
      ctrl ? { signal: ctrl.signal } : {});
  } catch (e) {
    if (timer) clearTimeout(timer);
    return { address: address, error: e && e.name === 'AbortError' ? 'UPSTREAM_TIMEOUT' : 'NETWORK' };
  }
  if (timer) clearTimeout(timer);
  if (!up.ok) {
    console.error('route-map geocode: upstream answered', up.status);
    return { address: address, error: 'UPSTREAM', http: up.status };
  }
  try { j = await up.json(); } catch (e) { return { address: address, error: 'UPSTREAM', http: up.status }; }
  if (!j || j.status === 'ZERO_RESULTS') return { address: address, error: 'ZERO_RESULTS' };
  if (j.status !== 'OK') {
    console.error('route-map geocode: upstream status', j.status);
    return { address: address, error: 'UPSTREAM_STATUS', status: String(j.status || 'NO_STATUS') };
  }
  const top = Array.isArray(j.results) ? j.results[0] : null;
  if (top && top.partial_match) return { address: address, error: 'PARTIAL_MATCH' };
  const loc = top && top.geometry && top.geometry.location;
  const lat = loc && loc.lat, lng = loc && loc.lng;
  if (!isCoord(lat, 90) || !isCoord(lng, 180)) return { address: address, error: 'BAD_LOCATION' };
  if (lat === 0 && lng === 0) return { address: address, error: 'BAD_LOCATION' };
  return { address: address, lat: lat, lng: lng };
}

// Geocode mode: a bounded list in, one named result per address out, never a partial silent drop.
async function geocodeAll(res, raw) {
  if (!Array.isArray(raw) || !raw.length || raw.length > MAX_GEOCODE) {
    res.status(400).json({ error: { code: 'BAD_STOPS',
      message: 'addresses must be an array of 1 to ' + MAX_GEOCODE + ' entries' } });
    return;
  }
  const key = process.env.GOOGLE_MAPS_API_KEY;
  if (!key) {
    res.status(503).json({ error: { code: 'NO_MAPS_KEY',
      message: 'No map key is configured on the server, so no address can be located.' } });
    return;
  }
  const results = await Promise.all(raw.map(function (a) { return geocodeOne(a, key); }));
  res.status(200).json({ ok: true, results: results, requested: raw.length,
    located: results.filter(function (r) { return r.lat !== undefined; }).length });
}

async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }
  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;
  if (!licenseKey) {
    res.status(401).json({ error: { code: 'NO_LICENSE', message: 'Missing bearer license key' } });
    return;
  }
  let lic;
  try {
    lic = await validateLicenseKey(licenseKey);
  } catch (err) {
    if (err && err.code === 'CONFIG') {
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
    return;
  }
  if (!lic.valid) { res.status(401).json({ error: { code: 'INVALID_LICENSE', message: 'Unknown license key' } }); return; }
  if (!lic.active) { res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: 'This license is not active' } }); return; }
  const app = APPS_WITH_FIELD_MAP.indexOf(lic.app_id) !== -1 ? lic.app_id : null;
  if (!app) {
    res.status(403).json({ error: { code: 'FORBIDDEN', message: 'This licence has no Field Map' } });
    return;
  }
  const session = verifySessionToken(tokenFromRequest(req), lic.license_hash, app);
  if (!session) {
    res.status(401).json({ error: { code: 'NO_SESSION', message: 'Sign in first' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = null; }
  }
  // Geocode mode shares the whole gate above and branches only after it.
  if (body && body.action === 'geocode') { await geocodeAll(res, body.addresses); return; }
  const raw = body && Array.isArray(body.addresses) ? body.addresses : null;
  if (!raw || !raw.length) {
    res.status(400).json({ error: { code: 'BAD_STOPS', message: 'addresses must be a non-empty array' } });
    return;
  }
  if (raw.some(function (a) { return typeof a !== 'string' || !a.trim() || a.length > MAX_ADDRESS_LEN; })) {
    res.status(400).json({ error: { code: 'BAD_STOPS',
      message: 'every address must be a non-empty string of at most ' + MAX_ADDRESS_LEN + ' characters' } });
    return;
  }
  const addresses = raw.slice(0, MAX_STOPS).map(function (a) { return a.trim(); });

  const key = process.env.GOOGLE_MAPS_API_KEY;
  if (!key) {
    res.status(503).json({ error: { code: 'NO_MAPS_KEY',
      message: 'No map key is configured on the server, so no image can be drawn. The directions link still works.' } });
    return;
  }

  const ctrl = typeof AbortController === 'function' ? new AbortController() : null;
  const timer = ctrl ? setTimeout(function () { ctrl.abort(); }, UPSTREAM_TIMEOUT_MS) : null;
  let up;
  try {
    up = await fetch(buildUrl(addresses, key), ctrl ? { signal: ctrl.signal } : {});
  } catch (e) {
    if (timer) clearTimeout(timer);
    const aborted = e && e.name === 'AbortError';
    res.status(aborted ? 504 : 502).json({ error: { code: aborted ? 'UPSTREAM_TIMEOUT' : 'UPSTREAM',
      message: aborted ? 'The map service did not answer in time.' : 'The map service could not be reached.' } });
    return;
  }
  if (timer) clearTimeout(timer);
  const type = (up.headers && up.headers.get && up.headers.get('content-type')) || '';
  if (!up.ok || type.indexOf('image/') !== 0) {
    // The upstream body can quote the request URL, which carries the key, so
    // it is logged as a status only and never relayed.
    console.error('route-map: upstream answered', up.status, type);
    res.status(502).json({ error: { code: 'UPSTREAM',
      message: 'The map service refused the request (HTTP ' + up.status + ').' } });
    return;
  }
  const bytes = Buffer.from(await up.arrayBuffer());
  if (bytes.length > MAX_IMAGE_BYTES) {
    res.status(502).json({ error: { code: 'UPSTREAM', message: 'The map image was larger than expected.' } });
    return;
  }
  res.status(200).json({ ok: true, image: 'data:' + type.split(';')[0] + ';base64,' + bytes.toString('base64'),
    stops: raw.length, drawn: addresses.length });
}

module.exports = handler;
module.exports.buildUrl = buildUrl;
module.exports.MAX_STOPS = MAX_STOPS;
module.exports.MAX_GEOCODE = MAX_GEOCODE;
