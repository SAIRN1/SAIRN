"""tests/claims/run_own_claim_overlap_probe.py

Run:  python tests/claims/run_own_claim_overlap_probe.py

THE GUARD THE OTHER TWO ARE SPECIAL CASES OF, DRIVEN AGAINST THE TWO REAL
INCIDENTS RATHER THAN AGAINST A CONSTRUCTED ONE.

Every collision check in sairn_claim.py opens `if c.get('session') == me:
continue`. The matcher has therefore never been pointed at the claims of the
session running it, and the only things standing between one session and two
claims for one piece of work were:

    `same`   an exact (subject, task) byte-match          -- befb65e3
    `stuck`  same subject AND the earlier claim UNPUBLISHED -- a50aaf60

Both live recurrences walked past both. Section 1 drives the tool with THE
ACTUAL STRINGS from each, taken from `.claude/claims/` rather than invented:

  fourth  same subject, earlier claim already on origin, task retyped
  cc      DIFFERENT subject, different session entirely from `stuck`'s reach

── WHAT THIS FILE IS DEFENDING, WHICH IS NOT "DOES IT BLOCK" ──────────────
A gate that refuses everything is trivially green on section 1 and useless.
The value is in the LINE: refuse when two strings describe the same thing,
allow when they merely sit in the same app, and never block on a claim the
tool's own expiry says is no longer held. Sections 2 and 3 are the arms that
would go red on an over-eager guard, and they are the ones worth keeping.

── AND SECTION 4, THE REGRESSION THAT WOULD BE INVISIBLE ──────────────────
The retry path -- re-running an identical claim after a failed push -- is the
one case where finding your own matching claim must NOT refuse. It must
republish. A guard inserted before it would turn the documented recovery
procedure into a refusal, and the only symptom would be sessions unable to
recover from a failed push, which reads as a network problem.

── THE SABOTAGE SECTION VERIFIES ITS OWN MUTATION APPLIED ─────────────────
tools/sabotage_control_check.py measured 23 of 39 controls on this platform
never checking that their sabotage landed. Each mutation below asserts, in
order: the anchor is found EXACTLY ONCE, the copy DIFFERS, and the mutated tool
then FAILS an arm above. tools/sairn_claim.py is never written to; the closing
section asserts that.
"""
# REQUIREMENT: sairn_claim.py refuses a second claim on work the same session
#   already holds, under any subject and any wording, using the same matcher it
#   applies to other sessions -- and does not refuse merely-related work, an
#   expired claim, or the identical-retry republish path
#
import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUBJECT = os.path.join(REPO, 'tools', 'sairn_claim.py')
sys.path.insert(0, os.path.join(REPO, 'tools'))

FAIL = []


def ok(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


def load(path=SUBJECT, name='sairn_claim_under_test'):
    """Import a COPY of the tool by path, so a mutated build can be driven
    exactly as the real one is rather than by reimplementing its logic."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def harness(mod, session='cc'):
    """The real cmd_claim, against a throwaway claim dir.

    Only save_mine is stubbed, and only its PUBLISH half: these arms are about
    the guard, and the git behaviour is already covered by
    tests/claims/run_push_verify_probe.py. Stubbing more would let a guard that
    never runs pass.
    """
    tmp = tempfile.mkdtemp(prefix='own-claim-probe-')
    mod.CLAIM_DIR = tmp
    mod.session_name = lambda: session
    path = os.path.join(tmp, session + '.json')

    def fake_save(doc, message, push):
        io.open(path, 'w', encoding='utf-8').write(json.dumps(doc))
        return True
    mod.save_mine = fake_save
    return tmp, path


def claim(mod, path, subject, task, seeded):
    io.open(path, 'w', encoding='utf-8').write(
        json.dumps({'session': mod.session_name(), 'claims': seeded}))
    args = argparse.Namespace(subject=subject, task=task.split(),
                              no_push=True, no_fetch=True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.cmd_claim(args)
    after = json.load(io.open(path, encoding='utf-8'))['claims']
    return rc, len(after), buf.getvalue()


def held(mod, session, subject, task, age_h=0.0):
    t = mod.now() - age_h * 3600
    return {'id': '%s-seed' % session, 'session': session, 'subject': subject,
            'task': task, 'claimed_at': mod.iso(t), 'claimed_at_epoch': t,
            'status': 'active', 'released_at': None}


# ── THE TWO REAL INCIDENTS, VERBATIM ──────────────────────────────────────
# Read out of the record rather than retyped here, so an arm cannot drift into
# testing a string nobody ever claimed.
CC_HELD = ('tier-a-discharge-and-exports',
           'discharge mechanism, export_coverage label plus pin, alf and mech '
           'export registries')
CC_RETYPED = ('cc',
              'tier a review gate single write point, export_coverage_check '
              'sairnvet label and pin, alf_staff_credentials and '
              'mech_credentials export registries, svExportControlled csv test')
FOURTH_HELD = ('fourth',
               'LAW_RECONCILE_ROLES missing role mapping, sd-agent callClaude '
               'loop breaker, G5 controls, G7 factors, rebase resolve tool')
FOURTH_RETYPED = ('fourth',
                  'rebase resolve semantic merge for the two json registers')


def run_arms(mod, label=''):
    """Every behavioural arm, as a dict of name -> bool. Returned rather than
    printed so the sabotage section can re-run the whole set against a mutated
    build and say WHICH arm died."""
    r = {}

    tmp, path = harness(mod, 'cc')
    try:
        rc, n, out = claim(mod, path, CC_RETYPED[0], CC_RETYPED[1],
                           [held(mod, 'cc', *CC_HELD)])
        r['cc incident: different subject, retyped task -> REFUSED'] = (
            rc == 3 and n == 1)
        r['cc incident: and NOTHING was appended'] = n == 1
        r['cc incident: the reason names the overlap'] = 'overlaps on' in out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    tmp, path = harness(mod, 'fourth')
    try:
        rc, n, out = claim(mod, path, FOURTH_RETYPED[0], FOURTH_RETYPED[1],
                           [held(mod, 'fourth', *FOURTH_HELD)])
        r['fourth incident: same subject, PUBLISHED earlier claim -> REFUSED'] = (
            rc == 3 and n == 1)
        r['fourth incident: overlap is the shared phrase, not the subject'] = (
            'rebase resolve' in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── THE ARMS THAT AN OVER-EAGER GUARD FAILS ──────────────────────────
    tmp, path = harness(mod, 'cc')
    try:
        # Two real, distinct pieces of work in one app, both genuinely held at
        # once by this session on 2026-09-16. Must be ALLOWED.
        rc, n, out = claim(
            mod, path, 'sv-controlled-export',
            'sairnvet controlled substance register export machinery',
            [held(mod, 'cc', 'sv-audit-log-retrievability',
                  'sairnvet dosing audit trail panel reader')])
        r['same app only -> ALLOWED'] = rc == 0 and n == 2
        r['...and said out loud rather than silently permitted'] = 'same app' in out

        rc, n, out = claim(mod, path, 'sairnroofing-research',
                           'worldwide competitive gap research pass',
                           [held(mod, 'cc', *CC_HELD)])
        r['unrelated work -> ALLOWED, and silent'] = (
            rc == 0 and n == 2 and 'already hold' not in out)

        # STALE_HOURS is 4. A claim nobody released is one this tool already
        # treats as not held; blocking on it would lock the session out for
        # ever over a row it forgot to close.
        rc, n, out = claim(mod, path, 'cc',
                           'alf_staff_credentials and mech_credentials export '
                           'registries, plus pin',
                           [held(mod, 'cc', *CC_HELD, age_h=5.0)])
        r['an EXPIRED own claim does NOT block'] = rc == 0 and n == 2

        # ── THE REGRESSION NOBODY WOULD SEE ──────────────────────────────
        # Identical re-run after a failed push is the documented recovery. It
        # must take the RETRY path and republish, not the refusal.
        same = held(mod, 'cc', 'cc', 'item 92 functional core imperative shell')
        rc, n, out = claim(mod, path, 'cc',
                           'item 92 functional core imperative shell', [same])
        r['identical retry still takes the RETRY path, not the refusal'] = (
            'RETRY of the same claim' in out and n == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return r


print('1-4. the guard, driven against the two real incidents and the three '
      'cases it must NOT block')
BASE = load()
base_arms = run_arms(BASE)
for name, passed in base_arms.items():
    ok(name, passed)

print('\n5. the tiering is a MEASUREMENT, not a preference')
# block_reason's first rule is `same subject`. Dropping it for the self case is
# the difference between 24 refusals and 33, and the extra nine were unrelated
# work sharing only a session-name subject. Pinned so a later "simplification"
# that passes the subject through is caught here rather than in the record.
ok('the subject is NOT consulted for a self-overlap',
   BASE.self_overlap('field quote wiring, check5 exemptions',
                     'supplier lead time and job risk engine') == (None, None),
   'two unrelated tasks collided -- the subject rule is back in')
ok('a shared identifier refuses',
   BASE.self_overlap('sv_controlled witnessing lock', 'parity over sv_controlled')[1] == 'refuse')
ok('a shared phrase refuses',
   BASE.self_overlap('G7 factors and rebase resolve tool',
                     'rebase resolve semantic merge')[1] == 'refuse')
ok('a shared APP only reports',
   BASE.self_overlap('sairnvet dose audit', 'sairnvet controlled export')[1] == 'report')
ok('nothing shared is neither',
   BASE.self_overlap('stonedesk field quote', 'sairnlaw deadline seed')[1] is None)

print('\n6. `audit` counts the shape that recurred, not only the one that was '
      'fixed')
# It reported ZERO after the guards on 2026-09-16 and was right on its own
# definition -- exact (session, subject, task) groups -- while the defect was
# recurring in two clones in the form that definition cannot see.
# A SECOND, CLEAN IMPORT. run_arms() repoints CLAIM_DIR at throwaway temp dirs
# and deletes them, so BASE can no longer see the real record -- reusing it here
# read ZERO claims and the arm below passed nothing while looking green on the
# first draft. Caught by the arm asserting the two live incidents are present.
FRESH = load(name='sairn_claim_record_read')
claims = FRESH.load_all(from_origin=False)
pairs = FRESH.same_work_pairs(claims)
ok('the record itself was readable -- zero claims is NOT a clean audit',
   len(claims) > 100, '%d claims read from %s' % (len(claims), FRESH.CLAIM_DIR))
ok('the real record yields same-work pairs the exact count misses',
   len(pairs) > 0, 'found %d' % len(pairs))
sessions = {p[0] for p in pairs}
ok('...from more than one session, so it is not one agent\'s habit',
   len(sessions) >= 2, sorted(sessions))
ok('...and BOTH live incidents are among them',
   any('rebase resolve' in (p[3] or '') for p in pairs)
   and any('alf pin' in (p[3] or '') for p in pairs),
   sorted({p[3] for p in pairs}))
# Concurrency is required, or the count grows for ever as a session legitimately
# revisits a subject weeks later.
ok('a pair NOT held at the same time is not counted',
   FRESH.same_work_pairs([
       {'session': 'x', 'subject': 'a', 'task': 'rebase resolve tool',
        'claimed_at_epoch': 1000, 'released_at': None, 'status': 'released'},
       {'session': 'x', 'subject': 'b', 'task': 'rebase resolve merge',
        'claimed_at_epoch': 1000 + 99 * 3600, 'released_at': None,
        'status': 'active'}]) == [],
   'a claim from four days later counted as a duplicate')

print('\n7. SABOTAGE -- each mutation is proved to have applied, then proved to '
      'take an arm red')
MUTATIONS = [
    ('the self-overlap guard is removed from cmd_claim',
     '    mine = my_active_overlaps(doc, task)',
     '    mine = []'),
    ('the guard refuses nothing -- every verdict demoted to a report',
     "    return reason, ('report' if reason.startswith('same app') else 'refuse')",
     "    return reason, 'report'"),
    ('the subject is passed back into the self matcher',
     "    reason = block_reason('', mine_task, '', their_task)",
     '    reason = block_reason(mine_task, mine_task, their_task, their_task)'),
    ('an expired claim is treated as held',
     '        if not is_active(c):\n            continue\n        reason, kind = self_overlap(task, c.get(\'task\'))',
     '        if c.get(\'status\') != \'active\':\n            continue\n        reason, kind = self_overlap(task, c.get(\'task\'))'),
]
src = io.open(SUBJECT, encoding='utf-8', newline='').read()
before_hash = hashlib.sha256(src.encode('utf-8')).hexdigest()
tmpdir = tempfile.mkdtemp(prefix='own-claim-sabotage-')
try:
    for i, (label, anchor, replacement) in enumerate(MUTATIONS):
        n = src.count(anchor)
        if n != 1:
            ok('%s -- anchor found exactly once' % label, False,
               'found %d times; this arm tests NOTHING until the anchor is '
               'updated' % n)
            continue
        mutated = src.replace(anchor, replacement)
        ok('%s -- the sabotage actually changed the file' % label, mutated != src)
        p = os.path.join(tmpdir, 'mut%d.py' % i)
        io.open(p, 'w', encoding='utf-8', newline='').write(mutated)
        try:
            arms = run_arms(load(p, 'mutant%d' % i))
            dead = sorted(k for k, v in arms.items() if not v)
        except Exception as e:                       # noqa: BLE001
            dead = ['(the mutated tool raised: %s)' % e]
        ok('%s -- an arm above goes RED' % label, bool(dead),
           'the mutated tool passed every arm, so nothing above is defending '
           'this')
        if dead:
            print('           killed: ' + '; '.join(d[:70] for d in dead[:3]))
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

ok('tools/sairn_claim.py was never written to by this probe',
   hashlib.sha256(io.open(SUBJECT, encoding='utf-8', newline='').read()
                  .encode('utf-8')).hexdigest() == before_hash)

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
