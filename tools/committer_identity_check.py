#!/usr/bin/env python
"""tools/committer_identity_check.py -- is this clone committing as itself?

THIS IS NOT HYPOTHETICAL AND IT RAN FOR THREE DAYS. On 2026-09-13 a sweep of
`git log --format=%an <%ae>` found 131 commits on origin/main authored AND
committed by `probe <probe@local>` -- the throwaway identity the push-gate
probes give their fixture commits. Real feature work was among them, including
an app's entire per-employee auth endpoint, plus claim commits and generated-doc
regenerations. Cause: `user.name`/`user.email` had been written into ONE clone's
LOCAL git config (SAIRN-fourth/.git/config, 2026-09-10) instead of being passed
per-invocation with `git -c`, so every commit that clone made from then on wore
the probe's name.

NOTHING NOTICED. No gate, no hook, no suite reads the committing identity --
verified, not assumed: `grep -n "%an\\|%ae\\|%cn\\|%ce\\|user\\.email\\|user\\.name"
tools/sairn_push_gate_hook.py` returns nothing. Check 8, the one check about
probe residue, keys on the commit SUBJECT matching `^PROBE\\b` and has never read
an identity, so it was not degraded by this and did not catch it either. Those
are two different facts and both matter: the gate was not broken, and the gate
was not looking.

WHAT THIS CHECKS, AND WHAT IT DOES NOT. It checks the identity this clone WILL
commit as -- forward-looking, because that is the half that can still be
prevented. It does NOT fail on the 131 commits already in history: rewriting
published history on a repo four clones share is a far worse risk than the wrong
name on a commit, so those are reported as a number and deliberately left alone.

THE THROWAWAY LIST IS DERIVED, NOT ARGUED. Hardcoding the identities this repo's
probes use would go stale the first time somebody wrote a new probe -- the same
failure the app map and the tooling inventory were both rewritten to stop. The
list is read out of the probe sources themselves.

    python tools/committer_identity_check.py            # exit 1 if compromised
    python tools/committer_identity_check.py --full     # and name the sources
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Both spellings the probes use: the ARGUMENT form `'user.email', 'probe@local'`
# and the `-c` form `user.email=probe@local`.
ARG_RE = re.compile(r"['\"]user\.(?:email|name)['\"]\s*,\s*['\"]([^'\"]+)['\"]")
DASH_C_RE = re.compile(r"['\"]user\.(?:email|name)=([^'\"]+)['\"]")


def probe_identities():
    """Every identity value this repo's own probes hand to git, with its source."""
    found = {}
    for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if not f.endswith(('.py', '.js')):
                continue
            p = os.path.join(root, f)
            try:
                with open(p, encoding='utf-8', errors='replace') as fh:
                    src = fh.read()
            except OSError:
                continue
            rel = os.path.relpath(p, REPO).replace('\\', '/')
            for m in list(ARG_RE.finditer(src)) + list(DASH_C_RE.finditer(src)):
                found.setdefault(m.group(1), set()).add(rel)
    return found


def effective():
    def get(k):
        r = subprocess.run(['git', '-C', REPO, 'config', '--get', k],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        return r.stdout.strip()

    def local(k):
        r = subprocess.run(['git', '-C', REPO, 'config', '--local', '--get', k],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        return r.stdout.strip()
    return get('user.name'), get('user.email'), local('user.name'), local('user.email')


def history_count(values):
    """How many commits on HEAD already carry one of these identities."""
    r = subprocess.run(['git', '-C', REPO, 'log', '--format=%an|%ae|%cn|%ce', 'HEAD'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    n = 0
    for line in r.stdout.splitlines():
        if any(v in line.split('|') for v in values):
            n += 1
    return n


def main(argv):
    full = '--full' in argv
    ids = probe_identities()
    name, email, lname, lemail = effective()

    print('committer identity check')
    print('  this clone commits as : %s <%s>' % (name or '<unset>', email or '<unset>'))
    print('  probe identities found in tests/ : %d' % len(ids))
    if full:
        for v in sorted(ids):
            print('    %-28s %s' % (v, ', '.join(sorted(ids[v]))))

    hits = [v for v in (name, email) if v and v in ids]
    already = history_count(list(ids))
    # REPORTED, NEVER FAILED ON. See the docstring: the history is not ours to
    # rewrite, and a number nobody prints is a number nobody acts on.
    print('  commits already carrying one : %d  (history, NOT rewritten)' % already)

    if not hits:
        print('  CLEAN -- this clone will not commit under a probe identity.')
        return 0

    print('')
    print('COMPROMISED: this clone is configured to commit as a THROWAWAY probe')
    print('identity. Every commit it makes will be attributed to a test fixture.')
    for v in hits:
        print('  %-28s used by %s' % (v, ', '.join(sorted(ids[v]))))
    if lname or lemail:
        print('')
        print('It is in this clone\'s LOCAL config, which is where it persists:')
        print('    git config --local --unset user.name')
        print('    git config --local --unset user.email')
        print('so the clone falls back to the global identity. A probe must pass')
        print('its identity per invocation with `git -c user.name=... commit`,')
        print('never by writing it into a config a later commit will read.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
