#!/usr/bin/env python
"""Standing regression: the comment stripper and an independent comment count
agree on EVERY app, every run.

    python tests/run_comment_strip_agreement_probe.py

Exit 0 all arms pass, 1 any arm fails, 2 COULD NOT RUN (no app found).

WHY THIS IS A TEST AND NOT A ONE-OFF (cody b61). In b59 the
sairn_dead_function_sweep guard refused three correct strips because it
assumed comments were single-digit percent. The cross-check that proved them
correct -- blanked share vs a whole-line comment count that never calls the
stripper -- was a scratch script. Kept as one, it answers once; the next
stripper regression (a `/*` in a regex literal, an HTML rule spanning JS
strings) or the next drift in the estimate goes unseen until a sweep refuses a
file again. Here it runs over every tracked *.html each time the suite does.

  A. per app: |blanked - comment_estimate()| <= RUNAWAY_MARGIN_PP, and the
     sweep's own guard does not call the file UNTRUSTED. Measured b59: every
     one of 22 apps between 0.0 and +0.5 points.
  B. the two are INDEPENDENT: comment_estimate() does not call
     strip_comments() or jscomments, so one runaway cannot hide in both.
  C. controls: a real runaway is outside the margin; a comment-heavy file
     is inside it -- so section A is not a check that passes everything.
"""
import glob
import inspect
import os
import subprocess
import sys

CONTROLS_FOR = ['tools/sairn_dead_function_sweep.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_dead_function_sweep as D  # noqa: E402

bad = 0


def arm(label, cond, detail=''):
    global bad
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         %s' % str(detail)[-300:]))
    if not cond:
        bad += 1


def gap(raw):
    code = D.strip_comments(raw)
    blanked = 100.0 * sum(1 for a, b in zip(raw, code) if a != b) / max(1, len(raw))
    return blanked, D.comment_estimate(raw)


def main():
    print('COMMENT STRIP vs INDEPENDENT COUNT -- every app')
    r = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    apps = [f for f in r.stdout.splitlines() if f and '/' not in f] if r.returncode == 0 else []
    if not apps:
        print('COULD NOT RUN: `git ls-files *.html` found no app (rc %s)' % r.returncode)
        return 2

    print('\nA. agreement, per app (margin %.1f points)' % D.RUNAWAY_MARGIN_PP)
    worst = None
    for f in sorted(apps):
        raw = open(os.path.join(REPO, f), encoding='utf-8', errors='replace').read()
        b, e = gap(raw)
        d = b - e
        worst = d if worst is None or d > worst else worst
        arm('%-28s blanked %5.1f  counted %5.1f  diff %+.2f' % (f, b, e, d),
            d <= D.RUNAWAY_MARGIN_PP, 'the strip blanked more than the comments an '
            'independent count can see -- a delimiter has run away, or the count drifted')
        try:
            D.sweep(os.path.join(REPO, f))
            trusted = True
        except D.UntrustedStrip as ex:
            trusted, why = False, str(ex)
        arm('%-28s the sweep trusts its strip' % f, trusted, locals().get('why', ''))
    print('  (%d apps; largest diff %+.2f points)' % (len(apps), worst))

    print('\nB. independence')
    est_src = inspect.getsource(D.comment_estimate)
    arm('comment_estimate() calls neither strip_comments() nor jscomments',
        'strip_comments' not in est_src.split('"""')[-1] and 'jscomments' not in est_src.split('"""')[-1],
        est_src)

    print('\nC. controls')
    runaway = ("<script>\nvar open = '<!--';\n%s\nvar shut = '-->';\n</script>\n"
               % '\n'.join('function f%d(){ return %d; }' % (i, i) for i in range(60)))
    b, e = gap(runaway)
    arm('a REAL runaway (HTML rule spanning two JS strings) is OUTSIDE the margin '
        '(blanked %.1f, counted %.1f)' % (b, e), b - e > D.RUNAWAY_MARGIN_PP)
    heavy = ('<script>\n/* %s */\n%s\nfunction used(){}\nused();\n</script>\n'
             % ('x' * 2000, '\n'.join('// prose line %d' % i for i in range(40))))
    b, e = gap(heavy)
    arm('a comment-HEAVY file (%.1f%% blanked) is INSIDE the margin (counted %.1f)'
        % (b, e), b > 25 and b - e <= D.RUNAWAY_MARGIN_PP)

    print('\n  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
