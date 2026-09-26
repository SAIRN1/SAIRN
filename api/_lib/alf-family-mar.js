// api/_lib/alf-family-mar.js
// SAIRNcare -- what a family member may see of the MAR, and nothing else.
//
// PURE -- no I/O, no clock, no network.
//
// ── THE DECISION THIS IMPLEMENTS ────────────────────────────────────────────
// Michael, 2026-09-26: the family portal's MAR access is READ-ONLY and
// CONSENT-GATED. Once consent is granted, the family member sees MEDICATION
// ADMINISTRATION STATUS only -- given / missed, the scheduled time, and an
// adherence figure. NOT the full editable MAR, NOT PRN clinical reasoning, NOT
// controlled-substance counts.
//
// ── WHY THAT SHAPE AND NOT A NARROWED MAR ──────────────────────────────────
// Two things agree on it, and they are worth naming because they come from
// opposite directions.
//
// HIPAA's MINIMUM NECESSARY standard asks what the least is that serves the
// purpose. The purpose a family member has is "is my mother being looked
// after" -- and that is answered by whether the morning medications were
// given, not by which medications they are. A medication LIST is a diagnosis
// by inference: an antipsychotic, an antiretroviral or a dementia drug names a
// condition the resident may not have disclosed to that relative.
//
// THE COMPETITIVE PATTERN SAYS THE SAME. PointClickCare's Connected Care
// Center and AlayaCare's family portal both surface care-event STATUS to
// family -- visits, tasks, medication events as occurrences -- rather than the
// clinical record itself. This is not an invention; it is the category's
// settled shape, and matching it is the design basis.
//
// ── WHAT IS STRIPPED, AND WHY EACH ONE ─────────────────────────────────────
//   medication_id / name / dose / route  A medication list is a diagnosis by
//                                        inference. The status answer does not
//                                        need it.
//   prn_reason                           PRN reasoning is clinical judgement
//                                        about symptoms -- agitation, pain,
//                                        nausea -- and is the most revealing
//                                        free text on the record.
//   effectiveness_check                  The same, one step later.
//   refusal_reason                       A refusal's REASON is clinical and
//                                        frequently behavioural. The FACT of a
//                                        refusal is a care event; the reason is
//                                        a symptom.
//   notes                                Free text written by staff for staff.
//   administered_by                      Naming the aide to a relative serves
//                                        no family purpose and creates one.
//   supervisor_notified                  An internal escalation flag.
//   entry_type 'count'                   Controlled-substance counts, excluded
//                                        outright by the decision and by the
//                                        fact that a count is a narcotics
//                                        register, not a care event.
//   entry_type 'medication_order'        The standing order IS the medication
//                                        list.
//   entry_type 'reconciliation'          Admission/transfer medication
//                                        reconciliation, same reason.
//   entry_type 'assessment_refusal'      A refusal of medication MANAGEMENT is
//                                        a capacity/consent matter.
//
// So exactly ONE entry_type survives -- `administration` -- and from it exactly
// four fields: date, scheduled time, status, and the resident it belongs to.
//
// ── THE ALLOW-LIST IS THE MECHANISM, NOT A DENY-LIST ───────────────────────
// Every field is dropped unless it is named. A deny-list would leak the next
// field somebody adds to an administration record, silently, to an external
// party -- and that is the failure mode this file exists to make impossible.
// A probe asserts an unknown field never survives.
//
// ── CONSENT IS CHECKED HERE AND IT DEFAULTS TO OFF ─────────────────────────
// `mar_consent !== true` yields NOTHING. Not an empty list that reads as "no
// medications" -- a refusal that says consent has not been granted, because
// those are different facts and a family member shown an empty list would
// reasonably conclude their relative is on no medication.

'use strict';

// The one entry type a family member may see, and the only fields of it.
const FAMILY_ENTRY_TYPE = 'administration';
const FAMILY_FIELDS = ['date', 'time', 'status'];

// The administration statuses this engine understands. An unrecognised status
// is passed through as `unknown` rather than dropped or guessed: dropping it
// would hide a real dose event from the adherence figure, and guessing would
// report an outcome nobody recorded.
const KNOWN_STATUSES = {
  given: 'given',
  refused: 'refused',
  held: 'held',
  not_given: 'missed',
  missed: 'missed'
};

function refuse(code, message) {
  return { ok: false, error: { code: code, message: message } };
}

// ── ONE ROW, REDUCED TO WHAT MAY LEAVE ─────────────────────────────────────
function familyRow(entry) {
  if (!entry || typeof entry !== 'object') return null;
  if (entry.entry_type !== FAMILY_ENTRY_TYPE) return null;
  const d = entry.data && typeof entry.data === 'object' ? entry.data : entry;
  const out = {};
  // ALLOW-LIST. Anything not named here does not exist as far as this function
  // is concerned, including fields added to the record after this was written.
  FAMILY_FIELDS.forEach(function (f) {
    if (d[f] !== undefined && d[f] !== null) out[f] = String(d[f]);
  });
  if (!out.date && !out.time) return null;
  const raw = String(out.status || '').toLowerCase().trim();
  out.status = KNOWN_STATUSES[raw] || 'unknown';
  // The resident id is carried so a caller can scope; it is NOT free text and
  // the portal token already resolves to exactly one resident.
  out.resident_id = String(entry.resident_id || (entry.data && entry.data.resident_id) || '');
  return out;
}

// ── ADHERENCE, AND WHAT IT REFUSES TO SAY ──────────────────────────────────
// A percentage over a denominator this engine can actually see. It counts the
// administration events RECORDED; it does not know about a dose that was due
// and never recorded at all, and it says so rather than implying completeness.
// A refused dose is NOT counted as given, and a HELD dose is neither -- a hold
// is usually a clinical decision, and scoring it against the resident or the
// facility would be this app taking a view it has no basis for.
function adherence(rows) {
  const counts = { given: 0, refused: 0, held: 0, missed: 0, unknown: 0 };
  (rows || []).forEach(function (r) {
    counts[r.status] = (counts[r.status] || 0) + 1;
  });
  const scored = counts.given + counts.refused + counts.missed;
  return {
    counts: counts,
    scored_events: scored,
    // null, never 0, when there is nothing to divide by. A 0% adherence figure
    // on an empty window reads as a facility failing, which is a claim from an
    // absence.
    percent_given: scored ? Math.round((counts.given / scored) * 1000) / 10 : null,
    held_excluded: counts.held,
    limits: 'counts RECORDED administration events only. A dose that was due '
      + 'and never recorded at all is not visible to this figure, and HELD '
      + 'doses are excluded from the denominator rather than scored.'
  };
}

// ── THE ENTRY POINT ────────────────────────────────────────────────────────
// `contact` is the family record; `entries` are alf_mar rows for ONE resident.
function familyMarView(input) {
  input = input || {};
  const contact = input.contact;
  if (!contact || typeof contact !== 'object') {
    return refuse('NO_CONTACT', 'no family contact record supplied');
  }
  if (contact.active === false) {
    return refuse('CONTACT_INACTIVE', 'this family contact has been deactivated');
  }
  // CONSENT DEFAULTS TO OFF, AND ONLY AN EXPLICIT TRUE OPENS IT. null,
  // undefined, 0, '' and 'true' are all NOT consent: a string 'true' arriving
  // from a form would be truthy, which is the coercion this platform has
  // already been bitten by.
  if (contact.mar_consent !== true) {
    return refuse('NO_MAR_CONSENT',
      'medication information has not been shared with this contact. Consent '
      + 'is granted per contact by the facility and is off until it is.');
  }
  const rows = (Array.isArray(input.entries) ? input.entries : [])
    .map(familyRow)
    .filter(Boolean);
  rows.sort(function (a, b) {
    const ka = (a.date || '') + ' ' + (a.time || '');
    const kb = (b.date || '') + ' ' + (b.time || '');
    return ka < kb ? 1 : (ka > kb ? -1 : 0);
  });
  return {
    ok: true,
    resident_id: String(input.resident_id || ''),
    consent: {
      granted: true,
      granted_at: contact.consent_granted_at || null,
      granted_by: contact.consent_granted_by || null
    },
    events: rows,
    adherence: adherence(rows),
    // SAID IN THE PAYLOAD, not only in this file. A consumer that renders this
    // object should be able to tell a family member what they are NOT seeing.
    not_included: 'medication names, doses and routes; PRN reasoning; refusal '
      + 'reasons; staff notes; who administered; controlled-substance counts; '
      + 'medication orders and reconciliations. This is administration STATUS '
      + 'only, and it is read-only.'
  };
}

module.exports = {
  FAMILY_ENTRY_TYPE,
  FAMILY_FIELDS,
  KNOWN_STATUSES,
  familyRow,
  adherence,
  familyMarView
};
