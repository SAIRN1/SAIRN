#!/usr/bin/env python
"""hover_hardfail_cap.py -- a general-purpose hard-fail severity cap for any
scored item list (SOC 2-style control results, a batch's own findings, a
review checklist). Own prefix, own location. Built 2026-10-07 (H1 batch P,
item 8).

THE RULE, STATED PLAINLY: an average score is not the final verdict. Any
item marked CRITICAL (security, data integrity, or an irreversible
operation) that is not fully passing CAPS THE WHOLE RESULT AT FAIL,
regardless of how high every other item scored -- a 95% average with one
failing critical item is a FAIL, never a rounded-up PASS. An unevidenced
control (claimed but with no real evidence attached) scores 0 for that
item, independent of the cap -- a claim with nothing behind it is worth
nothing, not partial credit for plausibility.

This generalizes hover_hardfail_severity_scorer.py's own keyword-based cap
(built for scoring THIS role's own hover_log.py batches specifically) to
any scored item list with an explicit severity/evidence shape -- a
different, broader tool, not a replacement for that one.

INPUT SHAPE: a list of dicts, each:
  {'name': str, 'score': float in [0, 100], 'critical': bool, 'evidenced': bool}
'evidenced' means a real, checkable basis for the score exists (a command
run, a file read, a captured exit code) -- not merely asserted.

OUTPUT: {'average': float, 'verdict': 'PASS'|'FAIL',
         'downgrade_rule': str or None, 'items': [...with any score-0
         overrides applied...]}
"""
import sys


def score_items(items):
    """items: list of {'name', 'score', 'critical', 'evidenced'}.
    Returns the full result dict described in the module docstring."""
    scored = []
    for it in items:
        name = it['name']
        score = it['score']
        critical = bool(it.get('critical', False))
        evidenced = bool(it.get('evidenced', True))
        overridden = False
        if not evidenced:
            score = 0
            overridden = True
        scored.append({'name': name, 'score': score, 'critical': critical,
                        'evidenced': evidenced, 'score_overridden_to_zero': overridden})

    average = sum(s['score'] for s in scored) / len(scored) if scored else 0.0

    # A critical item "not fully passing" -- score < 100 -- caps the whole
    # result at FAIL, regardless of the average. The FIRST such item found
    # is named as the downgrade rule (deterministic order: list order), so
    # a report never shows a bare FAIL with no named reason.
    downgrade_rule = None
    verdict = 'PASS'
    for s in scored:
        if s['critical'] and s['score'] < 100:
            verdict = 'FAIL'
            downgrade_rule = ('CAPPED BY CRITICAL ITEM: %r scored %s%s (average was %.1f)'
                               % (s['name'], s['score'],
                                  ' -- UNEVIDENCED, forced to 0' if s['score_overridden_to_zero'] else '',
                                  average))
            break

    return {'average': average, 'verdict': verdict, 'downgrade_rule': downgrade_rule, 'items': scored}


def _selftest():
    ok = 0
    total = 0

    total += 1
    r1 = score_items([
        {'name': 'a', 'score': 100, 'critical': False, 'evidenced': True},
        {'name': 'b', 'score': 100, 'critical': False, 'evidenced': True},
    ])
    if r1['verdict'] == 'PASS' and r1['downgrade_rule'] is None:
        ok += 1
        print('  ok   all-clean, no critical items -> PASS, no downgrade rule')
    else:
        print('  FAIL expected PASS/None, got %r' % r1)

    total += 1
    # THE REQUIRED CASE: a high average that must still FAIL.
    r2 = score_items([
        {'name': 'security-gate', 'score': 10, 'critical': True, 'evidenced': True},
        {'name': 'b', 'score': 100, 'critical': False, 'evidenced': True},
        {'name': 'c', 'score': 100, 'critical': False, 'evidenced': True},
        {'name': 'd', 'score': 100, 'critical': False, 'evidenced': True},
        {'name': 'e', 'score': 100, 'critical': False, 'evidenced': True},
    ])
    if r2['average'] >= 80 and r2['verdict'] == 'FAIL' and 'security-gate' in r2['downgrade_rule']:
        ok += 1
        print('  ok   HIGH AVERAGE (%.1f) STILL FAILS: one failing critical item caps the result, named in the rule -- %s'
              % (r2['average'], r2['downgrade_rule']))
    else:
        print('  FAIL expected average>=80 and FAIL with security-gate named, got %r' % r2)

    total += 1
    r3 = score_items([
        {'name': 'data-integrity-check', 'score': 100, 'critical': True, 'evidenced': False},
        {'name': 'b', 'score': 100, 'critical': False, 'evidenced': True},
    ])
    if (r3['verdict'] == 'FAIL' and r3['items'][0]['score'] == 0
            and r3['items'][0]['score_overridden_to_zero']
            and 'UNEVIDENCED' in r3['downgrade_rule']):
        ok += 1
        print('  ok   an unevidenced CRITICAL control scores 0 (not its claimed 100) and caps the result, named as unevidenced')
    else:
        print('  FAIL expected FAIL/score 0/UNEVIDENCED named, got %r' % r3)

    total += 1
    r4 = score_items([
        {'name': 'routine-check', 'score': 100, 'critical': False, 'evidenced': False},
        {'name': 'b', 'score': 100, 'critical': False, 'evidenced': True},
    ])
    if r4['verdict'] == 'PASS' and r4['items'][0]['score'] == 0 and r4['average'] == 50.0:
        ok += 1
        print('  ok   an unevidenced NON-critical control still scores 0 (pulling the average down) but does not by itself force a FAIL cap -- only a CRITICAL unevidenced item caps')
    else:
        print('  FAIL expected PASS/score 0/average 50, got %r' % r4)

    total += 1
    r5 = score_items([
        {'name': 'irreversible-op', 'score': 99.9, 'critical': True, 'evidenced': True},
    ])
    if r5['verdict'] == 'FAIL':
        ok += 1
        print('  ok   a critical item at 99.9 (not exactly 100) still caps -- "fully passing" means fully, not "close enough"')
    else:
        print('  FAIL expected FAIL at 99.9, got %r' % r5)

    print('%d/%d fixture checks correct' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    print('usage: hover_hardfail_cap.py --selftest')
    print('(library module -- import score_items() for real use; no CLI scoring mode, to avoid inventing an ad hoc input file format nobody asked for)')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
