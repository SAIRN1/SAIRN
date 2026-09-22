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
# REQUIREMENT: a claim that does not reach origin/main is never reported as
#   CLAIMED, and neither sairn_claim.py nor its session-start hook may write
#   the working tree while reading claims -- a claim invisible to the other
#   clones is the exact collision the claim system exists to prevent
#

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# SAIRN_CLAIM_TOOL points this probe at a MUTATED COPY of the tool.
# tests/claims/run_claim_retype_mutation_control.py uses it to prove the
# section-11 arms actually go red when the guard is removed -- the platform
# measured on 2026-09-13 that 23 of 39 negative controls never verify their own
# sabotage applied, so a control that cannot be shown to fail is not evidence.
# Defaults to the shipped tool, so an ordinary run is unchanged.
TOOL = os.environ.get('SAIRN_CLAIM_TOOL') or os.path.join(ROOT, 'tools', 'sairn_claim.py')
HOOK = os.path.join(ROOT, 'tools', 'sairn_claim_hook.py')

LOCAL_IMPORT_RE = re.compile(
    r'(?m)^\s*(?:import\s+([a-z_][a-z0-9_]*)|from\s+([a-z_][a-z0-9_]*)\s+import)')


def local_deps(path, seen=None):
    """Every tools/*.py module `path` imports, transitively, as bare names.

    Resolved from the SOURCE rather than kept as a list, because a list is a
    second copy of the import statements and goes stale the first time one is
    added. Only names that exist as `tools/<name>.py` are returned, so stdlib
    and third-party imports fall through untouched.
    """
    seen = set() if seen is None else seen
    try:
        with open(path, encoding='utf-8') as fh:
            src = fh.read()
    except OSError:
        return seen
    for a, b in LOCAL_IMPORT_RE.findall(src):
        name = a or b
        if name in seen:
            continue
        sibling = os.path.join(ROOT, 'tools', name + '.py')
        if os.path.isfile(sibling):
            seen.add(name)
            local_deps(sibling, seen)
    return seen


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
    r = subprocess.run(('git',) + args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if kw.get('check', True) and r.returncode != 0:
        raise RuntimeError('git %s failed in %s:\n%s' % (' '.join(args), cwd, r.stderr))
    return r


def run_tool(clone, *args):
    r = subprocess.run([sys.executable, os.path.join(clone, 'tools', 'sairn_claim.py')] + list(args),
                       cwd=clone, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
    # ── THE TOOL'S OWN SIBLING MODULES, RESOLVED RATHER THAN LISTED ─────────
    # This used to copy `sairn_claim.py` and nothing else. On 2026-09-22 that
    # stopped working silently: `527b31bf` added `import sairn_session_identity`
    # to the tool, the clone still received one file, and EVERY invocation
    # inside it died with ModuleNotFoundError. No claim was ever written, and
    # the failure surfaced 180 lines later as a FileNotFoundError on the claim
    # file the probe expected to read.
    #
    # A HAND-KEPT LIST WOULD BE A SECOND COPY OF THE IMPORT STATEMENTS and
    # would go stale the same way on the next sibling. The deps are read out of
    # the tool's own source, transitively.
    for dep in local_deps(TOOL):
        shutil.copy(os.path.join(ROOT, 'tools', dep + '.py'),
                    os.path.join(clone, 'tools', dep + '.py'))
    # LAST, so a mutated copy passed in via SAIRN_CLAIM_TOOL wins over anything
    # the dependency sweep may have copied under the same name.
    shutil.copy(TOOL, os.path.join(clone, 'tools', 'sairn_claim.py'))
    # ── AND THE CLONE HAS TO BE PROVISIONED ────────────────────────────────
    # The other half of the same 2026-09-22 breakage. `527b31bf` stopped
    # guessing the session name from the folder -- correctly, because a rename
    # had let a clone discharge its own Tier A obligation -- and now reads a
    # per-clone marker in `.git/`. A throwaway clone has no marker, so every
    # invocation raised NoIdentity and wrote nothing.
    #
    # Written directly rather than by shelling out to --provision: this is
    # fixture setup for a probe about claim publishing, and adding a second
    # subprocess whose failure mode is a third thing to diagnose buys nothing.
    with open(os.path.join(clone, '.git', 'sairn-session'), 'w',
              encoding='utf-8') as fh:
        fh.write('probe\n')
    # ── AND THE FIXTURE IS PROVEN TO WORK BEFORE ANYTHING IS ASSERTED ──────
    # local_deps() above closes the recurrence that actually happened -- a new
    # `import` of a tools/*.py sibling -- and it closes it properly, by reading
    # the tool's own source instead of keeping a list. This is the other half,
    # and it is about the SYMPTOM rather than the cause.
    #
    # THE FOUR-DAY LAG WAS NOT CAUSED BY THE MISSING MODULE. It was caused by
    # WHERE THE FAILURE SURFACED: the tool died inside the clone, nothing was
    # written, and the probe carried on for 180 lines before crashing on
    # `json.load` of a claim file that had never been created. A missing .json
    # reads as a fixture quirk; a missing module reads as what it is. One
    # subprocess here turns any such cause into the right message immediately.
    #
    # IT IS DELIBERATELY NOT LIMITED TO IMPORTS. local_deps() cannot see a data
    # file, a third-party package, a new marker in .git/ or an interpreter
    # version -- and this refusal does not need to know which of those it is.
    # `check`, NOT `list`, AND THAT WAS MEASURED RATHER THAN PICKED. In this
    # fixture `list` exits 0 whether or not .git/sairn-session exists -- it
    # never asks who you are -- so a smoke test built on it would have passed
    # through exactly half of the 2026-09-22 breakage and caught only the
    # import. `check` resolves the session to compare against your own claims,
    # so it exercises the identity path, and it is read-only: it writes no
    # claim, stages nothing and needs no network beyond the fetch the fixture
    # already has. Driven both ways in a throwaway clone: list 0/0, check 1/0
    # without and with the marker.
    smoke = subprocess.run(
        [sys.executable, os.path.join('tools', 'sairn_claim.py'),
         'check', 'probesmoke', 'fixture smoke test, writes nothing'],
        cwd=clone, capture_output=True, text=True, encoding='utf-8',
        errors='replace')
    if smoke.returncode != 0:
        raise SystemExit(
            'COULD NOT RUN -- sairn_claim.py does not execute inside this '
            "probe's own fixture, so no arm below would mean anything:\n"
            + ((smoke.stdout or '') + (smoke.stderr or '')).strip()[-600:]
            + '\n\nbuild() is missing something the tool now needs. A tools/*.py '
              'import is resolved automatically by local_deps(); anything else '
              '-- a data file, a third-party package, a new marker in .git/ -- '
              'has to be added there by hand.')
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
                           cwd=clone, capture_output=True, text=True, encoding='utf-8', errors='replace')
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

        # ── 9. A RE-RUN AFTER A FAILED PUSH IS A RETRY, NOT A SECOND CLAIM ───
        # Added 2026-09-14. Section 1-5 fixed the tool LYING about a claim that
        # did not land. What it did not fix is what the operator does next: the
        # failure message says to re-run, each re-run APPENDED another entry,
        # and whatever pushed later published all of them. Six unreleased claims
        # appeared in the real record, three identical from `fourth` 30-45s
        # apart and three from `cc` 13-29s apart the same hour -- two sessions,
        # same shape, neither a loop.
        #
        # The trigger is reproduced here rather than described: ONE unstaged
        # file makes `git rebase origin/main` exit 1 outright, so no push is
        # ever attempted and all three attempts fail identically.
        print('\n9. a failed push, then a re-run -- one entry, not two')
        git(clone, 'checkout', '--', '.claude/claims/probe.json', check=False)
        # Make the push impossible in the way it really failed: an unstaged
        # change to a TRACKED file. tools/sairn_claim.py is untracked in this
        # clone (build() copies it in), and an untracked file does NOT block a
        # rebase -- using it here would have made the whole section vacuous.
        DIRTY = os.path.join(clone, '.claude', 'claims', 'README.md')
        with open(DIRTY, 'a', encoding='utf-8') as f:
            f.write('probe: an unstaged change, which is what blocks rebase\n')
        dirty_now = git(clone, 'status', '--porcelain', '--untracked-files=no',
                        check=False).stdout.strip()
        check('the reproduction really did dirty a TRACKED file -- otherwise 9 '
              'proves nothing', dirty_now != '',
              'tree is clean; the rest of section 9 is vacuous')

        rc1, out1 = run_tool(clone, 'claim', 'probe', 'retry arm task')
        check('a claim that cannot be pushed exits 3', rc1 == 3, out1[-400:])
        check('...and says NOT CLAIMED rather than CLAIMED',
              'NOT CLAIMED' in out1, out1[-400:])
        check('...and NAMES THE DIRTY TREE as the cause, not just "push it yourself"',
              'WORKING TREE IS DIRTY' in out1, out1[-600:])
        check('...and tells the operator re-running is safe',
              'no second entry' in out1 or 'RETRY' in out1, out1[-600:])

        def entries(task):
            p = os.path.join(clone, '.claude', 'claims', 'probe.json')
            with open(p, encoding='utf-8') as f:
                return [c for c in json.load(f)['claims'] if c.get('task') == task]

        check('the entry IS written locally -- which is exactly why a re-run must '
              'not add another', len(entries('retry arm task')) == 1,
              str(len(entries('retry arm task'))))

        rc2, out2 = run_tool(clone, 'claim', 'probe', 'retry arm task')
        check('the re-run is recognised as a retry',
              'ALREADY CLAIMED BY THIS SESSION' in out2, out2[-400:])
        check('...and adds NO second entry -- the defect this arm exists for',
              len(entries('retry arm task')) == 1,
              'entries: %d' % len(entries('retry arm task')))
        check('...and still exits non-zero while it is unpublished', rc2 == 3,
              'rc=%s\n%s' % (rc2, out2[-300:]))

        # Now clear the real obstacle and re-run once more: the entry already
        # written must be PUBLISHED, still without a second entry.
        git(clone, 'checkout', '--', '.claude/claims/README.md')
        rc3, out3 = run_tool(clone, 'claim', 'probe', 'retry arm task')
        check('once the tree is clean the retry publishes the earlier entry',
              rc3 == 0, 'rc=%s\n%s' % (rc3, out3[-400:]))
        origin_doc = claims_on_origin(clone, 'probe') or {'claims': []}
        landed = [c for c in origin_doc['claims'] if c.get('task') == 'retry arm task']
        check('...and origin/main carries exactly ONE claim for that task',
              len(landed) == 1, 'on origin: %d' % len(landed))
        check('...and it is active', landed and landed[0].get('status') == 'active',
              str(landed))

        # ── 10. "nothing to commit" is not "nothing to publish" ──────────────
        # save_mine()'s early return said "Nothing to publish, so nothing can be
        # invisible". False in the one case that matters: an earlier run wrote
        # this exact file, committed it, and its push failed -- the local file
        # then matches, the early return fired, and the caller printed CLAIMED
        # over a commit no other clone could see.
        # save_mine() IS DRIVEN DIRECTLY HERE, and the reason is a failure this
        # arm had on its first version. Written as a `claim` re-run, it passed
        # with the fix SABOTAGED -- because the section-9 idempotency guard
        # catches that case first and save_mine's early return is never reached.
        # A passing arm that never enters the branch it names is worth less than
        # no arm. The branch is genuinely live: cmd_release() calls save_mine too.
        print('\n10. an unpushed commit is republished, not reported clean')
        rc4, out4 = run_tool(clone, 'claim', 'probe', 'unpushed arm task')
        check('a normal claim lands first', rc4 == 0, out4[-300:])

        head = git(clone, 'rev-parse', 'HEAD').stdout.strip()
        git(clone, 'push', '-q', '--force', 'origin', 'HEAD~1:main')
        git(clone, 'fetch', 'origin')
        check('the rewind really unpublished it -- otherwise arm 10 is vacuous',
              git(clone, 'merge-base', '--is-ancestor', head, 'origin/main',
                  check=False).returncode != 0, 'still an ancestor')

        # Import the clone's own copy so REPO/CLAIM_DIR resolve to the probe
        # tree, and call save_mine with the doc exactly as it is on disk: no
        # change to commit, but a commit sitting here unpublished.
        drive = (
            'import sys, json, io, os\n'
            'sys.path.insert(0, %r)\n'
            'import sairn_claim as S\n'
            'doc = S.load_mine()\n'
            'print("SAVE_MINE_RETURNED", S.save_mine(doc, "chore(claims): probe no-op", True))\n'
        ) % os.path.join(clone, 'tools')
        r = subprocess.run([sys.executable, '-c', drive], cwd=clone,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        out5 = (r.stdout or '') + (r.stderr or '')
        check('save_mine really took its no-change path -- otherwise this is a '
              'different test', '(no change to commit)' in out5, out5[-400:])
        check('...and it does NOT report success over an unpublished commit',
              'SAVE_MINE_RETURNED True' in out5 and 'not on origin/main' in out5,
              out5[-500:])
        check('...it republishes instead',
              git(clone, 'merge-base', '--is-ancestor', head, 'origin/main',
                  check=False).returncode == 0
              if 'SAVE_MINE_RETURNED True' in out5 else False,
              out5[-500:])
        check('...and origin/main carries the claim again',
              any(c.get('task') == 'unpushed arm task'
                  for c in (claims_on_origin(clone, 'probe') or {'claims': []})['claims']),
              out5[-400:])

        # ── 11. A RETYPED TASK STRING IS STILL A RETRY ───────────────────────
        # Section 9 drives the retry with the SAME string, and the guard it
        # covers compares `task` byte for byte. befb65e3's own commit message
        # says the real incident was not byte-identical: "cc has three for item
        # 92 ... with the task string slightly retyped between attempts". So
        # the case the fix was written from is the one section 9 does not
        # exercise, and driving it against the tool as shipped produced TWO
        # published claims from three attempts -- half the defect, still open.
        #
        # THE TWO STRINGS BELOW ARE THE REAL ONES from .claude/claims/cc.json's
        # history (9baec9be, then 7bec5124 and 6f7cb9d3), not invented
        # near-misses. A person retyping after a reported failure is the ONLY
        # way this state is reached: a machine repeats the string exactly.
        print('\n11. a RETYPED task string after a failed push -- still one entry')
        git(clone, 'checkout', '--', '.claude/claims/probe.json', check=False)
        A = ('item 92 functional core imperative shell on sbThreeWayMatch '
             'and ledger')
        B = ('item 92 functional core imperative shell sbThreeWayMatch and '
             'ledger money rule')
        DIRTY2 = os.path.join(clone, '.claude', 'claims', 'README.md')
        with open(DIRTY2, 'a', encoding='utf-8') as f:
            f.write('probe 11: an unstaged change, which is what blocks rebase\n')
        check('the reproduction really did dirty a TRACKED file -- otherwise 11 '
              'proves nothing',
              git(clone, 'status', '--porcelain', '--untracked-files=no',
                  check=False).stdout.strip() != '',
              'tree is clean; the rest of section 11 is vacuous')

        rcA, outA = run_tool(clone, 'claim', 'probe11', A)
        check('the first attempt fails to publish, as it must for this to be the '
              'retype case at all', rcA == 3, outA[-300:])

        def active11():
            p = os.path.join(clone, '.claude', 'claims', 'probe.json')
            with open(p, encoding='utf-8') as f:
                return [c for c in json.load(f)['claims']
                        if c.get('status') == 'active'
                        and c.get('subject') == 'probe11']

        check('...and the entry IS written locally', len(active11()) == 1,
              str(active11()))

        rcB, outB = run_tool(clone, 'claim', 'probe11', B)
        check('a RETYPED task on the same subject is refused, not appended',
              'UNPUBLISHED CLAIM' in outB, outB[-700:])
        check('...and adds NO second entry -- the half befb65e3 left open',
              len(active11()) == 1, 'entries: %d' % len(active11()))
        check('...and exits non-zero', rcB == 3, 'rc=%s' % rcB)
        # THE REFUSAL MUST BE ACTIONABLE. A refusal a person cannot act on is
        # one they route around, and routing around this one means editing the
        # claim file by hand.
        check('...and prints BOTH strings, so the operator can tell which is which',
              A in outB and B in outB, outB[-700:])
        # ANCHORED ON THE LABELLED LINE, not merely on the string appearing
        # somewhere. The first version of this arm checked `A in outB`, and the
        # mutation control showed that passes with the "already here" line
        # DELETED -- because A also appears in the re-run command below it. An
        # arm that a sabotage survives is worth less than no arm.
        check('...and labels which one is already on file, on its own line',
              ('already here (unpublished): ' + A) in outB, outB[-700:])
        check('...and says when it was claimed, so an operator can tell a retry '
              'from something they typed an hour ago',
              'claimed at' in outB, outB[-700:])
        check('...and names the exact command that publishes the earlier entry',
              ('claim probe11 ' + A) in outB, outB[-700:])


        git(clone, 'checkout', '--', '.claude/claims/README.md')
        rcC, outC = run_tool(clone, 'claim', 'probe11', A)
        check('re-running the EARLIER wording on a clean tree publishes it',
              rcC == 0, outC[-400:])
        pub11 = [c for c in (claims_on_origin(clone, 'probe') or {'claims': []})['claims']
                 if c.get('status') == 'active' and c.get('subject') == 'probe11']
        check('...and origin/main carries exactly ONE claim for that subject',
              len(pub11) == 1, str(pub11))

        # CONTROL, and it is the arm that keeps this from being a blanket block.
        # Once the earlier claim is PUBLISHED the failed-push state cannot
        # apply, and a second claim on the same subject is ordinary work. An
        # over-tight guard here would be worse than the defect: it would make
        # the tool refuse real claims, and a gate that must be talked past
        # routinely is one people learn to talk past.
        rcD, outD = run_tool(clone, 'claim', 'probe11',
                             'a genuinely different second piece of work')
        check('CONTROL: once the first is published, a DIFFERENT second claim on '
              'the same subject is allowed', rcD == 0, outD[-400:])
        pub11b = [c for c in (claims_on_origin(clone, 'probe') or {'claims': []})['claims']
                  if c.get('status') == 'active' and c.get('subject') == 'probe11']
        check('...and origin/main now carries two, which is correct',
              len(pub11b) == 2, str(len(pub11b)))

        # ── THE THIRD STATE: origin's copy cannot be read at all ─────────────
        # published_claim_ids() returns None there, and "could not tell" must
        # never be folded into "published" (PR 1.11). Fail CLOSED: an origin
        # nothing can be read from is also an origin nothing can be published
        # to, so refusing costs nothing that was going to work anyway -- while
        # failing OPEN appends the duplicate this whole section exists to stop.
        #
        # STAGED BY BREAKING THE BLOB ON ORIGIN, not by deleting a ref: the
        # tool fetches before it reaches this guard, and a fetch would put a
        # deleted remote-tracking ref straight back. Invalid JSON survives the
        # fetch, which is what makes the arm deterministic.
        seed_claims = os.path.join(seed, '.claude', 'claims')
        os.makedirs(seed_claims, exist_ok=True)
        git(seed, 'fetch', 'origin')
        git(seed, 'reset', '-q', '--hard', 'origin/main')
        with open(os.path.join(seed_claims, 'probe.json'), 'w', encoding='utf-8') as f:
            f.write('{ this is not json')
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'probe: unreadable claim blob on origin')
        git(seed, 'push', '-q', 'origin', 'main')
        broken = git(clone, 'fetch', 'origin', check=False)
        shown = git(clone, 'show', 'origin/main:.claude/claims/probe.json',
                    check=False).stdout
        check('the reproduction really did make origin\'s copy unparseable -- '
              'otherwise this arm proves nothing',
              broken.returncode == 0 and 'not json' in shown,
              'fetch rc=%s blob=%r' % (broken.returncode, shown[:80]))

        with open(DIRTY2, 'a', encoding='utf-8') as f:
            f.write('probe 11: dirty again for the unreadable-origin arm\n')
        rcE, outE = run_tool(clone, 'claim', 'probe11',
                             'a third wording while origin is unreadable')
        check('with origin UNREADABLE the guard still REFUSES -- fail closed, '
              'not fail open', 'UNPUBLISHED CLAIM' in outE and rcE == 3,
              outE[-700:])
        check('...and still adds no entry',
              len([c for c in active11()
                   if c.get('task') == 'a third wording while origin is unreadable']) == 0,
              str(active11()))
        git(clone, 'checkout', '--', '.claude/claims/README.md', check=False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n%d passed, %d failed' % (passed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
