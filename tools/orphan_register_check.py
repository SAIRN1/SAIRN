#!/usr/bin/env python
"""orphan_register_check.py -- find open-work rows that describe things which no
longer exist in the app.

WHY THIS EXISTS. On 2026-09-04 two rows in `docs/SAIRN-OPEN-WORK-INDEX.md` were
found to be stale by five weeks:

  * "panel-remnant double-render: sdRemnantRender() and remRender() both live"
    -- marked Open with a warning triangle. `remRender()` was deleted on
    2026-07-30; `stonedesk.html`'s orphaned-module register says so in two
    places.
  * "Two parallel template modules with different storage keys" -- marked Open.
    Resolved the same day; also in the register.

Both still paid for themselves, because checking them turned up real adjacent
defects. But a session trusting the index would have started by hunting July's
bugs, and nothing connected the index to the register in either direction.

── WHAT THIS CHECKS, AND WHY IT DOES NOT PARSE THE REGISTER ─────────────────
The first version of this tool tried to read the register's comment blocks and
extract which functions had been deleted. Three attempts, three different
failure modes:

  * narrow extraction: captured 2 of the 9 names in entry 4 and missed
    `remRender` -- the exact identifier that prompted the tool. It reported
    CLEAN against the historical index and would have shipped carrying a
    self-test claim in its own docstring that was FALSE.
  * wide extraction: pulled the prose words `finish`, `load`, `desc`, `ship`,
    `unit`, `result`, `notes`, `customer`, `date` and matched `date` against a
    SAIRNlaw row about a holiday statute -- eleven false findings.
  * camelCase-only extraction with a canonical-survivor subtraction: the
    subtraction window then swallowed most of the real names.

That churn IS the finding. A checker built on parsing English commentary is the
same class of thing as an assertion that matches prose about the code rather
than the code -- `sairn-code-scrubber` item 16, Shape A. So it does not parse
the register at all.

INSTEAD IT ASKS THE FILE. For every OPEN index row, take the identifiers the
row writes as code -- `` `name()` `` or `` `sd_key` `` -- and check whether they
exist in `stonedesk.html`:

  * a function name with no definition anywhere  -> the row describes something
    that is gone;
  * an `sd_*` storage key with no read and no write -> same.

No prose is interpreted on either side. The register remains the place a human
reads WHY something was removed; this only answers whether it is still there.

WHAT IT CANNOT CHECK, so a clean run is not over-read:

  * A row that names nothing in code form is invisible to it. That includes the
    template row above, which said "different storage keys" without naming
    them in its item cell -- it is caught only because its later cells do.
  * A row can be stale for reasons that have nothing to do with a missing
    identifier: a fixed bug, a decision taken, a figure that moved.
  * It reads "open" from the status column's text. An unusually phrased row
    slips past.

── IT HAS BEEN WATCHED GOING RED ────────────────────────────────────────────
A checker nobody has seen fail is a checker whose behaviour nobody knows. Point
this at the index as it stood before the 2026-09-04 corrections and it flags
the remnant row by name:

    git show 0e40bb8f:docs/SAIRN-OPEN-WORK-INDEX.md > /tmp/i.md
    python tools/orphan_register_check.py --index /tmp/i.md
    -> row 177 cites remRender() -- no definition in stonedesk.html

ONE OF THE TWO, NOT BOTH, AND THAT IS THE HONEST NUMBER. The template row said
"different storage keys" and named neither in code form, so it is invisible
here -- exactly the first limitation listed above, demonstrated rather than
asserted. Do not read a clean run as "the index is current".

Usage:
  python tools/orphan_register_check.py
  python tools/orphan_register_check.py --index <path>   # e.g. a historical copy

Exit codes: 0 clean / 1 findings / 2 error.
"""
import io
import os
import re
import sys

# Findings quote real index rows, which carry em dashes and warning triangles. A
# cp1252 stdout turns that into a crash INSIDE the reporting path -- a checker
# that dies while telling you what it found. Seen on this machine, 2026-09-04.
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, 'stonedesk.html')
INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')

# Phrases that mean a row is NOT open. Kept literal and short: a longer list
# makes this quieter, and quiet is the failure mode it exists to prevent.
CLOSED_MARKERS = ('closed', 'done', 'superseded', 'fixed', 'recovered', 'seeded',
                  'built and live', 'not a defect', 'accepted')

# Names that are real in the app but are not StoneDesk's own -- other apps'
# functions and platform helpers quoted in a StoneDesk row would otherwise read
# as missing. Only add here with a reason.
IGNORE_PREFIXES = ('dnt', 'rf_', 'sen', 'scp', 'law', 'sc_', 'sb_')


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def is_defined(src, name):
    n = re.escape(name)
    pats = [r'function\s+' + n + r'\s*\(',
            r'\b' + n + r'\s*[:=]\s*(async\s+)?function',
            r'window\.' + n + r'\s*=',
            r'\b' + n + r'\s*=\s*(async\s*)?\(']
    return any(re.search(p, src) for p in pats)


_SQL_NAMES = None


def sql_table_names():
    """Every `sd_*` name declared as a table in sql/.

    An index row citing `sd_public_rate_limits` is naming a SUPABASE TABLE, not
    a localStorage key, and it is correct that stonedesk.html never mentions it
    -- the server does. Without this, three such citations in one row were
    reported as things that had disappeared. The two namespaces share the `sd_`
    prefix, so the only way to tell them apart is to ask the schema files.
    """
    global _SQL_NAMES
    if _SQL_NAMES is None:
        names = set()
        sqldir = os.path.join(REPO, 'sql')
        if os.path.isdir(sqldir):
            for fn in os.listdir(sqldir):
                if fn.endswith('.sql'):
                    names |= set(re.findall(r'\b(sd_[a-z_]{3,})\b', read(os.path.join(sqldir, fn))))
        _SQL_NAMES = names
    return _SQL_NAMES


def key_touched(src, key):
    if key in sql_table_names():
        return True          # a database table, not this file's concern
    return ("'%s'" % key) in src or ('"%s"' % key) in src


def open_rows(index_path):
    rows = []
    for n, line in enumerate(read(index_path).split('\n'), 1):
        if not line.startswith('| **'):
            continue
        cells = line.split('|')
        if len(cells) < 5:
            continue
        item, status = cells[2], cells[3]
        if any(m in status.lower() for m in CLOSED_MARKERS):
            continue
        if item.strip().startswith('~~'):
            continue
        # StoneDesk rows only: this tool reads stonedesk.html, so a SAIRNlaw row
        # naming a SAIRNlaw function would be reported missing for no reason.
        if '**StoneDesk**' not in cells[1]:
            continue
        rows.append((n, item.strip(), line))
    return rows


def cited(line):
    """Identifiers a row writes AS CODE: `name()` or `sd_key` in backticks."""
    fns = set(re.findall(r'`([a-z][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*)\(\)`', line))
    fns |= set(re.findall(r'`([a-z][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*)\(`', line))
    keys = set(re.findall(r'`(sd_[a-z_]{3,})`', line))
    fns = {f for f in fns if not f.lower().startswith(IGNORE_PREFIXES)}
    return fns, keys


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    index_path = argv[argv.index('--index') + 1] if '--index' in argv else INDEX
    for p in (APP, index_path):
        if not os.path.exists(p):
            sys.stderr.write('not found: %s\n' % p)
            return 2
    src = read(APP)
    rows = open_rows(index_path)
    print('OPEN_STONEDESK_ROWS:%d' % len(rows))

    findings, checked = [], 0
    for n, item, line in rows:
        fns, keys = cited(line)
        checked += len(fns) + len(keys)
        gone_fns = sorted(f for f in fns if not is_defined(src, f))
        gone_keys = sorted(k for k in keys if not key_touched(src, k))
        if gone_fns:
            findings.append('row %d cites %s -- no definition in stonedesk.html. %s'
                            % (n, ', '.join(g + '()' for g in gone_fns), item[:80]))
        if gone_keys:
            findings.append('row %d cites %s -- the key appears nowhere in '
                            'stonedesk.html. %s' % (n, ', '.join(gone_keys), item[:80]))
    print('IDENTIFIERS_CHECKED:%d' % checked)

    if findings:
        print('\n--- OPEN ROWS DESCRIBING THINGS THAT ARE GONE ---')
        for f in findings:
            print('  ' + f)
        print('\nRESULT:FINDINGS (%d)' % len(findings))
        print('Read the row before closing it: on 2026-09-04 both stale rows still '
              'pointed at real adjacent defects.')
        return 1
    print('\nRESULT:CLEAN -- every identifier cited by an open StoneDesk row still '
          'exists in the file.')
    print('NOTE: a row that cites nothing in code form is invisible here, and a row '
          'can be stale for reasons this cannot see. A clean run is not a claim '
          'that the index is current.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
