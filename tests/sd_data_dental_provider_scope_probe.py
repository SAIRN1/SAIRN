"""api/sd-data-dental-provider-scope.test.js must go RED when the scope is undone.

Run: python tests/sd_data_dental_provider_scope_probe.py

WHY THIS SUITE. dnt_patients, dnt_referrals, dnt_gfe, dnt_txplans and
dnt_denial are PHI. The gate decides which patients a dentist sees, and its
failure mode is not a crash -- it is a wider list than the role is entitled to,
which looks exactly like a practice with more patients. Nothing in the response
distinguishes "scoped correctly" from "scope silently dropped".

THE SUITE ALSO PINS A DECISION THAT WENT THE OTHER WAY, and that is the part a
control has to protect from a well-meaning tightening: an UNLINKED referral is
VISIBLE to a scoped provider, not hidden. Michael's 2026-09-11 call, made after
the fail-closed version was measured -- a referral nobody can see is a patient
who does not get seen. A suite made only of "must refuse" arms would be
perfectly happy with that regression, which is why mutations 7 and 8 break the
permissive direction instead.

ONE PROPERTY PER MUTATION:

  1. the patient scope stops applying to scoped roles -- practice-wide PHI for
     a hygienist;
  2. an UNLINKED sign-in gets an empty 200 instead of 403 PROVIDER_NOT_LINKED,
     which is the fabricated-zero shape the suite's own comment names;
  3. an unprovisioned provider registry 403s the user instead of answering
     provisioned:false -- blaming the caller for a setup step;
  4. a failed scope lookup falls through to an unfiltered read, which is
     could-not-tell folded into a pass on PHI;
  5. the provider roster stops being owner-only, so anyone who can edit it can
     grant themselves a patient list;
  6. two logins may link to one provider, making the scope depend on row order;
  7. THE OTHER DIRECTION -- the unlinked-referral visibility is reverted to
     fail-closed, which no refusal arm would notice;
  8. THE OTHER DIRECTION AGAIN -- the widening 7 guards against, applied to
     dnt_patients, where it would make every unlinked patient practice-wide.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-dental-provider-scope.test.js')
SRC = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. the patient scope stops applying, so a scoped role reads the whole "
     "practice's PHI",
     SRC,
     "      if (DNT_PATIENT_SCOPED_RESOURCES[resource] && !DNT_PATIENT_BROAD_READ_ROLES[dntSess.role]) {",
     "      if (false && DNT_PATIENT_SCOPED_RESOURCES[resource] && !DNT_PATIENT_BROAD_READ_ROLES[dntSess.role]) {"),
    # THE FABRICATED ZERO. The suite's own comment calls an empty 200 here
    # indistinguishable from a practice with no patients -- Guardian 0b.
    # THE ANCHOR RUNS TO THE dntScopeIds LINE, and that is not padding. The
    # `if (!link.providerId)` + 403 block appears TWICE -- the patient-read
    # branch here and the appointments branch at :11365 -- and the narrow
    # anchor reported ANCHOR-2. An ambiguous anchor plants in whichever came
    # first and then asserts something about a line nobody chose.
    ("2. an UNLINKED sign-in gets an empty 200 instead of 403 "
     "PROVIDER_NOT_LINKED",
     SRC,
     "        if (!link.providerId) {\n"
     "          res.status(403).json({\n"
     "            error: {\n"
     "              code: 'PROVIDER_NOT_LINKED',\n"
     "              message: 'Your sign-in is not linked to a provider yet, so no patient records are shown. "
     "Ask the practice owner to open the Providers panel and link your login to your provider record.'\n"
     "            }\n"
     "          });\n"
     "          return;\n"
     "        }\n"
     "        dntScopeIds = await dntPatientIdsForProvider(link.providerId);",
     "        if (!link.providerId) {\n"
     "          res.status(200).json({ ok: true, data: [] });\n"
     "          return;\n"
     "        }\n"
     "        dntScopeIds = await dntPatientIdsForProvider(link.providerId);"),
    ("3. an unprovisioned provider registry 403s the caller rather than "
     "answering provisioned:false",
     SRC,
     "        if (!link.provisioned) {\n          res.status(200).json({ ok: true, data: [], provisioned: false });",
     "        if (!link.provisioned) {\n          res.status(403).json({ error: { code: 'PROVIDER_NOT_LINKED', message: 'Not linked' } });"),
    # COULD-NOT-TELL FOLDED INTO A PASS, on PHI. The lookup failing means the
    # patient list is UNKNOWN; reading unfiltered is the widest possible answer.
    ("4. a failed scope lookup falls through to an UNFILTERED read instead of "
     "refusing",
     SRC,
     "        if (!dntScopeIds) { res.status(502).json({ error: { code: 'SCOPE_LOOKUP_FAILED', message: 'Could not determine your patient list. Try again.' } }); return; }",
     "        if (!dntScopeIds) { dntScopeIds = null; }"),
    ("5. the provider roster stops being owner-only -- anyone who can edit it "
     "can grant themselves a patient list",
     SRC,
     "      if (resource === 'dnt_providers' && !DNT_MANAGEMENT_ROLES[dntWSess.role]) {",
     "      if (false && !DNT_MANAGEMENT_ROLES[dntWSess.role]) {"),
    ("6. two logins may link to one provider, so the scope is decided by row "
     "order",
     SRC,
     "      if (resource === 'dnt_providers' && payload && payload.linked_employee_id) {",
     "      if (false && payload && payload.linked_employee_id) {"),
    # ── 7 AND 8 ARE THE OTHER DIRECTION ────────────────────────────────────
    # Every mutation above breaks a REFUSAL, and a gate that refused everything
    # would satisfy all six. These two break the PERMISSION, which is where a
    # deliberate decision quietly gets tightened back into the defect it fixed.
    # THE MAP IS THE DECISION. DNT_UNLINKED_VISIBLE_RESOURCES exists for one
    # entry, and emptying it is exactly the fail-closed version Michael's
    # 2026-09-11 call replaced -- no error, no refusal, one role simply stops
    # seeing records another role can see.
    ("7. the unlinked-referral visibility is reverted to fail-closed, so the "
     "treating provider stops seeing referrals the front desk filed",
     SRC, "const DNT_UNLINKED_VISIBLE_RESOURCES = { dnt_referrals: true };",
     "const DNT_UNLINKED_VISIBLE_RESOURCES = {};"),
    ("8. and the widening THAT decision was scoped against -- dnt_patients "
     "treated the same way, making every unlinked patient practice-wide",
     SRC, "const DNT_PATIENT_SCOPED_RESOURCES = { dnt_patients: 'id',",
     "const DNT_PATIENT_SCOPED_RESOURCES = { dnt_patients: 'zz_no_such_key',"),
]

if __name__ == '__main__':
    sys.exit(run_probe(SUITE, MUTATIONS,
                       title='negative control -- api/sd-data-dental-provider-scope.test.js '
                             'must refuse each way the PHI scope can be undone'))
