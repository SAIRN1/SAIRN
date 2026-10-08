#!/usr/bin/env python
# OWNER: cc
"""Is every row in docs/scrutiny-flags.json true of the commit it names?

    python tools/scrutiny_ledger_check.py            # check the committed file
    python tools/scrutiny_ledger_check.py <path>     # check a merged candidate
    python tools/scrutiny_ledger_check.py --fixtures # the criteria lock, alone

Exit 0 every row holds, 1 findings, 2 COULD NOT RUN. READ-ONLY: it runs
`git show` and reads one JSON file, and writes nothing ever.

── WHY IT EXISTS, AND WHY IT IS NAMED IN A MERGE POLICY ────────────────────────
`docs/scrutiny-flags.json` declares `merge_policy: {strategy:
union-by-identity, records_key: flags, identity: [sha, path]}` and NO
`validator` key. `tools/sairn_rebase_resolve.py` requires one -- a non-empty
argv list whose argv[0] exists and which must PASS on the merged result -- so on
2026-10-08 it refused that file's conflict with EXIT 2, correctly, and the merge
had to be done by hand. Its own rule is the reason: "a validator that is absent
means the check DID NOT RUN, which is never a pass."

So this is not a tool somebody has to remember to run. It is referenced from the
policy it validates, which means the resolver invokes it on every conflict in
that file -- the difference this platform keeps paying for between a tool that
EXISTS and a tool that RUNS.

── THE PROPERTY IT CHECKS, AND WHY THAT ONE ────────────────────────────────────
A row says "commit <sha> changed <path>, which is something that CHECKS the
work." That claim is cheap to verify and was false in bulk twice:

  2026-10-06  nine rows keyed `"main"` -- a ref NAME, not a sha, so the
              (sha, path) identity could never dedup them.
  2026-10-08  rows keyed to the push TIP rather than to the commit carrying the
              diff. `bf174f30` was credited with three test files; it changes
              five docs files and none of them. Then the per-commit fix invented
              15 false rows of 20 on its first real push, by handing EMPTY diffs
              to a classifier that returns a row for anything it is given.

Both were found by reading the ledger, not by reading the code that wrote it.
`git show <sha> -- <path>` producing text is the whole property, and it is the
one a reviewer would check by hand.

── THE THREE STATES ARE KEPT APART, WHICH IS THE POINT ─────────────────────────
  HOLDS         the sha resolves and that path really has a diff in it.
  CONTRADICTED  the sha resolves and that path has NO diff in it. A FINDING:
                the row accuses a commit of something it did not do.
  MERGE_KEYED   the sha resolves and is a MERGE. A FINDING, and a DIFFERENT
                one: a merge authors no change, so it is never the commit in
                which a checker was edited -- and `git show` prints no diff for
                a merge, so an empty result there proves nothing either way.
                Separated because reporting "empty diff" for a merge is the
                same misdiagnosis this batch fixed in the D9 message: a true
                sentence pointing at the wrong cause. Measured on the real
                ledger: 18 of 48 apparent contradictions were merge-keyed.
  UNRESOLVABLE  the sha does not resolve in this clone. COULD NOT TELL, never
                folded into either of the others -- a row can legitimately name
                a commit this clone has not fetched, and calling that a finding
                would make the validator refuse honest merges.
Only CONTRADICTED, MERGE_KEYED and MALFORMED make this exit 1. UNRESOLVABLE is counted, named and
reported, and exits 0 with the count stated -- because a validator that fails on
an unfetched commit would be removed from the policy within a week, and then
nothing would check anything.
"""
import argparse
import collections
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join('docs', 'scrutiny-flags.json')
CRITERIA_VERSION = '2026-10-08.1'
EXIT_COULD_NOT_RUN = 2


def git(*args):
    r = subprocess.run(['git', '-C', REPO] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '')


def row_state(sha, path, shower=None):
    """('HOLDS'|'CONTRADICTED'|'UNRESOLVABLE'|'MALFORMED', detail).

    `shower` is injected so the criteria lock can drive every branch without a
    repository. The real one is _git_shower.
    """
    if not isinstance(sha, str) or not isinstance(path, str):
        return 'MALFORMED', 'sha=%r path=%r -- not both strings' % (sha, path)
    sha, path = sha.strip(), path.strip()
    if not sha or not path:
        return 'MALFORMED', 'empty sha or path'
    # A REF NAME IS THE 2026-10-06 DEFECT AND IS CAUGHT BY SHAPE, not by a
    # failed lookup: `main` resolves perfectly well and is still not an
    # identity, because the commit it names changes.
    if not all(c in '0123456789abcdef' for c in sha.lower()) or len(sha) < 7:
        return 'MALFORMED', ('%r is not a sha -- the identity is (sha, path) '
                             'and a ref name breaks dedup silently' % sha)
    resolved, text, parents = (shower or _git_shower)(sha, path)
    if not resolved:
        return 'UNRESOLVABLE', '%s does not resolve in this clone' % sha[:12]
    # ── A MERGE IS ITS OWN VERDICT, AND SAYING "EMPTY DIFF" HERE WOULD BE A
    # ── MISDIAGNOSIS OF EXACTLY THE KIND THIS BATCH FIXED ELSEWHERE (D9).
    # `git show` prints NOTHING for a merge commit by default, so an empty
    # result does not prove the merge failed to carry the file. The row is
    # still wrong -- a merge AUTHORS no change, so it cannot be the commit in
    # which somebody edited a checker -- but it is wrong for a different
    # reason, and reporting the wrong reason sends the reader to the wrong
    # place. Measured on the real ledger: of 48 rows that looked
    # CONTRADICTED, 18 were merge-keyed and would have carried a false
    # explanation.
    if (parents or 0) > 1:
        return 'MERGE_KEYED', ('%s is a MERGE commit (%d parents). A merge '
                               'authors no change, so it is never the commit '
                               'in which a checker was edited -- and `git '
                               'show` prints no diff for one, so an empty '
                               'result here proves nothing either way'
                               % (sha[:12], parents))
    if (text or '').strip():
        return 'HOLDS', ''
    return 'CONTRADICTED', ('%s resolves, is a single-parent commit, and its '
                            'diff for %s is EMPTY -- the row accuses a commit '
                            'of a change it does not contain'
                            % (sha[:12], path))


def _git_shower(sha, path):
    """(resolved, diff_text, parent_count) for one row's commit.

    The parent count is read HERE rather than inferred from an empty diff, so
    row_state() can tell a merge from a contradiction instead of guessing.
    """
    code, _out = git('cat-file', '-e', sha + '^{commit}')
    if code != 0:
        return False, '', 0
    pcode, pout = git('rev-list', '--parents', '-n', '1', sha)
    parents = (len((pout or '').split()) - 1) if pcode == 0 else 0
    _code, text = git('show', '--format=', '--unified=0', sha, '--', path)
    return True, text, parents


def load(path):
    try:
        raw = io.open(path, encoding='utf-8').read()
    except OSError as e:
        return None, 'could not read %s: %s' % (path, e)
    try:
        doc = json.loads(raw)
    except ValueError as e:
        return None, '%s is not valid JSON: %s' % (path, e)
    if not isinstance(doc, dict) or 'flags' not in doc:
        return None, ('%s exists and is not this ledger -- no `flags` key, so '
                      'NOTHING was checked' % path)
    if not isinstance(doc['flags'], list):
        return None, '%s: `flags` is %s, not a list' % (path, type(doc['flags']))
    return doc, ''


# ── THE CRITERIA LOCK (discipline 1), on an INJECTED shower ─────────────────
# The classifier is the whole tool, so it is locked before any real git read,
# and every arm is paired: a shape that must reach one state AND one that must
# not. Driven through row_state() itself rather than a copy of its condition.
FIXTURES = [
    ('aa11bb22cc33', 'tests/x.py', (True, '@@ -1 +1 @@\n-a\n+b\n', 1), 'HOLDS',
     'a sha that resolves with a real diff for that path'),
    ('aa11bb22cc33', 'tests/x.py', (True, '', 1), 'CONTRADICTED',
     'resolves and the diff is EMPTY -- the 2026-10-08 defect, 15 rows of 20'),
    ('aa11bb22cc33', 'tests/x.py', (True, '   \n  \n', 1), 'CONTRADICTED',
     'WHITESPACE is not a diff, so it must not read as one'),
    ('aa11bb22cc33', 'tests/x.py', (False, '', 0), 'UNRESOLVABLE',
     'does not resolve here -- COULD NOT TELL, and it must NOT be a finding, '
     'or the validator refuses honest merges over unfetched commits'),
    ('main', 'tests/x.py', (True, 'diff', 1), 'MALFORMED',
     'a REF NAME is the 2026-10-06 defect and is caught by SHAPE -- it '
     'resolves fine and is still not an identity'),
    ('abc', 'tests/x.py', (True, 'diff', 1), 'MALFORMED',
     'a sha too short to be one'),
    ('aa11bb22cc33', '', (True, 'diff', 1), 'MALFORMED', 'an empty path'),
    (None, 'tests/x.py', (True, 'diff', 1), 'MALFORMED', 'a non-string sha'),
    ('AA11BB22CC33', 'tests/x.py', (True, 'diff', 1), 'HOLDS',
     'UPPERCASE hex is still hex -- a case difference is not a malformed row'),
    ('aa11bb22cc33', 'tests/x.py', (True, '', 2), 'MERGE_KEYED',
     'a MERGE commit with an empty diff is MERGE_KEYED, not CONTRADICTED -- '
     '`git show` prints nothing for a merge, so the empty result proves '
     'nothing and the wrong reason would send the reader to the wrong place'),
    ('aa11bb22cc33', 'tests/x.py', (True, 'diff', 2), 'MERGE_KEYED',
     'a merge is MERGE_KEYED even WITH a diff -- a merge authors no change, '
     'so it is never the commit in which a checker was edited'),
    ('aa11bb22cc33', 'tests/x.py', (True, '', 0), 'CONTRADICTED',
     'a ROOT commit (no parents) with an empty diff is a real contradiction, '
     'not a merge -- the parent count must not be read as "merge if nonzero"'),
]


def run_fixtures(verbose=False):
    bad, arms = [], 0
    for sha, path, shown, want, why in FIXTURES:
        arms += 1
        got, _detail = row_state(sha, path, shower=lambda s, p, _r=shown: _r)
        if got != want:
            bad.append('%s -- wanted %s got %s' % (why, want, got))
        elif verbose:
            print('  ok   %-13s %s' % (want, why))
    return bad, arms


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('path', nargs='?', default=None,
                    help='ledger to check (default docs/scrutiny-flags.json); '
                         'a merged candidate is passed here by the resolver')
    ap.add_argument('--fixtures', action='store_true')
    a = ap.parse_args(argv)

    print('SCRUTINY LEDGER CHECK -- criteria %s' % CRITERIA_VERSION)
    bad, arms = run_fixtures(verbose=a.fixtures)
    if bad:
        print('\nCRITERIA LOCK FAILED -- %d of %d:' % (len(bad), arms))
        for b in bad:
            print('  ! %s' % b)
        print('\nNOTHING REAL WAS CHECKED. A misclassifying validator would '
              'bless a merged\nledger whose rows accuse the wrong commits, '
              'which is worse than no validator.')
        return EXIT_COULD_NOT_RUN
    print('criteria lock: %d/%d fixtures classify correctly, on an injected '
          'shower only' % (arms, arms))
    if a.fixtures:
        return 0

    path = a.path or os.path.join(REPO, LEDGER)
    doc, err = load(path)
    if doc is None:
        print('\nCOULD NOT RUN: %s' % err)
        return EXIT_COULD_NOT_RUN

    pol = doc.get('merge_policy') or {}
    ident = pol.get('identity')
    rows = doc['flags']
    states = collections.Counter()
    findings, unresolved = [], []
    seen = collections.Counter()
    for f in rows:
        if not isinstance(f, dict):
            states['MALFORMED'] += 1
            findings.append('a row that is not an object: %r' % (f,))
            continue
        sha, p = f.get('sha'), f.get('path')
        seen[(sha, p)] += 1
        st, detail = row_state(sha, p)
        states[st] += 1
        if st in ('CONTRADICTED', 'MALFORMED', 'MERGE_KEYED'):
            findings.append('%s  %s' % (p, detail))
        elif st == 'UNRESOLVABLE':
            unresolved.append('%s  %s' % (p, detail))

    dupes = [k for k, n in seen.items() if n > 1]

    print('\n  ledger                  %s' % os.path.relpath(path, REPO))
    print('  rows                  %4d' % len(rows))
    print('  HOLDS                 %4d   <- git show <sha> -- <path> has text'
          % states['HOLDS'])
    print('  CONTRADICTED          %4d   <- resolves, diff EMPTY: A FINDING'
          % states['CONTRADICTED'])
    print('  MERGE_KEYED           %4d   <- keyed to a MERGE, which authors no '
          'change: A FINDING' % states['MERGE_KEYED'])
    print('  MALFORMED             %4d   <- not a (sha, path) at all: A FINDING'
          % states['MALFORMED'])
    print('  UNRESOLVABLE          %4d   <- not in this clone: COULD NOT TELL, '
          'counted and NOT a finding' % states['UNRESOLVABLE'])
    print('  duplicate identities  %4d   <- the policy says union-by-identity '
          '%s' % (len(dupes), ident))

    if unresolved:
        print('\n%d row(s) COULD NOT BE CHECKED -- reported rather than passed '
              'or failed:' % len(unresolved))
        for u in unresolved[:20]:
            print('  ? %s' % u)
        if len(unresolved) > 20:
            print('  ... and %d more' % (len(unresolved) - 20))

    if dupes:
        findings.append('%d identity(ies) appear more than once, which the '
                        'declared union-by-identity policy forbids: %s'
                        % (len(dupes), [(s or '')[:12] + ' ' + (p or '')
                                        for s, p in dupes[:5]]))

    if findings:
        print('\n%d FINDING(S) -- rows that are not true of the commit they '
              'name:' % len(findings))
        for f in findings:
            print('  ! %s' % f)
        print('\nA row whose diff is empty is an accusation that is false on '
              'its face. Do NOT\nmerge a ledger in this state: fix the keying, '
              'or drop the rows and re-derive\nthem from the real commits.')
        return 1

    print('\nCLEAN -- every checkable row is true of the commit it names%s.'
          % ('' if not unresolved
             else ', and %d could not be checked (said above, not folded in)'
                  % len(unresolved)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
