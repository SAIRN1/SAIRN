#!/usr/bin/env python
"""Does this SQL file reference a table or column that does not exist?

WHY THIS EXISTS. A SQL file on this platform is written in a clone, reviewed as
text, and then pasted into the Supabase editor by hand. Nothing between those
two steps checks that the tables and columns it names are real. A typo'd column
in an INSERT fails loudly, which is fine; a typo'd column in a WHERE clause of
an UPDATE or DELETE does not fail at all -- it errors, or worse, it matches
nothing and reports success with zero rows touched. "0 rows" and "nothing needed
changing" look identical in the editor.

That is the same shape as every expensive failure recorded in this repo: not a
crash, a quiet wrong answer. See SAIRN-ACTIVE-WORK-cc.md for the two most recent
-- a seed correction that was committed but never loaded, and an export button
that had been handing users a one-line CSV.

TWO SCHEMA SOURCES, AND THE DIFFERENCE BETWEEN THEM IS THE POINT.

  LIVE      --live <snapshot.json>, produced by running
            sql/schema_snapshot_query.sql in the Supabase SQL editor and saving
            the JSON result. This is authoritative: it is what the database
            actually has.

  DECLARED  Parsed from every CREATE TABLE / ALTER TABLE ADD COLUMN in sql/*.sql
            in this repo. Always available, needs no credentials, and is only as
            true as the repo is. A table created by hand in the editor and never
            written down does not exist here; a schema file written but never
            run exists here and not in the database.

WITHOUT --live THIS TOOL DOES NOT PASS ANYTHING. It runs against DECLARED, says
so in every line of output, and exits 2 -- a distinct code, not 0. The platform
already learned this lesson in the push gate: "could not tell" reported as
silence is how a gate gets hollowed out, so an unavailable live schema is a
LOUD partial result and never a green light.

WHAT IT RESOLVES, AND WHAT IT REFUSES TO GUESS.

  Resolved to table AND columns:
      insert into T (c1, c2, ...)
      update T set c1 = ..., c2 = ...
      T.c  (qualified references anywhere, including WHERE and JOIN)

  Resolved to table only:
      select ... from T,  delete from T,  join T,  alter table T

  DELIBERATELY NOT RESOLVED: bare column names in a SELECT list or a WHERE
  clause of a multi-table statement. Deciding which table an unqualified `name`
  belongs to needs alias tracking and join resolution, and a wrong guess here
  produces a confident false finding -- the failure mode that gets a checker
  switched off. Those are COUNTED and reported as unresolved rather than
  silently dropped, so the output says how much of the file it actually
  checked.

Aliases, CTE names and subquery labels are collected and excluded, so
`with recent as (...) select * from recent` does not report a missing table
called `recent`. System schemas (information_schema, pg_catalog, pg_temp) are
skipped.

USAGE
    python tools/sairn_sql_preflight.py sql/some_change.sql
    python tools/sairn_sql_preflight.py --live db/schema_snapshot.json sql/*.sql
    python tools/sairn_sql_preflight.py --gate --require-live --live db/schema_snapshot.json sql/x.sql

EXIT CODES
    0  LIVE checked, nothing missing
    1  something is missing (either source)
    2  no live snapshot -- DECLARED-only, NOT a pass
    3  bad usage / unreadable input
    4  --require-live was asked for and no usable live schema exists

--require-live (added 2026-09-01) EXISTS BECAUSE EXIT 2 WAS BEING READ AS A PASS
BY A CALLER THAT ONLY CHECKED FOR 1. The push gate ran this in DECLARED mode and
denied only on exit 1, so every other outcome -- including "there is no live
schema at all" -- allowed the push silently. That is the same could-not-tell-
reported-as-silence shape this file's own docstring warns about, reproduced
inside the gate meant to prevent it.

With --require-live, an absent, unreadable or empty snapshot is exit 4 and never
exit 0/2, so a caller that treats "not 1" as success still cannot mistake a
missing schema for a clean file. The caller is expected to BLOCK on 4.
"""
import re
import sys
import os
import glob
import json

SYSTEM_SCHEMAS = ('information_schema', 'pg_catalog', 'pg_temp', 'pg_toast')

# Words that can follow a table position but are never a table name.
NOT_A_TABLE = {
    'select', 'values', 'set', 'where', 'from', 'join', 'on', 'as', 'and', 'or',
    'not', 'exists', 'case', 'when', 'then', 'else', 'end', 'with', 'only',
    'lateral', 'unnest', 'generate_series', 'jsonb_array_elements', 'json_to_record',
    'dual', 'returning', 'using', 'into', 'conflict', 'do', 'nothing', 'update',
    # Set-returning functions appear in FROM position and are not relations.
    'jsonb_each', 'jsonb_each_text', 'json_each', 'json_each_text',
    'jsonb_array_elements_text', 'jsonb_to_recordset', 'json_array_elements',
    'regexp_split_to_table', 'string_to_table', 'each',
}


def strip_noise(sql):
    """Remove comments and string/dollar-quoted literals.

    Literals go first and are replaced by a placeholder of equal length so that
    offsets are preserved and a table name never gets read out of a string. A
    seed file full of `insert ... values ('update customers set ...')` would
    otherwise produce findings from its own data.
    """
    def blank(m):
        return re.sub(r'\S', ' ', m.group(0))
    sql = re.sub(r'/\*.*?\*/', blank, sql, flags=re.S)
    sql = re.sub(r'(?m)--[^\n]*', blank, sql)
    sql = re.sub(r"\$\$.*?\$\$", blank, sql, flags=re.S)
    sql = re.sub(r"'(?:[^']|'')*'", blank, sql, flags=re.S)
    return sql


def _clean_ident(tok):
    tok = tok.strip().strip('"')
    if '.' in tok:
        schema, tok = tok.rsplit('.', 1)
        if schema.strip('"').lower() in SYSTEM_SCHEMAS:
            return None
    tok = tok.lower()
    # System catalogs are usually written UNQUALIFIED -- `from pg_class c join
    # pg_namespace n` -- so the schema check above never sees them. The audit
    # and introspection files in sql/ are full of these and every one was
    # reported as an undeclared table.
    if tok.startswith('pg_'):
        return None
    return tok


def declared_schema(sql_dir='sql'):
    """table -> set(columns), from every CREATE TABLE / ALTER TABLE ADD COLUMN."""
    schema = {}
    for path in sorted(glob.glob(os.path.join(sql_dir, '*.sql'))):
        text = strip_noise(open(path, encoding='utf-8', errors='replace').read())
        for m in re.finditer(
                r'create\s+(?:temp\s+|temporary\s+|unlogged\s+)?table\s+(?:if\s+not\s+exists\s+)?([\w".]+)\s*\((.*?)\)\s*;',
                text, re.S | re.I):
            name = _clean_ident(m.group(1))
            if not name:
                continue
            cols = schema.setdefault(name, set())
            for line in _split_top_level(m.group(2)):
                line = line.strip()
                if not line:
                    continue
                first = line.split()[0].lower().strip('"')
                # table-level constraints are not columns
                if first in ('primary', 'foreign', 'unique', 'check', 'constraint', 'exclude', 'like'):
                    continue
                cols.add(first)
        _absorb_ctas(text, schema)
        _absorb_alters(text, schema)
    return schema


def _absorb_ctas(text, schema):
    """`create [temp] table X as select ...` -- a table with no column list.

    Registered with an EMPTY column set on purpose. Empty means "this table
    exists, its columns are unknown", and check() already skips column
    comparison in that case rather than reporting every column as missing. The
    four `_grant_baseline_*` / `_anon_*_baseline_*` scratch tables in the grant
    audit files are all this form and all four were reported as undeclared
    until this existed.
    """
    for m in re.finditer(
            r'create\s+(?:temp\s+|temporary\s+|unlogged\s+)?table\s+(?:if\s+not\s+exists\s+)?([\w".]+)\s+as\b',
            text, re.I):
        name = _clean_ident(m.group(1))
        if name:
            schema.setdefault(name, set())


def _absorb_alters(text, schema):
    """Every ADD COLUMN in an ALTER TABLE, not just the first.

    THIS WAS A REAL FALSE POSITIVE, found by hand-checking the tool's own first
    finding rather than by reading the tool. The original pattern matched
    `alter table T add column c` once per statement, so this --

        alter table public.dnt_appointments
          add column if not exists provider_id text,
          add column if not exists operatory_id text,
          add column if not exists start_time timestamptz,
          add column if not exists end_time timestamptz,
          add column if not exists status text;

    -- registered provider_id and silently dropped the other four. The tool then
    reported sairndental_demo_seed_2026-08-27.sql as inserting four columns that
    do not exist. They do exist. Reporting four missing columns in a demo seed
    for a live dental app, wrongly, is exactly the kind of finding that gets a
    checker switched off after one use.
    """
    for m in re.finditer(r'alter\s+table\s+(?:if\s+exists\s+)?([\w".]+)(.*?);', text, re.S | re.I):
        name = _clean_ident(m.group(1))
        if not name:
            continue
        for cm in re.finditer(r'add\s+column\s+(?:if\s+not\s+exists\s+)?([\w"]+)', m.group(2), re.I):
            schema.setdefault(name, set()).add(cm.group(1).strip('"').lower())


def _split_top_level(body):
    """Split a CREATE TABLE body on commas that are not inside parentheses."""
    out, depth, cur = [], 0, []
    for ch in body:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append(''.join(cur))
    return out


def local_names(text):
    """CTE names, table aliases and subquery labels -- never real tables."""
    names = set()
    # A CTE may carry a column list -- `with declared(table_name) as (values ...)`
    # -- and the chain separator may sit anywhere relative to the closing paren.
    # Both forms are real in sql/ and both were being reported as missing tables.
    CTE = r'([\w"]+)\s*(?:\([^)]*\))?\s+as\s*(?:materialized\s+|not\s+materialized\s+)?\('
    for m in re.finditer(r'\bwith\s+(?:recursive\s+)?' + CTE, text, re.I):
        names.add(m.group(1).strip('"').lower())
    for m in re.finditer(r',\s*' + CTE, text, re.I):
        names.add(m.group(1).strip('"').lower())
    for m in re.finditer(r'\b(?:from|join)\s+[\w".]+\s+(?:as\s+)?([a-z_][\w]*)\b', text, re.I):
        a = m.group(1).lower()
        if a not in NOT_A_TABLE:
            names.add(a)
    for m in re.finditer(r'\)\s*(?:as\s+)?([a-z_][\w]*)\b', text, re.I):
        a = m.group(1).lower()
        if a not in NOT_A_TABLE:
            names.add(a)
    return names


def split_grants(text):
    """Pull GRANT/REVOKE statements out before the generic table scan.

    `revoke all on public.x from anon;` has a FROM whose object is a ROLE, not a
    table, and the first version of this tool duly reported missing tables
    called `anon` and `service_role` on the very first file it was pointed at.
    The table in a grant is the one after ON, and nothing after TO or FROM in
    these statements is ever a table.

    Returns (text_without_grants, tables_named_in_grants).
    """
    tables = set()

    # The object of a GRANT is not always a table, and the first version of this
    # function assumed it was. Across the repo that produced 15 findings for a
    # table called `schema` (from `on all tables in schema public`), 3 for
    # `function` (from `grant execute on function ...`) and one each for
    # `sequence` and `tables` (from `alter default privileges ... grant ... on
    # tables`). All noise, all from one lazy pattern.
    OBJ = re.compile(
        r'\bon\s+('
        r'all\s+\w+\s+in\s+schema\s+[\w"]+'   # all tables|sequences|routines in schema S
        r'|schema\s+[\w"]+'
        r'|function\s+[\w".]+\s*\([^)]*\)'
        r'|function\s+[\w".]+'
        r'|sequence\s+[\w".]+'
        r'|database\s+[\w"]+'
        r'|tables?\b'                        # `... grant select on tables to r`
        r'|sequences\b|routines\b|functions\b'
        r'|(?:table\s+)?[\w".]+'             # a real table, with or without TABLE
        r')', re.I)

    def take(m):
        for om in OBJ.finditer(m.group(0)):
            obj = om.group(1).strip()
            low = obj.lower()
            if re.match(r'^(all\s|schema\s|function\s|sequence\s|database\s)', low):
                continue
            if low in ('table', 'tables', 'sequence', 'sequences', 'routines', 'functions'):
                continue
            tables.add(re.sub(r'^table\s+', '', obj, flags=re.I))
        return re.sub(r'\S', ' ', m.group(0))

    text = re.sub(r'\b(?:grant|revoke)\b.*?;', take, text, flags=re.S | re.I)
    return text, tables


def references(text):
    """Return (table_only, table_columns, unresolved_count)."""
    tables = set()
    cols = {}
    text, grant_tables = split_grants(text)
    local = local_names(text)

    def add_table(raw):
        n = _clean_ident(raw)
        if n and n not in NOT_A_TABLE and n not in local:
            tables.add(n)
            return n
        return None

    for g in grant_tables:
        add_table(g)

    for m in re.finditer(r'\binsert\s+into\s+([\w".]+)\s*\(([^)]*)\)', text, re.I):
        t = add_table(m.group(1))
        if t:
            for c in m.group(2).split(','):
                c = c.strip().strip('"').lower()
                if re.fullmatch(r'[a-z_][\w]*', c or ''):
                    cols.setdefault(t, set()).add(c)

    for m in re.finditer(r'\bupdate\s+([\w".]+)\s+set\s+(.*?)(?:\bwhere\b|\breturning\b|;)', text, re.S | re.I):
        t = add_table(m.group(1))
        if t:
            for assign in _split_top_level(m.group(2)):
                c = assign.split('=')[0].strip().strip('"').lower()
                if re.fullmatch(r'[a-z_][\w]*', c or ''):
                    cols.setdefault(t, set()).add(c)

    # `a is distinct from b` contains the word FROM and no table. This produced
    # findings for `tst` and `test_data` -- both right-hand operands of a
    # comparison in a SAIRNlaw verification file, neither one a relation.
    text = re.sub(r'\bis\s+(?:not\s+)?distinct\s+from\b', ' IS_DISTINCT ', text, flags=re.I)

    for pat in (r'\bfrom\s+([\w".]+)', r'\bjoin\s+([\w".]+)',
                r'\bdelete\s+from\s+([\w".]+)', r'\balter\s+table\s+(?:if\s+exists\s+)?([\w".]+)',
                r'\btruncate\s+(?:table\s+)?([\w".]+)'):
        for m in re.finditer(pat, text, re.I):
            add_table(m.group(1))

    # ALIAS -> TABLE, so `a.last_login_at` is checked against the table `a`
    # stands for. Without this the qualified-reference probe case (D4 in
    # tests/sql_preflight/probe_defects.sql) was MISSED: the alias is in the
    # local-names set, so the reference was skipped as if it named a CTE.
    # Only aliases bound to a name this file actually treats as a table are
    # mapped, so a CTE alias still resolves to nothing rather than to a guess.
    # AN ALIAS REBOUND AS A COLUMN-ALIAS LIST IS NOT A TABLE ALIAS. Found
    # 2026-09-02 on the first LIVE run, against the real snapshot: two audit
    # files bind `k` twice --
    #
    #     from public.license_keys k                     -- table alias
    #     join lateral unnest(con.conkey) as k(attnum)   -- column alias list
    #
    # -- and this map is per FILE, not per statement, so `k.attnum` in the
    # second statement was attributed to license_keys and reported as
    # MISSING_COLUMN license_keys.attnum. Both findings were false, and both
    # would have blocked a push touching those files on the gate's first day
    # live, which is exactly how a checker gets switched off.
    #
    # The narrow fix is to drop any identifier that is ALSO bound as `as
    # name(cols)` anywhere in the file. Per-statement alias scoping would be
    # the general answer and is a bigger change with its own regression risk;
    # this removes the observed false positive without widening what the tool
    # claims to resolve. A name used both ways in one file is ambiguous to a
    # per-file map, and refusing to guess is this tool's stated rule.
    rebound = set()
    for m in re.finditer(r'\bas\s+([a-z_][\w]*)\s*\([^)]*\)', text, re.I):
        rebound.add(m.group(1).lower())

    alias = {}
    for m in re.finditer(r'\b(?:from|join)\s+([\w".]+)(?:\s+as)?\s+([a-z_][\w]*)\b', text, re.I):
        tgt = _clean_ident(m.group(1))
        a = m.group(2).lower()
        if tgt and tgt in tables and a not in NOT_A_TABLE and a not in rebound:
            alias[a] = tgt

    for m in re.finditer(r'\b([a-z_][\w]*)\.([a-z_][\w]*)\b', text, re.I):
        owner, col = m.group(1).lower(), m.group(2).lower()
        if owner in ('public',) or owner in SYSTEM_SCHEMAS:
            continue
        if owner in alias:
            cols.setdefault(alias[owner], set()).add(col)
        elif owner in local:
            continue
        elif owner in tables:
            cols.setdefault(owner, set()).add(col)

    # Bare identifiers this tool deliberately does not attribute to a table.
    unresolved = len(re.findall(r'\bwhere\b', text, re.I))
    return tables, cols, unresolved


def load_live(path):
    """Accept either {table: [cols]} or information_schema rows.

    Returns (schema, generated_at). `_generated_at` is written by
    sql/schema_snapshot_query.sql and is reported rather than enforced -- the
    tool has no way to know when the last migration ran, so it shows the age and
    lets the reader judge instead of inventing a staleness rule it cannot back.
    """
    data = json.load(open(path, encoding='utf-8'))
    schema = {}
    generated = None
    if isinstance(data, dict):
        for t, c in data.items():
            # EVERY underscore-prefixed key is metadata, not a table. This used
            # to skip only '_generated_at', so the two
            # `_anon_*_baseline_2026_08_26` keys already in the snapshot were
            # being loaded as tables whose "columns" were their contents. It
            # never surfaced because nothing references a table starting with
            # an underscore -- a latent wrong answer waiting for the first file
            # that did. Fixed here rather than left, since this change adds a
            # third metadata key.
            if t.startswith('_'):
                if t == '_generated_at':
                    generated = c
                continue
            schema[_clean_ident(t) or t.lower()] = set(x.lower() for x in c)
        return schema, generated
    for row in data:
        t = (row.get('table_name') or row.get('table') or '').lower()
        c = (row.get('column_name') or row.get('column') or '').lower()
        if t:
            schema.setdefault(t, set())
            if c:
                schema[t].add(c)
    return schema, generated


def check(path, schema, source='DECLARED', self_declare=True):
    raw = open(path, encoding='utf-8', errors='replace').read()
    text = strip_noise(raw)
    tables, cols, unresolved = references(text)
    known = dict((k, set(v)) for k, v in schema.items())
    if self_declare:
        # A file that CREATEs a table may then INSERT into it in the same run.
        own = declared_from_text(text)
        for t, c in own.items():
            known.setdefault(t, set()).update(c)
    findings = []
    # WORDING IS NOT COSMETIC HERE. Against LIVE, an absent table IS missing --
    # the database was asked. Against DECLARED, all that is known is that no
    # CREATE TABLE in this repo declares it, which is also true of every table
    # that predates the repo's schema files (public.license_keys, for one). Two
    # different claims deserve two different words.
    label = 'MISSING_TABLE' if source == 'LIVE' else 'UNDECLARED_TABLE'
    for t in sorted(tables):
        if t not in known:
            findings.append((label, t, ''))
            continue
        for c in sorted(cols.get(t, ())):
            if known[t] and c not in known[t]:
                findings.append(('MISSING_COLUMN', t, c))
    return findings, tables, cols, unresolved


def declared_from_text(text):
    schema = {}
    for m in re.finditer(r'create\s+table\s+(?:if\s+not\s+exists\s+)?([\w".]+)\s*\((.*?)\)\s*;',
                         text, re.S | re.I):
        name = _clean_ident(m.group(1))
        if not name:
            continue
        cols = schema.setdefault(name, set())
        for line in _split_top_level(m.group(2)):
            line = line.strip()
            if line:
                first = line.split()[0].lower().strip('"')
                if first not in ('primary', 'foreign', 'unique', 'check', 'constraint', 'exclude', 'like'):
                    cols.add(first)
    _absorb_ctas(text, schema)
    _absorb_alters(text, schema)
    return schema


# ── CHECK-CONSTRAINT DRIFT, added 2026-09-02 ───────────────────────────────
# WHY: SAIRNdental's dnt_appointments enforced octet_length(data::text) <= 65536
# in production while sql/sairndental_data_schema.sql said 1291059 and a
# migration sat written-but-unrun. Nothing could see it. This tool compared the
# two things that agreed -- tables and columns -- and never looked at the one
# that did not. A schema file claiming one bound while the database enforces
# another is the same class as a seed committed but never loaded, and it was
# invisible to every gate running at the time.
#
# NORMALISATION, AND ITS LIMIT, STATED. Postgres does not store what you typed:
# `octet_length(data::text) <= 65536` comes back as
# `CHECK ((octet_length((data)::text) <= 65536))`. Comparing raw text would
# report drift on every constraint in the platform, which is the
# permanently-red failure that made verify-skill-store's content check useless.
# So both sides are lowercased with all whitespace and parentheses removed.
# That is deliberately blunt: it cannot tell `a <= b` from `(a) <= (b)`, which
# is the point, but it also cannot tell `a and b` from `b and a`. A reordered
# predicate reads as drift. That is the safe direction -- a false positive gets
# looked at, a false negative is the bug this exists to catch.
CONSTRAINT_RE = re.compile(
    r'constraint\s+([a-z0-9_]+)\s+check\s*\((.*?)\)\s*(?:,|\)\s*;|$)',
    re.I | re.S)


def _norm_predicate(s):
    return re.sub(r'[\s()]+', '', (s or '').lower())


def declared_constraints(sql_dir='sql'):
    """{table: {constraint_name: predicate}} from every CREATE TABLE in sql/."""
    out = {}
    for path in sorted(glob.glob(os.path.join(sql_dir, '*.sql'))):
        text = strip_noise(open(path, encoding='utf-8', errors='replace').read())
        for m in re.finditer(r'create\s+table\s+(?:if\s+not\s+exists\s+)?([a-z0-9_."]+)\s*\((.*?)\n\s*\)\s*;',
                             text, re.I | re.S):
            table = _clean_ident(m.group(1))
            body = m.group(2)
            for c in CONSTRAINT_RE.finditer(body):
                out.setdefault(table, {})[c.group(1).lower()] = c.group(2)
    return out


def load_live_constraints(path):
    """{table: {name: definition}} from the snapshot's _constraints key."""
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception:
        return None
    raw = data.get('_constraints') if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return None
    out = {}
    for t, defs in raw.items():
        if isinstance(defs, dict):
            out[_clean_ident(t) or t.lower()] = {k.lower(): v for k, v in defs.items()}
    return out


def constraint_findings(declared, live):
    """(findings, unchecked) -- findings are (severity, table, name, detail)."""
    findings, unchecked = [], []
    if live is None:
        return findings, ['snapshot carries no _constraints key -- re-run '
                          'sql/schema_snapshot_query.sql to capture them']
    for table, cons in sorted(declared.items()):
        if table not in live:
            # The table itself may be genuinely absent; that is MISSING_TABLE's
            # job to report, not this one's. Saying nothing here would hide it,
            # so it is recorded as unchecked rather than skipped.
            unchecked.append('%s -- not present in the live snapshot, so its '
                             '%d declared CHECK(s) could not be compared'
                             % (table, len(cons)))
            continue
        for name, pred in sorted(cons.items()):
            got = live[table].get(name)
            if got is None:
                findings.append(('MISSING_CONSTRAINT', table, name,
                                 'declared in sql/ and NOT present on the live table'))
            elif _norm_predicate(pred) not in _norm_predicate(got):
                findings.append(('CONSTRAINT_DRIFT', table, name,
                                 'repo declares %s | live enforces %s'
                                 % (pred.strip(), got.strip())))
    return findings, unchecked


_GATE_LIVE_PATH = None   # set by main() before _gate(); keeps _gate's
                         # signature untouched for its existing callers.


def _gate(paths, schema, source):
    """--gate: a narrow, blockable answer for tools/sairn_push_gate_hook.py.

    THE EXIT CODE MEANS SOMETHING DIFFERENT HERE AND THAT IS DELIBERATE. The
    normal DECLARED run exits 2 because it cannot claim a file is correct. A
    gate is asking a smaller question it CAN answer without a live snapshot:

        the repo declares this table, and the repo does not declare this
        column -- so this INSERT/UPDATE names a column that, on the evidence
        in this repo, does not exist.

    That is MISSING_COLUMN, and it is the only class this blocks on.

    UNDECLARED_TABLE IS EXPLICITLY NOT BLOCKING. In DECLARED mode it fires on
    every real table with no tracked CREATE TABLE -- `license_keys` alone
    produces 17 across sql/, all of them correct code. Blocking on that would
    stop every licence-seed push on day one, and a gate that cries wolf gets
    switched off. They are printed as a note instead.

    MISSING_TABLE, WHICH ONLY EXISTS IN LIVE MODE, IS BLOCKING (2026-09-01).
    The two labels are not synonyms and check() already keeps them apart:
    UNDECLARED_TABLE means "no CREATE TABLE in this repo mentions it", which is
    true of plenty of real tables; MISSING_TABLE means the DATABASE WAS ASKED
    and does not have it. The second is a fact about production, so blocking on
    it is the whole reason to run against a live snapshot rather than the repo.

    Exit 0 = nothing blocking. Exit 1 = at least one blocking finding.
    Nothing else, so the hook keys on the code rather than parsing prose --
    a format change must not be able to silently disarm the gate.
    """
    BLOCKING_KINDS = ('MISSING_COLUMN', 'MISSING_TABLE')
    blocking, notes = [], []
    for path in paths:
        if not os.path.exists(path):
            continue
        findings, _, _, _ = check(path, schema, source)
        for kind, t, c in findings:
            entry = '%s: %s %s' % (os.path.basename(path), kind, t + ('.' + c if c else ''))
            (blocking if kind in BLOCKING_KINDS else notes).append(entry)
    for b in blocking:
        print(b)
    if notes:
        print('NON-BLOCKING (%s mode cannot prove these are absent from the database):' % source)
        for n in notes:
            print('  ' + n)
    # ── CHECK-constraint drift (2026-09-02) ───────────────────────────────
    # Blocks ONLY on a real disagreement, and only when the snapshot actually
    # carries constraint data. "The snapshot has no _constraints key" is a
    # could-not-tell, not a pass and not a block: making it blocking would
    # refuse every SQL push until someone re-runs the snapshot query, which is
    # how a gate gets switched off in its first hour.
    #
    # Once the data is there, drift IS blocking, because it is a fact about
    # production: the repo says one bound and the database enforces another,
    # which is exactly the state SAIRNdental shipped in with a 64 KiB ceiling
    # under a 1.2 MiB photo payload.
    if _GATE_LIVE_PATH:
        cf, cu = constraint_findings(declared_constraints(),
                                     load_live_constraints(_GATE_LIVE_PATH))
        if cf:
            print('')
            print('CHECK CONSTRAINT DRIFT -- the repo and the database disagree:')
            for kind, table, name, detail in cf:
                print('  %-20s %s.%s' % (kind, table, name))
                print('      %s' % detail)
            print('  A migration is inert until someone runs it. Apply it, or correct')
            print('  the schema file, then re-run sql/schema_snapshot_query.sql.')
            blocking = True
        # NO OUTPUT ON could-not-tell IN GATE MODE, and that is a deliberate
        # reversal. My first version printed a "NOT CHECKED (not a pass)" line
        # here and tests/sql_preflight/run_probe.py caught it immediately: it
        # asserts that a clean gate run is exit 0 AND SILENT, because the push
        # hook's clean case is silence. Printing on every clean SQL push is
        # noise, and quietly changing a contract another session encoded in a
        # committed test is not mine to do. The note still appears in the
        # normal (non-gate) output, which is where a human reads it.

    return 1 if blocking else 0


def _no_live(reason, live_path, require_live):
    """One place to report an unusable live schema, and one place to decide
    whether that is fatal. Under --require-live it is exit 4 and the caller is
    expected to block; without it the historical behaviour is unchanged."""
    print('LIVE SCHEMA UNAVAILABLE: %s' % reason)
    print('  expected snapshot: %s' % live_path)
    if not require_live:
        return None
    print('')
    print('*** BLOCKING. --require-live was asked for, and "could not tell" is')
    print('*** not a pass. Regenerate the snapshot before continuing:')
    print('***   1. run sql/schema_snapshot_query.sql in the Supabase SQL editor')
    print('***   2. save the single JSON result cell as %s' % live_path)
    return 4


def main(argv):
    live_path, paths, gate, require_live = None, [], False, False
    i = 0
    while i < len(argv):
        if argv[i] == '--live':
            i += 1
            if i >= len(argv):
                print('--live needs a path'); return 3
            live_path = argv[i]
        elif argv[i] == '--gate':
            gate = True
        elif argv[i] == '--require-live':
            require_live = True
        else:
            paths.append(argv[i])
        i += 1
    if not paths:
        print(__doc__); return 3
    if require_live and not live_path:
        rc = _no_live('--require-live given with no --live path', '(none given)', True)
        return rc

    if live_path:
        # EVERY WAY A SNAPSHOT CAN BE UNUSABLE GOES THROUGH ONE PATH. The
        # original code only handled "file not found" and only as exit 3; a
        # snapshot that existed but was truncated, empty, or invalid JSON threw
        # out of main() instead, and a hook that catches exceptions and allows
        # would have turned a corrupt schema into a silent pass.
        if not os.path.exists(live_path):
            rc = _no_live('snapshot file does not exist', live_path, require_live)
            if rc is not None:
                return rc
            print('LIVE SNAPSHOT NOT FOUND: %s' % live_path); return 3
        try:
            schema, generated = load_live(live_path)
        except Exception as e:
            rc = _no_live('snapshot is unreadable (%s)' % e, live_path, require_live)
            if rc is not None:
                return rc
            return 3
        if not schema:
            rc = _no_live('snapshot declares no tables', live_path, require_live)
            if rc is not None:
                return rc
            return 3
        source = 'LIVE'
    else:
        schema, generated, source = declared_schema(), None, 'DECLARED'

    if gate:
        globals()['_GATE_LIVE_PATH'] = live_path if source == 'LIVE' else None
        return _gate(paths, schema, source)

    print('schema source: %s  (%d tables, %d columns)%s' %
          (source, len(schema), sum(len(v) for v in schema.values()),
           '  snapshot taken: ' + generated if generated else ''))
    if source == 'LIVE' and not generated:
        print('note: snapshot carries no _generated_at, so its age is unknown. '
              'Regenerate with sql/schema_snapshot_query.sql if in doubt.')
    if source == 'DECLARED':
        print('*** NOT A PASS. No --live snapshot given, so this compares against the')
        print('*** repo\'s CREATE TABLE statements, not the database. A table created by')
        print('*** hand and never written down looks MISSING here; a schema file written')
        print('*** but never run looks PRESENT. Run sql/schema_snapshot_query.sql in the')
        print('*** Supabase editor, save the JSON, and re-run with --live for a real check.')
    print('')

    total = 0
    for path in paths:
        if not os.path.exists(path):
            print('%-52s UNREADABLE' % path); return 3
        findings, tables, cols, unresolved = check(path, schema, source)
        total += len(findings)
        status = 'clean' if not findings else '%d FINDING(S)' % len(findings)
        print('%-52s %-14s tables=%d cols-checked=%d where-clauses-not-attributed=%d' %
              (os.path.basename(path), status, len(tables),
               sum(len(v) for v in cols.values()), unresolved))
        for kind, t, c in findings:
            print('    %-16s %s' % (kind, t + ('.' + c if c else '')))

    # ── CHECK-constraint drift (2026-09-02) ───────────────────────────────
    # Runs only in LIVE mode: comparing the repo against itself would report
    # nothing by construction. Reported separately from the per-file findings
    # because it is a property of the DATABASE vs the repo, not of any file
    # being pushed -- the dental drift existed while every SQL file in the repo
    # was internally consistent.
    if source == 'LIVE':
        cf, cu = constraint_findings(declared_constraints(), load_live_constraints(live_path))
        if cf or cu:
            print('')
            print('CHECK CONSTRAINTS')
            for kind, table, name, detail in cf:
                print('    %-20s %s.%s' % (kind, table, name))
                print('        %s' % detail)
            for note in cu:
                print('    COULD NOT CHECK      %s' % note)
            if cf:
                print('    A schema file saying one bound while the database enforces another is')
                print('    the same class as a seed committed and never loaded. SAIRNdental ran')
                print('    that way with a 64 KiB ceiling under a 1.2 MiB photo payload.')
            total += len(cf)

    print('')
    print('TOTAL FINDINGS: %d' % total)
    if total:
        return 1
    return 0 if source == 'LIVE' else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
