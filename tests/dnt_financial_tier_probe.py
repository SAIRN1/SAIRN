"""api/sd-data-dental-financial-tier.test.js must REFUSE, not merely agree.

Run: python tests/dnt_financial_tier_probe.py

TIER A, AND THE SUITE HAD NEVER BEEN DRIVEN. This suite guards the SAIRNdental
HIPAA minimum-necessary financial tier over seven Tier A resources --
`dnt_ar`, `dnt_charges`, `dnt_coverage_rules`, `dnt_denial`, `dnt_gfe`,
`dnt_payments`, `dnt_revenue` -- and had no negative control. Measured
2026-09-15: 7 of 154 JavaScript suites on this platform have one.

WHY THIS ONE. Unlike most, it EXECUTES the handler rather than matching its
text, so its assertions can be checked against real behaviour. The three things
it says it deliberately asserts are each a way the gate could look correct and
be wrong, and each is planted below:

  * a refused read must be a 403 and NEVER a 200 with an empty list -- an empty
    list is indistinguishable from a practice that has taken no payments, and
    the client renders a real zero from a permission check;
  * a refused read must not REACH THE NETWORK -- if the gate ran after the
    query, the financial rows have already left the database whatever the
    response says;
  * the clinical resources must NOT be swept into the financial tier, which
    would lock providers out of the records they are supposed to see.

A suite that has only ever been green is a suite whose behaviour nobody knows.
"""
# REQUIREMENT: a dental financial tier is read from the record rather than inferred, so
#   a patient cannot be moved between tiers by a display rule
#
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('api', 'sd-data-dental-financial-tier.test.js')
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. the READ gate is removed entirely -- a provider reads practice "
     "financials",
     API,
     "      if (DNT_FINANCIAL_RESOURCES[resource] && "
     "!DNT_FINANCIAL_ROLES[dntSess.role]) {\n"
     "        res.status(403).json({ error: { code: 'ROLE_NOT_PERMITTED', "
     "message: 'Financial records are limited to the practice owner and front "
     "desk' } });",
     "      if (false) {\n"
     "        res.status(403).json({ error: { code: 'ROLE_NOT_PERMITTED', "
     "message: 'Financial records are limited to the practice owner and front "
     "desk' } });"),

    ("2. THE FABRICATED ZERO: the refusal becomes a 200 with an empty list, "
     "which the client renders as a practice that has collected nothing",
     API,
     "        res.status(403).json({ error: { code: 'ROLE_NOT_PERMITTED', "
     "message: 'Financial records are limited to the practice owner and front "
     "desk' } });\n        return;\n      }\n      // Provider-scoped patient "
     "read.",
     "        res.status(200).json({ ok: true, data: [] });\n"
     "        return;\n      }\n      // Provider-scoped patient read.",),

    ("3. the role set widens to every dental role, so the tier exists and "
     "gates nobody",
     API,
     # ANCHOR UPDATED 2026-09-24: the role map moved inside roleSet() when the
     # plain-object-literal prototype hole was closed platform-wide, and this
     # arm sat on the old literal reporting ANCHOR-0 at origin/main -- a probe
     # arm testing nothing while looking armed.
     "    const DNT_FINANCIAL_ROLES = roleSet({ owner: true, frontdesk: true });",
     "    const DNT_FINANCIAL_ROLES = roleSet({ owner: true, frontdesk: true, "
     "provider: true });"),

    ("4. ONE resource silently leaves the tier -- the smallest possible diff, "
     "and A/R is the one a provider has least reason to see",
     API,
     "      dnt_ar: true, dnt_revenue: true, dnt_coverage_rules: true,",
     "      dnt_revenue: true, dnt_coverage_rules: true,"),

    ("5. good faith estimates leave the tier -- a priced document naming a "
     "patient and their date of birth",
     API,
     "      dnt_gfe: true\n    };",
     "    };"),

    ("6. the refusal loses its code, so the client cannot tell the financial "
     "tier from the patient-scope gate and the two collapse into one "
     "undifferentiated denial",
     API,
     "      if (DNT_FINANCIAL_RESOURCES[resource] && "
     "!DNT_FINANCIAL_ROLES[dntSess.role]) {\n"
     "        res.status(403).json({ error: { code: 'ROLE_NOT_PERMITTED',",
     "      if (DNT_FINANCIAL_RESOURCES[resource] && "
     "!DNT_FINANCIAL_ROLES[dntSess.role]) {\n"
     "        res.status(403).json({ error: { code: 'FORBIDDEN',"),

    ("7. a CLINICAL resource is swept into the financial tier -- the 'wrong "
     "split is worse than no split' failure, which locks a treating clinician "
     "out of the records they are supposed to see",
     API,
     "    const DNT_FINANCIAL_RESOURCES = {\n"
     "      dnt_charges: true, dnt_payments: true, dnt_denial: true,",
     "    const DNT_FINANCIAL_RESOURCES = {\n"
     "      dnt_appointments: true,\n"
     "      dnt_charges: true, dnt_payments: true, dnt_denial: true,"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='SAIRNdental financial tier -- the suite must refuse a gate that '
              'has stopped gating seven Tier A resources'))
