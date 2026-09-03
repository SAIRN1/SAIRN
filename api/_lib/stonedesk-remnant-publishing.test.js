// StoneDesk remnant publishing to the public catalog, driven verbatim from the
// real files.
//
// Competitive-gap audit GAP 8 ("no remnant publishing to the shop's public
// website"). THIS GAP WAS HALF-CLOSED AND THAT IS WHY IT WAS EASY TO MISS: the
// public catalog shipped the same day (GAP 1) and publishes SLABS, so the
// machinery existed and the audit item read as done. `stonedesk-catalog.html`
// contained the word "remnant" ZERO times, and nothing on any screen said the
// remnants were not in it. Found in the 2026-09-02 status re-derivation.
//
// THE FIVE PROPERTIES THIS FILE EXISTS TO HOLD:
//
//   1. ONLY A PUBLISHED **AND STILL AVAILABLE** REMNANT REACHES THE WEB. A
//      catalog offering a piece that has already been sold is the double-sale
//      problem in miniature -- the failure the slab reservation
//      compare-and-swap exists to stop. Both conditions are enforced on the
//      SERVER, not only in the browser.
//   2. THE PUBLIC SHAPE IS A BUILDER, NOT A DELETE-LIST. A field added to the
//      remnant blob later cannot leak by default, because the view is
//      assembled field by field -- there is no filter that can fail open.
//   3. THE PRICE **IS** PUBLISHED, AND THAT IS THE OPPOSITE OF THE SLAB RULE.
//      A slab's cost is what the SHOP PAID and is withheld; a remnant's price
//      is the ASKING price for a piece being cleared. Asserted in both
//      directions so a later "consistency fix" fails loudly instead of
//      silently deleting the feature.
//   4. `location` AND `age` ARE NOT PUBLISHED. The yard row maps the inside of
//      the building; `age` is a stored day count nothing increments, so
//      publishing it prints a fact that gets more wrong every day.
//   5. A MISSING sd_remnants TABLE MUST NOT TAKE THE SLAB CATALOG DOWN. The
//      remnant fetch is separate and non-fatal: a shop that has not run the
//      migration still gets its slabs.

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
const lib = require('./stonedesk-public.js');
const publicSrc = fs.readFileSync(path.join(ROOT, 'api', 'stonedesk-public.js'), 'utf8');
const libSrc = fs.readFileSync(path.join(ROOT, 'api', '_lib', 'stonedesk-public.js'), 'utf8');
const appSrc = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const pageSrc = fs.readFileSync(path.join(ROOT, 'stonedesk-catalog.html'), 'utf8');
const apiSrc = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

const { publicRemnantView, isRemnantPublishable, publicSlabView } = lib;

// A remnant blob as the yard actually stores it, plus the fields a shop would
// never want on a public page.
const REM = {
  id: 'R-001', stone: 'Calacatta Gold', size: '48x22', sqft: 7.3,
  status: 'Available', location: 'Yard-A Row 2', price: 185, age: 12,
  origin: 'J-2024-085', notes: 'Clean cut, no cracks', published: true
};

// ── 1. published AND available, both enforced ───────────────────────────
check('a published, available remnant is publishable', isRemnantPublishable(REM), true);
check('an unpublished remnant is not, whatever its status',
  isRemnantPublishable(Object.assign({}, REM, { published: false })), false);
check('a remnant with NO published flag is not -- absent means no, never yes by default',
  [isRemnantPublishable(Object.assign({}, REM, { published: undefined })),
   isRemnantPublishable({}), isRemnantPublishable(null), isRemnantPublishable(undefined)],
  [false, false, false, false]);
// The one that matters: ticked, but gone.
check('a SOLD remnant is not publishable even with the flag still ticked',
  isRemnantPublishable(Object.assign({}, REM, { status: 'Sold' })), false);
check('nor is a RESERVED one',
  isRemnantPublishable(Object.assign({}, REM, { status: 'Reserved' })), false);
check('nor is one with no status at all',
  isRemnantPublishable(Object.assign({}, REM, { status: '' })), false);
// `published` must be the boolean true, not merely truthy -- a stray string
// from an old import must not publish a piece.
check('a truthy non-boolean does not count as published',
  [isRemnantPublishable(Object.assign({}, REM, { published: 'yes' })),
   isRemnantPublishable(Object.assign({}, REM, { published: 1 }))], [false, false]);

// ── 2 & 4. the public shape is a builder and withholds the internals ────
{
  const v = publicRemnantView(REM);
  check('the public view carries exactly the intended keys and no others',
    Object.keys(v).sort(), ['id', 'notes', 'photo_base64', 'price', 'size', 'sqft', 'stone']);
  check('the yard location is NOT published -- it maps the inside of the building',
    'location' in v, false);
  check('the age is NOT published -- it is a stored count nothing increments',
    'age' in v, false);
  check('the originating job is not published either', 'origin' in v, false);
  check('and neither is the publish flag itself', 'published' in v, false);
  // The construction test: a field added to the blob later must not appear.
  const withNew = publicRemnantView(Object.assign({}, REM, {
    supplier_cost: 40, internal_note: 'undercut on the invoice', vendor: 'ACME'
  }));
  check('a field added to the blob later cannot leak -- the view is built, not filtered',
    [('supplier_cost' in withNew), ('internal_note' in withNew), ('vendor' in withNew)],
    [false, false, false]);
  check('a photo that is not a string is dropped rather than passed through',
    publicRemnantView(Object.assign({}, REM, { photo_base64: { evil: true } })).photo_base64, '');
}

// ── 3. the price IS published, and the slab cost is NOT ─────────────────
check('the remnant asking price reaches the public view', publicRemnantView(REM).price, 185);
check('a zero or missing price becomes null, not 0 -- 0 would read as free',
  [publicRemnantView(Object.assign({}, REM, { price: 0 })).price,
   publicRemnantView(Object.assign({}, REM, { price: undefined })).price], [null, null]);
// ASSERTED IN BOTH DIRECTIONS. These two rules look contradictory side by side
// and a later "consistency fix" would delete one of them; this makes that fix
// fail loudly.
{
  const slab = publicSlabView({ id: 'S1', material: 'granite', cost: 900, price: 1200, colorName: 'X' });
  check('a SLAB still publishes no cost and no price -- what the shop paid stays private',
    [('cost' in slab), ('price' in slab)], [false, false]);
  check('the library says out loud why the two rules differ',
    /THE PRICE IS PUBLISHED HERE, AND THAT IS THE OPPOSITE OF THE SLAB RULE/.test(libSrc), true);
  check('and the shop-facing panel says it too, where the toggle is',
    /deliberately the opposite of the slab rule above/.test(appSrc), true);
}

// ── the endpoint wires it up, and a missing table is not fatal ──────────
check('the catalog action filters remnants through isRemnantPublishable',
  /\.filter\(isRemnantPublishable\)\s*\n\s*\.map\(publicRemnantView\)/.test(publicSrc), true);
check('the remnant fetch is guarded by rr.ok so a missing table yields an empty list',
  /if \(rr\.ok\) \{/.test(publicSrc) && /let remnants = \[\];/.test(publicSrc), true);
check('and the response carries remnants alongside slabs',
  /remnants: remnants,\s*\n\s*remnant_count: remnants\.length/.test(publicSrc), true);
check('the endpoint header documents the not-already-gone rule',
  /IT WILL NOT SHOW A REMNANT THAT IS ALREADY GONE/.test(publicSrc), true);
// The whole point of the separate fetch: the slab catalog must survive it.
check('the slab fetch still fails the request but the remnant fetch does not',
  /if \(!r\.ok\) \{ res\.status\(502\)/.test(publicSrc) &&
  !/if \(!rr\.ok\) \{ res\.status/.test(publicSrc), true);

// ── the public page renders them, and stops contradicting itself ────────
check('the catalog page has a remnant card and a render target',
  /id="remnant-card"/.test(pageSrc) && /id="remnants"/.test(pageSrc) && /id="remnant-sub"/.test(pageSrc), true);
check('renderRemnants is defined and called with the endpoint field',
  /function renderRemnants\(rem\)\{/.test(pageSrc) &&
  /renderRemnants\(r\.data\.remnants\|\|\[\]\);/.test(pageSrc), true);
check('the card is hidden when there is nothing in it, not left as an empty heading',
  /if\(!rem\.length\)\{card\.className='card hide';box\.innerHTML='';return;\}/.test(pageSrc), true);
// The page used to say flatly "prices are not listed here". With remnants on it
// that is false, and a page that contradicts itself is worse than one that says
// nothing.
check('the footer no longer claims prices are never listed',
  /<strong>Slab<\/strong> prices are not listed here on purpose/.test(pageSrc) &&
  !/^Prices are not listed here on purpose/m.test(pageSrc), true);
check('the footer says remnants carry an asking price',
  /<strong>Remnants<\/strong> are single offcuts sold as they are, so those carry an asking price/.test(pageSrc), true);
check('a null price renders as "ask" rather than as $0',
  /var price=\(r\.price===null\|\|r\.price===undefined\)\?'ask':'\$'\+H\(r\.price\)/.test(pageSrc), true);
// ASSERTED ON THE CODE, NOT ON THE COMMENT EXPLAINING IT. The first version
// also matched the prose "nothing here needs to filter on status" and failed --
// the sentence WRAPS ACROSS TWO `//` LINES, so the phrase does not exist as
// contiguous text. Scrubber item 16 shape A, the wrapped-quote variant, and the
// only thing that actually matters here is that no status filter exists.
// ASSERTED ON THE EXTRACTED FUNCTION, NOT ON THE FILE OR ON THE COMMENT.
// Version one matched the prose "nothing here needs to filter on status" and
// failed -- the sentence WRAPS ACROSS TWO `//` LINES so the phrase does not
// exist as contiguous text (scrubber item 16 shape A, wrapped-quote variant).
// Version two matched `/r\.status/` file-wide and failed on `post()`'s
// `status:r.status`, an HTTP response code with nothing to do with remnants.
// The requirement is narrow: renderRemnants itself must not filter on status.
{
  const i = pageSrc.indexOf('function renderRemnants(');
  let depth = 0, j = pageSrc.indexOf('{', i), body = '';
  for (; j < pageSrc.length; j++) {
    if (pageSrc[j] === '{') depth++;
    else if (pageSrc[j] === '}') { depth--; if (!depth) { body = pageSrc.slice(i, j + 1); break; } }
  }
  check('the page does not re-filter on status -- one filter, on the server',
    [/status/.test(body), /renderRemnants\(r\.data\.remnants\|\|\[\]\);/.test(pageSrc)],
    [false, true]);
}
check('the remnant photo goes through the same safePhoto gate as a slab',
  /var ph=safePhoto\(r\.photo_base64\);/.test(pageSrc), true);

// ── the shop-facing side: sync, hydrate, and a visible held-back state ──
check('the remnant module exports a list, a sync and a hydrate rather than a second array copy',
  /window\.sdRemnantList=function\(\)\{return data;\};/.test(appSrc) &&
  /window\.sdRemnantSyncOne=async function\(r\)\{/.test(appSrc) &&
  /window\.sdRemnantHydrate=async function\(\)\{/.test(appSrc), true);
check('hydration replaces the local row rather than only adding unseen ones',
  /if\(JSON\.stringify\(byId\[r\.id\]\)!==JSON\.stringify\(r\)\)\{byId\[r\.id\]=r;changed=true;\}/.test(appSrc), true);
check('the toggle writes straight through to the server, not only to this device',
  /var ok=\(typeof sdRemnantSyncOne==='function'\) \? await sdRemnantSyncOne\(r\) : null;/.test(appSrc), true);
// ASSERTED ON THE GUARD INSIDE pcToggleRemnant, not on the sentence. The
// sentence is also in the SLAB toggle, and the negative control that changed
// `notify(!ok` to `notify(false` -- so a local-only save always reports success
// -- left the text untouched and scored a clean 50/50. Item 16 shape B, third
// time in this build.
{
  const i = appSrc.indexOf('window.pcToggleRemnant=async function');
  const body = appSrc.slice(i, appSrc.indexOf('function pcRenderRequests', i));
  check('a failed sync says the web catalog has NOT changed rather than reporting success',
    /notify\(!ok\s*[\r\n]+\s*\? 'Saved on this device only -- the catalog on the web has NOT changed/.test(body), true);
}
// THE HELD-BACK STATE IS THE ONE A SHOP WOULD OTHERWISE HAVE TO GUESS AT.
// THE GUARD IS PART OF THE ASSERTION, not just the label text. The first
// version matched `ticked, but held back` anywhere, so the negative control
// that disabled the branch with `false?` left the string in the file and
// scored a clean 50/50 -- scrubber item 16 shape B, existence where the
// requirement is use.
check('a ticked but not-Available remnant is shown as held back, with the reason',
  /:\(!web\?'ticked, but held back &mdash; '\+pcHtml\(r\.status\|\|'not Available'\)/.test(appSrc) &&
  /function pcRemnantOnWeb\(r\)\{ return !!\(r && r\.published===true && r\.status==='Available'\); \}/.test(appSrc), true);
check('and the toast says the same thing rather than claiming it was published',
  /Marked, but held back -- it is '\+r\.status\+', so it stays off the catalog until it is Available/.test(appSrc), true);
check('the panel table exists and is rendered from the shop panel',
  /id="pc-remnants-tbody"/.test(appSrc) &&
  (appSrc.match(/pcRenderRemnants\(\);/g) || []).length >= 2, true);
check('remnants are hydrated before the publish table is drawn',
  /if\(typeof sdRemnantHydrate==='function'\)await sdRemnantHydrate\(\);\s*\r?\n\s*pcRenderRemnants\(\);/.test(appSrc), true);
check('the panel states that only an Available piece reaches the web',
  /<strong>Only an Available piece reaches the web\.<\/strong>/.test(appSrc), true);
check('and that the yard location is never published',
  /location is never published<\/strong>/.test(appSrc), true);

// ── the resource and its store ──────────────────────────────────────────
check('the remnants resource is registered for stonedesk',
  /'remnants',/.test(fs.readFileSync(path.join(ROOT, 'api', '_resources', 'stonedesk.js'), 'utf8')), true);
check('sd-data has a remnants read and write branch keyed on remnant_id',
  /resource === 'remnants' && action === 'read'/.test(apiSrc) &&
  /resource === 'remnants' && action === 'write'/.test(apiSrc) &&
  /remnant_id: String\(payload\.id\)/.test(apiSrc), true);
check('the write refuses a payload with no id',
  /res\.status\(400\)\.json\(\{ error: \{ message: 'remnant payload\.id is required' \} \}\)/.test(apiSrc), true);
check('an unprovisioned table says so instead of reporting a successful write',
  /run sql\/stonedesk_remnants_schema\.sql in Supabase first/.test(apiSrc), true);
check('the read reports provisioned:false rather than an error when the table is absent',
  /if \(r\.status === 404 \|\| r\.status === 400\) \{ res\.status\(200\)\.json\(\{ ok: true, data: \[\], provisioned: false \}\); return; \}[\s\S]{0,200}sd_remnants/.test(apiSrc) ||
  /sd_remnants[\s\S]{0,400}provisioned: false/.test(apiSrc), true);

{
  const sql = fs.readFileSync(path.join(ROOT, 'sql', 'stonedesk_remnants_schema.sql'), 'utf8');
  const grants = sql.split(/\r?\n/).filter((l) => /^\s*grant\b/i.test(l));
  check('the schema exists and no grant confers delete',
    [/create table if not exists public\.sd_remnants/.test(sql), grants.some((l) => /\bdelete\b/i.test(l))],
    [true, false]);
  check('RLS is on and there is no anon policy',
    /enable row level security/.test(sql) &&
    /revoke all on public\.sd_remnants from anon, authenticated/.test(sql), true);
  check('the blob is size-capped, like sd_slabs, because a photo lives in it',
    /octet_length\(data::text\) <= 65536/.test(sql), true);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
