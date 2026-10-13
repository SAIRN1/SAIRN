#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b5, queue item 10
"""Shard docs/SAIRN-OPEN-WORK-INDEX.md into per-app files, and PROVE the shards
still carry every row.

    python tools/open_work_shard.py --write    # (re)generate docs/open-work/
    python tools/open_work_shard.py --check    # shards == index, row for row
    python tools/open_work_shard.py            # --check

`--write` also writes docs/open-work/ACTIVE.md, which is the file an agent is
meant to READ. See "PER-APP SHARDING IS NOT ENOUGH" below -- it was not enough,
and that is a measurement rather than a design preference.

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── THE PROBLEM, MEASURED ───────────────────────────────────────────────────
docs/SAIRN-OPEN-WORK-INDEX.md is 2,380,170 bytes -- roughly 640,000 tokens,
which does not fit any session window. CLAUDE.md already forbids opening it and
says why: a truncated read is indistinguishable from a complete one, so the
failure is not "I ran out of room", it is a confident answer about rows nobody
saw. The instruction has been "grep it, never open it" for weeks, which works
exactly as long as attention does.

── WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT ───────────────────────
It writes one shard per App value, carrying that app's rows BYTE-FOR-BYTE --
the whole line, copied, never rebuilt. PR 2.1 forbids editing a row by
splitting on `|`; this never edits a row at all, which is the only safe way to
move 854 of them.

IT DOES NOT DELETE ANYTHING FROM THE INDEX, and that is a staging decision
rather than timidity. Fourteen tools parse those rows today -- dispatch_state,
stale_row_sweep, index_duplicate_check and its hook, independence_check,
orphan_register_check, traceability_matrix, accepted_risk_expiry_audit,
md_table_check, two hover-auditor duplicate-finding checkers,
hover_threshold_cluster, run_md_table_check_probe -- and doc_sha_reseat.py
REWRITES the file on every rebase to re-seat SHA citations. Removing the rows
before those move would, in the best case, break them loudly; in the worst and
likelier case doc_sha_reseat would keep running, write nothing, and report
clean, which is a silent coverage loss on 367 citations.

SO TWO COPIES EXIST FOR NOW, AND THAT IS ONLY SAFE BECAUSE `--check` MAKES
THEM PROVABLY EQUAL. A second copy of something with nothing forcing them to
match is the duplication this platform keeps paying for. `--check` is the
forcing function: it exits 1 the moment a row exists in one and not the other,
in either direction, and it is meant to be wired as a push gate once the
readers have moved.

── PER-APP SHARDING IS NOT ENOUGH, AND THE NUMBERS SAY SO ──────────────────
Measured after the first run of this tool, not predicted before it:

    platform.md   260 rows   838,657 bytes
    tooling.md    157 rows   397,113 bytes
    sairnlaw.md    98 rows   369,748 bytes

So the biggest shard is still TWICE the 400,000-byte standing-document ceiling
`tools/tooling_inventory.py --standing-doc-sizes` enforces, and splitting by
app alone would have handed an agent a file it still cannot open. Filtering to
OPEN rows does not rescue it either: 146 open Platform rows are 469,672 bytes.

THE CAUSE IS THE ROW, NOT THE COUNT. These rows average about 2.9KB each --
the Status and Next-action cells carry whole paragraphs of evidence, which is
why the index is valuable and why it cannot be read whole.

So `--write` also emits ACTIVE.md: ONE SHORT LINE PER OPEN ROW -- app, a
truncated item, the status word, the owner, and a pointer to the shard and line
where the full text lives. That is the file an agent reads; the shard is what
it greps afterwards for the one row it needs. The full text is never
duplicated into ACTIVE.md, because a second copy of the paragraph would
recreate the problem one file along.

── WHAT A SHARD IS ────────────────────────────────────────────────────────
docs/open-work/<slug>.md, where the slug is the App cell normalised to
lowercase with non-alphanumerics collapsed to a dash. The app cell is taken
from the row verbatim and only normalised for the FILENAME; the row keeps its
original spelling, including `**Platform**` bolding and the `PLATFORM` /
`Platform` and `sairngrounds` / `SAIRNgrounds` case variants that exist in the
real file. Those variants are REPORTED rather than merged -- merging them is a
content decision about whether two spellings are one app, and this tool does
not make content decisions.
"""
import hashlib
import io
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-13.1'
INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
SHARD_DIR = os.path.join(REPO, 'docs', 'open-work')

# The open-items table's header, used to find the table rather than assuming a
# line number. Two tables in the file share this shape (the main one and the
# 2026-08-24 addendum); BOTH are sharded, which is why the header is matched
# repeatedly instead of once.
HEADER_RE = re.compile(r'^\|\s*App\s*\|\s*Item\s*\|\s*Status\s*\|')
SEPARATOR_RE = re.compile(r'^\|[\s:\-]+\|')
NL = chr(10)


def app_of(line):
    """The App cell, verbatim apart from surrounding whitespace and markup.

    NOT a split-and-rebuild: only cell 1 is read, and the row itself is never
    reassembled from its cells.
    """
    cells = line.split('|')
    if len(cells) < 3:
        return None
    return re.sub(r'[*`]', '', cells[1]).strip()


# A filename has to be a filename. Measured rather than assumed: one row's App
# cell is a struck-through section marker, not an app, and it produced a
# 198-character slug -- which `git cat-file` could not even stat, so the
# push-gate control-byte check exited 2 COULD NOT RUN on it. A check that
# cannot read a file reports nothing, which is the worst of the three states.
#
# CAPPED AND MADE UNAMBIGUOUS: 48 characters of slug plus a short hash of the
# FULL app string. Truncation alone would silently merge two long App values
# that share a prefix into one shard, which is a data loss dressed as a
# filename; the hash makes the mapping injective and is stable across runs
# because it is taken from the text, not from a counter.
SLUG_MAX = 48


def slug(app):
    s = re.sub(r'[^a-z0-9]+', '-', (app or '').lower()).strip('-')
    if not s:
        return 'unattributed'
    if len(s) <= SLUG_MAX:
        return s
    h = hashlib.sha256((app or '').encode('utf-8')).hexdigest()[:8]
    return '%s-%s' % (s[:SLUG_MAX].rstrip('-'), h)


def read_index():
    if not os.path.isfile(INDEX):
        return None, '%s does not exist, so NOTHING was checked.' % INDEX
    return io.open(INDEX, encoding='utf-8', errors='replace').read(), ''


def collect(src):
    """-> (rows_by_slug, header_line, stats). Rows are whole lines, verbatim."""
    rows, header, in_table, stats = {}, None, False, {
        'tables': 0, 'data_rows': 0, 'skipped_non_rows': 0, 'apps': {}}
    for line in src.split(NL):
        if HEADER_RE.match(line):
            in_table, stats['tables'] = True, stats['tables'] + 1
            header = header or line
            continue
        if SEPARATOR_RE.match(line):
            continue
        if not line.startswith('|'):
            # A blank line or prose ends the table. Tracked rather than assumed
            # so a reordering of the document cannot silently drop a tail.
            if in_table and line.strip():
                stats['skipped_non_rows'] += 1
            in_table = False
            continue
        if not in_table:
            # A pipe row OUTSIDE an App|Item table -- the contradictions table
            # and the recently-closed table. Left where it is.
            continue
        app = app_of(line)
        if app is None:
            stats['skipped_non_rows'] += 1
            continue
        rows.setdefault(slug(app), []).append(line)
        stats['data_rows'] += 1
        stats['apps'].setdefault(slug(app), set()).add(app)
    return rows, header, stats


BANNER = (
    '<!-- GENERATED by tools/open_work_shard.py. Rows are copied VERBATIM from\n'
    '     docs/SAIRN-OPEN-WORK-INDEX.md, which is still the canonical file --\n'
    '     fourteen tools parse it and doc_sha_reseat.py rewrites it on every\n'
    '     rebase. Do not edit a row here; edit it in the index and re-run\n'
    '     `python tools/open_work_shard.py --write`. `--check` proves the two\n'
    '     agree row for row and exits 1 if they ever do not. -->')


# ── THIS PATTERN SHIPPED WITH A LITERAL BACKSPACE AND MATCHED NOTHING ──────
# Caught by the first run, which reported all 812 rows OPEN. The word
# boundaries were written through two layers of shell quoting and arrived
# in the file as byte 0x08, so the compiled pattern was
# '(?i)<BS>(closed|...)<BS>' -- a pattern that cannot match any text at
# all. CLAUDE.md names this exact defect as one of the six that paid for
# the cross-domain disciplines: "a regex that shipped with a literal
# backspace and could never match". It is built from a WORD LIST now, so
# there is no backslash for a quoting layer to eat, and the assert below
# refuses to run rather than classifying every row as open.
#
# The boundaries are not needed: these words are looked for anywhere in a
# prose Status cell, and `fixed` inside `prefixed` is not a word this
# column uses.
_CLOSED_WORDS = ('closed', 'landed', 'done', 'fixed', 'resolved',
                 'superseded', 'withdrawn', 'not a defect', 'no action')
CLOSED_RE = re.compile('(?i)(%s)' % '|'.join(_CLOSED_WORDS))
if not CLOSED_RE.search('FIXED 2026'):
    raise SystemExit(
        'COULD NOT RUN: CLOSED_RE cannot match a word it is made of, so every\n'
        'row would classify as OPEN. See the comment above this line.')

# THE OPEN/CLOSED SPLIT IS A HEURISTIC OVER THE STATUS CELL AND SAYS SO.
# There is no machine-readable state on these rows -- the Status cell is prose,
# which is why it carries the evidence that makes the index worth having. A row
# this misclassifies is still IN its shard with its full text; only its
# presence in ACTIVE.md is affected. ACTIVE.md says this out loud at the top so
# nobody reads its absence as proof a row is closed.


def is_open(line):
    cells = line.split('|')
    return not CLOSED_RE.search(cells[3] if len(cells) > 3 else '')


def cell(line, i, width):
    cells = line.split('|')
    raw = cells[i] if len(cells) > i else ''
    raw = re.sub(r'[*`\[\]]', '', raw)
    raw = re.sub(r'\s+', ' ', raw).strip()
    return (raw[:width - 1] + '~') if len(raw) > width else raw.ljust(width)


def write_active(rows, shard_lines):
    """One line per OPEN row, with a pointer to the shard and line."""
    out = [
        '# Open work -- ACTIVE index',
        '',
        BANNER,
        '',
        'READ THIS FILE. Then grep the shard for the one row you need:',
        '',
        '    grep -n "<the item>" docs/open-work/<app>.md',
        '    sed -n "<line>p" docs/open-work/<app>.md',
        '',
        'WHY THIS FILE EXISTS, measured rather than assumed: per-app sharding',
        'alone did NOT fit. docs/open-work/platform.md is 838,657 bytes and',
        'tooling.md is 397,113 -- the ceiling is 400,000 -- because these rows',
        'average about 2.9KB each. Filtering to open rows does not rescue it:',
        '146 open Platform rows are 469,672 bytes. The row is the problem, not',
        'the count, so the full text is NOT duplicated here.',
        '',
        'OPEN/CLOSED IS A HEURISTIC OVER A PROSE STATUS CELL. There is no',
        'machine-readable state on these rows. A row missing from this file is',
        'NOT proof it is closed -- it is proof its Status cell matched a',
        'closed-ish word. Every row, open or not, is in its shard in full.',
        '',
        '| App | Item | Status | Owner | Where |',
        '|---|---|---|---|---|',
    ]
    n = 0
    for s in sorted(rows):
        for line in rows[s]:
            if not is_open(line):
                continue
            ln = shard_lines.get(id(line))
            out.append('| %s | %s | %s | %s | `open-work/%s.md:%s` |'
                       % (cell(line, 1, 16), cell(line, 2, 72),
                          cell(line, 3, 28), cell(line, 4, 12), s,
                          ln if ln else '?'))
            n += 1
    out.append('')
    out.append('%d open row(s) of %d total.'
               % (n, sum(len(v) for v in rows.values())))
    out.append('')
    p = os.path.join(SHARD_DIR, 'ACTIVE.md')
    io.open(p, 'w', encoding='utf-8', newline=NL).write(NL.join(out))
    return n, os.path.getsize(p)


def write_shards(rows, header):
    os.makedirs(SHARD_DIR, exist_ok=True)
    written = []
    for s in sorted(rows):
        names = ', '.join(sorted({app_of(r) for r in rows[s]}))
        body = [
            '# Open work -- %s' % names,
            '',
            BANNER,
            '',
            '%d row(s), copied from docs/SAIRN-OPEN-WORK-INDEX.md.'
            % len(rows[s]),
            '',
            header,
            '|---|---|---|---|---|---|---|',
        ]
        first_row_line = len(body) + 1
        body.extend(rows[s])
        body.append('')
        p = os.path.join(SHARD_DIR, '%s.md' % s)
        io.open(p, 'w', encoding='utf-8', newline=NL).write(NL.join(body))
        written.append((s, len(rows[s]), os.path.getsize(p)))
        for i, line in enumerate(rows[s]):
            SHARD_LINES[id(line)] = first_row_line + i
    return written


# Populated by write_shards() so ACTIVE.md can point at a real line number
# rather than asking the reader to search a 838KB file for a paragraph.
SHARD_LINES = {}


def read_shards():
    """-> {slug: [rows]} from disk, or None if the directory is absent."""
    if not os.path.isdir(SHARD_DIR):
        return None
    out = {}
    for fn in sorted(os.listdir(SHARD_DIR)):
        if not fn.endswith('.md'):
            continue
        # ACTIVE.md IS NOT A SHARD. It carries one SHORT line per open row,
        # deliberately not the verbatim row, so comparing it against the index
        # reports drift on every run -- which is what the first --check did.
        if fn == 'ACTIVE.md':
            continue
        s = fn[:-3]
        text = io.open(os.path.join(SHARD_DIR, fn), encoding='utf-8',
                       errors='replace').read()
        rows = []
        for line in text.split(NL):
            if (line.startswith('|') and not SEPARATOR_RE.match(line)
                    and not HEADER_RE.match(line)):
                rows.append(line)
        out[s] = rows
    return out


def cmd_check():
    src, err = read_index()
    if err:
        print('COULD NOT RUN: %s' % err)
        return EXIT_COULD_NOT_RUN
    rows, header, stats = collect(src)
    if not rows:
        print('COULD NOT RUN: no App|Item rows were found in %s. Either the '
              'table shape changed or the file is not what this tool thinks '
              'it is -- and an empty answer would report every shard as '
              'correct.' % os.path.relpath(INDEX, REPO))
        return EXIT_COULD_NOT_RUN
    shards = read_shards()
    print('OPEN-WORK SHARDS -- criteria %s' % CRITERIA_VERSION)
    print('  index      : %s' % os.path.relpath(INDEX, REPO))
    print('  index rows : %d across %d table(s), %d app value(s)'
          % (stats['data_rows'], stats['tables'], len(rows)))
    if shards is None:
        print('\nCOULD NOT RUN: %s does not exist. Run --write first.'
              % os.path.relpath(SHARD_DIR, REPO))
        return EXIT_COULD_NOT_RUN

    findings = []
    for s in sorted(set(rows) | set(shards)):
        a, b = rows.get(s, []), shards.get(s, [])
        if a == b:
            continue
        only_index = [r for r in a if r not in b]
        only_shard = [r for r in b if r not in a]
        findings.append(
            '%s: index has %d row(s), the shard has %d. %d only in the index, '
            '%d only in the shard.'
            % (s, len(a), len(b), len(only_index), len(only_shard)))
        for r in (only_index[:2] + only_shard[:2]):
            # ASCII-FOLDED BEFORE PRINTING. The rows carry U+26A0 and other
            # non-cp1252 characters, and the first --check DIED with a
            # UnicodeEncodeError while printing a finding -- a check that
            # crashes mid-report has reported nothing, which is worse than the
            # drift it found.
            findings.append('    %s'
                            % r[:150].encode('ascii', 'replace').decode())

    # THE CASE VARIANTS ARE REPORTED, NEVER MERGED. Whether `PLATFORM` and
    # `Platform` are one app is a content question, and a tool that answered it
    # would be deciding what somebody else's row means.
    variants = {s: sorted(v) for s, v in stats['apps'].items() if len(v) > 1}
    if variants:
        print('\n%d slug(s) carry more than one App spelling -- REPORTED, not '
              'merged, because whether two spellings are one app is a content '
              'decision:' % len(variants))
        for s, v in sorted(variants.items()):
            print('  = %-22s %s' % (s, ', '.join(v)))

    print('')
    if findings:
        print('DRIFT (%d) -- the shards and the index disagree:' % len(findings))
        for f in findings:
            print('  ! %s' % f)
        print('\nRe-run `python tools/open_work_shard.py --write`. If that does '
              'not clear it, a row was edited in a shard rather than in the '
              'index, and the shard is NOT the place to edit one.')
        return EXIT_FINDING
    print('CLEAN -- every one of the %d index row(s) is present in its shard, '
          'byte for byte,\nand no shard carries a row the index does not. The '
          'index is still canonical.' % stats['data_rows'])
    return EXIT_CLEAN


def cmd_write():
    src, err = read_index()
    if err:
        print('COULD NOT RUN: %s' % err)
        return EXIT_COULD_NOT_RUN
    rows, header, stats = collect(src)
    if not rows:
        print('COULD NOT RUN: no App|Item rows found. Nothing was written.')
        return EXIT_COULD_NOT_RUN
    written = write_shards(rows, header)
    n_active, active_bytes = write_active(rows, SHARD_LINES)
    print('OPEN-WORK SHARDS -- wrote %d file(s) under %s'
          % (len(written) + 1, os.path.relpath(SHARD_DIR, REPO)))
    print('  %-24s %4d open row(s)  %7d bytes   <- READ THIS ONE'
          % ('ACTIVE.md', n_active, active_bytes))
    for s, n, size in sorted(written, key=lambda x: -x[1]):
        print('  %-24s %4d row(s)  %7d bytes' % (s, n, size))
    total = sum(n for _s, n, _z in written)
    print('  %-24s %4d row(s) total, against %d found in the index'
          % ('', total, stats['data_rows']))
    if total != stats['data_rows']:
        print('  ! THOSE TWO NUMBERS DISAGREE. Nothing is trustworthy until '
              'they match.')
        return EXIT_FINDING
    print('\nNow run --check. Writing is not proof.')
    return EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--write' in argv:
        return cmd_write()
    return cmd_check()


if __name__ == '__main__':
    sys.exit(main())
