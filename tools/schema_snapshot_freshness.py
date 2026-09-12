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

BOTH READINGS WERE REAL SIMULTANEOUSLY, AND THAT WAS MEASURED NOT ARGUED. Two
of the 39 were checked live through api/sd-data on 2026-09-11:

  mech_checks   provisioned:true  on MECH-PINNACLE-2026 -- the table EXISTS and
                the snapshot is behind.
  grd_rounds    provisioned:false on GRD-PINNACLE-2026 -- the table does NOT
                exist; sql/sairngrounds_caddie_schema.sql has never been run.

Same list, opposite causes. Anyone resolving the list by picking one explanation
for all of it would have been wrong about the other kind.

── IT NOW RESOLVES MOST OF THEM, AND THE RULE IS NOT A GUESS (2026-09-12) ──
The refusal above was right while the capture was CHRONICALLY STALE. It leaves
real information on the floor once a fresh capture exists, because git knows
when each CREATE statement was written:

    if the CREATE was committed BEFORE the capture ran, and the capture STILL
    does not list the table, then "the snapshot is behind" is EXCLUDED for that
    table -- the snapshot is newer than the declaration. What remains is that
    the SQL was never run.

The other direction stays genuinely undecidable and is still reported that way:
a CREATE committed after the capture is simply newer than the snapshot, which is
ordinary and not a finding. A CREATE stamped at the same instant as the capture
is undecidable too -- the migration could have run between the two.

MEASURED THE DAY THIS LANDED, against the capture generated 2026-09-11 15:42
UTC (375 tables, committed 2026-09-12 in 3d603dd0): 89 tables declared in sql/
are absent, 31 of them QUERIED BY LIVE api/ CODE, and ALL 89 resolve to NEVER
RUN. Zero undecidable. Corroborated by a second source sharing no mechanism --
CC's storefront probes answered 503 UNAVAILABLE / NOT_PROVISIONED live for three
of the StoneDesk five on 2026-09-12, and the grd_rounds read above put it at
provisioned:false. An absence alone is consistent with a stale snapshot and a
503 alone with an outage; neither explanation survives the other.

BECAUSE EVERY REAL CASE RESOLVES ONE WAY, THE LIVE DATA CANNOT TELL A WORKING
RULE FROM ONE STUCK ON "never-run". tests/run_schema_verdict_probe.py section 4
plants the opposite case on a throwaway git repo and demands "undecidable", and
section 3 plants the table name in a COMMENT committed months before the CREATE
and demands the later date -- dating a declaration from prose that merely names
it would call a live table never-run.

STILL TRUE: a table that sql/ creates, that api/ QUERIES, and that the snapshot
lacks is the high-signal set, and those are listed first and separately.

WHAT IT CANNOT SEE, said here rather than discovered later:
  * whether a table the snapshot DOES list still exists -- a capture can be
    stale in that direction too and nothing here would notice;
  * columns. This is table-level only; a table present with a missing column
    looks clean;
  * tables created outside sql/ entirely;
  * whether the CAPTURE ITSELF IS COMPLETE for the schema it covers. Every
    "never run" verdict rests on that assumption, and a truncated or narrowly
    scoped capture would make every absence look like a migration that did not
    happen. The verdict prints the evidence it used so it can be argued with
    rather than taken on trust.

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


def captured_when(snap):
    """When the snapshot was CAPTURED, preferring the capture's own stamp.

    The first version read the git commit date, and that is the wrong field for
    exactly the reason this tool exists. On 2026-09-11 a fresh capture sat
    uncommitted in the working tree while git still reported 2026-09-02, so the
    header said "10 days ago" about a file generated minutes earlier. A tool
    whose job is detecting staleness must not take its own freshness reading
    from metadata that lags the thing it describes.

    `_generated_at` comes out of the query itself. The commit date is still
    printed beside it, because a capture that exists only in one clone is not
    yet a fact for anyone else -- and that gap is the failure this tool was
    built for.
    """
    gen = str(snap.get('_generated_at') or '').strip() or 'no _generated_at in the file'
    r = subprocess.run(['git', 'log', '-1', '--format=%cs', '--',
                        'db/schema_snapshot.json'],
                       cwd=REPO, capture_output=True, text=True)
    committed = (r.stdout or '').strip() or 'never committed'
    dirty = subprocess.run(['git', 'status', '--porcelain', '--',
                            'db/schema_snapshot.json'],
                           cwd=REPO, capture_output=True, text=True)
    pending = ' -- UNCOMMITTED, so no other clone has it yet' if (dirty.stdout or '').strip() else ''
    return '%s (generated); last committed %s%s' % (gen, committed, pending)


def _parse_stamp(s):
    """Seconds-resolution UTC tuple from either stamp format, or None.

    Handles the capture's `2026-09-11 15:42:46.942345+00` and git's
    `--date=iso-strict` `2026-09-11T11:42:46-04:00`. Compared as UTC, because
    the capture is stamped in UTC and commits are stamped in local time -- a
    naive string compare of those two is wrong by the offset, which for this
    repo is four hours and would silently reclassify anything committed in that
    window on the day of a capture.
    """
    import datetime
    s = (s or '').strip()
    if not s:
        return None
    # The offset is TWO digits in the capture (`+00`) and four in git's
    # iso-strict (`-04:00`). The first version required four and silently
    # returned None for every capture stamp, which made the tool report
    # "no usable date" for all 31 tables -- a disambiguation that answered
    # "undecidable" to everything reads exactly like the old refusal.
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})'
                 r'(?:\.\d+)?\s*(Z|[+-]\d{2}(?::?\d{2})?)?$', s)
    if not m:
        return None
    y, mo, d, hh, mm, ss, off = m.groups()
    dt = datetime.datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss))
    if off and off != 'Z':
        off = off.replace(':', '')
        sign = -1 if off[0] == '-' else 1
        dt -= datetime.timedelta(hours=sign * int(off[1:3]),
                                 minutes=sign * int(off[3:5] or 0))
    return dt


def create_introduced(table, sql_path):
    """When the CREATE TABLE for `table` first appeared in `sql_path`, as UTC.

    Searched by the CREATE STATEMENT TEXT, not by the bare table name. The name
    alone is wrong here: it occurs in comments, in grant lines and in a header
    describing the file, any of which can predate the CREATE by weeks and would
    date the declaration too early -- which in this tool means calling a table
    NEVER RUN on the strength of a comment. Same class as section 1.2 of
    docs/SAIRN-PROCESS-RULES.md, one step over.
    """
    src = io.open(os.path.join(REPO, sql_path), encoding='utf-8',
                  errors='replace').read()
    m = re.search(
        r'create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?%s\b' % re.escape(table),
        strip_sql_comments(src), re.I)
    if not m:
        return None
    r = subprocess.run(['git', 'log', '--reverse', '--format=%ad',
                        '--date=iso-strict', '-S', m.group(0), '--', sql_path],
                       cwd=REPO, capture_output=True, text=True)
    for line in (r.stdout or '').split('\n'):
        if line.strip():
            return _parse_stamp(line.strip())
    return None


def verdicts(missing, created, snap):
    """Resolve "never run" vs "snapshot is behind" where git can decide it.

    ── WHY THIS IS NOT A GUESS ─────────────────────────────────────────────
    The tool used to print both readings for every absent table and refuse to
    choose, which was right while the capture was chronically stale. It leaves
    real information on the floor once the capture is fresh:

        if the CREATE statement was committed BEFORE the capture ran, and the
        capture still does not list the table, then "the snapshot is behind"
        is EXCLUDED for that table. The snapshot is newer than the declaration.
        What remains is that the SQL was never run.

    The other direction stays genuinely undecidable and is still reported as
    such: a CREATE committed after the capture is simply newer than the
    snapshot, which is ordinary and not a finding.

    MEASURED THE DAY THIS WAS ADDED (2026-09-12), against the capture generated
    2026-09-11 15:42 UTC: all 31 tables that api/ queries and the snapshot
    lacks resolve to NEVER RUN, and zero were undecidable. Corroborated by a
    second source that shares no mechanism -- CC's storefront probes answered
    503 UNAVAILABLE / NOT_PROVISIONED live for three of them on 2026-09-12,
    and an earlier live read put grd_rounds at provisioned:false.

    THE RESIDUAL UNCERTAINTY, STATED RATHER THAN IMPLIED: this assumes the
    capture is COMPLETE for the schema it covers. A capture truncated or scoped
    to fewer schemas would make every absence look like a never-run migration.
    That limit is real and is why the verdict names the evidence it used.
    """
    cap = _parse_stamp(str(snap.get('_generated_at') or ''))
    out = {}
    for t in missing:
        when = create_introduced(t, created[t])
        if cap is None or when is None:
            out[t] = ('undecidable', when, 'no usable date on the capture or the CREATE')
        elif when < cap:
            out[t] = ('never-run', when,
                      'the capture is NEWER than this CREATE and still lacks the '
                      'table, so "the snapshot is behind" is excluded')
        else:
            out[t] = ('undecidable', when,
                      'this CREATE is NEWER than the capture -- ordinary, not a finding')
    return out


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

    real_tables = sum(1 for k in snap if not k.startswith('_'))
    missing = sorted(t for t in created if t not in snap)
    high = [t for t in missing if t in queried]
    undecided = [t for t in missing if t not in queried]

    vd = verdicts(missing, created, snap)
    never_run_queried = [t for t in high if vd[t][0] == 'never-run']

    if '--json' in argv:
        print(json.dumps({'snapshot_tables': real_tables, 'sql_tables': len(created),
                          'missing_and_queried': high, 'missing_only': undecided,
                          'never_run_and_queried': never_run_queried,
                          'verdicts': {t: {'verdict': vd[t][0],
                                           'create_committed': (vd[t][1].isoformat()
                                                                if vd[t][1] else None),
                                           'because': vd[t][2]} for t in missing},
                          'created_in': {t: created[t] for t in missing}}, indent=1))
    else:
        print('SCHEMA SNAPSHOT FRESHNESS -- report only, nothing was written')
        print('  snapshot captured : %s' % captured_when(snap))
        # Real tables only. `_constraints` and `_generated_at` are metadata, and
        # counting them inflated every "tables in snapshot" figure this tool has
        # printed -- 258 where the truth was 254, 379 where it is 375.
        print('  tables in snapshot: %d' % real_tables)
        print('  tables created in sql/: %d' % len(created))
        print('  created in sql/ but ABSENT from the snapshot: %d' % len(missing))
        print('    of those, also QUERIED by api/ : %d  <- live code expects these'
              % len(high))
        print('    of THOSE, resolved to NEVER RUN : %d  <- the migration did not happen'
              % len(never_run_queried))
        for t in high:
            v, when, why = vd[t]
            print('\n  %s' % t)
            print('      created in %s, queried by api/, NOT in the snapshot.' % created[t])
            if v == 'never-run':
                print('      VERDICT: NEVER RUN. CREATE committed %s; %s.'
                      % (when.strftime('%Y-%m-%d %H:%M UTC') if when else '?', why))
            else:
                print('      UNDECIDABLE: %s.' % why)
                print('      Either that SQL has never been run, or the snapshot is behind.')
        if undecided:
            nr = sum(1 for t in undecided if vd[t][0] == 'never-run')
            print('\n  ABSENT and NOT queried by api/ -- %d of %d also resolve to '
                  'never-run, listed not hidden:' % (nr, len(undecided)))
            for t in undecided:
                print('      %-42s %-11s %s' % (t, vd[t][0], created[t]))
        print('\n  WHAT "NEVER RUN" RESTS ON, so it can be argued with: the capture')
        print('  is newer than the CREATE statement and still lacks the table, so the')
        print('  competing reading -- that the snapshot is behind -- is excluded for')
        print('  that table. It assumes the capture is COMPLETE for the schema it')
        print('  covers; a truncated or narrowly-scoped capture would make every')
        print('  absence look like a migration that did not happen.')
        print('\n  TO RE-CAPTURE: run sql/schema_snapshot_query.sql in the Supabase SQL')
        print('  editor, copy the single JSON cell, and SAVE IT as db/schema_snapshot.json')
        print('  -- then COMMIT it. On 2026-09-11 the query had been run the night before')
        print('  and the file was still byte-identical to the 2026-09-02 capture, so the')
        print('  save-and-commit half is the step that actually goes missing.')

    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
