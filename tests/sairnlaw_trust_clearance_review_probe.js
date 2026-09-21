// tests/sairnlaw_trust_clearance_review_probe.js
//
// Run:  node tests/sairnlaw_trust_clearance_review_probe.js
//
// INDEPENDENT REVIEW of 2ee9c819 (cody) -- lawSetClearance() getting the three
// things confirmVoid() has had since 2026-09-02 -- under the Tier A obligation
// cody opened 2026-09-21T13:41:23Z on law_trusttx. The register ASSIGNS this
// obligation to fourth (reviewer_owner, stamped at open time), which is why
// there is no question this turn about who was reviewing it.
//
// ── REPORT-ONLY AND EXIT 0 ────────────────────────────────────────────────
// Same precedent as tests/dnt_rollup_review_probe.js: a finding on another
// agent's file, and a failing suite would block every other session's push on a
// defect they did not write. It PRINTS. I am not fixing anything -- a review
// claim is not the file.
//
// ── THE HARNESS IS CODY'S OWN, DELIBERATELY ───────────────────────────────
// It lifts lawSetClearance() out of the shipped sairnlaw.html and reuses the
// same stub shape, INCLUDING the fidelity fix cody made this turn -- a
// trustTransactions() that deep-copies, because one returning the store by
// reference makes the whole stale-snapshot class unplantable. Reusing it means
// a finding here is a finding about the function and not about my fixture.
//
// Five press-on points. Three hold, one holds for a better reason than the one
// given, and one has a finding that only exists because press-on (3) and
// press-on (5) are read together.

'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8').replace(/\r\n/g, '\n');
const engineSrc = fs.readFileSync(
  path.join(ROOT, 'api', '_lib', 'law-trust-reconcile.js'), 'utf8');

let findings = 0;

function grab(sig, term) {
  const a = html.indexOf(sig);
  assert.ok(a > 0, 'not found in sairnlaw.html: ' + sig);
  const e = html.indexOf(term, a);
  assert.ok(e > a, 'terminator missing after ' + sig);
  return html.slice(a, e + term.length);
}

function harness(o) {
  o = o || {};
  const store = { law_trusttx: JSON.parse(JSON.stringify(o.rows || [])) };
  const calls = { writes: [], toasts: [] };
  const ctx = {
    console: { warn() {}, error() {} },
    ld: (k, d) => (store[k] === undefined ? d : JSON.parse(JSON.stringify(store[k]))),
    st: (k, v) => { store[k] = JSON.parse(JSON.stringify(v)); return true; },
    // Cody's fidelity fix, kept: a deep copy is what the real ld() does.
    trustTransactions: () => JSON.parse(JSON.stringify(store.law_trusttx)),
    rTrust: () => { calls.renders = (calls.renders || 0) + 1; },
    toast: (m) => calls.toasts.push(m),
    fdate: (d) => String(d || '--'),
    lawWriteFailText: (r, f) => f,
    prompt: (m, d) => (o.promptValue === undefined ? d : o.promptValue),
    sdnData: async (a, r, rec) => {
      calls.writes.push({ a, r, id: rec && rec.id, sent: JSON.parse(JSON.stringify(rec)) });
      if (o.duringWrite) o.duringWrite(store);
      return o.syncFails ? null : (o.syncResult !== undefined ? o.syncResult : { ok: true });
    },
    __store: store, __calls: calls,
  };
  vm.createContext(ctx);
  vm.runInContext([
    grab('async function lawSetClearance(', '\n}\n'),
    grab('function lawMarkCleared(', '\n}\n'),
    grab('function lawMarkOutstanding(', '\n'),
  ].join('\n'), ctx);
  return ctx;
}

const ROW = (o) => Object.assign(
  { id: 'T1', client_id: 'CL-1', type: 'Disbursement', amount: 40,
    date: '2026-09-14', status: 'Posted' }, o || {});
const rowOf = (c) => c.__store.law_trusttx[0];
const lastToast = (c) => (c.__calls.toasts[c.__calls.toasts.length - 1] || '');

function head(n, t) { console.log('\n=== FINDING ' + n + ': ' + t + '\n'); }
function answered(n, t) { console.log('\n=== PRESS-ON (' + n + '): ' + t + '\n'); }

(async function () {

  // ── PRESS-ON (3), and the finding it leads to ────────────────────────────
  answered(3, 'the already-in-target-state refusal can only be OVER-permissive,\n'
            + '                 never over-restrictive -- every shape cody worried about falls\n'
            + '                 through to the round trip, which is the safe side');
  {
    const cases = [
      ['cleared_on stored as null rather than deleted, marking outstanding',
       ROW({ cleared: false, cleared_on: null }), null, true],
      ['cleared_on stored as a differently-shaped string, re-dating',
       ROW({ cleared: true, cleared_on: '09/20/2026' }), '2026-09-20', false],
      ['cleared_on absent entirely, marking outstanding',
       ROW({ cleared: false }), null, true],
      ['the EXACT outstanding state, marking outstanding',
       ROW({ cleared: false }), null, true],
    ];
    for (const [what, row, on, outstanding] of cases) {
      if (row.cleared_on === undefined && outstanding) delete row.cleared_on;
      const c = harness({ rows: [row] });
      await c.lawSetClearance('T1', on, outstanding);
      const wrote = c.__calls.writes.length;
      console.log('  ' + what.slice(0, 58).padEnd(58) + ' write sent: ' + (wrote ? 'yes' : 'NO -- refused'));
    }
    console.log(`
  HOLDS, AND THE DIRECTION IS THE POINT. The refusal is
  \`outstanding ? (t.cleared===false && t.cleared_on===undefined)
               : (t.cleared===true && t.cleared_on===clearedOn)\`
  -- two strict equality tests against a value that came out of a prompt. Every
  shape cody asked about FAILS those tests and therefore falls through to the
  round trip: cleared_on left as null is not undefined, and a differently
  formatted date is not === the prompt string. So the refusal can only ever be
  too PERMISSIVE (one redundant write), never too restrictive (a Re-date
  silently refused). That is the safe side and it is safe by construction rather
  than by the cases happening to be absent.`);
  }

  // ── FINDING 1 ───────────────────────────────────────────────────────────
  head(1, 'the refusal and the disbursement gap COMBINE: on a cheque the\n'
        + '            server never stored, pressing Cleared again with the same date is\n'
        + '            REFUSED with "already marked cleared" -- the retry the user was\n'
        + '            just told to make');
  {
    // Step 1: the disbursement path cody documents -- the server answers ok:true
    // carrying the stored row and writes NOTHING. The function reads a truthy
    // result and reports success.
    const c = harness({ rows: [ROW({})], syncResult: { ok: true } });
    await c.lawMarkCleared('T1');                 // prompt default = today
    const after = rowOf(c);
    console.log('  press 1: local row is cleared           : %s (on %s)',
      after.cleared, after.cleared_on);
    console.log('  press 1: toast                          : %s', lastToast(c));
    // Step 2: the user learns the server has nothing (a colleague's device shows
    // it outstanding) and presses Cleared again with the SAME date to retry.
    const c2 = harness({ rows: [JSON.parse(JSON.stringify(after))] });
    await c2.lawSetClearance('T1', after.cleared_on, false);
    const retried = c2.__calls.writes.length > 0;
    console.log('  press 2, SAME date (the retry)          : write sent: %s',
      retried ? 'yes' : 'NO -- REFUSED');
    console.log('  press 2: toast                          : %s', lastToast(c2));
    if (!retried) {
      findings++;
      console.log(`
  Both halves are cody's own: press-on (3) records the refusal as scoped "SO
  RE-DATE STILL WORKS", and press-on (5) records that on a Disbursement the
  server stores no clearance at all and this function "reports success over a
  no-op". Read together they close the only recovery path the user has.

  THE SEQUENCE, DRIVEN ABOVE. A cheque is marked cleared. The local row says
  cleared, the toast says "Marked cleared", and the server has nothing --
  rpc/law_check_and_insert_disbursement's existing-id branch returned the stored
  row without writing. The practice then discovers the mismatch the only way
  they can, from another device. They press Cleared again with the same date,
  because the date has not changed and re-sending is the obvious repair.

  THEY ARE TOLD "This transaction is already marked cleared 2026-09-21." and
  NOTHING IS SENT. The refusal is reading the LOCAL row, which is the one thing
  in the system that is wrong. To get a write out at all they have to enter a
  DIFFERENT date -- which would be a false clearance date -- or mark it
  outstanding and then cleared again, which is two writes and not a sequence
  anybody would guess.

  WHY THIS IS NOT JUST A RESTATEMENT OF PRESS-ON (5). Press-on (5) is about the
  server losing the write, and it is honestly recorded as out of scope with its
  own open-work row. This is about the CLIENT refusing the retry, it is in the
  file this change touches, and it would still be there after the SQL is fixed:
  any future path where a write is reported successful but does not land leaves
  the local row in a state that refuses its own retry.

  IT IS ALSO THE ONE CASE THE REFUSAL'S OWN REASONING DOES NOT COVER. The
  comment says an already-in-target-state press "is a round trip that can ONLY
  LOSE -- it re-sends the record, risks a failure whose revert has nothing to
  revert, and toasts a change nobody made". That is true when local and server
  AGREE. When they disagree -- exactly the state the disbursement gap produces
  -- the round trip is the only thing that can WIN, and it is the case that gets
  refused.

  SUGGESTED FIX, and the smaller one first: exempt the retry. The record already
  carries cleared_at, so "local says cleared and the last write did not land" is
  expressible -- keep a flag on the row when sdnData returns falsy and let the
  refusal through while it is set. Failing that, the refusal's toast should
  offer the way out in words ("already marked cleared here; if another device
  disagrees, mark it outstanding and clear it again") rather than reading as a
  completed action. What it must not do is what it does now: refuse silently and
  correctly according to a record nobody has any reason to trust.`);
    } else {
      console.log('  CLOSED -- the retry now reaches the server.');
    }
  }

  // ── PRESS-ON (1) ────────────────────────────────────────────────────────
  answered(1, 'leaving another device\'s value standing is right, and the toast\n'
            + '                 carries the one thing that makes it right');
  {
    // My change is "outstanding"; another device records "cleared" mid-flight.
    const c = harness({
      rows: [ROW({ cleared: true, cleared_on: '2026-09-18', cleared_at: 'OLD' })],
      syncFails: true,
      duringWrite: (store) => {
        store.law_trusttx[0].cleared = true;
        store.law_trusttx[0].cleared_on = '2026-09-19';
        store.law_trusttx[0].cleared_at = 'THEIRS';
      },
    });
    await c.lawSetClearance('T1', null, true);
    const r = rowOf(c);
    console.log('  my write FAILED, theirs landed mid-flight');
    console.log('  local row now                          : cleared=%s on=%s at=%s',
      r.cleared, r.cleared_on, r.cleared_at);
    console.log('  the record was left alone              : %s',
      r.cleared_at === 'THEIRS');
    console.log('  the toast names the collision          : %s',
      /changed on another device/.test(lastToast(c)));
    console.log('  ...and does NOT claim the change applied: %s',
      /did NOT reach the server/.test(lastToast(c)));
    console.log(`
  RIGHT, AND FOR A REASON WORTH STATING RATHER THAN ASSUMING. The two values
  disagree about money, so one of them has to stand, and the question is which
  one has EVIDENCE behind it. Theirs reached the server; mine did not. Leaving
  theirs is the only choice that does not assert something no server agrees
  with, and overwriting it is precisely the erasure this change was made to stop
  -- the review that opened the obligation asked whether the revert could
  RESURRECT another device's clearance and the answer was that it could ERASE
  one.

  THE TOAST IS ADEQUATE BECAUSE IT SAYS BOTH THINGS, which is the part that
  could have been got wrong: that this change did NOT reach the server, and that
  the record now shows somebody else's value. Either sentence alone would
  mislead -- the first reads as "nothing happened", the second as "your change
  was overridden".

  WHERE I WOULD NOT DEFEND IT: the user is told to "Refresh to see the current
  ledger" and the ledger has ALREADY been re-rendered from the re-read array, so
  they are looking at the current state while being told to go and get it. Not a
  finding; the instruction is harmless and one word ("refreshed") would be more
  accurate.`);
  }

  // ── PRESS-ON (4) ────────────────────────────────────────────────────────
  answered(4, 'the timestamp-not-nonce assumption HOLDS, and for a stronger\n'
            + '                 reason than the prompt cody relied on');
  {
    const outBtn = /t\.cleared_on\|\|t\.cleared===false\?'':' <button[^>]*lawMarkOutstanding/.test(html);
    const setsBeforeAwait = (() => {
      const f = grab('async function lawSetClearance(', '\n}\n');
      return f.indexOf("st('law_trusttx',list)") < f.indexOf('await sdnData')
        && f.indexOf('rTrust();') < f.indexOf('await sdnData');
    })();
    console.log('  the Outstanding button is omitted once the row is outstanding : %s', outBtn);
    console.log('  st() and rTrust() both run BEFORE the await                   : %s',
      setsBeforeAwait);
    console.log('  the Cleared path goes through a blocking prompt()             : %s',
      /var d=prompt\(/.test(grab('function lawMarkCleared(', '\n}\n')));
    console.log(`
  HOLDS. Cody's stated reason is "impossible through a prompt() and a
  disabled-free button path", and the prompt half is true -- prompt() blocks, so
  a second click cannot be dispatched while the first is open.

  THE OUTSTANDING PATH HAS NO PROMPT AT ALL (lawMarkOutstanding goes straight to
  lawSetClearance(id, null, true)), so the prompt argument does not cover it --
  and it holds anyway for a better reason: st() and rTrust() both run
  SYNCHRONOUSLY BEFORE the await, JavaScript dispatches the second click only
  after the first handler yields, and by then the re-render has REMOVED the
  Outstanding button because the row is now cleared===false. So the control the
  second press would need is gone before the second press can be delivered.

  That is a stronger guarantee than "nobody can click that fast", and it is
  worth having in the record because the weaker version invites somebody to
  "fix" it with a nonce that is not needed. What WOULD break it is moving
  rTrust() after the await, which is the edit to watch.`);
  }

  // ── PRESS-ON (2) ────────────────────────────────────────────────────────
  answered(2, 'cleared_at is read by nothing, and the size argument holds with\n'
            + '                 room to spare');
  {
    const reads = ['cleared_on', 'cleared', 'date', 'amount', 'type', 'isVoided'];
    console.log('  the reconcile engine names cleared_at anywhere : %s',
      /cleared_at/.test(engineSrc));
    console.log('  the fields it does read                        : %s',
      reads.filter((f) => new RegExp('\\b' + f).test(engineSrc)).join(', '));
    const row = ROW({ cleared: true, cleared_on: '2026-09-20',
                      cleared_at: new Date().toISOString() });
    console.log('  a full cleared row, serialised                 : %d bytes',
      JSON.stringify(row).length);
    console.log('  cleared_at adds                                : %d bytes',
      JSON.stringify({ cleared_at: new Date().toISOString() }).length - 2);
    console.log(`
  HOLDS, AND THE SIZE HALF IS NOT CLOSE. The platform's jsonb cap on this family
  of tables is 64KB; a whole cleared trust row serialises to a couple of hundred
  bytes and cleared_at adds about forty. There is no realistic path from here to
  a size limit, so that part of the worry can be closed rather than carried.

  ON FIELD-WISE READERS: api/_lib/law-trust-reconcile.js never names cleared_at,
  and a repository-wide search finds it only in sairnlaw.html and this feature's
  own tests -- the other hits are sairnbuild.html's cheque register, a different
  app with its own unrelated field of the same name. So cody's "changes no
  reconciliation figure" is right, and the way it was checked (driving the engine
  with and without the field and comparing output byte-for-byte) is the right
  way to check it.

  ONE THING I WOULD ADD TO THE RECORD rather than raise: cleared_at is written
  on EVERY press, including the ones that succeed, and it is never read except
  by the revert. A field that exists only to be compared by the code that wrote
  it is fine -- confirmVoid's stamp is the same shape -- but it is worth a line
  saying so, because the next reader will reasonably assume a timestamp field
  means "when it cleared" and it does not: cleared_on means that.`);
  }

  // ── PRESS-ON (5) ────────────────────────────────────────────────────────
  answered(5, 'cody\'s reading of the SQL is CORRECT, checked against the\n'
            + '                 function body rather than against the description');
  {
    const sqlPath = path.join(ROOT, 'sql', 'sairnlaw_trusttx_functions.sql');
    let sql = '';
    try { sql = fs.readFileSync(sqlPath, 'utf8'); } catch (e) { sql = ''; }
    const fn = sql.indexOf('law_check_and_insert_disbursement');
    const body = fn >= 0 ? sql.slice(fn, fn + 4000) : '';
    const params = (body.match(/p_[a-z_]+/g) || []);
    const uniq = [...new Set(params)];
    console.log('  the SQL file was readable                     : %s', !!sql);
    console.log('  its parameters                                : %s', uniq.join(', '));
    console.log('  any parameter mentioning clearance            : %s',
      uniq.filter((p) => /clear/.test(p)).join(', ') || 'NONE');
    console.log('  an existing-id branch that RETURNS without writing : %s',
      /already|existing|idempot/i.test(body));
    console.log('  api/sd-data.js routes a Disbursement to that rpc   : %s',
      /law_check_and_insert_disbursement/.test(
        fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8')));
    console.log(`
  CONFIRMED. The parameter list carries no clearance field of any kind, so a
  clearance cannot reach the row through this path even on a first insert, and
  the existing-id branch returns the stored row without writing -- which is
  correct as retry-idempotency and is exactly what makes the clearance write a
  silent no-op. The response is ok:true, lawSetClearance reads a truthy result,
  and it toasts "Marked cleared".

  DEPOSITS REALLY ARE FINE: they take the plain upsert, which writes data
  wholesale, so cleared_on lands.

  DECLARING THIS OUT OF SCOPE WAS RIGHT. It is a server-plus-SQL change on trust
  money; doing it inside a client-side hardening commit would have put a
  migration and an rpc signature change in a diff nobody would expect to find
  them in. It has its own open-work row and its own claim, which is the handling
  the platform asks for.

  WHAT THE DISCLOSURE DOES NOT SAY, and FINDING 1 above is the consequence: the
  client's own refusal makes that server gap unrecoverable from the UI. The two
  were recorded as separate concerns and they are not separate in the hands of
  the person holding the cheque.`);
  }

  console.log('\n=== CHECKED AND CORRECT ===');
  console.log(`  * all three of confirmVoid's properties really are carried across, driven
    on cody's own two-device harness: the ledger is RE-READ after the await, the
    revert fires only on this call's own stamp, and an already-in-target-state
    press is refused.
  * the fidelity fix is the load-bearing part of the suite and cody found it
    rather than inheriting it: a trustTransactions() stub returning the store BY
    REFERENCE makes the entire stale-snapshot class unplantable, so every
    two-device arm before it was green for free.
  * the revert writes back the RE-READ array, so a hydration landing mid-flight
    is not written away -- and that is the defect that was whole-array rather
    than one row.
  * lawMarkCleared returns its promise rather than dropping it, which is what
    lets a test assert after the write settles instead of before.
  * a voided transaction is refused before anything else, and the refusal is
    checked ahead of the target-state test so a voided row cannot be "already
    cleared".`);

  console.log('\n' + findings + ' finding(s). Report-only: exit 0 by design.');
  process.exit(0);
})();
