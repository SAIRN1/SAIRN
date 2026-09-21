// tests/sairnlaw_clearance_refusal_review_probe.js
//
// INDEPENDENT REVIEW of cody's Tier A obligation 2026-09-21T14:53:05Z on
// law_trusttx -- the SERVER half: the 409 CLEARANCE_NOT_STORED refusal added to
// api/sd-data.js in 6b777f00. Report-only. It fixes nothing and exits 0 always.
//
// I reviewed the CLIENT half of the same resource two hours earlier
// (obligation 2026-09-21T13:41:23Z, discharged; probe
// tests/sairnlaw_trust_clearance_review_probe.js), so the seam is the same seam
// and this is the other end of it.
//
// ── WHY THIS FILE MAKES NO ASSERTION, DELIBERATELY ────────────────────────
// My last review probe carried two anchor checks -- it lifted a function out of
// sairnlaw.html by literal string and had to refuse if the anchor moved -- so it
// COULD fail, which made it a guard, which correctly raised an independent-review
// obligation of its own under is_report_only_artefact()'s third condition.
//
// This one needs no anchor: it `require`s the real api/sd-data.js the way the
// author's own suite does, and a require that cannot resolve throws on its own
// without anything here to help it. So there is nothing to assert about
// fidelity, every exit below is the literal 0, and the file is genuinely
// report-only rather than report-only-in-intent. That is not a trick to dodge
// the gate: it is the gate's predicate being right about a file that cannot
// fail. A finding here is a sentence for a human, not a red build.
//
// ── THE HARNESS IS THE AUTHOR'S, RESHAPED ONLY WHERE IT HAD TO BE ─────────
// Same mock req/res, same license stub, same REST stub shape as
// api/sd-data-law-trusttx-clearance.test.js, so a finding is a finding about
// api/sd-data.js and not about my fixture. The one thing I added is an rpc
// stub that can answer as a FIRST INSERT rather than only as an existing-id
// retry, because that distinction turns out to be the whole finding.

'use strict';
process.env.SD_AUTH_SECRET = ['law', 'clearance', 'review', 'fixture'].join('-');
const { signSessionToken } = require('../api/_lib/auth.js');

const LIC = 'law-clearance-review-hash';
let findings = 0;

function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}

function mockReq(payload) {
  return {
    method: 'POST',
    headers: {
      authorization: 'Bearer GOOD-KEY',
      'x-sd-auth': signSessionToken({
        app: 'sairnlaw', employee_id: 'emp-owner', role: 'owner', license_hash: LIC,
      }),
    },
    body: { action: 'write', resource: 'law_trusttx', app_id: 'sairnlaw', payload },
  };
}

function loadHandler(fetchImpl) {
  delete require.cache[require.resolve('../api/_lib/license')];
  require.cache[require.resolve('../api/_lib/license')] = {
    exports: {
      validateLicenseKey: async () => ({
        valid: true, active: true, license_hash: LIC,
        trial_ends_at: null, stripe_subscription_id: null,
      }),
    },
  };
  global.fetch = fetchImpl;
  delete require.cache[require.resolve('../api/sd-data.js')];
  return require('../api/sd-data.js');
}

// The cheque as the DATABASE holds it -- exactly the eleven keys
// law_check_and_insert_disbursement's jsonb_build_object builds, and not one
// clearance field among them. Read off sql/sairnlaw_trusttx_functions.sql:207
// rather than copied from the author's fixture, so the two agreeing means
// something.
const STORED = {
  id: 'T-CHQ', matter_id: 'M1', client_id: 'C1', type: 'Disbursement',
  amount: 40, method: null, reference_number: null, description: null,
  date: '2026-09-14', status: 'Posted', created_at: '2026-09-14',
};

// What lawSetClearance() sends: the WHOLE record with the clearance applied.
// Verified against sairnlaw.html:3518-3523 -- `cleared`, `cleared_on` (deleted
// when outstanding) and `cleared_at`, then `sdnData('write','law_trusttx',t)`
// with t being the entire transaction object.
const MARKED = Object.assign({}, STORED, {
  cleared_on: '2026-09-20', cleared: true, cleared_at: '2026-09-21T12:00:00.000Z',
});
const OUTSTANDING = Object.assign({}, STORED, {
  cleared: false, cleared_at: '2026-09-21T12:00:00.000Z',
});

function restStub(calls, opts) {
  const o = opts || {};
  return async function (url, init) {
    const u = String(url);
    calls.push({
      url: u, method: (init && init.method) || 'GET',
      body: init && init.body ? JSON.parse(init.body) : null,
    });
    if (u.indexOf('sairnlaw_employee_auth') !== -1) {
      return { ok: true, status: 200, json: async () => [{ active: true }] };
    }
    if (u.indexOf('rpc/law_check_and_insert_disbursement') !== -1) {
      // TWO BRANCHES, MODELLED SEPARATELY, because the whole finding is that the
      // handler cannot tell them apart -- so they must be different stubs here
      // or the comparison proves nothing. `freshInsert` builds the returned row
      // the way the INSERT branch's jsonb_build_object does, out of the nine p_
      // parameters it was actually sent (sql/sairnlaw_trusttx_functions.sql:207)
      // rather than out of a constant, so the absence of a clearance field in it
      // is derived from the SQL's key list and not asserted by my fixture.
      // The default is the existing-id branch: the stored row, untouched.
      const p = init && init.body ? JSON.parse(init.body) : {};
      const inserted = {
        id: p.p_trusttx_id, matter_id: p.p_matter_id, client_id: p.p_client_id,
        type: 'Disbursement', amount: p.p_amount, method: p.p_method,
        reference_number: p.p_reference_number, description: p.p_description,
        date: p.p_tx_date, status: 'Posted', created_at: p.p_created_at,
      };
      const answered = o.freshInsert ? inserted : (o.rpcData || STORED);
      o.rpcAnswered = answered;
      return { ok: true, status: 200, json: async () => [{ data: answered }] };
    }
    if (u.indexOf('rpc/law_check_and_void_deposit') !== -1) {
      return { ok: true, status: 200,
               json: async () => [o.voidRow === null ? {} : { data: o.voidRow || STORED }] };
    }
    if (u.indexOf('law_trusttx') !== -1) {
      const sent = init && init.body ? JSON.parse(init.body) : {};
      return { ok: true, status: 200, json: async () => [{ data: sent.data || {} }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
}

async function write(payload, opts) {
  const calls = [];
  const o = opts || {};
  const handler = loadHandler(restStub(calls, o));
  const res = mockRes();
  await handler(mockReq(payload), res);
  // o.rpcAnswered is the row the stubbed RPC handed back -- exposed so a check
  // below can show the two branches really did answer different objects rather
  // than taking my word for it.
  return { res, calls, rpcAnswered: o.rpcAnswered };
}

const line = (label, value) => console.log('  ' + String(label).padEnd(50) + ': ' + value);
const code = (res) => String(res.statusCode) + ' '
  + ((res.body && res.body.error && res.body.error.code) || (res.body && res.body.ok ? 'ok:true' : '-'));

(async () => {

console.log('\n=== FINDING 1: the handler CANNOT TELL a first insert from an existing-id retry,\n'
  + '            and the refusal asserts it is the retry -- so a cheque that was\n'
  + '            JUST POSTED to the trust ledger is reported as "Nothing was saved"');
{
  // A FIRST INSERT returns the row the RPC just built. An EXISTING-ID retry
  // returns the row that was already there. Both come back as `v_row`, both
  // carry the same eleven jsonb keys, and the function exposes NO flag saying
  // which branch ran -- read off the SQL: `if v_existing_found then v_row :=
  // v_existing; else ... insert ... returning * into v_row; end if;` and then
  // one shared `return v_row`.
  // The INSERT-branch case is driven with a DIFFERENT cheque -- a new id, a
  // different amount and a different date -- so the row it returns cannot be
  // confused with the stored one and the two stubs are provably distinct. The
  // clearance fields are the same three either way, which is the only part the
  // refusal reads.
  const FRESH_CHQ = Object.assign({}, MARKED, {
    id: 'T-CHQ-NEW', amount: 125, date: '2026-09-21', created_at: '2026-09-21',
  });
  const retry = await write(MARKED, { rpcData: STORED });
  const fresh = await write(FRESH_CHQ, { freshInsert: true });

  line('EXISTING-ID branch -- nothing was written', code(retry.res));
  line('INSERT branch -- the cheque WAS just written', code(fresh.res));
  // The two branches answered DIFFERENT objects -- the existing-id branch the
  // stored row, the insert branch a row built from the request's own p_ params.
  line('the two branches returned different rows',
    JSON.stringify(retry.rpcAnswered) !== JSON.stringify(fresh.rpcAnswered));
  line('  existing-id branch returned id/amount',
    retry.rpcAnswered.id + ' / ' + retry.rpcAnswered.amount);
  line('  insert branch returned id/amount',
    fresh.rpcAnswered.id + ' / ' + fresh.rpcAnswered.amount);
  line('neither carries a clearance key',
    ['cleared', 'cleared_on', 'cleared_at'].every((k) =>
      retry.rpcAnswered[k] === undefined && fresh.rpcAnswered[k] === undefined));
  line('the two RESPONSES are byte-identical anyway',
    JSON.stringify(retry.res.body) === JSON.stringify(fresh.res.body));
  console.log('  the sentence the biller reads:');
  console.log('    "' + retry.res.body.error.message.slice(0, 120) + '..."');

  findings += 1;
  console.log(`
  THE TWO REALITIES ARE INDISTINGUISHABLE AT THIS SEAM AND THE MESSAGE PICKS ONE.
  The refusal opens "Nothing was saved. This disbursement already exists, and the
  write path that guards the trust balance cannot carry ...". The second clause is
  the diagnosis and it is correct in the common case. The FIRST clause -- Nothing
  was saved -- is false whenever the RPC took its insert branch, and so is
  "already exists".

  HOW THAT CASE IS REACHED, AND IT IS NOT CONTRIVED: lawSetClearance() sends the
  ENTIRE transaction record, not a patch (sairnlaw.html:3523,
  sdnData('write','law_trusttx',t)). So on a disbursement that exists on THIS
  DEVICE but not on the server, marking it cleared is a first insert of a real
  cheque -- balance-checked, committed, and then answered "Nothing was saved".
  A local-only disbursement is exactly the state the client-half review found
  (obligation 13:41:23Z, Finding 1) and exactly what a failed create leaves
  behind.

  THE HARM IS NOT THE WRONG WORD, IT IS WHAT THE WORD INVITES. A biller told
  nothing was saved about a cheque does the obvious thing and enters it again.
  Re-sending the SAME record is harmless -- same id, existing-id branch, no
  write. Entering it AGAIN AS A NEW CHEQUE is a second disbursement against
  client trust funds, and law_client_balance will happily allow it if the balance
  covers it. That is the one direction a trust-accounting refusal must never
  push somebody.

  WHY THE 409 ITSELF IS STILL RIGHT: a clearance the caller asked for was not
  stored, and saying so is correct in both branches. The defect is confined to a
  sentence claiming knowledge the handler does not have.

  SUGGESTED FIX, no new state and no RPC change: stop asserting the branch. The
  handler knows exactly two things -- the clearance did not land, and the rest of
  the row did. Say that: "The clearing status was NOT recorded -- the write path
  that guards the trust balance cannot carry cleared, cleared_at. Any other
  details in this transaction are stored. Do not re-enter this cheque." The last
  sentence is the one that matters and it is true in both branches.

  IF THE BRANCH IS WORTH DISTINGUISHING -- and I do not think it is worth a
  migration on this function -- the SQL already computes it in v_existing_found
  and throws it away at the shared return.`);
}

console.log('\n=== PRESS-ON (3): CLEARANCE_KEYS IS A CLOSED LIST AND A FOURTH FIELD IS\n'
  + '                 SILENTLY CONFIRMED -- exactly the drift cody asked about,\n'
  + '                 driven rather than reasoned');
{
  const known = await write(MARKED, { rpcData: STORED });
  const fourth = await write(
    Object.assign({}, STORED, { cleared_by: 'emp-owner' }), { rpcData: STORED });

  line('the three known keys -> refused', code(known.res));
  line('a FOURTH clearance field, cleared_by -> ', code(fourth.res));
  line('...and the RPC request carried cleared_by',
    JSON.stringify(fourth.calls.find((c) => c.url.indexOf('rpc/law_check') !== -1).body)
      .indexOf('cleared_by') !== -1);

  console.log(`
  THE ANSWER TO THE QUESTION AS ASKED IS: YES, IT DRIFTS SILENTLY, and the
  failure is fail-OPEN. A clearance-ish field outside the three-name list is
  neither sent to the RPC (its nine parameters have no room for it) nor compared
  against what came back, so the caller gets 200 ok:true over a field that was
  never stored -- which is the ORIGINAL defect of this whole obligation,
  reproduced for any future field.

  I AM NOT RAISING IT AS A FINDING, and the reason is a fact rather than a
  judgement: the client writes exactly these three and no more. Verified by
  reading every clearance write in sairnlaw.html -- :3518-3520 sets 'cleared',
  'cleared_on', 'cleared_at' and the revert at :3540-3542 restores the same
  three. There is no fourth field today, so nothing is silently confirmed today.

  WHAT MAKES IT WORTH A LINE ANYWAY: the list lives in api/sd-data.js and the
  fields live in sairnlaw.html, with nothing between them. The cheap guard is
  not a longer list -- it is inverting the test. Compare every key the payload
  sends against the row that came back and refuse on ANY mismatch, then no list
  can go stale; the reason not to is that the plain-upsert keys legitimately
  differ (the RPC stamps status 'Posted' and its own created_at), so an
  inverted test needs a short EXPECTED-TO-DIFFER list instead -- which is the
  same maintenance problem with a safer failure direction. Worth a comment
  naming the three as a mirror of sairnlaw.html at minimum.`);
}

console.log('\n=== PRESS-ON (2): the retires-itself property HOLDS, and it holds on a\n'
  + '                 PARTIAL match too, which is the part that could have\n'
  + '                 gone wrong quietly');
{
  const stored = Object.assign({}, STORED, {
    cleared_on: '2026-09-20', cleared: true, cleared_at: '2026-09-21T12:00:00.000Z',
  });
  const full = await write(MARKED, { rpcData: stored });

  const partial = Object.assign({}, STORED, {
    cleared_on: '2026-09-20', cleared: true, cleared_at: 'A-DIFFERENT-STAMP',
  });
  const part = await write(MARKED, { rpcData: partial });

  line('store carries ALL three -> no refusal', code(full.res));
  line('...and the 200 hands back the STORED row',
    JSON.stringify(full.res.body.data) === JSON.stringify(stored));
  line('store carries two of three -> refused', code(part.res));
  line('...naming ONLY the field that differs',
    JSON.stringify(part.res.body.error.fields));

  console.log(`
  HOLDS, AND THE COMPARISON IS THE RIGHT MECHANISM. The day the RPC learns the
  fields, the values match and this stops firing with nothing to remember to
  remove -- driven above, not taken from the comment. The partial case is the
  one worth having driven: it names cleared_at alone rather than refusing
  wholesale or passing because two of three agreed.

  NOTHING ELSE IN THE RESPONSE PATH DROPS THE FIELDS, which was the second half
  of the question. The 200 answers { ok: true, data: row.data } -- the store's
  own row, not the request echoed back -- so once the RPC carries the clearance
  the client receives it. Checked above: the data returned is the stored object
  including all three clearance keys, and sairnlaw.html's sdnData() reads d.data.

  ONE ASYMMETRY I WOULD RECORD RATHER THAN RAISE: the comparison is
  JSON.stringify on both sides, so '2026-09-20' and a differently-formatted date
  meaning the same day would refuse. That is the safe direction here -- a refusal
  on a real mismatch of representation is better than confirming a value the
  store holds differently -- and it is the same strictness the client-side
  already has. Worth knowing before somebody normalises dates anywhere near
  this.`);
}

console.log('\n=== PRESS-ON (5): the VOID and DEPOSIT routes really do bypass this, neither\n'
  + '                 can reach the RPC another way -- AND the void path carries\n'
  + '                 the ORIGINAL false-success shape, unguarded');
{
  const dep = await write(Object.assign({}, MARKED, { type: 'Deposit' }));
  const depRpc = dep.calls.some((c) => c.url.indexOf('rpc/law_check_and_insert') !== -1);
  const voided = await write(Object.assign({}, MARKED, { status: 'Voided' }));
  const voidRpc = voided.calls.some((c) => c.url.indexOf('rpc/law_check_and_insert') !== -1);

  line('Deposit + clearance -> reached the insert RPC', depRpc);
  line('Deposit + clearance -> answer', code(dep.res));
  line('Voided Disbursement -> reached the insert RPC', voidRpc);
  line('Voided Disbursement -> answer', code(voided.res));

  // The void branch's fallback: when the void RPC hands back no row the handler
  // answers 200 with `data: payload` -- the REQUEST, echoed as though stored.
  const echo = await write(
    Object.assign({}, MARKED, { status: 'Voided' }), { voidRow: null });
  line('void RPC returns NO row -> answer', code(echo.res));
  line('...and the data handed back is the REQUEST, not a stored row',
    JSON.stringify(echo.res.body.data) === JSON.stringify(
      Object.assign({}, MARKED, { status: 'Voided' })));

  console.log(`
  BOTH BYPASSES CONFIRMED AND NEITHER CAN REACH THE RPC ANOTHER WAY. The branch
  order in api/sd-data.js decides it and the order is the guard: the
  payload.status === 'Voided' branch is tested BEFORE the Disbursement branch,
  and the Disbursement branch is gated on status !== 'Voided', so the two are
  mutually exclusive by construction rather than by the cases happening not to
  overlap. A Deposit never mentions the insert RPC at all and takes the plain
  upsert, which sends data: payload wholesale -- which is why a deposit in
  transit keeps its clearance and a cheque does not.

  WHAT I WOULD FLAG, and it is not in the five: THE VOID PATH STILL ANSWERS
  ok:true OVER THE REQUEST. When law_check_and_void_deposit hands back no row,
  the handler answers 200 with data: (voidRow && voidRow.data) ? voidRow.data :
  payload -- the caller's own input, returned as though it were stored. That is
  the exact shape this obligation was opened to remove, one branch above the
  place it was removed, and the sibling disbursement branch REFUSES the same
  condition with 502 DISBURSEMENT_NOT_WRITTEN.

  I AM NOT RAISING IT AS A FINDING OF THIS CHANGE, for two reasons that both
  matter. It PREDATES this commit -- 6b777f00 does not touch that line -- so it
  is not a regression, and a review that charges an author for the neighbourhood
  stops being read. And I could NOT establish that the fallback is reachable:
  the SQL's void function ends with a bare "return v_row" after an UPDATE ...
  returning, so a missing row would need the update to match nothing, which the
  ALREADY_VOIDED and NOT_FOUND refusals above it are there to have caught
  already. UNREACHABLE-BY-ARGUMENT IS NOT UNREACHABLE, which is the whole lesson
  of the obligation I am reviewing -- the disbursement branch's equivalent
  fallback was also unreachable by argument. Recorded as its own open-work row,
  not as a finding here.`);
}

console.log('\n=== PRESS-ON (4): no other arm in the suite asserts over the MESSAGE where it\n'
  + '                 means the LIST -- checked by reading every assertion, and\n'
  + '                 the one that legitimately reads the message is named');
{
  const fs = require('fs');
  const suite = fs.readFileSync(
    require('path').join(__dirname, '..', 'api', 'sd-data-law-trusttx-clearance.test.js'), 'utf8');
  const lines = suite.split('\n');
  const msgReads = [];
  const fieldReads = [];
  lines.forEach((l, i) => {
    if (/error\.message/.test(l)) msgReads.push(i + 1);
    if (/error\.fields/.test(l)) fieldReads.push(i + 1);
  });
  line('lines reading error.message', msgReads.join(', ') || 'none');
  line('lines reading error.fields', fieldReads.join(', ') || 'none');

  // The arm runs from its own test() line to the next one -- taken by index
  // rather than by a fixed character window, because the first version of this
  // check used a 900-character slice, stopped inside the arm's (long) comment
  // before reaching its assertion, and reported the arm as NOT reading .fields
  // when it does. A window that ends early reads exactly like an arm that is
  // missing something.
  const armStart = suite.indexOf('MARKING IT OUTSTANDING IS REFUSED TOO');
  const armEnd = suite.indexOf('await test(', armStart);
  const armText = suite.slice(armStart, armEnd === -1 ? suite.length : armEnd);
  line('the outstanding arm spans N chars', armText.length);
  line('...and reads error.fields', /error\.fields/.test(armText));
  line('...and does NOT read error.message', !/error\.message/.test(armText));

  console.log(`
  CLEAN, AND THE DIVISION IS THE RIGHT ONE. The outstanding arm -- the one whose
  earlier version matched /\\bcleared\\b/ against the refusal's own closing
  words and stayed green over a planted defect -- now reads error.fields, the
  machine-readable list. Nothing else asserts a field NAME through the prose.

  THE ONE ARM THAT STILL READS error.message IS RIGHT TO: "...and the refusal
  SAYS WHAT IS WRONG rather than blaming the network" is a claim ABOUT the
  wording, so the wording is the correct subject. A sentence assertion is only
  wrong when the sentence is standing in for data.

  AND THE MISS IS WRITTEN INTO THE CODE RATHER THAN QUIETLY CORRECTED -- the
  comment beside the refusal in api/sd-data.js explains why 'fields' exists, so
  the next person to add an arm is told the rule instead of rediscovering it.
  That is the part worth copying elsewhere.`);
}

console.log('\n=== PRESS-ON (1): 409 IS RIGHT, AND THE ALTERNATIVE THAT LOOKS BEST IS THE\n'
  + '                 WORST ONE -- 501 would be read by the client as a retryable\n'
  + '                 outage');
{
  const fs = require('fs');
  const src = fs.readFileSync(
    require('path').join(__dirname, '..', 'api', 'sd-data.js'), 'utf8');
  const family = [];
  ['ALREADY_VOIDED', 'WRITE_CONFLICT', 'TRUSTTX_ID_COLLISION',
   'INSUFFICIENT_TRUST_BALANCE', 'VOID_WOULD_NEGATIVE_BALANCE',
   'CLEARANCE_NOT_STORED'].forEach((c) => {
    const re = new RegExp('status\\(409\\)[^\\n]*' + c);
    if (re.test(src)) family.push(c);
  });
  line('codes this endpoint already answers 409 on', family.length);
  line('the family', family.join(', '));
  // The comment justifying 409 cites three precedents by name. Two of them are
  // real; count how many times the third appears anywhere in the file.
  line('WRITE_CONFLICT occurrences in api/sd-data.js',
    (src.match(/WRITE_CONFLICT/g) || []).length);
  line('...and it is answered by a status(409) anywhere',
    /status\(409\)[^\n]*WRITE_CONFLICT/.test(src));

  const lawSrc = fs.readFileSync(
    require('path').join(__dirname, '..', 'sairnlaw.html'), 'utf8');
  line('the client branches on any HTTP status number', /status\s*===\s*(4|5)\d\d/.test(lawSrc));
  line('...it uses the server sentence instead (lawWriteFailText)',
    lawSrc.indexOf('lawWriteFailText') !== -1);

  console.log(`
  409 IS RIGHT AND THE REASONING IN THE CODE IS SOUND AS FAR AS IT GOES: nothing
  failed in the store, its answer was readable, and 502 would tell a biller the
  server is broken when it is working exactly as written.

  WHERE I WOULD PUSH BACK ON THE FRAMING RATHER THAN THE CODE: the question asks
  whether "this path structurally cannot do what you asked" belongs in the 409
  family at all. It does not, strictly -- 409 is a conflict with current state
  and this is a capability gap. 422 is the honest literal answer. BUT THE CHOICE
  THAT MATTERS IS NOT THE ONE ASKED ABOUT. 501 Not Implemented is the code that
  reads best on paper here and it is the dangerous one: it sits in the 5xx
  family, and everything a client, a proxy, a log dashboard or an on-call rota
  does with a 5xx says "the server is having a problem, try later". This refusal
  is permanent until a migration ships. A retryable-looking code on a permanent
  refusal about trust money is worse than a slightly loose 409.

  AND THE PRACTICAL ANSWER IS THAT THE NUMBER IS NEARLY INERT HERE, WHICH I
  CHECKED RATHER THAN ASSUMED: sairnlaw.html branches on no HTTP status number
  at all on this path -- it records the server's own sentence and shows it
  through lawWriteFailText(), so what the biller sees is the message either way.
  The code matters to logs and to any future caller, not to the user today.

  SO: LEAVE IT AT 409, and the reason to leave it is consistency with the five
  codes beside it rather than correctness of the category. If it is ever revisited
  the move is 422, never 501.

  ONE CORRECTION TO THE JUSTIFICATION RATHER THAN TO THE DECISION, measured
  above: the comment says this endpoint "already spends 409 on: ALREADY_VOIDED,
  WRITE_CONFLICT, TRUSTTX_ID_COLLISION". Two of those three are real.
  WRITE_CONFLICT appears in api/sd-data.js EXACTLY ONCE -- in that sentence --
  and is answered by no status(409) anywhere in the file. The conclusion still
  holds and holds more widely than claimed, because there are two real
  precedents the sentence did not cite (INSUFFICIENT_TRUST_BALANCE and
  VOID_WOULD_NEGATIVE_BALANCE, both 409 on this same resource). So the right
  repair is to the list, not to the code. Worth fixing because a cited precedent
  is what the next person checks instead of re-deriving it, and this one sends
  them looking for something that is not there.`);
}

console.log('\n=== CHECKED AND CORRECT ===');
{
  console.log(`  * THE SECTION-1 ARM IS THE LOAD-BEARING ONE AND IT IS HONEST ABOUT WHY:
    "the RPC call carries NO clearance field at all" is a fact about
    api/sd-data.js alone and needs no model of Postgres, so it cannot be wrong
    about the database. Everything downstream rests on it and it rests on
    nothing.
  * THE SQL READING IS CORRECT, re-derived from the function body rather than
    from the commit message: nine p_ parameters, none of them a clearance
    field; jsonb_build_object over eleven fixed keys (the message says ten --
    the eleventh is 'status'); and one shared return v_row after both branches.
  * THE DEPOSIT CONTRAST IS WHAT MAKES IT A SEAM RATHER THAN A RULE, and it is
    driven in the suite rather than asserted in prose: same app, same resource,
    same field, opposite outcome, decided by type.
  * fields EXISTS BECAUSE THE CONTROL CAUGHT THE AUTHOR'S OWN ARM, twice, and
    both misses are recorded in the code instead of being quietly fixed. The
    second miss -- a regex over the refusal's prose matching the refusal's own
    closing words -- is the exact shape that survives review, and it was caught
    by a mutation rather than by reading.
  * 5 MUTATIONS ALL REFUSED and api/sd-data.js byte-identical afterwards, run
    here rather than taken from the record: tests/run_law_trusttx_clearance_sabotage_probe.py
    9/9, and the suite 9/9.
  * DECLARING THE RPC SIGNATURE CHANGE OUT OF SCOPE WAS RIGHT, and for a reason
    the record states plainly: it is a migration on the function that gates trust
    balances, with a deploy-ordering hazard if the api half lands first.`);
}

console.log('\n' + findings + ' finding(s). Report-only: exit 0 by design.\n');
process.exit(0);

})();
