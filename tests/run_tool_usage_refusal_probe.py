# OWNER: hank
"""run_tool_usage_refusal_probe.py -- a tool invoked with no argument must PRINT
USAGE AND EXIT 2, not traceback.

    python tests/run_tool_usage_refusal_probe.py
    python tests/run_tool_usage_refusal_probe.py --selftest

EXIT 0 every subject refuses properly, 1 at least one does not, 2 COULD NOT RUN.

── WHY EXIT 2 AND NOT EXIT 1 ───────────────────────────────────────────────
On this platform **exit 1 means FINDINGS** and **exit 2 means COULD NOT RUN**.
An uncaught `IndexError` exits 1. So a tool that tracebacks on a missing
argument is INDISTINGUISHABLE, to anything reading an exit code, from a tool
that ran and found something -- which is the third-state collapse PR §1.11
names, arriving through a missing `len(sys.argv)` check.

── MEASURED, 2026-10-07, all 315 scripts under tools/ ──────────────────────
**8 of 315 tracebacked on a bare run. 67 refused in words.** So the convention
was already overwhelmingly established and these eight were the exceptions --
which is what makes it a defect rather than a missing feature.

── IT FAILS BEFORE THE FIX, AND THAT IS CHECKED, NOT CLAIMED ───────────────
Every subject below exited **1** with `IndexError: list index out of range`
before this batch. Arm B drives each one and asserts **2**, so running this
probe against the parent commit turns every arm red. The before-state is in
`scratchpad/before.<tool>`.

── WHAT THIS DOES NOT COVER ────────────────────────────────────────────────
**ALL EIGHT ARE NOW FIXED.** `tools/gh_push.py:182` was the last one and is not
an arm here, deliberately: it is OWNED (`docs/tool-owner-map.json` says `cc`),
it was fixed under that ownership at `cd8b815b`, and it is locked by
`tests/run_gh_push_argv_probe.py`. A second lock on the same line in this file
would be a second copy of the same check, which is the duplication rule this
platform already pays for -- so the citation points there instead.

`tools/va_rule_currency.py` WAS on that routing list and is now a subject. Its
map entry is `"basis": "UNRECORDED", "owner": null` -- no OWNER line and no
claim has ever named it, though the file HAS history. Nobody to route TO is not
deferring the decision, it is declining to make one. Taken under this session's
claim, stated rather than done quietly.

BASIS RENAMED 2026-10-07: the two paragraphs above read `"basis": "NONE" --
**no owner at all**, not UNKNOWN`, a consumer re-interpreting the field in
prose because one `NONE` carried two opposite facts. UNRECORDED and UNKNOWN are
now separate states in the map and the gloss is gone.

**Its refusal is the only one of the seven that needs TWO arguments**, and the
second is not cosmetic: `wanted = sys.argv[2:]`, so an empty `wanted` does not
raise -- the loop's `name not in wanted` test matches nothing and the tool
prints NOTHING and exits 0. Silent success on a run that examined no rule is
worse than the traceback it replaces, because a caller cannot tell it from
"every rule is clean". Arm C drives that case specifically.

It also does not check that a subject still WORKS with a real argument -- that is
a different question, and it is answered separately in the commit message by
driving each one against a real file.
"""
import io
import os
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-10-07.1'

# The six this session claimed and fixed. LISTED HERE rather than discovered by
# scanning tools/ for `sys.argv[1]`: a probe that derives its own population
# from its subject cannot see the population change, and a newly-added tool with
# the same defect should be a NEW finding somebody looks at, not silently
# absorbed into this arm.
SUBJECTS = [
    'checkblocks.py',
    'div_balance_check.py',
    'extract_scripts.py',
    'js_code_only_diff.py',
    'literal_drift_check.py',
    'nav_panel_check.py',
    # ── THE SEVENTH, ADDED 2026-10-07 ────────────────────────────────────
    # Previously in NOT_MINE below as "no OWNER line, no claim has ever named
    # it". That is still true, and it is the REASON it moved here rather than
    # an objection to it: docs/tool-owner-map.json records
    # `"basis": "UNRECORDED", "owner": null` -- no owner recorded, so there is
    # nobody to route TO, and leaving it on the routing list was not deferring
    # the decision, it was declining to make one.
    'va_rule_currency.py',
]
# Named so the probe reports them every run rather than leaving them to a
# document nobody opens. NONE LEFT as of 2026-10-07: gh_push.py:182 was the
# last, it IS owned (docs/tool-owner-map.json says `cc`), it was fixed under
# that ownership at cd8b815b, and tests/run_gh_push_argv_probe.py locks it. An
# EMPTY list is the honest state and is printed as such rather than deleted --
# a routing list that disappears reads as "there was never one".
NOT_MINE = []


def main(argv):
    print('TOOL USAGE REFUSAL -- criteria %s' % CRITERIA_VERSION)
    print('  subjects (this session\'s claim) : %d' % len(SUBJECTS))
    print('  same defect, NOT mine, routed   : %s'
          % ('; '.join(NOT_MINE) if NOT_MINE
             else 'NONE OUTSTANDING -- the last, gh_push.py:182, was fixed at '
                  'cd8b815b under its own ownership and is locked by '
                  'tests/run_gh_push_argv_probe.py'))
    print('')
    missing = [s for s in SUBJECTS
               if not os.path.isfile(os.path.join(REPO, 'tools', s))]
    if missing:
        print('COULD NOT RUN: these subjects are not on disk: %s'
              % ', '.join(missing))
        print('Nothing was driven. This is NOT "they all refuse properly".')
        return 2

    npass = nfail = 0

    def ck(label, cond, extra=''):
        nonlocal npass, nfail
        if cond:
            npass += 1
            print('  ok   ' + label)
        else:
            nfail += 1
            print('  FAIL ' + label)
            if extra:
                print('       ' + str(extra)[:300])

    for s in SUBJECTS:
        p = subprocess.run([sys.executable, os.path.join('tools', s)],
                           cwd=REPO, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=60)
        out = p.stdout.decode('utf-8', 'replace')
        ck('B. %-24s bare run exits 2, not 1' % s, p.returncode == 2,
           'exit=%d  %s' % (p.returncode, out.strip().split('\n')[-1][:160]))
        ck('B. %-24s ...and says COULD NOT RUN and prints a usage line, so the '
           'reader is told WHAT is missing rather than shown a stack' % s,
           'COULD NOT RUN' in out and 'usage:' in out, out[:200])
        ck('B. %-24s ...and does NOT traceback -- a stack trace is what makes '
           'this indistinguishable from a real failure' % s,
           'Traceback (most recent call last)' not in out, out[:200])

    # ── C. THE PARTIAL-ARGUMENT CASE, WHICH ARM B CANNOT SEE ─────────────
    # va_rule_currency.py takes TWO arguments. Given only the first, the old
    # code did not raise -- it matched no rule, printed nothing and exited 0.
    # Arm B drives a BARE run, which the IndexError already covered, so arm B
    # alone would have gone green over a silent-success path. This arm is the
    # one that would have been red.
    p = subprocess.run([sys.executable, os.path.join('tools', 'va_rule_currency.py'),
                        os.path.join('tests', 'run_tool_usage_refusal_probe.py')],
                       cwd=REPO, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    out = p.stdout.decode('utf-8', 'replace')
    ck('C. va_rule_currency.py with a FILE but NO RULE exits 2, not 0. Exit 0 '
       'with no output is indistinguishable from "every rule is clean", and '
       'arm B cannot reach this case at all', p.returncode == 2,
       'exit=%d  out=%r' % (p.returncode, out[:160]))
    ck('C. ...and names which argument is missing, not just that one is',
       'no rule to look for' in out, out[:200])

    print('')
    print('%d passed, %d failed' % (npass, nfail))
    return 1 if nfail else 0


if __name__ == '__main__':
    sys.exit(main([a for a in sys.argv[1:] if a != '--selftest']))
