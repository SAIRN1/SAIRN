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
INVESTIGATED 2026-09-21, AND THE ANSWER IS THAT THE GATE MUST NOT BE WIRED YET.
The first version of this file said the blast radius was unknown. It is not:

  * sairnfreedom.html has ONE transport, sfData() at :1716, and it sends
    `Authorization: Bearer <licence>` and NOTHING ELSE. No X-SD-Auth header
    exists anywhere in the file. Every other gated app sends one.
  * `sairnfreedom` is not in api/_lib/auth.js's ROLES_BY_APP, so no session
    token CAN be signed for it -- signSessionToken throws on an unknown app.
  * there is no api/sf-auth.js. Sixteen other apps have their own -auth.js.
  * there is no sf_employee_auth table in sql/ and no reference to one
    anywhere in api/sd-data.js.
  * the nine auth-shaped hits in sairnfreedom.html are all about DOCUMENT
    SIGNING KEYS -- cryptographic signatures on posts -- not employee sessions.

DRIVEN, not reasoned: adding `sf_accounts` to SD_SESSION_GATED in memory and
replaying exactly what sfData() sends answers

    403 FORBIDDEN "A valid employee session is required - sign in first"

so wiring the gate today locks every real call out of the general ledger. The
repair is NOT one line in that table; the table entry is the LAST step of four.
Scoped as its own item -- see the open-work row -- rather than guessed at.
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

  NOT FIXED, AND NOW FOR A MEASURED REASON RATHER THAN AN UNKNOWN ONE. The
  client cannot send a session token: there is no api/sf-auth.js, no
  sf_employee_auth table, no `sairnfreedom` entry in ROLES_BY_APP, and no
  X-SD-Auth header anywhere in sairnfreedom.html. Wiring the table entry today
  answers 403 to every real call -- driven, not assumed.

  FOUR PIECES, IN THIS ORDER, and the table entry is the LAST:
    1. sql/sairnfreedom_employee_auth_schema.sql   the roster and PIN store
    2. `sairnfreedom` in api/_lib/auth.js ROLES_BY_APP, with its real roles
    3. api/sf-auth.js                              sign-in, lockout, set_active
    4. sairnfreedom.html sends X-SD-Auth on sfData()
    5. THEN sf_* in SD_SESSION_GATED -- one line, and only then

  Steps 1-4 are sairn-employee-auth-scaffold's whole subject and that skill
  says thirteen apps already ship this; SAIRNfreedom is not one of them.""" % (findings, len(sf_tier_a)))

    print('\n%d finding(s). Report-only: exit 0 by design.' % findings)
    return 0


sys.exit(main())
