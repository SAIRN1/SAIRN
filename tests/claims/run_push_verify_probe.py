"""tests/claims/run_push_verify_probe.py

Run:  python tests/claims/run_push_verify_probe.py

Holds the 2026-09-04 fixes to the claim system:

  * sairn_claim.py -- a claim that does not reach origin/main must never be
    reported as CLAIMED (sections 1-5, 7);
  * neither sairn_claim.py NOR tools/sairn_claim_hook.py may write the working
    tree or the index while reading claims (sections 6 and 8).

Section 8 was added after the first pass fixed the library and left the HOOK
untouched -- and the hook is the copy that runs unattended at every session
start, so the defect was still firing everywhere while the probe read green.

── THE DEFECT ────────────────────────────────────────────────────────────────
save_mine() printed a failure line and returned None, and both callers printed
"CLAIMED." regardless. So a push that failed with a non-fast-forward -- the
ORDINARY case when two of the four clones claim within the same few seconds --
left the claim committed locally and INVISIBLE to every other clone, while the
tool said it was claimed.

That is the exact collision this tool exists to prevent, happening inside the
tool. It was reproduced live: "error: failed to push some refs" immediately
followed by "CLAIMED." Same false-success shape as a deploy watcher that
swallows a 403 -- the expensive part is not the error, it is the confident line
printed after it.

── WHY A REAL GIT REPO AND NOT A MOCK ────────────────────────────────────────
The whole fix is about what git actually does: whether a rebase resolves a
non-fast-forward, and whether the commit is genuinely an ancestor of
origin/main afterwards. A stubbed subprocess would assert that the code calls
the commands it calls, which is not the question. These build a real bare
remote and real clones on disk; no network is involved.

The probe is self-contained and leaves nothing behind.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, 'tools', 'sairn_claim.py')
HOOK = os.path.join(ROOT, 'tools', 'sairn_claim_hook.py')

passed = 0
failed = 0


def check(name, cond, detail=''):
    global passed, failed
    if cond:
        print('  ok   ' + name)
        passed += 1
    else:
        print('  FAIL ' + name + (('\n       ' + detail) if detail else ''))
        failed += 1


def git(cwd, *args, **kw):
    r = subprocess.run(('git',) + args, cwd=cwd, capture_output=True, text=True)
    if kw.get('check', True) and r.returncode != 0:
        raise RuntimeError('git %s failed in %s:\n%s' % (' '.join(args), cwd, r.stderr))
    return r


def run_tool(clone, *args):
    r = subprocess.run([sys.executable, os.path.join(clone, 'tools', 'sairn_claim.py')] + list(args),
                       cwd=clone, capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def build():
    """A bare origin plus one working clone named SAIRN-probe.

    The clone's directory name matters: session_name() derives the session from
    it, exactly as the four real clones are distinguished.
    """
    tmp = tempfile.mkdtemp(prefix='sairn-claim-probe-')
    origin = os.path.join(tmp, 'origin.git')
    seed = os.path.join(tmp, 'seed')
    clone = os.path.join(tmp, 'SAIRN-probe')

    git(tmp, 'init', '--bare', '-b', 'main', origin)
    git(tmp, 'init', '-b', 'main', seed)
    for k, v in (('user.email', 'probe@example.invalid'), ('user.name', 'Probe'),
                 ('commit.gpgsign', 'false')):
        git(seed, 'config', k, v)
    os.makedirs(os.path.join(seed, '.claude', 'claims'))
    with open(os.path.join(seed, '.claude', 'claims', 'README.md'), 'w') as f:
        f.write('probe\n')
    git(seed, 'add', '-A')
    git(seed, 'commit', '-q', '-m', 'seed')
    git(seed, 'remote', 'add', 'origin', origin)
    git(seed, 'push', '-q', 'origin', 'main')

    git(tmp, 'clone', '-q', origin, clone)
    for k, v in (('user.email', 'probe@example.invalid'), ('user.name', 'Probe'),
                 ('commit.gpgsign', 'false')):
        git(clone, 'config', k, v)
    os.makedirs(os.path.join(clone, 'tools'), exist_ok=True)
    shutil.copy(TOOL, os.path.join(clone, 'tools', 'sairn_claim.py'))
    return tmp, origin, seed, clone


def claims_on_origin(clone, session):
    """Read the session's claim file as it exists on origin/main -- the only
    view that matters, because it is the one other clones will fetch."""
    git(clone, 'fetch', 'origin')
    r = git(clone, 'show', 'origin/main:.claude/claims/%s.json' % session, check=False)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def main():
    print('sairn_claim.py -- a claim that did not reach origin is NOT a claim\n')
    tmp, origin, seed, clone = build()
    try:
        # ── 1. the happy path still works, and is verified against the remote ──
        rc, out = run_tool(clone, 'claim', 'probesubject', 'first claim')
        check('a normal claim exits 0 and says CLAIMED', rc == 0 and 'CLAIMED.' in out,
              'rc=%s out=%s' % (rc, out))
        check('...and says it VERIFIED the push, not merely that it pushed',
              'verified on origin/main' in out, out)
        doc = claims_on_origin(clone, 'probe')
        check('...and the claim really is on origin/main',
              doc is not None and any(c['subject'] == 'probesubject' for c in doc['claims']),
              str(doc))

        # ── 2. the ordinary race: origin moved between fetch and push ──────────
        # Another clone pushed its own commit. The first push is a
        # non-fast-forward; the retry must rebase and land it, because one-file-
        # per-session means there is nothing to conflict over.
        # The seed clone is itself behind now (the tool just pushed a claim
        # through the other clone), so it catches up first -- the same thing a
        # real second session does before it commits.
        git(seed, 'pull', '--rebase', '-q', 'origin', 'main')
        with open(os.path.join(seed, 'other.txt'), 'w') as f:
            f.write('another session pushed\n')
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'another session')
        git(seed, 'push', '-q', 'origin', 'main')
        # The clone is now behind and does not know it -- exactly the state a
        # session is in when it claims a few seconds after another one.
        rc, out = run_tool(clone, 'claim', 'racesubject', 'claimed into a race')
        check('a claim raced by another push still lands, and exits 0', rc == 0,
              'rc=%s out=%s' % (rc, out))
        doc = claims_on_origin(clone, 'probe')
        check('...and the raced claim is on origin/main',
              doc is not None and any(c['subject'] == 'racesubject' for c in doc['claims']),
              str(doc))
        check('...and the other session\'s commit was not lost',
              git(clone, 'cat-file', '-e', 'origin/main:other.txt', check=False).returncode == 0)

        # ── 3. a push that CANNOT succeed must not print CLAIMED ───────────────
        git(clone, 'remote', 'set-url', 'origin',
            os.path.join(tmp, 'no-such-remote.git'))
        rc, out = run_tool(clone, 'claim', 'doomedsubject', 'push cannot succeed')
        check('an unpushable claim exits NON-ZERO', rc != 0, 'rc=%s' % rc)
        check('...and never prints CLAIMED', 'CLAIMED.' not in out.replace('NOT CLAIMED', ''),
              out)
        check('...and says NOT CLAIMED in those words', 'NOT CLAIMED' in out, out)
        check('...and says the work still reads as unclaimed to everyone else',
              'still sees this work as unclaimed' in out, out)
        check('...and does not leave the repo mid-rebase',
              not os.path.exists(os.path.join(clone, '.git', 'rebase-merge')) and
              not os.path.exists(os.path.join(clone, '.git', 'rebase-apply')))

        # ── 4. release reports honestly too ───────────────────────────────────
        rc, out = run_tool(clone, 'release', 'probesubject')
        check('an unpushable release exits NON-ZERO', rc != 0, 'rc=%s' % rc)
        check('...and says NOT RELEASED rather than staying silent',
              'NOT RELEASED' in out, out)

        # ── 5. and recovers once the remote is reachable again ────────────────
        git(clone, 'remote', 'set-url', 'origin', origin)
        rc, out = run_tool(clone, 'release', 'probesubject')
        check('a release lands once the remote is back, and exits 0', rc == 0,
              'rc=%s out=%s' % (rc, out))
        doc = claims_on_origin(clone, 'probe')
        released = [c for c in (doc or {}).get('claims', [])
                    if c['subject'] == 'probesubject']
        check('...and origin/main shows it released',
              bool(released) and released[0]['status'] == 'released', str(released))

        # ── 6. check and list must not touch the working tree ─────────────────
        # CLAUDE.md documents half of this: `git checkout origin/main --
        # .claude/claims` DESTROYS a hand-written claim that has not been
        # committed, from a command that sounds read-only. The other half is
        # that it also STAGES what it wrote, leaving a staged revert of a claim
        # this clone had already committed -- observed in the real repo on
        # 2026-09-04.
        handwritten = os.path.join(clone, '.claude', 'claims', 'handwritten.json')
        payload = {'session': 'handwritten', 'claims': [
            {'id': 'handwritten-1', 'session': 'handwritten', 'subject': 'byhand',
             'task': 'written by hand and not yet committed',
             'claimed_at': '2026-09-04T00:00:00Z', 'claimed_at_epoch': 9e9,
             'status': 'active', 'released_at': None}]}
        with open(handwritten, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
        for cmd in (('list',), ('check', 'somethingelse', 'unrelated work')):
            run_tool(clone, *cmd)
            check('`%s` leaves an uncommitted hand-written claim on disk' % cmd[0],
                  os.path.exists(handwritten), 'it was deleted by ' + cmd[0])
            staged = git(clone, 'diff', '--cached', '--name-only', check=False).stdout.strip()
            check('`%s` stages nothing' % cmd[0], staged == '',
                  'staged: ' + staged)
        dirty = [l for l in git(clone, 'status', '--porcelain=v1', check=False)
                 .stdout.split('\n') if l.strip() and not l.startswith('?? tools/')]
        # `?? tools/` is this harness's own copy of the script, never committed.
        check('...and nothing else in the tree was modified or staged',
              dirty == ['?? .claude/claims/handwritten.json'], str(dirty))
        os.remove(handwritten)

        # ── 7. the guard is load-bearing, not decorative ──────────────────────
        # If save_mine() ever goes back to returning None, `if not ok` fires on
        # every call and the happy path breaks loudly rather than silently --
        # but a version that returns True unconditionally would pass everything
        # above. This asserts the verification step exists by name.
        src = open(TOOL, encoding='utf-8').read()
        check('save_mine verifies against origin rather than trusting the exit code',
              re.search(r'def on_origin\(', src) and 'merge-base' in src and
              "'--is-ancestor'" in src, 'on_origin/merge-base not found')
        check('cmd_claim acts on the result instead of printing regardless',
              re.search(r'ok\s*=\s*save_mine\(', src) and 'NOT CLAIMED' in src)

        # ── 8. THE HOOK, which is the copy that actually runs every time ──────
        # Section 6 covers sairn_claim.py. On 2026-09-04 that fix was applied
        # there and NOT to tools/sairn_claim_hook.py, which is registered as a
        # SessionStart hook and therefore runs automatically at EVERY session
        # start -- so the destructive `git checkout origin/main --
        # .claude/claims` was still firing on every session in every clone,
        # while the probe and CLAUDE.md both read as if the defect were closed.
        # Caught only because a plain `git status` at session start showed
        # `M .claude/claims/hank.json` staged, which nobody had staged.
        #
        # The lesson generalises past this tool: a fix verified on the copy a
        # human invokes, when a second copy runs unattended, is not verified.
        # These assertions therefore run the HOOK BINARY, not the library.
        os.makedirs(os.path.join(clone, 'tools'), exist_ok=True)
        shutil.copy(HOOK, os.path.join(clone, 'tools', 'sairn_claim_hook.py'))

        # Another session's claim, pushed to origin and never pulled by this
        # clone. Only a hook that really reads origin/main can see it.
        git(seed, 'pull', '--rebase', '-q', 'origin', 'main')
        with open(os.path.join(seed, '.claude', 'claims', 'otherclone.json'),
                  'w', encoding='utf-8') as f:
            json.dump({'session': 'otherclone', 'claims': [
                {'id': 'otherclone-1', 'session': 'otherclone',
                 'subject': 'somethingelse', 'task': 'work only origin knows about',
                 'claimed_at': '2026-09-04T00:00:00Z',
                 'claimed_at_epoch': time.time() - 600,
                 'status': 'active', 'released_at': None}]}, f)
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'another clone claims something')
        git(seed, 'push', '-q', 'origin', 'main')

        # ...and a claim this clone wrote by hand and has NOT committed. It must
        # survive the hook, and it must not be mistaken for a fact on origin.
        with open(handwritten, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
        before = open(handwritten, encoding='utf-8').read()

        # ...and an UNCOMMITTED EDIT to a file that DOES exist on origin. This
        # is the destruction case, and the one a new file does not cover:
        # `git checkout <ref> -- path` only writes paths present in the ref, so
        # a brand-new local file survives it while an edit to a tracked one is
        # silently replaced by origin's copy. That is precisely what happened to
        # .claude/claims/hank.json in SAIRN-fourth on 2026-09-04.
        mine = os.path.join(clone, '.claude', 'claims', 'probe.json')
        minedoc = json.load(open(mine, encoding='utf-8'))
        minedoc['claims'].append(
            {'id': 'probe-uncommitted', 'session': 'probe',
             'subject': 'notyetpushed', 'task': 'edited locally, not committed',
             'claimed_at': '2026-09-04T00:00:00Z',
             'claimed_at_epoch': time.time(),
             'status': 'active', 'released_at': None})
        with open(mine, 'w', encoding='utf-8') as f:
            json.dump(minedoc, f)
        mine_before = open(mine, encoding='utf-8').read()

        r = subprocess.run([sys.executable,
                            os.path.join(clone, 'tools', 'sairn_claim_hook.py')],
                           cwd=clone, capture_output=True, text=True)
        check('the hook exits 0', r.returncode == 0, r.stderr)
        try:
            ctx = json.loads(r.stdout)['hookSpecificOutput']['additionalContext']
        except (ValueError, KeyError):
            ctx = ''
            check('the hook emits parseable SessionStart output', False, r.stdout)
        else:
            check('the hook emits parseable SessionStart output', True)

        check('the hook reports a claim that exists ONLY on origin/main',
              'otherclone' in ctx and 'work only origin knows about' in ctx, ctx)
        check('...without claiming the fetch failed', 'MAY BE INCOMPLETE' not in ctx, ctx)
        check('...and does not report an uncommitted local file as a real claim',
              'byhand' not in ctx, ctx)

        check('the hook leaves an uncommitted hand-written claim on disk',
              os.path.exists(handwritten), 'the hook deleted it')
        check('...byte-identical',
              os.path.exists(handwritten) and
              open(handwritten, encoding='utf-8').read() == before,
              'the hook overwrote it')
        check('the hook leaves an UNCOMMITTED EDIT to a tracked claim file intact',
              open(mine, encoding='utf-8').read() == mine_before,
              'the hook replaced it with origin\'s copy -- the real 2026-09-04 damage')
        staged = git(clone, 'diff', '--cached', '--name-only', check=False).stdout.strip()
        check('the hook stages nothing', staged == '', 'staged: ' + staged)
        dirty = sorted(l for l in git(clone, 'status', '--porcelain=v1', check=False)
                       .stdout.split('\n') if l.strip() and not l.startswith('?? tools/'))
        check('...and modifies nothing else in the tree',
              dirty == [' M .claude/claims/probe.json',
                        '?? .claude/claims/handwritten.json'], str(dirty))
        os.remove(handwritten)
        git(clone, 'checkout', '--', '.claude/claims/probe.json')

        # A source assertion as well, because every check above would still pass
        # if the hook read origin correctly AND ALSO ran a checkout afterwards.
        hooksrc = open(HOOK, encoding='utf-8').read()
        executed = re.findall(r"\[\s*'git'\s*,\s*'([a-z-]+)'", hooksrc)
        check('the hook never executes `git checkout`', 'checkout' not in executed,
              'git commands executed: %s' % sorted(set(executed)))
        check('...and reads origin/main with `git show`', 'show' in executed,
              'git commands executed: %s' % sorted(set(executed)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n%d passed, %d failed' % (passed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
