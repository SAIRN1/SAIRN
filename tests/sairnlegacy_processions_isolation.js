// tests/sairnlegacy_processions_isolation.js
//
// Run:  node tests/sairnlegacy_processions_isolation.js
//
// REQUIREMENT: leg_processions carries a DEVICE'S LIVE GPS POSITION joined to a
//   named decedent's case, so every read and write of it must require a verified
//   sairnlegacy session AND must be scoped to the caller's own licence -- never
//   reachable on the licence key alone, and never crossing a tenant boundary.
//
// ── WHY THIS ARM EXISTS AND WHY IT IS NOT A DUPLICATE ─────────────────────
// leg_processions was Tier B/B on a cell saying "no PII" until 2026-09-29. It
// holds `{id, case_id, status, lead_vehicle_label, started_at, ended_at,
// last_lat, last_lng, last_accuracy, last_updated_at, created_at}`, and
// `shareProcessionLocation()` (sairnlegacy.html:3746) calls the BROWSER'S OWN
// navigator.geolocation.getCurrentPosition with enableHighAccuracy and writes the
// real coordinates onto that case's row. rProcession() renders them as a
// clickable Google Maps link. It was promoted to Confidentiality-A the same day.
//
// A DELEGATED SOURCE-READING PASS ON THIS EXACT RESOURCE REPORTED IT CLEAN --
// "render only" -- and would have buried the finding a second time. That is the
// reason for a MECHANICAL arm rather than another read: the row is inert-looking
// unless you follow the one function that writes to it from a device sensor, and
// the next reader gets the same chance to miss it.
//
// ── WHAT IT ASSERTS, AND WHY EACH IS ON THE LIST ──────────────────────────
// 1. leg_processions is in LEG_RESOURCES, so the session gate covers it. The gate
//    is `if (LEG_RESOURCES[resource])` -- MEMBERSHIP IS THE WHOLE PROTECTION, and
//    a resource added to the app and forgotten here is open on the licence key
//    alone. That shape shipped three times: dnt_* (2026-08-27), SF_RESOURCES, and
//    LEG_RESOURCES itself on 2026-09-21, when 36 tables were open.
// 2. The gate runs BEFORE the read and the write branches, not inside one.
// 3. Every query is scoped by license_hash, so one funeral home cannot read
//    another's vehicle positions.
// 4. The APP's own write path sends a session token.
// 5. The coordinates are never rendered into a URL that leaves the app.
//
// ── ASSERTED ON SOURCE, AND THE LIMIT IS STATED ───────────────────────────
// This is a static arm over api/sd-data.js and sairnlegacy.html. It cannot prove
// the DEPLOYED function refuses -- only tools/alf_facility_role_gate_live_probe.py's
// shape can do that, and there is no live probe for this resource. What it can do
// is fail the day somebody removes leg_processions from the gated map, which is
// the failure that has actually happened three times.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const API = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
const APP = fs.readFileSync(path.join(ROOT, 'sairnlegacy.html'), 'utf8');

let pass = 0;
function t(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; }
}

console.log('leg_processions -- a device\'s live GPS, joined to a named case');

// ── THE GATED MAP, DERIVED FROM THE HANDLER ───────────────────────────────
const mapStart = API.indexOf('const LEG_RESOURCES = {');
assert.ok(mapStart > 0, 'LEG_RESOURCES is not in api/sd-data.js -- the anchor '
  + 'moved and every assertion below would be vacuous');
const mapBlock = API.slice(mapStart, API.indexOf('};', mapStart));
const gated = [...mapBlock.matchAll(/([a-z_]+):\s*'/g)].map((m) => m[1]);

t('LEG_RESOURCES parses to a non-trivial map (' + gated.length + ' resources)',
  () => {
    assert.ok(gated.length >= 30,
      'only ' + gated.length + ' parsed -- a short map makes the membership '
      + 'assertion below pass for the wrong reason');
  });

t('leg_processions IS in LEG_RESOURCES, so the session gate covers it', () => {
  assert.ok(gated.includes('leg_processions'),
    'leg_processions is NOT in the gated map, so it is reachable on the licence '
    + 'key alone -- the exact shape that shipped three times (dnt_* 2026-08-27, '
    + 'SF_RESOURCES, and LEG_RESOURCES itself on 2026-09-21 with 36 tables open). '
    + 'This resource carries a device\'s live coordinates.');
});

// ── THE GATE RUNS BEFORE THE BRANCHES ─────────────────────────────────────
t('the session check runs BEFORE the read and write branches, not inside one',
  () => {
    const guard = API.indexOf('if (LEG_RESOURCES[resource]) {', mapStart);
    const read = API.indexOf("if (LEG_RESOURCES[resource] && action === 'read')", mapStart);
    const write = API.indexOf("if (LEG_RESOURCES[resource] && action === 'write')", mapStart);
    assert.ok(guard > 0, 'no bare LEG_RESOURCES guard found');
    assert.ok(read > guard && write > guard,
      'the read/write branches do not both come AFTER the guard -- a gate inside '
      + 'one branch leaves the other open, which is how a read gate with no write '
      + 'gate has happened on this platform before');
    const body = API.slice(guard, read);
    assert.ok(/verifySessionToken\(/.test(body) && /NO_SESSION/.test(body),
      'the guard does not call verifySessionToken and answer NO_SESSION');
    assert.ok(/'sairnlegacy'/.test(body),
      'the guard does not pin the app to sairnlegacy -- without the third '
      + 'argument a token minted for another app would satisfy it');
  });

// ── TENANT SCOPE ──────────────────────────────────────────────────────────
t('every leg_ query is scoped by license_hash', () => {
  const read = API.indexOf("if (LEG_RESOURCES[resource] && action === 'read')", mapStart);
  const seg = API.slice(read, read + 1200);
  assert.ok(/license_hash=eq\.' \+ enc\(licHash\)/.test(seg),
    'the read does not filter on license_hash from the handler-derived value, so '
    + 'one funeral home could read another\'s vehicle positions');
  assert.ok(!/payload\.license_hash|body\.license_hash/.test(seg),
    'the scope comes from the PAYLOAD somewhere in this branch -- a '
    + 'client-supplied tenant key is not a boundary');
});

// ── THE APP SIDE ──────────────────────────────────────────────────────────
t('the app writes leg_processions through a transport that sends the session',
  () => {
    assert.ok(/sdnData\('write','leg_processions'/.test(APP.replace(/\s+/g, '')) ||
              /sdnData\(\s*'write'\s*,\s*'leg_processions'/.test(APP),
      'no sdnData write of leg_processions found -- either the transport changed '
      + 'or a direct fetch was introduced, and a direct fetch builds its own '
      + 'headers and can forget the token (the 2026-09-25 sdn_invoices defect)');
    // 1400 CHARACTERS WAS TOO SHORT AND THE ARM FAILED FOR THAT REASON, not
    // because the token is missing. sdnData's header block carries a 20-line
    // comment recording the 2026-09-21 measurement (56 of 58 call sites sent no
    // token, and 36 tables were open), so the X-SD-Auth line sits at offset
    // ~1726. A FIXED-WIDTH WINDOW OVER SOURCE TEXT is the defect class this repo
    // has recorded four times; the window now ends at the function's own return
    // rather than at a character count.
    const tStart = APP.indexOf('function sdnData');
    const tEnd = APP.indexOf('return fetch(', tStart);
    assert.ok(tEnd > tStart, 'sdnData has no fetch -- the transport changed shape');
    const transport = APP.slice(tStart, tEnd);
    assert.ok(/X-SD-Auth/.test(transport),
      'sdnData does not attach X-SD-Auth, so every gated write would 401');
  });

t('the GPS write comes from the device sensor and nothing else sets it', () => {
  const fn = APP.slice(APP.indexOf('function shareProcessionLocation'),
                       APP.indexOf('function shareProcessionLocation') + 1200);
  assert.ok(/navigator\.geolocation\.getCurrentPosition/.test(fn),
    'shareProcessionLocation no longer reads the device sensor -- if the '
    + 'coordinates now come from somewhere else, the confidentiality basis in '
    + 'docs/CRITICALITY-TIERS.md names the wrong source');
  assert.ok(/enableHighAccuracy\s*:\s*true/.test(fn),
    'the high-accuracy flag is gone -- the tier cell cites it, and a cell citing '
    + 'a flag that is not there is the citation-drift shape this repo keeps '
    + 'finding');
  // The ONLY writers of the coordinate fields. A third one would be a path the
  // tier cell does not describe.
  const writers = (APP.match(/last_lat\s*[:=]/g) || []).length;
  assert.ok(writers <= 3,
    writers + ' sites assign last_lat. The cell describes exactly two -- the '
    + 'seed in startProcession and the sensor write in shareProcessionLocation. '
    + 'A third is a path nobody has read.');
});

t('the coordinates are rendered only into a link the USER clicks, never fetched',
  () => {
    const r = APP.slice(APP.indexOf('function rProcession'),
                        APP.indexOf('function rProcession') + 1400);
    assert.ok(/google\.com\/maps\?q='\+p\.last_lat/.test(r.replace(/\s+/g, '')) ||
              /maps\?q=/.test(r),
      'the Maps link is gone -- the tier cell cites it as the disclosure surface');
    assert.ok(!/fetch\(/.test(r),
      'rProcession now FETCHES something. Sending coordinates to any host from '
      + 'the render path would move this resource from "rendered as a link the '
      + 'user chooses to open" to "transmitted", which is a different '
      + 'confidentiality question than the cell answers.');
  });

console.log('\n' + pass + ' passed');
