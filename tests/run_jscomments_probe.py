"""Run tools/jscomments.py's own probe, so that something does.

    python tests/run_jscomments_probe.py     (exit 0 pass, 1 fail)

WHY THIS THIN FILE EXISTS. `jscomments.py` is the ONE comment stripper every
SAIRN scanner is supposed to use, written after three separate implementations
were measured destroying 89% of `sairncare.html` and reporting CLEAN. It ships
a real differential probe -- and on 2026-09-13 `tooling_inventory.py` classified
it **UNWIRED**: nothing under `tests/` ran it, and nothing ever had.

It had been reading as SUITE-ONLY for one reason, and the reason is the same
defect found in the meta-checker the same day: a file MENTIONED it in prose.
Once the inventory stopped counting prose as invocation, the real state showed.

So the library that exists to stop scanners going silently blind had a probe
nobody ran. **A tool that exists is not a mechanism; a tool that RUNS is.**

This file adds no assertions of its own on purpose. The cases live beside the
implementation, where the next person editing that state machine will see them;
duplicating them here would create the second copy of something that this repo
keeps recording as the root cause of its own surprises. All this does is make
the suite execute them.
"""
# REQUIREMENT: comment stripping removes comments without touching a string or a regex
#   literal that merely looks like one, because a scanner fed mangled source
#   reports confident nonsense
#
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'jscomments.py')

p = subprocess.run([sys.executable, TOOL, '--probe'], cwd=REPO,
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', timeout=300)
out = (p.stdout or '') + (p.stderr or '')
print(out.rstrip())

rc = p.returncode
fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


print('')
check(rc == 0, 'the differential probe passes (exit %d)' % rc)

# IT RAN, AND THE COUNT IS NOT ZERO. A probe with no cases exits 0 too, and
# "0 case(s) failed" is what an empty run and a clean run both print -- so the
# arm that matters is that both strippers were actually exercised.
check('case(s) failed' in out, 'it really ran and reported a case count')
check('blank_string_bodies' in out,
      'the string-blanking half ran too, not just strip_comments')

if fails:
    print('')
    print('%d FAILING CHECK(S)' % len(fails))
    sys.exit(1)
sys.exit(0)
