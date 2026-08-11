// api/_lib/dental-reminder-window.js
// Pure window-selection logic for SAIRNdental appointment reminders --
// no network/DB access, testable in isolation
// (dental-reminder-window.test.js). Extracted out of send-reminder.js so
// the core "which appointments are due right now" logic can be verified
// without a live Resend send. See
// docs/superpowers/specs/2026-08-11-sairndental-email-reminders-design.md §3.
//
// Window definition (precise form): an appointment needs the 48h
// reminder when 47 < hoursUntil <= 48, and the 2h reminder when
// 1 < hoursUntil <= 2. Half-open on the near edge, closed on the far
// edge -- an hourly cron can't skip either window, and neither stage
// double-sends within one window.

function hoursUntil(startTimeISO, nowMs) {
  return (new Date(startTimeISO).getTime() - nowMs) / (1000 * 60 * 60);
}

function needsStage(row, stage, nowMs) {
  var h = hoursUntil(row.start_time, nowMs);
  var already = stage === '48h' ? row.data.reminder_48h_sent_at : row.data.reminder_2h_sent_at;
  if (already) return false;
  if (stage === '48h') return h > 47 && h <= 48;
  return h > 1 && h <= 2;
}

module.exports = { hoursUntil: hoursUntil, needsStage: needsStage };
