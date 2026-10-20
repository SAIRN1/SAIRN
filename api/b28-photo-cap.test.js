// api/b28-photo-cap.test.js
//
// Run:  node api/b28-photo-cap.test.js
//
// ── THE DEFECT ──────────────────────────────────────────────────────────────
// `api/sairndental/public-book.js` accepts up to 1.2MB of patient photos on a
// self-scheduled booking and writes them into `dnt_appointments`, whose DB
// constraint was raised to 1,291,059 bytes for exactly that reason. The STAFF
// path to the same table runs through `api/sd-data.js`, which capped EVERY
// write at 65,536 bytes.
//
// So the booking lands and then cannot be acted on. sairndental.html's pending
// queue reads the row whole and sends it back on confirm or decline, so every
// staff write on a photo-bearing booking was answered 413 PAYLOAD_TOO_LARGE.
// **Not confirmable and not declinable** -- a real patient request parked in a
// queue nobody can empty, under a size error that points at the staff member's
// click rather than at the photo.
//
// The same gap hid a DEAD ERROR HANDLER one app over: `rf_claim_photos`
// answers 413 on a `rfcph_data_size` violation, and no payload that cleared a
// 64KB gate could ever violate a 1.5MB constraint.
//
// ── WHAT THIS SUITE IS FOR, BEYOND THE TWO FIXES ────────────────────────────
// Eight tables carry a `data` constraint ABOVE 64KB and the cap table covers
// two. C6 asserts every covered cap equals the number in the SQL file; C7 PINS
// the uncovered six so neither closing one nor adding a ninth happens quietly.
// A list that polices itself is the difference between this defect being fixed
// and it being fixed twice more in six months.
//
// No database is touched. The real dispatcher runs against a PostgREST
// stand-in; the drift arms read sql/*.sql off disk.
//
// Exit: 0 all arms passed · 1 an arm FAILED

'use strict';

process.env.SD_AUTH_SECRET = process.env.SD_AUTH_SECRET
  || ['b28', 'photo', 'cap', 'fixture'].join('-');
process.env.SUPABASE_URL = process.env.SUPABASE_URL || 'https://test.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'test-key';

const fs = require('fs');
const path = require('path');
const { signSessionToken } = require('./_lib/auth');
const photoVal = require('./_lib/dental-photo-validation');

const REPO = path.dirname(__dirname);
const SQL_DIR = path.join(REPO, 'sql');
const SD_DATA_SRC = fs.readFileSync(path.join(__dirname, 'sd-data.js'), 'utf8');
const HASH = 'b28-cap-hash';
const KEY = 'KEY-FOR-' + HASH;

let pass = 0, fail = 0;
const failed = [];
function ok(l) { pass++; console.log('  ok    ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL  ' + l);
  if (why) console.log('        ' + String(why).slice(0, 900));
}
function is(cond, label, detail) { if (cond) ok(label); else bad(label, detail); }
function section(t) { console.log('\n' + t); }

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function eCode(res) { return (res.body && res.body.error && res.body.error.code) || ''; }
function eMsg(res) { return (res.body && res.body.error && res.body.error.message) || ''; }

function pgMock(calls) {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    calls.push({ url: u, method: method });
    if (/_employee_auth/.test(u)) {
      const m = u.match(/employee_id=eq\.([^&]+)/);
      const who = m ? decodeURIComponent(m[1]) : 'emp-1';
      return { ok: true, status: 200, json: async () => [
        { license_hash: HASH, employee_id: who, role: 'owner', active: true }] };
    }
    if (method === 'POST' || method === 'PATCH') {
      let parsed = null;
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = { id: 'X' }; }
      return { ok: true, status: 200,
               json: async () => [Array.isArray(parsed) ? parsed[0] : parsed] };
    }
    // Every GET answers ONE row, which is what the pre-read guards of both
    // branches need (dnt_appointments checks for a clash, rf_claim_photos
    // checks the claim is visible).
    return { ok: true, status: 200, json: async () => [
      { id: 'row-1', claim_id: 'CLM-1', appointment_id: 'APT-1',
        assigned_to: 'emp-1', assignee_id: 'emp-1', data: {} }] };
  };
}

function loadHandler(fetchImpl, app) {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: app })
    }
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

async function write(app, resource, role, payload) {
  const calls = [];
  const h = loadHandler(pgMock(calls), app);
  const res = mockRes();
  await h({
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + KEY,
      'x-sd-auth': signSessionToken({
        app: app, employee_id: 'emp-1', role: role, license_hash: HASH })
    },
    body: { action: 'write', resource: resource, payload: payload }
  }, res);
  return { res: res, calls: calls };
}

// A filler string of EXACTLY n bytes inside the JSON encoding. `x` encodes as
// one byte and needs no escaping, so length and byte count coincide -- which is
// the only reason a cap arm can be sized to the byte at all.
function filler(n) { return 'x'.repeat(n); }

// Grow a payload until its JSON encoding is just over / just under a target.
// SIZED BY MEASUREMENT, NEVER BY ARITHMETIC ON THE FILLER LENGTH: the rest of
// the payload contributes bytes too, and an arm that assumed otherwise would
// sit a few bytes off the boundary it claims to be testing.
function sizedTo(base, targetBytes, fillerKey) {
  let lo = 0, hi = targetBytes + 4096;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    const p = Object.assign({}, base);
    p[fillerKey] = filler(mid);
    if (Buffer.byteLength(JSON.stringify(p), 'utf8') < targetBytes) lo = mid + 1;
    else hi = mid;
  }
  const out = Object.assign({}, base);
  out[fillerKey] = filler(lo);
  return out;
}
function bytesOf(p) { return Buffer.byteLength(JSON.stringify(p), 'utf8'); }

// ── THE SQL SIDE, READ RATHER THAN REMEMBERED ───────────────────────────────
// Scans every sql/*.sql for `constraint <name>_data_size check
// (octet_length(data::text) <= N)` and returns {name: N}. The SQL file is the
// authority here, not a number in this test: an arm holding its own copy of
// 1291059 would compare the fix to itself.
function sqlDataSizeConstraints() {
  const out = {};
  for (const f of fs.readdirSync(SQL_DIR)) {
    if (!f.endsWith('.sql')) continue;
    const src = fs.readFileSync(path.join(SQL_DIR, f), 'utf8');
    const re = /constraint\s+([a-z_]+)_data_size\s+check\s*\(\s*octet_length\(data::text\)\s*<=\s*(\d+)\s*\)/g;
    let m;
    while ((m = re.exec(src)) !== null) {
      // LAST DEFINITION WINS, and that is deliberate: a size MIGRATION
      // supersedes the original schema file, and
      // sql/sairndental_appointments_photo_size_migration.sql is exactly that
      // case. Keeping the first would compare the fix against a ceiling the
      // database no longer has.
      out[m[1]] = { bytes: Number(m[2]), file: f };
    }
  }
  return out;
}

// constraint prefix -> the resource name api/sd-data.js dispatches on. Written
// out rather than derived by un-abbreviating the prefix, because `rfcph` ->
// `rf_claim_photos` and `sdqrp` -> `sd_quote_request_photos` are not
// derivable, and a guessed mapping would make a drift arm silently skip a row.
// -- CORRECTED IN b29, AND THE CORRECTION IS THE FINDING -------------------
// b28 wrote this map by un-abbreviating each constraint prefix into its TABLE
// name and treating that as the resource. THREE OF THE NINE WERE WRONG, and
// the error ran in the direction that OVERSTATES the problem -- b28's C7
// pinned "six uncovered" when three of those six are not written through this
// file's cap gate at all:
//
//   sdlocations  -> the resource is `locations`, NOT `sd_locations`
//                   (api/sd-data.js:3935/3943). tools/gate1_verify.py's own
//                   header warns about exactly this: "THE RESOURCE IS NOT THE
//                   TABLE and that is the whole trap this map exists for."
//   sdprogphoto  -> written by api/sd-sub-data.js, whose own cap is ALREADY
//                   1572864 (SUB_JOB_PAYLOAD_MAX_BYTES, :92). Never a defect.
//   sdqrp        -> written by api/stonedesk-public.js, whose MAX_PHOTO_CHARS
//                   is 1400000 and whose comment says it was sized FROM the
//                   1572864 row cap. Never a defect.
//
// And a fourth that is a different defect rather than a mis-mapping:
//   rfinv        -> `rf_invoices` has NO `action === 'write'` branch. Its
//                   writes are the custom verbs issue / add_payment /
//                   reconcile_claim / gl_export, and THE CAP GATE ONLY FIRES
//                   ON action === 'write' (api/sd-data.js:892). So it is not
//                   under-capped, it is UNCAPPED. Routed, not fixed here.
//
// NOT_GOVERNED_HERE below is the three-state answer. "Covered", "uncovered"
// and "not this gate's business" are three facts, and folding the third into
// the second is what made b28's six a six.
const PREFIX_TO_RESOURCE = {
  dntap: 'dnt_appointments',
  rfcph: 'rf_claim_photos',
  rfagr: 'rf_claim_agreements',
  rfphotos: 'rf_photos',
  rfpro: 'rf_proposals',
  sdlocations: 'locations'
};

// Oversized constraints whose rows this file's write-cap gate does NOT govern.
// Each carries WHERE it is governed instead, so the claim is checkable rather
// than asserted.
const NOT_GOVERNED_HERE = {
  rfinv: 'rf_invoices writes through custom verbs (issue, add_payment, '
       + 'reconcile_claim, gl_export); the cap gate fires only on the write '
       + 'action, so this table is UNCAPPED at the API rather than '
       + 'under-capped. api/sd-data.js:892 is the gate. ROUTED.',
  sdprogphoto: 'sd_progress_photos is written by api/sd-sub-data.js, whose '
             + 'SUB_JOB_PAYLOAD_MAX_BYTES (:92) is already 1572864 -- the same '
             + 'number as its DB constraint. Correct already.',
  sdqrp: 'sd_quote_request_photos is written by api/stonedesk-public.js, whose '
       + 'MAX_PHOTO_CHARS is 1400000 and whose comment derives it FROM the '
       + '1572864 row cap. Correct already.'
};

// The cap table as api/sd-data.js actually writes it, parsed from source.
// `PAYLOAD_CAP_BY_RESOURCE` is a module-level const and is not exported, so a
// runtime read is not available; the source IS the thing under test here.
function capTableFromSource() {
  const out = {};
  const re = /PAYLOAD_CAP_BY_RESOURCE\.([a-z_]+)\s*=\s*([^;]+);/g;
  let m;
  while ((m = re.exec(SD_DATA_SRC)) !== null) {
    const expr = m[2].trim();
    const lit = expr.match(/^(\d+)$/);
    out[m[1]] = lit
      ? Number(lit[1])
      // The one non-literal entry imports the dental module's derivation.
      // Resolved through the module rather than regexed into a number, so the
      // arm follows the same value the handler does.
      : (/STORAGE_CEILING_BYTES/.test(expr) ? photoVal.STORAGE_CEILING_BYTES : NaN);
  }
  return out;
}

const APPT = { id: 'APT-1', appointment_id: 'APT-1', patient_id: 'PT-1',
               provider_id: 'PV-1', procedure_type_id: 'PR-1',
               start_time: '2031-03-04T09:00:00Z', end_time: '2031-03-04T10:00:00Z',
               status: 'Confirmed' };
// THE VOCABULARY IS THE BRANCH'S, NOT A PLAUSIBLE ONE. `phase: 'before'` and
// `elevation: 'north'` were the first spelling and both are rejected by
// roofingClaims.validatePhoto -- so R1 measured a 400 from a field validator
// and would have read as "the write is refused" when the cap had nothing to do
// with it. The same trap api/b18-countersign-lock.test.js records for thin
// payloads: "some refusal happened" is not "this gate refused".
const RFPHOTO = { id: 'PH-1', claim_id: 'CLM-1', phase: 'tear_off',
                  elevation: 'front' };

// An ADULT date of birth. Without it the branch answers 400 GUARDIAN_REQUIRED,
// which is correct behaviour and nothing to do with a payload cap.
const PATIENT = { id: 'PT-9', patient_id: 'PT-9', first_name: 'A',
                  last_name: 'B', dob: '1980-01-01' };

(async function main() {
  const sqlCaps = sqlDataSizeConstraints();
  const capTable = capTableFromSource();

  // ═════════════════════════════════════════════════════════════════════
  section('P. THE PATIENT PHOTO BOOKING -- a 300KB photo must be actionable');
  // ═════════════════════════════════════════════════════════════════════

  // P1 IS THE REPRODUCTION. 300KB is the client's own compression target
  // (docs/superpowers/specs/2026-08-11-sairndental-photo-capture-design.md
  // §2), so this is the ordinary case and not an edge one. Before the fix this
  // answered 413 and the booking could not be confirmed OR declined.
  {
    const p = sizedTo(APPT, 300 * 1024, 'notes_filler');
    const { res } = await write('sairndental', 'dnt_appointments', 'owner', p);
    // 200 AND NOT MERELY "NOT 413". `statusCode !== 413` was the first
    // spelling and it would have gone green on a 400 from some unrelated
    // validator -- "some answer that was not a size refusal" rather than "the
    // staff member can confirm this booking", which is the claim being made.
    is(res.statusCode === 200,
       'P1. THE REPRODUCTION: a ' + bytesOf(p) + '-byte appointment write '
       + 'SUCCEEDS -- 200, so the booking is actionable',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // P2. THE CEILING IS STILL A CEILING. One byte over the DB constraint is
  // refused AT THE API, which is the whole reason to have a cap here at all:
  // a clear 413 rather than an opaque Postgres error, the trade the slabs
  // paragraph in api/sd-data.js records paying for the hard way.
  {
    const over = photoVal.STORAGE_CEILING_BYTES + 1;
    const p = sizedTo(APPT, over, 'notes_filler');
    const { res } = await write('sairndental', 'dnt_appointments', 'owner', p);
    is(res.statusCode === 413 && eCode(res) === 'PAYLOAD_TOO_LARGE',
       'P2. ' + bytesOf(p) + ' bytes, past the ' + photoVal.STORAGE_CEILING_BYTES
       + '-byte ceiling -> 413 PAYLOAD_TOO_LARGE at the API',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // P3. THE MESSAGE NAMES THE CAP THAT APPLIED. It used to read "the limit is
  // 65536 (64KB)" unconditionally; on this resource that is now false, and a
  // wrong number in a size error sends the reader to recompress against a
  // budget nobody is enforcing.
  {
    const p = sizedTo(APPT, photoVal.STORAGE_CEILING_BYTES + 1, 'notes_filler');
    const { res } = await write('sairndental', 'dnt_appointments', 'owner', p);
    is(/dnt_appointments/.test(eMsg(res))
       && eMsg(res).indexOf(String(photoVal.STORAGE_CEILING_BYTES)) !== -1
       && eMsg(res).indexOf('65536') === -1,
       'P3. the 413 names dnt_appointments and its REAL cap, and does not say '
       + '65536',
       eMsg(res));
  }

  // ═════════════════════════════════════════════════════════════════════
  section('D. THE 64KB DEFAULT IS UNCHANGED FOR EVERYTHING ELSE');
  // ═════════════════════════════════════════════════════════════════════

  // D1. The arm that would catch the fix having been written as a global
  // raise. `dnt_patients` carries `dntpt_data_size <= 65536` and stores no
  // image; raising it "for consistency" would remove a guard doing its job,
  // which is the sentence the photo-size migration already wrote down.
  {
    const p = sizedTo(PATIENT, 100 * 1024, 'blob');
    const { res } = await write('sairndental', 'dnt_patients', 'owner', p);
    is(res.statusCode === 413 && /65536/.test(eMsg(res)),
       'D1. a 100KB dnt_patients write is still refused, and still at 65536',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // D2. And under the default cap nothing changed at all.
  {
    const p = sizedTo(Object.assign({}, PATIENT, { id: 'PT-8', patient_id: 'PT-8' }),
                      10 * 1024, 'blob');
    const { res } = await write('sairndental', 'dnt_patients', 'owner', p);
    is(res.statusCode === 200,
       'D2. a 10KB dnt_patients write SUCCEEDS -- 200, the default cap is not '
       + 'refusing ordinary writes',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // ═════════════════════════════════════════════════════════════════════
  section('R. rf_claim_photos -- the dead 1.5MB handler that found this');
  // ═════════════════════════════════════════════════════════════════════

  {
    const p = sizedTo(RFPHOTO, 300 * 1024, 'image_blob');
    const { res } = await write('sairnroofing', 'rf_claim_photos', 'owner', p);
    is(res.statusCode === 200,
       'R1. a ' + bytesOf(p) + '-byte claim photo WRITES -- 200. The table was '
       + 'sized at 1.5MB for this and the API allowed 64KB',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }
  {
    const p = sizedTo(RFPHOTO, 1572864 + 1, 'image_blob');
    const { res } = await write('sairnroofing', 'rf_claim_photos', 'owner', p);
    is(res.statusCode === 413 && /rf_claim_photos/.test(eMsg(res)),
       'R2. past 1572864 -> 413, named for the resource',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // R3. THE ORDERING THAT KEEPS THE :9857 HANDLER INERT, ASSERTED. The API cap
  // must never EXCEED the DB constraint, or a refusal that is a clean 413
  // becomes an opaque Postgres error. This is the arm that makes "the dead
  // handler is a drift backstop" a fact rather than a hope.
  {
    const apiCap = capTable.rf_claim_photos;
    const dbCap = (sqlCaps.rfcph || {}).bytes;
    is(typeof apiCap === 'number' && typeof dbCap === 'number' && apiCap <= dbCap,
       'R3. the API cap for rf_claim_photos is AT OR BELOW rfcph_data_size, so '
       + 'the API refuses first and the DB message stays a backstop',
       'api=' + apiCap + ' db=' + dbCap);
  }

  // ═════════════════════════════════════════════════════════════════════
  section('B. b29 -- THE FOUR CAPS CLOSED IN b29, DRIVEN NOT DECLARED');
  // ═════════════════════════════════════════════════════════════════════

  // C6/C7 prove the cap TABLE agrees with sql/. These prove the GATE answers
  // differently because of it -- a table entry nothing reads is the inert
  // protection this suite's own comments keep warning about. Every arm here
  // was RED before the b29 entries landed, by the same stash-and-rerun
  // ablation §6 of the b29 handoff records.
  //
  // THE PAYLOADS ARE THE BRANCHES' OWN AND THEY WERE PROBED, NOT GUESSED.
  // `rf_claim_agreements` with {id, claim_id, event_type} answers 400 naming
  // five missing fields; `rf_photos` answers 400 "payload.photo_base64 is
  // required". A thin payload would make these arms measure a field validator
  // while claiming to measure a cap.
  const AGREEMENT = { id: 'AG-1', claim_id: 'CLM-1', event_type: 'executed',
                      signer_name: 'A Homeowner', signature_data: 'data:,sig',
                      signing_venue: 'buyer_residence',
                      executed_at: '2026-10-19', state: 'OH' };
  const RFPHOTO2 = { id: 'PH-9', job_id: 'JOB-1', photo_base64: 'data:,x' };
  const PROPOSAL = { id: 'PR-9', job_id: 'JOB-1', event_type: 'issued',
                     issued_on: '2026-10-19',
                     line_items: [{ description: 'tear-off', amount: 1000 }] };
  const LOCATION = { id: 'LOC-9', name: 'Yard A' };

  for (const t of [
    { app: 'sairnroofing', resource: 'rf_claim_agreements', base: AGREEMENT,
      cap: 1572864, key: 'notes_filler',
      why: 'its schema says a captured signature "must not be squeezed into '
         + 'the 64KB ceiling" -- and it was' },
    { app: 'sairnroofing', resource: 'rf_proposals', base: PROPOSAL,
      cap: 1572864, key: 'notes_filler', why: 'line items plus a snapshot' },
    { app: 'sairnroofing', resource: 'rf_photos', base: RFPHOTO2,
      cap: 1572864, key: 'photo_base64', why: 'a measurement photograph' },
    { app: 'stonedesk', resource: 'locations', base: LOCATION,
      cap: 16384, key: 'notes_filler',
      why: 'THE ONE THAT WENT DOWN: 16384 is its own constraint and the API '
         + 'was permitting four times it' }
  ]) {
    // UNDER the cap -> it writes.
    {
      const under = Math.min(300 * 1024, Math.floor(t.cap / 2));
      const pay = sizedTo(t.base, under, t.key);
      const { res } = await write(t.app, t.resource, 'owner', pay);
      is(res.statusCode === 200,
         'B1[' + t.resource + ']. ' + bytesOf(pay) + ' bytes WRITES (200) -- '
         + t.why,
         res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
    }
    // ONE BYTE OVER -> 413, and the message names this resource and this cap.
    {
      const pay = sizedTo(t.base, t.cap + 1, t.key);
      const { res } = await write(t.app, t.resource, 'owner', pay);
      is(res.statusCode === 413 && eCode(res) === 'PAYLOAD_TOO_LARGE'
         && eMsg(res).indexOf(String(t.cap)) !== -1
         && eMsg(res).indexOf(t.resource) !== -1,
         'B2[' + t.resource + ']. ' + bytesOf(pay) + ' bytes -> 413 naming '
         + t.resource + ' and ' + t.cap,
         res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
    }
  }

  // B3. THE ONE THAT MATTERS MOST FOR `locations`, BECAUSE ITS CAP WENT DOWN:
  // a payload between the new cap and the old default must now be REFUSED.
  // Before b29 a 40KB yard record was accepted here and then refused by
  // Postgres with an opaque error -- the slabs failure in the direction that
  // paragraph did not consider.
  {
    const pay = sizedTo(LOCATION, 40 * 1024, 'notes_filler');
    const { res } = await write('stonedesk', 'locations', 'owner', pay);
    is(res.statusCode === 413 && /16384/.test(eMsg(res)),
       'B3. a 40KB `locations` write -- accepted by this API before b29 and '
       + 'refused by Postgres -- is now refused HERE, at 16384, with a clear '
       + '413',
       res.statusCode + ' ' + eCode(res) + ' ' + eMsg(res));
  }

  // ═════════════════════════════════════════════════════════════════════
  section('C. THE CAP TABLE POLICES ITSELF AGAINST sql/');
  // ═════════════════════════════════════════════════════════════════════

  // C5. The scan found something at all. Without this, every arm below would
  // pass vacuously the day the regex stops matching -- item 8 of the
  // cross-domain disciplines, the check that quietly stops checking.
  {
    const n = Object.keys(sqlCaps).length;
    is(n >= 20,
       'C5. the SQL scan found ' + n + ' data-size constraints (>= 20), so the '
       + 'arms below are reading something',
       JSON.stringify(Object.keys(sqlCaps)).slice(0, 200));
  }

  // C6. EVERY COVERED CAP EQUALS THE NUMBER IN THE SQL FILE.
  {
    const problems = [];
    for (const [resource, apiCap] of Object.entries(capTable)) {
      const prefix = Object.keys(PREFIX_TO_RESOURCE)
        .find((k) => PREFIX_TO_RESOURCE[k] === resource);
      if (!prefix) { problems.push(resource + ': no constraint prefix mapped'); continue; }
      const db = sqlCaps[prefix];
      if (!db) { problems.push(resource + ': no ' + prefix + '_data_size in sql/'); continue; }
      if (apiCap !== db.bytes) {
        problems.push(resource + ': api=' + apiCap + ' but ' + prefix
          + '_data_size=' + db.bytes + ' in ' + db.file);
      }
    }
    is(Object.keys(capTable).length >= 2 && problems.length === 0,
       'C6. all ' + Object.keys(capTable).length + ' cap-table entries equal '
       + 'their DB constraint exactly',
       problems.join(' | '));
  }

  // C7. THE PIN, REWRITTEN IN b29 AND NOW A THREE-STATE PIN.
  //
  // b28's version pinned a SET of six "uncovered" oversized tables. Three of
  // those six were never this gate's business, and one of the remaining three
  // is uncapped by a different mechanism -- see PREFIX_TO_RESOURCE above for
  // the measurement. So the pin now has two lists, and an oversized constraint
  // in NEITHER is a finding: it means a table grew a large row cap and nobody
  // decided which gate governs it.
  //
  // THE POINT IS UNCHANGED. Closing one, or a new oversized constraint
  // arriving, still turns this red and still costs somebody a sentence.
  const EXPECTED_UNCOVERED = [];
  {
    const uncovered = [];
    for (const [prefix, db] of Object.entries(sqlCaps)) {
      if (db.bytes <= 65536) continue;
      if (NOT_GOVERNED_HERE[prefix]) continue;
      const resource = PREFIX_TO_RESOURCE[prefix];
      if (!resource) { uncovered.push('UNMAPPED:' + prefix); continue; }
      if (!(resource in capTable)) uncovered.push(resource);
    }
    uncovered.sort();
    is(JSON.stringify(uncovered) === JSON.stringify(EXPECTED_UNCOVERED),
       'C7. every oversized constraint this gate governs now HAS a cap entry, '
       + 'and the three it does not govern are declared with where they are '
       + 'governed instead',
       'found ' + JSON.stringify(uncovered) + '\n        expected '
       + JSON.stringify(EXPECTED_UNCOVERED));
  }

  // C7b. THE DECLARED EXEMPTIONS MUST STILL BE OVERSIZED, which is what stops
  // NOT_GOVERNED_HERE becoming a place to hide a table. If one drops to 64KB
  // or below its entry is stale; if a prefix in it is not in sql/ at all, the
  // entry is about nothing.
  {
    const stale = [];
    for (const prefix of Object.keys(NOT_GOVERNED_HERE)) {
      const db = sqlCaps[prefix];
      if (!db) { stale.push(prefix + ': no ' + prefix + '_data_size in sql/'); continue; }
      if (db.bytes <= 65536) {
        stale.push(prefix + ': now ' + db.bytes + ' bytes, no longer oversized '
                   + '-- remove the exemption');
      }
    }
    is(stale.length === 0,
       'C7b. all ' + Object.keys(NOT_GOVERNED_HERE).length + ' declared '
       + 'not-governed-here entries are still real and still oversized',
       stale.join(' | '));
  }

  // C8. REWRITTEN IN b29: `locations` is now IN the table, and LOWER.
  //
  // b28 kept it out, correctly for b28: its constraint is 16384, so the API
  // permitted FOUR TIMES what the database accepts, and a fix here LOWERS a
  // cap rather than raising one -- which can refuse a write that works today.
  // Michael's b29 decision is that 16384 is the intended number.
  //
  // AND LOWERING IT CANNOT REFUSE AN EXISTING ROW, which had to be established
  // before touching it. Not by sampling -- BY CONSTRUCTION:
  // `sdlocations_data_size check (octet_length(data::text) <= 16384)` means
  // Postgres has refused every row above 16384 for as long as the constraint
  // has existed, so no stored row can be over it. A live read on SD-AUDIT-2026
  // agreed and added nothing: the table answered `provisioned: false`, zero
  // rows, which is a could-not-tell about other licences and is recorded as
  // one rather than as a clean measurement.
  //
  // THE RESOURCE IS `locations`, NOT `sd_locations`. An entry under the table
  // name would be INERT, because the gate is keyed on the dispatched resource
  // -- and inert protection is this platform's least favourite shape.
  {
    const db = (sqlCaps.sdlocations || {}).bytes;
    is(db === 16384 && capTable.locations === 16384,
       'C8. `locations` is capped at its own 16384-byte DB constraint, under '
       + 'the resource name the dispatcher uses -- the API no longer '
       + 'over-permits',
       'db=' + db + ' apiCap=' + capTable.locations);
  }

  // C9. THE PROTOTYPE ARM. The table is indexed by a client-supplied resource
  // name. On a plain object literal `PAYLOAD_CAP_BY_RESOURCE['constructor']`
  // is a FUNCTION, `payloadBytes > thatFunction` is `false`, and the cap is
  // silently disabled by a resource name. Inert today only because the
  // envelope gate whitelists the resource first -- which is exactly how all 48
  // literals tests/role_maps_have_no_prototype.js was built for were inert.
  {
    is(/PAYLOAD_CAP_BY_RESOURCE\s*=\s*Object\.create\(null\)/.test(SD_DATA_SRC),
       'C9. the cap table is built with Object.create(null), so no inherited '
       + 'name can be read as a cap',
       'not found in api/sd-data.js');
  }

  console.log('\n' + (fail ? 'FAILED' : 'PASSED') + ' -- ' + pass + ' passed, '
    + fail + ' failed'
    + (fail ? '\nFAILING ARMS: ' + failed.join(', ') : ''));
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  console.error('HARNESS ERROR -- no verdict was reached, which is NOT a pass');
  console.error(e);
  process.exit(1);
});
