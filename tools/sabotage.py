"""sabotage.py -- plant a defect so that FAILING TO PLANT IT IS LOUD.

    python tools/sabotage.py --selftest

── THE CLASS THIS CONSOLIDATES ───────────────────────────────────────────────
A negative control breaks a real source file, runs the checker, and asserts it
goes red. The sabotage is almost always `src.replace(anchor, ...)`. When the
target is refactored the anchor stops matching, **str.replace silently does
nothing**, and the control runs the checker against an unmodified file.

`tools/sabotage_control_check.py` measures how widespread that is. **Re-measured
2026-10-20: 107 probes sabotage a real source file, 99 verify the sabotage
applied, 8 do not.** (This paragraph said *50 / 39 / 11, measured 2026-09-15*
for five weeks; the 2026-09-13 write-up before it said 23 of 39. The population
has more than doubled and the unguarded count has fallen in absolute terms.
Three stale figures in one place is why the next line exists.) **Run the tool;
do not quote any of these numbers from here** — re-measuring rather than
repeating the remembered number is the whole point and this file was not
exempt from it.

That tool answers *"is this control guarded?"*. This module is the other half:
**the thing to reach for so the next control is guarded by construction rather
than by remembering.**

── THREE APPROACHES ALREADY EXIST HERE AND EACH IS RIGHT ABOUT A DIFFERENT
── FAILURE. THAT IS THE RECOMBINATION.

  PRESENCE        `assert anchor in src`
                  Catches a RENAME. Blind to an anchor that matches in four
                  places.

  UNIQUENESS      `if src.count(anchor) != 1: refuse`
                  `tests/failsafe/countersign_coverage_probe.py` does this, and
                  reports could-not-test rather than skipping. Catches hitting
                  the WRONG SITE.

  MATERIALISATION read the file back and look for the marker
                  `tests/sairncode_gates_mutation_control.js` asserts "the
                  mutation is present in the bytes on disk", because a claim
                  about a string in memory is not a claim about what the next
                  process will read.

**AND A FOURTH THAT AVOIDS ANCHORS ENTIRELY.** `tools/guard_ablation.py` ablates
BY LINE NUMBER, and its comment is the argument: `if
(!CRM_MANAGEMENT_ROLES[session.role]) {` appears at FOUR sites, so four real
gates became four non-answers — *"and `replace(..., 1)` would silently have hit
the first one four times if the count had not been checked."* A line index
cannot be ambiguous. It still re-reads the line and asserts it matches before
touching it, so a stale index refuses instead of damaging a random line.

None of the four is a substitute for the others, which is why this module offers
both planting strategies and applies presence, uniqueness and materialisation to
each rather than picking a house style.

── COULD-NOT-SABOTAGE IS A THIRD STATE AND IS NEVER A SKIP ──────────────────
Every refusal here raises `CouldNotSabotage`. It is deliberately an EXCEPTION
and not a return value: a caller that ignores a returned `None` writes exactly
the silent no-op this exists to remove, and on this platform PR §1.11 already
says a check that could not run must never be folded into a pass.

── AND A LAYER OUT: THE PLANT CAN LAND AND THE TEST PATH STILL NOT RUN ──────
**A probe must prove the path under test actually executed before it reports a
verdict.** Everything above answers *"is the defect in the file?"*. That is not
the same question as *"did the thing being tested look at the file?"*, and on
2026-10-20 the difference cost a verdict: cc's b26 CHECK 5d harness planted an
out-of-scope path for the `hank` population, the plant was written to disk
correctly, and the **pre-commit** hook then refused the commit (a `tools/*.py`
with no inventory entry). The commit never happened. The harness drove the
pre-push hook over a **clean tree**, read exit 0, and reported hank
**ALLOWED** — a probe reporting a verdict on a test it never ran, and the
friendliest possible wrong answer: *"the gate did not refuse."*

`verdict()` is the only thing in this module that hands back a verdict, and it
cannot produce one without the evidence that the subject was inside what the
test actually examined. Absent that it returns `INCONCLUSIVE`, which is neither
a pass nor a fail. `tally()` then keeps it out of both buckets, because *"4 of
5 refused"* over four real refusals and one untested case is the b26 defect
surviving into the write-up.

── WHAT THIS DOES NOT DO ────────────────────────────────────────────────────
It does not decide whether the checker's verdict afterwards is correct — a
control can plant perfectly and still assert the wrong thing. It does not answer
whether the anchor is a MEANINGFUL defect rather than a cosmetic edit. And it
does not migrate the 11: each needs its own reading, and a mechanical rewrite of
somebody else's control is how a working control becomes a broken one.

`verdict()` cannot be forced on a caller either: a harness that never calls it
still prints whatever it likes. What it removes is having to re-invent the
ran-check per probe, which is why b26's was inline and local and why no other
probe in the repo had one.
"""
import io
import os
import sys


class CouldNotSabotage(Exception):
    """The defect was NOT planted. Never catch this to continue."""


def plant(src, anchor, replacement, occurrences=1):
    """Replace `anchor` with `replacement`, refusing unless it occurs exactly
    `occurrences` times.

    Returns the mutated text. Raises CouldNotSabotage with the real count, so
    the message says *why* rather than that something went wrong.
    """
    if not anchor:
        raise CouldNotSabotage('empty anchor: nothing to plant')
    n = src.count(anchor)
    if n != occurrences:
        raise CouldNotSabotage(
            'anchor occurs %d time(s), expected %d -- the target has probably '
            'been refactored. THE CONTROL DID NOT RUN; this is not a pass.\n'
            '  anchor: %r' % (n, occurrences, anchor[:120]))
    out = src.replace(anchor, replacement, occurrences)
    if out == src:
        # Reachable when replacement == anchor, which is the purest form of the
        # bug: a sabotage that changes nothing and then reports on an untouched
        # file.
        raise CouldNotSabotage(
            'the replacement is identical to the anchor, so nothing changed')
    return out


def plant_at_line(src, line_number, expected, replacement):
    """Ablate BY LINE NUMBER, the `guard_ablation.py` strategy.

    `line_number` is 1-based. `expected` is what that line must currently be
    (compared after stripping trailing whitespace) -- a stale index refuses
    rather than damaging a random line.
    """
    lines = src.split('\n')
    idx = line_number - 1
    if idx < 0 or idx >= len(lines):
        raise CouldNotSabotage(
            'line %d is outside a file of %d lines' % (line_number, len(lines)))
    if lines[idx].rstrip() != expected.rstrip():
        raise CouldNotSabotage(
            'line %d is not what this control expects, so the index is stale '
            'and ablating it would damage an unrelated line.\n'
            '  expected: %r\n  found   : %r'
            % (line_number, expected.strip()[:100], lines[idx].strip()[:100]))
    lines[idx] = replacement
    return '\n'.join(lines)


def write_and_verify(path, text, marker):
    """Write the mutant and prove the marker is in the BYTES ON DISK.

    The in-memory check says the string was built. This says the next process
    will read it -- a different claim, and the one that matters when the
    checker runs in a subprocess.

    `newline=''` on both sides: a control that flips a CRLF file's line endings
    while planting a one-line defect produces a diff nobody can review, and on a
    checker that reads line endings it would be sabotaging two things at once.
    """
    with io.open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    with io.open(path, encoding='utf-8', errors='replace', newline='') as fh:
        on_disk = fh.read()
    if marker not in on_disk:
        raise CouldNotSabotage(
            'the mutant was written to %s but the marker is not in the bytes '
            'read back. THE CONTROL DID NOT RUN.\n  marker: %r'
            % (path, marker[:120]))
    return on_disk


class Planted(object):
    """Context manager: plant, run the body, always restore.

    Restores from the text read at ENTRY. That is correct for one control and
    WRONG if two run concurrently against the same file -- the second snapshots
    the first's mutation as its 'original' and restores it. This platform has
    had that exact incident. **Prefer a throwaway git worktree over this for
    anything that runs in the suite**; the docstring says so rather than the
    class pretending to be safe.
    """

    def __init__(self, path, marker=None):
        self.path = path
        self.marker = marker
        self.original = None

    def __enter__(self):
        with io.open(self.path, encoding='utf-8', errors='replace', newline='') as fh:
            self.original = fh.read()
        return self

    def apply(self, mutated):
        return write_and_verify(self.path, mutated, self.marker or mutated[:0] or ' ')

    def __exit__(self, *exc):
        if self.original is not None:
            with io.open(self.path, 'w', encoding='utf-8', newline='') as fh:
                fh.write(self.original)
        return False


INCONCLUSIVE = 'INCONCLUSIVE'


def verdict(decided, subject, examined, label='the path under test'):
    """The only verdict this module hands back, and it needs the ran-check.

    `decided` is what the probe observed (e.g. 'REFUSED' / 'ALLOWED').
    `subject` is the thing that had to be under test -- a planted path, a
    marker, a line.  `examined` is the text of what the test path ACTUALLY
    looked at: the outgoing range, the file list the checker was handed, the
    checker's own echo of its input.  Not the probe's intent, and not the
    bytes on disk -- `write_and_verify` already covers disk, and b26's plant
    was on disk the whole time.

    Returns `(verdict, why)`.  `verdict` is `decided` only when `subject`
    appears in `examined`; otherwise it is `INCONCLUSIVE` and `why` says what
    was looked for and what the test path contained instead.

    `decided` may not itself be INCONCLUSIVE: a caller passing it in has
    already made the judgement this function exists to make, and letting it
    through would mean the evidence was never consulted.
    """
    if decided == INCONCLUSIVE:
        raise CouldNotSabotage(
            'INCONCLUSIVE is this function\'s output, never its input -- pass '
            'what the probe OBSERVED and let the evidence decide')
    if not subject:
        raise CouldNotSabotage('empty subject: nothing to prove ran')
    examined = examined or ''
    if subject in examined:
        return decided, ''
    return INCONCLUSIVE, (
        'THE TEST PATH NEVER EXAMINED THE SUBJECT, so %r is not a result in '
        'either direction.\n'
        '  looked for : %r\n'
        '  %s saw     : %s'
        % (decided, subject[:160], label,
           (repr(examined.strip()[:300]) if examined.strip()
            else 'NOTHING AT ALL -- an empty range reads exactly like a clean one')))


def tally(rows):
    """Count a verdict table so an untested case cannot be quoted as a pass.

    `rows` is an iterable of `(name, got, want)`.  A row whose `got` is
    `INCONCLUSIVE` lands in its OWN bucket -- never in passed, never in
    failed -- and both counts are printed whether or not they are zero, so
    neither hides behind the other.

    Returns `(exit_code, lines)`.  0 only when every row was decided AND
    matched.  1 when something genuinely failed, which outranks an unknown
    because a confirmed failure is actionable.  2 -- the could-not-run code --
    when nothing failed but something never ran.
    """
    rows = list(rows)
    passed, failed, unran = [], [], []
    for name, got, want in rows:
        (unran if got == INCONCLUSIVE else
         passed if got == want else failed).append(name)
    lines = [
        '  %d of %d decided and matched' % (len(passed), len(rows)),
        '  %d decided and did NOT match%s'
        % (len(failed), (': ' + ', '.join(failed)) if failed else ''),
        '  %d INCONCLUSIVE -- counted in neither%s'
        % (len(unran), (': ' + ', '.join(unran)) if unran else ''),
    ]
    if unran:
        lines.append('  DO NOT QUOTE %d/%d: %d case(s) never ran.'
                     % (len(passed), len(rows), len(unran)))
    return (1 if failed else 2 if unran else 0), lines


def _selftest():
    ok = True

    def check(name, cond, detail=''):
        nonlocal ok
        print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + str(detail)))
        if not cond:
            ok = False

    def raises(fn, needle):
        try:
            fn()
        except CouldNotSabotage as e:
            return needle.lower() in str(e).lower()
        except Exception:
            return False
        return False

    src = 'a = 1\nif guard:\n    refuse()\nb = 2\nif guard:\n    refuse()\n'

    print('1. plant -- presence and uniqueness, both directions')
    check('a unique anchor is planted',
          plant(src, 'a = 1', 'a = 99').startswith('a = 99'))
    check('a MISSING anchor refuses, and says the count',
          raises(lambda: plant(src, 'nonexistent', 'x'), 'occurs 0 time'))
    check('a DUPLICATED anchor refuses rather than hitting the first',
          raises(lambda: plant(src, 'if guard:', 'if False:'), 'occurs 2 time'),
          'this is the guard_ablation case: four real gates became non-answers')
    check('...and says the control did not run',
          raises(lambda: plant(src, 'nope', 'x'), 'not a pass'))
    check('a no-op replacement refuses -- the purest form of the bug',
          raises(lambda: plant(src, 'a = 1', 'a = 1'), 'identical'))
    check('occurrences=2 accepts a deliberate double replace',
          plant(src, 'if guard:', 'if False:', occurrences=2).count('if False:') == 2)

    print('\n2. plant_at_line -- an index cannot be ambiguous, but it can be stale')
    check('the right line is ablated',
          plant_at_line(src, 2, 'if guard:', 'if False:').split('\n')[1] == 'if False:')
    check('a STALE index refuses instead of damaging a random line',
          raises(lambda: plant_at_line(src, 4, 'if guard:', 'x'), 'stale'))
    check('an out-of-range line refuses', raises(lambda: plant_at_line(src, 999, 'x', 'y'),
                                                 'outside a file'))
    check('trailing whitespace does not make a real match refuse',
          plant_at_line(src, 2, 'if guard:   ', 'if False:').split('\n')[1] == 'if False:')

    print('\n3. write_and_verify -- the bytes a process will actually read')
    import tempfile
    d = tempfile.mkdtemp(prefix='sabotage-selftest-')
    p = os.path.join(d, 'subject.py')
    io.open(p, 'w', encoding='utf-8', newline='').write(src)
    check('a real mutant verifies', 'if False:' in write_and_verify(
        p, plant(src, 'a = 1', 'a = 99') + 'if False:\n', 'if False:'))
    check('a marker that is NOT in the text refuses',
          raises(lambda: write_and_verify(p, src, 'never-appears'), 'not in the bytes'))

    print('\n4. CRLF is preserved -- a control must sabotage ONE thing')
    crlf = 'a = 1\r\nb = 2\r\n'
    io.open(p, 'w', encoding='utf-8', newline='').write(crlf)
    mutated = plant(crlf, 'a = 1', 'a = 99')
    write_and_verify(p, mutated, 'a = 99')
    back = io.open(p, encoding='utf-8', newline='').read()
    check('the file is still CRLF after planting', back == 'a = 99\r\nb = 2\r\n', repr(back))

    print('\n5. Planted restores, even when the body raises')
    io.open(p, 'w', encoding='utf-8', newline='').write(src)
    try:
        with Planted(p, marker='a = 99') as pl:
            pl.apply(plant(src, 'a = 1', 'a = 99'))
            raise RuntimeError('the checker blew up')
    except RuntimeError:
        pass
    check('the subject is restored after an exception',
          io.open(p, encoding='utf-8', newline='').read() == src)
    try:
        os.remove(p)
        os.rmdir(d)
    except OSError:
        pass

    print('\n6. CouldNotSabotage is an EXCEPTION, not a return value')
    check('it is an Exception subclass', issubclass(CouldNotSabotage, Exception))
    check('...so a caller cannot ignore it the way a returned None is ignored',
          not raises(lambda: plant(src, 'a = 1', 'a = 99'), 'x'),
          'a successful plant must not raise')

    print('\n7. verdict -- the ran-check: a plant on disk is not a test that ran')
    RANGE = 'tools/zz_probe.txt\napi/other.js\n'
    check('a subject INSIDE what the test path examined keeps its verdict',
          verdict('REFUSED', 'tools/zz_probe.txt', RANGE) == ('REFUSED', ''))
    v, why = verdict('ALLOWED', 'tools/zz_probe.txt', '')
    check('THE b26 CASE: plant absent from the outgoing range -> INCONCLUSIVE',
          v == INCONCLUSIVE, v)
    check('...and the reason says an empty range reads like a clean one',
          'NOTHING AT ALL' in why, why[:120])
    check('...and the friendly wrong answer ALLOWED is not what comes back',
          v != 'ALLOWED')
    v2, why2 = verdict('REFUSED', 'tools/zz_probe.txt', 'api/other.js\n')
    check('a NON-EMPTY range that simply lacks the subject is INCONCLUSIVE too',
          v2 == INCONCLUSIVE and 'api/other.js' in why2, (v2, why2[:80]))
    check('INCONCLUSIVE may not be passed IN -- that would skip the evidence',
          raises(lambda: verdict(INCONCLUSIVE, 'x', 'x'), 'never its input'))
    check('an empty subject refuses rather than matching everything',
          raises(lambda: verdict('REFUSED', '', RANGE), 'nothing to prove'))
    check('ABLATION: without the ran-check the same inputs give a VERDICT',
          ('ALLOWED' if 'tools/zz_probe.txt' else INCONCLUSIVE) == 'ALLOWED',
          'this arm is the counterfactual, not a test of the code')

    print('\n8. tally -- an untested case is not a denominator')
    code, lines = tally([('a', 'REFUSED', 'REFUSED'),
                         ('b', 'REFUSED', 'REFUSED'),
                         ('c', 'REFUSED', 'REFUSED'),
                         ('d', 'REFUSED', 'REFUSED'),
                         ('hank', INCONCLUSIVE, 'REFUSED')])
    check('4 decided + 1 inconclusive is NOT exit 0', code == 2, code)
    check('...the passed count is 4 of 5 and the inconclusive is named',
          '4 of 5 decided and matched' in lines[0] and 'hank' in lines[2],
          lines)
    check('...and it says in words not to quote the ratio',
          any('DO NOT QUOTE' in ln for ln in lines))
    check('a real failure outranks an unknown, and both still print',
          tally([('a', 'ALLOWED', 'REFUSED'), ('b', INCONCLUSIVE, 'REFUSED')])[0] == 1)
    check('...and the inconclusive is still visible in that same table',
          '1 INCONCLUSIVE' in tally([('a', 'ALLOWED', 'REFUSED'),
                                     ('b', INCONCLUSIVE, 'REFUSED')])[1][2])
    check('all decided and matched is the only exit 0',
          tally([('a', 'REFUSED', 'REFUSED')])[0] == 0)
    check('an EMPTY table is exit 0 and says 0 of 0 -- a run with no cases is '
          'not a pass to quote either',
          tally([])[0] == 0 and '0 of 0' in tally([])[1][0])

    print('')
    print('  all arms pass' if ok else '  ARMS FAILED -- do not trust this module')
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(_selftest() if '--selftest' in sys.argv[1:] else
             (print(__doc__.strip().split('\n')[0]) or 2))
