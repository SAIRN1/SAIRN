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

# tools/ on the path EXPLICITLY, because this file now imports checker_kit and a
# copy of it executed from anywhere else -- which is exactly what this file's own
# teeth section does -- would otherwise die on the import rather than run and be
# judged. A control that cannot start looks identical to one that found nothing.
if os.path.join(REPO, 'tools') not in sys.path:
    sys.path.insert(0, os.path.join(REPO, 'tools'))

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
    """Blank comments, preserving offsets. DELEGATES TO tools/checker_kit.py.

    ── THIS WAS SEVENTY LINES OF HAND-ROLLED CHAR-BY-CHAR PARSING, AND ITEM 28
    ── IS THE REASON IT IS NOT ANY MORE.
    Item 28 folded the structural skeleton every checker re-derives -- the
    exit-code contract, the control pair, and COMMENT-STRIPPED PARSING -- into
    tools/checker_kit.py, precisely so the next checker would not write its own
    copy. This file wrote its own copy anyway, on 2026-09-15, hours after using
    the kit would have been a one-line import.

    AND THE KIT WAS ALREADY RIGHT ABOUT THE BUG THE COPY SHIPPED WITH. The
    hand-rolled version treated a dollar-quoted `$$` body as OPAQUE -- exactly
    backwards, since in plpgsql every function comment lives inside `$$` -- so a
    body mentioning the isolation guard only in a `--` comment classified
    GUARDED. Its own fixture caught that before it ran on sql/. Verified
    2026-09-15: `checker_kit.strip_comments(src, sql=True)` strips a comment
    inside a `$$` body, preserves the code around it, and preserves offsets.

    The wrapper is kept rather than inlining the call at both sites so this
    file's probe keeps naming the behaviour it tests -- and so the delegation is
    the thing under test rather than an implementation detail nobody drives.
    """
    from checker_kit import strip_comments
    return strip_comments(src, sql=True)


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


DROP_RE = re.compile(
    r'drop\s+function\s+(?:if\s+exists\s+)?(?:public\.)?(\w+)\s*\(([^)]*)\)', re.I)


def arity(arglist):
    """Count top-level commas + 1. Good enough for these signatures, and a
    miscount errs toward NOT matching, which drops a finding rather than
    inventing one."""
    depth, n = 0, 1
    if not arglist.strip():
        return 0
    for ch in arglist:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        elif ch == ',' and depth == 0:
            n += 1
    return n


def superseded(defs_by_file, drops_by_file):
    """A file that DEFINES a function signature another migration explicitly
    DROPPED. Re-running it restores exactly what that migration removed.

    ── THE FIRST VERSION OF THIS HAD THE WRONG PREDICATE, AND MISSED THE WORSE
    ── OF THE TWO REAL INSTANCES.
    It looked for "an UNGUARDED copy where another file has a GUARDED one",
    which finds a reverted guard and nothing else. The sharper hazard has
    nothing to do with the guard: sql/sairn_ai_rate_limit_consume_fn.sql
    defines a 3-argument sairn_ai_rate_limit_consume and IS guarded, and
    sql/sairn_ai_tenant_subbudget_2026-09-15.sql explicitly DROPS that exact
    signature before creating a 6-argument form with defaults on the last
    three. Re-running the guarded older file therefore puts BOTH forms in the
    catalogue, a 3-argument call matches both, and Postgres refuses the whole
    call with "function is not unique" -- a hard outage on every AI call on the
    platform, which is precisely the state the tenant work's own comment says
    it avoided by dropping rather than overloading.

    So the rule is DROP-based, not guard-based: whoever wrote a `drop function`
    stated that this signature must not exist, and any file still creating it
    is a landmine whether or not it is guarded.
    """
    dropped = {}
    for path, drops in drops_by_file.items():
        for name, n in drops:
            dropped.setdefault((name, n), []).append(path)
    out = []
    for path, defs in defs_by_file.items():
        for name, n, _verdict in defs:
            key = (name, n)
            if key in dropped:
                others = [p for p in dropped[key] if p != path]
                if others:
                    out.append((path, '%s/%d args' % (name, n), others))
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
    defs_by_file, drops_by_file = {}, {}
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
        rows, defs = [], []
        for name, body, _off in split_functions(clean):
            verdict, why = classify(body)
            # EVERY definition is recorded for the drop cross-reference, not
            # just the ones taking a lock: the "function is not unique" hazard
            # has nothing to do with locking.
            m = re.match(r'[^(]*\(([^)]*)\)', body[body.index('(') :] if '(' in body else '')
            arglist = m.group(1) if m else ''
            defs.append((name, arity(arglist), verdict))
            if verdict != 'NO_LOCK':
                rows.append((name, verdict, why))
        drops = [(m.group(1), arity(m.group(2))) for m in DROP_RE.finditer(clean)]
        if drops:
            drops_by_file['sql/' + fn] = drops
        if defs:
            defs_by_file['sql/' + fn] = defs
        if rows:
            by_file['sql/' + fn] = rows
    return by_file, superseded(defs_by_file, drops_by_file), unreadable


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
        print('SUPERSEDED DEFINITIONS -- a file still CREATES a signature that')
        print('another migration explicitly DROPPED. THIS IS NOT ABOUT THE')
        print('GUARD: the dropped form may be perfectly guarded, and the hazard')
        print('is that re-creating it beside a DEFAULTED overload makes a call')
        print('match BOTH, so Postgres refuses it entirely -- "function is not')
        print('unique", a hard outage rather than a degradation. Nothing about')
        print('running a migration tells you it is the older one:')
        for path, name, others in sup:
            print('  ! %s still creates %s, which was DROPPED by %s'
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
