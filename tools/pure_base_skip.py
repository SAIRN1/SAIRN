#!/usr/bin/env python
# OWNER: cody
"""May a push retry skip the gate because only the BASE moved? (C3, cody b58)

    python tools/pure_base_skip.py --old-base <sha> --gated-patches <file>

Exit 0 = SKIP is allowed (`git push --no-verify` may follow).
Exit 1 = take the FULL gate, with the reason printed.
Exit 2 = COULD NOT DECIDE -- the caller must take the full gate.

Anything but 0 means gate. That is the whole contract, and it is why this is a
tool and not a paragraph: C3 in docs/recurring-bug-classes-2.md was decided in
b57 and enforced only by a scratchpad shell script, where nothing could test it
and the next session would not have it.

A SKIP NEEDS ALL FOUR, checked in this order:
  1. the patch-ids of our commits equal the ones the gate last PASSED on;
  2. no file we change was also changed by the incoming commits;
  3. NO incoming change touches what the gate itself reads -- the tier
     register, .githooks/, the hook, or any tool the hook imports or runs.
     The overlap rule cannot see these: our files are untouched, but the
     gate that passed is no longer the gate that would run;
  4. the whole-tree re-check is green on the NEW base: defect_register,
     master_plan and traceability_matrix --check, in parallel (~18 s).

THE GATE'S READ SET IS DERIVED, NOT LISTED. It is every tools/<x>.py that the
hook or .githooks/pre-push names or imports. A hand list goes stale the day the
hook gains a check -- and stale here means a skip over a changed gate. If the
derivation finds fewer than MIN_GATE_TOOLS, the anchor has moved and this
exits 2 rather than trusting a short list.
"""
import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = 'tools/sairn_push_gate_hook.py'
PRE_PUSH = '.githooks/pre-push'
TIER_REGISTER = 'docs/CRITICALITY-TIERS.md'
MIN_GATE_TOOLS = 20   # 40+ measured at b58; far below that means the regex lost its anchor
RECHECKS = (('defect_register', 'tools/defect_register.py'),
            ('master_plan', 'tools/master_plan.py'),
            ('traceability_matrix', 'tools/traceability_matrix.py'))
SKIP, GATE, CANNOT = 0, 1, 2

_NAME = re.compile(r"tools/([A-Za-z0-9_]+\.(?:py|js))|['\"]([A-Za-z0-9_]+\.(?:py|js))['\"]|"
                   r"^\s*(?:import|from)\s+([A-Za-z0-9_]+)", re.M)


def gate_tools(repo=REPO):
    """The tools/*.py the gate runs or imports, or None if it cannot be read."""
    found = set()
    for rel in (HOOK, PRE_PUSH):
        try:
            with open(os.path.join(repo, rel), encoding='utf-8', errors='replace') as fh:
                src = fh.read()
        except OSError:
            return None
        for m in _NAME.finditer(src):
            name = m.group(1) or m.group(2) or (m.group(3) + '.py')
            if os.path.isfile(os.path.join(repo, 'tools', name)):
                found.add('tools/' + name)
    return found


def regate_reason(incoming, tools):
    """The first incoming path that changes the gate itself, or None."""
    for p in incoming:
        if p == TIER_REGISTER or p.startswith('.githooks/') or p == HOOK or p in tools:
            return p
    return None


def decide(ours, incoming, patches, gated, tools, recheck):
    """(code, reason). `recheck` is called only when 1-3 already allow a skip."""
    if tools is None or len(tools) < MIN_GATE_TOOLS:
        return CANNOT, ('the gate read set could not be derived (%s tools found, floor %d)'
                        % (None if tools is None else len(tools), MIN_GATE_TOOLS))
    if not patches or patches != gated:
        return GATE, 'our patch-ids are not the ones the gate passed on'
    both = sorted(set(ours) & set(incoming))
    if both:
        return GATE, 'incoming commits also change %s' % both[0]
    hit = regate_reason(incoming, tools)
    if hit:
        return GATE, 'incoming commits change what the gate reads: %s' % hit
    red = [name for name, rc in recheck() if rc != 0]
    if red:
        return GATE, 'whole-tree re-check not green on the new base: %s' % ', '.join(red)
    return SKIP, 'pure base move; whole-tree re-check green'


def run_rechecks(repo=REPO):
    def one(item):
        name, rel = item
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        try:
            r = subprocess.run([sys.executable, rel, '--check'], cwd=repo, env=env,
                               capture_output=True, timeout=600)
            return name, r.returncode
        except (OSError, subprocess.TimeoutExpired):
            return name, None   # did not run is not green
    with ThreadPoolExecutor(len(RECHECKS)) as ex:
        return list(ex.map(one, RECHECKS))


def _git_lines(*args):
    r = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('git %s: %s' % (' '.join(args), r.stderr.strip()))
    return [l for l in r.stdout.splitlines() if l.strip()]


def our_patch_ids():
    """Sorted patch-ids of origin/main..HEAD. A re-seat commit only rewrites
    sha strings after a rebase and is left out; the re-check covers it."""
    out = []
    for sha in _git_lines('rev-list', 'origin/main..HEAD'):
        if _git_lines('log', '-1', '--format=%s', sha)[0].startswith('chore(register-reseat'):
            continue
        diff = subprocess.run(['git', 'show', sha], cwd=REPO, capture_output=True)
        pid = subprocess.run(['git', 'patch-id', '--stable'], cwd=REPO, input=diff.stdout,
                             capture_output=True)
        if diff.returncode or pid.returncode:
            raise RuntimeError('patch-id failed for ' + sha)
        if pid.stdout.split():
            out.append(pid.stdout.split()[0].decode())
    return ' '.join(sorted(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--old-base', help='origin/main before this retry fetched')
    ap.add_argument('--gated-patches', help='file holding the patch-ids the gate last passed on')
    ap.add_argument('--print-patches', action='store_true',
                    help='print our patch-ids (what to record after a gate PASS) and exit')
    a = ap.parse_args(argv)
    if a.print_patches:
        try:
            print(our_patch_ids())
            return 0
        except RuntimeError as e:
            print('COULD NOT RUN: %s' % e, file=sys.stderr)
            return CANNOT
    if not a.old_base or not a.gated_patches:
        ap.error('--old-base and --gated-patches are required')
    try:
        with open(a.gated_patches, encoding='utf-8') as fh:
            gated = fh.read().strip()
    except OSError:
        gated = ''
    try:
        ours = _git_lines('diff', '--name-only', 'origin/main', 'HEAD')
        incoming = _git_lines('diff', '--name-only', a.old_base, 'origin/main')
        patches = our_patch_ids()
    except RuntimeError as e:
        print('MODE=gate  COULD NOT DECIDE: %s' % e)
        return CANNOT
    code, why = decide(ours, incoming, patches, gated, gate_tools(), run_rechecks)
    print('MODE=%s  %s' % ('skip' if code == SKIP else 'gate', why))
    return code


if __name__ == '__main__':
    sys.exit(main())
