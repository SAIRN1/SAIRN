// independent drive of requireCountersignature at HEAD (not cody's arms)
const cs = require(require('path').join(process.env.REPO || process.cwd(), 'api/_lib/countersign.js'));
const law = require(require('path').join(process.env.REPO || process.cwd(), 'api/law-countersign.js'));
const P = law.PROFILE;
let calls = [];
function stub(roster, tokenRow, opts) {
  opts = opts || {};
  global.fetch = async (url, init) => {
    url = String(url);
    calls.push(((init && init.method) || 'GET') + ' ' + url.replace(/https?:\/\/[^/]*/, '').slice(0, 160));
    const ok = (b) => ({ ok: true, status: 200, json: async () => b });
    if (url.indexOf(P.employeeTable) !== -1) {
      if (opts.rosterFail) return { ok: false, status: 500, json: async () => ({}) };
      const m = /employee_id=eq\.([^&]*)/.exec(url);
      const id = decodeURIComponent(m[1]);
      const inactive = opts.inactive && opts.inactive.indexOf(id) !== -1;
      return ok(roster[id] && !inactive ? [{ employee_id: id, role: roster[id] }] : []);
    }
    if (url.indexOf(P.tokenTable) !== -1) {
      if (init && init.method === 'PATCH') return ok(opts.spendEmpty ? [] : [{ id: 1 }]);
      return ok(tokenRow ? [tokenRow] : []);
    }
    return ok([]);
  };
}
const base = { resource: 'law_trusttx', payload: { amount_cents: 100 }, licHash: 'L', rest: (p) => 'https://x.example/rest/v1/' + p, headers: {} };
const hash = cs.contentHash('law_trusttx', base.payload);
const tok = (o) => Object.assign({ id: 1, content_hash: hash, prepared_by: 'P1', prepared_role: 'paralegal', countersign_employee_id: 'A1', countersign_role: 'attorney', spent_at: null, expires_at: new Date(Date.now() + 60000).toISOString() }, o || {});
let pass = 0, fail = 0;
async function arm(name, ctx, roster, tokenRow, opts, want) {
  calls = []; stub(roster, tokenRow, opts);
  const r = await cs.requireCountersignature(P, Object.assign({}, base, ctx));
  const got = r ? r.body.error.code + ':' + r.status : 'null';
  const ok = got === want; ok ? pass++ : fail++;
  console.log((ok ? '  ok   ' : '  FAIL ') + name + '  got=' + got + ' want=' + want + '  fetches=' + calls.length);
}
(async () => {
  // finding 1: the PREPARED_ONLY bypass
  await arm('F1-a token attorney, roster attorney -> bypass allowed', { callerRole: 'attorney', callerEmployeeId: 'A1', token: '' }, { A1: 'attorney' }, null, {}, 'null');
  await arm('F1-b token attorney, roster DEMOTED to paralegal -> refused', { callerRole: 'attorney', callerEmployeeId: 'A1', token: '' }, { A1: 'paralegal' }, null, {}, 'COUNTERSIGN_ROLE_REVOKED:403');
  await arm('F1-c token attorney, roster owner (promoted) -> allowed', { callerRole: 'attorney', callerEmployeeId: 'A1', token: '' }, { A1: 'owner' }, null, {}, 'null');
  await arm('F1-d token attorney, deactivated -> refused', { callerRole: 'attorney', callerEmployeeId: 'A1', token: '' }, { A1: 'attorney' }, null, { inactive: ['A1'] }, 'COUNTERSIGN_NO_LONGER_ACTIVE:403');
  await arm('F1-e roster unreadable -> 503 fail closed, not a pass', { callerRole: 'attorney', callerEmployeeId: 'A1', token: '' }, {}, null, { rosterFail: true }, 'COUNTERSIGN_CHECK_FAILED:503');
  await arm('F1-f callerEmployeeId MISSING -> refused (no row for undefined)', { callerRole: 'attorney', token: '' }, { A1: 'attorney' }, null, {}, 'COUNTERSIGN_NO_LONGER_ACTIVE:403');
  await arm('F1-g token PARALEGAL promoted in roster, no token -> REQUIRED (never widens)', { callerRole: 'paralegal', callerEmployeeId: 'A1', token: '' }, { A1: 'attorney' }, null, {}, 'COUNTERSIGN_REQUIRED:403');
  await arm('F1-h roster role with different case -> refused', { callerRole: 'attorney', callerEmployeeId: 'A1', token: '' }, { A1: 'Attorney' }, null, {}, 'COUNTERSIGN_ROLE_REVOKED:403');
  // finding 2: the settling step
  await arm('F2-a signer and preparer still qualified -> spend and proceed', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, { P1: 'paralegal', A1: 'attorney' }, tok(), {}, 'null');
  await arm('F2-b signer DEMOTED but still active inside TTL -> refused', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, { P1: 'paralegal', A1: 'paralegal' }, tok(), {}, 'COUNTERSIGN_ROLE_REVOKED:403');
  await arm('F2-c preparer demoted to a non-preparer role -> refused', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, { P1: 'bookkeeper', A1: 'attorney' }, tok(), {}, 'COUNTERSIGN_ROLE_REVOKED:403');
  await arm('F2-d signer deactivated -> refused', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, { P1: 'paralegal', A1: 'attorney' }, tok(), { inactive: ['A1'] }, 'COUNTERSIGN_NO_LONGER_ACTIVE:403');
  await arm('F2-e roster unreadable at settle -> 503', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, {}, tok(), { rosterFail: true }, 'COUNTERSIGN_CHECK_FAILED:503');
  await arm('F2-f signer promoted attorney->owner after signing -> allowed', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, { P1: 'paralegal', A1: 'owner' }, tok(), {}, 'null');
  await arm('F2-g replay: spent token refused', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, { P1: 'paralegal', A1: 'attorney' }, tok({ spent_at: 'x' }), {}, 'COUNTERSIGN_ALREADY_SPENT:409');
  await arm('F2-h lost compare-and-set race -> ALREADY_SPENT', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, { P1: 'paralegal', A1: 'attorney' }, tok(), { spendEmpty: true }, 'COUNTERSIGN_ALREADY_SPENT:409');
  await arm('F2-i content mismatch refused', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T', payload: { amount_cents: 999 } }, { P1: 'paralegal', A1: 'attorney' }, tok(), {}, 'COUNTERSIGN_CONTENT_MISMATCH:409');
  await arm('F2-j preparer == signer refused', { callerRole: 'paralegal', callerEmployeeId: 'P1', token: 'T' }, { P1: 'attorney' }, tok({ countersign_employee_id: 'P1' }), {}, 'COUNTERSIGN_SAME_PERSON:409');
  calls = []; stub({ A1: 'attorney' }, null, {});
  await cs.requireCountersignature(P, Object.assign({}, base, { callerRole: 'attorney', callerEmployeeId: 'A1', token: '' }));
  const q = calls[0] || '';
  const scoped = q.indexOf('license_hash=eq.L') !== -1 && q.indexOf('active=eq.true') !== -1 && q.indexOf('select=employee_id,role') !== -1;
  scoped ? pass++ : fail++;
  console.log((scoped ? '  ok   ' : '  FAIL ') + 'roster query is licence-scoped, active-only, reads role: ' + q);
  console.log(pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
