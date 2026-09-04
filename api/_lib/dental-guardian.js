// api/_lib/dental-guardian.js
//
// One implementation of "a SAIRNdental patient under 18 needs a guardian we can
// reach", shared by the two server-side write paths.
//
// ── WHY THIS FILE EXISTS ──────────────────────────────────────────────────
// The rule was stated in three places and implemented in one and a half. On
// 2026-09-04:
//
//   sairndental.html addPatient()  enforced it -- in browser JavaScript
//   api/sairndental/public-book.js did not; the patient object it wrote did
//                                  not contain the guardian keys at all
//   api/sd-data.js generic write   did not; that handler validates payload.id
//                                  and nothing else, for fifteen resources
//
// and a comment beside rcReachable() asserted it as a property of the SYSTEM.
// A paediatric record could therefore exist with no guardian contact, after
// which rcReachable() fell back to whatever phone number a public form had
// collected -- possibly the child's.
//
// Both server paths now call this. The browser keeps its own copy on purpose:
// it runs before the user has finished typing and drives which inputs are
// visible, which is a different job from deciding whether a write is allowed.
// Sharing one function between a client that must be forgiving and a server
// that must not would force one of them to be wrong.

// A guardian is reachable if there is a name AND at least one of phone/email.
// Name alone is not enough: the whole point of the rule is that the practice
// can contact an adult about this patient, and a name is not a contact method.
function hasReachableGuardian(g) {
  const obj = g || {};
  const name = String(obj.name || obj.guardian_name || '').trim();
  const phone = String(obj.phone || obj.guardian_phone || '').trim();
  const email = String(obj.email || obj.guardian_email || '').trim();
  return !!(name && (phone || email));
}

// UNPARSEABLE OR ABSENT IS TREATED AS A MINOR, on the server, deliberately.
// The input is untrusted here, so an unreadable date of birth means "ask for a
// guardian" rather than "assume adult and wave it through". The browser copy
// answers the opposite way for the opposite reason -- there the field is
// required and already checked, and hiding the guardian inputs part-way
// through typing a date would fight the user.
function isMinorDob(dob) {
  const p = String(dob == null ? '' : dob).split('-');
  if (p.length !== 3) return true;
  const b = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
  if (isNaN(b.getTime())) return true;
  const today = new Date();
  let age = today.getFullYear() - b.getFullYear();
  const m = today.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < b.getDate())) age--;
  return age < 18;
}

// Returns a message when the record must be refused, or null when it is fine.
// A message rather than a boolean because the caller shows it to a person, and
// "GUARDIAN_REQUIRED" on its own does not say what to do about it.
//
// `record` is a patient payload: guardian details may arrive either as the
// stored field names (guardian_name/guardian_phone/guardian_email, which is
// what the app sends) or nested under `guardian` (what the public booking page
// sends). Both are accepted so neither caller has to reshape its payload to
// satisfy a validator.
function guardianProblem(record) {
  const r = record || {};
  if (!isMinorDob(r.dob)) return null;
  const g = r.guardian && typeof r.guardian === 'object' ? r.guardian : r;
  if (hasReachableGuardian(g)) return null;
  return 'This patient is under 18, so the record needs a parent or guardian name '
       + 'and either a phone number or an email address. If this is an existing '
       + 'patient, add the guardian details to their record and save again.';
}

module.exports = { guardianProblem, isMinorDob, hasReachableGuardian };
