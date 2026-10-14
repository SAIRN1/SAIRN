// api/sd-data-scp-session-gate.test.js
//
// REQUIREMENT: ELEVEN OF SAIRNscape'S TWELVE RESOURCES refuse a call that
//   carries no employee session, AND every correctly signed-in crew still gets
//   through. Was "the two Tier A SAIRNscape resources" until 2026-10-13 -- the
//   scope has widened five times since and this line said two the whole way,
//   which is the one place in this file a reader starts.
//
// CROSS-TENANT-ISOLATION: none (this file is about identity WITHIN a company,
//   not about the tenant boundary; `invoices` and `scp_quotes` already have
//   tenant arms in api/sd-data-cross-tenant-ownbranch.test.js)
//
// Run:  node api/sd-data-scp-session-gate.test.js
//
// ── WHY THIS EXISTS ──────────────────────────────────────────────────────
// All twelve SAIRNscape resources dispatched on the licence hash alone, with
// NO session check of any kind -- and the licence key is shipped to the browser
// and readable by anyone who can open sairnscape.html, so it was the whole
// authorisation. Two of the twelve are Tier A on integrity: `invoices` (money)
// and `scp_quotes` (the priced quote every invoice descends from).
//
// Identical shape to SAIRNfreedom's fifteen and SAIRNdesign's nine, both swept
// earlier in September 2026. SAIRNscape was not swept with either, and
// tests/app_session_isolation.js recorded that gap in prose from 2026-09-24
// rather than leaving it undocumented -- this file is that row being closed.
//
// ── THE HALF THAT BREAKS APPS, AND IT IS THE HALF THIS FILE IS MOSTLY ABOUT
// A gate is two lines. The failure this platform has recorded three times is
// not forgetting the gate, it is arming it before the CLIENT can send a token
// -- which answers 403 "sign in first" to every correctly signed-in employee
// and fails closed AND confusingly, the hardest failure to read.
//
// MEASURED BEFORE ARMING, and SAIRNscape is the easy case: scpData() attaches
// X-SD-Auth from SCP_SESSION_KEY on every call whenever a token exists
// (sairnscape.html:2107) -- there is no per-call `withSession` flag to forget,
// which is exactly what had to be repaired in sairndesign.html. So the client
// half needed no change. THE ARMS BELOW READ THE SHIPPED PAGE RATHER THAN
// TRUSTING THAT SENTENCE, because "no change was needed" is the claim most
// worth checking when no diff exists to review.
//
// ── THE SECOND PRECONDITION, WHICH IS ORDERING ───────────────────────────
// scpData attaching the header is necessary and not sufficient: a token that
// does not EXIST yet cannot be attached. Both login paths must write the
// session to sessionStorage BEFORE the first server read. They do --
// scpDoLogin and scpDoBootstrap each setItem then call scpApplyLoggedIn, which
// calls scpInit, which calls scpSyncFromServer -- and an arm below asserts
// that ordering on the source, because reversing it would make every read on a
// fresh login unauthenticated and now refused.
//
// ── AND THE THIRD LIST, WHICH IS WHERE THIS GOES WRONG QUIETLY ───────────
// A resource in SD_SESSION_GATED and NOT in SD_GATE_APP resolves expectedApp
// to 'stonedesk', so a genuine SAIRNscape token fails verification and the
// caller is refused with "sign in first" no matter what they do. The two lists
// DISAGREEING is the defect, so the arm below asserts they AGREE rather than
// asserting either one's contents -- the same shape
// api/sd-data-sf-session-gate.test.js and api/sd-data-sdn-session-gate.test.js
// use for SAIRNfreedom and SAIRNdesign.
//
// ── THE NAME TRAP, AND IT IS SPECIFIC TO THIS APP ────────────────────────
// SAIRNscape claimed the BARE names `invoices` and `schedule` before the scp_
// convention existed. The storage table is `scp_invoices`; the RESOURCE is
// `invoices`. A gate written against 'scp_invoices' would gate nothing at all
// and every arm asserting a refusal would still be satisfiable by some other
// branch -- so the positive arms below are what make this file decisive, not
// the refusals.

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['scp', 'session', 'gate', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');
const { fnBody } = require('../tests/lib/fn_span.js');

const HASH = 'scape-company-A-hash';
const APP = 'sairnscape';
const SD_DATA = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
const PAGE = fs.readFileSync(path.join(__dirname, '..', 'sairnscape.html'), 'utf8');

// The two this commit gates, written out rather than parsed, because the arm
// below cross-checks the SOURCE against this list in both directions -- a list
// derived from the source could not catch the source being wrong.
//
// THE STOPPING RULE IS "TIER A", NOT "THESE TWO NAMES". If a third SAIRNscape
// row is promoted, it belongs here and in both tables on the same day, which is
// what the sdn set's growth from five to nine on 2026-09-24 established.
// ── `customers` ADDED 2026-10-05, AND IT BREAKS THE STOPPING RULE ABOVE ────
// On purpose, and the arm below caught the source change before this list was
// touched: adding the two SD_SESSION_GATED / SD_GATE_APP lines turned the
// set-equality arm RED with nothing else edited, which is exactly what that
// arm is for and is recorded here as the one time it fired.
//
// WHY IT IS HERE WHEN THE REGISTER SAYS B. Proven live with a control before
// anything was changed: on SCP-DEMO-2026 with NO session, `read customers`
// answered 200 and returned a row carrying NAME, EMAIL, PHONE AND STREET
// ADDRESS; `write customers` with an id-less payload answered 400 from the
// handler body, so the gate did not fire and nothing was stored; and
// `invoices` and `scp_quotes` on the SAME bare key answered 403 both.
//
// `customers` is carried B/B in docs/CRITICALITY-TIERS.md while its own
// confidentiality cell already reads "A CUSTOMER's NAME, PHONE, EMAIL AND
// STREET ADDRESS" -- the basis was corrected and the LETTER was not, and the
// letter is what a Tier-A-scoped sweep reads. THE GATE IS NOW AHEAD OF THE
// REGISTER, the B->A retier is owed, and hank holds that file
// (2026-10-05T12:57:55Z). Waiting for a register cell while a customer's
// address is readable on a browser-shipped licence key is the wrong trade; the
// retier is the root-cause follow-up, not a precondition.
// ── THREE MORE, 2026-10-11, FROM A REPRODUCING ARTIFACT RATHER THAN A SWEEP ─
// .claude/skills/sairn-hover-auditor/tools-hover2/scp_session_gate_repro.py
// --all reported 15 of 22 resource/action pairs gated by NEITHER mechanism at
// 263f736f. Eight resources were ungated; THREE are taken and FIVE are left,
// and the five are named in UNGATED_REST below so the scope is a disclosure
// rather than an absence.
//
//   scp_designs            THE THIRD TIER A ROW, AND IT WAS OWED. The note
//                          above says "if a third SAIRNscape row is promoted,
//                          it belongs here and in both tables on the same day."
//                          docs/CRITICALITY-TIERS.md:538 promoted it B -> A on
//                          2026-10-05 -- "a design is wrong on its approval,
//                          and a quote is raised on a plan the client never
//                          approved" -- and it did not land. Register line 136
//                          names SAIRNscape's three A rows as invoices,
//                          scp_quotes, scp_designs. This closes that set.
//
//   scp_vendors            B BY THE LETTER, CONTACT PII BY THE COLUMNS -- the
//                          same shape as `customers`, found the same way.
//                          sql/sairnscape_data_schema_phase2.sql gives its
//                          `data` jsonb as name, category, CONTACT, PHONE,
//                          EMAIL, terms, notes. Its register cell says outright
//                          that it was "classified by the stated B rule rather
//                          than individually read" -- and that sentence sits on
//                          six of the eight ungated rows. The B -> A retier is
//                          owed; it is not a precondition, for the reason the
//                          `customers` note above gives.
//
//   scp_progress_photos    `photo_b64` -- a photograph of a customer's property
//                          -- plus `captured_by` and `qc_by`, two named
//                          employees. AND THE REPRO CALLED ITS WRITE FIXED:
//                          scp_session_gate_repro.py:78 is
//                          `branch_gate = 'verifySessionToken' in body`, a
//                          substring test, and the write branch
//                          (api/sd-data.js:5231) does call it -- inside
//                          `if (payload.qc_status === ...)`. So the gate fired
//                          on a QC DECISION and never on a photo upload, and
//                          the true figure is 16 of 22 ungated by content, not
//                          15. Reported to that file's owner, not edited: it is
//                          hover2's.
//                          The QC block is LEFT ALONE. It is not a session gate
//                          under another name -- it additionally requires
//                          SCP_QC_AUTHORITY_ROLES and refuses self-QC against
//                          the SERVER's `captured_by`. The table entry makes a
//                          session unconditional; that block still decides who
//                          may approve.
// ── AND THE LAST FIVE, 2026-10-13 (b8), ON MICHAEL'S DECISION ───────────────
// The paragraph below used to end "it is NOT a finding, and it is not made
// here". IT HAS NOW BEEN MADE, so the five move from UNGATED_REST into GATED
// and every claim their old entry made about their columns stays true -- no
// person's name, no contact detail, no money, no regulated determination on
// any of the five rows, a customer_id FOREIGN KEY with the identity on the
// `customers` row, which has been gated since 2026-10-05.
//
// SO THE GATE IS NOT JUSTIFIED BY DISCLOSURE OF A PERSON and that is stated
// rather than glossed: it is justified by the licence key being SHIPPED TO THE
// BROWSER, which makes an irrigation schedule, a controller inventory and a
// job's scope readable by anyone who can open the app.
//
// THESE FIVE WERE THE WHOLE OF WHAT STILL REPRODUCED. hover2's artifact
// .claude/skills/sairn-hover-auditor/tools-hover2/scp_session_gate_repro.py
// --all last reported 10 of 22 resource/action pairs reachable by NEITHER
// mechanism, and the ten are exactly these five times two verbs.
//
// MOVING THEM IN HERE WRITES NO ARM BY HAND: each name adds six, the same way
// the 2026-10-11 three did -- refusal on read and on write, allow-with-a-real-
// session on read and on write, a wrong-app token, and a deactivated
// credential.
const GATED = ['customers', 'invoices', 'scp_quotes',
  'scp_designs', 'scp_vendors', 'scp_progress_photos',
  'scp_jobs', 'scp_irr_controllers', 'scp_irr_zones',
  'scp_irr_schedules', 'scp_water_features',
  // ── AND THE TWELFTH, 2026-10-14 (b9) -- MICHAEL DECIDED IT ────────────────
  // b8 left `schedule` in UNGATED_REST below as a DISCLOSURE, with its own note
  // saying nobody had decided it and that the one thing needing a read first
  // was whether StoneDesk calls it. That read was done and recorded (all seven
  // StoneDesk mentions are navigation, not sd-data calls); Michael has now
  // decided to gate it on the same argument as the five. SAIRNscape is 12 of 12.
  'schedule'];

// ── THE FIVE THAT STAY LICENCE-ONLY, NAMED, 2026-10-11 ──────────────────────
// Was a single `UNGATED_WITNESS = 'scp_vendors'`, described as "one of the ten
// that stay licence-only ... a disclosure, so the day somebody widens the scope
// it is visible here." IT HAD TO MOVE, and that is the finding rather than the
// bookkeeping: the negative control was sitting on the ONE remaining ungated
// resource that carries a named contact's phone and e-mail. A control chosen
// for being ungated is not evidence that being ungated is right.
//
// ALL FIVE ARE LISTED, NOT ONE. A single witness proves a gate did not widen to
// that one name; it says nothing about the other four, and the previous shape
// could not distinguish "nine still ungated" from "one".
//
// EACH ONE'S COLUMNS WERE READ OUT OF sql/sairnscape_data_schema*.sql ON
// 2026-10-11, not taken from its register letter -- which is the step that
// turned scp_vendors from a witness into a gate:
//   scp_jobs              job_id, customer_id FK, data{scope, target_date,
//                         status, recurring_schedule_id}
//   scp_irr_controllers   controller_id, customer_id FK, data{name, brand,
//                         model, zones_supported, install_date, notes} -- the
//                         `name` is the CONTROLLER's
//   scp_irr_zones         zone_id, customer_id FK, data{name, zone_type,
//                         station, head_count, sqft, status, backflow, ...}
//   scp_irr_schedules     irrsched_id, zone_id, data{days, start, duration,
//                         status}
//   scp_water_features    feature_id, customer_id FK, data{name, type, scale,
//                         size, pump, filter, condition, ...} -- the one row of
//                         the eight whose register cell says it WAS read
//                         individually
// No person's name, no contact detail, no money and no regulated determination
// on any of the five. A customer_id FOREIGN KEY, with the identity on the
// customer row, which IS gated. Gating them anyway is a defensible product
// decision about whether an unsigned-in crew may see an irrigation schedule --
// it is NOT a finding, and it is not made here.
// ── THE FIVE MOVED OUT 2026-10-13 (b8) AND THE CONTROL DID NOT VANISH ───────
// All five of the above are now in GATED. A negative control that becomes an
// empty loop is the vacuity this suite has already been burned by twice, so the
// list is NOT emptied -- it is repopulated from a population that was never
// measured.
//
// `schedule` IS THE TWELFTH SAIRNscape RESOURCE AND THE REPRO ONLY EVER SAW
// ELEVEN. api/_resources/sairnscape.js owns twelve names; 22 pairs is 11 x 2,
// and `schedule` -- served at api/sd-data.js:5607 (read) and :5615 (write) --
// is the one it never counted. It is NOT in SD_SESSION_GATED at this HEAD.
//
// IT IS LEFT UNGATED DELIBERATELY AND THAT IS A DISCLOSURE, NOT AN
// ENDORSEMENT. Michael's decision named the five that reproduced; nobody has
// decided this one, and `schedule` is the only SAIRNscape resource whose bare
// name is also a StoneDesk PANEL id (stonedesk.html:40366 and six other
// mentions, every one of them navigation rather than an sd-data call -- read at
// this HEAD, which is why that reading is written down instead of the gate
// being widened on an assumption). Gating it needs that read confirmed by
// somebody who is deciding it, not by this suite.
//
// THE ARM BELOW IS WHY THIS IS NOT JUST A COMMENT: `schedule` must still answer
// on the licence key alone, so the day it is gated -- rightly or by accident --
// this file goes red and says so.
// ── THE LICENCE-ONLY LIST IS NOW EMPTY, AND THAT COSTS THIS FILE ITS OLD ────
// ── NEGATIVE CONTROL, WHICH IS SAID OUT LOUD RATHER THAN LEFT TO BE NOTICED ─
// 2026-10-14 (b9). Every SAIRNscape resource is gated, so the loop that drove
// "and what is not gated is still not gated" now has NOTHING TO DRIVE. A
// zero-length loop passes forever and prints nothing, which is exactly the
// vacuity this file has been burned by twice and warned about in b8 in these
// same words -- so it is NOT left as an empty loop.
//
// WHAT REPLACES IT, and why this is stronger rather than merely different:
//
//   * THE DERIVED-POPULATION ARM still runs and now says GATED == the whole
//     registry. A thirteenth resource landing in api/_resources/sairnscape.js
//     and not in the gate fails this suite on the same commit.
//   * AN EXPLICIT ARM asserts the list is EMPTY ON PURPOSE. The day somebody
//     re-opens a SAIRNscape resource to the bare licence key, that arm is where
//     it has to be written down.
//   * THE ANTI-VACUITY PROPERTY MOVES TO THE PAIRED POSITIVE ARMS. The reason a
//     403 arm means anything is that the SAME harness answers 200 when a real
//     session is attached -- twelve resources x read and write. A harness that
//     403-ed everything would fail twenty-four arms, not pass them.
//   * PLUS ONE CROSS-APP CONTROL, because all of the above is still inside this
//     app: a bare-key call to `employees`, which has its OWN older gate, must
//     NOT come back with this table's "sign in first". That is the arm that
//     fails if SD_SESSION_GATED ever starts swallowing resources it was never
//     asked about -- the shape api/sd-data-session-gate.test.js has driven
//     since the table existed, kept here too because this is the file that
//     touches that table most often.
const UNGATED_REST = [];

// ── THE PER-RESOURCE WRITE PAYLOAD, 2026-10-13 (b8) ─────────────────────────
// Only the fields a resource's own branch REQUIRES and that are not in the
// {id, customer_id} base. Read out of api/sd-data.js at this HEAD, with the
// line that enforces each one, so this is a citation and not a recollection:
//
//   scp_progress_photos  payload.schedule_id  api/sd-data.js:5826
//   scp_irr_schedules    payload.zone_id      api/sd-data.js:5218
//
// Everything else in GATED requires payload.customer_id, which is in the base.
// `invoices` and `scp_quotes` included -- checked, not assumed (:5637, :5595).
const WRITE_EXTRA = {
  scp_progress_photos: { schedule_id: 'S-1' },
  scp_irr_schedules: { zone_id: 'Z-1' }
};

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
async function atest(name, fn) {
  try { await fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  res.setHeader = function () { return res; };
  return res;
}
function loadHandler() {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: HASH,
                 trial_ends_at: null, stripe_subscription_id: null, app_id: APP };
      }
    }
  };
  global.fetch = async function (url, opts) {
    const u = String(url);
    // A CREDENTIAL LOOKUP IS NOT THE QUERY UNDER TEST. The gate re-checks that
    // the signed-in employee is still ACTIVE before serving anything, and a
    // stub that answered [] here would make every positive arm below fail 403
    // CREDENTIAL_INACTIVE -- a false negative that reads exactly like the gate
    // refusing a correctly signed-in caller, which is the thing these arms are
    // supposed to be able to detect.
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, json: async () =>
        [{ license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: true }] };
    }
    if (opts && opts.method === 'POST') {
      return { ok: true, status: 200, json: async () => [JSON.parse(opts.body)] };
    }
    return { ok: true, status: 200, json: async () => [{ data: { ok: true } }] };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}
async function callWith(headers, body) {
  const h = loadHandler();
  const res = mockRes();
  await h({ method: 'POST', headers: headers, body: body }, res);
  return res;
}
const BEARER = { authorization: 'Bearer KEY' };
function withToken(app, role) {
  return Object.assign({}, BEARER, {
    'x-sd-auth': signSessionToken({ app: app, employee_id: 'emp-1',
                                    role: role || 'owner', license_hash: HASH })
  });
}

(async function () {
  // Derived rather than written, so the banner cannot be the stale line again.
  console.log('SAIRNscape -- ' + GATED.length + ' of '
    + (GATED.length + UNGATED_REST.length)
    + ' resources demand an employee session; licence-only: '
    + UNGATED_REST.join(', ') + '\n');

  section('THE TWO LISTS MUST AGREE -- the way this goes wrong quietly');

  test('both gated SAIRNscape resources have an SD_GATE_APP entry', function () {
    // Anchored on the VALUE 'sairnscape' for the second list and on membership
    // in GATED for the first, because these two resource names share no prefix
    // -- `invoices` is bare. A prefix parser of the kind the sdn and sf suites
    // use would find `scp_quotes` and silently miss `invoices`, which is the
    // half that carries the money.
    const gateTable = SD_DATA.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/);
    const appTable = SD_DATA.match(/const SD_GATE_APP = \{[\s\S]*?\n    \};/);
    assert.ok(gateTable, 'SD_SESSION_GATED is gone');
    assert.ok(appTable, 'SD_GATE_APP is gone');
    const gatedIn = GATED.filter((r) =>
      new RegExp("'" + r + "':\\s*\\['read', 'write'\\]").test(gateTable[0])).sort();
    const appIn = (appTable[0].match(/'([a-z_]+)':\s*'sairnscape'/g) || [])
      .map((s) => s.match(/'([a-z_]+)'/)[1]).sort();
    assert.deepStrictEqual(gatedIn, GATED.slice().sort(),
      'SD_SESSION_GATED does not gate both Tier A SAIRNscape resources for read '
      + 'AND write -- found: ' + gatedIn.join(', '));
    assert.deepStrictEqual(appIn, GATED.slice().sort(),
      'SD_SESSION_GATED and SD_GATE_APP disagree. A resource in the first and '
      + 'not the second resolves expectedApp to "stonedesk" and refuses every '
      + 'correctly signed-in crew lead -- it fails CLOSED and confusingly.');
  });

  test('the RESOURCE name is the bare one the dispatch actually uses', function () {
    // The trap this app carries and no other does. If somebody "tidies" the
    // gate entry to 'scp_invoices' it gates a resource that does not exist,
    // every refusal arm below still passes for the wrong reason, and the money
    // row goes back to licence-only in silence.
    assert.ok(/if \(resource === 'invoices' && action === 'read'\)/.test(SD_DATA),
      "the `invoices` read branch is gone or renamed -- if the resource really "
      + "is called something else now, this whole file's anchor moved");
    assert.ok(!/'scp_invoices':\s*\['read', 'write'\]/.test(SD_DATA),
      "SD_SESSION_GATED carries 'scp_invoices', which is the STORAGE TABLE and "
      + 'not a resource the dispatch ever sees. That entry gates nothing.');
  });

  section('THE CLIENT CAN ACTUALLY SEND A TOKEN -- the precondition, read out '
    + 'of the shipped page');

  test('scpData attaches X-SD-Auth with no per-call flag to forget', function () {
    const at = PAGE.indexOf('var headers = { \'Content-Type\': \'application/json\', Authorization: \'Bearer \' + licKey };');
    assert.ok(at > -1, "scpData's header block not found -- anchor moved");
    const fn = PAGE.slice(at, at + 400);
    assert.ok(/sessionStorage\.getItem\(SCP_SESSION_KEY\); if \(tok\) headers\['X-SD-Auth'\] = tok;/.test(fn),
      'scpData no longer sets X-SD-Auth from the stored session. The gate above '
      + 'then refuses every correctly signed-in employee, which is the failure '
      + 'arming a gate before the client can send a token produces.');
    assert.ok(!/withSession/.test(fn),
      'a withSession-style flag has appeared on scpData\'s header. SAIRNdesign '
      + 'had exactly that and 18 of 19 call sites never passed it.');
  });

  test('every scpData call for these two goes through that one helper', function () {
    // The header being unconditional only covers the call sites that USE the
    // helper. A bespoke fetch for either resource would bypass it entirely.
    for (const r of GATED) {
      const direct = PAGE.split('\n').filter((l) =>
        l.indexOf("'" + r + "'") > -1 && /fetch\s*\(/.test(l) && l.indexOf('scpData') === -1);
      assert.deepStrictEqual(direct, [],
        r + ' has a call site that calls fetch() directly instead of scpData(), '
        + 'so it carries no session header and is now refused: ' + direct.join(' | '));
    }
  });

  test('a session exists BEFORE the first server read, on BOTH login paths', function () {
    // scpDoLogin and scpDoBootstrap each write the token to sessionStorage and
    // then call scpApplyLoggedIn -> scpInit -> scpSyncFromServer. Reversed,
    // every read on a fresh login would carry no token and now be refused.
    for (const fname of ['scpDoLogin', 'scpDoBootstrap']) {
      const start = PAGE.indexOf('function ' + fname + '(){');
      assert.ok(start > -1, fname + ' not found -- anchor moved');
      const body = PAGE.slice(start, PAGE.indexOf('window.' + fname + '=' + fname + ';', start));
      const setsToken = body.indexOf('sessionStorage.setItem(SCP_SESSION_KEY');
      const enters = body.indexOf('scpApplyLoggedIn(');
      assert.ok(setsToken > -1, fname + ' no longer stores a session token');
      assert.ok(enters > -1, fname + ' no longer calls scpApplyLoggedIn');
      assert.ok(setsToken < enters,
        fname + ' enters the app BEFORE storing the session token, so the first '
        + 'read after a sign-in carries no header and is now refused');
    }
    // And the third link: scpApplyLoggedIn is the only route into scpInit, and
    // scpInit is what triggers the first server read.
    const apply = PAGE.slice(PAGE.indexOf('function scpApplyLoggedIn(role){'),
                             PAGE.indexOf('function scpDoLogin(){'));
    assert.ok(/scpInit\(\);/.test(apply),
      'scpApplyLoggedIn no longer calls scpInit -- the ordering asserted above '
      + 'no longer says anything about when the first read happens');
    // ── BOUNDED BY scpInit's OWN CLOSING BRACE, NOT BY `+ 900` ───────────
    // MEASURED 2026-10-06: scpInit() is 726 bytes and the window was 900, so
    // 174 bytes of the NEXT thing were being searched -- and what is in those
    // 174 bytes is a comment block that talks about sync functions by name:
    //
    //     "\n\n// Read-through sync -- same honest-degrade behavior as
    //      SAIRNgrounds'\n// grdSyncFromServer(): ..."
    //
    // The arm passes today for the right reason -- `scpSyncFromServer();` IS
    // inside scpInit. But if somebody removed that call and left a comment
    // saying so, this arm would go on passing, which is the whole failure
    // mode it exists to catch. A positive assertion over a too-long span
    // fails GREEN.
    //
    // The sweep that found it measured 26 span sites against their functions'
    // balanced closes; this was the ONE real silent-direction disagreement.
    // Eight others were LONG by 1-2 bytes of pure whitespace and are left
    // alone, because a gap that is a newline cannot carry a false match --
    // checked by printing the gap bytes rather than assuming.
    const init = fnBody(PAGE, 'function scpInit(){');
    assert.ok(/scpSyncFromServer\(\);/.test(init),
      'scpInit no longer calls scpSyncFromServer -- re-derive where the first '
      + 'server read now happens and re-anchor this arm on that');
  });

  section('THE GATE ITSELF -- driven, both directions');

  for (const resource of GATED) {
    await atest(resource + ' read with NO session is refused', async function () {
      const res = await callWith(BEARER, { action: 'read', resource: resource });
      assert.strictEqual(res.statusCode, 403,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
    });

    await atest(resource + ' write with NO session is refused', async function () {
      const res = await callWith(BEARER,
        { action: 'write', resource: resource, payload: { id: 'X-1', customer_id: 'C-1' } });
      assert.strictEqual(res.statusCode, 403,
        'answered ' + res.statusCode + ' ' + JSON.stringify(res.body));
    });

    await atest(resource + ' read WITH a valid SAIRNscape session is allowed',
      async function () {
        // THE PAIRED POSITIVE, and the half that matters most: a gate that
        // refused everybody would pass every arm above and lock a landscaping
        // company out of its own quotes and invoices.
        const res = await callWith(withToken(APP), { action: 'read', resource: resource });
        assert.strictEqual(res.statusCode, 200,
          'a correctly signed-in crew lead was refused: ' + res.statusCode + ' '
          + JSON.stringify(res.body) + ' -- if this is FORBIDDEN, check that '
          + resource + ' is in SD_GATE_APP as well as SD_SESSION_GATED');
      });

    await atest(resource + ' write WITH a valid SAIRNscape session is allowed',
      async function () {
        // The write half of the same point. A gate is a SPLIT, not a lockout,
        // and a read-only positive would not have noticed a write that refused
        // everybody.
        // `schedule_id` ADDED 2026-10-11, and it is worth the line. This arm
        // asserts a STATUS CODE, so a payload the handler rejects at validation
        // reads as "the gate refused a signed-in write" when it did nothing of
        // the kind -- scp_progress_photos requires payload.schedule_id
        // (api/sd-data.js:5231) and this arm answered 400 for exactly that
        // reason the moment the resource was gated.
        //
        // THE SUPERSET IS GONE AND THE MAP IS WRITTEN, 2026-10-13 (b8). This
        // arm used to send one three-field superset to every resource, with
        // its own note saying "the day a FOURTH is needed, write the map".
        // scp_irr_schedules is that day: api/sd-data.js:5218 requires
        // payload.zone_id as well as payload.id, so the superset answered 400
        // and the arm reported it as a payload problem -- correctly, and that
        // is the whole reason the note existed.
        //
        // WHY A MAP IS BETTER THAN A FOURTH FIELD: a field one resource needs,
        // sent to all of them, means a resource added later whose requirement
        // is already in the superset passes this arm while nobody learns it has
        // one. Per-resource, the new name gets a 400 until somebody reads the
        // branch.
        const res = await callWith(withToken(APP),
          { action: 'write', resource: resource,
            payload: Object.assign({ id: 'X-1', customer_id: 'C-1' },
                                   WRITE_EXTRA[resource] || {}) });
        assert.strictEqual(res.statusCode, 200,
          'a correctly signed-in write was refused: ' + res.statusCode + ' '
          + JSON.stringify(res.body) + ' -- a 400 here is a PAYLOAD problem in '
          + 'this arm, not a gate refusal');
      });

    await atest(resource + ' refuses a token minted for ANOTHER SAIRN app',
      async function () {
        // Guardian Check 28's collision, and the reason SD_GATE_APP exists.
        // sairndesign chosen deliberately: it is the app whose registry scan
        // claimed `invoices` before the handler settled the question.
        const res = await callWith(withToken('sairndesign'),
          { action: 'read', resource: resource });
        assert.strictEqual(res.statusCode, 403,
          'a sairndesign session reached ' + resource);
      });

    await atest(resource + ' refuses a DEACTIVATED credential on a token that '
      + 'still verifies', async function () {
        // verifySessionToken proves the token was minted by us and has not
        // expired. It proves nothing about NOW, and deactivation is the one
        // control an owner has for somebody who has just left.
        const h = (function () {
          const handler = loadHandler();
          const prev = global.fetch;
          global.fetch = async function (url, opts) {
            if (/_employee_auth\?/.test(String(url))) {
              return { ok: true, status: 200, json: async () =>
                [{ license_hash: HASH, employee_id: 'emp-1', role: 'owner', active: false }] };
            }
            return prev(url, opts);
          };
          return handler;
        })();
        const res = mockRes();
        await h({ method: 'POST', headers: withToken(APP),
                  body: { action: 'read', resource: resource } }, res);
        assert.strictEqual(res.statusCode, 403,
          'a deactivated credential still reached ' + resource + ': '
          + res.statusCode + ' ' + JSON.stringify(res.body));
        assert.strictEqual(res.body.error.code, 'CREDENTIAL_INACTIVE');
      });
  }

  section('THE TWO LISTS TOGETHER ARE THE WHOLE APP -- derived, so a '
    + 'THIRTEENTH resource cannot be covered by neither');

  // ADDED 2026-10-13 (b8), AND IT IS THE ARM THAT WOULD HAVE CAUGHT `schedule`
  // A WEEK EARLIER. Every figure this suite has ever quoted about SAIRNscape
  // came from the repro's 22 pairs, which is 11 resources x 2 verbs -- and the
  // registry owns TWELVE. A resource in neither GATED nor UNGATED_REST is
  // invisible to every other arm in this file: not gated, so no refusal arm;
  // not disclosed, so no licence-only arm. That is the same shape as a gated
  // resource driven by nothing, one level up.
  //
  // DERIVED FROM api/_resources/sairnscape.js RATHER THAN COUNTED, so adding a
  // thirteenth resource to the registry turns this red on the same commit.
  test('GATED + UNGATED_REST is exactly what the registry owns', function () {
    const SCP = require('./_resources/sairnscape.js');
    const owned = SCP.resources.slice().sort();
    const covered = GATED.concat(UNGATED_REST).sort();
    assert.deepStrictEqual(covered, owned,
      'this suite\'s two lists and api/_resources/sairnscape.js disagree. '
      + 'In the registry and in neither list: '
      + owned.filter((r) => covered.indexOf(r) === -1).join(', ')
      + ' -- in a list and not in the registry: '
      + covered.filter((r) => owned.indexOf(r) === -1).join(', '));
    assert.ok(GATED.length > UNGATED_REST.length,
      'more SAIRNscape resources are disclosed as licence-only than are gated, '
      + 'which inverts what this suite is for');
    // A stale WRITE_EXTRA key is a payload sent to a resource that no longer
    // exists or is no longer gated -- silent, because an extra field is simply
    // ignored by every branch that does not read it.
    const stale = Object.keys(WRITE_EXTRA).filter((r) => GATED.indexOf(r) === -1);
    assert.deepStrictEqual(stale, [],
      'WRITE_EXTRA carries a key that is not in GATED: ' + stale.join(', '));
  });

  section('THE LICENCE-ONLY LIST IS EMPTY ON PURPOSE -- and what replaces the '
    + 'control it used to be');

  // THE LOOP THAT WAS HERE IS GONE BECAUSE IT WOULD DRIVE NOTHING. From
  // 2026-10-11 to 2026-10-14 this section ran one arm per licence-only
  // resource, and the whole point was that a control chosen for being ungated
  // is not evidence that being ungated is right. All twelve are gated now, so
  // the loop would print nothing and pass -- and a zero-length loop that passes
  // is indistinguishable from a control that works. Replaced, not deleted.
  test('UNGATED_REST is EMPTY, and that is a statement rather than a leftover',
    function () {
      assert.deepStrictEqual(UNGATED_REST, [],
        'a SAIRNscape resource has been re-opened to the bare licence key: '
        + UNGATED_REST.join(', ') + '. That may be right -- but it is a scope '
        + 'change and THIS is where it gets written down, with the reason.');
      // Stated against the registry rather than as a number, so it cannot go
      // stale the way "the two Tier A resources" did for five widenings.
      const SCP = require('./_resources/sairnscape.js');
      assert.strictEqual(GATED.length, SCP.resources.length,
        'every resource the registry owns is gated, or this count disagrees: '
        + GATED.length + ' gated vs ' + SCP.resources.length + ' owned');
    });

  // ── THE CROSS-APP CONTROL, AND IT IS THE ONE THAT SURVIVES A FULL GATE ────
  // Everything above this line is inside SAIRNscape, so none of it can see the
  // failure where SD_SESSION_GATED starts refusing resources it was never
  // asked about. `employees` has its OWN, older gate; what matters is that this
  // table did not swallow it. Same shape api/sd-data-session-gate.test.js has
  // driven since the table existed -- kept here as well because this is the
  // file that edits that table most often, and the duplication is the point.
  await atest('a resource with its OWN gate is not swallowed by this table',
    async function () {
      const res = await callWith(BEARER, { action: 'read', resource: 'employees' });
      assert.ok(res.body && res.body.error,
        'expected `employees` to keep its own refusal, got '
        + res.statusCode + ' ' + JSON.stringify(res.body).slice(0, 120));
      assert.ok(!/sign in first/i.test((res.body.error.message) || ''),
        'SD_SESSION_GATED answered for a resource it does not own -- the gate '
        + 'has widened past its table');
    });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
