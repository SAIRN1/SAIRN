"""Which OPEN rows in the work index have had their subject MOVE underneath them.

    python tools/stale_row_sweep.py              # the sweep
    python tools/stale_row_sweep.py --fixtures   # the blind lock alone
    python tools/stale_row_sweep.py --json

Report only. Nothing gates on this, and it CANNOT close a row -- see the limit
section, which is the most important part of this file.

── WHY THIS EXISTS, AND IT IS A MEASURED CASE, NOT A WORRY ─────────────────
On 2026-09-18 a row in `docs/SAIRN-OPEN-WORK-INDEX.md` read **OPEN, ASSIGNED TO
HANK** and named three SAIRNvet findings. All three had been fixed EIGHT DAYS
EARLIER, in `ad588e6c` (13:18) and `1348466a` (13:43) -- both landing HOURS
AFTER the row was written, on the same afternoon, by two different sessions.
Nobody came back. The row sat in the queue for eight days looking like work.

It was found BY ACCIDENT: a session picked the row up, went to do the work, and
discovered there was none. That is the whole detection mechanism this index has
had, and it scales with nothing. A queue that quietly accumulates already-done
rows is how a queue stops being read, which is the failure the index itself was
built to end.

THE SHAPE IS SPECIFIC AND IT IS MECHANICAL: a row states a date and names
artifacts; commits touch those artifacts AFTER that date; nothing compares the
two. Everything in that sentence is in git.

── WHAT IT DOES *NOT* CLAIM, AND THIS IS THE HALF THAT KEEPS IT HONEST ─────
IT DOES NOT DECIDE THAT A ROW IS STALE. It cannot. "Does this row's finding
still reproduce" is a question about behaviour, and the only general answer is
to go and look -- which is exactly the human judgement the row exists to
request. A tool that printed "CLOSED" here would be manufacturing verdicts, and
this repo has a register full of what that costs.

What it says is strictly weaker and actually true: **this row's named artifacts
have changed since it was written, so the row is a CLAIM ABOUT A FILE THAT NO
LONGER EXISTS IN THAT FORM.** Re-read it. That turns "somebody happens to pick
it up" into a ranked list, which is the entire gain being claimed.

So a hit is NOT a defect and NOT a closure. It is a re-read request, ranked by
how far the ground has moved.

── TWO ANCHORS, AND THE SECOND ONE IS WHAT CATCHES THE FOUNDING CASE ───────
  FILE    a backticked path in the row -- `api/_lib/license.js`. Commits since
          the row's date that touched it.
  SYMBOL  a backticked identifier that looks like code -- `svSeedStore`,
          `sv_peerconsults` -- searched with `git log -G` inside the app file
          the row's App cell names.

THE PATH-ONLY FIRST VERSION MISSED THE SAIRNVET ROW COMPLETELY. That row names
no file path at all; it names symbols. A checker reconciled only against
synthetic fixtures would have shipped that way, which is why
`tests/stale_row_sweep_control.py` arm 6 runs the real tool against the real
historical index and requires both fix commits by name.

── THE THREE BUCKETS, AND THE THIRD IS NOT LOW ─────────────────────────────
  MOVED       the row is dated, has at least one anchor, and commits touched an
              anchor after that date. THESE ARE THE FINDINGS.
  QUIET       dated, anchored, nothing touched it since. The row is as true
              today as the day it was written. Counted, not listed.
  CANNOT CHECK   no usable date in the STATUS cell, or no anchor at all.
              **Reported separately and counted as COULD-NOT-RUN, never folded
              into QUIET** -- a row this tool cannot check is indistinguishable
              from a fresh one only if you let it be. PR 1.11 in its sweep form.

A previous version of this idea would have printed "100 rows checked, 46 stale".
It would have been checking 57 and calling 43 quiet.

── RANKING, AND WHY IT IS NOT THE COMMIT COUNT ─────────────────────────────
The first run ranked by raw commits and put three rows on top with 154, 139 and
131 -- every one of them dominated by `api/sd-data.js`, the file nearly every
change touches. The number was a property of the FILE. `register_feed_gate.py`
shipped that same defect and the index records the verdict: a sequencer that
puts everything in the top band is worse than no sequencer, because it looks
like a priority order and is a fabricated one. So a file in the top decile of
churn is BROAD and does not drive the rank; rows anchored only on broad files
are reported in their own list rather than sorted to the top. The decile is
derived per run and printed.

── WHY THE DATE COMES FROM THE STATUS CELL AND NOT FROM GIT BLAME ──────────
Blame gives the date the LINE was last edited, and these rows are edited to add
verification notes long after the finding was written -- the SAIRNvet row's line
was touched the day it was closed. Blame would have called it fresh. The STATUS
cell is where a row states its own provenance ("FOUND 2026-09-18 (Cody)",
"SCOPED 2026-09-13", "ASSIGNED TO HANK on Michael's call 2026-09-10"). Reading
dates from the whole row instead pulled STATUTE dates out of SAIRNlaw prose --
`since 2021-01-01` -- and sent those rows up a ranking built on the resulting
count. See `row_date` for the full account.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN, finish  # noqa: E402

INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')

# REQUIREMENT: an OPEN row whose named artifacts have been committed to since
#   the row was written is SURFACED, ranked, and never silently carried -- and a
#   row this tool cannot date or anchor is reported as uncheckable rather than
#   counted as quiet.

CRITERIA_VERSION = 1

# A row is open unless its status says otherwise. CLOSED wins over OPEN when
# both appear, because rows are commonly written as "~~OPEN~~ -- CLOSED 2026-..."
# and reading the first match would keep every closed row in the sweep forever.
CLOSED_RE = re.compile(r'\b(CLOSED|FIXED AND LIVE|RESOLVED|WITHDRAWN|SUPERSEDED|'
                       r'DISCHARGED|DONE)\b', re.I)
OPEN_RE = re.compile(r'\b(OPEN|BLOCKED|NOT FIXED|NOT YET|NOT BUILT|NOT SEEDED|'
                     r'PENDING|UNVERIFIED|AWAITING)\b', re.I)

DATE_RE = re.compile(r'\b(20\d{2}-\d{2}-\d{2})\b')

# Backticked paths only. A bare word that looks like a filename is not enough:
# the rows are prose and `api/sd-data.js` in backticks is a deliberate reference
# while "sd-data" in a sentence is not.
PATH_RE = re.compile(r'`([A-Za-z0-9_][A-Za-z0-9_./-]*\.'
                     r'(?:js|py|html|sql|json|md|yml|yaml|ts))`')

HEADER_CELL = 'App'


def rows_of(text):
    """Every data row of the index as a list of cells, with its line number.

    The row is split on `|` for READING only. Nothing here writes a row back --
    CLAUDE.md forbids editing a row by splitting it, and this tool never edits
    one at all.
    """
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 6:
            continue
        if cells[0] == HEADER_CELL or set(cells[0]) <= set('-: *'):
            continue
        out.append((n, cells))
    return out


def is_open(cells):
    """True when the STATUS cell still reads as open work."""
    status = cells[2]
    if CLOSED_RE.search(status):
        return False
    return bool(OPEN_RE.search(status))


def row_date(cells, floor=None):
    """The EARLIEST date in the STATUS cell, or None.

    ── THE STATUS CELL ONLY, AND THE FIRST VERSION GOT THIS WRONG ───────────
    This first read every cell in the row and took the earliest date anywhere.
    On the real index that produced `since 2021-01-01` for the Kentucky row,
    `since 2023-05-05` for Tennessee and `since 2025-07-02` for another -- all
    of them STATUTE AND SOURCE-READ DATES quoted in the row's prose. A row that
    cites a 2021 rule is not a 2021 row, and the effect was silent: an
    impossibly early `since` makes git return years of commits and the row
    rockets up a ranking built on that count. A wrong answer that sorts itself
    to the top is the worst kind.

    The STATUS cell is where a row states its own provenance -- "FOUND
    2026-09-18 (Cody)", "SCOPED 2026-09-13 (Fourth)", "Open -- DERIVED
    2026-09-10 (Hank)". A date there is about the ROW. A date in the detail
    cell may be about anything.

    EARLIEST WITHIN THAT CELL is still right, and for the original reason: a
    status edited three times carries several, and the claim is as old as the
    first.

    `floor` is a second, independent guard: a date before the repository's own
    first commit cannot be a row date. It is DERIVED from git rather than
    written here, and it catches the citation shape even if one ever appears in
    a status cell.
    """
    dates = sorted(set(DATE_RE.findall(cells[2])))
    if floor:
        dates = [d for d in dates if d >= floor]
    return dates[0] if dates else None


def repo_floor():
    """The date of the repository's FIRST commit. No row predates it."""
    r = subprocess.run(['git', 'log', '--reverse', '--format=%ad',
                        '--date=short', '--max-parents=0'],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git log --max-parents=0 failed: %s'
                           % (r.stderr or '').strip())
    lines = [l.strip() for l in (r.stdout or '').splitlines() if l.strip()]
    if not lines:
        raise RuntimeError('could not read the first commit date')
    return sorted(lines)[0]


def row_paths(cells, exists):
    """Backticked paths in the row that resolve to a real tracked file.

    A path that does NOT resolve is returned separately rather than dropped: a
    row naming a file that no longer exists is itself worth knowing about, and
    silently ignoring it would let a renamed file read as a quiet row.
    """
    named = sorted(set(PATH_RE.findall(' '.join(cells))))
    live = [p for p in named if exists(p)]
    gone = [p for p in named if not exists(p)]
    return live, gone


# ── THE SYMBOL ANCHOR, AND IT IS THE ONE THAT CATCHES THE FOUNDING CASE ─────
# The first version anchored on backticked FILE PATHS only. Reconciled against
# the SAIRNvet row this tool was built from -- the real true positive, pulled
# out of git at `50adbda7^` -- it MISSED IT ENTIRELY. That row names no file
# path at all. It names `svSeedStore`, `svSyncSuppressed`, `pcOpenDetail()` and
# `sv_peerconsults`: the SYMBOLS the finding is about.
#
# A checker reconciled only against clean inputs is a checker whose behaviour
# nobody knows. This one was, for about an hour, and it would have shipped as a
# 46-row report that could not see the single case in its own docstring.
#
# `git log -G<symbol> -- <app file>` answers exactly the right question: did any
# commit's DIFF mention this symbol since the row was written. Run against the
# founding case it returns ad588e6c and 1348466a and nothing else -- the two
# fixes, by name. `-S` would not: it counts occurrence changes, and ad588e6c
# edited the body of pcOpenDetail without changing how many times the name
# appears.
#
# Scoped to the row's own app file so the history walk is bounded. A symbol
# anchor is always SPECIFIC: `svSeedStore` is not a word that moves because the
# platform is busy.
SYMBOL_RE = re.compile(r'`([A-Za-z_][A-Za-z0-9_]{4,})(?:\(\))?`')
# Looks like code rather than English: an underscore, or an internal capital.
CODEISH = re.compile(r'_|[a-z][A-Z]')


def row_symbols(cells):
    """Backticked identifiers in the row that look like code, not prose."""
    out = set()
    for cell in cells:
        for sym in SYMBOL_RE.findall(cell):
            if CODEISH.search(sym):
                out.add(sym)
    return sorted(out)


def app_file(cells, exists):
    """`<app>.html` for the row's App cell, when such a file is tracked.

    Derived from the cell rather than a hardcoded map: the App-File-Map has
    drifted seven times and a table here would be an eighth copy of it.
    """
    name = re.sub(r'[^A-Za-z0-9]', '', cells[0]).lower()
    cand = '%s.html' % name
    return cand if name and exists(cand) else None


def symbol_commits(sym, date, path):
    """Commits since `date` whose DIFF to `path` mentions `sym`."""
    r = subprocess.run(
        ['git', 'log', '--since=%s' % date, '--format=%h %ad %s',
         '--date=short', '-G%s' % sym, '--', path],
        cwd=REPO, capture_output=True, text=True, encoding='utf-8',
        errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git log -G failed for %s: %s'
                           % (sym, (r.stderr or '').strip()))
    lines = [l for l in (r.stdout or '').splitlines() if l.strip()]
    return len(lines), lines


def tracked_set():
    """Every path git tracks, as a set. One subprocess, not one per row."""
    r = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git ls-files failed: %s' % (r.stderr or '').strip())
    return set(l.strip() for l in (r.stdout or '').splitlines() if l.strip())


def churn_of(path):
    """All-time commit count for a path. One subprocess per anchor, cached."""
    if path in _CHURN:
        return _CHURN[path]
    r = subprocess.run(['git', 'rev-list', '--count', 'HEAD', '--', path],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git rev-list failed for %s: %s'
                           % (path, (r.stderr or '').strip()))
    _CHURN[path] = int((r.stdout or '0').strip() or 0)
    return _CHURN[path]


_CHURN = {}


def commits_since(path, date):
    """(count, [subject, ...]) for commits touching `path` strictly after `date`.

    `--since` is inclusive of the day, so a commit made the same day the row was
    written counts. That is deliberate and it is the SAIRNvet case exactly: the
    row and both fixes share a date and the fixes came hours later. Excluding
    the day would have missed the one case this tool was built from.
    """
    r = subprocess.run(
        ['git', 'log', '--since=%s' % date, '--format=%h %ad %s',
         '--date=short', '--', path],
        cwd=REPO, capture_output=True, text=True, encoding='utf-8',
        errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git log failed for %s: %s' % (path, (r.stderr or '').strip()))
    lines = [l for l in (r.stdout or '').splitlines() if l.strip()]
    return len(lines), lines


# ── RANKING BY RAW COMMIT COUNT IS A FABRICATED ORDER, AND THIS REPO HAS
#    ALREADY PAID FOR THAT EXACT MISTAKE ────────────────────────────────────
# The first run of this tool put line 356 at the top with 154 commits, line 309
# with 139 and line 561 with 131 -- and every one of those totals is dominated
# by `api/sd-data.js`, the file that addresses every resource on the platform
# and that nearly every change touches. The number was a property of the FILE,
# not of the row.
#
# That is the same defect `tools/register_feed_gate.py` shipped and had to fix:
# its first sequencer put 54 commits in the top risk band because one file
# addresses every resource, and the open-work index records the verdict --
# "A SEQUENCER THAT PUTS EVERYTHING IN THE TOP BAND IS WORSE THAN NO SEQUENCER:
# it looks like a priority order and is a fabricated one."
#
# So an anchor is only allowed to drive the rank when the anchor is SPECIFIC.
# A file in the top decile of all-time churn among the anchors is BROAD: its
# movement says almost nothing about any one row. Rows anchored ONLY on broad
# files are still reported -- they may well be stale -- but in their own list
# with the reason stated, rather than sorted to the top where they would crowd
# out the rows the tool can actually say something about.
#
# THE CUT IS DERIVED FROM THE DATA AND PRINTED, not written in here as a
# constant somebody would have to trust.
BROAD_DECILE = 0.90


def broad_anchors(paths, churn):
    """The anchor paths whose all-time churn puts them in the top decile.

    Returns (set_of_broad_paths, cut_value). With fewer than ten anchors the
    decile is meaningless and nothing is called broad -- a rule that starts
    classifying on three data points is inventing the distribution.
    """
    counts = sorted(churn(p) for p in paths)
    if len(counts) < 10:
        return set(), None
    cut = counts[int(len(counts) * BROAD_DECILE)]
    return set(p for p in paths if churn(p) >= cut), cut


def sweep(text, exists, log, churn=None, floor=None, glog=None):
    """(moved, quiet, cannot_check, cut). Pure apart from the callables.

    `churn(path) -> int` is the file's ALL-TIME commit count, used only to tell
    a specific anchor from a broad one. Passing None disables that split, which
    is what the fixtures do: ten synthetic rows cannot support a decile.

    `glog(symbol, date, path) -> (count, lines)` is the SYMBOL anchor. Passing
    None disables it, and a row anchored only on symbols then reads uncheckable
    -- never quiet.
    """
    open_rows, cannot = [], []
    for n, cells in rows_of(text):
        if not is_open(cells):
            continue
        date = row_date(cells, floor)
        live, gone = row_paths(cells, exists)
        subject = re.sub(r'[*`~]', '', cells[1])[:76]
        syms = row_symbols(cells) if glog else []
        appf = app_file(cells, exists) if glog else None
        if not appf:
            syms = []            # nowhere bounded to look
        if date is None:
            cannot.append((n, subject, 'no usable date in the STATUS cell -- a '
                                       'date in the prose may be a citation '
                                       'rather than this row\'s own, so the row '
                                       'is uncheckable, not dated from it'))
            continue
        if not live and not syms:
            why = ('names %d file(s) that no longer exist (%s)'
                   % (len(gone), ', '.join(gone))) if gone else \
                  ('names no backticked file path and no code symbol in an app '
                   'file -- nothing to watch')
            cannot.append((n, subject, why))
            continue
        open_rows.append((n, subject, date, live, syms, appf))

    all_paths = sorted(set(p for _, _, _, live, _, _ in open_rows for p in live))
    broad, cut = (broad_anchors(all_paths, churn) if churn else (set(), None))

    moved, quiet = [], []
    for n, subject, date, live, syms, appf in open_rows:
        specific, wide, detail = 0, 0, []
        for p in live:
            c, lines = log(p, date)
            if p in broad:
                wide += c
            else:
                specific += c
            detail.extend('%s%s  %s' % (p, ' [broad]' if p in broad else '', l)
                          for l in lines)
        seen = set()
        for sym in syms:
            c, lines = glog(sym, date, appf)
            for l in lines:
                if l in seen:        # one commit touching three symbols is ONE
                    continue         # commit, not three
                seen.add(l)
                specific += 1
                detail.append('%s in %s  %s' % (sym, appf, l))
        if specific or wide:
            moved.append({'line': n, 'subject': subject, 'since': date,
                          'paths': live, 'symbols': syms, 'app_file': appf,
                          'commits': specific + wide,
                          'specific': specific, 'broad_only': specific == 0,
                          'detail': detail})
        else:
            quiet.append((n, subject, date))
    # Rank on the SPECIFIC count. Rows with none fall to the end by construction
    # rather than by a second sort nobody can see.
    moved.sort(key=lambda m: (-m['specific'], -m['commits'], m['line']))
    return moved, quiet, cannot, cut


# ── THE BLIND LOCK ──────────────────────────────────────────────────────────
# Criteria locked against synthetic rows BEFORE the tool is pointed at the real
# index, per docs/2026-09-13-cross-domain-disciplines.md. Every fixture states
# the answer it must get, and HALF OF THEM MUST NOT FIRE -- a rule that flagged
# every open row would pass a one-sided lock and be useless.
# NOT `| App |` -- that is the real table's HEADER cell and every fixture using
# it was silently skipped as a header, which the lock reported as 8 wrong
# answers in one direction. A fixture that cannot reach the code it fixes is
# worth less than no fixture, because it reads as coverage.
_ROW = '| Platform | %s | %s | owner | -- | %s | S |'

FIXTURES = (
    ('an open dated row whose file moved -> MOVED',
     _ROW % ('subject `a.js`', 'Open -- FOUND 2026-09-01', 'detail'),
     'moved'),
    ('the SAIRNvet shape: row and fix share a DATE, fix landed hours later',
     _ROW % ('subject `a.js`', 'OPEN -- ASSIGNED 2026-09-10', 'detail'),
     'moved'),
    ('an open dated row whose file has NOT moved -> quiet',
     _ROW % ('subject `b.js`', 'Open -- FOUND 2026-09-01', 'detail'),
     'quiet'),
    # MUST NOT be reported as MOVED.
    ('a CLOSED row is not swept at all, even though its file moved',
     _ROW % ('subject `a.js`', 'CLOSED 2026-09-02 -- verified', 'detail'),
     'skipped'),
    ('a row written ~~OPEN~~ then CLOSED reads as closed, not open',
     _ROW % ('subject `a.js`', '~~Open~~ -- CLOSED 2026-09-02', 'detail'),
     'skipped'),
    ('an open row with NO date -> cannot check, NOT quiet',
     _ROW % ('subject `a.js`', 'Open', 'detail'),
     'cannot'),
    ('an open dated row naming NO file -> cannot check, NOT quiet',
     _ROW % ('subject with no path', 'Open -- FOUND 2026-09-01', 'detail'),
     'cannot'),
    ('an open dated row whose named file does not exist -> cannot check',
     _ROW % ('subject `gone.js`', 'Open -- FOUND 2026-09-01', 'detail'),
     'cannot'),
    ('a bare filename NOT in backticks is not an anchor',
     _ROW % ('subject a.js in prose', 'Open -- FOUND 2026-09-01', 'detail'),
     'cannot'),
    ('the EARLIEST date is used, not the latest',
     _ROW % ('subject `c.js`', 'Open -- FOUND 2026-09-01, re-checked 2026-09-20',
             'detail'),
     'moved'),
    # THE CITATION SHAPE. Real rows quote statute and source-read dates in their
    # prose -- 2021-01-01 for Kentucky, 2023-05-05 for Tennessee. Reading those
    # as the row's date made `since` years too early and sorted the row to the
    # top of a ranking built on the resulting commit count.
    ('a date in the DETAIL cell is not the row date',
     _ROW % ('subject `a.js`', 'Open', 'the rule dates from 2021-01-01'),
     'cannot'),
    ('...and a status date is still read when the detail also has a citation',
     _ROW % ('subject `a.js`', 'Open -- FOUND 2026-09-01',
             'the rule dates from 2021-01-01'),
     'moved'),

    # ── THE FOUNDING CASE, REDUCED. The real SAIRNvet row names NO file path
    #    at all, only symbols, and the path-only version of this tool missed it.
    ('SYMBOL ANCHOR: a row naming only `svSeedStore`, in an app row',
     '| SAIRNvet | subject `svSeedStore` | OPEN -- ASSIGNED 2026-09-10 | o | -- '
     '| detail | S |',
     'moved'),
    ('...and two symbols touched by the SAME commits count once, not twice',
     '| SAIRNvet | subject `svSeedStore` and `svSyncSuppressed` '
     '| OPEN -- ASSIGNED 2026-09-10 | o | -- | detail | S |',
     'moved'),
    ('a symbol nothing has touched -> quiet, not moved',
     '| SAIRNvet | subject `quietSymbol_x` | Open -- FOUND 2026-09-01 | o | -- '
     '| detail | S |',
     'quiet'),
    ('an ENGLISH word in backticks is not a symbol anchor',
     '| SAIRNvet | subject `complete` | Open -- FOUND 2026-09-01 | o | -- '
     '| detail | S |',
     'cannot'),
    ('a symbol in a row whose App cell has no app file -> cannot check',
     '| Platform | subject `svSeedStore` | Open -- FOUND 2026-09-01 | o | -- '
     '| detail | S |',
     'cannot'),
)


def run_fixtures(quiet=False):
    """Every fixture, against a planted repo that exists only in memory."""
    exists = {'a.js', 'b.js', 'c.js', 'sairnvet.html'}.__contains__

    def log(path, date):
        # a.js moved after 2026-09-01 and after 2026-09-10; b.js never moved;
        # c.js moved on the 10th, which is AFTER the earliest date in its row
        # and BEFORE the later one -- so it only reports MOVED if the earliest
        # date is the one used. That is the whole point of that fixture.
        if path == 'a.js':
            return 1, ['abc1234 2026-09-15 a later fix']
        if path == 'c.js':
            return (1, ['def5678 2026-09-10 a fix']) if date <= '2026-09-10' else (0, [])
        return 0, []

    def glog(sym, date, path):
        # svSeedStore moved in sairnvet.html; quietSymbol never did. Two
        # commits for the first, so the de-duplication arm has something to
        # collapse when a row names two symbols touched by the same commit.
        if sym in ('svSeedStore', 'svSyncSuppressed') and path == 'sairnvet.html':
            return 2, ['ad588e6c 2026-09-10 the photo fix',
                       '1348466a 2026-09-10 the finally fix']
        return 0, []

    wrong = []
    for label, row, want in FIXTURES:
        moved, quietrows, cannot, _cut = sweep(row, exists, log, glog=glog)
        got = ('moved' if moved else 'cannot' if cannot
               else 'quiet' if quietrows else 'skipped')
        if got != want:
            wrong.append('%-62s expected %-8s got %s' % (label, want, got))
    if not quiet:
        for w in wrong:
            print('  WRONG  %s' % w)
        fires = sum(1 for f in FIXTURES if f[2] == 'moved')
        print('  %d/%d fixtures correct (%d must fire as MOVED, %d must not)'
              % (len(FIXTURES) - len(wrong), len(FIXTURES), fires,
                 len(FIXTURES) - fires))
    return wrong


def main(argv):
    # ── THE ROWS CONTAIN EMOJI AND THIS CONSOLE IS cp1252 ────────────────────
    # A row subject beginning with a warning emoji raised UnicodeEncodeError
    # midway through the report -- AFTER the summary line had printed. That is
    # the worst shape a crash can take here: the counts are on screen, the run
    # is dead, and a reader skimming the top has a complete-looking report of an
    # incomplete sweep. `tools/suite_control_triage.py` carries the same note
    # about the same console. Reconfiguring is the fix; errors='replace' so an
    # unencodable character costs one glyph rather than the whole run.
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--fixtures', action='store_true',
                    help='run the blind lock alone and exit')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--index', default=INDEX)
    args = ap.parse_args(argv)

    if args.fixtures:
        wrong = run_fixtures()
        if wrong:
            print('\nTHE BLIND LOCK FAILED -- the criteria do not do what this '
                  'file says they do, so nothing below it can be believed.')
            return EXIT_COULD_NOT_RUN
        print('\nblind lock OK (criteria version %d)' % CRITERIA_VERSION)
        return EXIT_CLEAN

    # THE LOCK RUNS ON EVERY RUN, not only under --fixtures. A criteria drift
    # that broke the rule would otherwise produce a confident sweep over the
    # real index and nothing would say the rule had changed.
    wrong = run_fixtures(quiet=True)
    if wrong:
        print('COULD NOT RUN: the blind lock failed, so the sweep below was not '
              'attempted. Run --fixtures to see which criteria broke.')
        return EXIT_COULD_NOT_RUN

    try:
        tracked = tracked_set()
        text = io.open(args.index, encoding='utf-8', errors='replace').read()
    except (RuntimeError, OSError) as e:
        print('COULD NOT RUN: %s' % e)
        return EXIT_COULD_NOT_RUN

    try:
        moved, quiet, cannot, cut = sweep(text, tracked.__contains__,
                                          commits_since, churn_of, repo_floor(),
                                          symbol_commits)
    except RuntimeError as e:
        print('COULD NOT RUN: %s' % e)
        return EXIT_COULD_NOT_RUN

    total = len(moved) + len(quiet) + len(cannot)
    if args.json:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'open_rows': total, 'moved': moved,
                          'quiet': len(quiet), 'broad_cut': cut,
                          'cannot_check': [{'line': n, 'subject': s, 'why': w}
                                           for n, s, w in cannot]}, indent=2))
        return (EXIT_COULD_NOT_RUN if cannot else
                EXIT_FINDING if moved else EXIT_CLEAN)

    print('STALE-ROW SWEEP -- report only, and it CANNOT close a row')
    print('  %d open row(s) in %s' % (total, os.path.relpath(args.index, REPO)))
    ranked = [m for m in moved if not m['broad_only']]
    broad_only = [m for m in moved if m['broad_only']]
    print('  %d MOVED (%d rankable, %d anchored only on a high-churn file), '
          '%d quiet, %d uncheckable'
          % (len(moved), len(ranked), len(broad_only), len(quiet), len(cannot)))
    if cut is not None:
        print('  A file is BROAD at >= %d all-time commits -- the top decile of '
              'the %d anchor' % (cut, len(set(p for m in moved for p in m['paths']))))
        print('  path(s) these rows name. Derived from this run, not a constant: a '
              'row whose only')
        print('  anchor is api/sd-data.js moves every day and that says nothing '
              'about the row.')
    print('')
    print('  A HIT IS A RE-READ REQUEST, NOT A CLOSURE. It says the row\'s named')
    print('  files have been committed to since the row was written, so the row')
    print('  describes a file that no longer exists in that form. Whether the')
    print('  finding still reproduces is a question about BEHAVIOUR and only a')
    print('  person going to look can answer it.')
    print('')
    for m in ranked[:25]:
        print('  line %-5d %2d specific commit(s) since %s (%d incl. broad)'
              % (m['line'], m['specific'], m['since'], m['commits']))
        print('      %s' % m['subject'])
        for d in m['detail'][:4]:
            print('        %s' % d)
        if len(m['detail']) > 4:
            print('        ... %d more' % (len(m['detail']) - 4))
    if len(ranked) > 25:
        print('  ... %d more rankable row(s) not printed' % (len(ranked) - 25))
    if broad_only:
        print('')
        print('  ANCHORED ONLY ON A HIGH-CHURN FILE (%d) -- still possibly stale,'
              % len(broad_only))
        print('  but the movement is about the file rather than the row, so these')
        print('  are NOT ranked and NOT hidden either:')
        for m in broad_only[:15]:
            print('    line %-5d %s' % (m['line'], m['subject'][:66]))
        if len(broad_only) > 15:
            print('    ... %d more' % (len(broad_only) - 15))

    return finish(
        ['line %d: %d commit(s) to %s since %s -- re-read this row'
         % (m['line'], m['commits'], ', '.join(m['paths']), m['since'])
         for m in moved],
        ['line %d: %s (%s)' % (n, s, w) for n, s, w in cannot],
        clean_line='\nCLEAN -- every checkable open row names files nothing has '
                   'touched since it was written.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
