#!/usr/bin/env python
# OWNER: fourth
r"""A SUITE THAT READS ITS APP FILE WITHOUT THE OVERRIDE ITS SIBLINGS HONOUR.

    python tools/suite_override_consistency.py
    python tools/suite_override_consistency.py --json
    python tools/suite_override_consistency.py --selftest

REPORT ONLY. Exit 0 clean, 1 findings, 2 COULD NOT RUN. Writes nothing.

── THE INCIDENT, AND WHY THE OBVIOUS SWEEP MISSES IT ──────────────────────
On 2026-10-05 a session needed to know whether a change to `sairnlegacy.html`
had broken `tests/sairnlegacy_write_failure_voice.js`. It ran

    LEG_HTML=<pre-change copy> node tests/sairnlegacy_write_failure_voice.js
    node tests/sairnlegacy_write_failure_voice.js

got the same failure both times, and read that as "pre-existing, not mine."

**That suite does not read `LEG_HTML`.** It reads `path.join(ROOT, FILE)`.
Both runs tested the identical file, so the comparison established nothing --
while looking like a careful A/B. The conclusion happened to be correct, which
is the worst outcome: a void method that returns the right answer gets reused.

A sweep for "suites that DOCUMENT an override they ignore" does NOT catch it.
That suite documents nothing; the override was invented by the caller, who
assumed the convention held because **its siblings honour it**:
`tests/sairnlegacy_item_price_lists.js` and
`tests/sairnlegacy_reservation_lock.js` both read `LEG_HTML`.

── SO THE SIGNAL IS INCONSISTENCY WITHIN A FAMILY, NOT AN ABSENT FEATURE ──
This finds suites that read an app's HTML while a MAJORITY of the suites
reading that same app accept an override for it. That is the state in which a
reader reasonably assumes the override works everywhere -- and is wrong about
exactly one file.

**A suite with no override is not itself a defect.** Plenty are deliberately
pinned to the real file. The finding is the MIXED family, and the fix is a
judgement: add the override, or say in the header that this one is pinned.
Both are better than silence, because silence is what the caller read.

── WHAT IT CANNOT SEE ─────────────────────────────────────────────────────
* An override read through a helper rather than `process.env` directly.
* A family of one: with a single suite there is no majority and no
  expectation to violate, so it is skipped rather than guessed at.
* Whether the override, where present, actually reaches the read -- that is
  `grep` finding the name, not dataflow. A suite that reads the variable and
  then ignores the value would pass here.
"""

import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_RX = re.compile(r"process\.env\.([A-Z][A-Z0-9_]{2,})")
# A suite "is about" an app when it names that app's HTML file.
APP_RX = re.compile(r"['\"](sairn[a-z]+|stonedesk)(?:-[a-z]+)?\.html['\"]")


def scan():
    fams = {}
    for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__')]
        for f in sorted(files):
            if not f.endswith('.js'):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace('\\', '/')
            try:
                s = io.open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            apps = set(APP_RX.findall(s))
            if len(apps) != 1:
                continue            # 0 = not an app suite; >1 = cross-app, no single family
            app = apps.pop()
            envs = set(ENV_RX.findall(s))
            fams.setdefault(app, []).append((rel, envs))
    return fams


def findings(fams):
    out = []
    for app, members in sorted(fams.items()):
        if len(members) < 3:
            continue   # no majority to violate
        counts = {}
        for _rel, envs in members:
            for e in envs:
                counts[e] = counts.get(e, 0) + 1
        for var, n in sorted(counts.items()):
            if n * 2 <= len(members):
                continue   # not a majority convention
            missing = [rel for rel, envs in members if var not in envs]
            for rel in missing:
                out.append({'app': app, 'var': var, 'suite': rel,
                            'honoured_by': n, 'family': len(members)})
    return out


def selftest():
    """Fixtures. A detector whose only evidence is a clean sweep of the real
    tree is indistinguishable from one that cannot detect anything."""
    cases = [
        ('majority honours it, one does not -> FINDING',
         {'a': [('s1', {'X_HTML'}), ('s2', {'X_HTML'}), ('s3', set())]}, 1),
        ('every member honours it -> clean',
         {'a': [('s1', {'X_HTML'}), ('s2', {'X_HTML'}), ('s3', {'X_HTML'})]}, 0),
        ('NO member honours it -> clean, there is no convention to violate',
         {'a': [('s1', set()), ('s2', set()), ('s3', set())]}, 0),
        ('a MINORITY honours it -> clean, one suite is not a convention',
         {'a': [('s1', {'X_HTML'}), ('s2', set()), ('s3', set())]}, 0),
        ('family of two is skipped -- no majority exists',
         {'a': [('s1', {'X_HTML'}), ('s2', set())]}, 0),
        ('two families are judged independently',
         {'a': [('s1', {'A_HTML'}), ('s2', {'A_HTML'}), ('s3', set())],
          'b': [('t1', set()), ('t2', set()), ('t3', set())]}, 1),
    ]
    bad = 0
    for name, fam, want in cases:
        got = len(findings(fam))
        ok = got == want
        print(('  ok   ' if ok else '  FAIL ') + name)
        if not ok:
            bad += 1
            print('        wanted %d finding(s), got %d' % (want, got))
    verdicts = set(len(findings(f)) > 0 for _n, f, _w in cases)
    if verdicts != {True, False}:
        print('  FAIL CONTROL: the fixture set does not reach both verdicts')
        bad += 1
    else:
        print('  ok   CONTROL: the fixture set reaches both verdicts')
    print('\n%d case(s), %d failed' % (len(cases), bad))
    return 1 if bad else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--selftest' in argv:
        return selftest()
    fams = scan()
    if not fams:
        sys.stderr.write('COULD NOT RUN -- no app suite found under tests/. '
                         'That is not a clean result.\n')
        return 2
    found = findings(fams)
    if '--json' in argv:
        print(json.dumps({'families': len(fams), 'findings': found},
                         indent=2, sort_keys=True))
        return 1 if found else 0
    print('SUITE OVERRIDE CONSISTENCY -- does one suite ignore what its siblings honour?')
    print('  app families examined   %3d' % len(fams))
    print('  findings                %3d' % len(found))
    print('')
    for f in found:
        print('  %-54s does NOT read %s, which %d of %d %s suites do'
              % (f['suite'], f['var'], f['honoured_by'], f['family'], f['app']))
    print('')
    print('A SUITE WITHOUT AN OVERRIDE IS NOT ITSELF A DEFECT -- many are')
    print('deliberately pinned to the real file. The finding is the MIXED')
    print('family: a caller reasonably assumes the convention holds and is')
    print('wrong about one file. Add the override, or say in the header that')
    print('this one is pinned. Silence is what gets misread.')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
