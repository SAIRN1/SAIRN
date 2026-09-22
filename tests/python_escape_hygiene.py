r"""No Python file in tools/ or tests/ may compile with a SyntaxWarning.

Run: python tests/python_escape_hygiene.py

WHY THIS EXISTS, and it is not tidiness. `"\s"` in a non-raw string is an
INVALID ESCAPE SEQUENCE. Python currently keeps the backslash and warns; the
warning's own text says "such sequences will not work in the future", and
CPython has been walking this from DeprecationWarning to SyntaxWarning to a
planned SyntaxError. So every one of these is a file that compiles today and
stops compiling on a future interpreter -- on a platform where tools/ holds the
gates and tests/ holds the controls.

THE SHARPER HALF IS WHERE IT WAS FOUND. tests/run_temporary_state_probe.py
carried one in its module docstring, and the push gate printed it inside EVERY
generated-document refusal tonight -- nested in the middle of a block of real
findings, in a tool's own output, over and over. A warning that appears beside
findings and means nothing is training to skim the findings. That is the cost
this check is really for, and it is why the answer is a gate rather than a
one-line fix to one file.

WHAT IT DOES NOT DO. It compiles; it does not import and it does not execute,
so a file with a bad escape inside a branch nobody runs is still caught, and a
file with a genuine runtime bug is not. Compilation is the whole scope and the
docstring says so rather than leaving a reader to infer it.

THIS FILE CAUGHT ITSELF ON ITS FIRST RUN, which is the demonstration and is
kept rather than tidied away: the docstring you are reading quotes the very
escape it is about, so the check reported its own author before it reported
anybody else. The docstring is raw now, which is the same fix it recommends.

THE FIX IS ALMOST ALWAYS A RAW STRING, not an escaped backslash: `r"..."`
preserves the text exactly, while `\\s` changes what the string CONTAINS, which
matters when the string is prose somebody reads or a regex somebody edits.
"""
import glob
import io
import os
import sys
import warnings

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# tools/ and tests/ only. Not api/ (no Python), not archive/ -- CLAUDE.md says
# the preserved ancestor branch must not be run or recreated, and scanning it
# would report dead 2026-06 snapshots forever.
PATTERNS = ('tools/*.py', 'tests/*.py', 'tests/**/*.py')


def offenders():
    """[(relpath, [messages])] for every file that compiles with a SyntaxWarning."""
    seen, out = set(), []
    for pat in PATTERNS:
        for path in sorted(glob.glob(os.path.join(REPO, pat), recursive=True)):
            rel = os.path.relpath(path, REPO).replace('\\', '/')
            if rel in seen:
                continue
            seen.add(rel)
            try:
                src = io.open(path, encoding='utf-8').read()
            except (OSError, UnicodeDecodeError) as e:
                # COULD NOT READ is not CLEAN. A file this cannot open is
                # reported rather than skipped, for the reason PR 1.11 states.
                out.append((rel, ['COULD NOT READ: %s' % e]))
                continue
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                try:
                    compile(src, path, 'exec')
                except SyntaxError as e:
                    out.append((rel, ['DOES NOT COMPILE AT ALL: %s' % e]))
                    continue
                msgs = [str(x.message) for x in w
                        if issubclass(x.category, SyntaxWarning)]
            if msgs:
                out.append((rel, msgs))
    return seen, out


def main():
    print('python escape hygiene -- an invalid escape is a file that stops '
          'compiling later\n')
    seen, bad = offenders()
    print('  scanned: %d file(s) across %s' % (len(seen), ', '.join(PATTERNS)))
    if not seen:
        # A scan that reached nothing is not a pass. Same rule the rest of this
        # repo applies to an empty result set.
        print('\nCOULD NOT RUN: the scan matched no files at all, so nothing was '
              'checked. That is not clean.')
        return 3
    for rel, msgs in bad:
        print('  FAIL %s' % rel)
        for m in msgs:
            print('         %s' % m)
    if bad:
        print('\n%d file(s) carry a SyntaxWarning. The fix is almost always a RAW '
              'string -- r"..." keeps the text exactly as written, while doubling '
              'the backslash changes what the string contains.' % len(bad))
        return 1
    print('  ok   no file emits a SyntaxWarning')
    return 0


if __name__ == '__main__':
    sys.exit(main())
