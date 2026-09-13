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

── AND IT NOW DRIVES THE EXIT CODE, WHICH IT NEVER DID (2026-09-13) ────────
Every arm here called `survey()` directly. That was reasonable when this was a
run-by-hand survey, and it stopped being reasonable when the tool was PROMOTED
into `tools/report_only_checks.py` with `'verdict': by_exit` -- a reader that
looks at the return code and nothing else. `main()` ended in an unconditional
`return 0`, so the registry could never see a finding no matter how many the
tool printed. Proved rather than argued: a planted copy printed both hits and
exited 0.

A control that tests the FUNCTION while the registry reads the PROCESS is a
control aimed at the wrong layer -- the same shape as the 84 green isolation
tests that never touched SAIRNlaw's storage validator. The CLI is driven here
now, in both directions.
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['discarded_verdict_crossfile.py']

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

# ── THE PROCESS, not just the function ──────────────────────────────────────
# report_only_checks.py reads this tool with by_exit, which looks at the return
# code and NOTHING else. Every arm above calls survey() in-process and would
# stay green while the registry saw nothing -- which is exactly what happened
# from promotion on 2026-09-10 until 2026-09-13.
import subprocess                                                # noqa: E402

CLI = os.path.join(ROOT, 'tools', 'discarded_verdict_crossfile.py')


def cli_rc(root):
    p = subprocess.run([sys.executable, CLI, '--root', root], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=600)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


with io.open(target, 'w', encoding='utf-8') as fh:
    fh.write(original + PLANT)
rc, out = cli_rc(tmp)
check('a planted hit makes the PROCESS exit non-zero', rc, 1)
check('...and the counts are still printed for a human',
      'BARE_STATEMENT_CROSS_FILE:1' in out, True)

with io.open(target, 'w', encoding='utf-8') as fh:
    fh.write(original)
rc, out = cli_rc(tmp)
check('and an unplanted copy exits 0', rc, 0)
check('...having really scanned it -- 0 is a count, not a skip',
      'VERDICT_SHAPED_EXPORTS:0' in out, False)

shutil.rmtree(tmp, ignore_errors=True)

print(('FAILED  ' if fails else 'ok  ') +
      'discarded-verdict-crossfile: 11 checks, %d failed' % fails)
sys.exit(1 if fails else 0)
