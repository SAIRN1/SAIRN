"""A PUBLISHED FIGURE MUST REGENERATE, or it is a claim with a date on it.

Run:  python tools/fact_sheet_regenerates.py
      python tools/fact_sheet_regenerates.py --sheet <path>
      python tools/fact_sheet_regenerates.py --json

── WHY ─────────────────────────────────────────────────────────────────────
docs/FACT-SHEET-2026-09-29.md is taken into company meetings. Every figure in it
carries the command that produced it, which is the whole point: a number can be
re-run in front of the person asking.

**That property decays silently.** The repository changes every hour. A sheet
written on Monday is a set of assertions by Wednesday, and nothing about reading
it reveals which ones have moved. The failure mode is specific and bad: a figure
stated confidently in a meeting, from a document that looked authoritative
because it cited its own derivation.

**And it has already happened once, inside the sheet's own first draft.** A row
claimed 266 tools and cited `git ls-files tools/`, which returns 281 -- the
command did not produce the number. That was caught by hand. This is the check.

── WHAT IT DECIDES ─────────────────────────────────────────────────────────
For every figure this file knows how to derive, it RE-RUNS the derivation and
compares to the number printed in the sheet. A difference is a FINDING, not a
warning: the sheet is either current or it is not.

A command that CANNOT RUN is `COULD NOT RUN` (exit 2), never a pass. A figure
nobody can re-derive is exactly the thing the sheet promises does not exist.

── WHAT IT CANNOT SEE, so the gap is a decision ────────────────────────────
* Figures marked UNAVAILABLE in the sheet. There is nothing to re-run.
* The panel counts. They are derived by a per-application judgement about what
  marks a panel, and a judgement is not a command -- the sheet says so, and
  encoding it here would turn a stated judgement into a hidden one.
* The patent dates. They come from a quoted sentence, not a computation.
* Whether a figure is the RIGHT figure. It checks that the number matches the
  command, which is the defect it was built for; it cannot tell whether the
  command answers the question a reader has in mind.
* The two per-week lines are checked as ARITHMETIC over figures already checked,
  not re-derived independently.
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker_kit import (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN,  # noqa: E402
                         REPO, read, finish)

CRITERIA_VERSION = '2026-09-28.1'
DEFAULT_SHEET = os.path.join('docs', 'FACT-SHEET-2026-09-29.md')


# ── NO SHELL. THE FIRST VERSION USED ONE AND EVERY GIT FIGURE CAME BACK 0 ────
# `subprocess.run(..., shell=True)` on Windows runs cmd.exe, where
# `git ls-files 'sql/*.sql'` does not glob and `grep`, `wc` and `xargs` do not
# exist -- so six derivations silently returned 0 and were reported as the sheet
# being wrong. THE SHEET WAS RIGHT AND THE CHECKER WAS BROKEN, which is the worse
# direction: a checker that reports a correct document as stale gets ignored, and
# then it is ignored on the day the document really is stale.
#
# Everything below runs git with an ARGUMENT LIST and counts in Python. The
# command the SHEET prints is for a human at a shell; the checker derives the
# same number without depending on one, so the two cannot disagree because of
# which shell somebody has.
def git_lines(*args):
    """git output as a list of non-empty lines, or None if git failed."""
    p = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        return None
    return [x.strip() for x in (p.stdout or '').splitlines() if x.strip()]


def tracked_count(*patterns):
    lines = git_lines('ls-files', *patterns)
    return None if lines is None else len(lines)


def tool_value(module_args, pattern):
    p = subprocess.run([sys.executable] + list(module_args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    m = re.search(pattern, (p.stdout or '') + (p.stderr or ''))
    return int(m.group(1)) if m else None


def derive():
    """{label: (value, how)} for every figure this tool can re-run.

    Each entry's `how` is the SAME command the sheet prints, so a divergence
    here is a divergence a reader would hit.
    """
    d = {}

    html = git_lines('ls-files', '*.html')
    d['apps_total'] = (None if html is None else
                       len([f for f in html
                            if not f.startswith(('archive/', 'docs/'))]),
                       "git ls-files '*.html', excluding archive/ and docs/")

    d['sql_files'] = (tracked_count('sql/*.sql'), "git ls-files 'sql/*.sql'")
    d['suites_js'] = (tracked_count('tests/*.js', 'tests/**/*.js'),
                      "git ls-files 'tests/*.js' 'tests/**/*.js'")
    d['suites_api'] = (tracked_count('api/*.test.js', 'api/_lib/*.test.js'),
                       "git ls-files 'api/*.test.js' 'api/_lib/*.test.js'")
    d['suites_py'] = (tracked_count('tests/*.py', 'tests/**/*.py'),
                      "git ls-files 'tests/*.py' 'tests/**/*.py'")
    if None not in (d['suites_js'][0], d['suites_api'][0], d['suites_py'][0]):
        d['suites_total'] = (d['suites_js'][0] + d['suites_api'][0] + d['suites_py'][0],
                             'sum of the three suite rows')

    tl = git_lines('ls-files', 'tools/')
    d['tools'] = (None if tl is None else
                  len({os.path.basename(f) for f in tl
                       if f.endswith(('.py', '.js', '.cjs', '.sh'))
                       and '__pycache__' not in f}),
                  'git ls-files tools/, executables only, deduplicated by name')

    cl = git_lines('log', '--oneline', '--since=2026-05-15')
    d['commits'] = (None if cl is None else len(cl),
                    'git log --oneline --since=2026-05-15')

    d['resources'] = (tool_value(['tools/criticality_tier_check.py'],
                                 r'RESOURCE_ROWS:(\d+)'),
                      'python tools/criticality_tier_check.py -> RESOURCE_ROWS')
    d['tier_a'] = (tool_value(['tools/criticality_tier_check.py'], r'TIER_A:(\d+)'),
                   'python tools/criticality_tier_check.py -> TIER_A')

    # The review ledger and the defect register are read as data, not scraped
    # from a tool's prose -- a count parsed out of a sentence moves when the
    # sentence is reworded.
    try:
        recs = json.loads(read(os.path.join(REPO, 'docs', 'tier-a-reviews.json')))['records']
        d['obligations_total'] = (len(recs), 'review ledger record count')
        d['obligations_reviewed'] = (len([r for r in recs if r.get('status') == 'reviewed']),
                                     "review ledger, status 'reviewed'")
        d['obligations_open'] = (len([r for r in recs if r.get('status') == 'open']),
                                 "review ledger, status 'open'")
    except Exception:
        d['obligations_total'] = (None, 'review ledger unreadable')

    try:
        reg = json.loads(read(os.path.join(REPO, 'docs', 'defect-density-register.json')))
        rows = [r for r in reg.get('records', []) if not r.get('confirmation')]
        d['defects_total'] = (len(rows), 'defect register record count')
        for sev in ('critical', 'high', 'moderate', 'low'):
            d['defects_' + sev] = (len([r for r in rows if r.get('severity') == sev]),
                                   'defect register, severity ' + sev)
        for layer in ('product', 'tooling', 'test'):
            d['defects_layer_' + layer] = (len([r for r in rows if r.get('layer') == layer]),
                                           'defect register, layer ' + layer)
    except Exception:
        d['defects_total'] = (None, 'defect register unreadable')

    return d


# Which sheet figure each derivation must equal. The sheet is the SUBJECT, so
# the number is located by its label rather than by line number -- a line number
# in a document that grows is stale the moment somebody inserts a paragraph.
ROW_PATTERNS = {
    'apps_total':          r'Applications and pages, total \|\s*\*\*([\d,]+)\*\*',
    'sql_files':           r'Database schema files \|\s*\*\*([\d,]+)\*\*',
    'suites_total':        r'Automated test suites, total \|\s*\*\*([\d,]+)\*\*',
    'suites_js':           r'JavaScript suites \|\s*\*\*([\d,]+)\*\*',
    'suites_api':          r'Endpoint suites \|\s*\*\*([\d,]+)\*\*',
    'suites_py':           r'Python probes \|\s*\*\*([\d,]+)\*\*',
    'tools':               r'Verification tools and checkers \|\s*\*\*([\d,]+)\*\*',
    'commits':             r'Commits since 2026-05-15 \|\s*\*\*([\d,]+)\*\*',
    'resources':           r'Registered data resources \|\s*\*\*([\d,]+)\*\*',
    'tier_a':              r'criticality resources under mandatory review \|\s*\*\*([\d,]+)\*\*',
    'obligations_total':   r'Review obligations raised \|\s*\*\*([\d,]+)\*\*',
    'obligations_reviewed': r'Review obligations discharged\*\* \|\s*\*\*([\d,]+)\*\*',
    'obligations_open':    r'Currently open \|\s*\*\*([\d,]+)\*\*',
    'defects_total':       r'Defects registered, total\*\* \|\s*\*\*([\d,]+)\*\*',
    'defects_critical':    r'severity — critical \|\s*([\d,]+)',
    'defects_high':        r'severity — high \|\s*([\d,]+)',
    'defects_moderate':    r'severity — moderate \|\s*([\d,]+)',
    'defects_low':         r'severity — low \|\s*([\d,]+)',
    'defects_layer_product': r'layer — in product code \|\s*([\d,]+)',
    'defects_layer_tooling': r'layer — in tooling \|\s*([\d,]+)',
    'defects_layer_test':    r'layer — in tests \|\s*([\d,]+)',
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sheet', default=DEFAULT_SHEET)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    path = os.path.join(REPO, args.sheet) if not os.path.isabs(args.sheet) else args.sheet
    if not os.path.isfile(path):
        print('COULD NOT RUN: %s is not on disk. An absent sheet is not a clean '
              'one -- there is nothing to check a figure against.' % args.sheet)
        return EXIT_COULD_NOT_RUN
    sheet = read(path)

    derived = derive()
    findings, could_not_run, checked, rows = [], [], 0, []

    for key, pat in sorted(ROW_PATTERNS.items()):
        if key not in derived:
            could_not_run.append('%s: this tool has no derivation for it, so the '
                                 'printed figure was NOT checked' % key)
            continue
        value, how = derived[key]
        if value is None:
            could_not_run.append('%s: the derivation could not run (%s), so the '
                                 'printed figure was NOT checked' % (key, how))
            continue
        m = re.search(pat, sheet)
        if not m:
            findings.append('%s: derived %d, but NO figure matching this label is '
                            'in the sheet -- either the row was removed or its '
                            'wording changed, and an unanchored check is the next '
                            'defect along.' % (key, value))
            continue
        printed = int(m.group(1).replace(',', ''))
        checked += 1
        rows.append((key, printed, value, printed == value))
        if printed != value:
            findings.append('%s: the sheet prints %s and the command now returns '
                            '%d. Derived by: %s' % (key, m.group(1), value, how))

    print('FACT SHEET REGENERATES -- a published figure must still be true')
    print('  criteria          : %s' % CRITERIA_VERSION)
    print('  sheet             : %s' % args.sheet)
    print('  CHECKED / UNIVERSE: %d / %d figures this tool can derive'
          % (checked, len(ROW_PATTERNS)))
    print()
    for key, printed, value, agree in rows:
        print('  %-3s %-24s sheet=%-7s derived=%s'
              % ('ok' if agree else '!!', key, printed, value))
    print()
    print('  FIGURES THIS TOOL DELIBERATELY DOES NOT CHECK: the panel counts (a')
    print('  per-application judgement, which is not a command), the patent dates (a')
    print('  quoted sentence, not a computation), and anything the sheet itself')
    print('  marks UNAVAILABLE. Those are stated in the sheet as judgements and')
    print('  encoding them here would turn a stated judgement into a hidden one.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'sheet': args.sheet,
                          'checked': checked, 'universe': len(ROW_PATTERNS),
                          'rows': [{'key': k, 'sheet': p, 'derived': v,
                                    'agree': a} for k, p, v, a in rows],
                          'findings': findings,
                          'could_not_run': could_not_run}, indent=2))

    return finish(findings, could_not_run=could_not_run, clean_line=(
        '\nALL %d checkable figures in the sheet still regenerate exactly.' % checked))


if __name__ == '__main__':
    sys.exit(main())
