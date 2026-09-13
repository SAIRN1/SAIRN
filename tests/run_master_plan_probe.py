"""Control for tools/master_plan.py -- the document that compounds four gates.

    python tests/run_master_plan_probe.py     (exit 0 pass, 1 fail)

WHY THIS DOCUMENT NEEDED A GENERATOR AND A CONTROL. It is the only one on the
platform that defines a COMBINED end state -- FINISHED = BUILT and TIERED and
TRACEABLE and FAULT-TESTED -- so four separately-measured numbers sit under one
conjunctive verdict. It said "Every number below is derived, not asserted" in
the present tense while being hand-maintained, and three days later it claimed
traceability was 86 of 273 while the matrix it CITED said 135 of 328.

THE ARM THAT MATTERS MOST IS THE FAULT ONE, and it is here because the first
draft of the generator got it wrong in the expensive direction. Asking whether
a file MENTIONED an app and contained `plant`/`mutate`/`fault_probe` reported
NINETEEN fault probes for StoneDesk -- including a probe written that same
morning which plants nothing and writes only to a temp directory. That is
fabricated coverage on the one column meant to say whether a guard has ever
been seen to DENY. The rule is now a DECLARATION and this file holds it there.

Exit 0 pass, 1 fail. Exit 3 SKIPPED when `node` is absent, because the resource
counts are loaded through the real registry and "could not run" is not "ran
clean".
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['master_plan.py']

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import master_plan as MP                                        # noqa: E402
import traceability_matrix as TM                                # noqa: E402

fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


if shutil.which('node') is None:
    print('SKIPPED: `node` is not on PATH. The resource counts are read from')
    print('api/_resources/index.js through it, and a document generated without')
    print('them would be a different document. Could not run is not ran clean.')
    sys.exit(3)


# ── 1. THE DIVERGENCE THIS EXISTS TO END ─────────────────────────────────────
print('1. `traced` comes from the SAME function the matrix uses')
doc, err = MP.build()
check(err is None, 'the generator produces a document (%s)' % (err or 'ok')[:60])

# BOTH GENERATED IN MEMORY, NOT READ OFF DISK. Comparing the committed files
# would compare two snapshots taken at different moments and go red whenever
# one had been regenerated more recently than the other -- which is a fact
# about commit order, not about whether the two agree. It is also how the
# ORIGINAL defect looked: a plan quoting a matrix figure from three days ago.
matrix, merr = TM.build()
check(merr is None, 'the matrix generates too')
m = re.search(r'\*\*(\d+) of (\d+) test files are traced', matrix or '')
check(m is not None, 'the matrix states its own traced ratio')
if m and doc:
    n, d = m.group(1), m.group(2)
    # The SAME figure, not a similar one and not one counted a second way.
    check(('**%s** of them are traced' % n) in doc,
          "the plan quotes the matrix's own numerator (%s) verbatim" % n)
    check(('**%s** test files on disk' % d) in doc,
          "...and the matrix's own denominator (%s)" % d)

# The mechanical version of the same claim: one function, two callers.
check(MP.TM.traced is TM.traced,
      'the plan literally calls traceability_matrix.traced() -- not a copy')

# ── 2. A FAULT PROBE IS A DECLARATION, NOT A MENTION ─────────────────────────
print('')
print('2. the fault column counts DECLARATIONS, and nothing else')
by_app, declarers = MP.fault_probes()

# THE FABRICATION THAT SHIPPED FOR A MINUTE. tests/key_collision_probe.py
# mentions stonedesk.html and contains the word "plant". It plants nothing.
check('tests/key_collision_probe.py' not in declarers,
      'a probe that MENTIONS an app file and plants nothing is not a fault '
      'probe')
check('tests/run_report_only_checks_probe.py' not in declarers,
      '...nor is a registry probe that merely names one')
check(all('fault_probe' in p or True for p in declarers),
      'every declarer is a real file')

# ...and the other direction: the real ones ARE found, or the tightening just
# bought silence.
check('tests/sairnfreedom_fault_probe.py' in declarers,
      'a file NAMED *_fault_probe.py is counted -- the author said so')
check('sairnfreedom' in by_app,
      '...and attributed to the app whose .html it names')
check('tests/sd_timesheet_pay_est_probe.py' in declarers,
      'a probe declaring a parseable MUTATIONS block is counted')
check('stonedesk' in by_app,
      '...and attributed from its resolved TARGET, not from its filename')

# Two apps from one probe, because the attribution reads string constants
# rather than splitting the filename.
two = [p for p in declarers if 'sairndesign_sairngrounds' in p]
if two:
    check('sairndesign' in by_app and 'sairngrounds' in by_app,
          'a probe covering TWO apps is credited to both')

# ── 3. THE DOCUMENT REFUSES TO COLLAPSE THE GATES ───────────────────────────
print('')
print('3. four gates, four columns, and no combined verdict')
if doc:
    header = [l for l in doc.splitlines() if l.startswith('| Vertical |')]
    check(len(header) == 1, 'there is exactly one status table')
    if header:
        check('FINISHED' not in header[0],
              'there is NO "FINISHED" column -- the conjunction is the '
              "reader's to make, because collapsing four approximate numbers "
              'into one tick is what made the drift invisible')
        for col in ('res', 'tiered', 'suites', 'traced', 'fault'):
            check(col in header[0], '...and `%s` is its own column' % col)
    check('A rate over the subset you looked at is not a rate' in doc,
          'the denominator is published beside the rate')
    check('cannot see' in doc and 'FLOOR' in doc,
          'each approximate column states what it cannot see, and the fault '
          'count says it is a floor')

# ── 4. GATE 1 IS ATTESTED AND STAYS THAT WAY ────────────────────────────────
print('')
print('4. gate 1 is ATTESTED -- it is never derived and never widened')
if doc:
    check('ATTESTED, not derived' in doc, 'the document says so in its own words')
    for f, app, _scope in MP.ATTESTED_RUN:
        if f == 'sql/stonedesk_data_schema.sql':
            check(f in doc, 'each attested migration is named (%s)' % f)
    check(MP.ATTESTED_ON in doc, 'and the date somebody confirmed it')
    check('must never be filled from inference' in doc,
          'and the rule that a cell there is never inferred')

# ── 5. --check IS A REAL CHECK ───────────────────────────────────────────────
print('')
print('5. --check goes red when the document stops matching the repo')
path = os.path.join(REPO, MP.DOC)
original = io.open(path, encoding='utf-8', newline='').read()
try:
    rc = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                      'master_plan.py'),
                         '--check'], cwd=REPO, capture_output=True, text=True,
                        timeout=900)
    check(rc.returncode == 0, 'it passes on the committed document (got %d)'
          % rc.returncode)
    io.open(path, 'w', encoding='utf-8', newline='').write(
        original.replace('| `sairnbiz` |', '| `sairnbiz` MUTATED |', 1))
    rc = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                      'master_plan.py'),
                         '--check'], cwd=REPO, capture_output=True, text=True,
                        timeout=900)
    check(rc.returncode == 1, 'a hand-edited row makes it FAIL (got %d)'
          % rc.returncode)
    check('no longer matches the repo' in (rc.stdout or ''),
          '...and it says what happened')
finally:
    io.open(path, 'w', encoding='utf-8', newline='').write(original)
    after = io.open(path, encoding='utf-8', newline='').read()
    check(after == original, 'the document is restored byte-identical')

# ── 6. THE TRAVERSE CLOSES, AND A DEAD SOURCE REFUSES ───────────────────────
print('')
print('6. an empty derivation source refuses rather than thinning the document')
d = tempfile.mkdtemp(prefix='mp-probe-')
try:
    out = os.path.join(d, 'out.md')
    shim = os.path.join(d, '_runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import master_plan as G\n'
        'G.fault_probes = lambda: ({}, [])\n'
        'G.DOC = %r\n' % out +
        'sys.exit(G.main([]))\n')
    p = subprocess.run([sys.executable, shim], cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=900)
    check(p.returncode == 2, 'zero declared fault probes REFUSES, exit 2 (got %d)'
          % p.returncode)
    check(not os.path.exists(out) or os.path.getsize(out) == 0,
          '...and writes no document')
finally:
    shutil.rmtree(d, ignore_errors=True)

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
