"""tests/run_primitive_obsession_probe.py -- does the primitive-obsession
check's fixture lock actually hold its criteria, or does a broken detector run
on real data anyway?

    python tests/run_primitive_obsession_probe.py

REQUIREMENT: for every mutation planted in tools/primitive_obsession_check.py,
a real run must exit 2 (COULD NOT RUN -- the lock refused) or 1 (a fixture
became a real finding) -- NEVER 0. Exit 0 with a broken detector is a checker
reporting CLEAN over shapes it can no longer see, which is the exact silent
state the cross-domain disciplines' fixture-lock convention exists to prevent.

Run directly rather than through sabotage_harness: the suite under test IS the
tool's own --self-test plus a real run, and the harness models a separate
suite file.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'primitive_obsession_check.py')

MUTATIONS = [
    ("1. THE MEASURED-DEFAULT DETECTOR GOES BLIND: the || half of the pattern "
     "is broken, so Number(amount)||0 -- the sairndental silent-$0 shape -- "
     "stops matching anything and every money default reports clean",
     "r'(0(?![\\w.])|[\\'\"][^\\'\"]*[\\'\"]|\\d[\\w.]*)')",
     "r'(9999NEVERMATCHES)')"),

    ("2. THE ENV DETECTOR GOES BLIND: process.env stops being part of the "
     "pattern, so Number(process.env.X) -- where '' is 0 and a cleared "
     "feature looks configured -- is invisible",
     r"process\.env",
     r"process\.envZZZ"),

    ("3. THE LOCALE-DATE STORE DETECTOR GOES BLIND: the assignment half is "
     "broken, so `date: new Date().toLocaleDateString()` reports clean",
     "toLocaleDateString\\s*\\(')",
     "toLocaleDateStringZZZ\\s*\\(')"),

    ("4. THE STRIPPER STOPS BLANKING STRINGS, so the shape quoted inside a "
     "refusal message becomes a finding -- the fixture asserting prose is "
     "not code must catch this, or the tool starts teaching exemptions",
     "        if c in ('\"', \"'\", '`'):\n            quote = c",
     "        if False:\n            quote = c"),

    # 5 IS A COMPOUND, AND THE FIRST VERSION OF THIS PROBE PROVED IT HAS TO
    # BE. Skipping the lock ALONE exits 0 legitimately -- the detectors are
    # intact, real data is clean, nothing is wrong yet. The defect only bites
    # when the lock is gone AND a detector drifts, so that is what is planted:
    # both at once. What refuses it is the tool's shape-vanish backstop (a
    # shape with baselined keys finding zero matches is exit 2), which was
    # ADDED because this arm's first version survived.
    ("5. THE LOCK IS SKIPPED AND A DETECTOR DRIFTS in the same change -- "
     "every env-number key reports 'fixed since baseline' and a tool with no "
     "backstop exits 0, CLEAN over a shape it can no longer see",
     "    lockfail = fixture_lock()",
     "    lockfail = []\n"
     "    globals()['ENV_NUMBER_RE'] = re.compile('NEVERMATCHESANYTHING')"),
]


def run_tool(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO)
    return r.returncode


def main():
    src = io.open(TOOL, encoding='utf-8').read()
    failures = []
    ok = 0

    print('primitive-obsession check: a broken detector must REFUSE to judge, '
          'never report CLEAN\n')

    # CONVENTION 18, 2026-10-07: ONE ASSERTION PER ARM, AND A LIVE-TREE ARM
    # NEVER GATES THE REST.
    #
    # This block used to be `if run_tool() != 0: print FAIL 0; return 1` -- a
    # precondition gate on the state of the REAL REPOSITORY. Ordinary feature
    # work makes the tool exit 1 (18 new unbaselined occurrences across five
    # apps at eb430f25), and the probe then printed ONE line and ran NONE of
    # its mutation arms. The detector was unverified in either direction, which
    # is worse than a red arm, and it is worse than the identical assertion in
    # tests/run_truthy_sum_probe.py, which sits LAST and still reports 13
    # passing arms. Same assertion, opposite blast radius, from ordering alone.
    #
    # THE GATE WAS NOT GRATUITOUS and that is why this is a degrade, not a
    # deletion. The per-mutation criterion below is `rc != 0`, and on a dirty
    # tree the UNMUTATED tool already exits 1 -- so `rc != 0` would be
    # satisfied whether or not the mutation was caught. The arm would pass
    # vacuously.
    #
    # SO THE CRITERION NARROWS INSTEAD OF THE PROBE STOPPING. Exit 2 is the
    # fixture lock refusing, and it is unambiguous on a dirty tree because the
    # real run's findings produce 1, never 2. When the baseline is dirty every
    # mutation must produce exactly 2; when it is clean the original `rc != 0`
    # stands. The criterion in force is PRINTED, because a narrower test
    # reported as the wider one is the thing this whole file exists to prevent.
    _baseline = run_tool()
    _strict = _baseline != 0
    if _strict:
        print('  WARN 0. the tool is NOT clean on the real tree (exit %d), so '
              'the mutation criterion NARROWS to exit==2 (the fixture lock '
              'refusing) rather than exit!=0 -- on a dirty tree exit 1 is '
              'ambiguous between "mutation caught" and "real findings".'
              % _baseline)
        print('       THIS IS NOT A PASS AND NOT A STOP. The arms below still '
              'run and still mean something; they mean something NARROWER, '
              'and the exit code at the end reflects only what was tested.')
    else:
        print('  ok   0. the tool is CLEAN on the real tree before anything is '
              'planted, so the criterion is the full exit!=0')

    for i, (title, old, new) in enumerate(MUTATIONS, 1):
        if old not in src:
            failures.append(title)
            print('  FAIL %d. MUTATION DID NOT APPLY -- anchor not found. The '
                  'tool changed shape and this probe is testing nothing: %s'
                  % (i, title[:80]))
            continue
        mutated = src.replace(old, new, 1)
        io.open(TOOL, 'w', encoding='utf-8', newline='').write(mutated)
        try:
            rc = run_tool()
        finally:
            io.open(TOOL, 'w', encoding='utf-8', newline='').write(src)
        _caught = (rc == 2) if _strict else (rc != 0)
        if not _caught:
            failures.append(title)
            print('  FAIL %d. %s -- the tool exited %d with this defect '
                  'planted%s: %s'
                  % (i,
                     'NOT REFUSED BY THE LOCK' if _strict else 'SILENT',
                     rc,
                     ' (criterion: exit==2, because the baseline is dirty)'
                     if _strict else '',
                     title[:100]))
        else:
            ok += 1
            print('  ok   %d. refused (exit %d%s): %s'
                  % (i, rc, ', lock' if _strict else '', title[:100]))

    if io.open(TOOL, encoding='utf-8').read() != src:
        print('  FAIL restore -- the tool is not byte-identical after the probe')
        return 1
    print('  ok   the tool is byte-identical again')
    # ALSO CONVENTION 18: this was a second live-tree gate with a `return 1`.
    # Whether the restored tool is CLEAN is a fact about the REPOSITORY, so it
    # is reported as its own line and compared against the baseline taken at
    # the top. A CHANGE between the two is the real finding, because that would
    # mean the probe moved the tree it was measuring.
    _after = run_tool()
    if _after != _baseline:
        failures.append('the tool exits %d after restore but exited %d before '
                        '-- the probe changed the tree it was measuring'
                        % (_after, _baseline))
        print('  FAIL the exit code MOVED across the probe: %d before, %d '
              'after. Byte-identical source with a different verdict means '
              'something else moved.' % (_baseline, _after))
    else:
        print('  ok   and the exit code is unchanged across the probe (%d '
              'before, %d after), so whatever the tree state, this probe did '
              'not alter it' % (_baseline, _after))

    if failures:
        print('\n%d MUTATION(S) SURVIVED:' % len(failures))
        for t in failures:
            print('  - ' + t[:110])
        return 1
    print('\nALL %d MUTATIONS REFUSED%s.'
          % (len(MUTATIONS),
             ' UNDER THE NARROWED exit==2 CRITERION, because the real tree is '
             'not clean -- a SMALLER claim than a clean-tree run makes'
             if _strict else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
