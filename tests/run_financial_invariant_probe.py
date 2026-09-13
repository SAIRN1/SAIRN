"""tests/run_financial_invariant_probe.py -- both halves of the financial-write
piece: the invariant runner and the idempotency checker.

    python tests/run_financial_invariant_probe.py

THE ARMS THAT MATTER ARE THE CONTROLS. Both tools report clean on this repo
today, and a tool that reports clean is indistinguishable from one that looks at
nothing unless it can be shown to go red. So:

  * a real engine is SABOTAGED by one cent and the runner must catch it;
  * a synthetic in-memory-keyed write must read as GUARDED-IN-MEMORY, because
    no real instance exists on this platform to point at;
  * each tool's blind lock must BITE -- break a criterion and the tool must
    refuse to judge anything real, exiting 2 rather than reporting a pass.

ACCURACY AND STABILITY ARE PINNED AS SEPARATE FIELDS (arm 3). Collapsing them
would have hidden the first real finding of this build: ledger.validateEntry
read 2000/2000 STABLE while MISCLASSIFIED, because the adapter compared
undefined with undefined. A single score would have said PASS.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import idempotency_check as I                                   # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def node(*args, **kw):
    p = subprocess.run(['node', os.path.join(kw.get('root', REPO), 'tools',
                                             'invariant_runner.js')] + list(args),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=kw.get('root', REPO))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def py(*args):
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'idempotency_check.py')]
                       + list(args), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=REPO)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('1. the blind lock runs in ISOLATION, before any engine is called')
rc, out = node('--fixtures')
check('1a  the runner lock passes on its own', rc == 0, 'exit %d' % rc)
check('1b  and it says the fixtures ran before any engine was called',
      'before any engine was called' in out)
rc, out = py('--fixtures')
check('1c  the idempotency lock passes on its own', rc == 0, 'exit %d' % rc)
check('1d  and its POSITIVE fixture is the real api/ledger.js, not a synthetic one',
      'REAL api/ledger.js' in out)

print('2. THE LOCK BITES -- a broken criterion stops everything')
tmp = tempfile.mkdtemp(prefix='fininv-')
shutil.copytree(os.path.join(REPO, 'tools'), os.path.join(tmp, 'tools'))
shutil.copytree(os.path.join(REPO, 'api'), os.path.join(tmp, 'api'),
                ignore=shutil.ignore_patterns('*.test.js'))
reg = os.path.join(tmp, 'tools', 'invariant_registry.js')
src = io.open(reg, encoding='utf-8').read()
# Invert the double-entry criterion: balanced now means UNbalanced.
# THE SABOTAGE MUST ACTUALLY APPLY, AND THAT IS NOW ASSERTED.
# The anchor was `o.debit_total === o.credit_total`. When the registry moved to
# integer cents that string stopped existing, str.replace() silently did
# nothing, and arms 2a/2b failed against a tool that was working perfectly -- a
# control that no longer breaks its target tests nothing, which is the SECOND
# time that exact shape has appeared in this file.
_sab = src.replace('o.debit_total_cents === o.credit_total_cents',
                   'o.debit_total_cents !== o.credit_total_cents', 1)
check('2z  the sabotage anchor still matches -- a control that no longer breaks '
      'its target is not a control', _sab != src,
      'the registry changed shape and this anchor did not follow')
io.open(reg, 'w', encoding='utf-8', newline=chr(10)).write(_sab)
rc, out = node(root=tmp)
check('2a  an inverted criterion makes the runner exit 2', rc == 2, 'exit %d' % rc)
check('2b  and it says NOTHING REAL WAS RUN', 'NOTHING REAL WAS RUN' in out)
shutil.rmtree(tmp, ignore_errors=True)

print('3. ACCURACY and STABILITY are two fields, never one score')
rc, out = node('--cases', '200', '--json')
data = json.loads(out[out.index('{'):])
for r in data['results']:
    check('3a  %-34s has both fields' % r['id'],
          'accuracy' in r and 'stability' in r and 'verdict' in r['accuracy']
          and 'held' in r['stability'])
check('3b  every row carries the EVIDENCE its type was read from',
      all(len(r.get('evidence', '')) > 40 for r in data['results']))
# ── ARM 3c REWRITTEN 2026-09-13, AND THE REASON IS A CORRECTION TO ME ──
# It used to assert margin appeared on EXACTLY ONE row, "not padded onto
# equalities". That was right about the mathematics and wrong about the code:
# roofing-billing and care-charges both check `|stated - computed| < 0.005`, and
# a 0.005 tolerance band has real unused headroom. ledger is the genuine
# exception -- a bare `===` on FLOATS with no band at all, which is itself the
# finding rather than an absence of one.
#
# This is a criterion corrected on the merits after measuring the engines, NOT
# an assertion loosened to make a changed tool pass. The distinction is the one
# docs/2026-09-13-cross-domain-disciplines.md item 1 exists to keep visible, and
# the old wording is quoted above so a reader can see exactly what changed.
withmargin = [r for r in data['results'] if r['margin'].get('worst') is not None]
check('3c  every engine now reports a margin -- the tolerance band is in the CODE '
      'even where the identity is an equality',
      len(withmargin) == len(data['results']),
      '%d of %d' % (len(withmargin), len(data['results'])))
check('3d  a margin is never displayed wider than the band it sits inside',
      all(abs(r['margin']['worst']) <= 0.0050001 for r in withmargin),
      [(r['id'], r['margin']['worst']) for r in withmargin])
check('3e  the double-entry row is distinguishable: a zero-width band reports a '
      'NON-POSITIVE margin, because there is no headroom to have',
      [r for r in withmargin if r['id'].startswith('ledger')][0]['margin']['worst'] <= 0)

print('4. CONTROL -- sabotage a REAL engine by one cent and the runner must catch it')
target = os.path.join(REPO, 'api', '_lib', 'roofing-billing.js')
orig = io.open(target, encoding='utf-8').read()
old = '  const subtotal = money(lines.reduce(function (s, l) { return s + l.amount; }, 0));'
try:
    assert old in orig, 'sabotage anchor missing -- the control cannot run'
    io.open(target, 'w', encoding='utf-8', newline='\n').write(
        orig.replace(old, old[:-2] + ') - 0.01;', 1))
    rc, out = node('--cases', '200')
    check('4a  a one-cent error in a real engine is caught', rc == 1, 'exit %d' % rc)
    check('4b  and it is reported as a STABILITY failure, not an accuracy one',
          'TYPE CONFIRMED   0/200' in out or '0/200' in out)
finally:
    io.open(target, 'w', encoding='utf-8', newline='\n').write(orig)
check('4c  the engine was restored byte-identical',
      io.open(target, encoding='utf-8').read() == orig)
rc, out = node('--cases', '200')
check('4d  and the restored tree is clean again', rc == 0, 'exit %d' % rc)

print('5. the idempotency checker names the dangerous shape')
got = I.analyse('x.js', "const seen = new Map();\n"
                        "if (seen.has(payload.idempotency_key)) return;\n"
                        "await fetch(rest('t'), { method: 'POST' });")
check('5a  a module-level key store consulted WITH the caller key is GUARDED-IN-MEMORY',
      got['verdict'] == 'GUARDED-IN-MEMORY', got['verdict'])
got = I.analyse('x.js', "const BOUNDARY_LOGGED = new Set();\n"
                        "if (!BOUNDARY_LOGGED.has(seenKey)) log();\n"
                        "const q = 'source_id';\n"
                        "await fetch(rest('t'), { method: 'POST' });")
check('5b  CONTROL: a LOG-dedupe store is NOT -- the real api/sd-data.js false '
      'positive that forced this narrowing',
      got['verdict'] != 'GUARDED-IN-MEMORY', got['verdict'])
got = I.analyse('x.js', "await fetch('https://x', { method: 'POST' });")
check('5c  a retryable write with no key is UNGUARDED', got['verdict'] == 'UNGUARDED')
check('5d  a file with no write at all is not judged',
      I.analyse('x.js', "const a = 1;") is None)

rc, out = py()
check('5e  the real run exits 1 while unguarded writes exist', rc == 1, 'exit %d' % rc)
check('5f  and it DISCLOSES that its negative fixture is synthetic',
      'NEGATIVE FIXTURE IS SYNTHETIC' in out)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
