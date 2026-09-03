// SAIRNlaw trust disbursement -- the cross-client trusttx_id collision.
//
// FOUND 2026-09-03 while re-verifying SAIRNlaw's open list. Recorded in
// docs/SAIRN-OPEN-WORK-INDEX.md as "can return a null row on a cross-client
// trusttx_id collision", which names the SECOND-worst of two failures.
//
// ROOT CAUSE, ONE SENTENCE: the advisory lock is keyed on
// (license_hash, client_id) and the uniqueness constraint and idempotency
// lookup are keyed on (license_hash, trusttx_id). One is per-client, the other
// per-licence, and they disagree.
//
//   FAILURE 1 -- A CLIENT'S TRUST ROW RETURNED TO ANOTHER CLIENT'S REQUEST.
//   The retry-idempotency lookup had no client predicate, so a disbursement
//   for client B whose id already existed under client A took the retry branch
//   and returned A's row: A's amount, matter, description and reference
//   number, handed back with HTTP 200 {ok:true} for B's transaction. No money
//   moved for B and nothing said so.
//
//   FAILURE 2 -- A PHANTOM DISBURSEMENT THAT REPORTS SUCCESS.
//   `on conflict do nothing returning *` returns NO row, so the function
//   returned a null composite, and api/sd-data.js did
//   `data: row ? row.data : payload` -- echoing THE CALLER'S OWN PAYLOAD back
//   as the stored row. Screen said posted; ledger had nothing.
//
//   REACHABLE, NOT THEORETICAL. sairnlaw.html's newId() is
//   prefix + Date.now() + floor(random()*1000) -- a thousand suffixes per
//   millisecond, not a UUID, shared across every client in the firm.
//
// ── WHAT THIS FILE CAN AND CANNOT PROVE, STATED PLAINLY ─────────────────
// There is no Postgres in this environment, so the plpgsql cannot be executed.
// This file therefore does two DIFFERENT things and does not pretend they are
// the same:
//
//   (a) STRUCTURAL assertions against the REAL SQL text and the REAL API
//       source. These are what tie the file to reality, and every one of them
//       is backed by a negative control that edits the real file and must make
//       this suite fail.
//   (b) A DECISION-TABLE MODEL of the function's control flow, asserting the
//       intended behaviour case by case. THE MODEL IS A REIMPLEMENTATION and
//       proves nothing about the SQL on its own -- it documents the contract
//       the structural assertions pin down. Said out loud because a model
//       mistaken for a driver is exactly how a test ends up asserting its own
//       copy.

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', '..');
// CONSOLIDATED 2026-09-03: all three law_trusttx functions now live in ONE
// file. The three that used to define them are gutted -- the duplicate text is
// gone, which is what actually removes the silent-revert trap. Assertions
// below therefore read the consolidated file, and separate ones assert the
// three old files define NOTHING.
const SQL = fs.readFileSync(path.join(ROOT, 'sql', 'sairnlaw_trusttx_functions.sql'), 'utf8');
const OLD_FILES = ['sairnlaw_trust_disbursement_atomic_check.sql',
                   'sairnlaw_deposit_void_balance_guard.sql',
                   'sairnlaw_trusttx_cross_client_collision_2026-09-03.sql']
  .map((f) => [f, fs.readFileSync(path.join(ROOT, 'sql', f), 'utf8')]);
const API = fs.readFileSync(path.join(ROOT, 'api', 'sd-data.js'), 'utf8');
const HTML = fs.readFileSync(path.join(ROOT, 'sairnlaw.html'), 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

// Drops comment lines, for any assertion about ORDER or ABSENCE. Used twice
// below because both the SQL and the API fix EXPLAIN themselves in prose that
// names the very strings being checked -- scrubber item 16 shape A, which
// caught this file twice before the negative controls even ran.
function stripLines(text, commentRe) {
  return text.split('\n').filter((l) => !commentRe.test(l)).join('\n');
}

// The function body only -- so an assertion cannot pass on the header prose
// that EXPLAINS the fix. Scrubber item 16 shape A: this file's own commentary
// contains every phrase the guards do.
const FN_START = SQL.indexOf('create or replace function public.law_check_and_insert_disbursement');
const FN_END = SQL.indexOf('$$;', FN_START);
const FN = SQL.slice(FN_START, FN_END);
// COMMENTS STRIPPED for any assertion about ORDER or ABSENCE. The first
// version compared indexOf('TRUSTTX_ID_COLLISION') against
// indexOf('INSUFFICIENT_TRUST_BALANCE') over the raw body and failed -- because
// the comment EXPLAINING why the collision is checked first names the balance
// error. Scrubber item 16 shape A: an assertion tripping on the prose about the
// thing it is checking.
const FN_CODE = stripLines(FN, /^\s*--/);

// ── (a) STRUCTURAL: the SQL actually carries the fix ───────────────────
// COUNTED, NOT MERELY PRESENT. There are TWO client-scoped lookups -- the
// idempotency check and the post-conflict re-select -- and the first version
// of this assertion used .test(), which the SECOND one satisfied on its own.
// The negative control that deleted the client predicate from the FIRST lookup
// (restoring the actual leak) scored a clean 26/26. Both must carry it.
check('BOTH trusttx lookups are client-scoped, not just one',
  (FN_CODE.match(/where license_hash = p_license_hash\s*\n\s*and trusttx_id = p_trusttx_id\s*\n\s*and client_id = p_client_id;/g) || []).length, 2);
// Same failure, same fix: two raise sites (the lookup path and the race path).
// .test() passed while one of them was turned into a `raise notice`.
check('a same-id/different-client collision RAISES on BOTH paths, never returns the other row',
  (FN_CODE.match(/raise exception\s*\n\s*'TRUSTTX_ID_COLLISION/g) || []).length, 2);
// And the branch has to be LIVE. `if false then` left the constant in the file
// and every text assertion above it still passed -- scrubber item 16 shape B.
check('the collision branch is reached by a real condition, not disabled',
  /select client_id into v_other_client[\s\S]{0,200}?if found then/.test(FN_CODE) &&
  !/if false then/.test(FN_CODE), true);
// The collision must be tested BEFORE the balance arithmetic, or the caller is
// told their balance is short when the balance was never the problem.
check('the collision is checked before the balance guard, not after',
  FN_CODE.indexOf('TRUSTTX_ID_COLLISION') < FN_CODE.indexOf('INSUFFICIENT_TRUST_BALANCE'), true);
check('the collision message does NOT name the other client',
  /already exists under a different client/.test(FN) &&
  !/v_other_client/.test(FN_CODE.slice(FN_CODE.indexOf('raise exception'))), true);
check('the do-nothing null path is closed by a re-select',
  /if v_row\.trusttx_id is null then/.test(FN_CODE) &&
  /v_row := v_existing;/.test(FN_CODE.slice(FN_CODE.indexOf('if v_row.trusttx_id is null then'))), true);
// The final guard must be REACHED, not merely present. `if false then` in front
// of it re-opened the null return while the constant stayed in the file.
check('no path can return null -- a final guard raises, and it is live',
  /if v_row\.trusttx_id is null then\s*\n\s*raise exception\s*\n\s*'DISBURSEMENT_NOT_WRITTEN/.test(FN_CODE), true);
check('there are exactly two null-guards: the re-select and the final refusal',
  (FN_CODE.match(/if v_row\.trusttx_id is null then/g) || []).length, 2);
// The retry contract must survive the fix: same id AND same client still
// returns the stored row without re-running the balance check.
check('a genuine same-client retry still short-circuits to the existing row',
  /if v_existing_found then\s*\n\s*v_row := v_existing;/.test(FN), true);
// Widening the lock would serialize every client in the firm behind one
// another for a rare collision. The fix makes the rare case loud instead.
check('the advisory lock is still per-client, not widened to the licence',
  /pg_advisory_xact_lock\(hashtext\(p_license_hash \|\| ':' \|\| p_client_id\)\)/.test(FN), true);

// ── the superseded chain -- the trap that would silently undo this ─────
// Re-running step 3a restores the vulnerable body with no error anywhere.
// Step 3a already carried that warning about step 2; it now carries it about
// this file too.
// THE TRAP IS GONE BECAUSE THE DUPLICATE TEXT IS GONE, not because a third
// warning was added. Two of the three files already carried a prose warning
// about the file before them -- the trap was known twice and answered twice
// with a comment, and a comment does not stop a `\i` in a SQL editor.
OLD_FILES.forEach(function (pair) {
  check(pair[0] + ' defines no function at all any more',
    (pair[1].match(/create or replace function/g) || []).length, 0);
  check(pair[0] + ' points at the one file that does',
    /sql\/sairnlaw_trusttx_functions\.sql/.test(pair[1]), true);
});
check('exactly one file defines the three trusttx functions',
  (SQL.match(/create or replace function/g) || []).length, 3);
// Step 2 still owns the table DDL -- gutting it must not have taken that with
// it, or re-running it for a column would silently do nothing.
check('step 2 kept its DDL, so it is still the place to re-run the columns',
  /alter table public\.law_trusttx add column if not exists amount numeric;/.test(OLD_FILES[0][1]) &&
  /create index if not exists idx_lawtrusttx_client_status/.test(OLD_FILES[0][1]), true);
// The incident analysis is the reason the consolidated file's refusals are
// worded as they are; deleting it would leave them looking like taste.
// Matched on phrases that do NOT wrap. "CROSS-CLIENT TRUST-ACCOUNT LEAK"
// breaks across two `--` lines in that file's header, so the contiguous string
// is not there -- the wrapped-quote variant of scrubber item 16 shape A, which
// has now caught this same test file three times.
check('the incident record survives in the file that found it',
  /A PHANTOM DISBURSEMENT THAT REPORTS SUCCESS/.test(OLD_FILES[2][1]) &&
  /THE LOCK AND THE UNIQUENESS KEY DISAGREED/.test(OLD_FILES[2][1]), true);
check('and the consolidated file says a fourth file would rebuild the trap',
  /IF YOU ADD A FOURTH FILE THAT REDEFINES ANY FUNCTION BELOW/.test(SQL) &&
  /REBUILT THE TRAP/.test(SQL), true);
// The void guard's lookups are NOT client-scoped, and that is correct -- it
// learns client_id from the stored row and takes no caller-asserted client.
// Said out loud so a future reader does not "fix" them by analogy.
check('the consolidated file explains why the void guard is not client-scoped',
  /accepts no caller-asserted client at all/.test(SQL), true);

// ── (a) STRUCTURAL: the API no longer lies on a missing row ────────────
// ASSERTED ON THE CODE, NOT THE FILE. The first version required
// `data: row ? row.data : payload` to be absent from api/sd-data.js and failed
// -- because the fix's own comment QUOTES the old line to say what it replaced.
// Same shape as the SQL ordering assertion above. Comments stripped.
const API_CODE = stripLines(API, /^\s*\/\//);
check('the API refuses a missing row instead of echoing the caller payload',
  /if \(!row \|\| !row\.data\) \{/.test(API_CODE) &&
  !/data: row \? row\.data : payload/.test(API_CODE), true);
// COUNTED. There are TWO "NOT posted" refusals -- the RPC-error mapping and
// the missing-row guard -- and .test() passed while the negative control had
// replaced one of them with "Saved." A lawyer reading "Saved" on a
// disbursement that was never written is the whole failure.
check('the refusal says nothing was written, on BOTH paths, so a lawyer does not retry blind',
  (API_CODE.match(/The disbursement was NOT posted/g) || []).length, 2);
check('a collision is a 409 the caller can act on, not a 502 store error',
  /if \(\/TRUSTTX_ID_COLLISION\/\.test\(msg\)\) \{[\s\S]{0,200}res\.status\(409\)/.test(API), true);
check('and the user-facing message does not name the other client either',
  /already used by a different client on this licence/.test(API) &&
  !/client [A-Z0-9-]+ holds/.test(API), true);
check('DISBURSEMENT_NOT_WRITTEN is mapped rather than falling through to a generic error',
  /if \(\/DISBURSEMENT_NOT_WRITTEN\/\.test\(msg\)\) \{/.test(API), true);
// The balance refusal that already existed must survive untouched.
check('the pre-existing INSUFFICIENT_TRUST_BALANCE mapping is intact',
  /INSUFFICIENT_TRUST_BALANCE: disbursement \(-\?\[\\d\.\]\+\) exceeds balance/.test(API) ||
  /INSUFFICIENT_TRUST_BALANCE/.test(API), true);

// ── the id generator, which is why this is reachable ──────────────────
check('newId is a timestamp plus 1000 random suffixes, not a UUID',
  /function newId\(prefix\)\{return prefix\+'-'\+Date\.now\(\)\+'-'\+Math\.floor\(Math\.random\(\)\*1000\);\}/.test(HTML), true);

// ── (b) THE DECISION-TABLE MODEL ──────────────────────────────────────
// A REIMPLEMENTATION of the SQL's control flow, not a driver of it. It
// documents the contract; the assertions above are what hold the SQL to it.
function model(rows, req) {
  const sameIdSameClient = rows.find((r) =>
    r.license_hash === req.license_hash && r.trusttx_id === req.trusttx_id && r.client_id === req.client_id);
  if (sameIdSameClient) return { ok: true, row: sameIdSameClient, why: 'retry' };
  const sameIdOtherClient = rows.find((r) =>
    r.license_hash === req.license_hash && r.trusttx_id === req.trusttx_id);
  if (sameIdOtherClient) return { ok: false, code: 'TRUSTTX_ID_COLLISION' };
  const balance = rows
    .filter((r) => r.license_hash === req.license_hash && r.client_id === req.client_id && r.status === 'Posted')
    .reduce((s, r) => s + (r.type === 'Deposit' ? r.amount : -r.amount), 0);
  if (!(req.amount > 0)) return { ok: false, code: 'INVALID_AMOUNT' };
  if (req.amount > balance) return { ok: false, code: 'INSUFFICIENT_TRUST_BALANCE' };
  const row = { license_hash: req.license_hash, trusttx_id: req.trusttx_id, client_id: req.client_id,
    amount: req.amount, type: 'Disbursement', status: 'Posted' };
  return { ok: true, row: row, why: 'inserted' };
}

const L = 'LIC1';
const LEDGER = [
  { license_hash: L, trusttx_id: 'TX-1', client_id: 'A', amount: 500, type: 'Deposit', status: 'Posted' },
  { license_hash: L, trusttx_id: 'TX-2', client_id: 'B', amount: 300, type: 'Deposit', status: 'Posted' },
  { license_hash: L, trusttx_id: 'TX-9', client_id: 'A', amount: 100, type: 'Disbursement', status: 'Posted' }
];

check('MODEL: a disbursement for a different client with a colliding id is REFUSED, not given the other row',
  model(LEDGER, { license_hash: L, trusttx_id: 'TX-9', client_id: 'B', amount: 50 }),
  { ok: false, code: 'TRUSTTX_ID_COLLISION' });
check('MODEL: the same id for the SAME client is still an idempotent retry',
  model(LEDGER, { license_hash: L, trusttx_id: 'TX-9', client_id: 'A', amount: 100 }).why, 'retry');
check('MODEL: a retry returns the STORED row, not the request',
  model(LEDGER, { license_hash: L, trusttx_id: 'TX-9', client_id: 'A', amount: 999 }).row.amount, 100);
check('MODEL: a fresh id still posts normally',
  model(LEDGER, { license_hash: L, trusttx_id: 'TX-NEW', client_id: 'B', amount: 250 }).why, 'inserted');
check('MODEL: the balance guard still bites, and on the RIGHT client',
  model(LEDGER, { license_hash: L, trusttx_id: 'TX-NEW', client_id: 'B', amount: 400 }).code,
  'INSUFFICIENT_TRUST_BALANCE');
// The pre-fix behaviour, written down so the regression is legible: without a
// client predicate this same request returned client A's 100 disbursement.
check('MODEL: pre-fix, the same call would have returned A\'s row -- that is the leak',
  (function () {
    const preFix = LEDGER.find((r) => r.trusttx_id === 'TX-9');
    return { client: preFix.client_id, amount: preFix.amount };
  })(), { client: 'A', amount: 100 });
// A different LICENCE is a different firm. The id is not seen at all, so the
// collision branch never fires -- what stops it is the balance guard, on a
// client with no deposits, which is the correct refusal for the right reason.
check('MODEL: an id colliding across LICENCES is not a collision -- the key is licence-scoped by design',
  model(LEDGER, { license_hash: 'LIC2', trusttx_id: 'TX-9', client_id: 'B', amount: 50 }).code,
  'INSUFFICIENT_TRUST_BALANCE');
check('MODEL: and with a funded client on that other licence, it simply posts',
  model(LEDGER.concat([{ license_hash: 'LIC2', trusttx_id: 'D1', client_id: 'B', amount: 900, type: 'Deposit', status: 'Posted' }]),
        { license_hash: 'LIC2', trusttx_id: 'TX-9', client_id: 'B', amount: 50 }).why, 'inserted');

console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
if (fail) process.exit(1);
