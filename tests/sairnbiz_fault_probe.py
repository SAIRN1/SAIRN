"""SAIRNbiz's money suites must DENY, not merely agree.

Run: python tests/sairnbiz_fault_probe.py

── GATE 4, ON THE BEST RATIO LEFT ───────────────────────────────────────────
`docs/MASTER-PLAN.md` gate 4: the guards are known to DENY, not merely to pass.
SAIRNbiz carried 9 suites and 8 of them traced to a stated requirement -- the
densest coverage on the platform -- and **zero** fault probes. Dense coverage
that has never been red is the case where a mutation probe is worth most,
because everything else already looks finished.

── WHAT THIS DELIBERATELY DOES NOT RE-TEST ──────────────────────────────────
`tests/sairnbiz_void_mutation_control.js` already plants TWELVE mutations in the
void mechanism and verifies each one applied. Re-covering that ground would add
arms and no information. This probe takes the money paths that control does not
touch: the THREE-WAY MATCH's own decision, and the LEDGER SOURCE-ID trail.

(That file is JS, so `master_plan.py` -- which counts a parseable MUTATIONS
block or a `*_fault_probe.py` name, both `.py` -- has never counted it. The
vertical read 0 while holding a good control. Stated here because otherwise
this probe's arrival looks like it closed a gap that was partly already shut.)

── EVERY MUTATION IS A DEFECT THIS APP REALLY HAD, OR ONE ITS OWN COMMENTS ──
── NAME AS THE THING BEING PREVENTED ───────────────────────────────────────
The float-comparison arm is the sharpest: `sbMatchPure` decided money equality
in binary floating point against a tolerance of exactly 0.00, so two partial
deliveries of $1,870.93 and $1,957.54 against a $3,828.47 PO summed to
3828.4700000000003 and the gate printed *"billed $3828.47 against $3828.47
actually received"* -- two identical figures and a refusal nobody could act on.
Found by RUNNING the shipped function during the item 44 author-blind review,
not by reading it. This arm is that regression returning.

── EVERY ARM RUNS IN A THROWAWAY WORKTREE, never this clone ────────────────
The rule this platform paid for on 2026-09-10, when a stranded PROBE commit
reached origin twice in two days.

── EVERY ANCHOR IS COUNTED, NOT MERELY FOUND ───────────────────────────────
`once()` asserts exactly one match and refuses rather than letting `replace()`
pick. And each arm names WHICH suite must refuse, because a mutation that takes
some unrelated suite red proves nothing about the guard it was aimed at.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
HTML = 'sairnbiz.html'
MATCH = os.path.join('tests', 'sairnbiz_bill_cannot_settle_unmatched.js')
LEDGER = os.path.join('tests', 'sairnbiz_ledger_source_id.js')

SUBJECTS = (HTML, MATCH, LEDGER)

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


print('sairnbiz -- the three-way match and the ledger trail must REFUSE\n')

wt = tempfile.mkdtemp(prefix='sairn-sb-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:

    # ── THE WORKING TREE, NOT HEAD, AND THE REASON IS A REAL TRAP ──────────
    # `git worktree add ... HEAD` gives a copy of what was COMMITTED. That is
    # right for isolation and wrong for what this probe is for: a suite change
    # made to close a hole this probe just found is UNCOMMITTED, so the probe
    # would keep reporting the same hole and the fix would look ineffective.
    # It happened on the first run of this file. So the subject files are
    # copied over from the working tree after the worktree is created -- the
    # isolation is unchanged (nothing is ever written back), and what gets
    # tested is what you are about to commit.
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

    def arm(label, suite, old, new):
        try:
            mutated = ORIG.replace(once(old), new, 1)
            assert mutated != ORIG, 'the mutation changed nothing: ' + label
            write(mutated)
            rc, out = run(wt, suite)
            check(label + '  [' + os.path.basename(suite) + ']', rc != 0,
                  'the suite still PASSED against the mutation\n' + out[-300:])
        finally:
            write(ORIG)

    # ── ARM 0: THE CONTROLS, FIRST ─────────────────────────────────────────
    for suite in (MATCH, LEDGER):
        rc, out = run(wt, suite)
        check('the shipped tree passes %s' % os.path.basename(suite), rc == 0,
              out[-400:])

    # ── 1. THE FLOAT COMPARISON RETURNS ────────────────────────────────────
    # The item 44 finding, exactly. Two partial deliveries summing to
    # 3828.4700000000003 made Math.abs(bill - recv) come out 4.5e-13 against a
    # zero tolerance, and a CORRECT bill was refused with two identical figures
    # printed side by side.
    arm('money compared in binary floating point again', MATCH,
        '  var poC=sbMoneyCents(po.amt), billC=sbMoneyCents(amt);',
        '  var poC=Number(po.amt)||0, billC=Number(amt)||0;')
    # THE FIRST VERSION OF THIS ARM WAS WRONG AND IS RECORDED RATHER THAN
    # QUIETLY REPLACED. It mutated the per-receipt conversion to
    # `(Number(r.val)||0)*100`, expecting the float error back -- and the suite
    # PASSED, correctly: 1870.93*100 and 1957.54*100 are each EXACT in IEEE754,
    # so scaling before summing loses nothing. Reading that as a hole in the
    # suite would have been the reverse of the truth. The error only exists
    # when the SUM happens in dollars, which is what the shipped defect did, so
    # that is what this plants: a dollar-space comparison on the received side,
    # |3828.47 - 3828.4700000000003| = 4.5e-13 > 0, refusing a correct bill.
    arm('...and the same on the RECEIVED side alone, which is where it bit',
        MATCH,
        '  if(recs.length&&Math.abs(billC-recvC)>tolC)',
        '  if(recs.length&&Math.abs((Number(amt)||0)-recs.reduce(function(a,r){'
        'return a+(Number(r.val)||0);},0))>SB_MATCH_TOLERANCE)')

    # ── 2. TWO POs WITH ONE NUMBER BECOMES PICK-THE-FIRST ──────────────────
    # po_num comes from a PER-DEVICE counter, so two workstations really do both
    # raise PO-2026-001. Taking [0] validates a bill against whichever happened
    # to be first, with a different amount sitting beside it and nothing said.
    arm('a duplicate PO number silently picks the first row', MATCH,
        "  if(pos.length>1) return {ok:false,reasons:[pos.length+' different purchase orders are numbered '+po_num",
        "  if(false) return {ok:false,reasons:[pos.length+' different purchase orders are numbered '+po_num")

    # ── 3. THE VENDOR STOPS BEING PART OF THE MATCH ────────────────────────
    # A three-way match that does not check who the bill is from is a two-way
    # match with a longer name.
    arm('the bill no longer has to come from the PO\'s vendor', MATCH,
        "  if(sbVendorKey(po.vendor)!==sbVendorKey(vendor))\n    reasons.push('vendor differs:",
        "  if(false)\n    reasons.push('vendor differs:")

    # ── 4. A BILL WITH NOTHING RECEIVED STOPS BEING HELD ───────────────────
    # The whole mechanism: a bill is RECORDED but cannot be SETTLED until goods
    # are known to have arrived.
    arm('a bill against a PO with no receipts is no longer held', MATCH,
        '  if(!recs.length) reasons.push(recsHeld',
        '  if(false) reasons.push(recsHeld')

    # ── 5. A BILL WITH NO PO NUMBER AT ALL PASSES ──────────────────────────
    arm('a bill carrying no purchase-order number passes the gate', MATCH,
        "  if(!po_num) return {ok:false,reasons:['no purchase order number on this bill']};",
        '')

    # ── 6. THE LEDGER TRAIL POINTS AT NOTHING AGAIN ────────────────────────
    # saveExp() used to mint 'EX-'+Date.now().slice(-6) purely to fill
    # source_id and never wrote it onto the expense, so every expense entry in
    # the general ledger pointed at a string matching nothing in sb_exps.
    arm('an expense posting points at an id the record does not carry', LEDGER,
        "      source_app:'sairnbiz',source_kind:'expense',source_id:exId,",
        "      source_app:'sairnbiz',source_kind:'expense',source_id:'EX-'+String(Date.now()).slice(-6),")

    # ── 7. AND THE SAME SHAPE ONE FUNCTION DOWN ────────────────────────────
    # blId fell back to the invoice number, which is optional and which two
    # vendors can issue identically -- so it is a human handle, never a key.
    arm('a bill posting keys on the optional invoice number instead of the bill id',
        LEDGER,
        "    source_app:'sairnbiz',source_kind:'bill_received',source_id:blId,",
        "    source_app:'sairnbiz',source_kind:'bill_received',source_id:$('blinv').value.trim(),")

    # ── THE CLOSING CONTROL ────────────────────────────────────────────────
    # Every arm restores in a `finally`. A restore that silently failed would
    # leave every later arm passing against a mutated file, and the probe would
    # report green while testing a corrupted state -- the one failure mode that
    # defeats this whole method.
    check('the worktree copy is byte-identical to the working tree after every arm',
          io.open(os.path.join(wt, HTML), encoding='utf-8', newline='').read() == ORIG,
          'a restore did not land -- later arms tested a mutated file')
    for suite in (MATCH, LEDGER):
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
