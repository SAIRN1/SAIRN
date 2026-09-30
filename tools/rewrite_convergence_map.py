"""Every hook and tool that can rewrite the tree or a commit -- and whether the chain settles.

Run:  python tools/rewrite_convergence_map.py --map        # the map, markdown
      python tools/rewrite_convergence_map.py --map --json # the map, machine-readable
      python tools/rewrite_convergence_map.py --verify     # anchors + coverage
      python tools/rewrite_convergence_map.py --simulate   # does the chain settle?

── WHY A MAP IS NOT ENOUGH, AND WHY A SIMULATION IS THE REAL ARTEFACT ──────
On 2026-09-29 nine consecutive commits in one branch did nothing but re-seat
register shas. The chain:

  1. tools/push_retry.py --loop rebases onto origin/main;
  2. .githooks/post-rewrite re-seats the register's cited shas onto the ones the
     rebase just produced, WRITES the file, and correctly refuses to commit on
     anyone's behalf -- so the tree is now dirty;
  3. the loop's regenerate step stages only the three GENERATED docs, so the
     register stays dirty;
  4. amend_safety() correctly refuses a dirty tree, the push is blocked, the
     loop rebases again, and step 2 repeats.

EVERY STEP IS INDIVIDUALLY CORRECT. The hook is right not to commit for
somebody. The regenerate allowlist is right not to sweep. The amend guard is
right to refuse a dirty tree. Reading each in isolation found nothing for nine
commits, because the defect is not in a step -- it is in the closure.

So a list of actors would not have caught this and would not catch the next
one. What catches it is running the actors as transitions over a shared state
and asking whether the composition has a fixed point. That is --simulate, and
its only meaningful control is ABLATION: remove the fold-in step and the
simulation must go red. A convergence check that passes on converging code
proves nothing unless it is also shown to fail on diverging code.

── THE MAP IS VERIFIED, NOT ASSERTED ───────────────────────────────────────
Every actor carries an ANCHOR: a file and a string that must appear in it
EXACTLY ONCE. The anchor is deliberately the INVOCATION line rather than
anything in the file's header prose -- rewriting a comment must not change the
verdict, and deleting the call must.

Zero matches is exit 2 COULD NOT RUN, not exit 0. The map's claim about that
actor is no longer checkable, and an unverifiable claim reported as verified is
how every map on this platform has gone stale. MORE than one match is also
refused: an ambiguous anchor cannot tell you which site it found, so it is not
evidence either. That two-sided uniqueness guard is the shape the sabotage
control scored as stronger than a bare `anchor in src`.

── COVERAGE IS CHECKED AGAINST DISK, NOT AGAINST ITSELF ────────────────────
--verify lists .githooks/ from the filesystem and the GENERATED table out of
tools/push_retry.py, and fails if anything there is absent from the map. A map
that only knows what it already knows is the eighth discipline's exact failure:
nothing announces the day it stopped describing the repo.
"""
import argparse
import ast
import io
import json
import os
import re
import subprocess
import sys

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── THE MAP ─────────────────────────────────────────────────────────────────
# `self_retrigger` is the field the livelock turned on, so it is required on
# every actor and its value is a sentence, not a boolean: "no" and "no, because
# it refuses to commit" are the same answer but only the second one tells the
# next reader why the chain still closed.
ACTORS = [
    {
        'name': 'post_rewrite_hook',
        'kind': 'hook',
        'file': '.githooks/post-rewrite',
        'anchor': '--post-rewrite',
        'trigger': 'git fires it once after a rebase or an --amend completes, '
                   'with the old->new sha map on stdin',
        'writes': 'docs/defect-density-register.json -- re-seats cited shas. '
                  'Does not stage and does not commit.',
        'self_retrigger': 'NO on its own: it writes a file, and writing a file '
                          'is not a rewrite, so git never fires it again. But '
                          'the dirty tree it leaves blocks the amend, the push '
                          'fails, and the LOOP rebases again -- which does fire '
                          'it again. This is the livelock, and it is a property '
                          'of the loop, not of the hook.',
    },
    {
        'name': 'prepare_commit_msg_hook',
        'kind': 'hook',
        'file': '.githooks/prepare-commit-msg',
        'anchor': 'for CHECK in staged_conflict_marker_check.py staged_credential_check.py',
        'trigger': 'every git commit, INCLUDING the commit inside '
                   'git rebase --continue (pre-commit does not fire there)',
        'writes': 'nothing. It refuses, non-zero, and the staged resolution '
                  'stays staged.',
        'self_retrigger': 'NO -- it writes nothing at all, so there is nothing '
                          'for it to react to.',
    },
    {
        'name': 'pre_commit_hook',
        'kind': 'hook',
        'file': '.githooks/pre-commit',
        'anchor': 'hover_auditor_scope_gate.py" --pre-commit',
        'trigger': 'every git commit in a clone carrying the hover-auditor '
                   'marker in .git/; one file test and exit in every other clone',
        'writes': 'nothing. Refuses out-of-scope writes.',
        'self_retrigger': 'NO -- writes nothing.',
    },
    {
        'name': 'pre_push_hook',
        'kind': 'hook',
        'file': '.githooks/pre-push',
        'anchor': 'sairn_push_gate_hook.py" --pre-push',
        'trigger': 'every push, from any caller -- Bash, a Python subprocess, '
                   'an IDE. That is the property the old command-text regex '
                   'never had.',
        'writes': 'nothing. Refuses the push.',
        'self_retrigger': 'NO -- writes nothing. It can make the loop retry, '
                          'which is the loop re-entering, not this re-firing.',
    },
    {
        'name': 'push_retry_rebase',
        'kind': 'tool',
        'file': 'tools/push_retry.py',
        'anchor': 'def cmd_loop(',
        'trigger': 'python tools/push_retry.py --loop, and again on each '
                   'attempt while the branch is behind origin/main',
        'writes': 'rewrites local commits (the rebase). FIRES post-rewrite.',
        'self_retrigger': 'YES, by design and bounded: --attempts N. The rebase '
                          'is what fires post_rewrite_hook, which is the first '
                          'half of the closed loop.',
    },
    {
        'name': 'push_retry_regenerate',
        'kind': 'tool',
        'file': 'tools/push_retry.py',
        'anchor': 'def regenerate():',
        'trigger': 'each loop attempt, after the rebase',
        'writes': 'the three GENERATED docs, and stages ONLY those. PR 2.5: a '
                  'conflict in a derived document is resolved by re-deriving.',
        'self_retrigger': 'NO -- re-deriving from the same source is idempotent, '
                          'so a second run writes the same bytes and the tree '
                          'stops changing. Its correct refusal to stage anything '
                          'else is what leaves the register dirty.',
    },
    {
        'name': 'amend_guard',
        'kind': 'tool',
        'file': 'tools/push_retry.py',
        'anchor': 'def amend_safety():',
        'trigger': 'before any --amend the loop would perform',
        'writes': 'nothing. Exit 3 and a reason when an amend is unsafe.',
        'self_retrigger': 'NO -- writes nothing. It is the step that was right '
                          'to refuse and therefore right to hold the livelock '
                          'open until the fold-in existed.',
    },
    {
        'name': 'fold_reseat',
        'kind': 'tool',
        'file': 'tools/push_retry.py',
        'anchor': 'def reseat_only():',
        'trigger': 'each loop attempt, on a dirty register only',
        'writes': 'stages docs/defect-density-register.json -- ONLY when every '
                  'changed line is a "commit" citation AND defect_register.py '
                  '--check passes. Anything else is left and named.',
        'self_retrigger': 'NO -- once folded the register is clean, so the next '
                          'attempt finds nothing to fold. THIS IS THE STEP THAT '
                          'CLOSES THE LIVELOCK, which is why ablating it is the '
                          'known-bad control.',
    },
    {
        'name': 'defect_register_reseat',
        'kind': 'tool',
        'file': 'tools/defect_register.py',
        'anchor': 'def reseat_base(',
        'trigger': '--post-rewrite from the hook, or --reseat by hand',
        'writes': 'docs/defect-density-register.json. Never commits.',
        'self_retrigger': 'NO -- a re-seat onto already-correct shas is a no-op, '
                          'so it reaches a fixed point in one further pass. That '
                          'fixed-point property was itself a fix: it used to '
                          'accept a DANGLING commit as a good sha and skip the '
                          'records a rebase had orphaned.',
    },
    # ── THE TWO THE DECLARATION MISSED, FOUND BY --derive ──────────────────
    # Both are squarely in the convergence chain and neither was in the
    # twelve-entry map I wrote. They are here because the repository was asked
    # instead of the author.
    {
        'name': 'claim_commit_push',
        'kind': 'tool',
        'file': 'tools/sairn_claim.py',
        'anchor': "'git', 'push', 'origin', 'HEAD:main'",
        'trigger': 'every `claim` and every `release` -- so several times a '
                   'session, from any session',
        'writes': '.claude/claims/<session>.json, then COMMITS it and PUSHES, '
                  'rebasing onto origin/main first when it is behind.',
        'self_retrigger': 'NO by itself -- the claim file it writes is the one '
                          'it then commits, and a second claim writes different '
                          'content rather than the same content again. BUT ITS '
                          'REBASE FIRES post_rewrite_hook exactly as the push '
                          'loop does, so it can enter the livelock from a '
                          'completely different door. It refuses outright on an '
                          'unstaged change rather than staging by breadth, '
                          'which is what keeps it out.',
    },
    {
        'name': 'rebase_resolve',
        'kind': 'tool',
        'file': 'tools/sairn_rebase_resolve.py',
        'anchor': "if pol.get('strategy') != STRATEGY:",
        'trigger': 'by hand during a conflicted rebase, on a ledger whose '
                   'merge_policy it reads from the COMMON ANCESTOR',
        'writes': 'the merged ledger, and STAGES it -- never commits. Stages '
                  'nothing unless the ledger\'s own validator passes.',
        'self_retrigger': 'NO -- a union of a set with itself is that set, so a '
                          'second run on the merged file finds nothing to '
                          'merge. It REFUSES on a deleted record or on one both '
                          'sides changed differently, which is the case where a '
                          'union would be a different wrong answer rather than '
                          'a safer one.',
    },
    {
        'name': 'regen_master_plan',
        'kind': 'regenerator',
        'file': 'tools/master_plan.py',
        'anchor': 'def main(',
        'trigger': 'push_retry_regenerate, or by hand',
        'writes': 'docs/MASTER-PLAN.md',
        'self_retrigger': 'NO -- derived from the repo, idempotent on a second run.',
    },
    {
        'name': 'regen_traceability_matrix',
        'kind': 'regenerator',
        'file': 'tools/traceability_matrix.py',
        'anchor': 'def main(',
        'trigger': 'push_retry_regenerate, or by hand',
        'writes': 'docs/traceability-matrix.md',
        'self_retrigger': 'NO -- derived from the repo, idempotent on a second run.',
    },
    {
        'name': 'regen_tooling_inventory',
        'kind': 'regenerator',
        'file': 'tools/tooling_inventory.py',
        'anchor': 'def main(',
        'trigger': 'push_retry_regenerate, or by hand',
        'writes': 'docs/TOOLING-INVENTORY.md',
        'self_retrigger': 'NO -- derived from the repo, idempotent on a second run.',
    },
]

BY_NAME = dict((a['name'], a) for a in ACTORS)


# ── THE DERIVED SET, AND WHY A DECLARATION IS NOT A MEASUREMENT ────────────
# Everything above is the AUTHOR'S CLAIM. `--derive` answers the same question
# from the repository instead, by three clauses that never consult ACTORS:
#
#   1. every file under the directory `core.hooksPath` ACTUALLY names;
#   2. every file that calls git with a MUTATING verb -- commit, add, push,
#      rebase, reset, merge, amend, checkout -- ON THIS TREE rather than on a
#      sandbox it created itself;
#   3. every file that opens a GIT-TRACKED path for writing.
#
# DRIVING IT FOUND TWO ACTORS THE DECLARED MAP HAD MISSED, both squarely in
# the convergence chain: tools/sairn_claim.py (add, commit, push and REBASE --
# it rebases and pushes on every claim and every release) and
# tools/sairn_rebase_resolve.py (stages the merged ledger). A twelve-entry map
# written by the session that built the chain missed two of its own members.
# That is the whole argument for deriving rather than declaring.
#
# AND THE DERIVATION IS BLIND WHERE THE MAP IS NOT. Clause 2 cannot see
# .githooks/post-rewrite, which shells out to defect_register.py and calls no
# git verb of its own; it cannot see the three regenerators, which only write
# files; and it cannot resolve push_retry.py into four separate actors,
# because it is file-granular and they are not. So both sets are printed with
# their symmetric difference and NEITHER is treated as the answer.
MUTATING_VERBS = ('commit', 'add', 'push', 'rebase', 'reset', 'merge',
                  'amend', 'checkout')
SUBPROC_NAMES = ('run', 'call', 'check_call', 'check_output', 'Popen', 'system',
                 'getoutput', 'getstatusoutput', 'spawn', 'git', 'run_git', 'sh')
SANDBOX = re.compile('mkdtemp|mkstemp|TemporaryDirectory|worktree'
                     "|git[^\n]{0,24}['\"]init['\"]")
WRITE_MODE = re.compile("open\\s*\\([^)]{0,200}['\"](?:w|w\\+|wb)['\"]")
TRACKED_LIT = re.compile("['\"]([A-Za-z0-9_./-]+\\.(?:md|json|js|py|html|sql))['\"]")

# Files the derivation finds that are deliberately OUTSIDE the convergence
# chain. Each really does mutate the tree or the index, so clause 2 is right
# to find them; none participates in the rebase/regenerate/amend/push loop
# whose fixed point --simulate is about. Named here rather than filtered by a
# pattern, so the exemption is auditable and a new one has to be argued for.
OUT_OF_SCOPE = {
    'tools/bare_run_write_check.py':
        'restores the working tree with `git checkout -- .` after its own '
        'sweep. Mutates the tree; runs nowhere near the push loop.',
    'tools/condition_coverage.py':
        'restores ONE engine file with `git checkout -- <path>` after mutating '
        'it for coverage. Same shape, same reason.',
    'tests/seam_check/run_probe.py':
        'restores the endpoint it mutated with a targeted `git checkout --`; '
        'its own header says never a reset.',
    'tests/seam_check/run_delegation_probe.py':
        'same as run_probe.py, for the delegation seam.',
    'tests/run_gate_caller_impact_probe.py':
        '`git add -N <planted>` so a planted file is visible to the gate under '
        'test. Touches the INDEX only and never commits.',
    'tests/run_live_probe_residue_probe.py':
        'the same `git add -N` plant-and-check shape.',
    'tests/run_out_of_service_probe.py':
        'the same `git add -N` plant-and-check shape.',
    'tests/run_register_freshness_propose_probe.py':
        'stages a scratch file to drive the freshness gate. Index only.',
}


def _hooks_dir(root):
    """The directory core.hooksPath REALLY names -- not .githooks by faith."""
    try:
        p = subprocess.run(['git', 'config', '--get', 'core.hooksPath'],
                           cwd=root, capture_output=True, text=True)
        return (p.stdout or '').strip() or None
    except OSError:
        return None


def _tracked(root):
    try:
        p = subprocess.run(['git', 'ls-files'], cwd=root,
                           capture_output=True, text=True)
        return set(x.strip() for x in (p.stdout or '').split('\n') if x.strip())
    except OSError:
        return set()


def _git_verbs(src, ext, rel, notes):
    verbs = set()
    if ext == '.py':
        try:
            tree = ast.parse(src)
        except SyntaxError:
            notes.append('%s DOES NOT PARSE -- not scanned, and not a clean '
                         'answer' % rel)
            return verbs
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            nm = (f.attr if isinstance(f, ast.Attribute)
                  else (f.id if isinstance(f, ast.Name) else ''))
            if nm not in SUBPROC_NAMES:
                continue
            toks = []
            for sub in ast.walk(n):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    toks.extend(sub.value.split())
            tl = [t.lower() for t in toks]
            if nm in ('git', 'run_git') or 'git' in tl:
                for v in MUTATING_VERBS:
                    if v in tl or ('--' + v) in tl:
                        verbs.add(v)
        return verbs
    for line in src.split('\n'):
        st = line.strip()
        if st.startswith('#') or st.startswith('//') or 'git' not in line:
            continue
        for v in MUTATING_VERBS:
            if re.search(r'\b' + v + r'\b', line):
                verbs.add(v)
    return verbs


def _tracked_writes(src, ext, tracked):
    """Tracked paths this file opens FOR WRITING, read off the AST.

    THE FIRST VERSION ASKED TWO SEPARATE QUESTIONS AND AND-ed THEM: does the
    file contain a write-mode open anywhere, and does it mention a tracked path
    anywhere. Every probe in tests/ satisfies both -- it names its SUBJECT (a
    tracked file, which it only reads) and writes to a tempdir. That produced
    122 unaccounted files, which is not a finding, it is a broken clause: a
    gate that flags 122 correct files is a gate somebody deletes.
    The tracked path has to be the ARGUMENT of the write, so the two facts are
    joined at the call rather than in the file.
    """
    out = []
    if ext != '.py':
        return out
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nm = (f.attr if isinstance(f, ast.Attribute)
              else (f.id if isinstance(f, ast.Name) else ''))
        if nm != 'open':
            continue
        strs = [a.value for a in list(n.args) + [k.value for k in n.keywords]
                if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if not any(m in ('w', 'w+', 'wb', 'a', 'a+') for m in strs):
            continue
        for s in strs:
            if s in tracked:
                out.append(s)
    return out


def derive(root):
    hooks = _hooks_dir(root)
    tracked = _tracked(root)
    derived, notes = {}, []

    if not hooks:
        notes.append('core.hooksPath is NOT SET in this clone, so clause 1 '
                     'found nothing. That is a could-not-tell, not an empty '
                     'answer -- run python tools/install_git_hooks.py.')
    else:
        hd = os.path.join(root, hooks.replace('/', os.sep))
        if not os.path.isdir(hd):
            notes.append('core.hooksPath names %r and that directory does not '
                         'exist, so NO hook runs in this clone.' % hooks)
        else:
            for fn in sorted(os.listdir(hd)):
                if fn.startswith('.') or fn.endswith('.md'):
                    continue
                derived.setdefault(hooks + '/' + fn, set()).add('clause1-hook')

    for d in ('tools', 'tests', 'scripts'):
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dp, dn, fns in os.walk(base):
            dn[:] = [x for x in dn if x != '__pycache__']
            for fn in sorted(fns):
                ext = os.path.splitext(fn)[1].lower()
                if ext not in ('.py', '.js', '.sh', ''):
                    continue
                path = os.path.join(dp, fn)
                rel = os.path.relpath(path, root).replace(os.sep, '/')
                try:
                    src = io.open(path, encoding='utf-8', errors='replace').read()
                except OSError:
                    notes.append('%s UNREADABLE -- not scanned' % rel)
                    continue
                verbs = _git_verbs(src, ext, rel, notes)
                if verbs and not SANDBOX.search(src):
                    derived.setdefault(rel, set()).add(
                        'clause2-mutates-this-tree(%s)' % ','.join(sorted(verbs)))
                for lit in _tracked_writes(src, ext, tracked):
                    derived.setdefault(rel, set()).add(
                        'clause3-writes-tracked(%s)' % lit)
                    break
    return derived, notes, hooks


def cmd_derive(root):
    derived, notes, hooks = derive(root)
    declared_files = {}
    for a in ACTORS:
        declared_files.setdefault(a['file'], []).append(a['name'])

    dset, fset = set(derived), set(declared_files)
    unaccounted = sorted(dset - fset - set(OUT_OF_SCOPE))
    exempted = sorted(dset & set(OUT_OF_SCOPE))
    declared_only = sorted(fset - dset)

    print('ACTOR DERIVATION -- declared vs measured')
    print('core.hooksPath           : %s' % (hooks or 'NOT SET'))
    print('declared actors          : %d in %d file(s)'
          % (len(ACTORS), len(declared_files)))
    print('derived files            : %d' % len(dset))
    print('  also declared          : %d' % len(dset & fset))
    print('  named in OUT_OF_SCOPE  : %d' % len(exempted))
    print('  UNACCOUNTED FOR        : %d' % len(unaccounted))
    for n in notes:
        print('  NOTE: %s' % n)
    print('')
    if unaccounted:
        print('DERIVED, NEITHER DECLARED NOR EXEMPTED -- this is what blocks:')
        for rel in unaccounted:
            print('  %-46s %s' % (rel, ', '.join(sorted(derived[rel]))))
        print('')
    print('DECLARED BUT NOT DERIVED -- %d, and NOT a finding.' % len(declared_only))
    print('Clause 2 only sees a MUTATING GIT VERB, so a hook that shells out to')
    print('another tool, a regenerator that only writes a file, and several')
    print('sub-actors sharing one file are all invisible to it. A file-granular')
    print('scan cannot resolve push_retry.py into four actors.')
    for rel in declared_only:
        print('  %-46s %s' % (rel, ', '.join(declared_files[rel])))
    print('')
    if unaccounted:
        return EXIT_FINDING
    print('OK -- every derived file is either a declared actor or named in')
    print('OUT_OF_SCOPE with the reason it is not in the convergence chain.')
    return EXIT_CLEAN


# ── verification ────────────────────────────────────────────────────────────
def verify(root):
    could_not_run, findings = [], []
    for a in ACTORS:
        path = os.path.join(root, a['file'].replace('/', os.sep))
        if not os.path.isfile(path):
            could_not_run.append((a['name'], '%s does not exist' % a['file']))
            continue
        src = io.open(path, encoding='utf-8', errors='replace').read()
        n = src.count(a['anchor'])
        if n == 0:
            could_not_run.append((a['name'],
                                  '%s no longer contains its anchor %r -- the '
                                  'map cannot be checked against it'
                                  % (a['file'], a['anchor'])))
        elif n > 1:
            could_not_run.append((a['name'],
                                  '%s contains its anchor %r %d times -- an '
                                  'ambiguous anchor is not evidence'
                                  % (a['file'], a['anchor'], n)))
        for field in ('trigger', 'writes', 'self_retrigger'):
            if not a.get(field, '').strip():
                findings.append((a['name'], 'declares no %s' % field))

    # COVERAGE, read off disk rather than out of this file.
    hookdir = os.path.join(root, '.githooks')
    mapped_hooks = set(a['file'].split('/')[-1] for a in ACTORS
                       if a['kind'] == 'hook')
    if os.path.isdir(hookdir):
        for fn in sorted(os.listdir(hookdir)):
            if fn.startswith('.') or fn.endswith('.md'):
                continue
            if fn not in mapped_hooks:
                findings.append(('.githooks/' + fn,
                                 'a hook exists on disk and the map does not '
                                 'name it'))
    else:
        could_not_run.append(('.githooks', 'directory absent -- hook coverage '
                                           'was NOT checked'))

    # The GENERATED table is the loop's own source of truth; read it, do not
    # restate it. A regenerator added there and not here is exactly the drift
    # this is for.
    pr = os.path.join(root, 'tools', 'push_retry.py')
    mapped_regens = set(a['file'] for a in ACTORS if a['kind'] == 'regenerator')
    if os.path.isfile(pr):
        src = io.open(pr, encoding='utf-8', errors='replace').read()
        m = re.search(r'^GENERATED\s*=\s*\[(.*?)^\]', src, re.S | re.M)
        if not m:
            could_not_run.append(('tools/push_retry.py',
                                  'the GENERATED table could not be located -- '
                                  'regenerator coverage was NOT checked'))
        else:
            gens = re.findall(r"'(tools/[^']+\.py)'", m.group(1))
            if not gens:
                could_not_run.append(('tools/push_retry.py',
                                      'the GENERATED table parsed to zero '
                                      'regenerators, which cannot be right'))
            for g in gens:
                if g not in mapped_regens:
                    findings.append((g, 'push_retry.py regenerates it and the '
                                        'map does not name it'))
    else:
        could_not_run.append(('tools/push_retry.py',
                              'absent -- regenerator coverage was NOT checked'))

    print('REWRITE MAP VERIFY -- root %s' % root)
    print('actors declared: %d   (%d hook, %d tool, %d regenerator)'
          % (len(ACTORS),
             sum(1 for a in ACTORS if a['kind'] == 'hook'),
             sum(1 for a in ACTORS if a['kind'] == 'tool'),
             sum(1 for a in ACTORS if a['kind'] == 'regenerator')))
    print('')
    if could_not_run:
        print('COULD NOT RUN -- %d anchor(s) unresolvable. This is NOT a pass:'
              % len(could_not_run))
        for name, why in could_not_run:
            print('  %-28s %s' % (name, why))
        print('')
        print('Re-read the file, fix the anchor or the claim, and re-run.')
        return EXIT_COULD_NOT_RUN
    if findings:
        print('MAP IS STALE -- %d finding(s):' % len(findings))
        for name, why in findings:
            print('  %-28s %s' % (name, why))
        return EXIT_FINDING
    print('OK -- every anchor resolves exactly once, every actor declares its '
          'trigger,')
    print('write and self-retrigger answer, and nothing on disk is unmapped.')
    return EXIT_CLEAN


# ── the simulation ──────────────────────────────────────────────────────────
# STATE. Deliberately tiny and deliberately the five things the livelock
# actually turned on. A bigger state space would model more and prove less.
#
#   behind          commits behind origin/main
#   ledger_dirty    docs/defect-density-register.json modified, unstaged
#   generated_dirty one of the three GENERATED docs modified, unstaged
#   conflicted      unmerged paths present
#   pushed          terminal success
def step(state, enabled, inject_loop):
    """One attempt of the push loop. Returns the next state."""
    s = dict(state)

    # 1. rebase, if behind. Fires post-rewrite.
    if s['behind'] > 0 and not s['conflicted']:
        s['behind'] = 0
        if 'post_rewrite_hook' in enabled:
            # The hook re-seats and leaves the file dirty, uncommitted.
            s['ledger_dirty'] = True

    # 2. regenerate. Idempotent: re-deriving twice writes the same bytes, so
    #    generated_dirty is cleared by staging rather than reappearing.
    if 'push_retry_regenerate' in enabled:
        s['generated_dirty'] = False
        if inject_loop:
            # KNOWN-BAD: a regenerator that stamps a run time writes new bytes
            # every pass, so its own write re-triggers it forever. This is a
            # real shape -- a generator with a timestamp in its output -- and
            # it is why self_retrigger is a required field on every actor.
            s['generated_dirty'] = True

    # 3. fold the re-seat in, if it is provably nothing but shas.
    if 'fold_reseat' in enabled and s['ledger_dirty'] and not s['conflicted']:
        s['ledger_dirty'] = False

    # 4. the amend guard. Refuses on a dirty tree or unmerged paths.
    blocked = s['ledger_dirty'] or s['generated_dirty'] or s['conflicted']

    # 5. push.
    if not blocked and s['behind'] == 0:
        s['pushed'] = True
    return s


def key(s):
    return (s['behind'], s['ledger_dirty'], s['generated_dirty'],
            s['conflicted'], s['pushed'])


START_STATES = [
    ('already up to date, clean',
     dict(behind=0, ledger_dirty=False, generated_dirty=False,
          conflicted=False, pushed=False)),
    ('behind by two, clean -- the ordinary case',
     dict(behind=2, ledger_dirty=False, generated_dirty=False,
          conflicted=False, pushed=False)),
    ('behind, and a generated doc already modified',
     dict(behind=1, ledger_dirty=False, generated_dirty=True,
          conflicted=False, pushed=False)),
    ('behind, and the register already re-seated by a previous attempt',
     dict(behind=1, ledger_dirty=True, generated_dirty=False,
          conflicted=False, pushed=False)),
    ('conflicted -- must stop, and stopping IS a fixed point',
     dict(behind=1, ledger_dirty=False, generated_dirty=False,
          conflicted=True, pushed=False)),
]


def simulate(steps, without, inject_loop):
    enabled = set(BY_NAME) - set(without)
    print('REWRITE CHAIN SIMULATION -- %d step budget' % steps)
    if without:
        print('ABLATED: %s' % ', '.join(without))
    if inject_loop:
        print('INJECTED: a regenerator whose own write re-triggers it')
    print('')
    bad = []
    for label, start in START_STATES:
        seen = {key(start): 0}
        s = start
        verdict = None
        for i in range(1, steps + 1):
            s = step(s, enabled, inject_loop)
            k = key(s)
            if s['pushed']:
                verdict = 'PUSHED at step %d' % i
                break
            if k in seen:
                if k == key(start) and i == 1:
                    verdict = 'FIXED POINT at step %d (no progress possible)' % i
                else:
                    verdict = ('CYCLE -- step %d returns to step %d with no push'
                               % (i, seen[k]))
                break
            seen[k] = i
        if verdict is None:
            verdict = 'DID NOT SETTLE within %d steps' % steps
        ok = verdict.startswith('PUSHED') or verdict.startswith('FIXED POINT')
        if not ok:
            bad.append((label, verdict))
        print('  %-4s %-58s %s' % ('ok' if ok else 'BAD', label, verdict))
    print('')
    if bad:
        print('NON-CONVERGENT -- %d start state(s) never settle:' % len(bad))
        for label, verdict in bad:
            print('  %s -> %s' % (label, verdict))
        print('')
        print('This is the nine-commit livelock shape: every actor individually')
        print('correct, the composition with no fixed point.')
        return EXIT_FINDING
    print('OK -- every start state reaches a push or a fixed point.')
    return EXIT_CLEAN


def print_map(as_json):
    if as_json:
        print(json.dumps({'actors': ACTORS}, indent=1))
        return EXIT_CLEAN
    print('# Hook and tool rewrite map')
    print('')
    print('Generated by `tools/rewrite_convergence_map.py --map`. Verify with')
    print('`--verify`; the convergence claim is checked by `--simulate`.')
    print('')
    for kind in ('hook', 'tool', 'regenerator'):
        print('## %ss' % kind.capitalize())
        print('')
        for a in ACTORS:
            if a['kind'] != kind:
                continue
            # ASCII only. This output is redirected into a .md file by a shell
            # whose default encoding is cp1252, and an em-dash lands there as a
            # replacement character. Not worth a codec argument for a hyphen.
            print('### `%s` -- `%s`' % (a['name'], a['file']))
            print('')
            print('- **Anchor (must appear exactly once):** `%s`' % a['anchor'])
            print('- **Trigger:** %s' % a['trigger'])
            print('- **Writes:** %s' % a['writes'])
            print('- **Can its own write re-trigger it?** %s' % a['self_retrigger'])
            print('')
    return EXIT_CLEAN


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--map', action='store_true')
    g.add_argument('--verify', action='store_true')
    g.add_argument('--simulate', action='store_true')
    g.add_argument('--derive', action='store_true',
                   help='derive the actor set from the repo by three clauses '
                        'and compare it to the declaration')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--root', default=REPO)
    ap.add_argument('--steps', type=int, default=12)
    ap.add_argument('--without', action='append', default=[],
                    help='ablate a named actor -- the known-bad control')
    ap.add_argument('--inject-loop', action='store_true',
                    help='known-bad control: a regenerator that re-triggers itself')
    a = ap.parse_args(argv)

    if a.map:
        return print_map(a.json)
    if a.verify:
        return verify(a.root)
    if a.derive:
        return cmd_derive(a.root)
    for w in a.without:
        if w not in BY_NAME:
            print('COULD NOT RUN -- no actor named %r. Known: %s'
                  % (w, ', '.join(sorted(BY_NAME))))
            return EXIT_COULD_NOT_RUN
    return simulate(a.steps, a.without, a.inject_loop)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
