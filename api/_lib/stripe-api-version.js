// api/_lib/stripe-api-version.js
// ---------------------------------------------------------------------------
// ONE PINNED STRIPE API VERSION, FOR EVERY `new Stripe(...)` ON THE PLATFORM.
//
// ── WHY THIS EXISTS (2026-09-15) ───────────────────────────────────────────
// All five production call sites constructed `new Stripe(stripeKey)` with NO
// apiVersion, which means each one silently inherits whatever version the
// INSTALLED SDK happens to default to. `package.json` carries `"stripe":
// "^17.4.0"`, so the installed SDK is "whatever the latest 17.x is at build
// time" -- a moving target that Vercel resolves fresh on every deploy.
//
// The consequence is the part worth reading: bumping the SDK is not one
// change, it is two. The library moves AND the wire format of every request
// moves with it -- different response shapes, different required fields,
// different expansion behaviour -- on the endpoints that take a customer's
// money. Only one of those two changes appears in the diff. A reviewer reading
// "stripe ^17 -> ^22" sees a dependency bump; what actually shipped is a
// dependency bump plus an API migration nobody wrote down.
//
// ── THE VALUE IS MEASURED, NOT REMEMBERED ─────────────────────────────────
// Taken from the SDK this repo actually resolves to, read out of the package
// rather than recalled:
//
//     npm pack stripe@17.7.0
//     package/cjs/apiVersion.js:  exports.ApiVersion = '2025-02-24.acacia';
//
// So this pin is a NO-OP TODAY, deliberately. It changes nothing about what
// the five endpoints send right now; it only stops the wire format from moving
// on its own the next time somebody touches package.json. A pin whose value
// had been guessed would have been a silent API migration of its own, which is
// the exact defect it is here to prevent.
//
// ── WHEN YOU UPGRADE THE SDK ──────────────────────────────────────────────
// Do the two halves separately and in this order:
//   1. Bump the SDK with this pin left ALONE. Nothing about the wire format
//      changes, so the diff is a real dependency bump and nothing else.
//   2. Then move this constant, as its own commit, with the Stripe changelog
//      entries for every version crossed read and the affected calls checked.
// Doing both at once is the thing this file exists to make impossible to do by
// accident.
//
// Held by api/_lib/stripe-api-version.test.js, which fails if any
// `new Stripe(` in api/ is constructed without an apiVersion -- because a
// SIXTH call site added later would otherwise reintroduce the defect silently
// and this constant would sit here looking like it was doing something.

'use strict';

const STRIPE_API_VERSION = '2025-02-24.acacia';

module.exports = { STRIPE_API_VERSION };
