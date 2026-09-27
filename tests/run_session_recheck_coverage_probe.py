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
print('\n4b. THE PRE-GATE SHAPE -- and why recognising it is not an escape hatch')
# THIS TOOL'S MODEL WAS WRONG AND ITS OWN SUBJECT PROVED IT. `explicit < gates ->
# partial` assumes ONE RE-CHECK PER GATE. api/sd-data.js's 131 uncovered gates
# were closed by a SINGLE re-check at the entry point, above every gate -- one
# edit rather than 131 -- and this tool called that a REGRESSION, because the gate
# count rose by one (the pre-gate's own verification) while the re-check count
# stayed at one. It would have rewarded 132 scattered copies and punished the fix.
#
# The recognition is position-based and STRICT, and the negative arms below are
# the point: a loose version would score any early re-check as total coverage.
PRE = ("module.exports = async () => {\n"
       "  const p = verifySessionToken(tokenFromRequest(req), licHash);\n"
       + RECHECK)
write(d, 'api/pre.js', PRE + (GATE * 12) + '};\n')
rc, out = run(d)
check('ONE re-check with exactly ONE gate above it, and 12 below, is '
      'covered-pre-gate -- not partial', 'covered-pre-gate' in out
      and num(out, 'FILES_PARTIAL') == 0,
      'partial=%s :: %s' % (num(out, 'FILES_PARTIAL'),
                            [l for l in out.split('\n') if 'pre.js' in l]))
check('...and it contributes ZERO uncovered gates, because a 13th gate added '
      'later is behind it too',
      num(out, 'GATES_UNCOVERED_INSIDE_PARTIAL_FILES') == 0,
      str(num(out, 'GATES_UNCOVERED_INSIDE_PARTIAL_FILES')))
os.remove(os.path.join(d, 'api', 'pre.js'))

# ── NEGATIVE 1: TWO gates above the re-check leaves those two uncovered ────
write(d, 'api/mid.js',
      "module.exports = async () => {\n" + (GATE * 2) + RECHECK + (GATE * 10) + '};\n')
rc, out = run(d)
check('TWO gates above the re-check is PARTIAL, not a pre-gate -- those two run '
      'on the token alone', num(out, 'FILES_PARTIAL') == 1,
      [l for l in out.split('\n') if 'mid.js' in l])
os.remove(os.path.join(d, 'api', 'mid.js'))

# ── NEGATIVE 2: ZERO gates above it is not a pre-gate either ───────────────
# A re-check with no verified session above it has nothing to look up. The old
# arm 4 fixture is exactly this shape and must stay partial.
write(d, 'api/nogate.js',
      "module.exports = async () => {\n" + RECHECK + (GATE * 10) + '};\n')
rc, out = run(d)
check('ZERO gates above the re-check is PARTIAL too -- it would be querying for '
      'a session nothing has verified', num(out, 'FILES_PARTIAL') == 1,
      [l for l in out.split('\n') if 'nogate.js' in l])
os.remove(os.path.join(d, 'api', 'nogate.js'))

# ── NEGATIVE 3: TWO re-checks is not a pre-gate, however early they are ────
# NAMED tworechecks.js, NOT two.js -- the first draft of this arm reused
# `api/two.js`, a fixture arm 1 created and arms 5 and 6 still depend on, and then
# DELETED it. Arm 5's control then failed for a reason that had nothing to do with
# its subject: removing an unprotected file lowered FILES_WITH_NEITHER, so the pin
# no longer registered a regression and the control's `rc == 1` went to 0. A
# fixture that mutates shared state is the probe's own version of the defect this
# tool hunts, and it took a red arm three sections away to surface it.
write(d, 'api/tworechecks.js',
      PRE + RECHECK + (GATE * 10) + '};\n')
rc, out = run(d)
check('TWO re-checks is PARTIAL -- two employee reads per request and two places '
      'for the three-state handling to drift', num(out, 'FILES_PARTIAL') == 1,
      [l for l in out.split('\n') if 'tworechecks.js' in l])
os.remove(os.path.join(d, 'api', 'tworechecks.js'))

# ---------------------------------------------------------------------------
print('\n4c. DELETING A PRE-GATE IS A REGRESSION -- the hole the ablation found')
# FOUND BY ABLATING THE FIX, NOT BY REVIEW. Removing api/sd-data.js's entire
# pre-gate made every AGGREGATE read better: uncovered-in-partial went 131 -> 0,
# because a file with zero re-checks is not `partial` any more, and one incidental
# `active=eq.true` in 14,900 lines landed it on covered-by-route instead of
# NEITHER. Numbers improved, exit 0, and the fix could have been reverted in
# silence. The aggregates cannot see a DOWNGRADE, only a count, so the verdict
# itself is pinned per file.
#
# The obvious repair -- requiring route >= gates -- is the one this tool must NOT
# make: every api/*-auth.js has 3 to 13 gates and ONE active=eq.true inside the
# shared loadEmployee() that every gated path calls, and accusing all seventeen
# was this tool's own first wrong number. Arm 5 guards that. So this arm guards
# the downgrade instead, leaving the classification alone.
write(d, 'api/pregate.js', PRE + (GATE * 12) + '};\n')
rc, out = run(d, '--baseline')
check('a pre-gate file pins as covered-pre-gate', rc == 0, 'exit=%s' % rc)
# Now delete ONLY the re-check, leaving the gates and an incidental route hit --
# strictly worse, and the shape that used to read as an improvement.
write(d, 'api/pregate.js',
      "module.exports = async () => {\n"
      "  const p = verifySessionToken(tokenFromRequest(req), licHash);\n"
      + (GATE * 12) + ROUTE + '};\n')
rc, out = run(d)
check('removing the re-check but keeping an incidental active=eq.true is a '
      'REGRESSION, not an improvement', rc == 1 and 'REGRESSION' in out,
      'exit=%s :: %s' % (rc, out[-400:]))
check('...and it names the file and BOTH verdicts, so the downgrade is legible',
      'api/pregate.js' in out and 'covered-pre-gate ->' in out, out[-400:])
os.remove(os.path.join(d, 'api', 'pregate.js'))
run(d, '--baseline')   # restore the pin for the arms below

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
sd_row = [l for l in out.split('\n') if 'api/sd-data.js' in l and 'covered' in l
          or ('api/sd-data.js' in l and 'partial' in l)]
# ── THIS ARM PASSED FOR THE WRONG REASON AND THEN FOR NO REASON ────────────
# It read `'api/sd-data.js' in out and 'partial' in out` -- two INDEPENDENT
# substring tests over the whole output, and the word "partial" appears in the
# tool's own legend on every run. So it could never fail while the tool printed
# its legend, and it kept passing on 2026-09-26 after sd-data.js became
# covered-pre-gate, reporting the OPPOSITE of the truth. Anchored on that file's
# OWN ROW now, and on the verdict the row actually carries.
check('api/sd-data.js is reported covered-pre-gate -- a SINGLE re-check at the '
      'entry point above all 133 gates, which is what closed 131 of them',
      len(sd_row) == 1 and 'covered-pre-gate' in sd_row[0],
      str(sd_row))
check('...and it is NOT reported partial, which is what it was until the '
      'pre-gate landed', not any('partial' in l for l in sd_row), str(sd_row))
after_bytes = io.open(real_pin, 'rb').read() if os.path.isfile(real_pin) else None
after_mtime = os.path.getmtime(real_pin) if os.path.isfile(real_pin) else None
check('a plain run WROTE NOTHING to the real pin file -- identical bytes AND an '
      'unchanged mtime, so a write-then-restore would fail this too',
      before_bytes == after_bytes and before_mtime == after_mtime,
      'bytes_same=%s mtime_same=%s' % (before_bytes == after_bytes,
                                       before_mtime == after_mtime))
# THE SAME WRONG INSTRUMENT, SIX LINES BELOW THE COMMENT EXPLAINING IT
# ── AND IT WAS STILL HERE. The paragraph above records that `git status
# --porcelain` was the wrong way to ask "did this tool write" and was replaced
# with bytes and mtime -- FOR THE PIN FILE. The api/ half of the same arm kept
# the discarded instrument, so it went red on 2026-09-26 the moment api/sd-data.js
# had an uncommitted edit: it was reporting the AUTHOR's work in progress as the
# TOOL having written to api/. Fixed the same way, against the files the tool
# actually reads.
api_files = [os.path.join(REPO, 'api', 'sd-data.js'),
             os.path.join(REPO, 'api', 'sd-sub-data.js')]
api_before = [(io.open(p, 'rb').read(), os.path.getmtime(p)) for p in api_files]
run(REPO)
api_after = [(io.open(p, 'rb').read(), os.path.getmtime(p)) for p in api_files]
check('...and a run WRITES NOTHING to api/ -- bytes AND mtime on the files it '
      'reads, not `git status`, which reports the author\'s own uncommitted work',
      api_before == api_after, 'an api/ file was written by the tool')

shutil.rmtree(d, ignore_errors=True)
print('\n%s  run_session_recheck_coverage_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
