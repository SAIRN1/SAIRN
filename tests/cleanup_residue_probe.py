"""Probe the three things tools/cleanup_residue_check.py learned 2026-09-10.

WHY. That tool exists to doubt the `NOT RUN` label on fifteen-plus hand-written
cleanup SQL files. Its first version answered nothing about 29 of them and
reported three of them as CLEAN anyway -- a false clean inside the checker
written to catch false labels. The three had no parsed delete and no live read;
they were CLEAN only because the count was computed by SUBTRACTION,
`len(report) - residue - unread`, so every file that fell through the
classification landed in the reassuring bucket.

THE THREE FIXES, EACH WITH ITS NEGATIVE CONTROL:

  1. CLEAN IS COUNTED, NEVER SUBTRACTED. A file nothing could be checked in is
     COULD NOT READ. Arm 1 asserts the fixture reports CLEAN : 0 *and* computes
     what the old subtraction would have said on the same input -- if that trap
     value is not 1, the fixture is not reproducing the bug and the arm is
     worthless.

  2. `encode(digest('KEY','sha256'),'hex')` IS THE SAME SCOPING as a pasted
     64-char hash, and reading only the literal form missed it. Arm 2 also runs
     the pre-fix regex over the same fixture as its control: it must find
     nothing, or the fix is being credited for something that already worked.

  3. THE APP COMES FROM THE RESOURCE REGISTRY, NOT THE LICENCE SEED ROW.
     RF-PINNACLE-2026 is a real customer licence provisioned outside this repo,
     so no `values (...)` row for it exists in sql/ and the old lookup returned
     "an unknown app" for nine roofing files. Arm 3 asserts rf_invoices resolves
     to sairnroofing through api/_resources/, and the control asserts the old
     seed-row route genuinely fails for that key -- the fix is only worth having
     because the thing it replaced could not answer.

  4. A COMMENTED-OUT DELETE IS NOT A DELETE, and is reported as such rather than
     as a parse miss -- different files, different thing to do about them.

OFFLINE. No arm touches the network; every one runs on a fixture written to a
temp directory or on a direct function call.

Run: python tests/cleanup_residue_probe.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import cleanup_residue_check as C  # noqa: E402

TOOL = os.path.join(REPO, 'tools', 'cleanup_residue_check.py')
OLD_HASH_RE = re.compile(r"license_hash\s*=\s*'([0-9a-f]{64})'", re.I)

failures = []


def check(arm, ok, detail):
    print('  %-4s %-58s %s' % ('PASS' if ok else 'FAIL', arm, detail))
    if not ok:
        failures.append(arm)


# ---------------------------------------------------------------- fixtures
tmp = tempfile.mkdtemp(prefix='cleanup_residue_probe_')

COMMENTED_ONLY = os.path.join(tmp, 'commented_only_cleanup.sql')
open(COMMENTED_ONLY, 'w', encoding='utf-8').write(
    "-- Proposed, not runnable. Nothing below executes.\n"
    "-- delete from public.dnt_referrals\n"
    "--   where license_hash = encode(digest('DNT-PINNACLE-2026','sha256'),'hex')\n"
    "--     and referral_id = 'RF-VERIFY-PROBE-20260825';\n")

DIGEST_FORM = os.path.join(tmp, 'digest_form_cleanup.sql')
open(DIGEST_FORM, 'w', encoding='utf-8').write(
    "delete from public.rf_invoices\n"
    "  where license_hash = encode(digest('RF-PINNACLE-2026', 'sha256'), 'hex')\n"
    "    and invoice_id = 'probe-invoice-1';\n")

print('CLEANUP RESIDUE PROBE -- offline, no network, nothing written to the repo')

# ------------------------------------------------- arm 1: no clean by subtraction
p = subprocess.run([sys.executable, TOOL, COMMENTED_ONLY],
                   capture_output=True, text=True, cwd=REPO)
out = (p.stdout or '') + (p.stderr or '')
clean_line = re.search(r'CLEAN\s+:\s*(\d+)', out)
unread_line = re.search(r'COULD NOT READ:\s*(\d+)', out)
seen_line = re.search(r'files seen\s+:\s*(\d+)', out)
clean_n = int(clean_line.group(1)) if clean_line else -1
unread_n = int(unread_line.group(1)) if unread_line else -1
seen_n = int(seen_line.group(1)) if seen_line else -1

check('1a  unchecked file is not counted CLEAN', clean_n == 0,
      'CLEAN : %d' % clean_n)
check('1b  it is counted COULD NOT READ instead', unread_n == 1,
      'COULD NOT READ : %d' % unread_n)
check('1c  exit code says NOT a pass', p.returncode == 2,
      'exit %d' % p.returncode)
# The negative control. residue is 0 and unread is what the OLD code would have
# recorded for this file: nothing. So the old subtraction yields 1 CLEAN.
trap = seen_n - 0 - 0
check('1d  CONTROL: the old subtraction really did say CLEAN here', trap == 1,
      'len(report) - residue - unread == %d (the bug)' % trap)

# ------------------------------------------------------- arm 2: digest scoping
rows = C.targets(DIGEST_FORM)
got_key = [k for _t, _h, k, _i in rows]
check('2a  digest() form resolves the licence key', got_key == ['RF-PINNACLE-2026'],
      repr(got_key))
check('2b  CONTROL: the pre-fix literal-hash regex finds nothing here',
      not OLD_HASH_RE.search(open(DIGEST_FORM, encoding='utf-8').read()),
      'old HASH_RE did not match, as expected')
ids = rows[0][3] if rows else set()
check('2c  the id survives alongside it', ids == {'probe-invoice-1'}, repr(sorted(ids)))
check('2d  sha256 is not mistaken for a target id', 'sha256' not in ids,
      "'sha256' absent from the id set")

# ---------------------------------------------------- arm 3: app from registry
apps = C.resource_apps()
check('3a  rf_invoices resolves to sairnroofing', apps.get('rf_invoices') == ['sairnroofing'],
      repr(apps.get('rf_invoices')))
check('3b  an unregistered table resolves to nothing',
      not apps.get('sairnroofing_employee_auth'),
      repr(apps.get('sairnroofing_employee_auth')))
# The control: the route this replaced cannot answer for this licence at all.
seedrow = False
import glob  # noqa: E402
for f in glob.glob(os.path.join(REPO, 'sql', '*license*.sql')):
    src = open(f, encoding='utf-8', errors='replace').read()
    if re.search(r"values\s*\(\s*'RF-PINNACLE-2026'", src):
        seedrow = True
check('3c  CONTROL: RF-PINNACLE-2026 has no seed row to read an app from',
      not seedrow, 'no `values (\'RF-PINNACLE-2026\'` anywhere in sql/*license*.sql')

# ------------------------------------------- arm 4: commented delete is not live
check('4a  a commented-out delete is not parsed as live', C.targets(COMMENTED_ONLY) == [],
      'targets() == []')
check('4b  and it is reported as proposed, not as a parse miss',
      'commented out' in out, 'message names the real reason')

shutil.rmtree(tmp, ignore_errors=True)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  %s' % f)
sys.exit(1 if failures else 0)
