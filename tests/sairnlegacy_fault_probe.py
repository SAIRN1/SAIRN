"""tests/sairnlegacy_reservation_lock.js must DENY, not merely agree.

GATE 4 FOR THE VERTICAL WITH THE WORST COVERAGE-TO-RESOURCES RATIO ON THE
PLATFORM. docs/MASTER-PLAN.md measured SAIRNlegacy at 36 resources -- the second
most of any app -- with ONE suite, ONE traced and ZERO fault probes, while its
Tier A list is leg_certs, leg_invoices and leg_preneed (pre-need funeral money).

The suite is the first half. This is the second, because a suite whose findings
are clean has by construction never refused anything and nobody knows whether it
can. Gate 4's own wording: "The guards are known to DENY, not merely to pass. A
guard that has never been red is not known to be a guard."

── WHAT IS PLANTED, AND WHY THESE ─────────────────────────────────────────────
The reservation lock is the one genuinely load-bearing control in this app's
server path, and the consequence is in the handler's own comment: "the same
physical casket/urn promised to two grieving families". Every mutation below is a
defect somebody could plausibly write, and most of them make the code SIMPLER:

  * the conditional PATCH becomes an ordinary upsert -- the lock removed, and
    nothing about the code looks wrong afterwards
  * the condition survives but the licence scope does not
  * zero rows matched becomes a 200 -- the silent failure, and the shortest
    possible diff
  * the gate widens to every transition, which breaks ordinary saves instead
  * the client rolls back from its PRE-AWAIT SNAPSHOT again, silently undoing a
    concurrent release (the real 2026-09-02 defect, restored)
  * the client rolls back unconditionally, clobbering newer state (the same bug
    in the other direction)
  * the optimistic write is kept on a 409, leaving a device showing a
    reservation the server never holds
  * a non-409 failure is rolled back too, losing a reservation that is real

EVERY ARM MUTATES A COPY IN A THROWAWAY WORKTREE, never this clone. This repo
established on 2026-09-10 that a probe which edits tracked files is
indistinguishable from residue when it dies, and it established it the hard way:
a stranded PROBE commit reached origin twice in two days, once deleting a field
that had already made SAIRNlaw compute Florida five days late.

EVERY ANCHOR IS COUNTED, NOT MERELY FOUND. An anchor is a string match against
code somebody else keeps editing, so going AMBIGUOUS is how it ages -- and a
probe that plants in whichever place came first is asserting something about a
line nobody chose. ANCHOR-0 and ANCHOR-2 are both failures here, not skips.

Run: python tests/sairnlegacy_fault_probe.py
"""

import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
SUITE = os.path.join('tests', 'sairnlegacy_reservation_lock.js')

APP = 'sairnlegacy.html'
API = os.path.join('api', 'sd-data.js')

MUTATIONS = [
    ("1. the lock becomes an ordinary upsert -- the shortest diff that removes it",
     API,
     "      if (resource === 'leg_merch_units' && payload.status === 'Reserved') {",
     "      if (false) {"),

    ("2. the condition survives but the LICENCE scope does not -- one funeral "
     "home reserves another's unit",
     API,
     "          'leg_merch_units?license_hash=eq.' + enc(licHash) +\n"
     "          '&merch_unit_id=eq.' + enc(String(payload.id)) +",
     "          'leg_merch_units?merch_unit_id=eq.' + enc(String(payload.id)) +"),

    ("3. the status condition is dropped, so the PATCH overwrites a reservation "
     "somebody else already holds",
     API,
     "          '&data->>status=eq.Available'\n        ), {",
     "          ''\n        ), {"),

    ("4. zero rows matched answers 200 -- the silent failure",
     API,
     "        if (!Array.isArray(rows) || rows.length === 0) {\n"
     "          res.status(409).json({ error: { code: 'ALREADY_RESERVED',",
     "        if (false) {\n"
     "          res.status(409).json({ error: { code: 'ALREADY_RESERVED',"),

    ("5. the refusal loses its code, so the client cannot tell a lost race from "
     "any other failure",
     API,
     "res.status(409).json({ error: { code: 'ALREADY_RESERVED', message: 'This unit could not be reserved",
     "res.status(409).json({ error: { code: 'CONFLICT', message: 'This unit could not be reserved"),

    ("6. the gate widens to EVERY transition, so an ordinary release starts "
     "answering 409",
     API,
     "      if (resource === 'leg_merch_units' && payload.status === 'Reserved') {",
     "      if (resource === 'leg_merch_units') {"),

    ("7. the message stops naming the not-yet-synced cause, so a director hunts "
     "a colleague who did nothing",
     API,
     "or it has not finished syncing to the server yet.",
     "Somebody else has already reserved it."),

    ("8. app_id is taken from the client again",
     API,
     "        body: JSON.stringify({ license_hash: licHash, app_id: 'sairnlegacy', [idCol]: String(payload.id), data: payload, updated_at: nowISO() })\n"
     "      });\n"
     "      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlegacy data tables",
     "        body: JSON.stringify({ license_hash: licHash, app_id: body.app_id || 'sairnlegacy', [idCol]: String(payload.id), data: payload, updated_at: nowISO() })\n"
     "      });\n"
     "      if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNlegacy data tables"),

    ("9. THE REAL 2026-09-02 DEFECT, RESTORED: the rollback writes back its "
     "PRE-AWAIT snapshot and silently undoes a concurrent release",
     APP,
     "      var fresh = merchUnits();\n"
     "      var fu = fresh.find(function(x){ return x.id === mcReserveUnit; });",
     "      var fresh = list;\n"
     "      var fu = fresh.find(function(x){ return x.id === mcReserveUnit; });"),

    ("10. the rollback stops checking the reservation is still OURS, clobbering "
     "newer state",
     APP,
     "      if(fu && fu.status === 'Reserved' && fu.reserved_for_case_id === caseId){",
     "      if(fu){"),

    ("11. the optimistic write is KEPT on a 409 -- the device shows a "
     "reservation the server never holds",
     APP,
     "        fu.status='Available'; fu.reserved_for_case_id=''; fu.reserved_at='';\n"
     "        st('leg_merch_units', fresh);",
     "        /* rollback removed */"),

    ("12. every failure rolls back, so a NOT_PROVISIONED answer loses a "
     "reservation that is real on this device",
     APP,
     "    if(r.status===409&&d&&d.error&&d.error.code==='ALREADY_RESERVED'){",
     "    if(!(r.ok&&d&&d.ok)){"),

    ("13. the pre-write local re-check goes, so a stale copy overwrites "
     "somebody else's reservation before the server ever sees it",
     APP,
     "  if(u.status!=='Available'){$('reserve-err').textContent='This unit was just reserved by someone else",
     "  if(false){$('reserve-err').textContent='This unit was just reserved by someone else"),

    ("14. a failed write stops recording the server's reason, so the toast "
     "invents one",
     APP,
     "    if(!(r.ok&&d&&d.ok))legLastErr['leg_merch_units']={code:(d&&d.error&&(d.error.code||''))||('HTTP_'+r.status),message:(d&&d.error&&d.error.message)||''};",
     "    if(!(r.ok&&d&&d.ok))legLastErr['leg_merch_units']={code:'',message:''};"),

    ("15. a thrown request is swallowed",
     APP,
     "    legLastErr['leg_merch_units']={code:'NETWORK',message:e.message};",
     "    /* swallowed */"),
]

fails = []
ran = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    ran.append(name)
    if not cond:
        fails.append(name)


def run(wt):
    r = subprocess.run(['node', os.path.join(wt, SUITE)], cwd=wt,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def read(wt, rel):
    with io.open(os.path.join(wt, rel), 'rb') as f:
        return f.read()


def write(wt, rel, data):
    with io.open(os.path.join(wt, rel), 'wb') as f:
        f.write(data)


def dirty_now():
    """This clone's dirty tracked files, as a set."""
    out = subprocess.run(['git', '-C', REPO, 'status', '--porcelain',
                          '--untracked-files=no'], capture_output=True, text=True).stdout
    return set(l.strip() for l in out.split('\n') if l.strip())


def main():
    print('SAIRNlegacy -- the reservation lock suite must refuse a handler or a '
          'client that has stopped holding it\n')

    # ── SNAPSHOT THE DIRT BEFORE, NOT JUST AFTER (2026-09-14) ─────────────────
    # The first version of the closing arm asked whether sairnlegacy.html and
    # api/sd-data.js were dirty AT ALL, and it fired on its very first real run
    # -- against api/sd-data.js, which was dirty because of the author's OWN
    # uncommitted work in the same session. That conflates two different things:
    # "the probe left residue" and "somebody is editing this file". Only the
    # first is a finding, and a probe that cries wolf about the second is one
    # people learn to ignore -- which is exactly how real residue would get
    # through. So the comparison is BEFORE against AFTER, and the arm reports
    # only what THIS RUN changed.
    dirty_before = dirty_now()

    wt = tempfile.mkdtemp(prefix='sairn-leg-')
    shutil.rmtree(wt, ignore_errors=True)
    add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach',
                          wt, 'HEAD'], capture_output=True, text=True)
    if add.returncode != 0:
        print('SKIPPED: could not create a worktree -- NOTHING WAS VERIFIED.')
        print(add.stderr.strip()[:300])
        return 3

    # THE SUITE IS COPIED IN FROM THIS CLONE, not taken from HEAD. A worktree at
    # HEAD does not contain a suite that has not been committed yet, so the
    # baseline would be red for a reason that has nothing to do with the subject
    # -- and "red" is the verdict this probe reads. Copying the ONE file under
    # test keeps the probe usable before the commit and after it, and keeps every
    # other file in the worktree at HEAD where it belongs.
    try:
        shutil.copy(os.path.join(REPO, SUITE), os.path.join(wt, SUITE))
    except OSError as e:
        print('SKIPPED: could not stage the suite into the worktree -- NOTHING '
              'WAS VERIFIED. %s' % e)
        shutil.rmtree(wt, ignore_errors=True)
        subprocess.run(['git', '-C', REPO, 'worktree', 'prune'],
                       capture_output=True, text=True)
        return 3

    try:
        # ── 0. BASELINE ───────────────────────────────────────────────────────
        # Without this, every "BITES" below could be a suite that is red for an
        # unrelated reason -- and in a worktree at HEAD, an uncommitted suite is
        # exactly the way that happens.
        rc, out = run(wt)
        check('0. the suite is GREEN in the worktree before anything is planted '
              '(exit %s)' % rc, rc == 0,
              '\n       '.join([l for l in out.split('\n') if l.strip()][-4:]))
        if rc != 0:
            print('\n  The baseline is red, so no mutation below would mean '
                  'anything. Stopping.')
            return 1

        originals = {}
        for rel in sorted({m[1] for m in MUTATIONS}):
            originals[rel] = read(wt, rel)

        for name, rel, old, new in MUTATIONS:
            src = originals[rel]
            hits = src.count(old.encode('utf-8'))
            if hits != 1:
                # ANCHOR-0 and ANCHOR-2 are FAILURES, not skips. A stale anchor
                # is how this class of probe quietly stops testing anything.
                check(name, False, 'ANCHOR-%d in %s' % (hits, rel))
                continue
            write(wt, rel, src.replace(old.encode('utf-8'), new.encode('utf-8'), 1))
            rc, out = run(wt)
            check(name, rc != 0,
                  'SILENT -- the suite passed with this defect planted')
            write(wt, rel, src)

        # ── THE PLANTS WERE REALLY UNDONE, checked by hash rather than assumed.
        for rel, data in originals.items():
            check('the worktree copy of %s is byte-identical again' % rel,
                  hashlib.sha256(read(wt, rel)).hexdigest()
                  == hashlib.sha256(data).hexdigest())
        rc, out = run(wt)
        check('and the suite is GREEN again with everything restored (exit %s)'
              % rc, rc == 0)
    finally:
        shutil.rmtree(wt, ignore_errors=True)
        subprocess.run(['git', '-C', REPO, 'worktree', 'prune'],
                       capture_output=True, text=True)

    # ── THIS CLONE WAS NEVER TOUCHED. The one claim a probe like this must not
    #    take on faith, because taking it on faith is what stranded two commits.
    new_dirt = sorted(dirty_now() - dirty_before)
    check('this run left NOTHING newly dirty in this clone -- %d file(s) were '
          'already modified before it started and are not this probe\'s doing'
          % len(dirty_before), not new_dirt, '; '.join(new_dirt))

    print()
    if fails:
        print('%d ARM(S) FAILED:' % len(fails))
        for f in fails:
            print('  - ' + f)
        return 1
    # COUNTED, not derived from the length of MUTATIONS plus a guess. An arm
    # that was skipped would still be inside that arithmetic and would read as
    # having passed.
    print('ALL %d ARMS PASS -- every planted defect was refused (%d mutations).'
          % (len(ran), len(MUTATIONS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
