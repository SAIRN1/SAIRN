#!/usr/bin/env python3
"""tools/second_pass_coverage_scan.py -- which flows are only ever tested on
their FIRST attempt, and never on a second attempt following an aborted or
refused one?

    python tools/second_pass_coverage_scan.py
    python tools/second_pass_coverage_scan.py --list
    python tools/second_pass_coverage_scan.py --baseline

Exit 0 no worse than pinned, 1 a regression, 2 COULD NOT TELL.

── THE FAILURE CLASS, AND A REAL ONE RATHER THAN AN INVENTED ONE ────────────
The Boeing 737 MAX VNAV defect was invisible in steady-state flight. It required
a specific PRIOR STATE TRANSITION to surface: a missed approach, and then an
altered flight path. Every first-pass test passed. The aircraft only misbehaved on
the second attempt at something after the first had been abandoned.

Software tests have the same blind spot and it is structural, not lazy. A suite is
written by driving the happy path once, then adding refusal arms beside it. Each
arm STARTS FROM A CLEAN STATE. What almost nothing does is: attempt, have it
REFUSED or ABORTED, and then attempt again -- which is the state a real user is
in every time anything goes wrong.

THIS PLATFORM HAS ALREADY PAID FOR IT TWICE IN ONE DAY, both in the same shape:
  * `git checkout --ours` mid-rebase shipped six conflict markers into
    docs/tier-a-reviews.json. A rebase IS a re-attempt; the first apply failed.
  * tools/push_retry.py exists at all because a retry loop amended mid-rebase.
Both are second-attempt defects. Neither was a first-pass bug.

── WHAT IS MEASURED ────────────────────────────────────────────────────────
Per suite, per action driven:

  FIRST-PASS ONLY   the suite drives the action, and never drives it AGAIN after
                    asserting a refusal or an abort in the same test arm
  SECOND-PASS       some arm asserts a refusal/abort and then drives it again

The arm boundary is BRACE-MATCHED on masked source, never a fixed window -- a
fixed slice would pull the next arm's second drive into this arm and report
coverage that is not there. (That is the third paren/brace matcher in tools/; if a
fourth is written, extract it rather than copying again.)

── THE PRIMARY FINDING IS THE CROSS-REFERENCE, NOT THE RAW LIST ────────────
A raw "first-pass only" list is long and mostly uninteresting: plenty of actions
have no meaningful second attempt. So the headline is the INTERSECTION -- code
that DOCUMENTS a retry, resume, re-attempt or abort path, whose suite never
exercises the second pass. A documented retry with no second-pass arm is a claim
nobody tested.

The raw list is printed too, labelled as a list to READ. That distinction is
deliberate: an earlier tool of mine invented a long findings list from a weak
anchor and had to be deleted the same hour. A wide screen is only honest if it
says which half is load-bearing.

── WHAT IT CANNOT DO ───────────────────────────────────────────────────────
It reads TEXT. A second pass driven through a helper, a loop, or a fixture that
re-seeds state between attempts is invisible to it, so FIRST-PASS ONLY over-reports
and that is the safe direction here. It also cannot judge whether a given action
HAS a meaningful second attempt -- `read` mostly does not, `submit` mostly does --
and it does not guess.

A RATCHET, pinned to docs/second-pass-coverage.json. An absent or unparseable pin
is exit 2, and so is finding zero driven actions at all.
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = os.path.join(REPO, 'docs', 'second-pass-coverage.json')

ARM_START = re.compile(r"""\b(?:await\s+)?(?:test|it)\s*\(""")
ACTION = re.compile(r"""action\s*[:=]+\s*['"]([a-z][a-z0-9_]*)['"]""")

# A refusal or an abort ASSERTED -- the thing that makes the next drive a SECOND
# attempt rather than a first one.
REFUSED = re.compile(
    r"""FORBIDDEN|NOT_AUTHORIS|NOT_AUTHORIZ|CONFLICT|REFUS|DENIED|ABORT"""
    r"""|status(?:Code)?\s*,\s*(?:4\d\d|5\d\d)"""
    r"""|\b(?:4\d\d|5\d\d)\s*,"""
    r"""|ok\s*,\s*false|success\s*,\s*false""", re.I)

# Code that CLAIMS a retry/resume/abort path. The cross-reference half.
DOCUMENTS_RETRY = re.compile(
    r"""\bretry\b|\bretries\b|\bre-?attempt|\bresume\b|\brebase --continue"""
    r"""|\brebase --abort|\bsecond attempt|\btry again|\breplay\b""", re.I)

# Actions with no meaningful second attempt. Deliberately SHORT: a long list here
# would become the escape hatch that makes every finding disappear.
NO_SECOND_PASS_SENSE = {'read', 'list', 'get', 'status', 'whoami', 'compute',
                        'search', 'export', 'render', 'fingerprint'}


class CouldNotTell(Exception):
    pass


def mask(s):
    """s with string, comment and regex-literal CONTENTS blanked, same length.

    Braces inside a message string are not nesting levels. Counting them closes an
    arm early (under-report, safe); an unmatched brace in a string closes it late
    (over-report -- it would credit the NEXT arm's second drive to this one).
    """
    out = list(s)
    i, n = 0, len(s)
    prev = '\n'

    def blank(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '

    while i < n:
        c = s[i]
        if c in '\'"`':
            j, q = i + 1, c
            while j < n:
                if s[j] == '\\':
                    j += 2
                    continue
                if s[j] == q:
                    break
                j += 1
            blank(i, min(j + 1, n))
            prev, i = 'x', min(j + 1, n)
            continue
        if c == '/' and i + 1 < n and s[i + 1] == '/':
            j = s.find('\n', i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
            continue
        if c == '/' and i + 1 < n and s[i + 1] == '*':
            j = s.find('*/', i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
            continue
        if c == '#':  # python suites
            j = s.find('\n', i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
            continue
        if not c.isspace():
            prev = c
        i += 1
    return ''.join(out)


def arm_spans(src, masked):
    """[(start, end)] for each test arm, bounded by its own matching parenthesis."""
    spans = []
    for m in ARM_START.finditer(masked):
        paren = masked.find('(', m.start())
        if paren < 0:
            continue
        depth, i, n = 0, paren, len(masked)
        end = None
        while i < n:
            if masked[i] == '(':
                depth += 1
            elif masked[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
            i += 1
        if end is None:
            # The arm's extent could not be established. NOT credited with
            # second-pass coverage -- an unreadable arm is the third state.
            continue
        spans.append((m.start(), end))
    return spans


def suite_files():
    out = []
    for sub, exts in ((('api',), ('.test.js',)),
                      (('api', '_lib'), ('.test.js',)),
                      (('tests',), ('.js', '.py'))):
        base = os.path.join(REPO, *sub)
        if not os.path.isdir(base):
            continue
        walker = os.walk(base) if sub == ('tests',) else [(base, [], os.listdir(base))]
        for root, _, names in walker:
            for n in sorted(names):
                if n.endswith(exts):
                    out.append(os.path.join(root, n))
    if not out:
        raise CouldNotTell('no suite files found under api/ or tests/')
    return sorted(set(out))


def analyse_suite(src):
    """(first_pass_only, second_pass) as sets of action names."""
    masked = mask(src)
    driven, second = set(), set()
    for a in ACTION.findall(src):
        driven.add(a)
    for start, end in arm_spans(src, masked):
        arm_src = src[start:end]
        # Within one arm: a refusal asserted, and THEN the same action driven
        # again after it. Position matters -- a refusal after the last drive is
        # not a second attempt.
        hits = [(m.start(), m.group(1)) for m in ACTION.finditer(arm_src)]
        refusals = [m.start() for m in REFUSED.finditer(arm_src)]
        if not refusals or len(hits) < 2:
            continue
        for pos, name in hits:
            if any(r < pos for r in refusals) and any(p < min(
                    r for r in refusals if r < pos) for p, n2 in hits if n2 == name):
                second.add(name)
    return driven - second, second


def scan():
    results = {}
    for path in suite_files():
        rel = os.path.relpath(path, REPO).replace(os.sep, '/')
        try:
            src = io.open(path, encoding='utf-8', errors='replace').read()
        except OSError as exc:
            raise CouldNotTell('%s could not be read (%s) -- NOT a pass' % (rel, exc))
        first, second = analyse_suite(src)
        first = {a for a in first if a not in NO_SECOND_PASS_SENSE}
        if not first and not second:
            continue
        results[rel] = {
            'first_only': sorted(first),
            'second': sorted(second),
            'documents_retry': bool(DOCUMENTS_RETRY.search(src)),
        }
    if not results:
        raise CouldNotTell(
            'no suite drove an `action:` anywhere -- the drive shape moved and '
            'NOTHING was measured. This is NOT "everything is covered".')
    return results


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--baseline', action='store_true')
    args = ap.parse_args(argv)

    try:
        res = scan()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2

    documented = {r: v for r, v in res.items()
                  if v['documents_retry'] and v['first_only'] and not v['second']}
    any_second = {r for r, v in res.items() if v['second']}
    total_first = sum(len(v['first_only']) for v in res.values())

    print('SECOND-PASS COVERAGE -- is a flow ever retried after being refused?')
    print('The 737 MAX VNAV defect needed a missed approach and THEN an altered')
    print('path. First-pass tests all passed. This looks for that blind spot.')
    print('')
    print('%d suite(s) drive an action.' % len(res))
    print('  suites with ANY second-pass arm                     : %d' % len(any_second))
    print('  actions tested ONLY on a first attempt              : %d' % total_first)
    print('  *** suites that DOCUMENT a retry/resume/abort path')
    print('      and have NO second-pass arm at all              : %d' % len(documented))
    print('')

    if documented:
        print('THE LOAD-BEARING FINDING -- a documented retry nobody tested twice:')
        for rel in sorted(documented):
            print('   %s' % rel)
            print('      first-attempt only: %s'
                  % ', '.join(documented[rel]['first_only'][:8]))
        print('')

    if args.list:
        print('CONTEXT -- every first-attempt-only action. A LIST TO READ, not a')
        print('list of defects: a second pass driven through a helper or a loop is')
        print('invisible here, and many actions have no meaningful second attempt.')
        for rel in sorted(res):
            if res[rel]['first_only']:
                print('   %-58s %s' % (rel, ', '.join(res[rel]['first_only'][:6])))
        print('')

    if args.baseline:
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Pinned second-pass coverage. Written by '
                     'tools/second_pass_coverage_scan.py --baseline. A ratchet: '
                     '`documented_without_second_pass` must never rise.',
            '_why': 'A flow is normally tested from a clean state. The state a '
                    'user is actually in when anything goes wrong is the SECOND '
                    'attempt after a refused or aborted first one. Both of '
                    '2026-09-27 defects were that shape.',
            'documented_without_second_pass': len(documented),
            'documented_files': sorted(documented),
            'suites_with_second_pass': len(any_second),
            'first_attempt_only_actions': total_first,
            'suites_driving_actions': len(res),
        }, indent=2, sort_keys=True) + '\n')
        print('wrote %s' % os.path.relpath(PIN, REPO))
        return 0

    if not os.path.isfile(PIN):
        sys.stderr.write('COULD NOT TELL -- %s does not exist, so NOTHING was '
                         'compared. Run --baseline once.\n'
                         % os.path.relpath(PIN, REPO))
        return 2
    try:
        pin = json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        sys.stderr.write('COULD NOT TELL -- %s will not parse (%s). NOTHING WAS '
                         'COMPARED.\n' % (os.path.relpath(PIN, REPO), e))
        return 2
    was = pin.get('documented_without_second_pass')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer '
                         '`documented_without_second_pass`.\n')
        return 2

    now = len(documented)
    if now > was:
        print('REGRESSION -- documented retry paths with no second-pass arm rose '
              'from %d to %d.' % (was, now))
        print('Add an arm that drives the flow, asserts the refusal, and drives it')
        print('AGAIN -- or say why the second attempt cannot differ and re-pin.')
        return 1
    if now < was:
        print('IMPROVED -- fell from %d to %d. Re-pin:' % (was, now))
        print('   python tools/second_pass_coverage_scan.py --baseline')
        return 0
    print('OK -- no worse than pinned (%d).' % was)
    print('A RATCHET IS NOT A PASS. %d documented retry path(s) still have no arm '
          'that attempts the flow twice.' % now)
    return 0


if __name__ == '__main__':
    sys.exit(main())
