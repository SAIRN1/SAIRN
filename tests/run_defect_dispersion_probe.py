"""Control pair for tools/defect_dispersion.py.

Run: python tests/run_defect_dispersion_probe.py

A dispersion figure is the easiest kind of number to quote wrongly, so the arms
that matter are the ones proving the tool cannot be quoted wrongly: that the
two Gini columns really differ, that a refused population is refused rather than
defaulted, and that the maths is right on inputs whose answer is known in
advance.

OFFLINE. Every arm calls a function directly or runs the tool once.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import defect_dispersion as D                                   # noqa: E402

CONTROLS_FOR = ['defect_dispersion.py']

FAILED = []


def check(label, got, want):
    ok = got == want
    print('  %s %s' % ('ok  ' if ok else 'FAIL', label))
    if not ok:
        print('       expected %r, got %r' % (want, got))
        FAILED.append(label)


def near(label, got, want, tol=0.001):
    ok = got is not None and abs(got - want) <= tol
    print('  %s %s' % ('ok  ' if ok else 'FAIL', label))
    if not ok:
        print('       expected ~%r, got %r' % (want, got))
        FAILED.append(label)


def main():
    print('defect dispersion control pair\n')

    # ── 1. THE MATHS, on inputs whose answer is known ────────────────────────
    print('1. gini() against cases with a known answer')
    near('perfectly even is 0', D.gini([5, 5, 5, 5]), 0.0)
    near('all in one of four is 0.75', D.gini([4, 0, 0, 0]), 0.75)
    near('all in one of ten is 0.90', D.gini([1, 0, 0, 0, 0, 0, 0, 0, 0, 0]), 0.90)
    check('an empty list is None, not zero', D.gini([]), None)
    check('all zeros is 0.0, not a divide-by-zero', D.gini([0, 0, 0]), 0.0)
    near('top20 of a perfectly even set is 0.2-ish',
         D.top_share([1] * 10), 0.2)
    near('top20 when one unit holds everything is 1.0',
         D.top_share([10, 0, 0, 0, 0, 0, 0, 0, 0, 0]), 1.0)
    check('top_share of nothing is None', D.top_share([]), None)

    # ── 2. THE TWO COLUMNS REALLY DIFFER ─────────────────────────────────────
    # This is the arm the whole design rests on. If the population figure were
    # computed over the affected units too, both columns would agree and the
    # tool would be quietly reporting the flattering number twice.
    print('\n2. the affected and population figures are NOT the same number')
    d = D.dimension('x', {'a': 3, 'b': 3, 'c': 3}, 100, 'note')
    near('among 3 affected units, evenly: 0', d['gini_among_affected'], 0.0)
    check('...but over a population of 100 it is far higher',
          d['gini_over_population'] > 0.9, True)
    check('...and the 97 zeros are counted and reported', d['zero_units'], 97)

    # CONTROL: when the population IS the affected set, they must agree --
    # otherwise the difference above could be an artefact rather than the zeros.
    d2 = D.dimension('x', {'a': 3, 'b': 3, 'c': 3}, 3, 'note')
    check('CONTROL: population == affected makes the two agree',
          round(d2['gini_among_affected'], 6) == round(d2['gini_over_population'], 6),
          True)
    check('...with no zero units', d2['zero_units'], 0)

    # ── 3. AN UNCOUNTED POPULATION IS REFUSED, NOT DEFAULTED ─────────────────
    print('\n3. a population nobody counted is refused')
    d3 = D.dimension('x', {'a': 1}, None, 'note')
    check('gini over population is None', d3['gini_over_population'], None)
    check('top20 over population is None', d3['top20_over_population'], None)
    check('...and it says so rather than leaving a blank',
          'NOT COUNTED' in d3['population_note'], True)
    check('...while the affected figure is still computed',
          d3['gini_among_affected'] is not None, True)

    # ── 4. THE REAL RUN ──────────────────────────────────────────────────────
    print('\n4. the real register')
    r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'defect_dispersion.py'),
                        '--json'], capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    doc = json.loads(r.stdout)
    check('it runs against the committed register', doc['records'] > 0, True)
    dims = {d['dimension']: d for d in doc['dimensions']}
    check('every dimension is present',
          sorted(dims) == sorted(['app', 'detection method', 'file', 'layer',
                                  'originating commit', 'session']), True)
    check('the detection-method population is refused, not guessed',
          dims['detection method']['gini_over_population'], None)
    check('...which makes the whole run COULD-NOT-RUN rather than clean',
          bool(doc['could_not_run']), True)
    check('...and exit 2', r.returncode, 2)
    check('layer has a population of exactly three',
          dims['layer']['population'], 3)
    check('the commit dimension has more population than affected units',
          dims['originating commit']['population'] > dims['originating commit']['affected_units'],
          True)

    # ── 5. THE CAVEATS ARE PRINTED, NOT IMPLIED ──────────────────────────────
    print('\n5. the number cannot be quoted bare')
    out = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'defect_dispersion.py')],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', cwd=REPO,
                         env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                  PYTHONUTF8='1')).stdout
    check('it says to read both columns together',
          'READ THE TWO GINI COLUMNS TOGETHER OR NEITHER' in out, True)
    check('it says a high figure is as much about COVERAGE as causation',
          'ABOUT COVERAGE' in out, True)
    check('it labels session as a proxy, not an agent',
          'A PROXY, NOT AN AGENT' in out, True)
    check('it says the file dimension OVER-attributes',
          'over-attributes' in out, True)
    check('and it calls itself a description rather than a verdict',
          'DESCRIPTION' in out.upper(), True)

    print('')
    if FAILED:
        print('FAILED  dispersion probe: %d failed' % len(FAILED))
        for f in FAILED:
            print('  - %s' % f)
        return 1
    print('ALL DISPERSION PROBE ASSERTIONS PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
