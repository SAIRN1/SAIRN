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
* The ELAPSED SPANS -- 98 days / 14.0 weeks, the 18.6-week build span, the days
  since the defect register opened. Those are read OUT OF the sheet and used as
  divisors, not re-derived. A per-week figure is therefore exact against the span
  the sheet states, and the span itself is unchecked.
* The tooling-inventory rows (checkers, generators, scheduled, hook-wired,
  invoked-by-a-test, recorded decisions not to automate) and the live-probe rows.
  They have commands and could be derived; they are not, and that gap is printed
  rather than left to the CHECKED count to imply.

── RESTATEMENTS ARE FIGURES TOO ────────────────────────────────────────────
Beyond the rows with commands, the sheet says several numbers AGAIN in prose --
"6,885 commits / 14.0 weeks", "178 of the 360 are in tooling or tests". Those
decay exactly like a row and nothing was watching them: on 2026-09-28 the commits
row was refreshed 6,890 -> 6,900, this tool exited 0, and the line directly
beneath the row still read 6,885. The checker was clean and the document
contradicted itself on the page somebody reads aloud. See DERIVED_PATTERNS.
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

CRITERIA_VERSION = '2026-09-28.2'
# Written out rather than escaped: this file is edited by scripts often enough
# that a literal backslash-n in a source edit has broken it twice.
NL = chr(10)
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

    # The sheet's own paragraph about the bare command needs both halves of it,
    # because the paragraph exists to show the two numbers differ and why.
    d['tools_bare'] = (None if tl is None else len(tl),
                       'git ls-files tools/, every tracked file')
    d['tools_data'] = (None if tl is None else
                       len([f for f in tl
                            if not f.endswith(('.py', '.js', '.cjs', '.sh'))
                            and f.endswith('.json')]),
                       'git ls-files tools/, tracked .json data files')

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


# ── RESTATEMENTS: THE SAME FIGURE, WRITTEN AGAIN WITHOUT A COMMAND ──────────
# Every row above carries its own command. The entries below do not: they are
# ARITHMETIC over those rows, or the identical count spelled out again in a
# sentence. They drift the moment a row is refreshed and nothing about reading
# the document reveals it -- which is precisely what happened on 2026-09-28.
#
# Each entry is (regex, tuple of per-group callables). ONLY THE DIGITS INSIDE A
# CAPTURE GROUP ARE EVER REWRITTEN; the prose around them is written by a person
# and stays that way. A callable of None marks an INPUT -- a divisor the sheet
# itself states, read out and used, never overwritten. That is the honest
# arrangement: this tool re-derives the counts and takes the spans on the
# sheet's word, and the docstring says so rather than implying it checked both.
DIV = chr(0xF7)      # the division sign the sheet prints
MDASH = chr(0x2014)  # the em dash the sheet prints


def pat(s):
    """The two non-ASCII glyphs the sheet uses, kept out of this file's source.

    This file is edited by scripts often enough that a mangled encoding has
    broken an anchor before, and an anchor that stops matching is reported
    here as a finding -- but only if the anchor itself survived the edit.
    """
    return s.replace('{DIV}', DIV).replace('{M}', MDASH)


def rnd(x):
    """Half-up, stated. round() is half-to-even and the sheet is read aloud."""
    return int(x + 0.5)


def need(vals, key):
    v = vals.get(key)
    if v is None:
        raise ValueError('the derivation for %s did not run' % key)
    return v


# Spans the sheet states and this tool does NOT re-derive. Read once, used as
# divisors, and named in the docstring as unchecked.
SHEET_SCALARS = {
    'days_vc':     r'\| Elapsed development span \| \*\*(\d+) days / [\d.]+ weeks\*\*',
    'weeks_vc':    r'\| Elapsed development span \| \*\*\d+ days / ([\d.]+) weeks\*\*',
    'defect_days': r'\*\*2026-09-09\*\* ' + MDASH + r' (\d+) days',
    'defect_weeks': r'([\d.]+) weeks since the register opened',
}

DERIVED_PATTERNS = {
    'restated_commits_per_week': (
        pat(r'\| Commits per week \(mean\) \| \*\*([\d,]+)\*\* \| ([\d,]+) {DIV} ([\d.]+) \|'),
        (lambda g, v: rnd(need(v, 'commits') / float(g[2])),
         lambda g, v: need(v, 'commits'),
         None)),
    'restated_commits_per_day': (
        pat(r'\| Commits per day \(mean\) \| \*\*([\d,]+)\*\* \| ([\d,]+) {DIV} (\d+) \|'),
        (lambda g, v: rnd(need(v, 'commits') / float(g[2])),
         lambda g, v: need(v, 'commits'),
         None)),
    'say_commits_headline': (
        r'\*\*"Roughly ([\d,]+) commits a week, every week',
        (lambda g, v: rnd(need(v, 'commits') / need(v, 'weeks_vc') / 10.0) * 10,)),
    'say_commits_math': (
        pat(r'> ([\d,]+) commits {DIV} ([\d.]+) weeks under version control = '
            r'\*\*([\d,]+) per week\*\*, ([\d,]+) per day\.'),
        (lambda g, v: need(v, 'commits'),
         None,
         lambda g, v: rnd(need(v, 'commits') / float(g[1])),
         lambda g, v: rnd(need(v, 'commits') / need(v, 'days_vc')))),
    'say_commits_span': (
        r'Over the full ([\d.]+)-week build span the average is \*\*([\d,]+) per week\*\*',
        (None,
         lambda g, v: rnd(need(v, 'commits') / float(g[0])))),
    'say_defects_headline': (
        r'\*\*"About ([\d,]+) defects caught per week',
        (lambda g, v: rnd(need(v, 'defects_total') / need(v, 'defect_weeks')
                          / 10.0) * 10,)),
    'say_defects_math': (
        pat(r'> ([\d,]+) defects {DIV} ([\d.]+) weeks since the register opened '
            r'2026-09-09 = \*\*([\d,]+) per\s+(?:> )?week\*\*, ([\d,]+) per day\.'),
        (lambda g, v: need(v, 'defects_total'),
         None,
         lambda g, v: rnd(need(v, 'defects_total') / float(g[1])),
         lambda g, v: rnd(need(v, 'defects_total') / need(v, 'defect_days')))),
    'say_defects_layers': (
        r'and ([\d,]+) of\s+(?:> )?the ([\d,]+) were in the tooling and tests',
        (lambda g, v: need(v, 'defects_layer_tooling') + need(v, 'defects_layer_test'),
         lambda g, v: need(v, 'defects_total'))),
    'prose_defects_total': (
        r'\*\*What this figure is and is not\.\*\* ([\d,]+) is the count since',
        (lambda g, v: need(v, 'defects_total'),)),
    'prose_defects_layers': (
        r'\*\*([\d,]+) of\s+the ([\d,]+) are in tooling or tests',
        (lambda g, v: need(v, 'defects_layer_tooling') + need(v, 'defects_layer_test'),
         lambda g, v: need(v, 'defects_total'))),
    'press_on_defects': (
        pat(r'\*\*Defects {M} (\d+) days of recording\*\*, and ([\d,]+) of ([\d,]+) '
            r'are in tooling'),
        (lambda g, v: int(need(v, 'defect_days')),
         lambda g, v: need(v, 'defects_layer_tooling') + need(v, 'defects_layer_test'),
         lambda g, v: need(v, 'defects_total'))),
    'prose_tools_bare': (
        pat(r'bare `git ls-files tools/` returns \*\*([\d,]+)\*\* {M} it counts (\d+) '
            r'data\s+files and one\s+configuration file that are not tools\. '
            r'\*\*([\d,]+)\*\* is the count of executable'),
        (lambda g, v: need(v, 'tools_bare'),
         lambda g, v: need(v, 'tools_data'),
         lambda g, v: need(v, 'tools'))),
}

# Named here rather than left for the CHECKED count to imply. A figure absent
# from both tables above is not checked by anything, and a coverage number that
# counts only what it decided to look at reads as "covered everything".
NOT_DERIVED_HERE = (
    'the panel counts (a per-application judgement, not a command)',
    'the patent dates and count (a quoted sentence, not a computation)',
    'the application classification rows -- vertical / consumer / satellite',
    'the tooling-inventory rows: checkers, generators, scheduled, hook-wired, '
    'invoked-by-a-test, recorded decisions not to automate',
    'the live-probe rows, and how many of them write',
    'the elapsed spans -- 98 days / 14.0 weeks, 18.6 weeks, days since the '
    'register opened. READ OUT OF THE SHEET and used as divisors, not checked',
    'the root-commit evidence table',
    'anything the sheet itself marks UNAVAILABLE',
)


def derived_expectations(sheet, vals):
    """[(key, [(span, printed, fresh)...])] for every restatement.

    Returns three lists: resolved entries, anchors that did not match, and keys
    whose inputs could not be derived. The three are kept apart on purpose --
    "the anchor is gone" and "the command did not run" are different failures
    and folding either into a pass is the defect this repo names most often.
    """
    resolved, missing, could_not = [], [], []
    for key, (rx, fns) in sorted(DERIVED_PATTERNS.items()):
        m = re.search(rx, sheet)
        if not m:
            missing.append(key)
            continue
        groups = m.groups()
        try:
            edits = []
            for i, fn in enumerate(fns):
                if fn is None:
                    continue
                printed = groups[i]
                fresh = ('{:,}'.format(fn(groups, vals)) if ',' in printed
                         else str(fn(groups, vals)))
                edits.append((m.span(i + 1), printed, fresh))
        except ValueError as exc:
            could_not.append('%s: %s, so the restated figure was NOT checked'
                             % (key, exc))
            continue
        resolved.append((key, edits))
    return resolved, missing, could_not


def sheet_scalars(sheet):
    """The divisors the sheet states. A missing one makes its users COULD NOT RUN."""
    out = {}
    for key, rx in SHEET_SCALARS.items():
        m = re.search(rx, sheet)
        out[key] = float(m.group(1)) if m else None
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sheet', default=DEFAULT_SHEET)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--update', action='store_true',
                    help='rewrite every DERIVABLE figure from its own command and '
                         'stamp the run time. Never touches a figure it cannot '
                         'derive, and exits non-zero if any derivation failed.')
    ap.add_argument('--now', default=None,
                    help='the timestamp to stamp (default: system clock). Exists so '
                         'the control can assert the stamp without racing a clock.')
    args = ap.parse_args(argv)

    path = os.path.join(REPO, args.sheet) if not os.path.isabs(args.sheet) else args.sheet
    if not os.path.isfile(path):
        print('COULD NOT RUN: %s is not on disk. An absent sheet is not a clean '
              'one -- there is nothing to check a figure against.' % args.sheet)
        return EXIT_COULD_NOT_RUN
    sheet = read(path)

    derived = derive()

    # ── --update: REWRITE WHAT CAN BE DERIVED, TOUCH NOTHING ELSE ───────────
    # THE ORDER MATTERS AND IS THE WHOLE SAFETY PROPERTY: a figure is written
    # ONLY when its derivation returned a value. A derivation that could not run
    # leaves the OLD number in place -- because a blank or a zero in a document
    # somebody reads aloud is worse than a number that is merely stale, and a
    # stale number is at least one that was true once.
    #
    # It still EXITS NON-ZERO when any derivation failed, so "the sheet updated
    # cleanly" and "the sheet updated as far as it could" are never the same
    # answer. That is the third state, in a mode whose whole purpose is to make
    # the document trustworthy minutes before it is printed.
    if args.update:
        stamp = args.now or datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        written, skipped, missing = [], [], []
        for key, pat in sorted(ROW_PATTERNS.items()):
            value = derived.get(key, (None, ''))[0]
            if value is None:
                skipped.append(key)
                continue
            m = re.search(pat, sheet)
            if not m:
                missing.append(key)
                continue
            printed = m.group(1)
            fresh = '{:,}'.format(value) if ',' in printed else str(value)
            if printed == fresh:
                continue
            a, b = m.span(1)
            sheet = sheet[:a] + fresh + sheet[b:]
            written.append((key, printed, fresh))

        # ── THEN THE RESTATEMENTS, against the rows just written ───────────
        # Right-to-left inside each match, so an earlier replacement of a
        # different width cannot move the span of a later one.
        vals = dict((k, val) for k, (val, _how) in derived.items())
        vals.update(sheet_scalars(sheet))
        resolved, d_missing, d_could_not = derived_expectations(sheet, vals)
        missing.extend(d_missing)
        skipped.extend(c.split(':')[0] for c in d_could_not)
        for key, edits in resolved:
            for (a, b), printed, fresh in sorted(edits, reverse=True):
                if printed == fresh:
                    continue
                sheet = sheet[:a] + fresh + sheet[b:]
                written.append((key, printed, fresh))

        # ── A FAILED UPDATE MUST NOT STAMP A FRESH TIME ────────────────────
        # Caught by the control on its first run: a broken derivation correctly
        # left the old FIGURES in place and then wrote a NEW timestamp over
        # them. That is worse than either failure alone -- the figures are
        # stale and the stamp says they were just refreshed, so the one signal
        # a reader would check is the one that lies.
        #
        # The stamp is therefore written ONLY on a clean update. A partial run
        # leaves the previous stamp standing, which is the honest thing: it
        # still describes the last time the figures really were refreshed.
        # The stamp is a single line replaced wholesale, so repeated runs
        # cannot accumulate stamps.
        if not skipped and not missing:
            line = ('**Figures refreshed %s by `python '
                    'tools/fact_sheet_regenerates.py --update`.**' % stamp)
            if re.search(r'^\*\*Figures refreshed .*--update`\.\*\*$', sheet, re.M):
                sheet = re.sub(r'^\*\*Figures refreshed .*--update`\.\*\*$', line,
                               sheet, count=1, flags=re.M)
            else:
                anchor = '**No file names, no customer data'
                sheet = sheet.replace(anchor, line + NL + NL + anchor, 1)

        io.open(path, 'w', encoding='utf-8', newline=NL).write(sheet)

        print('FACT SHEET UPDATE')
        print('  sheet   : %s' % args.sheet)
        print('  stamped : %s' % stamp)
        print('  rewritten: %d' % len(written))
        for k, old, new in written:
            print('     %-24s %s -> %s' % (k, old, new))
        if skipped:
            print('  LEFT ALONE, derivation could not run: %d -- the OLD figure '
                  'stands, deliberately' % len(skipped))
            for k in skipped:
                print('     %s' % k)
        if missing:
            print('  LABEL NOT FOUND IN THE SHEET: %d' % len(missing))
            for k in missing:
                print('     %s' % k)
        if skipped or missing:
            print(NL + 'NOT A CLEAN UPDATE. Some figure was not refreshed, and '
                  'the sheet still carries whatever it said before. Exit is '
                  'non-zero so this cannot read as done.')
            return EXIT_COULD_NOT_RUN
        print(NL + 'Every derivable figure in the sheet is now exact as of the '
              'stamp.')
        return EXIT_CLEAN

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

    # ── AND THE RESTATEMENTS ────────────────────────────────────────────────
    vals = dict((k, val) for k, (val, _how) in derived.items())
    vals.update(sheet_scalars(sheet))
    resolved, d_missing, d_could_not = derived_expectations(sheet, vals)
    could_not_run.extend(d_could_not)
    for key in d_missing:
        findings.append('%s: the sentence this restated figure lives in no longer '
                        'matches its anchor. It was NOT checked, and a restatement '
                        'nothing watches is how the sheet contradicted itself on '
                        '2026-09-28.' % key)
    restated = 0
    for key, edits in resolved:
        for _span, printed, fresh in edits:
            restated += 1
            agree = printed == fresh
            rows.append((key, printed, fresh, agree))
            if not agree:
                findings.append('%s: the sheet restates %s where the figures it is '
                                'computed from now give %s.' % (key, printed, fresh))

    print('FACT SHEET REGENERATES -- a published figure must still be true')
    print('  criteria          : %s' % CRITERIA_VERSION)
    print('  sheet             : %s' % args.sheet)
    print('  CHECKED / UNIVERSE: %d / %d figures with their own command'
          % (checked, len(ROW_PATTERNS)))
    print('  RESTATEMENTS      : %d numbers said again in prose or as arithmetic'
          % restated)
    print()
    for key, printed, value, agree in rows:
        print('  %-3s %-26s sheet=%-7s derived=%s'
              % ('ok' if agree else '!!', key, printed, value))
    print()
    print('  FIGURES THIS TOOL DOES NOT CHECK AT ALL -- named rather than left for')
    print('  the count above to imply, because a coverage number that counts only')
    print('  what it looked at reads as "covered everything":')
    for line in NOT_DERIVED_HERE:
        print('    * %s' % line)

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'sheet': args.sheet,
                          'checked': checked, 'universe': len(ROW_PATTERNS),
                          'restatements': restated,
                          'not_derived_here': list(NOT_DERIVED_HERE),
                          'rows': [{'key': k, 'sheet': p, 'derived': v,
                                    'agree': a} for k, p, v, a in rows],
                          'findings': findings,
                          'could_not_run': could_not_run}, indent=2))

    return finish(findings, could_not_run=could_not_run, clean_line=(
        '\nALL %d checkable figures and %d restatements in the sheet still '
        'regenerate exactly.' % (checked, restated)))


if __name__ == '__main__':
    sys.exit(main())
