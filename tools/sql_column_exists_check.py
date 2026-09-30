"""Does every column a sql/ file FILTERS ON actually exist on that table?

    python tools/sql_column_exists_check.py
    python tools/sql_column_exists_check.py --json
    python tools/sql_column_exists_check.py --selftest

── THE DEFECT THIS WOULD HAVE CAUGHT, AND IT REACHED origin/main ───────────
2026-09-29. A residue-removal block was pushed in a doc naming `entry_id` on
`mech_checks` and `mech_takeoffs`. Those tables use `check_id` and `takeoff_id`;
`entry_id` is what the REST of this platform's blob tables use, and the two were
conflated by habit.

**EVERY STATEMENT IN THAT BLOCK WOULD ERROR 42703 undefined_column.** The select
returns nothing, the deletes remove nothing, and the confirm step -- the one
meant to prove the rows are gone -- cannot print 0 either; it errors too. So a
removal script that looked complete would have deleted nothing, and in any runner
that reports the last successful statement rather than the first failing one, it
would read as a clean sweep.

**A COLUMN NAME IS THE ONE PART OF HAND-WRITTEN SQL NOTHING CHECKS.** A typo in a
table name fails loudly at the first read; a typo in a column name fails exactly
as loudly IF a human is watching the output, and silently otherwise. The schema is
in the repository and the deployed column list is in db/schema_snapshot.json, so
this is checkable and was not being checked.

── WHAT IT CHECKS, NARROWLY AND ON PURPOSE ─────────────────────────────────
For each statement in each sql/ file it can attribute to ONE table, it validates
the identifiers used in a FILTER POSITION -- `where <col> =`, `and <col> =`,
`<col> is null`, `<col> in (` -- against that table's column list.

FILTERS ONLY, NOT EVERY IDENTIFIER. A filter is where a wrong column silently
matches nothing; a wrong column in a select list is a loud error with no data
loss behind it, and widening this to every identifier means parsing expressions,
aliases and CTEs, which is a SQL parser. This is deliberately not one.

── WHERE THE TRUTH COMES FROM, AND WHY THERE ARE TWO SOURCES ───────────────
1. THE DECLARED schema: `create table ... (...)` blocks across sql/. Complete for
   anything sql/ creates, and it is what a reviewer reads.
2. THE DEPLOYED columns: db/schema_snapshot.json, captured from
   information_schema. It is what a statement will actually meet.

BOTH, BECAUSE THEY CAN DISAGREE. Every schema file uses
`create table if not exists`, so a table created before a column was added keeps
the old shape and the declared source would bless a column the database does not
have. A name is only ACCEPTED when at least one source has it, and a name present
in one and absent from the other is reported as a DISAGREEMENT rather than as
clean -- that is the case the 2026-09-29 defect would have landed in if the
deployed and declared shapes had drifted.

── THE SNAPSHOT IS MISSING THE ONE FIELD THAT WOULD MAKE THIS COMPLETE ─────
db/schema_snapshot.json is `{table: [column, ...]}` and carries no nullability,
no type and no constraint. sql/schema_snapshot_query.sql selects
`jsonb_agg(c.column_name ...)` and never `c.is_nullable`. So this check can say a
column EXISTS and cannot say anything about it -- which is enough for the defect
it was built for and not enough for the NOT NULL question that came up the same
day. Adding `is_nullable` to that aggregate is one line and is named in the
report.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(REPO, 'db', 'schema_snapshot.json')

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

# A statement's table. Only the forms that name ONE table unambiguously; a join
# is skipped and counted, because attributing a filter to the wrong side of a
# join is a false finding and this check must not manufacture one.
TABLE_RE = re.compile(
    r'\b(?:from|update|into|delete\s+from)\s+(?:public\.)?([a-z_][a-z0-9_]*)', re.I)
JOIN_RE = re.compile(r'\bjoin\b', re.I)
# A filter position: the identifier whose value is being compared.
FILTER_RE = re.compile(
    r'\b(?:where|and|or)\s+(?:public\.)?(?:[a-z_][a-z0-9_]*\.)?'
    r'([a-z_][a-z0-9_]*)\s*(?:=|<>|!=|>=|<=|>|<|\bis\b|\bin\b|\blike\b)', re.I)

# SQL words a FILTER_RE capture can be, which are never columns.
NOT_A_COLUMN = frozenset((
    'not', 'exists', 'select', 'true', 'false', 'null', 'current_setting',
    'case', 'when', 'then', 'else', 'end', 'count', 'coalesce', 'encode',
    'digest', 'lower', 'upper', 'now', 'octet_length', 'length', 'auth',
    'cast', 'extract', 'any', 'all', 'array', 'jsonb_agg', 'to_jsonb',
))


def _strip(sql):
    """Comments out, so a column named only in prose is not validated."""
    sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.S)
    return re.sub(r'--[^\n]*', ' ', sql)


def declared_columns():
    """{table: {column}} from every `create table` block under sql/."""
    out = {}
    files = subprocess.run(['git', '-C', REPO, 'ls-files', 'sql'],
                           capture_output=True, text=True).stdout.split()
    for rel in files:
        if not rel.endswith('.sql'):
            continue
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError:
            continue
        for m in re.finditer(
                r'create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?'
                r'([a-z_][a-z0-9_]*)\s*\(([\s\S]*?)\n\s*\)\s*;', _strip(src), re.I):
            tbl, body = m.group(1).lower(), m.group(2)
            cols = set()
            for line in body.split('\n'):
                cm = re.match(r'\s*([a-z_][a-z0-9_]*)\s+\S', line)
                if cm and cm.group(1).lower() not in (
                        'primary', 'unique', 'constraint', 'foreign', 'check'):
                    cols.add(cm.group(1).lower())
            if cols:
                out.setdefault(tbl, set()).update(cols)
        # ── ALTER TABLE ADD COLUMN, AND WITHOUT IT THIS CHECK IS UNUSABLE ────
        # The first real run reported FIVE findings and all five were the same
        # false positive: a migration that ADDS a column and then queries it in
        # the same file. Reading only `create table` blocks means every migration
        # looks like it filters on a column that does not exist -- five false
        # positives on a clean repository, which is enough to get a gate switched
        # off, and the reason to close it before proposing this as one.
        for m in re.finditer(
                r'alter\s+table\s+(?:if\s+exists\s+)?(?:public\.)?([a-z_][a-z0-9_]*)'
                r'([\s\S]*?);', _strip(src), re.I):
            tbl = m.group(1).lower()
            for am in re.finditer(
                    r'add\s+column\s+(?:if\s+not\s+exists\s+)?([a-z_][a-z0-9_]*)',
                    m.group(2), re.I):
                out.setdefault(tbl, set()).add(am.group(1).lower())
    return out


def deployed_columns():
    """{table: {column}} from the snapshot, or None when it cannot be read."""
    if not os.path.isfile(SNAPSHOT):
        return None
    try:
        d = json.loads(io.open(SNAPSHOT, encoding='utf-8').read())
    except ValueError:
        return None
    if not isinstance(d, dict) or not d:
        return None
    return dict((k.lower(), set(c.lower() for c in v))
                for k, v in d.items() if isinstance(v, list))


def statements(sql):
    return [s for s in _strip(sql).split(';') if s.strip()]


def scan_text(sql, declared, deployed):
    """(findings, disagreements, skipped) for one file's text."""
    findings, disagree, skipped = [], [], []
    for st in statements(sql):
        # ── GRANTS, POLICIES AND FUNCTION BODIES ARE NOT QUERIES ─────────────
        # TABLE_RE matched the `on` in `grant ... on ... to service_role` and the
        # `from` in `revoke ... from service_role`, so the first run counted 591
        # of its 1012 skipped statements as "table not in either source: on" and
        # "...: service_role". That is noise inflating the blind count, which is
        # worse than not counting -- it makes the honest disclosure unreadable.
        if re.match(r'\s*(?:grant|revoke|create\s+policy|drop\s+policy|'
                    r'alter\s+table|comment\s+on|create\s+index|drop\s+index|'
                    r'create\s+extension|do\s|set\s)', st, re.I):
            continue
        tables = TABLE_RE.findall(st)
        if not tables:
            continue
        if JOIN_RE.search(st) or len(set(t.lower() for t in tables)) > 1:
            skipped.append(('multi-table statement', st.strip()[:70]))
            continue
        tbl = tables[0].lower()
        dcl, dep = declared.get(tbl), (deployed or {}).get(tbl)
        if dcl is None and dep is None:
            skipped.append(('table not in either source: %s' % tbl,
                            st.strip()[:70]))
            continue
        for col in set(c.lower() for c in FILTER_RE.findall(st)):
            if col in NOT_A_COLUMN:
                continue
            in_dcl = dcl is not None and col in dcl
            in_dep = dep is not None and col in dep
            if not in_dcl and not in_dep:
                findings.append({'table': tbl, 'column': col,
                                 'statement': st.strip()[:90]})
            elif dcl is not None and dep is not None and in_dcl != in_dep:
                disagree.append({'table': tbl, 'column': col,
                                 'declared': in_dcl, 'deployed': in_dep})
    return findings, disagree, skipped


def selftest():
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    dcl = {'mech_checks': {'id', 'license_hash', 'check_id', 'data'}}
    dep = {'mech_checks': {'id', 'license_hash', 'check_id', 'data'}}

    # THE 2026-09-29 STATEMENT, VERBATIM IN SHAPE.
    f, d, s = scan_text(
        "delete from public.mech_checks where entry_id = 'GATE-LIVE-CHECK';",
        dcl, dep)
    ck('THE DEFECT: entry_id on mech_checks is REPORTED',
       len(f) == 1 and f[0]['column'] == 'entry_id')

    f, d, s = scan_text(
        "delete from public.mech_checks where check_id = 'GATE-LIVE-CHECK';",
        dcl, dep)
    ck('CONTROL: the CORRECT column is not reported', not f)

    f, d, s = scan_text(
        "select * from public.mech_checks where license_hash = encode(digest('K','sha256'),'hex');",
        dcl, dep)
    ck('CONTROL: a function call in the value position is not read as a column',
       not f)

    f, d, s = scan_text(
        "select 1 from public.mech_checks c join public.mech_docs d on true "
        "where d.nonexistent = 'x';", dcl, dep)
    ck('a JOIN is SKIPPED and counted, not guessed at',
       not f and len(s) == 1)

    f, d, s = scan_text("delete from public.mech_checks where check_id = 'x';",
                        dcl, {'mech_checks': {'id', 'license_hash', 'data'}})
    ck('DECLARED-vs-DEPLOYED DISAGREEMENT is its own answer, not a finding and '
       'not clean', not f and len(d) == 1)

    f, d, s = scan_text("delete from public.unknown_tbl where whatever = 'x';",
                        dcl, dep)
    ck('an unknown TABLE is skipped and counted rather than reported as a bad '
       'column', not f and len(s) == 1)
    print('')
    return EXIT_FINDING if bad else EXIT_CLEAN


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        print('sql_column_exists_check --selftest\n')
        return selftest()

    declared = declared_columns()
    deployed = deployed_columns()
    if not declared:
        sys.stderr.write(
            'COULD NOT RUN: no `create table` block parsed out of sql/, so no '
            'column could be validated. NOTHING WAS CHECKED -- this is not a '
            'clean run.\n')
        return EXIT_COULD_NOT_RUN

    files = [f for f in subprocess.run(['git', '-C', REPO, 'ls-files', 'sql'],
                                       capture_output=True, text=True).stdout.split()
             if f.endswith('.sql')]
    findings, disagree, skipped = [], [], []
    for rel in files:
        src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                      errors='replace').read()
        f, d, s = scan_text(src, declared, deployed)
        for x in f:
            x['file'] = rel
        for x in d:
            x['file'] = rel
        findings += f
        disagree += d
        skipped += [(rel,) + t for t in s]

    if args.json:
        print(json.dumps({'findings': findings, 'disagreements': disagree,
                          'skipped': len(skipped)}, indent=2, sort_keys=True))
        return EXIT_FINDING if findings else EXIT_CLEAN

    print('SQL COLUMN EXISTENCE -- does a filtered column exist on its table?')
    print('  sql files scanned            : %d' % len(files))
    print('  tables with a DECLARED shape : %d' % len(declared))
    print('  tables in the DEPLOYED snapshot: %s'
          % (len(deployed) if deployed is not None else 'SNAPSHOT UNREADABLE'))
    print('')
    print('  FILTERS ON A COLUMN NEITHER SOURCE HAS : %d' % len(findings))
    for x in findings:
        print('    %s  %s.%s' % (x['file'], x['table'], x['column']))
        print('        %s' % x['statement'])
    print('  DECLARED/DEPLOYED DISAGREEMENTS        : %d' % len(disagree))
    for x in disagree:
        print('    %s  %s.%s  declared=%s deployed=%s'
              % (x['file'], x['table'], x['column'], x['declared'], x['deployed']))

    # ── WHAT THIS CHECK CANNOT SEE, COUNTED IN ITS OWN OUTPUT ───────────────
    # The rule this platform adopted on 2026-09-25: a report-only screen prints
    # its own blind-spot count as a declared, counted line, because a total is
    # not a location and a clean run over a narrow population reads as a clean
    # run over everything.
    import collections
    why = collections.Counter(t[1] if len(t) > 1 else 'unknown' for t in skipped)
    print('')
    print('  BLIND TO THIS CHECK: %d statement(s) were NOT validated, and they '
          'are not counted clean:' % len(skipped))
    for reason, n in why.most_common(8):
        print('      %-46s %d' % (reason[:46], n))
    print('    A multi-table statement is skipped because attributing a filter to '
          'the wrong side of a')
    print('    join is a false finding, and this is deliberately not a SQL parser.')
    print('    FILTER POSITIONS ONLY -- a wrong column in a SELECT list is a loud '
          'error with no')
    print('    silent data loss behind it, and validating every identifier means '
          'parsing expressions.')
    if deployed is None:
        print('    THE DEPLOYED SNAPSHOT WAS NOT READ, so every verdict above '
              'rests on the DECLARED')
        print('    schema alone -- and every schema file uses `create table if '
              'not exists`, so a table')
        print('    created before a column was added keeps the old shape.')
    print('    NULLABILITY, TYPE AND CONSTRAINTS ARE NOT KNOWN AT ALL: '
          'db/schema_snapshot.json is')
    print('    {table: [column]}, and sql/schema_snapshot_query.sql selects '
          'c.column_name and never')
    print('    c.is_nullable. Adding it to that aggregate is one line.')
    print('')
    return EXIT_FINDING if findings else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
