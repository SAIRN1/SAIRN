// tests/run_restore_coherence_probe.js
//
// Run:  node tests/run_restore_coherence_probe.js
//
// The control pair for tools/restore_coherence_check.js. Item 65d.
//
// CONTROLS_FOR = ['restore_coherence_check.js']
//
// THE ARM THAT MATTERS RESTORES A DELIBERATELY TRUNCATED COPY AND DEMANDS THE
// CHECKER FIND IT. Everything else exists so that arm cannot be satisfied by a
// checker that always fails: a faithful copy must come back COHERENT, and a row
// written AFTER the last checkpointed window -- ordinary live traffic -- must
// not be called damage.
//
// IT DRIVES A REAL HTTP SERVER AND THE REAL TOOL AS A SUBPROCESS. Not an
// injected fetch, not an internal function: the tool is what somebody will
// actually run at 3am with an env var and a URL, and that is the thing under
// test. A mocked internal would prove the arithmetic and nothing about whether
// the tool works when pointed at a database.
//
// THE FAKE ANSWERS ONLY WHAT IT MODELS. An unrecognised table returns 404 --
// which the tool treats as "skipped", the honest answer for a table that is not
// in this target -- and an unrecognised QUERY SHAPE returns 500 rather than an
// empty array, because a silent [] is how a fake makes a broken query look like
// a clean result.

'use strict';
const assert = require('assert');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const CONTROLS_FOR = ['restore_coherence_check.js'];
const REPO = path.dirname(__dirname);
const TOOL = path.join(REPO, 'tools', 'restore_coherence_check.js');
const AC = require(path.join(REPO, 'api', 'audit-checkpoint.js'));

let pass = 0, fail = 0;
function ok(name, cond, detail) {
  console.log('  ' + (cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '\n        ' + String(detail).slice(0, 700)));
  if (cond) pass++; else fail++;
}

const DAY = 24 * 60 * 60 * 1000;
const D0 = Date.UTC(2026, 8, 10);
const iso = (ms) => new Date(ms).toISOString();
const TABLE = 'sairnlaw_audit_log';

function row(id, ms) {
  return {
    id: id, license_hash: 'L1', employee_id: 'e1', role: 'owner',
    event_type: 'login_success', detail: null, created_at: iso(ms)
  };
}

// A faithful two-day history, with the checkpoints computed by the REAL
// digest -- imported, never re-derived here. A second implementation of the
// canonical form in this file would let the tool and the fixture drift apart
// and the arms would then be testing their own agreement.
function world() {
  const rows = [row('a', D0 + 1), row('b', D0 + 2), row('c', D0 + DAY + 1)];
  const w1 = rows.filter((r) => r.created_at < iso(D0 + DAY));
  const w2 = rows.filter((r) => r.created_at >= iso(D0 + DAY) && r.created_at < iso(D0 + 2 * DAY));
  const d1 = AC.digestOf(AC.GENESIS, w1);
  const d2 = AC.digestOf(d1, w2);
  return {
    rows: rows,
    checkpoints: [
      { audit_table: TABLE, window_start: iso(D0), window_end: iso(D0 + DAY),
        row_count: w1.length, digest: d1, prev_digest: AC.GENESIS },
      { audit_table: TABLE, window_start: iso(D0 + DAY), window_end: iso(D0 + 2 * DAY),
        row_count: w2.length, digest: d2, prev_digest: d1 }
    ]
  };
}

function serve(state) {
  const srv = http.createServer((req, res) => {
    const u = new URL(req.url, 'http://x');
    const table = u.pathname.replace('/rest/v1/', '');
    const send = (code, body, extra) => {
      res.writeHead(code, Object.assign({ 'Content-Type': 'application/json' }, extra || {}));
      res.end(JSON.stringify(body));
    };
    if (table === 'sairn_audit_checkpoint') {
      if (state.noCheckpointTable) return send(404, { code: 'PGRST205', message: 'does not exist' });
      return send(200, state.checkpoints);
    }
    if (table === TABLE) {
      const gte = u.searchParams.get('created_at');   // PostgREST repeats the key
      const all = state.rows.slice().sort((a, b) =>
        a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : (a.id < b.id ? -1 : 1));
      const params = u.searchParams.getAll('created_at');
      let rows = all;
      if (params.length === 2) {
        const lo = decodeURIComponent(params[0].replace('gte.', ''));
        const hi = decodeURIComponent(params[1].replace('lt.', ''));
        rows = all.filter((r) => r.created_at >= lo && r.created_at < hi);
      } else if (gte === null) {
        return send(500, { message: 'the fake was asked a shape it does not model: ' + req.url });
      }
      const total = state.overstateTotal || rows.length;
      return send(200, rows, { 'Content-Range': '0-' + rows.length + '/' + total });
    }
    if (state.extra && state.extra[table]) {
      const sel = u.searchParams.get('select');
      const out = state.extra[table].map((r) => ({ [sel]: r[sel] }));
      return send(200, out, { 'Content-Range': '0-' + out.length + '/' + out.length });
    }
    // Not modelled: 404, which is a table that is not in this target.
    return send(404, { code: 'PGRST205', message: 'does not exist' });
  });
  return new Promise((resolve) => srv.listen(0, '127.0.0.1', () => resolve(srv)));
}

// ── ASYNC, AND THE SYNCHRONOUS VERSION DEADLOCKED ──────────────────────────
// The first draft used spawnSync. The fake PostgREST server runs in THIS
// process, and spawnSync blocks this process's event loop -- so the server
// could never answer the subprocess's requests and both sides waited for each
// other for ever. The symptom was a probe that produced no output at all, which
// reads exactly like a probe that has not been run.
function runTool(port, args) {
  return new Promise((resolve) => {
    const p = spawn(process.execPath, [TOOL].concat(args || []), {
      env: Object.assign({}, process.env, {
        SAIRN_TARGET_URL: 'http://127.0.0.1:' + port,
        SAIRN_TARGET_KEY: 'k'
      })
    });
    let out = '';
    p.stdout.on('data', (d) => { out += d; });
    p.stderr.on('data', (d) => { out += d; });
    // A BOUND, AND IT IS REPORTED RATHER THAN SILENT. Without it a tool that
    // hangs makes this probe hang, and a probe that never finishes is
    // indistinguishable from one nobody ran.
    const timer = setTimeout(() => {
      p.kill();
      out += '\n[PROBE] the tool did not exit within 60s and was killed';
    }, 60000);
    p.on('close', (code) => { clearTimeout(timer); resolve({ code: code, out: out }); });
  });
}

async function withWorld(mutate, fn) {
  const state = world();
  if (mutate) mutate(state);
  const srv = await serve(state);
  try { return await fn(srv.address().port, state); }
  finally { srv.close(); }
}

(async () => {
  console.log('restore_coherence_check -- the control pair');

  console.log('\n--- A. a faithful copy ---');
  await withWorld(null, async (port) => {
    const r = await runTool(port);
    ok('A1 exits 0', r.code === 0, 'rc=' + r.code + '\n' + r.out);
    ok('A2 says COHERENT', /COHERENT/.test(r.out), r.out);
    ok('A3 names how many windows it verified against the fingerprint',
      /FINGERPRINT OK: sairnlaw_audit_log -- 2 of 2/.test(r.out), r.out);
    ok('A4 says NO BASELINE was compared rather than implying counts were checked',
      /no --baseline given/.test(r.out), r.out);
    ok('A5 publishes the referential denominator',
      /REFERENTIAL: \d+ relation\(s\) checked/.test(r.out), r.out);
  });

  console.log('\n--- B. THE CONTROL: a truncated restore ---');
  await withWorld((s) => { s.rows = s.rows.filter((r) => r.id !== 'b'); }, async (port) => {
    const r = await runTool(port);
    ok('B1 exits 1 -- a finding, not a clean run', r.code === 1, 'rc=' + r.code + '\n' + r.out);
    ok('B2 it says WINDOW_CHANGED', /WINDOW_CHANGED/.test(r.out), r.out);
    ok('B3 it says rows were LOST, not merely that something differs',
      /LOST 1 row/.test(r.out), r.out);
    ok('B4 it names WHEN the restore diverged',
      r.out.indexOf(iso(D0 + DAY)) !== -1, r.out);
    ok('B5 and it does NOT claim the later window is fine -- it stops at the first divergence',
      !/FINGERPRINT OK: sairnlaw_audit_log/.test(r.out), r.out);
  });

  console.log('\n--- C. the other damage shapes are named apart ---');
  await withWorld((s) => { s.rows.push(row('forged', D0 + 3)); }, async (port) => {
    const r = await runTool(port);
    ok('C1 an EXTRA row in a closed window is GAINED', /GAINED 1 row/.test(r.out), r.out);
  });
  await withWorld((s) => { s.rows[0].role = 'admin'; }, async (port) => {
    const r = await runTool(port);
    ok('C2 the same count with changed content is named as content, not as loss',
      /the same number of rows with DIFFERENT CONTENT/.test(r.out), r.out);
  });
  await withWorld((s) => { s.checkpoints[1].prev_digest = 'rewritten'; }, async (port) => {
    const r = await runTool(port);
    ok('C3 a rewritten FINGERPRINT is CHAIN_BROKEN, a different finding from the rows moving',
      /CHAIN_BROKEN/.test(r.out) && !/WINDOW_CHANGED/.test(r.out), r.out);
  });

  console.log('\n--- D. live traffic is not damage ---');
  await withWorld((s) => { s.rows.push(row('today', D0 + 2 * DAY + 500)); }, async (port) => {
    const r = await runTool(port);
    ok('D1 a row written AFTER the last checkpointed window is not a finding',
      r.code === 0, 'rc=' + r.code + '\n' + r.out);
  });

  console.log('\n--- E. could-not-check is never a clean restore ---');
  await withWorld((s) => { s.checkpoints = []; }, async (port) => {
    const r = await runTool(port);
    ok('E1 an EMPTY checkpoint table exits 2, not 0', r.code === 2, 'rc=' + r.code + '\n' + r.out);
    ok('E2 and says a clean run over an empty chain would be a statement about nothing',
      /statement about nothing/.test(r.out), r.out);
  });
  await withWorld((s) => { s.noCheckpointTable = true; }, async (port) => {
    const r = await runTool(port);
    ok('E3 a MISSING checkpoint table exits 2 and names the migration',
      r.code === 2 && /audit_checkpoint_schema\.sql/.test(r.out), 'rc=' + r.code + '\n' + r.out);
    ok('E4 ...and says that is not the same as a faithful restore',
      /not the same as a faithful restore/.test(r.out), r.out);
  });
  await withWorld((s) => { s.overstateTotal = 99; }, async (port) => {
    const r = await runTool(port);
    ok('E5 a window that could not be read IN FULL is could-not-check, never a pass',
      r.code === 2 && /could not be read in full/.test(r.out), 'rc=' + r.code + '\n' + r.out);
    ok('E6 ...and it is not reported as a finding about the data',
      !/WINDOW_CHANGED/.test(r.out), r.out);
  });

  console.log('\n--- F. the derived referential pass ---');
  await withWorld((s) => {
    s.extra = {
      rf_draws: [{ job_id: 'J1' }, { job_id: 'GHOST' }],
      rf_jobs: [{ job_id: 'J1' }]
    };
  }, async (port) => {
    const r = await runTool(port);
    ok('F1 an orphan is found where the database has no foreign key to complain',
      /ORPHANS: 1 distinct job_id/.test(r.out), r.out);
    ok('F2 it names both sides', /rf_draws/.test(r.out) && /rf_jobs/.test(r.out), r.out);
    ok('F3 and it says REPORT-ONLY, so nobody reads an orphan as a verdict',
      /REPORT-ONLY/.test(r.out), r.out);
  });
  await withWorld((s) => {
    s.extra = { rf_draws: [{ job_id: 'J1' }], rf_jobs: [{ job_id: 'J1' }] };
  }, async (port) => {
    const r = await runTool(port);
    ok('F4 THE PAIR: a relation with no orphans reports nothing', !/ORPHANS/.test(r.out), r.out);
  });

  console.log('\n--- G. no target configured ---');
  {
    // No server is running for this one, so there is nothing to deadlock
    // against -- but it uses the same async helper anyway, because two ways of
    // starting the same subprocess is two things to keep in step.
    const r = await new Promise((resolve) => {
      const p = spawn(process.execPath, [TOOL], {
        env: Object.assign({}, process.env, {
          SAIRN_TARGET_URL: '', SAIRN_TARGET_KEY: '',
          SUPABASE_URL: '', SUPABASE_SERVICE_ROLE_KEY: ''
        })
      });
      let out = '';
      p.stdout.on('data', (d) => { out += d; });
      p.stderr.on('data', (d) => { out += d; });
      p.on('close', (code) => resolve({ code: code, out: out }));
    });
    ok('G1 it refuses rather than checking nothing quietly', r.code === 2, 'rc=' + r.code);
    ok('G2 and says nothing checked is not nothing wrong',
      /not the same as nothing being wrong/.test(r.out), r.out);
  }

  console.log('');
  console.log(fail ? ('restore_coherence: ' + fail + ' ARM(S) FAILED')
                   : 'restore_coherence: all ' + pass + ' arms pass');
  process.exit(fail ? 1 : 0);
})();
