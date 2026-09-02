// confirmVoid's rejection path -- driven verbatim from sairnlaw.html.
//
// TED'S CROSS-APP SCAN FLAGGED THIS AS A read-await-write STALE-ARRAY HIT AND
// THAT PART WAS A FALSE POSITIVE. Both confirmVoid and saveTrustTransaction
// RE-READ the collection after the await, so an unrelated transaction changed
// or added during the round trip survives -- cases 5 and 6 below pass against
// the ORIGINAL code. Same outcome as the two reported SAIRNlegacy hits.
//
// WHAT WAS REAL IS THE SAME FAMILY POINTING THE OTHER WAY. Re-reading is
// necessary and not sufficient: the revert set the record back to Posted
// UNCONDITIONALLY. If another device voided the same transaction during the
// round trip, and the server rejected THIS request for any reason other than
// ALREADY_VOIDED, the revert resurrected a genuinely voided trust transaction
// and wiped the other void's reason. clientLedgerBalance counts Posted rows,
// so a resurrected DEPOSIT inflates a client trust balance -- and that balance
// is what saveTrustTransaction's disbursement guard checks against. The
// failure direction is authorising a disbursement that overdraws real client
// money.
//
// The same trap applied to a transaction that was already Voided before the
// click: the Void button renders only on a Posted row, but the row comes from
// a snapshot, and another device can void it between render and click.
//
// SCORES: 5/8 against the pre-fix function, 8/8 after. The three that moved are
// the two concurrent-void cases and the already-voided case.
const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', '..', 'sairnlaw.html');
const src = fs.readFileSync(HTML, 'utf8');

function extract(name) {
  const start = src.indexOf('async function ' + name + '(');
  if (start < 0) throw new Error('not found: ' + name);
  let i = src.indexOf('{', start), depth = 0;
  for (; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced: ' + name);
}
const CONFIRM_VOID = extract('confirmVoid');

// ── stubbed world ────────────────────────────────────────────────────────
function makeWorld(opts) {
  const store = { law_trusttx: JSON.parse(JSON.stringify(opts.initial)) };
  const fields = { voidreason: opts.reason || 'clerical error' };
  const world = {
    voidTxId: opts.voidTxId,
    $: (id) => ({
      get value() { return fields[id] || ''; },
      set value(v) { fields[id] = v; },
      set textContent(v) { world.lastErr = v; },
      get textContent() { return world.lastErr || ''; },
      classList: { add() {}, remove() {} },
    }),
    trustTransactions: () => JSON.parse(JSON.stringify(store.law_trusttx)),
    st: (k, v) => { store[k] = JSON.parse(JSON.stringify(v)); },
    closeVoidModal: () => {},
    rTrust: () => {}, rDash: () => {},
    toast: (m) => { world.lastToast = m; },
    sdnData: async (op, res, rec) => {
      // The concurrent event happens WHILE the request is in flight -- the
      // whole point of the shape being tested.
      if (opts.during) opts.during(store);
      await new Promise(r => setTimeout(r, 5));
      return opts.result;
    },
    store,
  };
  return world;
}

async function run(opts) {
  const w = makeWorld(opts);
  const fn = new Function('w', `
    var voidTxId = w.voidTxId, $ = w.$, trustTransactions = w.trustTransactions, st = w.st,
        closeVoidModal = w.closeVoidModal, rTrust = w.rTrust, rDash = w.rDash,
        toast = w.toast, sdnData = w.sdnData;
    ${CONFIRM_VOID}
    return confirmVoid();
  `);
  await fn(w);
  return w.store.law_trusttx;
}

const TX = (id, status) => ({ id, matter_id: 'M1', client_id: 'C1', type: 'Deposit', amount: 500,
  date: '2026-06-01', method: 'Check', reference_number: '', description: 'retainer',
  status: status || 'Posted', voided_reason: status === 'Voided' ? 'earlier void' : '',
  voided_at: status === 'Voided' ? '2026-06-02T00:00:00Z' : '', created_at: '2026-06-01' });

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; console.log('  ok  ' + name); return; }
  fail++;
  console.log('  FAIL ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

(async () => {
  console.log('confirmVoid, driven verbatim from sairnlaw.html\n');

  // 1. The happy path still works.
  let out = await run({ initial: [TX('TR-1')], voidTxId: 'TR-1', result: { ok: true } });
  check('a clean void marks the transaction Voided', out[0].status, 'Voided');

  // 2. Rejection reverts its own record.
  out = await run({ initial: [TX('TR-1')], voidTxId: 'TR-1',
    result: { rejected: true, code: 'BALANCE_GUARD', message: 'would overdraw' } });
  check('a rejected void reverts that record to Posted', out[0].status, 'Posted');

  // 3. ALREADY_VOIDED keeps the void, per the code's own comment.
  out = await run({ initial: [TX('TR-1')], voidTxId: 'TR-1',
    result: { rejected: true, code: 'ALREADY_VOIDED', message: 'already voided' } });
  check('ALREADY_VOIDED leaves it Voided', out[0].status, 'Voided');

  // 4. THE ONE UNDER TEST. Another device voids the SAME transaction while the
  //    request is in flight, and the server rejects THIS request for a
  //    different reason. The revert should not resurrect a genuinely voided
  //    transaction -- that puts money back into the trust ledger.
  out = await run({
    initial: [TX('TR-1')], voidTxId: 'TR-1',
    during: (store) => {
      store.law_trusttx = store.law_trusttx.map(t => t.id === 'TR-1'
        ? Object.assign({}, t, { status: 'Voided', voided_reason: 'voided on another device',
                                 voided_at: '2026-06-03T00:00:00Z' })
        : t);
    },
    result: { rejected: true, code: 'BALANCE_GUARD', message: 'would overdraw' },
  });
  check('a transaction voided elsewhere DURING the round trip stays Voided',
    out[0].status, 'Voided');
  check('and its reason is not wiped', out[0].voided_reason, 'voided on another device');

  // 5. A DIFFERENT transaction changed during the flight must survive the
  //    revert untouched -- the SAIRNlegacy symptom.
  out = await run({
    initial: [TX('TR-1'), TX('TR-2')], voidTxId: 'TR-1',
    during: (store) => {
      store.law_trusttx = store.law_trusttx.map(t => t.id === 'TR-2'
        ? Object.assign({}, t, { status: 'Voided', voided_reason: 'other clerk' }) : t);
    },
    result: { rejected: true, code: 'BALANCE_GUARD', message: 'would overdraw' },
  });
  check('an unrelated void made during the round trip survives the revert',
    out.find(t => t.id === 'TR-2').status, 'Voided');

  // 6. A transaction ADDED during the flight must survive.
  out = await run({
    initial: [TX('TR-1')], voidTxId: 'TR-1',
    during: (store) => { store.law_trusttx = store.law_trusttx.concat([TX('TR-3')]); },
    result: { rejected: true, code: 'BALANCE_GUARD', message: 'would overdraw' },
  });
  check('a transaction added during the round trip survives the revert',
    out.map(t => t.id).sort(), ['TR-1', 'TR-3']);

  // 7. Voiding something that was ALREADY Voided before the click.
  out = await run({ initial: [TX('TR-1', 'Voided')], voidTxId: 'TR-1',
    result: { rejected: true, code: 'BALANCE_GUARD', message: 'would overdraw' } });
  check('an already-Voided transaction is not resurrected by a rejected re-void',
    out[0].status, 'Voided');

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
