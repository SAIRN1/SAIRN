#!/usr/bin/env python
r"""hover_audit_effectiveness.py -- this role's own audit-effectiveness
metrics, computed from its own real self-log over real windows, against
real EXTERNAL benchmarks rather than a feeling that things are going well.

Built H1 b68 from a real research pass on how adversarial auditors, red
teams and independent verifiers actually measure their own improvement.
Own tool, own clone, independent of H2 -- nothing here is shared with or
copied from H2's equivalent, and H2's own code was not read.

-- WHY THIS EXISTS, AND WHAT WAS ACTUALLY MISSING -------------------------
59 hover tools existed before this one. They measure the PLATFORM (what the
build agents did), or this role's own COVERAGE (which targets got looked
at: hover_coverage_ledger, scope_narrowing_check, defect_density_weighting,
undirected_sweep_freshness), or one tool's own trustworthiness
(tool_provenance_check, the sabotage benchmark). NONE of them measured
whether THIS ROLE IS GETTING BETTER OR WORSE AT AUDITING, over time,
against any external standard. hover_self_health.py is the closest and is
genuinely a different question: it checks whether the ROUTINE is still
running (technique staleness, EQA cadence, bar drift), not whether the
routine is still FINDING anything.

SKILL.md has asked for exactly this twice and never got it mechanically:
(1) "Track a real, earned calibration number from Debate outcomes, not a
stated-up-front guess... queried from the self-log itself, never asserted
from memory"; (2) the TUV inversion -- "a near-zero finding rate over time
is not evidence of cleanliness -- it is itself worth scrutinizing... if the
self-log shows an unusually long clean streak, that streak is itself a
prompt to ask whether rotation has quietly settled into checking only what
is already known to be safe." Both were prose. Prose is not a trigger --
this file's own SKILL.md section says so in those words, about a different
gap, after a reviewer caught exactly this shape one level up.

-- THE RESEARCH THIS IS BUILT FROM, WITH THE REAL NUMBERS NAMED -----------
Not invented, and not a vague gesture at "best practice":

* REPEAT AUDIT FINDINGS RATE (RAFR), internal-audit practice: the share of
  findings in a period that are recurrences of previously-identified
  issues. Published benchmark: <=5% within 12 months, and <=1% for
  Critical/Major. Described in the field as "a leading indicator of control
  sustainability, remediation effectiveness, and risk culture" -- a high or
  RISING rate indicates ineffective remediation or root causes not actually
  addressed. The sobering industry figure alongside it: over 50% of real
  audit findings recur, because records get CLOSED rather than root causes
  fixed. REPEAT_BENCHMARK_PCT / REPEAT_BENCHMARK_SEVERE_PCT below are those
  two published numbers, not this role's own guesses.

* DISCOVERY RATE, red-team practice: unique validated findings per unit of
  effort, tracked across repeated cycles -- the field's own framing is that
  "tracking [it] over multiple cycles helps organizations determine whether
  detection capabilities are improving." The point is the TREND across
  windows, never one window's absolute number.

* QAIP (IIA Global Internal Audit Standards): an audit FUNCTION is itself
  required to run a periodic quality-assurance and improvement programme
  measuring its own effectiveness, not only its subjects'. This tool is the
  measurement half of that for this role; the EQA checkpoint already in
  SKILL.md is the independent-review half.

-- THE LIMIT THAT IS THE WHOLE POINT, NOT A FOOTNOTE ----------------------
A FALLING DISCOVERY RATE CANNOT BE SEPARATED, FROM THIS DATA ALONE, INTO
"this role got less effective" VERSUS "the platform genuinely got cleaner."
Both produce the identical number. The red-team literature names this exact
ambiguity (is the testing improving, or the target?) and the honest answer
is that one log cannot resolve it -- which is why every rate below is
printed as a measurement with its denominator, never as a verdict on this
role's competence, and why a flagged alarm means GO LOOK, never "you are
bad at this." The ambiguity is reported in the output itself, every run,
rather than left for a reader to remember.

A SECOND, NARROWER LIMIT, DISCLOSED THE SAME WAY: repeat_target_rate is a
PROXY for RAFR, not RAFR. Real RAFR means "the same issue recurred after
being supposedly fixed." What this can actually see is "a later finding
cited a file an earlier finding had already cited" -- which catches a real
recurrence AND also catches a genuinely new, unrelated defect in a
frequently-audited file. It is a repeat-TARGET rate. Named as such
everywhere it is printed, and the benchmark comparison is offered as
orientation rather than as a pass/fail on a metric this log cannot fully
compute.

-- METRIC DENOMINATORS ARE ALWAYS PRINTED, PER SKILL.md's OWN RULE --------
"any rate this role reports or accepts from a checker must state its
denominator explicitly, every time" (the Iron Dome 90%-of-what lesson).
repeat_target_rate's denominator is findings with at least one RESOLVABLE
CITED PATH -- measured at 274 of 435 findings when this tool was built, not
all 435, and the tool prints both numbers rather than quietly computing
over the subset.

-- WINDOWS ARE BY ENTRY COUNT, AND WHY NOT BY BATCH ----------------------
Measured before choosing: only 46 of 435 real findings carry a parseable
"h1 bNN" batch marker in their summary text (282 of 1599 entries overall).
Windowing by batch would therefore drop ~89% of real findings or invent a
batch for them. Entry-count windows (default 200) use every real entry and
are stated in the output so no reader mistakes a window for a batch.

Run:
  python hover_audit_effectiveness.py [--log PATH] [--window N] [--json]
  python hover_audit_effectiveness.py --selftest
"""

import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOG = os.path.join(HERE, 'hover-audit-log.jsonl')

EXIT_OK = 0
EXIT_ALARM = 1
EXIT_COULD_NOT_RUN = 2

DEFAULT_WINDOW = 200

# The two published internal-audit RAFR benchmarks, named as external
# numbers rather than this role's own targets. Compared against the
# repeat-TARGET proxy below with that distinction stated at the print site.
REPEAT_BENCHMARK_PCT = 5.0
REPEAT_BENCHMARK_SEVERE_PCT = 1.0

# The severities the <=1% benchmark is stated for ("Critical/Major").
SEVERE = ('critical', 'high')

# ── THE HUB-FILE CORRECTION, FOUND BY THIS TOOL'S OWN FIRST REAL RUN ──────
# The first live run raised its own repeat-target alarm at 80.95% against a
# 5% benchmark. Following that alarm (which is what the alarm is FOR) rather
# than reporting the number, the real driver turned out to be the platform's
# SHAPE, not recurring defects: of 238 distinct paths cited across 357
# covered findings, two carry a third of all citations --
# docs/CRITICALITY-TIERS.md (127) and api/sd-data.js (74) -- because they
# are the platform's shared tier registry and its single shared dispatcher.
# Nearly every real finding touches one of them, so at FILE granularity
# "this path was cited before" is close to always true and carries almost
# no information on this codebase.
#
# So the rate is reported TWICE: raw, and EXCLUDING hub files. The ex-hubs
# figure is the one the alarm fires on, because it is the one that means
# "a repeat on a file that is not audited by nearly everything."
#
# HUB_SHARE_PCT is REASONED FROM THE MEASURED DISTRIBUTION, not picked in
# the abstract, and the distribution is printed every run so the choice can
# be re-derived or argued with: at 10% of covered findings the two genuine
# hubs (36% and 21%) separate cleanly from the next path down
# (sairnlegacy.html, 7%). Recalibrate if that gap closes -- the same honesty
# every other reasoned constant in this role's tooling carries.
HUB_SHARE_PCT = 10.0

# A path-shaped token in a free-text `ref` field: has a slash or a known
# source extension. Deliberately narrow -- `ref` also legitimately carries
# non-path tags ("b15,b16", "sf-session-gate"), and counting those as cited
# files would manufacture repeats out of batch labels.
_PATH_RE = re.compile(r'^[\w./\\-]+\.(?:js|py|html|json|md|sql|jsonl|sh|ts)$')


class CouldNotRun(Exception):
    pass


def read_log(log_path):
    """Every entry, in file order. Fails CLOSED -- a missing or unparseable
    log is never an empty list silently reported as "no findings, all
    clean", which is the exact shape this platform's own rules forbid."""
    if not os.path.isfile(log_path):
        raise CouldNotRun('self-log not found at %s' % log_path)
    rows = []
    with io.open(log_path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as e:
                raise CouldNotRun('self-log line %d does not parse: %s' % (n, e))
    if not rows:
        raise CouldNotRun('self-log at %s is empty -- nothing to measure '
                          '(an empty log is not a clean result)' % log_path)
    return rows


def cited_paths(entry):
    """The real file paths a finding cites. source_shas keys first (those
    are derived, verified paths written by the staleness guard), then
    path-shaped tokens from the free-text ref. Returns a set, possibly
    empty -- an empty set means this finding cannot contribute to the
    repeat-target denominator, and is counted as uncovered rather than
    treated as a non-repeat."""
    paths = set()
    shas = entry.get('source_shas')
    if isinstance(shas, dict):
        for p in shas:
            if p:
                paths.add(str(p).replace('\\', '/'))
    ref = entry.get('ref')
    if isinstance(ref, str):
        for tok in re.split(r'[,\s;]+', ref):
            tok = tok.strip()
            if tok and _PATH_RE.match(tok):
                paths.add(tok.replace('\\', '/'))
    return paths


def is_finding(entry):
    return entry.get('type') == 'finding'


def discovery_rate(entries):
    """Findings per 100 log entries. The denominator is EVERY entry, not
    only findings -- that is the point: effort spent checking and finding
    nothing is real effort, and dividing findings by findings would always
    return 100%."""
    total = len(entries)
    if total == 0:
        return 0.0, 0, 0
    n = sum(1 for e in entries if is_finding(entry=e))
    return (100.0 * n / total), n, total


def hub_paths(entries, share_pct=HUB_SHARE_PCT):
    """(hubs, counts, covered) -- paths cited by more than `share_pct` of
    findings that cite any resolvable path. Measured from the entries given,
    never a hardcoded filename list, so a new shared dispatcher becomes a
    hub automatically and a retired one stops being one."""
    counts = {}
    covered = 0
    for e in entries:
        if not is_finding(e):
            continue
        paths = cited_paths(e)
        if not paths:
            continue
        covered += 1
        for p in paths:
            counts[p] = counts.get(p, 0) + 1
    if not covered:
        return set(), counts, 0
    threshold = covered * share_pct / 100.0
    return {p for p, n in counts.items() if n > threshold}, counts, covered


def repeat_target_stats(entries, exclude=None):
    """(pct, repeats, covered, uncovered, severe_pct, severe_repeats,
    severe_covered) over the entries given, in order.

    A finding is a REPEAT-TARGET if any path it cites was already cited by
    an EARLIER finding in this same sequence. Strictly earlier -- the first
    finding on a path is never its own repeat. Findings citing no
    resolvable path are UNCOVERED: excluded from the denominator and
    reported separately, never silently counted as non-repeats (which
    would deflate the rate by padding the denominator with rows that could
    not be assessed).

    `exclude` drops hub paths (see HUB_SHARE_PCT) before the comparison. A
    finding whose ONLY cited paths are hubs then has nothing left to assess
    and becomes UNCOVERED rather than silently a non-repeat -- the same
    fail-honest direction as a finding that cited no path at all."""
    exclude = exclude or set()
    seen = set()
    repeats = covered = uncovered = 0
    severe_repeats = severe_covered = 0
    for e in entries:
        if not is_finding(e):
            continue
        paths = cited_paths(e) - exclude
        if not paths:
            uncovered += 1
            continue
        covered += 1
        severe = (e.get('severity') or '').lower() in SEVERE
        if severe:
            severe_covered += 1
        if paths & seen:
            repeats += 1
            if severe:
                severe_repeats += 1
        seen |= paths
    pct = (100.0 * repeats / covered) if covered else None
    severe_pct = (100.0 * severe_repeats / severe_covered) if severe_covered else None
    return pct, repeats, covered, uncovered, severe_pct, severe_repeats, severe_covered


def self_contradiction_stats(entries):
    """(pct, contradicting, findings). A `contradicts` pointer is this
    role's own structured admission that an EARLIER call of its own was
    wrong when made -- the one genuinely precision-shaped signal in this
    log, because it is recorded by the same party it counts against. Not
    the same thing as a build agent disputing a finding (that is Debate,
    and this log does not carry a structured outcome field for it -- named
    as a real gap in the output, not silently approximated)."""
    findings = sum(1 for e in entries if is_finding(e))
    contradicting = sum(1 for e in entries if e.get('contradicts'))
    pct = (100.0 * contradicting / findings) if findings else None
    return pct, contradicting, findings


def clean_streaks(entries):
    """(current_streak, max_streak) of consecutive entries carrying no
    finding. The TUV inversion: a long clean run is a prompt to check
    whether rotation has settled onto already-safe ground, never evidence
    of cleanliness on its own."""
    current = best = 0
    for e in entries:
        if is_finding(e):
            current = 0
        else:
            current += 1
            best = max(best, current)
    return current, best


def severity_mix(entries):
    mix = {}
    for e in entries:
        if not is_finding(e):
            continue
        key = (e.get('severity') or '(unset)').lower()
        mix[key] = mix.get(key, 0) + 1
    return mix


def windows(entries, size):
    """Consecutive entry-count windows, oldest first. A trailing partial
    window is kept and LABELLED partial -- dropping it would hide the most
    recent, most decision-relevant data, and silently padding it would
    distort its own rate."""
    out = []
    for start in range(0, len(entries), size):
        chunk = entries[start:start + size]
        out.append({
            'first_seq': chunk[0].get('seq'),
            'last_seq': chunk[-1].get('seq'),
            'entries': len(chunk),
            'partial': len(chunk) < size,
            'rows': chunk,
        })
    return out


def trend(values):
    """'rising' / 'falling' / 'flat' / None over the last two real values.
    Deliberately two points, not a fitted line: with a handful of windows a
    regression slope would look more authoritative than the data supports,
    which is the manufactured-precision shape SKILL.md forbids."""
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    a, b = vals[-2], vals[-1]
    if abs(b - a) < 1e-9:
        return 'flat'
    return 'rising' if b > a else 'falling'


def analyse(entries, window=DEFAULT_WINDOW):
    overall_rate, n_findings, n_entries = discovery_rate(entries)
    r_pct, r_rep, r_cov, r_unc, s_pct, s_rep, s_cov = repeat_target_stats(entries)
    c_pct, c_n, c_findings = self_contradiction_stats(entries)
    cur_streak, max_streak = clean_streaks(entries)

    hubs, path_counts, hub_denom = hub_paths(entries)
    h_pct, h_rep, h_cov, h_unc, hs_pct, hs_rep, hs_cov = repeat_target_stats(
        entries, exclude=hubs)

    wins = []
    for w in windows(entries, window):
        rate, nf, ne = discovery_rate(w['rows'])
        wr_pct, wr_rep, wr_cov, wr_unc, _, _, _ = repeat_target_stats(w['rows'])
        wh_pct, _, wh_cov, _, _, _, _ = repeat_target_stats(w['rows'], exclude=hubs)
        wins.append({
            'first_seq': w['first_seq'], 'last_seq': w['last_seq'],
            'entries': w['entries'], 'partial': w['partial'],
            'discovery_rate_per_100': round(rate, 2),
            'findings': nf,
            'repeat_target_pct': None if wr_pct is None else round(wr_pct, 2),
            'repeat_covered': wr_cov,
            'repeat_target_pct_ex_hubs': None if wh_pct is None else round(wh_pct, 2),
            'repeat_covered_ex_hubs': wh_cov,
        })

    alarms = []
    # THE ALARM FIRES ON THE EX-HUBS RATE, not the raw one -- the raw rate
    # was measured at 81% on this platform purely because two shared files
    # are touched by a third of all findings, which says nothing about
    # recurrence. The raw figure is still reported, never hidden; it is just
    # not what triggers.
    if h_pct is not None and h_pct > REPEAT_BENCHMARK_PCT:
        alarms.append(
            'repeat-target rate EXCLUDING hub files is %.1f%% of %d covered '
            'finding(s) -- above the published RAFR benchmark of %.0f%%. READ '
            'THE REPEATS: this is still a proxy (same file re-cited), not '
            'proof the same root cause recurred'
            % (h_pct, h_cov, REPEAT_BENCHMARK_PCT))
    if hs_pct is not None and hs_pct > REPEAT_BENCHMARK_SEVERE_PCT:
        alarms.append(
            'repeat-target rate among critical/high findings, excluding hub '
            'files, is %.1f%% of %d -- above the published %.0f%% benchmark '
            'for Critical/Major'
            % (hs_pct, hs_cov, REPEAT_BENCHMARK_SEVERE_PCT))
    # The TUV inversion, with a MEASURED baseline rather than a picked
    # number: the alarm fires when the CURRENT clean run exceeds this log's
    # own historical worst, i.e. this is already the longest quiet stretch
    # on record. No invented constant to go stale.
    if max_streak > 0 and cur_streak >= max_streak and cur_streak > 1:
        alarms.append(
            'current clean streak (%d consecutive entries with no finding) '
            'equals or exceeds this log\'s own historical maximum (%d) -- the '
            'TUV inversion: a record-long quiet stretch is a prompt to check '
            'whether rotation has settled onto already-safe ground, never '
            'evidence of cleanliness' % (cur_streak, max_streak))

    return {
        'entries': n_entries,
        'findings': n_findings,
        'discovery_rate_per_100': round(overall_rate, 2),
        'repeat_target_pct': None if r_pct is None else round(r_pct, 2),
        'repeat_target_repeats': r_rep,
        'repeat_target_covered': r_cov,
        'repeat_target_uncovered': r_unc,
        'repeat_target_severe_pct': None if s_pct is None else round(s_pct, 2),
        'repeat_target_severe_repeats': s_rep,
        'repeat_target_severe_covered': s_cov,
        'repeat_target_pct_ex_hubs': None if h_pct is None else round(h_pct, 2),
        'repeat_target_repeats_ex_hubs': h_rep,
        'repeat_target_covered_ex_hubs': h_cov,
        'repeat_target_uncovered_ex_hubs': h_unc,
        'repeat_target_severe_pct_ex_hubs': None if hs_pct is None else round(hs_pct, 2),
        'repeat_target_severe_repeats_ex_hubs': hs_rep,
        'repeat_target_severe_covered_ex_hubs': hs_cov,
        'hub_paths': sorted(hubs),
        'hub_share_pct': HUB_SHARE_PCT,
        'hub_denominator': hub_denom,
        'top_cited_paths': sorted(path_counts.items(),
                                   key=lambda kv: (-kv[1], kv[0]))[:10],
        'distinct_cited_paths': len(path_counts),
        'citation_concentration_top10_pct': (
            None if not path_counts else round(
                100.0 * sum(n for _, n in sorted(
                    path_counts.items(), key=lambda kv: -kv[1])[:10])
                / sum(path_counts.values()), 2)),
        'total_citations': sum(path_counts.values()),
        'self_contradiction_pct': None if c_pct is None else round(c_pct, 2),
        'self_contradictions': c_n,
        'clean_streak_current': cur_streak,
        'clean_streak_max': max_streak,
        'severity_mix': severity_mix(entries),
        'window_size': window,
        'windows': wins,
        'discovery_rate_trend': trend([w['discovery_rate_per_100'] for w in wins]),
        'repeat_target_trend': trend([w['repeat_target_pct'] for w in wins]),
        'repeat_target_trend_ex_hubs': trend(
            [w['repeat_target_pct_ex_hubs'] for w in wins]),
        'alarms': alarms,
        'benchmarks': {'repeat_pct': REPEAT_BENCHMARK_PCT,
                       'repeat_severe_pct': REPEAT_BENCHMARK_SEVERE_PCT},
    }


def render(res):
    L = []
    L.append('HOVER AUDIT-EFFECTIVENESS METRICS -- this role measuring ITSELF')
    L.append('  %d log entries, %d finding(s)' % (res['entries'], res['findings']))
    L.append('')
    L.append('DISCOVERY RATE (red-team metric: validated findings per unit effort)')
    L.append('  overall: %.2f findings per 100 log entries  (denominator: all '
             '%d entries, checks included -- effort that found nothing is '
             'still effort)' % (res['discovery_rate_per_100'], res['entries']))
    L.append('  trend across windows: %s' % (res['discovery_rate_trend'] or
                                              'n/a (need 2+ windows)'))
    L.append('')
    L.append('REPEAT-TARGET RATE (proxy for internal-audit RAFR; benchmark '
             '<=%.0f%%, <=%.0f%% critical/high)'
             % (res['benchmarks']['repeat_pct'],
                res['benchmarks']['repeat_severe_pct']))
    if res['repeat_target_pct'] is None:
        L.append('  COULD NOT MEASURE: no finding cites a resolvable path')
    else:
        L.append('  %.2f%% -- %d repeat(s) of %d finding(s) WITH a resolvable '
                 'cited path' % (res['repeat_target_pct'],
                                  res['repeat_target_repeats'],
                                  res['repeat_target_covered']))
        L.append('  %d finding(s) cite no resolvable path: UNCOVERED, excluded '
                 'from that denominator rather than counted as non-repeats'
                 % res['repeat_target_uncovered'])
    if res['repeat_target_severe_pct'] is None:
        L.append('  critical/high: none with a resolvable path -- not measured')
    else:
        L.append('  critical/high: %.2f%% -- %d of %d'
                 % (res['repeat_target_severe_pct'],
                    res['repeat_target_severe_repeats'],
                    res['repeat_target_severe_covered']))
    L.append('  trend: %s' % (res['repeat_target_trend'] or 'n/a (need 2+ windows)'))
    L.append('  WHAT THIS IS NOT: real RAFR means the same issue recurred '
             'after being fixed. This sees "a later finding cited a file an '
             'earlier finding already cited" -- a real recurrence looks like '
             'this, and so does a genuinely new defect in a much-audited file.')
    L.append('')
    L.append('  -- THE SAME RATE, EXCLUDING HUB FILES (this is the one the '
             'alarm uses) --')
    L.append('  HUBS, derived not hardcoded: a path cited by >%.0f%% of the '
             '%d findings that cite any path. %d distinct path(s) cited '
             'overall; %d qualify as hub(s):'
             % (res['hub_share_pct'], res['hub_denominator'],
                res['distinct_cited_paths'], len(res['hub_paths'])))
    for p in res['hub_paths']:
        n = dict(res['top_cited_paths']).get(p)
        L.append('     %s%s' % (p, '' if n is None else ' (%d citations)' % n))
    if res['repeat_target_pct_ex_hubs'] is None:
        L.append('  ex-hubs: COULD NOT MEASURE -- no finding cites a '
                 'non-hub path')
    else:
        L.append('  ex-hubs: %.2f%% -- %d repeat(s) of %d finding(s) citing '
                 'at least one NON-hub path (%d more are uncovered once hubs '
                 'are removed: their only citations were hubs)'
                 % (res['repeat_target_pct_ex_hubs'],
                    res['repeat_target_repeats_ex_hubs'],
                    res['repeat_target_covered_ex_hubs'],
                    res['repeat_target_uncovered_ex_hubs']))
    if res['repeat_target_severe_pct_ex_hubs'] is not None:
        L.append('  ex-hubs critical/high: %.2f%% -- %d of %d'
                 % (res['repeat_target_severe_pct_ex_hubs'],
                    res['repeat_target_severe_repeats_ex_hubs'],
                    res['repeat_target_severe_covered_ex_hubs']))
    L.append('  ex-hubs trend: %s' % (res['repeat_target_trend_ex_hubs']
                                       or 'n/a (need 2+ windows)'))
    L.append('  WHY: this tool\'s own first live run alarmed at 80.95% raw. '
             'Following that alarm found the cause was the platform\'s SHAPE '
             '-- two shared files carry a third of all citations -- not '
             'recurring defects. The raw number stays printed; the ex-hubs '
             'number is what means something here.')
    L.append('  TOP-CITED PATHS (so the hub choice can be re-derived):')
    for p, n in res['top_cited_paths'][:6]:
        L.append('     %4d  %s' % (n, p))
    if res['citation_concentration_top10_pct'] is not None:
        L.append('  CITATION CONCENTRATION: the top 10 paths carry %.1f%% of '
                 'all %d finding-citations across %d distinct paths.'
                 % (res['citation_concentration_top10_pct'],
                    res['total_citations'], res['distinct_cited_paths']))
    L.append('  MEASURED VERDICT ON THIS METRIC, not tuned away: excluding '
             'hubs moved the rate 81%->70%, so the proxy is still dominated '
             'by structure rather than recurrence. The reason is the real '
             'shape of this codebase -- ~17 single-file apps plus 2 shared '
             'hubs -- so almost any second finding in an app re-cites that '
             'app\'s one file. CONCLUSION: at FILE granularity the repeat '
             'proxy is not informative here, and no threshold fixes that. '
             'Real RAFR needs resource/function granularity (the per-resource '
             'identity the tier register already carries). Named as this '
             'tool\'s own real limit and a real next step, rather than tuned '
             'until it produced a comfortable number.')
    L.append('')
    L.append('SELF-CONTRADICTION RATE (own earlier call recorded as wrong)')
    if res['self_contradiction_pct'] is None:
        L.append('  not measurable: no findings')
    else:
        L.append('  %.2f%% -- %d contradicting entr(ies) against %d finding(s)'
                 % (res['self_contradiction_pct'], res['self_contradictions'],
                    res['findings']))
    L.append('  GAP, NAMED: Debate outcomes (a build agent disputing a '
             'finding, confirmed vs explained-away) have no structured field '
             'in this log, so that calibration number -- which SKILL.md asks '
             'for -- still cannot be computed. Not approximated here.')
    L.append('')
    L.append('CLEAN STREAK (TUV inversion)')
    L.append('  current %d consecutive entries with no finding; historical max %d'
             % (res['clean_streak_current'], res['clean_streak_max']))
    L.append('')
    L.append('SEVERITY MIX: %s' % (', '.join(
        '%s=%d' % (k, v) for k, v in sorted(res['severity_mix'].items())) or 'none'))
    L.append('')
    L.append('WINDOWS of %d entries (NOT batches -- only 46 of 435 findings '
             'carry a parseable batch marker, measured, so entry-count '
             'windows are used instead)' % res['window_size'])
    for w in res['windows']:
        L.append('  seq %s-%s%s: %.2f/100 (%d finding(s)); repeat-target raw '
                 '%s | ex-hubs %s'
                 % (w['first_seq'], w['last_seq'],
                    ' [PARTIAL]' if w['partial'] else '',
                    w['discovery_rate_per_100'], w['findings'],
                    'n/a' if w['repeat_target_pct'] is None
                    else '%.1f%% of %d' % (w['repeat_target_pct'], w['repeat_covered']),
                    'n/a' if w['repeat_target_pct_ex_hubs'] is None
                    else '%.1f%% of %d' % (w['repeat_target_pct_ex_hubs'],
                                            w['repeat_covered_ex_hubs'])))
    L.append('')
    L.append('THE AMBIGUITY THIS CANNOT RESOLVE, STATED EVERY RUN: a falling '
             'discovery rate is equally consistent with this role becoming '
             'less effective AND with the platform genuinely getting cleaner. '
             'One log cannot separate them. Every number above is a '
             'measurement to go look at, never a verdict.')
    if res['alarms']:
        L.append('')
        L.append('ALARM(S) -- each means GO LOOK, not "you are bad at this":')
        for a in res['alarms']:
            L.append('  - %s' % a)
    else:
        L.append('')
        L.append('No alarm: repeat-target rate within benchmark and the current '
                 'clean streak is not a record. A measured all-clear, not an '
                 'unrun check.')
    return '\n'.join(L)


# ── fixtures ──────────────────────────────────────────────────────────────

def _selftest():
    import tempfile
    import shutil

    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    real_lines = 0
    if os.path.isfile(DEFAULT_LOG):
        with io.open(DEFAULT_LOG, encoding='utf-8') as f:
            real_lines = sum(1 for l in f if l.strip())

    def entry(seq, type_='check', severity='', shas=None, ref='', contradicts=None):
        e = {'seq': seq, 'type': type_, 'severity': severity, 'ref': ref,
             'summary': 'fixture', 'target': 'self',
             'ts': '2026-10-19T00:00:00Z'}
        if shas is not None:
            e['source_shas'] = {p: 'a' * 40 for p in shas}
        if contradicts is not None:
            e['contradicts'] = contradicts
        return e

    # --- cited_paths: the two real sources, and the non-path rejections ---
    ck('cited_paths reads source_shas keys',
       cited_paths(entry(1, shas=['api/x.js'])) == {'api/x.js'})
    ck('cited_paths picks a path-shaped token out of a free-text ref',
       cited_paths(entry(1, ref='api/y.js,sf-session-gate')) == {'api/y.js'})
    ck('KNOWN-BAD CONTROL: a batch tag in ref is NOT counted as a cited '
       'path (counting "b15,b16" as files would manufacture repeats)',
       cited_paths(entry(1, ref='b15,b16,b17')) == set())
    ck('cited_paths normalises backslashes so one file is not two paths',
       cited_paths(entry(1, shas=['api\\z.js'])) == {'api/z.js'})
    ck('cited_paths unions both sources without duplicating',
       cited_paths(entry(1, shas=['api/a.js'], ref='api/a.js,api/b.js'))
       == {'api/a.js', 'api/b.js'})

    # --- discovery rate: denominator is ALL entries, not findings ---
    rate, nf, ne = discovery_rate([entry(1), entry(2, 'finding'), entry(3), entry(4)])
    ck('discovery_rate counts findings over ALL entries (1 of 4 = 25/100)',
       abs(rate - 25.0) < 1e-9 and nf == 1 and ne == 4)
    ck('discovery_rate on an empty list is 0, not a crash',
       discovery_rate([])[0] == 0.0)

    # --- repeat-target: FAILING-FIRST, the bad state asserted before the good ---
    rows_repeat = [
        entry(1, 'finding', 'high', shas=['api/x.js']),
        entry(2, 'finding', 'high', shas=['api/x.js']),   # repeat of x
        entry(3, 'finding', 'low', shas=['api/y.js']),    # first on y
    ]
    pct, rep, cov, unc, spct, srep, scov = repeat_target_stats(rows_repeat)
    ck('F1 (failing-first) a genuine re-cite IS counted a repeat (1 of 3 '
       'covered = 33.3%)', rep == 1 and cov == 3 and abs(pct - 100.0 / 3) < 1e-6)
    ck('F2 the FIRST finding on a path is never its own repeat', rep == 1)
    ck('F3 severe (critical/high) repeats are counted separately (1 of 2)',
       srep == 1 and scov == 2)

    rows_clean = [
        entry(1, 'finding', 'high', shas=['api/x.js']),
        entry(2, 'finding', 'high', shas=['api/y.js']),
    ]
    pct2, rep2, cov2, _, _, _, _ = repeat_target_stats(rows_clean)
    ck('G1 distinct paths produce a 0% repeat rate, not a false positive',
       rep2 == 0 and pct2 == 0.0 and cov2 == 2)

    rows_unc = [entry(1, 'finding', 'high', ref='b15'),
                entry(2, 'finding', 'high', shas=['api/x.js'])]
    pct3, rep3, cov3, unc3, _, _, _ = repeat_target_stats(rows_unc)
    ck('C1 a finding citing no resolvable path is UNCOVERED -- excluded '
       'from the denominator, never counted as a non-repeat (cov=1, unc=1)',
       cov3 == 1 and unc3 == 1)
    ck('C2 repeat rate is None (not 0.0) when nothing could be assessed',
       repeat_target_stats([entry(1, 'finding', 'high', ref='b1')])[0] is None)

    # --- a check (not a finding) citing a path must not seed the repeat set ---
    rows_check_first = [entry(1, 'check', shas=['api/x.js']),
                        entry(2, 'finding', 'high', shas=['api/x.js'])]
    ck('C3 KNOWN-BAD CONTROL: a CHECK citing a path does not make the next '
       'finding on that path a repeat -- repeats are finding-to-finding',
       repeat_target_stats(rows_check_first)[1] == 0)

    # --- hub detection and the ex-hubs rate, the b68 self-caught correction ---
    # A hub file touched by nearly every finding, plus one genuinely
    # repeated non-hub file, plus distinct non-hub files. Raw rate should be
    # near-total; ex-hubs should isolate the ONE real repeat.
    hub_rows = [
        entry(1, 'finding', 'high', shas=['docs/HUB.md', 'api/a.js']),
        entry(2, 'finding', 'high', shas=['docs/HUB.md', 'api/b.js']),
        entry(3, 'finding', 'high', shas=['docs/HUB.md', 'api/c.js']),
        entry(4, 'finding', 'high', shas=['docs/HUB.md', 'api/a.js']),  # real repeat: a.js
    ]
    hubs, counts, denom = hub_paths(hub_rows, share_pct=50.0)
    ck('H1 hub_paths derives the hub from the measured distribution (HUB.md '
       'in 4 of 4 findings), never a hardcoded name',
       hubs == {'docs/HUB.md'} and denom == 4)
    ck('H2 a non-hub file cited once is NOT a hub',
       'api/b.js' not in hubs and counts['api/b.js'] == 1)
    raw_pct, raw_rep, raw_cov, _, _, _, _ = repeat_target_stats(hub_rows)
    ck('H3 the RAW rate is inflated by the hub (3 of 4 are repeats purely '
       'because every finding cites HUB.md)', raw_rep == 3 and raw_cov == 4)
    ex_pct, ex_rep, ex_cov, ex_unc, _, _, _ = repeat_target_stats(
        hub_rows, exclude=hubs)
    ck('H4 the EX-HUBS rate isolates the one REAL repeat (api/a.js re-cited) '
       '-- 1 of 4, not 3 of 4', ex_rep == 1 and ex_cov == 4)
    ck('H5 KNOWN-BAD CONTROL: excluding hubs must NOT also erase the real '
       'repeat -- a filter that returned 0 here would be hiding the signal '
       'it exists to isolate', ex_rep != 0)
    only_hub = [entry(1, 'finding', 'high', shas=['docs/HUB.md']),
                entry(2, 'finding', 'high', shas=['docs/HUB.md'])]
    oh_pct, oh_rep, oh_cov, oh_unc, _, _, _ = repeat_target_stats(
        only_hub, exclude={'docs/HUB.md'})
    ck('H6 a finding whose ONLY citations are hubs becomes UNCOVERED, not a '
       'silent non-repeat (cov=0, unc=2, pct=None)',
       oh_cov == 0 and oh_unc == 2 and oh_pct is None)
    ck('H7 hub_paths on zero covered findings returns an empty hub set, not '
       'a crash or a divide-by-zero',
       hub_paths([entry(1, 'check')]) == (set(), {}, 0))

    # H8 CORRECTED, 2026-10-19, AND SAID RATHER THAN SILENTLY ADJUSTED: the
    # first version asserted analyse() always reports BOTH rates, and it
    # FAILED on this 4-finding fixture. The code was right and the
    # assertion was wrong -- on a 4-finding log every cited path clears a
    # 10%-of-findings hub threshold (a.js is 2 of 4 = 50%), so everything
    # is a hub, nothing is left to compare, and the ex-hubs rate is
    # correctly None rather than a fabricated 0%. That small-sample
    # property is worth locking as the real behaviour, so it is asserted
    # here in both directions instead of being hidden by loosening the test.
    res_hub_small = analyse(hub_rows, window=100)
    ck('H8a SMALL-SAMPLE HONESTY: with the default %.0f%% threshold and only '
       '4 findings, every path qualifies as a hub, so the ex-hubs rate is '
       'None (could-not-measure) rather than a fabricated 0%%'
       % HUB_SHARE_PCT,
       res_hub_small['repeat_target_pct'] is not None
       and res_hub_small['repeat_target_pct_ex_hubs'] is None)

    # A realistically-shaped log: 20 findings on distinct files, one real
    # repeat on a non-hub path (2 of 22 citations = 9%, under the 10%
    # threshold), and one genuine hub cited by all of them.
    real_shape = []
    for i in range(1, 21):
        real_shape.append(entry(i, 'finding', 'moderate',
                                 shas=['docs/HUB.md', 'api/f%d.js' % i]))
    real_shape.append(entry(21, 'finding', 'moderate',
                             shas=['docs/HUB.md', 'api/dup.js']))
    real_shape.append(entry(22, 'finding', 'moderate',
                             shas=['docs/HUB.md', 'api/dup.js']))
    res_real = analyse(real_shape, window=100)
    ck('H8b on a realistically-shaped log BOTH rates are reported, and the '
       'ex-hubs rate is far lower than the raw one (raw %.1f%% vs ex-hubs '
       '%.1f%%) -- the whole point of the correction'
       % (res_real['repeat_target_pct'] or -1,
          res_real['repeat_target_pct_ex_hubs'] or -1),
       res_real['repeat_target_pct'] is not None
       and res_real['repeat_target_pct_ex_hubs'] is not None
       and res_real['repeat_target_pct_ex_hubs'] < res_real['repeat_target_pct'])
    ck('H8c the ex-hubs rate catches the ONE real non-hub repeat (api/dup.js)',
       res_real['repeat_target_repeats_ex_hubs'] == 1)
    ck('H8d docs/HUB.md is identified as the hub on the realistic fixture too',
       res_real['hub_paths'] == ['docs/HUB.md'])
    hub_text = render(res_hub_small)
    ck('H9 render names the real hub path(s) so the correction is auditable',
       'docs/HUB.md' in hub_text and 'EXCLUDING HUB FILES' in hub_text)

    # --- self-contradiction ---
    cpct, cn, cf = self_contradiction_stats(
        [entry(1, 'finding', 'high'), entry(2, 'finding', 'high', contradicts=1)])
    ck('self_contradiction_stats counts contradicts pointers against findings',
       cn == 1 and cf == 2 and abs(cpct - 50.0) < 1e-9)

    # --- clean streaks ---
    cur, mx = clean_streaks([entry(1), entry(2), entry(3, 'finding'), entry(4)])
    ck('clean_streaks: current resets after a finding, max remembers the run',
       cur == 1 and mx == 2)

    # --- windows ---
    ws = windows([entry(i) for i in range(1, 6)], 2)
    ck('windows splits oldest-first and LABELS the trailing partial window',
       len(ws) == 3 and ws[-1]['partial'] is True and ws[0]['partial'] is False)

    # --- trend: two points only, and the None cases ---
    ck('trend rising', trend([1.0, 2.0]) == 'rising')
    ck('trend falling', trend([2.0, 1.0]) == 'falling')
    ck('trend flat', trend([2.0, 2.0]) == 'flat')
    ck('trend is None with fewer than 2 real values (never a fabricated '
       'direction from one point)', trend([1.0]) is None and trend([None, 1.0]) is None)

    # --- the alarms, both directions ---
    # A1 CORRECTED, 2026-10-19, SAME DECLARATION AS H8: the first version
    # used 5 findings all citing ONE path and asserted an alarm. It FAILED
    # after the hub correction, and correctly so -- a single path cited by
    # 5 of 5 findings IS a hub, so it is excluded and nothing is left to
    # alarm on. The alarm now fires on the ex-hubs rate by design, so the
    # fixture had to become a shape where the repeats are on NON-hub paths:
    # 12 distinct hub-paired findings plus 4 repeats spread over 2 non-hub
    # files, which clears the 10% threshold for each repeated path while
    # putting the ex-hubs rate above the 5% benchmark.
    #
    # THE ARITHMETIC, WORKED OUT RATHER THAN GUESSED AT (the first corrected
    # attempt still failed at 0.0% because 2 citations out of 16 findings is
    # 12.5%, which made the repeated paths hubs too): with N covered
    # findings and k paths each cited twice, a repeated path stays a non-hub
    # while 2 <= 0.10*N, i.e. N >= 20, and the ex-hubs rate k/N clears the
    # 5% benchmark while k > 0.05*N. N=22, k=2 satisfies both: each repeated
    # path is 2/22 = 9.1% (not > 2.2, so not a hub) and the rate is
    # 2/22 = 9.1% (> 5%, so it alarms).
    alarm_rows = []
    for i in range(1, 19):
        alarm_rows.append(entry(i, 'finding', 'high',
                                 shas=['docs/HUB.md', 'api/u%d.js' % i]))
    for j, path in enumerate(['api/r1.js', 'api/r1.js', 'api/r2.js', 'api/r2.js']):
        alarm_rows.append(entry(19 + j, 'finding', 'high',
                                 shas=['docs/HUB.md', path]))
    res_alarm = analyse(alarm_rows, window=100)
    ck('A1 an over-benchmark EX-HUBS repeat rate RAISES an alarm (2 real '
       'repeats on non-hub paths, %s%%)'
       % (res_alarm['repeat_target_pct_ex_hubs']),
       any('EXCLUDING hub files' in a and 'RAFR benchmark' in a
           for a in res_alarm['alarms']))
    res_quiet = analyse(rows_clean, window=100)
    ck('A2 KNOWN-BAD CONTROL: a within-benchmark log raises NO repeat alarm '
       '(an always-alarming checker is worth nothing)',
       not any('RAFR benchmark' in a for a in res_quiet['alarms']))
    ck('A2b KNOWN-BAD CONTROL: a log whose only repeats are on a HUB path '
       'raises no repeat alarm -- that is the false alarm this correction '
       'exists to stop',
       not any('RAFR benchmark' in a for a in analyse(
           [entry(i, 'finding', 'high', shas=['docs/HUB.md'])
            for i in range(1, 8)], window=100)['alarms']))

    streak_rows = [entry(1, 'finding', 'high', shas=['api/x.js'])] + \
                  [entry(i) for i in range(2, 8)]
    res_streak = analyse(streak_rows, window=100)
    ck('A3 a record-long current clean streak raises the TUV alarm',
       any('TUV inversion' in a for a in res_streak['alarms']))

    # --- analyse() end to end, and the honest-ambiguity line is always printed ---
    text = render(analyse(rows_repeat, window=2))
    ck('render always states the discovery-rate ambiguity it cannot resolve',
       'cannot separate them' in text)
    ck('render always prints the repeat-rate denominator, never a bare pct',
       'finding(s) WITH a resolvable cited path' in text)
    ck('render names the Debate-outcome gap rather than approximating it',
       'no structured field' in text)

    # --- fail-closed paths ---
    tmp = tempfile.mkdtemp(prefix='hover_audit_eff_fx_')
    try:
        missing = os.path.join(tmp, 'nope.jsonl')
        raised = False
        try:
            read_log(missing)
        except CouldNotRun:
            raised = True
        ck('FAIL-CLOSED: a missing log raises CouldNotRun, never an empty '
           '"all clean" result', raised)

        empty = os.path.join(tmp, 'empty.jsonl')
        io.open(empty, 'w', encoding='utf-8').close()
        raised2 = False
        try:
            read_log(empty)
        except CouldNotRun:
            raised2 = True
        ck('FAIL-CLOSED: an EMPTY log raises CouldNotRun -- an empty log is '
           'not a clean result', raised2)

        broken = os.path.join(tmp, 'broken.jsonl')
        with io.open(broken, 'w', encoding='utf-8') as f:
            f.write(json.dumps(entry(1)) + '\n')
            f.write('{not json\n')
        raised3 = False
        try:
            read_log(broken)
        except CouldNotRun as e:
            raised3 = 'line 2' in str(e)
        ck('FAIL-CLOSED: an unparseable line raises CouldNotRun naming the '
           'real line number, never a partial silent read', raised3)

        good = os.path.join(tmp, 'good.jsonl')
        with io.open(good, 'w', encoding='utf-8') as f:
            for e in rows_repeat:
                f.write(json.dumps(e) + '\n')
        ck('read_log reads a real file back in order',
           [r['seq'] for r in read_log(good)] == [1, 2, 3])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    lines_after = 0
    if os.path.isfile(DEFAULT_LOG):
        with io.open(DEFAULT_LOG, encoding='utf-8') as f:
            lines_after = sum(1 for l in f if l.strip())
    ck('SAFETY NET: the real self-log gained zero lines during this selftest '
       '(before=%d, after=%d)' % (real_lines, lines_after),
       lines_after == real_lines)

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--log', default=DEFAULT_LOG)
    ap.add_argument('--window', type=int, default=DEFAULT_WINDOW)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        return EXIT_OK if _selftest() else 1

    if args.window < 1:
        print('COULD NOT RUN: --window must be >= 1')
        return EXIT_COULD_NOT_RUN
    try:
        rows = read_log(args.log)
    except CouldNotRun as e:
        print('COULD NOT RUN: %s' % e)
        return EXIT_COULD_NOT_RUN

    res = analyse(rows, window=args.window)
    if args.json:
        print(json.dumps(res, indent=1, sort_keys=True))
    else:
        print(render(res))
    return EXIT_ALARM if res['alarms'] else EXIT_OK


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
