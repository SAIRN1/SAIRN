"""Does the irreversible class in tools/tier_a_review_gate.py refuse what it
claims to, stay silent when empty, and FAIL CLOSED on a member it cannot
evaluate?

WHY THIS EXISTS. The name-based half of that gate matches Tier A resource names
on changed lines, which cannot see a change to the machinery every resource
depends on. Measured, not argued: `dadfedf4` -- "all 48 role membership sets get
a null prototype", a change to `api/_lib/auth.js`, the file 82 API files
require -- is answered by that gate with

    "No file in this change names a Tier A resource on a changed line ...
     Nothing to record."   exit 0

The class closes that by matching on PATH. Arm 1 below pins the gap itself, so
the day somebody "simplifies" the class away, the reason it existed is still
driven rather than only written down.

THE THREE THINGS A CLASS LIKE THIS FAILS BY, each with an arm:

  1. IT IS RED ON ARRIVAL and gets switched off. The class ships EMPTY and must
     be a no-op -- arm 2 drives a member-shaped change with no members and
     requires exit 0.
  2. IT SILENTLY IGNORES A MEMBER IT CANNOT EVALUATE, so the list looks
     protective and protects nothing. Arm 5 plants an unknown `kind` and
     requires CouldNotTell rather than a skip (PR 1.11).
  3. IT FIRES ON EVERYTHING, which is the same as firing on nothing. Arm 4
     drives a sql/ file with no grant or revoke in the diff and requires no
     match -- a gate that refuses every SQL file would be talked past within a
     day.

NO ARM EDITS THE REAL CLASS. Every arm passes its own members in, so this probe
cannot be made to pass by adding a member to the shipped tuple, and adding one
cannot make it fail.
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'tier_a_review_gate.py')

spec = importlib.util.spec_from_file_location('tier_a_review_gate', TOOL)
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

ok = 0
bad = []


def check(label, cond, detail=''):
    global ok
    if cond:
        ok += 1
        print('  ok   ' + label)
    else:
        bad.append(label + (' -- ' + detail if detail else ''))
        print('  FAIL ' + label + (('\n       ' + detail) if detail else ''))


AUTH = 'api/_lib/auth.js'
MEMBER = (('path', AUTH, 'shared by 82 API files; a token minted under a wrong '
                         'role map cannot be recalled by a revert'),)

SQL_DIFF = ('diff --git a/sql/x_grants.sql b/sql/x_grants.sql\n'
            '--- a/sql/x_grants.sql\n+++ b/sql/x_grants.sql\n@@ -1,2 +1,3 @@\n'
            ' -- header\n'
            '+revoke delete on public.dnt_patients from service_role;\n')
SQL_NO_GRANT = SQL_DIFF.replace(
    '+revoke delete on public.dnt_patients from service_role;',
    '+-- a comment that mentions nothing')
SQLGRANT = (('sqlgrant', None,
             'the statement has already run against the live database'),)

print('irreversible class: does it refuse, stay quiet, and fail closed?\n')

print('1. THE MEASURED GAP -- the name-based half cannot see this change')
sha = subprocess.run(['git', 'log', '--format=%H', '-1', '--since=2026-09-11',
                      '--', AUTH], cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
if not sha:
    print('  SKIPPED: no recent commit touching ' + AUTH + ' in this clone')
    auth_diff = None
else:
    # ── MADE HERMETIC 2026-10-15 (cody b16), AND THE OLD ARM'S OWN
    #    DIAGNOSIS WOULD HAVE BEEN WRONG ─────────────────────────────────────
    # This arm went red in the b15 full-tree run and its failure text invited
    # exactly one conclusion: "if the name-based half now catches shared
    # libraries, re-read whether this class is still needed". DRIVEN, that
    # conclusion is FALSE, and it was leaking live state in TWO ways at once:
    #
    #  1 THE OBLIGATION FILE. G.check() reads the real
    #    docs/tier-a-reviews.json, whose open obligations change every time any
    #    session opens or discharges one. Measured today it answered "TIER A
    #    CODE CHANGED AND ONLY PART OF IT IS RECORDED ... already covered:
    #    invoices, leg_aftercare" -- today's backlog, not this gap.
    #  2 THE COMMIT'S SCOPE. `range_diff(sha~1, sha)` takes the WHOLE commit,
    #    and the most recent commit touching api/_lib/auth.js also touched
    #    api/_lib/leg-roles.js and others that DO name Tier A resources. So the
    #    arm was asking about auth.js and measuring a twenty-resource change.
    #
    # Both are closed here: the obligation file is a FIXTURE with no records,
    # and the diff is RESTRICTED to the one path the arm is about. With both
    # controlled the gate answers exit 0 -- "No file in this change names a
    # Tier A resource on a changed line" -- so THE GAP IS REAL and this class
    # is still needed. The pin is still on the gap; it is now a pin on the gap
    # rather than on today's obligation backlog.
    _fxdir = tempfile.mkdtemp(prefix='irrev-tiera-fixture-')
    _fx = os.path.join(_fxdir, 'tier-a-reviews.json')
    io.open(_fx, 'w', encoding='utf-8', newline='\n').write(
        json.dumps({'records': []}, indent=1))
    _real_reviews = G.REVIEWS
    G.REVIEWS = _fx
    try:
        auth_diff = subprocess.run(
            ['git', 'diff', '-U3', sha + '~1', sha, '--', AUTH],
            cwd=REPO, capture_output=True, text=True, encoding='utf-8',
            errors='replace').stdout
        # A PRECONDITION, not an assumption: an empty diff would make the arm
        # below pass over nothing at all.
        check('the path-restricted diff for ' + AUTH + ' is NON-EMPTY, so the '
              'arm below is measuring a real change to that one file',
              len(auth_diff.strip()) > 0,
              'git diff %s~1 %s -- %s produced %d bytes'
              % (sha[:12], sha[:12], AUTH, len(auth_diff)))
        code, lines = G.check(auth_diff, verbose=True)
        # THE PIN IS ON THE GAP, NOT ON THE FIX. If this ever stops being exit
        # 0 with no members, the name-based half has grown to cover shared
        # libraries and this whole class may be redundant -- which is a
        # finding, not a failure, and this message says so rather than reading
        # as a defect. It is now a trustworthy signal: with the obligation file
        # and the diff scope both fixtured, exit 1 can only mean the matcher
        # changed.
        check('with NO members, a change to ' + AUTH + ' is still not recorded '
              '(this is the gap the class exists for)',
              code == 0, 'exit was %d -- the obligation file is a FIXTURE with '
                         'no records and the diff is restricted to %s, so if '
                         'this is not 0 the name-based half really has grown '
                         'to cover shared libraries; re-read whether this '
                         'class is still needed. lines: %s'
                         % (code, AUTH, str(lines)[:200]))
    finally:
        G.REVIEWS = _real_reviews
        shutil.rmtree(_fxdir, ignore_errors=True)

print('\n2. THE EMPTY CLASS IS A NO-OP -- nothing is red on arrival')
check('an empty class matches nothing, even on a member-shaped path',
      G.touched_irreversible(SQL_DIFF, ()) == {}, repr(G.touched_irreversible(SQL_DIFF, ())))
check('...and the SHIPPED class is empty, so this gate changes no push today',
      G.IRREVERSIBLE_CLASS == (), repr(G.IRREVERSIBLE_CLASS))

print('\n3. WITH A MEMBER, the same change is REFUSED and NAMED')
if auth_diff is not None:
    hit = G.touched_irreversible(auth_diff, MEMBER)
    check('the member matches on path', AUTH in hit, repr(hit))
    real = G.IRREVERSIBLE_CLASS
    try:
        G.IRREVERSIBLE_CLASS = MEMBER
        code, lines = G.check(auth_diff, verbose=True)
    finally:
        G.IRREVERSIBLE_CLASS = real
    body = '\n'.join(lines)
    check('...and check() refuses it', code == 1, 'exit was %d' % code)
    check('...naming the file and marking it IRREVERSIBLE',
          AUTH in body and '[IRREVERSIBLE]' in body, body[:300])
    check('...and says WHY the name-based half missed it',
          'matched on PATH' in body, body[:400])
    # THE OTHER DIRECTION, or the arms above only prove a gate that always
    # refuses. A diff touching nothing in the class must still pass WITH the
    # member installed.
    real = G.IRREVERSIBLE_CLASS
    try:
        G.IRREVERSIBLE_CLASS = MEMBER
        code2, _ = G.check(SQL_NO_GRANT, verbose=True)
    finally:
        G.IRREVERSIBLE_CLASS = real
    check('...while an unrelated change still passes with the member installed',
          code2 == 0, 'exit was %d' % code2)

print('\n4. THE sqlgrant KIND matches a statement, not a directory')
check('a diff ADDING a revoke matches',
      G.touched_irreversible(SQL_DIFF, SQLGRANT) == {'sql/ grant|revoke': ['sql/x_grants.sql']},
      repr(G.touched_irreversible(SQL_DIFF, SQLGRANT)))
check('a sql/ diff with NO grant or revoke does NOT match -- a gate that '
      'refused every SQL file would be talked past',
      G.touched_irreversible(SQL_NO_GRANT, SQLGRANT) == {},
      repr(G.touched_irreversible(SQL_NO_GRANT, SQLGRANT)))
# The match is on ADDED lines. A revoke sitting in context is not this push's.
CTX = SQL_DIFF.replace('+revoke delete', ' revoke delete')
check('a grant in hunk CONTEXT does not match -- it is not what this push does',
      G.touched_irreversible(CTX, SQLGRANT) == {}, repr(G.touched_irreversible(CTX, SQLGRANT)))

print('\n5. FAIL CLOSED: a member this gate cannot evaluate is COULD NOT TELL')
try:
    G.touched_irreversible(SQL_DIFF, (('bogus-kind', 'x', 'why'),))
    check('an unknown member kind raises rather than being skipped', False,
          'it returned instead of raising -- a member silently ignored '
          'protects nothing while appearing in the list')
except G.CouldNotTell as e:
    check('an unknown member kind raises rather than being skipped', True)
    check('...and the message names the kind', 'bogus-kind' in str(e), str(e)[:160])
# AND IT REACHES THE EXIT CODE as 2, not 1: the hook maps 1 to a specific
# accusation and 2 to "could not tell", and this file's own header records what
# happens when a crash wears the vocabulary of a finding.
real = G.IRREVERSIBLE_CLASS
try:
    G.IRREVERSIBLE_CLASS = (('bogus-kind', 'x', 'why'),)
    code, lines = G.check(SQL_DIFF, verbose=True)
finally:
    G.IRREVERSIBLE_CLASS = real
check('...and check() returns 2 (could-not-tell), never 1 (a finding)',
      code == 2, 'exit was %d: %s' % (code, ' '.join(lines)[:200]))

print('')
if bad:
    print('%d ARM(S) FAILED' % len(bad))
    for b in bad:
        print('  ' + b)
    sys.exit(1)
print('ALL %d IRREVERSIBLE-CLASS ASSERTIONS PASS' % ok)
