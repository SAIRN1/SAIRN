"""tools/hover_self_health_shim.py must run THIS clone's hook and never another's.

Run: python tests/run_hover_self_health_shim_probe.py

# REQUIREMENT: the registration this shim replaces pointed at ONE clone's copy
#   by absolute path, so a second auditor instance self-checked the FIRST one's
#   log on every firing. The only thing that makes the replacement worth having
#   is that it CANNOT do that -- so the arms below drive the absent-hook case
#   hardest, and one of them exists purely to assert that no fallback appears.

EVERY ARM IS DRIVEN AGAINST SYNTHETIC HOME DIRECTORIES built from the rule,
never against the real ~/.claude/projects. The slug derivation is checked
against the REAL directory names separately, in A1, because it is the one part
of this shim that could silently point at nothing and a synthetic fixture would
happily agree with a wrong rule.

THE THREE STATES ARE THE POINT, and they are not symmetrical:
  * build clone, no marker        -> SILENT. Anything else is noise inside
                                     another agent's session.
  * auditor clone WITH a hook     -> run it, pass its output through unchanged
  * auditor clone WITHOUT a hook  -> SAY SO BY NAME. Not silence, which reads
                                     as a pass, and not another clone's copy,
                                     which is the original defect restored.
"""
import io
import json
import os
import importlib.util
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SHIM = os.path.join(REPO, 'tools', 'hover_self_health_shim.py')

passed = failed = 0


def ok(name, cond, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   ' + name)
    else:
        failed += 1
        print('  FAIL ' + name + ('\n         ' + str(detail) if detail else ''))


def load():
    spec = importlib.util.spec_from_file_location('shim', SHIM)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def make_clone(tmp, name, marker, hook_body=None):
    """A git repo with (optionally) the auditor marker, plus a fake HOME whose
    projects directory is keyed on the slug this shim derives."""
    clone = os.path.join(tmp, name)
    os.makedirs(clone)
    subprocess.run(['git', 'init', '-q'], cwd=clone, capture_output=True)
    if marker:
        io.open(os.path.join(clone, '.git', 'sairn-hover-auditor-clone'), 'w').write('')
    home = os.path.join(tmp, name + '-home')
    m = load()
    d = os.path.join(home, '.claude', 'projects',
                     m.slug_for(os.path.abspath(clone)), 'hover-audit-log')
    os.makedirs(d)
    if hook_body is not None:
        io.open(os.path.join(d, 'hover_self_health_hook.py'), 'w',
                encoding='utf-8').write(hook_body)
    return clone, home


def run_shim(clone, home):
    env = dict(os.environ)
    env['CLAUDE_PROJECT_DIR'] = clone
    env['HOME'] = home
    env['USERPROFILE'] = home          # expanduser('~') uses this on Windows
    r = subprocess.run([sys.executable, SHIM], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=clone, env=env)
    return r.returncode, (r.stdout or ''), (r.stderr or '')


HOOK_OK = ("import json,sys\n"
           "sys.stdout.write(json.dumps({'hookSpecificOutput':{'hookEventName':"
           "'SessionStart','additionalContext':'REAL-HOOK-RAN-HERE'}}))\n")


def main():
    print('hover_self_health_shim -- this clone\'s hook, or an honest silence,'
          ' or an honest refusal\n')
    m = load()

    # ── A1: the slug rule against the REAL directories, not a fixture ───────
    real = os.path.join(os.path.expanduser('~'), '.claude', 'projects')
    if os.path.isdir(real):
        names = set(os.listdir(real))
        checked = [p for p in ('SAIRN-hover', 'SAIRN-hover2', 'SAIRN-hank')
                   if m.slug_for(os.path.abspath('C:/Users/marsh/Documents/' + p)) in names]
        ok('A1 the slug rule reproduces REAL directory names under '
           '~/.claude/projects -- a synthetic fixture would agree with a wrong '
           'rule, so this one arm is driven against the world',
           len(checked) >= 2, 'matched: %s' % checked)
    else:
        ok('A1 the slug rule reproduces REAL directory names', False,
           'COULD NOT RUN: %s is not a directory. Not a pass.' % real)

    tmp = tempfile.mkdtemp(prefix='hshim-')
    try:
        # ── A2: build clone -- SILENT ──────────────────────────────────────
        clone, home = make_clone(tmp, 'build', marker=False, hook_body=HOOK_OK)
        rc, out, err = run_shim(clone, home)
        ok('A2 a clone with NO auditor marker is SILENT -- an auditor self-check '
           'inside a build agent\'s session is noise in a place it does not belong',
           rc == 0 and out.strip() == '', 'rc=%s out=%r err=%r' % (rc, out[:200], err[:200]))

        # ── A3/A4: auditor WITH a hook -- run it, pass it through ──────────
        clone, home = make_clone(tmp, 'aud1', marker=True, hook_body=HOOK_OK)
        rc, out, err = run_shim(clone, home)
        ok('A3 an auditor clone WITH its own hook runs it',
           rc == 0 and 'REAL-HOOK-RAN-HERE' in out, 'out=%r err=%r' % (out[:300], err[:200]))
        try:
            body = json.loads(out)['hookSpecificOutput']['additionalContext']
        except Exception:
            body = None
        ok('A4 ...and the hook\'s OWN output is passed through unchanged, not '
           're-wrapped -- the hook already distinguishes ran-passed, ran-failed '
           'and could-not-run, and restating a verdict this shim did not compute '
           'is how a wrapper starts lying',
           body == 'REAL-HOOK-RAN-HERE', body)

        # ── A5/A6: THE ORIGINAL DEFECT. Auditor with NO hook of its own, while
        #          ANOTHER clone's hook exists and is reachable. ─────────────
        clone2, home2 = make_clone(tmp, 'aud2', marker=True, hook_body=None)
        # Plant a neighbour's hook inside the SAME fake home, exactly as hover1's
        # sits beside hover2's in the real one.
        other = os.path.join(home2, '.claude', 'projects',
                             m.slug_for(os.path.abspath(os.path.join(tmp, 'aud1'))),
                             'hover-audit-log')
        os.makedirs(other, exist_ok=True)
        io.open(os.path.join(other, 'hover_self_health_hook.py'), 'w',
                encoding='utf-8').write(
            "import json,sys\n"
            "sys.stdout.write(json.dumps({'hookSpecificOutput':{'hookEventName':"
            "'SessionStart','additionalContext':'NEIGHBOUR-HOOK-RAN'}}))\n")
        rc, out, err = run_shim(clone2, home2)
        ok('A5 THE DEFECT, ASSERTED AS AN ABSENCE: an auditor clone with no hook '
           'of its own does NOT reach for the neighbouring clone\'s copy, even '
           'though it exists and is readable',
           'NEIGHBOUR-HOOK-RAN' not in out, out[:300])
        ok('A6 ...and it says so BY NAME rather than falling silent -- silence '
           'here reads as a pass, and this clone\'s log genuinely has not been '
           'checked',
           rc == 0 and 'NO hover_self_health_hook.py' in out
           and 'did NOT run' in out, 'rc=%s out=%r' % (rc, out[:300]))

        # ── A7: a hook that fails must not be reported as a pass ───────────
        clone3, home3 = make_clone(tmp, 'aud3', marker=True,
                                   hook_body="import sys\nsys.exit(3)\n")
        rc, out, err = run_shim(clone3, home3)
        ok('A7 a hook that exits non-zero and prints NOTHING is reported as not '
           'having reported -- "did not report" and "reported a pass" are '
           'different facts',
           rc == 0 and 'did not report' in out, 'rc=%s out=%r' % (rc, out[:300]))

        # ── A8: the shim never exits non-zero ──────────────────────────────
        ok('A8 every path exits 0 -- a nonzero SessionStart hook surfaces '
           'stderr noise and can interfere with startup, which is why the '
           'verdict lives in the text and not in the exit code',
           rc == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n%d passed, %d failed' % (passed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
