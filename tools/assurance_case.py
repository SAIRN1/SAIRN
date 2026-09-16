"""Item 5: the structured argument from Tier A claims to the evidence that exists.

    python tools/assurance_case.py
    python tools/assurance_case.py --full     # also run the slow evidence
    python tools/assurance_case.py --json
    python tools/assurance_case.py --self-check

Exit 0 when every developed goal is SUPPORTED, 1 when one is not, 2 when the
argument could not be evaluated. REPORT ONLY -- and an assurance case is an
ARGUMENT, never a proof.

── WHY A TOOL AND NOT A DOCUMENT ───────────────────────────────────────────
An assurance case written as prose is true on the day it is written. This
platform's eighth standing discipline is that NOTHING ANNOUNCES THE DAY A CHECK
STOPS TESTING ANYTHING -- so a case whose leaves are sentences rots silently and
keeps reading as assurance. Every leaf here is a COMMAND or an ARTIFACT, run or
read on each invocation, and a leaf that cannot be evaluated is reported as
COULD-NOT-RUN rather than quietly dropped.

── THE SHAPE IS GSN, AND THE PARTS THAT MATTER ARE THE UNCOMFORTABLE ONES ──
Goal / Strategy / Solution, with two node kinds this platform needs more than
the others:

  UNDEVELOPED   a goal with no evidence under it. In GSN this is a diamond, and
                it is drawn rather than omitted. A case that only shows the
                branches it can support is an advert.
  ASSUMPTION    something the argument rests on that is not itself evidenced.
                Named, so a reader can reject it.

A goal is SUPPORTED only if every child is. There is no partial credit and no
weighting: a weighted score would let a strong branch carry a weak one, and the
weak branch is the one that will be exercised.

── WHAT THIS CASE DOES NOT CLAIM ───────────────────────────────────────────
  * NOT that Tier A data is safe. It says which claims currently have evidence
    behind them and which do not, and today MOST DO NOT.
  * NOT that the evidence is sufficient. A control that fires is evidence the
    control fires; whether that control is the right one is a judgement, and
    the judgement is recorded in each leaf's `why` rather than computed.
  * NOT a certification artefact. Nothing here maps to a standard's clauses,
    and presenting it as though it did would be the compliance-adjacent
    labelling this repo already refused once when it declined to call
    mutation-derived condition coverage "MC/DC".
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN                       # noqa: E402

SLOW = 'slow'          # only evaluated under --full


def _run(cmd, timeout=180):
    """(exit_code, output) or (None, reason) when it could not run at all."""
    try:
        r = subprocess.run([sys.executable] + cmd, cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=timeout,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                    PYTHONUTF8='1'))
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return None, 'timed out after %ds' % timeout
    except Exception as e:                                       # noqa: BLE001
        return None, '%s: %s' % (type(e).__name__, e)


# ── THE EVIDENCE LEAVES ─────────────────────────────────────────────────────
# `expect` is a function of (exit_code, output) -> (bool, measured_text).
# It returns the MEASURED FIGURE as well as the verdict, so the case reports a
# number a reader can check rather than a colour.

def _exit_zero(note):
    def f(rc, out):
        return rc == 0, '%s (exit %s)' % (note, rc)
    return f


def _tier_register(rc, out):
    import re
    src = io.open(os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md'),
                  encoding='utf-8').read()
    rows = re.findall(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*([ABC])\*\*\s*\|',
                      src, re.M)
    a = sum(1 for _n, t in rows if t == 'A')
    return (rc == 0 and a > 0), '%d Tier A resources of %d tiered (checker exit %s)' % (a, len(rows), rc)


def _suite_controls(rc, out):
    import re
    m = re.search(r'(\d+) have a negative control', out)
    n = re.search(r'(\d+) suite\(s\)', out)
    if not m or not n:
        return False, 'could not parse the coverage output'
    have, total = int(m.group(1)), int(n.group(1))
    return have == total, '%d of %d suites have a negative control' % (have, total)


def _condition_cov(rc, out):
    import re
    rows = re.findall(r'^\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)\s+', out, re.M)
    if not rows:
        return False, 'no engine rows parsed'
    ops = sum(int(r[0]) for r in rows)
    killed = sum(int(r[1]) for r in rows)
    surv = sum(int(r[2]) for r in rows)
    return surv == 0, ('%d of %d operands killed, %d survived across %d engines'
                       % (killed, ops, surv, len(rows)))


def _write_path(rc, out):
    import re
    m = re.search(r'total (\d+) site\(s\) OPEN AND UNREAD', out)
    open_n = int(m.group(1)) if m else -1
    return (rc == 0 and open_n == 0), (
        'ratchet holds (exit %s); %s write site(s) still OPEN AND UNREAD'
        % (rc, open_n if open_n >= 0 else '?'))


def _register_factors(rc, out):
    import re
    m = re.search(r'contributing factors: (\d+) of (\d+) record', out)
    if not m:
        return False, 'could not parse the register output'
    have, total = int(m.group(1)), int(m.group(2))
    return rc == 0 and have == total, (
        '%d of %d records carry contributing factors (checker exit %s)'
        % (have, total, rc))


def _retry(rc, out):
    import re
    m = re.search(r'(\d+) retry construct\(s\).*?(\d+) concerning', out, re.S)
    if not m:
        return False, 'could not parse the retry output'
    return int(m.group(2)) == 0, ('%s construct(s) re-issue a remote call, %s '
                                  'without backoff or bound'
                                  % (m.group(1), m.group(2)))


ARGUMENT = {
    'goal': 'G1',
    'claim': 'Tier A resources on this platform are protected by controls that '
             'are KNOWN TO WORK -- not merely present.',
    'context': [
        'Tier A is defined per RESOURCE in docs/CRITICALITY-TIERS.md: money, '
        'regulated or protected data, or a resource whose failure has already '
        'caused a documented incident.',
        'This platform has no route from a clone to the deployed database, so '
        'every leaf below is evidence about the REPOSITORY unless it says '
        'otherwise.',
    ],
    'assumptions': [
        'A1: the tier assigned to each resource is correct. It is a judgement, '
        'hand-written, and checked for completeness but not for correctness.',
        'A2: a control that refuses a planted defect would also refuse the real '
        'one. Mutation evidence is evidence about the control, not about every '
        'defect that control might meet.',
        'A3: the repository is what is deployed. Nothing here verifies that, '
        'and the isolation-level sweep of 2026-09-15 recorded the same limit.',
    ],
    'strategy': 'S1: argue over the ways a Tier A control is known to fail on '
                'this platform -- unidentified, unreviewed, silently lost, '
                'untested, unexercised, unrecorded, unverified-when-new, and '
                'unrestorable.',
    'subgoals': [
        {'goal': 'G2',
         'claim': 'Every Tier A resource is IDENTIFIED and carries cited evidence '
                  'for its tier.',
         'evidence': [{
             'id': 'E1', 'cmd': ['tools/criticality_tier_check.py'],
             'expect': _tier_register,
             'why': 'the checker refuses a Tier A row with an empty evidence '
                    'cell, so the register cannot carry a bare label'}]},

        {'goal': 'G3',
         'claim': 'A change touching a Tier A resource RAISES A REVIEW '
                  'OBLIGATION that must be discharged.',
         'evidence': [{
             'id': 'E2', 'cmd': ['tools/tier_a_review_gate.py'],
             'expect': _exit_zero('no undischarged Tier A obligation'),
             'why': 'the gate fails closed: a register it cannot parse is '
                    'COULD NOT TELL, never an empty set'}]},

        {'goal': 'G4',
         'claim': 'A Tier A write cannot be SILENTLY LOST.',
         'evidence': [
             {'id': 'E3', 'cmd': ['tools/write_path_fault_scan.py', '--ratchet'],
              'expect': _write_path,
              'why': 'the ratchet stops the class growing. It does NOT reduce '
                     'the standing count, and those sites are recorded OPEN '
                     'AND UNREAD rather than accepted'},
             {'id': 'E4', 'cmd': ['tools/retry_policy_audit.py'],
              'expect': _retry,
              'why': 'a failed write that is never re-issued is lost, so the '
                     'retry picture is part of this goal rather than a '
                     'separate one'}]},

        {'goal': 'G5',
         'claim': 'The suites guarding Tier A are KNOWN TO CATCH a real defect.',
         'evidence': [{
             'id': 'E5', 'cmd': ['tools/suite_control_coverage.py'],
             'expect': _suite_controls,
             'why': 'a suite that has only ever been green is a suite whose '
                    'behaviour nobody knows'}]},

        {'goal': 'G6',
         'claim': 'Decisions inside Tier A engines are EXERCISED, not merely '
                  'executed.',
         'evidence': [{
             'id': 'E6', 'cmd': ['tools/condition_coverage.py'],
             'expect': _condition_cov, 'cost': SLOW,
             'why': 'negating an operand and watching the suite die is stronger '
                    'than a coverage percentage, which only proves the line ran'}]},

        {'goal': 'G7',
         'claim': 'A defect found in Tier A is RECORDED with every contributing '
                  'factor, not one labelled root cause.',
         'evidence': [{
             'id': 'E7', 'cmd': ['tools/defect_register.py', '--check'],
             'expect': _register_factors,
             'why': 'the register refuses a `root_cause` field by name and '
                    'requires `recurrence_open` on any record carrying factors'}]},

        {'goal': 'G8',
         'claim': 'A NEW Tier A control is verified against every claim it makes '
                  'before it is trusted.',
         'evidence': [{
             'id': 'E8', 'cmd': ['tools/first_article_check.py'],
             'expect': _exit_zero('every recorded inspection complete and current'),
             'why': 'the inspection is hashed against the artefact, so it stops '
                    'being evidence the day the bytes change'}]},

        {'goal': 'G9',
         'claim': 'Tier A data is RESTORABLE from backup.',
         'undeveloped': 'NO EVIDENCE REACHABLE FROM A CLONE. The nightly backup '
                        'restores what it took and runs a coherence check, which '
                        'is real -- but whether the backup reader can SEE every '
                        'Tier A table depends on a default ACL per creating '
                        'role, and the two queries that would answer it '
                        '(verify 2c and 2d in sql/backup_reader_role.sql) have '
                        'never been run. Until they are, this goal is '
                        'UNDEVELOPED and the case says so rather than borrowing '
                        'the backup job\'s green as an answer. See '
                        'docs/2026-09-15-backup-reader-default-acl-verification.md.'},

        {'goal': 'G10',
         'claim': 'The controls above run against the DEPLOYED system, not only '
                  'the repository.',
         'undeveloped': 'NO ROUTE FROM A CLONE TO THE DEPLOYED DATABASE. Every '
                        'other goal in this case is evidence about files. This '
                        'is drawn as its own goal rather than folded into a '
                        'caveat, because a caveat at the bottom of a page is '
                        'read once and an undeveloped goal is read every time.'},
    ],
}


def evaluate(argument, run_slow=False):
    rows, could_not_run = [], []
    for sg in argument['subgoals']:
        if 'undeveloped' in sg:
            rows.append({'goal': sg['goal'], 'claim': sg['claim'],
                         'verdict': 'UNDEVELOPED', 'why': sg['undeveloped'],
                         'evidence': []})
            continue
        ev_rows, all_ok = [], True
        for ev in sg['evidence']:
            if ev.get('cost') == SLOW and not run_slow:
                ev_rows.append({'id': ev['id'], 'verdict': 'NOT RUN THIS PASS',
                                'measured': 'slow evidence; use --full',
                                'why': ev['why']})
                all_ok = False
                could_not_run.append('%s: slow evidence not run (use --full)'
                                     % ev['id'])
                continue
            rc, out = _run(ev['cmd'])
            if rc is None:
                ev_rows.append({'id': ev['id'], 'verdict': 'COULD NOT RUN',
                                'measured': out, 'why': ev['why']})
                all_ok = False
                could_not_run.append('%s: %s' % (ev['id'], out))
                continue
            ok, measured = ev['expect'](rc, out)
            ev_rows.append({'id': ev['id'],
                            'verdict': 'SUPPORTS' if ok else 'DOES NOT SUPPORT',
                            'measured': measured, 'why': ev['why'],
                            'cmd': ' '.join(ev['cmd'])})
            all_ok = all_ok and ok
        rows.append({'goal': sg['goal'], 'claim': sg['claim'],
                     'verdict': 'SUPPORTED' if all_ok else 'NOT SUPPORTED',
                     'evidence': ev_rows})
    developed = [r for r in rows if r['verdict'] in ('SUPPORTED', 'NOT SUPPORTED')]
    top = ('SUPPORTED' if developed and all(r['verdict'] == 'SUPPORTED'
                                            for r in developed)
           else 'NOT SUPPORTED')
    return rows, top, could_not_run


def self_check():
    fails = []

    def ck(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            fails.append(name)

    # ── THE PARSERS, against synthetic output. Every one of these reads a
    #    number out of another tool's text, and a parser that silently returns
    #    zero would make the case report a figure nobody measured.
    ok, m = _suite_controls(1, '  152 suite(s) -- tests\n  13 have a negative control (a probe')
    ck('the suite-control parser reads BOTH numbers', not ok and '13 of 152' in m, m)
    ok, m = _suite_controls(1, 'nothing parseable here')
    ck('...and says so rather than reporting zero when it cannot parse',
       not ok and 'could not parse' in m, m)
    ok, m = _suite_controls(0, '  9 suite(s) -- x\n  9 have a negative control (a probe')
    ck('...and a fully controlled tree SUPPORTS -- the leaf can pass', ok, m)

    ok, m = _write_path(0, 'baseline recorded 2026-09-15, total 25 site(s) OPEN AND UNREAD')
    ck('the write-path parser does not call 25 open sites supported', not ok, m)
    ok, m = _write_path(0, 'baseline recorded x, total 0 site(s) OPEN AND UNREAD')
    ck('...and zero open sites SUPPORTS', ok, m)

    ok, m = _condition_cov(1, '\n  ledger               44      32       12           0   yes\n')
    ck('the condition parser sums operands and survivors',
       not ok and '32 of 44' in m and '12 survived' in m, m)
    ok, m = _condition_cov(0, '\n  ledger               10      10        0           0   yes\n')
    ck('...and a clean engine SUPPORTS', ok, m)

    ok, m = _register_factors(0, 'contributing factors: 5 of 85 record(s) carry them')
    ck('the register parser does not call 5 of 85 supported', not ok and '5 of 85' in m, m)

    ok, m = _retry(1, '  3 retry construct(s) on a remote call, 2 concerning')
    ck('the retry parser reads the concerning count', not ok and '2 without' in m, m)
    ok, m = _retry(0, '  0 retry construct(s) on a remote call, 0 concerning')
    ck('...and zero concerning SUPPORTS', ok, m)

    # ── THE ARGUMENT'S OWN SHAPE ────────────────────────────────────────
    ids = [sg['goal'] for sg in ARGUMENT['subgoals']]
    ck('every subgoal id is unique', len(set(ids)) == len(ids), ids)
    und = [sg for sg in ARGUMENT['subgoals'] if 'undeveloped' in sg]
    ck('the case DRAWS its undeveloped goals rather than omitting them',
       len(und) >= 1, len(und))
    ck('...and each one says WHY it is undeveloped, at length',
       all(len(sg['undeveloped']) > 80 for sg in und),
       [len(sg['undeveloped']) for sg in und])
    ck('every developed subgoal has at least one evidence leaf',
       all(sg.get('evidence') for sg in ARGUMENT['subgoals']
           if 'undeveloped' not in sg))
    ck('every evidence leaf names WHY it is evidence for its goal',
       all(len(str(e.get('why') or '')) > 30
           for sg in ARGUMENT['subgoals'] for e in sg.get('evidence', [])))
    ck('the argument records its ASSUMPTIONS, which are not evidenced',
       len(ARGUMENT['assumptions']) >= 3, ARGUMENT['assumptions'])

    # ── NO PARTIAL CREDIT. A weighted score would let a strong branch carry a
    #    weak one, and the weak branch is the one that gets exercised.
    fake = {'subgoals': [
        {'goal': 'X', 'claim': 'c', 'evidence': [
            {'id': 'a', 'cmd': ['-c', 'import sys;sys.exit(0)'],
             'expect': _exit_zero('ok'), 'why': 'x' * 40},
            {'id': 'b', 'cmd': ['-c', 'import sys;sys.exit(1)'],
             'expect': _exit_zero('no'), 'why': 'x' * 40}]}]}
    rows, top, _c = evaluate(fake)
    ck('one failing leaf makes its goal NOT SUPPORTED, whatever the siblings do',
       rows[0]['verdict'] == 'NOT SUPPORTED' and top == 'NOT SUPPORTED', rows)
    fake2 = {'subgoals': [{'goal': 'X', 'claim': 'c', 'evidence': [
        {'id': 'a', 'cmd': ['-c', 'import sys;sys.exit(0)'],
         'expect': _exit_zero('ok'), 'why': 'x' * 40}]}]}
    rows2, top2, _c2 = evaluate(fake2)
    ck('...and an all-passing goal IS supported, so the verdict is not constant',
       rows2[0]['verdict'] == 'SUPPORTED' and top2 == 'SUPPORTED', rows2)

    # AN UNDEVELOPED GOAL MUST NOT MAKE THE TOP CLAIM FAIL *OR* PASS by itself:
    # it is outside the supported/unsupported axis, and folding it into either
    # is how a case either cries wolf or flatters itself.
    fake3 = {'subgoals': [
        {'goal': 'X', 'claim': 'c', 'evidence': [
            {'id': 'a', 'cmd': ['-c', 'import sys;sys.exit(0)'],
             'expect': _exit_zero('ok'), 'why': 'x' * 40}]},
        {'goal': 'Y', 'claim': 'c2', 'undeveloped': 'z' * 90}]}
    rows3, top3, _c3 = evaluate(fake3)
    ck('an UNDEVELOPED goal is neither supported nor unsupported',
       top3 == 'SUPPORTED'
       and [r['verdict'] for r in rows3] == ['SUPPORTED', 'UNDEVELOPED'],
       [r['verdict'] for r in rows3])

    print('\n%d failure(s)' % len(fails))
    return 1 if fails else 0


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                            # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-check', action='store_true', dest='selfcheck')
    args = ap.parse_args(argv)

    if args.selfcheck:
        return self_check()

    started = time.time()
    try:
        rows, top, cnr = evaluate(ARGUMENT, run_slow=args.full)
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
        return EXIT_COULD_NOT_RUN

    if args.json:
        print(json.dumps({'top_goal': ARGUMENT['goal'],
                          'top_claim': ARGUMENT['claim'],
                          'top_verdict': top, 'context': ARGUMENT['context'],
                          'assumptions': ARGUMENT['assumptions'],
                          'strategy': ARGUMENT['strategy'], 'subgoals': rows,
                          'could_not_run': cnr,
                          'elapsed_s': round(time.time() - started, 1)}, indent=1))
        return 0 if top == 'SUPPORTED' else 1

    if not args.quiet:
        print('ASSURANCE CASE -- item 5, report only. AN ARGUMENT, NEVER A PROOF.')
        print('')
        print('  %s  %s' % (ARGUMENT['goal'], ARGUMENT['claim']))
        print('  VERDICT OVER THE DEVELOPED GOALS: %s' % top)
        print('')
        for c in ARGUMENT['context']:
            print('  CONTEXT  %s' % c)
        print('')
        print('  %s' % ARGUMENT['strategy'])
        print('')
        for r in rows:
            print('  %-4s %-14s %s' % (r['goal'], r['verdict'], r['claim']))
            if r['verdict'] == 'UNDEVELOPED':
                print('        %s' % r['why'])
            for e in r['evidence']:
                print('        %-4s %-18s %s' % (e['id'], e['verdict'],
                                                 e['measured']))
                print('             %s' % e['why'])
            print('')
        print('  ASSUMPTIONS -- not evidenced, and named so they can be rejected:')
        for a in ARGUMENT['assumptions']:
            print('    %s' % a)
        print('')
        if cnr:
            print('  COULD NOT RUN (%d) -- NOT a pass:' % len(cnr))
            for c in cnr:
                print('    ? %s' % c)
            print('')
        print('  A GOAL IS SUPPORTED ONLY IF EVERY CHILD IS. There is no partial')
        print('  credit and no weighting: a weighted score lets a strong branch')
        print('  carry a weak one, and the weak branch is the one that gets')
        print('  exercised. An UNDEVELOPED goal is neither supported nor')
        print('  refuted -- it is drawn because a case that shows only the')
        print('  branches it can support is an advert.')
    return 0 if top == 'SUPPORTED' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
