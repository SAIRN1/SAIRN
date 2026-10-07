#!/usr/bin/env python
# OWNER: cc
"""Drive tools/py_guard_check.py THROUGH ITS CLI and check the exit codes.

    python tests/run_py_guard_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

── WHY THIS EXISTS WHEN THE TOOL ALREADY HAS 37 ARMS ────────────────────────
Cross-domain disciplines item 6: independence needs a STRUCTURALLY DIFFERENT
METHOD, not a second copy of the same one. The tool's own `--selftest` calls
`scan_source()` in process and compares return values. It therefore cannot see
anything that lives between a function's return value and what the program
actually does with it:

  * a verdict computed correctly and not reaching sys.exit -- which this repo
    has shipped (`_rc` assigned and never used in gen_ma_seed.py, fixed
    2026-10-07, and it printed DRIFTED while exiting 0);
  * argv parsed by one path and acted on by another;
  * a refusal that prints and then returns 0 anyway.

This probe runs the real command in a subprocess, reads the REAL exit code from
`returncode`, and never looks at a pipeline's status. Every subject it scans is
a file it wrote itself under a tempdir -- it never points the tool at the repo,
so a defect in the tool cannot make this probe report on 306 real files.

── WHAT THIS PROBE CANNOT SEE, stated rather than discovered later ──────────
  * whether the four rules are the RIGHT four. That is the design note's
    question, not this one's.
  * whether a flag on a real file is a true positive. Every arm here runs on a
    hand-built subject whose right answer is known, which is the point
    (discipline 1) and also the limit.
  * the full-population run. 306 files take seconds but their verdict depends on
    the tree, and an arm whose expected value changes when somebody else commits
    is an arm that will be deleted the first time it goes red.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, 'tools', 'py_guard_check.py')

if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- %s is absent. This probe is about that file and '
          'reports nothing without it.' % TOOL)
    sys.exit(2)

NL = chr(10)

BAD = {
    'R1': 'import subprocess' + NL + 'subprocess.run(["x"])' + NL,
    'R2': 'try:' + NL + '    f()' + NL + 'except ValueError:' + NL + '    pass' + NL,
    'R3': 'def t():' + NL + '    assert (1 == 2, "never fails")' + NL,
    'R4': 'import sys' + NL + 'sys.exit("something went wrong")' + NL,
}
CLEAN = {
    'R1': ('import subprocess' + NL + 'r = subprocess.run(["x"])' + NL
           + 'if r.returncode:' + NL + '    raise SystemExit(r.returncode)' + NL),
    'R2': ('try:' + NL + '    f()' + NL + 'except ValueError as e:' + NL
           + '    print(e)' + NL + '    raise SystemExit(2)' + NL),
    'R3': 'def t():' + NL + '    assert 1 == 2, "can fail"' + NL,
    'R4': 'import sys' + NL + 'sys.exit(2)' + NL,
}


def run(args, cwd=None):
    """-> (returncode, stdout). The code comes from returncode, NEVER from a
    pipeline and never from a status string."""
    p = subprocess.run([sys.executable, TOOL] + args, cwd=cwd or ROOT,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def write(d, name, src):
    path = os.path.join(d, name)
    io.open(path, 'w', encoding='utf-8', newline=NL).write(src)
    return path


arms = []
TMP = tempfile.mkdtemp(prefix='py-guard-probe-')
try:
    # ── one directory per rule, one subject file in it ───────────────────────
    for rid in sorted(BAD):
        bd = os.path.join(TMP, 'bad-' + rid)
        cd = os.path.join(TMP, 'clean-' + rid)
        os.makedirs(bd)
        os.makedirs(cd)
        write(bd, 'subject.py', BAD[rid])
        write(cd, 'subject.py', CLEAN[rid])

        rc, out = run([bd])
        arms.append(('%s planted-bad: CLI exits 1 and names the rule' % rid,
                     (rc, rid in out), (1, True)))

        rc, out = run([cd])
        arms.append(('%s clean: CLI exits 0 and says CLEAN' % rid,
                     (rc, 'CLEAN' in out), (0, True)))

        # ── THE ABLATION, through the CLI, per rule and per arm ─────────────
        rc, out = run(['--disable', rid, bd])
        arms.append(('ABLATION %s disabled: the same bad subject exits 0' % rid,
                     (rc, 'ABLATED' in out), (0, True)))

    # ── all four bad subjects at once: exit 1, every rule named ─────────────
    allbad = os.path.join(TMP, 'all-bad')
    os.makedirs(allbad)
    for rid in sorted(BAD):
        write(allbad, 'subject_%s.py' % rid, BAD[rid])
    rc, out = run([allbad])
    arms.append(('all four shapes together: exit 1, all four rules named',
                 (rc, sorted(r for r in BAD if r in out)),
                 (1, sorted(BAD))))

    # ── a file that will not parse: COULD NOT PARSE, and NOT a finding ─────
    bp = os.path.join(TMP, 'broken')
    os.makedirs(bp)
    write(bp, 'subject.py', 'def broken(:' + NL)
    rc, out = run([bp])
    arms.append(('an unparseable file is COULD NOT PARSE, not a finding, and '
                 'not clean-with-silence',
                 (rc, 'COULD NOT PARSE' in out, 'finding(s)' in out),
                 (0, True, False)))

    # ── an EMPTY scope is COULD NOT RUN, not clean ─────────────────────────
    empty = os.path.join(TMP, 'empty')
    os.makedirs(empty)
    rc, out = run([empty])
    arms.append(('an empty population is COULD NOT RUN (2), never a clean 0',
                 (rc, 'COULD NOT RUN' in out), (2, True)))

    # ── the argv guard, through the CLI ────────────────────────────────────
    rc, out = run(['--bogus'])
    arms.append(('an unrecognised flag exits 2 and reads nothing',
                 (rc, 'not recognised' in out), (2, True)))
    rc, out = run(['--disable', 'R9'])
    arms.append(('--disable with an unknown rule id exits 2',
                 (rc, 'wants a rule id' in out), (2, True)))
    rc, out = run(['--help'])
    arms.append(('--help exits 0', rc, 0))
    # THIS ARM CAUGHT A REAL DEFECT IN THE TOOL ON ITS FIRST RUN. --help printed
    # the module docstring, the docstring carried box-drawing characters, and on
    # a cp1252 console print() raised UnicodeEncodeError so --help exited 1. The
    # arm above is what found it; this one pins the cause so a future docstring
    # cannot reintroduce it.
    arms.append(('--help output is ASCII-encodable, so a cp1252 console cannot '
                 'crash it',
                 sorted({c for c in out if ord(c) > 127}), []))

    # ── THE VERDICT REACHES THE EXIT CODE, which is this probe's whole point ─
    # A tool can print the right thing and exit the wrong code; that has
    # happened in this repo. So assert the PAIR, not either half.
    rc, out = run([os.path.join(TMP, 'bad-R2')])
    arms.append(('printing a finding and exiting 1 are the SAME run',
                 (rc == 1, 'finding(s)' in out), (True, True)))
    rc, out = run([os.path.join(TMP, 'clean-R2')])
    arms.append(('printing CLEAN and exiting 0 are the SAME run',
                 (rc == 0, 'CLEAN' in out), (True, True)))

    # ── it writes nothing: the subject dir is unchanged after a scan ────────
    before = sorted(os.listdir(os.path.join(TMP, 'bad-R1')))
    run([os.path.join(TMP, 'bad-R1')])
    after = sorted(os.listdir(os.path.join(TMP, 'bad-R1')))
    arms.append(('a scan writes nothing into the directory it reads',
                 after, before))

    # ── the criteria lock runs on the DEFAULT PATH and is printed ───────────
    # checker_selftest_check.py's three properties: a known-positive fixture
    # set, run on the default path, with its outcome PRINTED beside the result.
    rc, out = run([os.path.join(TMP, 'clean-R1')])
    arms.append(('the criteria lock runs and REPORTS on an ordinary scan',
                 'criteria lock:' in out, True))

finally:
    shutil.rmtree(TMP, ignore_errors=True)

passed = 0
for name, got, want in arms:
    ok = got == want
    passed += ok
    print('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
    if not ok:
        print('       wanted %r' % (want,))
        print('       got    %r' % (got,))
print('py_guard CLI probe: %d/%d arm(s) pass' % (passed, len(arms)))
sys.exit(0 if passed == len(arms) else 1)
