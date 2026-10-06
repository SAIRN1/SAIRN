// api/_lib/firebase-admin.js
// ---------------------------------------------------------------------------
// Mints Firebase custom auth tokens for SAIRNcash, scoped to the caller's
// real server-verified customerId (trial row uuid or Stripe customer id).
//
// WHY THIS EXISTS: SAIRNcash's Realtime Database sync (income/deductions/
// profile/chat, all under sairncash/customers/{customerId}/) had no Firebase
// Authentication step at all -- every read/write hit the RTDB unauthenticated,
// which is why turning on real security rules immediately produced
// PERMISSION_DENIED on every write (found live 2026-08-19). The two
// alternatives were (a) rules that trust an unguessable customerId in the
// path with no real auth check, or (b) real auth -- Michael's confirmed
// choice was (b). This is that: a signed-in Firebase user whose uid equals
// customerId, so RTDB rules can check `auth.uid === $customerId` for real,
// not just "hope nobody guesses the id."
//
// Uses the official firebase-admin SDK (audited library) rather than
// hand-rolling the JWT signing custom tokens require -- same precedent this
// repo's package.json already set for @simplewebauthn/server: security-
// critical crypto goes through an audited library, not custom code.
//
// REQUIRES env: SAIRNCASH_FIREBASE_SERVICE_ACCOUNT -- the full service-
// account JSON for the sarintype-6e070 Firebase project (Firebase Console ->
// Project Settings -> Service Accounts -> Generate new private key), pasted
// as-is as the env var's value. This is a SEPARATE credential from the
// SAIRNCASH_FIREBASE_* client config vars (those are public, safe in browser
// JS; this one is a private server secret, never sent to the client).
//
// Lazy singleton: only initializes firebase-admin on first real call, so an
// unrelated SAIRNcash endpoint (or another app's serverless function in this
// shared Vercel project) never pays the init cost or fails on a missing env
// var it doesn't need.
//
// ---------------------------------------------------------------------------
// PORTED TO THE MODULAR ENTRY POINTS, 2026-10-06. WHY, AND WHAT IT UNBLOCKS.
//
// This file used the LEGACY NAMESPACE -- admin.apps, admin.app(),
// admin.credential.cert, admin.auth(), admin.database(). firebase-admin v13
// REMOVED that namespace: at 14.5.0 `require('firebase-admin')` IS the modular
// `firebase-admin/app` surface and exports only cert, initializeApp, getApp,
// getApps, deleteApp and errors. Measured side by side:
//
//     admin.credential  12.7.0 object    14.5.0 undefined
//     admin.auth        12.7.0 function  14.5.0 undefined
//     admin.apps        12.7.0 object    14.5.0 undefined
//     admin.app         12.7.0 function  14.5.0 undefined
//     admin.database    12.7.0 function  14.5.0 undefined
//     admin.initializeApp        function          function   <- the survivor
//
// ALL THREE EXPORTED FUNCTIONS BROKE, not just the minting one, and
// `initializeApp` surviving is what made it invisible to a load-and-list smoke
// test. `tools/dep_surface_check.py --package firebase-admin --version 14.5.0`
// reproduces it mechanically: 2 of 11 named symbol paths resolved before this
// port.
//
// THE SUBPATHS EXIST IN BOTH VERSIONS, which is the only reason this port is
// safe to land while package.json still pins ^12.7.0. Verified by loading
// them, 2026-10-06: `firebase-admin/app` gives initializeApp, getApp, getApps,
// cert, deleteApp as functions and `firebase-admin/auth`.getAuth and
// `firebase-admin/database`.getDatabase are functions, IDENTICALLY under
// 12.7.0 and under 14.5.0.
//
// THIS PORT DOES NOT UPGRADE ANYTHING. package.json is unchanged. It clears
// trigger 1 of the four recorded in docs/2026-10-05-dependabot-high-triage.md:
// *"api/_lib/firebase-admin.js is ported to the modular API -- that is what
// unblocks 14.5.0"*. The upgrade decision stays where addendum 3 left it until
// somebody takes that decision deliberately.
//
// The requires stay INSIDE the functions. That is the lazy-singleton property
// stated above, and hoisting them to module scope would quietly undo it.
// ---------------------------------------------------------------------------

let _app = null;

function getAdminApp() {
  if (_app) return _app;

  const raw = process.env.SAIRNCASH_FIREBASE_SERVICE_ACCOUNT;
  if (!raw) {
    const e = new Error('SAIRNCASH_FIREBASE_SERVICE_ACCOUNT not set in environment');
    e.code = 'CONFIG';
    throw e;
  }

  let serviceAccount;
  try {
    serviceAccount = JSON.parse(raw);
  } catch (err) {
    const e = new Error('SAIRNCASH_FIREBASE_SERVICE_ACCOUNT is not valid JSON: ' + err.message);
    e.code = 'CONFIG';
    throw e;
  }

  // MODULAR ENTRY POINTS, not the legacy namespace -- see the block at the
  // foot of this header. Still required INSIDE the function, deliberately:
  // the lazy-singleton property above is why, and importing at module scope
  // would make every unrelated SAIRNcash endpoint pay the SDK load.
  const { initializeApp, getApp, getApps, cert } = require('firebase-admin/app');
  // A cold-started sibling serverless invocation could have already
  // initialized the default app in this same runtime -- reuse it instead of
  // throwing on a duplicate-app-name error.
  _app = getApps().length
    ? getApp()
    : initializeApp({ credential: cert(serviceAccount) });
  return _app;
}

// uid is always customerId (trial row uuid or Stripe customer id) -- never
// anything client-supplied or free-form, so the resulting token's uid can be
// trusted by RTDB rules as exactly "the customer this request already proved
// ownership of via a real trial/license check higher up the call stack."
// Throws (rather than returning null) on any failure so callers can decide
// how to surface it -- minting is expected to succeed whenever it's called
// with a real customerId; a failure here is a real operational problem
// (bad/missing credential, Firebase outage), not a normal "not found" case.
async function mintCustomToken(uid) {
  if (!uid || typeof uid !== 'string') {
    throw new Error('mintCustomToken requires a real customerId string');
  }
  const app = getAdminApp();
  const { getAuth } = require('firebase-admin/auth');
  return getAuth(app).createCustomToken(uid);
}

// ---------------------------------------------------------------------------
// REALTIME DATABASE ACCESS (added 2026-09-01 for api/sairncash/stripe-webhook.js)
//
// A SEPARATE, NAMED ADMIN APP, deliberately. getAdminApp() above initialises
// with credentials only and no databaseURL, and it may also REUSE a default app
// that a sibling serverless invocation created in the same runtime -- so it
// cannot be assumed to carry a database URL, and retrofitting one onto an
// already-initialised app is not possible. Initialising our own named app
// avoids the question entirely and leaves the token-minting path untouched.
//
// REQUIRES env: SAIRNCASH_FIREBASE_DATABASE_URL (already served to the client
// by api/sairncash/firebase-config.js, so it is the same value, not a new one)
// plus the same SAIRNCASH_FIREBASE_SERVICE_ACCOUNT the minting path uses.
const DB_APP_NAME = 'sairncash-db';
let _dbApp = null;

function getDbApp() {
  if (_dbApp) return _dbApp;
  const raw = process.env.SAIRNCASH_FIREBASE_SERVICE_ACCOUNT;
  const databaseURL = process.env.SAIRNCASH_FIREBASE_DATABASE_URL;
  if (!raw || !databaseURL) {
    const e = new Error('SAIRNCASH_FIREBASE_SERVICE_ACCOUNT / SAIRNCASH_FIREBASE_DATABASE_URL not set in environment');
    e.code = 'CONFIG';
    throw e;
  }
  let serviceAccount;
  try {
    serviceAccount = JSON.parse(raw);
  } catch (err) {
    const e = new Error('SAIRNCASH_FIREBASE_SERVICE_ACCOUNT is not valid JSON: ' + err.message);
    e.code = 'CONFIG';
    throw e;
  }
  const { initializeApp, getApps, cert } = require('firebase-admin/app');
  const existing = getApps().filter(Boolean).find(function (a) { return a.name === DB_APP_NAME; });
  _dbApp = existing || initializeApp(
    { credential: cert(serviceAccount), databaseURL: databaseURL },
    DB_APP_NAME
  );
  return _dbApp;
}

// Merge-writes an object at an RTDB path. update() rather than set() so a
// write touching one field cannot silently erase a sibling written by a
// different code path.
async function rtdbUpdate(path, value) {
  if (!path || typeof path !== 'string') throw new Error('rtdbUpdate requires a path');
  const { getDatabase } = require('firebase-admin/database');
  await getDatabase(getDbApp()).ref(path).update(value);
}

async function rtdbGet(path) {
  if (!path || typeof path !== 'string') throw new Error('rtdbGet requires a path');
  const { getDatabase } = require('firebase-admin/database');
  const snap = await getDatabase(getDbApp()).ref(path).once('value');
  return snap.val();
}

module.exports = { mintCustomToken, rtdbUpdate, rtdbGet };
