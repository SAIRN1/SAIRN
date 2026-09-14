// api/sairncash/trial-renew.js
// Admin-only: grants the next real 30-day trial window. Gated by
// Authorization: Bearer SAIRNCASH_ADMIN_SECRET, same shape as
// api/sairndental/send-reminder.js's CRON_SECRET gate -- fails closed
// (500) if the env var itself is unset, 401 if the header is
// missing/wrong. Never callable from sairncash.html; confirmed by
// Michael 2026-08-18 that renewal is a manual-approval action, not
// self-service -- this is the only write path that can extend
// expires_at.
//
// Sets a fresh 30-day window from the moment of approval (not
// additive -- doesn't stack onto whatever time was left).
//
// REQUIRES env: SAIRNCASH_ADMIN_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// See docs/superpowers/specs/2026-08-18-sairncash-trial-flow-design.md.

const { computeExpiry } = require('../_lib/sairncash-trial.js');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'POST only' } });
    return;
  }
  if (!process.env.SAIRNCASH_ADMIN_SECRET) {
    console.error('SAIRNCASH_ADMIN_SECRET not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }
  if (req.headers.authorization !== 'Bearer ' + process.env.SAIRNCASH_ADMIN_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }

  const email = req.body && req.body.email;
  const note = (req.body && req.body.note) || null;
  if (!email) {
    res.status(400).json({ error: { message: 'Missing email' } });
    return;
  }

  // -- THE RETRY KEY. Item 6, 2026-09-14. --------------------------------
  // This handler SELECTs renewal_count, adds one in JavaScript, and PATCHes it
  // back with a fresh expires_at computed from NOW. If the PATCH commits and
  // the response is lost, the retry reads the already-incremented value and
  // writes a SECOND new 30-day window -- one approval, two extensions, on the
  // only write path that can extend expires_at at all.
  //
  // OPTIONAL, because there are live admin callers. Without a key the
  // behaviour is what it was, double-extend-on-retry included; requiring one
  // would break every existing caller to fix a failure they may not hit.
  //
  // NOT HASHED, unlike trial-start's key, and the difference is the reason
  // rather than the shape: that endpoint is PUBLIC and holding its key
  // retrieves a trial token, so the key is a credential. This one is behind
  // the admin bearer and retrieves only the expiry of a renewal the caller
  // just performed.
  const renewKey = req.body && req.body.idempotency_key;
  if (renewKey !== undefined && renewKey !== null && renewKey !== '') {
    // Refused rather than ignored: an admin who sends a malformed key and gets
    // a 200 would believe the retry is protected when it is not.
    if (typeof renewKey !== 'string' || !/^[A-Za-z0-9_.:-]{16,128}$/.test(renewKey)) {
      res.status(400).json({ error: { code: 'BAD_IDEMPOTENCY_KEY',
        message: 'idempotency_key must be 16-128 characters of [A-Za-z0-9_.:-]. It is optional; a malformed one is refused rather than ignored, because an approval retried without protection extends the trial twice.' } });
      return;
    }
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }

  try {
    const lookupR = await fetch(
      // THE EXTRA COLUMN IS ONLY ASKED FOR WHEN THERE IS A KEY, for the same
      // reason the PATCH only sends it: PostgREST answers an unknown column in
      // `select=` with a 400, so asking unconditionally would break EVERY
      // renewal until the migration ran. `expires_at` is asked for always --
      // it already exists, and the retry branch needs it.
      SUPABASE_URL + '/rest/v1/sairncash_trial?email=eq.' + encodeURIComponent(email)
        + '&select=renewal_count,expires_at'
        + (renewKey ? ',renew_idempotency_key' : ''),
      { headers: { apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY } }
    );
    if (!lookupR.ok) {
      const lookText = await lookupR.text().catch(() => '');
      if (renewKey && /renew_idempotency_key/.test(lookText)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Retry-safe renewal is not set up yet -- run sql/sairncash_trial_renew_idempotency_2026-09-14.sql in Supabase. Retry without idempotency_key to renew the old way.' } });
        return;
      }
      res.status(502).json({ error: { message: 'Could not look up trial' } });
      return;
    }
    const rows = await lookupR.json();
    if (!rows || rows.length === 0) {
      res.status(404).json({ error: { message: 'No trial found for that email' } });
      return;
    }

    // THE RETRY, RECOGNISED BEFORE ANYTHING IS COMPUTED. If this row already
    // carries the key we were sent, this exact approval has already been
    // applied: return the expiry it produced. Minting a new one would be the
    // double extension, and it would look like a success.
    if (renewKey && rows[0].renew_idempotency_key === renewKey) {
      res.status(200).json({
        ok: true, expiresAt: rows[0].expires_at,
        renewalCount: rows[0].renewal_count, retried: true
      });
      return;
    }

    const now = Date.now();
    const expiresAt = computeExpiry(now);
    const priorCount = rows[0].renewal_count || 0;
    const nextRenewalCount = priorCount + 1;

    const patchR = await fetch(
      // THE COMPARE-AND-SET, and it closes a DIFFERENT failure from the key
      // above. `renewal_count=eq.<what we read>` means a writer whose read has
      // gone stale matches ZERO rows instead of overwriting the other one's
      // increment. The key cannot do this: two genuinely different approvals
      // carry different keys and both are legitimate, so only the count can
      // tell a racing writer it lost.
      //
      // `is.null` is how PostgREST spells "= NULL" -- an untouched row has a
      // NULL count and `renewal_count=eq.0` would match nothing, which would
      // make the FIRST renewal of every trial fail.
      SUPABASE_URL + '/rest/v1/sairncash_trial?email=eq.' + encodeURIComponent(email)
        + '&renewal_count=' + (rows[0].renewal_count === null
                               || rows[0].renewal_count === undefined
                               ? 'is.null' : 'eq.' + priorCount),
      {
        method: 'PATCH',
        headers: {
          apikey: SERVICE_KEY,
          Authorization: 'Bearer ' + SERVICE_KEY,
          'Content-Type': 'application/json',
          // return=representation, NOT minimal: the compare-and-set below is
          // only observable as a ROW COUNT, and `minimal` returns no body to
          // count. A CAS nobody can read the result of is not a CAS.
          Prefer: 'return=representation'
        },
        // THE COLUMN IS SENT ONLY WHEN THERE IS A KEY. PostgREST answers an
        // unknown column with 400, so sending it unconditionally would break
        // EVERY renewal until the migration ran -- including admins who never
        // asked for this. Guardian check 29's two-files-one-change shape.
        body: JSON.stringify(Object.assign({
          status: 'active',
          expires_at: expiresAt,
          renewal_count: nextRenewalCount,
          last_renewed_at: new Date(now).toISOString(),
          last_renewed_note: note
        }, renewKey ? { renew_idempotency_key: renewKey } : {}))
      }
    );
    if (!patchR.ok) {
      const bodyText = await patchR.text().catch(() => '');
      // An unknown column is not an outage, and it is reachable only for a
      // caller who sent a key. Name the migration rather than telling an admin
      // to try again forever.
      if (renewKey && /renew_idempotency_key/.test(bodyText)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Retry-safe renewal is not set up yet -- run sql/sairncash_trial_renew_idempotency_2026-09-14.sql in Supabase. Retry without idempotency_key to renew the old way.' } });
        return;
      }
      console.error('SAIRNcash trial-renew patch failed:', patchR.status, bodyText);
      res.status(502).json({ error: { message: 'Could not renew trial' } });
      return;
    }

    // ZERO ROWS BACK IS HOW THE LOSER OF THE COMPARE-AND-SET FINDS OUT, and it
    // arrives as a 200. Without this check a stale writer would be told its
    // renewal succeeded while nothing was written -- a false success, which is
    // the shape this whole sweep is about. `return=representation` is required
    // for the row count to be visible at all.
    const patched = await patchR.json().catch(() => null);
    if (Array.isArray(patched) && patched.length === 0) {
      res.status(409).json({ error: { code: 'CONCURRENT_RENEWAL',
        message: 'This trial was renewed by someone else while this request was in flight, so nothing was written. Re-read the trial and decide whether it still needs renewing -- retrying blindly would extend it twice.' } });
      return;
    }

    res.status(200).json({ ok: true, expiresAt: expiresAt, renewalCount: nextRenewalCount });
  } catch (e) {
    console.error('SAIRNcash trial-renew error:', e.message);
    res.status(502).json({ error: { message: 'Could not renew trial' } });
  }
};
