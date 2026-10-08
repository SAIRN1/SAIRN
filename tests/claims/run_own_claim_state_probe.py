"""Prove a session can see its OWN claim's liveness -- the one view that could not.

THE DEFECT, MEASURED 2026-10-08 AND NOT HYPOTHETICAL.
`sairn_claim.py`'s `registry_claims(me)` builds liveness-stamped pseudo-claims
for every session EXCEPT `me`. So cody, fourth and hank all read cc's claim with
`_alive=True` from the pid lock and `is_active()` returned True whatever its age.
cc's own view had no `_alive` and no `_heartbeat`, fell through to the fixed
`now() - claimed_at < 4h` timeout, and reported its own live 5.3-hour claim as
gone. One record, two answers, and the session's own answer was the wrong one.

AND IT CORRECTS A CLAIM THE b3 REPORT MADE. That report said items 6-12 landed
under a claim "invisible to every other clone as live work". False -- every other
clone saw it held. The real defect is narrower and still real: the session is the
one party that cannot see its own liveness, which is what made it re-claim and
then state a conclusion that was not true.

WHAT THESE ARMS LOCK. `own_claim_state()` and `stamp_own_liveness()` as PURE
functions of (claim rows, liveness tuple) -- `own_liveness` is replaced per arm,
so no arm depends on what any real process is doing. A probe whose verdict moves
with unrelated live work is not a probe, which is the same reason
`registry_claims()` refuses to read the machine registry out of its own clone.

Every arm is PAIRED: a state that must be reached AND one that must not.
"""
import importlib.util
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location(
    'sairnclaim', os.path.join(REPO, 'tools', 'sairn_claim.py'))
claim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claim)

_fail = []


def ok(what, cond, detail=''):
    if cond:
        print('  ok   %s' % what)
    else:
        _fail.append(what)
        print('  FAIL %s%s' % (what, ('\n         [%s]' % (detail,))
                               if detail else ''))


NOW = time.time()


def row(hours_old, status='active', session='cc', **kw):
    d = {'session': session, 'status': status, 'subject': session,
         'task': 'planted', 'claimed_at': 'planted',
         'claimed_at_epoch': NOW - hours_old * 3600}
    d.update(kw)
    return d


class Patched(object):
    """Replace own_liveness / load_mine / session_name for one arm, then restore.

    Restoring matters: a later arm reading a leaked stub would be measuring the
    stub. The anchor is asserted present before replacement, so a rename cannot
    turn these arms into no-ops that pass for ever.
    """

    def __init__(self, liveness, rows, me='cc'):
        self.liveness, self.rows, self.me = liveness, rows, me

    def __enter__(self):
        for name in ('own_liveness', 'load_mine', 'session_name',
                     'own_claim_state', 'stamp_own_liveness'):
            assert hasattr(claim, name), 'anchor %s is gone' % name
        self.saved = (claim.own_liveness, claim.load_mine, claim.session_name)
        claim.own_liveness = lambda: self.liveness
        claim.load_mine = lambda: {'claims': self.rows}
        claim.session_name = lambda: self.me
        return claim

    def __exit__(self, *a):
        claim.own_liveness, claim.load_mine, claim.session_name = self.saved
        return False


ALIVE = ('ALIVE', 'this session owns the lock (CLAUDE_PID 1)', NOW - 60)
DEAD = ('DEAD', 'pid 1 is gone', None)
UNKNOWN = ('UNKNOWN', 'liveness raised', None)

print('A. the b3 FAILURE ITSELF -- a live process on a claim past the timeout')
with Patched(ALIVE, [row(10.0)]):
    st, c, why = claim.own_claim_state()
    ok('a 10-hour claim whose process is ALIVE reads HELD -- this is the exact '
       'case that read as gone and caused seven commits under a claim I '
       'believed expired', st == 'HELD', (st, why))
    ok('...and the reason names the pid lock rather than the clock',
       'lock' in (why or ''), why)

print('\nB. THE MIRROR CASE, which raising the timeout would have broken')
with Patched(DEAD, [row(0.1)]):
    st, c, why = claim.own_claim_state()
    ok('a SIX-MINUTE-OLD claim whose process is GONE reads DEAD, expired NOW '
       'and not in 3h54 -- liveness has to cut both ways or it is just a '
       'longer timeout', st == 'DEAD', (st, why))

print('\nC. liveness UNKNOWN falls back to the timeout, in BOTH directions')
with Patched(UNKNOWN, [row(10.0)]):
    st, _c, why = claim.own_claim_state()
    ok('UNKNOWN + past the timeout -> EXPIRED', st == 'EXPIRED', (st, why))
    ok('...and says the liveness was unknown rather than implying a dead '
       'process', 'unknown' in (why or '').lower(), why)
with Patched(UNKNOWN, [row(1.0)]):
    st, _c, why = claim.own_claim_state()
    ok('UNKNOWN + inside the timeout -> HELD, so losing the registry does not '
       'invent a refusal', st == 'HELD', (st, why))

print('\nD. no row at all is NONE, which is not the same as EXPIRED')
with Patched(ALIVE, []):
    st, c, why = claim.own_claim_state()
    ok('no active row -> NONE', st == 'NONE', (st, why))
    ok('...and NONE carries no claim object to misread', c is None, c)
with Patched(ALIVE, [row(1.0, status='released')]):
    st, _c, _w = claim.own_claim_state()
    ok('a RELEASED row is not an active claim -> NONE', st == 'NONE', st)

print('\nE. the NEWEST active row is the one judged')
with Patched(ALIVE, [row(10.0), row(0.5)]):
    st, c, _w = claim.own_claim_state()
    ok('two active rows -> the most recent is judged',
       st == 'HELD' and abs(c['claimed_at_epoch'] - (NOW - 1800)) < 5,
       (st, c and c['claimed_at_epoch'] - NOW))

print('\nF. stamp_own_liveness touches MY rows and nothing else')
with Patched(ALIVE, []) as m:
    mine, theirs = row(10.0, session='cc'), row(10.0, session='hank')
    reg = row(10.0, session='cc', _registry=True)
    m.stamp_own_liveness([mine, theirs, reg])
    ok('my own row is stamped alive', mine.get('_alive') is True, mine)
    ok('...and is_active() now agrees with every other clone',
       m.is_active(mine) is True, m.is_active(mine))
    ok('ANOTHER session\'s git row is NOT stamped -- my pid says nothing about '
       'hank', '_alive' not in theirs, theirs)
    ok('a _registry row is left alone, because it already carries its own '
       'stamp and a second writer is a second answer',
       '_alive_why' not in reg or reg.get('_registry') is True, reg)

print('\nG. UNKNOWN leaves the fields ABSENT rather than writing a value')
with Patched(UNKNOWN, []) as m:
    r = row(10.0)
    m.stamp_own_liveness([r])
    ok('no _alive key is written on UNKNOWN, so is_active() keeps the timeout '
       'instead of reading a planted None as an answer', '_alive' not in r, r)
    ok('...and the row is therefore still expired at 10 hours',
       m.is_active(r) is False, m.is_active(r))

print('\nH. TEETH -- the arms above must fail without the stamp')
# ABLATION, and it is the point of this file: with stamp_own_liveness reduced to
# a no-op, arm A must go red. A green suite against the pre-fix behaviour would
# mean these arms measure nothing.
_saved = claim.stamp_own_liveness
try:
    claim.stamp_own_liveness = lambda claims: claims
    with Patched(ALIVE, [row(10.0)]):
        st, _c, _w = claim.own_claim_state()
        ok('with the stamp ablated, the 10-hour live claim goes back to '
           'EXPIRED -- so arm A is measuring the fix and not the clock',
           st == 'EXPIRED', st)
finally:
    claim.stamp_own_liveness = _saved
with Patched(ALIVE, [row(10.0)]):
    st, _c, _w = claim.own_claim_state()
    ok('and the stamp is restored afterwards, so no later arm reads a stub',
       st == 'HELD', st)

print('')
if _fail:
    print('%d failure(s)' % len(_fail))
    for f in _fail:
        print('  - %s' % f)
    sys.exit(1)
print('ALL ARMS PASS')
sys.exit(0)
