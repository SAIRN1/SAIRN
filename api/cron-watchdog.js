// api/cron-watchdog.js
// ---------------------------------------------------------------------------
// WHO NOTICES WHEN A SCHEDULED JOB STOPS. Item 54.
//
// Cron-only: Bearer CRON_SECRET. GET or POST; Vercel's cron sends a GET.
//
// ── THE GAP, STATED ACCURATELY RATHER THAN DRAMATICALLY ────────────────────
// api/sairndental/send-reminder.js already logs `sweep complete -- scanned N,
// sent N, ...` on every run, and that line DOES distinguish a sweep that sent
// reminders from one that found nothing due -- the counts differ. Its own
// comment says why the line exists.
//
// WHAT IS MISSING IS THAT NOTHING WATCHES FOR THE LINE'S ABSENCE. A cron that
// stops firing, times out, or 500s writes no line at all, and nothing searches
// a log for something that is not there. Absence is the one signal a log cannot
// volunteer, and it is the only signal that says a job is dead.
//
// ── THE INDEPENDENCE THIS HAS, AND THE INDEPENDENCE IT DOES NOT ────────────
// SAID PLAINLY BECAUSE IT IS THE LIMIT OF THE WHOLE DESIGN. This watchdog runs
// on the SAME Vercel cron scheduler as the jobs it watches. If that scheduler
// stops, the watchdog stops with it and reports nothing -- two units sharing a
// failure mode, which is convention 7's exact lesson: a second copy is not a
// second opinion.
//
// So it is honestly described as: a watchdog for ONE JOB FAILING, not for the
// platform failing. The out-of-band half is tools/cron_liveness_check.py, which
// runs OUTSIDE Vercel, reads the same heartbeats, and is the only thing here
// that survives a total scheduler outage. A hosted uptime check pinging this
// endpoint from a third party would close the remaining gap and is a decision
// about spend and vendors, not something to invent quietly in a file.
//
// ── A JOB THAT NEVER BEAT HAS NO ROW, so a table scan alone cannot see it ──
// EXPECTED_JOBS is declared here and an arm in api/cron-watchdog.test.js
// asserts it matches vercel.json's cron list exactly, in BOTH directions. A
// job added to the schedule and not here would be unwatched and nothing would
// say so; a job removed from the schedule and left here would alarm forever.
// The declaration is cheap; the drift is what needed a control.
// ---------------------------------------------------------------------------

const { beat } = require('./_lib/heartbeat');

const HEARTBEAT_TABLE = 'sairn_cron_heartbeat';

// path -> expected interval in seconds. MUST match vercel.json; the test
// asserts it, because a comment saying "keep these in step" has never once kept
// two lists in step on this platform.
const EXPECTED_JOBS = {
  '/api/sairndental/send-reminder': 3600,
  '/api/alf-alerts': 3600,
  '/api/audit-checkpoint': 86400,
  // THE WATCHDOG WATCHES ITSELF, and that is not circular reasoning -- it
  // cannot report its own silence, but it can leave the evidence of it. Its
  // heartbeat is what tools/cron_liveness_check.py reads from OUTSIDE Vercel,
  // and a missing watchdog beat is the one symptom that distinguishes "no job
  // is in trouble" from "nothing has been checked at all".
  '/api/cron-watchdog': 3600
};

// ── THE ALARM IS TIGHTER THAN THE FAILURE POINT (convention 4) ─────────────
// A beat lands at the END of a run, so a job on a 1h schedule is normally up to
// an hour old and that is healthy, not late. LATE is "it has missed one"; DEAD
// is "it has missed two", which no single slow run explains. The grace exists
// because a cron fires on a schedule, not on a stopwatch: a run starting 90
// seconds late is routine and must not read as a missed interval.
const GRACE_SECONDS = 300;
function lateAfter(interval) { return interval * 2 + GRACE_SECONDS; }
function deadAfter(interval) { return interval * 3 + GRACE_SECONDS; }

function headers() {
  const k = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return { apikey: k, Authorization: 'Bearer ' + k, 'Content-Type': 'application/json' };
}
function isMissingTable(s) {
  s = String(s || '');
  return s.indexOf('PGRST205') !== -1 || s.indexOf('42P01') !== -1 ||
         s.indexOf('does not exist') !== -1;
}

function assess(nowMs, rows) {
  const byJob = {};
  for (const r of rows) byJob[r.job] = r;
  const report = [];
  for (const job of Object.keys(EXPECTED_JOBS).sort()) {
    const interval = EXPECTED_JOBS[job];
    const row = byJob[job];
    if (!row) {
      // NEVER BEATEN is not the same as LATE, and it must not be reported as
      // it: a job that has never once run is usually a deploy or a schedule
      // that was never wired, which is a different fix from a job that stopped.
      report.push({
        job: job, status: 'NEVER_BEAT', expected_interval_seconds: interval,
        why: 'no heartbeat row exists for this job at all -- it has never '
           + 'completed a run, or sql/cron_heartbeat_schema.sql predates it'
      });
      continue;
    }
    const ageSec = Math.floor((nowMs - Date.parse(row.last_run_at)) / 1000);
    const entry = {
      job: job, last_run_at: row.last_run_at, age_seconds: ageSec,
      expected_interval_seconds: interval, last_outcome: row.outcome,
      // MARGIN, not just a verdict. "1,900 seconds until this is late" is a
      // different thing to act on from "late", and a check that only ever says
      // the second has already let the bad run ship.
      seconds_until_late: lateAfter(interval) - ageSec,
      detail: row.detail === undefined ? null : row.detail
    };
    if (ageSec > deadAfter(interval)) entry.status = 'DEAD';
    else if (ageSec > lateAfter(interval)) entry.status = 'LATE';
    else entry.status = 'ok';
    // A JOB THAT RAN AND FAILED IS ALIVE AND UNHAPPY, which needs a different
    // response from silence. Kept as its own status rather than folded into
    // LATE -- collapsing them would send somebody to check the scheduler when
    // the scheduler is fine.
    if (entry.status === 'ok' && row.outcome === 'failed') entry.status = 'FAILING';
    if (entry.status === 'ok' && row.outcome === 'partial') entry.status = 'PARTIAL';
    report.push(entry);
  }
  // A row for a job nobody expects is reported rather than ignored: it is
  // either a job removed from vercel.json and still beating, or a name typo
  // that means the real job is being watched under the wrong key.
  for (const job of Object.keys(byJob).sort()) {
    if (!EXPECTED_JOBS[job]) {
      report.push({
        job: job, status: 'UNDECLARED', last_run_at: byJob[job].last_run_at,
        why: 'this job beats but is not in EXPECTED_JOBS -- either it was '
           + 'removed from vercel.json and is still running, or its name does '
           + 'not match the one being watched'
      });
    }
  }
  return report;
}

module.exports = async (req, res) => {
  if (!process.env.CRON_SECRET) {
    console.error('cron-watchdog: CRON_SECRET not set');
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }
  const missing = [
    !process.env.SUPABASE_URL ? 'SUPABASE_URL' : null,
    !process.env.SUPABASE_SERVICE_ROLE_KEY ? 'SUPABASE_SERVICE_ROLE_KEY' : null
  ].filter(Boolean);
  if (missing.length) {
    console.error('cron-watchdog: not configured, missing: ' + missing.join(', '));
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }

  try {
    const url = String(process.env.SUPABASE_URL).replace(/\/+$/, '') +
      '/rest/v1/' + HEARTBEAT_TABLE +
      '?select=job,last_run_at,outcome,detail,expected_interval_seconds';
    const r = await fetch(url, { headers: headers() });
    const text = await r.text().catch(() => '');
    if (!r.ok) {
      if (isMissingTable(text)) {
        // NOT "no stale jobs". A watchdog reporting a clean sweep over a table
        // that does not exist is the cheeriest possible way to say nothing is
        // being watched.
        res.status(503).json({
          error: {
            code: 'NOT_PROVISIONED',
            message: 'The cron heartbeat table is not set up yet -- run '
                   + 'sql/cron_heartbeat_schema.sql. NOTHING was checked, and '
                   + 'that is not the same as nothing being wrong.'
          }
        });
        return;
      }
      console.error('cron-watchdog: heartbeat read failed HTTP ' + r.status + ' ' + text.slice(0, 200));
      res.status(502).json({ error: { message: 'Could not read heartbeats, so nothing was checked.' } });
      return;
    }
    let rows;
    try { rows = JSON.parse(text); } catch (e) { rows = null; }
    if (!Array.isArray(rows)) {
      res.status(502).json({ error: { message: 'Heartbeat read returned a non-array, so nothing was checked.' } });
      return;
    }

    const report = assess(Date.now(), rows);
    const bad = report.filter((x) => x.status !== 'ok');
    // LOGGED, NOT JUST RETURNED -- the same reason every cron here logs its
    // completion: Vercel discards the response body, so a watchdog whose only
    // output was a body would itself be the silent job.
    console.log('cron-watchdog: checked ' + report.length + ' job(s) -- ' +
      report.map((x) => x.job + '=' + x.status).join(', '));
    if (bad.length) {
      console.error('cron-watchdog: ' + bad.length + ' job(s) NOT ok -- ' + JSON.stringify(bad));
    }
    // THE WATCHDOG LEAVES ITS OWN EVIDENCE. It cannot report its own silence,
    // but tools/cron_liveness_check.py reads this row from outside Vercel, and
    // a missing watchdog beat is the one symptom that separates "no job is in
    // trouble" from "nothing has been checked at all".
    await beat({
      job: '/api/cron-watchdog',
      outcome: bad.length ? 'partial' : 'ok',
      expected_interval_seconds: 3600,
      detail: { checked: report.length, not_ok: bad.map(function (x) { return x.job + '=' + x.status; }) }
    });
    res.status(200).json({ ok: bad.length === 0, checked: report.length, jobs: report });
  } catch (err) {
    console.error('cron-watchdog: error', err && err.message);
    res.status(502).json({ error: { message: 'Upstream error -- try again' } });
  }
};

module.exports.EXPECTED_JOBS = EXPECTED_JOBS;
module.exports.assess = assess;
module.exports.lateAfter = lateAfter;
module.exports.deadAfter = deadAfter;
module.exports.GRACE_SECONDS = GRACE_SECONDS;
