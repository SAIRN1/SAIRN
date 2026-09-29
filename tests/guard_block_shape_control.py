"""tests/guard_block_shape_control.py -- attacks tools/employee_auth_guard_check.py.

Run:  python tests/guard_block_shape_control.py

── WHAT CHANGED, AND WHY IT NEEDED A CONTROL ─────────────────────────────
`guarded` used to be `MARKER in src` -- the sentence "ZERO active provisioners"
anywhere in the file. That failed in BOTH directions on 2026-09-29:

  * a correct guard whose message WRAPPED between "active" and "provisioners"
    was invisible, and the tool refused a file that carried a real guard;
  * a file carrying that sentence in a COMMENT and no `do $$` block at all
    would have passed, and nothing would have said so.

Three structural conditions replace it: the marker must be in CODE, inside a
real `do $$ ... $$;` block, and that block must sit in the SAME transaction as
the write. Each of the three has a fixture below that must FAIL, because a rule
with no failing fixture is a rule nobody has tested.

── AND THE ARM THAT KEEPS IT USABLE ──────────────────────────────────────
A correct file must still PASS. A detector that refuses everything is not
stricter, it is broken, and it is the shape that gets a gate switched off.
"""
CONTROLS_FOR = ['employee_auth_guard_check.py']

import importlib.util
import io
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'employee_auth_guard_check.py')
EXIT_COULD_NOT_RUN = 2

FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


if not os.path.isfile(TOOL):
    sys.stderr.write('COULD NOT RUN: tools/employee_auth_guard_check.py is not '
                     'on disk. This control tested nothing, which is a third '
                     'state and not a pass.\n')
    sys.exit(EXIT_COULD_NOT_RUN)

spec = importlib.util.spec_from_file_location('eagc', TOOL)
eagc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eagc)

NL = chr(10)
MARK = 'ZERO active provisioners'
WRITE = ("insert into public.zz_employee_auth (license_hash, employee_id)" + NL
         + "values ('abc', 'zz');")
GUARD = (NL.join([
    'do $$',
    'declare rows int; prov int;',
    'begin',
    "  select count(*) into rows from public.zz_employee_auth;",
    "  select count(*) into prov from public.zz_employee_auth where active;",
    '  if rows > 0 and prov = 0 then',
    "    raise exception 'ABORTED: would leave % rows and " + MARK + ".', rows;",
    '  end if;',
    'end $$;']))


def verdict(sql_text):
    """classify() on a throwaway file. Returns the dict, or None."""
    fd, path = tempfile.mkstemp(suffix='.sql', prefix='zz_guard_', dir=REPO)
    os.close(fd)
    try:
        io.open(path, 'w', encoding='utf-8', newline='').write(sql_text)
        return eagc.classify(path)
    finally:
        os.remove(path)


print('CONTROL PAIR -- tools/employee_auth_guard_check.py' + NL)

print('THE ARM THAT KEEPS IT USABLE: a correct file still passes')
good = NL.join(['begin;', WRITE, GUARD, 'commit;'])
c = verdict(good)
ok('a real guard, inside a do-block, inside the transaction -> GUARDED',
   c and c['guarded'] is True, c)
ok('...and it is recognised as a writer at all', c is not None)

print(NL + 'KNOWN-BAD (a): the sentence in a COMMENT only, no do-block')
bad_a = NL.join(['begin;',
                 '-- This file is safe because it would never leave ' + MARK + '.',
                 WRITE, 'commit;'])
c = verdict(bad_a)
ok('a prose-only marker is NOT a guard', c and c['guarded'] is False, c)
ok('...and the tool SAYS the marker was prose', c and c['marker_in_prose_only'] is True,
   'nothing distinguishes "no guard at all" from "a guard written as a sentence", '
   'and only the second needs somebody told they were nearly right: %r' % (c,))

print(NL + 'KNOWN-BAD (b): a real guard OUTSIDE the transaction')
bad_b = NL.join(['begin;', WRITE, 'commit;', GUARD])
c = verdict(bad_b)
ok('a guard after commit; is NOT a guard', c and c['guarded'] is False,
   'a guard that runs after the write is durable reports a problem it has '
   'already allowed: %r' % (c,))

print(NL + 'KNOWN-BAD (c): the message WRAPPED mid-phrase')
wrapped = GUARD.replace(MARK, 'ZERO active' + NL + "       provisioners")
bad_c = NL.join(['begin;', WRITE, wrapped, 'commit;'])
c = verdict(bad_c)
ok('a wrapped message is NOT recognised -- the limit, stated not hidden',
   c and c['guarded'] is False,
   'this is the SAME direction the old rule failed in, and it is left in place '
   'deliberately: matching across a line break would re-admit the prose match '
   'this change closed. The fix is to write the phrase on one line, and the '
   'refusal text says so: %r' % (c,))

print(NL + 'AND THE STRIPPER: a -- inside a STRING is not a comment')
tricky = NL.join(['begin;', WRITE,
                  "-- the next line is a literal, not a comment:",
                  "select 'a -- b' as note;", GUARD, 'commit;'])
c = verdict(tricky)
ok('a string containing -- does not blank the rest of the file',
   c and c['guarded'] is True,
   'the comment stripper swallowed the guard after a literal containing --, '
   'which is the sql_preflight defect reproduced here: %r' % (c,))

print(NL + 'NO WRITE AT ALL -> not a writer, not a verdict')
ok('a file with no employee_auth write is None, never "guarded"',
   verdict('select 1;') is None)

print(NL + '%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
