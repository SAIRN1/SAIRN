"""The control for tools/entity_baseline_readiness.py (item 51).

Run: python tests/run_baseline_readiness_probe.py

WHY THIS EXISTS WHEN THE TOOL ALREADY HAS --self-check: that self-check builds
its own fixtures and grades itself against them, so a bug shared between the
fixture generator and `assess()` passes both halves. This probe re-derives the
counts from the REAL register with a plain Counter -- a different method on
different data -- and checks the tool's published numbers against them. It also
pins the two accounting identities that no fixture can prove: that every record
is either counted as a unit or reported as excluded, and that the exit code
follows the verdict.
"""
import collections
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import entity_baseline_readiness as R                            # noqa: E402

CONTROLS_FOR = ['entity_baseline_readiness.py']

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


recs = json.load(io.open(os.path.join(REPO, 'docs',
                                      'defect-density-register.json'),
                         encoding='utf-8'))['records']
rows = {r['dimension']: r for r in R.assess_all(recs)}

print('baseline readiness control -- %d records\n' % len(recs))

# ── 1. THE NUMBERS, RE-DERIVED A DIFFERENT WAY ─────────────────────────────
for field in ('app', 'layer', 'detection_method'):
    mine = collections.Counter(r.get(field) for r in recs if r.get(field))
    for bucket in R.NOT_AN_ENTITY:
        mine.pop(bucket, None)
    row = rows[field]
    check('%s: the unit count matches an independent Counter' % field,
          row['units'] == len(mine), '%s vs %s' % (row['units'], len(mine)))
    check('%s: the record count matches' % field,
          row['records'] == sum(mine.values()),
          '%s vs %s' % (row['records'], sum(mine.values())))
    check('%s: the largest unit matches' % field,
          row['largest'] == (max(mine.values()) if mine else 0),
          '%s vs %s' % (row['largest'], max(mine.values()) if mine else 0))

# ── 2. NOTHING IS LOST: counted + excluded == every record with that field ──
# A silent drop would shrink the very count the bar is applied to, and every
# arm above would still pass because they would shrink together.
for field in ('app', 'layer', 'detection_method'):
    have = sum(1 for r in recs if r.get(field))
    row = rows[field]
    check('%s: counted + excluded accounts for every record that has the field'
          % field, row['records'] + row['excluded_records'] == have,
          '%d + %d != %d' % (row['records'], row['excluded_records'], have))

# ── 3. THE REAL VERDICT TODAY, AND WHICH BAR IT FAILED ─────────────────────
# Both halves are asserted, because "NOT READY" alone would pass on a tool that
# answered NOT READY unconditionally -- and the two failures have different
# remedies: one is fixed by waiting and the other never is.
check('app is NOT READY on VOLUME -- a shortage of records, which time fixes',
      rows['app']['verdict'] == 'NOT READY -- VOLUME', rows['app']['verdict'])
check('layer clears the record bar and is STILL not ready -- no denominator, '
      'which time does not fix',
      rows['layer']['volume_ok'] is True
      and rows['layer']['has_exposure'] is False
      and rows['layer']['verdict'] == 'NOT READY -- NO DENOMINATOR',
      rows['layer'])
check('PLATFORM is excluded from app and is the majority of the register',
      rows['app']['excluded_records'] > rows['app']['records'],
      '%d excluded vs %d counted' % (rows['app']['excluded_records'],
                                     rows['app']['records']))

# ── 4. THE EXIT CODE FOLLOWS THE VERDICT ───────────────────────────────────
p = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'entity_baseline_readiness.py'),
                    '--json'],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
doc = json.loads(p.stdout)
check('with nothing ready the exit code is 1, not 0',
      p.returncode == 1 and doc['any_ready'] is False,
      '%s any_ready=%s' % (p.returncode, doc.get('any_ready')))
check('...and the bar it applied is published in the output, not just printed',
      doc['min_records_per_unit'] == R.MIN_RECORDS_PER_UNIT
      and doc['min_ready_units'] == R.MIN_READY_UNITS, doc.get('min_records_per_unit'))

# THE TEXT PATH HAS ITS OWN RETURN and is the one a person actually runs. It
# was untested until a mutant that zeroed only this branch passed every arm
# above -- the --json arm returns earlier and never reaches it.
t = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'entity_baseline_readiness.py')],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('the TEXT run also exits 1 when nothing is ready',
      t.returncode == 1, '%s' % t.returncode)
check('...and says NO ENTITY IS READY rather than printing a table and stopping',
      'NO ENTITY IS READY' in t.stdout, t.stdout[-200:])
check('...and names the bar it applied in the text, not only in the JSON',
      str(R.MIN_RECORDS_PER_UNIT) in t.stdout and 'JUDGEMENT' in t.stdout,
      t.stdout[:300])

# ── 5. THE CHECK CAN SAY YES. Without this arm every arm above passes on a
#      tool that answers NOT READY for every input there will ever be. ──────
fat = [{'app': 'a%d' % (i % 3), 'layer': 'product',
        'detection_method': 'code-review'} for i in range(90)]
check('a register where three apps each clear the bar IS ready',
      R.assess(fat, 'app')['verdict'] == 'READY', R.assess(fat, 'app'))

# ── 6. THE CLAIMS THE FIRST ARTICLE INSPECTION FOUND UNVERIFIED ────────────
# Added 2026-09-15 by the FAI on this tool (docs/2026-09-15-first-article-
# entity-baseline-readiness.md). Each arm below exists because the tool's own
# header states something and nothing checked it. An adversarial read had
# already passed over this file; FAI asks the different question -- is every
# STATED requirement verified -- and these five are what it returned.
import io as _io                                                 # noqa: E402
import json as _json                                             # noqa: E402
import tempfile                                                  # noqa: E402

# CLAIM: "Exit 0 when at least one entity is ready". Every exit-code arm above
# tests the NOT-ready side, so the tool could have returned 1 unconditionally.
_tmpdir = tempfile.mkdtemp(prefix='fai_baseline_')
_ready_reg = os.path.join(_tmpdir, 'ready-register.json')
_io.open(_ready_reg, 'w', encoding='utf-8').write(_json.dumps({'records': fat}))
_real_reg = R.REGISTER
try:
    R.REGISTER = _ready_reg
    check('CLAIM "exit 0 when at least one entity is ready": it really does',
          R.main([]) == 0, 'expected exit 0 on a register where app is READY')
    check('...and on the --json path too, which returns separately',
          R.main(['--json']) == 0, 'expected exit 0')
finally:
    R.REGISTER = _real_reg

# CLAIM: "2 when the question could not be answered". Nothing exercised it, so
# an unreadable register could have been reported as "nothing is ready" -- a
# could-not-run folded into a finding, which is the PR 1.11 shape exactly.
try:
    R.REGISTER = os.path.join(_tmpdir, 'no-such-register.json')
    check('CLAIM "exit 2 when the question could not be answered": an '
          'unreadable register is COULD-NOT-RUN, not "nothing is ready"',
          R.main([]) == 2, 'expected exit 2')
finally:
    R.REGISTER = _real_reg

# CLAIM: "excluded by name and the exclusion is PRINTED, because a silent
# exclusion is a different tool from a declared one". The exclusion COUNT was
# asserted; that it reaches the page was not.
check('CLAIM "the exclusion is PRINTED": the excluded count appears in the '
      'text output, not only in the JSON',
      'excluded as a catch-all bucket' in t.stdout
      and str(rows['app']['excluded_records']) in t.stdout,
      t.stdout[:400])

# CLAIM: "one unit is not a comparison, and a baseline is one". MIN_READY_UNITS
# was asserted to be >= 2 as a CONSTANT. A constant is not a behaviour: the
# comparison could have been written `>= 1` and the arm would not have noticed.
_one = [{'app': 'solo', 'layer': 'product', 'detection_method': 'code-review'}
        for _ in range(90)]
check('CLAIM "one unit is not a comparison": a register where exactly ONE app '
      'clears the bar is NOT ready',
      R.assess(_one, 'app')['verdict'] != 'READY', R.assess(_one, 'app'))
check('...and it is the VOLUME verdict, so the reason given is the true one',
      R.assess(_one, 'app')['verdict'] == 'NOT READY -- VOLUME',
      R.assess(_one, 'app')['verdict'])

# CLAIM: "REPORT ONLY -- nothing gates on this". Stated in the header and
# nowhere enforced. It is mechanically checkable, so it is checked.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import report_only_checks as _ROC                                # noqa: E402
_reg_names = [x['tool'] if isinstance(x, dict) else x[0] for x in _ROC.REGISTRY]
check('CLAIM "report only, nothing gates on this": it is NOT in the report-only '
      'RUNNER registry', 'entity_baseline_readiness.py' not in _reg_names,
      _reg_names[:5])
check('...and it IS recorded as a deliberate NOT-PROMOTED decision rather than '
      'simply forgotten',
      'entity_baseline_readiness.py' in [x[0] for x in _ROC.NOT_PROMOTED])
_gate = _io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
                 encoding='utf-8', errors='replace').read()
check('...and the push gate does not invoke it',
      'entity_baseline_readiness' not in _gate)

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
