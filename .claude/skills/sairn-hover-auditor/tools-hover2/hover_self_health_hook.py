#!/usr/bin/env python
"""hover_self_health_hook.py (hover2's own build) -- SessionStart wrapper
that runs THIS clone's hover_self_health.py and speaks the hook envelope.

THE GAP THIS CLOSES, confirmed at every session start since 2026-09-22 by
tools/hover_self_health_shim.py's third-state message: hover2 had no hook of
its own, so hover2's log was never self-checked by this mechanism (and
before the shim existed, hover2's sessions silently self-checked HOVER1's
log -- the script-relative/cwd-relative disagreement the shim documents).

CONTRACT, derived from the shim's own source (tools/hover_self_health_shim.py,
a tracked platform file -- reading it is the point of a published contract):
  - invoked with no args, cwd = the platform clone;
  - must print the SessionStart envelope itself:
      {"hookSpecificOutput": {"hookEventName": "SessionStart",
                              "additionalContext": "..."}}
  - three outcomes, never two: ran-and-reported, ran-and-failed (say what),
    could-not-run (say why) -- an empty stdout is treated by the shim as
    "did not report", so this file always prints SOMETHING when it runs.

GATE, same defense-in-depth as the precedent in SKILL.md: first action is a
marker check (.git/sairn-hover-auditor-clone via `git rev-parse --git-dir`
from the CWD). Not the hover auditor's own clone -> exit silently with zero
output, so a build clone sees nothing even if this file is ever invoked
directly rather than through the shim's own gate.

FIRES ARE RECORDED LOCALLY: one JSON line per firing appended to
hover_self_health_fires.jsonl IN THIS directory -- hover2's firing record
stays in hover2's territory (H1's fires file already accumulated hover2's
pre-shim firings once; never again).

SELF-LOG RESOLUTION IS SCRIPT-RELATIVE ON PURPOSE: hover_self_health.py
lives beside this file and reads the log beside itself, so this hook can
only ever check the log of the instance whose directory it lives in.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
HEALTH = os.path.join(HERE, 'hover_self_health.py')
FIRES = os.environ.get('HOVER_FIRES_LOG_OVERRIDE') or os.path.join(
    HERE, 'hover_self_health_fires.jsonl')
MARKER = 'sairn-hover-auditor-clone'


def is_hover_clone():
    try:
        r = subprocess.run(['git', 'rev-parse', '--git-dir'],
                           capture_output=True, text=True, timeout=8)
        if r.returncode != 0:
            return False
        gitdir = r.stdout.strip()
        return os.path.isfile(os.path.join(gitdir, MARKER))
    except Exception:
        return False


def slug_for(path):
    """The projects-directory slug for a clone path -- SAME direction and
    SAME formula as tools/hover_self_health_shim.py's own slug_for() (the
    tracked platform file this hook's whole invocation chain already
    depends on), so the two cannot drift independently without the shim
    breaking too. Un-slugging (slug -> path) is deliberately NOT attempted:
    the encoding is lossy (a literal '-' in a real path, e.g. SAIRN-hover2,
    is indistinguishable from an encoded separator), which the first draft
    of this guard learned by failing its own fixture on this very clone's
    real name."""
    return path.replace(':', '-').replace('\\', '-').replace('/', '-')


def own_project_slug(here=None):
    """LOCATION-DEPENDENT, found live 2026-09-29 (item 4/5, stonedesk-era
    paste): correct ONLY when this file lives two levels under
    .claude/projects/<slugged-path>/hover-audit-log/, where
    dirname(HERE) is the slugged project directory. The platform-repo
    backup copy under .claude/skills/sairn-hover-auditor/tools-hover2/
    computes the WRONG slug (its own selftest catches this: 'slug_for()
    on this clone's real path equals this hook's own project-dir name'
    fails there) -- that copy is a source backup, never meant to run
    in-place as the SessionStart hook itself. Only the ORIGINAL copy in
    this real projects-directory location is ever actually invoked."""
    return os.path.basename(os.path.dirname(here or HERE))


def cwd_is_own_clone():
    """CROSS-CLONE MISDIRECTION GUARD, 2026-09-28 -- the defense-in-depth
    layer whose absence in H1's hook this role reported at seq 267, then
    CONFIRMED PRESENT-BY-SYMMETRY in this very file by driving it from
    H1's clone cwd: is_hover_clone() alone answers 'is cwd A hover clone',
    not 'is cwd THIS hook's OWN clone', so this hook fired from H1's clone
    and reported hover2's data to a session standing in H1's -- the exact
    historical misdirection shape, opposite direction. Slugs cwd's repo
    toplevel (lossless direction) and compares against this hook's own
    project-directory name. Fail-CLOSED: any inability to resolve either
    side returns False (the caller reports COULD NOT RUN, never another
    clone's data)."""
    try:
        r = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                           capture_output=True, text=True, timeout=8)
        if r.returncode != 0:
            return False
        top = r.stdout.strip().replace('/', '\\')
    except Exception:
        return False
    return slug_for(top).lower() == own_project_slug().lower()


def emit(text):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': text}}))


def record_fire(outcome):
    try:
        with open(FIRES, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'ts': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'cwd': os.getcwd(), 'outcome': outcome},
                sort_keys=True) + '\n')
    except OSError:
        pass  # a fire record must never block the report itself


def main():
    if not is_hover_clone():
        return 0  # build clone or foreign cwd: zero output by design
    if not cwd_is_own_clone():
        # A DIFFERENT hover clone's cwd: refuse loudly with COULD NOT RUN,
        # never silently report THIS clone's data into another clone's
        # session -- the seq-267 misdirection shape, guarded here.
        record_fire('could-not-run-foreign-clone')
        emit('HOVER2 SELF-HEALTH: COULD NOT RUN -- this hook belongs to '
             'project %s but was invoked from a DIFFERENT hover-auditor '
             'clone\'s working directory. Reporting this clone\'s data '
             'into another clone\'s session is the exact cross-clone '
             'misdirection the shim layer exists to prevent; invoke the '
             'OTHER clone\'s own hook via its own shim instead. Nothing '
             'was checked.' % own_project_slug())
        return 0
    if not os.path.isfile(HEALTH):
        record_fire('could-not-run')
        emit('HOVER2 SELF-HEALTH: COULD NOT RUN -- hover_self_health.py is '
             'missing beside this hook (%s). The check did not run; that is '
             'a third state, not a pass.' % HEALTH)
        return 0
    try:
        r = subprocess.run([sys.executable, HEALTH], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=20)
    except Exception as e:
        record_fire('could-not-run')
        emit('HOVER2 SELF-HEALTH: COULD NOT RUN hover_self_health.py (%s). '
             'The check did not run; that is a third state, not a pass.' % e)
        return 0
    out = (r.stdout or '').strip()
    if r.returncode != 0:
        record_fire('ran-and-failed')
        emit('HOVER2 SELF-HEALTH: ran and exited %d -- read this, it is not '
             'a pass.\n%s\nstderr: %s'
             % (r.returncode, out[:3000], (r.stderr or '').strip()[:400]))
        return 0
    record_fire('ran-and-passed')
    emit('HOVER2 SELF-HEALTH (this clone\'s own log, checked by this '
         'clone\'s own hook):\n%s' % out[:3500])
    return 0


def _selftest():
    fails = []

    def chk(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            fails.append(label)

    # slug-derivation fixtures (path -> slug, the lossless direction; an
    # un-slug attempt failed its own fixture on this clone's real
    # hyphen-carrying name and was replaced by this)
    # LOCATION-INDEPENDENT since 2026-09-29 (item 2): own_project_slug()
    # ALREADY accepted an injectable `here` param, but this arm called it
    # with no argument, so it silently used the real module HERE -- correct
    # only from this file's ORIGINAL invocation location (two levels under
    # .claude/projects/<slug>/hover-audit-log/), and genuinely wrong from
    # the platform-repo backup copy under .claude/skills/sairn-hover-
    # auditor/tools-hover2/ (confirmed live: this exact arm failed there).
    # FIXED: inject the real, intended HERE value explicitly, so the
    # ASSERTION exercises the real logic against a KNOWN path regardless
    # of where this file actually happens to be sitting when run.
    _real_here = (r'C:\Users\marsh\.claude\projects\C--Users-marsh-'
                 r'Documents-SAIRN-hover2\hover-audit-log')
    chk('slug_for() on this clone\'s real path equals this hook\'s own '
        'project-dir name (location-independent: HERE injected, not read '
        'from this file\'s own actual location)',
        slug_for(r'C:\Users\marsh\Documents\SAIRN-hover2').lower()
        == own_project_slug(here=_real_here).lower())
    chk('slug_for() on H1\'s clone path does NOT equal this hook\'s slug '
        '(the discriminating case, same injected HERE)',
        slug_for(r'C:\Users\marsh\Documents\SAIRN-hover').lower()
        != own_project_slug(here=_real_here).lower())
    # KNOWN-BAD CONTROL, location-independent (deliberately does NOT read
    # actual runtime location, since that would make the control's own
    # truth value depend on where THIS run happens to sit): a WRONG here=
    # (the platform-repo backup-copy path, a genuinely different directory
    # from the real invocation location) must NOT produce the same slug as
    # the real one. Proves own_project_slug() actually discriminates on
    # its input rather than the two assertions above passing for any here=
    # value regardless of correctness.
    _wrong_here = (r'C:\Users\marsh\Documents\SAIRN-hover2\.claude\skills'
                  r'\sairn-hover-auditor\tools-hover2')
    chk('KNOWN-BAD CONTROL: a WRONG here= (the platform-repo backup-copy '
        'path) does NOT produce the same slug as the real invocation '
        'location -- proves the injected-HERE assertions above actually '
        'discriminate, not vacuously true for any input',
        own_project_slug(here=_wrong_here) != own_project_slug(here=_real_here))

    # REGRESSION TEST, the seq-267 shape: invoked with cwd inside a
    # DIFFERENT hover-auditor clone, the full hook must emit COULD NOT RUN
    # naming the foreign-clone condition -- never this clone's own report.
    other = r'C:\Users\marsh\Documents\SAIRN-hover'
    if os.path.isdir(os.path.join(other, '.git')):
        # FIXED 2026-09-29 (item 2): this spawns a REAL subprocess running
        # main(), which calls record_fire() and appended a real line to the
        # REAL hover_self_health_fires.jsonl beside this file on every
        # --selftest run -- confirmed live via a git-status/file-listing
        # snapshot before and after. HOVER_FIRES_LOG_OVERRIDE redirects the
        # subprocess's own write to a real temp file instead, cleaned up
        # in the finally block below; the real fires log is never touched
        # by a test run again.
        import tempfile as _tf3
        _fires_fd, _fires_tmp = _tf3.mkstemp(suffix='.jsonl', prefix='selftest_fires_')
        os.close(_fires_fd)
        _env = dict(os.environ, HOVER_FIRES_LOG_OVERRIDE=_fires_tmp)
        try:
            r = subprocess.run([sys.executable, os.path.abspath(__file__)],
                               capture_output=True, text=True, cwd=other,
                               timeout=30, env=_env)
        finally:
            if os.path.isfile(_fires_tmp):
                os.remove(_fires_tmp)
        out = r.stdout
        chk('REGRESSION: invoked from H1\'s clone cwd, the hook refuses '
            'with COULD NOT RUN (foreign clone), never reports hover2 data',
            'COULD NOT RUN' in out and 'DIFFERENT hover-auditor clone' in out
            and 'HOVER2 SELF-HEALTH (this clone' not in out)
    else:
        chk('REGRESSION: (H1 clone not present on disk -- cannot drive the '
            'foreign-cwd case; counted as FAIL rather than skipped, because '
            'an undriven regression test is not a regression test)', False)

    # KNOWN-BAD CONTROL that must FAIL: a deliberately broken guard (the
    # pre-fix behavior, cwd_is_own_clone always True) must be CAUGHT by
    # re-running the same foreign-cwd drive and seeing the misdirection.
    # Simulated in-process: with the guard forced open, main()'s gate
    # would pass and the foreign session would get this clone's data --
    # asserted by checking the guard is the ONLY thing standing between
    # is_hover_clone() (True in H1's clone too) and the report path.
    if os.path.isdir(os.path.join(other, '.git')):
        r2 = subprocess.run(
            [sys.executable, '-c',
             'import subprocess,sys;'
             'r=subprocess.run(["git","rev-parse","--git-dir"],'
             'capture_output=True,text=True);'
             'import os;'
             'sys.exit(0 if os.path.isfile(os.path.join(r.stdout.strip(),'
             '"sairn-hover-auditor-clone")) else 1)'],
            cwd=other, capture_output=True, timeout=30)
        chk('KNOWN-BAD CONTROL: is_hover_clone()-equivalent alone answers '
            'True from H1\'s clone too -- proving the old single-gate '
            'behavior WOULD have misdirected, i.e. the new guard is the '
            'load-bearing difference, not redundant',
            r2.returncode == 0)
    else:
        chk('KNOWN-BAD CONTROL: (H1 clone not present -- cannot prove the '
            'old gate passes there; FAIL rather than skip)', False)

    print()
    if fails:
        print('%d SELFTEST FAILURE(S): %s' % (len(fails), fails))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(_selftest())
    sys.exit(main())
