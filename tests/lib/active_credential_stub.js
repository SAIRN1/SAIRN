// tests/lib/active_credential_stub.js
//
// Wrap a test's `global.fetch` stub so the active-credential re-check can answer.
//
// ── WHY THIS EXISTS ────────────────────────────────────────────────────────
// api/sd-data.js gained an active-credential PRE-GATE on 2026-09-26: one
// credentialStillActive() at the dispatcher's entry point, covering all 133
// verifySessionToken gates instead of the 70 action-pairs the old per-resource
// placement reached. The re-check loads the caller's own row from that app's
// `*_employee_auth` table and refuses CREDENTIAL_INACTIVE when the row is
// ABSENT or `active !== true` -- because a deleted employee is exactly "no row",
// so an absent row cannot be treated as a pass.
//
// FIFTEEN SUITES BROKE, AND THE FIXTURES WERE THE THING THAT WAS WRONG. Their
// fetch stubs answer every GET with a generic row (`[{ data: { id: 'X-1' } }]`
// and similar), which has no `active` field -- so they were modelling an
// employee row that cannot exist in a real deployment, and the refusal was the
// correct response to it. Those suites are about resource gating, cross-tenant
// isolation and role scope; none of them is about the credential re-check, which
// has its own controls in api/sd-data-active-credential.test.js and eleven
// driven arms in api/_lib/auth.test.js.
//
// SO THIS ANSWERS ONLY THE EMPLOYEE-AUTH READ, AND PASSES EVERYTHING ELSE
// THROUGH UNTOUCHED. It is deliberately not a general-purpose fake: a helper
// that started answering other tables would let a suite pass on traffic its own
// stub never modelled, which is the failure the stubs exist to prevent.
//
// IT MODELS AN EMPLOYEE IN GOOD STANDING, which is the state every one of these
// suites means by "signed in". A suite that wants the DEACTIVATED state must not
// use this -- it should answer the read itself, which is what
// api/bridge-push-auth.test.js does for exactly that arm.

'use strict';

// The one table-name shape the re-check uses. Matching on the suffix rather than
// on a list of app names on purpose: a new app's table is covered the day it is
// added, and a list here would be a second copy of AUTH_TABLE_BY_APP.
const AUTH_TABLE = /_employee_auth\?/;

/**
 * wrapFetch(inner) -> fetch
 *
 * `arguments` forwarding, not a fixed signature, because the stubs it wraps are
 * written every shape there is in this directory: `async function ()` reading
 * nothing, `async function (url, init)`, and `async (url, init) => {}`. A wrapper
 * that declared `(url, init)` would silently drop a third argument from any stub
 * that grows one.
 */
function wrapFetch(inner) {
  return function () {
    const url = String(arguments.length ? arguments[0] : '');
    if (AUTH_TABLE.test(url)) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ([{ active: true }]),
        text: async () => '[{"active":true}]'
      });
    }
    return inner.apply(this, arguments);
  };
}

module.exports = { wrapFetch: wrapFetch, AUTH_TABLE: AUTH_TABLE };
