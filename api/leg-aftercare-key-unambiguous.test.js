// api/leg-aftercare-key-unambiguous.test.js
//
// Run:  node api/leg-aftercare-key-unambiguous.test.js
//
// F4 and F5 from fourth's b20 review
// (docs/2026-10-14-fourth-b20-leg-role-matrix-discharge.md), both routed to
// hank.
//
//   F4  THE leg_aftercare KEY IS DELIMITER-AMBIGUOUS. `checkin_type` is
//       normalised to A-Z0-9 with `-` as the separator, `case_id` is passed
//       through with trim() alone, and `-` is BOTH the joiner and the
//       normaliser's output character -- so the boundary between the two
//       fields is not recoverable:
//
//         {case_id:'CS-7',   checkin_type:'1 Week'}  ->  AC-CS-7-1-WEEK
//         {case_id:'CS-7-1', checkin_type:'Week'}    ->  AC-CS-7-1-WEEK
//
//       The upsert is on_conflict=license_hash,aftercare_id with
//       merge-duplicates, so a collision SILENTLY OVERWRITES a different
//       case's check-in and returns 200.
//
//       NOT reachable through the shipped UI -- the type comes from a fixed
//       three-element plan and case ids are newId('CS') = 'CS-'+Date.now()+
//       '-'+digits, always three segments -- but reachable by any licence-key
//       holder posting directly, and by any future creation path with a
//       free-text type. The code's own comment rests on exactly that
//       assumption: "(case_id, checkin_type) is unique by construction".
//
//   F5  THE SERVER-SIDE CANONICALISATION LEAVES A LOCAL DUPLICATE on the very
//       device it was built to protect. sdnData() marks the CLIENT's id as
//       synced and discards the server's rewritten one, so an un-upgraded
//       device keeps the random id locally, the next hydrate pulls the
//       canonical row, fails to match it, and pushes it as a SECOND local
//       row. One check-in, two local rows -- which is the duplicate
//       grief-follow-up symptom the fix exists to prevent.
//
// THE ARMS DRIVE BOTH REAL COPIES. The server's derivation through the real
// api/sd-data.js handler; the client's by EXTRACTING the functions from
// sairnlegacy.html and running them in a vm with a stubbed store. A
// reimplementation of either would pass against the unfixed code.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.join(__dirname, '..');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['legac', 'fixture', String(process.pid)].join('-');
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const KEY = 'k';
const HASH = crypto.createHash('sha256').update(KEY).digest('hex');

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 400));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

function mockRes() {
  const r = { statusCode: null, body: null };
  r.status = (c) => { r.statusCode = c; return r; };
  r.json = (b) => { r.body = b; return r; };
  return r;
}
require.cache[require.resolve('./_lib/license')] = {
  id: require.resolve('./_lib/license'),
  filename: require.resolve('./_lib/license'),
  loaded: true,
  exports: {
    validateLicenseKey: async () => ({
      valid: true, active: true, license_hash: HASH,
      trial_ends_at: null, stripe_subscription_id: null, app_id: 'sairnlegacy' })
  }
};
const { signSessionToken } = require('./_lib/auth');
delete require.cache[require.resolve('./sd-data.js')];
const handler = require('./sd-data.js');

function legFetch() {
  return async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    if (/_employee_auth\?/.test(u)) {
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [{ license_hash: HASH, employee_id: 'E1',
                                    role: 'owner', active: true }] };
    }
    if (method !== 'GET') {
      return { ok: true, status: 200, headers: { get: () => '' },
               text: async () => '[]',
               json: async () => [JSON.parse(init.body)] };
    }
    return { ok: true, status: 200, headers: { get: () => '' },
             text: async () => '[]', json: async () => [] };
  };
}
// THE SERVER'S OWN DERIVATION, read off the real handler's answer rather than
// recomputed here. `payload.id` goes in as a random value and comes back as
// whatever the branch decided the key is.
async function serverKey(caseId, type, idIn) {
  global.fetch = legFetch();
  const res = mockRes();
  const payload = { id: idIn === undefined ? 'RANDOM-' + Math.random() : idIn };
  if (caseId !== undefined) payload.case_id = caseId;
  if (type !== undefined) payload.checkin_type = type;
  await handler({ method: 'POST',
    headers: { authorization: 'Bearer ' + KEY,
               'x-sd-auth': signSessionToken({ app: 'sairnlegacy',
                 employee_id: 'E1', role: 'owner', license_hash: HASH }) },
    body: { action: 'write', resource: 'leg_aftercare', app_id: 'sairnlegacy',
            payload: payload } }, res);
  return (res.body && res.body.data && res.body.data.id) !== undefined
    ? res.body.data.id : null;
}

// ── THE CLIENT HALF, EXTRACTED AND RUN ──────────────────────────────────────
// Not read by eye and not reimplemented. Each named function is lifted out of
// sairnlegacy.html at column 0 and evaluated in a vm with a stubbed
// localStorage, which is how the SAIRNfreedom delete defects were driven in
// b12.
const HTML = (function () {
  try { return fs.readFileSync(path.join(ROOT, 'sairnlegacy.html'), 'utf8'); }
  catch (e) { return null; }
})();
function lift(name) {
  if (HTML === null) return null;
  const re = new RegExp('\\nfunction ' + name + '\\([^)]*\\)\\{[\\s\\S]*?\\n\\}');
  const m = HTML.match(re);
  return m ? m[0] : null;
}
function clientWorld(names) {
  const src = [];
  const missing = [];
  names.forEach(function (n) {
    const s = lift(n);
    if (s === null) missing.push(n); else src.push(s);
  });
  if (missing.length) return { missing: missing };
  const store = {};
  const sandbox = {
    console: console,
    localStorage: {
      getItem: (k) => (store[k] === undefined ? null : store[k]),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; }
    },
    APP_ID: 'sairnlegacy',
    DATA_API: 'https://example.invalid/api/sd-data',
    LEG_SYNCED_KEY: 'leg_synced_ids',
    legSession: null,
    legLastErr: {},
    legFetchTimeoutSignal: function () { return undefined; },
    toast: function () {},
    fetch: null,
    __store: store
  };
  vm.createContext(sandbox);
  try { vm.runInContext(src.join('\n'), sandbox); }
  catch (e) { return { error: e }; }
  return { sandbox: sandbox, store: store };
}

console.log('F4/F5. the leg_aftercare key, and the id the device keeps\n');

(async () => {
  // ── F4.1 THE COLLIDING PAIR, SERVER SIDE ────────────────────────────────
  console.log('F4. two different records cannot derive one key');
  {
    const k1 = await serverKey('CS-7', '1 Week');
    const k2 = await serverKey('CS-7-1', 'Week');
    is(k1 !== k2,
       'F4a. THE ARM THE FINDING IS -- (\'CS-7\',\'1 Week\') and '
     + '(\'CS-7-1\',\'Week\') derive DIFFERENT keys. They used to derive the '
     + 'same one, and the upsert is merge-duplicates, so one case\'s check-in '
     + 'silently overwrote another\'s and returned 200',
       'k1=' + k1 + ' k2=' + k2);
    is(k1 !== k2 && typeof k1 === 'string' && typeof k2 === 'string'
       && k1.length > 3 && k2.length > 3,
       'F4b. ...and both are still real keys. "Make them different" is also '
     + 'satisfied by returning null for one of them, which would break the '
     + 'de-duplication the key exists for',
       'k1=' + JSON.stringify(k1) + ' k2=' + JSON.stringify(k2));
  }
  {
    // A SMALL ADVERSARIAL TABLE, not one pair. The pair above is the one
    // fourth found; the question is whether the SCHEME is unambiguous.
    const pairs = [
      ['CS-7', '1 Week'], ['CS-7-1', 'Week'], ['CS-7-1-WEEK', ''],
      ['CS', '7-1-Week'], ['CS-7', '1-Week'], ['CS-7', '1  Week'],
      ['CS-1760000000000-123', '1 Week'], ['CS-1760000000000-123', '1 Month'],
      ['CS-1760000000000-123', '1 Year'], ['CS-1760000000000-124', '1 Week'],
      ['CS-1760000000000', '123-1 Week'], ['cs-7', '1 Week'],
      ['CS-7 ', '1 Week'], ['CS--7', '1 Week'], ['CS-7', 'ad hoc check-in'],
      ['CS-7', 'AD-HOC-CHECK-IN']
    ];
    // ── "DISTINCT" MEANS DISTINCT AFTER THE DECLARED NORMALISATION ────────
    // Two normalisations are DELIBERATE and predate this fix: case_id is
    // trimmed, and checkin_type is upper-cased with every run of non-A-Z0-9
    // collapsed to one `-`. So '1 Week', '1-Week' and '1  Week' ARE the same
    // check-in type and must share a key -- that is the de-duplication the key
    // exists for. The first draft of this arm compared RAW pairs and reported
    // those as collisions, which is the arm failing about the fixture rather
    // than finding anything. Ambiguity is what is measured here; type
    // normalisation is asserted separately in F4j.
    const normType = (s) => String(s).trim().toUpperCase()
      .replace(/[^A-Z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    const seen = {};
    const collisions = [];
    for (const p of pairs) {
      const k = await serverKey(p[0], p[1], 'SENT-ID');
      const norm = JSON.stringify([String(p[0]).trim(), normType(p[1])]);
      if (seen[k] !== undefined && seen[k] !== norm) {
        collisions.push(k + ' <- ' + seen[k] + ' AND ' + norm);
      }
      seen[k] = norm;
    }
    is(collisions.length === 0,
       'F4c. no two DISTINCT (case_id, normalised checkin_type) pairs in a '
     + '16-row adversarial table derive one key -- including a case id that '
     + 'swallows a type fragment, a type that looks like a case segment, and '
     + 'an empty type',
       JSON.stringify(collisions));
    const a = await serverKey('CS-7', '1 Week');
    const b = await serverKey('CS-7', '1-Week');
    const c = await serverKey('CS-7', '1  week');
    is(a === b && b === c,
       'F4j. ...and the TYPE normalisation is still deliberate: \'1 Week\', '
     + '\'1-Week\' and \'1  week\' are one check-in type and share one key. '
     + 'That is the de-duplication the key exists for, and a fix that made '
     + 'them three keys would be three follow-ups to one family',
       'a=' + a + ' b=' + b + ' c=' + c);
  }

  // ── F4.2 EXISTING IDS ARE NOT BROKEN ────────────────────────────────────
  console.log('\nF4. and the ids the shipped app has already written are unchanged');
  {
    // THE ONLY PAIRS THE SHIPPED APP CAN PRODUCE. newId('CS') is
    // 'CS-'+Date.now()+'-'+Math.floor(Math.random()*1000) -- three segments,
    // digits only -- and generateAftercareSchedule writes exactly three fixed
    // types. Read off sairnlegacy.html:1561 and :4240, not assumed.
    const real = 'CS-1760000000000-123';
    const got = {};
    for (const t of ['1 Week', '1 Month', '1 Year']) got[t] = await serverKey(real, t);
    is(got['1 Week'] === 'AC-' + real + '-1-WEEK'
       && got['1 Month'] === 'AC-' + real + '-1-MONTH'
       && got['1 Year'] === 'AC-' + real + '-1-YEAR',
       'F4d. THE PRESERVATION ARM -- a real generated case id with each of the '
     + 'three standard types still derives the EXACT historic key, byte for '
     + 'byte. Any scheme that changes these orphans every aftercare row in '
     + 'production: the next write lands on a new row and the old one is '
     + 'stranded, which is the duplicate this key exists to prevent',
       JSON.stringify(got));
    is(got['1 Week'] !== got['1 Month'] && got['1 Month'] !== got['1 Year']
       && got['1 Week'] !== got['1 Year'],
       'F4e. CONTROL -- the three standard types on one case are three keys. '
     + 'Without this, "collapse everything to one row" passes F4d',
       JSON.stringify(got));
    const other = await serverKey('CS-1760000000000-124', '1 Week');
    is(other !== got['1 Week'],
       'F4f. CONTROL -- two different real cases with the SAME type are two '
     + 'keys. This is the direction fourth measured as uncovered: the existing '
     + 'arms proved different-type-same-case and nothing proved '
     + 'different-case',
       'other=' + other);
  }
  {
    const kept = await serverKey(undefined, undefined, 'AC-KEEP-ME');
    is(kept === 'AC-KEEP-ME',
       'F4g. CONTROL -- a payload missing case_id or checkin_type keeps its '
     + 'own id. A key built from a missing field collides with every other row '
     + 'missing the same field, which is worse than the bug being fixed',
       String(kept));
    const upper = await serverKey('CS-7', '1 Week');
    const lower = await serverKey('cs-7', '1 Week');
    is(upper !== lower,
       'F4h. case_id is NOT case-folded, and that is a DECISION recorded as an '
     + 'arm rather than left to drift. fourth flagged the fold as the same '
     + 'class; folding only here would make the key say two cases are one '
     + 'while every other comparison in sairnlegacy.html (`a.case_id===caseId`) '
     + 'says they are two. Whether case ids should be case-insensitive at all '
     + 'is a product question and is routed, not answered in a key derivation',
       'upper=' + upper + ' lower=' + lower);
  }

  // ── F4.3 THE TWO COPIES STILL AGREE ─────────────────────────────────────
  console.log('\nF4. the client copy and the server copy agree on every pair');
  {
    const w = clientWorld(['legAcEsc', 'legAftercareId']);
    if (w.missing) {
      cannot('F4i. legAftercareId() was not found in sairnlegacy.html, so the '
           + 'two derivations could not be compared', w.missing.join(','));
    } else if (w.error) {
      cannot('F4i. the extracted client function would not run', String(w.error));
    } else {
      const pairs = [['CS-7', '1 Week'], ['CS-7-1', 'Week'],
                     ['CS-1760000000000-123', '1 Week'],
                     ['CS-1760000000000-123', '1 Year'],
                     ['CS 9', 'ad hoc  check-in'], ['cs-7', '1 Week'],
                     ['CS--7', ''], ['CS-7', 'AD-HOC']];
      const disagree = [];
      for (const p of pairs) {
        const sent = 'SENT-ID';
        const s = await serverKey(p[0], p[1], sent);
        const c = w.sandbox.legAftercareId(p[0], p[1]);
        // THE CONTRACT IS "SAME KEY, OR BOTH DECLINE". The client returns null
        // where the server leaves the caller's id alone; comparing the two
        // strings directly would read a correctly-matched refusal as a
        // disagreement, which is the arm failing about itself.
        const expected = c === null ? sent : c;
        if (s !== expected) {
          disagree.push(JSON.stringify(p) + ' server=' + s + ' client=' + c);
        }
      }
      is(disagree.length === 0,
         'F4i. the CLIENT\'s legAftercareId() and the SERVER\'s derivation '
       + 'produce the same key for all eight pairs, INCLUDING the colliding '
       + 'one. Two copies of a key derivation is convention 7\'s drift risk '
       + 'and there is no way to share one function between a static page and '
       + 'a serverless handler, so they are extracted and RUN against each '
       + 'other rather than compared by eye',
         JSON.stringify(disagree));
    }
  }

  // ── F5. THE DEVICE ADOPTS THE SERVER'S ID ───────────────────────────────
  console.log('\nF5. the un-upgraded device stops keeping a second local row');
  {
    const w = clientWorld(['st', 'ld', 'legSyncedRead', 'legMarkSynced',
                           'legAdoptServerId', 'legLicenseKey', 'sdnData']);
    if (w.missing) {
      // A MISSING FUNCTION IS A FAIL, NOT AN UNPROVEN. "The fix is not there"
      // and "I could not measure it" are different answers and only one of
      // them is this suite's job to report.
      bad('F5a. the client-side functions F5 needs are not all present in '
        + 'sairnlegacy.html -- the fix has not landed',
          'missing: ' + w.missing.join(', '));
      bad('F5b. depends on F5a', 'missing: ' + w.missing.join(', '));
      bad('F5c. depends on F5a', 'missing: ' + w.missing.join(', '));
      bad('F5d. depends on F5a', 'missing: ' + w.missing.join(', '));
    } else if (w.error) {
      cannot('F5a. the extracted client functions would not run', String(w.error));
    } else {
      const sb = w.sandbox;
      sb.localStorage.setItem('leg_license_key', KEY);
      // ONE local row with a RANDOM id -- the un-upgraded-device state, which
      // is the whole subject of F5.
      const RAND = 'AC-1760000000000-abc';
      const CANON = 'AC-CS-1760000000000-123-1-WEEK';
      function serverReplies(serverId) {
        sb.fetch = function () {
          return Promise.resolve({ ok: true, status: 200,
            json: function () {
              return Promise.resolve({ ok: true, data: { id: serverId,
                case_id: 'CS-1760000000000-123', checkin_type: '1 Week' } });
            } });
        };
      }
      sb.st('leg_aftercare', [{ id: RAND, case_id: 'CS-1760000000000-123',
                                checkin_type: '1 Week', status: 'Pending' }]);
      serverReplies(CANON);
      await sb.sdnData('write', 'leg_aftercare',
        { id: RAND, case_id: 'CS-1760000000000-123', checkin_type: '1 Week' });
      let rows = sb.ld('leg_aftercare', []);
      is(rows.length === 1 && rows[0].id === CANON,
         'F5a. after a write the server CANONICALISED, the local row carries '
       + 'the SERVER\'s id and there is still exactly one row. It used to keep '
       + 'the random id: the next hydrate pulls the canonical row, fails to '
       + 'match it, and pushes it as a second local row -- one check-in, two '
       + 'grief-support follow-ups to a bereaved family',
         JSON.stringify(rows).slice(0, 200));
      let synced = JSON.parse(sb.localStorage.getItem('leg_synced_ids') || '{}');
      const arr = (synced.leg_aftercare || []).map(String);
      is(arr.indexOf(CANON) !== -1,
         'F5b. ...and it is the SERVER\'s id that is marked synced. Marking '
       + 'the client\'s meant the record the server actually holds had no '
       + 'recorded permission to be overwritten by a hydrate, which is the '
       + 'server-wins carve-out reading the wrong id',
         JSON.stringify(synced));
      // THE ALREADY-CONVERGED CASE. A device that has both rows -- the random
      // one it wrote and the canonical one a hydrate brought down -- must end
      // with ONE, because the server has said they are the same record.
      sb.st('leg_aftercare', [
        { id: CANON, case_id: 'CS-1760000000000-123', checkin_type: '1 Week',
          status: 'Pending' },
        { id: RAND, case_id: 'CS-1760000000000-123', checkin_type: '1 Week',
          status: 'Pending' }]);
      serverReplies(CANON);
      await sb.sdnData('write', 'leg_aftercare',
        { id: RAND, case_id: 'CS-1760000000000-123', checkin_type: '1 Week' });
      rows = sb.ld('leg_aftercare', []);
      is(rows.length === 1 && rows[0].id === CANON,
         'F5c. ...and a device that ALREADY has both rows ends with one. The '
       + 'server merged them into a single row, so keeping both locally is the '
       + 'duplicate surviving the fix that was supposed to remove it',
         JSON.stringify(rows).slice(0, 200));
      // CONTROL. When the server returns the SAME id -- every resource except
      // this one -- nothing may move.
      sb.st('leg_cases', [{ id: 'CS-9', decedent_name: 'A' }]);
      sb.fetch = function () {
        return Promise.resolve({ ok: true, status: 200,
          json: function () { return Promise.resolve({ ok: true, data: { id: 'CS-9' } }); } });
      };
      await sb.sdnData('write', 'leg_cases', { id: 'CS-9', decedent_name: 'A' });
      const cases = sb.ld('leg_cases', []);
      synced = JSON.parse(sb.localStorage.getItem('leg_synced_ids') || '{}');
      is(cases.length === 1 && cases[0].id === 'CS-9'
         && (synced.leg_cases || []).map(String).indexOf('CS-9') !== -1,
         'F5d. CONTROL -- when the server returns the same id, the row and the '
       + 'synced map are exactly as before. 57 call sites go through this '
       + 'transport and only leg_aftercare rewrites an id; a change that '
       + 'touched the other 56 would be the blast radius nobody asked for',
         'cases=' + JSON.stringify(cases) + ' synced=' + JSON.stringify(synced));
    }
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log(failed.length + ' ARM(S) FAILED: ' + failed.join(', '));
  if (notProved.length) console.log(notProved.length + ' ARM(S) UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
})().catch((e) => { console.error(e); process.exit(1); });
