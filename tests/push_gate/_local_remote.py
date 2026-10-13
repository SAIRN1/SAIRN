"""A throwaway BARE remote, so a push-gate probe's verdict does not need the network.

── WHY (2026-10-13, b5 item 6) ───────────────────────────────────────────────
check4_probe.py and check7_probe.py decide whether a gate FIRED by running
`git push --dry-run origin HEAD:main` and reading the refusal text. Pointing
`origin` at the real GitHub URL makes the verdict depend on three things that
have nothing to do with the check under test:

  1. THE NETWORK. No connectivity, no verdict.
  2. THE REMOTE TIP MOVING. Five clones push to this branch; when origin/main
     advances mid-run the sha git hands the hook is an object this clone does
     not have, and the gate refuses with "the outgoing range could not be read"
     BEFORE the check is reached. Both probes already carry a fetch-and-retry
     for exactly this and both still report COULD NOT RUN when it persists.
  3. EVERY OTHER CHECK IN THE HOOK. Measured on 2026-10-12: both probes exited
     3 COULD NOT RUN on a CLEAN push because the external-file-index check
     refused over ANOTHER SESSION'S handoff sitting on a shared Drive. A probe
     for a BLOCKING gate could not reach its own subject for a reason entirely
     outside the repository.

A bare repo on local disk removes (1) and (2) completely: it is created at BASE
and nothing else pushes to it, so the outgoing range is exactly the fixture
commit, every time. It does NOT remove (3) -- the hook is the same hook and
still runs every check -- and that is said here rather than implied, because a
helper that silently narrowed what the gate checks would be defeating the gate
to test it.

── WHAT THIS DELIBERATELY DOES NOT DO ───────────────────────────────────────
It does not stub, skip or weaken the pre-push hook. `core.hooksPath` still
points at the clone's own `.githooks`, the real
`tools/sairn_push_gate_hook.py` still runs, and every check still votes. The
only thing that changes is WHERE the push is going.

It is also OPT-IN and the real-remote path stays the default. A probe that can
only run against a local remote has stopped proving anything about the push
that actually ships -- so `SAIRN_PROBE_LOCAL_REMOTE=1` (or `--local-remote`)
turns it on, and the probe says which mode it ran in.
"""
import os
import shutil
import subprocess


ENV_FLAG = 'SAIRN_PROBE_LOCAL_REMOTE'


def requested(argv=None):
    """True if this run should use a local bare remote. Opt-in, both ways."""
    if (os.environ.get(ENV_FLAG) or '').strip() in ('1', 'true', 'yes', 'on'):
        return True
    return '--local-remote' in list(argv or [])


def _run(*args, **kw):
    return subprocess.run(list(args), capture_output=True, text=True,
                          encoding='utf-8', errors='replace', **kw)


def create(main_repo, base_sha, where):
    """Make a bare repo at `where` carrying `main` at `base_sha`.

    -> (path, None) on success, or (None, reason). NEVER half-builds silently:
    a bare remote with no `main` branch would make every `push --dry-run`
    refuse for a reason that looks like a gate refusal and is not.
    """
    # ── EVERY FAILURE PATH BELOW CLEANS UP AFTER ITSELF, AND THE FIRST
    #    VERSION DID NOT (fixed 2026-10-13, same session, by measurement) ───
    # When the seeding step failed, `create()` returned a reason and left the
    # half-built bare repo in %TEMP% -- and because it returned None the
    # caller's `BARE` stayed None, so the atexit handler had nothing to remove
    # and never warned. One directory was found leaked by `ls` after four probe
    # runs, with no `refs/heads/main` in it, which is how it was identified as
    # the failed attempt rather than a live one. A half-built fixture that
    # survives silently is the same defect class this directory exists to
    # refuse, one layer out.
    def _fail(reason):
        destroy(where)
        return None, reason

    if os.path.isdir(where):
        shutil.rmtree(where, ignore_errors=True)
    r = _run('git', 'init', '--bare', '--quiet', where)
    if r.returncode != 0:
        return _fail('git init --bare failed: %s' % (r.stderr or '').strip()[:200])
    # Seed `main` by FETCHING INTO THE BARE REPO, not by pushing out of the
    # clone.
    #
    # ── AND THAT DIRECTION IS THE WHOLE POINT, NOT A STYLE CHOICE ─────────
    # The first version pushed from the clone, which ran the clone's OWN
    # pre-push hook against the seeding push -- so building the fixture was
    # itself gated, and on 2026-10-13 it failed with "copy-exactly: new branch,
    # no remote base" plus two other checks. Fixture setup is not a push being
    # reviewed, and the alternative was `--no-verify`, which means a probe for
    # a push gate would be bypassing a push gate to start up. A fetch runs no
    # pre-push hook at all, so nothing is bypassed and nothing is gated.
    r = _run('git', '-C', where, 'fetch', '--quiet', main_repo,
             '%s:refs/heads/main' % base_sha)
    if r.returncode != 0:
        return _fail('seeding main at %s into the bare remote failed: %s'
                     % (base_sha[:12], (r.stderr or '').strip()[:200]))
    # Verify rather than assume. A bare repo that reports success and carries
    # no ref is the silent-pass shape this whole directory exists to refuse.
    r = _run('git', '-C', where, 'rev-parse', 'refs/heads/main')
    if r.returncode != 0 or not (r.stdout or '').strip().startswith(base_sha[:8]):
        return _fail('the bare remote has no main at %s after seeding (got %r)'
                     % (base_sha[:12], (r.stdout or '').strip()))
    return where, None


def point_at(clone, remote_path):
    """Set `clone`'s origin to the bare remote and fetch it. -> None or reason."""
    for args in (['remote', 'set-url', 'origin', remote_path],
                 ['fetch', '--quiet', 'origin', 'main']):
        r = _run('git', '-C', clone, *args)
        if r.returncode != 0:
            return '%s failed: %s' % (' '.join(args[:2]),
                                      (r.stderr or '').strip()[:200])
    return None


def destroy(where):
    """Remove it, and SAY SO if it survives.

    Same reasoning as check8_probe.py's `_rmtree_loud`: on Windows a git object
    store carries read-only pack files, and `ignore_errors=True` swallowed the
    failure there and leaked a clone per run, silently.
    """
    def _chmod_retry(func, p, _exc):
        try:
            os.chmod(p, 0o700)
            func(p)
        except OSError:
            pass
    if not os.path.isdir(where):
        return True
    shutil.rmtree(where, onerror=_chmod_retry)
    if os.path.isdir(where):
        print('WARNING: could not remove the throwaway bare remote at %s -- it '
              'will sit in TEMP until somebody deletes it.' % where)
        return False
    return True
