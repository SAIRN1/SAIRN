#!/usr/bin/env python
r"""advisory_lock_isolation_check.py -- a pg_advisory lock whose correctness
rests on READ COMMITTED, with nothing enforcing READ COMMITTED.

    python tools/advisory_lock_isolation_check.py
    python tools/advisory_lock_isolation_check.py --json
    python tools/advisory_lock_isolation_check.py --self-check   # fixtures only

Exit 0 clean, 1 findings, 2 COULD NOT RUN. REPORT ONLY.

── THE DEFECT, AND WHY IT SURVIVES REVIEW ──────────────────────────────────
`pg_advisory_xact_lock` serialises ACQUISITION. It does not move the
transaction's SNAPSHOT. Under READ COMMITTED every statement after the lock
takes a fresh snapshot, so a caller that waited sees what the previous holder
committed and read-decide-write is genuinely atomic. Under REPEATABLE READ or
SERIALIZABLE the snapshot is fixed at the transaction's first data statement, so
a caller that WAITED ON THE LOCK still reads from before the holder committed --
and then writes.

THE CAP OVER-RUNS, OR THE BALANCE OVERDRAWS, WITH THE LOCK WORKING PERFECTLY THE
WHOLE TIME. There is no error, no contention symptom, and nothing in the lock's
own behaviour to review. That is why it survives: the code containing the bug is
correct, and the thing that is wrong is a setting in another file.

── WHAT THIS REPORTS, AND THE TWO SHAPES IT DELIBERATELY DOES NOT ──────────
A function is reported only when ALL of:

  1. it takes an advisory lock, and
  2. after the lock it READS state into a variable or aggregates a table, and
  3. after that read it WRITES (insert/update), and
  4. it does not check `current_setting('transaction_isolation')`.

TWO SHAPES ARE SAFE BY CONSTRUCTION AND ARE CLASSIFIED, NOT SUPPRESSED. Both
fail LOUD under REPEATABLE READ -- Postgres raises serialization_failure (40001)
rather than silently reading stale -- which is the opposite of the defect above:

  SELECT ... FOR UPDATE   re-reads the latest committed row version or errors.
                          `sairn_circuit_breaker_step` is this.
  UPDATE ... RETURNING    a single atomic statement; an update against a row a
                          concurrent transaction committed raises 40001.
                          `rf_allocate_invoice_number` is this.

REPORTING THOSE WOULD BE WORSE THAN MISSING THEM. A checker that flags the two
correct patterns alongside the broken one teaches readers that its findings are
noise, and this repo's own record is that an over-reporting first draft is a
column people switch off.

── WHAT IT CANNOT SEE, STATED RATHER THAN IMPLIED ─────────────────────────
It reads SQL TEXT IN THIS REPOSITORY. It cannot see the deployed database. A
file carrying the guard proves nothing about the installed function until the
migration is re-run, and `create or replace` means an OLDER file defining the
same function can silently REVERT a guard if somebody re-runs it. That specific
hazard is reported separately, as SUPERSEDED, because it is real and invisible:
sql/sairn_ai_usage_columns_2026-09-02.sql still carries a guard-less definition
of a function that was guarded on 2026-09-15.
"""

import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(REPO, 'sql')

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

FUNC_RE = re.compile(
    r'create\s+or\s+replace\s+function\s+(?:public\.)?(\w+)\s*\(', re.I)
LOCK_RE = re.compile(r'pg_advisory(?:_xact)?_lock\s*\(', re.I)
GUARD_RE = re.compile(r"current_setting\s*\(\s*'transaction_isolation'\s*\)", re.I)
# A read whose value is carried forward into a later decision.
READ_RE = re.compile(r'\bselect\b[^;]*?\binto\b', re.I | re.S)
AGG_RE = re.compile(r'\bselect\s+count\s*\(|\bsum\s*\(', re.I)
FOR_UPDATE_RE = re.compile(r'\bfor\s+update\b', re.I)
WRITE_RE = re.compile(r'\b(insert\s+into|update)\s+(?:public\.)?\w+', re.I)
# `update ... returning ... into` in ONE statement is the atomic shape.
ATOMIC_UPDATE_RE = re.compile(r'\bupdate\b[^;]*?\breturning\b', re.I | re.S)


def strip_sql_comments(src):
    """Remove -- line comments and /* */ blocks WITHOUT touching string bodies.

    Char-by-char rather than a regex, for the reason CLAUDE.md already records:
    the regex version of exactly this shipped a literal backspace on this
    platform, and a string containing a comment marker breaks it silently. Here
    it matters concretely -- every one of these files carries long prose blocks
    that name `insert`, `update` and `transaction_isolation`, so a comment-blind
    scan would find the guard in the COMMENT that says the guard is missing.
    """
    out = []
    i, n = 0, len(src)
    in_s = in_d = in_dollar = False
    dollar_tag = ''
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        # ── COMMENTS INSIDE A $$ BODY STILL HAVE TO BE STRIPPED ─────────────
        # The first version of this treated a dollar-quoted body as opaque and
        # copied it verbatim -- which is precisely backwards, because in
        # plpgsql EVERY function comment lives inside $$. Its own fixture
        # caught it: a body whose only mention of the guard was in a `--`
        # comment classified GUARDED. So the closing tag is watched for here
        # and everything else falls through to the normal string and comment
        # handling below.
        if in_dollar and not in_s and not in_d and src.startswith(dollar_tag, i):
            out.append(' ' * len(dollar_tag))
            i += len(dollar_tag)
            in_dollar = False
            continue
        if in_s:
            out.append(c)
            if c == "'":
                if nxt == "'":
                    out.append(nxt)
                    i += 2
                    continue
                in_s = False
            i += 1
            continue
        if in_d:
            out.append(c)
            if c == '"':
                in_d = False
            i += 1
            continue
        if c == '-' and nxt == '-':
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if c == '/' and nxt == '*':
            depth = 1
            out.append('  ')
            i += 2
            while i < n and depth:
                if src.startswith('/*', i):
                    depth += 1
                    out.append('  ')
                    i += 2
                elif src.startswith('*/', i):
                    depth -= 1
                    out.append('  ')
                    i += 2
                else:
                    out.append(' ' if src[i] != '\n' else '\n')
                    i += 1
            continue
        if not in_dollar:
            m = re.match(r'\$(\w*)\$', src[i:])
            if m:
                dollar_tag = m.group(0)
                in_dollar = True
                out.append(dollar_tag)
                i += len(dollar_tag)
                continue
        if c == "'":
            in_s = True
        elif c == '"':
            in_d = True
        out.append(c)
        i += 1
    return ''.join(out)


def split_functions(clean):
    """[(name, body, offset)] for each create-or-replace-function in the text.

    The body runs to the next function definition or end of file. That is
    deliberately generous: a body cut SHORT could miss the very guard or write
    the verdict turns on, and over-reading merges two functions into one --
    which makes a finding LESS likely, not more. Erring toward a missed finding
    over a fabricated one is the right direction for a checker nobody has
    watched yet.
    """
    hits = [(m.group(1), m.start()) for m in FUNC_RE.finditer(clean)]
    out = []
    for idx, (name, start) in enumerate(hits):
        end = hits[idx + 1][1] if idx + 1 < len(hits) else len(clean)
        out.append((name, clean[start:end], start))
    return out


def classify(body):
    """(verdict, why). Verdicts: GUARDED, SAFE_SHAPE, NO_RMW, UNGUARDED."""
    lock = LOCK_RE.search(body)
    if not lock:
        return 'NO_LOCK', 'no advisory lock'
    after = body[lock.end():]
    if GUARD_RE.search(body):
        return 'GUARDED', "checks current_setting('transaction_isolation')"

    # ── THE SAFE SHAPES ARE CLASSIFIED BEFORE "IS THERE A READ AT ALL" ──────
    # ORDER MATTERS AND ITS OWN FIXTURE CAUGHT THIS. `update ... returning ...
    # into` is a read AND a write in one atomic statement and contains no
    # `select`, so asking "are there reads?" first sent the roofing-shaped
    # function to NO_RMW -- a harmless verdict reached by wrong reasoning,
    # which is the kind that stops being harmless the next time the rule moves.
    atomic_rmw = ATOMIC_UPDATE_RE.search(after)
    if FOR_UPDATE_RE.search(after):
        return ('SAFE_SHAPE',
                'the post-lock read is SELECT ... FOR UPDATE, which re-reads '
                'the latest committed row version or raises 40001 -- loud, '
                'not silent')

    reads = list(READ_RE.finditer(after)) + list(AGG_RE.finditer(after))
    if atomic_rmw and not reads:
        return ('SAFE_SHAPE',
                'the read and the write are ONE statement -- UPDATE ... '
                'RETURNING, which raises 40001 against a concurrently-updated '
                'row rather than reading a stale snapshot')
    if not reads:
        return 'NO_RMW', 'takes the lock but reads no state after it'
    writes = list(WRITE_RE.finditer(after))
    if not writes:
        return 'NO_RMW', 'reads after the lock but never writes'

    return ('UNGUARDED',
            'takes an advisory lock, then READS state and WRITES based on it, '
            'with nothing requiring READ COMMITTED')


def superseded(functions_by_file):
    """Files defining a function that ANOTHER file also defines, where this
    copy is unguarded and the other is guarded.

    `create or replace` means re-running the older file silently reverts the
    guard, and nothing about running a migration warns you it is older.
    """
    guarded, out = {}, []
    for path, funcs in functions_by_file.items():
        for name, verdict, _why in funcs:
            if verdict == 'GUARDED':
                guarded.setdefault(name, []).append(path)
    for path, funcs in functions_by_file.items():
        for name, verdict, _why in funcs:
            if verdict in ('UNGUARDED', 'NO_RMW') and name in guarded:
                others = [p for p in guarded[name] if p != path]
                if others:
                    out.append((path, name, others))
    return out


FIXTURES = [
    ('vulnerable', """
create or replace function public.f_bad(p int) returns jsonb language plpgsql as $$
declare v bigint; begin
  perform pg_advisory_xact_lock(hashtext('k'));
  select count(*) into v from public.t where a >= now();
  if v >= p then return '{}'::jsonb; end if;
  insert into public.t default values;
  return '{}'::jsonb;
end; $$;
""", 'UNGUARDED'),
    ('guarded', """
create or replace function public.f_good(p int) returns jsonb language plpgsql as $$
declare v bigint; i text; begin
  i := current_setting('transaction_isolation');
  if i <> 'read committed' then raise exception 'nope'; end if;
  perform pg_advisory_xact_lock(hashtext('k'));
  select count(*) into v from public.t;
  insert into public.t default values;
  return '{}'::jsonb;
end; $$;
""", 'GUARDED'),
    ('for update', """
create or replace function public.f_forupdate() returns void language plpgsql as $$
declare r record; begin
  perform pg_advisory_xact_lock(hashtext('k'));
  select * into r from public.t where id = 1 for update;
  update public.t set n = r.n + 1 where id = 1;
end; $$;
""", 'SAFE_SHAPE'),
    ('atomic update returning', """
create or replace function public.f_atomic() returns integer language plpgsql as $$
declare v integer; begin
  perform pg_advisory_xact_lock(hashtext('k'));
  insert into public.c (k) values ('x') on conflict do nothing;
  update public.c set n = n + 1 where k = 'x' returning n - 1 into v;
  return v;
end; $$;
""", 'SAFE_SHAPE'),
    ('lock but no read', """
create or replace function public.f_norm() returns void language plpgsql as $$
begin
  perform pg_advisory_xact_lock(hashtext('k'));
  insert into public.t default values;
end; $$;
""", 'NO_RMW'),
    # THE COMMENT TRAP, and it is the reason the stripper is char-by-char. Every
    # real file here carries prose naming the guard; a comment-blind scan reads
    # this as GUARDED and reports the platform clean.
    ('guard named only in a comment', """
create or replace function public.f_comment(p int) returns jsonb language plpgsql as $$
declare v bigint; begin
  -- this relies on current_setting('transaction_isolation') being read committed
  perform pg_advisory_xact_lock(hashtext('k'));
  select count(*) into v from public.t;
  insert into public.t default values;
  return '{}'::jsonb;
end; $$;
""", 'UNGUARDED'),
]


def self_check(verbose=True):
    bad = []
    for label, src, want in FIXTURES:
        clean = strip_sql_comments(src)
        funcs = split_functions(clean)
        if len(funcs) != 1:
            bad.append((label, 'split into %d functions' % len(funcs), want))
            continue
        got, why = classify(funcs[0][1])
        if verbose:
            print('    %-28s %-11s %s' % (label, got, 'ok' if got == want else 'EXPECTED ' + want))
        if got != want:
            bad.append((label, got, want))
    return bad


def scan():
    by_file, unreadable = {}, []
    if not os.path.isdir(SQL_DIR):
        return None, None, ['sql/ does not exist at ' + SQL_DIR]
    for fn in sorted(os.listdir(SQL_DIR)):
        if not fn.endswith('.sql'):
            continue
        p = os.path.join(SQL_DIR, fn)
        try:
            src = io.open(p, encoding='utf-8', errors='strict').read()
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append('%s: %s' % (fn, exc))
            continue
        clean = strip_sql_comments(src)
        rows = []
        for name, body, _off in split_functions(clean):
            verdict, why = classify(body)
            if verdict != 'NO_LOCK':
                rows.append((name, verdict, why))
        if rows:
            by_file['sql/' + fn] = rows
    return by_file, superseded(by_file), unreadable


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-check', action='store_true')
    args = ap.parse_args(argv)

    # THE FIXTURES RUN FIRST, EVERY RUN, NOT ONLY UNDER --self-check. A checker
    # that has silently stopped classifying must not then report the repository
    # clean -- that is the exact "reports a pass it never performed" shape
    # CLAUDE.md names, and a blind lock is cheap enough to pay for on every run.
    bad = self_check(verbose=args.self_check)
    if args.self_check:
        print('\n%d fixture(s) misclassified' % len(bad))
        return EXIT_CLEAN if not bad else EXIT_FINDING
    if bad:
        print('COULD NOT RUN -- the blind lock failed, so nothing was scanned:')
        for label, got, want in bad:
            print('  fixture %r classified %s, expected %s' % (label, got, want))
        return EXIT_COULD_NOT_RUN

    by_file, sup, unreadable = scan()
    if by_file is None:
        print('COULD NOT RUN: ' + '; '.join(unreadable))
        return EXIT_COULD_NOT_RUN

    findings = [(f, n, w) for f, rows in by_file.items()
                for n, v, w in rows if v == 'UNGUARDED']
    counts = {}
    for rows in by_file.values():
        for _n, v, _w in rows:
            counts[v] = counts.get(v, 0) + 1

    if args.json:
        print(json.dumps({'by_file': by_file, 'superseded': sup,
                          'unreadable': unreadable, 'counts': counts}, indent=1))
        return EXIT_FINDING if (findings or sup) else (
            EXIT_COULD_NOT_RUN if unreadable else EXIT_CLEAN)

    print('advisory-lock isolation: %d function(s) take an advisory lock'
          % sum(len(r) for r in by_file.values()))
    for v in ('UNGUARDED', 'GUARDED', 'SAFE_SHAPE', 'NO_RMW'):
        if v in counts:
            print('    %-11s %d' % (v, counts[v]))
    print('')
    for f, rows in sorted(by_file.items()):
        for name, verdict, why in rows:
            mark = '  ! ' if verdict == 'UNGUARDED' else '    '
            print('%s%-11s %s  %s' % (mark, verdict, f, name))
            if verdict in ('UNGUARDED', 'SAFE_SHAPE'):
                print('                  %s' % why)
    if sup:
        print('')
        print('SUPERSEDED DEFINITIONS -- `create or replace` means re-running')
        print('the older file silently REVERTS the guard, and nothing about')
        print('running a migration tells you it is older:')
        for path, name, others in sup:
            print('  ! %s defines %s unguarded; guarded in %s'
                  % (path, name, ', '.join(others)))
    if unreadable:
        print('')
        print('COULD NOT READ (%d) -- not counted clean:' % len(unreadable))
        for u in unreadable:
            print('  - %s' % u)
    print('')
    print('THE REPOSITORY IS NOT THE DATABASE. A guard in a file does nothing')
    print('until that migration is re-run; this cannot see the deployed')
    print('function and does not claim to.')
    if findings or sup:
        return EXIT_FINDING
    return EXIT_COULD_NOT_RUN if unreadable else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
