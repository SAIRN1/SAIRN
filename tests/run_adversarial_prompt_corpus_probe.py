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

# ── A STABLE LAST LINE (2026-10-20, cody b28) ─────────────────────────────
# AT THE TOP, NOT THE END, FOR TWO REASONS. (1) This probe calls sys.exit()
# at module level; SystemExit propagates out of the module body, so an
# atexit.register() below it is never reached -- b27 appended it and
# measured 0 of 12. (2) atexit runs handlers in REVERSE registration order,
# so being registered FIRST is what makes this line print LAST.
# THE CONCEPT: this probe must print ONE deterministic final line on every
#   exit path, so docs/known-red-suites.json can record a tail the runner
#   really produces -- b26 measured this file's stored tail as one it CANNOT.
#
# atexit fires after the summary AND after sys.exit(1), which is the path an
# arm failure takes here. The line carries NO DIGITS on purpose:
# known_red_check.py normalises digits away, so a count would make a red run
# and a green run compare EQUAL. It is a CONSTANT rather than a verdict for
# two reasons, the second of which was a real bug in the first draft:
#   1. known_red_check.py decides RECOVERED from the run's GREEN list, by
#      exit code, so the tail's only job is to identify the last line.
#   2. atexit handlers receive NO exit code, and sys.last_value is an
#      interactive-mode artefact of an uncaught exception -- it is NOT set
#      by sys.exit(1), which is the path this probe takes. Reading it would
#      have printed one verdict for every run.
import atexit as _b27_atexit


def _b27_stable_last_line():
    try:
        print('SUITE-RESULT tests/run_adversarial_prompt_corpus_probe.py END')
    except Exception:
        pass


_b27_atexit.register(_b27_stable_last_line)
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'adversarial_prompt_corpus.py')
# The same file as a repo-relative literal, so tools/probe_anchor_freshness.py
# can count the sabotage anchors below. TOOL is computed from REPO, so all three
# were `skipped` -- never counted -- and that is how arm 8's anchor vanished on
# 2026-09-26 (34d1ff0ed widened UNTRUSTED_WORDS) and stayed red unseen until
# cody b49.
SUBJECT = os.path.join('tools', 'adversarial_prompt_corpus.py')
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
    # UPDATED 2026-09-25: the five traced sites are now FENCED, so a clean
    # sweep (exit 0, zero unfenced) is the CORRECT verdict -- the old "reports
    # findings" expectation would have demanded the defect stay unfixed, which
    # is a control holding a platform to its own worst state. What must hold is
    # that the sweep RAN and CLASSIFIED; arm 10 is what proves those sites are
    # still being seen rather than silently lost.
    # A FLOOR, NOT AN EQUALITY (cody b49). This said "5" and went red on
    # 2026-09-26 when 34d1ff0ed fenced three more sites (8 today): the arm
    # punished a fix. The five traced sites may never vanish; more may be added.
    _fenced = re.search(r'NOT AS CLEAN: (\d+) site\(s\)', out)
    arm('4. the sweep runs and classifies: zero unfenced, at least 5 reported '
        'as fenced (%s)' % (_fenced.group(1) if _fenced else '?'),
        code == 0 and 'NO DELIMITER: 0 site(s)' in out
        and bool(_fenced) and int(_fenced.group(1)) >= 5,
        'exit ' + str(code) + chr(10) + out[-300:])
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

    # `edit` is [(SUBJECT, old, new)]: the list-of-tuples form tools/probe_anchor_freshness.py
    # counts, so a vanished anchor here is seen without running this file.
    def sabotage(label, edit, expect):
        (_subject, old, new), = edit
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
             [(SUBJECT, "UNTRUSTED_WORDS = ('complaint', 'notes', 'note', 'transcript', 'desc')",
              "UNTRUSTED_WORDS = ()")],
             lambda c, o: c == 2 and 'COULD NOT RUN' in o
             and 'NOTHING was scanned' in o)

    # M2. The lock is broken -> the sweep must REFUSE to run, not report.
    sabotage('9. a broken criterion makes the sweep REFUSE rather than report '
             'findings from criteria that cannot classify a known case',
             [(SUBJECT, "UNTRUSTED_PREFIXES = (\n    'ocr',",
              "UNTRUSTED_PREFIXES = (\n    'zzz_not_a_field',")],
             lambda c, o: c == 2 and 'COULD NOT RUN' in o
             and 'NOTHING was scanned' in o)

    # M3. The delimiter list empties -> fenced sites must reclassify as
    # at-risk, never disappear. (Zero are fenced today, so this proves the
    # BRANCH exists rather than moving a number -- said plainly because a
    # mutation that cannot change today's output is weak evidence.)
    # M3. Emptying the FENCE-CALL hints must move every fenced site into the
    # at-risk bucket -- NEVER make one disappear. This is the arm that proves
    # the five sites are still being traced now that they are fenced: without
    # it, a criteria change that stopped seeing them entirely would look
    # identical to a clean platform.
    # RE-DERIVED cody b49, THE SAME CORRECTION AS M1: since 34d1ff0ed
    # (2026-09-26) the lock carries a FENCED per-app fixture, so emptying the
    # hints misclassifies it and the sweep REFUSES (exit 2) before it reports
    # any count. Fenced sites cannot go quiet because nothing is reported at
    # all, and that is what this arm now requires. It asserted the pre-fixture
    # counts (5 -> at-risk) and had been red since that commit.
    sabotage('10. emptying the fence-call hints cannot make a fenced site '
             'vanish -- the lock refuses the sweep first',
             [(SUBJECT, "    'sffence(', 'fencedblock(', 'promptwithuntrusted(',",
              "    'zzz_no_such_fence',")],
             lambda c, o: c == 2 and 'COULD NOT RUN' in o
             and 'NOTHING was scanned' in o)
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
