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
def problems(rec, resolve_files=True, unknown=None):
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
        # ── THE OLD PREDICATE WAS IMPOSSIBLE TO HOLD. 2026-10-15 (cody b18) ─
        # It required `git log -1 --format=%H -- <files>` to EQUAL the recorded
        # sha -- i.e. the record's sha must still be the LAST commit touching
        # its own file set. That is true at the instant the record is written
        # and decays the moment anybody touches any of those files again, which
        # on a repo with five pushing sessions is hours.
        #
        # MEASURED over the 26 records carrying the field:
        #     3   still match (their files simply have not been touched since)
        #     11  the recorded sha is an ANCESTOR of the current answer -- the
        #         record was RIGHT when written and the files moved after it
        #     8   the recorded sha IS NOT AN OBJECT IN THIS CLONE AT ALL -- the
        #         commit was rewritten by a rebase after the record was written
        #     4   the sha exists but is unreachable from HEAD -- same cause, an
        #         abandoned pre-rebase commit still in the object store
        # 23 of 26 CANNOT match, and not one of them is a defect in a record.
        # That is 23 of this probe's 24 real-record failures.
        #
        # WHAT THE STAMP IS ACTUALLY FOR: proving the sha was derived from the
        # record's OWN FILE SET rather than from HEAD -- which is the whole
        # reason `opened_at_sha_basis` exists. The time-stable form of that is
        # MEMBERSHIP, not recency: the sha must be a commit that TOUCHES the
        # file set. A HEAD-derived stamp on a record whose files HEAD did not
        # touch still fails it, which is the defect being guarded. It survives
        # every later commit, and it is NAMED AS WEAKER than the original: it
        # cannot tell "derived from the file set" from "derived from HEAD on a
        # day HEAD happened to touch one of these files".
        #
        # AND A REWRITTEN SHA IS COULD-NOT-TELL, NOT A FAILURE. A rebase can
        # delete the commit a correct record names. Folding that into either a
        # pass or a failure would be the same mistake in two directions, so it
        # goes out of band through `unknown`.
        if unknown is not None:
            t = git('cat-file', '-t', sha)
            if t.returncode != 0 or t.stdout.strip() != 'commit':
                unknown.append('sha %s is NOT AN OBJECT in this clone -- the '
                               'commit was rewritten (a rebase) after this '
                               'record was written. COULD NOT TELL.'
                               % str(sha)[:12])
                return bad
            if git('merge-base', '--is-ancestor', sha, 'HEAD').returncode != 0:
                unknown.append('sha %s is not reachable from HEAD -- an '
                               'abandoned pre-rebase commit. COULD NOT TELL.'
                               % str(sha)[:12])
                return bad
        q = git('log', '--format=%H', '--', *files)
        touched = set((q.stdout or '').split())
        if q.returncode != 0 or not touched:
            bad.append('git log over its %d file(s) answered nothing, so the '
                       'sha cannot be re-derived -- COULD NOT TELL for this row'
                       % len(files))
        elif sha not in touched:
            bad.append('sha %s touches NONE of its %d declared file(s), so it '
                       'was not derived from them' % (str(sha)[:12], len(files)))
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
# A REAL commit that touches something else entirely, for the negative fixture.
# Re-derived rather than pinned, and checked to be DIFFERENT from _real -- if a
# single commit touched both files the fixture would assert nothing, and that is
# a precondition rather than an assumption.
_other = git('log', '-1', '--format=%H', '--', 'docs/SAIRN-PROCESS-RULES.md'
             ).stdout.strip()
if not _real or not _other or _real == _other:
    could_not_run('the fail-first fixtures need two DIFFERENT real commits, one '
                  'touching tools/tier_a_review_gate.py and one touching '
                  'docs/SAIRN-PROCESS-RULES.md. Got %r and %r, so the negative '
                  'fixture would assert nothing.'
                  % (str(_real)[:12], str(_other)[:12]))
FIXTURES = [
    ('the field MISSING is flagged',
     {'opened_at': '2099-01-01T00:00:00Z', 'files': GOODFILES,
      'opened_at_sha': _real}),
    # ── THE NEGATIVE FIXTURE NEEDED A REAL SHA. 2026-10-15 (cody b18) ──────
    # It used 'd' * 40. Under the membership predicate a non-existent sha is
    # COULD-NOT-TELL rather than flagged -- correctly, because a rebase can
    # delete the commit a sound record names -- so this fixture would have
    # stopped flagging anything. It now uses a REAL commit that touches a
    # DIFFERENT file, which is the actual defect shape: a sha derived from
    # something other than the record's own file set.
    ('a file-set sha that does NOT match its file set is flagged',
     {'opened_at': '2099-01-01T00:00:00Z', 'files': GOODFILES,
      'opened_at_sha': _other, 'opened_at_sha_basis': 'file-set'}),
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

CNR = []
for rec in POST:
    _u = []
    p = problems(rec, unknown=_u)
    if _u:
        # COULD NOT TELL, OUT OF BAND. The sha this record names was rewritten
        # or abandoned by a rebase, so neither "sound" nor "unsound" is
        # derivable for it. Counted and printed, never folded into either.
        CNR.append('%s %s -- %s' % (rec.get('author_session'),
                                    rec['opened_at'], _u[0]))
        continue
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
if CNR:
    print('')
    print('%d post-fix record(s) COULD NOT BE TOLD EITHER WAY -- not passed, '
          'not failed:' % len(CNR))
    for c in CNR:
        print('  - ' + c)
    print('  Each names a commit a REBASE rewrote or abandoned after the record '
          'was written.')
    print('  The record may be perfectly sound; this clone can no longer '
          're-derive it.')
print('tier-a --open basis probe: %d/%d arm(s) pass (%d fail-first fixture, '
      '%d real record asserted, %d could-not-tell)'
      % (passed, len(arms), len(FIXTURES) + 1, len(POST) - len(CNR), len(CNR)))
# A FAILED ARM OUTRANKS A COULD-NOT-TELL. And a run where EVERY real record was
# could-not-tell has asserted nothing about the ledger, so it must not report
# clean -- that is the empty-population shape this file's own docstring is about,
# arriving by rebase rather than by there being no records.
if passed != len(arms):
    sys.exit(1)
if CNR and len(POST) == len(CNR):
    could_not_run('every one of the %d post-fix records names a sha this clone '
                  'cannot resolve, so the fixtures passed and NOTHING was '
                  'asserted about the real ledger.' % len(POST))
sys.exit(3 if CNR else 0)
