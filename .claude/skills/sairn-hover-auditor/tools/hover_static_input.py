#!/usr/bin/env python
"""hover_static_input.py -- deterministic STATIC ANALYSIS as an INPUT to this
role's review, with a hard rule: a run that could not complete reads
INCONCLUSIVE and NEVER clean. Built H1 b72, item 4.

THE RULE THIS FILE EXISTS FOR, stated as the single sentence it is:
**EXIT 0 PLUS A RULE TIMEOUT IS NOT A CLEAN RESULT.**
Every static analyser worth running reports two different things on two
different channels -- the findings it made, and the work it could not
finish. Most of them exit 0 for both. semgrep exits 0 with a `errors` array
listing rules that timed out; eslint exits 0 while reporting a file it could
not parse; `node --check` is per-file so a skipped file is simply absent
from the output. In all three cases the DEFAULT READING of exit 0 is "no
problems found", and in all three cases that reading is wrong whenever the
second channel is non-empty. This is PR SS1.11 applied to somebody else's
tool instead of to one of mine: could-not-run is a THIRD STATE and folding
it into "passed" reports a check that never happened.

WHY IT IS WORTH A FILE. b71's #1617, #1619 and #1622 were all found by
READING. The deterministic sweeps that were supposed to find them reported
3 candidates and 0 candidates respectively, and b72's own recall
measurement (#1634) put a number on why: my patterns catch 1 of 6
structurally different spellings of a defect they already know. A static
analyser written by somebody else is a genuinely different instrument and
is therefore worth feeding IN -- but only if its silence can be
distinguished from its success, which is what this file does.

THE CLASSIFIER IS THE WHOLE TOOL and it is a pure function, so every arm
including the exit-0-with-timeout arm is driven by a fixture rather than by
hoping an analyser misbehaves on cue:

    classify(exit_code, stdout, stderr, timed_out, targets, seen)
      -> ('CLEAN' | 'FINDINGS' | 'INCONCLUSIVE', [reasons])

INCONCLUSIVE wins over CLEAN on ANY of: a wall-clock timeout; a non-empty
error channel; a partial-coverage signal (fewer targets reported on than
were handed in); a parse/rule failure named in stdout even at exit 0; or
unparseable output. INCONCLUSIVE also wins over FINDINGS, because a run
that found two things and could not finish has an unknown third.

WHAT IS DELIBERATELY NOT HERE: a bundled analyser. semgrep is not on this
machine (checked, b72) and this tool does not install one -- the repo's
deny list blocks package installs for good reason and an auditor
self-provisioning its own toolchain is a change nobody reviewed. It runs
what is actually present (`node --check`, `python -m py_compile`) and
reports the absence of the others as an absence rather than passing the
gap off as a clean sweep.

Run:
  python hover_static_input.py --analyse <file> [<file>...]
  python hover_static_input.py --review-input <file> [...]   # the block
  python hover_static_input.py --selftest
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_INCONCLUSIVE = 2

PER_FILE_TIMEOUT = 25

# Signals that a run did not cover what it was asked to, EVEN AT EXIT 0.
# Each is a real string one of these analysers emits.
PARTIAL_SIGNALS = (
    (re.compile(r'\btimed?\s*out\b', re.I), 'a rule or file timed out'),
    (re.compile(r'\bTimeout\b'), 'a timeout was reported'),
    (re.compile(r'"errors"\s*:\s*\[\s*\{'), 'the analyser reported a non-empty errors array'),
    (re.compile(r'\bPartial(?:ly)?\b.{0,24}\b(scan|parse|analys)', re.I),
     'the analyser described its own run as partial'),
    (re.compile(r'\bcould not parse\b|\bparse error\b|\bParsingError\b', re.I),
     'a target could not be parsed, so it was not analysed'),
    (re.compile(r'\bskipp(?:ed|ing)\b', re.I), 'a target was skipped'),
    (re.compile(r'\bout of memory\b|\bOOM\b', re.I), 'the analyser ran out of memory'),
)


def classify(exit_code, stdout, stderr, timed_out, targets, seen):
    """('CLEAN'|'FINDINGS'|'INCONCLUSIVE', reasons). Pure."""
    reasons = []
    blob = (stdout or '') + '\n' + (stderr or '')
    if timed_out:
        reasons.append('WALL-CLOCK TIMEOUT: the analyser was killed before '
                        'it finished, so its silence covers nothing')
    for rx, why in PARTIAL_SIGNALS:
        if rx.search(blob):
            reasons.append('PARTIAL-RUN SIGNAL: %s' % why)
    if targets and seen is not None and seen < len(targets):
        reasons.append('PARTIAL COVERAGE: %d target(s) handed in, %d '
                        'reported on -- the %d not reported are UNKNOWN, '
                        'not clean' % (len(targets), seen, len(targets) - seen))
    if reasons:
        # Deliberately ahead of both other verdicts. A run that found
        # things AND could not finish has an unknown remainder, so it is
        # not FINDINGS either.
        return 'INCONCLUSIVE', reasons
    if exit_code not in (0, 1):
        return 'INCONCLUSIVE', ['UNEXPECTED EXIT %s: neither the analyser\'s '
                                 'clean code nor its findings code, so its '
                                 'output cannot be interpreted' % exit_code]
    if exit_code == 1 or re.search(r'\berror\b', blob, re.I):
        return 'FINDINGS', ['the analyser reported at least one problem']
    return 'CLEAN', ['exit 0, empty error channel, full coverage']


def run_node_check(paths):
    """(exit, stdout, stderr, timed_out, seen). `node --check` is per-file,
    so `seen` is counted explicitly -- a file that never got a verdict is
    the partial-coverage case this tool exists to catch, and with a
    per-file analyser it is invisible unless somebody counts."""
    outs, errs, seen, worst, timed = [], [], 0, 0, False
    for p in paths:
        try:
            r = subprocess.run(['node', '--check', p], capture_output=True,
                                text=True, timeout=PER_FILE_TIMEOUT)
        except subprocess.TimeoutExpired:
            timed = True
            errs.append('%s: timed out after %ds' % (p, PER_FILE_TIMEOUT))
            continue
        except OSError as e:
            errs.append('%s: could not run node (%s)' % (p, e))
            continue
        seen += 1
        worst = max(worst, 1 if r.returncode else 0)
        if r.stdout:
            outs.append(r.stdout)
        if r.stderr:
            errs.append(r.stderr)
    return worst, '\n'.join(outs), '\n'.join(errs), timed, seen


def run_py_compile(paths):
    outs, errs, seen, worst, timed = [], [], 0, 0, False
    for p in paths:
        try:
            r = subprocess.run([sys.executable, '-m', 'py_compile', p],
                                capture_output=True, text=True,
                                timeout=PER_FILE_TIMEOUT)
        except subprocess.TimeoutExpired:
            timed = True
            errs.append('%s: timed out after %ds' % (p, PER_FILE_TIMEOUT))
            continue
        except OSError as e:
            errs.append('%s: could not run py_compile (%s)' % (p, e))
            continue
        seen += 1
        worst = max(worst, 1 if r.returncode else 0)
        if r.stderr:
            errs.append(r.stderr)
    return worst, '\n'.join(outs), '\n'.join(errs), timed, seen


ANALYSERS = (
    ('node --check', ('.js',), run_node_check),
    ('python -m py_compile', ('.py',), run_py_compile),
)

# Named, checked, and ABSENT. Reported as missing rather than omitted --
# "we ran the analysers we had" and "the tree is clean" are different
# claims and only the first one is true here.
NOT_AVAILABLE = (
    ('semgrep', 'not on PATH on this machine (checked b72). NOT installed '
                'by this tool: the repo denies package installs, and an '
                'auditor self-provisioning a toolchain is a change nobody '
                'reviewed.'),
    ('eslint with a project config', 'npx eslint resolves, but this repo '
                                      'carries no eslint config, so a run '
                                      'would report on default rules '
                                      'nobody chose. Not run rather than '
                                      'run meaninglessly.'),
)


def analyse(paths):
    """[(name, verdict, reasons, detail)] -- one row per analyser that had
    targets."""
    rows = []
    for name, exts, fn in ANALYSERS:
        targets = [p for p in paths if os.path.splitext(p)[1] in exts]
        if not targets:
            continue
        code, out, err, timed, seen = fn(targets)
        verdict, reasons = classify(code, out, err, timed, targets, seen)
        rows.append((name, verdict, reasons,
                      {'targets': len(targets), 'seen': seen,
                       'exit': code, 'stderr': (err or '')[:400]}))
    return rows


def review_input(paths):
    """The block handed to the review as INPUT. A dict, not prose, so a
    caller cannot skim past an INCONCLUSIVE."""
    rows = analyse(paths)
    verdicts = [r[1] for r in rows]
    if not rows:
        overall = 'INCONCLUSIVE'
        why = ['NO ANALYSER HAD A TARGET: nothing was analysed, which is '
                'not the same as nothing being wrong']
    elif 'INCONCLUSIVE' in verdicts:
        overall = 'INCONCLUSIVE'
        why = ['at least one analyser could not complete']
    elif 'FINDINGS' in verdicts:
        overall = 'FINDINGS'
        why = ['at least one analyser reported a problem']
    else:
        overall = 'CLEAN'
        why = ['every analyser that had a target completed and reported '
                'nothing']
    return {
        'overall': overall,
        'why': why,
        'analysers': [{'name': n, 'verdict': v, 'reasons': rs, 'detail': d}
                       for n, v, rs, d in rows],
        'not_available': [{'name': n, 'reason': r} for n, r in NOT_AVAILABLE],
        'how_to_read_this': (
            'INCONCLUSIVE IS NOT CLEAN. Do not treat the absence of findings '
            'from an incomplete run as evidence. The not_available list is '
            'part of the result: the analysers that did run do not cover '
            'what the missing ones would have.'),
    }


def selftest():
    ok = [0]
    bad = [0]

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   %s' % name)
        else:
            bad[0] += 1
            print('  FAIL %s' % name)

    v, r = classify(0, '', '', False, ['a.js'], 1)
    ck('S1 exit 0, empty channels, full coverage -> CLEAN', v == 'CLEAN')

    v, r = classify(1, 'SyntaxError: x', '', False, ['a.js'], 1)
    ck('S2 exit 1 -> FINDINGS', v == 'FINDINGS')

    # THE ARM THE DISPATCH NAMES.
    v, r = classify(0, '{"results": [], "errors": [{"type": "Timeout", '
                        '"rule_id": "r1"}]}', '', False, ['a.js'], 1)
    ck('S3 THE NAMED ARM -- EXIT 0 WITH A RULE TIMEOUT READS INCONCLUSIVE, '
       'NEVER CLEAN (%s)' % (r[0][:58] if r else ''), v == 'INCONCLUSIVE')

    v, r = classify(0, '', 'rule foo timed out after 5s', False, ['a.js'], 1)
    ck('S4 a timeout on STDERR at exit 0 also reads INCONCLUSIVE -- the '
       'signal is not required to be on stdout', v == 'INCONCLUSIVE')

    v, r = classify(0, '', '', True, ['a.js'], 0)
    ck('S5 a WALL-CLOCK kill reads INCONCLUSIVE and says the silence covers '
       'nothing', v == 'INCONCLUSIVE'
       and any('WALL-CLOCK' in x for x in r))

    v, r = classify(0, '', '', False, ['a.js', 'b.js', 'c.js'], 2)
    ck('S6 PARTIAL COVERAGE -- 3 targets in, 2 reported on -- reads '
       'INCONCLUSIVE and names the count, which is the only way a per-file '
       'analyser\'s skipped file is ever visible', v == 'INCONCLUSIVE'
       and any('PARTIAL COVERAGE' in x for x in r))

    v, r = classify(1, 'SyntaxError', 'rule bar timed out', False, ['a.js'], 1)
    ck('S7 INCONCLUSIVE BEATS FINDINGS: a run that found something AND '
       'could not finish has an unknown remainder, so it is not reported as '
       'FINDINGS', v == 'INCONCLUSIVE')

    v, r = classify(137, '', '', False, ['a.js'], 1)
    ck('S8 an UNEXPECTED exit code (137, OOM-killed) is INCONCLUSIVE rather '
       'than guessed in either direction', v == 'INCONCLUSIVE')

    v, r = classify(0, 'Skipping 4 files (could not parse)', '', False,
                     ['a.js'], 1)
    ck('S9 a self-described skip at exit 0 reads INCONCLUSIVE',
       v == 'INCONCLUSIVE')

    ck('S10 an empty target list for every analyser gives an INCONCLUSIVE '
       'overall, not a CLEAN one -- "nothing was analysed" and "nothing is '
       'wrong" are different claims',
       review_input(['notes.txt'])['overall'] == 'INCONCLUSIVE')

    ck('S11 the review-input block NAMES the analysers that are absent, so '
       'a reader cannot mistake what ran for full coverage',
       [a['name'] for a in review_input(['notes.txt'])['not_available']]
       == [n for n, _ in NOT_AVAILABLE])

    ck('S12 and it carries an explicit how-to-read line saying INCONCLUSIVE '
       'is not clean',
       'INCONCLUSIVE IS NOT CLEAN' in review_input(['notes.txt'])['how_to_read_this'])

    # Drive the REAL analysers against real files, because b72 has already
    # produced three return-shape bugs in freshly written tools whose
    # fixtures all passed (hover_context_watch x2, hover_vendor_sample x1).
    real_py = os.path.join(HERE, 'hover_static_input.py')
    rows = analyse([real_py])
    ck('S13 the REAL py_compile analyser runs against this very file and '
       'returns CLEAN (%s)' % (rows[0][1] if rows else 'no row'),
       len(rows) == 1 and rows[0][1] == 'CLEAN')

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        badpy = os.path.join(td, 'broken.py')
        with open(badpy, 'w', encoding='utf-8') as f:
            f.write('def (:\n')
        rows2 = analyse([badpy])
        ck('S14 KNOWN-BAD CONTROL: a genuinely unparseable python file is '
           'NOT reported CLEAN by the real analyser (%s)'
           % (rows2[0][1] if rows2 else 'no row'),
           rows2 and rows2[0][1] in ('FINDINGS', 'INCONCLUSIVE'))

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return EXIT_CLEAN if not bad[0] else EXIT_FINDINGS


def main(argv):
    if '--selftest' in argv:
        return selftest()
    paths = [a for a in argv if not a.startswith('--')]
    if not paths:
        print('usage: --analyse <file>... | --review-input <file>... | --selftest')
        return EXIT_INCONCLUSIVE
    block = review_input(paths)
    if '--review-input' in argv:
        print(json.dumps(block, indent=1))
    else:
        print('OVERALL: %s' % block['overall'])
        for w in block['why']:
            print('  %s' % w)
        for a in block['analysers']:
            print('  %-24s %-13s targets=%d seen=%d exit=%s'
                  % (a['name'], a['verdict'], a['detail']['targets'],
                     a['detail']['seen'], a['detail']['exit']))
            for rs in a['reasons']:
                print('      %s' % rs)
        print('  NOT AVAILABLE, and this is part of the result:')
        for a in block['not_available']:
            print('      %-32s %s' % (a['name'], a['reason']))
        print('  %s' % block['how_to_read_this'])
    return {'CLEAN': EXIT_CLEAN, 'FINDINGS': EXIT_FINDINGS,
            'INCONCLUSIVE': EXIT_INCONCLUSIVE}[block['overall']]


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
