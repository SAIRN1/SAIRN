#!/usr/bin/env python
"""tests/run_advisory_lock_isolation_probe.py -- controls for
tools/advisory_lock_isolation_check.py.

THE DEFECT UNDER TEST IS INVISIBLE IN THE CODE THAT CONTAINS IT. A function that
takes an advisory lock, reads, decides and writes is CORRECT under READ
COMMITTED and silently wrong under REPEATABLE READ -- so the thing being
detected is a dependency on a setting that lives in another file. A checker for
that has one way to fail badly: report the platform clean because it stopped
classifying.

SO THE FIXTURES ARE THE SUBJECT'S OWN BLIND LOCK AND THEY RUN ON EVERY REAL RUN,
not only under --self-check. This file proves that lock actually fails when the
classifier is wrong, and proves each verdict separately -- a classifier that
returned one constant would satisfy a one-sided test.

TWO OF THE SIX FIXTURES EXIST BECAUSE THEY CAUGHT REAL BUGS IN THE FIRST DRAFT,
before it ever ran against sql/:
  * the comment trap -- the stripper treated a $$ body as opaque, which is
    exactly backwards, because in plpgsql every function comment lives inside
    $$. A body whose only mention of the guard was in a `--` comment classified
    GUARDED.
  * atomic update -- `update ... returning ... into` is a read and a write in
    one statement and contains no `select`, so asking "are there reads?" first
    sent it to NO_RMW: a harmless verdict reached by wrong reasoning.

Exit 0 all arms passed, 1 otherwise.
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
SUBJECT = os.path.join(REPO, 'tools', 'advisory_lock_isolation_check.py')

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('    ok   %s' % label)
    else:
        FAILS.append(label)
        print('    FAIL %s' % label)
        if detail:
            print('         %s' % str(detail)[:400])


import advisory_lock_isolation_check as C   # noqa: E402


def verdict(sql):
    clean = C.strip_sql_comments(sql)
    funcs = C.split_functions(clean)
    assert len(funcs) == 1, 'fixture defines %d functions' % len(funcs)
    return C.classify(funcs[0][1])


# ══ A. every verdict, proved separately ════════════════════════════════════
print('\nA. the classifier -- each verdict on its own')
for label, src, want in C.FIXTURES:
    got, why = verdict(src)
    ok('%-28s -> %s' % (label, want), got == want, 'got %s (%s)' % (got, why))

ok('the four verdicts are all reachable -- a constant would pass a one-sided test',
   len(set(w for _l, _s, w in C.FIXTURES)) == 4,
   sorted(set(w for _l, _s, w in C.FIXTURES)))


# ══ B. the comment stripper, which is where the first real bug was ═════════
print('\nB. the stripper -- $$ bodies are NOT opaque')
BODY = """create or replace function public.f() returns void language plpgsql as $$
begin
  -- current_setting('transaction_isolation') is mentioned ONLY here
  perform pg_advisory_xact_lock(hashtext('k'));
  select count(*) into v from public.t;
  insert into public.t default values;
end; $$;"""
clean = C.strip_sql_comments(BODY)
ok('a -- comment INSIDE a $$ body is stripped',
   'transaction_isolation' not in clean, clean[:200])
ok('...and the code around it survives',
   'pg_advisory_xact_lock' in clean and 'insert into' in clean, clean[:200])

STR = """create or replace function public.g() returns text language plpgsql as $$
begin
  return 'a -- not a comment and current_setting(''transaction_isolation'') either';
end; $$;"""
clean2 = C.strip_sql_comments(STR)
ok('a -- inside a STRING is not treated as a comment',
   'not a comment' in clean2, clean2[:200])

ok('a /* block */ comment is stripped',
   'HIDDEN' not in C.strip_sql_comments('select 1; /* HIDDEN */ select 2;'))
ok('nested /* /* */ */ blocks are handled',
   'HIDDEN' not in C.strip_sql_comments('select 1; /* a /* b */ HIDDEN */ select 2;'))


# ══ C. the real repository, and the three fixes are asserted BY NAME ═══════
print('\nC. against the real sql/ tree')
by_file, sup, unreadable = C.scan()
ok('the scan ran', by_file is not None, unreadable)
flat = {(f, n): v for f, rows in (by_file or {}).items() for n, v, _w in rows}
ok('it found the advisory-lock functions at all', len(flat) >= 8, len(flat))
ok('nothing was unreadable -- an unreadable file is not a clean one',
   not unreadable, unreadable)

# The three guards added 2026-09-15. Named individually so removing ONE is a
# red arm rather than a number that still looks about right.
for f, n in (('sql/cl_rate_limit_consume_fn_2026-09-04.sql', 'cl_rate_limit_consume'),
             ('sql/sairnlaw_trusttx_functions.sql', 'law_check_and_insert_disbursement'),
             ('sql/sairnlaw_trusttx_functions.sql', 'law_check_and_void_deposit')):
    ok('%s is GUARDED' % n, flat.get((f, n)) == 'GUARDED', flat.get((f, n)))

# The two safe shapes. If either is ever reported UNGUARDED the checker has
# started over-reporting, which is how a column gets switched off.
ok('sairn_circuit_breaker_step is SAFE_SHAPE, not a finding (FOR UPDATE)',
   flat.get(('sql/sairn_circuit_breaker_schema.sql', 'sairn_circuit_breaker_step')) == 'SAFE_SHAPE',
   flat.get(('sql/sairn_circuit_breaker_schema.sql', 'sairn_circuit_breaker_step')))
ok('rf_allocate_invoice_number is SAFE_SHAPE, not a finding (UPDATE RETURNING)',
   flat.get(('sql/sairnroofing_billing_schema.sql', 'rf_allocate_invoice_number')) == 'SAFE_SHAPE',
   flat.get(('sql/sairnroofing_billing_schema.sql', 'rf_allocate_invoice_number')))

ok('the superseded stale migration is reported',
   any('sairn_ai_usage_columns' in p for p, _n, _o in (sup or [])), sup)


# ══ D. TEETH -- the blind lock must actually stop a broken checker ═════════
print('\nD. teeth -- a broken classifier must NOT report the repo clean')
src = io.open(SUBJECT, encoding='utf-8').read()
ANCHOR = "    return ('UNGUARDED',"
ok('the teeth anchor is present in the subject', src.count(ANCHOR) == 1,
   'anchor stale or ambiguous -- section D tests NOTHING')
broken = src.replace(ANCHOR, "    return ('GUARDED',")
ok('the neutering changed the source', broken != src)

TMP = tempfile.mkdtemp(prefix='ali_')
try:
    bp = os.path.join(TMP, 'broken_check.py')
    io.open(bp, 'w', encoding='utf-8').write(broken)
    r = subprocess.run([sys.executable, bp], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=REPO)
    ok('the broken copy runs at all', r.returncode in (0, 1, 2), r.stderr[-300:])
    # THE POINT: it must not silently report clean. The blind lock catches the
    # misclassification and turns it into COULD NOT RUN.
    ok('TEETH: a classifier that can never say UNGUARDED exits COULD NOT RUN (2), '
       'not CLEAN (0)', r.returncode == 2, 'exit %s\n%s' % (r.returncode, r.stdout[-400:]))
    ok('...and says the blind lock failed, rather than printing a clean sweep',
       'blind lock failed' in r.stdout, r.stdout[:300])

    # And the other direction: an always-UNGUARDED classifier must also be
    # caught, or the lock is only half a lock.
    ANCHOR2 = "        return 'NO_RMW', 'takes the lock but reads no state after it'"
    ok('the second teeth anchor is present', src.count(ANCHOR2) == 1)
    broken2 = src.replace(ANCHOR2,
                          "        return 'UNGUARDED', 'always'")
    ok('the second neutering changed the source', broken2 != src)
    bp2 = os.path.join(TMP, 'broken2.py')
    io.open(bp2, 'w', encoding='utf-8').write(broken2)
    r2 = subprocess.run([sys.executable, bp2], capture_output=True, text=True,
                        encoding='utf-8', errors='replace', cwd=REPO)
    ok('TEETH: an always-UNGUARDED classifier is ALSO caught by the lock',
       r2.returncode == 2, 'exit %s' % r2.returncode)

    # CONTROL: the unmodified subject must still classify cleanly, or the two
    # arms above would pass against a checker that is simply always broken.
    r3 = subprocess.run([sys.executable, SUBJECT, '--self-check'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', cwd=REPO)
    ok('CONTROL: the real subject passes its own blind lock',
       r3.returncode == 0, r3.stdout[-300:])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the scratch directory is gone', not os.path.isdir(TMP))


print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
