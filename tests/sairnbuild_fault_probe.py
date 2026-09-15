"""SAIRNbuild's cache scoping, its backup hook and its retainage refusals must DENY.

Run: python tests/sairnbuild_fault_probe.py

── GATE 4, ON THE LAST VERTICAL WITH 32 RESOURCES AND NO PROBE ─────────────
`docs/MASTER-PLAN.md` gate 4: the guards are known to DENY, not merely to pass.
SAIRNbuild owns **32 resources** -- more than any other app -- and had **zero**
fault probes. Four suites cover it and every one of them was green, which is
exactly the state gate 4 exists to distrust: a suite that has never been
observed failing has not been shown to discriminate.

── THREE SUBJECTS, CHOSEN BECAUSE THEY FAIL IN THREE DIFFERENT DIRECTIONS ──
  * A SILENT PRIVACY LEAK. `bldCacheOwnerChanged()` / `bldPurgeScopedCaches()`
    clear 32 cached `bld_*` collections when a DIFFERENT employee signs in on
    the same browser. Break it and the second person on a shared site laptop
    reads the first one's bids. Nothing on screen looks wrong -- the data is
    real, it is just somebody else's.
  * SILENT DATA LOSS. The backup hook inside `st()` is the only thing standing
    between thirty collections and one browser. Its three guards each fail
    quietly and in a different way: pushing during `seed()` fills a customer's
    server with demo rows; dropping the changed-only comparison turns a repaint
    into hundreds of writes; and NOT recording a failed push makes that failure
    PERMANENT, because the next save sees the record unchanged and skips it.
    That last one is the defect the pending queue was built for.
  * A SILENT FALSE FINANCIAL RECORD. The retainage release refusals in
    `api/sd-data.js`. A release larger than was ever held, or one that reduces
    an existing release, is not an error anybody sees -- it is a number on a
    contractual balance that is wrong in the direction somebody chases money in.

── EVERY ARM IS A DEFECT THIS PLATFORM REALLY HAD ──────────────────────────
The no-id skip is the line StoneDesk lost SIX collections to. The pending queue
exists because every push this feature ever attempted failed for weeks in
silence. The cache purge exists because a scoped read is defeated by a stale
local copy. None of these are hypothetical failure modes invented to have
something to mutate.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ────────────────
Subject files are copied from the WORKING TREE, not taken from HEAD, so a suite
change made to close a hole this probe finds is visible to it. That trap was hit
for real on tests/sairnbiz_fault_probe.py's first run.

── EVERY ANCHOR IS COUNTED, NOT MERELY FOUND ───────────────────────────────
`once()` asserts exactly one match and refuses rather than letting `replace()`
pick which site to damage.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()

HTML = 'sairnbuild.html'
API = os.path.join('api', 'sd-data.js')
# Suites
CACHE = os.path.join('tests', 'phi_cache_scoped_to_user.js')
BACKUP = os.path.join('tests', 'sairnbuild_server_backup.js')
PENDING = os.path.join('tests', 'sairnbuild_backup_pending.js')
RETAIN = os.path.join('api', '_lib', 'sairnbuild-retainage-endpoint.test.js')
SUITES = (CACHE, BACKUP, PENDING, RETAIN)
# Everything copied in from the working tree. The retainage suite reaches for
# api/_lib/auth.js, api/_lib/license.js and api/_lib/calendar-date.js, which the
# worktree already carries at HEAD -- only files this probe MUTATES, or that a
# working-tree edit could have changed, need copying.
SUBJECTS = (HTML, API) + SUITES

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(wt, suite):
    r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('sairnbuild -- the cache purge, the backup hook and the retainage '
      'refusals must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-bld-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    for _rel in SUBJECTS:
        shutil.copyfile(os.path.join(REPO, _rel), os.path.join(wt, _rel))

    ORIG = {}
    for rel in (HTML, API):
        ORIG[rel] = io.open(os.path.join(wt, rel), encoding='utf-8', newline='').read()

    def write(rel, text):
        io.open(os.path.join(wt, rel), 'w', encoding='utf-8', newline='').write(text)

    def restore():
        for rel, txt in ORIG.items():
            write(rel, txt)

    def once(rel, needle):
        n = ORIG[rel].count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1 -- '
                        'widen the anchor rather than letting replace() pick'
                        % (needle[:60], n, rel))
        return needle

    def arm(label, suite, edits):
        # ── THE SABOTAGE VERIFIES ITSELF BEFORE THE SUITE IS ASKED ─────────
        # Measured 2026-09-13: 23 of 39 negative controls on this platform
        # never check that their own sabotage APPLIED. One that did not apply
        # runs the suite against the SHIPPED file, gets a pass, and reports
        # "the suite still PASSED against the mutation" -- a real-looking
        # finding about a mutation that never existed. `once()` proves the
        # anchor is unique; this proves the bytes actually moved.
        try:
            for rel, old, new in edits:
                text = ORIG[rel].replace(once(rel, old), new, 1)
                assert text != ORIG[rel], (
                    'sabotage did not apply to %s for arm %r -- the replacement is '
                    'identical to the original' % (rel, label))
                write(rel, text)
            for rel, _old, _new in edits:
                on_disk = io.open(os.path.join(wt, rel), encoding='utf-8',
                                  newline='').read()
                assert on_disk != ORIG[rel], (
                    'sabotage did not reach disk for %s on arm %r' % (rel, label))
            rc, out = run(wt, suite)
            check(label + '  [' + os.path.basename(suite) + ']', rc != 0,
                  'the suite still PASSED against the mutation\n' + out[-300:])
        finally:
            restore()

    # ── ARM 0: THE CONTROLS, FIRST ─────────────────────────────────────────
    # Without these a probe whose worktree is broken reports every arm as
    # "caught" -- a suite that cannot run also cannot pass.
    for suite in SUITES:
        rc, out = run(wt, suite)
        check('the shipped tree passes %s' % os.path.basename(suite), rc == 0,
              out[-400:])

    # ═══ DIRECTION 1: THE SECOND PERSON ON THE LAPTOP READS THE FIRST'S BIDS
    #
    # 1. The owner-change detector never fires. The purge is still there and
    #    still correct; it is simply never called, which is the version of this
    #    bug that survives a code review of the purge itself.
    arm('an owner-change detector that never fires is caught', CACHE,
        [(HTML, '  return prev !== null && prev !== who;\n',
          '  return false;\n')])

    # 2. ...and the other half, because they fail independently. The detector
    #    fires correctly and the purge does nothing.
    arm('a purge that clears nothing is caught', CACHE,
        [(HTML, '  BLD_SCOPED_CACHES.forEach(function(k){try{localStorage.removeItem(k);}catch(e){}});',
          '  if (false) BLD_SCOPED_CACHES.forEach(function(k){try{localStorage.removeItem(k);}catch(e){}});')])

    # 3. ONE KEY FALLS OFF THE LIST, and it is the one the suite names as the
    #    private thing. A list of 32 strings loses an entry in a merge without
    #    anybody noticing; the code keeps working perfectly for the other 31.
    arm('bld_bids dropped from the scoped-cache list is caught', CACHE,
        [(HTML, "var BLD_SCOPED_CACHES = ['bld_bids','bld_sub_bids',",
          "var BLD_SCOPED_CACHES = ['bld_sub_bids',")])

    # ═══ DIRECTION 2: THE BACKUP DOES THE WRONG AMOUNT OF WORK, SILENTLY
    #
    # 4. A FAILED PUSH IS NOT RECORDED. This is the sharpest arm in the file.
    #    The push already failed and already said nothing; not queueing the id
    #    makes it PERMANENT, because the next save of that collection sees the
    #    record unchanged and skips it. The record stays on one device for good
    #    and the app looks healthy the entire time.
    arm('a failed push that is never queued for retry is caught', PENDING,
        [(HTML, '      if (saved === null) bldPendingMark(key, rid); else bldPendingClear(key, rid);',
          '      if (saved === null) { /* dropped */ } else bldPendingClear(key, rid);')])

    # 5. THE SEED GUARD. seed() writes ~30 arrays of demo rows in one pass.
    #    Pushing them puts demo data in a paying customer's server tables --
    #    and it is indistinguishable from their own records afterwards.
    arm('pushing demo rows during seed() is caught', BACKUP,
        [(HTML, '  if (!_bldSyncOn[key] || bldSeeding) return;',
          '  if (!_bldSyncOn[key]) return;')])

    # 6. THE CHANGED-ONLY COMPARISON. Dropping it is not a data defect at all
    #    -- every record still reaches the server. It turns one page repaint
    #    into hundreds of network writes, which is why a correctness-only suite
    #    would let it through.
    arm('pushing every record on every render is caught', BACKUP,
        [(HTML, '    if (before[String(r.id)] === now) return;   // unchanged -- nothing to push',
          '    if (false) return;')])

    # 7. THE NO-id SKIP STOPS COUNTING. StoneDesk lost SIX collections to this
    #    exact line: rows with no id left the function without a sound while
    #    sitting on a list whose name reads as "this is backed up". Here the
    #    row is still skipped -- only the COUNT is lost, so the warning never
    #    prints. Losing the disclosure is the whole defect.
    arm('a row with no id skipped WITHOUT being counted is caught', BACKUP,
        [(HTML, "    if (!r || r.id === undefined || r.id === null || r.id === '') { skipped++; return; }",
          "    if (!r || r.id === undefined || r.id === null || r.id === '') { return; }")])

    # ═══ DIRECTION 3: A CONTRACTUAL BALANCE THAT IS QUIETLY WRONG
    #
    # 8. A RELEASE MAY BE REDUCED. Reducing a release is un-paying somebody,
    #    and it leaves no trace: the figure simply becomes smaller.
    arm('a retainage release that goes BACKWARDS is caught', RETAIN,
        [(API, '      if (relAmt < already) {', '      if (false) {')])

    # 9. THE ENGINE'S OWN REFUSALS STOP BEING ENFORCED. This is the arm that
    #    proves the branch actually DELEGATES: newProblems is the whole
    #    mechanism by which a rule added to wip-accounting.js is enforced here.
    #    Neutralise it and "more retainage released than was ever held" lands.
    arm('releasing more than was ever held is caught', RETAIN,
        [(API, '      if (newProblems.length) {', '      if (false) {')])

    # 10. THE DATE HELPER IS DOWNGRADED TO THE SHAPE IT REPLACED -- the exact
    #     fourteen-times-copied line api/_lib/calendar-date.js exists to retire.
    #     '2026-02-31' passes the shape and `new Date` silently repairs it into
    #     2026-03-03. A release date three days from where somebody typed it.
    arm('a date-SHAPED release date that is not a real date is caught', RETAIN,
        [(API, '      if (!isBldDate(relOn)) {',
          '      if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(relOn)) {')])

    # 11. ...and the same downgrade on `today`, which is a different code path
    #     and would otherwise be covered only by inference from arm 10.
    arm('a date-SHAPED `today` that is not a real date is caught', RETAIN,
        [(API, '      if (!isBldDate(bToday)) {',
          '      if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(String(bToday || \'\'))) {')])

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    # Every arm restores in a `finally`. A restore that silently failed would
    # leave every later arm passing against a mutated file, and the probe would
    # report green while testing a corrupted state -- the one failure mode that
    # defeats this whole method.
    ok_all = all(io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() == ORIG[rel] for rel in ORIG)
    check('both subject files are byte-identical to the working tree after '
          'every arm', ok_all,
          'a restore did not land -- later arms tested a mutated file')
    for suite in SUITES:
        rc, out = run(wt, suite)
        check('...and %s is green again on it' % os.path.basename(suite),
              rc == 0, out[-300:])
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
