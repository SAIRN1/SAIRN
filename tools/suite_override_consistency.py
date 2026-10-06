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


def suite_files():
    """Every JS suite in the universe, from the SAME two places
    tools/run_all_tests.py:discover() reads.

    ── THIS WAS A HOLE IN THIS TOOL, FOUND 2026-10-06 ────────────────────
    The first version walked `tests/` only. `api/*.test.js` and
    `api/_lib/*.test.js` are suites too -- 71 of them read an app's HTML --
    and leaving them out did not merely narrow the sweep: a family's
    MAJORITY is computed from its members, so an excluded member can flip
    a convention from majority to minority and make a real finding
    disappear. A narrower corpus is not a smaller version of the same
    answer. That is the same shape cody measured in
    append_only_read_order_scan and schema_provisioning_check.
    """
    out = []
    for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__')]
        for f in sorted(files):
            if f.endswith('.js'):
                out.append(os.path.join(root, f))
    for sub in ('', '_lib', 'sairndental'):
        d = os.path.join(REPO, 'api', sub) if sub else os.path.join(REPO, 'api')
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.test.js'):
                out.append(os.path.join(d, f))
    return out


def scan():
    """-> (families, census). The census carries EVERY suite examined with a
    verdict, so "0 findings" can be read beside how many suites were in a
    position to produce one. A finding count with no denominator is the
    figure this repo keeps having to re-derive."""
    fams = {}
    census = []
    for p in suite_files():
        rel = os.path.relpath(p, REPO).replace('\\', '/')
        try:
            s = io.open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            census.append((rel, None, 'UNREADABLE', set()))
            continue
        apps = set(APP_RX.findall(s))
        envs = set(ENV_RX.findall(s))
        if not apps:
            census.append((rel, None, 'NO_APP_HTML', envs))
            continue
        if len(apps) > 1:
            # No single family, so no single convention to violate. Counted
            # rather than dropped: these are the suites this tool is BLIND to
            # by construction, and that is a number, not a footnote.
            census.append((rel, None, 'CROSS_APP', envs))
            continue
        app = apps.pop()
        fams.setdefault(app, []).append((rel, envs))
        census.append((rel, app, None, envs))
    return fams, census


def census_verdicts(fams, census):
    """Fill in the per-suite verdict for the app suites, now that family
    majorities are known. Returns {verdict: [rel, ...]}."""
    # The same rule findings() uses: any FILE-shaped override a sibling reads.
    seen = {}
    for app, members in fams.items():
        s = set()
        for _rel, envs in members:
            s |= set(e for e in envs if FILE_VAR_RX.search(e))
        seen[app] = s
    out = {}
    for rel, app, fixed, envs in census:
        if fixed:
            out.setdefault(fixed, []).append(rel)
            continue
        members = fams[app]
        if len(members) < 2:
            v = 'FAMILY_OF_ONE'
        elif not seen[app]:
            v = 'NO_CONVENTION'
        elif seen[app] - envs:
            v = 'FINDING'
        else:
            v = 'HONOURS'
        out.setdefault(v, []).append(rel)
    return out


# An override var only names an APP FILE when it looks like one. Credentials
# and service URLs are shared by every suite that talks to the API and have
# nothing to do with which file is read, so SD_AUTH_SECRET and SUPABASE_URL
# are not conventions about file substitution and must not be counted as one.
FILE_VAR_RX = re.compile(r'_HTML$|_FILE$|_PATH$|_SRC$')


def findings(fams, rule='any'):
    """Suites that read an app's HTML without an override a SIBLING honours.

    ── THE RULE CHANGED ON 2026-10-06, BECAUSE THE FIRST ONE COULD NOT FIRE ──
    The first version required a MAJORITY of the family to honour the var.
    Measured against the real tree that day, NO app-file override reaches a
    majority anywhere except sairnmechanical (3 of 3, where there is nothing
    to find): LEG_HTML is 2 of 7, SD_HTML 6 of 70, SB_HTML 7 of 20, DNT_HTML
    5 of 18. So the detector returned `findings 0` over 488 suites and COULD
    NOT HAVE RETURNED ANYTHING ELSE -- including for the exact incident it was
    written for, where a caller passed LEG_HTML to
    tests/sairnlegacy_write_failure_voice.js because two siblings accept it.

    A clean run from a rule that cannot fire is the shape this repo keeps
    paying for, and the number it produced would have been quoted.

    THE REAL MISREADING IS NOT ABOUT MAJORITIES. The caller did not count; the
    caller saw one sibling and generalised. So the trigger is ANY sibling, and
    the RATIO is reported with every finding -- `2 of 7` -- so a reader can
    see for themselves that it is not a convention. That is the methodology
    rule this measurement produced: a convention inferred from a sample states
    n of N before it is used as evidence.

    `rule='majority'` is kept so the old behaviour is still runnable and the
    difference is measurable rather than asserted.
    """
    out = []
    for app, members in sorted(fams.items()):
        if len(members) < 2:
            continue   # a family of one has no sibling to disagree with
        counts = {}
        for _rel, envs in members:
            for e in envs:
                if FILE_VAR_RX.search(e):
                    counts[e] = counts.get(e, 0) + 1
        for var, n in sorted(counts.items()):
            if rule == 'majority' and n * 2 <= len(members):
                continue
            missing = [rel for rel, envs in members if var not in envs]
            for rel in missing:
                out.append({'app': app, 'var': var, 'suite': rel,
                            'honoured_by': n, 'family': len(members),
                            'is_majority': n * 2 > len(members)})
    return out


def selftest():
    """Fixtures. A detector whose only evidence is a clean sweep of the real
    tree is indistinguishable from one that cannot detect anything."""
    # (name, families, expected under rule='any', expected under 'majority')
    cases = [
        ('majority honours it, one does not -> FINDING under both rules',
         {'a': [('s1', {'X_HTML'}), ('s2', {'X_HTML'}), ('s3', set())]}, 1, 1),
        ('every member honours it -> clean under both',
         {'a': [('s1', {'X_HTML'}), ('s2', {'X_HTML'}), ('s3', {'X_HTML'})]}, 0, 0),
        ('NO member honours it -> clean, there is no convention to violate',
         {'a': [('s1', set()), ('s2', set()), ('s3', set())]}, 0, 0),
        # ── THE ARM THE RULE CHANGE EXISTS FOR ────────────────────────────
        # A MINORITY honours it. The old majority rule called this clean, and
        # that is the shape of the real 2026-10-05 incident: a caller passed
        # LEG_HTML to a suite that ignores it because two siblings accept it.
        ('a MINORITY honours it -> FINDING under `any`, MISSED by `majority`',
         {'a': [('s1', {'X_HTML'}), ('s2', set()), ('s3', set())]}, 2, 0),
        ('family of two with one override -> FINDING under `any` only',
         {'a': [('s1', {'X_HTML'}), ('s2', set())]}, 1, 0),
        ('a family of ONE cannot disagree with a sibling -> clean',
         {'a': [('s1', set())]}, 0, 0),
        ('two families are judged independently',
         {'a': [('s1', {'A_HTML'}), ('s2', {'A_HTML'}), ('s3', set())],
          'b': [('t1', set()), ('t2', set()), ('t3', set())]}, 1, 1),
        # ── CREDENTIALS ARE NOT A FILE-SUBSTITUTION CONVENTION ────────────
        # Measured in the real tree: SD_AUTH_SECRET and SUPABASE_URL are read
        # by whichever suites talk to the API, which says nothing about which
        # FILE a suite reads. Counting them produced findings against suites
        # that had no file override to be inconsistent about.
        ('a shared CREDENTIAL var is not a file convention -> clean',
         {'a': [('s1', {'SD_AUTH_SECRET'}), ('s2', set()), ('s3', set())]}, 0, 0),
        ('...and an app-file var in the SAME family is still caught',
         {'a': [('s1', {'SD_AUTH_SECRET', 'X_HTML'}), ('s2', {'SD_AUTH_SECRET'}),
                ('s3', set())]}, 2, 0),
    ]
    bad = 0
    for name, fam, want_any, want_maj in cases:
        got_any = len(findings(fam, rule='any'))
        got_maj = len(findings(fam, rule='majority'))
        ok = got_any == want_any and got_maj == want_maj
        print(('  ok   ' if ok else '  FAIL ') + name)
        if not ok:
            bad += 1
            print('        any: wanted %d got %d | majority: wanted %d got %d'
                  % (want_any, got_any, want_maj, got_maj))
    verdicts = set(len(findings(f, rule='any')) > 0 for _n, f, _a, _m in cases)
    if verdicts != {True, False}:
        print('  FAIL CONTROL: the fixture set does not reach both verdicts')
        bad += 1
    else:
        print('  ok   CONTROL: the fixture set reaches both verdicts')
    # ── ABLATION: the rule change has to be load-bearing on these fixtures,
    # not just differently worded. At least one case must separate the two.
    sep = [n for n, f, a, m in cases
           if len(findings(f, rule='any')) != len(findings(f, rule='majority'))]
    if not sep:
        print('  FAIL CONTROL: no fixture separates `any` from `majority`, so '
              'the rule change is not proven here')
        bad += 1
    else:
        print('  ok   CONTROL: %d fixture(s) separate `any` from `majority`'
              % len(sep))
    print('\n%d case(s), %d failed' % (len(cases), bad))
    return 1 if bad else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--selftest' in argv:
        return selftest()
    fams, census = scan()
    if not fams:
        sys.stderr.write('COULD NOT RUN -- no app suite found under tests/ or '
                         'api/. That is not a clean result.\n')
        return 2
    found = findings(fams)
    verdicts = census_verdicts(fams, census)
    ORDER = ('FINDING', 'HONOURS', 'NO_CONVENTION', 'FAMILY_OF_ONE',
             'CROSS_APP', 'NO_APP_HTML', 'UNREADABLE')
    if '--json' in argv:
        print(json.dumps({'families': len(fams), 'findings': found,
                          'suites_examined': len(census),
                          'verdicts': dict((k, sorted(verdicts.get(k, [])))
                                           for k in ORDER if verdicts.get(k))},
                         indent=2, sort_keys=True))
        return 1 if found else 0
    print('SUITE OVERRIDE CONSISTENCY -- does one suite ignore what its siblings honour?')
    print('  JS suites examined      %3d   tests/**.js + api/**/*.test.js'
          % len(census))
    print('  app families examined   %3d' % len(fams))
    print('  findings                %3d' % len(found))
    print('')
    print('  PER-VERDICT CENSUS -- the denominator the finding count needs')
    for k in ORDER:
        n = len(verdicts.get(k, []))
        if n:
            print('    %-18s %4d' % (k, n))
    print('    %-18s %4d   <- must equal the suites examined above'
          % ('TOTAL', sum(len(v) for v in verdicts.values())))
    print('')
    print('  ONLY `FINDING` AND `HONOURS` WERE IN A POSITION TO PRODUCE A')
    print('  FINDING. Everything below NO_CONVENTION is a suite this tool')
    print('  cannot judge -- not a suite it judged clean. Read the two')
    print('  numbers, never the finding count alone.')
    print('')
    maj = sum(1 for f in found if f['is_majority'])
    print('  of the %d findings, %d sit under a MAJORITY convention and %d '
          'under a MINORITY one' % (len(found), maj, len(found) - maj))
    print('  -- the ratio is printed per finding because a convention '
          'inferred from')
    print('  a sample has to state n of N before it is used as evidence. '
          'LEG_HTML')
    print('  is 2 of 7, and that is what the 2026-10-05 A/B comparison '
          'rested on.')
    print('')
    for f in found:
        print('  %-58s no %-12s (%d of %d %s suites read it)'
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
