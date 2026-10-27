#!/usr/bin/env python3
# OWNER: cc
"""The PRESENCE PASSED AS PROOF checklist, as code a stress tool must satisfy.

    python tools/presence_proof.py --checklist   # print the checklist
    python tools/presence_proof.py --fixtures    # criteria lock

Named in cc b55 (docs/defect-density-register.json, four records). A check
confirms that a thing EXISTS -- a case at a cite, totals that match, a
signature string, a date in a field -- and the app shows that as the thing
being RIGHT. A stress test aimed at that shape fails in its own way unless it
is planned. If it only asserts that the app RAN, a false "Reconciled" or
"VERIFIED" passes it silently.

USE: a stress tool builds a list of Scenario(...) and calls `require_plan()`
BEFORE it drives anything. The plan is refused (exit 2, COULD NOT RUN) unless
every item on the checklist below is answered. After driving, `verdict()` turns
each observation into PASS / FAIL / CONTROL-OK / CONTROL-FAIL by the plan's own
operational definitions, not by an exit code.
"""
import sys

CRITERIA_VERSION = '2026-10-27.1'

CHECKLIST = (
    ('CLAIM', 'Name the exact positive status the app shows -- the literal word, '
              'badge or value ("Paid", "Signed", "COMPLIANT", "100%"). A test that '
              'cannot say what the user would read cannot tell a false one from a true one.'),
    ('TRUTH', 'State the real fact the claim is about, for this input, in one sentence '
              '-- and why the input makes it false ("the payment record is $1, the '
              'invoice is $5,000").'),
    ('FAIL MEANS', 'Write FAIL operationally, before driving: "the app shows <CLAIM> '
                   'while <TRUTH>". Not "exit 1", not "an exception". If the app CRASHES '
                   'rather than showing the claim, that is a separate finding and never a PASS.'),
    ('DETECTOR', 'Read the claim off what the USER sees or what is STORED and later shown '
                 '-- the rendered text, the persisted status field -- not off an internal '
                 'return value the screen does not use.'),
    ('CONTROL', 'Include at least one input where the claim is TRUE and must be shown. A '
                'tool whose only outcome is "not shown" cannot tell a working check from a '
                'broken harness. A control that fails makes the run COULD NOT RUN.'),
    ('ABLATION', 'Name one change that should turn a PASS into a FAIL, and run it once. '
                 'A PASS nobody has seen fail is a presence passed as proof one level up.'),
    ('UNSEEN', 'Ask what the check never SEES -- an input shape it does not parse, a row '
               'past a slice, a field it never reads. An unseen item that reaches the user '
               'unflagged is a FAIL, not "not applicable".'),
    ('SCOPE', 'Say what is REAL (driven as shipped) and what is a FIXTURE or STUB, in the '
              'tool\'s header and in its output.'),
)


class Scenario(object):
    """One stress input.

    expect_claim -- True for a CONTROL (the claim is true and must be shown);
                    False for a stress input (the claim must NOT be shown).
    detect(obs)  -- returns True when the app SHOWS `claim`, read per DETECTOR.
    """

    def __init__(self, sid, claim, truth, fail_means, detect, expect_claim=False, unseen=None):
        self.sid, self.claim, self.truth = sid, claim, truth
        self.fail_means, self.detect = fail_means, detect
        self.expect_claim, self.unseen = expect_claim, unseen


def plan_problems(scenarios, ablation, scope):
    """[] when the plan answers the checklist. Pure."""
    bad = []
    if not scenarios:
        return ['no scenarios']
    for s in scenarios:
        # A CONTROL needs no FAIL MEANS: its failure is defined once, below, as
        # "the true claim was not shown".
        for field in ('claim', 'truth') + (() if s.expect_claim else ('fail_means',)):
            if not str(getattr(s, field) or '').strip():
                bad.append('%s: %s is empty' % (s.sid, field.upper()))
        if not callable(s.detect):
            bad.append('%s: no DETECTOR' % s.sid)
        fm = str(s.fail_means or '').lower()
        if not s.expect_claim and ('exit' in fm.split()[:2] or fm.strip() in ('fail', 'error')):
            bad.append('%s: FAIL MEANS is an exit code, not what the user sees' % s.sid)
        if not s.expect_claim and s.claim and s.claim.lower() not in fm:
            bad.append('%s: FAIL MEANS does not name the claim %r' % (s.sid, s.claim))
    if not any(s.expect_claim for s in scenarios):
        bad.append('no CONTROL: no scenario where the claim is true and must be shown')
    if not str(ablation or '').strip():
        bad.append('no ABLATION named')
    if not str(scope or '').strip():
        bad.append('no SCOPE statement (what is real, what is a fixture)')
    return bad


def require_plan(scenarios, ablation, scope):
    bad = plan_problems(scenarios, ablation, scope)
    if bad:
        print('PLAN REFUSED -- the presence-proof checklist is not answered, so a false '
              'positive could pass silently. COULD NOT RUN:')
        for b in bad:
            print('  ! ' + b)
        sys.exit(2)


def verdict(scenario, obs):
    """-> (verdict, reason) by the scenario's own operational definition."""
    if isinstance(obs, dict) and obs.get('crash'):
        return ('CONTROL-FAIL' if scenario.expect_claim else 'FAIL',
                'CRASHED (%s) -- never a pass' % obs['crash'])
    shown = bool(scenario.detect(obs))
    if scenario.expect_claim:
        return ('CONTROL-OK', 'shows %r as it should' % scenario.claim) if shown \
            else ('CONTROL-FAIL', 'did NOT show %r on a true input' % scenario.claim)
    if shown:
        return 'FAIL', scenario.fail_means
    return 'PASS', 'does not show %r' % scenario.claim


def run_fixtures():
    ok = Scenario('ok', 'Paid', 'it is paid', '', lambda o: True, expect_claim=True)
    st = Scenario('s', 'Paid', '$1 of $5000 received', 'the app shows Paid while $1 of $5000 is received',
                  lambda o: o.get('status') == 'Paid')
    cases = [
        (plan_problems([ok, st], 'x', 'y') == [], 'a full plan is accepted'),
        (any('CONTROL' in b for b in plan_problems([st], 'x', 'y')), 'a plan with no control is refused'),
        (any('ABLATION' in b for b in plan_problems([ok, st], '', 'y')), 'a plan with no ablation is refused'),
        (any('exit code' in b for b in plan_problems(
            [ok, Scenario('e', 'Paid', 't', 'exit 1', lambda o: 0)], 'x', 'y')),
         'FAIL MEANS of "exit 1" is refused'),
        (any('does not name the claim' in b for b in plan_problems(
            [ok, Scenario('n', 'Paid', 't', 'it is wrong', lambda o: 0)], 'x', 'y')),
         'FAIL MEANS that does not name the claim is refused'),
        (verdict(st, {'status': 'Paid'})[0] == 'FAIL', 'the claim shown on a false input is FAIL'),
        (verdict(st, {'status': 'Partial'})[0] == 'PASS', 'not shown is PASS'),
        (verdict(st, {'crash': 'TypeError'})[0] == 'FAIL', 'a crash is a FAIL, never a PASS'),
        (verdict(Scenario('c', 'Paid', 't', '', lambda o: o.get('status') == 'Paid', True),
                 {'status': 'x'})[0] == 'CONTROL-FAIL', 'a control not shown is CONTROL-FAIL'),
        (any('TRUTH' in b for b in plan_problems(
            [ok, Scenario('t', 'Paid', '', 'shows Paid', lambda o: 0)], 'x', 'y')),
         'a stress input with no TRUTH is refused'),
    ]
    return [why for good, why in cases if not good], len(cases)


def main(argv):
    bad, n = run_fixtures()
    if bad:
        print('CRITERIA LOCK FAILED:')
        for b in bad:
            print('  ! ' + b)
        return 2
    print('PRESENCE PASSED AS PROOF -- criteria lock %s: %d/%d fixtures' % (CRITERIA_VERSION, n, n))
    if '--checklist' in argv or not argv:
        print('')
        print('Answer every item BEFORE driving a stress test:')
        for i, (k, v) in enumerate(CHECKLIST, 1):
            print('  %d. %-10s %s' % (i, k, v))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
