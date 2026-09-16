"""tests/phi_cache_scoped_to_user.js must REFUSE, not merely agree.

Run: python tests/phi_cache_scope_probe.py

TIER A, AND THE MOST DIRECTLY HARMFUL SUITE WITHOUT A CONTROL. This one guards
PHI on a SHARED DEVICE -- the ordinary case in both industries it covers: one
station tablet at a nurses' desk, one office machine in a home-care agency.
`alf_clients` and `sen_clients` are Tier A, and the defect it was written for
put residents a second user is not assigned to BOTH on screen AND into an
outbound AI prompt that told the model the list was already scoped server-side.

Measured 2026-09-15: 13 of 152 suites on this platform have a negative control.

WHAT IS PLANTED. The mechanism is purge-on-identity-change, and every mutation
below removes one property of it while leaving something that still looks like
a guard:

  * the scoped list loses the PHI key itself -- the purge still runs and clears
    everything except the one that matters;
  * a FIRST sign-in stops being exempt, so the additive merge is thrown away
    every morning. That is the failure the suite's own arm 3 exists for: a fix
    that purges on every entry passes every "no leak" assertion and breaks the
    offline case;
  * the identity key drops the ROLE, so the same person returning with reduced
    permissions keeps the wider roster they hydrated as an owner;
  * the purge is called but its result ignored, which reads as correct in review
    because the call is right there.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'phi_cache_scoped_to_user.js')
CARE = 'sairncare.html'
SENIOR = 'sairnsenior.html'

MUTATIONS = [
    ("1. SAIRNcare: the PHI key leaves the scoped list -- the purge still runs "
     "and clears everything except the resident roster",
     CARE,
     "var ALF_SCOPED_CACHES = ['alf_clients','alf_staff','alf_mar','alf_billing',",
     "var ALF_SCOPED_CACHES = ['alf_staff','alf_mar','alf_billing',"),

    ("2. SAIRNsenior: the same key leaves its list, checked separately because "
     "two apps sharing a shape is not two apps sharing a fix",
     SENIOR,
     "var SEN_SCOPED_CACHES = ['sen_clients',",
     "var SEN_SCOPED_CACHES = ["),

    ("3. SAIRNcare: a FIRST sign-in is no longer exempt, so the additive merge "
     "is thrown away every morning -- the offline device loses rows the server "
     "has not seen",
     CARE,
     "  return prev !== null && prev !== who;",
     "  return true;"),

    ("4. SAIRNcare: the identity key drops the ROLE, so the same person "
     "returning with reduced permissions keeps the wider roster they hydrated "
     "as an owner",
     CARE,
     "  var who=(d&&d.employee_id||'')+'|'+(d&&d.role||'');",
     "  var who=(d&&d.employee_id||'');"),

    ("5. SAIRNcare: the purge is CALLED and its trigger ignored -- reads as "
     "correct in review because the call is right there",
     CARE,
     "  if(alfCacheOwnerChanged(d))alfPurgeScopedCaches();\n  alfSession=",
     "  alfCacheOwnerChanged(d);\n  alfSession="),

    ("6. SAIRNcare: the purge body empties, so the list is right and nothing "
     "is removed",
     CARE,
     "  ALF_SCOPED_CACHES.forEach(function(k){try{localStorage.removeItem(k);}"
     "catch(e){}});",
     "  /* nothing */"),

    ("7. SAIRNcare: the owner marker stops being WRITTEN, so every sign-in "
     "compares against the same stale value and the second user never "
     "registers as a change",
     CARE,
     "  try{localStorage.setItem('alf_cache_owner',who);}catch(e){}",
     "  /* not recorded */"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='PHI cache scope -- the suite must refuse a purge that has '
              'stopped purging the roster on a shared device'))
