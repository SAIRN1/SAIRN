#!/usr/bin/env python
"""hover_self_health.py (hover2's own independent build) -- checks THIS
clone's own self-log for routine, technique staleness, and bar drift,
against real self-log data rather than impression.

WRITTEN FROM H1's STATED PURPOSE, NOT H1's SOURCE. .claude/skills/sairn-
hover-auditor/SKILL.md narrates that H1 built a tool answering exactly
this question ("routine, technique staleness, bar drift") but never
published it as a formal interface spec the way the staleness-guard and
Tier 0/1 specs were -- so there is no contract to satisfy here, only a
purpose to independently re-derive. Every check below is designed from
what is actually MEASURABLE in hover2's own hover-audit-log.jsonl, not
copied or guessed from H1's internals.

FOUR CHECKS, each against real log data:

  ROUTINE (adjacent-repeat) -- entries whose target repeats the
  immediately preceding entry's target. hover_log.py's own rotation gate
  already REFUSES an undeclared repeat at write time, so this count
  should structurally be all-declared; this check confirms that
  invariant holds across the whole log rather than trusting the gate
  never had a bypass (an entry written before the gate existed, a path
  that skipped append_entry(), etc.).

  ROUTINE (app concentration) -- the longest run of consecutive entries
  whose `ref` field names only ONE app file. The target-repeat gate
  catches repeating the exact same RESOURCE; it does not catch parking
  on one APP across many different resources within it, which is a
  narrower, real form of the identical routine problem.

  TECHNIQUE STALENESS -- a named, explicit set of techniques this role's
  own tooling and mandate make available (duplicate-check, Tier 0 live
  execution, Tier 1 live production, cross-referencing a prior
  developer's own code comment, H1/H2 reconciliation, differential
  review, adversarial review, sabotage/mutation testing, coverage-ledger
  work). For each, the LAST entry (by seq) whose summary matches it, or
  NEVER if it has not appeared at all. Reported per the platform's own
  named discipline (CLAUDE.md, cross-domain disciplines doc): as a named
  table, not one combined figure -- nine numbers, never an average.

  BAR DRIFT -- the log's entries split into two halves by seq (first
  half vs second half, chronological). Finding-rate and severity
  distribution reported for EACH HALF SEPARATELY, per the same "report
  accuracy and stability as two numbers, never one" discipline -- a
  single combined ratio across the whole log would hide a real drift
  the same way a single accuracy figure hides an unstable check.

  COVERAGE-LEDGER STANDING -- calls hover_coverage_ledger.py's own
  --status output live (never a stored/remembered number) and surfaces
  its own "N covered / M not" line directly, because a stale count here
  would be exactly the failure class this whole file exists to prevent.

    python hover_self_health.py
    python hover_self_health.py --selftest
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, 'hover-audit-log.jsonl')
COVERAGE_LEDGER_TOOL = os.path.join(HERE, 'hover_coverage_ledger.py')

VALID_SEVERITY_ORDER = ('critical', 'high', 'moderate', 'low', '')

TECHNIQUES = [
    ('duplicate_check',
     re.compile(r'duplicate.check', re.I)),
    ('tier0_live_execution',
     re.compile(r'tier ?0|vm sandbox|referenceerror', re.I)),
    ('tier1_live_production',
     re.compile(r'tier ?1\b|control arm|verified.{0,30}failed.{0,30}unverified', re.I)),
    ('code_already_knows_xref',
     re.compile(r"code already knows|developer'?s own comment|already states the "
                r"conclusion|access.control.*already", re.I)),
    ('h1_h2_reconciliation',
     re.compile(r'h1.?/?h2|reconcil|bucket \(a\)|bucket \(b\)', re.I)),
    ('differential_review',
     re.compile(r'differential.review|diff review', re.I)),
    ('adversarial_review',
     re.compile(r'adversarial|hostile persona', re.I)),
    ('sabotage_mutation_test',
     re.compile(r'sabotage|mutation|planted.{0,20}(defect|bug)', re.I)),
    ('coverage_ledger_work',
     re.compile(r'coverage.ledger|discharge.{0,20}obligation', re.I)),
]

_APP_FILE_RE = re.compile(r'\b([a-z0-9_]+\.html)\b', re.I)


def read_log(path=None):
    """[entries] oldest-first, or (None, problem) if unreadable. Mirrors
    hover_log.py's own read_all() honesty: a missing file is a real, valid
    empty state; a malformed file is a problem, never silently partial."""
    path = path or LOG_PATH
    if not os.path.isfile(path):
        return [], ''
    entries = []
    try:
        with io.open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except (OSError, ValueError) as exc:
        return None, 'could not read/parse %s: %s' % (path, exc)
    return entries, ''


def check_adjacent_repeats(entries):
    """(undeclared_count, declared_count, total_adjacent_repeats). An
    undeclared repeat slipping through despite the write-time gate is a
    serious anomaly -- it means either a pre-gate entry or a write path
    that bypassed append_entry()."""
    undeclared = declared = 0
    for i in range(1, len(entries)):
        if entries[i].get('target') == entries[i - 1].get('target'):
            if entries[i].get('same_target_reason'):
                declared += 1
            else:
                undeclared += 1
    return undeclared, declared, undeclared + declared


def check_app_concentration(entries):
    """(app_name_or_None, longest_run_length, run_end_seq_or_None). Looks
    at `ref` for app *.html filenames; a run is consecutive entries whose
    ref mentions EXACTLY one distinct app and no other. Entries touching
    zero or multiple apps break a run (a multi-app entry is cross-app
    work, not concentration)."""
    best_app, best_len, best_end_seq = None, 0, None
    cur_app, cur_len, cur_end_seq = None, 0, None
    for e in entries:
        apps = set(m.lower() for m in _APP_FILE_RE.findall(e.get('ref') or ''))
        if len(apps) == 1:
            app = next(iter(apps))
            if app == cur_app:
                cur_len += 1
            else:
                cur_app, cur_len = app, 1
            cur_end_seq = e.get('seq')
            if cur_len > best_len:
                best_app, best_len, best_end_seq = cur_app, cur_len, cur_end_seq
        else:
            cur_app, cur_len, cur_end_seq = None, 0, None
    return best_app, best_len, best_end_seq


_META_TARGET_NAMES = frozenset(('own_tooling', 'self'))


def _is_meta_entry(e):
    """True for an entry ABOUT this role's own tooling (a self-health
    report, a tool build note, a self-audit) rather than an actual audit
    finding/check against a platform resource. Three signals, because no
    one is complete on its own: --source-exempt-reason (the structured
    field hover_log.py carries for exactly this distinction, but only
    exists on entries written after that flag was built); a target
    ending in '.py' (names a tool); a target matching a small, known set
    of non-resource meta-names this role has actually used
    ('own_tooling', 'self') for entries written BEFORE the exempt-reason
    field existed at all -- found necessary by running this live: seq 36
    (a real self-audit, target='own_tooling') predates --source-exempt-
    reason entirely and would otherwise still misfire. HONESTLY
    DISCLOSED, NOT CLAIMED COMPLETE: an even older meta entry using some
    OTHER target string not in this set could still misfire; this is a
    best-effort reconstruction of intent from a log that changed its own
    conventions over time, not a guarantee."""
    if e.get('source_exempt_reason'):
        return True
    target = e.get('target') or ''
    return target.endswith('.py') or target in _META_TARGET_NAMES


def check_technique_staleness(entries):
    """{technique_name: last_seq_or_None}. NEVER (None) is reported
    honestly, not folded into a 0 that reads like 'used at seq 0'.

    META ENTRIES ARE EXCLUDED, found necessary by running this live, not
    by inspection: a report ABOUT which techniques are unused (like this
    tool's own seq-99 self-sequence note) mentions every technique BY
    NAME while explaining that none of them were used -- and a bare
    keyword search cannot tell 'I used adversarial review' from 'I have
    NOT used adversarial review', so the first live run reported every
    genuinely-unused technique as 'last used at seq 99', the exact entry
    that was DISCUSSING their absence. Filtering meta entries (identified
    the same way hover_log.py's own --source-exempt-reason already marks
    'this is about my own tooling, not a platform read') closes it."""
    result = {}
    for name, pattern in TECHNIQUES:
        last_seq = None
        for e in entries:
            if _is_meta_entry(e):
                continue
            haystack = (e.get('summary') or '') + ' ' + (e.get('ref') or '')
            if pattern.search(haystack):
                last_seq = e.get('seq')
        result[name] = last_seq
    return result


def check_bar_drift(entries):
    """(first_half_stats, second_half_stats). Each stats dict:
    {'n': int, 'finding_rate': float, 'severity': {sev: count}}. Split by
    COUNT of entries (chronological halves), not by seq value, so an
    uneven append rate does not skew which entries land in which half."""
    def stats(chunk):
        n = len(chunk)
        findings = [e for e in chunk if e.get('type') == 'finding']
        sev_counts = {}
        for e in findings:
            sev = e.get('severity') or '(none)'
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
        return {
            'n': n,
            'finding_rate': (len(findings) / n) if n else 0.0,
            'severity': sev_counts,
        }
    mid = len(entries) // 2
    return stats(entries[:mid]), stats(entries[mid:])


def check_coverage_ledger_standing(tool_path=None, timeout=30):
    """(covered, not_covered, total, raw_line) from a LIVE run of
    hover_coverage_ledger.py --status, or (None, None, None, reason) if it
    could not be run -- never a remembered number."""
    tool_path = tool_path or COVERAGE_LEDGER_TOOL
    if not os.path.isfile(tool_path):
        return None, None, None, 'hover_coverage_ledger.py not found at %s' % tool_path
    try:
        p = subprocess.run([sys.executable, tool_path, '--status'],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, None, None, 'TIMEOUT after %ss' % timeout
    except OSError as exc:
        return None, None, None, 'could not run: %s' % exc
    m = re.search(r'(\d+) covered by this role.s self-log, (\d+) NOT', p.stdout or '')
    if not m:
        return None, None, None, ('could not parse coverage-ledger output '
                                  '(tool ran, output shape unexpected)')
    covered, not_covered = int(m.group(1)), int(m.group(2))
    return covered, not_covered, covered + not_covered, m.group(0)


def run_report(log_path=None):
    entries, problem = read_log(log_path)
    if entries is None:
        return None, 'COULD NOT RUN: %s' % problem
    lines = []
    lines.append('HOVER2 SELF-HEALTH -- %d entries in %s' % (len(entries), log_path or LOG_PATH))
    lines.append('')

    undeclared, declared, total_repeat = check_adjacent_repeats(entries)
    lines.append('ROUTINE (adjacent-repeat): %d declared, %d UNDECLARED (of %d total '
                 'adjacent same-target repeats)' % (declared, undeclared, total_repeat))
    if undeclared:
        lines.append('  ANOMALY: the write-time rotation gate should make this 0 -- '
                     'investigate how %d undeclared repeat(s) reached the log' % undeclared)

    app, run_len, end_seq = check_app_concentration(entries)
    lines.append('ROUTINE (app concentration): longest single-app run = %d entries%s'
                 % (run_len, (' (%s, ending seq %s)' % (app, end_seq)) if app else ''))

    lines.append('')
    lines.append('TECHNIQUE STALENESS (last seq used, never averaged into one figure):')
    tech = check_technique_staleness(entries)
    for name, last_seq in tech.items():
        lines.append('  %-26s %s' % (name, ('seq %s' % last_seq) if last_seq is not None else 'NEVER'))

    lines.append('')
    first, second = check_bar_drift(entries)
    lines.append('BAR DRIFT (two numbers, never combined):')
    lines.append('  first half  (n=%-3d): finding_rate=%.2f  severity=%s'
                 % (first['n'], first['finding_rate'], first['severity']))
    lines.append('  second half (n=%-3d): finding_rate=%.2f  severity=%s'
                 % (second['n'], second['finding_rate'], second['severity']))

    lines.append('')
    covered, not_covered, total, raw = check_coverage_ledger_standing()
    if covered is None:
        lines.append('COVERAGE-LEDGER STANDING: COULD NOT RUN (%s)' % raw)
    else:
        lines.append('COVERAGE-LEDGER STANDING (live, not remembered): %d covered, '
                     '%d NOT covered, of %d review-shaped commits' % (covered, not_covered, total))

    return '\n'.join(lines), ''


def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1
    report, problem = run_report()
    if report is None:
        print(problem)
        return 2
    print(report)
    return 0


def run_fixtures():
    ok = [0]
    bad = []

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   ' + name)
        else:
            bad.append(name)
            print('  FAIL ' + name)

    e1 = {'seq': 1, 'target': 'a', 'summary': 'checked a', 'ref': 'foo.html'}
    e2 = {'seq': 2, 'target': 'a', 'summary': 'checked a again',
          'ref': 'foo.html', 'same_target_reason': 'deliberate follow-up'}
    e3 = {'seq': 3, 'target': 'a', 'summary': 'checked a a third time', 'ref': 'foo.html'}
    e4 = {'seq': 4, 'target': 'b', 'summary': 'checked b', 'ref': 'bar.html'}
    u, d, t = check_adjacent_repeats([e1, e2, e3, e4])
    ck('check_adjacent_repeats() counts a declared repeat as declared',
       d == 1)
    ck('check_adjacent_repeats() counts an UNDECLARED repeat as undeclared '
       '-- e3 repeats e2\'s target with no same_target_reason',
       u == 1)
    ck('check_adjacent_repeats() total is declared+undeclared', t == 2)

    run_entries = [
        {'seq': 1, 'ref': 'foo.html'}, {'seq': 2, 'ref': 'foo.html'},
        {'seq': 3, 'ref': 'foo.html'}, {'seq': 4, 'ref': 'bar.html'},
        {'seq': 5, 'ref': 'foo.html,bar.html'},  # multi-app breaks the run
        {'seq': 6, 'ref': 'baz.html'}, {'seq': 7, 'ref': 'baz.html'},
    ]
    app, run_len, end_seq = check_app_concentration(run_entries)
    ck('check_app_concentration() finds the longest single-app run '
       '(3 consecutive foo.html entries)', app == 'foo.html' and run_len == 3)
    ck('check_app_concentration() correctly reports the run-ending seq',
       end_seq == 3)

    tech_entries = [
        {'seq': 5, 'summary': 'ran a duplicate-check before filing', 'ref': ''},
        {'seq': 9, 'summary': 'used Tier 0 live execution against a real function', 'ref': ''},
    ]
    tech = check_technique_staleness(tech_entries)
    ck('check_technique_staleness() finds the LAST matching seq for a '
       'technique that appears', tech['duplicate_check'] == 5)
    ck('check_technique_staleness() reports NEVER (None), not 0, for a '
       'technique that never appears in the fixture',
       tech['differential_review'] is None and tech['adversarial_review'] is None)
    ck('check_technique_staleness() matches tier0 by name variant',
       tech['tier0_live_execution'] == 9)

    # REGRESSION: found by running this live against the real self-log, not
    # by inspection -- a meta-report entry DISCUSSING which techniques are
    # unused mentions every technique by name, and the first version
    # reported every genuinely-unused technique as 'last used' at that
    # report's own seq.
    meta_entries = tech_entries + [
        {'seq': 99, 'target': 'hover_self_health.py',
         'source_exempt_reason': 'capability-gap inventory, not a platform file',
         'summary': ('sairn-differential-review and sairn-adversarial-reviewer '
                    'have NOT been invoked once this entire session'),
         'ref': ''},
    ]
    tech_meta = check_technique_staleness(meta_entries)
    ck('check_technique_staleness() does NOT count a meta-report entry '
       "DISCUSSING an unused technique (by --source-exempt-reason or a "
       "target ending in .py) as an actual USE of it",
       tech_meta['differential_review'] is None
       and tech_meta['adversarial_review'] is None)
    ck('...and a meta entry with a .py target (no exempt-reason set) is '
       'ALSO excluded, via the target-suffix signal alone',
       check_technique_staleness(tech_entries + [
           {'seq': 100, 'target': 'some_tool.py',
            'summary': 'discusses adversarial review in passing', 'ref': ''},
       ])['adversarial_review'] is None)
    ck('...and a PRE-dated-flag meta entry (real seq-36 shape: '
       "target='own_tooling', no source_exempt_reason key at all, from "
       'before that flag existed) is excluded too, via the known-'
       'meta-target-name fallback',
       check_technique_staleness(tech_entries + [
           {'seq': 36, 'target': 'own_tooling',
            'summary': 'self-audit discussing sabotage and coverage ledger '
                       'work in the abstract', 'ref': ''},
       ])['sabotage_mutation_test'] is None)

    drift_entries = (
        [{'type': 'check', 'severity': ''}] * 8 +
        [{'type': 'finding', 'severity': 'high'}] * 2
        + [{'type': 'finding', 'severity': 'critical'}] * 8
        + [{'type': 'check', 'severity': ''}] * 2
    )
    f, s = check_bar_drift(drift_entries)
    ck('check_bar_drift() computes the first half\'s finding rate correctly '
       '(2 of 10)', abs(f['finding_rate'] - 0.2) < 1e-9)
    ck('check_bar_drift() computes the second half\'s finding rate '
       'separately (8 of 10) -- the two numbers are NOT averaged together',
       abs(s['finding_rate'] - 0.8) < 1e-9)
    ck('check_bar_drift() severity counts are per-half, not merged',
       f['severity'].get('high') == 2 and s['severity'].get('critical') == 8)

    import tempfile
    tmpdir = tempfile.mkdtemp()
    good_path = os.path.join(tmpdir, 'good.jsonl')
    with io.open(good_path, 'w', encoding='utf-8') as f_:
        f_.write(json.dumps({'seq': 1, 'target': 'x', 'summary': 's', 'ref': ''}) + '\n')
    entries_ok, problem_ok = read_log(good_path)
    ck('read_log() round-trips a real well-formed file',
       not problem_ok and len(entries_ok) == 1)

    missing_path = os.path.join(tmpdir, 'does-not-exist.jsonl')
    entries_missing, problem_missing = read_log(missing_path)
    ck('read_log() on a missing file reports an empty, valid log (not an '
       'error) -- matches hover_log.py\'s own read_all() semantics',
       entries_missing == [] and not problem_missing)

    bad_path = os.path.join(tmpdir, 'bad.jsonl')
    with io.open(bad_path, 'w', encoding='utf-8') as f_:
        f_.write('not json at all\n')
    entries_bad, problem_bad = read_log(bad_path)
    ck('read_log() on a malformed file reports a problem, not a silent '
       'partial read', entries_bad is None and problem_bad)

    covered, not_covered, total, raw = check_coverage_ledger_standing(
        tool_path=os.path.join(tmpdir, 'does-not-exist.py'))
    ck('check_coverage_ledger_standing() on a missing tool reports '
       'COULD NOT RUN honestly rather than a fabricated count',
       covered is None and 'not found' in raw)

    real_report, real_problem = run_report()
    ck('run_report() runs cleanly against THIS clone\'s REAL self-log '
       '(not a fixture) and includes every section',
       not real_problem
       and 'ROUTINE' in real_report and 'TECHNIQUE STALENESS' in real_report
       and 'BAR DRIFT' in real_report and 'COVERAGE-LEDGER' in real_report)

    print('')
    if bad:
        print('%d of %d selftest arm(s) failed' % (len(bad), ok[0] + len(bad)))
        return False
    print('OK -- %d arms passed.' % ok[0])
    return True


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
