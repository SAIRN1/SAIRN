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
Two of the eight are NOT in this list and are not fixed:
`tools/gh_push.py` and `tools/va_rule_currency.py`. `tools/tool_owner_map.py`
reports `va_rule_currency.py` as having **no `# OWNER:` line and no claim that
has ever named it**, and `gh_push.py` as UNKNOWN rather than unowned. Neither is
in this session's claim, so both are listed for routing instead of edited.

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
]
# Named so the probe reports them every run rather than leaving them to a
# document nobody opens.
NOT_MINE = ['gh_push.py (owner UNKNOWN)',
            'va_rule_currency.py (no OWNER line, no claim has ever named it)']


def main(argv):
    print('TOOL USAGE REFUSAL -- criteria %s' % CRITERIA_VERSION)
    print('  subjects (this session\'s claim) : %d' % len(SUBJECTS))
    print('  same defect, NOT mine, routed   : %s' % '; '.join(NOT_MINE))
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

    print('')
    print('%d passed, %d failed' % (npass, nfail))
    return 1 if nfail else 0


if __name__ == '__main__':
    sys.exit(main([a for a in sys.argv[1:] if a != '--selftest']))
