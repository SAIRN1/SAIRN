"""The control on tools/sql_column_exists_check.py: it must catch the
2026-09-29 statement, and it must not fire on correct SQL.

    python tests/run_sql_column_exists_probe.py

── WHAT IT IS A CONTROL FOR ────────────────────────────────────────────────
A residue-removal block reached origin/main naming `entry_id` on `mech_checks`
and `mech_takeoffs`. Those tables use `check_id` and `takeoff_id`. Every statement
in that block would error 42703 undefined_column -- including the CONFIRM step,
so it could not even print the 0 it was meant to prove.

── THE TWO DIRECTIONS, AND THE SECOND IS THE ONE THAT DECIDES USABILITY ────
Catching the bad column is necessary. A check that also fires on correct SQL is a
check that gets switched off, and this one's FIRST REAL RUN reported five findings
and all five were false: migrations that ADD a column with `alter table` and then
query it, while the parser read only `create table`. So the false-positive arms
below are not decoration -- they are the arms that decide whether this can be a
gate at all.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

TOOL = os.path.join(REPO, 'tools', 'sql_column_exists_check.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: %s is missing. Nothing below was checked, and that is '
          'not a pass.' % TOOL)
    sys.exit(EXIT_COULD_NOT_RUN)

import sql_column_exists_check as C                              # noqa: E402

passed = failed = 0


def ck(name, cond, detail=''):
    global passed, failed
    print(('  ok   ' if cond else '  FAIL ') + name)
    if cond:
        passed += 1
    else:
        failed += 1
        if detail:
            print('         ' + str(detail).replace('\n', '\n         ')[:500])


print('tools/sql_column_exists_check.py -- catches the wrong column, and does '
      'not fire on right SQL\n')

DCL = {'mech_checks': {'id', 'license_hash', 'app_id', 'check_id', 'data',
                       'created_at', 'updated_at'}}
DEP = dict(DCL)

# ── 1. THE STATEMENT THAT SHIPPED ───────────────────────────────────────────
BAD = ("delete from public.mech_checks\n"
       " where license_hash = encode(digest('MECH-PINNACLE-2026','sha256'),'hex')\n"
       "   and entry_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP';")
f, d, s = C.scan_text(BAD, DCL, DEP)
ck('1. THE 2026-09-29 STATEMENT: entry_id on mech_checks is REPORTED',
   len(f) == 1 and f[0]['column'] == 'entry_id' and f[0]['table'] == 'mech_checks',
   f)
ck('1b. ...and license_hash in the SAME statement is NOT reported, so the arm '
   'above is finding the wrong column and not flagging the statement wholesale',
   not [x for x in f if x['column'] == 'license_hash'], f)

GOOD = BAD.replace('entry_id', 'check_id')
f, d, s = C.scan_text(GOOD, DCL, DEP)
ck('1c. CONTROL: the CORRECTED statement is clean', not f, f)

# ── 2. THE FALSE POSITIVES THAT WOULD GET IT SWITCHED OFF ───────────────────
ck('2. a function call in the value position is not read as a column',
   not C.scan_text(
       "select * from public.mech_checks where license_hash = "
       "encode(digest('K','sha256'),'hex');", DCL, DEP)[0])

f, d, s = C.scan_text(
    "select 1 from public.mech_checks c join public.mech_docs m on true "
    "where m.no_such_col = 'x';", DCL, DEP)
ck('2b. a JOIN is SKIPPED AND COUNTED, never attributed to one side',
   not f and len(s) == 1, (f, s))

f, d, s = C.scan_text("delete from public.tbl_nobody_declares where q = 'x';",
                      DCL, DEP)
ck('2c. an unknown TABLE is skipped and counted, not reported as a bad column',
   not f and len(s) == 1, (f, s))

ck('2d. a GRANT is not read as a query -- the `on` and the `from service_role` '
   'used to be parsed as table names and inflated the blind count by 591',
   not C.scan_text(
       'grant select, insert on public.mech_checks to service_role;\n'
       'revoke all on public.mech_checks from service_role;', DCL, DEP)[0]
   and not C.scan_text(
       'grant select on public.mech_checks to service_role;', DCL, DEP)[2])

# THE FALSE POSITIVE THE FIRST REAL RUN ACTUALLY PRODUCED, five times over.
MIGRATION = ("alter table public.mech_checks add column if not exists "
             "idempotency_key text;\n"
             "select count(*) from public.mech_checks where idempotency_key is null;")
decl_from_alter = {'mech_checks': set(DCL['mech_checks'])}
f, d, s = C.scan_text(
    MIGRATION,
    {'mech_checks': DCL['mech_checks'] | {'idempotency_key'}},
    DEP)
ck('2e. THE FIRST RUN\'S OWN FALSE POSITIVE: a migration that ADDS a column and '
   'then filters on it is not a finding once `alter table add column` is parsed',
   not f, f)

# ── 3. THE THIRD ANSWER: DECLARED AND DEPLOYED DISAGREE ─────────────────────
f, d, s = C.scan_text(GOOD, DCL, {'mech_checks': {'id', 'license_hash', 'data'}})
ck('3. a column DECLARED and not DEPLOYED is a DISAGREEMENT, not a finding and '
   'not clean -- that is the case a migration nobody ran lands in',
   not f and len(d) == 1 and d[0]['declared'] and not d[0]['deployed'], (f, d))

# ── 4. THE PARSERS ACTUALLY READ THE REPO ───────────────────────────────────
dcl = C.declared_columns()
ck('4. the declared parser finds mech_checks.check_id in sql/, so arm 1 is '
   'comparing against a real schema and not an empty dict',
   'mech_checks' in dcl and 'check_id' in dcl['mech_checks'], sorted(dcl)[:5])
ck('4b. ...and entry_id is NOT among mech_checks columns, which is the fact the '
   'whole check turns on',
   'entry_id' not in dcl.get('mech_checks', set()),
   sorted(dcl.get('mech_checks', [])))
dep = C.deployed_columns()
ck('4c. the deployed snapshot parses and carries mech_checks',
   dep is not None and 'mech_checks' in dep and 'check_id' in dep['mech_checks'],
   'snapshot unreadable' if dep is None else sorted(dep.get('mech_checks', [])))

# ── 5. THE TOOL RUNS, SELF-TESTS, AND PRINTS ITS OWN BLIND COUNT ────────────
p = subprocess.run([sys.executable, TOOL, '--selftest'], cwd=REPO,
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
ck('5. --selftest exits 0 (exit %d)' % p.returncode, p.returncode == EXIT_CLEAN,
   (p.stdout or '') + (p.stderr or ''))

p = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
out = (p.stdout or '') + (p.stderr or '')
ck('5b. the real run PRINTS a counted blind-spot line, so a clean verdict cannot '
   'be read as a clean verdict over everything',
   'BLIND TO THIS CHECK:' in out and 'statement(s) were NOT validated' in out,
   out[-400:])
ck('5c. ...and it names the nullability gap, because a column that EXISTS is not '
   'a column that is NOT NULL and this check cannot tell',
   'c.is_nullable' in out, out[-400:])
ck('5d. the real run reports ZERO bad-column findings on this repo, so arm 1 is '
   'a control and not the tool\'s ordinary state',
   'FILTERS ON A COLUMN NEITHER SOURCE HAS : 0' in out,
   [l for l in out.split('\n') if 'FILTERS ON A COLUMN' in l])

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
