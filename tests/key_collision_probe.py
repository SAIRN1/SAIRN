"""Control pair for tools/key_collision_check.py.

    python tests/key_collision_probe.py     (exit 0 pass, 1 fail)

WHY THIS FILE EXISTS. `tools/checker_control_check.py` asked every promoted
checker for a file that DECLARES itself its control. This one had none.

ONE FILE NAMED IT AND WAS NOT ITS CONTROL, which is the part worth recording.
`tests/sairndental_settings_patch.js` reads this checker's SOURCE to assert an
acknowledgement entry exists and still describes the code as it is. That is a
useful test and it is not a control: it never runs the tool, never plants a
collision, and would pass unchanged against a checker that had stopped
detecting anything at all. Declaring it would have credited this checker with
proof it can fire on the strength of a file that never fires it.

EVERY SECTION IS A PAIR AND BOTH HALVES ARE REQUIRED:

    plant the defect -> the checker must REPORT it
    plant clean      -> the checker must STAY SILENT

THE THREE ARMS THAT ARE NOT THE OBVIOUS PAIR are where this checker has
actually gone wrong before, per its own header:

  * NORMAL CRUD IS NOT A COLLISION. An earlier function-name-based version
    flagged 9 keys that were all an add/edit/delete trio writing ONE variable.
    The signature is 2+ distinct BACKING VARIABLES, not 2+ writers.
  * A WRAPPER IS NOT A BLIND ZERO. Before 2026-08-07 the checker matched
    literal `localStorage.setItem` only, so an app routing every write through
    `st(k,v)` answered `TOTAL_KEY_WRITES:0` -- a blind zero that reads exactly
    like a clean one. The arm asserts the wrapper is DETECTED BY NAME and that
    the collision through it is still found.
  * A COLLISION IN A COMMENT IS NOT A COLLISION. Comments are stripped as of
    2026-09-12, found by comment_sensitivity_check.py: the tool was counting a
    line of prose as one of its 93 key writes. The verdict did not change that
    day, which is exactly why it survived -- so the arm pins the case where it
    WOULD change.

FIXTURES ARE WRITTEN TO A TEMP DIRECTORY AND NEVER TO A REAL APP FILE. A control
that mutates a tracked file in place is how this platform stranded five PROBE
commits on `origin/main` in one day.

The last arm runs against the REAL stonedesk.html, because the acknowledgement
mechanism cannot be exercised on a fixture -- ACKNOWLEDGED is a literal table
inside the tool, keyed on real key names and real variable pairs. It asserts
the SHAPE and never the COUNT: the unacknowledged total is a burndown, and an
arm pinned to a burndown dies the moment the number moves. See the comment at
that arm for the hour in which that was proved.

Exit 0 pass, 1 fail.
"""
# REQUIREMENT: two features cannot share a storage key, because a collision silently
#   overwrites one feature's data with another's
#
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['key_collision_check.py']

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, 'tools')
fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def on(body):
    d = tempfile.mkdtemp(prefix='keycol-probe-')
    p = os.path.join(d, 'app.html')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    try:
        q = subprocess.run([sys.executable,
                            os.path.join(TOOLS, 'key_collision_check.py'), p],
                           cwd=REPO, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=600)
        return q.returncode, (q.stdout or '') + (q.stderr or '')
    finally:
        shutil.rmtree(d, ignore_errors=True)


def num(out, label):
    m = re.search(r'^%s:(\d+)' % re.escape(label), out, re.M)
    return int(m.group(1)) if m else -1


# ── 1. THE PAIR ──────────────────────────────────────────────────────────────
print('1. two distinct backing variables on one key')
rc, out = on('<html><body><script>\n'
             'var zzCustomers = [];\n'
             'var zzOther = [];\n'
             "function saveA(){ localStorage.setItem('zz_key',"
             ' JSON.stringify(zzCustomers)); }\n'
             "function saveB(){ localStorage.setItem('zz_key',"
             ' JSON.stringify(zzOther)); }\n'
             '</script></body></html>\n')
check(rc == 1, 'two distinct variables writing one key exits 1 (got %d)' % rc)
check(num(out, 'COLLISIONS') == 1, '...and reports COLLISIONS:1 (got %d)'
      % num(out, 'COLLISIONS'))
check('zzCustomers' in out and 'zzOther' in out, '...and names both variables')

# ── 2. NORMAL CRUD IS NOT A COLLISION ────────────────────────────────────────
# Three functions, ONE variable, plus an inline literal reset. The reset is the
# part that has to be excluded separately: clearing state to `[]` is not a
# competing shape and counting it would make every app with a Clear button red.
print('')
print('2. CONTROL: an add/edit/delete trio on one variable is not a collision')
rc, out = on('<html><body><script>\n'
             'var zzItems = [];\n'
             "function addOne(){ localStorage.setItem('zz_key',"
             ' JSON.stringify(zzItems)); }\n'
             "function editOne(){ localStorage.setItem('zz_key',"
             ' JSON.stringify(zzItems)); }\n'
             "function delOne(){ localStorage.setItem('zz_key',"
             ' JSON.stringify(zzItems)); }\n'
             "function reset(){ localStorage.setItem('zz_key', '[]'); }\n"
             '</script></body></html>\n')
check(rc == 0, 'four writers, one variable, exits 0 (got %d)' % rc)
check(num(out, 'COLLISIONS') == 0, '...and reports COLLISIONS:0 (got %d)'
      % num(out, 'COLLISIONS'))
# IT DID READ THE FILE. A tool finding zero writes also reports zero collisions,
# so the clean verdict means nothing without this.
check(num(out, 'TOTAL_KEY_WRITES') == 4,
      '...and it really saw all four writes (got %d)'
      % num(out, 'TOTAL_KEY_WRITES'))

# ── 3. THE WRAPPER, which used to produce a BLIND ZERO ───────────────────────
print('')
print('3. a storage-write wrapper is detected by name, not hardcoded')
rc, out = on('<html><body><script>\n'
             'function zzSt(k,v){ localStorage.setItem(k, JSON.stringify(v)); }\n'
             'var zzAlpha = [];\n'
             'var zzBeta = [];\n'
             "function saveA(){ zzSt('zz_key', zzAlpha); }\n"
             "function saveB(){ zzSt('zz_key', zzBeta); }\n"
             '</script></body></html>\n')
check("'zzSt'" in out, 'a never-before-seen wrapper name is auto-detected')
check(num(out, 'TOTAL_KEY_WRITES') == 2,
      '...and its calls are counted, not a blind zero (got %d)'
      % num(out, 'TOTAL_KEY_WRITES'))
check(rc == 1, '...and the collision through it is still reported (got %d)' % rc)
check('zzAlpha' in out and 'zzBeta' in out, '...naming both variables')

# ── 4. A COLLISION THAT ONLY EXISTS IN A COMMENT ─────────────────────────────
# The 2026-09-12 fix. Without comment stripping the ghost writer below is a
# second distinct variable on zz_key, and the tool reports a defect in code that
# does not exist. The verdict MOVES here, which it did not on the day the fix
# landed -- that run changed only the count, which is why nothing contradicted
# the tool for as long as it was wrong.
print('')
print('4. CONTROL: a second writer that exists only in a COMMENT')
rc, out = on('<html><body><script>\n'
             'var zzItems = [];\n'
             '// The old code did this, and it collided:\n'
             "//   localStorage.setItem('zz_key', JSON.stringify(zzGhost));\n"
             "function saveOne(){ localStorage.setItem('zz_key',"
             ' JSON.stringify(zzItems)); }\n'
             '</script></body></html>\n')
check(rc == 0, 'prose describing a collision is not a collision (got %d)' % rc)
check(num(out, 'TOTAL_KEY_WRITES') == 1,
      '...and the commented write is not counted at all (got %d)'
      % num(out, 'TOTAL_KEY_WRITES'))
check('zzGhost' not in out, '...and the ghost variable is never named')

# ── 5. THE ACKNOWLEDGEMENT MECHANISM, against the real file ──────────────────
# This cannot be driven on a fixture: ACKNOWLEDGED is a literal table inside the
# tool, keyed on real key names and the exact variable pair somebody traced by
# hand. The arm asserts the SHAPE rather than the count -- the count is a
# burndown and pinning it would rot the moment a pair is resolved, which is the
# failure tests/fail_open_browser_probe.py already recorded against itself.
print('')
print('5. the real stonedesk.html: acknowledged is not the same as absent')
app = os.path.join(REPO, 'stonedesk.html')
if not os.path.exists(app):
    print('  SKIP stonedesk.html is not in this clone')
else:
    q = subprocess.run([sys.executable,
                        os.path.join(TOOLS, 'key_collision_check.py'), app],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=600)
    out = (q.stdout or '') + (q.stderr or '')
    total = num(out, 'COLLISIONS')
    m = re.search(r'unacknowledged:\s*(\d+)', out)
    unack = int(m.group(1)) if m else -1
    check(total > 0, 'the real file HAS collisions -- they are acknowledged, '
                     'not absent (got %d)' % total)

    # ── THE UNACKNOWLEDGED COUNT IS REPORTED, NOT ASSERTED ──────────────────
    # This arm shipped for about an hour asserting `unack == 0` and exit 0, and
    # a rebase onto origin/main broke it within that hour: commit 71ef8357
    # (Saved Drawings delete) introduced a fifth collision on `sd_drawings`
    # that nobody has traced yet. THE PROBE WAS WRONG, NOT THE TOOL -- the
    # assertion pinned a BURNDOWN, and a probe pinned to a current defect rots
    # the moment that defect moves in either direction. That is the same
    # failure tests/fail_open_browser_probe.py records against its own first
    # version (2 arms dead the moment the fourteenth loader was fixed) and
    # tests/reachability/live_mode_probe.py against its own (5 arms pinned to
    # seven findings removed the next day, red for six days).
    #
    # The SHAPE is what this arm can honestly hold: every acknowledgement is
    # printed and carries a written reason, and the scan really ran. The count
    # is printed as a number so a human sees it move.
    print('     live: %d collision(s), %d unacknowledged, exit %d'
          % (total, unack, q.returncode))
    # EVERY ACKNOWLEDGEMENT CARRIES A REASON. An exemption with a reason beside
    # it is a decision; one without is a silence.
    acked = [l for l in out.splitlines() if l.startswith('ACKNOWLEDGED: ')]
    check(len(acked) == total - unack,
          'every ACKNOWLEDGED collision is printed, not silently dropped '
          '(%d printed, %d acknowledged)' % (len(acked), total - unack))
    check(all(len(l.split(' -- ', 1)) == 2 and len(l.split(' -- ', 1)[1]) > 40
              for l in acked),
          '...and each one carries a written reason, not a bare entry')
    # THE EXIT CODE MUST TRACK THE UNACKNOWLEDGED COUNT, whatever that count
    # is. This is the half that does not rot: it is a property of the tool, not
    # a fact about today's stonedesk.html.
    check(q.returncode == (1 if unack else 0),
          'exit code tracks the UNACKNOWLEDGED count, not the total '
          '(%d unacknowledged, exit %d)' % (unack, q.returncode))
    check(num(out, 'TOTAL_KEY_WRITES') > 50,
          'and the scan really ran over the real file (got %d writes)'
          % num(out, 'TOTAL_KEY_WRITES'))

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
