"""tests/sairnvet_audit_and_controlled.js must DENY, not merely agree.

Run: python tests/sairnvet_fault_probe.py

── WHY SAIRNVET AND WHY NOW ─────────────────────────────────────────────────
`docs/MASTER-PLAN.md` gate 4: *"a mutation probe that plants a real defect in
that app's source and proves a guard catches it. The guards are known to DENY,
not merely to pass. A guard that has never been red is not known to be a
guard."*

SAIRNvet owns **41 resources -- more than any other vertical on this platform**
-- and had **no fault probe at all**. It holds `sv_controlled`, the DEA-relevant
controlled-substance register, and `sv_audit_log`, the dosing audit trail. Its
suite, `tests/sairnvet_audit_and_controlled.js`, carries 58 arms and has been
green every time anybody has run it. Green is what a suite that cannot fail
looks like from the outside, and this is the only way to tell the two apart.

NOT COUNTED BEFORE, AND THE REASON IS WORTH STATING. `tests/faults/` already
holds `sv_backup_write_faults.js` and `sv_suppression_faults.js`, and neither is
this. Those inject a RUNTIME fault -- storage throwing mid-write -- and assert
the app copes. This mutates the SOURCE and asserts the SUITE refuses. They are
different questions and only the second one answers gate 4. (`master_plan.py`
also counts only `.py` probes, which is a second reason those two do not show
up; that is its business, not this file's.)

── EVERY ARM MUTATES A COPY IN A THROWAWAY WORKTREE, never this clone ───────
Established on this platform on 2026-09-10, the hard way: a stranded PROBE
commit reached origin twice in two days, once deleting a field whose absence had
already made SAIRNlaw compute Florida five days late.

── EVERY ANCHOR IS COUNTED, NOT MERELY FOUND ────────────────────────────────
An anchor is a string match against code somebody else keeps editing, so going
AMBIGUOUS is how it ages. `once()` asserts exactly one match and refuses rather
than letting `replace()` pick.

── EVERY ARM RESTORES A DEFECT THIS APP REALLY HAD ──────────────────────────
Not invented mutations. Each one is the code as it stood before the 2026-09-04
silent-failure sweep, or the guard added after it, so a green arm means the
suite would catch that specific regression returning -- which is a narrower and
more useful claim than "the suite reacts to damage".
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
SUITE = os.path.join('tests', 'sairnvet_audit_and_controlled.js')
HTML = 'sairnvet.html'

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(wt):
    r = subprocess.run(['node', os.path.join(wt, SUITE)], cwd=wt,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('sairnvet -- the 58-arm audit and controlled-substance suite must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-sv-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    ORIG = io.open(os.path.join(wt, HTML), encoding='utf-8', newline='').read()

    def write(text):
        io.open(os.path.join(wt, HTML), 'w', encoding='utf-8', newline='').write(text)

    def once(needle):
        n = ORIG.count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1 -- '
                        'widen the anchor rather than letting replace() pick'
                        % (needle[:60], n, HTML))
        return needle

    def arm(label, marker, old, new):
        try:
            write(ORIG.replace(once(old), new, 1))
            rc, out = run(wt)
            check(label, rc == 1 and marker in out,
                  'exit=%s marker_present=%s\n%s' % (rc, marker in out, out[-300:]))
        finally:
            write(ORIG)

    # ── ARM 0: THE CONTROL, FIRST ───────────────────────────────────────────
    # A probe whose arms all pass against a suite that was already broken would
    # report the same thing as a working one.
    rc, out = run(wt)
    check('the shipped tree PASSES', rc == 0, out[-400:])
    check('...and the suite really ran its arms rather than exiting early',
          '58 passed' in out, out[-300:])

    # ── ARM 1: the clinical sign-off stops reading the audit result ─────────
    # The original defect. onDoseVetSignoff() said "recorded for this patient"
    # over a write that had not happened, and the audit row is the ONLY thing
    # that handler writes.
    arm('a sign-off that confirms over a FAILED audit write is caught',
        'a failed sign-off does NOT say "recorded for this patient"',
        '    if(!audited) return;   // logDoseAudit has already said what happened\n',
        '')

    # ── ARM 2: Schedule II balances summed ACROSS units again ──────────────
    # The seed carries Fentanyl in mL and logControlledUse() creates a newly
    # logged drug with unit '' -- so one reduce adds millilitres to milligrams
    # and prints the result as a controlled-substance balance.
    arm('summing Schedule II across UNITS is caught',
        'mL and mg are reported separately',
        '      byUnit[u] = (byUnit[u]||0) + Number(d.onHand||0);',
        '      byUnit["units"] = (byUnit["units"]||0) + Number(d.onHand||0);')

    # ── ARM 3: the KPI claims a date filter that does not exist ────────────
    # These rows carry no transaction date, only a free-text lastTransaction
    # string, so "This Month" described a filter nothing implements.
    arm('a KPI label claiming a month filter that does not exist is caught',
        'the KPI no longer claims to be scoped to this month',
        '<div class="kpi"><div class="kpi-label">Negative Balances (all time)</div>',
        '<div class="kpi"><div class="kpi-label">Discrepancies This Month</div>')

    # ── ARM 4: a refused audit write stops telling anyone ──────────────────
    # st() returns false on a full or unavailable store. Silence here is the
    # whole 2026-09-04 family: a lost DEA-relevant row and nothing on screen.
    arm('a refused audit write that says NOTHING is caught',
        'and SAYS SO -- this is the whole defect',
        "    showToast('NOT recorded to the audit log",
        "    if(false) showToast('NOT recorded to the audit log")

    # ── ARM 5: logDoseAudit reports success regardless ─────────────────────
    # The sharper half of the same thing: not a missing message but a wrong
    # return value, which every one of the seventeen call sites would believe.
    arm('logDoseAudit returning true over a refused write is caught',
        'a refused audit write returns false',
        '    ok = st(SV_AUDIT_KEY, log);',
        '    st(SV_AUDIT_KEY, log); ok = true;')

    # ── ARM 6: the corrupt-store guard stops refusing the write ────────────
    # This is the guard that keeps an unreadable DEA log byte-for-byte intact
    # rather than overwriting it. Removing the refusal is how a compliance
    # record gets destroyed by the app that was meant to protect it.
    arm('a write over an UNREADABLE controlled-substance key is caught',
        'a direct write to the corrupt key is REFUSED',
        'catch(err){_svUnreadable[key]=true;_svWriteFailed=key;'
        'svBlockForCorruptStore([key]);return false;}',
        'catch(err){_svUnreadable[key]=true;}')

    # ── ARM 7: THE CONTROL AT THE END, NOT ONLY AT THE START ───────────────
    # Every arm above restores in a `finally`, and a restore that silently
    # failed would leave the remaining arms passing against a mutated file.
    # Asserting the tree is clean again is cheap and is the only thing that
    # distinguishes "all arms ran" from "the first arm ran".
    check('the worktree copy is byte-identical to HEAD after every arm',
          io.open(os.path.join(wt, HTML), encoding='utf-8', newline='').read() == ORIG,
          'a restore did not land -- later arms tested a mutated file')
    rc, out = run(wt)
    check('...and the suite is green again on it', rc == 0, out[-300:])
finally:
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)
    print('\n  the throwaway worktree is gone: %s' % (not os.path.isdir(wt)))

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
