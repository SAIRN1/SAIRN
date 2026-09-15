"""The three things every SAIRN checker has had to get right, in one place.

Not a framework and not a base class. Four small functions and three integers,
extracted 2026-09-13 from the checkers that already work, so the NEXT checker is
built THROUGH the shape rather than re-deriving it and getting one third of it
wrong. `tools/metamorphic_check.py` is the first consumer and was written
against this module rather than the module being reverse-engineered from it.

    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
    from checker_kit import tracked, strip_comments, finish, controls_line

── WHY THESE THREE AND NOT A FRAMEWORK ──────────────────────────────────────
Because these are the three that have each been got wrong more than once in
this repo, in different tools, in ways nothing caught:

  1. THE EXIT-CODE CONTRACT. `literal_drift_check.py` was promoted into the
     report-only registry with `'verdict': by_exit` and NO `sys.exit` anywhere
     in it, so it could never report a finding through the registry that ran
     it -- whatever it printed. Its evidence line, "0 findings", is what a deaf
     checker looks like. Separately and worse, the push gate disabled NINE of
     its ten checks behind one `if not os.path.isfile(...)` and reported a pass
     it never performed (register records 39, 41, 42, 43, 46). **"Could not
     run" is a THIRD STATE and is never folded into "passed"** -- PR §1.11.

  2. COMMENT-STRIPPED PARSING. The house defect. `comment_quote_check.py`'s own
     first version blanked from any `//` to end of line and swallowed every
     `https://`; `literal_drift_check.py` counted comment prose as live
     literals until 2026-09-11; `mutation_anchor_check.py` flagged its own
     probe for carrying the pattern as a fixture string. Canonical rule:
     PR §1.2, "Grep cannot tell code from text that describes code".

  3. THE CONTROL PAIR. A checker that has never been seen to FAIL is a checker
     whose behaviour nobody knows, and its clean line is then evidence for the
     wrong conclusion. `checkblocks.py` always exited 0 and nothing noticed,
     because a checker that always passes looks exactly like a codebase that
     is always clean.

`tracked()` is here as the fourth because every one of the three needs a file
list and the exclusions have to be PRINTED -- see below.

── WHAT IS DELIBERATELY *NOT* HERE ──────────────────────────────────────────
**No existing checker was migrated onto this module.** Rewriting eleven live,
promoted checkers to import a module written the same hour is a change whose
blast radius is every gate in the repo, and it is not what "extract the
skeleton" asks for. This is for the next one.

**One duplication is named rather than silently inherited.** There are two
comment-strippers in `tools/` today: `comment_quote_check.strip_comments`
(comments only, canonical, what this module delegates to) and a second,
independent character scanner inside `tools/truthy_sum_check.py` that ALSO
blanks string interiors. The second exists for a real reason -- it was written
after that checker matched its own subject quoted inside a refusal message --
but two scanners for one job is the "second copy of something" shape the
Guardian skill says to resolve on discovery. It is NOT resolved here, because
migrating a checker with a 51-key baseline is its own change with its own
control run. `strings=True` below is a THIRD implementation only in the sense
that it is the one a NEW checker should use; the open row is to collapse
truthy_sum_check onto it once that migration can be proven.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

# ── 1. THE EXIT-CODE CONTRACT ────────────────────────────────────────────────
# Three states, never two. The whole point is that the third one exists.
EXIT_CLEAN = 0          # ran fully, found nothing
EXIT_FINDING = 1        # ran fully, found something
EXIT_COULD_NOT_RUN = 2  # did NOT run, or ran partially. NOT a pass.

# Files nothing in this repo should ever be reported against, with the reason.
# RETURNED AND PRINTED, never silently dropped -- a silent exclusion reads as
# "covered everything" when it did not.
EXCLUDED_PREFIXES = (
    ('archive/',
     'the preserved ancestor branch; CLAUDE.md says it must not be run or '
     'recreated, and scanning it reports dead 2026-06 snapshots forever'),
    ('docs/skill-backups/',
     "a stored copy of a third-party skill's bundled asset that nothing here "
     'deploys or maintains'),
)
BINARY_EXT = ('.zip', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.woff',
              '.woff2', '.ttf', '.mp4', '.xlsx', '.docx', '.pyc', '.map')


def tracked(*patterns):
    """(files, exclusion_notes) for git-tracked paths matching `patterns`.

    Returns the notes rather than printing them, so the CALLER prints them in
    its own report -- the discipline is that they appear in the output, and a
    helper that printed them itself would put them in the wrong place in a
    --json run.
    """
    if not patterns:
        patterns = ('*.html', '*.js')
    out = subprocess.run(['git', 'ls-files'] + list(patterns), cwd=REPO,
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    files = []
    for f in out.split('\n'):
        f = f.strip()
        if not f or f.lower().endswith(BINARY_EXT):
            continue
        if any(f.startswith(p) for p, _ in EXCLUDED_PREFIXES):
            continue
        files.append(f)
    notes = ['%s -- %s' % (p, why) for p, why in EXCLUDED_PREFIXES]
    return files, notes


# ── 2. COMMENT-STRIPPED PARSING ──────────────────────────────────────────────
def strip_comments(src, strings=False, sql=False):
    """Blank comment spans, preserving offsets so line numbers stay true.

    `strings=False` delegates to `comment_quote_check.strip_comments`, which is
    the canonical implementation and stays the single source for the
    comments-only question. Do not fork it.

    `strings=True` additionally blanks string-literal INTERIORS, keeping the
    delimiters so tokens still delimit. Use this when the checker's subject is
    CODE: a pattern that matches its own fix's prose is the same defect whether
    that prose lives in a comment or in a string, and the second form is the one
    that has actually bitten (`api/_lib/dental-ledger.js` quotes the truthy-sum
    pattern verbatim inside a refusal message).

    Offsets are preserved in both modes: spans are overwritten with spaces and
    newlines are kept, so every line number a caller reports still points at the
    real file.
    """
    from comment_quote_check import strip_comments as _canonical
    blanked = _canonical(src, sql=sql)
    if not strings:
        return blanked
    out, i, n, quote = [], 0, len(blanked), None
    while i < n:
        c = blanked[i]
        if quote:
            if c == '\\' and i + 1 < n:
                out.append('  ')
                i += 2
                continue
            if c == quote:
                out.append(c)
                quote = None
            else:
                out.append('\n' if c == '\n' else ' ')
            i += 1
            continue
        if c in '\'"`':
            quote = c
            out.append(c)
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


# ── 3. THE CONTROL PAIR ──────────────────────────────────────────────────────
def controls_line(*tools):
    """The exact declaration a control file must carry, for copy-paste.

    `tools/checker_control_check.py` reads a literal `CONTROLS_FOR = [...]` out
    of every test file and will not infer it -- three inference models were
    tried and all three were wrong within an hour, each in a different
    direction. WHICH CHECKER A TEST IS A CONTROL FOR IS A FACT ITS AUTHOR KNOWS
    AND NOTHING ELSE RELIABLY DOES, so it is declared.

    A control is only a control when it asserts BOTH directions:
        plant the defect -> the checker must REPORT it   (non-zero exit)
        plant clean code -> the checker must STAY SILENT (zero exit)
    A check that always reports passes the first half alone; a check that never
    reports passes the second alone. Only the pair says anything.
    """
    return 'CONTROLS_FOR = [%s]' % ', '.join(repr(t) for t in tools)


# ── the reporting half of the contract ───────────────────────────────────────
def finish(findings, could_not_run=(), quiet=False, clean_line=None):
    """Print the verdict and return the exit code. The third state wins.

    `could_not_run` is checked FIRST and on purpose: a run that found nothing
    because it could not look is not clean, and folding it into EXIT_CLEAN is
    the single most repeated defect in this repo's own tooling. If both are
    non-empty the exit code is EXIT_COULD_NOT_RUN -- partial findings from a
    partial run are a floor, not an answer, and the caller is told so.
    """
    if not quiet:
        if could_not_run:
            print('\nCOULD NOT RUN (%d) -- this is NOT a pass:' % len(could_not_run))
            for c in could_not_run:
                print('  ? %s' % c)
        if findings:
            print('\nFINDINGS (%d):' % len(findings))
            for f in findings:
                print('  ! %s' % f)
        if could_not_run and findings:
            print('\nThe findings above are a FLOOR, not a total -- part of this '
                  'run did not happen.')
        if not findings and not could_not_run:
            print(clean_line or '\nCLEAN -- ran fully, found nothing.')
    if could_not_run:
        return EXIT_COULD_NOT_RUN
    return EXIT_FINDING if findings else EXIT_CLEAN


def read(path):
    """Read a text file the way every checker here reads one."""
    with io.open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()
