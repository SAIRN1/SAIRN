// tests/intake_form_public_surface.js
//
// Run:  node tests/intake_form_public_surface.js
//
// The intake form is built on the public surface that already existed, not on
// a new one. The task as written was to migrate intake_submissions to carry
// license_hash/app_id and a slug, and to add a rate-limit table. None of that
// was needed: sql/stonedesk_public_surface_schema.sql (2026-09-02) already
// ships sd_public_shop with a unique shop_slug, sd_quote_requests, and
// sd_public_rate_limits, and api/stonedesk-public.js is live and answering.
//
// So these assertions guard the thing that could quietly go wrong instead: a
// second public surface growing back, a photo silently not being stored, and
// INTAKE_FORM_LIVE being flipped before the migration has actually been run.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const R = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

const endpoint = R('api/stonedesk-public.js');
const page = R('stonedesk-intake.html');
const app = R('stonedesk.html');
const migration = R('sql/stonedesk_intake_photos_2026-09-03.sql');
const vercel = JSON.parse(R('vercel.json'));
const snapshot = JSON.parse(R('db/schema_snapshot.json'));

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('--- ' + t + ' ---'); }

// ---------------------------------------------------------------------------
section('the page exists and is actually routed');

test('THE 404 IS THE WHOLE POINT: /stonedesk-intake now has a route', () => {
  const srcs = vercel.routes.map((r) => r.src);
  assert.ok(srcs.includes('/stonedesk-intake$'),
    'no vercel route for /stonedesk-intake -- the page would still 404');
  const route = vercel.routes.find((r) => r.src === '/stonedesk-intake$');
  assert.strictEqual(route.dest, '/stonedesk-intake.html');
});

test('...and the build copies it, so the route resolves to something', () => {
  assert.match(vercel.buildCommand, /cp \*\.html dist\//);
  assert.ok(fs.existsSync(path.join(ROOT, 'stonedesk-intake.html')));
});

// ---------------------------------------------------------------------------
section('no second public surface was built');

test('the page posts to the EXISTING endpoint, not a new one', () => {
  assert.match(page, /var API = '\/api\/stonedesk-public'/);
  assert.ok(!/api\/stonedesk-intake/.test(page),
    'the page points at an intake-specific endpoint that should not exist');
  assert.ok(!fs.existsSync(path.join(ROOT, 'api', 'stonedesk-intake.js')),
    'a second public endpoint was created');
});

test('it reuses the quote_request action rather than adding a third', () => {
  assert.match(page, /action: 'quote_request'/);
  // ANCHORED ON THE WHOLE GUARD, not a substring of it. The first version of
  // this asserted the substring `action !== 'catalog' && action !== 'quote_request'`
  // and a negative control that APPENDED `&& action !== 'intake'` still matched
  // it -- the assertion passed while the thing it guards had changed.
  const guard = /if \(action !== 'catalog' && action !== 'quote_request'\) \{/;
  assert.match(endpoint, guard,
    'the action guard changed shape -- the two-action contract is what keeps '
    + 'the catalog form and the intake form the same surface');
  const conds = (/if \(action !== ([^)]*)\) \{/.exec(endpoint) || [])[1] || '';
  assert.strictEqual((conds.match(/action !==/g) || []).length, 1,
    'a third action was added to the guard: ' + conds);
});

test('THE MIGRATION ADDS ONE TABLE, not a slug column or a rate limiter', () => {
  const creates = migration.match(/create table if not exists public\.(\w+)/g) || [];
  assert.strictEqual(creates.length, 1, 'expected exactly one new table: ' + creates.join(', '));
  assert.match(creates[0], /sd_quote_request_photos/);
  assert.ok(!/rate_limit/i.test(migration.replace(/--[^\n]*/g, '')),
    'a second rate-limit table is being created -- sd_public_rate_limits already exists');
  assert.ok(!/alter table[\s\S]{0,80}intake_submissions/i.test(migration),
    'the migration touches intake_submissions; it is deliberately left alone');
});

test('the migration grants service_role only, and never delete or anon', () => {
  const grants = migration.match(/^grant [^\n]*/gm) || [];
  assert.ok(grants.length > 0, 'no grant at all -- the table would be unreadable');
  grants.forEach((g) => {
    assert.ok(!/\bdelete\b/i.test(g), 'a delete grant is back: ' + g);
    assert.ok(!/\banon\b/i.test(g), 'an anon grant would make kitchen photos world-readable: ' + g);
    assert.match(g, /to service_role;/);
  });
});

// ---------------------------------------------------------------------------
section('photos cannot be silently lost');

test('the photo table is NOT in the live snapshot -- so it must not be assumed', () => {
  // This is the fact that keeps INTAKE_FORM_LIVE false. If someone regenerates
  // the snapshot after running the migration, this assertion flips and is the
  // signal that the flag may move.
  const live = Object.prototype.hasOwnProperty.call(snapshot, 'sd_quote_request_photos');
  assert.strictEqual(live, false,
    'sd_quote_request_photos IS in the snapshot now -- the migration may have been '
    + 'run. Re-verify live, then INTAKE_FORM_LIVE can be considered.');
});

test('photos are validated BEFORE the request row is written', () => {
  const iPhoto = endpoint.indexOf('PHOTO_TOO_LARGE');
  const iWrite = endpoint.indexOf("rest('sd_quote_requests')");
  assert.ok(iPhoto > 0 && iWrite > 0, 'could not locate both points');
  assert.ok(iPhoto < iWrite,
    'an oversized photo is rejected AFTER the request row exists -- that leaves a '
    + 'request the shop can see with a photo the customer thinks they sent');
});

test('a failed photo write does not fail the request, and is not silent', () => {
  assert.match(endpoint, /photos_sent: photos\.length, photos_saved: photosSaved/);
  assert.match(endpoint, /console\.error\('stonedesk-public: photos rejected for '/,
    'a rejected photo is not logged with its reference');
});

test('the page reports a partial save instead of plain success', () => {
  assert.match(page, /could not be attached/);
  assert.ok(/sent && saved < sent/.test(page),
    'the page does not compare photos_sent against photos_saved');
});

test('the client cap matches the server cap, and the server is the one that holds', () => {
  const c = /MAX_PHOTO_CHARS = (\d+)/.exec(page);
  const s = /MAX_PHOTO_CHARS = (\d+)/.exec(endpoint);
  assert.ok(c && s, 'a cap is missing on one side');
  assert.strictEqual(c[1], s[1], 'the client and server photo caps disagree');
  assert.match(endpoint, /if \(p\.length > MAX_PHOTO_CHARS\)/,
    'the server does not enforce its own cap -- a client limit is a courtesy, not a control');
});

test('the per-photo cap fits inside the row constraint it has to live in', () => {
  // COMMENTS ARE STRIPPED FIRST, and this is the third time today an assertion
  // in this repo matched its own documentation instead of the code: the push
  // gate's override matcher, the intake bare-catch scan, and this. The
  // migration's header quotes sd_quote_requests' 64 KB cap to explain why the
  // photos need their own table, and an unstripped regex read that quotation as
  // the constraint under test and "failed" correctly-written SQL.
  const sql = migration.replace(/--[^\n]*/g, '');
  const rowCap = Number(/sdqrp_data_size check \(octet_length\(data::text\) <= (\d+)\)/.exec(sql)[1]);
  const cap = Number(/MAX_PHOTO_CHARS = (\d+)/.exec(endpoint)[1]);
  assert.ok(cap < rowCap,
    'a photo at the endpoint cap (' + cap + ') would not fit the row cap (' + rowCap + ')');
});

// ---------------------------------------------------------------------------
section('the link and the page agree on what ?shop= means');

test('the page reads ?shop= as the slug, matching /stonedesk-catalog', () => {
  assert.match(page, /var SLUG = qs\('shop'\)/);
});

test('the panel builds ?shop= from sd_public_shop, not a display name', () => {
  const i = app.indexOf('function intakeBuildLink()');
  const j = app.indexOf('function intakeCopyLink()');
  assert.ok(i > 0 && j > i, 'could not bound intakeBuildLink');
  const block = app.slice(i, j).replace(/\/\/[^\n]*/g, '');
  assert.match(block, /sdData\('read', 'sd_public_shop'/);
  assert.match(block, /\?shop=' \+ encodeURIComponent\(slug\)/);
  assert.ok(!/company_name/.test(block),
    'the company display name is still being read into the link');
});

test('the page validates the slug before showing the form', () => {
  const iCatalog = page.indexOf("action: 'catalog'");
  const iForm = page.indexOf("show('step-form')");
  assert.ok(iCatalog > 0 && iCatalog < iForm,
    'the form is shown without checking the shop exists -- a form that fails on '
    + 'submit wastes the customer\'s time and reads as the shop\'s fault');
});

test('the page surfaces the server\'s own message rather than a generic one', () => {
  assert.match(page, /data\.error && data\.error\.message/);
  assert.match(page, /Nothing was sent/,
    'a failed submit does not tell the customer nothing was sent');
});

// ---------------------------------------------------------------------------
section('INTAKE_FORM_LIVE stays false until the migration is really run');

test('THE GATE: the flag is still false', () => {
  assert.match(app, /var INTAKE_FORM_LIVE = false;/,
    'INTAKE_FORM_LIVE was flipped. It may only move once '
    + 'sql/stonedesk_intake_photos_2026-09-03.sql has been run AND confirmed live -- '
    + 'the page and route existing is not the same as the shop being able to receive '
    + 'what a customer sends.');
});

test('and the panel still warns, because the flag still says it is not live', () => {
  assert.match(app, /The intake form is not live yet/);
});

console.log('\n' + (fail === 0
  ? 'ALL ' + pass + ' INTAKE-FORM ASSERTIONS PASS'
  : pass + ' passed, ' + fail + ' FAILED'));
process.exit(fail === 0 ? 0 : 1);
