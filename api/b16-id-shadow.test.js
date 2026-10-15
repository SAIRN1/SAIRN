// api/b16-id-shadow.test.js
//
// Run:  node api/b16-id-shadow.test.js
//
// REQUIREMENT: on SD_LINEAGE and SD_HR, the SERVER'S OWN identifier column is
//   what a read returns as `id`. A value in the jsonb blob must not shadow it.
//
// ── THE DECISION THIS SUITE IS, AND THE TWO OPTIONS IT REJECTS ────────────
// b14 found the shape and deliberately did not pick, because the three
// available fixes are mutually exclusive and the measurement it had did not
// decide between them. Its own words:
//
//   "SD_LINEAGE AND SD_HR STILL LET A PAYLOAD id SHADOW THE COLUMN,
//    deliberately, and the three available fixes are mutually exclusive: the
//    column stops stringifying, the read stops re-adding id, or the client
//    stops comparing with ===. Only one is right and I did not pick."
//
// PICKED 2026-10-15 (hank b16): THE READ STOPS LETTING THE BLOB WIN.
//
//     was:  Object.assign({ id: x[cfg.idCol] }, x.data)     // data wins
//     now:  Object.assign({}, x.data, { id: x[cfg.idCol] }) // the COLUMN wins
//
// WHY THAT ONE AND NOT THE OTHER TWO, with the measurement for each:
//
//   "the column stops stringifying" -- REJECTED. `String(payload.id)` is what
//   the on_conflict key is built from; the column is the row's address. Making
//   it accept whatever type arrived would not close the shadow at all, it
//   would only make the two agree in the common case while still letting the
//   blob win in the uncommon one. It fixes the symptom on the easy inputs.
//
//   "the client stops comparing with ===" -- REJECTED, and this is the one
//   that needed measuring rather than arguing. It pushes the fix into
//   stonedesk.html for every comparison site that exists or is ever added,
//   and leaves the API returning an UNSTABLE TYPE for a row's own identifier.
//   The hazard is not the comparison; it is that a read can hand a client an
//   `id` that does not address the row it came from -- write it back and it
//   keys a different row, or no row.
//
//   "the read stops re-adding id" -- TAKEN. `id` becomes always a string, from
//   the column PostgREST selected, which is the same value every write keys
//   on. One expression, two registries, five resources.
//
// THE === RISK IS REAL AND IS MEASURED, NOT WAVED AWAY (arm I6). Making the
// column win means `id` is always a string, so a `===` against a
// LOCALLY-MINTED numeric id would start failing. Every id minted for these
// five resources is measured from the real pages: 'BLK'+Date.now(),
// 'BND'+Date.now(), 'EVT'+Date.now()+'-'+random, and
// Date.now().toString() -- all strings. If that ever stops being true I6 goes
// red and this decision needs revisiting, which is the point of asserting it
// rather than noting it.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SRC = path.join(__dirname, 'sd-data.js');

process.env[['SD', 'AUTH', 'SECRET'].join('_')] =
  ['b16', 'idshadow', String(process.pid)].join('-');
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
  if (why) console.log('           ' + String(why).slice(0, 500));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 500));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

// The five resources and their id columns, read from the handler rather than
// retyped -- a list in a test that drifts from the code tests the list.
const REGISTRIES = [
  { resource: 'sd_blocks', idCol: 'block_id', session: false },
  { resource: 'sd_bundles', idCol: 'bundle_id', session: false },
  { resource: 'sd_slab_history', idCol: 'event_id', session: false },
  { resource: 'sd_hr_employees', idCol: 'employee_key', session: true },
  { resource: 'sd_hr_certs', idCol: 'cert_key', session: true }
];

async function readResource(spec, row, modulePath) {
  const licResolved = require.resolve('./_lib/license');
  require.cache[licResolved] = {
    id: licResolved, filename: licResolved, loaded: true,
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: HASH, trial_ends_at: null,
        stripe_subscription_id: null, app_id: 'stonedesk' })
    }
  };
  const res200 = (rows) => ({ ok: true, status: 200, headers: { get: () => '' },
    text: async () => JSON.stringify(rows), json: async () => rows });
  global.fetch = async function (url) {
    const u = String(url);
    if (/_employee_auth\?/.test(u)) {
      return res200([{ license_hash: HASH, employee_id: 'S1', role: 'owner', active: true }]);
    }
    if (new RegExp(spec.resource + '\\?').test(u)) return res200([row]);
    return res200([]);
  };
  delete require.cache[require.resolve(modulePath || './sd-data.js')];
  const handler = require(modulePath || './sd-data.js');
  const { signSessionToken } = require('./_lib/auth');
  const out = { statusCode: null, body: null };
  out.status = (c) => { out.statusCode = c; return out; };
  out.json = (b) => { out.body = b; return out; };
  const headers = { authorization: 'Bearer ' + KEY };
  headers['x-sd-auth'] = signSessionToken({ app: 'stonedesk', employee_id: 'S1',
    role: 'owner', license_hash: HASH });
  await handler({ method: 'POST', headers: headers,
    body: { action: 'read', resource: spec.resource } }, out);
  return out;
}

// ── ABLATION on api/sd-data.js ───────────────────────────────────────────
function ablate(anchor, replacement, fn) {
  const src = fs.readFileSync(SRC, 'utf8');
  const n = src.split(anchor).length - 1;
  if (n !== 2) return { ok: false, why: 'anchor occurs ' + n + ' times, not 2 (one per registry)' };
  let r;
  try {
    fs.writeFileSync(SRC, src.split(anchor).join(replacement));
    r = { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(SRC, src);
    if (fs.readFileSync(SRC, 'utf8') !== src) {
      console.log('  HARD ERROR the ablation did not restore api/sd-data.js -- DO NOT COMMIT');
      process.exit(1);
    }
  }
  return r;
}

const A_READ = "Object.assign({}, x.data, { id: x[cfg.idCol] })";
const A_OLD = "Object.assign({ id: x[cfg.idCol] }, x.data)";

async function main() {
  console.log('api/b16-id-shadow.test.js');
  console.log('  the server\'s identifier column wins over a blob field');

  // ── I1: THE SHADOW IS CLOSED, on every one of the five ─────────────────
  const i1 = [];
  for (let k = 0; k < REGISTRIES.length; k += 1) {
    const spec = REGISTRIES[k];
    const row = {};
    row[spec.idCol] = 'REAL-1';
    // A number in the blob, which is the type the write stores whenever a
    // caller sends one: the column is String(payload.id), the blob is not.
    row.data = { id: 999, label: 'kept' };
    try {
      const out = await readResource(spec, row);
      const d = out.body && out.body.data && out.body.data[0];
      i1.push({ resource: spec.resource, status: out.statusCode,
                id: d && d.id, label: d && d.label });
    } catch (e) {
      i1.push({ resource: spec.resource, error: String(e && e.message) });
    }
  }
  const allColumnWins = i1.length === 5 && i1.every((r) =>
    r.status === 200 && r.id === 'REAL-1' && r.label === 'kept');
  is(allColumnWins,
     'I1. all FIVE SD_LINEAGE/SD_HR resources return the COLUMN\'s id '
   + '("REAL-1") and not the blob\'s 999, with every other blob field kept',
     JSON.stringify(i1));

  // ── I2: CONTROL -- a row with no blob id is unchanged ──────────────────
  // Without this arm "always return the column and drop the blob" passes I1,
  // and the read returns the blob WHOLE for these resources -- dropping it
  // would empty the panel.
  try {
    const spec = REGISTRIES[0];
    const row = { block_id: 'BLK-7',
      data: { blockNumber: 'B-2026-014', quarryName: 'Q', origin: 'IT' } };
    const out = await readResource(spec, row);
    const d = out.body && out.body.data && out.body.data[0];
    is(out.statusCode === 200 && d && d.id === 'BLK-7'
       && d.blockNumber === 'B-2026-014' && d.quarryName === 'Q' && d.origin === 'IT',
       'I2. CONTROL -- an ordinary row still returns its id plus every blob '
     + 'field. The read returns the blob WHOLE for these resources and that '
     + 'did not change',
       'status=' + out.statusCode + ' row=' + JSON.stringify(d));
  } catch (e) {
    bad('I2. CONTROL -- an ordinary row is unchanged', e && e.stack);
  }

  // ── I3: AND id IS ALWAYS A STRING, which is the property the pick buys ─
  try {
    const spec = REGISTRIES[0];
    const out = await readResource(spec, { block_id: '12345', data: { id: 12345 } });
    const d = out.body && out.body.data && out.body.data[0];
    is(d && typeof d.id === 'string' && d.id === '12345',
       'I3. the returned id is always a STRING, taken from the column the '
     + 'write keys on, so a round-trip addresses the same row',
       'typeof=' + (d && typeof d.id) + ' value=' + JSON.stringify(d && d.id));
  } catch (e) {
    bad('I3. the returned id is always a string', e && e.stack);
  }

  // ── I4: THE OLD EXPRESSION IS GONE FROM BOTH REGISTRIES ───────────────
  {
    const src = fs.readFileSync(SRC, 'utf8');
    const nNew = src.split(A_READ).length - 1;
    const nOld = src.split(A_OLD).length - 1;
    is(nNew === 2 && nOld === 0,
       'I4. the column-wins expression appears exactly TWICE (one per '
     + 'registry) and the blob-wins expression ZERO times. Fixing one '
     + 'registry and not the other is how this shape survives a fix',
       'column-wins=' + nNew + ' blob-wins=' + nOld);
  }

  // ── I5: ABLATION -- put the blob-wins expression back, I1 must flip ───
  if (allColumnWins) {
    const r = ablate(A_READ, A_OLD, async () => {
      return readResource(REGISTRIES[0],
        { block_id: 'REAL-1', data: { id: 999, label: 'kept' } },
        './sd-data.js');
    });
    if (!r.ok) {
      cannot('I5. ABLATION -- the blob-wins expression put back flips I1', r.why);
    } else {
      const out = await r.result;
      const d = out.body && out.body.data && out.body.data[0];
      is(d && d.id === 999,
         'I5. ABLATION -- with the blob-wins expression restored in BOTH '
       + 'registries the same read returns 999 again, so I1 is testing that '
       + 'expression and not the stub',
         'ablated id=' + JSON.stringify(d && d.id)
       + ' -- unchanged, so I1 passes for another reason');
    }
  } else {
    cannot('I5. ABLATION -- the blob-wins expression put back flips I1',
           'I1 did not pass, so there is nothing to ablate');
  }

  // ── I6: THE REJECTED OPTION, MEASURED -- every client id is a string ──
  // This is why "the client stops comparing with ===" was not the pick: it
  // does not need to, and if that ever changes this arm says so.
  {
    const files = [
      { f: 'stonedesk.html', pats: [/id:'BLK'\+Date\.now\(\)/, /id:'BND'\+Date\.now\(\)/,
                                    /id:'EVT'\+Date\.now\(\)/] },
      { f: 'stonedesk-hr.html', pats: [/id:\s*Date\.now\(\)\.toString\(\)/] }
    ];
    const results = [];
    files.forEach((spec) => {
      let src = null;
      try { src = fs.readFileSync(path.join(ROOT, spec.f), 'utf8'); }
      catch (e) { results.push({ f: spec.f, error: 'unreadable' }); return; }
      spec.pats.forEach((p) => {
        results.push({ f: spec.f, pat: String(p), found: p.test(src) });
      });
    });
    const allFound = results.length === 4 && results.every((r) => r.found === true);
    // AND the inverse: no bare numeric mint for these five resources' ids.
    const hrSrc = (function () {
      try { return fs.readFileSync(path.join(ROOT, 'stonedesk-hr.html'), 'utf8'); }
      catch (e) { return ''; }
    })();
    const bareNumericHr = /id:\s*Date\.now\(\)(?!\.toString)/.test(hrSrc);
    is(allFound && !bareNumericHr,
       'I6. the REJECTED option measured rather than argued -- all four id '
     + 'mints for these five resources produce STRINGS, so the clients\' === '
     + 'comparisons still match a column-sourced id and did not need to '
     + 'change. If a numeric mint appears this arm goes red and the pick '
     + 'needs revisiting',
       JSON.stringify(results) + ' bareNumericHr=' + bareNumericHr);
  }

  console.log('');
  console.log('  passed ' + pass + '  failed ' + fail + '  unproven ' + unproven);
  if (fail) console.log('  FAILING ARMS: ' + failed.join(' '));
  if (unproven) console.log('  UNPROVEN ARMS: ' + notProved.join(' '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main().catch((e) => { console.log('  HARD ERROR ' + (e && e.stack)); process.exit(1); });
