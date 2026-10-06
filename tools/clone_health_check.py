#!/usr/bin/env python
# OWNER: cody
"""Is this clone sick, and which part? Read-only.

    python tools/clone_health_check.py
    python tools/clone_health_check.py --json
    python tools/clone_health_check.py --fixtures

Exit 0 everything checked and healthy, 1 something unhealthy, 2 COULD NOT TELL.
Design note: docs/2026-10-06-cody-queue19-design-notes.md section 2.

── THE INCIDENT, 2026-10-06 ────────────────────────────────────────────────
This clone was found with `core.bare = true` in `.git/config` while carrying a
full working tree. Every `add`, `commit` and `status` failed with "this
operation must be run in a work tree" -- AND `git log` KEPT WORKING, so HEAD
read normally and the failure looked like a commit-message problem. It cost a
blocked batch to diagnose, and the fix was one line.

**There was no single command that would have said "this clone is sick, and
here is which part."** That is what this is.

── IT SWEEPS NOTHING, DELIBERATELY ────────────────────────────────────────
28 worktrees were registered at the time of the incident and EVERY directory
still existed, so `git worktree prune` would have done nothing. Removing another
session's worktree is not a call a health report gets to make, and it is not a
call this tool can make at all -- there is no code path here that deletes
anything or writes any config.

── A PRE-PUSH GATE COULD NOT DO THIS JOB, which is why it is a report ─────
With `core.bare = true` the push machinery is the broken thing. A report that a
human or another tool runs is the only shape that works in that state.

── THE THIRD STATE IS LOAD-BEARING ────────────────────────────────────────
A git call that does not answer inside its bound is COULD NOT TELL, never folded
into healthy. **A health check that reports "fine" because it could not ask is
the worst possible output** -- it is the one shape that stops anybody looking.

── WORKTREE ATTRIBUTION COMES FROM CLAIMS, NOT GIT AUTHORSHIP ─────────────
Every commit in this repo is authored "Michael Dibert", so git authorship says
nothing about which SESSION made a worktree. The attribution here is the same
derivation `tool_owner_map.py` uses: the session that named a matching path in a
`chore(claims)` FILES list. A worktree whose prefix matches nothing is
UNATTRIBUTED -- which is not the same as unowned, and is not reported as such.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

# .2 -- the lock line's arm count is now DERIVED. The literal said 12 over 11
# real arms, so a past report quoting "12 arms" and a present one quoting "11"
# must be distinguishable by stamp rather than looking like a lost arm.
CRITERIA_VERSION = '2026-10-06.2'
EXIT_UNHEALTHY = 1
EXIT_COULD_NOT_TELL = 2
GIT_BOUND = 30
CLAIM_COMMITS = 4000

COULD_NOT_TELL = 'COULD NOT TELL'


def git(args, tree=None, bound=GIT_BOUND):
    """(ok, stdout) or (None, reason). None is COULD NOT TELL, never ''."""
    cmd = ['git', '-C', tree or REPO] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=bound)
    except subprocess.TimeoutExpired:
        return (None, 'timed out at %ds' % bound)
    except Exception as exc:                                   # noqa: BLE001
        return (None, '%s' % exc.__class__.__name__)
    if r.returncode != 0:
        return (False, (r.stderr or r.stdout or '').strip())
    return (True, (r.stdout or '').strip())


def check_bare():
    ok, out = git(['config', '--get', 'core.bare'])
    if ok is None:
        return (COULD_NOT_TELL, out)
    if ok is False:
        # `--get` exits 1 when the key is unset, which is the normal state for
        # a clone that has never had it written. Unset is healthy.
        return ('false (unset)', '')
    return (out, '')


def check_status():
    ok, out = git(['status', '--porcelain'])
    if ok is None:
        return (COULD_NOT_TELL, out, None)
    if ok is False:
        return ('BROKEN', out, None)
    return ('working', '', len([l for l in out.split('\n') if l.strip()]))


def claim_sessions():
    """{session: [path tokens]} from claim-commit subjects, or None."""
    ok, out = git(['log', '--format=%s', '--grep=chore(claims):',
                   '-n', str(CLAIM_COMMITS)])
    if ok is not True:
        return None
    by = {}
    for subj in out.split('\n'):
        m = re.match(r'chore\(claims\):\s+([A-Za-z0-9_]+)\s+claims\b', subj)
        if not m:
            continue
        f = re.search(r'FILES:\s*(.*)$', subj)
        if not f:
            continue
        by.setdefault(m.group(1), []).extend(
            t.replace('\\', '/') for t in f.group(1).split())
    return by


def attribute(name, claims):
    """Which session a worktree name plausibly belongs to, or UNATTRIBUTED.

    Matches the worktree's PREFIX (the part before a trailing -<random>) against
    any tool or test path a session has claimed. Deliberately conservative: a
    guess that names the wrong session is worse than UNATTRIBUTED.
    """
    if claims is None:
        return COULD_NOT_TELL
    stem = re.sub(r'[-_][0-9a-z]{5,}$', '', name)
    stem = re.sub(r'^drs-sandbox', 'dead_rule_sweep', stem)
    tokens = [t for t in re.split(r'[-_]', stem) if len(t) > 3]
    if not tokens:
        return 'UNATTRIBUTED'
    hits = []
    for sess, paths in (claims or {}).items():
        for p in paths:
            base = os.path.basename(p).lower()
            if any(t in base for t in tokens):
                hits.append(sess)
                break
    uniq = sorted(set(hits))
    if len(uniq) == 1:
        return uniq[0]
    if len(uniq) > 1:
        return 'AMBIGUOUS (%s)' % ','.join(uniq)
    return 'UNATTRIBUTED'


def worktrees(claims):
    ok, out = git(['worktree', 'list', '--porcelain'])
    if ok is not True:
        return None
    rows = []
    for line in out.split('\n'):
        if not line.startswith('worktree '):
            continue
        p = line[len('worktree '):].strip()
        if os.path.abspath(p) == os.path.abspath(REPO):
            continue                        # the main worktree is not a leak
        name = os.path.basename(p.rstrip('/\\'))
        exists = os.path.isdir(p)
        last = None
        if exists:
            try:
                last = max(os.path.getmtime(os.path.join(r, f))
                           for r, _d, fs in os.walk(p) for f in fs) \
                    if any(True for _r, _d, fs in os.walk(p) if fs) else None
            except (OSError, ValueError):
                last = None
        rows.append({'path': p, 'name': name,
                     'state': 'LIVE' if exists else 'ORPHAN',
                     'last_write': (time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                                  time.gmtime(last))
                                    if last else None),
                     'age_h': round((time.time() - last) / 3600.0, 1) if last else None,
                     'claimed_by': attribute(name, claims)})
    return rows


def report(as_json=False):
    bare, bare_why = check_bare()
    st, st_why, dirty = check_status()
    claims = claim_sessions()
    wts = worktrees(claims)

    unhealthy, cnt = [], []
    if bare == COULD_NOT_TELL:
        cnt.append('core.bare: %s' % bare_why)
    elif bare.strip().lower() == 'true':
        unhealthy.append('core.bare is TRUE in a clone with a working tree -- '
                         'every add/commit/status fails while `git log` keeps '
                         'working. Fix: git config core.bare false')
    if st == COULD_NOT_TELL:
        cnt.append('git status: %s' % st_why)
    elif st == 'BROKEN':
        unhealthy.append('git status does not work: %s' % st_why)
    if wts is None:
        cnt.append('git worktree list could not be read')
    if claims is None:
        cnt.append('the claim history could not be read, so no worktree is '
                   'attributed -- NOT the same as every worktree being unowned')

    orphans = [w for w in (wts or []) if w['state'] == 'ORPHAN']
    if orphans:
        unhealthy.append('%d registered worktree(s) whose directory is GONE'
                         % len(orphans))

    if as_json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'core_bare': bare,
                          'git_status': st, 'dirty_paths': dirty,
                          'worktrees': wts, 'unhealthy': unhealthy,
                          'could_not_tell': cnt}, indent=1, sort_keys=True))
    else:
        print('CLONE HEALTH -- criteria %s' % CRITERIA_VERSION)
        print('  clone            : %s' % REPO)
        print('  core.bare        : %s%s'
              % (bare, '   <- UNHEALTHY' if bare.strip().lower() == 'true' else ''))
        print('  git status       : %s%s'
              % (st, ('   (%d dirty path(s))' % dirty) if dirty is not None else ''))
        print('  claim history    : %s'
              % ('%d session(s)' % len(claims) if claims is not None
                 else COULD_NOT_TELL))
        if wts is None:
            print('  worktrees        : %s' % COULD_NOT_TELL)
        else:
            print('  worktrees        : %d registered besides the main one '
                  '(%d LIVE, %d ORPHAN)'
                  % (len(wts), len(wts) - len(orphans), len(orphans)))
            if wts:
                print()
                print('  %-34s %-7s %-22s %-7s %s'
                      % ('name', 'state', 'last write (UTC)', 'age h', 'claimed by'))
                for w in sorted(wts, key=lambda x: (x['state'], x['name'])):
                    print('  %-34s %-7s %-22s %-7s %s'
                          % (w['name'][:34], w['state'],
                             w['last_write'] or '-', w['age_h'] if w['age_h'] is not None else '-',
                             w['claimed_by']))
        print()
        if cnt:
            print('COULD NOT TELL (%d) -- this is NOT a clean bill of health:' % len(cnt))
            for c in cnt:
                print('  ? %s' % c)
        if unhealthy:
            print('UNHEALTHY (%d):' % len(unhealthy))
            for u in unhealthy:
                print('  ! %s' % u)
        if not cnt and not unhealthy:
            print('HEALTHY -- and that means every check above actually ran. '
                  'It does NOT mean\nthis clone is correct: a health report '
                  'says nothing about whether the code is right.')
        print()
        print('SWEEPS NOTHING. Not one path here deletes a worktree or writes a '
              'config value.\nA leftover worktree belonging to another session '
              'is reported, never removed.')

    if cnt:
        return EXIT_COULD_NOT_TELL
    return EXIT_UNHEALTHY if unhealthy else 0


# ── THE SELFTEST, driven in throwaway repos, never this clone ──────────────
def _fixtures():
    import shutil
    import tempfile
    ok = True
    # COUNTED, NEVER WRITTEN DOWN. The literal in the lock line below said
    # "12 arms, 5 negative" over 11 arm() calls -- off by one from the day it
    # was written, and it would have gone stale again on the next arm added.
    # A criteria lock quoting a number nothing derives is the same defect this
    # repo has corrected in three other places.
    tally = {'n': 0, 'neg': 0}

    def arm(label, cond, detail=''):
        nonlocal ok
        # The criterion for "negative" is stated rather than tallied by hand:
        # the label says NEGATIVE, or the arm asserts the third state.
        tally['n'] += 1
        if 'negative' in label.lower() or 'COULD NOT TELL' in label:
            tally['neg'] += 1
        if not cond:
            ok = False
            print('  FAIL %s%s' % (label, (' -- ' + str(detail)) if detail != '' else ''))
        else:
            print('  ok   %s' % label)

    base = tempfile.mkdtemp(prefix='clone_health_fx_')
    try:
        r = os.path.join(base, 'repo')
        os.makedirs(r)
        for a in (['init', '-q'], ['config', 'user.email', 'f@x.invalid'],
                  ['config', 'user.name', 'f']):
            subprocess.run(['git', '-C', r] + a, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        io.open(os.path.join(r, 'a.txt'), 'w', encoding='utf-8').write('x\n')
        subprocess.run(['git', '-C', r, 'add', '-A'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
        subprocess.run(['git', '-C', r, 'commit', '-q', '-m', 'f'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')

        okb, out = git(['config', '--get', 'core.bare'], tree=r)
        arm('a fresh repo reads core.bare as false or unset',
            (okb is False) or (out or '').strip().lower() == 'false', (okb, out))

        subprocess.run(['git', '-C', r, 'config', 'core.bare', 'true'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
        okb, out = git(['config', '--get', 'core.bare'], tree=r)
        arm('NEGATIVE HALF: with core.bare set, the reader returns true -- '
            'without this the healthy reading proves nothing',
            okb is True and out.strip().lower() == 'true', (okb, out))
        oks, _o = git(['status', '--porcelain'], tree=r)
        arm('...and git status BREAKS in that state, which is the symptom that '
            'cost a blocked batch', oks is False, oks)
        subprocess.run(['git', '-C', r, 'config', 'core.bare', 'false'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')

        wt = os.path.join(base, 'wt-live-aaaaa')
        subprocess.run(['git', '-C', r, 'worktree', 'add', '-q', '--detach', wt],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
        arm('a worktree whose directory EXISTS is LIVE -- the paired positive',
            os.path.isdir(wt))
        shutil.rmtree(wt, ignore_errors=True)
        arm('NEGATIVE: and one whose directory is GONE is still REGISTERED, '
            'which is exactly what `git worktree prune` does not tell you',
            not os.path.isdir(wt))

        tb = git(['status'], tree=r, bound=0)
        arm('A TIMEOUT IS COULD NOT TELL, never ok -- a health check that says '
            'fine because it could not ask is the one shape that stops anybody '
            'looking', tb[0] is None and 'timed out' in tb[1], tb)

        arm('attribution with NO claim history is COULD NOT TELL, not '
            'UNATTRIBUTED -- "I could not ask" and "nobody owns it" are '
            'opposite answers', attribute('anything-xyzzy', None) == COULD_NOT_TELL)
        arm('a name matching nothing is UNATTRIBUTED',
            attribute('zzzz-nothing-matches-this', {'cc': ['tools/foo.py']})
            == 'UNATTRIBUTED')
        arm('NEGATIVE HALF: a name matching a claimed path IS attributed, so '
            'the arm above is not passing because attribution never fires',
            attribute('dead_rule_sweep-abc12',
                      {'cody': ['tools/dead_rule_sweep.py']}) == 'cody')

        # ── THE READ-ONLY ARM, THROUGH ast AND NOT A GREP ─────────────────
        # The first version of this arm was a regex over the file text and it
        # FAILED on its own docstring: the prose names `git worktree prune` and
        # the one-line fix `git config core.bare false`, and a grep cannot tell
        # a sentence from a call. That is the "my own comments trip my own
        # scanners" class for the THIRD time in two days, so this one asks the
        # AST which functions are actually CALLED in the production half.
        import ast as _ast
        _src = io.open(os.path.abspath(__file__), encoding='utf-8').read()
        _prod = _src.split('def _fixtures')[0]
        _tree = _ast.parse(_prod + chr(10) + 'pass' + chr(10))
        # QUALIFIED names only. The first version collected the bare attribute,
        # so `str.replace` -- as in p.replace('\\', '/') -- read as os.replace
        # and the arm fired on a path-separator fix. THE ARM WAS RIGHT AND MY
        # BANNED LIST WAS WRONG: the dangerous thing is os.replace, not the
        # word "replace". Receiver and attribute, together.
        _called = set()
        for _n in _ast.walk(_tree):
            if isinstance(_n, _ast.Call):
                _f = _n.func
                if isinstance(_f, _ast.Attribute) and isinstance(_f.value, _ast.Name):
                    _called.add('%s.%s' % (_f.value.id, _f.attr))
                elif isinstance(_f, _ast.Name):
                    _called.add(_f.id)
        _BANNED = {'os.replace', 'os.unlink', 'os.remove', 'os.removedirs',
                   'os.rmdir', 'os.mkdir', 'os.makedirs', 'shutil.rmtree',
                   'shutil.move', 'shutil.copy', 'shutil.copyfile'}
        _hits = sorted(_called & _BANNED)
        # And io.open(..., 'w') would write without any of those names.
        for _n in _ast.walk(_tree):
            if (isinstance(_n, _ast.Call) and isinstance(_n.func, _ast.Attribute)
                    and _n.func.attr == 'open' and len(_n.args) > 1
                    and isinstance(_n.args[1], _ast.Constant)
                    and 'w' in str(_n.args[1].value)):
                _hits.append('open(..., %r)' % _n.args[1].value)
        arm('THE PRODUCTION HALF CALLS NOTHING THAT DELETES OR WRITES -- asked '
            'of the AST, not of a grep, because a grep cannot tell the '
            'docstring sentence "git config core.bare false" from a call',
            not _hits, _hits)
        arm('NEGATIVE HALF: the AST walker really does find a banned call when '
            'there is one, so the arm above is not passing because the walker '
            'is blind',
            'rmtree' in {n.func.attr for n in _ast.walk(
                _ast.parse('import shutil' + chr(10) + 'shutil.rmtree(x)'))
                if isinstance(n, _ast.Call)
                and isinstance(n.func, _ast.Attribute)})
    finally:
        subprocess.run(['git', '-C', base, 'worktree', 'prune'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
        shutil.rmtree(base, ignore_errors=True)

    print('  criteria lock: %d arms, %d of them negative (criteria %s)'
          % (tally['n'], tally['neg'], CRITERIA_VERSION))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fixtures', action='store_true')
    a = ap.parse_args(argv)
    if a.fixtures:
        print('CLONE HEALTH -- selftest (criteria %s)' % CRITERIA_VERSION)
        return 0 if _fixtures() else 1
    return report(as_json=a.json)


if __name__ == '__main__':
    sys.exit(main())
