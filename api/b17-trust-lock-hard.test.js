// api/b17-trust-lock-hard.test.js
//
// Run:  node api/b17-trust-lock-hard.test.js
//
// ROUTED BY fourth, b26, FINDING H1: "THE TRUST HARD-LOCK IS UNTESTED. 2x2
// ABLATION, not an argument." Their table, reproduced exactly:
//
//   | arm      | lock    | table              | result                      |
//   | BASELINE | intact  | denies             | exit 0, 3a ok               |
//   | ARM B    | intact  | paralegal: 'r'     | exit 0, 3a ok  <- lock saves it |
//   | ARM C    | emptied | paralegal: 'r'     | exit 1, 3a FAIL             |
//   | ARM A    | emptied | denies (shipped)   | exit 0, 3a ok  <- THE DEFECT |
//
// "DELETE `LAW_TRUST_LOCKED` ENTIRELY AND THE WHOLE SUITE STAYS GREEN. The one
// defence built for the case where the table is wrong has no arm. And
// `law_bankstatements` has no arm at all in that suite -- the other member of
// the same lock, rated A on integrity at docs/CRITICALITY-TIERS.md:425."
//
// fourth's exact next step: "LAW_TRUST_LOCKED is already exported, so it is
// two assertions plus one behavioural arm for paralegal -> law_bankstatements
// -> 403. Then re-run the 2x2: ARM A must go RED, or the arm still is not
// testing the lock."
//
// ── WHY ARM A WAS GREEN, WHICH IS THE PART WORTH UNDERSTANDING ───────────
// `decide()` applied the TABLE first and re-asserted the lock only after the
// table had already agreed. On the shipped table the paralegal row for both
// locked resources is `''`, so the table denied and the lock line was never
// reached. The lock was a SECOND defence for the case where the table is
// wrong -- and a second defence is exactly the thing no behavioural arm can
// see while the first one is working. That was a flaw in how it was TESTED.
//
// ── AND IN b18 THE ORDER CHANGED, SO THIS PARAGRAPH IS CORRECTED, NOT ─────
// ── ANNOTATED. THE SENTENCE IT USED TO END WITH WAS "that is not a flaw ───
// ── in decide(); the order is deliberate and correct", AND IT IS NO ───────
// ── LONGER THE SHIPPED ORDER. ────────────────────────────────────────────
// `decide()` now consults LAW_TRUST_LOCKED FIRST and does not read the table
// at all for a locked resource held by a non-bar-admitted role. The reason is
// not this finding: it is C2. Michael's answer to practitioner question C2 is
// that a paralegal MAY PREPARE a trust disbursement for an attorney to
// authorise, and with the lock LAST the only place to express that exception
// was a wider TABLE grant -- widening the thing the lock exists to survive.
// The lock now owns trust policy including its one exception.
//
// EVERY ARM BELOW STILL READS THE SAME WAY and the 2x2 still lands on the
// same four cells; that was checked by running it, not assumed. What is NEW
// is T4b, which asserts the exception is named in the refusal and is as
// narrow as it claims.
//
// ── SO THE ARMS HERE ARE OF TWO KINDS AND BOTH ARE NEEDED ────────────────
//   T1-T4  assert the lock STRUCTURALLY -- its exact membership, that it is
//          frozen, and that the refusal MESSAGE is driven by it. These are
//          what go red when it is emptied, which is what ARM A needs.
//   T5-T7  assert it BEHAVIOURALLY through the real handler, including the
//          law_bankstatements arm that did not exist anywhere.
//   T8     runs fourth's 2x2 as four real ablations and asserts all four
//          cells, including that ARM A now goes RED **in this file**. A
//          finding that is fixed by an assertion nobody re-measures is a
//          finding that comes back.
//
// Spawning itself for T8 would recurse, so T8 runs the arms-only form via
// B17_TRUST_LOCK_ARMS_ONLY=1 in a child process. The ablation always restores
// the file and HARD-EXITS if it cannot.
//
// Exit: 0 all arms passed · 1 an arm FAILED · 3 an arm is UNPROVEN

'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { signSessionToken } = require('./_lib/auth');

const ROLES_SRC = path.join(__dirname, '_lib', 'law-roles.js');
const SELF = __filename;
const ARMS_ONLY = process.env.B17_TRUST_LOCK_ARMS_ONLY === '1';
const LIC_HASH = 'law-b17-lock-hash';

let pass = 0, fail = 0, unproven = 0;
const failed = [], notProved = [];
function ok(l) { pass++; console.log('  ok       ' + l); }
function bad(l, why) {
  fail++; failed.push(l.split('.')[0]);
  console.log('  FAIL     ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function cannot(l, why) {
  unproven++; notProved.push(l.split('.')[0]);
  console.log('  UNPROVEN ' + l);
  if (why) console.log('           ' + String(why).slice(0, 600));
}
function is(c, l, why) { if (c) ok(l); else bad(l, why); }

function freshRoles() {
  delete require.cache[require.resolve('./_lib/law-roles')];
  return require('./_lib/law-roles');
}

// ── THE HANDLER HARNESS, the same shape as
//    api/sd-data-law-trusttx-session.test.js, because an arm driven through a
//    different harness than the suite it is closing a gap in would not be
//    comparable to it.
function mockRes() {
  const res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(body, token) {
  const headers = { authorization: 'Bearer GOOD-KEY' };
  if (token) headers['x-sd-auth'] = token;
  return { method: 'POST', headers: headers, body: body };
}
function tokenFor(role) {
  return signSessionToken({ app: 'sairnlaw', employee_id: 'emp-' + role,
    role: role, license_hash: LIC_HASH });
}
function loadHandler() {
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: LIC_HASH,
                 trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  global.fetch = async function (url) {
    const u = String(url);
    if (u.indexOf('sairnlaw_employee_auth') !== -1) {
      return { ok: true, status: 200, json: async () => [{ active: true }] };
    }
    if (u.indexOf('law_bankstatements') !== -1 || u.indexOf('law_optx') !== -1) {
      return { ok: true, status: 200, json: async () => [{ data: { id: 'X1' } }] };
    }
    return { ok: true, status: 200, json: async () => [] };
  };
  delete require.cache[require.resolve('./_lib/law-roles')];
  delete require.cache[require.resolve('./sd-data.js')];
  return require('./sd-data.js');
}

function ablate(pairs, fn) {
  const backup = fs.readFileSync(ROLES_SRC, 'utf8');
  let src = backup;
  for (let i = 0; i < pairs.length; i += 1) {
    const n = src.split(pairs[i][0]).length - 1;
    if (n !== 1) return { ok: false, why: 'anchor ' + i + ' occurs ' + n + ' times, not 1' };
    src = src.split(pairs[i][0]).join(pairs[i][1]);
  }
  try {
    fs.writeFileSync(ROLES_SRC, src);
    if (fs.readFileSync(ROLES_SRC, 'utf8') !== src) {
      return { ok: false, why: 'the mutant did not land on disk' };
    }
    return { ok: true, result: fn() };
  } finally {
    fs.writeFileSync(ROLES_SRC, backup);
    if (fs.readFileSync(ROLES_SRC, 'utf8') !== backup) {
      console.log('  HARD ERROR the ablation did not restore api/_lib/law-roles.js '
        + '-- DO NOT COMMIT, the file on disk is a mutant');
      process.exit(1);
    }
  }
}

// THE TWO MUTATIONS, as (anchor, replacement) pairs.
const EMPTY_LOCK = [[
  'const LAW_TRUST_LOCKED = Object.freeze(Object.assign(Object.create(null), {\n'
    + '  law_trusttx: true,\n  law_bankstatements: true\n}));',
  'const LAW_TRUST_LOCKED = Object.freeze(Object.assign(Object.create(null), {\n'
    + '}));'
]];
const PERMISSIVE_TABLE = [[
  "law_trusttx:          { owner: 'rw', attorney: 'rw', paralegal: '',",
  "law_trusttx:          { owner: 'rw', attorney: 'rw', paralegal: 'r',"
]];

function runSelf(env) {
  // Exit code only. The child prints its own arm lines and they are not
  // re-printed here -- what T8 asserts is the CELL, which is an exit code.
  try {
    execFileSync(process.execPath, [SELF],
      { env: Object.assign({}, process.env, env), stdio: 'pipe' });
    return 0;
  } catch (e) {
    return typeof e.status === 'number' ? e.status : -1;
  }
}
function runSuite(file) {
  try {
    execFileSync(process.execPath, [path.join(__dirname, file)],
      { env: process.env, stdio: 'pipe' });
    return 0;
  } catch (e) {
    return typeof e.status === 'number' ? e.status : -1;
  }
}

async function arms() {
  const lawRoles = freshRoles();

  // ── T1: THE LOCK'S MEMBERSHIP, EXACTLY. This is the arm ARM A fails. ───
  // Asserted as a SET and not with two `=== true` checks, so emptying it,
  // dropping one member, or quietly ADDING a third all go red. A third member
  // is not hypothetically bad: the lock decides a refusal message too (T4),
  // so a resource added here starts telling users it is trust money.
  try {
    const keys = Object.keys(lawRoles.LAW_TRUST_LOCKED).sort();
    is(keys.length === 2 && keys[0] === 'law_bankstatements'
       && keys[1] === 'law_trusttx',
       'T1. LAW_TRUST_LOCKED holds EXACTLY law_bankstatements and law_trusttx',
       JSON.stringify(keys));
  } catch (e) { bad('T1. LAW_TRUST_LOCKED membership', e && e.stack); }

  // ── T2: AND IT IS FROZEN, which is half of what "hard" means ───────────
  // A policy a caller can mutate at runtime is a default, not a lock, and the
  // file's own note says the override mechanism may not reach this.
  try {
    const before = Object.keys(lawRoles.LAW_TRUST_LOCKED).length;
    try { lawRoles.LAW_TRUST_LOCKED.law_optx = true; } catch (e) { /* strict-mode throw is fine */ }
    const after = Object.keys(lawRoles.LAW_TRUST_LOCKED).length;
    is(Object.isFrozen(lawRoles.LAW_TRUST_LOCKED) && before === after
       && !lawRoles.LAW_TRUST_LOCKED.law_optx,
       'T2. the lock is FROZEN -- a caller cannot add a resource to it at runtime',
       'frozen=' + Object.isFrozen(lawRoles.LAW_TRUST_LOCKED)
       + ' before=' + before + ' after=' + after);
  } catch (e) { bad('T2. the lock is frozen', e && e.stack); }

  // ── T3: THE LOCK SURVIVES A PERMISSIVE TABLE -- the case it exists for ─
  // THIS IS fourth's ARM B MADE PERMANENT. It is the only arm that can see
  // the lock doing work, because on the shipped table it is unreachable. The
  // mutation puts paralegal: 'r' on law_trusttx -- the exact override the
  // spec says must not be possible -- and the lock must still DENY.
  try {
    const r = ablate(PERMISSIVE_TABLE, () => {
      const m = freshRoles();
      return {
        trusttx: m.decide('law_trusttx', 'paralegal', 'read'),
        deny: m.DENY,
        tableSays: m.LAW_ROLE_MATRIX.law_trusttx.paralegal
      };
    });
    if (!r.ok) {
      cannot('T3. the lock survives a permissive table (ARM B, permanent)', r.why);
    } else {
      is(r.result.tableSays === 'r' && r.result.trusttx === r.result.deny,
         'T3. ARM B -- with the TABLE opened to paralegal: \'r\' the LOCK still '
       + 'DENIES, which is the only condition under which it is reachable',
         JSON.stringify(r.result));
    }
  } catch (e) { bad('T3. ARM B -- the lock survives a permissive table', e && e.stack); }

  // ── T4: THE REFUSAL MESSAGE IS DRIVEN BY THE LOCK, not by the table ────
  // denyMessage() branches on LAW_TRUST_LOCKED, so emptying it silently
  // downgrades "Client trust records are available to the firm owner and
  // attorneys only" to the generic role sentence -- a user-visible change
  // that no status code would show.
  // b18: the anchor is `client trust` and no longer `trust records`. The
  // law_trusttx sentence now names the PREPARE route (C2) and does not contain
  // the words "trust records" at all, so the old anchor would have failed on
  // correct code -- an anchor that stops matching is item 8 of
  // docs/2026-09-13-cross-domain-disciplines.md and is why this is re-aimed
  // rather than deleted. `client trust` is in BOTH sentences by construction.
  try {
    const t = lawRoles.denyMessage('law_trusttx', 'paralegal');
    const bs = lawRoles.denyMessage('law_bankstatements', 'paralegal');
    const other = lawRoles.denyMessage('law_portalmessages', 'paralegal');
    is(/client trust/i.test(t) && /client trust/i.test(bs)
       && !/client trust/i.test(other),
       'T4. denyMessage names CLIENT TRUST for both locked resources and does '
     + 'NOT for an unlocked one, so the message is the lock speaking',
       JSON.stringify({ t: t, bs: bs, other: other }));
  } catch (e) { bad('T4. denyMessage is driven by the lock', e && e.stack); }

  // ── T4b (b18): THE C2 EXCEPTION IS NAMED, AND ONLY WHERE IT EXISTS ─────
  // Four properties in one arm because they are one claim: a refusal that
  // offers a route must offer it to the role that has one, on the resource
  // that has one, and must NOT offer it anywhere else. A refusal that invites
  // a paralegal to prepare a BANK STATEMENT would be a confident wrong answer
  // in the direction of a user wasting their time on something impossible.
  try {
    const pWrite = lawRoles.denyMessage('law_trusttx', 'paralegal', 'write');
    const pBank = lawRoles.denyMessage('law_bankstatements', 'paralegal', 'write');
    const bkWrite = lawRoles.denyMessage('law_trusttx', 'bookkeeper', 'write');
    const pPrepare = lawRoles.denyMessage('law_trusttx', 'paralegal',
                                          lawRoles.LAW_PREPARE_ACTION);
    is(/PREPARE/.test(pWrite)
       && !/PREPARE/.test(pBank)
       && !/PREPARE/.test(bkWrite)
       && !/PREPARE/.test(pPrepare),
       'T4b. the C2 prepare route is offered to paralegal on law_trusttx ONLY '
     + '-- not on law_bankstatements, not to bookkeeper, and not to somebody '
     + 'already preparing',
       JSON.stringify({ pWrite: pWrite, pBank: pBank, bkWrite: bkWrite,
                        pPrepare: pPrepare }));
  } catch (e) { bad('T4b. the C2 exception is named only where it exists', e && e.stack); }

  // ── T4c (b18): AND decide() AGREES WITH THE MESSAGE ────────────────────
  // The message and the decision are two code paths and nothing made them
  // agree. T4b proves what the refusal SAYS; this proves it is TRUE -- the
  // prepare the message invites actually succeeds, and the three cases it
  // does not offer actually fail. Both directions, because a message that
  // promises an allow nobody grants is worse than no message.
  try {
    const d = {
      pPrepareTrusttx: lawRoles.decide('law_trusttx', 'paralegal', lawRoles.LAW_PREPARE_ACTION),
      pWriteTrusttx: lawRoles.decide('law_trusttx', 'paralegal', 'write'),
      pPrepareBank: lawRoles.decide('law_bankstatements', 'paralegal', lawRoles.LAW_PREPARE_ACTION),
      bkPrepareTrusttx: lawRoles.decide('law_trusttx', 'bookkeeper', lawRoles.LAW_PREPARE_ACTION),
      pPrepareOther: lawRoles.decide('law_portalmessages', 'paralegal', lawRoles.LAW_PREPARE_ACTION)
    };
    is(d.pPrepareTrusttx === lawRoles.ALLOW
       && d.pWriteTrusttx === lawRoles.DENY
       && d.pPrepareBank === lawRoles.DENY
       && d.bkPrepareTrusttx === lawRoles.DENY
       && d.pPrepareOther === lawRoles.DENY,
       'T4c. decide() grants exactly the prepare the message offers and refuses '
     + 'the other four, including `prepare` used as a general verb on an '
     + 'unlocked resource',
       JSON.stringify(d));
  } catch (e) { bad('T4c. decide() agrees with the message', e && e.stack); }

  // ── T5: decide() DENIES paralegal ON law_bankstatements ────────────────
  // The member of the lock that had no arm anywhere.
  try {
    const m = freshRoles();
    is(m.decide('law_bankstatements', 'paralegal', 'read') === m.DENY
       && m.decide('law_bankstatements', 'paralegal', 'write') === m.DENY
       && m.decide('law_bankstatements', 'owner', 'read') !== m.DENY
       && m.decide('law_bankstatements', 'attorney', 'read') !== m.DENY,
       'T5. law_bankstatements: paralegal DENIED both verbs, owner and attorney not',
       JSON.stringify({
         pr: m.decide('law_bankstatements', 'paralegal', 'read'),
         pw: m.decide('law_bankstatements', 'paralegal', 'write'),
         o: m.decide('law_bankstatements', 'owner', 'read'),
         a: m.decide('law_bankstatements', 'attorney', 'read') }));
  } catch (e) { bad('T5. law_bankstatements decide()', e && e.stack); }

  // ── T6: AND THE ENDPOINT AGREES -- 403, no data, through the real
  //    handler. This is the behavioural arm fourth named.
  try {
    process.env.SUPABASE_URL = 'https://test.supabase.co';
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';
    process.env.SD_AUTH_SECRET = ['b17', 'lock', 'fixture'].join('-');
    const handler = loadHandler();
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_bankstatements' },
      tokenFor('paralegal')), res);
    is(res.statusCode === 403 && res.body && res.body.error
       && res.body.error.code === 'FORBIDDEN'
       && !('data' in res.body)
       && /trust records/i.test(String(res.body.error.message)),
       'T6. a signed-in paralegal reading law_bankstatements gets 403, no data '
     + 'array, and the TRUST message',
       res.statusCode + ' ' + JSON.stringify(res.body));
  } catch (e) { bad('T6. the endpoint refuses paralegal on law_bankstatements', e && e.stack); }

  // ── T7: THE CONTROL FOR T6. Without it "paralegal always refused" passes.
  // Same token, same handler, a resource the same table grants paralegal 'r'
  // on. If this goes red, T6's 403 is the session gate having swallowed the
  // role rather than the trust policy refusing it.
  try {
    const handler = loadHandler();
    const res = mockRes();
    await handler(mockReq({ action: 'read', resource: 'law_optx' },
      tokenFor('paralegal')), res);
    is(res.statusCode === 200 && res.body && res.body.ok === true,
       'T7. CONTROL -- the same paralegal token CAN read law_optx',
       res.statusCode + ' ' + JSON.stringify(res.body));
  } catch (e) { bad('T7. CONTROL -- paralegal can read law_optx', e && e.stack); }
}

async function main() {
  console.log('api/b17-trust-lock-hard.test.js'
    + (ARMS_ONLY ? '  [ARMS ONLY -- spawned by T8]' : ''));
  if (!ARMS_ONLY) {
    console.log('  fourth b26 H1: the trust hard-lock gets arms, and the 2x2 is re-run');
  }

  await arms();

  if (ARMS_ONLY) {
    console.log('');
    console.log('  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
    process.exit(fail ? 1 : (unproven ? 3 : 0));
  }

  // ── T8: fourth's 2x2, RE-RUN AS AN ARM ────────────────────────────────
  // Four real mutations of api/_lib/law-roles.js, each driving BOTH this
  // file's arms (via the arms-only child) and the suite fourth measured.
  // The cell that matters is ARM A: lock emptied, table shipped. fourth
  // measured exit 0 there, which is what made the finding. It must now be
  // exit 1 HERE while staying exit 0 THERE -- staying 0 there is not a
  // regression, it is the original finding, and nothing in this batch
  // changes api/sd-data-law-trusttx-session.test.js.
  const TRUSTTX_SUITE = 'sd-data-law-trusttx-session.test.js';
  const cells = [];
  function cell(name, pairs) {
    if (pairs === null) {
      cells.push({ name: name, mine: runSelf({ B17_TRUST_LOCK_ARMS_ONLY: '1' }),
                   theirs: runSuite(TRUSTTX_SUITE) });
      return;
    }
    const r = ablate(pairs, () => ({
      mine: runSelf({ B17_TRUST_LOCK_ARMS_ONLY: '1' }),
      theirs: runSuite(TRUSTTX_SUITE)
    }));
    if (!r.ok) { cells.push({ name: name, err: r.why }); return; }
    cells.push({ name: name, mine: r.result.mine, theirs: r.result.theirs });
  }

  cell('BASELINE', null);
  cell('ARM B  lock intact,  table permissive', PERMISSIVE_TABLE);
  cell('ARM C  lock emptied, table permissive', EMPTY_LOCK.concat(PERMISSIVE_TABLE));
  cell('ARM A  lock emptied, table shipped', EMPTY_LOCK);

  cells.forEach((c) => {
    console.log('    ' + c.name + ' -> '
      + (c.err ? 'COULD NOT RUN: ' + c.err
               : 'mine=' + c.mine + ' trusttx-suite=' + c.theirs));
  });
  const by = {};
  cells.forEach((c) => { by[c.name.split(' ')[0] + (c.name.split(' ')[1] || '')] = c; });
  const base = cells[0], armB = cells[1], armC = cells[2], armA = cells[3];

  if ([base, armB, armC, armA].some((c) => c.err)) {
    cannot('T8. the 2x2 ablation',
      cells.filter((c) => c.err).map((c) => c.name + ': ' + c.err).join(' ; '));
  } else {
    is(base.mine === 0 && base.theirs === 0,
       'T8a. BASELINE -- the shipped tree is green in both suites',
       JSON.stringify(base));
    // ARM B's expected value for THIS file is 3 (COULD NOT RUN), not 0, and
    // that is the right answer rather than a weaker one. T3 ablates the table
    // itself, so under ARM B its anchor is already mutated and it reports
    // COULD NOT RUN -- PR §1.11's third state -- instead of a pass it never
    // performed. Asserting 0 here would have required T3 to fold "could not
    // run" into "passed", which is the exact defect shape this platform keeps
    // paying for. The trusttx suite is unaffected and stays 0, which is
    // fourth's own ARM B measurement.
    is(armB.mine === 3 && armB.theirs === 0,
       'T8b. ARM B -- lock intact, table permissive: the trusttx suite is GREEN '
     + '(the lock saved a permissive row, fourth\'s measurement) and this file '
     + 'reports COULD NOT RUN (exit 3) because T3\'s own anchor is the thing '
     + 'ARM B mutated -- the third state, not a pass',
       JSON.stringify(armB));
    is(armC.theirs === 1,
       'T8c. ARM C -- lock emptied AND table permissive fails the trusttx suite, '
     + 'exactly as fourth measured',
       JSON.stringify(armC));
    is(armA.mine === 1,
       'T8d. ARM A IS NOW RED HERE -- emptying LAW_TRUST_LOCKED with the shipped '
     + 'table fails THIS file, which is fourth\'s H1 closed. It stays green in '
     + 'the trusttx suite and that is the original finding, not a regression',
       JSON.stringify(armA));
    is(armA.theirs === 0,
       'T8e. and ARM A STILL passes the trusttx suite -- stated rather than '
     + 'quietly fixed, because nothing in b17 touches that file\'s arms',
       JSON.stringify(armA));
  }

  console.log('');
  console.log('  ' + pass + ' passed, ' + fail + ' failed, ' + unproven + ' unproven');
  if (failed.length) console.log('  FAILED: ' + failed.join(', '));
  if (notProved.length) console.log('  UNPROVEN: ' + notProved.join(', '));
  process.exit(fail ? 1 : (unproven ? 3 : 0));
}

main();
