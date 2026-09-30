#!/usr/bin/env python
"""run_selftest_hygiene_sweep.py -- does any selftest WRITE outside a temp
directory? Built 2026-09-29 after hover_backup_mirror.py's selftest, run
from the platform-repo copy, git-inited a nested repository into the
platform worktree -- a selftest that mutates its surroundings is the
defect, wherever it happens to be launched from.

METHOD, per tool: snapshot BEFORE (git status --porcelain of the PLATFORM
repo + a recursive name/size/mtime listing of the live tool directory and
of a scratch launch cwd), run the selftest with cwd = a fresh scratch
directory, snapshot AFTER, and assert the three surfaces are unchanged:
(1) the platform repo's porcelain output, (2) the tool directory listing
MINUS the per-tool EXPECTED set (files a given selftest legitimately
touches in its own home, each named with the reason), (3) the launch cwd
(must stay empty -- a selftest that drops files into whatever directory
it was launched from is the exact wrong-directory hazard).

KNOWN-BAD CONTROL, run FIRST on every invocation: a planted fake tool
whose "selftest" writes a file into its launch cwd MUST fail assertion
(3). If the harness ever stops seeing that plant, the sweep's own passes
mean nothing -- the same fixture-lock discipline every checker here
carries.

Exit 0: control caught the plant AND every real selftest left all three
surfaces clean. Exit 1: a hit (named, with the paths that changed).
Exit 2: could not run.
"""
import os
import subprocess
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PLATFORM_REPO = os.path.join(os.path.expanduser('~'), 'Documents', 'SAIRN-hover')

# (tool, argv, expected-relative-paths-in-HERE that this selftest MAY touch,
#  each with the reason it is exempt)
SELFTESTS = [
    ('hover_log.py', ['--selftest'], {}),
    ('hover_backup_mirror.py', ['--selftest'], {
        # its fixtures snapshot/commit the REAL mirror repo's allowlist trio
        # by design (the token-gitignore and record-anchor arms run against
        # the real HERE) -- mirror bookkeeping, not contamination:
        '.git': 'the mirror repo itself; fixture arms commit real snapshots',
        'hover-audit-log.jsonl': 'read only, but mtime can update on Windows',
    }),
    ('hover_cold_scan_pool.py', ['--selftest'], {}),
    ('hover_tip_beacon.py', ['--selftest'], {}),
    ('hover_self_health_hook.py', ['--selftest'], {
        'hover_self_health_fires.jsonl':
            'T-OWNER runs the real hook against the real clone, which '
            'appends a fire record -- the hook is doing its job',
    }),
    ('hover_editor_review.py', ['--fixtures'], {}),
    ('run_editor_review_v3_known_bad_control.py', [], {}),
    ('hover_watchlist.py', ['--selftest'], {}),
    ('hover_duplicate_finding_check.py', ['--selftest'], {}),
    ('hover_pure_js_exec.py', ['--selftest'], {}),
    ('hover_second_opinion.py', ['--selftest'], {}),
    ('hover_claim_precheck.py', ['--selftest'], {}),
    ('hover_coverage_ledger.py', ['--selftest'], {}),
    ('hover_live_refusal_check.py', ['--selftest'], {}),
    ('sabotage_claim_verify.py', ['--selftest'], {}),
    ('tool_provenance_check.py', ['--selftest'], {}),
    ('scope_narrowing_check.py', ['--selftest'], {}),
    ('undirected_sweep_freshness.py', ['--selftest'], {}),
    ('verbalized_audit_awareness_scan.py', ['--selftest'], {}),
    ('peer_authority_trace_scan.py', ['--selftest'], {}),
    ('flagged_then_argued_down_scan.py', ['--selftest'], {}),
    ('git_history_secrets_scan.py', ['--selftest'], {}),
    ('code_quality_baseline.py', ['--selftest'], {}),
    ('hover_self_health.py', ['--selftest'], {}),
]

PLANT = r'''
import os, sys
# the KNOWN-BAD shape: a "selftest" that writes into its launch cwd
open(os.path.join(os.getcwd(), 'contamination_marker.txt'), 'w').write('bad')
print('1 ok, 0 failed')
'''


def listing(root, skip_names=()):
    out = {}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for f in files:
            if f.endswith('.pyc'):
                continue
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root)
            top = rel.replace('\\', '/').split('/')[0]
            if top in skip_names or rel in skip_names:
                continue
            try:
                st = os.stat(p)
                out[rel] = (st.st_size, st.st_mtime_ns)
            except OSError:
                out[rel] = ('unstatable', 0)
    return out


def porcelain():
    r = subprocess.run(['git', 'status', '--porcelain'], cwd=PLATFORM_REPO,
                       capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        return None
    return r.stdout


def run_one(tool_path, argv, expected, label):
    """Returns list of violation strings (empty = clean)."""
    cwd = tempfile.mkdtemp(prefix='hygiene_cwd_')
    viol = []
    try:
        skip = set(expected)
        before_repo = porcelain()
        before_dir = listing(HERE, skip)
        r = subprocess.run([sys.executable, tool_path] + argv, cwd=cwd,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=600)
        after_repo = porcelain()
        after_dir = listing(HERE, skip)
        cwd_files = os.listdir(cwd)
        if before_repo is None or after_repo is None:
            viol.append('%s: COULD NOT read platform-repo porcelain' % label)
        elif before_repo != after_repo:
            viol.append('%s: PLATFORM REPO CHANGED:\n%s' % (
                label, '\n'.join(sorted(set(after_repo.splitlines())
                                        ^ set(before_repo.splitlines())))))
        if before_dir != after_dir:
            changed = sorted(set(before_dir) ^ set(after_dir)
                             | {k for k in before_dir
                                if k in after_dir and before_dir[k] != after_dir[k]})
            viol.append('%s: TOOL DIR CHANGED (beyond expected %s): %s'
                        % (label, sorted(skip) or '(none)', changed[:10]))
        if cwd_files:
            viol.append('%s: WROTE INTO LAUNCH CWD: %s' % (label, cwd_files))
        if r.returncode not in (0, 1, 2):
            viol.append('%s: crashed rc=%d: %s' % (label, r.returncode,
                                                   (r.stderr or '')[:200]))
    finally:
        shutil.rmtree(cwd, ignore_errors=True)
    return viol


def main():
    # ── THE CONTROL FIRST, every run ────────────────────────────────────────
    plant_dir = tempfile.mkdtemp(prefix='hygiene_plant_')
    plant = os.path.join(plant_dir, 'planted_bad_selftest.py')
    open(plant, 'w', encoding='utf-8').write(PLANT)
    try:
        v = run_one(plant, [], {}, 'KNOWN-BAD PLANT')
        caught = any('WROTE INTO LAUNCH CWD' in x for x in v)
        if not caught:
            print('CONTROL FAILED: the planted cwd-writing selftest was NOT '
                  'caught -- this sweep can prove nothing. Violations seen: %r' % v)
            return 2
        print('control: the planted cwd-writing selftest IS caught (%d '
              'violation(s) incl. the cwd write) -- harness has teeth' % len(v))
    finally:
        shutil.rmtree(plant_dir, ignore_errors=True)

    hits = []
    for tool, argv, expected in SELFTESTS:
        path = os.path.join(HERE, tool)
        if not os.path.isfile(path):
            hits.append('%s: MISSING -- could not run (named, not skipped)' % tool)
            continue
        v = run_one(path, argv, expected, tool)
        if v:
            hits.extend(v)
            print('HIT  %s' % tool)
        else:
            print('ok   %s' % tool)

    print()
    if hits:
        print('%d violation(s):' % len(hits))
        for h in hits:
            print('  ' + h)
        return 1
    print('all %d selftests left the platform repo, the tool directory and '
          'their launch cwd unchanged.' % len(SELFTESTS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
