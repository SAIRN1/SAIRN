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

/**
 * Decide, without doing anything.
 *
 * @param report   what api/cron-watchdog.js assess() produced
 * @param prior    { job: { status, at_ms, count, escalated } } from the last run
 * @param nowMs    clock, passed in so this is testable without sleeping
 * @returns { actions: [...], memo: {...} }  memo is `prior` for the NEXT run
 */
function planResponse(report, prior, nowMs) {
  prior = prior || {};
  const actions = [];
  const memo = {};
  for (const entry of report) {
    const status = entry.status;
    if (status === 'ok') continue;                 // and it drops out of memo, which
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
