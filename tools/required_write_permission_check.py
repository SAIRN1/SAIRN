#!/usr/bin/env python
# OWNER: hank
"""Is every file a session is REQUIRED to write inside the set it is PERMITTED to?

    python tools/required_write_permission_check.py
    python tools/required_write_permission_check.py --quiet

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY -- it records a
structural contradiction between two gates; it does not change either.

── THE DEFECT IT EXISTS FOR ────────────────────────────────────────────────
Two gates, each correct on its own, deadlocked one role:

  tools/tier_a_review_gate.py       DEMANDS a record in docs/tier-a-reviews.json
  tools/hover_auditor_scope_gate.py REFUSES that path from the auditor's clone

The hover auditor could neither push nor record. It fired at H2 seq 416 and
again at seq 422, and the second time the record was written ON DISK to satisfy
the push gate and then reset because it could not be committed -- so the gate was
satisfied by something that did not persist, which is worse than either outcome
alone.

9b2735fa removed the one TRIGGER that was firing, by excluding auditor tooling
from the Tier A content scan. **It did not remove the requirement**, and it
could not answer the general question, which nothing on this platform was
asking: a gate can demand a write that another gate forbids, and the two are
individually correct the whole time. The next gate that demands a record meets
the same wall. This is that question, asked on a cadence.

── HOW IT ANSWERS IT ───────────────────────────────────────────────────────
REQUIREMENTS is a declared table -- a gate's demand is a judgement about what
that gate does, and deriving it from source would mean parsing intent. What is
NOT left to judgement is whether the table is still true: every entry names an
ANCHOR string that must still appear in the source of the tool that imposes it,
and a missing anchor is a refusal rather than a silently dropped row. That is
the same shape SKIP_REASONS uses in the gate this check is about.

PERMISSION is not declared. It is asked of the real oracle,
tools/hover_auditor_scope_gate.py, through the AuditorScope class it exports --
so this check cannot drift from what the gate actually enforces. If that module
cannot be imported, this check exits 2 and reports NOTHING, because "no
findings" from a check with no oracle is the exact shape it exists to catch
(PR §1.11).

── WHAT IT CAN AND CANNOT SEE ──────────────────────────────────────────────
  IT CAN SEE   a declared requirement that a named session is not permitted to
               satisfy, and a requirement whose anchor has gone stale.

  IT CANNOT SEE a requirement nobody has declared here. The table is hand-built
               and is the whole population -- so a clean run says the DECLARED
               requirements are satisfiable and says nothing about a gate added
               yesterday. It also cannot see a requirement that is conditional
               in a way the trigger text only describes: it reports that the
               PAIR is contradictory, not that the contradiction will be reached
               on any particular push. And it knows nothing about permissions
               outside this repo -- a clone's filesystem, a remote, a token.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, 'tools')
sys.path.insert(0, TOOLS)

CRITERIA_VERSION = '2026-09-30.1'

# ── THE DECLARED REQUIREMENTS ───────────────────────────────────────────────
# `path` may contain <session>, substituted per session before the permission
# question is asked -- a per-clone requirement is still a requirement.
REQUIREMENTS = (
    {'path': 'docs/tier-a-reviews.json',
     'required_by': 'tools/tier_a_review_gate.py',
     'anchor': 'tier_a_review_gate.py --open',
     'trigger': 'a push whose diff names a Tier A resource on a changed line, '
                'or touches a registered coding rule',
     'why': 'the gate REFUSES the push until an obligation record exists, and '
            'the record lives in that file'},
    {'path': 'docs/defect-density-register.json',
     # THE FIRST VERSION OF THIS ROW NAMED THE WRONG TOOL -- sairn_push_gate_hook
     # .py -- and the anchor check refused the whole run before any verdict was
     # printed. That is the row working: a hand-built table is wrong the moment
     # somebody guesses which gate does what, and guessing is exactly what a
     # table invites. The demander is register_feed_gate.py, confirmed by the
     # refusal text it prints.
     'required_by': 'tools/register_feed_gate.py',
     'anchor': 'defect_register.py --add',
     'trigger': 'a push containing a commit that closes a defect and cites no '
                'register record',
     'why': 'the push gate REFUSES until the defect is recorded, or until the '
            'commit carries a no-defect-record sentence'},
    {'path': '.claude/claims/<session>.json',
     'required_by': 'tools/sairn_claim.py',
     # NOT the bare word 'claims', which appears in prose all over that file and
     # would go on matching long after the requirement had moved. This is the
     # line that builds the per-session path.
     'anchor': "CLAIM_DIR = os.path.join(REPO, '.claude', 'claims')",
     'trigger': 'starting any claimed work -- PR 2.2, a claim is not written '
                'until it is committed',
     'why': 'a claim that is not committed is invisible to every other clone, '
            'so the commit is part of the requirement rather than a follow-up'},
)

# Sessions with no gate restricting what they may write. Declared rather than
# inferred from the absence of a rule: "nothing forbids it" and "nobody has
# written the rule yet" look identical from here, and only the first is a pass.
UNRESTRICTED_NOTE = ('no gate on this platform restricts what a build session '
                     'may write; the claim record coordinates them instead')


def _oracle():
    """tools/hover_auditor_scope_gate.py, or None.

    None means COULD NOT RUN, never "permitted". Without the gate this check
    cannot tell a forbidden path from an allowed one, and reporting no findings
    then would be the defect it exists to catch.
    """
    try:
        import hover_auditor_scope_gate as g
        if not hasattr(g, 'AuditorScope') or not hasattr(g, 'violations'):
            return None
        return g
    except Exception:                                          # noqa: BLE001
        return None


def sessions():
    """Every session this platform has a claim file for, plus the auditors.

    Derived from .claude/claims/ rather than listed, so a session added to the
    platform is checked on the day it appears rather than on the day somebody
    remembers this file.
    """
    d = os.path.join(REPO, '.claude', 'claims')
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        m = re.match(r'^([a-z][a-z0-9_-]{1,31})\.json$', fn)
        if m:
            out.append(m.group(1))
    return out


def permitted(session, path):
    """May `session` write `path`? Raises CouldNotTell if the oracle is absent."""
    g = _oracle()
    if g is None:
        raise RuntimeError('permission oracle unavailable')
    if not g.AuditorScope.is_auditor_session(session):
        # UNRESTRICTED, and it is declared above rather than assumed here.
        return True
    _allowed, refused = g.violations([path], g.AuditorScope(session))
    return not refused


def stale_anchors():
    """[(requirement path, required_by, anchor)] whose anchor is gone.

    A declared table rots. This is what turns "the requirement was removed
    upstream" from a finding nobody can act on into a refusal that names the
    line to re-derive.
    """
    bad = []
    for r in REQUIREMENTS:
        src = os.path.join(REPO, r['required_by'].replace('/', os.sep))
        if not os.path.isfile(src):
            bad.append((r['path'], r['required_by'], 'FILE MISSING'))
            continue
        body = io.open(src, encoding='utf-8', errors='replace').read()
        if r['anchor'] not in body:
            bad.append((r['path'], r['required_by'], r['anchor']))
    return bad


def scan():
    """[{session, path, required_by, trigger, permitted}] for every pair."""
    rows = []
    for s in sessions():
        for r in REQUIREMENTS:
            p = r['path'].replace('<session>', s)
            rows.append({'session': s, 'path': p,
                         'required_by': r['required_by'],
                         'trigger': r['trigger'], 'why': r['why'],
                         'permitted': permitted(s, p)})
    return rows


def main(argv):
    quiet = '--quiet' in argv

    g = _oracle()
    if g is None:
        print('COULD NOT RUN -- tools/hover_auditor_scope_gate.py could not be '
              'imported, or no longer exports AuditorScope and violations().')
        print('  That module IS the permission oracle. Without it this check '
              'cannot tell a forbidden path from an allowed one, and reporting '
              '"no findings" would be the exact shape it exists to catch.')
        return 2

    stale = stale_anchors()
    if stale:
        print('COULD NOT RUN -- %d declared requirement(s) no longer anchor in '
              'the tool that imposes them. NOTHING was judged:' % len(stale))
        for path, by, anchor in stale:
            print('  ! %s required by %s -- anchor %r not found' % (path, by, anchor))
        print('  Re-derive the requirement from the tool, or remove the row. A '
              'table that has stopped describing the gates is worse than none.')
        return 2

    rows = scan()
    bad = [r for r in rows if not r['permitted']]
    ses = sessions()

    if not quiet:
        print('REQUIRED-VS-PERMITTED WRITES -- criteria %s' % CRITERIA_VERSION)
        print('  REQUIREMENTS:%d  (declared, and each anchored in its tool)'
              % len(REQUIREMENTS))
        print('  SESSIONS_CHECKED:%d  %s' % (len(ses), ', '.join(ses)))
        print('  PAIRS:%d   FINDINGS:%d' % (len(rows), len(bad)))
        print()

    if bad:
        print('CONTRADICTORY PAIRS -- a gate demands a write another gate forbids:')
        for r in bad:
            print('  ! %s is REQUIRED to write %s' % (r['session'], r['path']))
            print('      required by : %s' % r['required_by'])
            print('      triggered by: %s' % r['trigger'])
            print('      because     : %s' % r['why'])
            print('      permitted   : NO -- tools/hover_auditor_scope_gate.py '
                  'refuses it from that clone')
        print()
        print('  NEITHER GATE IS WRONG. That is what makes this hard to see from '
              'inside either one, and it is why the check is a separate tool '
              'rather than an arm in one of them.')

    if not quiet:
        print('NOTE: the requirement table is HAND-BUILT and is the whole '
              'population, so a clean run says the DECLARED requirements are '
              'satisfiable and says nothing about a gate added yesterday. It '
              'cannot see a requirement nobody has declared here, it reports '
              'that a PAIR is contradictory rather than that any particular '
              'push will reach it, and it knows nothing about permissions '
              'outside this repo.')

    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
