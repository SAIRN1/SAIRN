"""The shared sabotage harness's MULTI-EDIT mutation must plant both edits, or
refuse -- it must never plant half a defect and report on the whole one.

Run: python tests/run_sabotage_harness_multiedit_probe.py

# REQUIREMENT: a mutation whose `old`/`new` are lists must apply EVERY edit
#   together, must FAIL (not skip, not silently half-apply) when any one of its
#   anchors is stale or ambiguous, and must leave a plain-string mutation
#   behaving byte-for-byte as it did before -- because 25+ negative controls on
#   this platform run through this one function, and a harness that quietly
#   plants a partial defect turns every one of them into a green run that
#   proved less than it says

WHY THIS EXISTS. `tests/sabotage_harness.py` gained multi-edit mutations on
2026-09-21 so that api/sc-credentials.js's two MUTUALLY REDUNDANT unknown-write
guards could be sabotaged together -- removing either alone is silent by
construction, so the only statable property is the conjunction. The harness had
no self-test of any kind at that point, and it is the single point every
negative control on this platform passes through.

THE FAILURE MODE THE CHANGE INTRODUCED IS A QUIET ONE, which is why it is
guarded here rather than checked once by hand: if a pair mutation's SECOND
anchor goes stale, the obvious implementation plants the first edit, finds the
suite still red for the first edit's reason, and reports the pair as refused.
That is a control reporting on a defect it did not plant.

IT IS DRIVEN AGAINST A FIXTURE, NOT AGAINST REAL CODE, and deliberately: the
fixture's two guards are redundant BY CONSTRUCTION, so "removing one alone is
silent" is a property of the subject rather than a guess about it. Both fixture
files are staged into the worktree like any other uncommitted subject.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sabotage_harness                                        # noqa: E402
from sabotage_harness import run_probe                         # noqa: E402

SUITE = os.path.join('tests', 'fixtures', 'harness_multiedit_suite.js')
SRC = os.path.join('tests', 'fixtures', 'harness_multiedit_src.js')

GUARD_A = "  if (first === 'UNKNOWN') { return 'REFUSED'; }   // GUARD A"
GUARD_C = "  if (classify(body) !== 'WROTE') { return 'REFUSED'; }   // GUARD C"
DEAD_A = "  if (false) { return 'REFUSED'; }   // GUARD A"
DEAD_C = "  if (false) { return 'REFUSED'; }   // GUARD C"


def _capture(fn):
    """Run fn() with stdout captured, returning (exit code, text)."""
    buf = io.StringIO()
    real, sys.stdout = sys.stdout, buf
    try:
        rc = fn()
    finally:
        sys.stdout = real
    return rc, buf.getvalue()


def main():
    fails = []

    def check(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '  ' + detail))
        if not cond:
            fails.append(name)

    print('the shared harness must plant BOTH edits of a pair, or refuse\n')

    # ── 1. THE PAIR IS PLANTED AND THE SUITE NOTICES ──────────────────────
    rc, out = _capture(lambda: run_probe(
        SUITE,
        [('both guards removed together', SRC, [GUARD_A, GUARD_C], [DEAD_A, DEAD_C])],
        title='(inner) a pair mutation plants both edits', stage=(SUITE, SRC)))
    check('1. a PAIR mutation is planted and the suite refuses it', rc == 0,
          out.strip()[-300:])

    # ── 2. AND NEITHER HALF ALONE IS OBSERVABLE, WHICH IS THE WHOLE POINT ──
    # These two inner probes are EXPECTED TO REPORT SILENT. If either bites on
    # its own then the fixture's guards are not redundant and arm 1 proves
    # nothing about pairs -- it would just be a single mutation in a list.
    for label, old, new in [('A', GUARD_A, DEAD_A), ('C', GUARD_C, DEAD_C)]:
        rc, out = _capture(lambda o=old, n=new: run_probe(
            SUITE, [('one guard alone', SRC, o, n)],
            title='(inner) single guard', stage=(SUITE, SRC)))
        check('2%s. guard %s removed ALONE is SILENT -- the fixture\'s guards '
              'really are redundant, so arm 1 is about the pair'
              % (label.lower(), label),
              rc == 1 and 'SILENT' in out, out.strip()[-200:])

    # ── 3. A STALE SECOND ANCHOR IS A FAILURE, NOT A HALF-PLANT ───────────
    # The quiet failure mode. Without the per-edit anchor check the first edit
    # lands, the suite is red for THAT reason, and the pair is credited.
    rc, out = _capture(lambda: run_probe(
        SUITE,
        [('pair whose SECOND anchor is stale', SRC,
          [GUARD_A, "  if (classify(body) !== 'NOPE') { return 'REFUSED'; }"],
          [DEAD_A, DEAD_C])],
        title='(inner) stale second anchor', stage=(SUITE, SRC)))
    check('3. a pair with a STALE SECOND ANCHOR fails as ANCHOR-0, and is not '
          'credited for a defect it never planted',
          rc == 1 and 'ANCHOR-0' in out and 'edit 2 of 2' in out,
          out.strip()[-300:])

    # ── 4. AN AMBIGUOUS ANCHOR IS ALSO A FAILURE ──────────────────────────
    rc, out = _capture(lambda: run_probe(
        SUITE,
        [('pair whose first anchor matches twice', SRC,
          ["return 'REFUSED';", GUARD_C], ["return 'X';", DEAD_C])],
        title='(inner) ambiguous first anchor', stage=(SUITE, SRC)))
    check('4. an AMBIGUOUS anchor in a pair fails as ANCHOR-2 rather than '
          'planting in whichever came first',
          rc == 1 and 'ANCHOR-2' in out and 'edit 1 of 2' in out,
          out.strip()[-300:])

    # ── 5. MISMATCHED LENGTHS ARE REFUSED RATHER THAN ZIPPED SHORT ────────
    # `zip` stops at the shorter list, so without this the extra edit would be
    # dropped in silence -- a pair mutation quietly becoming a single.
    rc, out = _capture(lambda: run_probe(
        SUITE,
        [('two olds, one new', SRC, [GUARD_A, GUARD_C], [DEAD_A])],
        title='(inner) mismatched lengths', stage=(SUITE, SRC)))
    check('5. a mutation with 2 old texts and 1 new is MALFORMED, not zipped '
          'short into a single edit', rc == 1 and 'MALFORMED' in out,
          out.strip()[-200:])

    # ── 6. A PLAIN STRING IS UNCHANGED, BYTE FOR BYTE ─────────────────────
    # 25+ existing controls pass a string. The normalisation must be invisible
    # to them: one edit, same anchor rules, same message with no "edit 1 of 1".
    rc, out = _capture(lambda: run_probe(
        SUITE,
        [('a plain string mutation', SRC,
          "  if (body.length === 0) return 'MISSED';",
          "  if (body.length === 0) return 'WROTE';")],
        title='(inner) plain string', stage=(SUITE, SRC)))
    check('6. a PLAIN STRING mutation still bites, with no pair wording in its '
          'message', rc == 0 and 'edit 1 of 1' not in out, out.strip()[-200:])

    rc, out = _capture(lambda: run_probe(
        SUITE, [('a plain string with a stale anchor', SRC,
                 "this text is not in the fixture", "x")],
        title='(inner) plain string, stale', stage=(SUITE, SRC)))
    check('6b. ...and a stale PLAIN anchor still reports a bare ANCHOR-0 with '
          'no edit numbering', rc == 1 and 'ANCHOR-0' in out
          and 'edit 1 of 1' not in out, out.strip()[-200:])

    print('\n' + ('%d ARM(S) FAILED' % len(fails) if fails
                  else 'ALL ARMS PASS -- the multi-edit path plants both edits '
                       'or refuses, and a single-string mutation is unchanged'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
