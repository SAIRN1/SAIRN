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

  const admin = require('firebase-admin');
  // A cold-started sibling serverless invocation could have already
  // initialized the default app in this same runtime -- reuse it instead of
  // throwing on a duplicate-app-name error.
  _app = admin.apps && admin.apps.length
    ? admin.app()
    : admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
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
  const admin = require('firebase-admin');
  return admin.auth(app).createCustomToken(uid);
}

module.exports = { mintCustomToken };
