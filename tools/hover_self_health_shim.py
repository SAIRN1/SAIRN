"""SessionStart shim: run THIS clone's hover self-health hook, never another's.

Registered in .claude/settings.json. Exits 0 always, like the hook it fronts.

── THE DEFECT THIS EXISTS TO CLOSE ─────────────────────────────────────────
.claude/settings.json registered the hook by ABSOLUTE PATH into hover1's
project directory:

    python "C:/Users/marsh/.claude/projects/
            C--Users-marsh-Documents-SAIRN-hover/hover-audit-log/
            hover_self_health_hook.py"

That file resolves its log, and its own fire record, from the location of the
SCRIPT -- `HERE = os.path.dirname(os.path.abspath(__file__))`. Its clone check,
`is_hover_clone()`, resolves from the CWD instead. The two disagree the moment a
second hover instance exists, and one does:

  * hover2's session starts, cwd is hover2's clone, which carries the
    `.git/sairn-hover-auditor-clone` marker, so the gate says YES, run.
  * The script then reads hover1's `hover-audit-log.jsonl`, because that is
    where the script lives.

SO hover2's SESSIONS HAVE BEEN SELF-CHECKING hover1's LOG, EVERY FIRING, AND
hover2's OWN LOG HAS NEVER BEEN CHECKED BY THIS MECHANISM AT ALL. The statusMessage
beside the registration said "no-op outside the hover auditor's own clone",
which is true of BUILD clones and false of the second auditor -- the one case
the wording did not anticipate.

A SECOND CONSEQUENCE, worth knowing before anybody reads that file as evidence:
`hover_self_health_fires.jsonl` in hover1's directory has been accumulating
hover2's firings too. The rows record `cwd`, so which clone fired is
recoverable -- but a reader counting lines to answer "did the hook fire for
hover1" gets a number that is too high unless they filter.

── WHAT THIS DOES, AND THE THIRD STATE ─────────────────────────────────────
Derives the per-clone hook path from CLAUDE_PROJECT_DIR (falling back to cwd)
and runs THAT, or says plainly that this clone has none. Three outcomes, never
two, and the third is the whole point:

  * not a hover clone            -> silent no-op, the build-clone case
  * this clone's hook is present -> run it, pass its output straight through
  * this clone has NO hook       -> say so BY NAME, and do not fall back

THERE IS DELIBERATELY NO FALLBACK TO ANOTHER CLONE'S COPY. The fallback IS the
defect. Measured 2026-09-22: hover2's directory contains hover_log.py,
hover_coverage_ledger.py and six others, and NO hover_self_health_hook.py -- so
the honest answer for hover2 today is "this clone has no self-health hook
installed", which is actionable, rather than a self-check silently performed
against somebody else's record.

── WHY A TRACKED SHIM RATHER THAN A CLEVERER SETTINGS ENTRY ────────────────
The path has to be COMPUTED -- the projects directory encodes the clone path as
a slug (`C:/Users/x/Documents/SAIRN-hover2` ->
`C--Users-x-Documents-SAIRN-hover2`) -- and a computed path means code. Code
belongs in a tracked, testable file, not JSON-escaped into a settings string
where nobody can read it and nothing can test it.

SCOPE: this file INVOKES the hover auditor's hook. It does not modify it, and
nothing under ~/.claude/projects/*/hover-audit-log/ is touched -- that is the
auditor's own territory and a build agent editing it is the boundary problem
running the other way (CLAUDE.md, the hover separation rules). The hook itself
is already correct in isolation; only the registration pointed at the wrong copy.
"""
import json
import os
import subprocess
import sys

HOOK_NAME = 'hover_self_health_hook.py'
MARKER = 'sairn-hover-auditor-clone'


def project_dir():
    d = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    return os.path.abspath(d)


def slug_for(path):
    """'C:/Users/x/Documents/SAIRN-hover2' -> 'C--Users-x-Documents-SAIRN-hover2'.

    Matches the directory names Claude Code already creates under
    ~/.claude/projects/ -- derived by checking against the real ones on disk
    rather than inferred from the documentation, because this is the only part
    of the shim that could silently point at nothing.
    """
    return path.replace(':', '-').replace('\\', '-').replace('/', '-')


def is_hover_clone():
    """Same marker and same lookup as tools/hover_auditor_scope_gate.py and
    .githooks/pre-push. Any failure to establish identity resolves to False --
    running an auditor's self-check inside a build agent's session is noise in
    a place it does not belong, and the cost of the opposite is one missed note.
    """
    try:
        r = subprocess.run(['git', 'rev-parse', '--git-dir'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=5, cwd=project_dir())
        if r.returncode != 0:
            return False
        git_dir = r.stdout.strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(project_dir(), git_dir)
        return os.path.isfile(os.path.join(git_dir, MARKER))
    except Exception:
        return False


def hook_path(home=None):
    base = home or os.path.expanduser('~')
    return os.path.join(base, '.claude', 'projects', slug_for(project_dir()),
                        'hover-audit-log', HOOK_NAME)


def emit(text):
    """SessionStart additionalContext, the same envelope the hook itself uses."""
    sys.stdout.write(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': text,
        }
    }))


def main():
    if not is_hover_clone():
        return 0                       # build clone: silent, one stat and out
    path = hook_path()
    if not os.path.isfile(path):
        # THE THIRD STATE. Named, not silent, and NOT satisfied by another
        # clone's copy -- reaching for one is the defect this shim closes.
        emit('HOVER SELF-HEALTH: this clone has NO %s installed.\n'
             '  expected at: %s\n'
             '  The self-check did NOT run. This is not a pass and it is not\n'
             '  a no-op -- this clone is a hover auditor (it carries the\n'
             '  .git/%s marker) and its own log has not been checked.\n'
             '  Install the hook in THIS clone; do not point the registration\n'
             '  at another clone\'s copy, which is what it used to do and is\n'
             '  why hover2 was self-checking hover1\'s log on every firing.'
             % (HOOK_NAME, path, MARKER))
        return 0
    try:
        r = subprocess.run([sys.executable, path], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=25, cwd=project_dir())
    except Exception as e:
        emit('HOVER SELF-HEALTH: COULD NOT RUN %s (%s). The check did not run;\n'
             '  that is a third state and it is not a pass.' % (path, e))
        return 0
    # PASS THE HOOK'S OWN OUTPUT STRAIGHT THROUGH. It already speaks the
    # SessionStart envelope and already distinguishes ran-and-passed,
    # ran-and-failed and could-not-run; re-wrapping it would put this shim in
    # the position of re-stating a verdict it did not compute.
    if r.stdout.strip():
        sys.stdout.write(r.stdout)
    elif r.returncode != 0:
        emit('HOVER SELF-HEALTH: %s exited %d and printed nothing. The check\n'
             '  did not report, which is not the same as reporting a pass.\n'
             '  stderr: %s' % (path, r.returncode, (r.stderr or '').strip()[:400]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
