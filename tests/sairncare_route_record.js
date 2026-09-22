// tests/sairncare_route_record.js
//
// What alf_claim_routes is allowed to record, and what a failed write is
// allowed to CLAIM. Both halves are about the same thing: a Tier A,
// append-only, no-delete-grant billing table must never hold a sentence
// nobody established.
//
// ── IT RUNS THE SHIPPED FUNCTIONS, NOT A COPY OF THEM ──────────────────────
// Every function under test is lifted out of sairncare.html by LINE RANGE at
// run time. A restated copy would keep passing after the real file changed,
// which on this platform is the failure mode that outlives every other one. If
// an anchor stops matching this file THROWS rather than skipping: a probe that
// silently tests nothing is worse than one that is red.
//
// NO REGEX OVER THE WHOLE FILE. sairncare.html is ~1MB and a `[\s\S]*?` across
// it backtracks for minutes; the first attempt at this extraction had to be
// killed. Lines, a start anchor, and a closing `}` in column zero.
//
// ── WHY THE ARMS DRIVE alfRoute() RATHER THAN HAND-WRITTEN BODIES ──────────
// The defect this suite exists for was NOT a wrong condition read in
// isolation. alfRouteRecordable()'s three codes were correct for the three
// codes alfRoute() mints, and the bug was that alfRoute handed it bodies it
// had never minted -- four shapes straight from api/sd-data.js. An arm that
// constructs the body it expects can never see that class of defect, so every
// end-to-end arm below feeds a REAL sd-data response through the REAL
// alfRoute and asks alfRouteRecordable about whatever comes out.
// DELIBERATELY NOT 'use strict'. The functions under test are lifted out of
// sairncare.html and brought into this scope by a DIRECT eval, and a strict
// eval gets its own scope -- the extraction would run, define nothing, and
// every arm would die on "alfRoute is not defined". Non-strict direct eval
// puts them in this module's scope, which is the whole point.
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'sairncare.html');
const LINES = fs.readFileSync(APP, 'utf8').split('\n');

function grab(anchor) {
  const hits = [];
  for (let i = 0; i < LINES.length; i++) if (LINES[i].startsWith(anchor)) hits.push(i);
  if (hits.length !== 1) {
    throw new Error('ANCHOR-' + hits.length + ' for ' + JSON.stringify(anchor) +
      ' in sairncare.html -- this suite is not testing what it says it tests. ' +
      'Fix the anchor, do not delete the arm.');
  }
  const start = hits[0];
  for (let j = start; j < LINES.length; j++) {
    if (LINES[j] === '}') return LINES.slice(start, j + 1).join('\n');
    if (LINES[j].endsWith(';') && LINES[j].startsWith('var ')) return LINES[j];
  }
  throw new Error('no closing brace found after ' + JSON.stringify(anchor));
}

// ── The environment the shipped functions expect ───────────────────────────
// Everything a browser would supply, and nothing more. DATA_API and APP_ID are
// only ever used as opaque values by the code under test.
const DATA_API = 'https://example.invalid/api/sd-data';
const APP_ID = 'sairncare';
const ALF_FETCH_TIMEOUT_MS = 15000;
let alfSession = null;
let LICENCE = 'ALF-TEST';
function alfLicenseKey() { return LICENCE; }
function alfFetchTimeoutSignal() { return undefined; }
const console_warn = console.warn;
console.warn = function () {};                 // the code under test is chatty by design

let NEXT = null;                               // what the stub `fetch` should do
global.fetch = function () {
  const n = NEXT;
  if (!n) return Promise.reject(new Error('no response queued'));
  if (n.throws) return Promise.reject(n.throws);
  return Promise.resolve({
    ok: n.status >= 200 && n.status < 300,
    status: n.status,
    json: function () {
      if (n.unparseable) return Promise.reject(new SyntaxError('Unexpected token <'));
      return Promise.resolve(n.body);
    }
  });
};

const SRC = [
  grab('var alfLastOutcome={}'),
  grab('function alfNote('),
  grab('function alfWriteVerdict('),
  grab('function alfLastErrText('),
  grab('function alfNotProvisioned('),
  grab('function alfData('),
  grab('function alfRoute('),
  grab('function alfRouteRecordable('),
  grab('function alfRouteOutcome('),
  grab('async function alfRecordRoute('),
  // GRABBED, NOT STUBBED (2026-09-22). prRenderRecorded now renders the trail's
  // server timestamp through fstamp() instead of a date-only slice, because two
  // determinations recorded the same day rendered identically and the refusal
  // message promises the reader can tell which is later. Stubbing it here would
  // make this suite blind to the exact thing that change was for -- section 8
  // asserts the rendered timestamp carries a time, and it can only do that
  // against the real helper.
  grab('function fstamp('),
  grab('async function prRenderRecorded(')
].join('\n');
// Everything alfRecordRoute() and prRenderRecorded() reach for that belongs to
// the browser or to the rest of the app. Declared as `var` so the direct eval
// above can see them and sections 7 and 8 can replace them. prRenderRecorded
// is a `var` too: section 7 stubs it to a counter, section 8 restores the real
// one that the eval defined.
var alfLastRoute = null, alfIsManagement, toast, prRenderRecorded, $, residents, H;
eval(SRC);                                     // eslint-disable-line no-eval

let failed = 0;
function ok(name, cond, detail) {
  if (cond) { console_warn('  ok   ' + name); return; }
  failed++;
  console_warn('  FAIL ' + name + (detail ? '  ' + detail : ''));
}
function section(s) { console_warn('\n' + s); }

// ── THE NINE BODIES api/sd-data.js's route branch CAN ACTUALLY RETURN ──────
// Copied from the branch itself (api/sd-data.js, `alf_payer_rules` + 'route'),
// not invented. The `judged` column is the fact every arm turns on: did the
// ENGINE answer, or did somebody else refuse before it ran.
const ROUTE_RESPONSES = [
  { name: '200 routed -- a payer decision', judged: true,
    r: { status: 200, body: { payer: 'FFS Medicare', why: 'x' } } },
  { name: '200 routed -- provider_choice', judged: true,
    r: { status: 200, body: { decision: 'provider_choice', options: [] } } },
  { name: '200 engine refusal NO_RULE_FOR_STATE', judged: true,
    r: { status: 200, body: { ok: false, error: { code: 'NO_RULE_FOR_STATE', message: 'not covered' } } } },
  { name: '200 engine refusal DX_MATCH_WOULD_DENY', judged: true,
    r: { status: 200, body: { ok: false, error: { code: 'DX_MATCH_WOULD_DENY', message: 'x' } } } },
  { name: '401 NO_SESSION', judged: false,
    r: { status: 401, body: { error: { code: 'NO_SESSION', message: 'Sign in first' } } } },
  { name: '403 FORBIDDEN', judged: false,
    r: { status: 403, body: { error: { code: 'FORBIDDEN', message: 'Only management can route a claim' } } } },
  { name: '503 NOT_PROVISIONED', judged: false,
    r: { status: 503, body: { error: { code: 'NOT_PROVISIONED', message: 'Billing rules are not set up yet' } } } },
  // THE ONE THAT WROTE THE ROW. upstream() answers 502 with a body carrying a
  // message and NO CODE AT ALL, so the old deny-list read '' and matched none
  // of its three entries.
  { name: '502 upstream() -- body carries NO code', judged: false,
    r: { status: 502, body: { error: { message: 'Data store error — try again' } } } },
  { name: '400 route requires program and service_month', judged: false,
    r: { status: 400, body: { error: { message: 'route requires program and service_month' } } } }
];

async function main() {
  section('1. alfRoute() stamps HTTP_<status> on EVERY non-200, and leaves a 200 alone');
  for (const c of ROUTE_RESPONSES) {
    NEXT = c.r;
    const out = await alfRoute({ program: 'medicaid_hcbs', service_month: '2026-09' });
    const code = (out && out.error && out.error.code) || '';
    if (c.r.status === 200) {
      ok(c.name + ' -- passes through untouched',
        JSON.stringify(out) === JSON.stringify(c.r.body), 'got ' + JSON.stringify(out));
    } else {
      ok(c.name + ' -- arrives as HTTP_' + c.r.status,
        code === 'HTTP_' + c.r.status, 'got code ' + JSON.stringify(code));
    }
  }
  NEXT = ROUTE_RESPONSES[6].r;
  const provMsg = await alfRoute({});
  ok("...and the server's own message survives the stamping",
    /not set up yet/.test((provMsg.error && provMsg.error.message) || ''),
    JSON.stringify(provMsg));

  NEXT = { status: 200, unparseable: true };
  const badBody = await alfRoute({});
  ok('an unparseable body is BAD_RESPONSE',
    badBody.error.code === 'BAD_RESPONSE', JSON.stringify(badBody));
  NEXT = { throws: new Error('ECONNREFUSED') };
  const netErr = await alfRoute({});
  ok('a dead connection is NETWORK', netErr.error.code === 'NETWORK', JSON.stringify(netErr));

  section('2. END TO END: only an answer the ENGINE gave is recordable');
  for (const c of ROUTE_RESPONSES) {
    NEXT = c.r;
    const out = await alfRoute({ program: 'medicaid_hcbs', service_month: '2026-09' });
    const rec = alfRouteRecordable(out, 'RES-1', '2026-09');
    ok((c.judged ? 'recordable:     ' : 'NOT recordable: ') + c.name,
      rec === c.judged, 'recordable=' + rec);
  }
  for (const [label, next] of [['BAD_RESPONSE', { status: 200, unparseable: true }],
                               ['NETWORK', { throws: new Error('x') }]]) {
    NEXT = next;
    const out = await alfRoute({});
    ok('NOT recordable: ' + label, alfRouteRecordable(out, 'RES-1', '2026-09') === false);
  }

  section('3. the consumer defends itself even if the producer regresses');
  // Both arms hand alfRouteRecordable a body alfRoute can no longer mint. They
  // are the guard against ONE edit to alfRoute reopening the hole, which is
  // exactly how it was open in the first place.
  ok('an error with NO code is refused on its own merits -- the 502 shape',
    alfRouteRecordable({ error: { message: 'Data store error' } }, 'RES-1', '2026-09') === false);
  ok('...and so is ok:false with no code at all',
    alfRouteRecordable({ ok: false, error: {} }, 'RES-1', '2026-09') === false);
  ok('a raw NO_SESSION body, unstamped, is NOT silently recordable... ',
    alfRouteRecordable({ error: { code: 'NO_SESSION' } }, 'RES-1', '2026-09') === true,
    'KNOWN AND DELIBERATE: with alfRoute stamping, this body cannot occur. ' +
    'Pinned so the day somebody adds an allow-list this arm tells them it changed.');

  section('4. the preconditions still hold -- no resident, no month, no result');
  NEXT = ROUTE_RESPONSES[0].r;
  const routed = await alfRoute({});
  ok('no resident_id  -> not recordable', alfRouteRecordable(routed, '', '2026-09') === false);
  ok('no service_month -> not recordable', alfRouteRecordable(routed, 'RES-1', '') === false);
  ok('no result at all -> not recordable', alfRouteRecordable(null, 'RES-1', '2026-09') === false);
  ok('outcome labels a refusal', alfRouteOutcome({ ok: false, error: { code: 'X' } }) === 'refused');
  ok('outcome labels a routed result', alfRouteOutcome({ payer: 'FFS' }) === 'routed');

  section('5. alfData(): WROTE / MISSED / UNKNOWN, three answers and not two');
  const VERDICTS = [
    ['200 ok:true            -> WROTE  ', { status: 200, body: { ok: true, data: { id: 'ROUTE-1' } } }, 'WROTE'],
    ['200 carrying ok:false  -> MISSED ', { status: 200, body: { ok: false, error: { code: 'X', message: 'no' } } }, 'MISSED'],
    ['400 bad payload        -> MISSED ', { status: 400, body: { error: { message: 'requires id' } } }, 'MISSED'],
    ['401 no session         -> MISSED ', { status: 401, body: { error: { code: 'NO_SESSION' } } }, 'MISSED'],
    ['403 wrong role         -> MISSED ', { status: 403, body: { error: { code: 'FORBIDDEN' } } }, 'MISSED'],
    ['409 already recorded   -> MISSED ', { status: 409, body: { error: { code: 'ALREADY_RECORDED' } } }, 'MISSED'],
    // THE SPLIT AT 500. A 4xx is the server reading the request and refusing
    // it; a 5xx is something failing along a request that was already
    // accepted, and whether the row landed is not established.
    ['502 store error        -> UNKNOWN', { status: 502, body: { error: { message: 'Data store error' } } }, 'UNKNOWN'],
    ['503 not provisioned    -> UNKNOWN', { status: 503, body: { error: { code: 'NOT_PROVISIONED' } } }, 'UNKNOWN'],
    ['unparseable 2xx body   -> UNKNOWN', { status: 200, unparseable: true }, 'UNKNOWN'],
    ['dead connection        -> UNKNOWN', { throws: new Error('ECONNREFUSED') }, 'UNKNOWN']
  ];
  for (const [label, next, want] of VERDICTS) {
    NEXT = next;
    await alfData('write', 'alf_claim_routes', { id: 'x' }, true);
    const got = alfWriteVerdict('alf_claim_routes');
    ok(label, got === want, 'got ' + got);
  }

  // THE ONE THE WHOLE FIX IS FOR. A 15s AbortSignal.timeout rejects with an
  // AbortError/TimeoutError, and the row may well have landed -- so the answer
  // must be UNKNOWN and the caller must not be told "Nothing was saved".
  const abort = new Error('The operation was aborted');
  abort.name = 'TimeoutError';
  NEXT = { throws: abort };
  await alfData('write', 'alf_claim_routes', { id: 'x' }, true);
  ok('A 15s TIMEOUT is UNKNOWN, never MISSED -- the write may have landed',
    alfWriteVerdict('alf_claim_routes') === 'UNKNOWN');
  ok('...and it says so in words the toast can use',
    /No answer in 15s/.test(alfLastErrText('alf_claim_routes')),
    JSON.stringify(alfLastErrText('alf_claim_routes')));

  LICENCE = '';
  await alfData('write', 'alf_claim_routes', { id: 'x' }, true);
  ok('no licence: nothing was SENT, so MISSED is a fact rather than a guess',
    alfWriteVerdict('alf_claim_routes') === 'MISSED');
  LICENCE = 'ALF-TEST';

  ok('a resource nobody has asked anything is UNKNOWN, not WROTE and not MISSED',
    alfWriteVerdict('alf_resource_never_touched') === 'UNKNOWN');

  section('6. provisioned:false is the server saying the TABLE IS NOT THERE');
  NEXT = { status: 200, body: { ok: true, data: [], provisioned: false } };
  const emptyUnprov = await alfData('read', 'alf_claim_routes', {}, true);
  ok('the read still returns [] -- the 31 callers are unchanged',
    Array.isArray(emptyUnprov) && emptyUnprov.length === 0);
  ok('...and the flag is no longer thrown away',
    alfNotProvisioned('alf_claim_routes') === true);

  NEXT = { status: 200, body: { ok: true, data: [], provisioned: true } };
  await alfData('read', 'alf_claim_routes', {}, true);
  ok('a genuinely EMPTY provisioned table is NOT reported as unprovisioned',
    alfNotProvisioned('alf_claim_routes') === false);

  NEXT = { status: 200, body: { ok: true, data: [] } };
  await alfData('read', 'alf_other', {}, true);
  ok('a branch that does not report the flag is NOT reported as unprovisioned',
    alfNotProvisioned('alf_other') === false);

  NEXT = { status: 500, body: { error: { message: 'x' } } };
  await alfData('read', 'alf_refused', {}, true);
  ok('a REFUSED read is not reported as unprovisioned either',
    alfNotProvisioned('alf_refused') === false);

  section('7. alfRecordRoute(): what the biller is TOLD, and what they are offered');
  // The load-bearing half of the UNKNOWN fix is not the wording, it is the
  // BUTTON. Re-enabling it under "Nothing was saved" offers the one action
  // that can do harm -- a retry mints a new Date.now() id, so the 409 that
  // would catch a repeat never fires and the append-only table takes a second
  // row for one determination. prRenderRecorded() is stubbed to a counter:
  // this asserts it is CALLED on both branches, which is the other half.
  alfLastRoute = { res: { payer: 'FFS Medicare' }, inputs: { program: 'hospice_ma' },
                   resident_id: 'RES-1', service_month: '2026-09', program: 'hospice_ma' };
  let BTN = null, TOASTS = [], RENDERS = 0;
  const REAL_RENDER = prRenderRecorded;    // section 8 puts the real one back
  alfIsManagement = function () { return true; };
  toast = function (m) { TOASTS.push(m); };
  prRenderRecorded = function () { RENDERS++; };
  $ = function (id) { return id === 'pr-record-btn' ? BTN : null; };
  async function press(next) {
    BTN = { disabled: false, textContent: 'Record this determination' };
    TOASTS = []; RENDERS = 0;
    NEXT = next;
    await alfRecordRoute();
    return { btn: BTN, toast: TOASTS.join(' '), renders: RENDERS };
  }

  const wrote = await press({ status: 200, body: { ok: true, data: { id: 'x' } } });
  ok('WROTE: the button says Recorded and stays disabled',
    wrote.btn.textContent === 'Recorded' && wrote.btn.disabled === true, JSON.stringify(wrote.btn));
  ok('WROTE: the trail is re-read', wrote.renders === 1);

  const missed = await press({ status: 403, body: { error: { code: 'FORBIDDEN', message: 'Billing is not available to your role' } } });
  ok('MISSED: the button IS offered again -- retrying a refusal is safe',
    missed.btn.disabled === false && missed.btn.textContent === 'Record this determination',
    JSON.stringify(missed.btn));
  ok('MISSED: the toast says refused and Nothing was saved',
    /refused/.test(missed.toast) && /Nothing was saved/.test(missed.toast), missed.toast);
  ok("MISSED: it quotes the server's own reason rather than guessing one",
    /Billing is not available to your role/.test(missed.toast), missed.toast);

  const timeout = new Error('aborted'); timeout.name = 'TimeoutError';
  const unknown = await press({ throws: timeout });
  ok('UNKNOWN: the button is NOT re-enabled -- the retry is the harmful action',
    unknown.btn.disabled === true, JSON.stringify(unknown.btn));
  ok('UNKNOWN: and it does not still read "Recording…"',
    /NOT CONFIRMED/.test(unknown.btn.textContent), JSON.stringify(unknown.btn.textContent));
  ok('UNKNOWN: the toast says UNKNOWN and never "Nothing was saved"',
    /UNKNOWN/.test(unknown.toast) && !/Nothing was saved/.test(unknown.toast), unknown.toast);
  ok('UNKNOWN: it names the specific harm of pressing again -- a SECOND row',
    /SECOND row/.test(unknown.toast), unknown.toast);
  ok('UNKNOWN: the trail is re-read too, so the screen answers what the toast cannot',
    unknown.renders === 1);

  const store5xx = await press({ status: 502, body: { error: { message: 'Data store error' } } });
  ok('a 5xx on the WRITE is UNKNOWN as well, and holds the button the same way',
    store5xx.btn.disabled === true && /UNKNOWN/.test(store5xx.toast), store5xx.toast);

  section('8. prRenderRecorded(): four states, and NEVER MIGRATED is its own');
  // Section 6 proves alfNotProvisioned() answers correctly. This proves the
  // TRAIL ASKS IT -- a helper nothing consults is the same silence with an
  // extra function in it.
  prRenderRecorded = REAL_RENDER;
  const BOX = { innerHTML: null };
  $ = function (id) { return id === 'pr-recorded' ? BOX : null; };
  residents = function () { return [{ id: 'RES-1', name: 'A. Resident' }]; };
  H = function (s) { return String(s === undefined || s === null ? '' : s); };
  async function render(next) { BOX.innerHTML = null; NEXT = next; await prRenderRecorded(); return BOX.innerHTML; }

  const unprov = await render({ status: 200, body: { ok: true, data: [], provisioned: false } });
  ok('NEVER MIGRATED says the table does not exist and names the migration',
    /NOT SET UP/.test(unprov) && /sairncare_payer_rules_schema\.sql/.test(unprov), unprov);
  ok('...and it does NOT tell the biller to press a button that cannot work',
    !/press <b>Record this determination<\/b>/.test(unprov), unprov);

  const genuinelyEmpty = await render({ status: 200, body: { ok: true, data: [], provisioned: true } });
  ok('GENUINELY EMPTY still says so, and still points at the button',
    /has been recorded yet/.test(genuinelyEmpty) && !/NOT SET UP/.test(genuinelyEmpty), genuinelyEmpty);

  const refused = await render({ status: 403, body: { error: { code: 'FORBIDDEN' } } });
  ok('REFUSED is neither of the two -- "NOT an empty list"',
    /could not be read/.test(refused) && /NOT an empty list/.test(refused), refused);

  const rows = await render({ status: 200, body: { ok: true, provisioned: true,
    data: [{ resident_id: 'RES-1', service_month: '2026-09', outcome: 'refused',
             decided_by: 'EMP-9', created_at: '2026-09-19T10:00:00Z' }] } });
  ok('A REAL TRAIL renders the row, resolves the resident and labels the outcome',
    /A\. Resident/.test(rows) && /not routed/.test(rows) && /2026/.test(rows), rows);

  // ── THE TRAIL'S TIMESTAMP MUST CARRY A TIME, NOT ONLY A DATE (2026-09-22) ──
  // The 409 below promises the trail shows "both, with the later one as what is
  // believed now". This column rendered `String(created_at).slice(0,10)`, so two
  // determinations recorded the SAME DAY carried identical text and the reader
  // could not tell which was later even with both in front of them. Ordering the
  // server read fixes the sequence; this is what makes the sequence legible.
  //
  // ASSERTED AS A CLOCK COMPONENT, NOT AS A LITERAL STRING. fstamp() renders in
  // the reader's LOCAL zone -- created_at is UTC, and printing an unmarked UTC
  // clock face is worse than a date alone because it looks local and is not. A
  // literal expected string would therefore pass or fail on the runner's
  // timezone rather than on the code, which is a test that measures the machine.
  // The day is not asserted for the same reason: a far-western zone moves it.
  ok('...and the "On" column carries a TIME, so same-day rows are distinguishable',
    /\d:\d\d(:\d\d)?\s?(AM|PM)?/.test(rows.replace(/2026-09/g, '')) &&
    !/>\s*2026-09-19\s*</.test(rows), rows);

  // ── THE REFUSAL MUST NAME THE CORRECTION PATH (added 2026-09-22) ─────
  // alf_claim_routes is append-only and refuses an overwrite with 409
  // ALREADY_RECORDED. That refusal used to say only "cannot be overwritten",
  // which leaves a biller who has found a WRONG determination with nowhere to
  // go -- and the thing they try next is pressing Record again, which mints a
  // fresh id from Date.now() and puts TWO rows in the trail with nothing
  // marking which one is believed.
  //
  // ASSERTED ON THE SERVER SOURCE rather than by driving the handler, because
  // this suite drives the CLIENT half of the round trip. The message is the
  // contract between the two, and a message change with nothing pinning it is
  // one edit away from reverting in silence.
  {
    const fs = require('fs');
    const path = require('path');
    const api = fs.readFileSync(path.join(__dirname, '..', 'api', 'sd-data.js'), 'utf8');
    const i = api.indexOf("code: 'ALREADY_RECORDED', message: 'This routing decision");
    const msg = i < 0 ? '' : api.slice(i, api.indexOf("' } });", i));
    ok('the alf_claim_routes 409 names the CORRECTION PATH, not just the refusal',
      i > 0 && /A CORRECTED determination is a NEW decision/.test(msg)
      && /the trail will show both/.test(msg), msg.slice(0, 220));
    // The half easiest to leave out: a retry and a correction are
    // indistinguishable to this endpoint, so the message has to say so or it
    // invites the duplicate row it exists to prevent.
    ok('...and it warns that a RETRY and a CORRECTION look identical to the endpoint',
      /retry and a correction look identical/.test(msg), msg.slice(0, 220));

    // ── AND THE SAME STANDARD ACROSS EVERY alf_ APPEND-ONLY REFUSAL ──────
    // Added 2026-09-22 with the three siblings. This arm is DERIVED, not a
    // list: it finds every ALREADY_RECORDED in api/sd-data.js, keeps the ones
    // whose enclosing resource is alf_*, and requires each to name a
    // correction path. A hand-written list of five would go stale the moment a
    // sixth append-only alf_ resource is added, and would go stale SILENTLY --
    // which is the whole failure mode this suite keeps running into.
    //
    // IT ALSO CORRECTS A MISCOUNT OF MINE: the open-work row first said FOUR
    // siblings needed this and named alf_observations, which is not a resource
    // -- it was alf_op_audits read off its own message text, and that one
    // already said "Record a new entry instead". Three needed it, not four.
    {
      const re = /code: 'ALREADY_RECORDED', message: '([^']*)'/g;
      const missing = [];
      let found = 0, m;
      while ((m = re.exec(api)) !== null) {
        const before = api.slice(0, m.index);
        const owners = before.match(/resource === '([a-z_]+)'/g) || [];
        const owner = owners.length
          ? owners[owners.length - 1].replace(/resource === '|'/g, '') : '?';
        if (!/^alf_/.test(owner)) continue;
        found += 1;
        if (!/NEW entry|NEW signal|NEW record|NEW decision|Record a new entry/.test(m[1])) {
          missing.push(owner);
        }
      }
      ok('EVERY alf_ append-only refusal names a correction path, derived not listed',
        found >= 5 && missing.length === 0,
        'checked ' + found + ', missing: ' + (missing.join(', ') || 'none'));
    }
  }

  console_warn('\n' + (failed ? failed + ' ARM(S) FAILED' : 'ALL ARMS PASS'));
  process.exit(failed ? 1 : 0);
}

main().catch((e) => { console_warn('THREW: ' + (e && e.stack || e)); process.exit(1); });
