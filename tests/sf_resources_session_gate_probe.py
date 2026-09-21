"""SF_RESOURCES is served with NO employee session check. Report-only.

    python tests/sf_resources_session_gate_probe.py

Exit 0 by design -- this is a FINDING somebody has to decide about, not a gate.

-- THE FINDING ---------------------------------------------------------------
api/sd-data.js's SF_RESOURCES dispatcher serves 35 SAIRNfreedom resources,
THREE OF THEM TIER A -- sf_accounts, sf_ledger, sf_vendor_prices -- and neither
its read branch nor its write branch calls verifySessionToken, appears in the
shared SD_SESSION_GATED table, or can answer 401/403 at all. The licence key is
the entire authorisation, and the licence key is shipped to the browser and
readable by anyone who can open the app.

THIS IS THE SHAPE THE PLATFORM ALREADY HAS A RECORD OF. `law_trusttx` --
attorney IOLTA client trust money -- dispatched on licHash alone until
2026-09-16, and SD_SESSION_GATED's own comment describes it: "not a session
that had gone stale ... NO SESSION CHECK EXISTED. The licence key, which is
shipped to the browser and readable by anyone who can open the app, was the
whole authorisation." The fix there was one line in that table. SF was not
swept with it.

-- WHAT THIS IS NOT ----------------------------------------------------------
NOT a cross-tenant leak. api/sd-data-cross-tenant-dispatchers.test.js drives
these three and they filter by license_hash correctly -- tenant A cannot read
tenant B's ledger. The question here is the other one: WHICH PEOPLE INSIDE
tenant A may read tenant A's ledger, and the answer today is "anyone holding
the licence key", with no employee identity, no role, and nothing in the audit
trail saying who.

-- WHY IT IS REPORT-ONLY AND NOT A FIX ---------------------------------------
Adding sf_* to SD_SESSION_GATED would refuse every SAIRNfreedom call that does
not carry a session token -- which is every call the app makes today if it has
no sign-in flow wired to these resources. That is a product decision with a
blast radius (does SAIRNfreedom have employee sessions at all? is any of this
reached by an unauthenticated public path by design?), not a one-line repair,
and it is Michael's to make rather than a session's to assume. Measured and
recorded here so the decision is made against a number.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, 'api', 'sd-data.js')

# The two markers a session-gated branch on this platform carries. Named rather
# than inlined so the report can say WHICH one is missing.
MARKERS = ('verifySessionToken', 'tokenFromRequest')


def main():
    raw = io.open(SRC, encoding='utf-8', errors='replace').read()
    src = raw.replace('\r\n', '\n')

    i = src.index('const SF_RESOURCES = {')
    j = src.index('};', i)
    members = re.findall(r'^\s*([a-z_][a-z0-9_]*)\s*:', src[i:j], re.M)
    members += re.findall(r',\s*([a-z_][a-z0-9_]*)\s*:', src[i:j])
    members = sorted(set(members))

    # Tier A membership comes from the register, never a second copy here.
    tiers = io.open(os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md'),
                    encoding='utf-8', errors='replace').read()
    tier_a = set(re.findall(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*A\*\*\s*\|', tiers, re.M))
    if not tier_a:
        sys.stderr.write('COULD NOT TELL: the tier register yielded zero Tier A rows.\n')
        return 2
    sf_tier_a = sorted(set(members) & tier_a)

    print('SF_RESOURCES SESSION GATE -- report-only')
    print('')
    print('  resources served by the dispatcher : %d' % len(members))
    print('  of those, TIER A                   : %d  %s'
          % (len(sf_tier_a), ', '.join(sf_tier_a)))
    print('')

    findings = 0
    for action in ('read', 'write'):
        at = src.index("if (SF_RESOURCES[resource] && action === '%s')" % action)
        end = src.index('\n    }', at)
        branch = src[at:end]
        present = [m for m in MARKERS if m in branch]
        refuses = bool(re.search(r'status\((401|403)\)', branch))
        gated = bool(present) or refuses
        print('  %-5s branch: session markers=%-12s 401/403=%-5s  -> %s'
              % (action, ','.join(present) or 'NONE', refuses,
                 'GATED' if gated else 'NO SESSION CHECK'))
        if not gated:
            findings += 1

    # The shared table is the other place a gate could live, so it is checked
    # rather than assumed absent.
    k = src.index('const SD_SESSION_GATED = {')
    m = src.index('};', k)
    table = src[k:m]
    in_table = sorted(set(re.findall(r"'(sf_[a-z0-9_]+)'", table)))
    print('')
    print('  SD_SESSION_GATED entries naming an sf_ resource: %s'
          % (', '.join(in_table) if in_table else 'NONE'))
    print('  (law_trusttx was added to that table on 2026-09-16 for exactly this')
    print("   defect class -- see the table's own comment. SF was not swept with it.)")

    if not findings:
        print('')
        print('NOT REPRODUCED -- both branches now carry a session check. This')
        print('finding appears to be closed; re-read the row in the open-work index.')
        return 0

    print("""
FINDING (HIGH, ACCESS CONTROL) -- %d of 2 SF_RESOURCES branches have no
employee session check, on a dispatcher serving %d Tier A resources.

  WHAT SOMEBODY NEEDS TO REACH IT: the licence key. It is shipped to the
  browser and readable by anyone who can open the app, so "holds the licence"
  is not a meaningful restriction on WHO inside the business may read or write
  the general ledger, the chart of accounts and vendor pricing.

  WHAT IS NOT AT RISK: the tenant boundary. These three filter by license_hash
  correctly and that is now asserted -- see
  api/sd-data-cross-tenant-dispatchers.test.js. One tenant cannot reach
  another's rows. This is about identity WITHIN a tenant.

  AND THE AUDIT HALF, which does not show up as a refusal: a write with no
  session has no employee_id to record, so the ledger cannot say who made an
  entry. On sf_ledger that is the question an audit asks first.

  NOT FIXED HERE, DELIBERATELY. Adding sf_* to SD_SESSION_GATED refuses every
  call that does not carry a session token, and whether SAIRNfreedom wires one
  to these resources today is a product fact this probe does not know. Decide
  the scope first; the repair after that is one line in the table, the same one
  law_trusttx took.""" % (findings, len(sf_tier_a)))

    print('\n%d finding(s). Report-only: exit 0 by design.' % findings)
    return 0


sys.exit(main())
