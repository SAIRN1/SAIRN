// api/sairndental/public-complaint-submit.js
// Genuinely public, unauthenticated endpoint -- no license key
// anywhere in this file, same category as public-book.js/
// public-availability.js. Creates a new dnt_complaints thread and
// returns the one-time access_token the patient must save to
// view/reply later -- there is no recovery path if it's lost (design
// spec §0, disclosed, not a bug).

const crypto = require('crypto');
const { resolveSlug, checkAndIncrementRateLimit } = require('../_lib/dental-public');

function supabaseHeaders(extra) {
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return Object.assign({ apikey: SERVICE_KEY, Authorization: 'Bearer ' + SERVICE_KEY, 'Content-Type': 'application/json' }, extra || {});
}
function rest(path) {
  return process.env.SUPABASE_URL + '/rest/v1/' + path;
}
function newId(prefix) {
  return prefix + '-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
}
const MAX_MESSAGE_LEN = 4000;

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.status(204).end(); return; }
  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) { res.status(500).json({ error: { message: 'Server configuration error' } }); return; }

  const body = req.body || {};
  const slug = body.slug;
  const message = typeof body.message === 'string' ? body.message.trim() : '';
  const patientName = typeof body.patient_name === 'string' ? body.patient_name.trim() : '';
  if (!slug || !message) { res.status(400).json({ error: { message: 'slug and message are required' } }); return; }
  if (message.length > MAX_MESSAGE_LEN) { res.status(400).json({ error: { code: 'MESSAGE_TOO_LONG', message: 'Message is too long -- please keep it under ' + MAX_MESSAGE_LEN + ' characters' } }); return; }

  try {
    const rl = await checkAndIncrementRateLimit(req, 60, 5, 'complaint-submit'); // 5 submissions per hour per IP
    // A store we could not reach is NOT the same answer as a limit that was
    // exceeded. Saying "too many requests" for an unreachable database is a
    // wrong reason given confidently, and it hides an outage as user error.
    if (rl.unavailable) {
      console.error('SAIRNdental public-complaint-submit: rate-limit store unavailable -- refusing rather than allowing an uncounted request');
      res.status(503).json({ error: { code: 'UNAVAILABLE', message: 'Temporarily unavailable -- please call the office or try again shortly' } });
      return;
    }
    if (!rl.allowed) { res.status(429).json({ error: { code: 'RATE_LIMITED', message: 'Too many attempts -- please call the office or try again later' } }); return; }

    const licenseHash = await resolveSlug(slug);
    if (!licenseHash) { res.status(404).json({ error: { code: 'UNKNOWN_SLUG', message: 'Practice link not found' } }); return; }

    // ── IDEMPOTENT ON THE SUBMISSION, NOT ON THE REQUEST (2026-09-13) ────
    // A public form is retried by a double-click, by a browser resubmitting on
    // a slow response, and by a patient who saw no confirmation. Every one of
    // those filed a SECOND complaint, and the practice then had two records of
    // one grievance with the same first message -- which reads as two unhappy
    // patients and gets two replies.
    //
    // KEYED ON THE BUSINESS EVENT, the same choice api/ledger.js makes: the
    // practice, the patient's name and the message text. NOT on a caller-
    // supplied header -- a public form has no client code to send one, and a
    // key the caller invents is a key the caller can vary on a retry, which is
    // exactly the case this exists for.
    //
    // CHECKED AGAINST THE TABLE, never an in-memory map: this runs serverless,
    // so a second request is a second process and anything held in memory is
    // already gone. That distinction is the whole shape of the defect --
    // docs/2026-09-13-cross-domain-disciplines.md.
    //
    // THE WINDOW IS BOUNDED AT 10 MINUTES on purpose. A patient who writes the
    // same sentence a week later has a NEW complaint and must not be silently
    // folded into the old one; a duplicate within ten minutes is a retry.
    const submissionKey = crypto.createHash('sha256')
      .update(licenseHash + '\x00' + patientName + '\x00' + message)   // NUL delimiter,
      // written as an ESCAPE and never as a raw byte: a raw NUL makes the file
      // read as binary to grep and invisible to review, which is the control-char
      // defect this repo records. NUL rather than a space because a space can
      // occur in a name or a message, and 'ab'+'c' would then hash the same as
      // 'a'+'bc' -- a delimiter that cannot appear in the input cannot collide.
      .digest('hex');
    const sinceISO = new Date(Date.now() - 10 * 60 * 1000).toISOString();
    const dupRes = await fetch(rest('dnt_complaints?license_hash=eq.' + encodeURIComponent(licenseHash) +
      '&submission_key=eq.' + submissionKey +
      '&updated_at=gte.' + encodeURIComponent(sinceISO) +
      '&select=complaint_id,access_token&limit=1'), { headers: supabaseHeaders() });
    if (dupRes.ok) {
      const dupRows = await dupRes.json().catch(function () { return null; });
      if (Array.isArray(dupRows) && dupRows[0]) {
        // The SAME answer the original submission got. A patient who clicked
        // twice must see their complaint, not an error about clicking twice.
        res.status(200).json({ ok: true, duplicate_of_recent: true,
                               complaint_id: dupRows[0].complaint_id,
                               access_token: dupRows[0].access_token });
        return;
      }
    } else if (dupRes.status !== 404 && dupRes.status !== 400) {
      // REFUSE RATHER THAN FILE UNCHECKED. A failed duplicate check is not the
      // same answer as "no duplicate", and treating it as one is how a retry
      // storm becomes a duplicate storm.
      //
      // 404/400 means the column is not there yet, and this branch lets that
      // case fall through to the insert. ⚠ FALLING THROUGH IS NOT THE SAME AS
      // SUCCEEDING, and this comment claimed it was until 2026-09-17: it said
      // the case was "handled below by simply proceeding". IT IS NOT. The
      // insert below carries submission_key, PostgREST rejects an unknown
      // column outright, and the request ends as a 503 -- so before
      // sql/sairndental_complaint_idempotency_2026-09-13.sql has run, THIS
      // ENDPOINT REFUSES EVERY COMPLAINT. Fail-closed rather than silent, but
      // the public form is down, and the 503 below now says which of the two
      // things is missing instead of blaming the table.
      console.error('SAIRNdental public-complaint-submit: duplicate check failed, HTTP',
                    dupRes.status, '-- refusing rather than filing unchecked');
      res.status(503).json({ error: { code: 'UNAVAILABLE', message: 'Temporarily unavailable -- please call the office or try again shortly' } });
      return;
    }

    const complaintId = newId('COMP');
    const accessToken = crypto.randomBytes(32).toString('hex');
    const nowISO = new Date().toISOString();
    const data = {
      id: complaintId, patient_name: patientName, status: 'New',
      messages: [{ from: 'patient', text: message, at: nowISO }],
      created_at: nowISO.slice(0, 10)
    };

    const insertRes = await fetch(rest('dnt_complaints'), {
      method: 'POST',
      headers: Object.assign({}, supabaseHeaders(), { Prefer: 'return=representation' }),
      body: JSON.stringify({
        license_hash: licenseHash, app_id: 'sairndental', complaint_id: complaintId,
        access_token: accessToken, data: data, updated_at: nowISO,
        // Written even before the column exists: PostgREST rejects an unknown
        // column outright, so this is NOT a silent no-op -- the 400 is handled
        // above and surfaces as NOT_PROVISIONED rather than a quiet success.
        submission_key: submissionKey
      })
    });
    if (insertRes.status === 404 || insertRes.status === 400) {
      const bodyText = await insertRes.text().catch(function () { return ''; });
      // TWO DIFFERENT MISSING THINGS, AND THEY WERE ANSWERED WITH ONE MESSAGE
      // UNTIL 2026-09-17. `/does not exist/i` matches BOTH "relation
      // dnt_complaints does not exist" (42P01, no table) and "column
      // submission_key of relation dnt_complaints does not exist" (42703,
      // table is fine, one column is missing). Both returned "complaint tables
      // are not set up yet", which sends whoever reads the support ticket at
      // the wrong file: the table has existed for months and what is actually
      // missing is one ALTER TABLE.
      //
      // The column case is tested FIRST because its text contains the table
      // case's text -- ordering these the other way round would make the
      // specific branch unreachable.
      if (/column\b/i.test(bodyText) && /does not exist/i.test(bodyText)) {
        console.error('SAIRNdental public-complaint-submit: the idempotency COLUMN is missing --',
                      'run sql/sairndental_complaint_idempotency_2026-09-13.sql.', bodyText);
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental complaint intake is not finished being set up -- the table exists but one column is missing. Run sql/sairndental_complaint_idempotency_2026-09-13.sql.' } });
        return;
      }
      if (/does not exist/i.test(bodyText)) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental complaint tables are not set up yet.' } });
        return;
      }
      console.error('SAIRNdental public-complaint-submit insert error:', bodyText);
      res.status(502).json({ error: { message: 'Could not submit -- try again' } });
      return;
    }
    if (!insertRes.ok) {
      const errBody = await insertRes.json().catch(() => null);
      console.error('SAIRNdental public-complaint-submit insert error:', errBody);
      res.status(502).json({ error: { message: 'Could not submit -- try again' } });
      return;
    }

    res.status(200).json({ ok: true, token: accessToken });
  } catch (err) {
    console.error('SAIRNdental public-complaint-submit error:', err.message);
    res.status(502).json({ error: { message: 'Could not submit -- try again' } });
  }
};
