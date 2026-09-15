"""sabotage.py -- plant a defect so that FAILING TO PLANT IT IS LOUD.

    python tools/sabotage.py --selftest

── THE CLASS THIS CONSOLIDATES ───────────────────────────────────────────────
A negative control breaks a real source file, runs the checker, and asserts it
goes red. The sabotage is almost always `src.replace(anchor, ...)`. When the
target is refactored the anchor stops matching, **str.replace silently does
nothing**, and the control runs the checker against an unmodified file.

`tools/sabotage_control_check.py` measures how widespread that is. Measured
2026-09-15: **50 probes sabotage a real source file, 39 verify the sabotage
applied, 11 do not.** (The figure quoted in the 2026-09-13 write-up was 23 of
39; the class has improved since, and re-measuring rather than repeating the
remembered number is the whole point.)

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

── WHAT THIS DOES NOT DO ────────────────────────────────────────────────────
It does not decide whether the checker's verdict afterwards is correct — a
control can plant perfectly and still assert the wrong thing. It does not answer
whether the anchor is a MEANINGFUL defect rather than a cosmetic edit. And it
does not migrate the 11: each needs its own reading, and a mechanical rewrite of
somebody else's control is how a working control becomes a broken one.
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

    print('')
    print('  all arms pass' if ok else '  ARMS FAILED -- do not trust this module')
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(_selftest() if '--selftest' in sys.argv[1:] else
             (print(__doc__.strip().split('\n')[0]) or 2))
