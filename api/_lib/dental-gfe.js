// api/_lib/dental-gfe.js
//
// The 45 CFR 149.610(c)(1) completeness check for a SAIRNdental Good Faith
// Estimate, on the server.
//
// ── WHY THIS EXISTS ───────────────────────────────────────────────────────
// sairndental.html's issueGfe() has always refused to mark an estimate Issued
// while any federally required element is missing, and its comment says why
// better than this one could:
//
//     "REFUSED, not warned. An estimate handed to a patient missing a required
//      element is a non-compliant document that looks compliant, which is worse
//      than no document at all -- the practice believes it has met the
//      obligation and has not."
//
// That refusal was BROWSER JAVASCRIPT. The write then went to api/sd-data.js's
// generic DNT_RESOURCES handler, which validated payload.id and nothing else
// for fifteen resources, so the server stored status:'Issued' on an incomplete
// estimate without complaint.
//
// Found 2026-09-04 during a cross-path sweep, immediately after the same shape
// was found and fixed for the paediatric guardian rule. Not reachable through
// the ordinary UI -- unlike the guardian gap, which was -- so this is hardening
// rather than a live defect, and it got its own pass rather than a ride-along
// in a commit about guardians.
//
// ── WHAT THIS DOES NOT DECIDE ─────────────────────────────────────────────
// Whether a GFE is OWED at all is 149.610(b)(1)(i)-(ii), and it turns on a
// question only a person can answer: an insured patient who is not submitting a
// claim IS owed one. sairndental.html's gfeEligibility() puts that question to
// the user and does not answer it for them. This file deliberately does not
// either -- it checks the completeness of an estimate the practice has already
// decided to issue. A server that guessed eligibility would refuse legitimate
// estimates and, worse, would look authoritative doing it.

// `rec` is the GFE record, `patient` the dnt_patients data blob it names, and
// `settings` the practice's dnt_settings data blob. Returns an array of the
// missing elements, each labelled with its subparagraph, or an empty array.
//
// The labels are kept identical to sairndental.html's gfeMissing() on purpose:
// a practice that sees "(c)(1)(v) National Provider Identifier" in the app and
// a differently-worded refusal from the API would reasonably think they were
// two different problems.
function gfeMissing(rec, patient, settings) {
  const r = rec || {};
  const pt = patient || null;
  const s = settings || {};
  const miss = [];

  if (!pt || !pt.name) miss.push('(c)(1)(i) patient name');
  if (!pt || !pt.dob) miss.push('(c)(1)(i) patient date of birth');
  if (!r.primary_description) miss.push('(c)(1)(ii) description of the primary item or service');
  if (!r.lines || !r.lines.length) {
    miss.push('(c)(1)(iii) itemised list of items and services');
  } else {
    if (r.lines.some((l) => !l || !l.cdt_code)) miss.push('(c)(1)(iv) a service code on every line');
    if (r.lines.some((l) => !(Number(l && l.expected_charge) > 0))) miss.push('(c)(1)(iv) an expected charge on every line');
  }
  if (!s.gfe_legal_name) miss.push('(c)(1)(v) practice legal name');
  if (!s.gfe_npi) miss.push('(c)(1)(v) National Provider Identifier');
  if (!s.gfe_tin) miss.push('(c)(1)(v) Tax Identification Number');
  if (!s.gfe_state) miss.push('(c)(1)(v) State where services are furnished');
  if (!s.practice_address) miss.push('(c)(1)(v) location where services are furnished');
  return miss;
}

// Only an estimate being ISSUED is checked. A Draft is allowed to be
// incomplete -- that is what a draft is for, and refusing to save one would
// make the feature unusable while someone is still filling it in.
function issuedWithoutRequiredElements(rec, patient, settings) {
  const status = String((rec && rec.status) || '').trim().toLowerCase();
  if (status !== 'issued') return null;
  const miss = gfeMissing(rec, patient, settings);
  if (!miss.length) return null;
  return 'This estimate cannot be issued: 45 CFR 149.610(c)(1) still requires '
       + miss.length + ' element' + (miss.length === 1 ? '' : 's') + ' -- '
       + miss.join('; ') + '.';
}

module.exports = { gfeMissing, issuedWithoutRequiredElements };
