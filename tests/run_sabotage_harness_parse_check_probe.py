"""The shared harness must tell a REFUSED mutant from one that fails to PARSE.

Run: python tests/run_sabotage_harness_parse_check_probe.py

# REQUIREMENT: run_probe()'s per-mutation verdict must distinguish "the suite
#   refused the planted defect" from "the mutant has a syntax error and the
#   suite crashed on it" -- a parsing, genuinely-caught mutation still reports
#   CAUGHT, a non-parsing one FAILS the arm as MALFORMED-MUTATION naming the
#   parse error, and the two must never print the same verdict

WHY THIS EXISTS. Until 2026-09-25 the verdict was `rc != 0`, full stop.
Eleven probes run through run_probe(), and for every one of them a mutation
with an unbalanced brace was indistinguishable from a rule being enforced --
found when fourth's 2026-09-23T18:54:03Z review asked whether one specific
arm's mutant was "still a faithful mutation" and the only honest answer was
that nothing in the harness could say. Both directions are driven here against
the SAME committed fixtures the multiedit probe already uses, so the subject's
behaviour is known by construction.

The .py and .html halves of _parse_error() are driven directly against temp
files rather than through a worktree run -- the worktree half is identical
code and the expensive part is already proven by the .js directions.
"""
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sabotage_harness                                        # noqa: E402
from sabotage_harness import run_probe, _parse_error           # noqa: E402

SUITE = os.path.join('tests', 'fixtures', 'harness_multiedit_suite.js')
SRC = os.path.join('tests', 'fixtures', 'harness_multiedit_src.js')

GUARD_A = "  if (first === 'UNKNOWN') { return 'REFUSED'; }   // GUARD A"
GUARD_C = "  if (classify(body) !== 'WROTE') { return 'REFUSED'; }   // GUARD C"
DEAD_A = "  if (false) { return 'REFUSED'; }   // GUARD A"
DEAD_C = "  if (false) { return 'REFUSED'; }   // GUARD C"
# One brace short of parsing: the exact malformed-mutant shape the old verdict
# scored as CAUGHT.
BROKEN_A = "  if (false { return 'REFUSED'; }   // GUARD A"


def _capture(fn):
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

    print('the shared harness must tell a refusal from a syntax error\n')

    # ── 1. THE CONTROL DIRECTION: a parsing, caught mutation still passes ──
    rc, out = _capture(lambda: run_probe(
        SUITE,
        [('both guards removed together', SRC, [GUARD_A, GUARD_C], [DEAD_A, DEAD_C])],
        title='(inner) a parsing mutant is still CAUGHT', stage=(SUITE, SRC)))
    check('1. CONTROL: a mutation that parses and is refused still reports '
          'CAUGHT (probe exit 0)', rc == 0, out.strip()[-300:])
    check('   ...with no MALFORMED-MUTATION line anywhere',
          'MALFORMED-MUTATION' not in out)

    # ── 2. THE FIX DIRECTION: a NON-PARSING mutant fails the arm, named ────
    rc, out = _capture(lambda: run_probe(
        SUITE,
        [('a mutant one brace short of parsing', SRC, GUARD_A, BROKEN_A)],
        title='(inner) a non-parsing mutant is MALFORMED, not CAUGHT',
        stage=(SUITE, SRC)))
    check('2. a non-parsing mutant FAILS its arm (probe exit 1)', rc == 1,
          out.strip()[-300:])
    check('   ...as MALFORMED-MUTATION naming the parse error, never CAUGHT',
          'MALFORMED-MUTATION' in out and 'does not parse' in out,
          out.strip()[-300:])
    check('   ...and the suite was NEVER RUN against gibberish -- the baseline '
          'and restore arms stay green',
          'GREEN again with everything restored' in out)

    # ── 3. THE OTHER TWO EXTENSIONS, driven directly ───────────────────────
    with tempfile.TemporaryDirectory() as td:
        io.open(os.path.join(td, 'ok.py'), 'w', encoding='utf-8').write('x = 1\n')
        io.open(os.path.join(td, 'bad.py'), 'w', encoding='utf-8').write('def f(:\n')
        check('3. a clean .py parses (None)', _parse_error(td, 'ok.py') is None)
        err = _parse_error(td, 'bad.py')
        check('   a broken .py is named', bool(err) and 'SyntaxError' in err,
              repr(err))
        io.open(os.path.join(td, 'ok.html'), 'w', encoding='utf-8').write(
            '<html><script>var a = 1;</script><script src="x.js"></script></html>')
        io.open(os.path.join(td, 'bad.html'), 'w', encoding='utf-8').write(
            '<html><script>var a = ;</script></html>')
        check('   a clean .html (inline block + src= skipped) parses',
              _parse_error(td, 'ok.html') is None)
        err = _parse_error(td, 'bad.html')
        check('   a broken inline script block is named', bool(err)
              and 'script block' in err, repr(err))
        io.open(os.path.join(td, 'x.sql'), 'w', encoding='utf-8').write('junk(\n')
        check('   an unknown extension answers None -- the caller prints the '
              'stated no-parse-check note instead', _parse_error(td, 'x.sql') is None)

    print('')
    if fails:
        print('%d arm(s) FAILED: %s' % (len(fails), ', '.join(fails)))
        return 1
    print('all arms pass -- a refusal and a syntax error no longer share a verdict')
    return 0


if __name__ == '__main__':
    sys.exit(main())
