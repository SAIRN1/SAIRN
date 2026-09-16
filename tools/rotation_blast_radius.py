"""Item 61 -- rotation and scope are TWO controls, and neither substitutes for the other.

    python tools/rotation_blast_radius.py
    python tools/rotation_blast_radius.py --fixtures   # blind lock, reads no register
    python tools/rotation_blast_radius.py --json

Exit 0 when both columns are clean, 1 on a finding, 2 when the register could
not be read. REPORT ONLY.

── WHY TWO NUMBERS AND NEVER ONE ──────────────────────────────────────────────
The documented failure mode is treating one as the other:

  A FRESHLY-ROTATED OVERPRIVILEGED CREDENTIAL IS STILL DANGEROUS. Rotation
  shortens the window in which a leaked secret works. It does nothing at all
  about what that secret can reach while it does work.

  A TIGHTLY-SCOPED NEVER-ROTATED CREDENTIAL IS A DIFFERENT PROBLEM, not a
  smaller version of the same one. Scope bounds the blast radius; it says
  nothing about how long an attacker keeps the access.

So this prints two independent columns and REFUSES to combine them into a
posture score. `docs/2026-09-13-cross-domain-disciplines.md` §2 is the general
form of the same rule: accuracy and stability are two numbers, and one figure
covering both is a figure that hides whichever half is worse.

── THE THIRD LIST, WHICH IS NOT A THIRD NUMBER ────────────────────────────────
Identities that are BOTH broadly scoped AND never rotated are listed separately.
That is not an average of the two columns -- it is the intersection, and it is
the set where neither control is doing anything. Item 53's shape: two separately
tolerable states that are not tolerable together.

── WHAT THE REGISTER CAN AND CANNOT SUPPORT ───────────────────────────────────
`tools/nhi_register.py` is the source and it is honest about its own limits:
"A blank `last rotated` means NOBODY KNOWS, not never. No clone holds any of
these, so rotation dates are attested and none has been attested yet."

This tool inherits that limit exactly. It reports what the register RECORDS, and
a missing rotation date is reported as UNATTESTED -- not as "never rotated",
which would be a claim about the world made from the absence of a note.

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────────
  * Verify a scope. The scope text is a human's description, not a measured
    grant. `tools/grant_sweep` work and the role gates are what measure it; this
    reads the declaration.
  * Verify a rotation. No clone holds any of these credentials.
  * Decide that a broad scope is wrong. `supabase-service-role` is FULL by
    design and the design is defensible. BROAD is a description of blast radius,
    not an accusation.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

CRITERIA_VERSION = '2026-09-15.3'

# ── CRITERIA, FIXED BEFORE THE REAL REGISTER WAS READ ─────────────────────────
# Written against the synthetic fixtures below first. Calibrating these against
# the real 22 scopes would be tuning the instrument to flatter the corpus, which
# is the failure this platform has a standing rule against.
#
# ── REVISED ONCE, .1 -> .2, AND THE DIRECTION IS WHY IT IS ALLOWED ────────────
# The first run missed `postgres`, whose scope reads "Owns all 380-odd objects
# in public". Owning every object in the schema is as broad as access gets and
# the pattern list had no phrase for it. The revision was made, a fixture added
# in both directions, and the version bumped -- and it moved one row from
# BOUNDED to BROAD, i.e. AGAINST this platform. That is the test for whether a
# criteria change is a correction or a calibration: a change that makes the
# number worse is not tuning to flatter the corpus. A change that made it better
# would need the same scrutiny the corpus rule exists to apply.
#
# ONE BOUNDARY CASE LEFT DELIBERATELY UNRESOLVED, stated rather than silently
# decided: `stripe-account` is "live charge and refund authority on the
# SAIRNcash Stripe account". That is total authority within its domain and the
# domain is real money. It is classed BOUNDED here because widening BROAD to
# "holds authority over its own service" would make every third-party key broad
# and the column would stop discriminating. Whether money authority deserves its
# own tier is a judgement for a human, not a regex.
BROAD_SCOPE = re.compile(
    r'\bFULL\b|every table|all tables|bypass(?:ing)? RLS|BYPASSRLS|'
    r'admin authority|every app|without limit|full [a-z ]*authority|'
    r'SELECT on every|owns all|all \d*[- ]*odd objects|every object', re.I)

# A CADENCE, not a procedure. "Stripe dashboard" tells you HOW; it does not tell
# you WHEN, and a rotation with no when is a rotation that happens after an
# incident or not at all.
CADENCE = re.compile(
    r'\b(daily|weekly|monthly|quarterly|annually|yearly|every \d+ (?:days?|weeks?|'
    r'months?)|on a schedule|scheduled|automated|automatic)\b', re.I)

# Explicitly somebody else's to rotate. Recorded so it is not counted against
# this platform, and NOT counted as clean either.
NOT_OURS = re.compile(r'not ours|managed by', re.I)

# A compromise trigger: what happens if this one leaks. Distinct from a cadence
# -- an identity can have neither, either, or both, and they answer different
# questions.
COMPROMISE = re.compile(
    r'\bif (?:it |this )?(?:is )?(?:leak|compromis|expos)|on compromise|'
    r'compromise[- ]trigger|revoke immediately|if leaked', re.I)


def load_identities():
    """The register's own data, imported rather than re-parsed from the
    generated markdown. Returns None if it cannot be read -- an empty list would
    report a clean platform with no credentials on it."""
    try:
        import nhi_register
    except Exception:
        return None
    ids = getattr(nhi_register, 'IDENTITIES', None)
    if not ids:
        return None
    return ids


def rotation_state(ident):
    """One of: ATTESTED, SCHEDULED, PROCEDURE ONLY, NOT OURS, NOTHING RECORDED.

    UNATTESTED IS NOT "NEVER ROTATED". The register says so about itself and
    this inherits it: a missing date is the absence of a note, not a fact about
    the world.
    """
    last = (ident.get('last_rotated') or '').strip()
    rot = (ident.get('rotation') or '').strip()
    if last:
        return 'ATTESTED'
    if NOT_OURS.search(rot):
        return 'NOT OURS'
    if CADENCE.search(rot):
        return 'SCHEDULED'
    if rot:
        return 'PROCEDURE ONLY'
    return 'NOTHING RECORDED'


def scope_state(ident):
    return 'BROAD' if BROAD_SCOPE.search(ident.get('scope') or '') else 'BOUNDED'


# A drafted procedure has to SAY something. The bar is deliberately a length
# floor rather than a keyword list: "revoke it" satisfies any keyword check and
# tells an incident responder nothing. Same shape as --decide's reason floor in
# tools/defect_budget_policy.py.
MIN_PROCEDURE_CHARS = 120


def has_compromise_trigger(ident):
    """An explicit `compromise` procedure, or a trigger stated in prose.

    ── THE FIELD WAS ADDED AFTER THE FIRST RUN (.2 -> .3) AND THE NUMBER WENT UP
    On 2026-09-15 this reported 0 of 22. Five procedures were then WRITTEN for
    the five identities where neither control was doing anything, and this now
    reads that field.

    THAT IS THE DIRECTION THAT NEEDS SCRUTINY, so it is stated rather than
    left to be noticed: the figure improved. It improved because the DATA
    changed -- procedures were written that did not exist -- and not because
    the test was loosened. The criteria change is that a field which did not
    exist is now read; the fixture below proves an empty or thin one still does
    not count, which is what keeps that distinction honest.
    """
    proc = (ident.get('compromise') or '').strip()
    if len(proc) >= MIN_PROCEDURE_CHARS:
        return True
    blob = ' '.join(str(ident.get(k, '')) for k in ('rotation', 'scope', 'note'))
    return bool(COMPROMISE.search(blob))


UNROTATED = ('PROCEDURE ONLY', 'NOTHING RECORDED')


def intersection(rows):
    """Identities where NEITHER control is doing anything.

    A SET, not an average and not a union. The union would be "either control is
    weak", which is most of any register and says nothing; the average would be
    a posture score, which is the exact thing this tool refuses to produce. What
    is interesting is the overlap, and only the overlap.
    """
    return [r for r in rows
            if r['scope'] == 'BROAD' and r['rotation'] in UNROTATED]


def analyse(idents):
    rows = []
    for i in idents:
        rows.append({
            'id': i.get('id'),
            'rotation': rotation_state(i),
            'scope': scope_state(i),
            'compromise_trigger': has_compromise_trigger(i),
            'credentials': len(i.get('credentials') or []),
        })
    return rows


# ── THE BLIND LOCK ────────────────────────────────────────────────────────────
def fixtures():
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '  <- ' + str(detail)[:220]))
        if not cond:
            bad += 1

    F = {
        'full': {'id': 'full', 'scope': 'FULL read/write on every table',
                 'rotation': 'coordinated', 'last_rotated': ''},
        'bypass': {'id': 'bypass', 'scope': 'SELECT on every table, plus BYPASSRLS',
                   'rotation': '', 'last_rotated': ''},
        'narrow': {'id': 'narrow', 'scope': 'read one column of one table',
                   'rotation': 'rotated monthly, automated', 'last_rotated': ''},
        'dated': {'id': 'dated', 'scope': 'read one column of one table',
                  'rotation': 'by hand', 'last_rotated': '2026-09-01'},
        'theirs': {'id': 'theirs', 'scope': 'a narrow thing',
                   'rotation': 'not ours', 'last_rotated': ''},
        'trigger': {'id': 'trigger', 'scope': 'a narrow thing',
                    'rotation': 'by hand. If leaked, revoke immediately',
                    'last_rotated': ''},
    }

    ck('a FULL scope is BROAD', scope_state(F['full']) == 'BROAD')
    ck('BYPASSRLS on every table is BROAD too -- read-only is not narrow when '
       'it is read-EVERYTHING', scope_state(F['bypass']) == 'BROAD')
    ck('CONTROL: a genuinely narrow scope is BOUNDED. A detector that calls '
       'everything broad has measured nothing',
       scope_state(F['narrow']) == 'BOUNDED', scope_state(F['narrow']))
    ck('THE .1 -> .2 MISS: owning every object in the schema is BROAD. The '
       'first criteria set had no phrase for ownership and read `postgres` -- '
       '"Owns all 380-odd objects in public" -- as BOUNDED',
       scope_state({'scope': 'Owns all 380-odd objects in public'}) == 'BROAD')
    ck('CONTROL: and the revision did not widen BROAD to everything -- owning '
       'ONE object is still bounded',
       scope_state({'scope': 'owns the one table it writes'}) == 'BOUNDED',
       scope_state({'scope': 'owns the one table it writes'}))
    ck('CONTROL: the boundary case stays BOUNDED and is stated in the header '
       'rather than silently decided -- total authority over one third-party '
       'service is not the same as broad standing access to this platform',
       scope_state({'scope': 'live charge and refund authority on the '
                             'SAIRNcash Stripe account'}) == 'BOUNDED')

    ck('a recorded date is ATTESTED', rotation_state(F['dated']) == 'ATTESTED')
    ck('a CADENCE is SCHEDULED', rotation_state(F['narrow']) == 'SCHEDULED')
    ck('CONTROL: a PROCEDURE with no cadence is NOT scheduled. "Stripe '
       'dashboard" says HOW and never WHEN, and a rotation with no when happens '
       'after an incident or not at all',
       rotation_state(F['full']) == 'PROCEDURE ONLY', rotation_state(F['full']))
    ck('nothing recorded at all is its own state, not folded into PROCEDURE',
       rotation_state(F['bypass']) == 'NOTHING RECORDED')
    ck('somebody else\'s credential is NOT OURS -- recorded rather than counted '
       'against this platform, and not counted clean either',
       rotation_state(F['theirs']) == 'NOT OURS')
    ck('CONTROL: an ATTESTED date wins over everything else, because a date is '
       'evidence and the rest is intent',
       rotation_state(dict(F['dated'], rotation='not ours')) == 'ATTESTED')

    ck('a compromise trigger stated in prose is detected',
       has_compromise_trigger(F['trigger']))
    ck('an explicit `compromise` PROCEDURE is a trigger',
       has_compromise_trigger({'compromise': 'x' * MIN_PROCEDURE_CHARS}))
    ck('CONTROL: a THIN procedure is not. "Revoke it" satisfies any keyword '
       'check and tells an incident responder nothing, so the bar is a length '
       'floor and the field being PRESENT is not enough',
       not has_compromise_trigger({'compromise': 'revoke it'}))
    ck('CONTROL: an EMPTY procedure field is not a trigger either -- adding the '
       'key without writing anything must not move the number',
       not has_compromise_trigger({'compromise': ''})
       and not has_compromise_trigger({'compromise': '   '}))
    ck('CONTROL: a scheduled rotation is NOT a compromise trigger. They answer '
       'different questions and conflating them is the substitution this whole '
       'tool exists to refuse', not has_compromise_trigger(F['narrow']))

    rows = analyse(list(F.values()))
    by = {r['id']: r for r in rows}
    ck('the two columns are independent -- an identity can be BROAD and '
       'SCHEDULED, or BOUNDED and unrotated, and both combinations appear here',
       by['full']['scope'] == 'BROAD' and by['narrow']['scope'] == 'BOUNDED'
       and by['narrow']['rotation'] == 'SCHEDULED', rows)
    both = intersection(rows)
    ck('the intersection is computed as a SET, not as an average of the two '
       'columns', sorted(r['id'] for r in both) == ['bypass', 'full'],
       [r['id'] for r in both])
    ck('CONTROL: the intersection is not the UNION. A union would be "either '
       'control is weak", which is most of any register and says nothing',
       len(both) < len([r for r in rows if r['scope'] == 'BROAD'
                        or r['rotation'] in UNROTATED]),
       (len(both), [r['id'] for r in rows]))
    ck('CONTROL: a BOUNDED-and-scheduled identity is in neither finding list',
       by['narrow'] not in both)
    ck('CONTROL: no function combines the two columns into one score, by name',
       not any(n in globals() for n in ('posture_score', 'combined', 'overall',
                                        'security_score')))
    return out, bad


def main(argv):
    if '--fixtures' in argv:
        lines, bad = fixtures()
        print('ROTATION AND BLAST RADIUS -- blind lock, %d arms, no register read'
              % len(lines))
        for l in lines:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad
                        else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    lines, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- the real register was not read.')
        for l in lines:
            print(l)
        return 2

    idents = load_identities()
    if idents is None:
        print('COULD NOT READ tools/nhi_register.py IDENTITIES -- nothing was')
        print('measured. This is NOT a clean run.')
        return 2

    rows = analyse(idents)
    unrotated = [r for r in rows if r['rotation'] in UNROTATED]
    broad = [r for r in rows if r['scope'] == 'BROAD']
    both = intersection(rows)
    triggers = [r for r in rows if r['compromise_trigger']]

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'rows': rows},
                         indent=2))
        return 1 if (unrotated or broad) else 0

    print('ROTATION AND BLAST RADIUS -- item 61, criteria %s' % CRITERIA_VERSION)
    print('  %d fixture arms passed before the register was read.' % len(lines))
    print('  %d identity(ies) in tools/nhi_register.py' % len(rows))
    print('')
    print('  TWO CONTROLS, TWO NUMBERS, DELIBERATELY NOT COMBINED:')
    print('    ROTATION  %d of %d have no attested date and no schedule'
          % (len(unrotated), len(rows)))
    print('    SCOPE     %d of %d hold broad standing access'
          % (len(broad), len(rows)))
    print('    TRIGGER   %d of %d record what to do if this one is compromised'
          % (len(triggers), len(rows)))
    print('')
    print('  %-32s %-18s %-8s %s' % ('identity', 'rotation', 'scope', 'trigger'))
    for r in sorted(rows, key=lambda x: (x['scope'] != 'BROAD', x['id'])):
        print('  %-32s %-18s %-8s %s'
              % (r['id'][:32], r['rotation'], r['scope'],
                 'yes' if r['compromise_trigger'] else '-'))
    print('')
    if both:
        covered = [r for r in both if r['compromise_trigger']]
        print('  BROAD STANDING ACCESS *AND* NO ATTESTED ROTATION OR SCHEDULE,')
        print('  for %d. This is a SET, not an average of the two columns above:'
              % len(both))
        for r in both:
            print('    %-30s %s' % (r['id'],
                                    'compromise procedure drafted'
                                    if r['compromise_trigger']
                                    else 'NO compromise procedure'))
        print('')
        if covered:
            print('  %d of those %d now carry a drafted compromise procedure, '
                  'which is' % (len(covered), len(both)))
            print('  a THIRD control and not a fix for either of the first two.')
            print('  A procedure tells you what to do AFTER; it does not shorten')
            print('  the window and it does not narrow the blast radius. These')
            print('  rows are still in this list for exactly that reason.')
            print('')
    print('  ROTATION IS NOT A SUBSTITUTE FOR SCOPING AND SCOPING IS NOT A')
    print('  SUBSTITUTE FOR ROTATION. A freshly-rotated credential that can')
    print('  reach everything still reaches everything for as long as it is')
    print('  valid; a tightly-scoped one that is never rotated keeps whatever')
    print('  access it has for ever. The two columns are printed apart because')
    print('  a single posture figure hides whichever half is worse.')
    print('')
    print('  AND UNATTESTED IS NOT "NEVER ROTATED". The register says so about')
    print('  itself and this inherits it: no clone holds any of these')
    print('  credentials, so a missing date is the absence of a note rather')
    print('  than a fact about the world. What IS a fact is that nothing on')
    print('  this platform would notice either way.')
    return 1 if (unrotated or broad) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
