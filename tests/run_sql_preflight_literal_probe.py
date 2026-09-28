#!/usr/bin/env python3
"""tests/run_sql_preflight_literal_probe.py -- tools/sairn_sql_preflight.py must
not read a table name out of a string literal or a comment.

Run:  python tests/run_sql_preflight_literal_probe.py

── THE DEFECT THIS WAS WRITTEN FOR, AND IT IS NOT "MY PROSE WAS ODD" ──────
strip_noise() removed comments and literals in SEPARATE PASSES, in this order:

    /* */   then   --   then   $$...$$   then   '...'

So a `--` INSIDE A STRING LITERAL was treated as a line comment and blanked to
end of line -- taking the string's CLOSING QUOTE with it. From that point the
literal matcher is desynchronised for the rest of the file: what follows a real
literal is parsed as code, and an ordinary English word inside it is read as a
table name.

Measured on the real file that triggered it:

    comment on column public.alf_incidents.recorded_by is
      'Employee id of the filer, ... '
      '(2026-09-27) -- NOT that the filer is unknown ... '
      'from the reported_by key inside the data blob: ...';

    references(strip_noise(sql)) -> {'alf_incidents', 'the'}

and the gate blocked a push with `MISSING_TABLE the` -- a table that exists only
inside an English sentence. THE GATE WAS RIGHT TO BLOCK ON WHAT IT SAW; what it
saw was wrong.

── WHY THIS MATTERS MORE THAN A FALSE POSITIVE ───────────────────────────
A false positive is the SAFE direction and it is not the whole risk. The same
desynchronisation runs the other way: text after an unterminated literal is
parsed as code, so real SQL can land INSIDE what the scanner believes is a
string and be skipped entirely. Section 3 drives that direction, because a gate
whose whole argument is "a wrong column in a WHERE matches nothing and reports
success" cannot afford to silently skip a WHERE.

── CROSS-DOMAIN DISCIPLINE 1 ──────────────────────────────────────────────
Fixtures are synthetic and their right answers are known before the fix. Every
arm that asserts something is NOT found has a partner asserting the real SQL
beside it IS still found -- otherwise a strip_noise() that blanked the entire
file would pass every negative arm.
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import sairn_sql_preflight as P  # noqa: E402

FAILURES = []
N = [0]


def expect(name, got, want):
    N[0] += 1
    if got != want:
        FAILURES.append('%s\n     wanted %r\n     got    %r' % (name, want, got))
        print('  FAIL %s' % name)
    else:
        print('  ok   %s' % name)


def tables(sql):
    """The table names the checker would go on to verify."""
    refs = P.references(P.strip_noise(sql))
    return set(refs[0]) if isinstance(refs, tuple) else set(refs)


def section(t):
    print('')
    print(t)


# ── 1. THE EXACT SHAPE THAT BLOCKED THE PUSH ──────────────────────────────

COMMENT_ON = """alter table public.alf_incidents
  add column if not exists recorded_by text;

comment on column public.alf_incidents.recorded_by is
  'Employee id of the filer, taken from the verified session at write time and '
  'never from the request payload. NULL means the row predates this column '
  '(2026-09-27) -- NOT that the filer is unknown for a new row. Do not backfill '
  'from the reported_by key inside the data blob: it is caller-supplied.';
"""


def one():
    section('1. `comment on column <t>.<c> is \'a\' \'b\';` -- the real case')
    got = tables(COMMENT_ON)
    expect('no English word is read as a table', 'the' in got, False)
    expect('and the REAL table is still found, so the arm above is not passing '
           'because everything was blanked', 'alf_incidents' in got, True)


# ── 2. EVERY WAY A LITERAL CAN LOOK LIKE CODE ─────────────────────────────

CASES = [
    ('a `--` inside a literal does not open a comment',
     "insert into public.alf_incidents (data) values ('a -- b');",
     'alf_incidents', ['a', 'b']),
    ('a `/*` inside a literal does not open a block comment',
     "insert into public.alf_incidents (data) values ('x /* y');",
     'alf_incidents', ['x', 'y']),
    ('a quote inside a COMMENT does not open a literal',
     "-- the schema's own comment\nselect * from public.alf_incidents;",
     'alf_incidents', ['own', 'comment', 'schema']),
    ('SQL text inside a literal is not parsed as SQL',
     "insert into public.alf_incidents (data)\n"
     "  values ('update customers set x = 1 from orders');",
     'alf_incidents', ['customers', 'orders']),
    ('a doubled quote escape keeps the literal open',
     "insert into public.alf_incidents (data) values ('it''s from nowhere');",
     'alf_incidents', ['nowhere']),
    ('a dollar-quoted body is not parsed',
     "create function f() returns void as $$\n"
     "  select * from secret_table;\n$$ language sql;\n"
     "select * from public.alf_incidents;",
     'alf_incidents', ['secret_table']),
    # `comment on ...` is NOT a data reference and references() extracts nothing
    # from it -- DRIVEN, not assumed: references(strip_noise("comment on table
    # public.alf_incidents is 1;")) is the empty set. So this fixture pairs the
    # concatenated literal with a real ALTER; otherwise the must-find arm would
    # be asserting something the tool never claimed to do, and would have read
    # as a defect in the fix.
    ('a literal spanning several concatenated parts stays closed',
     "alter table public.alf_incidents add column x text;\n"
     "comment on table public.alf_incidents is\n"
     "  'one -- two '\n  'three from four '\n  'five';",
     'alf_incidents', ['two', 'three', 'four', 'five']),
]


def two():
    section('2. literals and comments that look like code')
    for name, sql, must_find, must_not in CASES:
        got = tables(sql)
        leaked = sorted([w for w in must_not if w in got])
        expect(name, leaked, [])
        expect('  ... and ' + must_find + ' is still found', must_find in got, True)


# ── 3. THE UNSAFE DIRECTION -- REAL SQL MUST NOT BE SWALLOWED ────────────
# A false positive is survivable. Desynchronisation runs BOTH ways, and the
# other way is a WHERE clause the gate never sees -- which is the exact failure
# this gate exists to prevent.

SWALLOWED = (
    "comment on column public.alf_incidents.recorded_by is\n"
    "  'a -- b';\n"
    "update public.alf_billing set amount = 0 where invoice_id = 'x';\n"
)


def three():
    section('3. THE UNSAFE DIRECTION -- SQL after a tricky literal is still read')
    got = tables(SWALLOWED)
    expect('the UPDATE after the literal is NOT swallowed', 'alf_billing' in got, True)
    # NOT asserted here: `comment on column` is not a data reference and
    # references() correctly extracts nothing from it. Driven rather than
    # assumed -- see the fixture note in section 2. The arm that matters is the
    # UPDATE above, which the old code lost entirely.
    expect('and no prose word leaked', 'the' in got or 'b' in got, False)


# ── 4. THE CONTROL: strip_noise MUST NOT JUST BLANK EVERYTHING ───────────

def four():
    section('4. THE CONTROL -- a blanket blanker would pass every arm above')
    cleaned = P.strip_noise(
        "select * from public.alf_incidents where id = 'abc';")
    expect('real SQL survives stripping', 'alf_incidents' in cleaned, True)
    expect('the literal does NOT survive', 'abc' in cleaned, False)
    expect('offsets are preserved (same length in, same length out)',
           len(cleaned), len("select * from public.alf_incidents where id = 'abc';"))


def main():
    print('SQL PREFLIGHT LITERAL PROBE -- a table name must never come from prose')
    one()
    two()
    three()
    four()
    print('')
    if FAILURES:
        print('%d of %d FAILED:' % (len(FAILURES), N[0]))
        for f in FAILURES:
            print('  - %s' % f)
        return 1
    print('%d/%d passed.' % (N[0], N[0]))
    print('')
    print('WHAT THIS DOES NOT PROVE: that the gate\'s SCHEMA comparison is right.')
    print('It proves only that what the gate believes is SQL is SQL. Whether a')
    print('real column exists is a different question and has its own arms.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
