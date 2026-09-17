#!/usr/bin/env python
"""Which failing suites are ALREADY KNOWN, and which one is new.

    python tools/known_red_check.py --from-run <run-all-tests output file>
    python tools/known_red_check.py --run          # run the suite first (slow)
    python tools/known_red_check.py --fixtures
    python tools/known_red_check.py --json

Exit 0 when every red suite is a known one and no entry is stale, 1 when
something needs a human, 2 when the question could not be answered. REPORT
ONLY -- nothing gates on this.

── THE PROBLEM, WHICH IS NOT THAT SUITES ARE RED ───────────────────────────
33 of 390 test files were red on origin/main when this was written, and nothing
recorded which 33. That number is not itself the defect -- a platform this size
carries known breakage and says so. The defect is that a GENUINELY NEW
REGRESSION IS INDISTINGUISHABLE FROM THE EXISTING SET. A reader who runs the
suite sees "34 failing" where yesterday said 33 and has no way to tell which one
is new without diffing two hour-long runs by hand, so in practice nobody does,
and "some suites are just red" becomes the reading.

That is the same shape as an untested assertion: a signal that cannot change
meaning is a signal nobody acts on.

── THE FOUR ANSWERS, AND WHY THREE OF THEM MATTER ─────────────────────────
  NEW        red, and not in the registry. THE ONE THE TOOL EXISTS FOR.
  KNOWN      red, in the registry, failing on the same arm it was recorded on.
  CHANGED    red, in the registry, but failing on a DIFFERENT arm. Not folded
             into KNOWN: a file recorded as red for reason A and now failing
             for reason B has a second defect that nothing recorded, and it is
             hiding inside an entry that says it is expected.
  RECOVERED  in the registry and now GREEN. Reported as loudly as NEW, and
             this is the half most such registries get wrong: a stale entry
             does not merely clutter the file, it SWALLOWS THE NEXT REAL
             FAILURE of that suite -- the tool would call it KNOWN.

A registry that only ever grows is an allow-list, and an allow-list over
failures is how a platform stops noticing them.

── WHAT IT DOES NOT DO ────────────────────────────────────────────────────
  * It does not judge whether a known-red suite SHOULD be red. The `why` field
    is a human's sentence and this tool never writes one.
  * It does not gate. A new red suite is a finding for a person, and making it
    blocking would turn every unrelated push into a hostage.
  * It cannot see a suite that is GREEN AND WRONG. Its whole subject is the
    exit code, which is the weakest thing a suite tells you.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN   # noqa: E402

REGISTRY = os.path.join(REPO, 'docs', 'known-red-suites.json')

# `  FAIL py    tests/x.py    the tail the runner printed`
FAIL_RE = re.compile(r'^\s{2}FAIL\s+(node|py)\s+(\S+)\s*(.*)$')
OK_RE = re.compile(r'^\s{2}ok\*?\s+(node|py)\s+(\S+)')
# The runner's own summary, used to refuse a truncated log.
# ── re.M IS LOAD-BEARING AND ITS ABSENCE WAS CAUGHT BY THE BLIND LOCK ───────
# These were compiled without re.MULTILINE, so `^` anchored to the START OF THE
# WHOLE LOG. TOTAL_RE matched only because a run log happens to begin with its
# RAN: line, and COUNT_RE -- which sits at the END -- could never match at all.
# The stated-count cross-check therefore never ran, in the fixtures OR on a real
# log, and the tool would have accepted a log whose own summary disagreed with
# the failures it listed. A pattern that cannot match is indistinguishable from
# a condition that never occurs.
TOTAL_RE = re.compile(r'^RAN:\s+(\d+)\s+JS\s+\+\s+(\d+)\s+PY\s+=\s+(\d+)\s+files', re.M)
COUNT_RE = re.compile(r'^(\d+)\s+FAILING TEST FILE\(S\)', re.M)


def parse_run(text):
    """(red {file: tail}, green {files}, error). Refuses a log it cannot trust."""
    red, green = {}, set()
    for line in text.split('\n'):
        m = FAIL_RE.match(line)
        if m:
            red[m.group(2).replace('\\', '/')] = m.group(3).strip()
            continue
        m = OK_RE.match(line)
        if m:
            green.add(m.group(2).replace('\\', '/'))
    # ── A TRUNCATED LOG MUST NOT READ AS A CLEAN PLATFORM ──────────────────
    # The runner prints its own totals. If they are absent the log was cut off
    # -- a killed run, a `head`, a still-open file -- and every suite after the
    # cut would silently count as NOT RED, which is exactly how a registry
    # would come to swallow a real regression.
    if not TOTAL_RE.search(text) and not COUNT_RE.search(text):
        return None, None, ('the run log carries neither a RAN: line nor a '
                            'FAILING TEST FILE(S) line, so it was truncated or '
                            'is not a run_all_tests.py log. Nothing was '
                            'compared.')
    stated = COUNT_RE.search(text)
    if stated and int(stated.group(1)) != len(red):
        return None, None, ('the log says %s FAILING TEST FILE(S) and %d FAIL '
                            'lines were parsed. One of the two is wrong and '
                            'this tool will not pick.'
                            % (stated.group(1), len(red)))
    return red, green, ''


def load_registry():
    if not os.path.isfile(REGISTRY):
        return None, 'no registry at %s' % REGISTRY
    try:
        d = json.load(io.open(REGISTRY, encoding='utf-8'))
    except ValueError as e:
        return None, 'the registry does not parse: %s' % e
    if not isinstance(d.get('entries'), list):
        return None, 'the registry has no `entries` list'
    return d, ''


def classify(red, green, entries):
    """NEW / KNOWN / CHANGED / RECOVERED."""
    known = {e['file']: e for e in entries}
    new, same, changed, recovered = [], [], [], []
    for path, tail in sorted(red.items()):
        e = known.get(path)
        if e is None:
            new.append((path, tail))
        elif _same_reason(e.get('tail', ''), tail):
            same.append((path, tail))
        else:
            changed.append((path, e.get('tail', ''), tail))
    for path, e in sorted(known.items()):
        if path in green:
            recovered.append((path, e.get('why', '')))
    return new, same, changed, recovered


def _same_reason(recorded, observed):
    """Is this the failure the entry recorded, or a different one?

    COMPARED ON THE RUNNER'S TAIL LINE, loosely. An exact match would make
    every entry stale the moment a count in the message moved -- "12/13 passed"
    becoming "11/13 passed" is the SAME defect getting worse, not a new one.
    Digits are therefore normalised away and the rest must match.

    That is deliberately the weaker direction: two different failures whose
    messages differ only in digits would read as the same. The alternative --
    exact matching -- produces a CHANGED row on every count movement, and a
    tool that cries wolf on its own registry is one nobody keeps current.
    """
    norm = lambda s: re.sub(r'\d+', 'N', (s or '').strip().lower())
    return norm(recorded) == norm(observed)


# ── THE BLIND LOCK ───────────────────────────────────────────────────────────
LOG_HEAD = 'RAN: 100 JS + 100 PY = 200 files (0 skipped)\n'
FIXTURES = (
    ('a red suite absent from the registry is NEW',
     LOG_HEAD + '  FAIL py    tests/a.py    boom\n1 FAILING TEST FILE(S)\n',
     [], {'new': ['tests/a.py'], 'same': [], 'changed': [], 'recovered': []}),
    ('a red suite in the registry, same tail, is KNOWN',
     LOG_HEAD + '  FAIL py    tests/a.py    boom\n1 FAILING TEST FILE(S)\n',
     [{'file': 'tests/a.py', 'tail': 'boom', 'why': 'x'}],
     {'new': [], 'same': ['tests/a.py'], 'changed': [], 'recovered': []}),
    ('...and a DIFFERENT tail is CHANGED, not KNOWN',
     LOG_HEAD + '  FAIL py    tests/a.py    a different arm\n1 FAILING TEST FILE(S)\n',
     [{'file': 'tests/a.py', 'tail': 'boom', 'why': 'x'}],
     {'new': [], 'same': [], 'changed': ['tests/a.py'], 'recovered': []}),
    ('...but a tail differing only in DIGITS is the same defect moving',
     LOG_HEAD + '  FAIL py    tests/a.py    11/13 passed\n1 FAILING TEST FILE(S)\n',
     [{'file': 'tests/a.py', 'tail': '12/13 passed', 'why': 'x'}],
     {'new': [], 'same': ['tests/a.py'], 'changed': [], 'recovered': []}),
    ('a registry entry now GREEN is RECOVERED -- a stale entry swallows the '
     'next real failure of that file',
     LOG_HEAD + '  ok   py    tests/a.py\n0 FAILING TEST FILE(S)\n',
     [{'file': 'tests/a.py', 'tail': 'boom', 'why': 'x'}],
     {'new': [], 'same': [], 'changed': [], 'recovered': ['tests/a.py']}),
    ('a green suite nobody recorded is not any of the four',
     LOG_HEAD + '  ok   py    tests/b.py\n0 FAILING TEST FILE(S)\n',
     [], {'new': [], 'same': [], 'changed': [], 'recovered': []}),
)


def run_fixtures():
    wrong = []
    for label, log, entries, want in FIXTURES:
        red, green, err = parse_run(log)
        if err:
            wrong.append('%-62s parse refused: %s' % (label, err))
            continue
        new, same, changed, recovered = classify(red, green, entries)
        got = {'new': [p for p, _ in new], 'same': [p for p, _ in same],
               'changed': [p for p, _, _ in changed],
               'recovered': [p for p, _ in recovered]}
        if got != want:
            wrong.append('%-62s expected %s, got %s' % (label, want, got))

    # THE TRUNCATION REFUSAL, both directions. Without it a cut-off log reports
    # every suite after the cut as not-red, which is the failure this registry
    # would otherwise institutionalise.
    _r, _g, err = parse_run('  FAIL py    tests/a.py    boom\n')
    if not err:
        wrong.append('a log with no totals line was ACCEPTED -- a truncated run '
                     'would read as a clean platform')
    _r, _g, err = parse_run(LOG_HEAD + '  FAIL py    tests/a.py  boom\n'
                            '2 FAILING TEST FILE(S)\n')
    if not err:
        wrong.append('a log whose stated count disagrees with its FAIL lines '
                     'was ACCEPTED')
    _r, _g, err = parse_run(LOG_HEAD + '0 FAILING TEST FILE(S)\n')
    if err:
        wrong.append('a WELL-FORMED log with no failures was refused: %s' % err)

    if wrong:
        print('REFUSING: the criteria do not classify their own fixtures.')
        for w in wrong:
            print('  ' + w)
        return EXIT_COULD_NOT_RUN
    print('  %d/%d fixtures correct, plus 3 log-trust arms.'
          % (len(FIXTURES), len(FIXTURES)))
    return EXIT_CLEAN


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    if '--run' in argv:
        p = subprocess.run([sys.executable,
                            os.path.join(REPO, 'tools', 'run_all_tests.py')],
                           cwd=REPO, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        text = (p.stdout or '') + (p.stderr or '')
    elif '--from-run' in argv:
        path = argv[argv.index('--from-run') + 1]
        try:
            text = io.open(path, encoding='utf-8', errors='replace').read()
        except OSError as e:
            print('COULD NOT RUN: %r -- nothing was compared.' % e)
            return EXIT_COULD_NOT_RUN
    else:
        print('COULD NOT RUN: pass --from-run <log> or --run. This tool '
              'compares a run against the registry and will not invent one.')
        return EXIT_COULD_NOT_RUN

    red, green, err = parse_run(text)
    if err:
        print('COULD NOT RUN: %s' % err)
        return EXIT_COULD_NOT_RUN
    reg, err = load_registry()
    if err:
        print('COULD NOT RUN: %s' % err)
        return EXIT_COULD_NOT_RUN

    new, same, changed, recovered = classify(red, green, reg['entries'])

    if '--json' in argv:
        print(json.dumps({'new': new, 'known': same, 'changed': changed,
                          'recovered': recovered,
                          'red_total': len(red), 'green_total': len(green)},
                         indent=2))
        return EXIT_FINDING if (new or changed or recovered) else EXIT_CLEAN

    print('KNOWN-RED SUITES -- report only, nothing gates on this')
    print('  %d red, %d green in this run; the registry records %d.'
          % (len(red), len(green), len(reg['entries'])))
    print('  registry measured %s against %s'
          % (reg.get('measured', '?'), (reg.get('measured_against') or '?')[:12]))
    print('')

    if new:
        print('  NEW (%d) -- RED AND NOT RECORDED. This is the one to read:'
              % len(new))
        for p, tail in new:
            print('    %-52s %s' % (p, tail[:70]))
        print('')
    if changed:
        print('  CHANGED (%d) -- recorded as red, now failing on a DIFFERENT '
              'arm. A second defect is hiding inside an entry that says this '
              'file is expected to fail:' % len(changed))
        for p, was, now in changed:
            print('    %s' % p)
            print('        recorded: %s' % was[:70])
            print('        observed: %s' % now[:70])
        print('')
    if recovered:
        print('  RECOVERED (%d) -- recorded as red and GREEN in this run. The '
              'entry is STALE and must be removed: while it stands, the next '
              'real failure of this file reads as KNOWN:' % len(recovered))
        for p, why in recovered:
            print('    %-52s was: %s' % (p, why[:60]))
        print('')
    if same:
        print('  KNOWN (%d), unchanged. Listed by name rather than counted, '
              'because a number cannot be checked against anything:' % len(same))
        for p, _ in same:
            print('    %s' % p)
        print('')

    # ── THE UNDIAGNOSED COUNT, BECAUSE THE REGISTRY PROMISES IT ────────────
    # docs/known-red-suites.json says a blank `why` is "a backlog rather than a
    # shrug, because tools/known_red_check.py reports how many entries are
    # undiagnosed". It did not, until this was added -- a document claiming a
    # behaviour of a tool that does not have it is the same defect as a comment
    # claiming an arm sees something it cannot. Printed on EVERY run, including
    # a clean one, so the backlog cannot be read as absent.
    undiagnosed = [e['file'] for e in reg['entries'] if not (e.get('why') or '').strip()]
    print('  UNDIAGNOSED: %d of %d entries record WHAT is red and not WHY.'
          % (len(undiagnosed), len(reg['entries'])))
    if undiagnosed:
        print('  A blank `why` is honest -- an invented cause ends the')
        print('  investigation -- but it is a backlog, not a resolution:')
        for f in undiagnosed[:8]:
            print('    %s' % f)
        if len(undiagnosed) > 8:
            print('    ...and %d more' % (len(undiagnosed) - 8))
    print('')

    if not (new or changed or recovered):
        print('  Every red suite in this run is a recorded one, on the arm it '
              'was recorded on, and no entry has gone stale.')
        print('')
        print('  THAT IS NOT "THE PLATFORM IS HEALTHY". %d suites are red and '
              'this tool only says somebody wrote down that they are.' % len(red))
        return EXIT_CLEAN
    return EXIT_FINDING


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
