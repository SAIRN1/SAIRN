#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b6, queue item 2 -- compaction survival
"""Under 20 lines, printed after a compaction, telling an agent who it is.

    python tools/compaction_brief.py            # this clone, from its marker
    python tools/compaction_brief.py --agent cc # a named one, for testing
    python tools/compaction_brief.py --all      # every clone, for a check
    python tools/compaction_brief.py --fixtures # the criteria lock

ALWAYS EXITS 0. It is wired as a SessionStart hook with matcher `compact`, and
a non-zero exit from a SessionStart hook is a session that will not start. Its
mechanism is the MESSAGE, not the status -- the same decision
hook_integrity_check made for its own `--hook` mode and for the same reason:
a check that can stop a session from starting gets removed within the hour.

── WHAT A COMPACTION ACTUALLY COSTS, AND WHY THIS IS FOUR FACTS ────────────
A compaction keeps a summary and drops the transcript. What survives is
whatever the summary happened to carry; what reliably does NOT survive is the
agent's own identity, which batch it is in, and where its instructions are --
because those were established in the first few turns and are the oldest thing
in the window.

So this prints exactly four things and nothing else:

  WHO    the agent name, from the per-clone marker -- never from the folder
         name. A clone renamed `SAIRN-cody` would otherwise answer "cody" and
         act as cody; hover finding #258 is that exact defect in two other
         tools.
  BATCH  the id taken from that agent's LATEST DIGEST ON DRIVE, by modified
         time, with the id parsed out of the filename.
  WHERE  the path to its latest handoff.
  WHAT   one instruction: re-read the handoff and state your position before
         acting.

── EVERY FACT SAYS WHERE IT CAME FROM, AND AN ABSENT ONE SAYS SO ───────────
A brief that silently omits a fact it could not find is worse than one that
prints nothing: the agent reads four lines, three of them true, and cannot
tell which. So a missing digest prints UNKNOWN with the directory it looked
in, and a missing handoff prints the same.
"""
import io
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

CRITERIA_VERSION = '2026-10-13.1'

# The shared Drive directory every agent writes its digest and handoff to.
DRIVE = os.environ.get('SAIRN_DRIVE_DIR') or os.path.join(
    'G:', os.sep, 'My Drive', 'SAIRN-status')

# The six clones, and the digest/handoff token each uses. The AUDITORS use
# different tokens from their session names -- hover writes `h1`, hover2 writes
# `h2` -- which is why this is a table and not a format string. Measured from
# the real directory listing rather than assumed.
AGENTS = {
    'cc':     {'digest': 'cc',     'handoff': 'cc'},
    'hank':   {'digest': 'hank',   'handoff': 'hank'},
    'cody':   {'digest': 'cody',   'handoff': 'cody'},
    'fourth': {'digest': 'fourth', 'handoff': 'fourth'},
    'hover':  {'digest': 'h1',     'handoff': 'h1'},
    'hover2': {'digest': 'h2',     'handoff': 'h2'},
}

DIGEST_RE = 'SAIRN-digest-%s-(?P<batch>[A-Za-z0-9]+)\\.txt$'
HANDOFF_PREFIXES = ('handoff-%s-', 'SAIRN-handoff-%s-', '%s-handoff')


def session_name():
    try:
        import sairn_session_identity as sid
        return sid.session_name()
    except Exception:                                            # noqa: BLE001
        return ''


def _listing(directory):
    try:
        return sorted(os.listdir(directory))
    except OSError:
        return None


def latest_digest(agent, directory=None, listing=None):
    """-> (batch_id, filename) from the NEWEST matching digest, or (None, why).

    NEWEST BY MODIFIED TIME, NOT BY NAME. Sorting `b10` after `b9`
    lexicographically is wrong and will be wrong the moment a batch id reaches
    two digits -- which h1's already have (b10, b11, b12 are on the Drive
    today). mtime is the only ordering that does not need a parser for an id
    scheme nobody has fixed.
    """
    directory = directory or DRIVE
    token = AGENTS.get(agent, {}).get('digest', agent)
    names = listing if listing is not None else _listing(directory)
    if names is None:
        return None, 'the Drive directory %s could not be read' % directory
    rx = re.compile(DIGEST_RE % re.escape(token))
    hits = []
    for n in names:
        m = rx.match(n)
        if m:
            p = os.path.join(directory, n)
            try:
                hits.append((os.path.getmtime(p), n, m.group('batch')))
            except OSError:
                hits.append((0, n, m.group('batch')))
    if not hits:
        return None, 'no digest matching %r in %s' % (
            DIGEST_RE % token, directory)
    hits.sort()
    return hits[-1][2], hits[-1][1]


def latest_handoff(agent, directory=None, listing=None):
    """-> (filename, '') for the newest handoff, or (None, why)."""
    directory = directory or DRIVE
    token = AGENTS.get(agent, {}).get('handoff', agent)
    names = listing if listing is not None else _listing(directory)
    if names is None:
        return None, 'the Drive directory %s could not be read' % directory
    pres = tuple(p % token for p in HANDOFF_PREFIXES)
    hits = []
    for n in names:
        if not n.lower().endswith('.md'):
            continue
        if any(n.startswith(p) for p in pres):
            p = os.path.join(directory, n)
            try:
                hits.append((os.path.getmtime(p), n))
            except OSError:
                hits.append((0, n))
    if not hits:
        return None, 'no handoff starting %s in %s' % (
            ' or '.join(repr(p) for p in pres), directory)
    hits.sort()
    return hits[-1][1], ''


def brief(agent, directory=None, listing=None):
    """The lines. UNDER 20, asserted by the probe, not hoped for."""
    directory = directory or DRIVE
    batch, dinfo = latest_digest(agent, directory, listing)
    handoff, hwhy = latest_handoff(agent, directory, listing)
    out = [
        'CONTEXT WAS COMPACTED. Four facts, then one instruction.',
        '',
        '  AGENT : %s' % (agent or 'UNKNOWN -- no per-clone marker; '
                                  'tools/sairn_session_identity.py'),
        '  BATCH : %s' % (batch if batch else 'UNKNOWN -- %s' % dinfo),
        '  FROM  : %s' % (dinfo if batch else '(no digest found)'),
        '  HANDOFF: %s' % (os.path.join(directory, handoff) if handoff
                           else 'UNKNOWN -- %s' % hwhy),
        '',
        'RE-READ THAT HANDOFF AND STATE YOUR POSITION BEFORE YOU ACT: which',
        'queue item you are on, what is already committed, and what you were',
        'about to do. Do not resume from this summary alone -- it kept what it',
        'happened to keep, and your own identity and batch are the oldest',
        'things in the window and the first to go.',
    ]
    if not batch or not handoff:
        out.extend([
            '',
            'A FACT PRINTED AS UNKNOWN IS NOT A FACT YOU MAY GUESS. Find it or',
            'say you could not, in your first message.',
        ])
    return out


def cmd_all():
    listing = _listing(DRIVE)
    print('COMPACTION BRIEF -- criteria %s' % CRITERIA_VERSION)
    print('  drive : %s%s' % (DRIVE, '' if listing is not None
                              else '   (UNREADABLE)'))
    print('')
    worst = 0
    for agent in sorted(AGENTS):
        batch, dinfo = latest_digest(agent, DRIVE, listing)
        handoff, _hw = latest_handoff(agent, DRIVE, listing)
        print('  %-7s batch=%-6s handoff=%s'
              % (agent, batch or 'UNKNOWN',
                 handoff or 'UNKNOWN'))
        if not batch or not handoff:
            worst = 1
    print('')
    if worst:
        print('At least one agent has no digest or no handoff on the Drive. The')
        print('brief prints UNKNOWN for it rather than omitting the line, which')
        print('is the point -- but that agent cannot be told its batch after a')
        print('compaction until it uploads one.')
    return worst


_FIX_LISTING = [
    'SAIRN-digest-cc-b4.txt', 'SAIRN-digest-cc-b5.txt',
    'SAIRN-digest-h1-b9.txt', 'SAIRN-digest-h1-b10.txt',
    'handoff-cc-2026-10-12.md', 'handoff-cc-2026-10-13.md',
    'SAIRN-handoff-h1-b10.md',
    'SAIRN-digest-nobody-b1.txt',
]


def run_fixtures():
    """The criteria lock, on a synthetic listing with no Drive involved."""
    print('COMPACTION BRIEF -- criteria lock %s' % CRITERIA_VERSION)
    bad = 0

    def check(label, got, want):
        nonlocal bad
        okk = got == want
        if not okk:
            bad += 1
        print('  %s %-58s got=%r' % ('ok  ' if okk else 'FAIL', label, got))

    # mtime ordering cannot be exercised on a synthetic list, so the fixture
    # asserts what CAN be asserted without touching a filesystem: that the id
    # is parsed out of the right token and that a miss is a named UNKNOWN.
    b, _ = latest_digest('cc', '/fake', _FIX_LISTING)
    check('a cc digest id is parsed from the filename', b in ('b4', 'b5'), True)
    b, _ = latest_digest('hover', '/fake', _FIX_LISTING)
    check('hover reads the h1 token, not its session name',
          b in ('b9', 'b10'), True)
    b, why = latest_digest('hank', '/fake', _FIX_LISTING)
    check('an agent with no digest is UNKNOWN', b, None)
    check('...and it says where it looked', 'no digest matching' in why, True)
    h, _ = latest_handoff('cc', '/fake', _FIX_LISTING)
    check('a cc handoff is found', h is not None, True)
    h, _ = latest_handoff('hover', '/fake', _FIX_LISTING)
    check('the auditor spelling SAIRN-handoff-h1- is found too',
          h == 'SAIRN-handoff-h1-b10.md', True)
    h, why = latest_handoff('cody', '/fake', _FIX_LISTING)
    check('an agent with no handoff is UNKNOWN', h, None)
    lines = brief('cc', '/fake', _FIX_LISTING)
    check('the brief is UNDER 20 lines', len(lines) < 20, True)
    check('...and names the agent', any('AGENT : cc' in l for l in lines), True)
    check('...and carries the one instruction',
          any('STATE YOUR POSITION' in l for l in lines), True)
    lines = brief('hank', '/fake', _FIX_LISTING)
    check('a brief with a missing fact prints UNKNOWN rather than omitting it',
          any('UNKNOWN' in l for l in lines), True)
    check('...and is still under 20 lines', len(lines) < 20, True)
    check('...and says an UNKNOWN is not a fact to guess',
          any('NOT A FACT YOU MAY GUESS' in l for l in lines), True)
    print('  %d/%d fixtures classify correctly' % (13 - bad, 13))
    return 1 if bad else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv:
        return run_fixtures()
    if '--all' in argv:
        return cmd_all()
    agent = ''
    if '--agent' in argv:
        agent = argv[argv.index('--agent') + 1]
    else:
        agent = session_name()
    for line in brief(agent):
        print(line)
    # ALWAYS 0. See the module docstring: a SessionStart hook that exits
    # non-zero is a session that does not start.
    return 0


if __name__ == '__main__':
    sys.exit(main())
