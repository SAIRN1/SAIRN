"""Control on the MERGEABLE-ledger half of tools/sairn_rebase_resolve.py.

    python tests/rebase_resolve_merge_control.py

Two halves, and the second is the one that makes the first mean anything.

BEHAVIOUR ARMS build a real throwaway git repo, produce a real rebase conflict
in a real ledger, and assert what the tool does. No mocking of git: the defect
this whole tool exists for -- `--theirs` not meaning what it reads like DURING A
REBASE -- is invisible to anything that fakes the stages, and stage 2/3 are
inverted relative to the words git prints. A fixture that hand-builds the three
sides cannot catch getting that backwards. This one can, because arm 1 asserts
which side's record ordering survived.

SABOTAGE ARMS then delete each guard from a scratch copy of the tool and require
the matching behaviour arm to FAIL. A control that has never been seen to fail
is not evidence that the guard works; it is evidence that the arm ran. Four of
the eight standing disciplines in docs/2026-09-13-cross-domain-disciplines.md
were paid for by checks that passed while testing nothing.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'sairn_rebase_resolve.py')
LEDGER = 'docs/ledger.json'

FAILURES = []
PASSES = [0]
TEMPS = []


def arm(name, ok, detail=''):
    if ok:
        PASSES[0] += 1
        print('  ok   %s' % name)
    else:
        FAILURES.append('%s\n         %s' % (name, detail))
        print('  FAIL %s\n         %s' % (name, detail))
    return bool(ok)


def git(cwd, *a):
    r = subprocess.run(('git',) + a, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def git_lines(cwd, *a):
    """STDOUT ONLY. git writes the CRLF warning to stderr, and folding the two
    together put `warning: ... LF will be replaced by CRLF` into a list of
    filenames -- an arm that failed on a real repo for a reason that had nothing
    to do with what it was testing."""
    r = subprocess.run(('git',) + a, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return [x for x in (r.stdout or '').split('\n') if x.strip()]


def policy(identity=('id',), strategy='union-by-identity',
           records_key='records', validator=('tools/validate.py',)):
    return {'strategy': strategy, 'records_key': records_key,
            'identity': list(identity), 'validator': list(validator)}


def ledger(records, pol=None, indent=2, **extra):
    d = {'merge_policy': policy() if pol is None else pol}
    d.update(extra)
    d['records'] = records
    return d, indent


def rec(i, **kw):
    r = {'id': 'r%d' % i, 'what': 'record %d' % i}
    r.update(kw)
    return r


def dump(obj, indent):
    return json.dumps(obj, indent=indent, ensure_ascii=False) + '\n'


def write(tmp, rel, text):
    p = os.path.join(tmp, rel.replace('/', os.sep))
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(p, 'w', encoding='utf-8', newline='').write(text)


def scenario(base, upstream, local, validator_exit=0, tool=TOOL,
             write_validator=True, dry=False):
    """Real repo, real rebase, real conflict. Returns (exit, output, tmpdir)."""
    tmp = tempfile.mkdtemp(prefix='rrmc_')
    TEMPS.append(tmp)
    git(tmp, 'init', '-q', '-b', 'main')
    git(tmp, 'config', 'user.email', 'control@example.invalid')
    git(tmp, 'config', 'user.name', 'control')
    if write_validator:
        write(tmp, 'tools/validate.py',
              'import sys\nsys.exit(%d)\n' % validator_exit)
        git(tmp, 'add', 'tools/validate.py')

    for obj_indent, msg, branch in ((base, 'base', None),
                                    (local, 'local', 'feature'),
                                    (upstream, 'upstream', 'main')):
        if branch == 'feature':
            git(tmp, 'checkout', '-q', '-b', 'feature')
        elif branch == 'main':
            git(tmp, 'checkout', '-q', 'main')
        obj, indent = obj_indent
        write(tmp, LEDGER, dump(obj, indent))
        git(tmp, 'add', LEDGER)
        git(tmp, 'commit', '-q', '-m', msg)

    git(tmp, 'checkout', '-q', 'feature')
    code, _out = git(tmp, 'rebase', 'main')
    if code == 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise AssertionError('fixture produced NO conflict -- the arm built on '
                             'it would pass without testing anything')
    argv = [sys.executable, tool] + (['--dry'] if dry else [])
    r = subprocess.run(argv, cwd=tmp, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or ''), tmp


def disk_text(tmp):
    return io.open(os.path.join(tmp, LEDGER.replace('/', os.sep)),
                   encoding='utf-8').read()


def ids_on_disk(tmp):
    obj = json.loads(io.open(os.path.join(tmp, LEDGER.replace('/', os.sep)),
                             encoding='utf-8').read())
    return [r['id'] for r in obj['records']], obj


def staged(tmp):
    return git_lines(tmp, 'diff', '--name-only', '--cached')


def unmerged(tmp):
    return git_lines(tmp, 'diff', '--name-only', '--diff-filter=U')


def has_stages(tmp):
    """The index still holds 1/2/3 for the ledger -- nothing was resolved."""
    return bool(git_lines(tmp, 'ls-files', '-u', LEDGER))


def still_conflicted(tmp):
    """The honest form of "nothing was staged" DURING a rebase.

    `git diff --cached` lists a file that merely HOLDS unmerged stages, so
    asserting it is empty fails even when the tool touched nothing -- the first
    draft of this control did exactly that, and the arms looked like real
    findings. What a refusal must leave behind is the CONFLICT, unresolved,
    which is what --diff-filter=U reports.
    """
    return unmerged(tmp) == [LEDGER]


# ── THE ARMS. Each returns (exit, output, tmp) so sabotage can re-run one. ────

def a1_clean_append(tool=TOOL):
    """Both sides appended. The one case that HAS a right answer."""
    base = ledger([rec(1)])
    up = ledger([rec(1), rec(2)])
    loc = ledger([rec(1), rec(3)])
    code, out, tmp = scenario(base, up, loc, tool=tool)
    try:
        ids, obj = ids_on_disk(tmp)
        ok = arm('a clean both-sides-append is merged and staged, exit 0',
                 code == 0, 'exit %d\n%s' % (code, out[-500:]))
        ok &= arm('...and it is a UNION -- neither side is dropped',
                  ids == ['r1', 'r2', 'r3'], ids)
        ok &= arm('...in upstream order first, so the side being rebased ONTO '
                  'keeps its ordering (stage 2 is upstream, not "theirs")',
                  ids.index('r2') < ids.index('r3'), ids)
        ok &= arm('...and the ledger is staged, so the rebase can continue',
                  LEDGER in staged(tmp) and not unmerged(tmp),
                  'staged=%s unmerged=%s' % (staged(tmp), unmerged(tmp)))
        ok &= arm('...and merge_policy survives the merge',
                  obj.get('merge_policy', {}).get('strategy')
                  == 'union-by-identity', sorted(obj))
        return ok, out, tmp
    finally:
        pass


def a2_deletion(tool=TOOL):
    """A record in the ancestor removed on one side. A union resurrects it."""
    base = ledger([rec(1), rec(2)])
    up = ledger([rec(1)])                       # r2 deleted upstream
    loc = ledger([rec(1), rec(2), rec(3)])
    code, out, tmp = scenario(base, up, loc, tool=tool)
    ok = arm('a DELETED ancestor record refuses, exit 1', code == 1,
             'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and says which record and which side',
              'r2' in out and 'upstream' in out, out[-400:])
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a3_both_changed(tool=TOOL):
    """Same record, changed differently on both sides. No side is taken."""
    base = ledger([rec(1)])
    up = ledger([rec(1, what='upstream wording')])
    loc = ledger([rec(1, what='local wording')])
    code, out, tmp = scenario(base, up, loc, tool=tool)
    ok = arm('a record changed DIFFERENTLY on both sides refuses, exit 1',
             code == 1, 'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and names the field that differs', 'what' in out, out[-400:])
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a4_one_side_changed(tool=TOOL):
    """The discharge case: one side edited a record, the other did not."""
    base = ledger([rec(1, status='open'), rec(2)])
    up = ledger([rec(1, status='open'), rec(2), rec(9)])
    loc = ledger([rec(1, status='discharged'), rec(2), rec(3)])
    code, out, tmp = scenario(base, up, loc, tool=tool)
    ok = arm('one-side-changed takes the change rather than refusing, exit 0',
             code == 0, 'exit %d\n%s' % (code, out[-500:]))
    if code == 0:
        _ids, obj = ids_on_disk(tmp)
        got = [r for r in obj['records'] if r['id'] == 'r1'][0].get('status')
        ok &= arm('...and it is the CHANGED version that survives',
                  got == 'discharged', got)
    return ok, out, tmp


def a5_same_id_both_added(tool=TOOL):
    """Not in the ancestor, added on both sides with different content."""
    base = ledger([rec(1)])
    up = ledger([rec(1), rec(7, what='upstream seven')])
    loc = ledger([rec(1), rec(7, what='local seven')])
    code, out, tmp = scenario(base, up, loc, tool=tool)
    ok = arm('the same identity ADDED on both sides, differently, refuses',
             code == 1, 'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a6_validator_missing(tool=TOOL):
    """Fail CLOSED. An absent validator means the check DID NOT RUN."""
    base = ledger([rec(1)])
    up = ledger([rec(1), rec(2)])
    loc = ledger([rec(1), rec(3)])
    code, out, tmp = scenario(base, up, loc, tool=tool, write_validator=False)
    ok = arm('an ABSENT validator is exit 2, not a pass', code == 2,
             'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and names the missing tool', 'tools/validate.py' in out,
              out[-400:])
    # The exit code alone does NOT prove the existence check is load-bearing:
    # with it removed, the merge runs, the absent validator fails to launch, and
    # the result check returns 2 anyway. What only the existence check gives is
    # the refusal happening BEFORE the file is rewritten -- so the working copy
    # still holds its markers, and nothing was done on the strength of a check
    # that never ran.
    ok &= arm('...and refuses BEFORE writing, so the working file is untouched',
              '<<<<<<<' in disk_text(tmp), disk_text(tmp)[:200])
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a7_validator_rejects(tool=TOOL):
    """Merged cleanly, and the ledger's own gate rejects the result."""
    base = ledger([rec(1)])
    up = ledger([rec(1), rec(2)])
    loc = ledger([rec(1), rec(3)])
    code, out, tmp = scenario(base, up, loc, tool=tool, validator_exit=3)
    ok = arm('a validator that REJECTS the merged result is exit 2', code == 2,
             'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and leaves the conflict unresolved even though the merge '
              'itself succeeded', still_conflicted(tmp), unmerged(tmp))
    return ok, out, tmp


def a8_policy_changed(tool=TOOL):
    """A rule that is itself in conflict cannot govern the conflict."""
    base = ledger([rec(1)])
    up = ledger([rec(1), rec(2)], pol=policy(identity=('what',)))
    loc = ledger([rec(1), rec(3)])
    code, out, tmp = scenario(base, up, loc, tool=tool)
    ok = arm('a side that rewrites merge_policy is exit 2', code == 2,
             'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a9_unknown_strategy(tool=TOOL):
    base = ledger([rec(1)], pol=policy(strategy='take-newest'))
    up = ledger([rec(1), rec(2)], pol=policy(strategy='take-newest'))
    loc = ledger([rec(1), rec(3)], pol=policy(strategy='take-newest'))
    code, out, tmp = scenario(base, up, loc, tool=tool)
    ok = arm('an unimplemented strategy is exit 2, never approximated',
             code == 2, 'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a10_undeclared_json(tool=TOOL):
    """The regression that matters: JSON without a policy is still SOURCE."""
    base = ({'records': [rec(1)]}, 2)
    up = ({'records': [rec(1), rec(2)]}, 2)
    loc = ({'records': [rec(1), rec(3)]}, 2)
    code, out, tmp = scenario(base, up, loc, tool=tool)
    ok = arm('JSON with NO merge_policy is still refused as SOURCE, exit 1',
             code == 1 and 'SOURCE' in out, 'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a11_identity_missing(tool=TOOL):
    """A record that cannot be identified is not quietly matched on the rest."""
    base = ledger([rec(1)])
    up = ledger([rec(1), {'what': 'no id at all'}])
    loc = ledger([rec(1), rec(3)])
    code, out, tmp = scenario(base, up, loc, tool=tool)
    ok = arm('a record missing an identity field is exit 2', code == 2,
             'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a12_indent_not_reproducible(tool=TOOL):
    """If we cannot rewrite the file in its own convention, we do not write it."""
    tmp = tempfile.mkdtemp(prefix='rrmc_')
    TEMPS.append(tmp)
    git(tmp, 'init', '-q', '-b', 'main')
    git(tmp, 'config', 'user.email', 'control@example.invalid')
    git(tmp, 'config', 'user.name', 'control')
    write(tmp, 'tools/validate.py', 'import sys\nsys.exit(0)\n')
    git(tmp, 'add', 'tools/validate.py')

    def odd(obj):                       # valid JSON, no indent setting matches
        return json.dumps(obj, ensure_ascii=False, separators=(',', ': ')) + '\n'
    b, _i = ledger([rec(1)])
    u, _i = ledger([rec(1), rec(2)])
    l_, _i = ledger([rec(1), rec(3)])
    write(tmp, LEDGER, odd(b))
    git(tmp, 'add', LEDGER)
    git(tmp, 'commit', '-q', '-m', 'base')
    git(tmp, 'checkout', '-q', '-b', 'feature')
    write(tmp, LEDGER, odd(l_))
    git(tmp, 'add', LEDGER)
    git(tmp, 'commit', '-q', '-m', 'local')
    git(tmp, 'checkout', '-q', 'main')
    write(tmp, LEDGER, odd(u))
    git(tmp, 'add', LEDGER)
    git(tmp, 'commit', '-q', '-m', 'upstream')
    git(tmp, 'checkout', '-q', 'feature')
    code, _o = git(tmp, 'rebase', 'main')
    if code == 0:
        raise AssertionError('fixture produced no conflict')
    r = subprocess.run([sys.executable, tool], cwd=tmp, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    ok = arm('a file this tool cannot reproduce byte-for-byte is exit 2, not '
             'reformatted wholesale', r.returncode == 2,
             'exit %d\n%s' % (r.returncode, out[-500:]))
    ok &= arm('...and leaves the conflict unresolved', still_conflicted(tmp),
              unmerged(tmp))
    return ok, out, tmp


def a13_dry_writes_nothing(tool=TOOL):
    base = ledger([rec(1)])
    up = ledger([rec(1), rec(2)])
    loc = ledger([rec(1), rec(3)])
    code, out, tmp = scenario(base, up, loc, tool=tool, dry=True)
    ok = arm('--dry reports the merge and exits 0', code == 0,
             'exit %d\n%s' % (code, out[-500:]))
    ok &= arm('...and stages nothing and leaves the conflict in place',
              still_conflicted(tmp) and has_stages(tmp),
              'unmerged=%s' % (unmerged(tmp),))
    return ok, out, tmp


ARMS = [a1_clean_append, a2_deletion, a3_both_changed, a4_one_side_changed,
        a5_same_id_both_added, a6_validator_missing, a7_validator_rejects,
        a8_policy_changed, a9_unknown_strategy, a10_undeclared_json,
        a11_identity_missing, a12_indent_not_reproducible, a13_dry_writes_nothing]


# ── SABOTAGE: every guard removed, and the matching arm must NOTICE ──────────
# The mutation is a literal source substitution, and it is asserted to have
# CHANGED the source. A find-and-replace that silently matched nothing produces
# an unmutated tool, the arm passes, and the sabotage run reports the control as
# strong -- inverted, and exactly the shape that put a literal backspace into a
# regex that could never match.
SABOTAGE = [
    ('the deletion guard', a2_deletion,
     'if dropped:', 'if False and dropped:'),
    ('the both-sides-changed guard', a3_both_changed,
     'if clashes:', 'if False and clashes:'),
    ('the validator-existence check', a6_validator_missing,
     "if not os.path.isfile(os.path.join(REPO, val[0])):",
     "if False and not os.path.isfile(os.path.join(REPO, val[0])):"),
    ('the validator-result check', a7_validator_rejects,
     'if r.returncode != 0:\n            print(\'\')',
     'if False and r.returncode != 0:\n            print(\'\')'),
    ('the policy-agreement check', a8_policy_changed,
     "if other != pol:", "if False and other != pol:"),
    ('the strategy check', a9_unknown_strategy,
     "if pol.get('strategy') != STRATEGY:",
     "if False and pol.get('strategy') != STRATEGY:"),
    ('the identity-presence check', a11_identity_missing,
     'if gone:\n                fail(', 'if False and gone:\n                fail('),
    ('the serializer round-trip proof', a12_indent_not_reproducible,
     "    fail('%s: no json.dumps indent in 1..8",
     "    return 2  # sabotage\n    fail('%s: no json.dumps indent in 1..8"),
]


def run_sabotage():
    src = io.open(TOOL, encoding='utf-8').read()
    out_lines = []
    for name, armfn, old, new in SABOTAGE:
        if old not in src:
            out_lines.append(('ANCHOR GONE', name,
                              'the mutation anchor is no longer in the tool, so '
                              'this guard was NOT tested'))
            continue
        d = tempfile.mkdtemp(prefix='rrsab_')
        TEMPS.append(d)
        broken = os.path.join(d, 'sairn_rebase_resolve.py')
        mutated = src.replace(old, new, 1)
        if mutated == src:
            out_lines.append(('NO-OP', name, 'replacement changed nothing'))
            continue
        io.open(broken, 'w', encoding='utf-8', newline='').write(mutated)
        before = len(FAILURES)
        try:
            armfn(tool=broken)
        except Exception as e:                                  # noqa: BLE001
            out_lines.append(('CAUGHT', name, '%s: %s' % (type(e).__name__, e)))
            del FAILURES[before:]
            continue
        caught = len(FAILURES) > before
        del FAILURES[before:]                   # sabotage failures are expected
        out_lines.append(('CAUGHT' if caught else 'MISSED', name,
                          '' if caught else 'the arm PASSED against a tool with '
                                            'this guard removed'))
    return out_lines


def main():
    print('BEHAVIOUR ARMS -- real repo, real rebase, real conflict')
    for fn in ARMS:
        print(' %s' % fn.__name__)
        fn()

    print('')
    print('SABOTAGE ARMS -- each guard removed, the arm must notice')
    verdicts = run_sabotage()
    missed = [v for v in verdicts if v[0] != 'CAUGHT']
    for state, name, why in verdicts:
        print('  %-11s %s%s' % (state, name, ('  -- ' + why) if why else ''))

    print('')
    if FAILURES:
        print('FAILED: %d behaviour arm(s)' % len(FAILURES))
        for f in FAILURES:
            print('    ' + f)
    if missed:
        print('FAILED: %d guard(s) were not actually tested' % len(missed))
    if FAILURES or missed:
        return 1
    print('OK: %d behaviour arm(s), %d guard(s) each proven to be load-bearing '
          'by removing it.' % (PASSES[0], len(verdicts)))
    return 0


if __name__ == '__main__':
    try:
        CODE = main()
    finally:
        for _d in TEMPS:
            shutil.rmtree(_d, ignore_errors=True)
    sys.exit(CODE)
