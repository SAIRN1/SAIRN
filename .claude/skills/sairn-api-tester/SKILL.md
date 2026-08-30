---
name: sairn-api-tester
description: Write and run tests against a SAIRN API endpoint that actually exercise it — the auth gate, the storage layer, the refusals, and the boundary in both directions. Trigger before calling any endpoint done, when adding a branch to api/sd-data.js or any api/*-auth.js, when a test file is added or changed, and whenever a suite is green but the feature has never been used. Encodes the specific ways tests on this platform have been green while the code was broken.
---

# SAIRN API Tester

Every rule here exists because a real SAIRN test suite was green while the thing
it named was broken. The failure mode is never "the test was weak" — it is
**"the test was aimed at the wrong layer"**, and a green bar makes that
invisible.

---

## 1. A test that cannot reach the code it names is worse than no test

**Incident:** `api/_lib/dental-credentials-endpoint.test.js` ran **1 passed / 15
failed** and had for some time. When written, every `dnt_*` branch was gated by
the licence key alone, so `Authorization: Bearer DNT-TEST` reached real logic.
Employee auth was added later; every branch began requiring `x-sd-auth`; the
harness never sent one. Fifteen 401s.

**The single passing test passed for the wrong reason.** *"evaluate writes
NOTHING"* is trivially true of a 401.

**Rules:**
- A harness must send a **real signed session**, not a stubbed one.
- Ask of every green test: *would this still pass if the feature were deleted?*
  If yes, it is asserting nothing.
- When an auth gate changes, **the test file is part of the blast radius.**

## 2. Sign the session for the hash the handler actually derives

**The trap, and it costs an hour if you have not seen it:** `license_hash` is
derived by `api/_lib/license.js` as **sha256 of the bearer key**. It is *not* the
`license_hash` field on the stubbed `license_keys` row.

A token signed against the row's literal value **verifies fine in isolation and
is rejected by the handler**, with an indistinguishable `NO_SESSION`.

    const { signSessionToken } = require('./auth');
    const LICENSE_HASH = require('./license').hashLicense('DNT-TEST');
    const tok = (role) => signSessionToken({
      app: 'sairndental', employee_id: 'EMP-' + role.toUpperCase(),
      role, license_hash: LICENSE_HASH });

Set `process.env.SD_AUTH_SECRET` **before requiring the handler** — both signer
and verifier read it at call time, and an unset secret makes every session
silently unverifiable.

## 3. Make role a parameter, not an invisible constant

**This is what let the `dnt_cred_rules` gap hide.** The harness always sent the
same implicit identity, so "which roles can do this" was never a question the
suite could ask.

    async function call(action, resource, payload, role) {   // role defaults to owner
      const headers = { authorization: 'Bearer ' + KEY };
      const r = role === undefined ? 'owner' : role;
      if (r !== null) headers['x-sd-auth'] = tok(r);         // null = no session at all
      ...
    }

Then assert the **whole ladder**, not just the happy path:

    no session   -> 401 NO_SESSION,  and nothing was stored
    wrong role   -> 403 FORBIDDEN,   and nothing was stored
    right role   -> 200,             and the row is present
    right role,
    bad payload  -> 400 <specific code>, and nothing was stored

## 4. Assert the refusal AND that nothing was written

A 403 that still wrote is a worse bug than a 200. Every negative case asserts
**both** the status code and the store's unchanged state.

    const before = JSON.stringify(store.rules);
    const r = await call('write', 'dnt_cred_rules', RULE, 'provider');
    assert.strictEqual(r.code, 403);
    assert.strictEqual(JSON.stringify(store.rules), before);

## 5. Mutation-check: prove the test fails on the old code

**A regression test that has never been red is not known to be a regression
test.** Before trusting a new test, run it against the pre-fix commit.

    git stash push api/sd-data.js && node <test> ; git stash pop

**Real result:** the `dnt_cred_rules` role tests went red against `a877978^` —
provider 200, frontdesk 200, `verified_by: 'license'` — and green after. That is
what made them a guard rather than decoration.

## 6. Unit tests do not exercise the storage layer — Guardian Check 29

**Incident:** California's service extensions. The engine learned the new rule
shape; the validator in a *different file* did not. **84 of 84 isolation tests
passed** while all seven California civil rows were unstorable. The real write
found it immediately: `400 INVALID_RULE — service_extension.add must be a
number of days.`

**Any diff touching a validator, a SQL `CHECK`/`unique`/`not null`, or the shape
of what gets persisted requires a real write through the real endpoint, a read
back, and the boundary tried in both directions.** A stub cannot catch a
constraint it does not implement.

## 7. Assert on the request the handler ISSUED, not just the response

An upsert and an insert both return 200. Only the outbound request tells them
apart — which is the only mechanical proof of "append-only".

    const insert = requests.filter(q => q.method === 'POST' && q.url.includes('dnt_credentials'))[0];
    assert.strictEqual(insert.url.indexOf('on_conflict'), -1);
    assert.strictEqual(String(insert.prefer).indexOf('merge-duplicates'), -1);
    assert.ok(/^[0-9a-f]{64}$/.test(insert.body.license_hash));   // DERIVED, not trusted from the row

That last line is deliberate: asserting a **shape** rather than a literal means
the test cannot pass on a trusted-from-the-row value.

## 8. Server-stamped fields must be proven un-spoofable

Where the server sets identity or provenance, send a hostile value and assert it
was discarded.

**Real check:** a caller-supplied `recorded_by: 'SOMEONE-ELSE'` was discarded in
favour of the session's `employee_id`. Same for `verified_by`, and for a caller
attempting to substitute the governing state on an Ohio-signed agreement.

## 9. Test the honest empty state, and distinguish it from a defect

Three states that must never collapse into each other:

- **not provisioned** — migration unrun → `{ ok: true, data: [], provisioned: false }`
- **provisioned and empty** — genuinely no rows
- **broken** — an error, surfaced as one

**Incident:** SAIRNcode's `sc_pctc` gate returned "not in your reference" on
every code and looked like a defect. Seeding two rows flipped it to correct
answers immediately — it was working. The same method proved the opposite on
StoneDesk's Slabs panel, where an empty store rendered **8 invented slabs** and
computed four KPIs from them.

**Seed one real record and re-run before reporting either verdict.**

## 10. Never invent a status code, a latency or an SLA

If the expected code is not read from the handler, do not assert it — go read
the branch. A test asserting a fabricated contract will pass once and mislead
forever.

## 11. Say what the suite does NOT cover

**Real disclosure from a stubbed suite:** *"these tables need
`sql/sairndental_credentials_schema.sql` run in Supabase, which this session has
no access to do. This file is a SUBSTITUTE for the live write/read-back, not a
replacement — the live round trip still has to be run."*

That sentence is the standard. A suite that does not state its own boundary
invites someone to read "24 passed" as "the feature works in production".

---

## Before calling an endpoint done

- [ ] Real signed session; `license_hash` derived, not borrowed
- [ ] Full role ladder asserted, including no-session
- [ ] Every refusal asserts the store is unchanged
- [ ] New tests mutation-checked against the pre-fix commit
- [ ] Storage-shape changes proven with a **real** write and read-back
- [ ] Append-only proven from the outbound request, not the response
- [ ] Server-stamped fields proven un-spoofable
- [ ] Empty vs unprovisioned vs broken kept distinct
- [ ] Coverage boundary written down
