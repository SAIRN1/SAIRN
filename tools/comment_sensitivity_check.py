"""Does any checker's answer CHANGE when the target's comments are removed?

WHY. Three times in two days a check matched text that only DESCRIBED code
rather than code: two probes greping for a literal their own fix's comment
quoted, and then the mutation-anchor tool flagging its own probe for carrying
the unsafe pattern as a fixture string. Each was fixed where it was found. This
asks the general question about the checker fleet instead of waiting for a
fourth.

IT IS BEHAVIOURAL, NOT STRUCTURAL, AND THAT IS THE POINT. The obvious way to
audit this is to grep each checker for a comment-stripping idiom. That was tried
first and it was WRONG TWICE IN ONE PASS: duplicate_global_check and
key_collision_check both hand-write a full character-level scanner that skips
comments, strings and regex literals, and neither uses any idiom a grep would
recognise -- so a grep-based survey called two of the most careful tools in the
repo unsafe. Grep was the wrong instrument for "does this code do X" for the
FOURTH time, this time in the audit rather than the tool.

So this runs each checker twice -- once on the real file, once on a copy with
comment spans blanked -- and compares the output. It does not care HOW a checker
handles comments, or whether it handles them at all. It cares only whether its
ANSWER depends on them. A checker that already ignores comments produces
identical output and says nothing.

MEASURED 2026-09-11, the day it was built: six checkers take a file argument,
run across every root app; ZERO differ. That is a real result and it is only
worth stating because the probe plants a comment-sensitive fixture and asserts
this tool catches it -- a comparison that can never differ would also report
zero.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * checkers that take no file argument. They resolve their own targets, and
    running those against a stripped tree would mean mutating the tree -- which
    is exactly what a read-only checker must not do;
  * a checker whose output is correct on both and wrong on both;
  * STRING literals. Only comments are blanked. A pattern matching code quoted
    inside a string is the same class and is NOT covered here -- it is what
    tools/mutation_anchor_check.py hit, and ast is the answer there, not this.

Usage:
    python tools/comment_sensitivity_check.py
    python tools/comment_sensitivity_check.py --json

Exit 0 when no checker's answer depends on comments, 1 when one does, 2 when a
checker could not be run at all -- which is not a pass.
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
from comment_quote_check import strip_comments  # noqa: E402

# Only checkers that take the file to inspect as argv[1]. See the docstring for
# why the rest are out of scope rather than quietly skipped.
CHECKERS = [
    'div_balance_check.py',
    'duplicate_global_check.py',
    'key_collision_check.py',
    'literal_drift_check.py',
    'nav_panel_check.py',
    'panel_nesting_check.py',
]


def run(tool, path):
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', tool), path],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    # The path appears in some outputs and legitimately differs between the real
    # file and the temp copy; normalise it out or every checker looks sensitive.
    out = (p.stdout or '') + (p.stderr or '')
    return p.returncode, out.replace(path, '<TARGET>').replace(
        path.replace('\\', '/'), '<TARGET>')


def main(argv):
    targets = sorted(glob.glob(os.path.join(REPO, '*.html')))
    tmp = tempfile.mkdtemp(prefix='comment_sensitivity_')
    rows, errors = [], []
    try:
        stripped = {}
        for t in targets:
            raw = io.open(t, encoding='utf-8', errors='replace').read()
            dst = os.path.join(tmp, os.path.basename(t))
            io.open(dst, 'w', encoding='utf-8', newline='\n').write(strip_comments(raw))
            stripped[t] = dst

        for tool in CHECKERS:
            if not os.path.exists(os.path.join(REPO, 'tools', tool)):
                errors.append((tool, 'not found'))
                continue
            for t in targets:
                rc_a, out_a = run(tool, t)
                rc_b, out_b = run(tool, stripped[t])
                same = (rc_a == rc_b and out_a == out_b)
                rows.append({'checker': tool,
                             'target': os.path.basename(t),
                             'same': same,
                             'exit_raw': rc_a, 'exit_stripped': rc_b})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    differs = [r for r in rows if not r['same']]
    by_tool = {}
    for r in rows:
        by_tool.setdefault(r['checker'], []).append(r)

    if '--json' in argv:
        print(json.dumps({'comparisons': rows, 'errors': errors}, indent=1))
    else:
        print('COMMENT SENSITIVITY -- report only; the stripped copies live in a temp dir')
        print('  checkers compared : %d' % len(by_tool))
        print('  comparisons run   : %d  (each checker x each root app)' % len(rows))
        print('  answers that CHANGE when comments are removed: %d' % len(differs))
        print('  could not run     : %d  (NOT a pass)' % len(errors))
        for tool in sorted(by_tool):
            d = sum(1 for r in by_tool[tool] if not r['same'])
            print('    %-30s targets=%-3d differ=%d' % (tool, len(by_tool[tool]), d))
        for r in differs:
            print('\n  %s on %s' % (r['checker'], r['target']))
            print('      its answer depends on the target COMMENTS: exit %d raw vs %d '
                  'stripped. It is matching text that describes code rather than code.'
                  % (r['exit_raw'], r['exit_stripped']))
        for tool, why in errors:
            print('\n  COULD NOT RUN  %s -- %s' % (tool, why))
        print('\n  NOTE: comments only. A pattern matching code quoted inside a STRING')
        print('  is the same class and is not covered -- see the module docstring.')

    if errors:
        return 2
    return 1 if differs else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
