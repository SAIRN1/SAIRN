// tests/stonedesk_locations.js
// StoneDesk multi-location (yards), competitive-gap audit GAP 7.
//
// The audit: "no multi-location support ... caps StoneDesk at single-yard shops
// and excludes exactly the consolidating multi-branch fabricator that has the
// budget." Verified absent word-boundary before building: `location_id` 0,
// `locationId` 0, `sd_locations` 0, `multiLocation` 0, `yard_id` 0.
//
// THE FIVE PROPERTIES THIS FILE HOLDS:
//
//  1. THE SLAB IS THE ONLY RECORD THAT CARRIES A LOCATION. Everything else
//     derives. Stamping a yard onto a job at creation freezes it -- move the
//     work and the history stays with the old yard forever.
//  2. UNASSIGNED IS ALWAYS ITS OWN ROW and is never folded into a yard. Every
//     slab that exists today has no yard because the field is new, so this is
//     the state every real shop is in the moment this ships.
//  3. THE ROLLUP IS COMPUTED FROM THE SLABS, NEVER STORED. A stored per-yard
//     count drifts the moment a slab moves.
//  4. A SLAB WITH NO COST IS COUNTED AS UNPRICED, NEVER SUMMED AS $0 -- the
//     rule the Slabs KPI row already follows.
//  5. `location_id` IS THE YARD; `yardLocation` IS THE BAY INSIDE IT. The free
//     text was already there and is untouched. Conflating them is why grepping
//     "location" made this look partly built when it was not built at all.

const fs = require('fs');
const path = require('path');

const ROOT = path.dirname(__dirname);
const src = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');
const api = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; console.log('  ok   ' + name); return; }
  fail++;
  console.log('  FAIL ' + name + '\n         expected ' + e + '\n         actual   ' + a);
}

function balanced(start) {
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function fn(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i);
}
// Same, but returns the whole `window.x = function(){...};` assignment so the
// extracted text is executable exactly as written in the app.
function fnAssign(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error('not found: ' + decl);
  return balanced(i) + ';';
}

// The rollup is driven for real: extracted verbatim and run against slab
// fixtures, so this exercises the arithmetic rather than the source text.
function build(world) {
  return new Function('W',
    'var sdSlabs=W.slabs, sdLocations=W.locations;\n' +
    'var slabCost=W.slabCost;\n' +
    // EXTRACTED, NOT REIMPLEMENTED. These two were hand-written stubs in the
    // first version, and the negative control that changed the REAL sdLocName
    // to relabel an unknown yard "Unassigned" scored a clean 54/54 -- the test
    // was asserting its own copy. Same class as testing a stub and calling it
    // coverage.
    'var window={};\n' +
    fnAssign('window.sdLocActive = function()') + '\n' +
    fnAssign('window.sdLocName = function(id)') + '\n' +
    'var sdLocActive=window.sdLocActive, sdLocName=window.sdLocName;\n' +
    fn('window.sdLocRollup = function(){') + '\n' +
    'return { rollup: window.sdLocRollup, name: sdLocName, active: sdLocActive };'
  )(world);
}
const COST = (s) => (s.cost === null || s.cost === undefined ? null : Number(s.cost));
function world(o) {
  return { slabs: o.slabs || [], locations: o.locations || [], slabCost: COST };
}
const SLAB = (o) => Object.assign({ id: 's', usableSqft: 10, cost: 100 }, o);
const LOCS = [{ id: 'L1', name: 'Cleveland', active: true },
               { id: 'L2', name: 'Akron', active: true }];

console.log('StoneDesk GAP 7 -- yards attribute inventory, and never invent it');

// ── 2 & 3. unassigned is its own row; the rollup is computed ────────────
{
  const w = build(world({
    locations: LOCS,
    slabs: [SLAB({ id: 'a', location_id: 'L1', usableSqft: 50, cost: 400 }),
            SLAB({ id: 'b', location_id: 'L1', usableSqft: 30, cost: 200 }),
            SLAB({ id: 'c', location_id: 'L2', usableSqft: 20, cost: 100 }),
            SLAB({ id: 'd', usableSqft: 15, cost: 90 })]
  }));
  const out = w.rollup();
  const by = {}; out.rows.forEach((r) => { by[r.location_id || '__none'] = r; });
  check('each yard carries only its own slabs',
    [by.L1.slabs, by.L1.sqft, by.L1.value, by.L2.slabs], [2, 80, 600, 1]);
  check('a slab with no yard lands in its OWN row, not in the first yard',
    [by.__none.slabs, by.__none.sqft, by.__none.value], [1, 15, 90]);
  check('and that row is named Unassigned', by.__none.name, 'Unassigned');
  check('the columns add up to the whole yard -- nothing is dropped',
    [out.totals.slabs, out.totals.sqft, out.totals.value], [4, 115, 790]);
  check('Unassigned sorts LAST -- it is a gap to close, not a yard to rank',
    out.rows[out.rows.length - 1].location_id, '');
}
{
  // The state EVERY shop is in the moment this ships: the field is new, so no
  // slab has a yard. It must read as one honest Unassigned row.
  const out = build(world({ locations: LOCS, slabs: [SLAB({ id: 'a' }), SLAB({ id: 'b' })] })).rollup();
  const un = out.rows.filter((r) => !r.location_id)[0];
  check('with no slab attributed anywhere, Unassigned holds all of them',
    [un.slabs, out.totals.slabs], [2, 2]);
  // Sorted by slabs then NAME, so two empty yards come out alphabetically.
  // The tiebreak is deliberate -- it makes the table stable between two renders
  // of the same data rather than depending on insertion order.
  check('and the yards still appear, at zero, rather than vanishing',
    out.rows.filter((r) => r.location_id).map((r) => [r.name, r.slabs]),
    [['Akron', 0], ['Cleveland', 0]]);
}
{
  // A closed yard is not seeded, but a slab still sitting in one is still
  // reported -- the stone did not stop existing when the office shut.
  const out = build(world({
    locations: [{ id: 'L1', name: 'Cleveland', active: true },
                { id: 'L9', name: 'Old Yard', active: false }],
    slabs: [SLAB({ id: 'a', location_id: 'L9' })]
  })).rollup();
  check('a closed yard holding stone is still a row',
    out.rows.filter((r) => r.location_id === 'L9').map((r) => r.slabs), [1]);
  check('but a closed yard is not counted as an open one', build(world({
    locations: [{ id: 'L1', name: 'A', active: true }, { id: 'L9', name: 'B', active: false }]
  })).active().length, 1);
}

// ── 4. no cost is UNPRICED, never $0 ───────────────────────────────────
{
  const out = build(world({
    locations: [LOCS[0]],
    slabs: [SLAB({ id: 'a', location_id: 'L1', cost: 500 }),
            SLAB({ id: 'b', location_id: 'L1', cost: null })]
  })).rollup();
  const r = out.rows[0];
  check('an unpriced slab is counted and disclosed, not summed as zero',
    [r.slabs, r.value, r.unpriced], [2, 500, 1]);
  check('and the total carries the same disclosure', out.totals.unpriced, 1);
}
{
  // A yard this device does not hold still had stone in it. Saying so beats a
  // raw id, and beats relabelling it Unassigned -- it WAS assigned, to
  // something not here. Same rule as SAIRNsenior's brName().
  const w = build(world({ locations: [], slabs: [SLAB({ id: 'a', location_id: 'GONE' })] }));
  check('a yard not on this device says so rather than showing a raw id',
    w.name('GONE'), '(yard not on this device)');
  const out = w.rollup();
  check('and its slabs are NOT relabelled Unassigned',
    out.rows.map((r) => [r.location_id, r.slabs]), [['GONE', 1]]);
}

// ── 1 & 5. where the field lives, and what it is not ───────────────────
check('the slab record carries location_id',
  /yardLocation:location, location_id:locId,/.test(src), true);
check('and yardLocation -- the BAY -- is untouched beside it',
  /var location=prompt\('Bay\/location:','''?\)/.test(src) || /var location=prompt\('Bay\/location:',''\)/.test(src), true);
// ASSERTED ON THE STORED-RECORD SITE, not on every mention. The first version
// counted `/location_id:/` file-wide and failed at 3 -- the other two are the
// ROLLUP BUCKET (`location_id:k`), which is a computed row rather than a
// persisted record, and it is correct for that to carry one. The property is
// that exactly one thing STORES it, and that thing is the slab.
check('exactly one record type stores a location_id, and it is the slab',
  [(src.match(/location_id:locId/g) || []).length,
   (src.match(/location_id:k,/g) || []).length], [1, 1]);
// The derived ones, named so a later session adding a stamp to any of them
// fails here rather than quietly freezing that record's attribution.
['quote', 'job', 'po', 'remnant', 'invoice'].forEach((kind) => {
  check('no ' + kind + ' record stores its own location_id',
    new RegExp(kind + '[^\n]{0,120}location_id\s*:', 'i').test(src), false);
});
check('the panel states that a yard is not a bay',
  /<b>A yard is not a bay\.<\/b>/.test(src), true);

// ── the honest refusal: attribution, not access control ────────────────
check('the panel says in terms that this does NOT partition access',
  /<b>This attributes inventory to a yard\. It does NOT partition access\.<\/b>/.test(src), true);
check('and names what would be required instead of implying it is done',
  /authorisation change reaching every panel and the employee roster/.test(src), true);

// ── the filter, and the Unassigned bucket being reachable ──────────────
check('the slab list honours the yard filter',
  /var loc=!lf\|\|\(lf==='__none'\?!s\.location_id:String\(s\.location_id\|\|''\)===lf\);/.test(src), true);
check('Unassigned is selectable -- otherwise the slabs needing attention are the one group nobody can list',
  /<option value="__none">Unassigned<\/option>/.test(src), true);
check('the filter is hidden below two yards rather than shown with one option',
  /if\(ls\.length < 2\)\{ sel\.style\.display='none'; sel\.innerHTML=''; return; \}/.test(src), true);

// ── creation: a guess is never made ───────────────────────────────────
check('the yard prompt only appears when there is a choice to make',
  /if\(locs\.length>1\)\{/.test(src) && /\} else if\(locs\.length===1\)\{/.test(src), true);
check('an out-of-range answer leaves the slab UNASSIGNED rather than defaulting to the first yard',
  /if\(n>=1&&n<=locs\.length\) locId=locs\[n-1\]\.id;/.test(src), true);

// ── sync, and the local-only warning ──────────────────────────────────
check('hydration replaces the local row rather than only adding unseen ones',
  /if\(JSON\.stringify\(byId\[l\.id\]\)!==JSON\.stringify\(l\)\)\{ byId\[l\.id\]=l; changed=true; \}/.test(src), true);
check('a yard that only saved locally says the server has NOT got it',
  /the server has NOT got this yard/.test(src), true);
check('a yard is CLOSED, never deleted',
  /window\.sdLocToggle = async function\(id\)\{/.test(src) &&
  !/sdData\('delete','locations'/.test(src), true);

// ── panel wiring ──────────────────────────────────────────────────────
['panel-locations', 'loc-rollup', 'loc-list', 'loc-note',
 'loc-kpi1', 'loc-kpi2', 'loc-kpi3', 'loc-kpi4',
 'sb-locations', 'slabs-location-filter'].forEach((id) => {
  check('the DOM node #' + id + ' exists', new RegExp('id="' + id + '"').test(src), true);
});
check('the sidebar button points at the panel', /id="sb-locations" onclick="sbNav\('locations'\)"/.test(src), true);
check('the panel is wired into the nav render hook',
  /if\(id==='locations'&&typeof window\.sdLocRender==='function'\)window\.sdLocRender\(\);/.test(src), true);
check('something on screen adds a yard', /onclick="sdLocAdd\(\)"/.test(src), true);

// ── server ────────────────────────────────────────────────────────────
check('sd-data has a locations read and write branch keyed on location_id',
  /resource === 'locations' && action === 'read'/.test(api) &&
  /resource === 'locations' && action === 'write'/.test(api) &&
  /location_id: String\(payload\.id\)/.test(api), true);
// ANCHORED TO THE GUARD, not the message. The message survives when the `if`
// around it is disabled, and the negative control that did exactly that scored
// a clean 54/54. Scrubber item 16 shape B, third time in this session.
check('the server refuses an unnamed yard -- it would render as a raw id everywhere',
  /if \(!String\(payload\.name \|\| ''\)\.trim\(\)\) \{/.test(api) &&
  /location name is required -- an unnamed yard renders as a raw id/.test(api), true);
check('the server refuses a write with no id',
  /message: 'location payload\.id is required'/.test(api), true);
check('an unprovisioned table says so instead of reporting a successful write',
  /run sql\/stonedesk_locations_schema\.sql in Supabase first/.test(api), true);
check('there is no delete verb for locations',
  /resource === 'locations' && action === 'delete'/.test(api), false);
check('the resource is registered',
  /'locations',/.test(fs.readFileSync(path.join(ROOT, 'api', '_resources', 'stonedesk.js'), 'utf8')), true);

{
  const sql = fs.readFileSync(path.join(ROOT, 'sql', 'stonedesk_locations_schema.sql'), 'utf8');
  const grants = sql.split(/\r?\n/).filter((l) => /^\s*grant\b/i.test(l));
  check('the schema exists and no grant confers delete',
    [/create table if not exists public\.sd_locations/.test(sql), grants.some((l) => /\bdelete\b/i.test(l))],
    [true, false]);
  check('RLS is on with no anon policy',
    /enable row level security/.test(sql) &&
    /revoke all on public\.sd_locations from anon, authenticated/.test(sql), true);
  // Asserted on the column list, not the file: the prose above explains at
  // length why no sd_slabs migration is needed, and a file-wide match would hit
  // that explanation. Scrubber item 16 shape A.
  const cols = sql.slice(sql.indexOf('create table if not exists'), sql.indexOf(');', sql.indexOf('create table if not exists')));
  check('the table stores no per-yard slab count -- the rollup is computed',
    /slab_count|slabs_at|inventory_value/.test(cols), false);
}


// ── 6. THE RECONCILE INVARIANT (added 2026-09-03) ──────────────────────────
// Reassigning a slab between yards changes the BUCKETS and must not change the
// GRAND TOTAL. `totals` cannot test that by itself: it is the SUM OF THE ROWS,
// so it agrees with the rows by construction and would still agree after a
// slab had been dropped on the floor. The only check with any force compares
// against what came IN.
//
// Same reason api/_lib/roofing-consolidation.js returns input_total and
// reconciles on every call.
{
  const out = build(world({
    locations: LOCS,
    slabs: [SLAB({ id: 'a', location_id: 'L1' }),
            SLAB({ id: 'b', location_id: 'L2' }),
            SLAB({ id: 'c' })]
  })).rollup();
  check('a healthy rollup reconciles against the slabs it was given',
    [out.reconciles, out.input_total.slabs, out.totals.slabs], [true, 3, 3]);
}
{
  const out = build(world({ locations: LOCS, slabs: [] })).rollup();
  check('an empty shop reconciles rather than reading as broken',
    [out.reconciles, out.input_total.slabs], [true, 0]);
}
{
  // Reassigning moves a slab between buckets and leaves the book alone.
  const before = build(world({ locations: LOCS,
    slabs: [SLAB({ id: 'a', location_id: 'L1', cost: 400 }), SLAB({ id: 'b', location_id: 'L1', cost: 200 })] })).rollup();
  const after = build(world({ locations: LOCS,
    slabs: [SLAB({ id: 'a', location_id: 'L1', cost: 400 }), SLAB({ id: 'b', location_id: 'L2', cost: 200 })] })).rollup();
  check('reassigning changes the buckets and not the grand total',
    [before.totals.slabs === after.totals.slabs,
     before.totals.value === after.totals.value,
     before.rows.filter((r) => r.location_id === 'L2')[0].slabs,
     after.rows.filter((r) => r.location_id === 'L2')[0].slabs,
     before.reconciles && after.reconciles],
    [true, true, 0, 1, true]);
}
{
  // NEGATIVE CONTROL, and the first version of it was worthless -- it computed
  // the comparison in the TEST and asserted on that, so hardcoding
  // `reconciles: true` in the app scored a clean pass. Exactly the mistake this
  // harness already records about stubbing sdLocName.
  //
  // This drives the REAL extracted source with the loss injected INTO it, and
  // asserts on the flag the app actually returns.
  const lossy = new Function('W',
    'var sdSlabs=W.slabs, sdLocations=W.locations;\n' +
    'var slabCost=W.slabCost;\n' +
    'var window={};\n' +
    fnAssign('window.sdLocActive = function()') + '\n' +
    fnAssign('window.sdLocName = function(id)') + '\n' +
    'var sdLocActive=window.sdLocActive, sdLocName=window.sdLocName;\n' +
    // The injected defect: the rollup drops the first slab on the floor.
    fn('window.sdLocRollup = function(){').replace('slabs.forEach(function(s){', 'slabs.slice(1).forEach(function(s){') + '\n' +
    'return window.sdLocRollup();'
  )(world({ locations: LOCS,
            slabs: [SLAB({ id: 'a', location_id: 'L1' }), SLAB({ id: 'b', location_id: 'L1' })] }));
  check('NEGATIVE CONTROL: a rollup that drops a slab returns reconciles:false',
    [lossy.reconciles, lossy.totals.slabs, lossy.input_total.slabs], [false, 1, 2]);
}

check('the panel shows the failure in red rather than a total nobody can reconcile',
  /id="loc-reconcile"/.test(src) && /do not reconcile/i.test(src), true);
// Asserted on the CONDITION, not on the message. A first draft matched only
// the refusal string, and disabling the whole condition while leaving the
// string in place still scored a pass -- the message is not the gate.
check('the write path is management-gated -- an upsert rename relabels every slab pointing at the yard',
  /!locSession \|\| !CRM_MANAGEMENT_ROLES\[locSession\.role\]/.test(api) &&
  /Only an owner or admin can add, rename or close a yard/.test(api), true);
check('locations is session-gated like slabs, and was licence-scoped before',
  /'locations':\s*\['read',\s*'write'\]/.test(api), true);

check('a REFUSED yard write is rolled back locally, not left as a device-only ghost',
  /Only an owner or admin can add a yard -- nothing was saved/.test(src) &&
  /Only an owner or admin can close or reopen a yard -- nothing was changed/.test(src), true);
check('and an OUTAGE is still kept locally -- a refusal and a dead network are different answers',
  /Saved on this device only -- the server has NOT got this yard/.test(src), true);

console.log(fail ? ('FAILED ' + fail + '/' + (pass + fail)) : ('ALL ' + pass + ' YARD ASSERTIONS PASS'));
process.exit(fail ? 1 : 0);
