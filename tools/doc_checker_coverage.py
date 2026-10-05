# OWNER: cc
"""tools/doc_checker_coverage.py -- which markdown files this change TOUCHES are
read by NO structural checker.

── WHY THIS EXISTS, AND IT IS A MEASURED ANSWER TO A MEASURED QUESTION ────────
On 2026-10-05 five instrument failures of mine were written up, and the honest
note at the end of that write-up was: *four of the five were found by measuring
my own claims and the fifth by an assertion; NONE was found by a cadenced
check, so the next of this class also waits for somebody to look.*

Two of those five share one cause this tool can see:

  * A `|` inside a code span malformed a row of `docs/CRITICALITY-TIERS.md`,
    nine days after the lesson was written up. `md_table_check.py` DID NOT SEE
    IT, because that file was not in its `DEFAULT_FILES`. The discipline did
    not fail -- the instrument did not read the file.

  * BECAUSE the real tool was blind to that file, I hand-rolled a one-off
    checker, which then FALSE-FLAGGED three HEADER rows in an unrelated
    document. Narrow coverage does not merely miss defects, it manufactures a
    worse instrument, and the session trusts it.

BOTH WOULD HAVE BEEN ANSWERED BY ONE QUESTION ASKED AT COMMIT TIME: *is the
markdown file I am editing read by anything?* If the answer had been "no", the
first failure becomes a coverage fix instead of a malformed row, and the second
never happens because there is no reason to hand-roll.

THE QUESTION IS CHEAP AND IT IS NOT A WISH-LIST ITEM. It needs no new
convention: checkers on this platform already declare their file sets as
module-level uppercase lists of repo-relative `.md` paths, and this reads them
out of the source with `ast` rather than importing -- an import runs
module-level code, and a coverage report must not be able to change what it
measures.

── WHAT IT DELIBERATELY DOES NOT DO ──────────────────────────────────────────
It does NOT say an uncovered file is wrong. Most markdown in this repo is prose
and needs no structural check; a session handoff with no tables wants none. The
output is a LIST TO READ, and the judgement -- is this file one whose structure
matters -- stays with the person. A gate here would be cleared by deleting a
table, which is worse than the gap.

── THE DENOMINATOR IS PUBLISHED, because discipline 8 requires it ─────────────
A coverage tool that does not say what it could not read is the defect it exists
to find. Every run prints: how many `tools/*.py` were parsed, how many declared
a doc file set, and how many could not be parsed AT ALL -- named, never absent.
A file set built from a glob, a config read at run time, or a list assembled
inside a function is INVISIBLE to this tool, and a checker covering your file
that way will be reported as not covering it. That is a FALSE "uncovered", it
is the known weakness, and it is printed on every run rather than buried here.

── IT FAILS CLOSED (PR 1.11) ──────────────────────────────────────────────────
Exit 2 COULD NOT RUN -- never 0 -- when git cannot be read, when no checker
module can be parsed at all, or when `--range` names something git rejects. A
coverage report that quietly measured nothing would be the fifth instance of
the class above.

Exit 1 only with `--strict`, which nothing wires today; the default is report-
only, exit 0.

CLI:
    python tools/doc_checker_coverage.py              # staged + unstaged
    python tools/doc_checker_coverage.py --range A..B  # a commit range
    python tools/doc_checker_coverage.py --all         # every tracked .md
    python tools/doc_checker_coverage.py --selftest    # fixtures, both ways
"""
import ast
import glob
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COULD_NOT_RUN = 2


def die(why, detail=''):
    print('COULD NOT RUN -- this is not a pass.')
    print('  ' + why)
    if detail:
        for line in str(detail).rstrip().split('\n')[-8:]:
            print('    ' + line[:200])
    sys.exit(COULD_NOT_RUN)


def git(*args):
    p = subprocess.run(('git',) + args, cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        die('git %s failed, so the changed-file set is unknown.' % ' '.join(args),
            p.stderr)
    return p.stdout


def declared_coverage():
    """Every repo-relative .md path any tools/*.py declares in a module-level
    uppercase list, read with ast so nothing is executed.

    Returns (coverage, parsed, unparseable) -- the last two ARE the denominator
    and the caller must print them.
    """
    coverage, parsed, unparseable = {}, 0, []
    for path in sorted(glob.glob(os.path.join(REPO, 'tools', '*.py'))):
        rel = os.path.relpath(path, REPO).replace('\\', '/')
        try:
            tree = ast.parse(open(path, encoding='utf-8', errors='replace').read())
        except SyntaxError as e:
            unparseable.append((rel, 'SyntaxError line %s' % e.lineno))
            continue
        except OSError as e:
            unparseable.append((rel, repr(e)[:60]))
            continue
        parsed += 1
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not (node.targets and isinstance(node.targets[0], ast.Name)):
                continue
            name = node.targets[0].id
            if not name.isupper():
                continue
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                continue
            for el in node.value.elts:
                if isinstance(el, ast.Constant) and isinstance(el.value, str) \
                        and el.value.endswith('.md'):
                    coverage.setdefault(el.value.replace('\\', '/'), []).append(
                        '%s:%s' % (os.path.basename(rel), name))
    if parsed == 0:
        die('no tools/*.py could be parsed, so no coverage could be derived. '
            'Reporting "nothing is covered" from that state would be a '
            'confident wrong answer.')
    return coverage, parsed, unparseable


def changed_md(argv):
    if '--all' in argv:
        out = git('ls-files', '*.md')
        return sorted(f for f in out.split('\n') if f.strip()), 'every tracked .md'
    for i, a in enumerate(argv):
        if a == '--range':
            if i + 1 >= len(argv):
                die('--range needs a revision range, e.g. --range HEAD~3..HEAD')
            rng = argv[i + 1]
            out = git('diff', '--name-only', rng)
            return (sorted(f for f in out.split('\n')
                           if f.strip().endswith('.md')), 'range %s' % rng)
    out = git('status', '--porcelain')
    files = []
    for line in out.split('\n'):
        if len(line) > 3 and line[3:].strip().endswith('.md'):
            files.append(line[3:].strip().strip('"'))
    return sorted(set(files)), 'working tree (staged + unstaged)'


def selftest():
    """Both directions, on fixtures, because a coverage tool that cannot report
    a gap and a coverage tool that reports every file as a gap look identical
    from a clean run."""
    ok = True
    cov, parsed, unparseable = declared_coverage()
    # KNOWN-COVERED: md_table_check declares this one, so it must NOT be a gap.
    known = 'docs/SAIRN-OPEN-WORK-INDEX.md'
    if known not in cov:
        print('FAIL selftest: %s is declared by md_table_check and was not '
              'found -- the reader is broken, not the coverage' % known)
        ok = False
    else:
        print('ok   known-COVERED file is seen as covered (%s)' % ', '.join(cov[known]))
    # KNOWN-UNCOVERED: a path no tool can be declaring.
    ghost = 'docs/this-file-is-declared-by-nothing-%d.md' % 987654
    if ghost in cov:
        print('FAIL selftest: a ghost path was reported as covered')
        ok = False
    else:
        print('ok   known-UNCOVERED file is seen as uncovered')
    print('ok   denominator published: %d parsed, %d unparseable, %d doc paths'
          % (parsed, len(unparseable), len(cov)))
    return 0 if ok else 1


def main(argv):
    if '--selftest' in argv:
        return selftest()
    cov, parsed, unparseable = declared_coverage()
    files, how = changed_md(argv)

    print('DOC CHECKER COVERAGE -- %s' % how)
    print('  DENOMINATOR, published rather than implied:')
    print('    %d tools/*.py parsed, %d declared doc paths, %d UNPARSEABLE'
          % (parsed, len(cov), len(unparseable)))
    for rel, why in unparseable:
        print('      could not read: %s (%s)' % (rel, why))
    print('    NOTE: a file set built from a glob, a config, or assembled '
          'inside a function is INVISIBLE here, so an "uncovered" verdict can '
          'be wrong in the safe direction -- it over-reports gaps.')
    print()

    if not files:
        print('  No markdown files in scope. Nothing to say.')
        return 0

    covered, gaps = [], []
    for f in files:
        who = cov.get(f.replace('\\', '/'))
        (covered if who else gaps).append((f, who))

    for f, who in covered:
        print('  covered    %-56s %s' % (f, ', '.join(who)))
    if gaps:
        print()
        print('  %d markdown file(s) in this change are read by NO declared '
              'checker:' % len(gaps))
        for f, _ in gaps:
            print('    UNCOVERED  %s' % f)
        print()
        print('  THIS IS A LIST TO READ, NOT A VERDICT. Most markdown here is '
              'prose and wants no structural check. The question worth asking '
              'is the one that was missed on 2026-10-05: does this file carry '
              'TABLES whose structure matters, and if so should it join '
              "md_table_check.py's DEFAULT_FILES rather than get a hand-rolled "
              'checker?')
    else:
        print()
        print('  Every markdown file in this change is read by something.')

    if '--strict' in argv and gaps:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
