"""Is db/schema_snapshot.json still describing the database this repo builds?

WHY. The snapshot is a PASTED CAPTURE. sql/schema_snapshot_query.sql is run in
the Supabase SQL editor, the single JSON cell is copied, and step 3 is "save it
as db/schema_snapshot.json". Step 3 is a human action with nothing behind it,
and on 2026-09-11 it was measurably skipped: the query had been run the night
before, the committed snapshot was still the 2026-09-02 capture, and the working
copy was byte-identical to HEAD.

THAT IS NOT A TIDINESS PROBLEM. tools/gate_column_check.py reads this file to
answer "does this column exist", and a column missing from a stale capture is
indistinguishable from a column that does not exist. Its one live finding is a
missing column. `mech_checks` answered provisioned:true on MECH-PINNACLE-2026
that same day and is absent from the snapshot -- so the capture was already
demonstrably behind the database, and anything reasoning from it was reasoning
from a partial picture without being told so.

WHAT IT DOES. Reads every `create table [if not exists] <name>` in sql/ and asks
whether the snapshot knows that table. A name in sql/ but not in the snapshot has
exactly two readings and the tool refuses to choose between them:

  * the SQL has never been run, so the table does not exist. A real finding, and
    the reason the cleanup-file and load-gate rows exist;
  * the SQL HAS been run and the snapshot is behind. A capture problem.

BOTH READINGS ARE REAL, SIMULTANEOUSLY, AND THAT IS MEASURED NOT ARGUED. Two of
the 39 were checked live through api/sd-data on 2026-09-11:

  mech_checks   provisioned:true  on MECH-PINNACLE-2026 -- the table EXISTS and
                the snapshot is behind.
  grd_rounds    provisioned:false on GRD-PINNACLE-2026 -- the table does NOT
                exist; sql/sairngrounds_caddie_schema.sql has never been run.

Same list, opposite causes. Anyone who resolves this list by picking one
explanation for all 39 will be wrong about the other kind, which is why the tool
reports the question rather than an answer.

IT DISAMBIGUATES WHERE IT HONESTLY CAN. A table that sql/ creates, that api/
QUERIES, and that the snapshot lacks is the high-signal set: live code expects
it. Those are listed first and separately. Everything else is listed as
undecidable, because guessing which of the two readings applies is exactly the
kind of confident wrong answer this repo keeps finding.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * whether a table the snapshot DOES list still exists -- a capture can be
    stale in that direction too and nothing here would notice;
  * columns. This is table-level only; a table present with a missing column
    looks clean;
  * tables created outside sql/ entirely.

Usage:
    python tools/schema_snapshot_freshness.py
    python tools/schema_snapshot_freshness.py --json

Exit 0 when the snapshot knows every table sql/ creates, 1 when it does not,
2 when the snapshot is missing or unreadable -- which is not a pass.
"""
import glob
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(REPO, 'db', 'schema_snapshot.json')

CREATE_RE = re.compile(
    r'create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?([a-z_][a-z0-9_]*)', re.I)
QUERY_RE = re.compile(r"/rest/v1/([a-z_][a-z0-9_]*)|\brest(?:Url)?\(\s*'([a-z_][a-z0-9_]*)")


def strip_sql_comments(text):
    out, i, n = list(text), 0, len(text)
    while i < n:
        if text.startswith('--', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
        else:
            i += 1
    return ''.join(out)


def captured_when():
    r = subprocess.run(['git', 'log', '-1', '--format=%cs (%cr)', '--',
                        'db/schema_snapshot.json'],
                       cwd=REPO, capture_output=True, text=True)
    return (r.stdout or '').strip() or 'unknown'


def main(argv):
    if not os.path.exists(SNAPSHOT):
        print('db/schema_snapshot.json is missing. NOT a pass -- nothing was checked.')
        return 2
    try:
        with io.open(SNAPSHOT, encoding='utf-8') as fh:
            snap = json.load(fh)
    except Exception as e:
        print('db/schema_snapshot.json could not be read: %s. NOT a pass.' % e)
        return 2

    created = {}
    for f in sorted(glob.glob(os.path.join(REPO, 'sql', '*.sql'))):
        src = strip_sql_comments(io.open(f, encoding='utf-8', errors='replace').read())
        for t in CREATE_RE.findall(src):
            created.setdefault(t, os.path.relpath(f, REPO).replace(os.sep, '/'))

    queried = set()
    for f in glob.glob(os.path.join(REPO, 'api', '**', '*.js'), recursive=True):
        if f.endswith('.test.js'):
            continue
        src = io.open(f, encoding='utf-8', errors='replace').read()
        code = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))
        for a, b in QUERY_RE.findall(code):
            queried.add(a or b)
    queried.discard('rpc')

    missing = sorted(t for t in created if t not in snap)
    high = [t for t in missing if t in queried]
    undecided = [t for t in missing if t not in queried]

    if '--json' in argv:
        print(json.dumps({'snapshot_tables': len(snap), 'sql_tables': len(created),
                          'missing_and_queried': high, 'missing_only': undecided,
                          'created_in': {t: created[t] for t in missing}}, indent=1))
    else:
        print('SCHEMA SNAPSHOT FRESHNESS -- report only, nothing was written')
        print('  snapshot captured : %s' % captured_when())
        print('  tables in snapshot: %d' % len(snap))
        print('  tables created in sql/: %d' % len(created))
        print('  created in sql/ but ABSENT from the snapshot: %d' % len(missing))
        print('    of those, also QUERIED by api/ : %d  <- live code expects these'
              % len(high))
        for t in high:
            print('\n  %s' % t)
            print('      created in %s, queried by api/, NOT in the snapshot.' % created[t])
            print('      Either that SQL has never been run, or the snapshot is behind.')
            print('      Both are real; this tool will not guess which.')
        if undecided:
            print('\n  ABSENT but not queried by api/ -- undecidable here, listed not hidden:')
            for t in undecided:
                print('      %-42s %s' % (t, created[t]))
        print('\n  TO RE-CAPTURE: run sql/schema_snapshot_query.sql in the Supabase SQL')
        print('  editor, copy the single JSON cell, and SAVE IT as db/schema_snapshot.json')
        print('  -- then COMMIT it. On 2026-09-11 the query had been run the night before')
        print('  and the file was still byte-identical to the 2026-09-02 capture, so the')
        print('  save-and-commit half is the step that actually goes missing.')

    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
