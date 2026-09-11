"""Every hook command in .claude/settings.json must resolve from ANY working
directory, and every hook script must behave the same when it does.

    python tests/hook_command_anchoring_probe.py

WHY THIS EXISTS -- it bricked a live session, 2026-09-10. Hook commands were
written `python tools/<name>.py`, a path relative to the working directory, and
Claude Code runs hooks in the **Bash tool's persisted working directory**. One
`cd tools` was enough: every PreToolUse hook then resolved to
`tools/tools/<name>.py`, failed to open, and **failed the tool call before the
command ran -- including the `cd ..` that would have fixed it**. `Write` and
`Edit` were blocked the same way by `redaction_check.py`, so the obvious escape
of writing a shim was blocked too. It took a tool that is not hook-gated to get
out.

It fails CLOSED, which is the safe direction and is why this was a nuisance
rather than a hole. It is still a session-ending nuisance, and the fix is four
characters of shell per line.

THE FIX IS `${CLAUDE_PROJECT_DIR:-.}`, and the fallback is the point. The
harness sets CLAUDE_PROJECT_DIR -- measured, not assumed, by wiring a temporary
hook that printed it. If a future harness stops setting it the command degrades
to exactly what it was before, so this change cannot be worse than what it
replaces.

── THE SECOND HALF, WHICH IS THE ONE THAT COULD HAVE DONE REAL DAMAGE ────────
Making the scripts REACHABLE from a subdirectory means they now RUN there,
where before they did not run at all. So every hook script was checked for
working-directory dependence, and one had it:

`session_lock_check.clone_name()` read `os.path.basename(os.getcwd())`.
Measured before the fix: `tools/` -> 'tools', `docs/` -> 'docs'. **Every clone
has a `tools/` and a `docs/`**, so a drifted cwd did not merely mislabel the
session -- it made all four clones claim the SAME lock and report each other as
duplicate sessions, in the one directory where they are guaranteed to collide.
Converting a brick into a wrong answer would have been a worse trade than
leaving it alone, which is why this arm exists rather than a note saying the
scripts "should be fine".

The other seven were checked too and need no change: `sairn_push_gate_hook.py`
and `sairn_claim_hook.py` both walk up from `os.getcwd()` to the repo root,
which still lands correctly from a subdirectory, and the rest derive paths from
`__file__` or take them from the hook payload.

Exit 0 pass, 1 fail.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(REPO, '.claude', 'settings.json')
ELSEWHERE = os.path.join(REPO, 'docs')

fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def hook_commands():
    d = json.load(io.open(SETTINGS, encoding='utf-8'))
    out = []
    for event, groups in d.get('hooks', {}).items():
        for g in groups:
            for h in g.get('hooks', []):
                out.append((event, g.get('matcher', '(any)'), h.get('command', '')))
    return out


print('1. EVERY HOOK COMMAND THAT RUNS A REPO SCRIPT IS ANCHORED')
cmds = hook_commands()
check(bool(cmds), 'settings.json declares hooks at all (fixture is valid)')
# A bare `tools/...` is the defect. Anchored forms carry CLAUDE_PROJECT_DIR.
bare = [(e, m, c) for e, m, c in cmds
        if re.search(r'(?<!/)\btools/[\w.-]+\.py', c)
        and 'CLAUDE_PROJECT_DIR' not in c]
for e, m, c in bare:
    print('        %s %s -- %s' % (e, m, c[:80]))
check(bare == [],
      'no hook command resolves a repo script relative to the cwd (%d bare)'
      % len(bare))
anchored = [c for _, _, c in cmds if 'CLAUDE_PROJECT_DIR' in c]
check(len(anchored) >= 9,
      'the anchored form is actually in use (%d command(s))' % len(anchored))
# THE FALLBACK IS NOT DECORATION. Without `:-.` an unset variable would make
# the path `/tools/x.py`, which is WORSE than the bug being fixed -- it would
# fail from the repo root too.
check(all(':-.' in c for c in anchored),
      'every anchored command keeps the `:-.` fallback, so an unset variable '
      'degrades to the old behaviour rather than to an absolute /tools path')

print('')
print('2. EVERY HOOK SCRIPT NAMED IN settings.json EXISTS')
named = sorted({m.group(1) for _, _, c in cmds
                for m in [re.search(r'tools/([\w.-]+\.py)', c)] if m})
missing = [n for n in named if not os.path.isfile(os.path.join(REPO, 'tools', n))]
check(missing == [], 'all %d named script(s) are on disk %s' % (len(named), missing))

print('')
print('3. clone_name() IS A FACT ABOUT THE CLONE, NOT ABOUT THE CWD')
# Driven as a subprocess from three real directories rather than by reading the
# source, because the defect was invisible in the source -- `os.getcwd()` looks
# perfectly reasonable until you know where hooks run.
code = ('import sys;sys.path.insert(0, r"%s");'
        'import session_lock_check as s;print(s.clone_name())'
        % os.path.join(REPO, 'tools'))
names = {}
for cwd in (REPO, ELSEWHERE, os.path.join(REPO, 'tools')):
    r = subprocess.run([sys.executable, '-c', code], cwd=cwd,
                       capture_output=True, text=True, timeout=120)
    names[os.path.basename(cwd)] = (r.stdout or r.stderr).strip()
print('        %s' % names)
check(len(set(names.values())) == 1,
      'the same clone name from the repo root, docs/ and tools/')
check(names.get('tools') not in ('tools', ''),
      "and it is NOT the subdirectory's own name -- 'tools' would collide "
      'across all four clones')

print('')
print('4. EVERY HOOK SCRIPT LOADS WHEN INVOKED FROM A SUBDIRECTORY')
# LOADED, NOT RUN, and that distinction is deliberate. Running them means a
# full report_only_checks sweep (minutes) or a claim-hook fetch -- the first
# version of this arm passed `--help` to report_only_checks.py, which has no
# such flag and falls through to the full report, and the probe blew its
# timeout. Executing the module body is exactly the thing the brick prevented
# and is what this needs to prove; the behaviour of each hook is its own
# probe's job.
loader = (
    'import importlib.util,sys;'
    'spec=importlib.util.spec_from_file_location("hooked", sys.argv[1]);'
    'm=importlib.util.module_from_spec(spec);'
    'spec.loader.exec_module(m);'
    'print("LOADED")'
)
for tool in named:
    path = os.path.join(REPO, 'tools', tool)
    r = subprocess.run([sys.executable, '-c', loader, path], cwd=ELSEWHERE,
                       capture_output=True, text=True, timeout=120)
    check('LOADED' in (r.stdout or ''),
          '%s executes its module body from docs/ %s'
          % (tool, ('-- ' + (r.stderr or '').strip().splitlines()[-1][:70])
             if 'LOADED' not in (r.stdout or '') else ''))

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
