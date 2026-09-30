#!/usr/bin/env python
# OWNER: cody
"""A NEW tools/*.py file must say which session owns it.

    python tools/tool_owner_header_check.py <path> [<path> ...]

WHY. On 2026-09-30 a sweep found 22 tools that mutate the repo when run with no
arguments. Routing that to their owners was impossible: 21 of the 22 have no
recorded owner anywhere the claim system can see. Every one was authored through
the same git identity, so `git log` cannot say either, and the claim record only
knows a file if somebody happened to name it in a claim string. The answer was
"register the rest by owner" and it could not be given.

A NEW FILE IS THE ONLY MOMENT THE ANSWER IS FREE. Whoever is writing it knows.

    # OWNER: cody

on its own line, anywhere in the first 40 lines, before any code. One of the
recognised session names; a made-up one is refused, because an owner nobody can
be asked is not an owner.

── WHAT THIS DOES NOT DO, STATED RATHER THAN DISCOVERED ─────────────────────
It does NOT require the header on the 282 tools that already exist. That is
grandfathering and it is deliberate: a gate that refuses every push touching any
tool would be switched off within the hour, and the 282 need routing by hand from
the claim history, not a header invented by whoever next edits them. The count is
PRINTED on every run so the backlog cannot quietly become the normal state.

Exit 0 when every file given carries a valid owner, 1 when any does not, 2 COULD
NOT RUN -- no files given, or a file could not be read. Called from a gate where
exit 0 means allow, so "I could not check" is never folded into "it is fine".
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The sessions that can be asked. Derived from the claim record's own directory
# rather than hardcoded: a sixth build agent appears as a claim file, and a list
# here would be wrong for exactly as long as CLAUDE.md's clone registry was.
def known_sessions():
    d = os.path.join(REPO, '.claude', 'claims')
    try:
        names = sorted(n[:-5] for n in os.listdir(d) if n.endswith('.json'))
    except OSError:
        return None
    return names or None


HEADER_RX = re.compile(r'^#\s*OWNER:\s*([A-Za-z0-9][\w.-]*)\s*$', re.M)
HEAD_LINES = 40


def owner_of(path):
    """(owner, why_not). owner is None when the header is absent or malformed."""
    try:
        head = ''.join(io.open(path, encoding='utf-8', errors='replace')
                       .readlines()[:HEAD_LINES])
    except OSError as e:
        return None, 'could not read: %s' % e
    m = HEADER_RX.search(head)
    if not m:
        loose = re.search(r'OWNER\s*[:=]', head)
        if loose:
            return None, ('something like an OWNER line is there but not in the '
                          'form `# OWNER: <session>` on its own line')
        return None, 'no `# OWNER: <session>` line in the first %d lines' % HEAD_LINES
    return m.group(1), ''


def main(argv):
    paths = [a for a in argv if not a.startswith('-')]
    if not paths:
        sys.stderr.write(
            'No files given. COULD NOT RUN -- an empty run reporting "every new '
            'tool declares an owner" is a measurement that did not happen, and '
            'this is called from a gate where exit 0 means allow.\n')
        return 2

    sessions = known_sessions()
    if sessions is None:
        sys.stderr.write(
            'COULD NOT RUN -- .claude/claims/ is unreadable, so there is no list '
            'of sessions to validate an owner against. Accepting any string here '
            'would make the check cosmetic.\n')
        return 2

    missing, wrong, could_not, ok_rows = [], [], [], []
    for p in paths:
        ap = p if os.path.isabs(p) else os.path.join(REPO, p)
        if not os.path.isfile(ap):
            could_not.append((p, 'no such file'))
            continue
        owner, why = owner_of(ap)
        if owner is None:
            if why.startswith('could not read'):
                could_not.append((p, why))
            else:
                missing.append((p, why))
        elif owner not in sessions:
            wrong.append((p, owner))
        else:
            ok_rows.append((p, owner))

    grandfathered = 0
    tools_dir = os.path.join(REPO, 'tools')
    if os.path.isdir(tools_dir):
        for n in os.listdir(tools_dir):
            if not n.endswith('.py'):
                continue
            o, _w = owner_of(os.path.join(tools_dir, n))
            if o is None:
                grandfathered += 1

    print('TOOL OWNER HEADER CHECK')
    print('  files given        : %d' % len(paths))
    print('  declared an owner  : %d' % len(ok_rows))
    for p, o in ok_rows:
        print('      %-52s OWNER: %s' % (p, o))
    print('  known sessions     : %s' % ', '.join(sessions))
    print('  GRANDFATHERED      : %d existing tools/*.py carry no OWNER line. '
          'NOT' % grandfathered)
    print('                       refused here, and printed every run so the '
          'backlog cannot')
    print('                       quietly become the normal state.')
    if missing:
        print('')
        print('  NO OWNER: %d' % len(missing))
        for p, why in missing:
            print('      %s' % p)
            print('          %s' % why)
    if wrong:
        print('')
        print('  OWNER IS NOT A KNOWN SESSION: %d' % len(wrong))
        for p, o in wrong:
            print('      %-52s OWNER: %r' % (p, o))
            print('          not one of %s -- an owner nobody can be asked is not '
                  'an owner' % ', '.join(sessions))
    if could_not:
        print('')
        print('  COULD NOT CHECK: %d -- NOT counted as declared' % len(could_not))
        for p, why in could_not:
            print('      %-52s %s' % (p, why))
    print('')
    if missing or wrong:
        print('A NEW TOOL WITH NO OWNER CANNOT BE ROUTED. 21 of the 22 bare-run')
        print('writers found on 2026-09-30 had no owner derivable from git, from')
        print('the claim record, or from anything else, and "register the rest by')
        print('owner" could not be done. Add one line:')
        print('')
        print('    # OWNER: <your session name>')
        return 1
    if could_not:
        print('Nothing failed AND %d file(s) were not checked. Not a clean bill.'
              % len(could_not))
        return 2
    print('Every file given declares an owner that can be asked.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
