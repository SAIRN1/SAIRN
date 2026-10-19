#!/usr/bin/env python
"""hover_scope_prepush_check.py -- a clone-local, additive pre-push check:
reject the push if any file in the range being pushed falls outside a
shared manifest of hover-only paths.

ONE-LINE CONCEPT (written before this code, per b65 methodology): a shared
manifest of hover-allowed path prefixes, read by a local pre-push hook in
EACH hover clone, rejects a push that stages anything outside it -- the
manifest lives outside both clones' git trees so it stays in sync without
either clone's commit history carrying it.

WHY THIS AND NOT A CHANGE TO tools/hover_auditor_scope_gate.py. That gate
is the platform's own tracked, shared enforcement (pre-commit, in
.githooks/, out of this role's edit scope -- it is not under
.claude/skills/sairn-hover-auditor/). This is a SECOND, clone-local,
additive layer: it runs before the real .githooks/pre-push via a
clone-local `core.hooksPath` override (set in .git/config, never tracked,
never shared) and ALWAYS chains to the real hook afterward -- it can only
add a rejection, never remove one. If this script is ever absent or its
manifest unreadable, the WRAPPER (hover_scope_prepush_wrapper.sh) fails
CLOSED -- reject the push -- rather than silently skipping to the real
hook, per this platform's own standing rule that a check depending on an
absent tool must fail closed, not fold into a pass.

Usage (invoked by the wrapper, not normally run by hand):
  python hover_scope_prepush_check.py --range <old>..<new> [--manifest PATH]
  python hover_scope_prepush_check.py --selftest

Exit 0: every changed file matches an allowed prefix.
Exit 1: at least one file does not -- REJECT the push.
Exit 2: could not run (manifest missing/unreadable, bad range) -- also a
        reject at the wrapper level, never treated as a pass.
"""
import json
import os
import subprocess
import sys

DEFAULT_MANIFEST = os.path.join(os.path.expanduser('~'), 'SAIRN-SESSION-LOCKS',
                                 'hover-scope-manifest.json')


class CouldNotRun(Exception):
    pass


def load_manifest(path):
    if not os.path.isfile(path):
        raise CouldNotRun('manifest not found at %s -- FAILING CLOSED, not '
                           'treating a missing manifest as an empty (allow-all) one' % path)
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise CouldNotRun('manifest at %s unreadable/invalid: %s' % (path, e))
    prefixes = data.get('allowed_prefixes')
    if not isinstance(prefixes, list) or not prefixes:
        raise CouldNotRun('manifest at %s has no allowed_prefixes list -- an '
                           'empty list would allow nothing OR everything '
                           'depending on how it is read, so a malformed one '
                           'fails closed instead of guessing' % path)
    return prefixes


def is_allowed(path, prefixes):
    norm = path.replace('\\', '/')
    for p in prefixes:
        pn = p.replace('\\', '/')
        if pn.endswith('/'):
            if norm.startswith(pn):
                return True
        elif norm == pn:
            return True
    return False


def _git_diff(git_range, cwd):
    # stdin=DEVNULL on EVERY subprocess this module spawns, on purpose: this
    # script runs inside a git pre-push hook, which is itself fed ref lines
    # on ITS OWN stdin by git. A child process that inherits that stream
    # (the Python default) can consume or otherwise interfere with it even
    # when the child never explicitly reads from stdin -- hit LIVE while
    # building this hook (b65): a bare `git fetch` with no stdin redirect
    # broke the real downstream hover_auditor_scope_gate.py's own stdin
    # read, "supplied NO ref lines on stdin", purely by being in the
    # process tree. DEVNULL makes that class of interference impossible.
    return subprocess.run(['git', 'diff', '--name-only', git_range],
                           capture_output=True, text=True, cwd=cwd,
                           stdin=subprocess.DEVNULL)


def changed_files(git_range, cwd=None):
    r = _git_diff(git_range, cwd)
    if r.returncode != 0:
        # The live failure mode this clause exists for (b65, hit for real
        # while testing this hook, five sessions pushing to one branch):
        # the ref line's remote_sha is routinely an object this clone has
        # not fetched yet, so the range above does not resolve. ONE fetch,
        # ONE retry -- not a loop, and still fails closed if the retry
        # also fails.
        fetch = subprocess.run(['git', 'fetch', '-q', 'origin'],
                                capture_output=True, text=True, cwd=cwd,
                                stdin=subprocess.DEVNULL)
        r2 = _git_diff(git_range, cwd)
        if r2.returncode != 0:
            raise CouldNotRun(
                'git diff --name-only %s failed even after a fetch retry: '
                '%s (fetch: rc=%s %s)' % (git_range, r2.stderr.strip(),
                                          fetch.returncode, fetch.stderr.strip()[:200]))
        r = r2
    return [l for l in r.stdout.splitlines() if l.strip()]


def check(git_range, manifest_path=None, cwd=None):
    prefixes = load_manifest(manifest_path or DEFAULT_MANIFEST)
    files = changed_files(git_range, cwd=cwd)
    violations = [f for f in files if not is_allowed(f, prefixes)]
    return files, violations


def main(argv):
    manifest_path = None
    git_range = None
    cwd = None
    i = 0
    while i < len(argv):
        if argv[i] == '--manifest' and i + 1 < len(argv):
            manifest_path = argv[i + 1]
            i += 2
        elif argv[i] == '--range' and i + 1 < len(argv):
            git_range = argv[i + 1]
            i += 2
        elif argv[i] == '--cwd' and i + 1 < len(argv):
            cwd = argv[i + 1]
            i += 2
        elif argv[i] == '--selftest':
            return 0 if run_fixtures() else 1
        else:
            i += 1
    if not git_range:
        print('usage: hover_scope_prepush_check.py --range <old>..<new> '
              '[--manifest PATH] [--cwd PATH] | --selftest')
        return 2
    try:
        files, violations = check(git_range, manifest_path, cwd)
    except CouldNotRun as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    if violations:
        print('HOVER SCOPE MANIFEST -- REJECTED. %d of %d changed file(s) '
              'fall outside the hover-only manifest:' % (len(violations), len(files)))
        for v in violations:
            print('  %s' % v)
        return 1
    print('HOVER SCOPE MANIFEST -- OK. %d changed file(s), all within the '
          'hover-only manifest.' % len(files))
    return 0


def run_fixtures():
    import tempfile
    ok = True

    def c(name, got, want):
        nonlocal ok
        p = (got == want)
        ok = ok and p
        print('  %s   %s  got=%r want=%r' % ('ok' if p else 'FAIL', name, got, want))

    prefixes = ['.claude/skills/sairn-hover-auditor/', 'docs/defect-density-register.json']
    c('directory-prefix match', is_allowed('.claude/skills/sairn-hover-auditor/tools/x.py', prefixes), True)
    c('exact-file match', is_allowed('docs/defect-density-register.json', prefixes), True)
    c('an out-of-scope platform file is rejected', is_allowed('api/sd-data.js', prefixes), False)
    c('backslash paths (Windows git diff can emit either) normalise the same way',
      is_allowed('.claude\\skills\\sairn-hover-auditor\\tools\\x.py', prefixes), True)
    c('a similarly-named but different file is NOT a prefix match',
      is_allowed('docs/defect-density-register.json.bak', prefixes), False)

    # KNOWN-BAD CONTROL: missing manifest fails closed (raises, not []).
    raised = False
    try:
        load_manifest(os.path.join(tempfile.mkdtemp(), 'nope.json'))
    except CouldNotRun:
        raised = True
    c('a missing manifest raises CouldNotRun, never silently returns an empty allow-list', raised, True)

    # KNOWN-BAD CONTROL: a manifest with no allowed_prefixes key fails closed too.
    tmp = tempfile.mkdtemp()
    bad = os.path.join(tmp, 'bad.json')
    with open(bad, 'w', encoding='utf-8') as f:
        json.dump({'version': 1}, f)
    raised2 = False
    try:
        load_manifest(bad)
    except CouldNotRun:
        raised2 = True
    c('a manifest missing allowed_prefixes entirely also raises, not an empty list', raised2, True)

    print('%s' % ('ALL OK' if ok else 'SOME FAILED'))
    return ok


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
