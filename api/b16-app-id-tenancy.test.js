// api/b16-app-id-tenancy.test.js
//
// Run:  node api/b16-app-id-tenancy.test.js
//
// REQUIREMENT: `memory` is the ONLY resource in api/sd-data.js whose `app_id`
//   is chosen by the CALLER. A caller must not be able to stamp app B on a
//   memory row while holding a session signed for app A.
//
// ── WHY THIS SUITE EXISTS, AND WHAT IT IS NOT ─────────────────────────────
// cody's docs/2026-10-15-cody-b16-app-id-tenancy.md REFUTED the reported
// tenancy defect. `tests/sairnlegacy_fault_probe.py` arm 8's label
// "app_id is taken from the client again" is a MUTATION label -- the defect
// the probe PLANTS -- not one it found. Measured against the handler: 116
// `app_id:` writes are the server's own string literals and exactly one is
// not.
//
// THERE IS THEREFORE NO RED-THEN-GREEN HERE AND THIS SUITE DOES NOT PRETEND
// TO ONE. The code is already correct. What was missing is the thing that
// would notice if it stopped being correct, and that gap is specific and
// measurable:
//
//     api/sd-data.js:1930   const memApp = String((body && body.app_id) || 'stonedesk');
//     api/sd-data.js:2137   const gateApp = (resource === 'memory') ? memApp : ...
//                           ^^^^ 207 lines apart, and nothing asserted they follow each other
//
// (cody's doc cites the gate at :2113 and calls it 429 lines away. Both were
// true when it was written; b16 added a comment block at :2041 and the line is
// now :2137. The citation is RE-DERIVED here rather than copied, because a
// line number in a test header is the first thing to rot.)
//
// cody's own words, quoted as written: "If that one line at :2113 is ever
// simplified to a fixed app while the row keeps `app_id: memApp`, this becomes
// a real cross-app write and no arm would notice." T6 is that sentence driven:
// the line IS simplified, in a copy, and T1 is re-run to see whether it
// notices.
//
// ── THE RED EVIDENCE IS THE ABLATION, NOT A PRE-FIX TREE ──────────────────
// Per docs/2026-09-13-cross-domain-disciplines.md item 12 -- remove ONE named
// layer from already-clean code and measure what IT alone catches, per ARM
// rather than per exit code. Two layers are ablated separately:
//
//     T6  :2137 `gateApp`        -> expected to FLIP T1 (403 -> not 403)
//     T7  :2016 `preExpectedApp` -> expected NOT to flip T1
//
// T7 is reported as a finding rather than dropped for being negative: the
// active-credential pre-gate derives the same expected app and NO behavioural
// arm in this suite covers it, so for that line T5's structural check is the
// only guard there is. Saying so is the point; a suite that only prints the
// layer it does cover reads as though it covered both.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b16', 'fixture', String(process.pid)].join('-');
process.env.SUPABASE_URL = 'https://fake.supabase.co';
process.env.SUPABASE_SERVICE_ROLE_KEY = 'fake-service-key';

const SRC = path.join(__dirname, 'sd-data.js');
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

// ── THE DRIVER ────────────────────────────────────────────────────────────
// Drives the REAL handler module (or a named mutant of it) through a real
// signed session. Nothing about the gate is modelled here: the token is
// produced by api/_lib/auth.js's own signSessionToken and verified by the
// handler's own verifySessionToken.
//
// `writes` captures every non-GET upstream call so an arm can assert not just
// the status code but that NO ROW WAS WRITTEN -- a 403 with a row already in
// the table would be the same failure wearing a refusal.
async function drive(modulePath, opts) {
  const licApp = opts.licApp;
  const sessApp = opts.sessApp;
  const writes = [];

  const licResolved = require.resolve('./_lib/license');
  const prevLic = require.cache[licResolved];
  require.cache[licResolved] = {
    id: licResolved, filename: licResolved, loaded: true,
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH,
        trial_ends_at: null, stripe_subscription_id: null, app_id: licApp })
    }
  };

  const prevFetch = global.fetch;
  global.fetch = async function (url, init) {
    const u = String(url);
    const method = (init && init.method) || 'GET';
    const res200 = (rows) => ({ ok: true, status: 200, headers: { get: () => '' },
      text: async () => JSON.stringify(rows), json: async () => rows });
    if (/_employee_auth\?/.test(u)) {
      return res200([{ license_hash: HASH, employee_id: 'S1',
                       role: 'owner', active: true }]);
    }
    if (/business_profiles\?/.test(u)) return res200([{ shop_id: 'SHOP1' }]);
    if (method !== 'GET') {
      let parsed = null;
      try { parsed = JSON.parse(init.body); } catch (e) { parsed = String(init.body); }
      writes.push({ url: u, method: method, body: parsed });
      return res200([parsed]);
    }
    return res200([]);
  };

  let handler, out = { statusCode: null, body: null };
  try {
    delete require.cache[require.resolve(modulePath)];
    handler = require(modulePath);
    const { signSessionToken } = require('./_lib/auth');
    const res = out;
    res.status = (c) => { res.statusCode = c; return res; };
    res.json = (b) => { res.body = b; return res; };
    const body = { action: 'write', resource: 'memory',
                   payload: { note: 'b16 tenancy fixture' } };
    if ('bodyAppId' in opts) body.app_id = opts.bodyAppId;
    await handler({ method: 'POST',
      headers: { authorization: 'Bearer ' + KEY,
                 'x-sd-auth': signSessionToken({ app: sessApp, employee_id: 'S1',
                   role: 'owner', license_hash: HASH }) },
      body: body }, res);
  } finally {
    global.fetch = prevFetch;
    if (prevLic) require.cache[licResolved] = prevLic;
    else delete require.cache[licResolved];
  }
  const memWrites = writes.filter((w) => /ai_memories/.test(w.url));
  return { status: out.statusCode, body: out.body,
           writes: writes, memWrites: memWrites,
           wroteApp: memWrites.length ? memWrites[0].body.app_id : null };
}

// ── THE MUTANT, same directory so `./_lib/...` still resolves ─────────────
// api/claude-guardrail-metamorphic.test.js's note applies verbatim: a require
// failure exits non-zero exactly like a sabotage that worked, so the mutant
// must land in api/ under a unique name and be removed in a finally. The
// anchor is checked for EXACTLY ONE occurrence before anything is replaced --
// a zero-match plant is the anchor-rot failure cody just finished diagnosing,
// and it reports as a pass.
async function ablate(anchor, replacement, tag, run) {
  const src = fs.readFileSync(SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 1) return { ok: false, why: 'anchor occurs ' + n + ' times, not 1: ' + anchor };
  const mutPath = path.join(__dirname, '_b16mut_' + tag + '_' + process.pid + '.js');
  fs.writeFileSync(mutPath, src.split(anchor).join(replacement));
  try {
    const back = fs.readFileSync(mutPath, 'utf8');
    if (back.indexOf(replacement) === -1) {
      return { ok: false, why: 'the mutant did not land on disk' };
    }
    const r = await run('./' + path.basename(mutPath));
    return { ok: true, result: r };
  } finally {
    try { delete require.cache[mutPath]; } catch (e) { /* not loaded */ }
    try { fs.unlinkSync(mutPath); } catch (e) { /* already gone */ }
  }
}

const A_GATE = "const gateApp = (resource === 'memory') ? memApp";
const A_PREGATE = "const preExpectedApp = (resource === 'memory') ? memApp";

async function main() {
  console.log('api/b16-app-id-tenancy.test.js');
  console.log('  the one client-chosen app_id in a 116-write handler, and the '
            + 'binding 183 lines away that makes it safe');

  // ── T1: THE REFUSAL ─────────────────────────────────────────────────────
  let t1;
  try {
    t1 = await drive('./sd-data.js',
      { licApp: 'stonedesk', sessApp: 'stonedesk', bodyAppId: 'sairnvet' });
    is(t1.status === 403 && t1.memWrites.length === 0,
       'T1. a memory write with a session signed for stonedesk and '
     + "body.app_id='sairnvet' is REFUSED 403 and writes NO ai_memories row",
       'status=' + t1.status + ' memWrites=' + t1.memWrites.length
     + ' body=' + JSON.stringify(t1.body));
  } catch (e) {
    bad('T1. a memory write with a foreign body.app_id is REFUSED 403', e && e.stack);
    t1 = null;
  }

  // ── T2: THE CONTROL THAT MAKES T1 MEAN ANYTHING ─────────────────────────
  // Without this arm "always 403" passes T1. The cross-app memory write is
  // DELIBERATE design -- api/sd-data.js:2105-2112 records the two-device live
  // check that found it returning 403 "no matter how correctly it was signed
  // in" -- so an arm that only proved refusal would be asking for the bug the
  // gate was written to fix.
  if (t1) {
    try {
      const t2 = await drive('./sd-data.js',
        { licApp: 'stonedesk', sessApp: 'sairnvet', bodyAppId: 'sairnvet' });
      is(t2.status === 200 && t2.wroteApp === 'sairnvet',
         'T2. CONTROL -- the same write with a session signed FOR sairnvet is '
       + "ADMITTED 200 and the row carries app_id 'sairnvet'. The gate is a "
       + 'binding, not a blanket refusal',
         'status=' + t2.status + ' wroteApp=' + JSON.stringify(t2.wroteApp)
       + ' body=' + JSON.stringify(t2.body));
    } catch (e) {
      bad('T2. CONTROL -- a correctly-signed cross-app memory write is ADMITTED',
          e && e.stack);
    }
  } else {
    cannot('T2. CONTROL -- a correctly-signed cross-app memory write is ADMITTED',
           'T1 threw, so the driver itself is not known to work');
  }

  // ── T3: THE DEFAULT, which is what StoneDesk itself sends ───────────────
  try {
    const t3 = await drive('./sd-data.js',
      { licApp: 'stonedesk', sessApp: 'stonedesk' });
    is(t3.status === 200 && t3.wroteApp === 'stonedesk',
       'T3. CONTROL -- no body.app_id at all defaults to stonedesk and is '
     + "ADMITTED 200 with app_id 'stonedesk'. StoneDesk's own read returns "
     + 'exactly the rows it returned before',
       'status=' + t3.status + ' wroteApp=' + JSON.stringify(t3.wroteApp));
  } catch (e) {
    bad('T3. CONTROL -- no body.app_id defaults to stonedesk', e && e.stack);
  }

  // ── T4: THE ALLOWLIST, the OTHER half of the memApp gating ──────────────
  try {
    const t4 = await drive('./sd-data.js',
      { licApp: 'stonedesk', sessApp: 'stonedesk', bodyAppId: 'not-an-app' });
    const code = t4.body && t4.body.error && t4.body.error.code;
    is(t4.status === 400 && code === 'UNKNOWN_APP' && t4.memWrites.length === 0,
       'T4. an app_id outside MEMORY_APPS is 400 UNKNOWN_APP and writes no '
     + 'row -- an orphan namespace nothing can read back is refused rather '
     + 'than created',
       'status=' + t4.status + ' code=' + code
     + ' memWrites=' + t4.memWrites.length);
  } catch (e) {
    bad('T4. an unknown app_id is 400 UNKNOWN_APP', e && e.stack);
  }

  // ── T5: THE STRUCTURAL ASSERTION cody ASKED FOR ─────────────────────────
  // Both places that derive an expected app for `memory` must derive it from
  // memApp, and each must occur exactly once so this arm cannot silently stop
  // matching. A count of 0 fails -- it does not skip.
  {
    const src = fs.readFileSync(SRC, 'utf8');
    const nGate = src.split(A_GATE).length - 1;
    const nPre = src.split(A_PREGATE).length - 1;
    const nLit = (src.match(/\(resource === 'memory'\) \? '/g) || []).length;
    is(nGate === 1 && nPre === 1 && nLit === 0,
       'T5. BOTH memory app derivations follow memApp and neither is a '
     + 'literal: gateApp x1, preExpectedApp x1, literal-app memory ternaries 0',
       'gateApp=' + nGate + ' preExpectedApp=' + nPre + ' literal=' + nLit);
  }

  // ── T6: ABLATE :2137 -- the layer T1 is supposed to be testing ──────────
  if (t1 && t1.status === 403) {
    try {
      const r = await ablate(A_GATE,
        "const gateApp = (resource === 'memory') ? 'stonedesk'", 'gate',
        (p) => drive(p, { licApp: 'stonedesk', sessApp: 'stonedesk',
                          bodyAppId: 'sairnvet' }));
      if (!r.ok) {
        cannot('T6. ABLATION of api/sd-data.js:2137 flips T1', r.why);
      } else {
        is(r.result.status !== 403,
           'T6. ABLATION -- with :2137 simplified to a fixed app the SAME '
         + 'request T1 drives is no longer refused, so T1 is testing that '
         + 'line and not something upstream of it (ablated status='
         + r.result.status + ' wroteApp=' + JSON.stringify(r.result.wroteApp) + ')',
           'ablated status=' + r.result.status + ' -- still 403, so T1 passes '
         + 'for a reason other than the gateApp binding and proves nothing '
         + 'about it');
      }
    } catch (e) {
      cannot('T6. ABLATION of api/sd-data.js:2137 flips T1', e && e.stack);
    }
  } else {
    cannot('T6. ABLATION of api/sd-data.js:2137 flips T1',
           'T1 did not produce a 403, so there is no refusal to ablate');
  }

  // ── T7: ABLATE :2016 -- and report that T1 does NOT cover it ────────────
  // A negative ablation, kept because it is the honest shape of this suite's
  // coverage. If this arm ever starts reporting that T1 DID flip, the
  // pre-gate has acquired behavioural coverage and this comment is stale.
  if (t1 && t1.status === 403) {
    try {
      const r = await ablate(A_PREGATE,
        "const preExpectedApp = (resource === 'memory') ? 'stonedesk'", 'pregate',
        (p) => drive(p, { licApp: 'stonedesk', sessApp: 'stonedesk',
                          bodyAppId: 'sairnvet' }));
      if (!r.ok) {
        cannot('T7. ABLATION of api/sd-data.js:2016 is NOT caught by T1', r.why);
      } else {
        is(r.result.status === 403,
           'T7. MEASURED AND REPORTED, not dropped for being negative -- '
         + 'ablating the active-credential pre-gate\'s own app derivation at '
         + ':2016 does NOT flip T1 (status=' + r.result.status + '). That line '
         + 'has NO behavioural arm here; T5 is the only guard on it, and that '
         + 'is a stated gap rather than a covered one',
           'ablated status=' + r.result.status + ' -- the pre-gate ablation DID '
         + 'change T1, so T1 now covers :2016 too and this arm is stale');
      }
    } catch (e) {
      cannot('T7. ABLATION of api/sd-data.js:2016 is NOT caught by T1', e && e.stack);
    }
  } else {
    cannot('T7. ABLATION of api/sd-data.js:2016 is NOT caught by T1',
           'T1 did not produce a 403');
  }

  // ── NO MUTANT LEFT BEHIND ───────────────────────────────────────────────
  {
    const left = fs.readdirSync(__dirname).filter((f) => /^_b16mut_/.test(f));
    is(left.length === 0,
       'T8. no mutant copy of sd-data.js is left in api/ -- an abandoned '
     + 'mutant is an untracked file the push gate would meet later',
       'left behind: ' + JSON.stringify(left));
  }

  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main().catch((e) => { console.log('  HARD ERROR ' + (e && e.stack)); process.exit(1); });
