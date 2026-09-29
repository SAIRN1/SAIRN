"""A live probe that WRITES must write to an audit licence, or not run.

    from audit_licence import require_audit_licence
    require_audit_licence(key, tool=__file__, writes='alf_facility')

── WHY THIS IS A GUARD AND NOT A CONVENTION ────────────────────────────────
On 2026-09-28 I verified that `add_rule` strips forged identity fields. Seeing
what an endpoint STORES requires a write, so one probe rule was written to
LAW-TEST-2026 -- and DELETE was revoked platform-wide on that table in August,
so the row cannot be removed by the API, by `service_role`, or by me. It needs
sql/zz_probe_residue_delete_2026-09-28.sql and a human in the SQL editor.

One probe. One un-deletable row. On a licence somebody may be shown.

THE ARGUMENT WAS ALREADY SETTLED AND NOT APPLIED. StoneDesk's own
sql/stonedesk_recovery_admin_seed.sql says *"THE FIX IS THE LICENCE, NOT THE
PIN"*, and SAIRNroofing followed it on 2026-09-02. Two roofing probes correctly
use RF-AUDIT-2026 today. Nothing made the other seven do the same, because the
rule lived in a comment in a SQL file rather than in the code path that writes.

── THE THREE-STATE RULE ────────────────────────────────────────────────────
A key is AUDIT (`*-AUDIT-*`) -> proceed.
A key is anything else       -> COULD NOT RUN, exit 2, naming the key and the
                                seed file that mints an audit licence.
No key at all                -> COULD NOT RUN, exit 2. Not a silent skip: a
                                verification that did not run is the third state
                                CLAUDE.md is about, and a probe that returns
                                early on a missing key looks exactly like one
                                that ran and found nothing.

EXIT 2, NEVER 1. A refusal to run is not a finding about the subject.

── WHAT THIS IS NOT FOR ────────────────────────────────────────────────────
**LOADERS.** `tools/load_deadline_seed.py` and `tools/load_compliance_seed.py`
write reference rules to REAL licences because that is their entire job, and
gating them on an audit licence would break seeding on 48 jurisdictions. They are
a different class and they must NOT call this. The distinction is DECLARED per
file rather than inferred -- see tools/live_probe_residue_audit.py -- because
"is this a loader or a probe" is a fact its author knows and nothing else
reliably does. Three inference models were tried for a similar question in
tools/checker_control_check.py and all three were wrong within an hour.

── THE ALLOWLIST, AND WHY IT TAKES A REASON ────────────────────────────────
`allow=` exists for a probe that must run against a specific non-audit licence
and can justify it -- a read-only reproduction of a customer-reported defect, for
instance. It takes the KEY and a SENTENCE. A bare allowlist entry is the escape
hatch that hollows a gate out; this repo has recorded that shape on
`--rule not-citable` and on the `no-defect-record:` trailer, both of which
demand a real sentence for the same reason.
"""
import os
import re
import sys

AUDIT_KEY_RE = re.compile(r'^[A-Z]{2,6}-AUDIT-\d{4}$')
SEED_FILE = 'sql/audit_license_seed_2026-09-28.sql'
EXIT_COULD_NOT_RUN = 2

# ── AUDIT LICENCES THAT ACTUALLY EXIST, MEASURED 2026-09-28 ─────────────────
# One check_license call per key against the deployed platform, not read off a
# seed file. THE FIRST VERSION OF THIS LIST WAS WRONG IN BOTH DIRECTIONS and the
# measurement is what caught it: it named SV-AUDIT-2026, which does NOT exist,
# and MECH/LAW-AUDIT-2026, which did not exist yet either. A list of keys that
# "exist" containing one that does not is worse than no list, because the
# not-in-the-list branch below is the only thing that warns -- so a probe pointed
# at SV-AUDIT-2026 would have been told nothing and then earned 401.
#
# ── RE-MEASURED 2026-09-29, AND FOUR OF THE SIX HAD CHANGED ────────────────
# This block said "ALF / LAW / SC / MECH / SV  401 ABSENT" and the tuple below
# named two keys. Michael ran sql/audit_license_seed_2026-09-28.sql in between,
# and NOTHING HERE MOVED -- so every probe using one of the four newly-minted
# licences was told it was "audit-SHAPED but not one this file knows about",
# which is a warning that means nothing and trains a reader to ignore the one
# case that does matter.
#
# ONE check_license CALL PER KEY against the deployed platform, 2026-09-29:
#
#   RF-AUDIT-2026    200 EXISTS   (seeded 2026-09-02)
#   SD-AUDIT-2026    200 EXISTS
#   ALF-AUDIT-2026   200 EXISTS   (seeded 2026-09-28)
#   LAW-AUDIT-2026   200 EXISTS   (seeded 2026-09-28)
#   MECH-AUDIT-2026  200 EXISTS   (seeded 2026-09-28)
#   SC-AUDIT-2026    200 EXISTS   (seeded 2026-09-28)
#   SV-AUDIT-2026    401 ABSENT   -- still, and deliberately: no probe needs it
#
# THIS TUPLE IS A SNAPSHOT AND CANNOT BE ANYTHING ELSE. Deriving it at run time
# means a network call inside a guard whose whole job is to run before anything
# touches the network, and deriving it from the seed FILE would read a key named
# in that file's prose as one it mints -- SV-AUDIT-2026 appears there in a
# sentence explaining why it is NOT seeded. So it is a dated measurement, and
# the date is here so the next reader can see how old it is rather than trusting
# the sentence around it.
#
# THE FAILURE MODE IS NOISE, NOT A BYPASS: an absent key still earns its 401
# from the platform. What a stale list costs is the NOTE below meaning nothing.
KNOWN_AUDIT_KEYS = ('SD-AUDIT-2026', 'RF-AUDIT-2026', 'ALF-AUDIT-2026',
                    'LAW-AUDIT-2026', 'MECH-AUDIT-2026', 'SC-AUDIT-2026')


def is_audit_licence(key):
    return bool(AUDIT_KEY_RE.match(str(key or '').strip()))


def require_audit_licence(key, tool='', writes='', allow=None):
    """Return the key, or exit 2 COULD NOT RUN with the reason.

    `allow` is {key: 'a real sentence'} -- never a bare list.
    """
    k = str(key or '').strip()
    name = os.path.basename(str(tool)) or 'this probe'
    what = (' It writes to %s.' % writes) if writes else ''

    if not k:
        sys.stderr.write(
            'COULD NOT RUN: %s needs a licence key and none was given.%s\n'
            'A verification that did not run is a THIRD STATE, not a pass -- and a '
            'probe that returns early on a missing key looks exactly like one that '
            'ran and found nothing.\n' % (name, what))
        raise SystemExit(EXIT_COULD_NOT_RUN)

    if is_audit_licence(k):
        if k not in KNOWN_AUDIT_KEYS:
            # Shape is right, existence is not confirmed. Say so and proceed --
            # refusing a correctly-shaped new audit licence would make minting
            # one require editing this file first.
            sys.stderr.write(
                'NOTE: %s is audit-SHAPED but is not one this file knows about '
                '(%s). Proceeding; if it answers 401 INVALID_LICENSE the seed has '
                'not been run.\n' % (k, ', '.join(KNOWN_AUDIT_KEYS)))
        return k

    if allow and k in allow and str(allow[k]).strip():
        sys.stderr.write('ALLOWED, non-audit licence, stated out loud: %s -- %s\n'
                         % (k, allow[k]))
        return k

    sys.stderr.write(
        'COULD NOT RUN: %s writes, and %r is not an audit licence.%s\n'
        '\n'
        'A probe that writes to a demo-facing licence leaves residue on the thing a\n'
        'prospect is shown, and some of it CANNOT BE REMOVED -- DELETE is revoked\n'
        'platform-wide on the reference tables, so a stray row needs a human in the\n'
        'SQL editor. That happened on 2026-09-28 and is why this guard exists.\n'
        '\n'
        'Use one of: %s\n'
        'If one is missing, %s mints it. Bootstrap it through the app\'s own\n'
        '`bootstrap` action afterwards -- the seed deliberately carries no PIN.\n'
        '\n'
        'If this probe genuinely must use %s, pass it in `allow=` WITH A SENTENCE\n'
        'saying why. A bare exemption is the escape hatch that hollows a gate out.\n'
        % (name, k, what, ', '.join(KNOWN_AUDIT_KEYS), SEED_FILE, k))
    raise SystemExit(EXIT_COULD_NOT_RUN)
