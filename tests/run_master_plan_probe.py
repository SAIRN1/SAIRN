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

# ── RE-ANCHORED 2026-09-17 ONTO THE SOURCE, AFTER GOING RED UNREAD ──────────
# This used to `re.search(r'\*\*(\d+) of (\d+) test files are traced')` against
# the MATRIX's prose. That sentence no longer exists -- the matrix was
# restructured to lead with the absolute count rather than the ratio -- so the
# arm had been failing on `main` ever since, and **the two arms underneath it
# were nested in `if m:` and therefore silently NOT RUNNING.** A visible red is
# bad; a visible red that switches off the two checks it guards is the shape
# PR 1.3 is written about, and this repo re-read the same lesson three commits
# ago in ccf38216.
#
# THE REPAIR IS NOT A NEW REGEX. Scraping one generated document to check
# another is a string anchor by construction, and it will drift again the next
# time somebody rewords a headline. The figures are taken from the SAME
# FUNCTIONS the plan itself calls, so a wording change cannot break it and a
# figure change cannot hide behind one.
_all_tests = TM.all_tests()
_cited = TM.traced()
_n, _d = len([t for t in _all_tests if t in _cited]), len(_all_tests)
check(_d > 0, 'there are test files to count at all -- a zero denominator '
              'would make both arms below vacuous')
if doc:
    # The SAME figure, not a similar one and not one counted a second way.
    check(('**%d** of them are traced' % _n) in doc,
          "the plan prints traceability_matrix.traced()'s own numerator (%d)"
          % _n)
    check(('**%d** test files on disk' % _d) in doc,
          "...and all_tests()'s own denominator (%d)" % _d)
    # TEETH: if the numbers were interchangeable the two arms above would pass
    # against a plan that had swapped them, which is precisely the confusion
    # -- a rate over the subset you looked at -- this paragraph exists to name.
    check(_n != _d,
          'numerator and denominator differ, so the two arms above are not '
          'the same assertion written twice')

# The mechanical version of the same claim: one function, two callers.
check(MP.TM.traced is TM.traced,
      'the plan literally calls traceability_matrix.traced() -- not a copy')

# ── 2. A FAULT PROBE IS A DECLARATION, NOT A MENTION ─────────────────────────
print('')
print('2. the fault column counts DECLARATIONS, and nothing else')
by_app, declarers, too_broad, unattributed, named_unresolved = MP.fault_probes()

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

# ── THE JAVASCRIPT HALF OF THE DECLARATION, ADDED 2026-09-15 ────────────────
# The rule was Python-only, which was an accident of which probe got written
# first rather than a decision -- and this document called SAIRNcode "no fault
# probe" while a 563-line, sabotage-verifying mutation control sat in tests/.
# Both directions, because a widening that silently credits everything is worse
# than the undercount it replaced.
check('tests/sairncode_gates_mutation_control.js' in declarers,
      'a *_mutation_control.js is a declaration in the other language')
check('sairncode' in by_app,
      '...and SAIRNcode is credited for it, which it was not before')
check('tests/faults/sv_backup_write_faults.js' in declarers,
      'a tests/faults/*.js is counted too')

# THE CAP, AND IT IS THE REASON THE WIDENING IS SAFE.
# tests/faults/transport_timeout_sweep.js names FIFTEEN app files. Crediting
# all fifteen from one file would flip nearly every remaining gap label at once
# on much weaker per-app evidence.
check('tests/faults/transport_timeout_sweep.js' not in declarers,
      'a file naming more apps than the cap is NOT credited')
check(any(r == 'tests/faults/transport_timeout_sweep.js' for r, _n in too_broad),
      '...and it is REMEMBERED BY NAME, not dropped silently -- excluded is '
      'not the same as absent')
check(all(n > MP.MAX_APPS_PER_JS_PROBE for _r, n in too_broad),
      'nothing is in the too-broad list that was under the cap')

# A JS FILE THAT DECLARES NOTHING IS STILL NOT A PROBE -- the widening must not
# have turned "any .js under tests/" into coverage.
check('tests/faults/faultkit.js' not in declarers,
      'a tests/faults helper that names no app file is not a probe')
check('tests/sairncode_gates.js' not in declarers,
      'the SUITE is not a probe -- only the control that mutates is')

# ── ATTRIBUTION IS `<app>.html`, AND NOT EVERY APP HAS ONE ──────────────────
# Added 2026-09-17. Two DIFFERENT invisibilities, and they are not the same
# defect: a probe can be counted in the TOTAL and credited to no app, or it can
# resolve to nothing and be absent from both. The second is the one the
# open-work row got wrong -- it said the total "does move, so nothing is lost"
# -- and tests/sairncash_fault_probe.py is the counterexample.
check(all(p in declarers for p, _t in unattributed),
      'an unattributed probe IS in the declared total -- that list is about '
      'the per-app column only')
check(all(not any((a + '.html') in t for a in MP.TM.apps())
          for _p, t in unattributed),
      'nothing is called unattributed that resolves to an app .html')
check(len(unattributed) > 0,
      'the unattributed list is non-empty -- if it ever goes to zero this arm '
      'and the disclosure it holds are asserting a property of nothing')

check('tests/sairncash_fault_probe.py' in named_unresolved,
      'a file the AUTHOR named *_fault_probe.py, resolving to nothing, is '
      'remembered by name rather than dropped in silence')
check('tests/sairncash_fault_probe.py' not in declarers,
      '...and it is genuinely NOT counted -- the total does not move for it, '
      'which is the half the open-work row had backwards')
check(all(p not in declarers for p in named_unresolved),
      'nothing is in both the declared total and the resolved-to-nothing list')
# THE DOUBLE-REPORT THAT WAS THERE FOR A MINUTE. transport_timeout_sweep.js
# resolves fifteen targets and is dropped by the CAP, so it reaches the same
# `not targets` branch -- and saying "no target could be resolved" about it
# would be a second, WRONG explanation for a fact the cap bullet already
# explains correctly.
check('tests/faults/transport_timeout_sweep.js' not in named_unresolved,
      'a file excluded by the CAP is not ALSO reported as resolving to '
      'nothing -- one fact, one explanation')

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
                         '--check'], cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
                        timeout=900)
    check(rc.returncode == 0, 'it passes on the committed document (got %d)'
          % rc.returncode)
    # ── THE SABOTAGE IS ASSERTED TO HAVE APPLIED (2026-09-16) ──────────────
    # `tools/sabotage_control_check.py` reported this probe UNGUARDED: it
    # replaced an anchor and never checked the anchor was there. The failure
    # mode is not silent here -- a rotted anchor makes the next arm report "a
    # hand-edited row makes it FAIL (got 0)" -- but that is a CONFUSING red
    # about the wrong thing, and a reader chasing it looks at master_plan.py
    # rather than at this line. UNIQUENESS rather than mere presence, because
    # an anchor matching twice would mutate whichever came first and this arm
    # would be asserting about a row nobody chose.
    ANCHOR = '| `sairnbiz` |'
    hits = original.count(ANCHOR)
    check(hits == 1, 'the sabotage anchor %r appears exactly once in the '
                     'document (found %d) -- at 0 nothing is planted and the '
                     'arm below would be measuring an unmutated file; above 1 '
                     'it plants in whichever came first'
                     % (ANCHOR, hits))
    io.open(path, 'w', encoding='utf-8', newline='').write(
        original.replace(ANCHOR, '| `sairnbiz` MUTATED |', 1))
    check(io.open(path, encoding='utf-8', newline='').read() != original,
          '...and the file on disk really differs from what it was')
    rc = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                      'master_plan.py'),
                         '--check'], cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
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
        # FIVE-tuple since 2026-09-17: (by_app, declarers, too_broad,
        # unattributed, named_unresolved). The shape is restated literally
        # rather than star-unpacked, because a fake that silently absorbs a new
        # return value is how this arm would go on passing against a generator
        # whose signature had moved out from under it.
        'G.fault_probes = lambda: ({}, [], [], [], [])\n'
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

# ── 7. THE STACK-UP: A BOUND, NOT A SCORE ───────────────────────────────────
# The itemized table names every contributor and still never says what the
# CHAIN can be off by. These arms hold the two properties that make the bound
# honest rather than decorative.
print('')
print('7. the worst-case bound, and RSS beside it')
if doc:
    check('WORST CASE:' in doc, 'the document publishes a worst-case bound')
    check('RSS for context:' in doc, '...and an RSS figure beside it for context')
    import re as _re
    m = _re.search(r'\*\*WORST CASE: (\d+)\.\*\* RSS for context: (\d+)\.', doc)
    check(m is not None, 'both numbers are readable from the document')
    if m:
        worst, rss = int(m.group(1)), int(m.group(2))
        # THE INEQUALITY IS THE WHOLE POINT. RSS below the sum is what says the
        # two are different combinations rather than the same number printed
        # twice -- and if they ever coincide, one contributor dominates so
        # completely that the others round away, which is worth seeing.
        check(rss <= worst, 'RSS (%d) never exceeds the worst case (%d)' % (rss, worst))
        check(worst > 0, 'a bound of zero would mean every classifier is exact, which none is')
    # A BUDGET THAT FLATTERED THE PLATFORM WOULD BE WORTH LITTLE. Every
    # contributor errs the same way, and the document must say so -- a reader
    # who thinks the error is two-sided will read the table as a confidence
    # interval, which it is not.
    check('UNDER-count' in doc or 'UNDER-counts' in doc,
          'the direction of every contributor is stated')
    check('cannot overstate' in doc,
          '...and that the document can only understate, never flatter')
    # RSS PRESENTED AS THE ANSWER WOULD BE THE COLLAPSE THIS DOCUMENT REFUSES
    # EVERYWHERE ELSE. It is context; the worst case is the number to act on.
    check('is NOT the answer' in doc and 'act on the worst case' in doc,
          'RSS is labelled as context, not as the verdict')
    # A ZERO CONTRIBUTOR IS A FINDING, NOT AN OMISSION.
    check('no contribution' in doc,
          'a contributor of zero is listed rather than dropped')
    check('contributes ZERO and is listed anyway' in doc,
          '...and the reason it is listed is written down')

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
