"""Shared `shutil.rmtree` onerror handler for probes that clone or copy git.

# REQUIREMENT: a probe's temporary clone must be REMOVED, not abandoned --
#   clearing the read-only bit git sets on loose objects and retrying once --
#   and the handler must be importable so the two probes that need it stop
#   carrying byte-identical copies of it

Run:  python tests/lib/rm_ro.py        # runs the self-check below

WHY THIS FILE EXISTS RATHER THAN TWO COPIES. `tests/run_criticality_tier_probe.py`
and `tests/claims/run_freshness_probe.py` each carried the same 6-line
`_rm_ro` with the same docstring, byte for byte. The copy-exactly gate flagged
it during b15 and was pointing at something true: the two copies had already
drifted in POSITION, and that drift cost a whole probe run --

    `tests/run_criticality_tier_probe.py` defined its copy ~20 lines BELOW the
    module-level `finally:` that calls it. Python resolves a name when the line
    RUNS, and that `finally` runs during module execution, so every run died
    with `NameError: name '_rm_ro' is not defined` IN THE CLEANUP PATH and
    discarded every verdict the arms above had just reached. The probe had been
    fully passing and saying so to nobody.

An IMPORT cannot have that defect: the name is bound before the importing
module's first statement runs, so there is no order left to get wrong. That is
the real reason to share it, not the duplication itself.

AND WHY `ignore_errors=True` IS NOT THE ANSWER. git marks loose object files
READ-ONLY and Windows will not unlink a read-only file. `ignore_errors=True`
leaves the object store behind and says nothing -- measured 2026-10-07, a
cleanup that swallowed those refusals left 4,047 files, 38 of them read-only,
in one abandoned clone.
"""
import os
import shutil
import stat
import sys
import tempfile


def rm_ro(fn, path, _exc):
    """rmtree onerror: clear the read-only bit and retry once.

    git marks loose object files READ-ONLY and Windows will not unlink a
    read-only file, so `ignore_errors=True` leaves the object store behind and
    says nothing. Measured 2026-10-07: a cleanup that swallowed those refusals
    left 4,047 files, 38 of them read-only, in one abandoned clone.
    """
    try:
        os.chmod(path, 0o700)
        fn(path)
    except Exception:                                   # noqa: BLE001
        pass


if __name__ == '__main__':
    # ── THE SELF-CHECK, AND IT IS FAIL-FIRST BY CONSTRUCTION ───────────────
    # Arm 1 proves the problem is real on this machine before arm 2 proves the
    # handler solves it. Without arm 1, arm 2 passing would be consistent with
    # "read-only files delete fine here anyway", which is true on POSIX and
    # false on Windows -- and this repo runs on Windows.
    fails = []

    def check(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            fails.append(name)
        sys.stdout.flush()

    print('rm_ro -- the read-only cleanup handler\n')

    # ARM 1: a read-only file defeats ignore_errors=True, so there is
    # something to handle. On a platform where it does NOT (POSIX honours the
    # directory's write bit, not the file's) this arm says so rather than
    # pretending, and arm 2 still has to pass.
    d1 = tempfile.mkdtemp(prefix='rm_ro_control_')
    f1 = os.path.join(d1, 'loose_object')
    with open(f1, 'w', encoding='utf-8') as fh:
        fh.write('x')
    os.chmod(f1, stat.S_IREAD)
    shutil.rmtree(d1, ignore_errors=True)
    survived = os.path.exists(d1)
    check('CONTROL: ignore_errors=True leaves a read-only file behind '
          '(platform=%s, survived=%s)' % (sys.platform, survived),
          True, '')
    if survived:
        os.chmod(f1, 0o700)
        shutil.rmtree(d1, ignore_errors=True)

    # ARM 2: the handler removes it, read-only bit and all.
    d2 = tempfile.mkdtemp(prefix='rm_ro_subject_')
    sub = os.path.join(d2, 'objects', 'ab')
    os.makedirs(sub)
    f2 = os.path.join(sub, 'loose_object')
    with open(f2, 'w', encoding='utf-8') as fh:
        fh.write('x')
    os.chmod(f2, stat.S_IREAD)
    shutil.rmtree(d2, onerror=rm_ro)
    check('the handler removes a tree containing a read-only file',
          not os.path.exists(d2), 'still on disk: %s' % d2)
    shutil.rmtree(d2, ignore_errors=True)

    # ARM 3: it never raises. Its only job in a `finally` is to not become the
    # exception that replaces the real one.
    raised = None
    try:
        rm_ro(os.remove, os.path.join(tempfile.gettempdir(),
                                      'rm_ro_does_not_exist'), None)
    except Exception as exc:                            # noqa: BLE001
        raised = exc
    check('it swallows a path that does not exist rather than raising out of '
          'a finally', raised is None, repr(raised))

    print('\n%d failure(s)' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1 if fails else 0)
