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
const { planResponse } = require('./_lib/cron-response');

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

// The one job this watchdog IS. Taken from the key above rather than retyped,
// because two spellings of the same route is how a self-exclusion silently
// stops excluding. It is REPORTED and never ACTED ON -- see the long note in
// api/_lib/cron-response.js, which was written from four hours of live logs of
// this job retrying itself into an HTTP 508 and latching itself FAILING.
const SELF_JOB = '/api/cron-watchdog';

// ── AND IT MUST NOT GRADE ITSELF EITHER (2026-09-17) ───────────────────────
// FOUND LIVE, from production logs rather than from reading the code.
// `SAIRN_OPS_EMAIL` was set in production and the channel came back CONFIGURED
// at 00:15:28Z -- the "CANNOT NOTIFY ANYBODY" line stopped being printed, which
// is the whole proof the fix landed -- and the self row went on reading PARTIAL
// anyway. The outcome written each run was derived from a `bad` list that
// CONTAINED THIS JOB'S OWN PREVIOUS ROW: partial -> PARTIAL -> partial, a loop
// closed entirely inside this function with no input from the world.
//
// THE ITEM 55 FIX REMOVED THE WATCHDOG RESPONDING TO ITSELF AND LEFT IT
// GRADING ITSELF, which latches exactly as hard and is far quieter. No retry,
// no HTTP 508, no alert storm -- just a monitor that is red for ever, an `ok`
// field that can never be true again, and a `cron_liveness_check.py` that can
// never exit 0. A monitor stuck red is this repository's own most recently
// repaired defect (ccf38216, a suite RED on main that nobody read); a fix that
// cannot be seen to have worked is indistinguishable from one that did not.
//
// ANOTHER job being bad still degrades this one to `partial`, and that is
// deliberately unchanged: it does not latch, because that job recovering
// empties the list. Only the SELF term is self-referential, so only the SELF
// term is removed -- and the self row is still REPORTED, still logged, still in
// `not_ok`. What is removed is it feeding its own next verdict.
//
// Pure and exported because the expression it replaces lived inline in the
// handler, where nothing could drive it, which is why five consecutive live
// runs were needed to see the latch at all.
function selfOutcome(bad, realUndelivered, channelConfigured, selfJob) {
  if (realUndelivered.length) return 'failed';
  const others = bad.filter(function (x) { return x.job !== selfJob; });
  return (others.length || !channelConfigured) ? 'partial' : 'ok';
}

// ── CAN THIS WATCHDOG TELL ANYBODY ANYTHING? ASKED EVERY RUN ───────────────
// FOUND LIVE 2026-09-15: SAIRN_OPS_EMAIL is not set in production, so every
// alert this thing has ever planned ended `"nobody was told"`. That was
// visible only inside a per-job action detail, under a headline reading
// `checked 4 job(s)` and an HTTP 200 -- so the watchdog looked healthy while
// being completely unable to notify.
//
// This is asked UNCONDITIONALLY, not only when there is something to send.
// Waiting until a real job fails to discover the channel is dead is the same
// defect as a backup nobody restores: the moment you need it is the moment you
// find out. The file's own rule already says a silently inert alerting system
// is worse than none, "because the existence of a watchdog is itself an
// assurance" -- this is that rule applied to the channel rather than to a
// single alert.
function notifyChannel() {
  const missing = [];
  if (!process.env.SAIRN_OPS_EMAIL) missing.push('SAIRN_OPS_EMAIL');
  if (!process.env.RESEND_API_KEY) missing.push('RESEND_API_KEY');
  if (!process.env.RESEND_FROM_EMAIL) missing.push('RESEND_FROM_EMAIL');
  return {
    configured: missing.length === 0,
    missing: missing,
    // SAIRN_ESCALATION_EMAIL is deliberately NOT in `missing`: alertTo() falls
    // back to SAIRN_OPS_EMAIL for an escalation, so its absence degrades who
    // gets told rather than whether anybody does. Reported separately so that
    // distinction is visible instead of inferred.
    escalation_has_own_address: !!process.env.SAIRN_ESCALATION_EMAIL
  };
}

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

// ── DELIVERY (item 55) ──────────────────────────────────────────────────────
// Kept apart from planResponse() on purpose: the DECISION is pure and
// exhaustively testable without a mail provider, and this half is the only part
// that talks to the outside world.
function alertTo(escalated) {
  return escalated
    ? (process.env.SAIRN_ESCALATION_EMAIL || process.env.SAIRN_OPS_EMAIL || null)
    : (process.env.SAIRN_OPS_EMAIL || null);
}

async function sendAlert(to, subject, text) {
  if (!process.env.RESEND_API_KEY || !process.env.RESEND_FROM_EMAIL) {
    return { sent: false, error: 'RESEND_API_KEY / RESEND_FROM_EMAIL not configured' };
  }
  try {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + process.env.RESEND_API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        from: process.env.RESEND_FROM_EMAIL, to: [to], subject: subject, text: text
      })
    });
    if (!r.ok) {
      const t = await r.text().catch(function () { return ''; });
      return { sent: false, error: 'Resend returned ' + r.status + ' ' + t.slice(0, 200) };
    }
    // The provider's id is captured so a SUCCESSFUL send is positively
    // observable rather than inferred from the absence of a failure line --
    // the same argument api/alf-alerts.js already makes about its own sends.
    const b = await r.json().catch(function () { return {}; });
    return { sent: true, id: (b && b.id) || null };
  } catch (e) {
    return { sent: false, error: String((e && e.message) || e).slice(0, 200) };
  }
}

function baseUrl() {
  if (process.env.SAIRN_BASE_URL) {
    return String(process.env.SAIRN_BASE_URL).replace(/\/+$/, '');
  }
  if (process.env.VERCEL_URL) return 'https://' + process.env.VERCEL_URL;
  return null;
}

// ONE ATTEMPT. Never a loop and never a second try inside the same run: a retry
// that failed is information, and retrying it again here would turn one bad
// minute into a stampede against a service that is already unwell.
async function retryJob(job) {
  const base = baseUrl();
  if (!base) {
    return { ok: false, error: 'neither SAIRN_BASE_URL nor VERCEL_URL is set, so there is no address to retry against' };
  }
  try {
    const r = await fetch(base + job, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + process.env.CRON_SECRET,
        'Content-Type': 'application/json'
      },
      body: '{}'
    });
    return { ok: r.ok, status: r.status };
  } catch (e) {
    return { ok: false, error: String((e && e.message) || e).slice(0, 200) };
  }
}

async function executeActions(actions) {
  const out = [];
  for (const a of actions) {
    if (a.action === 'suppressed' || a.action === 'NO_PLAN' || a.action === 'self') {
      // Carried through verbatim. `delivered` is deliberately ABSENT rather than
      // true: nothing was delivered, and nothing needed to be -- and a `true`
      // here would make the undelivered count below quietly wrong.
      out.push(a);
      continue;
    }
    if (a.action === 'retry') {
      const r = await retryJob(a.job);
      out.push(Object.assign({}, a, { delivered: r.ok, detail: r }));
      continue;
    }
    const escalated = a.action === 'escalate';
    const to = alertTo(escalated);
    if (!to) {
      // AN UNDELIVERABLE ALERT IS NOT A HANDLED EVENT. Recorded as delivered
      // false so the watchdog's own outcome degrades every run until somebody
      // configures a destination. An alerting system that is silently inert is
      // worse than none, because the existence of a watchdog is itself an
      // assurance somebody is relying on.
      out.push(Object.assign({}, a, {
        delivered: false,
        detail: {
          error: (escalated ? 'SAIRN_ESCALATION_EMAIL' : 'SAIRN_OPS_EMAIL') +
                 ' is not configured, so nobody was told'
        }
      }));
      continue;
    }
    const NL = String.fromCharCode(10);
    const subject = (escalated ? 'ESCALATION: ' : 'SAIRN cron: ') + a.job + ' is ' + a.status;
    const text = [
      a.job + ' is ' + a.status + '.',
      '',
      a.say || '',
      '',
      'Why now: ' + a.reason,
      'Consecutive checks in this state: ' + (a.count || 1),
      '',
      'This response was decided in advance -- see api/_lib/cron-response.js.',
      'Detection: api/cron-watchdog.js.',
      'Out-of-band check: CRON_SECRET=... python tools/cron_liveness_check.py'
    ].join(NL);
    const sent = await sendAlert(to, subject, text);
    out.push(Object.assign({}, a, { delivered: sent.sent, detail: sent, to: to }));
  }
  return out;
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
        //
        // NO BEAT HERE, AND THAT IS THE ONE CASE WHERE THE OMISSION IS RIGHT
        // rather than the defect fixed below. The heartbeat table is the thing
        // that is missing; beat() writes to that same table and would fail
        // identically. It already logs its own specific line for this --
        // "sql/cron_heartbeat_schema.sql has not been run" -- so calling it
        // would add a second, less precise message and no row. The console
        // line and the 503 are the whole signal available, and the watchdog
        // being un-monitorable while its own storage is absent is a fact about
        // the situation rather than something this file can fix.
        console.error('cron-watchdog: NOT_PROVISIONED -- the heartbeat table '
          + 'is absent, so nothing was checked AND no heartbeat could be '
          + 'written for this run either. Nothing is watching anything.');
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
      // ── THE WATCHDOG MUST REPORT ITS OWN FAILURE (fixed 2026-09-16) ──────
      // Both of these returned without beating. That is the same defect found
      // in api/audit-checkpoint.js and api/sairndental/send-reminder.js, and
      // it is the WORST instance of it, because NOTHING ELSE WATCHES THE
      // WATCHDOG -- this file is the only reader of the heartbeat table, and
      // the row it writes about itself is the only evidence that the sweep
      // ran. Failing these two ways wrote nothing, so the monitor went silent
      // exactly when it was broken, and its own staleness check for
      // `/api/cron-watchdog` is what would otherwise have caught that.
      //
      // The table EXISTS on this path -- the read failed for some other
      // reason -- so unlike the NOT_PROVISIONED branch above, beat() can
      // actually write here.
      await beat({
        job: '/api/cron-watchdog', outcome: 'failed',
        expected_interval_seconds: 3600,
        detail: { error: 'HEARTBEAT_READ_FAILED', http: r.status,
                  checked: 0, retry_helps: true }
      });
      res.status(502).json({ error: { message: 'Could not read heartbeats, so nothing was checked.' } });
      return;
    }
    let rows;
    try { rows = JSON.parse(text); } catch (e) { rows = null; }
    if (!Array.isArray(rows)) {
      console.error('cron-watchdog: heartbeat read returned a non-array');
      await beat({
        job: '/api/cron-watchdog', outcome: 'failed',
        expected_interval_seconds: 3600,
        detail: { error: 'HEARTBEAT_READ_NOT_AN_ARRAY', checked: 0,
                  retry_helps: true }
      });
      res.status(502).json({ error: { message: 'Heartbeat read returned a non-array, so nothing was checked.' } });
      return;
    }

    const nowMs = Date.now();
    const report = assess(nowMs, rows);
    const bad = report.filter((x) => x.status !== 'ok');

    // ── ITEM 55: THE RESPONSE, DECIDED IN ADVANCE ───────────────────────
    // The memo of what was already alerted rides in THIS job's own heartbeat
    // detail rather than in a new table. It is current-state, it is small, and
    // that row is written every run anyway -- a second table would be a second
    // migration to run and a second thing to be missing.
    const self = rows.filter(function (r) { return r.job === '/api/cron-watchdog'; })[0];
    const prior = (self && self.detail && self.detail.response_memo) || {};
    const planned = planResponse(report, prior, nowMs, SELF_JOB);
    const executed = await executeActions(planned.actions);
    const channel = notifyChannel();
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
    // AN UNDELIVERED RESPONSE DEGRADES THE WATCHDOG'S OWN OUTCOME. A watchdog
    // that detected correctly and could not tell anybody is not healthy, and
    // reporting `ok` because the DETECTION half worked is exactly how an
    // alerting system ends up silently inert.
    const undelivered = executed.filter(function (a) { return a.delivered === false; });
    if (!channel.configured) {
      console.error('cron-watchdog: CANNOT NOTIFY ANYBODY -- missing ' +
        channel.missing.join(', ') + '. Detection is running; every alert it '
        + 'plans will end "nobody was told".');
    }
    // ── WHICH OUTCOME, AND WHY IT IS NOT `failed` ──────────────────────────
    // An unconfigured channel is a STANDING CONFIGURATION STATE, not a run that
    // went wrong, and the difference is load-bearing rather than cosmetic:
    // writing `failed` here is what made this job read its own row next hour,
    // call itself FAILING, and alert about itself for ever. `partial` is the
    // honest word -- it detected correctly and it cannot notify, which is
    // literally part of the work done. It still is NOT `ok`, because an
    // alerting system that is silently inert is the defect this file names in
    // its own header.
    //
    // NOTE THE ORDER: an undelivered alert about a REAL job is still `failed`.
    // Only the "nothing is configured at all" case is downgraded, and only
    // because that case is now reported on its own axis where an outside reader
    // can see it standing.
    const realUndelivered = channel.configured ? undelivered : [];
    await beat({
      job: SELF_JOB,
      // SELF-EXCLUDED -- see selfOutcome() above. This expression used to read
      // `bad.length`, which includes this job's own previous row, and that is
      // the latch that kept the self status PARTIAL after the channel was fixed.
      outcome: selfOutcome(bad, realUndelivered, channel.configured, SELF_JOB),
      expected_interval_seconds: 3600,
      detail: {
        checked: report.length,
        not_ok: bad.map(function (x) { return x.job + '=' + x.status; }),
        response_memo: planned.memo,
        notify_channel: channel,
        undelivered: undelivered.map(function (a) { return a.action + ':' + a.job; })
      }
    });
    if (undelivered.length) {
      console.error('cron-watchdog: ' + undelivered.length +
        ' RESPONSE(S) COULD NOT BE DELIVERED -- ' + JSON.stringify(undelivered));
    }
    res.status(200).json({
      // `ok` NOW REQUIRES A USABLE CHANNEL, and that is a deliberate widening.
      // The independent check outside Vercel reads this field, and a watchdog
      // that detects perfectly and can tell nobody is not a healthy watchdog --
      // it is the failure this file's own header calls worse than having none.
      ok: bad.length === 0 && undelivered.length === 0 && channel.configured,
      checked: report.length, jobs: report,
      // ON ITS OWN AXIS rather than folded into `ok`, so the outside reader can
      // say WHICH of the two halves is broken. A boolean that collapses "a job
      // is down" and "nobody can be told" sends the reader to the wrong place.
      notify_channel: channel,
      // NAMED SEPARATELY from `jobs`: what was FOUND and what was DONE about it
      // are different questions, and a reader who cannot tell them apart cannot
      // tell a suppressed alert from an alert that was never planned.
      actions: executed
    });
  } catch (err) {
    console.error('cron-watchdog: error', err && err.message);
    res.status(502).json({ error: { message: 'Upstream error -- try again' } });
  }
};

module.exports.EXPECTED_JOBS = EXPECTED_JOBS;
module.exports.assess = assess;
module.exports.selfOutcome = selfOutcome;
module.exports.SELF_JOB = SELF_JOB;
module.exports.lateAfter = lateAfter;
module.exports.deadAfter = deadAfter;
module.exports.GRACE_SECONDS = GRACE_SECONDS;
module.exports.executeActions = executeActions;
module.exports.alertTo = alertTo;
module.exports.baseUrl = baseUrl;
