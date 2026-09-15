// tests/sairncash_entitlement_gate.js
//
// Run:  node tests/sairncash_entitlement_gate.js
//
// SAIRNCASH'S ENTITLEMENT GATE, DRIVEN VERBATIM FROM sairncash.html.
//
// ── WHY THIS FILE EXISTS ──────────────────────────────────────────────────
// `reverifySubscription()` carries this comment, in the source, today:
//
//     Re-verifies against the real subscription state once per app load --
//     closes the "forged localStorage grants permanent free access" gap a
//     pure isSubscribed() check (client-only, no server round-trip) can't
//     close on its own.
//
// That is a security claim about the only thing standing between a text
// editor and a paid product, and NOTHING DROVE IT. Found 2026-09-15 while
// writing tests/sairncash_fault_probe.py: three files mention sairncash.html
// and none of them executes this function. Gate 4 asks whether the existing
// guards DENY; here there was no suite to ask.
//
// ── THE FUNCTIONS ARE EXTRACTED FROM THE PAGE, NOT REIMPLEMENTED ──────────
// Sliced on comment banners rather than line numbers, the same way
// tests/sairnbuild_server_backup.js does it. A reimplementation would test a
// copy that agrees with the original exactly until the day it does not.
//
// ── WHAT IS DELIBERATELY NOT TESTED HERE ──────────────────────────────────
// initApp()'s DOM half. The gate expression is
// `justPaid || await reverifySubscription() || hasTrial`, so whether the app
// opens is decided entirely by these three predicates; asserting which element
// got a class would test the rendering and not the decision. Said rather than
// left as an absence.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'sairncash.html'), 'utf8');

let pass = 0, fail = 0;
async function test(name, fn) {
  try { await fn(); pass++; console.log('  ok   - ' + name); }
  catch (e) { fail++; console.log('  FAIL - ' + name + '\n         ' + e.message); }
}
function section(t) { console.log('\n--- ' + t + ' ---'); }

function slice(startMark, endMark) {
  const a = html.indexOf(startMark);
  assert.ok(a > 0, 'not found in sairncash.html: ' + startMark);
  const b = html.indexOf(endMark, a);
  assert.ok(b > a, 'end marker not found after ' + startMark);
  return html.slice(a, b);
}

// Subscription block: getSub/saveSub/isSubscribed/reverifySubscription.
const SUB_SRC = slice('// ── SUBSCRIPTION', '// MANAGE BILLING IS A REAL ACTION NOW');
// Trial block: getTrial/saveTrial/isTrialActive/reverifyTrial.
const TRIAL_SRC = slice('// ── TRIAL (30-day', 'async function startTrial()');

// ── THE EXTRACTION IS ASSERTED BEFORE ANYTHING IS DRIVEN ──────────────────
// A slice that silently stopped matching would define nothing, every `await
// ctx.reverifySubscription()` would throw into the harness, and the arms would
// report as failures about the APP rather than about this file. Worse, an arm
// written as "must be refused" would pass for the wrong reason. Named
// explicitly so a rename in the page is a loud failure here.
const REQUIRED = ['getSub', 'saveSub', 'isSubscribed', 'reverifySubscription',
                  'getTrial', 'saveTrial', 'isTrialActive', 'reverifyTrial'];

function harness(opts) {
  opts = opts || {};
  const store = Object.assign({}, opts.local || {});
  const calls = [];
  const ctx = {
    console, JSON, Date, String, Number, Object,
    localStorage: {
      getItem: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; }
    },
    // The fetch double records every call, which is what lets an arm assert
    // that NO server round-trip happened -- the property that distinguishes
    // "verified" from "believed".
    fetch: (url, init) => {
      calls.push({ url: String(url), body: init && init.body ? JSON.parse(init.body) : null });
      if (opts.network === 'down') return Promise.reject(new Error('network down'));
      const reply = (opts.reply || {});
      return Promise.resolve({ json: () => Promise.resolve(reply) });
    },
    __store: store,
    __calls: calls
  };
  vm.createContext(ctx);
  vm.runInContext(SUB_SRC + '\n' + TRIAL_SRC, ctx);
  for (const fn of REQUIRED) {
    assert.strictEqual(typeof ctx[fn], 'function',
      'extraction failed: ' + fn + ' is not defined -- the slice anchors in '
      + 'sairncash.html have moved, and every arm below would be testing nothing');
  }
  return ctx;
}

const FUTURE = new Date(Date.now() + 30 * 86400000).toISOString();
const PAST = new Date(Date.now() - 86400000).toISOString();

(async () => {
  console.log('sairncash entitlement gate -- a forged localStorage record must not open the app');

  // ── 0. THE EXTRACTION ───────────────────────────────────────────────────
  section('the page really was read');

  await test('every entitlement function was extracted from sairncash.html', async () => {
    const c = harness();
    REQUIRED.forEach((f) => assert.strictEqual(typeof c[f], 'function', f));
  });

  await test('the fetch double is wired, so "no round-trip" is observable', async () => {
    const c = harness({ local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE, subscriptionId: 'sub_1' }) }, reply: { valid: true, expiresAt: FUTURE } });
    await c.reverifySubscription();
    assert.strictEqual(c.__calls.length, 1,
      'a record WITH a subscriptionId did not reach the server, so an arm '
      + 'asserting zero calls below would pass for the wrong reason');
    assert.match(c.__calls[0].url, /\/api\/sairncash\/verify/);
  });

  // ── 1. THE CLAIM IN THE SOURCE ──────────────────────────────────────────
  section('a forged record must not grant access');

  await test('FORGED: valid + far-future expiry and NO subscriptionId is REFUSED', async () => {
    // This is the whole attack, and it needs no tooling: open devtools, write
    // one line, reload. The record asserts entitlement and carries nothing the
    // server could be asked about.
    const c = harness({ local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE }) } });
    const ok = await c.reverifySubscription();
    assert.strictEqual(ok, false,
      'a hand-written localStorage record with no server identity opened the '
      + 'app -- this is the gap the function\'s own comment says it closes');
  });

  await test('FORGED: ...and it never even asked the server', async () => {
    const c = harness({ local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE }) } });
    await c.reverifySubscription();
    assert.strictEqual(c.__calls.length, 0,
      'unexpected: a record with no subscriptionId produced a round-trip');
  });

  await test('FORGED: the refused record is REMOVED, not just refused', async () => {
    // Added 2026-09-15 by tests/sairncash_entitlement_fault_probe.py, which
    // deleted the removeItem and left this whole file green.
    //
    // The verdict is the same either way -- this branch returns false on every
    // load, because the offline fallback is only reachable after a fetch and a
    // fetch needs a subscriptionId. What the removal stops is the app holding
    // TWO CONTRADICTORY ANSWERS: getSub() is read by initFirebase() and
    // showAccount() as well as by the gate, so a record the paywall has
    // rejected would keep being handed to an account panel that renders it.
    const c = harness({ local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE }) } });
    await c.reverifySubscription();
    assert.strictEqual(c.__store.sairncash_sub, undefined,
      'the rejected record survived, so getSub() still reports a subscription '
      + 'the gate has already refused');
  });

  await test('FORGED: a made-up subscriptionId the server rejects is REFUSED', async () => {
    const c = harness({
      local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE, subscriptionId: 'sub_made_up' }) },
      reply: { valid: false }
    });
    assert.strictEqual(await c.reverifySubscription(), false);
    assert.strictEqual(c.__store.sairncash_sub, undefined,
      'a server rejection must REMOVE the local record, not leave it to be '
      + 'believed by the next offline load');
  });

  await test('the sibling function gets this right, which is the evidence it is a defect', async () => {
    // reverifyTrial() is the same shape three hundred lines away and refuses
    // outright when the record carries no server-checkable token. The two
    // disagreeing is what makes this a defect rather than a design choice.
    const c = harness({ local: { sairncash_trial: JSON.stringify({ expiresAt: FUTURE }) } });
    assert.strictEqual(await c.reverifyTrial(), false,
      'reverifyTrial no longer refuses a token-less record either');
    assert.strictEqual(c.__calls.length, 0);
  });

  // ── 2. WHAT MUST KEEP WORKING ───────────────────────────────────────────
  // A fix that refused everybody would pass every arm above. These are the
  // paying customers.
  section('a real subscriber still gets in');

  await test('a server-confirmed subscription opens the app and is re-saved', async () => {
    const c = harness({
      local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: PAST, subscriptionId: 'sub_1' }) },
      reply: { valid: true, expiresAt: FUTURE, subscriptionId: 'sub_1' }
    });
    assert.strictEqual(await c.reverifySubscription(), true);
    assert.strictEqual(JSON.parse(c.__store.sairncash_sub).expiresAt, FUTURE,
      'the fresh server answer was not written back');
  });

  await test('a NETWORK failure falls back to the last known real expiry -- documented', async () => {
    // Deliberate, and stated in the source: "Falls back to the last known real
    // expiresAt only on a network failure, never on an actual server
    // rejection." A paying customer on a bad connection must not be locked out.
    const c = harness({
      local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE, subscriptionId: 'sub_1' }) },
      network: 'down'
    });
    assert.strictEqual(await c.reverifySubscription(), true);
    assert.ok(c.__store.sairncash_sub, 'a network blip deleted a real subscription');
  });

  await test('...but a network failure does NOT resurrect an expired one', async () => {
    const c = harness({
      local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: PAST, subscriptionId: 'sub_1' }) },
      network: 'down'
    });
    assert.strictEqual(await c.reverifySubscription(), false);
  });

  await test('a real trial with a token the server confirms still opens the app', async () => {
    const c = harness({
      local: { sairncash_trial: JSON.stringify({ trialToken: 'tok_1', expiresAt: PAST }) },
      reply: { valid: true, expiresAt: FUTURE, daysLeft: 30 }
    });
    assert.strictEqual(await c.reverifyTrial(), true);
    assert.strictEqual(JSON.parse(c.__store.sairncash_trial).expiresAt, FUTURE);
  });

  await test('no record at all is simply not entitled', async () => {
    const c = harness();
    assert.strictEqual(await c.reverifySubscription(), false);
    assert.strictEqual(await c.reverifyTrial(), false);
    assert.strictEqual(c.__calls.length, 0);
  });

  // ── 3. THE CLIENT-ONLY PREDICATE IS STILL HONEST ABOUT ITSELF ───────────
  section('isSubscribed() is a display check, and that is all it is');

  await test('isSubscribed() believes a forged record -- which is WHY it is not the gate', async () => {
    // Not a defect. isSubscribed() is a pure local predicate and cannot be
    // anything else; the whole point of reverifySubscription() is that the
    // GATE must not be this function. Asserted so that a future change making
    // the gate client-only again fails here with the reason attached.
    const c = harness({ local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE }) } });
    assert.strictEqual(c.isSubscribed(), true,
      'if this is ever false, the arms above are passing for a different '
      + 'reason than the one they name');
  });

  // ── 4. HOW FAR THE BYPASS REACHED, PINNED RATHER THAN ASSERTED IN PROSE ─
  section('the blast radius: a forged record buys the shell, never the spend');

  await test('a forged record sends NO credential to the AI endpoint', async () => {
    // "How bad is it" is the first question anyone asks, and the answer here
    // is bounded and worth keeping bounded. scAiFetch() attaches a
    // subscriptionId or a trialToken ONLY when the stored record actually has
    // one, and api/sairncash/ai.js:143 answers 401 NO_SUBSCRIPTION when
    // neither arrives -- verified by reading that branch, not inferred from
    // the comment claiming it.
    //
    // So the bypass opened the paid UI and could never have bought a single
    // model call. If this arm ever goes red, the bypass has become a SPEND
    // exposure and is a different severity of finding.
    const c = harness({ local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE }) } });
    await c.scAiFetch({ prompt: 'x' });
    const ai = c.__calls.filter((x) => /\/api\/sairncash\/ai/.test(x.url));
    assert.strictEqual(ai.length, 1, 'scAiFetch did not reach the AI endpoint at all');
    assert.strictEqual(ai[0].body.subscriptionId, undefined,
      'a forged record produced a subscriptionId to send');
    assert.strictEqual(ai[0].body.trialToken, undefined,
      'a forged record produced a trialToken to send');
  });

  await test('...and a REAL subscriber still sends theirs', async () => {
    // Without this, the arm above would pass against an scAiFetch that never
    // attaches a credential to anybody -- which would break every paying
    // customer while looking like a security improvement.
    const c = harness({ local: { sairncash_sub: JSON.stringify({ valid: true, expiresAt: FUTURE, subscriptionId: 'sub_real' }) } });
    await c.scAiFetch({ prompt: 'x' });
    const ai = c.__calls.filter((x) => /\/api\/sairncash\/ai/.test(x.url));
    assert.strictEqual(ai[0].body.subscriptionId, 'sub_real');
  });

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail === 0 ? 0 : 1);
})();
