"""tests/run_discarded_verdict_crossfile_probe.py -- the survey's zero means
something only while this control still fires.

    python tests/run_discarded_verdict_crossfile_probe.py

`tools/discarded_verdict_crossfile.py` reports ZERO cross-module discarded
verdicts in `api/`. That is the finding, and it is the reason the cross-module
pass described in the open-work row was NOT built. A zero from a scanner
nobody has watched fire is indistinguishable from a scanner that does not
work -- which is the failure this repo has recorded more than once tonight
alone -- so the control ships with the tool rather than being a thing that was
done once and forgotten.

It copies `api/` to a temp directory, plants one of each shape into a real
file, and requires BOTH to be found and attributed to the right module. The
repo is never written to.
"""
import io
import os
import shutil
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import discarded_verdict_crossfile as dvc      # noqa: E402

fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        return
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r' % (label, expected, actual))


# canAssign() is exported by api/_lib/subcontractor-compliance.js and returns
# {allowed, ok}. Planted into a file that does not define it, which is what
# makes the hit cross-module.
PLANT = (
    '\nasync function __plantedBare(a, b) {\n'
    '  await canAssign(a, b);\n'
    '  return 1;\n'
    '}\n'
    'async function __plantedUnread(a, b) {\n'
    '  const verdict = canAssign(a, b);\n'
    '  return 2;\n'
    '}\n'
)

tmp = tempfile.mkdtemp(prefix='dvc-probe-')
shutil.copytree(os.path.join(ROOT, 'api'), os.path.join(tmp, 'api'))

names, clean = dvc.survey(tmp)
check('the untouched copy is clean, like the repo itself', len(clean), 0)
check('canAssign is recognised as verdict-shaped', 'canAssign' in names, True)
check('and attributed to the module that exports it',
      names.get('canAssign'), ['api/_lib/subcontractor-compliance.js'])

target = os.path.join(tmp, 'api', 'sc-ai.js')
with io.open(target, encoding='utf-8') as fh:
    original = fh.read()
with io.open(target, 'w', encoding='utf-8') as fh:
    fh.write(original + PLANT)

_, hits = dvc.survey(tmp)
kinds = sorted(h[0] for h in hits)
check('both planted shapes are found', kinds, ['BARE', 'UNREAD'])
check('and each names the file it was planted in',
      sorted(set(h[1] for h in hits)), ['api/sc-ai.js'])
check('and the module that actually exports the verdict',
      sorted(set(h[4] for h in hits)), ['api/_lib/subcontractor-compliance.js'])

# A verdict that IS read must not be reported -- otherwise the survey would
# flag every correct call site and its zero would be meaningless.
with io.open(target, 'w', encoding='utf-8') as fh:
    fh.write(original + '\nasync function __plantedRead(a, b) {\n'
                        '  const verdict = canAssign(a, b);\n'
                        '  if (!verdict.allowed) return null;\n'
                        '  return verdict;\n'
                        '}\n')
_, read_hits = dvc.survey(tmp)
check('a verdict that is actually consulted is NOT reported', len(read_hits), 0)

shutil.rmtree(tmp, ignore_errors=True)

print(('FAILED  ' if fails else 'ok  ') +
      'discarded-verdict-crossfile: 7 checks, %d failed' % fails)
sys.exit(1 if fails else 0)
