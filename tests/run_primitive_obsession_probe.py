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

    if run_tool() != 0:
        print('  FAIL 0. baseline: the tool is not clean before anything is '
              'planted, so no mutation below means anything')
        return 1
    print('  ok   0. the tool is CLEAN in the worktree before anything is planted')

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
        if rc == 0:
            failures.append(title)
            print('  FAIL %d. SILENT -- the tool exited 0 with this defect '
                  'planted: %s' % (i, title[:100]))
        else:
            ok += 1
            print('  ok   %d. refused (exit %d): %s' % (i, rc, title[:100]))

    if io.open(TOOL, encoding='utf-8').read() != src:
        print('  FAIL restore -- the tool is not byte-identical after the probe')
        return 1
    print('  ok   the tool is byte-identical again')
    if run_tool() != 0:
        print('  FAIL the tool is not clean after restore')
        return 1
    print('  ok   and CLEAN again with everything restored')

    if failures:
        print('\n%d MUTATION(S) SURVIVED:' % len(failures))
        for t in failures:
            print('  - ' + t[:110])
        return 1
    print('\nALL %d MUTATIONS REFUSED.' % len(MUTATIONS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
