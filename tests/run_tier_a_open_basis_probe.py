#!/usr/bin/env python
# OWNER: cc
"""Does --open still stamp the FILE SET rather than HEAD? One field answers it.

    python tests/run_tier_a_open_basis_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

THE DEFECT THIS WATCHES. tools/tier_a_review_gate.py --open used to stamp
`opened_at_sha` with HEAD, which is the commit the reviewer's diff is relative to
ONLY when --open runs directly on top of the change. 18078d38 measured the cost --
"34 of 63 checkable records anchor an obligation to a commit that never contained
its subject" -- and replaced it with subject_sha(file_set), recording the basis
beside the sha: 'file-set' is the real answer, 'head' the honest fallback when a
record names no files, 'could-not-tell' a refusal rather than a guess.

WHY ONE FIELD IS THE WHOLE CHECK. The fix is unobservable in the ledger except
through `opened_at_sha_basis`, which the fixed code writes on EVERY record and the
old code wrote on NONE. So its presence dates a record to after the fix, and its
value plus the sha can be re-derived from git. That makes a one-field assertion
strictly better than re-deriving 238 shas: it cannot be satisfied by accident.

THREE POPULATIONS, AND CONFLATING ANY TWO IS THE DEFECT THIS WOULD OTHERWISE HAVE
  POST-FIX   opened after 18078d38's commit time. These MUST carry the field, and
             a 'file-set' one must equal `git log -1` over its own files.
  PRE-FIX    opened before it. These CANNOT carry the field and are EXEMPT. The
             count is printed, never silently dropped -- an exemption nobody
             re-derives is how a population shrinks without anybody deciding.
  EMPTY      no post-fix record exists yet. That is COULD NOT RUN, not clean.
             A probe that reports clean over an empty population is the exact
             shape this repo keeps paying for: 'fixed' and 'never ran' would print
             the same line.

AND IT FAILS FIRST, ON FIXTURES, rather than waiting for a bad record to appear.
Four hand-built post-fix-shaped records are driven through the same predicate: one
with the field MISSING, one whose sha does not match its file set, one claiming
'head' while naming files, and one with a basis outside the vocabulary. Each must
be FLAGGED. Without those the real arm could pass by never being able to fail.

WHAT THIS PROBE CANNOT SEE, stated rather than discovered later:
  * whether subject_sha picked the RIGHT file set. It checks that the sha matches
    the files the record publishes; if --open derived the sha from a smaller set
    than it published, both would be self-consistent and wrong together. The gate
    has its own comment about that and it is not answerable from the ledger.
  * a record whose files have since been deleted. `git log -1` over a removed path
    still answers, so such a record passes here on a path that no longer exists.
  * 'could-not-tell'. It is accepted with sha None because that is the gate's own
    refusal value; no arm asserts the gate reaches it correctly.
  * anything about --discharge. This is the --open half only.
"""
import calendar
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'docs', 'tier-a-reviews.json')
# The commit that replaced head_sha() with subject_sha(file_set). Pinned by SHA
# AND re-checked by subject, so a rebase that moves it is a COULD NOT RUN rather
# than a silently wrong cutoff.
FIX_SHA = '18078d382de80a55dada34c13b4982149dcf7eda'
FIX_SUBJECT_FRAGMENT = '--open stamped HEAD'
BASES = ('file-set', 'head', 'could-not-tell')


def git(*a):
    return subprocess.run(['git'] + list(a), cwd=ROOT, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


def could_not_run(msg):
    print('COULD NOT RUN -- %s' % msg)
    sys.exit(2)


if not os.path.isfile(LEDGER):
    could_not_run('%s is absent.' % LEDGER)

r = git('log', '-1', '--format=%ct%n%s', FIX_SHA)
if r.returncode != 0 or not r.stdout.strip():
    could_not_run('the pinned fix commit %s does not resolve in this clone, so '
                  'there is no cutoff to partition the ledger by. Re-pin it by '
                  'finding the commit whose subject contains %r.'
                  % (FIX_SHA[:12], FIX_SUBJECT_FRAGMENT))
_lines = r.stdout.strip().split(chr(10))
FIX_EPOCH = int(_lines[0])
if FIX_SUBJECT_FRAGMENT not in (_lines[1] if len(_lines) > 1 else ''):
    could_not_run('%s resolves but its subject does not contain %r -- the pin is '
                  'stale and the cutoff would be wrong. Subject is: %r'
                  % (FIX_SHA[:12], FIX_SUBJECT_FRAGMENT,
                     _lines[1] if len(_lines) > 1 else ''))

try:
    LED = json.load(io.open(LEDGER, encoding='utf-8'))
except ValueError as e:
    could_not_run('%s does not parse as JSON: %s' % (LEDGER, e))
RECORDS = LED.get('records') or []
if not RECORDS:
    could_not_run('the ledger holds no records at all.')


def epoch(rec):
    try:
        return calendar.timegm(time.strptime(rec['opened_at'],
                                             '%Y-%m-%dT%H:%M:%SZ'))
    except Exception:                                           # noqa: BLE001
        return None


# ── THE PREDICATE. One function, used on the REAL records and on the fixtures,
# because two copies of a rule that must agree is how they stop agreeing.
def problems(rec, resolve_files=True):
    """-> [] when this post-fix record is sound, else a list of reasons."""
    bad = []
    basis = rec.get('opened_at_sha_basis')
    sha = rec.get('opened_at_sha')
    files = rec.get('files') or []
    if 'opened_at_sha_basis' not in rec:
        bad.append('no opened_at_sha_basis -- opened after the fix and the fix '
                   'writes that field on every record')
        return bad
    if basis not in BASES:
        bad.append('basis %r is outside %s' % (basis, (BASES,)))
        return bad
    if basis == 'head':
        if files:
            bad.append('basis is "head" but the record names %d file(s). head is '
                       'the fallback for a record with NO files; with files it '
                       'means the file-set derivation was skipped' % len(files))
        return bad
    if basis == 'could-not-tell':
        if sha:
            bad.append('basis is "could-not-tell" but a sha %r is recorded. A '
                       'refusal does not also answer' % str(sha)[:12])
        return bad
    # basis == 'file-set'
    if not sha:
        bad.append('basis is "file-set" and no sha is recorded')
        return bad
    if not files:
        bad.append('basis is "file-set" and the record names no files, so there '
                   'was no set to derive it from')
        return bad
    if resolve_files:
        q = git('log', '-1', '--format=%H', '--', *files)
        want = q.stdout.strip()
        if q.returncode != 0 or not want:
            bad.append('git log -1 over its %d file(s) answered nothing, so the '
                       'sha cannot be re-derived -- COULD NOT TELL for this row'
                       % len(files))
        elif want != sha:
            bad.append('sha %s is not the last commit touching its own file set '
                       '(%s)' % (str(sha)[:12], want[:12]))
    return bad


POST = [x for x in RECORDS if (epoch(x) or 0) > FIX_EPOCH]
PRE = [x for x in RECORDS if (epoch(x) or 0) <= FIX_EPOCH]
UNDATED = [x for x in RECORDS if epoch(x) is None]

print('fix commit      : %s  %s'
      % (FIX_SHA[:12], time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(FIX_EPOCH))))
print('records         : %d total' % len(RECORDS))
print('  POST-FIX      : %d  -- asserted on below' % len(POST))
print('  PRE-FIX       : %d  -- EXEMPT, they predate the field' % len(PRE))
if UNDATED:
    print('  UNDATED       : %d  -- opened_at unparseable, NOT asserted and NOT '
          'counted clean' % len(UNDATED))

arms = []

# ── FAIL-FIRST FIXTURES. Hand-built, locked before the real records are read.
GOODFILES = ['tools/tier_a_review_gate.py']
_real = git('log', '-1', '--format=%H', '--', *GOODFILES).stdout.strip()
FIXTURES = [
    ('the field MISSING is flagged',
     {'opened_at': '2099-01-01T00:00:00Z', 'files': GOODFILES,
      'opened_at_sha': _real}),
    ('a file-set sha that does NOT match its file set is flagged',
     {'opened_at': '2099-01-01T00:00:00Z', 'files': GOODFILES,
      'opened_at_sha': 'd' * 40, 'opened_at_sha_basis': 'file-set'}),
    ('basis "head" while NAMING files is flagged',
     {'opened_at': '2099-01-01T00:00:00Z', 'files': GOODFILES,
      'opened_at_sha': _real, 'opened_at_sha_basis': 'head'}),
    ('a basis outside the vocabulary is flagged',
     {'opened_at': '2099-01-01T00:00:00Z', 'files': GOODFILES,
      'opened_at_sha': _real, 'opened_at_sha_basis': 'whatever'}),
]
for label, rec in FIXTURES:
    arms.append(('FAIL-FIRST: %s' % label, bool(problems(rec)), True))

# And the positive fixture, so the predicate is not simply always-true.
arms.append(('FAIL-FIRST: a correctly stamped record is NOT flagged',
             problems({'opened_at': '2099-01-01T00:00:00Z', 'files': GOODFILES,
                       'opened_at_sha': _real,
                       'opened_at_sha_basis': 'file-set'}), []))

# ── THE REAL ARM. Empty is COULD NOT RUN, and it is checked AFTER the fixtures
# so a reader of an exit 2 still sees that the predicate works.
if not POST:
    for name, got, want in arms:
        print('  %-4s %s' % ('PASS' if got == want else 'FAIL', name))
    bad_fx = [n for n, g, w in arms if g != w]
    if bad_fx:
        print('and the FIXTURES themselves failed, which is a defect in this '
              'probe before it is anything about the ledger.')
        sys.exit(1)
    could_not_run('NO RECORD HAS BEEN OPENED SINCE THE FIX. The %d pre-fix '
                  'records cannot carry the field and are exempt, so there is '
                  'nothing to assert and this is NOT a pass. The fix is correct '
                  'by construction and UNEXERCISED by the real --open path; the '
                  'next --open by anybody closes this.' % len(PRE))

for rec in POST:
    p = problems(rec)
    arms.append(('REAL: %s %s is stamped from its FILE SET'
                 % (rec.get('author_session'), rec['opened_at']), p, []))

# ── AND THE EXEMPTION IS CHECKED, not assumed: a pre-fix record carrying the
# field would mean the cutoff is wrong, and that is worth knowing.
_pre_with = [x for x in PRE if 'opened_at_sha_basis' in x]
arms.append(('the exemption holds -- no PRE-FIX record carries the field, which '
             'is what makes the cutoff believable',
             len(_pre_with), 0))

passed = 0
for name, got, want in arms:
    ok = got == want
    passed += ok
    print('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
    if not ok:
        print('       wanted %r' % (want,))
        print('       got    %r' % (got,))
print('tier-a --open basis probe: %d/%d arm(s) pass (%d fail-first fixture, '
      '%d real record)' % (passed, len(arms), len(FIXTURES) + 1, len(POST)))
sys.exit(0 if passed == len(arms) else 1)
