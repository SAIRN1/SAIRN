"""Does a server file read a column that does not exist on the table it queried?

WHY. Three identical entitlement gates -- api/sd-data.js, api/sd-render.js and
api/_lib/sd-store.js -- read `lic.trial_ends_at` and refuse with 402 when the
trial has expired. `trial_ends_at` IS NOT A COLUMN on license_keys. It is always
null, the comparison is always false, and the 402 has never been reachable on any
licence. The entitlement check for the whole StoneDesk data path, the paid render
feature and the agent store, structurally unable to fire.

It survived because the code says so in prose. api/_lib/license.js initialises
`trial_ends_at: null` and comments the select as reading "newly-added columns
(e.g. trial_ends_at) ... if present" -- aspirational, and the column never
arrived. A reader sees a field, a gate, and a comment explaining the field, and
has no reason to doubt any of it. Same shape as StoneDesk's Layer 12 and Layer
30: not a missing check, a check that can only ever return the reassuring answer.

WHAT IT DOES. For each file under api/, it finds the PostgREST tables that file
queries (`/rest/v1/<table>?...`), and every property read off the parsed rows.
If the file queries EXACTLY ONE table, every such property must be a column of
that table in db/schema_snapshot.json. A property that is not is a read that can
only ever produce undefined.

ATTRIBUTION IS REFUSED RATHER THAN GUESSED. A file that queries several tables
cannot have its `row.x` reads attributed without real dataflow analysis, so those
files are COUNTED AND NAMED as not-checked instead of being quietly skipped --
api/sd-data.js is the big one, and calling it clean would be the exact failure
this tool exists to catch.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * anything in a multi-table file, as above;
  * a column that exists but is never populated -- the snapshot answers
    "does this column exist", not "does anything write to it";
  * a snapshot that has gone stale. db/schema_snapshot.json is a capture, and
    its age is printed on every run so the answer is read with its date
    attached rather than as a standing fact.

Usage:
    python tools/gate_column_check.py
    python tools/gate_column_check.py --json

Exit 0 clean, 1 when a read names a column that does not exist, 2 when the
snapshot is missing or unreadable -- which is not a pass.
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

# BOTH URL FORMS. A literal /rest/v1/<table>, and the `rest('<table>?...')`
# helper this codebase defines in five places -- counting only the literal form
# attributed three files and called the rest unattributable, which understates
# the coverage rather than the risk, but understating coverage is still a wrong
# number.
REST_RE = re.compile(r"/rest/v1/([a-z_][a-z0-9_]*)|\brest(?:Url)?\(\s*'([a-z_][a-z0-9_]*)")
# `const row = rows[0];` / `const r = rows[0]` -- the row variable, and then any
# property read off it.
ROWVAR_RE = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*\w+\[0\]\s*;")

# Properties that are read off a row but are NOT expected to be columns: the
# code's own bookkeeping. Declared with a reason, never left implicit.
NOT_A_COLUMN = {
    'length': 'array length, not a row property',
}


def snapshot():
    with io.open(SNAPSHOT, encoding='utf-8') as fh:
        return json.load(fh)


def snapshot_age_days():
    r = subprocess.run(['git', 'log', '-1', '--format=%cr', '--', 'db/schema_snapshot.json'],
                       cwd=REPO, capture_output=True, text=True)
    return (r.stdout or '').strip() or 'unknown'


def main(argv):
    if not os.path.exists(SNAPSHOT):
        print('db/schema_snapshot.json is missing. NOT a pass -- nothing was checked.')
        return 2
    try:
        cols = snapshot()
    except Exception as e:
        print('db/schema_snapshot.json could not be read: %s. NOT a pass.' % e)
        return 2

    findings, unattributed, checked = [], [], []
    absent_tables = set()
    files = sorted(glob.glob(os.path.join(REPO, 'api', '**', '*.js'), recursive=True))
    for f in files:
        if f.endswith('.test.js'):
            continue
        rel = os.path.relpath(f, REPO).replace(os.sep, '/')
        src = io.open(f, encoding='utf-8', errors='replace').read()
        # Comments describe tables and columns constantly in this repo; a table
        # name in prose is not a query. Strip before attributing.
        code = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)
        # `rest('rpc/name')` is a PostgREST FUNCTION call, not a table, and
        # capturing it as one made api/_lib/ai-rate-limit.js report "queries a
        # table absent from the snapshot" -- a finding about nothing. Dropped
        # by name because `rpc` is a reserved path segment, not a table anyone
        # could legitimately create.
        tables = sorted({a or b for a, b in REST_RE.findall(code)} - {'rpc'})
        if not tables:
            continue
        if len(tables) != 1:
            unattributed.append((rel, len(tables)))
            continue
        table = tables[0]
        if table not in cols:
            absent_tables.add(table)
            unattributed.append((rel, 0))
            continue
        known = set(cols[table])
        rowvars = set(ROWVAR_RE.findall(code))
        if not rowvars:
            continue
        checked.append((rel, table))
        for var in sorted(rowvars):
            for m in re.finditer(r'\b' + re.escape(var) + r'\.(\w+)', code):
                prop = m.group(1)
                if prop in known or prop in NOT_A_COLUMN:
                    continue
                line = code[:m.start()].count('\n') + 1
                findings.append({'file': rel, 'table': table, 'property': prop,
                                 'var': var, 'approx_line': line})

    # One entry per (file, property); the same read appears many times.
    seen, unique = set(), []
    for x in findings:
        k = (x['file'], x['property'])
        if k in seen:
            continue
        seen.add(k)
        unique.append(x)

    if '--json' in argv:
        print(json.dumps({'findings': unique, 'unattributed': unattributed,
                          'checked': checked}, indent=1))
    else:
        print('GATE COLUMN CHECK -- report only, nothing was written')
        print('  schema snapshot   : db/schema_snapshot.json, %d tables, last updated %s'
              % (len(cols), snapshot_age_days()))
        print('  files attributed  : %d  (query exactly one table)' % len(checked))
        print('  reads of a column that DOES NOT EXIST: %d' % len(unique))
        print('  NOT checked       : %d  (multi-table or unknown table -- NOT a pass)'
              % len(unattributed))
        for x in unique:
            print('\n  %s  reads %s.%s' % (x['file'], x['var'], x['property']))
            print('      `%s` is not a column of %s, so this read is always undefined.'
                  % (x['property'], x['table']))
            print('      %s has: %s' % (x['table'], ', '.join(sorted(cols[x['table']]))))
        if unattributed:
            print('\n  NOT CHECKED, named rather than skipped:')
            for rel, n in unattributed:
                why = ('queries %d tables -- attribution needs real dataflow' % n) if n else \
                      'queries a table absent from the snapshot'
                print('      %-44s %s' % (rel, why))
        if absent_tables:
            print('')
            print('  THE SNAPSHOT MAY BE STALE, and that is not a detail.')
            print('  %d table(s) queried by api/ are absent from it: %s'
                  % (len(absent_tables), ', '.join(sorted(absent_tables))))
            print('  A table missing from a capture is indistinguishable from a table')
            print('  that does not exist -- and the same is true one level down, of a')
            print('  COLUMN. Demonstrated, not hypothetical: mech_checks answered')
            print('  provisioned:true on MECH-PINNACLE-2026 on 2026-09-11 and is NOT in')
            print('  this snapshot. Re-capture before treating an absence as a finding.')
        print('\n  NOTE: this answers "does the column exist", not "does anything write')
        print('  to it". A column that exists and is never populated fails the same way.')

    return 1 if unique else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
