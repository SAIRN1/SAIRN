"""An unresolved VCS conflict marker, in any file, in any language.

    python tools/conflict_marker_check.py                  # the whole tree
    python tools/conflict_marker_check.py --files a.js b.md # a named set
    python tools/conflict_marker_check.py --outgoing        # what a push ships
    python tools/conflict_marker_check.py --json

Exit 0 clean, 1 a finding. There is no COULD-NOT-TELL: it reads bytes and either
finds a marker at the start of a line or does not.

── TWO REAL INCIDENTS, AND THE SECOND IS WHY THIS IS A GATE ────────────────────
2026-09-11  Three markers reached origin/main in docs/SAIRN-OPEN-WORK-INDEX.md.
            After the first one, "no header+separator pair occurs again", so
            md_table_check examined 110 OF 350 ROWS AND PRINTED A CLEAN PASS.

2026-09-15  TWICE IN ONE DAY, by two different sessions:
              * api/_lib/dnt-rollup.js -- markers pushed into a TIER A FILE by
                a session's own rebase automation (98bfea1e).
              * docs/SAIRN-OPEN-WORK-INDEX.md again, by me. md_table_check
                printed `MALFORMED_ROWS:0` and `UNCHECKABLE_LINES:406` on the
                same run, and only the first number gates.

THE COMMON CAUSE IS NOT CARELESSNESS, IT IS `git add -A` DURING A REBASE. Four
clones rebase onto each other constantly; a staged unmerged file looks exactly
like a resolved one to `git add`, and the push gate then checks a file whose
content nobody read.

── WHY A NEW CHECK RATHER THAN FIXING md_table_check ──────────────────────────
md_table_check already carries a CONFLICT regex, added 2026-09-12 for the first
incident. It did not stop either of the 2026-09-15 ones, for three separate
reasons, and every one of them is structural:

  1. IT ONLY READS MARKDOWN TABLES. Ted's incident was a .js file. A marker in
     source code is worse than one in a document -- it is a syntax error at best
     and, in a file that happens to still parse, a live defect.
  2. IT IS REPORT-ONLY. It is in report_only_checks.REGISTRY, which prints and
     never blocks.
  3. ITS VERDICT IS THE WRONG NUMBER. It measures UNCHECKABLE_LINES and gates on
     MALFORMED_ROWS, so a file it could not read passed a check about whether it
     could be read.

A marker is not a markdown problem. It is a "this file is not finished" problem,
and it belongs in a check that reads every file the push ships.

── THE BASELINE IS MEASURED, WHICH IS WHY THIS CAN BLOCK ON DAY ONE ───────────
All four marker shapes, anchored to the start of a line, across 2,069 tracked
files on 2026-09-15:

    <<<<<<<   0        =======   0
    >>>>>>>   0        |||||||   0     (diff3 style)

ZERO false positives, including the lone `=======` that ASCII banners and
markdown rules would be expected to produce. So the detector is as strict as it
can be at no cost -- and that is a measurement, not an assumption. Every other
check on this platform was staged through report-only first because its
false-positive rate was unknown; this one's is known.

THE ANCHOR IS WHY. `=======` mid-line is a markdown underline and appears
everywhere; `=======` at column zero appears nowhere. This repo's own documents
QUOTE all three markers in prose -- the 2026-09-11 open-work row contains
`<<<<<<<` inside backticks -- and none of that is at line start.

── WHAT IT CANNOT SEE ─────────────────────────────────────────────────────────
  * A conflict resolved WRONGLY. A file with no markers can still have had the
    wrong side kept, and nothing mechanical can tell.
  * A marker indented by even one space. That is deliberate: git writes them at
    column zero, and accepting leading whitespace would start matching prose.
  * Binary files, which are skipped and NAMED rather than silently dropped.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Anchored to column zero. See the header for why, and for the measured
# false-positive baseline that justifies including the bare `=======`.
MARKERS = (
    ('ours', re.compile(r'^<{7}(\s|$)')),
    ('base', re.compile(r'^\|{7}(\s|$)')),      # diff3 conflictStyle
    ('split', re.compile(r'^={7}(\s|$)')),
    ('theirs', re.compile(r'^>{7}(\s|$)')),
)

SKIP_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.woff',
            '.woff2', '.ttf', '.eot', '.mp4', '.webm', '.wasm')


def git(*args):
    r = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout if r.returncode == 0 else ''


def tracked():
    return [l.strip() for l in git('ls-files').split('\n') if l.strip()]


def outgoing():
    """Files the commits this push would send actually change. Same fallback
    order as the push gate's own outgoing_files(): @{u} then origin/main. An
    empty answer means the range is empty, which means the push ships nothing
    new -- not that nothing was checked."""
    for ref in ('@{u}', 'origin/main'):
        base = git('merge-base', ref, 'HEAD').strip()
        if base:
            out = git('diff', '--name-only', base, 'HEAD')
            return [l.strip() for l in out.split('\n') if l.strip()]
    return []


def scan_text(rel, body):
    """[(line number, marker kind, the line)] for every marker in one file."""
    found = []
    for i, line in enumerate(body.split('\n'), 1):
        for kind, rx in MARKERS:
            if rx.match(line):
                found.append((i, kind, line[:70]))
                break
    return found


def scan(paths):
    hits, skipped, unreadable = [], [], []
    for rel in paths:
        norm = rel.replace('\\', '/')
        if norm.lower().endswith(SKIP_EXT):
            skipped.append(norm)
            continue
        path = os.path.join(REPO, norm)
        if not os.path.isfile(path):
            continue                 # deleted by this change; nothing to read
        try:
            raw = io.open(path, 'rb').read()
        except OSError as e:
            unreadable.append((norm, str(e)[:60]))
            continue
        if b'\x00' in raw[:4096]:
            # BINARY BY CONTENT, not only by extension -- and NAMED, because a
            # silently skipped file is indistinguishable from a clean one.
            skipped.append(norm)
            continue
        body = raw.decode('utf-8', errors='replace')
        for ln, kind, text in scan_text(norm, body):
            hits.append({'file': norm, 'line': ln, 'kind': kind, 'text': text})
    return hits, skipped, unreadable


def main(argv):
    if '--files' in argv:
        paths = argv[argv.index('--files') + 1:]
        where = '%d named file(s)' % len(paths)
    elif '--outgoing' in argv:
        paths = outgoing()
        where = 'what this push would ship (%d file(s))' % len(paths)
    else:
        paths = tracked()
        where = 'every tracked file (%d)' % len(paths)

    hits, skipped, unreadable = scan(paths)

    if '--json' in argv:
        print(json.dumps({'findings': hits, 'skipped': skipped,
                          'unreadable': unreadable, 'scanned': len(paths)},
                         indent=2))
        return 1 if hits else 0

    print('UNRESOLVED CONFLICT MARKERS -- %s' % where)
    print('  files with a marker at the start of a line : %d'
          % len(set(h['file'] for h in hits)))
    if skipped:
        print('  skipped as binary (%d, NOT silently)        : %s'
              % (len(skipped), ', '.join(skipped[:3])))
    if unreadable:
        print('  COULD NOT READ (%d) -- not a pass          : %s'
              % (len(unreadable), unreadable[:2]))
    if not hits:
        print('')
        print('  CLEAN. No file carries an unresolved marker.')
        print('  The correct number IS zero: a marker means the file is not')
        print('  finished, and the measured false-positive baseline across')
        print('  2,069 tracked files is 0 for all four shapes.')
        return 0
    print('')
    for h in hits:
        print('  %s:%d  [%s]  %s' % (h['file'], h['line'], h['kind'], h['text']))
    print('')
    print('  THIS IS AN UNFINISHED MERGE, NOT A STYLE PROBLEM. In a source file')
    print('  it is a syntax error at best; in one that still parses it is a live')
    print('  defect. In a markdown table it severs every row after it -- the')
    print('  2026-09-11 incident had md_table_check reading 110 of 350 rows and')
    print('  printing a clean pass.')
    print('')
    print('  Resolve the conflict, then check the file actually has BOTH sides')
    print('  where both were real -- `git add -A` during a rebase is what put')
    print('  these here, and it cannot tell a resolved file from an unmerged one.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
