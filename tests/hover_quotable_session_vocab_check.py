"""The hover auditor's QUOTABLE list must know every session the platform has.

    python tests/hover_quotable_session_vocab_check.py
    python tests/hover_quotable_session_vocab_check.py --json

Exit 0  every session this could see is named in QUOTABLE
Exit 1  a real session is MISSING from QUOTABLE
Exit 2  COULD NOT TELL -- no source of sessions was readable, or the literal
        could not be parsed. Never folded into a pass.

── WHY THIS EXISTS: A HARDCODED LIST THAT MUST TRACK A MOVING REGISTRY ────────
`tools/hover_separation_audit.py`'s `quote_attribution()` decides whether a
quotation belongs to ANOTHER session, and it decides it by matching the
lead-in against `QUOTABLE` -- a literal tuple of session names. When a session
exists that QUOTABLE has never heard of, the lead-in `newclone said: "..."`
produces NO marker, the attribution comes back `none`, and a genuine citation
is classified DISPUTED instead of CITED.

THE FAILURE IS FAIL-SAFE AND THAT IS EXACTLY WHY IT SURVIVES. Under-suppression
reports MORE matches, never fewer, so nothing breaks and nobody is paged. The
signal just quietly gets noisier, and a noisier signal is one people stop
reading -- which is how the auditor loses the ability to tell a citation from a
claim.

THIS PLATFORM HAS LIVE PROOF THAT THIS CLASS OF DRIFT HAPPENS HERE. `CLAUDE.md`
said *"Four clones"* and named four for weeks after a fifth existed on disk and
was pushing commits; the file now carries its own instruction not to trust that
list -- *"Do not count them from this list -- count the directories."* `hover2`
appeared the same way. A list that must track a registry, with nothing checking
it, is the eighth cross-domain discipline's case: nothing announces the day it
stops being complete.

Same shape as `tests/law_reconcile_role_vocab_check.py`, and the same argument:
an allow-list entry that can never match is indistinguishable at the call site
from a deliberate exclusion, so there is no request that reveals it and no test
that makes requests ever will. It is checked statically or not at all.

── ONE DIRECTION ONLY, AND THE REASON IS THE WHOLE DESIGN ─────────────────────
This asks "is a real session MISSING from QUOTABLE". It does NOT ask whether
QUOTABLE contains a name that is not a clone, and refusing to ask that is
deliberate rather than lazy. Three entries are legitimately not clone
directories:

    ted      an alias for `fourth` -- the sairn-hover-auditor skill names the
             build agents as "Hank, CC, Fourth/Ted, Cody"
    hover1   the other spelling of `hover`; the audit itself aliases them
    michael  the human, who is quoted in logs and is not a session at all

A reverse check would report all three as phantoms on a clean tree. The
template this follows warns about exactly that: a checker that is confidently
wrong about what it misattributed is worse than one that is narrow and says so.

── WHERE THE TRUTH ABOUT SESSIONS LIVES, AND WHY NO SINGLE SOURCE IS ENOUGH ───
Three sources, and they disagree TODAY -- which is the reason all three are
read rather than one being trusted:

  .claude/claims/*.json      IN THE REPO, committed, one file per clone. The
                             portable source. MEASURED INCOMPLETE: `hover2`
                             has no claim file, so this source alone would
                             have missed it.
  ~/SAIRN-SESSION-LOCKS/status/*.json
                             the live registry. OUTSIDE every clone by design,
                             so it is absent on another machine and in CI.
  ~/Documents/SAIRN-*        the clone directories. What CLAUDE.md tells a
                             reader to count. Also machine-local.

So the union is taken, and WHICH SOURCES WERE READABLE IS PRINTED ON EVERY RUN.
A clean result from one source is a narrower claim than a clean result from
three, and the output says which one it is rather than letting "OK" carry a
reach it does not have. Exit 2 when none of the three could be read: a check
that saw no sessions has not established that QUOTABLE covers them.
"""
import glob
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(REPO, 'tools', 'hover_separation_audit.py')

CLAIMS_DIR = os.path.join(REPO, '.claude', 'claims')

# ── THE TWO MACHINE-LOCAL SOURCES ARE OVERRIDABLE, AND THE CONTROL IS WHY ────
# They were absolute paths reading the real workstation, so a synthetic tree
# could not move them: every control arm inherited this machine's real
# `hover2` and three arms went red for a reason that had nothing to do with
# the property they guard. The check was UNTESTABLE IN ISOLATION and only its
# control could see that -- which is the control doing its job, before the
# check shipped rather than after.
#
# Same mechanism and same reason as `SAIRN_TIER_REGISTER` on
# `tools/criticality_tier_check.py`: not a behaviour switch, the same code
# against a different set of paths. An empty string means "this source does
# not exist here", which is how an arm drives the not-readable branch.
STATUS_DIR = os.environ.get(
    'SAIRN_STATUS_DIR',
    os.path.expanduser(os.path.join('~', 'SAIRN-SESSION-LOCKS', 'status')))
CLONES_GLOB = os.environ.get(
    'SAIRN_CLONES_GLOB',
    os.path.expanduser(os.path.join('~', 'Documents', 'SAIRN-*')))

# Names that are legitimately in QUOTABLE without being a clone. Listed so the
# one-directional rule above is a stated decision and not an omission; nothing
# below reads this, it is here to be read by a person.
NON_CLONE_QUOTABLE = {
    'ted': 'alias for fourth',
    'hover1': 'alias for hover',
    'michael': 'the human, quoted in logs; not a session',
}


def could_not_tell(msg):
    print('COULD NOT TELL: ' + msg)
    print('This is exit 2. Nothing was established, and that is not a pass.')
    sys.exit(2)


def quotable():
    """Read the literal out of the audit tool. NEVER a second copy kept here --
    a copy would agree with itself while the original drifted, which is the
    defect one layer up."""
    if not os.path.isfile(AUDIT):
        could_not_tell('%s does not exist.' % os.path.relpath(AUDIT, REPO))
    src = io.open(AUDIT, encoding='utf-8').read()
    m = re.search(r'^QUOTABLE\s*=\s*\(([^)]*)\)', src, re.M | re.S)
    if not m:
        could_not_tell(
            'could not find `QUOTABLE = (...)` in %s. The anchor no longer '
            'matches, so this check tested NOTHING -- which is the failure '
            'mode it was written against, arriving from the other direction.'
            % os.path.relpath(AUDIT, REPO))
    names = [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", m.group(1))]
    names = [n.strip().lower() for n in names if n.strip()]
    if not names:
        could_not_tell(
            'QUOTABLE parsed to an EMPTY tuple. An empty list would make every '
            'session below look missing, which is a finding this check would '
            'have invented rather than found.')
    return set(names)


def sessions():
    """(union, per_source). Every session any readable source knows about.

    A source that is absent contributes nothing AND IS REPORTED AS ABSENT --
    the difference between "this source lists no extra sessions" and "this
    source could not be read" is the difference the whole file is about.
    """
    per = {}

    if os.path.isdir(CLAIMS_DIR):
        per['.claude/claims/*.json'] = {
            os.path.basename(p)[:-5].strip().lower()
            for p in glob.glob(os.path.join(CLAIMS_DIR, '*.json'))
        }
    else:
        per['.claude/claims/*.json'] = None

    if STATUS_DIR and os.path.isdir(STATUS_DIR):
        per['~/SAIRN-SESSION-LOCKS/status'] = {
            os.path.basename(p)[:-5].strip().lower()
            for p in glob.glob(os.path.join(STATUS_DIR, '*.json'))
        }
    else:
        per['~/SAIRN-SESSION-LOCKS/status'] = None

    clones = ({os.path.basename(p).split('SAIRN-', 1)[-1].strip().lower()
               for p in glob.glob(CLONES_GLOB) if os.path.isdir(p)}
              if CLONES_GLOB else set())
    per['~/Documents/SAIRN-*'] = clones or None

    union = set()
    for got in per.values():
        if got:
            union |= got
    return union, per


def main(argv):
    as_json = '--json' in argv
    names = quotable()
    union, per = sessions()
    readable = [k for k, v in per.items() if v is not None]

    if not readable:
        could_not_tell(
            'none of the three session sources could be read, so no session '
            'was seen at all. QUOTABLE may be complete or may not; this run '
            'did not find out.')

    missing = sorted(n for n in union if n and n not in names)

    if as_json:
        print(json.dumps({
            'quotable': sorted(names),
            'sessions_seen': sorted(union),
            'missing_from_quotable': missing,
            'sources_readable': readable,
            'sources_unreadable': [k for k, v in per.items() if v is None],
        }, indent=1))
        return 1 if missing else 0

    print('QUOTABLE in tools/hover_separation_audit.py : %s'
          % ', '.join(sorted(names)))
    print('')
    for src in sorted(per):
        got = per[src]
        print('  %-32s %s' % (
            src,
            ('NOT READABLE HERE -- contributes nothing and is not a clean bill'
             if got is None else ', '.join(sorted(got)) or '(none)')))
    print('')
    print('  sessions seen across %d of 3 sources: %s'
          % (len(readable), ', '.join(sorted(union)) or '(none)'))
    print('')

    if missing:
        print('FAILED: %d session(s) exist that QUOTABLE does not name: %s'
              % (len(missing), ', '.join(missing)))
        print('')
        print('    A quotation attributed to one of these resolves to NO marker,')
        print('    so quote_attribution() returns `none` and a genuine citation')
        print('    is classified DISPUTED rather than CITED. It fails SAFE --')
        print('    more matches reported, never fewer -- which is why it would')
        print('    have gone unnoticed. Add the name to QUOTABLE.')
        return 1

    print('OK: every session seen is named in QUOTABLE.')
    if len(readable) < 3:
        print('    NARROWER THAN IT LOOKS: only %d of the 3 sources were '
              'readable here.' % len(readable))
        print('    The two machine-local ones are absent by design off this '
              'workstation, so')
        print('    a clean run in CI establishes less than a clean run on '
              'Michael\'s machine.')
    print('    NOT CHECKED, deliberately: whether QUOTABLE names anything that '
          'is NOT a')
    print('    session. `ted`, `hover1` and `michael` are legitimate and a '
          'reverse check')
    print('    would report all three as phantoms -- see the docstring.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
