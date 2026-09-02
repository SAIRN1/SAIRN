// SAIRNsenior payer authorisation unit burn-down, driven verbatim from
// sairnsenior.html.
//
// Competitive-gap audit item A3 ("payer authorisation tracking with unit
// burn-down"). The audit records this as a genuine DIFFERENTIATOR rather than
// catch-up: it was "not found described in any Tier A product".
//
// WHAT WAS ALREADY THERE, VERIFIED BEFORE BUILDING, because the audit's
// "'units' zero" understates it. `senAuthRows()` / `rAuthBurnDown()` already
// existed on the Clients panel and measure against
// `sen_clients.authorized_hours` -- a SINGLE WEEKLY HOURS FIGURE with no
// number, no payer, no period, no expiry and no history. That is a care-plan
// check, not a payer authorisation, and it stays. A test below asserts BOTH
// screens now say which of the two questions they answer, because two tables
// both labelled "authorization" that legitimately disagree is worse than
// either alone.
//
// THE FIVE PROPERTIES THIS FILE EXISTS TO HOLD:
//
//   1. CONSUMPTION IS COMPUTED FROM VISITS AND NEVER STORED. There is no
//      units_used field, the server strips one if a client posts it, and the
//      burn-down is recomputed every render. A stored counter drifts the moment
//      a visit is edited, cancelled or re-clocked, and nothing afterwards can
//      say whether the counter or the visits are right.
//   2. DELIVERED, SCHEDULED AND NEVER-CLOCKED ARE THREE SEPARATE NUMBERS.
//      Delivered counts only real clocked time. Merging still-scheduled visits
//      into it is how a screen reports room that has already been scheduled
//      away. A PAST visit nobody clocked counts toward NEITHER -- scheduling a
//      visit is not evidence it happened -- and is reported as its own number.
//   3. REMAINING IS AGAINST DELIVERED ONLY. Netting off scheduled visits would
//      spend units before the work happened, and a cancellation would hand back
//      units that were never spent.
//   4. AMBIGUITY REFUSES. Two authorisations in force for one client on one
//      date resolve to nothing -- not the newer, not the larger, not the first
//      row. Burning units off an authorisation nobody chose makes the remaining
//      figure wrong on BOTH records at once.
//   5. UNITS ARE CONVERTED EXACTLY AND NO STATE ROUNDING RULE IS INVENTED.
//      Real Medicaid programmes round per visit and the rule differs by state.
//      Picking one would make every figure quietly wrong wherever it does not
//      apply, so none is picked and the panel says so.

const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', '..', 'sairnsenior.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start, open, close) {
  let i = src.indexOf(open, start), depth = 0;
  if (i < 0) throw new Error('no ' + open);
  for (; i < src.length; i++) {
    if (src[i] === open) depth++;
    else if (src[i] === close) { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced');
}
function fn(name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('not found: ' + name);
  return balanced(start, '{', '}');
}
function scalar(name) {
  const m = src.match(new RegExp('var ' + name + '=([^;]+);'));
  if (!m) throw new Error('not found: var ' + name);
  return 'var ' + name + '=' + m[1] + ';';
}

const TODAY = '2026-09-02';

// hrIsDate, hrAddDays and _senHhmmToMin are extracted rather than restubbed --
// the burn-down depends on their exact behaviour, and a stub that was merely
// close would let a real mismatch pass here. senLocalToday is the ONE thing
// stubbed, because a test whose answers change at midnight is not a test.
function build(world) {
  return new Function('W',
    scalar('AZ_UNCOVERED_DAYS') + '\n' +
    'var visits=W.visits, authorizations=W.authorizations;\n' +
    'var senLocalToday=function(){return "' + TODAY + '";};\n' +
    'var fdate=function(d){return String(d||"--");};\n' +
    fn('hrIsDate') + '\n' + fn('hrAddDays') + '\n' + fn('_senHhmmToMin') + '\n' +
    fn('azCovers') + '\n' + fn('azResolve') + '\n' + fn('azUnits') + '\n' +
    fn('azBurnDown') + '\n' + fn('azUncoveredVisits') + '\n' +
    'return { azCovers, azResolve, azUnits, azBurnDown, azUncoveredVisits, AZ_UNCOVERED_DAYS };'
  )(world);
}
function world(o) {
  o = o || {};
  return { visits: () => o.visits || [], authorizations: () => o.auths || [] };
}
// A clocked visit, expressed in real hours so the unit arithmetic is checked
// against something a human can verify by hand.
function clocked(clientId, date, hours) {
  return { id: 'V' + date + clientId + hours, client_id: clientId, status: 'completed', scheduled_date: date,
    clock_in_at: date + 'T09:00:00.000Z',
    clock_out_at: date + 'T' + String(9 + Math.floor(hours)).padStart(2, '0') + ':' + String(Math.round((hours % 1) * 60)).padStart(2, '0') + ':00.000Z' };
}
function booked(clientId, date, start, end) {
  return { id: 'B' + date + clientId + start, client_id: clientId, status: 'scheduled', scheduled_date: date, scheduled_start: start, scheduled_end: end };
}
const AUTH = { id: 'A1', client_id: 'CL1', auth_number: 'MC-771', units_authorized: 100,
  minutes_per_unit: 15, start_on: '2026-08-01', end_on: '2026-10-31', active: true };

// ── 1 & 5. exact conversion, no invented rounding rule ───────────────────
{
  const { azUnits } = build(world());
  check('one hour is four 15-minute units, two 30-minute units, one 60-minute unit',
    [azUnits(1, 15), azUnits(1, 30), azUnits(1, 60)], [4, 2, 1]);
  // 1h50m at 15-minute units is 7.33 units. A state that rounds down would say
  // 7 and one applying an eight-minute rule would say 8. This says the exact
  // figure and the panel says no rounding rule was applied -- a units figure
  // that is confidently wrong is worse than an exact one labelled as unrounded.
  check('a part-unit visit is NOT rounded to a whole unit in either direction',
    azUnits(1 + 50 / 60, 15), 7.33);
  check('an unusable unit basis yields zero rather than dividing by nothing',
    [azUnits(5, 0), azUnits(5, null), azUnits(5, 'quarter-hour')], [0, 0, 0]);
}

// ── 2 & 3. three separate numbers, and remaining is against delivered ─────
{
  // 5 hours delivered (20 units), 2 hours still booked in the future
  // (8 units), and one past visit nobody clocked.
  const W = world({
    auths: [AUTH],
    visits: [
      clocked('CL1', '2026-08-10', 3),
      clocked('CL1', '2026-08-20', 2),
      booked('CL1', '2026-09-10', '09:00', '11:00'),
      { id: 'X1', client_id: 'CL1', status: 'missed', scheduled_date: '2026-08-25', scheduled_start: '09:00', scheduled_end: '13:00' }
    ]
  });
  const b = build(W).azBurnDown(AUTH);
  check('delivered counts only clocked time', b.delivered, 20);
  check('scheduled is counted separately and never folded into delivered', b.scheduled, 8);
  check('a PAST visit nobody clocked counts toward neither and is reported on its own',
    [b.unclocked_past, b.delivered + b.scheduled], [1, 28]);
  check('remaining is against DELIVERED only, so a booking has not spent units yet',
    b.remaining, 80);
  check('projected is delivered plus scheduled, kept as its own figure', b.projected, 28);
  check('nothing is stored back on the authorisation -- the input object is untouched',
    Object.keys(AUTH).sort(), ['active', 'auth_number', 'client_id', 'end_on', 'id', 'minutes_per_unit', 'start_on', 'units_authorized']);
}
{
  // Cancelling a booked visit must not hand back units, because none were
  // spent. Same world as above with the future booking removed.
  const withBooking = build(world({ auths: [AUTH], visits: [clocked('CL1', '2026-08-10', 3), booked('CL1', '2026-09-10', '09:00', '11:00')] })).azBurnDown(AUTH);
  const without = build(world({ auths: [AUTH], visits: [clocked('CL1', '2026-08-10', 3)] })).azBurnDown(AUTH);
  check('cancelling a future booking changes scheduled and leaves remaining alone',
    [withBooking.remaining, without.remaining, withBooking.scheduled, without.scheduled],
    [88, 88, 8, 0]);
}
{
  // Visits outside the authorisation period belong to no part of its figures --
  // that is the whole difference between a period authorisation and the weekly
  // hours figure it replaces.
  const b = build(world({ auths: [AUTH], visits: [
    clocked('CL1', '2026-07-31', 4),   // day before it starts
    clocked('CL1', '2026-08-01', 1),   // first day, inclusive
    clocked('CL1', '2026-10-31', 1),   // last day, inclusive
    clocked('CL1', '2026-11-01', 4)    // day after it ends
  ] })).azBurnDown(AUTH);
  check('the period is inclusive at both ends and excludes everything outside it',
    b.delivered, 8);
}
{
  // Another client's visits are not this client's consumption.
  const b = build(world({ auths: [AUTH], visits: [clocked('CL1', '2026-08-10', 1), clocked('CL2', '2026-08-10', 10)] })).azBurnDown(AUTH);
  check('a different client\'s visits do not burn this authorisation', b.delivered, 4);
}
{
  // An unusable scheduled time is skipped and COUNTED, not silently dropped.
  const b = build(world({ auths: [AUTH], visits: [
    { id: 'U1', client_id: 'CL1', status: 'scheduled', scheduled_date: '2026-09-10', scheduled_start: 'morning', scheduled_end: 'noon' },
    { id: 'U2', client_id: 'CL1', status: 'scheduled', scheduled_date: '2026-09-10', scheduled_start: '13:00', scheduled_end: '11:00' }
  ] })).azBurnDown(AUTH);
  check('visits with unusable or inverted times are skipped and reported, not dropped in silence',
    [b.unparsed, b.scheduled], [2, 0]);
}
{
  // A clock-out before the clock-in is not negative delivered time. It falls
  // through to the scheduled/unclocked branches like any unusable clock.
  const b = build(world({ auths: [AUTH], visits: [
    { id: 'N1', client_id: 'CL1', status: 'completed', scheduled_date: '2026-08-10',
      clock_in_at: '2026-08-10T11:00:00.000Z', clock_out_at: '2026-08-10T09:00:00.000Z',
      scheduled_start: '09:00', scheduled_end: '11:00' }
  ] })).azBurnDown(AUTH);
  check('an inverted clock pair never produces negative delivered units',
    [b.delivered, b.unclocked_past], [0, 1]);
}

// ── 4. resolution: applied | none | ambiguous ────────────────────────────
{
  const { azResolve, azCovers } = build(world({ auths: [AUTH] }));
  check('a date inside the period resolves to the authorisation',
    [azResolve('CL1', '2026-09-01').status, azResolve('CL1', '2026-09-01').auth_number], ['applied', 'MC-771']);
  check('both ends of the period are inclusive',
    [azCovers(AUTH, '2026-08-01'), azCovers(AUTH, '2026-10-31')], [true, true]);
  check('a date outside the period does not resolve, and says the client HAS authorisations',
    [azResolve('CL1', '2026-11-05').status, /none covering 2026-11-05/.test(azResolve('CL1', '2026-11-05').reason)], ['none', true]);
  check('a client with nothing on file is told that, not told the date was wrong',
    /No authorisation is on file for this client/.test(azResolve('CL2', '2026-09-01').reason), true);
  check('an inactive authorisation covers nothing',
    azCovers(Object.assign({}, AUTH, { active: false }), '2026-09-01'), false);
  check('a visit with no service date is refused for that reason',
    /no service date/.test(azResolve('CL1', '').reason), true);
  check('a visit naming no client is refused for that reason',
    /names no client/.test(azResolve('', '2026-09-01').reason), true);
  check('an authorisation with an unreadable period covers nothing',
    [azCovers(Object.assign({}, AUTH, { end_on: '31/10/2026' }), '2026-09-01'),
     azCovers(Object.assign({}, AUTH, { start_on: '' }), '2026-09-01')], [false, false]);
}
{
  const A2 = Object.assign({}, AUTH, { id: 'A2', auth_number: 'MC-990', units_authorized: 40, start_on: '2026-08-15' });
  const { azResolve } = build(world({ auths: [AUTH, A2] }));
  const r = azResolve('CL1', '2026-09-01');
  check('two authorisations in force for one client on one date do not resolve', r.status, 'ambiguous');
  check('no authorisation is carried on an ambiguous result -- not the newer, not the larger',
    [r.auth_id, r.auth_number], [undefined, undefined]);
  check('both candidates are named so the overlap can be fixed',
    (r.candidates || []).map((c) => c.id).sort(), ['A1', 'A2']);
  check('the reason states why picking one would be wrong on BOTH records',
    /wrong on both at once/.test(r.reason), true);
  // Marking one inactive resolves it -- the fix the message names is asserted
  // to be the fix that works.
  const fixed = build(world({ auths: [AUTH, Object.assign({}, A2, { active: false })] })).azResolve('CL1', '2026-09-01');
  check('marking one inactive resolves the overlap, as the message instructs',
    [fixed.status, fixed.auth_number], ['applied', 'MC-771']);
}

// ── the dangerous case: delivered care with nothing covering it ──────────
{
  const W = world({
    auths: [AUTH],
    visits: [
      clocked('CL1', '2026-08-10', 2),   // covered
      clocked('CL2', '2026-08-10', 2),   // client has no authorisation at all
      clocked('CL1', '2026-07-15', 2),   // before the period, inside the 90-day window
      clocked('CL1', '2026-01-05', 2)    // outside the 90-day window
    ]
  });
  const { azUncoveredVisits, AZ_UNCOVERED_DAYS } = build(W);
  check('the lookback window is declared rather than implied', AZ_UNCOVERED_DAYS, 90);
  check('completed visits with no covering authorisation are found, and only inside the window',
    azUncoveredVisits().map((v) => v.client_id + '@' + v.scheduled_date).sort(),
    ['CL1@2026-07-15', 'CL2@2026-08-10']);
  // A scheduled visit is not yet care delivered without authorisation, and
  // flagging it would make the count a forecast rather than a finding.
  const withBooking = build(world({ auths: [AUTH], visits: [booked('CL2', '2026-09-20', '09:00', '11:00')] }));
  check('a future BOOKING is not reported as care delivered without authorisation',
    withBooking.azUncoveredVisits().length, 0);
}
{
  // An ambiguous resolution is uncovered too: nothing was applied, so nothing
  // authorised it. Treating ambiguous as covered would hide the overlap behind
  // a clean count.
  const A2 = Object.assign({}, AUTH, { id: 'A2', auth_number: 'MC-990' });
  const u = build(world({ auths: [AUTH, A2], visits: [clocked('CL1', '2026-08-10', 2)] })).azUncoveredVisits();
  check('a visit whose authorisation is ambiguous counts as uncovered, not as covered', u.length, 1);
}

// ── the panel exists and is reachable ────────────────────────────────────
// Fifteen of these on the Contracts build caught a resolver shipped with no
// markup at all -- pcRender was null-guarded on every element, so the nav
// button opened a blank screen in silence rather than throwing. Same shape
// here, same assertions.
['panel-authorizations', 'azmodal', 'az-tbody', 'az-denied', 'az-content', 'az-warnings',
 'az-notes-line', 'az-add-btn', 'az-modal-title', 'az-client', 'az-number', 'az-code',
 'az-units', 'az-basis', 'az-start', 'az-end', 'az-active', 'az-notes'].forEach((id) => {
  check('the DOM node #' + id + ' that the code reads actually exists', new RegExp('id="' + id + '"').test(src), true);
});
check('the panel is wired into nav', /if\(id==='authorizations'\)azRender\(\);/.test(src), true);
check('the sidebar button exists and points at it', /id="sb-authorizations" onclick="nav\('authorizations'\)"/.test(src), true);
check('something on screen opens the modal', /onclick="openAzModal\(\)"/.test(src), true);
check('the table header has a cell for every column the row renders, and the empty state spans them all',
  [(src.match(/<th>Client<\/th><th>Payer<\/th><th>Auth #<\/th>/) || []).length, /colspan="12"/.test(src)], [1, true]);

// ── the two burn-downs each say which question they answer ──────────────
// ASSERTED ON THE RENDERED HEADING, NOT ON THE FILE. Written first as
// `!/Authorization Burn-Down/.test(src)` and it failed -- on the two comments
// that exist to EXPLAIN the rename, one in the markup and one above azResolve.
// Scrubber item 16 shape A, twice in one file: a prose match tripping on the
// commentary about the thing it is checking for.
check('the weekly care-plan table no longer calls itself an authorization burn-down',
  [/<span class="ct">Care-Plan Hours &mdash; this week<\/span>/.test(src),
   /<span class="ct">Authorization Burn-Down/.test(src)], [true, false]);
check('and it says out loud that it is NOT the payer authorisation, naming where that lives',
  /not the payer authorisation<\/strong>/.test(src) && /on the <strong>Authorisations<\/strong> panel/.test(src), true);
check('the new panel states that no state rounding rule is applied',
  /No state-specific per-visit rounding rule is applied<\/strong>/.test(src), true);
check('and that the service code is recorded but nothing is matched on it',
  /nothing is matched on it<\/strong>/.test(src), true);

// ── the claim carries the authorisation that was in force that day ──────
check('generateClaim resolves the authorisation against the SERVICE date',
  /var auth=azResolve\(v\.client_id,v\.scheduled_date\);/.test(src), true);
check('the authorisation number is STORED on the claim, for an appeal filed weeks later',
  /auth_status:auth\.status,auth_note:auth\.reason\|\|''/.test(src) &&
  /auth_number:auth\.status==='applied'\?auth\.auth_number:''/.test(src), true);
check('where the contract requires prior authorisation, the claim says whether one actually applies',
  /PRIOR AUTHORISATION IS REQUIRED AND NONE APPLIES/.test(src), true);
check('an exhausted or overdrawn authorisation is called out at the moment the claim is made',
  /That authorisation is OVER by/.test(src) && /has no units left as of today/.test(src), true);
check('the claims table shows the stamped authorisation, guarded so historical claims show nothing',
  /c\.auth_status==='applied'&&c\.auth_number/.test(src) &&
  /else if\(c\.auth_status&&c\.auth_status!=='applied'\)/.test(src), true);
check('Billing hydrates authorisations alongside claims and contracts',
  /Promise\.all\(\[senHydrateClaims\(\),senHydratePayerContracts\(\),senHydrateAuthorizations\(\)\]\)/.test(src), true);
check('saving repaints without hydrating -- a hydrate racing the write would undo the edit',
  /closeAzModal\(\);azPaint\(\);/.test(src), true);
check('hydration replaces the local row rather than only adding unseen ones',
  /function senHydrateAuthorizations\(\)/.test(src) &&
  /JSON\.stringify\(byId\[a\.id\]\)!==JSON\.stringify\(a\)/.test(src), true);
check('a scheduler can read the burn-down and is not shown a write button that would 403',
  /if\(add\)add\.style\.display=senIsManagement\(\)\?'':'none';/.test(src), true);
// ASSERTED ON EXTRACTED CODE, NOT ON A WINDOW OF THE FILE -- same reason as
// the heading check above. The only `units_used` in sairnsenior.html is the
// comment saying there isn't one.
check('no authorisation code path reads or writes a used-units counter',
  /units_used/.test([fn('azBurnDown'), fn('azResolve'), fn('azCovers'), fn('azUnits'),
                     fn('saveAuthorization'), fn('openAzModal'), fn('azPaint'),
                     fn('senHydrateAuthorizations')].join('\n')), false);

// ── the browser refusals ─────────────────────────────────────────────────
check('the browser refuses a zero or negative unit count', /if\(!\(units>0\)\)\{toast\(/.test(src), true);
check('the browser requires BOTH dates, unlike a contract\'s open-ended term',
  /if\(!start\|\|!end\)\{toast\(/.test(src), true);
check('the browser refuses an end before the start', /if\(end<start\)\{toast\(/.test(src), true);
check('the browser requires an authorisation number', /The authorisation number is required/.test(src), true);

// ── the server refusals, which are not the same as the browser's ────────
{
  const api = fs.readFileSync(path.join(__dirname, '..', 'sd-data.js'), 'utf8');
  check('the read gate is the broad-read tier -- a scheduler needs remaining units before booking',
    /Authorisations are limited to management, coordinators and schedulers/.test(api) &&
    /if \(!SEN_CLIENT_BROAD_READ_ROLES\[session\.role\]\) \{[\s\S]{0,200}Authorisations are limited/.test(api), true);
  check('the write gate is management-only, and it is a SPLIT gate not a single one',
    /Only management can record or change an authorisation/.test(api) &&
    /if \(!senAuth\.MANAGEMENT_ROLES\[session\.role\]\) \{[\s\S]{0,160}Only management can record or change an authorisation/.test(api), true);
  check('the server refuses zero units', /units_authorized must be greater than zero/.test(api), true);
  check('the server refuses a unit basis it cannot divide by',
    /minutes_per_unit must be 15, 30 or 60/.test(api) &&
    /\[15, 30, 60\]\.indexOf\(Number\(payload\.minutes_per_unit\)\) < 0/.test(api), true);
  check('the server requires both dates and refuses an inverted period',
    /start_on must be YYYY-MM-DD/.test(api) && /end_on must be YYYY-MM-DD/.test(api) &&
    /end_on is before start_on/.test(api), true);
  check('the server requires a client and an authorisation number',
    /client_id is required/.test(api) && /auth_number is required/.test(api), true);
  // The one that matters most: a client could otherwise post its own
  // units_used, have it stored, and have the next device read it back looking
  // exactly like a figure the server computed.
  check('the server STRIPS a client-supplied units_used rather than storing it',
    /delete azBody\.units_used;/.test(api), true);
  check('an unprovisioned table says so instead of reporting a successful write',
    /run sql\/sairnsenior_authorizations_schema\.sql in Supabase first/.test(api), true);
  check('the resource is registered',
    /'sen_authorizations'/.test(fs.readFileSync(path.join(__dirname, '..', '_resources', 'sairnsenior.js'), 'utf8')), true);
}

{
  const sql = fs.readFileSync(path.join(__dirname, '..', '..', 'sql', 'sairnsenior_authorizations_schema.sql'), 'utf8');
  const grants = sql.split(/\r?\n/).filter((l) => /^\s*grant\b/i.test(l));
  check('the schema exists and no grant confers delete -- a finished authorisation is the record an appeal needs',
    [/create table if not exists public\.sen_authorizations/.test(sql), grants.some((l) => /\bdelete\b/i.test(l))],
    [true, false]);
  check('RLS is on and there is no anon policy',
    /enable row level security/.test(sql) && /revoke all on public\.sen_authorizations from anon, authenticated/.test(sql), true);
  // Asserted against the column list, not against the prose -- this file's own
  // commentary explains at length why there is no units_used column, and a
  // regex over the whole file would match that explanation. Scrubber item 16,
  // shape A.
  const cols = sql.slice(sql.indexOf('create table if not exists'), sql.indexOf(');', sql.indexOf('create table if not exists')));
  check('the table has no units_used column', /units_used/.test(cols), false);
}

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
