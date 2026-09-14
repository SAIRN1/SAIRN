"""SAIRNsenior's offline-EVV suite must DENY, not merely agree.

Run: python tests/sairnsenior_fault_probe.py

── GATE 4, AND WHY THIS SUBJECT ─────────────────────────────────────────────
`docs/MASTER-PLAN.md` gate 4: the guards are known to DENY, not merely to pass.
SAIRNsenior carried 10 suites and zero fault probes.

The subject is offline EVV because it is the one where a wrong record is worse
than a missing one. **Electronic Visit Verification is federally mandated** (21st
Century Cures Act), and the code this replaced returned *"check your connection
and try again"* and DISCARDED the clock event -- so a caregiver in a basement, a
rural home or a concrete stairwell had no way to record a visit that really
happened. The three properties the suite holds are all of that shape, and each
one fails silently if it breaks:

  1. THE RECORDED TIME IS WHEN THE CAREGIVER CLOCKED, NEVER WHEN IT SYNCED.
     Re-stamping on flush produces an EVV record that is precise, plausible and
     FALSE -- and nothing downstream can tell.
  2. FIFO, STOPPING AT THE FIRST FAILURE. One visit clocked in and out while
     offline queues two entries; applying the clock-out first leaves a
     completed visit with no start time, which reads as an EVV exception that
     never happened.
  3. NOTHING IS SILENTLY DROPPED at the queue cap.

── EVERY MUTATION IS ONE OF THOSE PROPERTIES, INVERTED ──────────────────────
Not invented damage. Each arm is the specific failure the suite's own header
names, so a green arm is the narrow claim that THAT regression would be caught.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ────────────────
And the subject files are copied in from the WORKING TREE rather than taken
from HEAD: a suite change made to close a hole this probe found is uncommitted,
and a probe that reads HEAD would keep reporting the same hole while the fix sat
on disk. That trap was hit for real on tests/sairnbiz_fault_probe.py's first run.

── EVERY ANCHOR IS COUNTED, NOT MERELY FOUND ───────────────────────────────
`once()` asserts exactly one match and refuses rather than letting `replace()`
pick which site to damage.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
HTML = 'sairnsenior.html'
EVV = os.path.join('api', '_lib', 'sairnsenior-offline-evv.test.js')
SUBJECTS = (HTML, EVV)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(wt, suite):
    r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('sairnsenior -- the offline-EVV suite must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-sen-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    for _rel in SUBJECTS:
        shutil.copyfile(os.path.join(REPO, _rel), os.path.join(wt, _rel))

    ORIG = io.open(os.path.join(wt, HTML), encoding='utf-8', newline='').read()

    def write(text):
        io.open(os.path.join(wt, HTML), 'w', encoding='utf-8', newline='').write(text)

    def once(needle):
        n = ORIG.count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1 -- '
                        'widen the anchor rather than letting replace() pick'
                        % (needle[:60], n, HTML))
        return needle

    def arm(label, edits):
        try:
            mutated = ORIG
            for old, new in edits:
                mutated = mutated.replace(once(old), new, 1)
            assert mutated != ORIG, 'the mutation changed nothing: ' + label
            write(mutated)
            rc, out = run(wt, EVV)
            check(label, rc != 0,
                  'the suite still PASSED against the mutation\n' + out[-300:])
        finally:
            write(ORIG)

    # ── ARM 0: THE CONTROL, FIRST ──────────────────────────────────────────
    rc, out = run(wt, EVV)
    check('the shipped tree PASSES', rc == 0, out[-400:])
    # A FLOOR, NOT A PINNED COUNT. The first version asserted '26/26' and went
    # red the moment this probe's own findings added four arms to the suite --
    # an assertion that fails on the fix it caused. What matters is that the
    # suite RAN and has not SHRUNK, so that is what is asserted, and the floor
    # is named rather than derived: a derived one would move with the shrink.
    m = re.search(r'PASS (\d+)/(\d+)', out)
    check('...and the suite really ran its checks rather than exiting early',
          bool(m) and m.group(1) == m.group(2) and int(m.group(2)) >= 26,
          'expected PASS n/n with n >= 26 (the count on 2026-09-14); got: '
          + out[-200:])

    # ── 1. THE TIME IS RE-STAMPED ON FLUSH ─────────────────────────────────
    # The record becomes precise, plausible and false. A visit clocked at 14:00
    # in a basement and synced at 18:40 is filed as an 18:40 visit, and every
    # downstream reviewer sees a consistent record of something that did not
    # happen at that time.
    arm('a replayed payload re-stamped with the SYNC time is caught',
        [("      var saved=await senData('write','sen_visits',entry.payload,true);",
          "      var saved=await senData('write','sen_visits',"
          "Object.assign({},entry.payload,{clock_in_at:new Date().toISOString()}),true);")])

    # ── 2. THE QUEUE FLUSHES NEWEST-FIRST ──────────────────────────────────
    # A clock-out reaching the server before its clock-in: a completed visit
    # with no start time, which reads as an EVV exception that never happened.
    arm('flushing the queue NEWEST-first is caught',
        [('      var entry=q[0];', '      var entry=q[q.length-1];'),
         ('      cur.shift();', '      cur.pop();')])

    # ── 3. A FAILURE SKIPS TO THE NEXT ENTRY ───────────────────────────────
    # Same damage by another route, and the more tempting one to write: it
    # looks like resilience.
    arm('a failed send that SKIPS to the next entry is caught',
        [('      if(!saved)break;',
          '      if(!saved){var _c=evvQueue();_c.shift();'
          'st(SEN_EVV_QUEUE_KEY,_c);continue;}')])

    # ── 4. THE CAP DROPS QUIETLY INSTEAD OF REFUSING ───────────────────────
    # Returning true at the cap means the caregiver is told the visit was
    # recorded and it was not. That is the one case where the event really is
    # lost, and the whole design is that it is said out loud.
    arm('a queue cap that reports success and drops the event is caught',
        [('  if(q.length>=SEN_EVV_QUEUE_MAX)return false;',
          '  if(q.length>=SEN_EVV_QUEUE_MAX)return true;')])

    # ── 5. THE OFFLINE EVENT IS DISCARDED AGAIN ────────────────────────────
    # The original defect, restored: a failed write and nothing queued.
    arm('an offline clock event that is discarded rather than queued is caught',
        [('    if(!evvQueueAdd(payload)){', '    if(true){')])

    # ── 6. THE POST-AWAIT RE-READ IS DROPPED ───────────────────────────────
    # Another clock action appending while a send is in flight is silently
    # overwritten -- a visit that vanishes from the queue without being sent.
    arm('writing back the PRE-await array, dropping a concurrent clock event, '
        'is caught',
        [('      var cur=evvQueue();', '      var cur=q;')])

    # ── 7. THE RE-ENTRY GUARD IS REMOVED ───────────────────────────────────
    arm('a flush that can run concurrently with itself is caught',
        [('  if(_evvFlushing)return {sent:0,left:evvQueue().length};',
          '  if(false)return {sent:0,left:evvQueue().length};')])

    # ── 8. THE LICENCE CHECK IS REMOVED ────────────────────────────────────
    # Without a key the flush must do nothing rather than erroring -- an
    # unlicensed device is exactly where the queue matters most.
    arm('a flush that tries to send with no licence key is caught',
        [('  if(!senLicenseKey())return {sent:0,left:evvQueue().length};',
          '  if(false)return {sent:0,left:evvQueue().length};')])

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    # Every arm restores in a `finally`. A restore that silently failed would
    # leave every later arm passing against a mutated file, and the probe would
    # report green while testing a corrupted state -- the one failure mode that
    # defeats this whole method.
    check('the worktree copy is byte-identical to the working tree after every arm',
          io.open(os.path.join(wt, HTML), encoding='utf-8', newline='').read() == ORIG,
          'a restore did not land -- later arms tested a mutated file')
    rc, out = run(wt, EVV)
    check('...and the suite is green again on it', rc == 0, out[-300:])
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
