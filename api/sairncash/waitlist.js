// api/sairncash/waitlist.js
// Real persistence for SAIRNcash's pre-launch waitlist -- replaces
// handleWaitlist()'s inherited fake success (showed "You're in!" and
// discarded the email, no fetch or storage call at all; found during the
// 2026-08-10 SAIRNcash pivot audit, same silent-failure class this
// platform's Guardian sweeps have caught repeatedly elsewhere).
//
// REQUIRES env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (already used by
// every other Supabase-backed api/*.js in this repo).
// REQUIRES migration: sql/sairncash_waitlist_schema.sql (not yet run).

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'POST only' } });
    return;
  }
  const email = req.body && req.body.email;
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    res.status(400).json({ error: { message: 'Valid email required' } });
    return;
  }
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in environment variables');
    res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    return;
  }
  try {
    const r = await fetch(SUPABASE_URL + '/rest/v1/sairncash_waitlist?on_conflict=email', {
      method: 'POST',
      headers: {
        apikey: SERVICE_KEY,
        Authorization: 'Bearer ' + SERVICE_KEY,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates'
      },
      body: JSON.stringify({ email: email })
    });
    if (r.status === 404 || r.status === 400) {
      res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'Waitlist table not set up yet -- run sql/sairncash_waitlist_schema.sql in Supabase first.' } });
      return;
    }
    if (!r.ok) {
      res.status(502).json({ error: { message: 'Could not join waitlist -- try again' } });
      return;
    }
    res.status(200).json({ ok: true });
  } catch (e) {
    console.error('SAIRNcash waitlist error:', e.message);
    res.status(502).json({ error: { message: 'Could not join waitlist -- try again' } });
  }
};
