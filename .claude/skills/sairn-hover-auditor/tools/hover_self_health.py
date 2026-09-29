#!/usr/bin/env python
"""
hover_self_health.py -- the hover-auditor's own system-of-quality-control check,
distinct from any check of a single finding. Built 2026-09-15.

WHY THIS EXISTS, NAMED PLAINLY (three real precedents, not one):
  1. PCAOB inspects audit FIRMS, not only individual audit engagements --
     tone at the top, independence, how work gets accepted. Everything else
     this role does is the engagement-level check. This is the firm-level one,
     aimed at itself.
  2. 14 CFR 61.57 (pilot currency): a privilege lapses without recent, GENUINE
     exercise and must be re-earned -- and currency is explicitly NOT the same
     claim as proficiency. Flying the same three landings every 90 days is
     legally current and not actually proficient. This file's routine-detection
     and technique-staleness sections are that test applied to this role.
  3. Amazon's Bar Raiser: independence that can quietly erode the closer the
     checker sits to shipping pressure, and a bar that can quietly lower
     without anyone deciding it should. This file's evidence-strength-trend
     and independence-proxy sections are that test applied to this role.

WHAT WOULD MAKE THIS CHECK FAIL, STATED BEFORE ANY RUN, NOT AFTER (so a bad
result cannot be explained away as "that's just what the number means"):
  - ROUTINE:      the same target checked twice in a row (an explicit,
                   already-written rotation rule), or one target receiving
                   more than ~40% of all check/finding attention with no
                   Tier/freshness justification visible in this file alone.
  - STALENESS:    any framework named in SKILL.md's substantial-length
                   sections (approx. one paragraph or more of dedicated
                   material) that has ZERO occurrences in any check or
                   finding entry -- only ever appearing in a "note" entry
                   about writing the file, never in a "check"/"finding" about
                   using it.
  - BAR DRIFT:    the fraction of check/finding entries carrying at least one
                   direct-evidence marker (ran/drove/planted/queried/manually/
                   independently confirmed) drops by more than 15 percentage
                   points from the first half of this role's history to the
                   second half.
  - INDEPENDENCE: 100% of checks landing on work that is either freshest-
                   commit or currently-active-claim, with never a single
                   instance of picking older, already-settled, or
                   deliberately re-checked-after-clean work.

THIS CANNOT BE QUIETLY TUNED TO PASS. The thresholds above are written into
this docstring BEFORE the numbers below were computed for this run, and the
mechanical parts (target-repeat detection, keyword presence) have no branch
that could be adjusted post-hoc without editing this comment block too --
which is why the thresholds are stated here, in prose, rather than only in
a config value a future run could silently change without anyone noticing
the goalposts moved. The append-only self-log this reads from is the same
protection LIGO's sealed injection envelope and this platform's hash-chain
already rely on: the input this script reads cannot be rewritten to look
better after the fact.

WHAT THIS DOES NOT COVER, STATED PLAINLY (an implied-broader-assurance claim
is worse than no claim at all):
  - It cannot see technique applied-but-not-named (a false NEVER-USED) or
    technique named-but-not-really-applied (a false USED) -- keyword presence
    in a summary is a proxy for the real thing, not the real thing.
  - It cannot reconstruct historical claim-activity timing (how fresh a claim
    was at the moment I picked it) for entries logged before this script
    existed -- the self-log does not store that. The independence proxy below
    uses only what IS stored: inter-check time gaps and target selection,
    which answer a narrower question than "was I under queue pressure."
  - It cannot judge whether a REASONING PATTERN (as opposed to a target or a
    technique) has gone stale -- that would need semantic judgment of my own
    prose, which a mechanical pass over the same prose cannot independently
    verify. Flagged as an open gap, not silently assumed covered.
  - A clean result here is a statement about the FIRM'S PROCESS as visible in
    this log, on this run, against these thresholds -- not a guarantee
    nothing has drifted in a way this file does not measure.

Run:  python hover_self_health.py [--log PATH]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

DEFAULT_LOG = 'hover-audit-log.jsonl'

# ── FRAMEWORKS NAMED AT SUBSTANTIAL LENGTH IN SKILL.md, EACH A REAL, SEPARATE
# TECHNIQUE RATHER THAN A REWORDING OF ANOTHER ONE ALREADY ON THE LIST ────────
# Keyword lists are deliberately narrow and literal (not stemmed / fuzzy) so a
# hit is a real textual claim of use, not a coincidental word match.
TECHNIQUES = {
    'STRIDE (threat-modeling property lens)': ['stride'],
    'MITRE ATT&CK (post-exploitation)': ['att&ck', 'mitre'],
    'PTES / dedicated threat-modeling pass': ['ptes', 'threat model', 'threat-model'],
    'Chaos engineering (hypothesis-first injection)': ['chaos engineer', 'gameday', 'ghost plane'],
    "Marzullo's Algorithm (third-source consensus)": ['marzullo'],
    'WADA biological-passport / individual baseline staircase': ['biological passport', 'staircase', 'individual baseline'],
    'IRS-style unweighted random sampling': ['unweighted', 'no-change rate'],
    'WCAG-EM sampling / accessibility audit': ['wcag', 'accessibility'],
    'License / IP compliance audit': ['license compliance', 'copyleft', 'sbom'],
    'FinOps / showback': ['finops', 'showback'],
    'DORA metrics': ['dora metric', 'deployment frequency', 'mttr', 'change failure rate'],
    'CMMI maturity ladder': ['cmmi'],
    'SLSA build provenance': ['slsa'],
    'Bus-factor / dependency health scanner': ['bus factor', 'bus-factor', 'dependency_health_check'],
    # 'secrets-scan' (no trailing space) is deliberate: it is the substring
    # shared by "secrets-scan", "secrets-scanning" and "secrets-scanner".
    # Added 2026-09-16 after a demonstrated FALSE never-used: entry 97 is a
    # real, platform-targeted application of this technique whose summary
    # opens "Secrets-scanning technique (queue item), applied for real",
    # and the prior keyword list ('secrets scan' with a space,
    # 'secrets-history') matched neither word-form. One technique of the
    # fifteen was reported unused for a hyphen. The other fourteen were
    # re-probed against the same corpus for near-miss word-forms at the
    # same time and are genuinely absent, not mis-spelled.
    'Secrets-history scan (TruffleHog/Gitleaks-style)': ['trufflehog', 'gitleaks', 'secrets scan', 'secrets-scan', 'secrets-history'],
    'CodeQL-style recurring dataflow check': ['codeql', 'data-flow tracing', 'dataflow'],
    'IOLTA three-way reconciliation': ['iolta', 'three-way'],
    'Common Criteria EAL / assurance-verification-certification vocabulary': ['common criteria', 'eal', 'assurance, verification'],
    'Formal equivalence checking (pure-core diff)': ['equivalence check'],
    'Technical due diligence (5 pillars)': ['technical due diligence', 'bus-factor scanner'],
    'Diátaxis documentation audit': ['diataxis', 'diátaxis'],
    'Purple teaming (real-time debate)': ['purple team'],
    'FIA scrutineering-style spec-vs-artifact diff': ['scrutineer', 'deep dive'],
    'GLI two-stage (selection + mapping) proof': ['gli ', 'gaming laboratories'],
    'Audit Risk Model (inherent/control/detection risk)': ['inherent risk', 'control risk', 'detection risk'],
}

STRONG_EVIDENCE_MARKERS = [
    'ran ', 'ran myself', 'ran it myself', 'drove', 'planted', 'manually',
    'independently confirmed', 'queried', 'reverted', 'hand-planted',
    'byte-identical', 'node --check', 'confirmed directly', 'grep confirms',
    'read directly', 'read the actual', 'live network', 'confirmed live',
    # ADDED 2026-09-28, NOT because these words appear often in a recent
    # window -- picking markers by frequency in the data you are about to
    # score is the exact FMEA-scorer failure named in the disciplines doc
    # ("a criterion chosen by looking at what produced a number"). Added
    # because they name the SAME category as every marker above -- a claim
    # to have looked at the primary artifact directly, not reasoned about
    # it -- and the vocabulary for that category shifted when this role's
    # dominant work shifted from build-agent feature verification (runtime
    # probes, sabotage mutations) to register/tier-cell auditing (reading a
    # seed, a write site and its consumers against a cited line). Both are
    # equally direct; only the WORDS for "I looked" changed. Locked by the
    # fixture control below BEFORE being trusted on real data.
    'read out of the app', 'seed at', 'seed matches', 'field list matches',
    'against current source', 'against current head', 'at current head',
    'consumer sweep', 'swept every', 'direct read', 'directly against',
]
WEAK_EVIDENCE_MARKERS = [
    'appears to', 'plausible', 'seems', 'likely', 'should be', 'presumably',
]


def _bar_drift_fixture_control():
    """Blind control for the strong/weak evidence markers, BOTH directions,
    written before the 2026-09-28 vocabulary expansion was trusted on real
    data (blind-analysis discipline). A fixture whose expected verdict
    changes to match what the classifier says is the one thing this control
    must never do -- these are the PREDICTION."""
    cases = [
        # (label, sentence, expect_strong, expect_weak)
        ('old-vocabulary strong marker still fires',
         'I confirmed directly by reading the actual source.', True, False),
        ('new register-vocabulary strong marker fires',
         'READ OUT OF THE APP: the seed matches the cell exactly.', True, False),
        ('new head-vocabulary strong marker fires',
         'Re-verified against current source at the current head.', True, False),
        ('weak language still flags weak regardless of length',
         'This appears to be plausible and likely correct.', False, True),
        ('neutral prose with NEITHER is neither -- not everything must score',
         'Filed a note for the build agent to pick up next.', False, False),
        ("a citation alone ('sairnbuild.html:3267') is NOT by itself strong "
         '-- a bare file:line is not a claim to have looked, only a pointer',
         'sairnbuild.html:3267 seeds the record.', False, False),
    ]
    failures = []
    for label, sentence, exp_strong, exp_weak in cases:
        s = sentence.lower()
        got_strong = any(m in s for m in STRONG_EVIDENCE_MARKERS)
        got_weak = any(m in s for m in WEAK_EVIDENCE_MARKERS)
        if got_strong != exp_strong:
            failures.append('%s: strong expected %s, got %s' % (label, exp_strong, got_strong))
        if got_weak != exp_weak:
            failures.append('%s: weak expected %s, got %s' % (label, exp_weak, got_weak))
    return {
        'fixtures_run': len(cases),
        'fixtures_failed': failures,
        'FAIL_control': len(failures) > 0,
    }

TRIGGER_MARKERS = {
    'freshest-commit': ['freshest', 'just committed', 'just pushed', 'fresh claim'],
    'tier-proximity': ['tier a', 'tier b'],
    'self-caught-by-agent': ['self-caught', 'caught its own', 'caught my own', 'self-correct'],
    'user-directed': ['routed to', 'user directed', 'per michael', "michael's"],
    're-check-of-prior-clean': ['re-check', 're-audit', 'already passed', 'already clean'],
    'random/judgment': ['judgment', 'worth a second look', 'no rule said'],
}


def load_entries(path):
    entries = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def parse_ts(e):
    return datetime.fromisoformat(e['ts'].replace('Z', '+00:00'))


SAME_EVENT_MAX_GAP_S = 2


def _is_same_event(prev, cur, gap_s):
    """One review that produced two log rows, not two rotation events."""
    return (
        gap_s <= SAME_EVENT_MAX_GAP_S
        and prev['type'] == 'check'
        and cur['type'] == 'finding'
    )


def _routine_fixture_control():
    """Blind control for _is_same_event, in BOTH directions.

    Expected classifications are written here as literals and are the
    PREDICTION, not a recording of what the function returned. A control
    that only ever shows the classifier saying yes is not a control.
    """
    cases = [
        # (label, prev_type, cur_type, gap_s, expected_same_event)
        ('check->finding, 0s  (the real shape)',      'check',   'finding', 0,   True),
        ('check->finding, 2s  (boundary, inclusive)', 'check',   'finding', 2,   True),
        ('check->finding, 3s  (just outside)',        'check',   'finding', 3,   False),
        ('check->check,   0s  (two reviews, 1 sec)',  'check',   'check',   0,   False),
        ('finding->check, 0s  (reversed order)',      'finding', 'check',   0,   False),
        ('check->finding, 600s (real repeat)',        'check',   'finding', 600, False),
        ('check->finding, 0s, DIFFERENT refs',        'check',   'finding', 0,   True),
    ]
    failures = []
    for label, pt, ct, gap, expected in cases:
        got = _is_same_event({'type': pt}, {'type': ct}, gap)
        if got != expected:
            failures.append(f'{label}: expected {expected}, got {got}')
    return {
        'fixtures_run': len(cases),
        'fixtures_failed': failures,
        'FAIL_control': len(failures) > 0,
    }


def check_routine(entries):
    """FAA currency-vs-proficiency, applied to WHO gets checked.

    A same-event check->finding pair is not a real rotation event -- it is
    ONE review producing two log rows. Counting it as an adjacent-target-
    repeat is the identical mistake already caught and fixed in
    check_rechecked_after_clean() (entries 102/instance-102 self-audit);
    fixed here the same way rather than left as a second copy of the same
    bug.

    CRITERIA, STATED EXACTLY (the earlier version of this docstring said
    "same ref" and the code never checked ref -- a real spec-vs-code drift
    in this role's own tooling, found 2026-09-16 and corrected here):
    same-event requires BOTH (a) type sequence check -> finding, and
    (b) gap <= SAME_EVENT_MAX_GAP_S. Ref is NOT part of the test: pair
    seq 5->7 is a genuine same-event pair with two different refs.

    DISCLOSED LIMIT ON HOW THE THRESHOLD WAS SET. It was derived from the
    real log, not blind-locked ahead of it: across all 27 adjacent
    same-target pairs on 2026-09-16, gaps are strictly bimodal -- 7 pairs
    at 0s (every one of them check->finding) and 20 pairs at >= 63s (none
    of them check->finding). The 2s window sits inside a 63s empty band,
    so it is wide enough to survive second-precision timestamps straddling
    a tick and far too narrow to swallow a real rotation event. That is a
    measured margin, not a guess -- but it is calibration ON the data, and
    is stated as such rather than presented as an independent prediction.
    The synthetic fixtures in _routine_fixture_control() are the blind
    control for the classifier in both directions."""
    cf = [e for e in entries if e['type'] in ('check', 'finding') and e['target'] != 'self']
    targets = [e['target'] for e in cf]
    counts = Counter(targets)
    total = len(targets)

    adjacent_repeats = []
    same_event_repeats = []
    for i in range(1, len(cf)):
        if cf[i]['target'] == cf[i - 1]['target']:
            gap_s = (parse_ts(cf[i]) - parse_ts(cf[i - 1])).total_seconds()
            entry = (cf[i - 1]['seq'], cf[i]['seq'], cf[i]['target'])
            if _is_same_event(cf[i - 1], cf[i], gap_s):
                same_event_repeats.append(entry)
            else:
                adjacent_repeats.append(entry)

    max_share = max(counts.values()) / total if total else 0
    max_target = counts.most_common(1)[0][0] if counts else None

    # ── DECLARED vs UNDECLARED, ADDED 2026-09-16 WITH THE ROTATION INTERLOCK ──
    # hover_log.py now REFUSES an undeclared repeat, so from this point on
    # every new repeat must carry a --same-target-reason. Splitting the count
    # is what makes the gate's own effectiveness measurable instead of assumed:
    # undeclared repeats can now only be historical, and a rising DECLARED
    # count is the drift the escape hatch could otherwise hide. Repeats logged
    # before the gate existed have no reason field and are counted separately
    # rather than retroactively relabelled -- AS-FOUND is not overwritten.
    by_seq = {e['seq']: e for e in cf}
    declared, undeclared = [], []
    for pair in adjacent_repeats:
        (declared if (by_seq[pair[1]].get('same_target_reason') or '').strip()
         else undeclared).append(pair)

    return {
        'total_target_checks': total,
        'distribution': dict(counts),
        'adjacent_repeats': adjacent_repeats,
        'adjacent_repeats_declared': declared,
        'adjacent_repeats_undeclared': undeclared,
        'same_event_repeats_excluded': same_event_repeats,
        'max_share': round(max_share, 3),
        'max_share_target': max_target,
        'FAIL_adjacent_repeat': len(adjacent_repeats) > 0,
        'FAIL_concentration_over_40pct': max_share > 0.40,
    }


def check_technique_staleness(entries):
    """FAA currency-vs-proficiency, applied to WHAT gets exercised.

    A finding entry that REPORTS a technique as unused necessarily names that
    technique -- 'STRIDE has never been used' contains the word STRIDE. Naive
    keyword matching over ALL check/finding text would count that sentence as
    USE, which is exactly backwards: it is the record of NON-use quoting its
    own subject. Caught for real on this file's second run (2026-09-15): every
    technique but one flipped to USED the moment entry #81, which named all 20
    unused techniques by name to report them unused, was fed into this same
    corpus. Fixed by excluding target == 'self' entries (meta-commentary about
    this auditing process itself) from the usage corpus -- genuine use has to
    show up in a check/finding aimed at an actual build agent or the platform,
    not in a sentence ABOUT the audit tooling."""
    check_finding_text = ' '.join(
        e['summary'].lower() for e in entries
        if e['type'] in ('check', 'finding') and e['target'] != 'self'
    )
    note_only_text = ' '.join(
        e['summary'].lower() for e in entries if e['type'] == 'note'
    )

    results = {}
    never_used = []
    written_not_used = []
    for name, keywords in TECHNIQUES.items():
        used_in_practice = any(k in check_finding_text for k in keywords)
        written_about = any(k in note_only_text for k in keywords)
        if used_in_practice:
            results[name] = 'USED (appears in a check/finding entry)'
        elif written_about:
            results[name] = 'WRITTEN BUT NEVER USED (only appears in a note about the skill file)'
            written_not_used.append(name)
        else:
            results[name] = 'NEVER REFERENCED AT ALL in the self-log'
            never_used.append(name)

    return {
        'per_technique': results,
        'never_referenced_at_all': never_used,
        'written_but_never_used': written_not_used,
        'FAIL_majority_unused': (len(never_used) + len(written_not_used)) > (len(TECHNIQUES) / 2),
    }


def standing_technique_queue(staleness_result):
    """Turn the unused-technique list from a statistic into a real, standing
    queue instead of leaving it to chance whether any of them ever get tried.

    Order is fixed and disclosed (TECHNIQUES dict insertion order, stable in
    Python 3.7+) rather than picked fresh each run -- a queue whose order
    could silently shuffle is not a real queue, it is the appearance of one.
    A technique needs no separate "mark as done" step: the moment it is
    genuinely used in a real check/finding, the self-log itself proves it and
    it drops off this list on the next run. The queue is read FROM the
    append-only log, not maintained as separate mutable state that could
    drift from what actually happened.
    """
    # never-referenced ranks ahead of written-but-unused: a technique nobody
    # has even written a real trigger for yet is the harder gap to close.
    ordered = [
        n for n in TECHNIQUES
        if n in staleness_result['never_referenced_at_all']
    ] + [
        n for n in TECHNIQUES
        if n in staleness_result['written_but_never_used']
    ]
    return {
        'queue_in_priority_order': ordered,
        'next_up': ordered[0] if ordered else None,
        'queue_length': len(ordered),
        'rule': (
            'Every future rotation pick should ask, alongside Tier/freshness/'
            'judgment: does this target and this piece of work give next_up '
            'a genuine opening -- not force it in where it does not fit, but '
            'actively look for the fit before defaulting to a familiar '
            'technique. Re-run this script after any pass that used one; a '
            'technique used for real disappears from this list on its own.'
        ),
    }


def check_bar_drift(entries):
    """Bar Raiser: is the evidence bar still where it started."""
    cf = [e for e in entries if e['type'] in ('check', 'finding')]
    n = len(cf)
    if n < 4:
        return {'note': 'too few entries to split meaningfully'}
    half = n // 2
    first, second = cf[:half], cf[half:]

    def strong_rate(group):
        hits = 0
        for e in group:
            s = e['summary'].lower()
            if any(m in s for m in STRONG_EVIDENCE_MARKERS):
                hits += 1
        return hits / len(group) if group else 0

    def weak_rate(group):
        hits = 0
        for e in group:
            s = e['summary'].lower()
            if any(m in s for m in WEAK_EVIDENCE_MARKERS):
                hits += 1
        return hits / len(group) if group else 0

    first_strong, second_strong = strong_rate(first), strong_rate(second)
    drop_pct = round((first_strong - second_strong) * 100, 1)

    return {
        'first_half_n': len(first),
        'second_half_n': len(second),
        'first_half_strong_evidence_rate': round(first_strong, 3),
        'second_half_strong_evidence_rate': round(second_strong, 3),
        'first_half_weak_language_rate': round(weak_rate(first), 3),
        'second_half_weak_language_rate': round(weak_rate(second), 3),
        'drop_in_percentage_points': drop_pct,
        'FAIL_bar_dropped_over_15pp': drop_pct > 15.0,
    }


def check_independence_proxy(entries):
    """Bar Raiser: proximity to shipping pressure, using only what the log
    actually stores (inter-check timing and trigger-language), with the
    historical-claim-freshness gap disclosed rather than faked."""
    cf = [e for e in entries if e['type'] in ('check', 'finding')]
    gaps_minutes = []
    for i in range(1, len(cf)):
        dt = (parse_ts(cf[i]) - parse_ts(cf[i - 1])).total_seconds() / 60.0
        if dt >= 0:
            gaps_minutes.append(dt)

    session_gaps = [g for g in gaps_minutes if g > 120]  # >2h = likely a session boundary
    working_gaps = [g for g in gaps_minutes if g <= 120]

    trigger_hits = Counter()
    for e in cf:
        s = e['summary'].lower()
        matched_any = False
        for name, keywords in TRIGGER_MARKERS.items():
            if any(k in s for k in keywords):
                trigger_hits[name] += 1
                matched_any = True
        if not matched_any:
            trigger_hits['unclassified'] += 1

    return {
        'inter_check_gap_minutes_within_session': {
            'count': len(working_gaps),
            'min': round(min(working_gaps), 1) if working_gaps else None,
            'median': round(sorted(working_gaps)[len(working_gaps) // 2], 1) if working_gaps else None,
            'max': round(max(working_gaps), 1) if working_gaps else None,
        },
        'session_boundary_gaps_excluded': len(session_gaps),
        'trigger_language_distribution': dict(trigger_hits),
        'FAIL_100pct_immediate_response': (
            len(working_gaps) > 0 and max(working_gaps) < 5
        ),
        'DISCLOSED_LIMIT': (
            'This does not know how fresh a claim was at the moment it was picked '
            'for entries logged before this script existed -- the self-log does not '
            'store claim-relative timing. It only measures gaps between my own '
            'consecutive log entries and the presence of trigger-language in my own '
            'prose, which is a narrower and weaker claim than "was I under queue '
            'pressure."'
        ),
    }


def check_rechecked_after_clean(entries):
    """Rotation's own rule: 'occasionally re-check something that already
    passed.' Has this ever actually happened, by ref?

    A check entry immediately followed by a finding entry on the SAME ref,
    logged seconds apart, is one review producing two log rows -- not a
    genuine later re-check. Counting that as satisfying this rule would be
    the tool passing itself for the wrong reason, so entries on the same ref
    less than GENUINE_GAP_MINUTES apart are excluded before judging this."""
    GENUINE_GAP_MINUTES = 10
    refs = defaultdict(list)
    for e in entries:
        if e['type'] in ('check', 'finding') and e.get('ref'):
            refs[e['ref']].append(e)

    same_event_pairs = {}
    genuine_rechecks = {}
    for ref, es in refs.items():
        if len(es) < 2:
            continue
        es_sorted = sorted(es, key=lambda e: e['ts'])
        seqs = [e['seq'] for e in es_sorted]
        gaps = [
            (parse_ts(es_sorted[i]) - parse_ts(es_sorted[i - 1])).total_seconds() / 60.0
            for i in range(1, len(es_sorted))
        ]
        if max(gaps) >= GENUINE_GAP_MINUTES:
            genuine_rechecks[ref] = seqs
        else:
            same_event_pairs[ref] = seqs

    return {
        'same_event_check_finding_pairs_excluded': same_event_pairs,
        'genuine_later_rechecks_of_same_ref': genuine_rechecks,
        'FAIL_never_rechecked_anything': len(genuine_rechecks) == 0,
    }


# IIA Global Internal Audit Standards (effective 2025): every audit function
# needs a real, periodic External Quality Assessment -- an independent
# validation of the audit function's OWN METHOD, distinct from spot-checking
# individual findings. Calibrated against this role's own measured
# process-pass rate at the time this was built (3 real process passes across
# this session's full history, 2026-09-16) -- stated here so the number
# cannot be quietly adjusted without editing this comment too.
EQA_CADENCE = 3


def check_eqa_checkpoint_due(entries):
    """How many process passes have happened since the last INDEPENDENT EQA
    checkpoint, and is one due.

    STRUCTURAL FIELDS ONLY (process_pass / eqa_checkpoint), never a
    'PROCESS PASS' text match over summaries -- the same reliability reason
    --same-target-reason is a field and not a keyword. Entries logged before
    these fields existed (real process passes 40, 142, 147) do not carry
    them and CANNOT be retrofitted -- the append-only hash chain forbids
    editing a past entry, and that is the correct behaviour, not a bug to
    work around: AS-FOUND is never rewritten. Those three are disclosed here
    as a historical, non-mechanical count; the mechanical count below starts
    at zero from the first entry that actually carries the field, which is
    an honest, visible baseline shift rather than a silent one.
    """
    HISTORICAL_PRE_FIELD_PROCESS_PASSES = 3  # entries 40, 142, 147 -- see docstring

    mechanical_passes = [e for e in entries if e.get('process_pass')]
    checkpoints = [e for e in entries if e.get('eqa_checkpoint')]

    last_checkpoint_seq = checkpoints[-1]['seq'] if checkpoints else 0
    passes_since_checkpoint = [e for e in mechanical_passes if e['seq'] > last_checkpoint_seq]

    # The historical three count toward the FIRST checkpoint only, once, so
    # the very first checkpoint isn't stalled waiting for three BRAND NEW
    # mechanically-tagged passes on top of process passes that already
    # happened before the field existed.
    effective_count = len(passes_since_checkpoint)
    if not checkpoints:
        effective_count += HISTORICAL_PRE_FIELD_PROCESS_PASSES

    return {
        'eqa_cadence': EQA_CADENCE,
        'historical_pre_field_process_passes': HISTORICAL_PRE_FIELD_PROCESS_PASSES,
        'checkpoints_ever_performed': len(checkpoints),
        'last_checkpoint_seq': last_checkpoint_seq,
        'mechanically_tagged_passes_since_last_checkpoint': len(passes_since_checkpoint),
        'effective_count_toward_next_checkpoint': effective_count,
        'FAIL_eqa_checkpoint_due': effective_count >= EQA_CADENCE,
    }


def check_tip_beacon():
    """Is hover_tip_beacon.py's own checkpoint (TIP-BEACON.md) actually
    current, or has it drifted the way hover_self_health.py itself once did
    before the SessionStart hook existed. Found real 2026-09-17: the beacon
    had been published once, at entry 138, and never refreshed for the rest
    of the session -- 66 entries stale, well past its own 15-entry bound --
    because nothing called --publish and nothing reported --check either.
    A passive tripwire that requires an active step to reset is not passive;
    reusing the tripwire's own --check here, via subprocess rather than a
    reimplementation, is a report-only check with the same discipline as
    every other function in this file: this role decides what to do about a
    stale beacon (most likely, republish it), the check does not do it
    silently -- an auto-refresh on every session-start run would let the
    beacon always read fresh regardless of whether anyone actually looked,
    which defeats the one property (staleness is visible without trusting
    that someone remembered) the beacon exists for.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    beacon_script = os.path.join(here, 'hover_tip_beacon.py')
    if not os.path.isfile(beacon_script):
        return {'ran': False, 'reason': 'hover_tip_beacon.py not found next to this file',
                'FAIL_tip_beacon_stale': False}
    try:
        r = subprocess.run([sys.executable, beacon_script, '--check'],
                            capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {'ran': False, 'reason': 'subprocess failed: %s' % e,
                'FAIL_tip_beacon_stale': False}
    output = (r.stdout or '') + (r.stderr or '')
    # exit 0 = fresh, 1 = stale, 2 = tampered/unreadable -- both non-zero are
    # real conditions worth surfacing, not folded into one boolean.
    return {
        'ran': True,
        'exit_code': r.returncode,
        'output': output.strip(),
        'FAIL_tip_beacon_stale': r.returncode != 0,
    }


def check_undirected_sweep_due(entries):
    """Wraps undirected_sweep_freshness.py's own real check -- imported
    directly rather than subprocessed, since it is pure Python operating on
    the SAME entries list this function already receives, unlike
    check_tip_beacon() above which genuinely needs a separate process to
    read a different file. Makes SKILL.md's deliberately-undirected-sweep
    principle (round 3) a real, running SessionStart condition rather than
    a paragraph nobody is mechanically reminded of.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import undirected_sweep_freshness as usf
    except Exception as e:
        return {'ran': False, 'reason': 'could not import undirected_sweep_freshness.py: %s' % e,
                'FAIL_undirected_sweep_due': False}
    return dict(usf.check_undirected_sweep_freshness(entries), ran=True)


def check_scope_narrowing(entries):
    """Wraps scope_narrowing_check.py's own real check, imported directly
    for the same reason check_undirected_sweep_due() is: pure Python over
    the same entries list already in hand.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import scope_narrowing_check as snc
    except Exception as e:
        return {'ran': False, 'reason': 'could not import scope_narrowing_check.py: %s' % e,
                'FAIL_scope_narrowed': False}
    return dict(snc.check_scope_narrowing(entries), ran=True)


def check_tool_provenance():
    """Wraps tool_provenance_check.py's own real check. Not driven off
    `entries` like undirected_sweep/scope_narrowing above -- it scans the
    real .py files on disk and a separate validations ledger, neither of
    which is in the hover-audit-log.jsonl entries list already in hand --
    so this is closer in shape to check_tip_beacon() above, just via direct
    import (pure Python, no subprocess needed) rather than a subprocess.

    Built 2026-09-23, direct instruction, after checking and finding the
    gap twice over: sabotage_closed_system_check.py was only ever run by
    the session that wrote it, against fixtures that same session also
    wrote; hover_tool_index.py shipped with no self-check of any kind.
    Every tracked hover tool starts at zero validations until a genuinely
    DIFFERENT hover instance runs it against a real historical holdout of
    already-confirmed findings and records that it reproduced them --
    same precedent as a security auditor itself being audited, or an ML
    pipeline refusing to promote a model that has not beaten a real
    holdout baseline. See tool_provenance_check.py's own docstring for the
    full account; this wrapper only surfaces its verdict at SessionStart.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import tool_provenance_check as tpc
    except Exception as e:
        return {'ran': False, 'reason': 'could not import tool_provenance_check.py: %s' % e,
                'FAIL_any_never_validated': False}
    tools = tpc.discover_tools()
    if not tools:
        return {'ran': False, 'reason': 'no tools discovered to track',
                'FAIL_any_never_validated': False}
    validations = tpc.load_jsonl(tpc.DEFAULT_LEDGER)
    log_entries = tpc.load_jsonl(tpc.DEFAULT_LOG)
    r = tpc.check_tool_provenance(tools, validations, log_entries)
    # check_tool_provenance() itself is pure and does not touch the
    # filesystem, so has_own_selftest is filled in here, the same way
    # tool_provenance_check.py's own main() does it, so this wrapper's
    # no_selftest_and_never_validated is not silently empty.
    for t in tools:
        r['by_tool'][t]['has_own_selftest'] = tpc.has_own_selftest(os.path.join(here, t))
    r['no_selftest_and_never_validated'] = sorted(
        t for t, d in r['by_tool'].items()
        if not d['ever_reproduced'] and d.get('has_own_selftest') is False)
    r['ran'] = True
    return r


def _eqa_fixture_control():
    """Blind control for check_eqa_checkpoint_due, same discipline as
    _routine_fixture_control -- expected results are the PREDICTION, written
    before the call, not a recording of what it happened to return."""
    def fake(seq, process_pass=False, eqa_checkpoint=False):
        return {'seq': seq, 'process_pass': process_pass, 'eqa_checkpoint': eqa_checkpoint}

    cases = [
        ('no entries at all -- historical 3 alone hits cadence 3',
         [], True),
        ('one checkpoint, then only 2 new mechanically-tagged passes -- not due',
         [fake(1, eqa_checkpoint=True), fake(2, process_pass=True), fake(3, process_pass=True)],
         False),
        ('one checkpoint, then exactly 3 new mechanically-tagged passes -- due',
         [fake(1, eqa_checkpoint=True), fake(2, process_pass=True),
          fake(3, process_pass=True), fake(4, process_pass=True)],
         True),
        ('a process-pass entry BEFORE the checkpoint must not count toward the next one',
         [fake(1, process_pass=True), fake(2, eqa_checkpoint=True),
          fake(3, process_pass=True), fake(4, process_pass=True)],
         False),
        ('a second checkpoint resets the count again',
         [fake(1, eqa_checkpoint=True), fake(2, process_pass=True), fake(3, process_pass=True),
          fake(4, process_pass=True), fake(5, eqa_checkpoint=True), fake(6, process_pass=True)],
         False),
    ]
    failures = []
    for label, entries, expected_due in cases:
        got = check_eqa_checkpoint_due(entries)['FAIL_eqa_checkpoint_due']
        if got != expected_due:
            failures.append('%s: expected due=%s, got %s' % (label, expected_due, got))
    return {
        'fixtures_run': len(cases),
        'fixtures_failed': failures,
        'FAIL_control': len(failures) > 0,
    }


def build_report(entries, log_path=None):
    """THE ONE PLACE THIS ROLE'S OWN CHECK LIST IS DECIDED. Built 2026-09-17
    after hover_self_health_hook.py was found to have silently drifted from
    this file THREE TIMES -- tip_beacon, bar_drift and independence_proxy
    were each patched into the hook by hand, one at a time, and each time the
    hook's own hand-copied list was a second place that had to be kept in
    sync with this one and quietly was not, until someone happened to notice.

    Both main() and hover_self_health_hook.py now call this single function
    and read report['failures'] directly. A future new check added to the
    dict below is automatically surfaced at SessionStart the same day it is
    written -- there is no second list to remember to update.
    """
    staleness = check_technique_staleness(entries)
    report = {
        'generated_from': log_path,
        'total_entries': len(entries),
        'routine_classifier_control': _routine_fixture_control(),
        'eqa_classifier_control': _eqa_fixture_control(),
        'bar_drift_classifier_control': _bar_drift_fixture_control(),
        'routine': check_routine(entries),
        'technique_staleness': staleness,
        'standing_technique_queue': standing_technique_queue(staleness),
        'bar_drift': check_bar_drift(entries),
        'independence_proxy': check_independence_proxy(entries),
        'recheck_of_prior_clean': check_rechecked_after_clean(entries),
        'eqa_checkpoint': check_eqa_checkpoint_due(entries),
        'tip_beacon': check_tip_beacon(),
        'undirected_sweep': check_undirected_sweep_due(entries),
        'scope_narrowing': check_scope_narrowing(entries),
        'tool_provenance': check_tool_provenance(),
    }

    # ── MESSAGE TEXT LIVES HERE, ONCE, NOT ALSO IN THE HOOK ─────────────────
    # hover_self_health_hook.py used to hand-rebuild this exact list with its
    # own, independently-worded copies of each message -- a second place that
    # had to be kept in sync with this one, found out of sync three times
    # (tip_beacon, bar_drift, independence_proxy each patched in separately
    # before this refactor). The hook now prints report['failures'] verbatim.
    routine = report['routine']
    failures = []
    if report['routine_classifier_control']['FAIL_control']:
        failures.append('CONTROL: same-event classifier failed its own synthetic '
                        'fixtures (%s). Every ROUTINE number below is untrusted -- '
                        'treat as could-not-run, not as a pass.'
                        % '; '.join(report['routine_classifier_control']['fixtures_failed']))
    if report['eqa_classifier_control']['FAIL_control']:
        failures.append('CONTROL: EQA-checkpoint classifier failed its own synthetic '
                        'fixtures (%s). The EQA due/not-due number below is untrusted.'
                        % '; '.join(report['eqa_classifier_control']['fixtures_failed']))
    if report['bar_drift_classifier_control']['FAIL_control']:
        failures.append('CONTROL: bar-drift evidence-marker classifier failed its own '
                        'synthetic fixtures (%s). The BAR DRIFT number below is untrusted.'
                        % '; '.join(report['bar_drift_classifier_control']['fixtures_failed']))
    if routine['FAIL_adjacent_repeat']:
        failures.append('ROUTINE adjacent-repeat: %d total (%d undeclared, historical -- '
                        'the interlock in hover_log.py now refuses an undeclared repeat; '
                        '%d declared)' % (len(routine['adjacent_repeats']),
                                          len(routine['adjacent_repeats_undeclared']),
                                          len(routine['adjacent_repeats_declared'])))
    if routine['FAIL_concentration_over_40pct']:
        failures.append('ROUTINE concentration: %r holds %.1f%% of all attention'
                        % (routine['max_share_target'], routine['max_share'] * 100))
    if staleness['FAIL_majority_unused']:
        failures.append('STALENESS: %d of %d named techniques never used in a real check'
                        % (len(staleness['written_but_never_used'])
                           + len(staleness['never_referenced_at_all']), len(TECHNIQUES)))
    if report['bar_drift'].get('FAIL_bar_dropped_over_15pp'):
        bd = report['bar_drift']
        failures.append('BAR DRIFT: strong-evidence rate dropped %.1fpp, second half vs '
                        'first (%.1f%% -> %.1f%%)'
                        % (bd['drop_in_percentage_points'],
                           bd['first_half_strong_evidence_rate'] * 100,
                           bd['second_half_strong_evidence_rate'] * 100))
    if report['independence_proxy']['FAIL_100pct_immediate_response']:
        gap = report['independence_proxy']['inter_check_gap_minutes_within_session']
        failures.append('INDEPENDENCE: fastest-ever within-session response time (%.1f min) '
                        'is under 5 minutes -- flags for manual review, not proof of a '
                        'problem on its own' % gap['min'])
    if report['recheck_of_prior_clean']['FAIL_never_rechecked_anything']:
        failures.append('ROUTINE: never once re-checked a ref already marked clean')
    if report['eqa_checkpoint']['FAIL_eqa_checkpoint_due']:
        failures.append('EQA CHECKPOINT DUE: %d process pass(es) since the last independent '
                        'validation (cadence %d). Needs a genuinely separate reviewer -- a '
                        'fresh agent with no hand in the self-audit under review, or Michael '
                        'directly -- not this role re-grading itself.'
                        % (report['eqa_checkpoint']['effective_count_toward_next_checkpoint'],
                           report['eqa_checkpoint']['eqa_cadence']))
    if report['tip_beacon']['FAIL_tip_beacon_stale']:
        failures.append('TIP BEACON: %s -- run '
                        'python hover_tip_beacon.py --publish after confirming '
                        'this is staleness and not tampering'
                        % report['tip_beacon'].get('output', 'stale or unreadable'))
    if report['undirected_sweep'].get('FAIL_undirected_sweep_due'):
        us = report['undirected_sweep']
        failures.append('UNDIRECTED SWEEP DUE: %d real check/finding entries since the '
                        'last one (cadence %d, %s) -- run a pass with no target and no '
                        'seed chosen in advance, then log it with '
                        'hover_log.py --add ... --undirected-sweep'
                        % (us.get('real_entries_since_last_sweep', 0), us.get('cadence', 0),
                           us.get('cadence_basis', '')))
    if report['scope_narrowing'].get('FAIL_scope_narrowed'):
        sn = report['scope_narrowing']
        failures.append('SCOPE NARROWING: %s has gone quiet past %d real entries -- '
                        'attention only, not a confirmed finding; pick one for the '
                        'next targeted pass or confirm the quiet stretch is real'
                        % (', '.join(sn.get('narrowed_agents', [])), sn.get('threshold', 0)))
    if report['tool_provenance'].get('FAIL_any_never_validated'):
        tp = report['tool_provenance']
        failures.append('TOOL PROVENANCE: %d of %d hover tools have never had an '
                        'independent holdout validation recorded (a different hover '
                        'instance reproducing a real, already-confirmed finding with '
                        'it) -- run python tool_provenance_check.py for the per-tool '
                        'list, then --record once a real cross-session validation '
                        'has actually happened'
                        % (len(tp.get('never_validated', [])), tp.get('total_tools', 0)))

    report['failures'] = failures
    report['overall'] = 'FAIL' if failures else 'PASS (bounded -- see DISCLOSED_LIMIT fields)'
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', default=DEFAULT_LOG)
    ap.add_argument('--next-technique', action='store_true',
                     help='Print only the next unused technique to deliberately '
                          'work into an upcoming pass, then exit.')
    args = ap.parse_args()

    entries = load_entries(args.log)

    if args.next_technique:
        q = standing_technique_queue(check_technique_staleness(entries))
        print('NEXT UP (%d still queued): %s' % (q['queue_length'], q['next_up']))
        return 0

    report = build_report(entries, log_path=args.log)
    print(json.dumps(report, indent=2))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
