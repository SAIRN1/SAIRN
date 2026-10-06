#!/usr/bin/env python
"""hover2_hardfail_score.py -- a batch's overall grade is capped by its
WORST star-flagged finding, never averaged against how many other items
passed. ONE real hit in a hard-fail category caps the whole batch,
regardless of pass count -- this is deliberate, not a bug: a credential-
deactivation bypass found alongside fifty clean checks is not "98% clean,"
it is "FAIL, with fifty items of context."

GOALS: star-flagged items (security, data integrity, irreversible
operations) cap the batch result regardless of the rest; the report names
the downgrade rule applied; a claimed-but-unevidenced control scores as a
hard-fail hit, not a pass.
NON-GOALS: not a general test-result aggregator -- only the three named
hard-fail categories get cap power; everything else is context. Not a
severity SCALE (no "medium"/"low" weighting) -- the whole design is that
averaging is the failure mode being refused.
ALTERNATIVES CONSIDERED: a weighted/averaged score (e.g. 98% -> "mostly
PASS") -- rejected outright, that is the exact failure this tool exists
to prevent (CLAUDE.md's own naming: a batch is not "98% clean" with one
open auth bypass). A longer list of hard-fail categories -- rejected: the
three below are chosen because "mostly fine" is not a meaningful sentence
for any one of them; stretching the list to catch more findings makes the
cap fire so often it stops meaning anything, the same failure class as an
alarm threshold tuned to always trip.
CROSS-CUTTING: pure function over a JSON list this role supplies; no git,
no subprocess, no network. Read-only, deterministic, no dependency on any
build-agent tool.

THE THREE HARD-FAIL CATEGORIES:

  DATA_LOSS      -- a write that can silently destroy or overwrite data
                    with no recovery path.
  AUTH_BYPASS     -- an unauthorized role or session reaches data or an
                    action a gate was supposed to refuse. Examples this
                    platform: employee_id case-sensitivity (a deactivated
                    credential keeps authenticating under a case-variant
                    name); alf_compliance_rules/evaluate (#894, any role
                    reaches a full staff roster a sibling branch
                    correctly restricts); alf_billing/derive_charges
                    (this role's own seq635, a billing-only role reads
                    real medication names through a second door).
  IRREVERSIBLE_WRITE -- a write with no audit trail and no undo once
                    committed, distinct from outright data loss: the data
                    persists, but WHAT HAPPENED to it cannot be
                    reconstructed afterward.

UNEVIDENCED-CONTROL RULE: a finding whose verdict is "PASS" but which
carries no evidence field (or an empty one) in a hard-fail category is
NOT treated as a real pass -- it is scored as a hit, same as OPEN, with
its own distinct reason text ("claimed PASS, no evidence cited"). A
"PASS" with a real evidence string (a command, a citation, a seq number)
is the only thing that clears a hard-fail category. This is the same
discipline this role already applies to every other finding this
session: a claim is not a fact until checked, and "I say it passed" with
nothing behind it is not a check.

USAGE:
    python hover2_hardfail_score.py --score findings.json
    python hover2_hardfail_score.py --selftest

findings.json: a JSON list of {"id": str, "category": str|null, "verdict":
"PASS"|"OPEN"|"FAIL", "evidence": str|null}. category is one of
DATA_LOSS, AUTH_BYPASS, IRREVERSIBLE_WRITE, or null/omitted for anything
else. evidence is required for a "PASS" verdict to count in a hard-fail
category -- omit or leave empty to test the unevidenced-control rule.
"""
import argparse
import json
import sys

HARD_FAIL_CATEGORIES = ('DATA_LOSS', 'AUTH_BYPASS', 'IRREVERSIBLE_WRITE')


def score(findings):
    """(grade, fired_rule_or_None, reasons) -- never averages a hard-fail
    category away. fired_rule is None only when no finding both carries a
    hard-fail category AND (has an open/failing verdict, OR a PASS with no
    evidence). A hard-fail category with verdict PASS AND real evidence
    does not cap anything; the cap is for a REAL open hit or an unproven
    claim, never for a genuinely-closed, evidenced control."""
    hits = []
    for f in findings:
        if f.get('category') not in HARD_FAIL_CATEGORIES:
            continue
        verdict = f.get('verdict')
        if verdict in ('OPEN', 'FAIL'):
            hits.append((f, verdict))
        elif verdict == 'PASS' and not (f.get('evidence') or '').strip():
            hits.append((f, 'UNEVIDENCED-PASS'))
    total = len(findings)
    passed = len([f for f in findings if f.get('verdict') == 'PASS'])
    if hits:
        cats = sorted(set(h[0]['category'] for h in hits))
        reasons = []
        for f, why in hits:
            if why == 'UNEVIDENCED-PASS':
                reasons.append('%s: %s (claimed PASS, no evidence cited -- scored as a hit)'
                               % (f['category'], f['id']))
            else:
                reasons.append('%s: %s (%s)' % (f['category'], f['id'], why))
        return ('FAIL -- CAPPED BY HARD-FAIL RULE', ','.join(cats), reasons)
    return ('%d/%d passed, no hard-fail category hit' % (passed, total), None, [])


def do_score(args):
    try:
        with open(args.score, encoding='utf-8') as fh:
            findings = json.load(fh)
    except (OSError, ValueError) as e:
        print('COULD NOT RUN: could not read/parse %s: %s' % (args.score, e))
        return 2
    grade, fired, reasons = score(findings)
    print('GRADE: %s' % grade)
    if fired:
        print('RULE FIRED: %s' % fired)
        for r in reasons:
            print('  - %s' % r)
    else:
        print('RULE FIRED: none')
    return 0


def selftest():
    cases = 0
    failed = 0

    def case(label, ok):
        nonlocal cases, failed
        cases += 1
        print(('  ok   ' if ok else '  FAIL ') + label)
        if not ok:
            failed += 1

    # 1. All PASS, no hard-fail category present -> clean grade.
    g, fired, _r = score([{'id': 'a', 'category': None, 'verdict': 'PASS'},
                          {'id': 'b', 'category': None, 'verdict': 'PASS'}])
    case('all-pass, no category, reports clean with no rule fired',
        fired is None and 'no hard-fail category hit' in g)

    # 2. 49 PASS + 1 AUTH_BYPASS OPEN -> FAIL, capped, not "98% pass".
    findings = [{'id': 'p%d' % i, 'category': None, 'verdict': 'PASS'} for i in range(49)]
    findings.append({'id': 'employee_id_auth', 'category': 'AUTH_BYPASS', 'verdict': 'OPEN'})
    g, fired, reasons = score(findings)
    case('49 passes + 1 open AUTH_BYPASS caps the batch at FAIL, not averaged',
        g.startswith('FAIL') and fired == 'AUTH_BYPASS' and len(reasons) == 1)

    # 3. A hard-fail CATEGORY with verdict PASS AND real evidence does NOT cap.
    g, fired, _r = score([{'id': 'employee_id_auth', 'category': 'AUTH_BYPASS',
                          'verdict': 'PASS', 'evidence': 'node test.js, 6/6 passed, exit 0'}])
    case('a hard-fail category whose verdict is PASS WITH evidence does not cap the batch',
        fired is None)

    # 4. TWO different hard-fail categories open at once -> both named, not just one.
    findings = [
        {'id': 'x', 'category': 'DATA_LOSS', 'verdict': 'OPEN'},
        {'id': 'y', 'category': 'IRREVERSIBLE_WRITE', 'verdict': 'FAIL'},
    ]
    g, fired, reasons = score(findings)
    case('two simultaneous hard-fail categories are BOTH named, not just the first',
        fired == 'DATA_LOSS,IRREVERSIBLE_WRITE' and len(reasons) == 2)

    # 5. A non-hard-fail category with verdict OPEN does NOT cap (not stretched to catch it).
    g, fired, _r = score([{'id': 'z', 'category': 'COSMETIC', 'verdict': 'OPEN'}])
    case('an open finding OUTSIDE the three hard-fail categories does not cap',
        fired is None)

    # 6. NEW: a hard-fail category claimed PASS with NO evidence scores as a hit, not a pass.
    g, fired, reasons = score([{'id': 'w', 'category': 'AUTH_BYPASS', 'verdict': 'PASS',
                               'evidence': ''}])
    case('a claimed PASS with empty evidence in a hard-fail category caps the batch',
        g.startswith('FAIL') and fired == 'AUTH_BYPASS'
        and 'no evidence cited' in reasons[0])

    # 7. Same as 6 but evidence key omitted entirely (not just empty) -- same result.
    g, fired, reasons = score([{'id': 'w2', 'category': 'DATA_LOSS', 'verdict': 'PASS'}])
    case('a claimed PASS with the evidence key OMITTED is treated the same as empty',
        g.startswith('FAIL') and fired == 'DATA_LOSS')

    print('')
    print('%d case(s), %d failed' % (cases, failed))
    return 1 if failed else 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--score')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.score:
        return do_score(args)
    sys.stderr.write('nothing to do -- pass --score <file> or --selftest\n')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
