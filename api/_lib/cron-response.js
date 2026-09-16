// api/_lib/cron-response.js
// ---------------------------------------------------------------------------
// WHAT HAPPENS WHEN THE WATCHDOG FINDS SOMETHING. Item 55, built on item 54.
//
// ── THE POINT IS THAT THE RESPONSE IS DECIDED IN ADVANCE ───────────────────
// A detector that stops at detecting hands the decision to whoever happens to
// read the output, at the moment they read it, under whatever pressure they are
// under. RESPONSE below is a table: for each status the watchdog can produce,
// what is done, written down before the incident rather than during it.
//
// planResponse() is PURE. It takes the report, the record of what was already
// alerted, and a clock, and returns the actions. Nothing is sent from it. That
// is deliberate: the decision half is the half worth testing exhaustively, and
// a planner that had to be driven through a mail provider would be tested the
// way mail providers allow rather than the way the decision needs.
//
// ── WHY RETRY IS NOT THE ANSWER TO EVERY STATUS ────────────────────────────
// Retrying is only useful when the RUN itself failed. It is actively wrong for:
//
//   NEVER_BEAT  -- the job has never once completed. That is a deploy or a
//                  schedule that was never wired, and re-invoking it will fail
//                  the same way while making the log look like flapping.
//   PARTIAL     -- on alf-alerts this means sends were rejected. A retry
//                  re-sends, which at best duplicates a medication alert to a
//                  facility and at worst hammers a provider that is already
//                  refusing. The fix is the provider, not another attempt.
//   UNDECLARED  -- nothing is wrong with the job; the watchdog's own list is
//                  out of date. Retrying somebody else's healthy job is not a
//                  response, it is an unrelated side effect.
//
// ── ALERT STORMS ARE THE FAILURE MODE OF EVERY SYSTEM LIKE THIS ────────────
// A DEAD job is DEAD on every run. Alerting hourly for a week produces 168
// identical emails, and the reliable consequence is a filter rule -- after
// which the NEXT real alert is invisible. So an alert fires on a STATUS CHANGE,
// or after REALERT_SECONDS of the same status, and never otherwise. What was
// suppressed is REPORTED, because a suppression nobody can see is
// indistinguishable from a detector that stopped working.
//
// ── AND THE HONESTY RULE THAT MATTERS MOST HERE ────────────────────────────
// AN UNDELIVERABLE ALERT IS NOT A HANDLED EVENT. If no destination is
// configured, or the provider refuses, the action is recorded as FAILED and the
// watchdog's own outcome degrades. An alerting system that is silently inert is
// the exact defect this platform keeps finding -- and it is worse here than
// having none, because the existence of a watchdog is itself an assurance.
// ---------------------------------------------------------------------------

// Same status a second time does not re-alert until this much has passed.
// 6 hours: long enough that a week-long outage produces four mails a day rather
// than twenty-four, short enough that an alert lost to a spam folder is not the
// only one that will ever be sent.
const REALERT_SECONDS = 6 * 60 * 60;

// ── THE PRE-PLANNED RESPONSE, ONE ROW PER STATUS ───────────────────────────
// `escalate_after` counts CONSECUTIVE detections of the same status, not hours:
// a job that has been DEAD across three watchdog runs is a different situation
// from one detected dead once, whatever the clock says.
const RESPONSE = {
  DEAD: {
    alert: true, retry: true, escalate_after: 3,
    say: 'the job has missed three or more intervals -- it is not running'
  },
  LATE: {
    alert: true, retry: false, escalate_after: null,
    say: 'the job has missed two intervals; one slow run does not explain that'
  },
  NEVER_BEAT: {
    alert: true, retry: false, escalate_after: null,
    say: 'the job has NEVER completed a run -- retrying cannot help, this is a '
       + 'deploy or a schedule that was never wired'
  },
  FAILING: {
    alert: true, retry: true, escalate_after: 3,
    say: 'the job ran on time and reported FAILED -- the scheduler is fine, the job is not'
  },
  PARTIAL: {
    alert: true, retry: false, escalate_after: 5,
    say: 'the job ran on time and did only part of its work -- on an alert sweep '
       + 'that means alive, on schedule, and notifying nobody. A retry would '
       + 're-send rather than fix it'
  },
  UNDECLARED: {
    alert: true, retry: false, escalate_after: null,
    say: "a job is beating that the watchdog's own list does not know about -- "
       + 'nothing is wrong with the job'
  }
};

// ── A MONITOR DOES NOT ACT ON ITSELF (added 2026-09-15, Hank) ──────────────
// FOUND IN PRODUCTION, NOT REASONED ABOUT. `/api/cron-watchdog` is in its own
// EXPECTED_JOBS list -- correctly, because it must leave its own heartbeat for
// an outside reader. But it was also RESPONDING to itself, and the two live
// consequences were both bad:
//
//  1. THE RETRY WAS THE RUNNING FUNCTION INVOKING ITSELF. Observed
//     2026-09-15T21:15:29Z: `{"action":"retry","job":"/api/cron-watchdog",
//     "delivered":false,"detail":{"ok":false,"status":508}}`. 508 is
//     Vercel's LOOP DETECTED.
//
//  2. A LATCH THAT COULD NEVER CLEAR, which is the worse half. An alert that
//     cannot be delivered degrades this job's own outcome to `failed`. Next
//     hour it reads its own row, sees `last_outcome: failed`, calls ITSELF
//     FAILING, plans another alert, fails to deliver it, and writes `failed`
//     again. Measured over four consecutive hours on 2026-09-15 with all three
//     REAL jobs reporting ok the whole time: the only thing the watchdog was
//     reporting was a fault it was causing itself.
//
//  AND IT DEFEATED THE ALERT-STORM RULE THROUGH A DOOR NOBODY CHECKED. The
//  self-status FLAPPED (PARTIAL -> FAILING -> FAILING -> PARTIAL) because the
//  outcome it wrote depended on what it had just failed to send. `same` was
//  false on every flap, so the once-per-6h suppression never applied and it
//  re-alerted every hour -- the exact storm REALERT_SECONDS exists to prevent.
//
// THE FIX IS NOT "SKIP THE SELF ROW". It stays in the report and it is still
// written to the heartbeat, because that row is the ONLY evidence an outside
// reader has that the watchdog ran at all -- api/cron-watchdog.js says so in
// its own comment, and tools/cron_liveness_check.py is the reader. What is
// removed is the watchdog RESPONDING to it. Who responds to a sick watchdog is
// a question a sick watchdog cannot answer, and the answer has to come from
// outside: .github/workflows/cron-liveness.yml is the independent second one.
function selfAction(entry, reason) {
  return {
    job: entry.job, status: entry.status, action: 'self',
    reason: reason,
    say: 'the watchdog does not alert, retry or escalate on ITSELF -- a monitor '
       + 'acting on its own verdict is not a second opinion, and the retry was '
       + 'literally this function invoking itself (HTTP 508). This is REPORTED '
       + 'so it is visible, and the response comes from the independent check '
       + 'outside Vercel.'
  };
}

/**
 * Decide, without doing anything.
 *
 * @param report   what api/cron-watchdog.js assess() produced
 * @param prior    { job: { status, at_ms, count, escalated } } from the last run
 * @param nowMs    clock, passed in so this is testable without sleeping
 * @param selfJob  the job id this watchdog IS, or null/absent. When given, that
 *                 job is REPORTED and never acted on. Optional rather than
 *                 required only because every existing caller and arm predates
 *                 it; the one real caller passes it.
 * @returns { actions: [...], memo: {...} }  memo is `prior` for the NEXT run
 */
function planResponse(report, prior, nowMs, selfJob) {
  prior = prior || {};
  const actions = [];
  const memo = {};
  for (const entry of report) {
    const status = entry.status;
    if (status === 'ok') continue;                 // and it drops out of memo, which
    if (selfJob && entry.job === selfJob) {
      // NOT `continue` before the memo write by accident -- deliberately no
      // memo entry either. A streak counter on a job nothing acts on is a
      // number with no consequence, and leaving one would make a later reader
      // think an escalation was pending.
      actions.push(selfAction(entry, 'this is the watchdog\'s own job'));
      continue;
    }
    const plan = RESPONSE[status];                 // is what resets the streak
    if (!plan) {
      // A STATUS WITH NO PLANNED RESPONSE IS A FINDING ABOUT THIS TABLE, not a
      // reason to do nothing. Silence here would mean a new watchdog status
      // quietly having no response at all.
      actions.push({
        job: entry.job, status: status, action: 'NO_PLAN',
        reason: 'no row in RESPONSE for status "' + status + '" -- the watchdog '
              + 'can produce a verdict this table does not answer'
      });
      continue;
    }
    const was = prior[entry.job];
    const same = was && was.status === status;
    const count = same ? (was.count || 1) + 1 : 1;
    const sinceMs = same && was.at_ms ? nowMs - was.at_ms : null;

    let alerted = false;
    if (!same) {
      actions.push({ job: entry.job, status: status, action: 'alert',
                     reason: 'status changed to ' + status, say: plan.say, count: count });
      alerted = true;
    } else if (sinceMs !== null && sinceMs >= REALERT_SECONDS * 1000) {
      actions.push({ job: entry.job, status: status, action: 'alert',
                     reason: 'still ' + status + ' after ' + Math.floor(sinceMs / 3600000) + 'h',
                     say: plan.say, count: count });
      alerted = true;
    } else {
      // REPORTED, NOT SILENT. A suppression nobody can see is indistinguishable
      // from a detector that stopped working.
      actions.push({
        job: entry.job, status: status, action: 'suppressed',
        reason: 'already alerted for ' + status + ' ' +
                (sinceMs === null ? 'this run' : Math.floor(sinceMs / 60000) + 'm ago') +
                '; next alert after ' + (REALERT_SECONDS / 3600) + 'h',
        count: count
      });
    }

    // RETRY ONCE PER DETECTION, NEVER IN A LOOP, and only on the first detection
    // of a run of the same status -- a job that is dead for a week must not be
    // re-invoked every hour.
    if (plan.retry && !same) {
      actions.push({ job: entry.job, status: status, action: 'retry',
                     reason: 'first detection of ' + status + '; one attempt' });
    }

    const escalate = plan.escalate_after && count >= plan.escalate_after &&
                     !(was && was.escalated);
    if (escalate) {
      actions.push({
        job: entry.job, status: status, action: 'escalate', count: count,
        reason: status + ' on ' + count + ' consecutive checks (threshold ' +
                plan.escalate_after + ')', say: plan.say
      });
    }
    memo[entry.job] = {
      status: status,
      at_ms: alerted ? nowMs : (was && was.at_ms) || nowMs,
      count: count,
      escalated: !!(escalate || (was && was.escalated))
    };
  }
  return { actions: actions, memo: memo };
}

module.exports = { planResponse, RESPONSE, REALERT_SECONDS };
