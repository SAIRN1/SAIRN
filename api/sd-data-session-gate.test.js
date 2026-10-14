// api/sd-data-session-gate.test.js
// REQUIREMENT: slabs, profile and memory require an employee SESSION and not
//   the licence key alone -- the key is a bearer credential StoneDesk prints
//   into a link the shop is told to send customers, and it read the whole slab
//   inventory, the business profile and the shop's AI memories
//
// Plain node:assert tests. Run: node api/sd-data-session-gate.test.js
//
// slabs, profile and memory predate per-employee sessions and were reachable
// with the licence key alone. docs/superpowers/specs/2026-09-02-licence-key-exposure-audit.md
// proved what that meant: the key is a bearer credential, StoneDesk printed it
// into a link the shop is told to send customers, and anyone holding it could
// read the whole slab inventory, the business profile (company, EIN, revenue
// range, owner) and the shop's AI memories -- and WRITE slabs.
//
// `profile` READ was held open for exactly one commit while SAIRNcode migrated
// off it, and is now gated too. The assertion that used to protect that hole is
// inverted below rather than deleted, so the file still records that the
// exception existed and that it closed.

const assert = require('assert');

function mockRes() {
  var res = { statusCode: null, body: null };
  res.status = function (c) { res.statusCode = c; return res; };
  res.json = function (b) { res.body = b; return res; };
  return res;
}
function mockReq(action, resource, payload) {
  return {
    method: 'POST',
    headers: { authorization: 'Bearer SD-TEST-KEY', 'x-sd-auth': 'tok' },
    body: { action: action, resource: resource, payload: payload || {} }
  };
}

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name + '\n    ' + e.message); process.exitCode = 1; }
}

function loadHandler(opts) {
  opts = opts || {};
  const calls = [];
  delete require.cache[require.resolve('./_lib/license')];
  require.cache[require.resolve('./_lib/license')] = {
    exports: {
      validateLicenseKey: async function () {
        return { valid: true, active: true, license_hash: 'test-hash', trial_ends_at: null, stripe_subscription_id: null };
      }
    }
  };
  const realAuth = require('./_lib/auth');
  delete require.cache[require.resolve('./_lib/auth')];
  require.cache[require.resolve('./_lib/auth')] = {
    exports: Object.assign({}, realAuth, {
      tokenFromRequest: function () { return 'tok'; },
      verifySessionToken: function () { return opts.noSession ? null : { employee_id: 'emp-1', role: 'sales' }; }
    })
  };
  // Any network call at all on a refused request is itself a defect.
  global.fetch = async function (url, init) {
    calls.push({ url: String(url), method: (init && init.method) || 'GET' });
    if (opts.refuseNetwork) throw new Error('the gate let a refused request reach the database');
    const m = (init && init.method) || 'GET';
    if (m === 'GET') return { ok: true, status: 200, json: async () => [] };
    return { ok: true, status: 201, json: async () => [{ data: {} }] };
  };
  delete require.cache[require.resolve('./sd-data.js')];
  return { handler: require('./sd-data.js'), calls: calls };
}

// The exposure, as the audit measured it, expressed as a table.
const GATED = [
  ['slabs', 'read'],
  ['slabs', 'write'],
  ['slabs', 'reserve'],
  ['slabs', 'release'],
  ['profile', 'read'],
  ['profile', 'write'],
  ['memory', 'read'],
  ['memory', 'write']
];

async function main() {
  console.log('api/sd-data.js -- the licence key alone is no longer enough for slabs/profile/memory');
  process.env.SUPABASE_URL = 'https://test.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key';

  for (const [resource, action] of GATED) {
    await test(resource + '/' + action + ' -> 403 with a licence key and NO session', async () => {
      const { handler, calls } = loadHandler({ noSession: true, refuseNetwork: true });
      const res = mockRes();
      const payload = resource === 'slabs' ? { id: 'S1', reservedFor: 'X' } : { x: 1 };
      await handler(mockReq(action, resource, payload), res);
      assert.strictEqual(res.statusCode, 403, 'status was ' + res.statusCode);
      assert.strictEqual(res.body.error.code, 'FORBIDDEN');
      assert.match(res.body.error.message, /sign in first/i);
      assert.strictEqual(calls.length, 0, 'a refused request still hit the database');
    });
  }

  for (const [resource, action] of GATED) {
    await test(resource + '/' + action + ' still works WITH a session', async () => {
      const { handler } = loadHandler({});
      const res = mockRes();
      const payload = resource === 'slabs' ? { id: 'S1', reservedFor: 'X' } : { x: 1 };
      await handler(mockReq(action, resource, payload), res);
      assert.notStrictEqual(res.statusCode, 403,
        'the gate refuses a legitimate signed-in caller');
    });
  }

  await test('THE HOLE IS CLOSED: no resource in the table is exempt any more', async () => {
    // This assertion used to say the opposite. profile/read was open only
    // while SAIRNcode probed it for licence validity without a session;
    // SAIRNcode now calls api/sc-auth.js check_license, verified live. Kept
    // inverted rather than deleted so the file records that the exception
    // existed, and would fail loudly if anyone re-opened it.
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\};/);
    assert.ok(!/'profile':\s*\['write'\]/.test(m[0]),
      'profile/read is exempt again -- if that is deliberate, say why in the table');
  });


// Parsed once, and the two REs are NAMED so the arm using them can say which
// one failed rather than reporting an empty set as agreement.
const GATED_RE = new RegExp('const SD_SESSION_GATED = \\{[\\s\\S]*?\\n    \\};');
const GATE_APP_RE = new RegExp('const SD_GATE_APP = \\{[\\s\\S]*?\\n    \\};');
function mapNames(blob) {
  // The quote characters are built rather than written: a single quote inside
  // a single-quoted pattern string is how the first draft of this helper
  // became a numeric literal and failed to parse.
  const Q = String.fromCharCode(39);
  const rx = new RegExp('^\\s*' + Q + '([a-z0-9_]+)' + Q + '\\s*:', 'gm');
  const out = new Set();
  let mm;
  while ((mm = rx.exec(blob)) !== null) out.add(mm[1]);
  return out;
}

  await test('the gate is a table, not scattered checks -- and the pair count is COUNTED, not claimed', () => {
    // This assertion used to be titled "lists exactly seven pairs" and counted
    // nothing -- it matched three entries and stopped. Adding 'locations' on
    // 2026-09-03 took the table to nine pairs and the title stayed green while
    // becoming false, which is the whole failure mode a count is supposed to
    // catch. It is now derived from the table rather than asserted about it.
    const fs = require('fs');
    const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
    const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/);
    assert.ok(m, 'the gate table is gone');
    assert.match(m[0], /'slabs':\s*\['read', 'write', 'reserve', 'release'\]/);
    assert.match(m[0], /'profile':\s*\['read', 'write'\]/);
    assert.match(m[0], /'memory':\s*\['read', 'write'\]/);
    // Yards, 2026-09-03. The GAP 7 branch described itself as carrying "the
    // same licence-scoped gate as 'slabs'" -- and slabs is in THIS table, so
    // locations had no session requirement at all and a licence key alone
    // could rename or close a yard.
    assert.match(m[0], /'locations':\s*\['read', 'write'\]/);
    // law_trusttx, 2026-09-16. ATTORNEY IOLTA CLIENT TRUST MONEY -- the one
    // figure a bar association audits -- and it had NO session gate at all.
    // Both branches dispatched on the licence hash alone, and the licence key
    // is shipped to the browser and readable by anyone who can open the app.
    // Not a session that had gone stale: no session check existed. The adjacent
    // `law_trust_reconcile` reads THE SAME TABLE forty lines below and verifies
    // a session AND a role, which is why it survived three reads of the file.
    //
    // THIS ARM WAS RED ON origin/main FOR THE RIGHT REASON AND NOBODY FINISHED
    // IT (fixed 2026-09-16). The count said 9 and the table held 11, so the arm
    // did exactly what it exists to do -- "add the new resource to this test
    // and say why it is gated" -- and the answer was never written down. A
    // suite left red by its own correct finding is a suite whose next finding
    // is read as noise.
    assert.match(m[0], /'law_trusttx':\s*\['read', 'write'\]/);
    // PHASE 2 COMPLETED, 2026-09-22. The last three SAIRNlaw resources that
    // were the licence key alone. Measured before the change: all six pairs
    // answered 200 with no token, against a control where law_invoices/read
    // answered 401. Driven in api/sd-data-law-phase2-session.test.js, which
    // this file's coverage arm below names -- adding them here without that
    // file fails that arm, which is how this was caught rather than shipped.
    assert.match(m[0], /'law_clients':\s*\['read', 'write'\]/);
    assert.match(m[0], /'law_matters':\s*\['read', 'write'\]/);
    assert.match(m[0], /'law_deadlines':\s*\['read', 'write'\]/);
    // SAIRNfreedom's three Tier A resources, 2026-09-21. Same shape as
    // law_trusttx above and found the same way: SF_RESOURCES' read and write
    // branches carried NO session check of any kind, so the licence key --
    // shipped to the browser and readable by anyone who can open the app --
    // was the whole authorisation on the general ledger, the chart of accounts
    // and vendor pricing. SAIRNfreedom was not swept with law_trusttx on
    // 2026-09-16. Gated LAST of five pieces, deliberately: until sf-auth.js,
    // the ROLES_BY_APP/AUTH_TABLE_BY_APP entries, the schema and the client's
    // X-SD-Auth header existed, arming this line would have 403'd every real
    // call with no way to clear it.
    assert.match(m[0], /'sf_accounts':\s*\['read', 'write'\]/);
    assert.match(m[0], /'sf_ledger':\s*\['read', 'write'\]/);
    assert.match(m[0], /'sf_vendor_prices':\s*\['read', 'write'\]/);
    // THE VERB LIST WAS HARDCODED AND SILENTLY UNDERCOUNTED (fixed 2026-09-24).
    // It read /'(read|write|reserve)'/, so adding 'release' to the table made
    // the count go DOWN relative to reality -- a new gated pair that this arm
    // could not see at all. An arm whose job is "the table did not change size"
    // must not have its own list of what counts as a row; it now counts every
    // verb inside every array, whatever the verb is called.
    const pairs = (m[0].match(/'[a-z_]+'(?=[,\]])/g) || []).length;
    // 17 -> 23 on 2026-09-22: phase 2's final three, six pairs. WHY THEY ARE
    // GATED, which is what this tripwire asks for: law_clients, law_matters and
    // law_deadlines were the last three resources in SAIRNlaw authorised by the
    // licence key alone -- a key shipped to the browser and readable by anyone
    // who can open the app. Measured before the change: all six pairs answered
    // 200 with no token, against a control where law_invoices/read answered 401.
    // law_matters names the client and the matter.
    //
    // 23 -> 55 LATER ON 2026-09-22, AND NOBODY WROTE THE REASON, which is the
    // whole point of this tripwire and it did not work as intended. Three
    // batches landed that day and this arm went red and STAYED red on
    // origin/main until 2026-09-24. Reconstructed from the gate table's own
    // comments rather than left blank:
    //   sdn_contracts, sdn_discounts, sdn_invoices, sdn_pos, sdn_referrals
    //     -- SAIRNdesign's five Tier A resources, ten pairs. Contracts,
    //        discounts, invoices and POS were authorised by the licence key
    //        alone for all eighteen resources in that map.
    //   the eight SAIRNfreedom resources hover2 audited and Michael approved
    //     -- sixteen pairs: a FELONY and gambling disqualification flag on a
    //        named volunteer, MINORS' names, ORC 2915 payee records, a DOB the
    //        app age-gates off, health and military status, a VA-adjacent
    //        referral outcome.
    //   sf_members, sf_donor_awards, sf_donor_tiers -- six pairs, the three
    //        the batch above named and left.
    //
    // 55 -> 57 on 2026-09-24: sf_signatures, two pairs. The other half of the
    // pair the 2026-09-22 finding named. sairnfreedom.html:5700 writes
    // {docId, docTitle, version, hash, signer, typed, signed} -- a named
    // person, their typed signature, and the governance document it binds them
    // to. Not a fact ABOUT a person but a REUSABLE INSTRUMENT that can be
    // lifted off one document and re-applied to another.
    //
    // WHY THE NUMBER IS STILL HARDCODED after going stale twice: a derived
    // expectation would make this arm assert its own premise, and the arm's
    // job is to STOP a resource being gated with no reason written down. The
    // fault was not the hardcoded number, it was landing a change that tripped
    // it and leaving the suite red. If this line is what is blocking you, the
    // fix is two edits -- the count, and the paragraph above saying why.
    //
    // 57 -> 58 on 2026-09-24: slabs gains 'release', one pair. WHY IT IS GATED,
    // which is what this tripwire asks for: release clears a reservation, and
    // an ungated release is the double-sale in two requests -- release the
    // other salesperson's hold, then reserve, and the compare-and-swap never
    // sees a conflict because there is not one left to see. It is the same
    // authority as 'reserve' pointed the other way and it carries the same gate.
    // 58 -> 66 on 2026-09-24: the four SAIRNdesign resources promoted B->A on
    // 2026-09-23 join the gate, eight pairs. WHY THEY ARE GATED, which is what
    // this tripwire asks for: they were promoted A on the money limb hours
    // AFTER the first five were gated (a client budget that steers the AI
    // adviser and decides over/under; a priced client accept/decline whose
    // Approved path reserves one-of-a-kind inventory; the catalogue BOTH
    // proposal and PO totals derive from; hours x billable_rate summed into
    // the month's billable value), and a Tier A resource on a licence key
    // alone is the exact finding that armed the first five.
    // 66 -> 70 on 2026-09-25: SAIRNscape's two Tier A resources, four pairs.
    // WHY THEY ARE GATED, which is what this tripwire asks for: all twelve
    // SAIRNscape resources dispatched on the licence hash alone with no session
    // check of any kind -- the same shape as law_trusttx, SF_RESOURCES and
    // SDN_RESOURCES before them, and SAIRNscape was swept with none of the
    // three. `invoices` is money (the write branch already refuses a
    // non-numeric amount because a string one reached a fold and printed
    // -99450 on a tax report) and `scp_quotes` is the priced quote every
    // invoice descends from.
    //
    // AND THE NAME IS THE PART TO READ TWICE: the RESOURCE is `invoices`,
    // spelled bare, because SAIRNscape claimed it before the scp_ convention
    // existed. The storage table is scp_invoices. A gate written against the
    // table name gates nothing and every refusal arm anywhere still passes.
    assert.match(m[0], /'invoices':\s*\['read', 'write'\]/);
    assert.match(m[0], /'scp_quotes':\s*\['read', 'write'\]/);
    // 70 -> 74 on 2026-09-29: TWO SAIRNfreedom resources, four pairs, and the
    // first of them had already moved the count and nobody noticed -- this arm
    // was RED ON MAIN at 72 before either was addressed, which is what a
    // tripwire looks like when it is carried rather than read.
    //
    // WHY THEY ARE GATED, which is what this tripwire asks for:
    //   sf_trustee_audits (hank) -- the quarterly financial-controls
    //     attestation for an ORC Chapter 2915 gaming post, and the fidelity
    //     bond covering the people who handle gaming receipts. Gated on arrival.
    //   sf_vehicle_service -- Tier A on INTEGRITY since 2026-09-23 and ungated
    //     for six days. It is the ONLY thing that advances the odometer
    //     sf_vehicles computes its service-due flag from. DRIVEN before the
    //     gate: read with no session answered 200, and the control
    //     sf_trustee_audits answered 403.
    assert.match(m[0], /'sf_trustee_audits':\s*\['read', 'write'\]/);
    assert.match(m[0], /'sf_vehicle_service':\s*\['read', 'write'\]/);
    // 74 -> 75 on 2026-09-29: ONE resource, ONE pair. mech_docs WRITE, and the
    // odd number is the point -- every entry before it is ['read', 'write'] and
    // this one is ['write'] alone.
    //
    // WHY IT IS GATED, which is what this tripwire asks for: MECH_RECORDS gated
    // all four of mech_quotes, mech_checks, mech_docs and mech_takeoffs on the
    // LICENCE KEY ALONE -- a key shipped to the browser -- and mech_docs is the
    // one of the four whose own server-side redactor
    // (api/_lib/mech-redact.js) carries patterns for SSN, EIN and card-length
    // digit runs, because scanDoc() asks a model to extract every field off
    // work orders, contracts, permits and invoices and the answer is stored
    // here. That redactor REDUCES text and NEVER REFUSES A WRITE, deliberately
    // and by its own header, so it was not the gate and there was no other one.
    //
    // WHY IT IS WRITE ONLY, which this arm should make somebody justify rather
    // than wave through: the reported finding is the WRITE. The READ stays
    // licence-only, and the three sibling tables stay licence-only -- each is
    // its own open-work row, and mech_checks is explicitly a DECISION nobody
    // has been asked to make. api/sd-data-mech-session-gate.test.js drives all
    // four of those UNCHANGED surfaces as well as the gated one, so widening
    // this later is visible rather than silent.
    assert.match(m[0], /'mech_docs':\s*\['write'\]/);
    // 75 -> 78 on 2026-10-05: ONE resource, THREE pairs. SAIRNscape
    // `customers`, read and write -- and the arithmetic is worth a line of its
    // own, because `['read', 'write']` is TWO pairs by this arm's own counter
    // and the third is the SD_GATE_APP entry that landed in the same edit.
    //
    // WHY IT IS GATED, which is what this tripwire exists to make somebody
    // justify. PROVEN LIVE WITH A CONTROL before the entry was written: on
    // SCP-DEMO-2026 with NO session token, `read customers` answered 200 and
    // returned a row carrying NAME, EMAIL, PHONE AND STREET ADDRESS, and
    // `write customers` with an id-less payload answered 400 from the HANDLER
    // BODY -- so the gate did not fire, and nothing was stored because :4769
    // refuses before any store call. The control is what makes it a finding
    // rather than a guess: `invoices` and `scp_quotes` on the SAME bare key
    // answered 403 both, so the gate existed, worked, and did not cover this.
    //
    // AND IT BREAKS THE "TIER A" STOPPING RULE DELIBERATELY. `customers` is
    // carried B/B in docs/CRITICALITY-TIERS.md while its own confidentiality
    // cell already reads "A CUSTOMER's NAME, PHONE, EMAIL AND STREET ADDRESS"
    // -- the basis was corrected and the LETTER was not, and the letter is
    // what a Tier-A-scoped sweep reads. THE GATE IS NOW AHEAD OF THE REGISTER.
    // The B->A retier is owed and hank holds that file
    // (2026-10-05T12:57:55Z). Waiting on a register cell while a customer's
    // address is readable on a browser-shipped licence key is the wrong trade.
    //
    // THE RESOURCE IS SPELLED BARE, same trap as `invoices` above: the storage
    // table is scp_customers and an entry under that name would gate nothing.
    assert.match(m[0], /'customers':\s*\['read', 'write'\]/);
    // 78 -> 80 on 2026-10-11: ONE resource, TWO pairs. SAIRNfreedom
    // `sf_officers`, read and write. Two, not three -- see the note at the end
    // of this block about what this counter actually counts.
    //
    // WHY IT IS GATED, which is what this tripwire exists to make somebody
    // justify. `sf_officers` is the post's GOVERNANCE RECORD -- who holds which
    // office -- and docs/CRITICALITY-TIERS.md:365 has carried it **A on
    // integrity, B on confidentiality** since the 2026-09-23 full sf_ re-audit,
    // eighteen days before this gate. It was in NEITHER list, so the licence
    // key alone -- shipped to the browser, readable by anyone who can open the
    // app -- could rewrite the roster wholesale through the generic
    // SF_RESOURCES write branch, which stores `data: payload` verbatim with no
    // role or capability check.
    //
    // THE SHARP PART IS THAT EVERY GUARD OVER THAT ROSTER IS CLIENT-SIDE:
    //   sairnfreedom.html:2849       activeProvisioners()
    //   sairnfreedom.html:2860-2869  SPEC 1c -- refuses deactivating the LAST
    //                                active provisioner
    //   sairnfreedom.html:2878-2885  refuses a second sole-holder
    // A server write past this table is a write past all three, and can leave
    // the post at zero active provisioners -- the unrecoverable-through-the-API
    // state SPEC 1c exists to make unreachable, and the state RF-PINNACLE-2026
    // is the live instance of.
    //
    // NOT PROVEN LIVE, and that is stated rather than implied. The 2026-10-05
    // entry above carries a bare-key 200 with a control; this one does not. The
    // evidence here is a reproducing artifact run against this file at the
    // commit before the fix, exit 1 REPRODUCES -> exit 0 FIXED after:
    //   .claude/skills/sairn-hover-auditor/tools-hover2/
    //     sf_officers_provisioning_bypass_repro.py
    // A live bare-key call was not driven. Source-level only.
    //
    // NOT A CREDENTIAL BYPASS. api/sf-auth.js:328 takes the provisioning role
    // from the SIGNED SESSION TOKEN, not from this table, so a forged officer
    // row mints nothing. The finding is integrity of the governance record and
    // of the three client-side guards above.
    //
    // ── WHAT THIS COUNTER COUNTS, because the 2026-10-05 entry above explains
    //    its own +3 as "two verbs plus the SD_GATE_APP entry" and that is NOT
    //    what line 206 does ─────────────────────────────────────────────────
    // `m[0]` is the SD_SESSION_GATED literal ALONE. SD_GATE_APP is a different
    // object and contributes nothing here. What it DOES count, and the reason
    // this entry is +2 while that one claimed +3, is that the regex runs over
    // this block's RAW TEXT -- comments are NOT blanked, unlike
    // api/sd-data-sf-session-gate.test.js:83 which blanks them before scanning.
    // So a COMMENT inside sd-data.js's gate table that quotes a two-verb array
    // literal adds two phantom pairs. MEASURED on this change: the first draft
    // of the sf_officers comment quoted one and this arm reported 82 for an
    // edit that added 2. The comment was reworded, not the count.
    //
    // That makes the +3 above suspect by the same mechanism. It is NOT
    // corrected here: 78 was the measured count at 263f736f and re-deriving
    // somebody else's arithmetic from a guess is how a tripwire's number stops
    // meaning anything. Flagged for whoever owns that entry.
    // 80 -> 86 on 2026-10-11, same batch, SECOND edit: THREE SAIRNscape
    // resources, SIX pairs -- scp_designs, scp_vendors, scp_progress_photos,
    // read and write each.
    //
    // WHY EACH, which is what this tripwire asks for. From
    // .claude/skills/sairn-hover-auditor/tools-hover2/scp_session_gate_repro.py
    // --all: 15 of 22 SAIRNscape resource/action pairs were gated by NEITHER
    // mechanism at 263f736f. Three of the eight ungated resources are gated
    // here; FIVE are deliberately left and are NAMED in
    // api/sd-data-scp-session-gate.test.js's UNGATED_REST, each with the
    // columns that justify leaving it.
    //   scp_designs           Tier A since 2026-10-05
    //                         (docs/CRITICALITY-TIERS.md:538). That suite's own
    //                         stopping rule made it OWED, not new.
    //   scp_vendors           B by letter; its `data` jsonb is name, category,
    //                         CONTACT, PHONE, EMAIL, terms, notes. The same
    //                         shape as `customers` above, found the same way --
    //                         by reading the row, not the tier cell. Its
    //                         register cell says in its own words that it was
    //                         "classified by the stated B rule rather than
    //                         individually read".
    //   scp_progress_photos   photo_b64 of a customer's property, plus
    //                         captured_by and qc_by. Its write was gated only
    //                         INSIDE `if (payload.qc_status === ...)`
    //                         (api/sd-data.js:5231), so an upload needed no
    //                         session and the repro -- a substring test for
    //                         verifySessionToken -- called it FIXED. The real
    //                         figure was 16 of 22, not 15.
    //
    // NOT PROVEN LIVE. No bare-key call was driven against SCP-DEMO-2026 for
    // any of the three, unlike the 2026-10-05 entry above which has one with a
    // control. Source-level plus the reproducing artifact's exit codes, and
    // that limit is stated rather than left to be assumed.
    // 86 -> 94 on 2026-10-11, same day, THIRD edit: FOUR SAIRNfreedom
    // resources, EIGHT pairs -- sf_sessions, sf_shifts, sf_tickets, sf_rentals,
    // read and write each. The count is +8 and not +12: SD_GATE_APP is a
    // different object and contributes nothing to `m[0]`, and the comment that
    // landed beside these four quotes no two-verb array literal, which the
    // note above this line explains is the only way a comment moves this
    // number. MEASURED at 94 after the edit, not predicted.
    //
    // WHY EACH, which is what this tripwire exists to make somebody justify.
    // DERIVED rather than picked: SF_RESOURCES carries 36 resources, 18 were
    // gated before this edit, and NINE of the remaining 18 are Tier A by
    // docs/CRITICALITY-TIERS.md's own letters. These four are the Tier A ones
    // with a money or statutory figure ON THE ROW:
    //   sf_sessions  register:373. prizeCap, receipts, prizes. prizeCap IS A
    //                STATUTORY LIMIT (ORC Chapter 2915), not a house rule, and
    //                this is the regulated event record the rest of the gaming
    //                family reconciles against. It sat at B until 2026-09-23
    //                while sf_ledger above it was already A.
    //   sf_shifts    register:374, and the only one of the four that is A on
    //                CONFIDENTIALITY too -- the row attributes a CASH VARIANCE
    //                to a NAMED employee and the app's own toast states it.
    //   sf_tickets   register:377. unitPrice and total snapshotted at the
    //                moment of sale, against a named member.
    //   sf_rentals   register:369. charge and proceeds, plus the
    //                alcohol/notified compliance pair the rental turns on.
    //
    // FIVE MORE ARE TIER A AND DELIBERATELY STAY UNGATED, named here so the
    // asymmetry is visible rather than silent -- which is the thing that let
    // sf_vehicle_service sit ungated for six days: sf_district_imports
    // (register:353), sf_events (:358), sf_permit_flags (:367), sf_products
    // (:368), sf_vehicles (:380). This file's sibling
    // api/sd-data-sf-session-gate.test.js says in its own words that widening
    // the gate is a PRODUCT DECISION about who may see a duty roster; the batch
    // that sent this change named four and their client write sites, not nine.
    // Routed with the derivation, not swept in.
    //
    // NOT PROVEN LIVE, stated rather than implied: no bare-key call was driven
    // against a real SAIRNfreedom licence for any of the four. Source-level,
    // plus the register letters and the client write sites read at this HEAD.
    assert.match(m[0], /'sf_sessions':\s*\['read', 'write'\]/);
    assert.match(m[0], /'sf_shifts':\s*\['read', 'write'\]/);
    assert.match(m[0], /'sf_tickets':\s*\['read', 'write'\]/);
    assert.match(m[0], /'sf_rentals':\s*\['read', 'write'\]/);
    // 94 -> 104 on 2026-10-13: FIVE SAIRNfreedom resources, TEN pairs --
    // sf_district_imports, sf_events, sf_permit_flags, sf_products,
    // sf_vehicles, read and write each. MEASURED at 104 after the edit, not
    // predicted, and the comment beside them in api/sd-data.js quotes no
    // two-verb array literal, which is the only way a comment moves this
    // number.
    //
    // WHY THEY ARE GATED, which is what this tripwire exists to make somebody
    // justify: MICHAEL DECIDED IT. All five are Tier A by
    // docs/CRITICALITY-TIERS.md's own letters and all five were NAMED by b4 as
    // the remainder of a nine-resource derivation it deliberately did not act
    // on -- "widening the gate is a PRODUCT DECISION", in this file's sibling's
    // words. The decision arrived; the five were the whole of it.
    //
    //   sf_district_imports  :353  district records the post cannot re-request
    //   sf_events            :358  the calendar everything else hangs off
    //   sf_permit_flags      :367  gaming permit state, ORC Chapter 2915
    //   sf_products          :368  the priced catalogue sf_tickets snapshots
    //   sf_vehicles          :380  reads the odometer sf_vehicle_service
    //                              advances -- and that WRITER was gated on
    //                              2026-09-29 while this READER stayed open
    //
    // THIS RETIRES A STOPPING RULE RATHER THAN APPLYING IT. Four waves of this
    // app stopped at Tier A; there is no Tier A sf_ resource left ungated, so
    // the next widening is a different question (nine B/B resources) and needs
    // its own decision.
    //
    // NOT PROVEN LIVE FOR THESE FIVE. The eleven gated before them WERE proven
    // live on 2026-10-13 -- bare key 403 on both verbs, valid session 200, see
    // docs/hank-evidence/b6_live_session_control_probe.py -- but that probe ran
    // against SAIRNscape and SF-PINNACLE-2026 has no employee PIN in this repo,
    // so the SAIRNfreedom half of that control could not be driven at all.
    // 104 -> 122 on 2026-10-13 (b7): THE LAST NINE SAIRNfreedom RESOURCES,
    // eighteen pairs. SAIRNfreedom is now gated wholesale, 36 of 36.
    //
    // WHY THEY ARE GATED, which is what this tripwire exists to make somebody
    // justify, AND IT IS NOT THE REASON ANY PREVIOUS WAVE GAVE. Every earlier
    // wave gated on the SENSITIVITY of the row and stopped when Tier A ran out
    // -- the paragraph directly above says so in its own words, that the next
    // widening is "a different question (nine B/B resources) and needs its own
    // decision". These nine are those nine, and they are the only sf_
    // resources that are B on integrity AND B on confidentiality.
    //
    // THE DIFFERENT QUESTION WAS ANSWERED BY A DIFFERENT ARGUMENT: the role
    // matrix in api/_lib/sf-roles.js already held a REVIEWED policy for all
    // nine, written in b6 to cover all 36 deliberately, and a role policy
    // cannot run on a licence-key-only resource because no session means no
    // role. So the policy existed and could not fire. Gating them is what
    // makes it fire. No matrix cell was authored to justify the gate -- the
    // cells predate it, which is the only reason this is not a product
    // decision being made by the session that benefits from it.
    //
    //   sf_bottle_fills  sf_ceremonial_items  sf_documents  sf_honor_details
    //   sf_inventory_counts  sf_national_categories  sf_service_hours
    //   sf_service_referrals  sf_vendors
    //
    // THREE OF THEM CLOSE A SPLIT PAIR, which is the sharpest part: documents
    // were open while the SIGNATURES THAT BIND PEOPLE TO THEM were gated
    // 2026-09-24; referrals were open while the service APPOINTMENTS were gated
    // 2026-09-22 for a VA-adjacent outcome; vendors were open while
    // sf_vendor_prices was gated 2026-09-21. Same shape as sf_vehicles and
    // sf_vehicle_service, which sat split for two weeks.
    //
    // sf_national_categories IS THE WEAKEST AND IS LABELLED SO IT CAN BE
    // REVERSED ALONE: it stores bare strings with no id, and both
    // sfSyncCollection and sfServerWinsMerge skip id-less records, so
    // client-side the gate is a no-op today. It is in for set completeness.
    //
    // NOT PROVEN LIVE, and the reason is now one SQL run away rather than
    // structural: SF-PINNACLE-2026 had no employee PIN anywhere in the repo,
    // which is why the b6 live control could only be driven against
    // SAIRNscape. b7 wrote sql/sairnfreedom_demo_owner_credential_2026-10-13.sql
    // (round-tripped through hashPin/verifyPin, then re-verified against the
    // literals in the committed file) so that this half becomes drivable the
    // moment Michael runs it. Source-level only until then.
    // 122 -> 132 on 2026-10-13 (b8): SAIRNscape'S LAST FIVE, TEN PAIRS --
    // scp_jobs, scp_irr_controllers, scp_irr_zones, scp_irr_schedules,
    // scp_water_features. Eleven of the app's twelve resources are now gated.
    //
    // WHY THEY ARE GATED, which is what this tripwire exists to make somebody
    // justify, AND IT IS NOT THE ARGUMENT ANY SAIRNscape WAVE GAVE BEFORE.
    // Every earlier wave gated on the SENSITIVITY of the row -- Tier A first,
    // then three more whose COLUMNS were read instead of their tier letter
    // (a contact's phone, a photo of a customer's property). These five do not
    // qualify on that argument and it is stated plainly rather than stretched:
    // no person's name, no contact detail, no money and no regulated
    // determination on any of the five rows, and each one's customer_id is a
    // FOREIGN KEY whose identity lives on `customers`, gated since 2026-10-05.
    //
    // THE ARGUMENT IS THE LICENCE KEY, AND IT IS MICHAEL'S DECISION. The key
    // that authorised these reads is SHIPPED TO THE BROWSER and readable by
    // anyone who can open the app, so "licence-only" means "public" for a row
    // that is a landscaping company's operational record -- its job scopes, its
    // controller inventory, its irrigation run times. The suite that disclosed
    // them as ungated said in its own words that gating them "is a defensible
    // product decision ... it is NOT a finding, and it is not made here". It
    // has now been made.
    //
    // MEASURED BEFORE, NOT ASSUMED: hover2's artifact
    // .claude/skills/sairn-hover-auditor/tools-hover2/scp_session_gate_repro.py
    // --all last reported 10 of 22 resource/action pairs reachable by NEITHER
    // mechanism, and the ten were exactly these five times two verbs. Read-only
    // from this clone; the auditor's clone was not entered.
    //
    // A SECOND BEHAVIOUR CHANGE RIDES ALONG AND IS CHOSEN, NOT INHERITED: being
    // in this table makes the deactivated-credential pre-check apply, so a
    // deactivated employee hitting these five now gets a hard 403
    // CREDENTIAL_INACTIVE instead of a logged pass-through.
    //
    // AND THE TWELFTH RESOURCE IS NOT GATED AND IS NOT AN OVERSIGHT.
    // api/_resources/sairnscape.js owns twelve names; `schedule`
    // (api/sd-data.js:5607/:5615) is outside the repro's 22 pairs and outside
    // the decision. api/sd-data-scp-session-gate.test.js now DRIVES it as the
    // licence-only control and derives its two lists from the registry, so a
    // thirteenth resource cannot land covered by neither.
    // 132 -> 134 on 2026-10-14 (b9): `schedule`, SAIRNscape's TWELFTH and last
    // licence-only resource, two pairs. MICHAEL'S DECISION, on the same
    // argument as the five in b8 -- the licence key is shipped to the browser.
    //
    // WHAT THIS CLOSES IS NOT A NEW FINDING, IT IS b8's DISCLOSURE. b8 gated
    // the five that hover2's repro reported and discovered the repro had only
    // ever measured ELEVEN of the app's twelve resources (22 pairs = 11 x 2).
    // `schedule` was in neither the gate nor the SAIRNscape suite's
    // licence-only list, so no arm in that file could see it in either
    // direction. It was left open because nobody had decided it, and the one
    // fact that needed reading first was recorded then: `schedule` is the only
    // SAIRNscape resource whose bare name is also a StoneDesk PANEL ID, and
    // all seven StoneDesk mentions are navigation rather than sd-data calls.
    //
    // AND IT COSTS THAT SUITE ITS LICENCE-ONLY CONTROL, which is handled there
    // rather than hidden: the loop that drove "what is not gated is still not
    // gated" now has nothing to drive, so it is replaced by an explicit
    // empty-on-purpose arm, a registry-derived count, and a cross-app arm
    // proving this table has not started swallowing resources it does not own.
    assert.strictEqual(pairs, 134,
      'the gate table changed size to ' + pairs + ' pairs -- add the new resource to this test and say why it is gated');
  });

  // ── EVERY GATED RESOURCE HAS AN expectedApp ENTRY (2026-09-29) ───────────
  // THE DEFECT THIS CLOSES, and it was live for a day: sf_trustee_audits was
  // added to SD_SESSION_GATED with no SD_GATE_APP entry, so the gate resolved
  // expectedApp to 'stonedesk' by default and refused EVERY correctly signed-in
  // SAIRNfreedom officer with FORBIDDEN "sign in first". It fails CLOSED and
  // CONFUSINGLY, which is the hardest failure to read and the one that gets a
  // security change reverted as broken rather than fixed.
  //
  // THE RULE COULD NOT BE WRITTEN UNTIL TODAY, and that is why it did not exist.
  // Four StoneDesk-native resources -- locations, memory, profile, slabs --
  // relied on `SD_GATE_APP[resource] || 'stonedesk'` and resolved CORRECTLY
  // without an entry, so "gated with no entry" was a state that was sometimes
  // right, and no arm could demand an entry without failing on four correct
  // ones. Those four are now explicit (no behaviour change -- the fallback
  // returned exactly those values), which leaves this rule with NO exemptions.
  //
  // PLATFORM-WIDE, not per-app. api/sd-data-sf-session-gate.test.js asserts the
  // same thing for sf_ names only; the resource that broke was an sf_ one and
  // the next one will not be.
  await test('every gated resource has an SD_GATE_APP entry -- nothing relies on the '
    + 'stonedesk default', () => {
      const fs = require('fs');
      const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
      const gatedM = src.match(GATED_RE);
      const appM = src.match(GATE_APP_RE);
      assert.ok(gatedM && appM,
        'one of the two maps could not be parsed out of the source, so this arm '
        + 'checked NOTHING -- a third state, not a pass');
      const gated = mapNames(gatedM[0]);
      const mapped = mapNames(appM[0]);
      // NOT VACUOUS: a regex that stopped matching empties both sets and the
      // difference with them, which reads exactly like agreement.
      assert.ok(gated.size >= 30 && mapped.size >= 30,
        'parsed ' + gated.size + ' gated and ' + mapped.size + ' mapped names -- '
        + 'a silent zero here looks identical to a clean result');
      const missing = [...gated].filter((n) => !mapped.has(n)).sort();
      assert.deepStrictEqual(missing, [],
        'session-gated with NO SD_GATE_APP entry, so expectedApp resolves to '
        + 'stonedesk and every correctly signed-in caller of that app is refused '
        + 'FORBIDDEN "sign in first": ' + missing.join(', '));
      console.log('       ' + gated.size + ' gated / ' + mapped.size
        + ' mapped, 0 relying on the default');
    });

  await test('NEGATIVE CONTROL: that arm CATCHES a gated resource with no entry', () => {
    // Without this, a broken parse or a difference that always returns empty
    // passes the arm above for ever. The fixture is the real defect shape:
    // present in one map, absent from the other.
    const g = mapNames("const SD_SESSION_GATED = {\n      'zz_one': ['read'],\n"
      + "      'zz_two': ['read'],\n    };");
    const a = mapNames("const SD_GATE_APP = {\n      'zz_one': 'zzapp',\n    };");
    const missing = [...g].filter((n) => !a.has(n));
    assert.deepStrictEqual(missing, ['zz_two'],
      'the set difference used by the arm above cannot see a gated resource '
      + 'with no entry, so that arm proves nothing');
  });


  // ── EVERY PAIR IN THE TABLE IS DRIVEN SOMEWHERE, AND IT IS SAID WHERE ─────
  // Added 2026-09-16. The count arm above proves the table has not changed
  // size; it says nothing about whether anything EXERCISES the entries. GATED
  // drives the StoneDesk-session pairs; everything needing another app's session
  // is driven in its own suite and named in `drivenElsewhere` below, because
  // this file mints StoneDesk tokens and cannot mint a SAIRNlaw or SAIRNfreedom
  // one.
  //
  // THE PROSE HERE USED TO SAY "7 of the 11 pairs" AND THE TABLE HELD 17 WHEN
  // THAT WAS READ (2026-09-22) -- a hand-maintained count in a comment, stale
  // and invisible because nothing compares prose to the table. Replaced with a
  // description rather than a number: the arm below DERIVES both sides and names
  // what is missing, so a count in this comment adds nothing but a second thing
  // to get wrong.
  //
  // The failure this prevents is the quiet one: a resource added to the table,
  // counted by the arm above, and driven by nothing anywhere -- which looks
  // identical to a covered resource from inside this file.
  await test('every pair in the gate table is DRIVEN -- here, or in a suite '
    + 'this arm names', () => {
      const fs = require('fs');
      const src = fs.readFileSync(require.resolve('./sd-data.js'), 'utf8');
      const m = src.match(/const SD_SESSION_GATED = \{[\s\S]*?\n    \};/);
      assert.ok(m, 'the gate table is gone');
      const inTable = (m[0].match(/'([a-z_]+)':\s*\[/g) || [])
        .map((x) => x.replace(/'|:|\s|\[/g, '')).sort();
      const drivenHere = [...new Set(GATED.map((p) => p[0]))];
      // Stated by hand, with the file that does the driving. A derived answer
      // here would be this arm asserting its own premise.
      const drivenElsewhere = {
        locations: 'api/sd-data-locations.test.js',
        law_trusttx: 'api/sd-data-law-trusttx-session.test.js',
        // Phase 2's final three, driven together in one suite for the same
        // reason law_trusttx has its own: they need a SAIRNlaw session and
        // this file mints StoneDesk ones. That suite drives the whole chain --
        // no session refused on read AND write with ZERO database calls, all
        // three real roles still reading, a write still succeeding so the gate
        // is a split rather than a lockout, a session from another SAIRN app
        // refused, a deactivated credential refused on a token that still
        // verifies, and both table entries asserted on the source.
        law_clients: 'api/sd-data-law-phase2-session.test.js',
        law_matters: 'api/sd-data-law-phase2-session.test.js',
        law_deadlines: 'api/sd-data-law-phase2-session.test.js',
        // SAIRNfreedom's three, driven in their own suite for the same reason
        // law_trusttx is: they need a SAIRNfreedom session, and this file mints
        // StoneDesk ones. That suite drives the whole chain -- no session
        // refused, a real session minted by api/sf-auth.js accepted, a write
        // gated as well as a read, a deactivated employee refused on a token
        // that is still cryptographically valid, and a token from another SAIRN
        // app refused.
        // -- sf_accounts, sf_ledger and sf_vendor_prices were listed here by
        //    name until 2026-09-24. They are not gone; they moved to the
        //    prefix rule below with the other twelve, because naming three of
        //    fifteen by hand is how the other twelve came to be covered by
        //    nothing. The suite is the same one.
        // SAIRNdesign's five, 2026-09-22. Driven in their own suite for the
        // same reason: that one mints sairndesign sessions.
        sdn_contracts: 'api/sd-data-sdn-session-gate.test.js',
        sdn_discounts: 'api/sd-data-sdn-session-gate.test.js',
        sdn_invoices: 'api/sd-data-sdn-session-gate.test.js',
        sdn_pos: 'api/sd-data-sdn-session-gate.test.js',
        sdn_referrals: 'api/sd-data-sdn-session-gate.test.js',
        // The four promoted B->A on 2026-09-23 and gated 2026-09-24 -- the
        // gate's stopping rule was "Tier A", not "the five names that were A
        // on the day it was armed". Driven in the same suite, whose GATED
        // table grew with them (40 arms).
        sdn_projects: 'api/sd-data-sdn-session-gate.test.js',
        sdn_proposals: 'api/sd-data-sdn-session-gate.test.js',
        sdn_specitems: 'api/sd-data-sdn-session-gate.test.js',
        sdn_timeentries: 'api/sd-data-sdn-session-gate.test.js',
        // SAIRNscape's two, 2026-09-25. Driven in their own suite for the same
        // reason: that one mints sairnscape sessions and this file mints
        // StoneDesk ones.
        //
        // `invoices` IS SPELLED BARE ON PURPOSE and is not a typo for
        // sdn_invoices or scp_invoices. SAIRNscape claimed the bare name
        // before the scp_ convention existed; the storage table is
        // scp_invoices and the RESOURCE the dispatch tests for is `invoices`.
        // The named suite has an arm whose whole job is that distinction.
        invoices: 'api/sd-data-scp-session-gate.test.js',
        scp_quotes: 'api/sd-data-scp-session-gate.test.js',
        // `customers`, 2026-10-05. Same suite, and it is driven there rather
        // than here for the same reason the other two are: that file mints
        // SAIRNscape sessions. Its GATED list drives a refusal, an allow with a
        // real session, a wrong-app token and a deactivated credential per
        // resource, so adding the name there added four arms without anybody
        // writing one -- 18 passed became 24.
        customers: 'api/sd-data-scp-session-gate.test.js',
        // SAIRNscape's three more, 2026-10-11. Same suite, same reason -- it
        // mints SAIRNscape sessions. Adding the three names to its GATED list
        // added SIX arms each without one being written: refusal on read and on
        // write, allow-with-a-real-session on read and on write, a wrong-app
        // token, and a deactivated credential. 24 passed became 46.
        //
        // scp_designs IS NOT A NEW DECISION. That suite's own note says "if a
        // third SAIRNscape row is promoted, it belongs here and in both tables
        // on the same day" -- docs/CRITICALITY-TIERS.md:538 promoted it B -> A
        // on 2026-10-05 and it did not land for six days.
        //
        // scp_vendors AND scp_progress_photos ARE AHEAD OF THE REGISTER, the
        // same way `customers` above is, and for the same reason: their columns
        // were read out of sql/sairnscape_data_schema_phase2.sql instead of
        // their tier letter. scp_vendors carries a named contact's PHONE and
        // EMAIL; scp_progress_photos carries photo_b64 of a customer's property
        // plus captured_by and qc_by. Both retiers are owed.
        //
        // AND scp_progress_photos' WRITE WAS ALREADY HALF-GATED IN A WAY A
        // SUBSTRING CHECK CANNOT SEE: api/sd-data.js:5231 calls
        // verifySessionToken inside `if (payload.qc_status === ...)`, so it
        // fired on a QC decision and never on an upload. The reproducing
        // artifact that found this family scored it FIXED for exactly that
        // reason. That is cross-domain convention 8 -- a check that stops
        // testing -- in a tool that was six days old.
        scp_designs: 'api/sd-data-scp-session-gate.test.js',
        scp_vendors: 'api/sd-data-scp-session-gate.test.js',
        scp_progress_photos: 'api/sd-data-scp-session-gate.test.js',
        // SAIRNscape's LAST FIVE, 2026-10-13 (b8). Same suite, same reason --
        // it mints SAIRNscape sessions and this file mints StoneDesk ones.
        // Adding the five names to its GATED list added THIRTY arms without one
        // being written (46 passed became 73, with two of the difference being
        // the new derived-completeness arm and the `schedule` control).
        //
        // THESE ARE THE FIRST ENTRIES HERE GATED ON A PRODUCT DECISION RATHER
        // THAN ON THE ROW'S CONTENT, and the pair-count comment above carries
        // the argument. What matters for THIS map is that the named suite no
        // longer hand-types its SAIRNscape population: it derives GATED +
        // UNGATED_REST against api/_resources/sairnscape.js, which is the
        // check that would have caught `schedule` -- the twelfth resource,
        // ungated, and invisible to every arm in that file until today.
        scp_jobs: 'api/sd-data-scp-session-gate.test.js',
        scp_irr_controllers: 'api/sd-data-scp-session-gate.test.js',
        scp_irr_zones: 'api/sd-data-scp-session-gate.test.js',
        scp_irr_schedules: 'api/sd-data-scp-session-gate.test.js',
        scp_water_features: 'api/sd-data-scp-session-gate.test.js',
        // The twelfth, 2026-10-14 (b9). Same suite, and it added six arms
        // without one being written (73 passed became 80, the rest being the
        // two arms that replaced the now-empty licence-only loop).
        //
        // `schedule` IS SPELLED BARE ON PURPOSE and is not a typo for
        // scp_irr_schedules or sairngrounds' schedule. SAIRNscape claimed the
        // bare name before the scp_ convention existed -- the same history as
        // `invoices` and `customers` above -- and api/sd-data.js:4892 records
        // that sairngrounds had to use a prefixed name BECAUSE this one was
        // already taken.
        schedule: 'api/sd-data-scp-session-gate.test.js',
        // SAIRNmechanical's one, 2026-09-29. Driven in its own suite for the
        // same reason as every entry above: that one mints sairnmechanical
        // sessions and this file mints StoneDesk ones.
        //
        // IT IS THE FIRST WRITE-ONLY ENTRY IN THE TABLE, so the named suite
        // carries something the others do not: arms that require the READ and
        // the three sibling mech_ writes to STILL ANSWER on the licence key
        // alone. A gate that quietly grew to cover mech_checks -- the cheque
        // register its own branch comment calls "the sharp one" -- would be an
        // unreviewed decision, and those arms are what make that visible.
        mech_docs: 'api/sd-data-mech-session-gate.test.js'
      };
      // ── AND THE sf_ REMAINDER, COVERED BY A RULE RATHER THAN BY NAME ──────
      // THIS ARM WAS RED ON origin/main FROM 2026-09-22 TO 2026-09-24 and the
      // reason is worth more than the fix. The map above named three sf_
      // resources; the gate held fifteen. Eleven of them -- minors' names, a
      // felony and gambling disqualification flag, an ORC 2915 payee record --
      // were gated in source and exercised by NOTHING, and this arm said so
      // correctly for two days while the suite sat red and was read as noise.
      // The comment forty lines above already records that happening once
      // before, in this same arm, in September 2026. Twice is a design fault
      // in the map, not in the people reading it.
      //
      // A per-resource line goes stale the moment a sixteenth is gated. A
      // PREFIX RULE does not -- but a prefix rule is also how a coverage claim
      // becomes a lie, so it is VERIFIED rather than trusted: the named suite
      // must itself derive its list from SD_SESSION_GATED, which is asserted
      // below. If somebody replaces that loop with a hand-typed list, this
      // stops passing.
      //
      // KEPT SEPARATE FROM drivenElsewhere ON PURPOSE. Every entry in that map
      // is checked by a literal mention of the resource name in the named
      // suite, which is exactly the check a derived loop must fail -- it drives
      // sf_disbursements without ever spelling it. Folding the prefix rule into
      // that map would have meant weakening the literal-mention check for all
      // eighteen named resources to accommodate one rule. These are verified by
      // a different assertion instead, immediately below.
      const SF_SUITE = 'api/sf-session-gate.test.js';
      const drivenByDerivedLoop = inTable.filter((r) => r.indexOf('sf_') === 0);
      const sfSuiteSrc = fs.readFileSync(
        require.resolve('./' + SF_SUITE.replace('api/', '')), 'utf8');
      assert.ok(sfSuiteSrc.indexOf('SD_SESSION_GATED') > -1,
        SF_SUITE + ' no longer reads SD_SESSION_GATED, so the prefix rule '
        + 'above is claiming coverage it cannot demonstrate. Either restore '
        + 'the derived loop there, or list each sf_ resource here by name.');
      assert.ok(sfSuiteSrc.indexOf('gatedSfResources') > -1,
        SF_SUITE + ' no longer drives a derived list of gated sf_ resources. '
        + 'The prefix rule above depends on that loop existing.');
      const covered = [...drivenHere, ...Object.keys(drivenElsewhere),
                       ...drivenByDerivedLoop].sort();
      assert.deepStrictEqual(inTable, covered,
        'a gated resource is driven by nothing: ' +
        inTable.filter((r) => covered.indexOf(r) === -1).join(', ') +
        ' -- add arms here, or name the suite that drives it');
      Object.keys(drivenElsewhere).forEach((r) => {
        const f = require.resolve('./' + drivenElsewhere[r].replace('api/', ''));
        assert.ok(fs.existsSync(f), 'the suite named for ' + r + ' does not exist: '
          + drivenElsewhere[r]);
        assert.ok(fs.readFileSync(f, 'utf8').indexOf(r) > -1,
          drivenElsewhere[r] + ' does not mention ' + r + ' at all');
      });
    });

  await test('an ungated resource is untouched by the table', async () => {
    const { handler } = loadHandler({ noSession: true });
    const res = mockRes();
    await handler(mockReq('read', 'employees', {}), res);
    // employees has its own, older gate -- what matters is that this one did
    // not start refusing things it was never asked to.
    assert.ok(res.body && res.body.error, 'expected employees to keep its own refusal');
    assert.ok(!/sign in first/i.test(res.body.error.message || ''),
      'the new gate swallowed a resource that has its own');
  });

  console.log('\n' + (process.exitCode ? 'FAILURES ABOVE' : 'ALL ' + passed + ' SESSION-GATE ASSERTIONS PASS'));
}

main();
