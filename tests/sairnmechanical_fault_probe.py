"""SAIRNmechanical's dispatch gate, its EPA threshold and its cheque identity must DENY.

Run: python tests/sairnmechanical_fault_probe.py

── GATE 4, AND THIS ONE IS THE MOST REGULATED SUBJECT IN THE SEAM ──────────
`docs/MASTER-PLAN.md` gate 4: the guards are known to DENY, not merely to pass.
SAIRNmechanical read 6 resources, 3 attributed suites, 0 fault probes -- and
five suites in total are green against it. None had ever been observed failing.

What makes this app different from the rest of the seam is that TWO of its
three subjects produce statements with a REGULATORY citation attached. A wrong
answer here is not a bad screen; it is a compliance claim the shop did not make
and cannot support.

── THREE SUBJECTS ─────────────────────────────────────────────────────────
  * EPA 608 SECTIONS ARE EQUIPMENT, NOT RANKS. Type I is small appliances,
    Type II high-pressure, Type III low-pressure, Universal all three. A Type I
    technician is not "less certified" than a Type II one -- they are certified
    for DIFFERENT MACHINES. So "has an EPA card" is not an answer to "may this
    person open this chiller", and a gate that treats the sections as a
    hierarchy dispatches somebody to work they are not certified for.
  * AN UNRECORDED REFRIGERANT CHARGE IS NEVER "BELOW THRESHOLD". EPA keys its
    leak-repair provisions to a full charge at or above 50 lb (40 CFR 82.157).
    `Number('')` is 0 in JavaScript, so an empty charge field coerced through
    Number() becomes a MEASURED ZERO and a unit nobody ever weighed gets
    reported as under the threshold. The engine's own header records that this
    was caught by a test rather than by a shop discovering it on a chiller.
  * ONE WORKSTATION'S CHEQUE OVERWRITING ANOTHER'S. `MECH_ID_FIELD` used to say
    `{ mech_checks: 'num' }`, so the server row was keyed on the CHEQUE NUMBER;
    the write is an upsert on (license_hash, check_id), and `crNum` starts at
    1001 on any device with no local `_crnum`. A second workstation issuing its
    own #1001 UPDATED the first device's #1001 -- a financial record replaced,
    silently, by an unrelated one.

── EVERY ARM IS A DEFECT THIS APP REALLY HAD ──────────────────────────────
The empty-charge coercion and the cheque-number key are both recorded incidents
on these exact files, not failure modes invented to have something to mutate.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ────────────────
Subjects are copied from the WORKING TREE, not taken from HEAD, so a suite
change made to close a hole this probe finds is visible to it.

── EVERY ANCHOR IS COUNTED AND EVERY SABOTAGE VERIFIES ITSELF ──────────────
`once()` asserts exactly one match rather than letting `replace()` pick a site;
`arm()` then asserts the bytes moved and reached disk, because 23 of 39
controls on this platform never check that their own sabotage applied.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()

CRED = os.path.join('api', '_lib', 'mech-credentials.js')
ASSET = os.path.join('api', '_lib', 'mech-assets.js')
HTML = 'sairnmechanical.html'

CRED_UNIT = os.path.join('api', '_lib', 'mech-credentials.test.js')
CRED_API = os.path.join('api', 'sd-data-mech-credentials.test.js')
ASSET_UNIT = os.path.join('api', '_lib', 'mech-assets.test.js')
ASSET_API = os.path.join('api', 'sd-data-mech-assets.test.js')
CHECKS = os.path.join('tests', 'mech_check_register_identity.js')
SUITES = (CRED_UNIT, CRED_API, ASSET_UNIT, ASSET_API, CHECKS)
SUBJECTS = (CRED, ASSET, HTML) + SUITES

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


print('sairnmechanical -- the dispatch gate, the EPA threshold and the cheque '
      'identity must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-mech-')
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
    for rel in (CRED, ASSET, HTML):
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
        try:
            for rel, old, new in edits:
                text = ORIG[rel].replace(once(rel, old), new, 1)
                assert text != ORIG[rel], (
                    'sabotage did not apply for arm %r' % label)
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
    for suite in SUITES:
        rc, out = run(wt, suite)
        check('the shipped tree passes %s' % os.path.basename(suite), rc == 0,
              out[-400:])

    # ═══ DIRECTION 1: SOMEBODY DISPATCHED TO WORK THEY MAY NOT DO ══════════
    #
    # 1. THE SECTION RULE COLLAPSES INTO "HAS A CARD". This is the headline
    #    defect the engine's header was written against: a Type I technician
    #    sent to a high-pressure chiller because the gate stopped asking WHICH
    #    equipment the certification covers.
    arm('an EPA 608 gate that accepts any section is caught', CRED_UNIT,
        [(CRED, "    return rec.epa_section === 'universal' || rec.epa_section === req.epa_section;",
          "    return true;")])

    # 2. ...and the same mutation seen from the ENDPOINT, which is a different
    #    code path and a different suite. A gate can be correct in the engine
    #    and never reached over HTTP.
    arm('...and the endpoint does not let it through either', CRED_API,
        [(CRED, "    return rec.epa_section === 'universal' || rec.epa_section === req.epa_section;",
          "    return true;")])

    # 3. AN EMPTY REQUIREMENT LIST BECOMES "ANYONE MAY GO". The refusal exists
    #    because a job nobody specified is not a job everybody is qualified
    #    for, and the difference is invisible on a dispatch board.
    arm('an empty requirement list read as universal eligibility is caught',
        CRED_UNIT,
        [(CRED, "  if (!Array.isArray(requirements) || !requirements.length) {",
          "  if (false) {")])

    # 4. AN EXPIRED CREDENTIAL STARTS DISPATCHING. `met` is the one line that
    #    decides whether a lapsed card still sends somebody to a job.
    arm('an EXPIRED credential that still dispatches is caught', CRED_UNIT,
        [(CRED, "      const met = c.status === 'current' || c.status === 'expiring';",
          "      const met = c.status !== 'missing';")])

    # ═══ DIRECTION 2: A COMPLIANCE CLAIM NOBODY MADE ═══════════════════════
    #
    # 5. Number('') IS 0. Remove the empty-string guard and a unit nobody ever
    #    weighed is reported as BELOW the 40 CFR 82.157 threshold -- the exact
    #    unknown-reported-as-cleared failure this file exists to prevent.
    arm('an EMPTY charge field read as a measured zero is caught', ASSET_UNIT,
        [(ASSET, "  if (typeof v === 'string' && v.trim() === '') return null;",
          "  /* guard removed */")])

    # 6. THE SAME WRONG ANSWER BY THE OTHER ROUTE. Keep chargeLb() honest and
    #    drop the null check instead: `null >= 50` is false, so an unweighed
    #    unit falls straight through to 'below'. Two different edits, one
    #    identical compliance claim -- which is why both are armed.
    arm('a NULL charge falling through to "below" is caught', ASSET_UNIT,
        [(ASSET, "  if (lb === null || lb < 0) {", "  if (false) {")])

    # 7. ...and from the endpoint, for the same reason as arm 2.
    arm('...and the endpoint does not report it as below either', ASSET_API,
        [(ASSET, "  if (typeof v === 'string' && v.trim() === '') return null;",
          "  /* guard removed */")])

    # 8. "NOBODY CHECKED" AND "CHECKED, NOT IN WARRANTY" COLLAPSE INTO ONE
    #    ANSWER. has_warranty === false is a POSITIVE finding somebody made.
    #    Folding it into unknown loses the distinction between a unit with no
    #    cover and a unit whose cover nobody has looked up.
    arm('an out-of-warranty unit reading the same as an unchecked one is caught',
        ASSET_UNIT,
        [(ASSET, "  if (asset.has_warranty === false) return { status: 'none', days: null, warn_days: w };",
          "  /* folded into unknown */")])

    # ═══ DIRECTION 3: A CHEQUE REPLACED BY AN UNRELATED ONE ════════════════
    #
    # 9. THE ORIGINAL DEFECT, RESTORED EXACTLY. Key the server row on the
    #    cheque NUMBER and a second workstation's #1001 upserts over the
    #    first's. Nothing errors; a financial record is simply replaced.
    arm('the cheque register keyed on the NUMBER again is caught', CHECKS,
        [(HTML, "  var MECH_ID_FIELD = {};",
          "  var MECH_ID_FIELD = { mech_checks: 'num' };")])

    # 10. THE MINT STOPS. Without a per-record id the push has nothing unique
    #     to key on, and mechPushOne falls back to `id` -- which is now absent,
    #     so the cheque is never backed up at all and says so only to a console
    #     nobody is reading.
    arm('a cheque saved with no minted id is caught', CHECKS,
        [(HTML, "  const entry={id:mechCheckId(),num:crNum++,",
          "  const entry={num:crNum++,")])

    # 11. THE BACKFILL STOPS. Cheques written before the fix have no id; the
    #     backfill is what gives the merge something to key on. Silently
    #     skipping it strands exactly the historical rows nobody will notice.
    arm('a backfill that leaves old cheques without ids is caught', CHECKS,
        [(HTML, "  (checks||[]).forEach(function(c){ if(c&&!c.id){ c.id=mechCheckId(); changed=true; } });",
          "  (checks||[]).forEach(function(c){ if(false){ c.id=mechCheckId(); changed=true; } });")])

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    # Every arm restores in a `finally`. A restore that silently failed would
    # leave every later arm passing against a mutated file, and the probe would
    # report green while testing a corrupted state -- the one failure mode that
    # defeats this whole method.
    ok_all = all(io.open(os.path.join(wt, rel), encoding='utf-8',
                         newline='').read() == ORIG[rel] for rel in ORIG)
    check('all three subject files are byte-identical to the working tree after '
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
