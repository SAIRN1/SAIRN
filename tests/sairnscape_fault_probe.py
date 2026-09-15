"""SAIRNscape's re-key guard, its merge and its loader must DENY.

Run: python tests/sairnscape_fault_probe.py

── GATE 4, ON THE VERTICAL WITH 12 RESOURCES AND ONE ATTRIBUTED SUITE ──────
`docs/MASTER-PLAN.md` gate 4: the guards are known to DENY, not merely to pass.
SAIRNscape read **12 resources, 1 suite, 0 traced, 0 fault probes** -- the
thinnest column on the board outside the apps with no server surface at all.

The `1 suite` is an ATTRIBUTION artefact and saying so is the point: the file
is genuinely covered, by THREE shared suites that carry no `sairnscape` in
their name (`licence_rekey_isolation.js`, `merge_by_id_overwrite.js`,
`ld_reports_unreadable.js`). All three are green. **None had ever been observed
failing against this app**, which is the state gate 4 exists to distrust.

── THREE SUBJECTS, IN DESCENDING ORDER OF WHAT THEY COST ───────────────────
  * THE RE-KEY GUARD DELETES A CUSTOMER'S DATA. That is what it is for, and it
    is why it is first. It sits between two failure modes that are both real:
    NOT wiping leaves the previous licence's jobs and customers visible to the
    next licence -- cross-tenant exposure inside the browser, which no amount
    of server-side licence scoping prevents because the leak never reaches a
    server -- and wiping WRONGLY destroys work that exists nowhere else. Every
    arm below breaks it in one of those two directions.
  * THE MERGE REPLACED A LOCAL RECORD AND SAID NOTHING. `scpMergeById` is one
    of three byte-identical copies; all three used to overwrite an edit made
    since the last sync with no error, no toast and no console line. The `_m`
    stamp and the conflict list are what stopped that.
  * THE LOADER COULD NOT TELL A CORRUPT RECORD FROM AN ABSENT ONE. `scpLd()`
    returned the default either way, so "your data is corrupt" and "you have
    none yet" rendered identically. This app carried the TRUTHINESS spelling,
    where an empty string silently took the absent branch.

── EVERY ARM IS A DEFECT THIS FILE REALLY HAD ──────────────────────────────
The merge overwrite, the truthiness loader and the unscoped storage prefix are
all recorded incidents on this app, not failure modes invented to have
something to mutate. The prefix arm is StoneDesk's lesson specifically: a
prefix of `sd` rather than `sd_` matches `sdn_clients` and deletes a design
studio's client list from inside another app.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ────────────────
The subject is copied from the WORKING TREE, not taken from HEAD, so a suite
change made to close a hole this probe finds is visible to it.

── EVERY ANCHOR IS COUNTED AND EVERY SABOTAGE VERIFIES ITSELF ──────────────
`once()` asserts exactly one match rather than letting `replace()` pick a site;
`arm()` then asserts the bytes actually moved and reached disk, because 23 of
39 controls on this platform never check that their own sabotage applied.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()

HTML = 'sairnscape.html'
REKEY = os.path.join('tests', 'licence_rekey_isolation.js')
MERGE = os.path.join('tests', 'merge_by_id_overwrite.js')
LOADER = os.path.join('tests', 'ld_reports_unreadable.js')
SUITES = (REKEY, MERGE, LOADER)
SUBJECTS = (HTML,) + SUITES

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


print('sairnscape -- the re-key guard, the merge and the loader must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-scp-')
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

    ORIG = {HTML: io.open(os.path.join(wt, HTML), encoding='utf-8', newline='').read()}

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
        try:
            for rel, old, new in edits:
                text = ORIG[rel].replace(once(rel, old), new, 1)
                assert text != ORIG[rel], (
                    'sabotage did not apply for arm %r -- the replacement is '
                    'identical to the original' % label)
                write(rel, text)
            for rel, _o, _n in edits:
                on_disk = io.open(os.path.join(wt, rel), encoding='utf-8',
                                  newline='').read()
                assert on_disk != ORIG[rel], (
                    'sabotage did not reach disk for arm %r' % label)
            rc, out = run(wt, suite)
            check(label + '  [' + os.path.basename(suite) + ']', rc != 0,
                  'the suite still PASSED against the mutation\n' + out[-300:])
        finally:
            restore()

    # ── ARM 0: THE CONTROLS, FIRST ─────────────────────────────────────────
    # A suite that cannot run also cannot pass, so without these a broken
    # worktree reports every arm below as "caught".
    for suite in SUITES:
        rc, out = run(wt, suite)
        check('the shipped tree passes %s' % os.path.basename(suite), rc == 0,
              out[-400:])

    # ═══ DIRECTION 1: THE THING THAT DELETES A CUSTOMER'S DATA ═════════════
    #
    # 1. THE GUARD NEVER FIRES. The fingerprint is compared and the answer is
    #    thrown away, so a new licence key opens the app on top of the previous
    #    licence's jobs and customers and sees them as its own. This is the
    #    exposure the feature exists to close, and nothing about the screen
    #    would look wrong -- the records are real, they are just not yours.
    arm('a re-key guard that always says yes is caught', REKEY,
        [(HTML, '  if (prev === next) return true;',
          '  if (true) return true;')])

    # 2. ...AND THE OPPOSITE DIRECTION, which is not the same bug and costs
    #    more. First run ADOPTS whatever is already on the device, because an
    #    existing install has no fingerprint and there is no way to know which
    #    licence its data belongs to. Turning that into a wipe destroys a real
    #    customer's records on the first load after an upgrade.
    arm('a first run that WIPES instead of adopting is caught', REKEY,
        [(HTML, '  if (!prev) { try { localStorage.setItem(SCP_LIC_FP, next); } catch (e) {} return true; }',
          '  if (!prev) { prev = "force-a-mismatch"; }')])

    # 3. THE REFUSAL STOPS REFUSING. Declining the confirm must keep the door
    #    shut; proceeding anyway makes the dialog decorative and deletes data
    #    somebody just said no to.
    arm('a declined confirmation that wipes anyway is caught', REKEY,
        [(HTML, """    return false;
  }
  ls.forEach(function (key) { try { localStorage.removeItem(key); } catch (e) {} });""",
          """    /* ignored */
  }
  ls.forEach(function (key) { try { localStorage.removeItem(key); } catch (e) {} });""")])

    # 4. THE PREFIX WIDENS BY ONE CHARACTER -- StoneDesk's lesson exactly.
    #    'scp' instead of 'scp_' is harmless on its own; 'sc' reaches
    #    `sc_license_key`, which belongs to SAIRNcode. The file's own live
    #    assertion SCP_SCOPE_OK names that key, so this must be caught by the
    #    guard failing closed rather than by anybody noticing the diff.
    arm('a storage prefix widened into another app is caught', REKEY,
        [(HTML, "var SCP_OWN_PREFIX = 'scp_';", "var SCP_OWN_PREFIX = 'sc';")])

    # 5. AND THE FAIL-CLOSED ITSELF. The scope check is the only thing between
    #    this wipe and another app's data. A wipe that runs with a broken scope
    #    check is the worst outcome in the file, and it is one `if` away.
    arm('a fail-CLOSED scope check turned fail-open is caught', REKEY,
        [(HTML, '  if (!SCP_SCOPE_OK) {', '  if (false) {')])

    # ═══ DIRECTION 2: AN EDIT DESTROYED BY THE NEXT SYNC ═══════════════════
    #
    # 6. LOCAL ALWAYS LOSES -- the original bug, restored exactly. An edit made
    #    after the last sync is silently reverted by the next one.
    arm('a merge where the local copy can never win is caught', MERGE,
        [(HTML, "    if(typeof lm==='string'&&typeof sm==='string'&&lm>sm){",
          "    if(false){")])

    # 7. THE TIE-BREAK FLIPS. `>` and `>=` agree everywhere EXCEPT when the two
    #    stamps are equal -- the same-millisecond case. One character, and the
    #    rule it breaks is that a local copy wins only on a STRICT newer.
    arm('a merge whose tie-break flips to >= is caught', MERGE,
        [(HTML, "&&lm>sm){", "&&lm>=sm){")])

    # 8. THE OVERWRITE GOES SILENT AGAIN. The record is still replaced
    #    correctly; only the CONFLICT REPORT is lost. That is the whole
    #    original defect -- the data movement was never the visible part.
    arm('an overwrite that is no longer reported is caught', MERGE,
        [(HTML, "    if(conflicts)conflicts.push({id:sr.id,kept:'server'});",
          "    if(false)conflicts.push({id:sr.id,kept:'server'});")])

    # ═══ DIRECTION 3: "CORRUPT" AND "EMPTY" RENDER IDENTICALLY ═════════════
    #
    # 9. THE TRUTHINESS SPELLING COMES BACK. `r ? ... : d` sends an EMPTY
    #    STRING down the absent branch. scpSv() JSON.stringify()s and can never
    #    write '', so an empty string in that store did not come from this app:
    #    it is an unreadable record being reported as "you have none yet".
    arm('a loader that reads an empty string as ABSENT is caught', LOADER,
        [(HTML, '  if(r===null) return d;                 // genuinely absent: the honest empty case',
          '  if(!r) return d;')])

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    # Every arm restores in a `finally`. A restore that silently failed would
    # leave every later arm passing against a mutated file, and the probe would
    # report green while testing a corrupted state -- the one failure mode that
    # defeats this whole method.
    ok_all = all(io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() == ORIG[rel] for rel in ORIG)
    check('the subject file is byte-identical to the working tree after every '
          'arm', ok_all,
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
