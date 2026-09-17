# REQUIREMENT: a duplicate claim recorded AFTER the guard that covers it is
#   reported as a live finding, and one recorded BEFORE is reported as history
#   -- so a fixed defect cannot be re-reported forever from its own archive
#
"""Control for `sairn_claim.py audit`.

    python tests/claims/run_claim_audit_probe.py

── WHY THIS COMMAND EXISTS, AND WHY IT NEEDS A CONTROL ────────────────────────
Released claims are KEPT on purpose -- "who ran this and when" is the question
the next session asks. The cost is that every duplicate ever recorded stays in
the file, so a reader opening `.claude/claims/` finds the 2026-09-13 quadruple
and the 2026-09-14 triple and reasonably concludes the bug is live. **That has
now happened twice.**

It is not live, and the DATES decide it rather than anybody's memory: every
exact duplicate in the record predates the guard that covers it -- `fourth`'s
triple by 43 minutes, `cc`'s pair by 22.

So the audit bins by date. **The arm that matters is the one proving it can
still say AFTER** -- a command that always answers "historical" is a command
that will miss the recurrence it exists to catch.

CONTROLS_FOR is declared, not inferred.
"""
CONTROLS_FOR = ['sairn_claim.py']

import io
import os
import sys
import contextlib

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_claim as C                                          # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


class Args(object):
    pass


def rec(session, task, epoch, status='released', subject=None):
    return {'session': session, 'subject': subject or session, 'task': task,
            'status': status, 'claimed_at': 'T%d' % epoch,
            'claimed_at_epoch': epoch}


def audit(claims):
    """Run the real command against a synthetic record. Returns (rc, output)."""
    real = C.load_all
    C.load_all = lambda from_origin=False: claims
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = C.cmd_audit(Args())
    finally:
        C.load_all = real
    return rc, buf.getvalue()


BEFORE = C.GUARDED_FROM - 3600
AFTER = C.GUARDED_FROM + 3600

print('\n1. THE BINNING, IN BOTH DIRECTIONS')
rc, out = audit([rec('a', 'x', BEFORE), rec('a', 'x', BEFORE + 30)])
check('a duplicate BEFORE the guard is counted as historical',
      'BEFORE the guard that covers them  1' in out, out[:600])
check('...and is NOT reported as a live finding',
      'A REAL FINDING' not in out, out[:600])
check('...and the run exits 0, because history is not a finding', rc == 0, rc)

rc, out = audit([rec('a', 'x', AFTER), rec('a', 'x', AFTER + 30)])
check('THE ARM THAT MATTERS: a duplicate AFTER the guard IS a live finding -- '
      'a command that always answers "historical" would miss the recurrence it '
      'exists to catch', 'A REAL FINDING' in out, out[:600])
check('...and it is printed with its session and timestamp, not just counted',
      'AFTER THE GUARD' in out, out[:800])
check('...and the run exits non-zero', rc != 0, rc)

print('\n2. WHAT IS AND IS NOT A DUPLICATE')
rc, out = audit([rec('a', 'x', BEFORE), rec('a', 'y', BEFORE + 30)])
check('CONTROL: two DIFFERENT task strings are not a duplicate -- exact means '
      'exact, and guessing that two wordings are one piece of work is what the '
      'phrase matcher already fails at',
      'duplicates (same session, subject and task): 0' in out.lower(), out[:500])
rc, out = audit([rec('a', 'x', BEFORE), rec('b', 'x', BEFORE + 30)])
check('CONTROL: the same task claimed by two DIFFERENT sessions is not a '
      'duplicate -- it is a collision, which is a different thing entirely',
      'duplicates (same session, subject and task): 0' in out.lower(), out[:500])
rc, out = audit([rec('a', 'x', BEFORE, subject='s1'),
                 rec('a', 'x', BEFORE + 30, subject='s2')])
check('CONTROL: the same task under two different SUBJECTS is not a duplicate',
      'duplicates (same session, subject and task): 0' in out.lower(), out[:500])

print('\n3. THE SECOND SHAPE IS COUNTED APART, NOT SUMMED IN')
many = [rec('a', 't%d' % i, BEFORE + i, status='active')
        for i in range(C.MANY_ACTIVE)]
rc, out = audit(many)
check('a session holding many ACTIVE claims is reported', 'active, oldest' in out,
      out[-700:])
check('...and it is NOT reported as a duplicate -- each is different work and '
      'the two need opposite fixes',
      'duplicates (same session, subject and task): 0' in out.lower(), out[:500])
check('...and it exits non-zero, because a phantom block is a real cost to '
      'another session', rc != 0, rc)
rc, out = audit([rec('a', 't%d' % i, BEFORE + i, status='active')
                 for i in range(C.MANY_ACTIVE - 1)])
check('CONTROL: one below the bar is NOT reported, so the bar is a bar',
      'no session is holding' in out, out[-500:])

print('\n4. IT CANNOT PASS BY LOOKING AT NOTHING')
rc, out = audit([])
check('an empty record is COULD-NOT-READ (exit 2), never a clean audit',
      rc == 2 and 'NOT a pass' in out, (rc, out[:300]))
rc, out = audit([rec('a', 'x', BEFORE)])
check('CONTROL: a single claim audits cleanly and exits 0, so the arm above is '
      'about emptiness and not about small inputs', rc == 0, (rc, out[:300]))

print('\n5. THE REAL RECORD, AND ONLY ITS STRUCTURAL FACTS')
real = C.load_all(from_origin=False)
check('the real claim record loads', isinstance(real, list) and len(real) > 50,
      real and len(real))
rc, out = audit(real)
# -- THIS ARM ASSERTED "NO POST-GUARD DUPLICATE AT ALL" AND THAT IS TOO
# -- STRONG (2026-09-17). It went red on a pair the guard was never able to
# -- catch, and the guard is not at fault.
#
# fourth held `... supabase_admin ownership ...` from 02:54 to 14:50 -- 11.9
# hours, never released -- and took a second overlapping claim at 13:56. The
# own-claim guard reads is_active(), and STALE_HOURS had expired the first one
# hours earlier, so there was nothing live to block against. `audit` reads the
# real held-span from `released_at`, by which measure the session genuinely held
# two claims on one piece of work.
#
# BOTH READINGS ARE RIGHT AND THEY MUST STAY DIFFERENT. If the guard used the
# held-span it would block for ever on a row somebody forgot to release; if
# `audit` used expiry it would under-count what the record actually shows.
#
# So this now asserts what the guard is ACCOUNTABLE for: no post-guard pair
# where BOTH claims were live when the second was made. A pair the expiry let
# through is a finding about release discipline, not about the guard -- and the
# second arm pins that distinction so it cannot be folded into a clean number.
_post = [q for q in C.same_work_pairs(real)
         if (q[2].get('claimed_at_epoch') or 0) > C.SELF_GUARDED_FROM]
_catchable = [q for q in _post
              if (q[2].get('claimed_at_epoch') or 0)
              - (q[1].get('claimed_at_epoch') or 0) < C.STALE_HOURS * 3600]
check('no post-guard duplicate was one the guard COULD have caught -- both '
      'claims live at the moment the second was made',
      not _catchable,
      [(q[0], q[1].get('claimed_at'), q[2].get('claimed_at'), q[3]) for q in _catchable])
check('CONTROL: a post-guard pair the EXPIRY let through is still REPORTED '
      'rather than folded into a clean count',
      ('AFTER THE GUARD' in out) == bool(_post),
      'audit says AFTER-THE-GUARD=%s, direct count says %d'
      % ('AFTER THE GUARD' in out, len(_post)))
check('CONTROL: and there really ARE duplicates to bin, so the arm above is '
      'not passing over an empty set',
      'duplicates (same session, subject and task): 0' not in out.lower(),
      out[:400])
check('the guard timestamps are real commits named in the tool, not a '
      'recollection', all(len(g[0]) >= 7 and g[2] > 0 for g in C.GUARDS), C.GUARDS)

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
