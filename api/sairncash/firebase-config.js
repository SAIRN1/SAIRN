// api/sairncash/firebase-config.js
// Serves SAIRNcash's Firebase config for cross-device chat sync.
// Ported from ~/Downloads/SAIRNtype_PRO (1)/sairntype_stripe/api/firebase-config.js
// with one deliberate change: that original used bare, generic env var
// names (APP, DOMAIN, URL, ID, BUCKET, SENDER, APPid) -- dangerously
// collision-prone in this shared Vercel project (15+ apps, already bitten
// by resource/env-name collisions before, see api/claude.js's own header
// and multiple SAIRN-BACKLOG.md entries). Renamed to SAIRNCASH_FIREBASE_*
// here, matching this platform's convention of app-prefixed resource
// names. Not yet provisioned in this Vercel project as of 2026-08-10 --
// gracefully degrades to no sync (client already handles a null config),
// same pattern as every other optional-integration gap on this platform.

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  const apiKey = process.env.SAIRNCASH_FIREBASE_API_KEY;
  if (!apiKey) { res.status(200).json(null); return; }
  res.status(200).json({
    apiKey: apiKey,
    authDomain: process.env.SAIRNCASH_FIREBASE_AUTH_DOMAIN,
    databaseURL: process.env.SAIRNCASH_FIREBASE_DATABASE_URL,
    projectId: process.env.SAIRNCASH_FIREBASE_PROJECT_ID,
    storageBucket: process.env.SAIRNCASH_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.SAIRNCASH_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.SAIRNCASH_FIREBASE_APP_ID,
    measurementId: process.env.SAIRNCASH_FIREBASE_MEASUREMENT_ID
  });
};
