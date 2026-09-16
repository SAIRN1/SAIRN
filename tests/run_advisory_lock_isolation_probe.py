CONTROLS_FOR = ['tools/advisory_lock_isolation_check.py']
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

# ── A LIMITATION OF THE SHARED KIT, RECORDED RATHER THAN HIDDEN ────────────
# The stripper now delegates to checker_kit.strip_comments(sql=True), which
# delegates in turn to comment_quote_check -- the canonical implementation this
# platform says not to fork. It does NOT nest block comments, and Postgres does:
# `/* a /* b */ HIDDEN */` leaves `HIDDEN */` live.
#
# THAT IS REACHABLE, NOT THEORETICAL. Measured 2026-09-15: 13 sql/ files use
# block comments and TWO of them nest -- full_crud_truncate_sweep_2026-08-24.sql
# nests SIX deep. It is not reachable for THIS checker, because neither file
# defines an advisory-lock function, and that is asserted below rather than
# assumed. The bug is reported as a finding against the canonical stripper and
# deliberately NOT fixed here: it is a shared module several checkers depend on,
# and folding that repair into this work would be the orthogonal change.
nested = C.strip_sql_comments('select 1; /* a /* b */ HIDDEN */ select 2;')
ok('KNOWN LIMITATION: nested /* /* */ */ blocks are NOT handled by the shared '
   'stripper, and this arm records it rather than hiding it',
   'HIDDEN' in nested,
   'if this went red the canonical stripper gained nesting -- delete this arm '
   'and restore the positive one')
_nest_files = []
for _fn in sorted(os.listdir(os.path.join(REPO, 'sql'))):
    if not _fn.endswith('.sql'):
        continue
    _src = io.open(os.path.join(REPO, 'sql', _fn), encoding='utf-8',
                   errors='replace').read()
    _d = _max = _i = 0
    while _i < len(_src) - 1:
        if _src[_i:_i + 2] == '/*':
            _d += 1
            _max = max(_max, _d)
            _i += 2
            continue
        if _src[_i:_i + 2] == '*/':
            _d = max(0, _d - 1)
            _i += 2
            continue
        _i += 1
    if _max > 1:
        _nest_files.append(_fn)
_scanned, _sup0, _unread0 = C.scan()
ok('...and NO file carrying a nested block comment defines an advisory-lock '
   'function, so the limitation cannot reach THIS checker',
   _nest_files and not any('sql/' + _f in (_scanned or {}) for _f in _nest_files),
   (_nest_files, sorted(_scanned or {})))


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

# ── THE SUPERSEDED CLASS IS DROP-BASED, NOT GUARD-BASED ───────────────────
# The first version keyed on "an UNGUARDED copy where another file has a
# GUARDED one" and WALKED STRAIGHT PAST THE WORSE OF THE TWO REAL INSTANCES.
# sql/sairn_ai_rate_limit_consume_fn.sql defines a 3-argument
# sairn_ai_rate_limit_consume and IS guarded; the tenant migration explicitly
# DROPS that signature before creating a 6-argument form with defaults on the
# last three. Re-running the guarded older file puts both in the catalogue, a
# 3-arg call matches both, and Postgres refuses it entirely -- "function is not
# unique", a hard outage on every AI call, which is precisely what the tenant
# work's own comment says dropping rather than overloading avoided.
ok('the DROPPED-signature landmine is reported',
   any('sairn_ai_rate_limit_consume_fn' in p for p, _n, _o in (sup or [])), sup)
ok('...and it is reported for the ARITY that was dropped, not just the name',
   any('/3 args' in n for _p, n, _o in (sup or [])), sup)
ok('...naming the migration that dropped it, so the reader knows which is newer',
   any(any('tenant_subbudget' in o for o in others) for _p, _n, others in (sup or [])),
   sup)
# The columns file was the FIRST instance and its definition was removed
# outright on 2026-09-15. If it comes back, that is a regression.
ok('sairn_ai_usage_columns no longer defines the function at all',
   not any('sairn_ai_usage_columns' in p for p, _n, _o in (sup or [])), sup)


# ══ D. TEETH -- the blind lock must actually stop a broken checker ═════════
print('\nD. teeth -- a broken classifier must NOT report the repo clean')
src = io.open(SUBJECT, encoding='utf-8').read()
ANCHOR = "    return ('UNGUARDED',"
ok('the teeth anchor is present in the subject', src.count(ANCHOR) == 1,
   'anchor stale or ambiguous -- section D tests NOTHING')
broken = src.replace(ANCHOR, "    return ('GUARDED',")
ok('the neutering changed the source', broken != src)

TMP = tempfile.mkdtemp(prefix='ali_')
# THE COPY NEEDS THE REAL tools/ ON ITS PATH, and finding that out was worth the
# arm. Since the subject started importing checker_kit (item 28's shared kit),
# a copy executed from a temp directory derives its own REPO from __file__ and
# cannot resolve the import -- so it died on ImportError and exited 1. The teeth
# arms below then failed while reporting nothing about the classifier, which is
# the shape where a control looks broken and is actually untested. PYTHONPATH is
# set explicitly rather than the arms being relaxed to accept exit 1.
TEETH_ENV = dict(os.environ, PYTHONPATH=os.path.join(REPO, 'tools'))
try:
    bp = os.path.join(TMP, 'broken_check.py')
    io.open(bp, 'w', encoding='utf-8').write(broken)
    r = subprocess.run([sys.executable, bp], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=REPO, env=TEETH_ENV)
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
                        encoding='utf-8', errors='replace', cwd=REPO, env=TEETH_ENV)
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
