// api/sairncash/trial-start.js
// Creates a real, server-authoritative 30-day trial -- no Stripe
// dependency (Michael's 2026-08-18 decision). One trial per email;
// the only anti-abuse control in v1 (confirmed acceptable by Michael --
// renewal is admin-approval-gated anyway, see trial-renew.js).
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// REQUIRES migration: sql/sairncash_trial_schema.sql.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

const crypto = require('crypto');
const { computeExpiry } = require('../_lib/sairncash-trial.js');

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const email = req.body && req.body.email;
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    res.status(400).json({ error: { message: 'Valid email required' } });
    return;
  }

  // ── THE RETRY KEY. Item 6, 2026-09-14. ──────────────────────────────────
  // The ROW could never duplicate -- email is UNIQUE and the 409 below is
  // handled. The REQUEST was not idempotent: trial_token is minted here and
  // returned only on the 200 path, so a lost response meant the retry got
  // ALREADY_EXISTS and the caller never received the token that was minted.
  // The trial existed on the server and was unreachable by the person it
  // belonged to, which is what the ALREADY_EXISTS message anticipates when it
  // says "Contact support if you need help accessing it."
  //
  // OPTIONAL, BECAUSE THIS IS A PUBLIC ENDPOINT WITH LIVE CALLERS. A caller
  // that sends no key behaves exactly as before, 409 and all. Requiring it
  // would break every existing client to fix a failure they may never hit.
  //
  // AND IT IS A KEY RATHER THAN "JUST RETURN THE TOKEN ON 409", which is the
  // fix public-complaint-submit.js uses and which would be a CREDENTIAL
  // DISCLOSURE here. That endpoint keys on a hash of the patient name and the
  // message -- content only the submitter had. This one is unauthenticated,
  // `Access-Control-Allow-Origin: *`, and its only input is an email address:
  // returning the trial token to anyone who posts an email would hand a
  // stranger somebody else's trial.
  const idemRaw = req.body && req.body.idempotency_key;
  let idemHash = null;
  if (idemRaw !== undefined && idemRaw !== null && idemRaw !== '') {
    // A guessable key reintroduces exactly the hole this avoids, so a short or
    // malformed one is REFUSED rather than quietly ignored -- silently
    // dropping it would leave the caller believing their retry is protected.
    if (typeof idemRaw !== 'string' || !/^[A-Za-z0-9_-]{24,128}$/.test(idemRaw)) {
      res.status(400).json({ error: { code: 'BAD_IDEMPOTENCY_KEY',
        message: 'idempotency_key must be 24-128 characters of [A-Za-z0-9_-]. It is optional, but a short or guessable one would let somebody else retrieve this trial, so it is refused rather than ignored.' } });
      return;
    }
    idemHash = crypto.createHash('sha256').update(idemRaw).digest('hex');
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }

  try {
    const trialToken = crypto.randomBytes(32).toString('hex');
    const startedAt = Date.now();
    const expiresAt = computeExpiry(startedAt);

    const r = await fetch(SUPABASE_URL + '/rest/v1/sairncash_trial', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal'
      },
      // THE COLUMN IS ADDED ONLY WHEN THERE IS A KEY, and that is not tidiness.
      // PostgREST rejects an UNKNOWN COLUMN with 400 -- so sending
      // `idempotency_key_hash: null` before sql/sairncash_trial_idempotency_
      // 2026-09-14.sql has run would break EVERY trial start, including the
      // callers who never asked for this. Two files, one change, one deployed:
      // Guardian check 29's shape exactly, and the deploy order here is code
      // first, migration second, so the code has to work without it.
      body: JSON.stringify(Object.assign({
        email: email,
        trial_token: trialToken,
        started_at: new Date(startedAt).toISOString(),
        expires_at: expiresAt
      }, idemHash ? { idempotency_key_hash: idemHash } : {}))
    });

    if (r.status === 404) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Trial table not set up yet -- run sql/sairncash_trial_schema.sql in Supabase first.' } });
      return;
    }
    if (r.status === 409) {
      // ── THE RETRY PATH ───────────────────────────────────────────────────
      // A 409 means the row already exists. Only a caller who can produce the
      // SAME idempotency key gets the token back; everyone else gets exactly
      // what they got before. That distinction is the whole security argument
      // for a key rather than an email lookup.
      if (idemHash) {
        const look = await fetch(SUPABASE_URL + '/rest/v1/sairncash_trial'
          + '?email=eq.' + encodeURIComponent(email)
          + '&idempotency_key_hash=eq.' + encodeURIComponent(idemHash)
          + '&select=trial_token,expires_at&limit=1', {
          headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY }
        });
        // A FAILED LOOKUP IS NOT "NO MATCH". Falling through to ALREADY_EXISTS
        // on a 500 would tell a legitimate retry its key was wrong, which is a
        // different and misleading answer. 502 says try again, which is true.
        if (!look.ok) {
          // 404 is the one exception and it is not an outage: the column does
          // not exist yet because the migration has not been run. Say which.
          const body = await look.text().catch(() => '');
          if (look.status === 404 || /idempotency_key_hash/.test(body)) {
            res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Retry-safe trial start is not set up yet -- run sql/sairncash_trial_idempotency_2026-09-14.sql. The trial itself already exists; this request was not able to return its token.' } });
            return;
          }
          console.error('SAIRNcash trial-start idempotent lookup failed:', look.status, body);
          res.status(502).json({ error: { message: 'Could not confirm an existing trial -- try again' } });
          return;
        }
        const rows = await look.json().catch(() => null);
        if (Array.isArray(rows) && rows[0] && rows[0].trial_token) {
          // THE SAME ANSWER THE FIRST ATTEMPT WOULD HAVE GIVEN. Not a new
          // token: minting one here would rotate the credential out from under
          // a first response that may yet arrive.
          res.status(200).json({ trialToken: rows[0].trial_token, expiresAt: rows[0].expires_at, retried: true });
          return;
        }
      }
      res.status(409).json({ error: { code: 'ALREADY_EXISTS', message: 'This email already has a SAIRNcash trial. Contact support if you need help accessing it.' } });
      return;
    }
    if (!r.ok) {
      const bodyText = await r.text().catch(() => '');
      // A COLUMN THAT DOES NOT EXIST IS NOT AN OUTAGE, and it is reachable only
      // for a caller who sent a key: PostgREST answers an unknown column with
      // 400, which would otherwise read as "could not start trial -- try again"
      // forever. Naming the migration is the difference between a five-minute
      // fix and a hunt. Same distinction sd-data.js draws between a missing
      // table and a refused row.
      if (idemHash && /idempotency_key_hash/.test(bodyText)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Retry-safe trial start is not set up yet -- run sql/sairncash_trial_idempotency_2026-09-14.sql in Supabase. Retry without idempotency_key to start a trial the old way.' } });
        return;
      }
      console.error('SAIRNcash trial-start insert failed:', r.status, bodyText);
      res.status(502).json({ error: { message: 'Could not start trial -- try again' } });
      return;
    }

    res.status(200).json({ trialToken: trialToken, expiresAt: expiresAt });
  } catch (e) {
    console.error('SAIRNcash trial-start error:', e.message);
    res.status(502).json({ error: { message: 'Could not start trial -- try again' } });
  }
};
