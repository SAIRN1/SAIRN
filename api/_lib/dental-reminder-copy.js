// api/_lib/dental-reminder-copy.js
// Pure email-copy builder for SAIRNdental appointment reminders -- no
// network/DB access, testable in isolation (dental-reminder-copy.test.js).
// Informational only, no cancel/reschedule link (design spec §0): states
// the appointment details and the practice's phone number to call for any
// change. practiceAddress appears in the footer as the CAN-SPAM-required
// physical address. See
// docs/superpowers/specs/2026-08-11-sairndental-email-reminders-design.md.

function formatWhen(startTimeISO) {
  var d = new Date(startTimeISO);
  return d.toLocaleString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
    hour: 'numeric', minute: '2-digit'
  });
}

// Same escaping discipline as sairndental.html's H() -- this text
// ultimately renders as HTML in a patient's inbox.
function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function buildReminderEmail(opts) {
  opts = opts || {};
  var practiceName = opts.practiceName || 'Your dental practice';
  var practicePhone = opts.practicePhone || '';
  var practiceAddress = opts.practiceAddress || '';
  var patientName = opts.patientName || 'there';
  var providerName = opts.providerName || 'your provider';
  var procedureLabel = opts.procedureLabel || 'your appointment';
  var when = formatWhen(opts.startTimeISO);
  var stage = opts.stage;

  var leadIn = stage === '2h'
    ? 'This is a reminder that your appointment is coming up soon:'
    : 'This is a reminder about your upcoming appointment:';

  var subject = stage === '2h'
    ? practiceName + ': your appointment is in about 2 hours'
    : practiceName + ': appointment reminder for ' + when;

  var callLine = practicePhone
    ? ('If you need to reschedule or cancel, please call us at ' + practicePhone + '.')
    : 'If you need to reschedule or cancel, please call the office.';

  var text = 'Hi ' + patientName + ',\n\n' + leadIn + '\n\n' +
    'When: ' + when + '\n' +
    'Provider: ' + providerName + '\n' +
    'Procedure: ' + procedureLabel + '\n\n' +
    callLine + '\n\n' +
    '-- ' + practiceName + (practiceAddress ? ('\n' + practiceAddress) : '');

  var html = '<p>Hi ' + escHtml(patientName) + ',</p>' +
    '<p>' + escHtml(leadIn) + '</p>' +
    '<p><strong>When:</strong> ' + escHtml(when) + '<br>' +
    '<strong>Provider:</strong> ' + escHtml(providerName) + '<br>' +
    '<strong>Procedure:</strong> ' + escHtml(procedureLabel) + '</p>' +
    '<p>' + escHtml(callLine) + '</p>' +
    '<p style="color:#666;font-size:12px">' + escHtml(practiceName) +
    (practiceAddress ? ('<br>' + escHtml(practiceAddress)) : '') + '</p>';

  return { subject: subject, text: text, html: html };
}

module.exports = { buildReminderEmail: buildReminderEmail, formatWhen: formatWhen, escHtml: escHtml };
