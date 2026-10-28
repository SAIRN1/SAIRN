#!/usr/bin/env python
# OWNER: cc
"""tools/builder_hook_presence.py -- install tools/builder_auditor_deny_hook.py
into every builder clone, and keep proving that it is still there, unmodified.

WHY THE PROOF RECURS. A PreToolUse hook that has been deleted, edited or
switched off looks exactly like one that is working and never had anything to
refuse. Nothing announces that difference. This check is wired as a
SessionStart hook in every builder clone, so it re-runs at the start of every
batch, including every batch that touches shared config. Each clone checks
ALL FOUR clones, not only itself. A clone whose own wiring was stripped is
therefore still reported by the next start in any of the other three.

WHAT "PRESENT AND UNMODIFIED" MEANS, per builder clone:
  1. <clone>/.git/sairn-hooks/ holds builder_auditor_deny_hook.py,
     builder_hook_presence.py and sairn_done_line.py (the last is the Stop
     hook that holds a batch's final message to its done line). Each has the
     git blob sha of the copy at origin/main. The reference is taken from whichever builder
     clone's origin/main is newest, so one clone that has not fetched
     cannot vouch for a stale copy.
  2. <clone>/.claude/settings.local.json carries the exact PreToolUse entry
     (matcher plus command), and the exact SessionStart and Stop entries.
  3. `disableAllHooks` is not true in that clone's settings.local.json, in its
     settings.json, or in ~/.claude/settings.json. Any one of those switches
     the hook off without touching a byte of it.

WHY THE COPY LIVES IN .git/sairn-hooks/ AND NOT tools/. The tracked file
arrives in a clone only when that clone pulls. A settings entry pointing at a
file that is not there yet would exit 2 on every call and block that clone
outright. A copy under .git/ travels with no commit, is not touched by a pull
and is per-clone. That is the same reason tools/sairn_session_identity.py
keeps its marker there. The cost is that a new version reaches a clone only by
re-running --install. The check reports such a copy as STALE until then, which
is the point of it.

THE BUILDER LIST IS DERIVED, never written out here. It is every
.claude/claims/<name>.json whose name is not an auditor's (^hover[0-9]*$) and
which has a sibling clone directory SAIRN-<name>. A claim with no clone on
this machine, such as `cloud`, is listed as not-on-this-machine rather than
counted.

    python tools/builder_hook_presence.py                  # check; exit 0 / 1 finding / 2 could not run
    python tools/builder_hook_presence.py --session-start  # the same, phrased for the start-of-session context
    python tools/builder_hook_presence.py --install        # copy + wire into every builder clone, then check
    python tools/builder_hook_presence.py --selftest
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

CRITERIA_VERSION = '2026-10-28.b66.3'
EXIT_OK, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

HOOK = 'builder_auditor_deny_hook.py'
SELF = 'builder_hook_presence.py'
DONE = 'sairn_done_line.py'          # its Stop hook (cc b66): the final message is the done line, exactly
FILES = (HOOK, SELF, DONE)
COPY_DIR = os.path.join('.git', 'sairn-hooks')
AUDITOR_RE = re.compile(r'^hover[0-9]*$')
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The clone that RAN this, whether from tools/ or from .git/sairn-hooks/.
if os.path.basename(REPO) == '.git':
    REPO = os.path.dirname(REPO)
USER_SETTINGS = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')


class CouldNotRun(Exception):
    pass


def git(repo, *args, **kw):
    return subprocess.run(['git', '-C', repo] + list(args), capture_output=True, timeout=60, **kw)


def blob_sha(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def matcher(ref):
    """Read from the REFERENCE hook, so the two cannot disagree about what is
    inspected, and so a clone that has not pulled can still run this. It is
    parsed rather than imported, because importing would run the hook's module
    code in the checker."""
    src = ref[HOOK][1].decode('utf-8')
    w = re.search(r"^WRITE_TOOLS = (\(.*?\))$", src, re.M)
    c = re.search(r"^COMMAND_TOOLS = (\(.*?\))$", src, re.M)
    if not (w and c):
        raise CouldNotRun('WRITE_TOOLS / COMMAND_TOOLS not found in the origin/main %s' % HOOK)
    import ast
    return '|'.join(ast.literal_eval(w.group(1)) + ast.literal_eval(c.group(1)))


def expected_entries(clone, match):
    root = os.path.abspath(clone).replace('\\', '/')
    return {
        'PreToolUse': {'matcher': match, 'hooks': [
            {'type': 'command', 'command': 'python "%s/.git/sairn-hooks/%s"' % (root, HOOK)}]},
        'SessionStart': {'hooks': [
            {'type': 'command', 'command': 'python "%s/.git/sairn-hooks/%s" --session-start' % (root, SELF)}]},
        'Stop': {'hooks': [
            {'type': 'command', 'command': 'python "%s/.git/sairn-hooks/%s" --stop-hook' % (root, DONE)}]},
    }


def builders(repo=REPO):
    """-> (present {name: clone_dir}, absent [names with a claim but no clone])."""
    claims = os.path.join(repo, '.claude', 'claims')
    try:
        names = sorted(f[:-5] for f in os.listdir(claims)
                       if re.match(r'^[a-z][a-z0-9_-]{1,31}\.json$', f))
    except OSError as e:
        raise CouldNotRun('the claim directory could not be listed (%s)' % e)
    parent = os.path.dirname(os.path.abspath(repo))
    present, absent = {}, []
    for n in names:
        if AUDITOR_RE.match(n):
            continue
        d = os.path.join(parent, 'SAIRN-%s' % n)
        (present.__setitem__(n, d) if os.path.isdir(os.path.join(d, '.git')) else absent.append(n))
    if len(present) < 2:
        raise CouldNotRun('only %d builder clone(s) found beside %s' % (len(present), repo))
    return present, absent


def reference(clones):
    """-> {filename: (blob_sha, bytes)} from the NEWEST builder origin/main."""
    best = None
    for name, d in clones.items():
        r = git(d, 'log', '-1', '--format=%ct', 'origin/main')
        if r.returncode != 0:
            continue
        ct = int(r.stdout.strip() or 0)
        if best is None or ct > best[0]:
            best = (ct, name, d)
    if best is None:
        raise CouldNotRun('no builder clone has a readable origin/main')
    out = {}
    for f in FILES:
        r = git(best[2], 'show', 'origin/main:tools/%s' % f)
        if r.returncode != 0:
            raise CouldNotRun('tools/%s is not on origin/main in %s (the newest, at %s) -- '
                              'it has to be pushed before it can be the reference' % (f, best[1], best[0]))
        out[f] = (blob_sha(r.stdout), r.stdout)
    return out, best[1]


def load_json(path):
    try:
        return json.loads(io.open(path, encoding='utf-8').read())
    except OSError:
        return None
    except ValueError as e:
        raise CouldNotRun('%s is not valid JSON (%s)' % (path, e))


def has_entry(rows, want):
    for r in rows or []:
        if r.get('matcher') == want.get('matcher') and r.get('hooks') == want['hooks']:
            return True
    return False


def check_clone(name, clone, ref, match, user_settings=USER_SETTINGS):
    """-> list of finding strings for one clone. Empty means present and unmodified."""
    out = []
    for f in FILES:
        p = os.path.join(clone, COPY_DIR, f)
        try:
            got = blob_sha(io.open(p, 'rb').read())
        except OSError:
            out.append('MISSING %s' % p)
            continue
        if got != ref[f][0]:
            out.append('MODIFIED-OR-STALE %s (blob %s, origin/main %s)' % (p, got[:12], ref[f][0][:12]))
    local = os.path.join(clone, '.claude', 'settings.local.json')
    doc = load_json(local)
    want = expected_entries(clone, match)
    if doc is None:
        out.append('NO %s' % local)
    else:
        hooks = doc.get('hooks') or {}
        for ev in sorted(want):
            if not has_entry(hooks.get(ev), want[ev]):
                out.append('UNWIRED %s: hooks.%s has no exact entry for %s' % (local, ev, want[ev]['hooks'][0]['command']))
    # The hook unions the manifest's auditor_paths with a built-in floor. A
    # manifest it cannot read leaves it on the floor alone, so say so here.
    man = load_json(os.path.join(clone, 'docs', 'sairn-path-manifest.json'))
    if not (isinstance(man, dict) and isinstance(man.get('auditor_paths'), list)):
        out.append('DEGRADED: %s/docs/sairn-path-manifest.json has no readable auditor_paths, '
                   'so the hook is on its built-in floor only' % clone)
    for s in (local, os.path.join(clone, '.claude', 'settings.json'), user_settings):
        d = load_json(s)
        if d and d.get('disableAllHooks') is True:
            out.append('DISABLED: disableAllHooks is true in %s' % s)
    return out


def run_check(repo=REPO, user_settings=USER_SETTINGS):
    """-> (exit_code, lines)."""
    try:
        clones, absent = builders(repo)
        ref, ref_from = reference(clones)
        match = matcher(ref)
    except CouldNotRun as e:
        return EXIT_COULD_NOT_RUN, ['BUILDER HOOK PRESENCE -- COULD NOT RUN: %s. This is NOT a pass.' % e]
    lines, bad = [], 0
    for name in sorted(clones):
        try:
            f = check_clone(name, clones[name], ref, match, user_settings)
        except CouldNotRun as e:
            return EXIT_COULD_NOT_RUN, ['BUILDER HOOK PRESENCE -- COULD NOT RUN on %s: %s' % (name, e)]
        bad += bool(f)
        lines.append('  %-7s %s' % (name, 'OK' if not f else 'FINDING'))
        lines.extend('          ' + x for x in f)
    head = ('BUILDER HOOK PRESENCE -- %d of %d builder clone(s) carry the deny hook unmodified '
            '(reference: origin/main in %s, hook blob %s)'
            % (len(clones) - bad, len(clones), ref_from, ref[HOOK][0][:12]))
    tail = ['  not on this machine: %s' % ', '.join(absent)] if absent else []
    return (EXIT_FINDING if bad else EXIT_OK), [head] + lines + tail


def atomic_write(path, data):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-', dir=d)
    try:
        with os.fdopen(fd, 'wb') as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def install(repo=REPO):
    clones, _absent = builders(repo)
    ref, ref_from = reference(clones)
    match = matcher(ref)
    for f in FILES:
        mine = blob_sha(io.open(os.path.join(repo, 'tools', f), 'rb').read())
        if mine != ref[f][0]:
            raise CouldNotRun('tools/%s in this clone (blob %s) is not the origin/main copy (%s). '
                              'Push it first: only a reviewed, landed copy is installed.'
                              % (f, mine[:12], ref[f][0][:12]))
    for name in sorted(clones):
        clone = clones[name]
        for f in FILES:
            atomic_write(os.path.join(clone, COPY_DIR, f), ref[f][1])
        local = os.path.join(clone, '.claude', 'settings.local.json')
        doc = load_json(local) or {}
        before = json.dumps(doc, sort_keys=True)
        hooks = doc.setdefault('hooks', {})
        want = expected_entries(clone, match)
        for ev, entry in want.items():
            mark = '/.git/sairn-hooks/'
            keep = [r for r in (hooks.get(ev) or [])
                    if not any(mark in (h.get('command') or '') for h in r.get('hooks') or [])]
            hooks[ev] = keep + [entry]
        # A REFRESH (new landed copies, wiring already exact) leaves the
        # settings file untouched. The settings files are deny-protected for
        # the agents, and a refresh has no reason to rewrite one.
        if json.dumps(doc, sort_keys=True) != before:
            atomic_write(local, (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
            print('  installed %-7s %s  (copies + settings wiring)' % (name, clone))
        else:
            print('  refreshed %-7s %s  (copies only; wiring already exact, settings untouched)' % (name, clone))
    return ref_from


# ── SELFTEST ────────────────────────────────────────────────────────────────
def selftest():
    import shutil
    bad, n = [], [0]

    def arm(name, ok, got=None):
        n[0] += 1
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, '' if ok else '   got %r' % (got,)))
        if not ok:
            bad.append(name)

    t = tempfile.mkdtemp(prefix='bhp-')
    try:
        g = ['-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'core.autocrlf=false']
        src = {f: io.open(os.path.join(REPO, 'tools', f), 'rb').read() for f in FILES}
        for nm in ('aa', 'bb', 'hover'):
            d = os.path.join(t, 'SAIRN-%s' % nm)
            os.makedirs(os.path.join(d, 'tools'))
            os.makedirs(os.path.join(d, '.claude', 'claims'))
            for c in ('aa', 'bb', 'hover', 'cloud'):
                io.open(os.path.join(d, '.claude', 'claims', c + '.json'), 'w').write('{}')
            os.makedirs(os.path.join(d, 'docs'))
            io.open(os.path.join(d, 'docs', 'sairn-path-manifest.json'), 'w').write('{"auditor_paths": ["x/"]}')
            for f, b in src.items():
                io.open(os.path.join(d, 'tools', f), 'wb').write(b)
            git(d, 'init', '-q')
            git(d, *(g + ['add', '-A']))
            git(d, *(g + ['commit', '-q', '-m', 'x']))
            git(d, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        us = os.path.join(t, 'user-settings.json')
        io.open(us, 'w').write('{}')
        a = os.path.join(t, 'SAIRN-aa')
        global REPO
        real = REPO
        REPO = a
        try:
            pres, absent = builders(a)
            arm('builders are derived: auditor excluded, a claim with no clone listed absent',
                sorted(pres) == ['aa', 'bb'] and absent == ['cloud'], (sorted(pres), absent))
            rc, lines = run_check(a, us)
            arm('BEFORE install: every clone is a FINDING, exit 1', rc == 1 and sum('FINDING' in x for x in lines) == 2, (rc, lines))
            install(a)
            rc, lines = run_check(a, us)
            arm('AFTER install: exit 0, both OK', rc == 0, (rc, lines))
            b_hook = os.path.join(t, 'SAIRN-bb', COPY_DIR, HOOK)
            io.open(b_hook, 'ab').write(b'# tampered\n')
            rc, lines = run_check(a, us)
            arm('a MODIFIED copy in ANOTHER clone is caught from this one', rc == 1 and any('MODIFIED' in x for x in lines), lines)
            install(a)
            loc = os.path.join(t, 'SAIRN-bb', '.claude', 'settings.local.json')
            doc = json.load(io.open(loc))
            doc['hooks']['PreToolUse'] = []
            io.open(loc, 'w').write(json.dumps(doc))
            rc, lines = run_check(a, us)
            arm('a stripped PreToolUse entry is UNWIRED', rc == 1 and any('UNWIRED' in x and 'PreToolUse' in x for x in lines), lines)
            install(a)
            doc = json.load(io.open(loc))
            doc['hooks']['Stop'] = []
            io.open(loc, 'w').write(json.dumps(doc))
            rc, lines = run_check(a, us)
            arm('a stripped Stop (done-line) entry is UNWIRED', rc == 1 and any('UNWIRED' in x and 'Stop' in x for x in lines), lines)
            install(a)
            doc = json.load(io.open(loc))
            doc['hooks']['PreToolUse'][0]['matcher'] = 'Edit'
            io.open(loc, 'w').write(json.dumps(doc))
            rc, lines = run_check(a, us)
            arm('a NARROWED matcher is UNWIRED (exact, not "some entry")', rc == 1, lines)
            install(a)
            doc = json.load(io.open(loc))
            arm('re-install replaces its own entry rather than stacking a second',
                len(doc['hooks']['PreToolUse']) == 1, doc['hooks']['PreToolUse'])
            m0 = os.stat(loc).st_mtime_ns
            body0 = io.open(loc, 'rb').read()
            install(a)
            arm('a REFRESH with exact wiring leaves settings.local.json byte-identical and unwritten',
                io.open(loc, 'rb').read() == body0 and os.stat(loc).st_mtime_ns == m0)
            io.open(us, 'w').write('{"disableAllHooks": true}')
            rc, lines = run_check(a, us)
            arm('disableAllHooks in the USER settings is a finding', rc == 1 and any('DISABLED' in x for x in lines), lines)
            io.open(us, 'w').write('{}')
            bman = os.path.join(t, 'SAIRN-bb', 'docs', 'sairn-path-manifest.json')
            io.open(bman, 'w').write('{not json')
            rc, lines = run_check(a, us)
            arm('a broken manifest is never a pass (COULD NOT RUN or DEGRADED)', rc in (1, 2), (rc, lines))
            io.open(bman, 'w').write('{}')
            rc, lines = run_check(a, us)
            arm('a manifest with no auditor_paths is DEGRADED', rc == 1 and any('DEGRADED' in x for x in lines), lines)
            io.open(bman, 'w').write('{"auditor_paths": ["x/"]}')
            io.open(os.path.join(a, 'tools', HOOK), 'ab').write(b'# local edit\n')
            try:
                install(a)
                arm('install REFUSES an unlanded local copy', False, 'installed')
            except CouldNotRun:
                arm('install REFUSES an unlanded local copy', True)
            for nm in ('aa', 'bb'):
                git(os.path.join(t, 'SAIRN-%s' % nm), 'update-ref', '-d', 'refs/remotes/origin/main')
            rc, lines = run_check(a, us)
            arm('no origin/main anywhere is COULD NOT RUN (exit 2), never a pass', rc == 2, (rc, lines))
        finally:
            REPO = real
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print('BUILDER HOOK PRESENCE SELFTEST -- criteria %s -- %d arm(s), %d failed' % (CRITERIA_VERSION, n[0], len(bad)))
    return 1 if bad else 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    if '--install' in argv:
        try:
            install()
        except CouldNotRun as e:
            print('INSTALL REFUSED -- %s' % e)
            return EXIT_COULD_NOT_RUN
    rc, lines = run_check()
    if '--session-start' in argv:
        # SessionStart cannot block. Exit 0 keeps the text in the agent's
        # context, which is the only place a finding here can act. A clean run
        # is ONE line, because hook output volume is what got every hook
        # removed on 2026-10-11.
        print(lines[0] if rc == EXIT_OK else '\n'.join(lines + [
            '  ACTION: the builder-into-auditor deny hook is not intact. Do not touch shared config '
            'until it is; re-install with `python tools/builder_hook_presence.py --install`.']))
        return 0
    print('\n'.join(lines))
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
