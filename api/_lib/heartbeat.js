// api/_lib/heartbeat.js
// ---------------------------------------------------------------------------
// THE ONE LINE A SCHEDULED JOB WRITES SO SOMETHING CAN NOTICE IT STOPPED.
// Item 54. Shared by every cron endpoint; see sql/cron_heartbeat_schema.sql.
//
//     const { beat } = require('./_lib/heartbeat');
//     await beat({ job: '/api/sairndental/send-reminder',
//                  outcome: 'ok', expected_interval_seconds: 3600,
//                  detail: summary });
//
// ── WHAT THIS IS FOR, SAID ACCURATELY ──────────────────────────────────────
// api/sairndental/send-reminder.js already logs `sweep complete -- scanned N,
// sent N, ...` on every run, and that line DOES distinguish a sweep that sent
// reminders from one that found nothing due. What no log can volunteer is its
// own ABSENCE: a cron that stops firing, times out, or 500s writes no line at
// all, and nothing searches a log for a thing that is not there.
//
// A heartbeat turns that into a positive fact somebody can query. It is not a
// replacement for the log line -- the log carries detail this row deliberately
// does not -- it is the thing that makes silence detectable.
//
// ── BEST-EFFORT, LIKE api/_lib/audit.js, AND FOR THE SAME REASON ───────────
// A failed heartbeat must never fail or delay the job it is reporting on. A
// reminder that went unsent because the monitoring write threw would be the
// monitor causing the outage it exists to detect. So this returns false and
// logs; it never throws, and callers are expected to ignore the return value.
//
// THE COST OF THAT IS REAL AND IS STATED RATHER THAN GLOSSED: a job whose
// heartbeat write silently fails looks DEAD to the watchdog while being
// perfectly alive. That is a false alarm, not a missed one -- the safe
// direction -- and the console line below is what lets somebody tell the two
// apart when it happens.
//
// ── WHY THE INTERVAL IS A PARAMETER ────────────────────────────────────────
// The job declares its own cadence on every beat. A schedule changed in
// vercel.json but not in some config table would make the watchdog alarm on a
// healthy job or stay quiet on a dead one, and nothing would ever catch that
// drift. One source of truth, restated every run.
// ---------------------------------------------------------------------------

const OUTCOMES = { ok: true, partial: true, failed: true };

async function beat(opts) {
  opts = opts || {};
  const job = opts.job;
  const outcome = opts.outcome;
  const interval = opts.expected_interval_seconds;

  // A HEARTBEAT WITH A MISSING FIELD IS NOT WRITTEN AT ALL rather than written
  // with a default. `job` defaulted to something generic would collide two jobs
  // onto one row -- the primary key is the job name -- and each would overwrite
  // the other's beat, so BOTH would look alive whenever EITHER ran.
  if (!job || !OUTCOMES[outcome] || !(interval > 0)) {
    console.error('heartbeat: refused, incomplete beat --',
      'job=' + job, 'outcome=' + outcome, 'interval=' + interval);
    return false;
  }
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    console.error('heartbeat: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set, '
      + 'so ' + job + ' beat nowhere');
    return false;
  }

  const now = new Date().toISOString();
  try {
    // UPSERT ON THE PRIMARY KEY. `merge-duplicates` is what makes a second beat
    // an update rather than a 409 -- and the key being `job` is what stops two
    // concurrent beats from the same job producing two rows the watchdog would
    // then read at random.
    const r = await fetch(url.replace(/\/+$/, '') + '/rest/v1/sairn_cron_heartbeat?on_conflict=job', {
      method: 'POST',
      headers: {
        apikey: key,
        Authorization: 'Bearer ' + key,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates,return=minimal'
      },
      body: JSON.stringify({
        job: String(job),
        last_run_at: now,
        outcome: outcome,
        detail: opts.detail === undefined ? null : opts.detail,
        expected_interval_seconds: Math.floor(interval),
        updated_at: now
      })
    });
    if (!r.ok) {
      const body = await r.text().catch(function () { return ''; });
      // NAMED, INCLUDING THE NOT-PROVISIONED CASE, because "the migration has
      // not been run" and "the write failed" send a reader to different places.
      const missing = body.indexOf('PGRST205') !== -1 || body.indexOf('42P01') !== -1 ||
                      body.indexOf('does not exist') !== -1;
      console.error('heartbeat: ' + job + ' did NOT beat -- HTTP ' + r.status +
        (missing ? ' -- sql/cron_heartbeat_schema.sql has not been run' : '') +
        ' -- ' + body.slice(0, 200));
      return false;
    }
    return true;
  } catch (e) {
    console.error('heartbeat: ' + job + ' did NOT beat --', e && e.message);
    return false;
  }
}

module.exports = { beat, OUTCOMES };
