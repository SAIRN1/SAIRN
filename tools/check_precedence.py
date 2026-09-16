#!/usr/bin/env python
"""Item 64: what happens when two independent checks disagree about the same
thing -- decided in advance, in one place, instead of ad hoc under pressure.

    python tools/check_precedence.py                 # the live pairing below
    python tools/check_precedence.py --json
    python tools/check_precedence.py --claims f.json # arbitrate claims from a file
    python tools/check_precedence.py --self-check    # the rule table, exhaustively

Exit 0 all resolved CLEAN · 1 at least one FINDING · 2 at least one
COULD_NOT_RUN · 3 at least one CONFLICT. REPORT ONLY, AND CONFLICT BLOCKS
NOTHING -- see the section on exit 3.

── WHY A RULE AND NOT A JUDGEMENT ──────────────────────────────────────────
This platform runs ~50 checkers over overlapping subjects. Two of them landing
on opposite answers is not hypothetical: `removal_path_check` reports NO removal
verb for a pair of SAIRNbiz resources while a void mechanism demonstrably
exists, because the checker reads EXTRA_ACTIONS and cannot see a client-side
status field. Both statements are true about different things, and the ONLY
reason that did not get resolved badly is that somebody happened to write the
reconciliation down.

(The two resources are deliberately not named here. This file SERVES no Tier A
resource -- it arbitrates verdicts -- and naming them made
tools/tier_a_review_gate.py refuse the push for an unrecorded Tier A review
obligation. Filing one would have been the wrong repair: it would assert that a
report-only arbiter needs independent review of trust-adjacent code it does not
touch, which is exactly the false-positive shape recorded on 2026-09-15 for a
review probe that necessarily named what it reviewed. The example survives
without the names; the row in docs/SAIRN-OPEN-WORK-INDEX.md has them.)

A rule invented at the moment of disagreement is invented by whoever is under
the most pressure, in the direction that unblocks them. So it is written here
first.

── THE THREE CASES, AND A FOURTH THAT IS EASY TO MISS ──────────────────────

  1. FINDING vs CLEAN            -> FINDING WINS. No exceptions.
     CLEAN is the vacuous default: it is what a checker that does nothing
     produces. `checkblocks.py` exited 0 for months and looked exactly like a
     clean codebase. A finding is a positive assertion that somebody's code
     made; clean is the absence of one. They are not symmetric and must never
     be treated as two opinions of equal standing.

  2. FINDING vs COULD_NOT_RUN    -> FINDING WINS, and the COULD_NOT_RUN is
     CARRIED, never absorbed. The finding stands on its own evidence; the fact
     that another check could not look is a SECOND, separate thing that is
     still true and still needs fixing. Folding it into the finding loses it.

  3. FINDING vs FINDING, contradicting on the same fact -> CONFLICT.
     NEITHER WINS. It escalates to a human and BLOCKS NOTHING.

  4. CLEAN vs COULD_NOT_RUN      -> COULD_NOT_RUN. Never CLEAN.
     The one this file exists to stop being decided the other way at 2am.
     "Could not tell" is a third state and is never folded into "passed"
     (PR SS1.11). One check looked and saw nothing; the other did not look. The
     pair does not add up to a clean bill, and a rule that let it would make
     every unrunnable check free.

  Agreement is not a case: FINDING+FINDING on the same value is corroboration,
  CLEAN+CLEAN is clean, CNR+CNR is could-not-run.

── WHAT IS DELIBERATELY NOT THE TIEBREAK, AND THIS IS THE DESIGN DECISION ──
**NOT tools/checker_confidence.py's rating.** The obvious mechanism is to rank
the two checkers and let the higher-confidence one win. It is rejected, for a
reason that is about what that number MEASURES rather than about how good it is:

  confidence = min(stability_band, evidence_band)

Stability is "has this checker's verdict moved on unchanged code". Evidence is
"has a control ever shown it can fire at all". **Neither is a statement about
whether it is right ON THIS INPUT.** A checker with a perfect flip rate and a
thorough control can still be wrong about one file -- `secrets_inventory.py`
reported four OIDC variables and a correctly-guarded live Stripe key as
unguarded on its first run, and nothing about its rating predicted that.

Using the rating as a tiebreak would convert a REAL DISAGREEMENT into a
confident single answer, silently, in favour of whichever checker has been
around longer. That is strictly worse than saying "these two disagree" out loud:
it destroys the only signal that something is wrong, and it does it in the
direction that looks most authoritative.

The rating is still PRINTED beside a conflict, because it helps a human decide.
It does not decide.

── EXIT 3 EXISTS AND NOTHING MAY GATE ON IT ────────────────────────────────
A CONFLICT is a question, not a verdict. Blocking a push on "two of our tools
disagree" punishes whoever happens to be pushing for a disagreement that
predates them, and the reliable consequence is an override habit -- which this
repo has already recorded costing more than the gate saved. So this tool is
REPORT ONLY, is registered as such, and its exit 3 is for a human and for the
report-only sweep. If it is ever wired into a gate, that is a change to this
rule and needs to be argued here first.
"""

import argparse
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN, EXIT_CONFLICT = 0, 1, 2, 3

FINDING, CLEAN, COULD_NOT_RUN, CONFLICT = 'FINDING', 'CLEAN', 'COULD_NOT_RUN', 'CONFLICT'
KINDS = (FINDING, CLEAN, COULD_NOT_RUN)


def resolve_group(claims):
    """Arbitrate the claims about ONE (subject, property). Pure.

    Returns {verdict, reason, carried, sources}. `carried` is what must be
    reported ALONGSIDE the verdict rather than being replaced by it -- rule 2's
    whole point.
    """
    kinds = set(c['kind'] for c in claims)
    unknown = kinds - set(KINDS)
    if unknown:
        # A kind this table does not answer is a finding ABOUT THIS TABLE, not a
        # reason to pick something. Silence here would mean a new verdict
        # quietly having no precedence at all -- the same shape
        # api/_lib/cron-response.js's NO_PLAN row exists for.
        return {'verdict': CONFLICT,
                'reason': 'NO RULE: claim kind(s) %s are not in the precedence '
                          'table, so this pair has no decided answer'
                          % sorted(unknown),
                'carried': [], 'sources': [c['source'] for c in claims]}

    findings = [c for c in claims if c['kind'] == FINDING]
    cnrs = [c for c in claims if c['kind'] == COULD_NOT_RUN]
    cleans = [c for c in claims if c['kind'] == CLEAN]

    if findings:
        # RULE 3 FIRST. Two findings that assert different VALUES of the same
        # property contradict each other, and that has to be caught before rule
        # 1 or 2 hands the win to "a finding".
        values = set(json.dumps(c.get('value'), sort_keys=True) for c in findings)
        if len(values) > 1:
            return {'verdict': CONFLICT,
                    'reason': 'two findings assert different values for the same '
                              'property: %s' % ' vs '.join(sorted(values)),
                    'carried': cnrs, 'sources': [c['source'] for c in findings]}
        if len(findings) > 1:
            return {'verdict': FINDING,
                    'reason': 'corroborated by %d independent checks' % len(findings),
                    'carried': cnrs, 'sources': [c['source'] for c in findings]}
        if cleans and cnrs:
            reason = ('RULE 1+2: a finding beats a clean AND beats a '
                      'could-not-run; the could-not-run is carried, not absorbed')
        elif cleans:
            reason = ('RULE 1: a finding beats a clean. CLEAN is the vacuous '
                      'default -- it is what a checker that does nothing produces')
        elif cnrs:
            reason = ('RULE 2: a finding beats a could-not-run, and the '
                      'could-not-run is carried because it is a SECOND thing '
                      'that is still true')
        else:
            reason = 'the only claim'
        return {'verdict': FINDING, 'reason': reason, 'carried': cnrs,
                'sources': [c['source'] for c in findings]}

    if cnrs:
        # RULE 4. Reached whether or not a CLEAN is present, and that is the
        # whole point: a clean does not rescue a could-not-run.
        reason = ('RULE 4: a clean does NOT rescue a could-not-run. One check '
                  'looked and saw nothing; the other did not look, and the pair '
                  'does not add up to a clean bill'
                  if cleans else 'nothing could look')
        return {'verdict': COULD_NOT_RUN, 'reason': reason, 'carried': [],
                'sources': [c['source'] for c in cnrs]}

    values = set(json.dumps(c.get('value'), sort_keys=True) for c in cleans)
    if len(values) > 1:
        return {'verdict': CONFLICT,
                'reason': 'two clean claims assert different values for the same '
                          'property: %s' % ' vs '.join(sorted(values)),
                'carried': [], 'sources': [c['source'] for c in cleans]}
    return {'verdict': CLEAN,
            'reason': 'agreed by %d check(s)' % len(cleans) if len(cleans) > 1
                      else 'the only claim',
            'carried': [], 'sources': [c['source'] for c in cleans]}


def resolve(claims):
    """Group by (subject, property) and arbitrate each group."""
    groups = {}
    for c in claims:
        groups.setdefault((c['subject'], c.get('property', '')), []).append(c)
    out = []
    for (subject, prop), group in sorted(groups.items()):
        r = resolve_group(group)
        r['subject'] = subject
        r['property'] = prop
        r['claims'] = group
        out.append(r)
    return out


# ── THE LIVE PAIRING ────────────────────────────────────────────────────────
# A precedence rule nothing consults is a document. These two tools are a
# GENUINE overlapping pair rather than one invented to give this file a job:
# both answer "how much is this checker's verdict worth", by structurally
# different methods -- checker_confidence.py by CONJUNCTION (min of stability
# and control evidence) and checker_estimate_fusion.py by a WEIGHTED fusion of
# the same two signals. Item 52's own header argues they are different
# questions, and they are; where they disagree about whether a checker's verdict
# is worth anything AT ALL, that is exactly case 3.
#
# THE MAPPING IS TAKEN FROM EACH TOOL'S OWN DOCUMENTED EXIT SEMANTICS, NOT FROM
# A THRESHOLD INVENTED HERE. That matters: picking a `fused >= 0.8 means HIGH`
# cutoff would manufacture disagreements out of an arbitrary line, which is the
# fabricated-figure defect this platform polices hardest. So the comparison is
# made only on the three-valued kind both tools genuinely speak.
def _confidence_kind(row):
    c = (row.get('confidence') or '').upper()
    if c == 'UNKNOWN':
        return COULD_NOT_RUN, 'confidence UNKNOWN -- not enough to rate it'
    if c == 'LOW':
        return FINDING, 'confidence LOW -- the state this tool exits 1 for'
    return CLEAN, 'confidence ' + c


def _fusion_kind(row):
    s = (row.get('state') or '').upper()
    if 'COULD NOT TELL' in s:
        return COULD_NOT_RUN, 'fusion COULD NOT TELL -- no usable signal'
    if 'UNCORRECTED' in s:
        return FINDING, 'fusion UNCORRECTED -- its corrector failed its own check'
    return CLEAN, 'fusion ' + s


def _run_json(tool, timeout=240):
    """(rows, problem). A tool that will not run is COULD NOT RUN, not absent."""
    p = os.path.join(REPO, 'tools', tool)
    if not os.path.isfile(p):
        return None, tool + ' is not at ' + p
    try:
        r = subprocess.run([sys.executable, p, '--json'], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           cwd=REPO, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, tool + ' did not finish within %ds' % timeout
    txt = r.stdout
    if '{' not in txt:
        return None, tool + ' emitted no JSON (exit %d)' % r.returncode
    try:
        return json.loads(txt[txt.index('{'):]).get('rows') or [], ''
    except ValueError as exc:
        return None, '%s emitted unparseable JSON: %s' % (tool, exc)


def live_claims():
    """(claims, problems). Problems are reported, never silently dropped."""
    claims, problems = [], []
    conf, why = _run_json('checker_confidence.py')
    if conf is None:
        problems.append(why)
    fuse, why2 = _run_json('checker_estimate_fusion.py')
    if fuse is None:
        problems.append(why2)
    if conf is None or fuse is None:
        return claims, problems
    by_tool = {}
    for row in conf:
        kind, detail = _confidence_kind(row)
        by_tool.setdefault(row['tool'], []).append(
            {'source': 'checker_confidence.py', 'subject': row['tool'],
             'property': 'verdict_is_worth_something', 'kind': kind,
             'detail': detail, 'rating': row.get('confidence')})
    for row in fuse:
        kind, detail = _fusion_kind(row)
        by_tool.setdefault(row['tool'], []).append(
            {'source': 'checker_estimate_fusion.py', 'subject': row['tool'],
             'property': 'verdict_is_worth_something', 'kind': kind,
             'detail': detail, 'rating': row.get('state')})
    for tool, cs in by_tool.items():
        # ONE SIDE ONLY IS NOT A DISAGREEMENT and must not be reported as one.
        # A tool present in one report and absent from the other is a coverage
        # gap in the reports, which is worth knowing and is NOT case 3.
        if len(cs) == 1:
            problems.append('%s appears in only one of the two reports (%s), so '
                            'no comparison was possible' % (tool, cs[0]['source']))
            continue
        claims.extend(cs)
    return claims, problems


# ── the rule table, proved exhaustively rather than sampled ─────────────────
CASES = [
    ([FINDING, CLEAN], FINDING, 'rule 1'),
    ([CLEAN, FINDING], FINDING, 'rule 1, order does not matter'),
    ([FINDING, COULD_NOT_RUN], FINDING, 'rule 2'),
    ([COULD_NOT_RUN, FINDING], FINDING, 'rule 2, order does not matter'),
    ([CLEAN, COULD_NOT_RUN], COULD_NOT_RUN, 'rule 4 -- the easy one to get wrong'),
    ([COULD_NOT_RUN, CLEAN], COULD_NOT_RUN, 'rule 4, order does not matter'),
    ([FINDING, CLEAN, COULD_NOT_RUN], FINDING, 'rules 1+2 together'),
    ([FINDING, FINDING], FINDING, 'corroboration, not conflict'),
    ([CLEAN, CLEAN], CLEAN, 'agreement'),
    ([COULD_NOT_RUN, COULD_NOT_RUN], COULD_NOT_RUN, 'nothing could look'),
    ([FINDING], FINDING, 'a single claim is not a disagreement'),
    ([CLEAN], CLEAN, 'a single claim is not a disagreement'),
    ([COULD_NOT_RUN], COULD_NOT_RUN, 'a single claim is not a disagreement'),
]


def self_check(verbose=True):
    bad = []
    for kinds, want, label in CASES:
        claims = [{'source': 's%d' % i, 'subject': 'x', 'property': 'p', 'kind': k}
                  for i, k in enumerate(kinds)]
        got = resolve_group(claims)['verdict']
        if verbose:
            print('    %-34s -> %-14s %s'
                  % ('+'.join(kinds), got, 'ok' if got == want else 'EXPECTED ' + want))
        if got != want:
            bad.append((label, got, want))
    # Case 3 needs VALUES, so it is driven separately rather than by kind.
    v = resolve_group([
        {'source': 'a', 'subject': 'x', 'property': 'p', 'kind': FINDING, 'value': 'A'},
        {'source': 'b', 'subject': 'x', 'property': 'p', 'kind': FINDING, 'value': 'B'}])
    if verbose:
        print('    %-34s -> %-14s %s' % ('FINDING(A)+FINDING(B)', v['verdict'],
                                         'ok' if v['verdict'] == CONFLICT else 'EXPECTED CONFLICT'))
    if v['verdict'] != CONFLICT:
        bad.append(('case 3', v['verdict'], CONFLICT))
    u = resolve_group([{'source': 'a', 'subject': 'x', 'property': 'p', 'kind': 'WAT'}])
    if verbose:
        print('    %-34s -> %-14s %s' % ('an unknown kind', u['verdict'],
                                         'ok' if u['verdict'] == CONFLICT else 'EXPECTED CONFLICT'))
    if u['verdict'] != CONFLICT:
        bad.append(('unknown kind', u['verdict'], CONFLICT))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-check', action='store_true')
    ap.add_argument('--claims', help='a JSON file of claims to arbitrate')
    args = ap.parse_args(argv)

    if args.self_check:
        bad = self_check()
        print('\n%d case(s) wrong' % len(bad))
        return EXIT_CLEAN if not bad else EXIT_FINDING

    # THE RULE TABLE IS PROVED BEFORE ANY REAL CLAIM IS ARBITRATED, every run.
    # An arbiter that has silently stopped applying rule 4 would otherwise
    # report a platform clean using the exact precedence this file exists to
    # forbid.
    bad = self_check(verbose=False)
    if bad:
        print('COULD NOT RUN -- the rule table failed its own check, so nothing '
              'was arbitrated:')
        for label, got, want in bad:
            print('  %s resolved %s, expected %s' % (label, got, want))
        return EXIT_COULD_NOT_RUN

    problems = []
    if args.claims:
        try:
            claims = json.load(io.open(args.claims, encoding='utf-8'))
        except (OSError, ValueError) as exc:
            print('COULD NOT RUN: %s' % exc)
            return EXIT_COULD_NOT_RUN
    else:
        claims, problems = live_claims()

    results = resolve(claims)
    counts = {}
    for r in results:
        counts[r['verdict']] = counts.get(r['verdict'], 0) + 1

    if args.json:
        print(json.dumps({'results': results, 'problems': problems,
                          'counts': counts}, indent=1))
    else:
        print('check precedence: %d subject(s) with more than one claim' % len(results))
        for v in (CONFLICT, FINDING, COULD_NOT_RUN, CLEAN):
            if v in counts:
                print('    %-14s %d' % (v, counts[v]))
        print('')
        for r in results:
            if r['verdict'] == CLEAN:
                continue
            mark = '  ! ' if r['verdict'] == CONFLICT else '    '
            print('%s%-14s %s [%s]' % (mark, r['verdict'], r['subject'], r['property']))
            print('                  %s' % r['reason'])
            for c in r['claims']:
                print('                    %-32s %-14s %s'
                      % (c['source'], c['kind'], c.get('detail', '')))
            for c in r.get('carried') or []:
                print('                  CARRIED, not absorbed: %s could not look (%s)'
                      % (c['source'], c.get('detail', '')))
        if problems:
            print('')
            print('COULD NOT COMPARE (%d) -- reported, not dropped:' % len(problems))
            for p in problems[:20]:
                print('  - %s' % p)
            if len(problems) > 20:
                print('  ... and %d more' % (len(problems) - 20))
        print('')
        print('CONFLICT BLOCKS NOTHING. It is a question for a human, and no gate')
        print('consumes this tool. Confidence ratings are printed beside a')
        print('conflict to help somebody decide; they do not decide.')

    if counts.get(CONFLICT):
        return EXIT_CONFLICT
    if counts.get(FINDING):
        return EXIT_FINDING
    if counts.get(COULD_NOT_RUN) or problems:
        return EXIT_COULD_NOT_RUN
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
