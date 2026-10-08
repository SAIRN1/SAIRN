#!/usr/bin/env python
"""tool_provenance_status.py (hover2's own build) -- cross-ledger provenance
status for THIS instance's tools.

THE GAP THIS CLOSES (Michael, 2026-09-26): validation events live in TWO
ledgers, one per hover instance, and any status computed from one ledger
alone is wrong in a specific, real direction. Confirmed before building,
not assumed: H1's ledger holds a real cross-session event (validator hover,
author hover2, claim_collision_scan.py, reproduced true, 2026-09-24) that
no hover2-ledger-only read can see -- so hover2's claim_collision_scan.py
would report NEVER VALIDATED while a genuine independent validation of it
sits on disk one directory over.

WHAT AN EVENT MEANS, re-derived from the recording tool's own contract
(H1's tool_provenance_check.py, read 2026-09-24 during its validation --
seq 203), not copied from its source:
  - `tool` is a BARE FILENAME, and both instances deliberately build
    same-named independent implementations. WHICH instance's tool was
    validated is carried by `author_session`, so status here keys on
    (tool, author_session == 'hover2') -- an event about H1's same-named
    tool must never clear hover2's.
  - validator_session == author_session never counts (self-validation is
    not validation; the recorder refuses these, but a hand-edited ledger
    line must not sneak one through the reader either).
  - reproduced true  -> independently validated.
  - reproduced false -> attempted, NOT confirmed -- still due.

FAIL-CLOSED ON THE READ, PR SS1.11: a ledger that is absent or unreadable
is a COULD-NOT-READ, printed by name, and the verdict line says the
coverage is PARTIAL -- "no validations found" is only ever claimed when
every known ledger was actually read. If NO ledger is readable at all the
tool exits 2 COULD NOT RUN rather than reporting every tool unvalidated.

BLIND LOCK (discipline 1): synthetic fixtures classify FIRST on every
invocation, in isolation from the real ledgers; any fixture miss refuses
the real run (exit 2). Fixtures cover both directions of every rule above.

Exit: 0 every tool validated and every ledger read; 1 tools due (the
normal state); 2 could not run; 3 tools due AND coverage partial.

Run:
  python tool_provenance_status.py            # report
  python tool_provenance_status.py --selftest # fixtures only

THIS TOOL'S OWN PROVENANCE, said rather than implied: built and
fixture-checked by the same session (hover2) in one sitting -- by the very
standard it reports on, its findings are not "independently validated"
until a DIFFERENT instance reproduces them against a real holdout and
records the event. Until then treat its report as this role's own working
view, not a confirmed fact.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MY_SESSION = 'hover2'
# Known ledgers: mine, then every sibling hover instance's. Paths are data,
# not discovery, because the sibling's project dir cannot be derived from
# this one mechanically -- if a third instance appears, add its line and
# the ABSENT reporting below will name it until the file exists.
# BUG FIXED 2026-10-07 (batch O, item 6): both lines below used to derive a
# path relative to HERE (inside the GIT CLONE's .claude/skills/... tree).
# The real ledgers -- for BOTH instances -- live outside every clone, under
# ~/.claude/projects/<project-dir>/hover-audit-log/ (see this role's own
# memory note "hover-self-log-location"). The old 'hover' line additionally
# nested H1's full project-dir name UNDER tools-hover2/, producing a path
# that could never exist regardless of the clone-relative mistake. Verified
# BOTH corrected paths exist on disk before trusting this fix (ls -la on
# each, 2026-10-07) -- not assumed from the naming convention alone.
_CLAUDE_PROJECTS = os.path.join(os.path.expanduser('~'), '.claude', 'projects')
LEDGERS = [
    ('hover2', os.path.join(
        _CLAUDE_PROJECTS, 'C--Users-marsh-Documents-SAIRN-hover2',
        'hover-audit-log', 'tool_provenance_validations.jsonl')),
    ('hover', os.path.join(
        _CLAUDE_PROJECTS, 'C--Users-marsh-Documents-SAIRN-hover',
        'hover-audit-log', 'tool_provenance_validations.jsonl')),
]
SKIP = {'tool_provenance_status.py', 'hover_tool_index.py', 'hover_log.py',
        '__pycache__'}


def discover_tools(here=HERE):
    try:
        return sorted(f for f in os.listdir(here)
                      if f.endswith('.py') and f not in SKIP)
    except OSError:
        return None


def read_ledger(path):
    """-> (events, status) with status in READ / ABSENT / UNREADABLE.
    ABSENT and UNREADABLE both return [] -- the STATUS is what stops an
    empty read being mistaken for an empty ledger."""
    if not os.path.exists(path):
        return [], 'ABSENT'
    try:
        events = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events, 'READ'
    except (OSError, ValueError):
        return [], 'UNREADABLE'


def provenance_status(tools, ledger_events, my_session=MY_SESSION):
    """Pure core, no I/O. ledger_events: list of (ledger_name, events).
    Returns dict with per-tool status and the rule decisions applied."""
    by_tool = {t: {'validated': False, 'attempted': False, 'events': []}
               for t in tools}
    cross_info = []   # events about ANOTHER author's tools, kept visible
    rejected_self = 0
    for ledger_name, events in ledger_events:
        for e in events:
            t = e.get('tool')
            if e.get('validator_session') == e.get('author_session'):
                rejected_self += 1
                continue
            if e.get('author_session') != my_session:
                cross_info.append((ledger_name, e))
                continue
            if t not in by_tool:
                continue  # a validated tool since deleted from disk
            d = by_tool[t]
            d['events'].append((ledger_name, e))
            if e.get('reproduced') is True:
                d['validated'] = True
            else:
                d['attempted'] = True
    due = sorted(t for t, d in by_tool.items() if not d['validated'])
    return {'by_tool': by_tool, 'due': due, 'cross_info': cross_info,
            'rejected_self_validations': rejected_self}


def _selftest():
    fails = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            fails.append(label)

    tools = ['a.py', 'b.py', 'c.py']
    ev = lambda tool, val, auth, rep: {
        'tool': tool, 'validator_session': val, 'author_session': auth,
        'reproduced': rep}

    r = provenance_status(tools, [('L1', [])], 'hover2')
    check('empty ledgers -> every tool due', r['due'] == tools)

    r = provenance_status(
        tools, [('theirs', [ev('a.py', 'hover', 'hover2', True)])], 'hover2')
    check('a cross-session event in the OTHER ledger clears exactly my a.py',
          r['due'] == ['b.py', 'c.py'] and r['by_tool']['a.py']['validated'])

    r = provenance_status(
        tools, [('L1', [ev('a.py', 'hover2', 'hover2', True)])], 'hover2')
    check('validator==author NEVER counts, even reproduced=true',
          r['due'] == tools and r['rejected_self_validations'] == 1)

    r = provenance_status(
        tools, [('L1', [ev('a.py', 'hover2', 'hover', True)])], 'hover2')
    check("an event about the OTHER author's same-named a.py does not clear mine",
          r['due'] == tools and len(r['cross_info']) == 1)

    r = provenance_status(
        tools, [('L1', [ev('b.py', 'hover', 'hover2', False)])], 'hover2')
    check('reproduced=false is attempted, still due',
          'b.py' in r['due'] and r['by_tool']['b.py']['attempted'])

    r = provenance_status(
        tools,
        [('L1', [ev('a.py', 'hover', 'hover2', True)]),
         ('L2', [ev('b.py', 'hover', 'hover2', True)])], 'hover2')
    check('events merge across ledgers', r['due'] == ['c.py'])

    r = provenance_status(
        tools, [('L1', [ev('gone.py', 'hover', 'hover2', True)])], 'hover2')
    check('an event for a tool no longer on disk is ignored, not crashed on',
          r['due'] == tools)

    print()
    if fails:
        print('%d SELFTEST FAILURE(S): %s' % (len(fails), fails))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


def main(argv):
    # Blind lock: fixtures first, every invocation, refusing the real run
    # on any miss -- nothing real gets judged by broken criteria.
    if _selftest() != 0:
        print('REFUSED: fixture lock failed -- nothing real was judged (exit 2).')
        return 2
    if '--selftest' in argv:
        return 0
    print()

    tools = discover_tools()
    if tools is None or not tools:
        print('COULD NOT RUN: no tools discoverable in %s' % HERE)
        return 2

    ledger_events, statuses = [], []
    for name, path in LEDGERS:
        events, status = read_ledger(path)
        statuses.append((name, path, status, len(events)))
        if status == 'READ':
            ledger_events.append((name, events))
    if not ledger_events:
        print('COULD NOT RUN: no ledger was readable at all. Refusing to '
              'report every tool unvalidated off an unread ledger set.')
        for name, path, status, _n in statuses:
            print('  %-7s %-10s %s' % (name, status, path))
        return 2

    r = provenance_status(tools, ledger_events)

    partial = any(s != 'READ' for _n, _p, s, _c in statuses)
    print('CROSS-LEDGER PROVENANCE -- %d tool(s), ledgers:' % len(tools))
    for name, path, status, n in statuses:
        print('  %-7s %-10s %d event(s)  %s' % (name, status, n, path))
    if partial:
        print('COVERAGE PARTIAL: at least one known ledger was not read -- '
              '"not validated" below means "not validated IN THE LEDGERS '
              'READ", not a settled fact.')
    print()
    for t in tools:
        d = r['by_tool'][t]
        if d['validated']:
            srcs = sorted({ln for ln, _e in d['events']})
            status = 'INDEPENDENTLY VALIDATED (%d event(s), ledger(s): %s)' % (
                len(d['events']), ', '.join(srcs))
        elif d['attempted']:
            status = 'ATTEMPTED, DID NOT REPRODUCE -- still due'
        else:
            status = 'not validated' + (' in the ledgers read' if partial else '')
        print('  %-36s %s' % (t, status))
    if r['rejected_self_validations']:
        print('\n%d self-validation event(s) REJECTED by the reader '
              '(validator == author never counts).' % r['rejected_self_validations'])
    if r['cross_info']:
        print('\n%d event(s) about the OTHER instance\'s tools seen and kept '
              'separate (author != %s):' % (len(r['cross_info']), MY_SESSION))
        for ln, e in r['cross_info']:
            print('  [%s] %s validated by %s (author %s) reproduced=%s'
                  % (ln, e.get('tool'), e.get('validator_session'),
                     e.get('author_session'), e.get('reproduced')))
    print()
    if r['due']:
        print('DUE: %d of %d of this instance\'s tools lack a reproduced '
              'independent validation%s.'
              % (len(r['due']), len(tools),
                 ' in the ledgers read' if partial else ''))
        return 3 if partial else 1
    print('OK: every tool has a reproduced independent validation on record'
          + (' -- but coverage was PARTIAL, so this is not a settled all-clear.'
             if partial else '.'))
    return 3 if partial else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
