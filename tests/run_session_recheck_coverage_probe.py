"""tools/session_recheck_coverage.py must NOTICE a new unprotected gate, must NOT
fire on a correct addition, and must refuse rather than pass when it cannot tell.

    python tests/run_session_recheck_coverage_probe.py

WHY THE NEGATIVE ARMS ARE THE ONES THAT MATTER. A ratchet is the easiest kind of
check to get wrong in the silent direction: pin a number, compare, and report OK
forever because the number never moves for a reason that has nothing to do with
the property. So every arm below plants a real file in a throwaway copy of the
repo's `api/` tree and drives the SHIPPING tool against it -- the clone is never
written, which the closing arm asserts by mtime as well as by content.

AND THE FIRST NUMBER THIS TOOL PRODUCED WAS WRONG, which is why arm 5 exists.
Counting only `credentialStillActive(` reports 3 of 222 gates covered and would
have accused seventeen correct `api/*-auth.js` files, every one of which
re-checks by loading the employee row with `active=eq.true`. An arm pins that
both mechanisms are counted.
"""
CONTROLS_FOR = ['session_recheck_coverage.py']

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_REL = os.path.join('tools', 'session_recheck_coverage.py')
PINS_REL = os.path.join('docs', 'session-recheck-coverage.json')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def sandbox():
    """A repo-shaped throwaway carrying only what the tool reads."""
    d = tempfile.mkdtemp(prefix='sairn-recheck-')
    os.makedirs(os.path.join(d, 'tools'))
    os.makedirs(os.path.join(d, 'docs'))
    os.makedirs(os.path.join(d, 'api', '_lib'))
    shutil.copy(os.path.join(REPO, TOOL_REL), os.path.join(d, TOOL_REL))
    return d


def write(d, rel, text):
    p = os.path.join(d, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(text)


def run(d, *args):
    r = subprocess.run([sys.executable, TOOL_REL] + list(args), cwd=d,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def num(out, key):
    for line in out.split('\n'):
        if line.startswith(key + ':'):
            return int(line.split(':', 1)[1])
    return None


GATE = "  const s = verifySessionToken(tokenFromRequest(req), licHash, 'x');\n"
RECHECK = "  const ok = await credentialStillActive(s, licHash, rest, headers);\n"
ROUTE = "  await fetch(rest(t + '?active=eq.true&select=active'), { headers });\n"

# ---------------------------------------------------------------------------
print('1. THE BASELINE IS A MEASUREMENT, not a target')
d = sandbox()
write(d, 'api/one.js', 'module.exports = async () => {\n' + GATE + RECHECK + '};\n')
write(d, 'api/two.js', 'module.exports = async () => {\n' + GATE + '};\n')
rc, out = run(d)
check('with no pin file it is COULD NOT TELL (exit 2), never a pass',
      rc == 2 and 'COULD NOT TELL' in out, 'exit=%s' % rc)
check('...and it counted both files: 2 gates', num(out, 'GATES_TOTAL') == 2,
      str(num(out, 'GATES_TOTAL')))
check('...and named the unprotected one as NEITHER',
      num(out, 'FILES_WITH_NEITHER') == 1 and 'api/two.js' in out,
      'files_with_neither=%s' % num(out, 'FILES_WITH_NEITHER'))
rc, out = run(d, '--baseline')
check('--baseline writes the pin file and exits 0',
      rc == 0 and os.path.isfile(os.path.join(d, PINS_REL)), 'exit=%s' % rc)
rc, out = run(d)
check('and the very next run is OK against its own pin', rc == 0 and 'OK --' in out,
      'exit=%s' % rc)
check('...and the OK says it is NOT a pass',
      'is not closed' in out or 'NOT a pass' in out, out[-200:])

# ---------------------------------------------------------------------------
print('\n2. A NEW UNPROTECTED GATE IS A REGRESSION -- the arm this exists for')
write(d, 'api/three.js', 'module.exports = async () => {\n' + GATE + '};\n')
rc, out = run(d)
check('adding a third file with a bare gate FAILS (exit 1)', rc == 1, 'exit=%s' % rc)
check('...and it names which number moved',
      'REGRESSION' in out and 'files_with_neither' in out, out[-300:])

# ---------------------------------------------------------------------------
print('\n3. CONTROL: A NEW *PROTECTED* GATE MUST NOT FIRE')
# Same third file, now with the re-check. A ratchet that fired on every new gate
# would be uninstallable and would be switched off within a day.
write(d, 'api/three.js', 'module.exports = async () => {\n' + GATE + RECHECK + '};\n')
rc, out = run(d)
check('a correctly re-checked new gate does NOT fail', rc == 0, 'exit=%s :: %s' % (rc, out[-200:]))

# ---------------------------------------------------------------------------
print('\n4. THE PARTIAL SHAPE -- what a presence check cannot see')
# One file, many gates, ONE re-check. This is api/sd-data.js: 132 gates and a
# single credentialStillActive, which satisfies "is it called at all" while 131
# gates run on the token alone.
write(d, 'api/many.js',
      'module.exports = async () => {\n' + RECHECK + (GATE * 10) + '};\n')
rc, out = run(d)
check('a file with 10 gates and 1 re-check is reported PARTIAL, not covered',
      'PARTIAL' in out and num(out, 'FILES_PARTIAL') == 1,
      'files_partial=%s' % num(out, 'FILES_PARTIAL'))
check('...and the UNCOVERED count inside it is 9, not 0',
      num(out, 'GATES_UNCOVERED_INSIDE_PARTIAL_FILES') == 9,
      str(num(out, 'GATES_UNCOVERED_INSIDE_PARTIAL_FILES')))
check('...and that counts as a regression against the pin', rc == 1, 'exit=%s' % rc)
os.remove(os.path.join(d, 'api', 'many.js'))

# ---------------------------------------------------------------------------
print('\n5. BOTH MECHANISMS ARE COUNTED -- the arm against this tool\'s own first '
      'wrong number')
# Counting only credentialStillActive reported 3 of 222 and would have accused
# every api/*-auth.js, which re-checks by loading the employee row filtered
# active=eq.true. A file using ONLY that route must read as covered.
write(d, 'api/byroute.js', 'module.exports = async () => {\n' + GATE + ROUTE + '};\n')
rc, out = run(d)
check('a gate protected only by an active=eq.true employee load reads as COVERED',
      'covered-by-route' in out and rc == 0,
      'exit=%s :: %s' % (rc, [l for l in out.split('\n') if 'byroute' in l]))
# CONTROL for the control: strip the route and it must go back to NEITHER, or the
# arm above would pass on a tool that called everything covered.
write(d, 'api/byroute.js', 'module.exports = async () => {\n' + GATE + '};\n')
rc, out = run(d)
check('CONTROL: remove the active=eq.true load and the same file is NEITHER again',
      rc == 1 and 'api/byroute.js' in out.split('NEITHER MECHANISM')[-1],
      'exit=%s' % rc)
os.remove(os.path.join(d, 'api', 'byroute.js'))

# ---------------------------------------------------------------------------
print('\n6. IMPROVEMENT IS REPORTED AND ASKS TO BE RE-PINNED')
write(d, 'api/two.js', 'module.exports = async () => {\n' + GATE + RECHECK + '};\n')
rc, out = run(d)
check('closing a gate reports IMPROVED and exits 0',
      rc == 0 and 'IMPROVED' in out, 'exit=%s :: %s' % (rc, out[-200:]))
check('...and says to re-pin so the gain cannot be lost', '--baseline' in out)

# ---------------------------------------------------------------------------
print('\n7. A COMMENTED-OUT GATE IS NOT A GATE')
write(d, 'api/commented.js',
      'module.exports = async () => {\n'
      '  // const s = verifySessionToken(tokenFromRequest(req), licHash, "x");\n'
      '};\n')
rc, out = run(d)
check('a gate inside a // comment is not counted',
      'api/commented.js' not in out, [l for l in out.split('\n') if 'commented' in l])
os.remove(os.path.join(d, 'api', 'commented.js'))

# ---------------------------------------------------------------------------
print('\n8. AN UNPARSEABLE PIN FILE IS COULD-NOT-TELL, NOT A PASS')
io.open(os.path.join(d, PINS_REL), 'w', encoding='utf-8', newline='\n').write('{ not json')
rc, out = run(d)
check('a corrupt pin file exits 2 and says nothing was compared',
      rc == 2 and 'will not parse' in out, 'exit=%s' % rc)

# ---------------------------------------------------------------------------
print('\n9. AND THE REAL REPO -- so the arms above are not a fixture dialect')
# ── ASSERTED BY BYTES AND mtime, NOT BY `git status` ───────────────────────
# The first version of this arm read `git status --porcelain`, which reports a
# NEWLY ADDED file as dirty until it is committed -- so it went red on the very
# commit that introduced the pin file, about a tool that had written nothing.
# A commit-state proxy for "was this written" is the wrong instrument: bytes and
# mtime answer the actual question and answer it whatever git thinks.
real_pin = os.path.join(REPO, PINS_REL)
before_bytes = io.open(real_pin, 'rb').read() if os.path.isfile(real_pin) else None
before_mtime = os.path.getmtime(real_pin) if os.path.isfile(real_pin) else None
rc, out = run(REPO)
check('the shipping api/ tree parses and yields a non-trivial gate count',
      (num(out, 'GATES_TOTAL') or 0) > 100, 'gates=%s' % num(out, 'GATES_TOTAL'))
check('...and api/sd-data.js is reported PARTIAL rather than covered',
      'api/sd-data.js' in out and 'partial' in out,
      [l for l in out.split('\n') if 'sd-data' in l])
after_bytes = io.open(real_pin, 'rb').read() if os.path.isfile(real_pin) else None
after_mtime = os.path.getmtime(real_pin) if os.path.isfile(real_pin) else None
check('a plain run WROTE NOTHING to the real pin file -- identical bytes AND an '
      'unchanged mtime, so a write-then-restore would fail this too',
      before_bytes == after_bytes and before_mtime == after_mtime,
      'bytes_same=%s mtime_same=%s' % (before_bytes == after_bytes,
                                       before_mtime == after_mtime))
api_dirty = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', 'api/'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace').stdout.strip()
check('...and no api/ file is modified in the clone', api_dirty == '', api_dirty[:200])

shutil.rmtree(d, ignore_errors=True)
print('\n%s  run_session_recheck_coverage_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
