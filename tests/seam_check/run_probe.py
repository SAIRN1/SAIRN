"""Prove the seam checker catches the REAL defect it was built for.

A checker that has only ever returned clean is unproven. This replants the
exact 2026-08-27 SAIRNlaw defect -- `service_methods` present in the engine,
absent from the endpoint payload -- and asserts the tool names it.

Restores with a targeted `git checkout --`, never a reset, and asserts the
restore actually happened.
"""
import subprocess, re, sys, os

import subprocess as _sp
REPO = _sp.run(['git','rev-parse','--show-toplevel'],capture_output=True,text=True).stdout.strip()
EP = 'api/legal-deadlines.js'


def run(*a, **k):
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True, **k)


def tool():
    r = run(sys.executable, 'tools/sairn_seam_check.py')
    return r.returncode, r.stdout


assert run('git', 'status', '--porcelain', '--', EP).stdout.strip() == '', \
    'endpoint must be unmodified before the probe'

before_rc, before_out = tool()
print('BASELINE exit', before_rc)
print('  legal-deadlines seam line:',
      [l.strip() for l in before_out.splitlines() if 'legal-deadlines' in l][:1])

# ---- plant the historical defect: drop service_methods from the payload ----
path = os.path.join(REPO, EP)
src = open(path, encoding='utf-8').read()
assert 'service_methods' in src, 'fixture invalid: endpoint does not forward service_methods today'
patched = re.sub(r'\n\s*service_methods\s*:[^\n]*\n', '\n', src, count=1)
assert patched != src, 'fixture invalid: nothing was removed'
open(path, 'w', encoding='utf-8').write(patched)

after_rc, after_out = tool()
line = [l for l in after_out.splitlines() if 'NOT FORWARDED' in l or 'service_methods' in l]
print('WITH DEFECT exit', after_rc)
for l in line:
    print('   ', l.strip())

caught = (after_rc == 1 and any('service_methods' in l for l in line))

# ---- restore, and prove the restore happened ----
run('git', 'checkout', '--', EP)
restored = (run('git', 'status', '--porcelain', '--', EP).stdout.strip() == '')
post_rc, _ = tool()

print()
print('CAUGHT the planted Florida defect      :', caught)
print('endpoint restored from git             :', restored)
print('exit code back to baseline after restore:', post_rc == before_rc, '(%s)' % post_rc)
import sys as _s
_s.exit(0 if (caught and restored and post_rc==before_rc) else 1)
