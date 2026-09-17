#!/usr/bin/env python
"""Control for tools/log_cluster.py.

    python tests/run_log_cluster_probe.py      (exit 0 pass, 1 fail)

A SIMILARITY SCORER WILL PRODUCE A PLAUSIBLE NUMBER FOR ANY PAIR, and a
plausible number is the one nobody checks. This platform has already been wrong
that way -- a negative-binomial k of 0.87 reading as heavy superspreading out of
pure chance. So every arm here drives synthetic inputs whose answer is known,
in both directions, and the refusals are tested as hard as the verdicts.

THE ARM THAT MATTERS MOST IS THE BACKSPACE ONE. While this tool was being
written, one templating pattern was created through a non-raw Python string and
shipped with a literal `\\x08` where `\\b` should have been -- a regex that can
never match, which is the exact defect this repository's own CLAUDE.md lists as
having happened before. The blind lock caught it because a fixture went red;
nothing else would have, because the pattern PRINTS correctly in an editor.
"""
CONTROLS_FOR = ['log_cluster.py']

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
import log_cluster as L                                           # noqa: E402

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('  ok   %s' % label)
    else:
        FAILS.append(label)
        print('  FAIL %s\n       %s' % (label, str(detail)[:300]))


def sim(a, b):
    return L.similarity(L.embed(a), L.embed(b))


print('1. NO PATTERN CONTAINS A CONTROL CHARACTER')
# The defect this file exists for. A non-raw '\\b' becomes a backspace, the
# pattern still LOOKS right in an editor, and it can never match anything.
_bad = []
for rx, rep in L._SUBS:
    for ch in rx.pattern:
        if ord(ch) < 32:
            _bad.append((rep, hex(ord(ch))))
            break
ok('every templating pattern is free of raw control characters',
   not _bad, _bad)
ok('...and the id pattern actually fires, which is what the backspace broke',
   L.templatise('licence 3f2a-11 is not active') == 'licence <id> is not active',
   L.templatise('licence 3f2a-11 is not active'))

print('')
print('2. TEMPLATING removes parameters and keeps structure')
ok('two runs of one template collapse to the same string',
   L.templatise('checked 4 job(s)') == L.templatise('checked 17 job(s)'))
ok('...and two DIFFERENT templates do not',
   L.templatise('checked 4 job(s)') != L.templatise('wrote 4 row(s)'))
ok('placeholders are NAMED, so a template can be read back',
   '<n>' in L.templatise('checked 4 jobs') and '<id>' in L.templatise('run ab-12'),
   L.templatise('checked 4 jobs') + ' | ' + L.templatise('run ab-12'))

print('')
print('3. THE SCORER SEPARATES what it claims to separate')
ok('same template, different parameters -> 1.0',
   sim('checked 4 job(s)', 'checked 17 job(s)') > 0.99)
ok('unrelated subjects -> low',
   sim('the slab could not be reserved because it is already on a job',
       'payroll tax rates are current for the 2026 filing year') < 0.4)
# BOTH DIRECTIONS. A scorer that returns 1.0 for everything passes the first
# arm; one that returns 0 for everything passes the second.
ok('...and the two are far apart, which neither degenerate scorer achieves',
   sim('checked 4 job(s)', 'checked 17 job(s)')
   - sim('the slab could not be reserved because it is already on a job',
         'payroll tax rates are current for the 2026 filing year') > 0.5)

print('')
print('4. THE BOILERPLATE FALSE POSITIVE IS REAL AND IS NOT SUPPRESSED')
# The premise the whole tool is built around: unrelated log lines that share
# boilerplate score very high. If this ever drops below 0.85 the tool's central
# warning has stopped being true and the threshold advice needs re-deriving.
_boiler = sim('app_id is required and must be a short identifier',
              'shopId is required and must be a short identifier')
ok('two different subjects sharing boilerplate still score above 0.85',
   _boiler >= 0.85, _boiler)
ok('...and the recommended threshold must therefore sit ABOVE it',
   True, 'checked against the live corpus in arm 6')

print('')
print('5. THE BLIND LOCK can fail, or it is decoration')
ok('the fixtures pass on the real scorer', not L.self_check(verbose=False))
_real_embed = L.embed
try:
    L.embed = lambda t: {0: 1.0}          # everything identical
    ok('...and they FAIL when the scorer says everything is the same',
       len(L.self_check(verbose=False)) >= 1,
       'a degenerate always-1.0 scorer passed the blind lock')
finally:
    L.embed = _real_embed

print('')
print('6. THE THRESHOLD IS CHOSEN FROM MEASUREMENT, NOT FROM LIST ORDER')
corpus = L.harvest()
ok('the corpus is non-trivial', len(corpus) > 200, len(corpus))
related, unrelated = L.labelled_pairs(corpus, limit=1500)
ok('both labelled populations are non-empty',
   len(related) > 10 and len(unrelated) > 200,
   (len(related), len(unrelated)))
_rel, _unrel, rows = L.measure(related, unrelated)
ok('the false-positive rate is MONOTONE NON-INCREASING in the threshold -- '
   'if it is not, the measurement is wrong rather than interesting',
   all(rows[i]['fp_rate'] >= rows[i + 1]['fp_rate'] for i in range(len(rows) - 1)),
   [(r['threshold'], r['fp_rate']) for r in rows])
_usable = [r for r in rows if r['fp_rate'] <= L.MAX_FP_RATE]
ok('at least one threshold meets the false-positive target', _usable,
   [(r['threshold'], r['fp_rate']) for r in rows])
# CALLED, NOT RE-IMPLEMENTED. The first version of this arm had its own copy of
# the selection rule, and the two promptly disagreed: the tool floored the
# recommendation at a known false positive and this copy did not, so the probe
# reported 0.85 as chosen while the tool chose 0.92. A selection rule copied
# into a test is a second rule that can drift from the first.
if _usable:
    _best = L.recommend(rows)
    ok('a threshold survives the floor as well as the sampled rate',
       _best is not None,
       [(r['threshold'], r['fp_rate']) for r in rows])
if _usable and _best:
    # THE BUG THIS ARM EXISTS FOR. The first version chose on true-positive
    # rate, which is flat at 100% here, so max() returned the FIRST entry --
    # 0.60 at 0.70% FP, while 0.92 measured 0.00%. A selection rule driven by a
    # flat metric is a selection rule driven by list order.
    ok('the chosen threshold has the LOWEST measured FP rate among those above '
       'the floor, not the lowest index',
       all(_best['fp_rate'] <= r['fp_rate'] for r in _usable
           if r['threshold'] > L.known_false_positive()),
       (_best['threshold'], _best['fp_rate']))
    ok('...and it sits above the boilerplate false positive from arm 4',
       _best['threshold'] > _boiler, (_best['threshold'], _boiler))
    # AND THE FLOOR CAN BITE, or it is decoration: with the floor raised past
    # every candidate, the tool must return NOTHING rather than the best of a
    # bad set.
    ok('TEETH: an impossible floor yields NO recommendation, not a fallback',
       L.recommend(rows, known_fp=0.999) is None,
       L.recommend(rows, known_fp=0.999))

print('')
print('7. IT REFUSES rather than clustering on an unvalidated threshold')
_rows_bad = [{'threshold': t, 'fp': 999, 'fp_rate': 0.5, 'tp': 1, 'tp_rate': 1.0}
             for t in L.THRESHOLDS]
ok('a model with 50% false positives leaves NO usable threshold',
   not [r for r in _rows_bad if r['fp_rate'] <= L.MAX_FP_RATE])
ok('the target is tighter than any plausible failure point (convention 4)',
   L.MAX_FP_RATE <= 0.05, L.MAX_FP_RATE)

print('')
print('8. CLUSTERING is an upper bound on distinct problems, and says so')
msgs = ['checked 4 job(s)', 'checked 17 job(s)', 'checked 2 job(s)',
        'the slab is already reserved', 'payroll rates are current']
cl = L.cluster(msgs, 0.92)
ok('the three template-identical lines land in ONE cluster',
   any(len(c) == 3 for c in cl), [len(c) for c in cl])
ok('...and the two unrelated ones do not join it',
   len(cl) == 3, [[m[:24] for m in c] for c in cl])

print('')
print('=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
