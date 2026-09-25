#!/usr/bin/env python
"""The control on tools/adversarial_prompt_corpus.py.

    python tests/run_adversarial_prompt_corpus_probe.py

Exit 0 all arms pass, 1 an arm failed.

WHY THIS EXISTS. The tool's whole output is a claim about which prompt sites
carry untrusted text, and a checker wrong in the GENEROUS direction reports a
platform safer than it is -- on the one surface where an overstated number is
worse than no number. Its own `--fixtures` lock is the first line; this drives
the things a lock inside the tool structurally cannot:

  * that the lock is WIRED -- a sweep must refuse to run when a fixture
    misclassifies, rather than reporting findings from broken criteria;
  * that the corpus cannot silently empty;
  * that the real-file sweep is not vacuous (it FINDS the known true positive
    and names the field);
  * MUTATION CONTROLS: three sabotages of the tool, each of which must change
    the verdict. A checker nobody has seen fail is a checker nobody has tested.

EVERY MUTATION ASSERTS ITS ANCHOR IS UNIQUE FIRST and restores from a byte
snapshot -- never `git checkout`, which has destroyed uncommitted work on this
platform before.
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'adversarial_prompt_corpus.py')
FAILED = []


def run(args):
    r = subprocess.run([sys.executable, TOOL] + args, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', cwd=REPO)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def arm(name, ok, detail=''):
    print('  %-4s %s' % ('ok' if ok else 'FAIL', name))
    if not ok and detail:
        print('       %s' % detail[:400])
    if not ok:
        FAILED.append(name)


def main():
    print('ADVERSARIAL PROMPT CORPUS -- the control on the checker\n')
    snap = io.open(TOOL, 'rb').read()
    src = snap.decode('utf-8')

    print('THE LOCK AND THE CORPUS')
    code, out = run(['--fixtures'])
    arm('1. the blind lock passes on its own fixtures', code == 0
        and 'classified correctly' in out, out[-300:])

    code, out = run(['--corpus'])
    n = int(re.search(r'(\d+) payload\(s\)', out).group(1)) if re.search(
        r'(\d+) payload\(s\)', out) else 0
    fams = len(re.findall(r'^== ', out, re.M))
    arm('2. the corpus is non-empty and multi-family (%d payloads, %d families)'
        % (n, fams), code == 0 and n >= 12 and fams >= 6, out[:200])
    arm('3. ...and it says a generated corpus is NOT exhaustive rather than '
        'implying coverage', 'not implied to be zero' in out.replace('\n', ' ')
        or 'NOT AN EXHAUSTIVE' in out, out[:300])

    print('\nTHE REAL SWEEP IS NOT VACUOUS')
    code, out = run([])
    arm('4. the sweep runs and reports findings on the real tree (exit 1)',
        code == 1, out[-300:])
    arm('5. ...and the counts are real: literal + interpolated > 90 sites',
        bool(re.search(r'PROMPT SITES: (\d+) literal', out))
        and sum(int(x) for x in re.findall(
            r'PROMPT SITES: (\d+) literal \(cannot carry untrusted text\), (\d+)',
            out)[0]) > 90, out[:300])
    # THE KNOWN TRUE POSITIVE, named rather than counted: sairnbuild's trade
    # analysis concatenates `job.notes` -- a user-typed free-text field -- into
    # its system prompt with no fence. Verified by hand at :6311.
    arm('6. it FINDS the verified true positive (sairnbuild notes -> prompt)',
        'sairnbuild.html' in out and 'notes' in out, out[:300])
    # CASE-NORMALISED: the tool prints this in caps, and the first version of
    # this arm looked for lower case and failed on output that said exactly the
    # right thing -- an arm wrong about its own subject, which is the shape this
    # whole file is about.
    arm('7. and it states that a fence is a mitigation, not a proof',
        'mitigation, not a proof' in out.replace('\n', ' ').lower(), out[-400:])

    print('\nMUTATION CONTROLS -- three sabotages, each must change the verdict')

    def sabotage(label, old, new, expect):
        n_ = src.count(old)
        if n_ != 1:
            arm(label, False, 'ANCHOR-%d -- re-derive it, do not type it' % n_)
            return
        io.open(TOOL, 'w', encoding='utf-8', newline='').write(
            src.replace(old, new, 1))
        try:
            import ast
            ast.parse(io.open(TOOL, encoding='utf-8').read())
        except SyntaxError as e:
            arm(label, False, 'MALFORMED-MUTATION: %s' % e)
            io.open(TOOL, 'wb').write(snap)
            return
        c, o = run([])
        arm(label, expect(c, o), 'exit %d\n%s' % (c, o[-300:]))
        io.open(TOOL, 'wb').write(snap)

    # M1. The untrusted list empties. THE EXPECTATION HERE WAS WRONG THE FIRST
    # TIME AND THE TOOL WAS RIGHT: I expected a CLEAN sweep (exit 0, zero
    # findings), which is the permanent-green-lie shape. What actually happens
    # is better -- the `complaint` fixture misclassifies, so the blind lock
    # REFUSES the sweep entirely with exit 2. An emptied criterion cannot
    # produce a reassuring number here, because the lock is upstream of the
    # sweep. Kept with the corrected expectation rather than deleted: it still
    # proves the findings depend on those fields, and now also proves the lock
    # covers this mutation.
    sabotage('8. emptying the untrusted-field list cannot produce a CLEAN '
             'sweep -- the lock refuses first, so the criteria cannot go quiet',
             "UNTRUSTED_WORDS = ('complaint', 'notes', 'transcript')",
             "UNTRUSTED_WORDS = ()",
             lambda c, o: c == 2 and 'COULD NOT RUN' in o
             and 'NOTHING was scanned' in o)

    # M2. The lock is broken -> the sweep must REFUSE to run, not report.
    sabotage('9. a broken criterion makes the sweep REFUSE rather than report '
             'findings from criteria that cannot classify a known case',
             "UNTRUSTED_PREFIXES = (\n    'ocr',",
             "UNTRUSTED_PREFIXES = (\n    'zzz_not_a_field',",
             lambda c, o: c == 2 and 'COULD NOT RUN' in o
             and 'NOTHING was scanned' in o)

    # M3. The delimiter list empties -> fenced sites must reclassify as
    # at-risk, never disappear. (Zero are fenced today, so this proves the
    # BRANCH exists rather than moving a number -- said plainly because a
    # mutation that cannot change today's output is weak evidence.)
    sabotage('10. emptying the delimiter list cannot make a site vanish -- '
             'every site stays in exactly one bucket',
             "DELIMITER_HINTS = (\n    '\"\"\"',",
             "DELIMITER_HINTS = (\n    'zzz_no_such_fence',",
             lambda c, o: 'FENCED, REPORTED SEPARATELY AND NOT AS CLEAN: 0'
             in o and 'NO DELIMITER: 15 site(s)' in o)

    print('\nRESTORATION')
    now = io.open(TOOL, 'rb').read()
    arm('11. the tool is byte-identical again', now == snap)
    code, out = run(['--fixtures'])
    arm('12. and its lock still passes', code == 0)

    print('')
    if FAILED:
        print('%d arm(s) FAILED: %s' % (len(FAILED), ', '.join(FAILED)))
        return 1
    print('all arms pass -- the lock is wired, the corpus is real, the sweep '
          'finds a verified')
    print('true positive, and three sabotages each move the verdict.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
