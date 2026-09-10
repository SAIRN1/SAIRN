"""Run the checkers that have been PROMOTED to report-only, and say what they find.

    python tools/report_only_checks.py            # full sweep, by hand
    python tools/report_only_checks.py --hook     # PostToolUse, reads a payload

── WHY THIS EXISTS ──────────────────────────────────────────────────────────
`docs/2026-09-09-tooling-inventory.md` found 28 working checkers in `tools/`
that nothing runs. Several were written in response to a real production
incident, proved on that incident, committed, and have not looked at the
codebase since. Three of them are named as REQUIRED by `sairn-guardian-v2` or
`CLAUDE.md` and were still unwired.

Wiring each one as its own hook entry would be 28 hook entries, 28 places to
keep in step, and 28 chances to repeat the `"if": "Bash(git push*)"` mistake.
This is ONE runner with a REGISTRY, so promoting the next checker is a registry
entry rather than a new hook -- the same argument
`tests/suite_control_backfill_probe.py` makes for one table instead of five
harnesses.

── REPORT-ONLY, AND WHY THAT IS NOT TIMIDITY (Michael's decision, 2026-09-09)
None of these had ever run against real code, so their real-world
false-positive rate was genuinely unknown. The first run proved that was the
right worry: `nav_panel_check.py` reported ALL 26 of SAIRNfreedom's panels
unreachable, because it scans `<button>` and that app navigates with
`<div class="nitem" onclick="sfNav('x')">`. Wired blocking, it would have
refused every SAIRNfreedom push while the app was fine. It is NOT in the
registry below until that is fixed.

So: same promotion path as push-gate checks 5 and 7 and `run_all_tests.py`
itself -- report-only until quiet in practice, then promoted individually.
**THE HOOK EXITS 0 ALWAYS.** The only thing it can do is say something.

Run by hand it exits 1 on findings, so a person can chain it. That asymmetry is
deliberate and is the whole difference between a report and a gate.

── SILENT ON A CLEAN RUN ────────────────────────────────────────────────────
A notice that fires on every push is a notice nobody reads. But a checker that
COULD NOT RUN does notify, because "could not run" being invisible is the
failure `run_all_tests.py` was built to end.

── NO LOCK, DELIBERATELY, AND THE DIFFERENCE MATTERS ────────────────────────
`run_all_tests.py` takes a per-clone lock because the probes it runs MUTATE
tracked files, and two runs corrupt each other's restores (2026-09-09). Every
checker here is READ-ONLY. Concurrent runs waste a little CPU and cannot
corrupt anything, and adding a lock would be machinery bought for a risk that
does not exist. If a MUTATING tool is ever added to this registry, that
reasoning stops holding -- take the lock then, and say so here.
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
# THE PUSH GATE IS IMPORTED, NOT COPIED. `tools/sairn_claim_hook.py` once
# carried its own copy of a line that had already been fixed in
# `tools/sairn_claim.py`, so the fix reached the tool a human invokes and
# missed the one that runs unattended. One definition, one place to fix.
from run_all_tests import pushes                                  # noqa: E402


def app_files(verbose=False):
    """Every LIVE app HTML file, derived from git rather than a hand list.

    TOP LEVEL ONLY, and that is a rule rather than a convenience: `vercel.json`
    routes every app from a file in the repo root, so a `.html` in a
    subdirectory is by definition not served.

    FOUND BY WIRING IT, 2026-09-09: the first version was a bare
    `git ls-files '*.html'` and it swept
    `archive/branch-lucid-ptolemy-b73vu0/`, the preserved ancestor branch --
    twelve dead 2026-06 snapshots that CLAUDE.md says explicitly are kept for
    provenance and must not be run or recreated. It reported 13 findings, 12 of
    them in code nobody deploys, which is exactly how a report-only checker
    earns the reputation that gets it switched off before it is ever promoted.

    The exclusion is PRINTED rather than silent -- a category quietly dropped
    is how a real file hides, the same argument `run_all_tests.py` makes for
    its UNRUN section.
    """
    r = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                       capture_output=True, text=True)
    every = sorted(f for f in r.stdout.split('\n') if f.strip())
    live = [f for f in every if '/' not in f]
    if verbose and len(every) != len(live):
        print('   (not scanned: %d non-root .html file(s) -- not routed by '
              'vercel.json, e.g. %s)'
              % (len(every) - len(live),
                 ', '.join(f for f in every if '/' in f)[:70]))
    return live


def by_exit(rc, out):
    """A checker that exits non-zero on a finding. Returns (findings, detail)."""
    return ([l for l in out.splitlines() if l.startswith('  - ') or
             l.startswith('FAIL')] or ['exit %d' % rc], out) if rc else ([], out)


# Sections of sairn_dead_button_audit.py that are DEFECTS, per the tool's own
# labelling. C1/C2 are OPPOSITE fixes and the tool says in its own output that
# they need a human read; D2 it labels "informational, count only".
#
# THIS IS A DELIBERATE NARROWING AND IT IS STATED RATHER THAN QUIET, because a
# silent category exclusion is exactly how a real finding hides -- the argument
# `run_all_tests.py` makes for its own UNRUN section. What it hides: on
# 2026-09-09 the full sweep found C1=1 on stonedesk.html (`notify()`, a
# showToast alias with 111 callers -- a false positive of that heuristic),
# C1=2 on sairnmechanical.html, and D2 on six apps. Run the tool directly to
# see them; `--all-sections` below prints them here.
DEFECT_SECTIONS = ('A.', 'B.', 'C2.', 'D1.')
COUNT_RE = re.compile(r'^([A-E]\d?)\..*?->\s*(\d+)\s*$')


def by_section(rc, out):
    """sairn_dead_button_audit.py ALWAYS exits 0 -- parse its sections.

    That is worth naming: a checker that cannot fail by exit code cannot be
    wired by exit code, which is a fair part of why this one sat unwired while
    being named as required by Guardian check 27.
    """
    findings, info = [], []
    for line in out.splitlines():
        m = COUNT_RE.match(line.strip())
        if not m or m.group(2) == '0':
            continue
        (findings if (m.group(1) + '.') in DEFECT_SECTIONS else info).append(
            line.strip())
    return findings, out


REGISTRY = [
    {
        'tool': 'vercel_config_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-09',
        'catches': "a buildCommand over Vercel's 256-char schema limit, and a "
                   "route whose destination file no cp copies",
        'why_it_matters': "a failed production deploy KEEPS SERVING the last "
                          "good build, so every later push reports clean while "
                          "production stays on old code -- that really happened "
                          "on 2026-07-30 and is why Guardian names this check",
        'evidence': 'real run 2026-09-09: buildCommand 92/256, PASS',
    },
    {
        'tool': 'sairn_dead_button_audit.py',
        'mode': 'apps',
        'verdict': by_section,
        'promoted': '2026-09-09',
        'catches': 'a handler target never defined (A), an inline handler whose '
                   'only action is a toast (B), a toast-only function with zero '
                   'callers (C2), and a same-scope duplicate definition (D1)',
        'why_it_matters': 'Guardian check 27 says run it against every app file '
                          'before declaring it done, and nothing ever did',
        'evidence': 'real run 2026-09-09 over all 22 app files: A=0 B=0 C2=0 '
                    'across every app, D1=1 on sairnmechanical.html (two '
                    'mechEsc definitions in one script block)',
    },
    {
        'tool': 'nav_panel_check.py',
        'mode': 'apps',
        'verdict': by_exit,
        'promoted': '2026-09-09, AFTER its matcher was fixed -- NOT as it stood',
        'catches': 'a panel no nav control reaches (Guardian checks 16-18), and '
                   'a duplicate id in static markup',
        'why_it_matters': "the safe-editing rules say run it after EVERY edit, "
                          "and nothing ever did",
        'evidence': 'its FIRST real run reported ALL 26 sairnfreedom panels '
                    'unreachable -- it scanned <button> and that app navigates '
                    'with <div class="nitem" onclick="sfNav(...)">. The element '
                    'is now derived like the class, the id and the function name '
                    'already were; re-run over all 22 apps: 22 PASS, 0 FAIL. '
                    'Held in BOTH directions by tests/run_report_only_checks_probe.py',
    },
    {
        'tool': 'cleanup_confirm_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-10, written the same day for a rule that existed '
                    'since 2026-08-26 with no mechanism behind it',
        'catches': 'a cleanup or migration file whose destructive statements '
                   'carry no confirm query and no expected answer -- so nobody '
                   'can ever establish what it did',
        'why_it_matters': 'the Supabase editor returns SUCCESS for the '
                          'statements it DID run, so a multi-statement paste '
                          'that stops halfway is indistinguishable from a '
                          'complete one. Two real cases on 2026-08-26',
        'evidence': 'first real run flagged 4 of 26 files; hand-reading every '
                    'one showed 2 real (sairndesign/sairnlegacy synctest, both '
                    'since given confirm blocks) and 2 false positives that '
                    'became fixtures -- a commented "not this run\'s debris" '
                    'delete, and a menu-only file. 26 files, 0 gaps now. Held '
                    'in both directions by tests/run_cleanup_confirm_probe.py',
    },
]


def run_one(entry, show_all, verbose=False):
    tool = entry['tool']
    targets = app_files(verbose) if entry['mode'] == 'apps' else [None]
    findings, unrun = [], []
    for t in targets:
        cmd = [sys.executable, os.path.join('tools', tool)] + ([t] if t else [])
        try:
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                               timeout=300)
        except Exception as e:                       # noqa: BLE001
            unrun.append('%s %s -- %s' % (tool, t or '', e))
            continue
        out = (r.stdout or '') + (r.stderr or '')
        got, _ = entry['verdict'](r.returncode, out)
        for g in got:
            findings.append('%s %s -- %s' % (tool, t or '', g.strip()))
        if show_all and out.strip():
            print('    ' + out.strip().replace('\n', '\n    '))
    return findings, unrun


def sweep(show_all=False, quiet=False):
    findings, unrun = [], []
    for entry in REGISTRY:
        if not quiet:
            print('-- %s --' % entry['tool'])
        f, u = run_one(entry, show_all, verbose=not quiet)
        findings += f
        unrun += u
        if not quiet:
            print('   %d finding(s), %d could not run' % (len(f), len(u)))
    return findings, unrun


def hook_main():
    # THE PAYLOAD IS THE GATE, and it is checked HERE rather than trusted to
    # `.claude/settings.json`. A hook entry's only gate is `matcher`, which
    # matches the TOOL NAME -- an `"if"` key is ignored in silence, which on
    # 2026-09-09 ran the full mutating test suite after every Bash tool call.
    # A HOOK THAT LOOKS GATED IN CONFIG IS UNGATED UNTIL THE HOOK ITSELF
    # CHECKS. Same reasoning and the same imported matcher as run_all_tests.py.
    try:
        payload = json.load(sys.stdin)
    except Exception:                                # noqa: BLE001
        payload = {}
    cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''
    # An absent or unreadable payload falls through and runs: that is this file
    # invoked by hand with --hook, and it is the same fail-open standard the
    # other hooks here hold.
    if payload and not pushes(cmd):
        return 0
    findings, unrun = sweep(quiet=True)
    if not findings and not unrun:
        return 0
    lines = []
    if findings:
        lines.append('%d report-only finding(s) after this push:' % len(findings))
        lines += ['  ' + f for f in findings[:12]]
    if unrun:
        lines.append('%d checker(s) COULD NOT RUN, so they verified nothing:'
                     % len(unrun))
        lines += ['  ' + u for u in unrun[:6]]
    lines.append('Run `python tools/report_only_checks.py` for the whole picture.')
    lines.append('REPORT ONLY -- this hook never blocks a push. These checkers '
                 'are on the same promotion path as push-gate checks 5 and 7: '
                 'blocking only once each has been quiet in practice.')
    print(json.dumps({
        'systemMessage': 'Report-only checkers: %d finding(s), %d unrun.'
                         % (len(findings), len(unrun)),
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': '\n'.join(lines),
        },
    }))
    return 0


def main(argv):
    if '--hook' in argv:
        return hook_main()
    if '--list' in argv:
        for e in REGISTRY:
            print('%-32s promoted %s (%s)' % (e['tool'], e['promoted'], e['mode']))
            print('    catches : %s' % e['catches'])
            print('    matters : %s' % e['why_it_matters'])
            print('    evidence: %s' % e['evidence'])
        return 0
    findings, unrun = sweep(show_all='--all-sections' in argv)
    print('')
    if unrun:
        print('COULD NOT RUN (%d) -- not a pass:' % len(unrun))
        for u in unrun:
            print('    %s' % u)
    if findings:
        print('FINDINGS (%d):' % len(findings))
        for f in findings:
            print('    %s' % f)
        print('')
        print('REPORT ONLY. Nothing here blocked anything. Read each one before '
              'acting -- these checkers have run against real code exactly once.')
    else:
        print('CLEAN -- %d promoted checker(s), no findings.' % len(REGISTRY))
    return 1 if (findings or unrun) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
