// api/b46-route-geocode.test.js
//
// Run:  node api/b46-route-geocode.test.js
//
// CONCEPT: an address becomes a coordinate only when Google returns a real,
// exact, in-range, non-0,0 fix; anything else is a named failure with no
// coordinate, and geocode mode sits behind the same licence + session gate as
// the map image. Every arm drives the real api/route-map.js handler with the
// licence store and Google stubbed.
//
// MUTATION CONTROLS: the same arms are then run against four mutated copies of
// the handler's source (compiled under the real filename so its requires
// resolve). Each mutant must be KILLED -- at least one arm fails -- or the
// arms are not testing what they claim. A mutant whose anchor is not found
// exactly once is COULD NOT RUN, never a pass.
//
// These are the b46 arms from fourth's scratchpad, committed after cc's b34
// review found none of them in the repo; S19 adds cc's foreign-licence arm.
//
// Exit: 0 all arms passed and every mutant killed - 1 an arm FAILED or a
// mutant SURVIVED - 2 COULD NOT RUN (a mutant anchor did not match once)

'use strict';
const fs = require('fs');
const path = require('path');
const Module = require('module');

// A placeholder-marked value on purpose: tools/redaction_check.py treats a
// "secret = '<16+ chars>'" literal without a placeholder marker as a credential.
process.env.SD_AUTH_SECRET = 'fake-b46-signing-value-for-this-test-only';
const KEY = 'test-maps-key-for-b46-only';

const LICENCE = require.resolve('./_lib/license');
const lic = { valid: true, active: true, app_id: 'stonedesk', license_hash: 'h-stonedesk' };
require.cache[LICENCE] = { id: LICENCE, filename: LICENCE, loaded: true,
  exports: { validateLicenseKey: async () => lic } };
const auth = require('./_lib/auth');

const API = path.join(__dirname, 'route-map.js');
const SRC = fs.readFileSync(API, 'utf8');
function compile(src) {
  const m = new Module(API, module);
  m.filename = API;
  m.paths = Module._nodeModulePaths(__dirname);
  m._compile(src, API);
  return m.exports;
}

// Google-shaped geocode answers, keyed by address.
const G = {
  '1 Good St': { status: 'OK', results: [{ geometry: { location: { lat: 40.7128, lng: -74.006 } } }] },
  '2 Good St': { status: 'OK', results: [{ geometry: { location: { lat: 40.73, lng: -73.99 } } }] },
  'Nowhere':   { status: 'ZERO_RESULTS', results: [] },
  'Denied':    { status: 'REQUEST_DENIED', results: [], error_message: 'The provided API key is invalid. key=' + KEY },
  'Island':    { status: 'OK', results: [{ geometry: { location: { lat: 0, lng: 0 } } }] },
  'Partial':   { status: 'OK', results: [{ partial_match: true, geometry: { location: { lat: 41, lng: -73 } } }] },
};
let upstream = [];
function geoFetch(url) {
  upstream.push(String(url));
  const a = decodeURIComponent((String(url).match(/address=([^&]*)/) || [])[1] || '').replace(/\+/g, ' ');
  if (a === 'Boom') return Promise.reject(new TypeError('fetch failed'));
  if (a === 'Http500') return Promise.resolve({ ok: false, status: 500, headers: { get: () => 'text/html' }, json: async () => { throw new Error('html'); } });
  const body = G[a] || { status: 'ZERO_RESULTS', results: [] };
  return Promise.resolve({ ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => body });
}
function mockRes() { const r = { code: 0, body: null }; r.status = (c) => { r.code = c; return r; }; r.json = (b) => { r.body = b; return r; }; return r; }
const TOKEN = auth.signSessionToken({ app: 'stonedesk', employee_id: 'e1', role: 'install', license_hash: 'h-stonedesk' });
const FOREIGN = auth.signSessionToken({ app: 'stonedesk', employee_id: 'e9', role: 'owner', license_hash: 'h-another-licence' });

// Runs every arm against one handler. -> [{ name, ok, detail }]
async function arms(handler) {
  const out = [];
  const check = (name, cond, detail) => out.push({ name, ok: !!cond, detail });
  const one = (r, i) => ((r.body && r.body.results) || [])[i] || {};
  async function call(addresses, token) {
    const headers = { authorization: 'Bearer SD-AUDIT-2026' };
    if (token !== null) headers['x-sd-auth'] = token || TOKEN;
    const res = mockRes(); upstream = [];
    await handler({ method: 'POST', headers, body: { action: 'geocode', addresses } }, res);
    return { code: res.code, body: res.body, upstream: upstream.slice() };
  }
  global.fetch = geoFetch;
  process.env.GOOGLE_MAPS_API_KEY = KEY;
  let r = await call(['1 Good St']);
  check('S1. OK -> 200 with lat/lng from results[0].geometry.location', r.code === 200 && one(r, 0).lat === 40.7128 && one(r, 0).lng === -74.006 && one(r, 0).address === '1 Good St', JSON.stringify(r.body));
  check('S2. the URL is the Geocoding API and carries the key server-side', r.upstream.length === 1 && r.upstream[0].indexOf('https://maps.googleapis.com/maps/api/geocode/json?') === 0 && r.upstream[0].indexOf('key=' + KEY) !== -1, r.upstream[0]);
  check('S3. the key never appears in the response', JSON.stringify(r.body).indexOf(KEY) === -1);
  r = await call(['Nowhere']);
  check('S4. ZERO_RESULTS -> named failure, no coordinate', r.code === 200 && one(r, 0).error === 'ZERO_RESULTS' && one(r, 0).lat === undefined && one(r, 0).lng === undefined, JSON.stringify(r.body));
  r = await call(['Denied']);
  check('S5. REQUEST_DENIED -> UPSTREAM_STATUS naming the status, no coordinate', one(r, 0).error === 'UPSTREAM_STATUS' && one(r, 0).status === 'REQUEST_DENIED' && one(r, 0).lat === undefined, JSON.stringify(r.body));
  check('S6. Google\'s error_message (which can quote the key) is never relayed', JSON.stringify(r.body).indexOf(KEY) === -1 && JSON.stringify(r.body).indexOf('provided API key') === -1);
  r = await call(['Http500']);
  check('S7. HTTP 500 -> UPSTREAM with the HTTP status, no coordinate', one(r, 0).error === 'UPSTREAM' && one(r, 0).http === 500 && one(r, 0).lat === undefined, JSON.stringify(r.body));
  r = await call(['Boom']);
  check('S8. network throw -> NETWORK, no coordinate', one(r, 0).error === 'NETWORK' && one(r, 0).lat === undefined, JSON.stringify(r.body));
  r = await call(['Island']);
  check('S9. an OK answer at 0,0 is NOT a coordinate (BAD_LOCATION)', one(r, 0).error === 'BAD_LOCATION' && one(r, 0).lat === undefined, JSON.stringify(r.body));
  r = await call(['Partial']);
  check('S10. partial_match is Google guessing -> PARTIAL_MATCH, no coordinate', one(r, 0).error === 'PARTIAL_MATCH' && one(r, 0).lat === undefined, JSON.stringify(r.body));
  r = await call(['1 Good St', 'Nowhere', 'Boom', '2 Good St']);
  check('S11. mixed batch: one result per address, in order, counts honest', r.code === 200 && r.body.results.length === 4 && r.body.located === 2 && r.body.requested === 4
    && one(r, 0).lat === 40.7128 && one(r, 1).error === 'ZERO_RESULTS' && one(r, 2).error === 'NETWORK' && one(r, 3).lat === 40.73, JSON.stringify(r.body));
  const many = []; for (let i = 0; i < 26; i++) many.push(i + ' Good St');
  r = await call(many);
  check('S12. more than 25 addresses -> 400 BAD_STOPS, Google never asked', r.code === 400 && r.body.error.code === 'BAD_STOPS' && r.upstream.length === 0, JSON.stringify(r.body));
  r = await call(many.slice(0, 25));
  check('S13. exactly 25 is accepted', r.code === 200 && r.body.results.length === 25, r.code);
  r = await call(['1 Good St', 'x'.repeat(201)]);
  check('S14. an over-long address fails ALONE (BAD_ADDRESS), the rest still geocode', r.code === 200 && one(r, 0).lat === 40.7128 && one(r, 1).error === 'BAD_ADDRESS' && r.upstream.length === 1, JSON.stringify(r.body));
  r = await call([]);
  check('S15. empty list -> 400 BAD_STOPS', r.code === 400 && r.body.error.code === 'BAD_STOPS');
  r = await call(['1 Good St'], null);
  check('S16. no session -> 401 NO_SESSION, Google never asked', r.code === 401 && r.body.error.code === 'NO_SESSION' && r.upstream.length === 0);
  r = await call(['1 Good St'], FOREIGN);
  check('S19. a session minted for ANOTHER licence -> 401 NO_SESSION, Google never asked', r.code === 401 && r.body.error.code === 'NO_SESSION' && r.upstream.length === 0, JSON.stringify(r.body));
  delete process.env.GOOGLE_MAPS_API_KEY;
  r = await call(['1 Good St']);
  check('S17. no key -> 503 NO_MAPS_KEY, Google never asked, no coordinate', r.code === 503 && r.body.error.code === 'NO_MAPS_KEY' && r.upstream.length === 0 && !r.body.results, JSON.stringify(r.body));
  process.env.GOOGLE_MAPS_API_KEY = KEY;
  // The image path is unchanged: a body with no action still draws a map.
  const ir = mockRes(); upstream = [];
  global.fetch = async (u) => { upstream.push(String(u)); return { ok: true, status: 200, headers: { get: () => 'image/png' }, arrayBuffer: async () => Uint8Array.from([1, 2]).buffer }; };
  await handler({ method: 'POST', headers: { authorization: 'Bearer X', 'x-sd-auth': TOKEN }, body: { addresses: ['1 A St'] } }, ir);
  check('S18. no action -> the static-map image path, unchanged', ir.code === 200 && typeof (ir.body && ir.body.image) === 'string' && upstream[0].indexOf('/staticmap?') !== -1, JSON.stringify(ir.body).slice(0, 120));
  return out;
}

const MUTANTS = [
  { name: 'M1 the 0,0 check removed',
    anchor: "  if (lat === 0 && lng === 0) return { address: address, error: 'BAD_LOCATION' };\n", repl: '' },
  { name: 'M2 the partial_match check removed',
    anchor: "  if (top && top.partial_match) return { address: address, error: 'PARTIAL_MATCH' };\n", repl: '' },
  { name: 'M3 the cap raised to 26',
    anchor: 'const MAX_GEOCODE = 25;', repl: 'const MAX_GEOCODE = 26;' },
  { name: 'M4 the geocode branch moved above the session check',
    anchor: '  const session = verifySessionToken(',
    repl: "  if (req.body && req.body.action === 'geocode') { await geocodeAll(res, req.body.addresses); return; }\n  const session = verifySessionToken(" },
];

(async () => {
  let fail = 0, couldNot = 0;
  const real = await arms(require('./route-map.js'));
  real.forEach((a) => {
    if (a.ok) console.log('  ok   ' + a.name);
    else { fail++; console.log('  FAIL ' + a.name + (a.detail ? '\n       ' + String(a.detail).slice(0, 300) : '')); }
  });
  for (const m of MUTANTS) {
    const n = SRC.split(m.anchor).length - 1;
    if (n !== 1) { couldNot++; console.log('  COULD NOT RUN ' + m.name + ': anchor found ' + n + ' times'); continue; }
    const res = await arms(compile(SRC.replace(m.anchor, m.repl)));
    const killedBy = res.filter((a) => !a.ok).map((a) => a.name.split('.')[0]);
    if (killedBy.length) console.log('  ok   ' + m.name + ' -- KILLED by ' + killedBy.join(', '));
    else { fail++; console.log('  FAIL ' + m.name + ' -- SURVIVED: no arm noticed'); }
  }
  console.log('\n' + (couldNot ? 'COULD NOT RUN' : fail ? 'FAILED' : 'ok') + '  b46 route geocode: ' + real.filter((a) => a.ok).length + '/' + real.length + ' arms, '
    + MUTANTS.length + ' mutants, ' + fail + ' failed, ' + couldNot + ' could not run');
  process.exit(couldNot ? 2 : fail ? 1 : 0);
})().catch((e) => { console.log('HARNESS ERROR: ' + (e && e.stack || e)); process.exit(2); });
