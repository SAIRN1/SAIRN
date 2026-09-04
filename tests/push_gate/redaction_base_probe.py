"""Probe the Check 6 defect found and fixed 2026-09-04.

THE DEFECT. git hands a PRE-PUSH hook the sha the REMOTE has right now. That
sha can be a commit this clone has never fetched -- and with four clones
pushing concurrently it is the ORDINARY case, not an edge one: it happens every
time you lose a race. Check 6 ran

    git log --unified=0 -p <that sha>..<tip>

which exits 128 "Invalid revision range" when the base is not in the object
store. The exception handler turned that into

    NOTE: the credential scan could not run (...), so this push is UNCHECKED
    for credentials.

and the push went out scanned by nothing. Observed live on 2026-09-04 and then
read out of `git reflog show origin/main`: the hook was handed 55a408a5 while
this clone's origin/main was still ae89eea5, and 55a408a5 arrived on the NEXT
fetch, after that push.

WHY A PROBE AND NOT A UNIT TEST. Every previous defect in this check was found
by DRIVING it and missed by reasoning about it -- the tip-snapshot version
looked correct until a probe branch deleted the file in a second commit, and
the range-diff version looked correct until the same probe ran again. This one
is the third. So it is driven end to end: a real clone, a real commit carrying
a real credential SHAPE, and the hook invoked exactly as .githooks/pre-push
invokes it, with a real four-field stdin line.

No network, no remote beyond a local path, and nothing is written to the repo
this runs in.

THE CREDENTIAL IS ASSEMBLED AT RUNTIME, never written as a literal, because
tools/redaction_check.py is itself a PreToolUse Write hook -- a probe with a
token literal in its source cannot be saved to disk by an agent.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()

FAIL = []


def check(name, got, want):
    if got == want:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s\n          got:  %r\n          want: %r" % (name, got, want))
        FAIL.append(name)


def ok(name, cond, detail=''):
    check(name, bool(cond), True) if cond else (
        print("  FAIL  %s%s" % (name, ('\n          ' + detail) if detail else '')),
        FAIL.append(name))
    return cond


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True, text=True)


def run_hook(clone, tip_sha, base_sha, hook_src=None):
    """Invoke the gate exactly as .githooks/pre-push does.

    Returns (returncode, stdout, stderr). hook_src, when given, is a path to an
    alternative copy of the hook -- used by the mutation arm to run the OLD
    implementation against the identical scenario.

    THE SCRIPT COMES FROM THE WORKING TREE, THE REPO IT INSPECTS IS THE CLONE.
    Running the clone's own copy would test whatever is COMMITTED, so an
    uncommitted fix reads as still broken and an uncommitted BREAK reads as
    still fixed -- the probe would be measuring the wrong file. The hook
    resolves the repo it works on from cwd, so pointing cwd at the clone is
    enough; redaction_check.py is still loaded from the clone, which is
    identical either way.
    """
    script = hook_src or os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
    stdin = 'refs/heads/main %s refs/heads/main %s\n' % (tip_sha, base_sha)
    env = dict(os.environ)
    env.pop('SAIRN_SEED_GATE', None)
    p = subprocess.run([sys.executable, script, '--pre-push'],
                       cwd=clone, input=stdin, capture_output=True, text=True,
                       env=env, timeout=180)
    return p.returncode, p.stdout, p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix='sairn_redaction_base_')
    clone = os.path.join(tmp, 'clone')
    try:
        # A local clone: real objects, real tools/, real sql/, its own object
        # store, and NO core.hooksPath (git does not clone config), so invoking
        # the gate here cannot recurse into another gate.
        c = subprocess.run(['git', 'clone', '--quiet', '--local', REPO, clone],
                           capture_output=True, text=True)
        if c.returncode != 0:
            print('  SKIP  could not create a local clone: ' + (c.stderr.strip() or '?'))
            return 0
        git(clone, 'config', 'user.email', 'probe@example.invalid')
        git(clone, 'config', 'user.name', 'redaction base probe')

        real_base = git(clone, 'rev-parse', 'origin/main').stdout.strip()
        # A syntactically valid sha that is in no object store anywhere. This is
        # the whole scenario: git names a base this clone does not have.
        unfetched = 'b' * 40
        ok('the unfetched base really is absent from the clone',
           git(clone, 'rev-parse', '--verify', '--quiet', unfetched + '^{commit}').returncode != 0)
        ok('the real base really is present',
           git(clone, 'rev-parse', '--verify', '--quiet', real_base + '^{commit}').returncode == 0)

        # ── the commit under test ──────────────────────────────────────────
        # Assembled, never a literal. Matches VENDOR_PATTERNS' github_token.
        token = 'gh' + 'p_' + ('A' * 36)
        probe_file = os.path.join(clone, 'probe_credential.txt')
        with open(probe_file, 'w', encoding='utf-8') as f:
            f.write('token = "%s"\n' % token)
        git(clone, 'add', 'probe_credential.txt')
        git(clone, 'commit', '--quiet', '-m', 'probe: a credential shape in the outgoing range')
        secret_tip = git(clone, 'rev-parse', 'HEAD').stdout.strip()

        print('\nA. the control: a base this clone HAS, secret in the range')
        rc, out, err = run_hook(clone, secret_tip, real_base)
        ok('the push is BLOCKED', rc == 1, 'rc=%r stderr=%r' % (rc, err[-300:]))
        ok('...naming the pattern kind and the file',
           'github_token' in err and 'probe_credential.txt' in err, err[-300:])
        ok('...and never printing the secret itself', token not in (out + err))

        print('\nB. THE DEFECT: the base git names is not in this clone')
        rc, out, err = run_hook(clone, secret_tip, unfetched)
        ok('the push is STILL BLOCKED', rc == 1, 'rc=%r stdout=%r stderr=%r'
           % (rc, out[-300:], err[-300:]))
        ok('...it did not report itself UNCHECKED', 'UNCHECKED' not in out)
        ok('...and it says which base it fell back to',
           'credential scan used' in out and unfetched[:12] in out, out[-400:])
        ok('...still without printing the secret', token not in (out + err))

        print('\nC. a clean range is allowed, silently')
        git(clone, 'reset', '--quiet', '--hard', 'HEAD~1')
        clean_tip = git(clone, 'rev-parse', 'HEAD').stdout.strip()
        rc, out, err = run_hook(clone, clean_tip, unfetched)
        ok('allowed', rc == 0, 'rc=%r stderr=%r' % (rc, err[-300:]))
        ok('no credential deny text', 'credential-shaped' not in (out + err))

        print('\nD. MUTATION: restore the old base handling and the probe must bite')
        # The exact line the fix replaced. If this arm PASSES the gate, arm B
        # above is decorative.
        src = open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
                   encoding='utf-8').read()
        old = re.sub(
            r"        _tried = \(\[base\] if base else \[\]\).*?"
            r"raise RuntimeError\('no diff base this clone can resolve -- tried ' \+ ', '\.join\(_tried\)\)",
            "        _base = base or 'origin/main'",
            src, flags=re.S)
        if old == src:
            print('  FAIL  the mutation matched nothing -- the fix was renamed or removed')
            FAIL.append('mutation did not apply')
        else:
            broken = os.path.join(tmp, 'old_hook.py')
            with open(broken, 'w', encoding='utf-8') as f:
                f.write(old)
            ok('the mutated hook still parses',
               subprocess.run([sys.executable, '-m', 'py_compile', broken],
                              capture_output=True).returncode == 0)
            git(clone, 'reset', '--quiet', '--hard', secret_tip)
            rc, out, err = run_hook(clone, secret_tip, unfetched, hook_src=broken)
            ok('the OLD code lets the secret through', rc == 0, 'rc=%r' % rc)
            ok('...and says only that it was UNCHECKED', 'UNCHECKED' in out, out[-300:])
            # Same old code, a base it CAN resolve -- proves the mutation broke
            # only the base handling and not the scan itself.
            rc, out, err = run_hook(clone, secret_tip, real_base, hook_src=broken)
            ok('the OLD code still blocks when the base resolves', rc == 1, 'rc=%r' % rc)

        print('\nE. the SIBLING checks were never affected -- checked, not assumed')
        # Checks 1/2/3 read the same `base` through outgoing_files(), which
        # falls through @{u} and origin/main because its git() helper returns ''
        # on a non-zero exit instead of raising. That is correct BY ACCIDENT,
        # and the accident is one edit away from being undone: make git() raise
        # and every check goes silent on a raced push with no message at all --
        # strictly worse than check 6's failure, which at least announced
        # itself. Asserted here so that edit fails loudly.
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import sairn_push_gate_hook as H  # noqa: E402
        files = H.outgoing_files(clone, unfetched, secret_tip)
        ok('outgoing_files() still sees the outgoing file with an unfetched base',
           'probe_credential.txt' in files, repr(files[:5]))
        ok('...and its git() helper returns empty rather than raising on a bad rev',
           H.git(clone, 'log', unfetched + '..HEAD', '--name-only', '--pretty=format:') == '')

        print('\n%d failure(s)' % len(FAIL))
        return 1 if FAIL else 0
    finally:
        # A local clone hardlinks objects into the source repo, so removing it
        # must never be allowed to reach the real .git. shutil.rmtree only ever
        # sees the temp directory, and the clone was made INTO it.
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
