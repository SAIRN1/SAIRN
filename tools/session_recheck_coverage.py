"""tools/session_recheck_coverage.py -- a session gate that never asks again.

    python tools/session_recheck_coverage.py            # report + ratchet
    python tools/session_recheck_coverage.py --baseline  # rewrite the pins

── WHAT THIS MEASURES, AND WHY A PRESENCE CHECK COULD NOT ──────────────────
`verifySessionToken()` proves a token was minted by us and has not expired. It
proves NOTHING ABOUT NOW: there is no server-side session store on this platform
(every endpoint is a stateless function), so a credential DEACTIVATED after the
token was issued keeps working until `exp` -- up to SESSION_TTL_MS, 12 hours.
Deactivation is the one control an owner has over somebody who has just left.

Two mechanisms close that, and counting only one of them UNDERSTATES the
platform badly:

  1. `credentialStillActive(session, licHash, rest, headers)` from
     api/_lib/auth.js -- the explicit re-check.
  2. An employee-row load filtered `active=eq.true` -- what every
     `api/*-auth.js` does inside `loadEmployee()`. A deactivated credential
     simply does not come back, so the route refuses without naming the
     re-check at all.

MEASURING ONLY (1) REPORTS 3 OF 222 GATES, i.e. 1.4%, AND THAT NUMBER IS WRONG.
It is the first figure this tool produced and it is recorded here because it is
the kind of number that gets quoted: every `*-auth.js` endpoint re-checks by
route (2), and reporting them as unprotected would have accused seventeen
correct files. Both mechanisms are counted.

── WHY A BASELINE AND A RATCHET RATHER THAN A PASS/FAIL ────────────────────
The honest state today is NOT closed, and a check that simply failed would sit
permanently red -- which this platform records as the state that gets scrolled
past, and then the real failure beside it does too. So the pins below are the
MEASURED state, the check fails when coverage gets WORSE, and closing a gate is
a `--baseline` away from being permanent.

A ratchet is not a pass. `python tools/session_recheck_coverage.py` printing OK
means "no worse than when this was pinned", never "the gap is closed". The
report says so on every run.

── WHAT IT CANNOT SEE, STATED RATHER THAN LEFT TO BE ASSUMED ───────────────
FILE-LEVEL PRESENCE IS NOT PER-GATE COVERAGE and the extreme case is the reason
this file exists: api/sd-data.js contains one `credentialStillActive` and 132
gates, so "this file has a mechanism" is true and 131 gates still do not use it.
The per-file ratio is therefore reported beside the count, and a file whose
ratio is far below 1 is the finding rather than a rounding note.

It also cannot tell whether a given gate NEEDS the re-check: a read-only or
self-scoped endpoint is a weaker case than a money write. That judgement is not
automatable and is not attempted -- the numbers are the input to it.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PINS = os.path.join('docs', 'session-recheck-coverage.json')

GATE = 'verifySessionToken('
EXPLICIT = 'credentialStillActive('
BY_ROUTE = re.compile(r'active=eq\.true')


def _code_lines(src):
    """Lines with the obvious comment shapes dropped.

    NOT a parser, and that is a bound rather than an oversight: a `//` inside a
    string would survive here. It cannot produce a false GATE count, because a
    string containing `verifySessionToken(` would have to be a deliberate
    fixture -- and tests are excluded below. Recorded because
    tools/sairn_dead_button_audit.py paid 58 phantom findings for assuming the
    opposite about a different shape.
    """
    for line in src.split('\n'):
        t = line.strip()
        if t.startswith('//') or t.startswith('*') or t.startswith('/*'):
            continue
        yield t


def scan():
    out = {}
    for root, _dirs, files in os.walk(os.path.join(REPO, 'api')):
        for f in sorted(files):
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace(os.sep, '/')
            try:
                src = io.open(p, encoding='utf-8', errors='replace').read()
            except OSError as e:
                # A FILE THAT CANNOT BE READ IS NOT A FILE WITH NO GATES.
                out[rel] = {'unreadable': str(e)}
                continue
            gates = explicit = route = 0
            for t in _code_lines(src):
                gates += t.count(GATE)
                explicit += t.count(EXPLICIT)
                route += len(BY_ROUTE.findall(t))
            if gates or explicit:
                out[rel] = {'gates': gates, 'explicit': explicit, 'route': route}
    return out


def verdict(row):
    """One of: covered-explicit, covered-by-route, NEITHER, partial."""
    if row.get('unreadable'):
        return 'UNREADABLE'
    g, e, r = row['gates'], row['explicit'], row['route']
    if not g:
        return 'no-gate'
    if e and e < g:
        return 'partial'
    if e:
        return 'covered-explicit'
    if r:
        return 'covered-by-route'
    return 'NEITHER'


def load_pins():
    p = os.path.join(REPO, PINS)
    if not os.path.isfile(p):
        return None
    try:
        return json.load(io.open(p, encoding='utf-8'))
    except ValueError as e:
        # A PIN FILE THAT WILL NOT PARSE IS NOT AN ABSENT ONE. Exit 2 below.
        return {'_unreadable': str(e)}


def main(argv):
    rows = scan()
    unreadable = [k for k, v in rows.items() if v.get('unreadable')]
    tot_gates = sum(v.get('gates', 0) for v in rows.values() if not v.get('unreadable'))
    neither = {k: v for k, v in rows.items() if verdict(v) == 'NEITHER'}
    partial = {k: v for k, v in rows.items() if verdict(v) == 'partial'}
    gates_neither = sum(v['gates'] for v in neither.values())
    gates_uncovered_in_partial = sum(v['gates'] - v['explicit'] for v in partial.values())

    print('SESSION-GATE RE-CHECK COVERAGE')
    print('%-30s %6s %9s %9s  %s' % ('file', 'gates', 'explicit', 'by-route', 'verdict'))
    for rel in sorted(rows, key=lambda k: -rows[k].get('gates', 0)):
        v = rows[rel]
        if v.get('unreadable'):
            print('%-30s %6s %9s %9s  UNREADABLE -- %s'
                  % (rel, '?', '?', '?', v['unreadable'][:40]))
            continue
        print('%-30s %6d %9d %9d  %s'
              % (rel, v['gates'], v['explicit'], v['route'], verdict(v)))

    print('')
    print('GATES_TOTAL:%d' % tot_gates)
    print('GATES_IN_FILES_WITH_NEITHER_MECHANISM:%d' % gates_neither)
    print('GATES_UNCOVERED_INSIDE_PARTIAL_FILES:%d' % gates_uncovered_in_partial)
    print('FILES_WITH_NEITHER:%d' % len(neither))
    print('FILES_PARTIAL:%d' % len(partial))
    print('FILES_UNREADABLE:%d' % len(unreadable))

    if partial:
        print('')
        print('PARTIAL -- the file has the mechanism and most of its gates do not use it.')
        print('This is the shape a presence check cannot see: one call site satisfies')
        print('"is it called at all" while every other gate on the same request path')
        print('runs on the token alone.')
        for rel in sorted(partial, key=lambda k: -partial[k]['gates']):
            v = partial[rel]
            print('   %-28s %d of %d gates re-check (%d uncovered)'
                  % (rel, v['explicit'], v['gates'], v['gates'] - v['explicit']))
    if neither:
        print('')
        print('NEITHER MECHANISM -- a deactivated credential works here until the')
        print('token expires. Whether that matters is per endpoint and is NOT decided')
        print('here; the list is the input to that judgement.')
        for rel in sorted(neither):
            print('   %-28s %d gate(s)' % (rel, neither[rel]['gates']))

    print('')
    print('A RATCHET IS NOT A PASS. OK below means "no worse than the pinned state",')
    print('never "closed". The pinned numbers are the measured gap, not a target.')

    pins = load_pins()
    if '--baseline' in argv:
        data = {
            '_what': 'Pinned session-gate re-check coverage. Written by '
                     'tools/session_recheck_coverage.py --baseline. A ratchet: the '
                     'check fails when any number below gets WORSE. Closing a gate '
                     'and re-running --baseline is how it improves.',
            'gates_total': tot_gates,
            'gates_in_files_with_neither_mechanism': gates_neither,
            'gates_uncovered_inside_partial_files': gates_uncovered_in_partial,
            'files_with_neither': len(neither),
            'files_partial': len(partial),
        }
        io.open(os.path.join(REPO, PINS), 'w', encoding='utf-8', newline='\n').write(
            json.dumps(data, indent=2, sort_keys=True) + '\n')
        print('')
        print('wrote %s' % PINS)
        return 0

    if pins is None:
        print('')
        print('COULD NOT TELL -- %s does not exist, so nothing was compared. Run '
              '--baseline once to pin the measured state. This is NOT a pass.' % PINS)
        return 2
    if pins.get('_unreadable'):
        print('')
        print('COULD NOT TELL -- %s will not parse (%s). NOTHING WAS COMPARED.'
              % (PINS, pins['_unreadable'][:80]))
        return 2
    if unreadable:
        print('')
        print('COULD NOT TELL -- %d api file(s) could not be read, so the counts '
              'above are over a smaller population than the repo has.' % len(unreadable))
        return 2

    # WORSE IN EITHER DIRECTION IS A REGRESSION. More uncovered gates is the
    # obvious one; more gates in a NEITHER file is the one a new endpoint
    # introduces without touching anything that exists.
    checks = [
        ('gates_in_files_with_neither_mechanism', gates_neither),
        ('gates_uncovered_inside_partial_files', gates_uncovered_in_partial),
        ('files_with_neither', len(neither)),
    ]
    bad = [(k, pins.get(k), v) for k, v in checks
           if pins.get(k) is not None and v > pins[k]]
    if bad:
        print('')
        print('REGRESSION -- session-gate re-check coverage got WORSE:')
        for k, was, now in bad:
            print('   %-42s pinned %s -> now %s' % (k, was, now))
        print('Either re-check the new gate, or say why it does not need it and')
        print('re-pin with --baseline in the same commit as the reason.')
        return 1
    improved = [(k, pins.get(k), v) for k, v in checks
                if pins.get(k) is not None and v < pins[k]]
    if improved:
        print('')
        print('IMPROVED -- re-pin with --baseline so the gain cannot be lost:')
        for k, was, now in improved:
            print('   %-42s pinned %s -> now %s' % (k, was, now))
        return 0
    print('')
    print('OK -- no worse than pinned. The gap itself is UNCHANGED and is not closed.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
